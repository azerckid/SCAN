"""TASK-009 deterministic V1 and error-contract regression gate."""

import asyncio
import json
import socket
from collections.abc import Callable
from pathlib import Path

import pytest

from scan_tool.application.source_orchestration import RetryPolicy, SourceOrchestrator
from scan_tool.application.terminal import exit_code_for_result
from scan_tool.domain import validate_analysis_request, validate_analysis_result
from scan_tool.domain.analysis_error import ErrorCode
from scan_tool.domain.analysis_request import (
    AuthAnalysisRequest,
    DexAnalysisRequest,
    FreezeAnalysisRequest,
    SourcePolicy,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.source import (
    JsonRpcSourceRequest,
    SourceFailure,
    SourceFailureKind,
    SourcePayload,
)
from scan_tool.slices.auth import analyze_auth_replay
from scan_tool.slices.dex import analyze_dex_replay
from scan_tool.slices.freeze import analyze_freeze_replay

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/05_QA_Validation/examples/analysis"
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def _analyze_twice(name: str) -> tuple[AnalysisResult, AnalysisResult]:
    request = validate_analysis_request(_load_json(EXAMPLES / f"{name}-request.json")).root
    if isinstance(request, DexAnalysisRequest):
        analyzer: Callable[..., AnalysisResult] = analyze_dex_replay
        replay = FIXTURES / "FX-SVC-DEX-001/raw-replay.json"
    elif isinstance(request, AuthAnalysisRequest):
        analyzer = analyze_auth_replay
        replay = FIXTURES / "FX-EVM-AUTH-001/raw-replay.json"
    elif isinstance(request, FreezeAnalysisRequest):
        analyzer = analyze_freeze_replay
        replay = FIXTURES / "FX-EVM-FREEZE-001/raw-replay.json"
    else:
        raise AssertionError(f"unsupported integration fixture: {name}")
    raw = replay.read_bytes()
    return (
        analyzer(request, raw, checkpoint_id=f"CP-{name.upper()}-REGRESSION"),
        analyzer(request, raw, checkpoint_id=f"CP-{name.upper()}-REGRESSION"),
    )


@pytest.mark.parametrize("name", ("dex", "auth", "freeze"))
def test_confirmed_verticals_are_byte_stable_without_network(
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*_: object, **__: object) -> socket.socket:
        raise AssertionError("offline regression attempted a network connection")

    monkeypatch.setattr(socket, "socket", reject_network)
    first, second = _analyze_twice(name)

    assert first.root.status == second.root.status == "complete"
    assert first.to_contract_dict() == second.to_contract_dict()
    assert first.model_dump_json() == second.model_dump_json()


ERROR_MATRIX = {
    ErrorCode.INVALID_INPUT: ("failed", 2),
    ErrorCode.UNSUPPORTED_CHAIN: ("failed", 4),
    ErrorCode.SOURCE_UNAVAILABLE: ("partial", 3),
    ErrorCode.RATE_LIMITED: ("partial", 3),
    ErrorCode.ARCHIVE_REQUIRED: ("partial", 3),
    ErrorCode.TRACE_UNAVAILABLE: ("partial", 3),
    ErrorCode.DECODE_FAILED: ("partial", 3),
    ErrorCode.EVIDENCE_INCOMPLETE: ("partial", 3),
    ErrorCode.RECONCILIATION_FAILED: ("failed", 4),
    ErrorCode.SCHEMA_INVALID: ("failed", 2),
    ErrorCode.RULE_RESTRICTED: ("failed", 5),
}


def _result_with_error(code: ErrorCode, status: str) -> AnalysisResult:
    document = _load_json(EXAMPLES / "dex-result.json")
    document["status"] = status
    if status == "failed":
        document["results"] = []
        document["evidence"] = []
        document["sources"] = []
        document["warnings"] = []
    document["errors"] = [
        {
            "error_id": f"ERR-REG-{code.value.upper().replace('_', '-')}",
            "code": code.value,
            "message": "Structured TASK-009 error matrix probe.",
            "stage": "integration_gate",
            "retryable": False,
            "attempt_count": 0,
        }
    ]
    return validate_analysis_result(document)


@pytest.mark.parametrize(
    ("code", "expected"),
    tuple(ERROR_MATRIX.items()),
)
def test_all_error_codes_have_valid_status_and_exit_code(
    code: ErrorCode,
    expected: tuple[str, int],
) -> None:
    status, exit_code = expected
    result = _result_with_error(code, status)

    assert result.root.status == status
    assert result.root.errors[0].code is code
    assert exit_code_for_result(result) == exit_code


def test_error_matrix_covers_the_complete_public_enum() -> None:
    assert set(ERROR_MATRIX) == set(ErrorCode)


class FailingLiveAdapter:
    source_id = "DS-EVM-RPC-PUBLIC"
    provider_id = "provider-failure-probe"

    async def execute(self, request: object) -> SourcePayload:
        raise SourceFailure(SourceFailureKind.UNAVAILABLE, "reviewed source failure")


def test_live_source_failure_cannot_change_offline_fixture_result() -> None:
    before, _ = _analyze_twice("dex")
    execution = asyncio.run(
        SourceOrchestrator(
            [FailingLiveAdapter()],
            retry_policy=RetryPolicy(max_attempts=1),
        ).execute(
            JsonRpcSourceRequest(
                capability="transaction",
                method="eth_getTransactionByHash",
                params=["0x" + "ab" * 32],
            ),
            SourcePolicy.model_validate(
                {
                    "rule_status": "allowed",
                    "allowed_source_ids": ["DS-EVM-RPC-PUBLIC"],
                    "source_order": ["DS-EVM-RPC-PUBLIC"],
                    "allow_fallback": False,
                    "offline_mode": False,
                }
            ),
        )
    )
    after, _ = _analyze_twice("dex")

    assert execution.error is not None
    assert execution.error.code is ErrorCode.SOURCE_UNAVAILABLE
    assert before.to_contract_dict() == after.to_contract_dict()
