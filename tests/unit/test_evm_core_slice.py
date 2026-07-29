"""TASK-012 EVM Core complete, partial, and failed replay tests."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import EvmCoreAnalysisRequest
from scan_tool.slices.evm_core import analyze_evm_core_replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    "FX-BASIC-EVM-001",
    "FX-BASIC-EVM-002",
    "FX-EVM-TOKEN-001",
    "FX-EVM-TOKEN-002",
)


def _request(fixture_id: str) -> EvmCoreAnalysisRequest:
    request = validate_analysis_request(
        json.loads((FIXTURES / fixture_id / "analysis-request.json").read_text())
    ).root
    assert isinstance(request, EvmCoreAnalysisRequest)
    return request


def _replay(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "raw-replay.json").read_text())


@pytest.mark.parametrize("fixture_id", CASES)
def test_complete_replays_are_deterministic(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    first = analyze_evm_core_replay(request, replay)
    second = analyze_evm_core_replay(request, replay)

    assert first.root.status == "complete"
    assert first.root.results
    assert first.root.evidence
    assert first.to_contract_dict() == second.to_contract_dict()


@pytest.mark.parametrize(
    ("fixture_id", "mutate", "error_code"),
    (
        ("FX-BASIC-EVM-001", lambda value: value["codes"].pop(), "source_unavailable"),
        ("FX-BASIC-EVM-002", lambda value: value["token_states"].clear(), "archive_required"),
        (
            "FX-EVM-TOKEN-001",
            lambda value: value.update(range_complete=False),
            "evidence_incomplete",
        ),
        (
            "FX-EVM-TOKEN-002",
            lambda value: (value.update(trace_complete=False), value["internal_calls"].clear()),
            "trace_unavailable",
        ),
    ),
)
def test_incomplete_replays_preserve_partial_results(
    fixture_id: str,
    mutate: Callable[[dict[str, object]], object],
    error_code: str,
) -> None:
    replay = _replay(fixture_id)
    mutate(replay)

    result = analyze_evm_core_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "partial"
    assert result.root.results
    assert result.root.errors[0].code == error_code


@pytest.mark.parametrize("fixture_id", CASES)
def test_invalid_replay_is_structured_failed(fixture_id: str) -> None:
    result = analyze_evm_core_replay(_request(fixture_id), b"{}")

    assert result.root.status == "failed"
    assert result.root.results == []
    assert result.root.evidence == []
    assert result.root.errors[0].code == "decode_failed"


def test_multiple_internal_inflows_have_unique_evidence_ids() -> None:
    fixture_id = "FX-EVM-TOKEN-002"
    replay = _replay(fixture_id)
    internal_calls = cast(list[dict[str, object]], replay["internal_calls"])
    second_call = dict(internal_calls[0])
    second_call["index"] = "2"
    second_call["value"] = "1"
    internal_calls.append(second_call)

    result = analyze_evm_core_replay(_request(fixture_id), json.dumps(replay).encode())
    evidence_ids = [item.evidence_id for item in result.root.evidence]

    assert result.root.status == "complete"
    assert len(evidence_ids) == len(set(evidence_ids))
    assert "EV-TOKEN-INTERNAL-ETH-2" in evidence_ids


@pytest.mark.parametrize(
    ("fixture_id", "mutate"),
    (
        (
            "FX-BASIC-EVM-001",
            lambda value: value["codes"][0].update(block_number="0x1"),
        ),
        (
            "FX-EVM-TOKEN-001",
            lambda value: value.update(start_block="0x1"),
        ),
    ),
)
def test_replay_scope_mismatch_is_structured_failed(
    fixture_id: str,
    mutate: Callable[[dict[str, object]], object],
) -> None:
    replay = _replay(fixture_id)
    mutate(replay)

    result = analyze_evm_core_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "decode_failed"


def test_unrelated_transaction_internal_call_is_not_counted() -> None:
    fixture_id = "FX-EVM-TOKEN-002"
    replay = _replay(fixture_id)
    internal_calls = cast(list[dict[str, object]], replay["internal_calls"])
    unrelated = dict(internal_calls[0])
    unrelated["transaction_hash"] = f"0x{'12' * 32}"
    unrelated["value"] = "999"
    internal_calls.append(unrelated)

    result = analyze_evm_core_replay(_request(fixture_id), json.dumps(replay).encode())
    value = result.root.results[0].value

    assert result.root.status == "complete"
    assert value["successful_call_count"] == 1
    assert value["internal_inflow_wei"] == "14449515027026387018"
