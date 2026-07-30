"""TASK-015 intel_context (Label/OSINT/Actor) complete, partial, failed tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import IntelContextAnalysisRequest
from scan_tool.slices.intel_context import analyze_intel_context_replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
COMPLETE_CASES = (
    "FX-OSINT-LABEL-CONFLICT-001",
    "FX-OSINT-SANCTIONS-HISTORY-001",
    "FX-OSINT-ENS-CONFLICT-001",
    "FX-ACTOR-RELATION-HUB-001",
)


def _request_document(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "analysis-request.json").read_text())


def _request(fixture_id: str) -> IntelContextAnalysisRequest:
    request = validate_analysis_request(_request_document(fixture_id)).root
    assert isinstance(request, IntelContextAnalysisRequest)
    return request


def _replay(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "source-replay.json").read_text())


@pytest.mark.parametrize("fixture_id", COMPLETE_CASES)
def test_complete_replays_are_deterministic(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    first = analyze_intel_context_replay(request, replay)
    second = analyze_intel_context_replay(request, replay)

    assert first.root.status == "complete"
    assert first.root.results and first.root.evidence
    assert first.to_contract_dict() == second.to_contract_dict()


@pytest.mark.parametrize("fixture_id", COMPLETE_CASES)
def test_complete_results_keep_attribution_not_assessed(fixture_id: str) -> None:
    result = analyze_intel_context_replay(
        _request(fixture_id), json.dumps(_replay(fixture_id)).encode()
    )
    value = result.root.results[0].value
    blob = json.dumps(value)
    # ownership / criminality / coordination must never be asserted as truth
    for key in ("ownership_assessment", "criminality_assessment", "coordination_assessment"):
        if key in blob:
            assert f'"{key}": "not_assessed"' in json.dumps(value, separators=(", ", ": "))


def test_common_funder_is_partial_until_completeness_proven() -> None:
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    result = analyze_intel_context_replay(
        _request(fixture_id), json.dumps(_replay(fixture_id)).encode()
    )
    assert result.root.status == "partial"
    assert result.root.errors[0].code == "evidence_incomplete"
    value = result.root.results[0].value
    assert value["common_funder_assessment"] == "candidate"
    assert value["initial_inflow_complete"] is False


def test_common_funder_complete_when_both_completeness_hold() -> None:
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    replay = _replay(fixture_id)
    replay["initial_inflow_complete"] = True
    replay["service_exclusion_complete"] = True
    replay["coverage_gaps"] = []
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "complete"


@pytest.mark.parametrize("fixture_id", COMPLETE_CASES)
def test_invalid_replay_is_structured_failed(fixture_id: str) -> None:
    result = analyze_intel_context_replay(_request(fixture_id), b"{}")
    assert result.root.status == "failed"
    assert result.root.results == []
    assert result.root.errors[0].code == "decode_failed"


def test_label_subject_not_bound_to_request_is_rejected() -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    replay = _replay(fixture_id)
    replay["subject_address"] = "0x00000000000000000000000000000000000000ff"
    replay["ens"]["address"] = "0x00000000000000000000000000000000000000ff"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_label_dataset_and_ens_address_divergence_is_rejected() -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    replay = _replay(fixture_id)
    replay["ens"]["address"] = "0x00000000000000000000000000000000000000ff"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_actor_hub_mismatch_with_request_is_rejected() -> None:
    fixture_id = "FX-ACTOR-RELATION-HUB-001"
    replay = _replay(fixture_id)
    replay["hub"]["address"] = "0x00000000000000000000000000000000000000ff"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_query_kind_shape_mismatch_is_rejected() -> None:
    # A label request pointed at the ENS replay bundle must not silently succeed.
    request = _request("FX-OSINT-LABEL-CONFLICT-001")
    ens_replay = json.dumps(_replay("FX-OSINT-ENS-CONFLICT-001")).encode()
    result = analyze_intel_context_replay(request, ens_replay)
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_restricted_source_policy_blocks_before_decode() -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["source_policy"])["offline_mode"] = False
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"
