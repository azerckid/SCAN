"""Source policy, retry, and fallback orchestration tests."""

import asyncio
from datetime import UTC, datetime

from scan_tool.application.source_orchestration import RetryPolicy, SourceOrchestrator
from scan_tool.domain.analysis_error import ErrorCode
from scan_tool.domain.analysis_request import SourcePolicy
from scan_tool.domain.source import (
    JsonRpcSourceRequest,
    SourceAttemptOutcome,
    SourceFailure,
    SourceFailureKind,
    SourcePayload,
)

NOW = datetime(2026, 7, 27, 13, 0, tzinfo=UTC)


class ScriptedAdapter:
    def __init__(
        self,
        source_id: str,
        provider_id: str,
        actions: list[SourcePayload | SourceFailure],
    ) -> None:
        self.source_id = source_id
        self.provider_id = provider_id
        self.actions = actions
        self.call_count = 0

    async def execute(self, request: object) -> SourcePayload:
        self.call_count += 1
        action = self.actions[self.call_count - 1]
        if isinstance(action, SourceFailure):
            raise action
        return action


def source_policy(
    *,
    rule_status: str = "allowed",
    source_order: list[str] | None = None,
    allow_fallback: bool = True,
    offline_mode: bool = False,
) -> SourcePolicy:
    order = source_order or ["DS-EVM-RPC-PUBLIC"]
    return SourcePolicy.model_validate(
        {
            "rule_status": rule_status,
            "allowed_source_ids": order,
            "source_order": order,
            "allow_fallback": allow_fallback,
            "offline_mode": offline_mode,
        }
    )


def request() -> JsonRpcSourceRequest:
    return JsonRpcSourceRequest(
        capability="transaction",
        method="eth_getTransactionByHash",
        params=["0x" + "ab" * 32],
    )


def payload(raw_bytes: bytes = b'{"result":"ok"}') -> SourcePayload:
    return SourcePayload(
        raw_bytes=raw_bytes,
        status_code=200,
        media_type="application/json",
        endpoint_host="rpc.example",
        endpoint_path="/",
        retrieved_at=NOW,
    )


def run(orchestrator: SourceOrchestrator, policy: SourcePolicy):
    return asyncio.run(orchestrator.execute(request(), policy))


def test_policy_blocks_restricted_offline_and_unconfirmed_live_before_adapter_call() -> None:
    adapter = ScriptedAdapter("DS-EVM-RPC-PUBLIC", "provider-a", [payload()])
    orchestrator = SourceOrchestrator([adapter], clock=lambda: NOW)

    restricted = run(orchestrator, source_policy(rule_status="restricted"))
    offline = run(orchestrator, source_policy(offline_mode=True))
    unconfirmed = run(orchestrator, source_policy(rule_status="unconfirmed"))

    assert restricted.error is not None
    assert restricted.error.code is ErrorCode.RULE_RESTRICTED
    assert restricted.error.stage == "source_policy"
    assert offline.error is not None
    assert offline.error.code is ErrorCode.SOURCE_UNAVAILABLE
    assert offline.error.stage == "source_transport"
    assert unconfirmed.error is not None
    assert unconfirmed.error.code is ErrorCode.RULE_RESTRICTED
    assert restricted.attempts == offline.attempts == unconfirmed.attempts == ()
    assert adapter.call_count == 0


def test_retry_records_timeout_transient_error_and_success() -> None:
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    adapter = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(SourceFailureKind.TIMEOUT, "source request timed out"),
            SourceFailure(
                SourceFailureKind.TRANSIENT,
                "source returned a temporary server error",
                status_code=503,
                raw_bytes=b"temporary",
            ),
            payload(),
        ],
    )
    orchestrator = SourceOrchestrator(
        [adapter],
        retry_policy=RetryPolicy(jitter_ratio=0),
        sleep=record_sleep,
        clock=lambda: NOW,
    )

    execution = run(orchestrator, source_policy())

    assert execution.succeeded
    assert waits == [0.5, 1.0]
    assert [attempt.outcome for attempt in execution.attempts] == [
        SourceAttemptOutcome.FAILED,
        SourceAttemptOutcome.FAILED,
        SourceAttemptOutcome.SUCCESS,
    ]
    assert [attempt.retryable for attempt in execution.attempts] == [True, True, False]
    assert execution.attempts[1].raw_sha256 is not None


def test_retry_after_overrides_backoff() -> None:
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    adapter = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(
                SourceFailureKind.RATE_LIMITED,
                "source rate limit reached",
                status_code=429,
                retry_after="4",
            ),
            payload(),
        ],
    )
    orchestrator = SourceOrchestrator(
        [adapter],
        sleep=record_sleep,
        clock=lambda: NOW,
    )

    execution = run(orchestrator, source_policy())

    assert execution.succeeded
    assert waits == [4.0]
    assert execution.attempts[0].wait_seconds == 4.0


def test_invalid_retry_after_uses_bounded_backoff() -> None:
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    adapter = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(
                SourceFailureKind.RATE_LIMITED,
                "source rate limit reached",
                status_code=429,
                retry_after="NaN",
            ),
            payload(),
        ],
    )
    orchestrator = SourceOrchestrator(
        [adapter],
        retry_policy=RetryPolicy(jitter_ratio=0),
        sleep=record_sleep,
        clock=lambda: NOW,
    )

    execution = run(orchestrator, source_policy())

    assert execution.succeeded
    assert waits == [0.5]


def test_permanent_failure_is_not_retried_and_fallback_is_preserved() -> None:
    primary = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(
                SourceFailureKind.PERMANENT,
                "source rejected the request",
                status_code=400,
                raw_bytes=b"bad request",
            )
        ],
    )
    secondary = ScriptedAdapter(
        "DS-EVM-RPC-ARCHIVE",
        "provider-b",
        [payload(b'{"result":"fallback"}')],
    )
    order = ["DS-EVM-RPC-PUBLIC", "DS-EVM-RPC-ARCHIVE"]
    orchestrator = SourceOrchestrator([primary, secondary], clock=lambda: NOW)

    execution = run(orchestrator, source_policy(source_order=order))

    assert execution.succeeded
    assert primary.call_count == secondary.call_count == 1
    assert execution.response is not None
    assert execution.response.source_id == "DS-EVM-RPC-ARCHIVE"
    assert execution.response.provider_id == "provider-b"
    assert execution.response.fallback_from == ("DS-EVM-RPC-PUBLIC",)
    assert [attempt.source_id for attempt in execution.attempts] == order


def test_fallback_false_never_calls_second_source() -> None:
    primary = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [SourceFailure(SourceFailureKind.UNAVAILABLE, "source request failed")],
    )
    secondary = ScriptedAdapter(
        "DS-EVM-RPC-ARCHIVE",
        "provider-b",
        [payload()],
    )
    order = ["DS-EVM-RPC-PUBLIC", "DS-EVM-RPC-ARCHIVE"]
    orchestrator = SourceOrchestrator([primary, secondary], clock=lambda: NOW)

    execution = run(
        orchestrator,
        source_policy(source_order=order, allow_fallback=False),
    )

    assert not execution.succeeded
    assert execution.error is not None
    assert execution.error.code is ErrorCode.SOURCE_UNAVAILABLE
    assert primary.call_count == 1
    assert secondary.call_count == 0


def test_exhausted_rate_limit_uses_structured_error() -> None:
    adapter = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(
                SourceFailureKind.RATE_LIMITED,
                "source rate limit reached",
                status_code=429,
            )
        ],
    )
    orchestrator = SourceOrchestrator(
        [adapter],
        retry_policy=RetryPolicy(max_attempts=1),
        clock=lambda: NOW,
    )

    execution = run(orchestrator, source_policy())

    assert execution.error is not None
    assert execution.error.code is ErrorCode.RATE_LIMITED
    assert execution.error.stage == "source_transport"
    assert execution.error.retryable is False
    assert execution.error.attempt_count == 1


def test_invalid_response_is_not_retried() -> None:
    adapter = ScriptedAdapter(
        "DS-EVM-RPC-PUBLIC",
        "provider-a",
        [
            SourceFailure(
                SourceFailureKind.INVALID_RESPONSE,
                "source returned malformed JSON",
                status_code=200,
                raw_bytes=b"not-json",
            ),
            payload(),
        ],
    )
    orchestrator = SourceOrchestrator([adapter], clock=lambda: NOW)

    execution = run(orchestrator, source_policy())

    assert not execution.succeeded
    assert adapter.call_count == 1
    assert len(execution.attempts) == 1
    assert execution.attempts[0].retryable is False


def test_duplicate_source_ids_are_rejected() -> None:
    first = ScriptedAdapter("DS-EVM-RPC-PUBLIC", "provider-a", [payload()])
    second = ScriptedAdapter("DS-EVM-RPC-PUBLIC", "provider-b", [payload()])

    try:
        SourceOrchestrator([first, second])
    except ValueError as error:
        assert str(error) == "source_id values must be unique"
    else:
        raise AssertionError("duplicate source IDs must be rejected")
