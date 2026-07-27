"""Rules-gated retry and fallback orchestration for read-only sources."""

import asyncio
import hashlib
import math
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from scan_tool.domain.analysis_error import ErrorCode
from scan_tool.domain.analysis_request import RuleStatus, SourcePolicy
from scan_tool.domain.source import (
    SourceAttempt,
    SourceAttemptOutcome,
    SourceExecution,
    SourceExecutionError,
    SourceFailure,
    SourceFailureKind,
    SourcePayload,
    SourceRequest,
    SourceResponse,
    source_request_fingerprint,
)
from scan_tool.ports.source import SourceAdapter

type Clock = Callable[[], datetime]
type Sleeper = Callable[[float], Awaitable[None]]
type RandomValue = Callable[[], float]

RETRYABLE_FAILURES = {
    SourceFailureKind.TIMEOUT,
    SourceFailureKind.RATE_LIMITED,
    SourceFailureKind.TRANSIENT,
}


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must not be negative")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between 0 and 1")


class SourceOrchestrator:
    """Apply policy, retry, and fallback without owning transport clients."""

    def __init__(
        self,
        adapters: Sequence[SourceAdapter],
        *,
        retry_policy: RetryPolicy | None = None,
        sleep: Sleeper = asyncio.sleep,
        clock: Clock | None = None,
        random_value: RandomValue = random.random,
    ) -> None:
        self._adapters = {adapter.source_id: adapter for adapter in adapters}
        if len(self._adapters) != len(adapters):
            raise ValueError("source_id values must be unique")
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep
        self._clock = clock or (lambda: datetime.now(UTC))
        self._random_value = random_value

    async def execute(
        self,
        request: SourceRequest,
        policy: SourcePolicy,
    ) -> SourceExecution:
        policy_error = self._policy_error(policy)
        if policy_error is not None:
            return SourceExecution(response=None, attempts=(), error=policy_error)

        source_ids = list(policy.source_order)
        if not policy.allow_fallback:
            source_ids = source_ids[:1]

        attempts: list[SourceAttempt] = []
        failed_sources: list[str] = []
        last_failure: SourceFailure | None = None
        last_adapter: SourceAdapter | None = None

        for source_id in source_ids:
            adapter = self._adapters.get(source_id)
            if adapter is None or source_id not in policy.allowed_source_ids:
                continue
            last_adapter = adapter
            response, source_attempts, last_failure = await self._execute_source(
                adapter,
                request,
            )
            attempts.extend(source_attempts)
            if response is not None:
                return SourceExecution(
                    response=SourceResponse(
                        source_id=adapter.source_id,
                        provider_id=adapter.provider_id,
                        request_fingerprint=source_request_fingerprint(request),
                        payload=response,
                        attempts=tuple(attempts),
                        fallback_from=tuple(failed_sources),
                    ),
                    attempts=tuple(attempts),
                    error=None,
                )
            failed_sources.append(adapter.source_id)

        error_code = (
            ErrorCode.RATE_LIMITED
            if last_failure is not None and last_failure.kind is SourceFailureKind.RATE_LIMITED
            else ErrorCode.SOURCE_UNAVAILABLE
        )
        return SourceExecution(
            response=None,
            attempts=tuple(attempts),
            error=SourceExecutionError(
                code=error_code,
                message=_safe_final_message(error_code),
                source_id=last_adapter.source_id if last_adapter else None,
                provider_id=last_adapter.provider_id if last_adapter else None,
                retryable=False,
                attempt_count=len(attempts),
            ),
        )

    def _policy_error(self, policy: SourcePolicy) -> SourceExecutionError | None:
        if policy.rule_status is RuleStatus.RESTRICTED:
            return SourceExecutionError(
                code=ErrorCode.RULE_RESTRICTED,
                message="source execution is restricted by the active rules policy",
                source_id=None,
                provider_id=None,
                retryable=False,
                attempt_count=0,
            )
        if policy.offline_mode:
            return SourceExecutionError(
                code=ErrorCode.SOURCE_UNAVAILABLE,
                message="offline mode has no source transport; use stored cache or fixture data",
                source_id=None,
                provider_id=None,
                retryable=False,
                attempt_count=0,
            )
        if policy.rule_status is not RuleStatus.ALLOWED:
            return SourceExecutionError(
                code=ErrorCode.RULE_RESTRICTED,
                message="live source execution requires an explicitly allowed rules policy",
                source_id=None,
                provider_id=None,
                retryable=False,
                attempt_count=0,
            )
        return None

    async def _execute_source(
        self,
        adapter: SourceAdapter,
        request: SourceRequest,
    ) -> tuple[SourcePayload | None, list[SourceAttempt], SourceFailure | None]:
        attempts: list[SourceAttempt] = []
        last_failure: SourceFailure | None = None
        for attempt_number in range(1, self._retry_policy.max_attempts + 1):
            started_at = self._clock()
            try:
                payload = await adapter.execute(request)
            except SourceFailure as failure:
                last_failure = failure
                retryable = failure.kind in RETRYABLE_FAILURES
                has_next_attempt = attempt_number < self._retry_policy.max_attempts
                wait_seconds = (
                    self._retry_delay(attempt_number, failure)
                    if retryable and has_next_attempt
                    else None
                )
                attempts.append(
                    SourceAttempt(
                        source_id=adapter.source_id,
                        provider_id=adapter.provider_id,
                        attempt_number=attempt_number,
                        started_at=started_at,
                        finished_at=self._clock(),
                        outcome=SourceAttemptOutcome.FAILED,
                        failure_kind=failure.kind,
                        status_code=failure.status_code,
                        retryable=retryable and has_next_attempt,
                        wait_seconds=wait_seconds,
                        raw_sha256=_sha256(failure.raw_bytes),
                    )
                )
                if wait_seconds is None:
                    break
                await self._sleep(wait_seconds)
            else:
                attempts.append(
                    SourceAttempt(
                        source_id=adapter.source_id,
                        provider_id=adapter.provider_id,
                        attempt_number=attempt_number,
                        started_at=started_at,
                        finished_at=self._clock(),
                        outcome=SourceAttemptOutcome.SUCCESS,
                        failure_kind=None,
                        status_code=payload.status_code,
                        retryable=False,
                        wait_seconds=None,
                        raw_sha256=payload.raw_sha256,
                    )
                )
                return payload, attempts, None
        return None, attempts, last_failure

    def _retry_delay(self, attempt_number: int, failure: SourceFailure) -> float:
        retry_after = _retry_after_seconds(failure.retry_after, self._clock())
        if retry_after is not None:
            return min(retry_after, self._retry_policy.max_delay_seconds)
        exponential = self._retry_policy.base_delay_seconds * 2 ** (attempt_number - 1)
        jitter = exponential * self._retry_policy.jitter_ratio * self._random_value()
        return min(exponential + jitter, self._retry_policy.max_delay_seconds)


def _retry_after_seconds(value: str | None, now: datetime) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if target.tzinfo is None:
            return None
        seconds = (target - now).total_seconds()
    if not math.isfinite(seconds):
        return None
    return max(0.0, seconds)


def _sha256(raw_bytes: bytes | None) -> str | None:
    if raw_bytes is None:
        return None
    return hashlib.sha256(raw_bytes).hexdigest()


def _safe_final_message(code: ErrorCode) -> str:
    if code is ErrorCode.RATE_LIMITED:
        return "all allowed source attempts were rate limited"
    return "all allowed sources failed or were unavailable"
