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


def test_common_funder_is_partial_and_splits_confirmed_from_candidate() -> None:
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    result = analyze_intel_context_replay(
        _request(fixture_id), json.dumps(_replay(fixture_id)).encode()
    )
    assert result.root.status == "partial"
    assert result.root.errors[0].code == "evidence_incomplete"
    by_type = {item.result_type: item for item in result.root.results}
    relations = by_type["find_common_funder_relations"]
    assessment = by_type["find_common_funder_assessment"]
    # confirmed on-chain seed outputs vs candidate hypothesis are separate results
    assert relations.classification == "confirmed_fact"
    assert assessment.classification == "heuristic"
    assert assessment.value["common_funder_assessment"] == "candidate"


def test_common_funder_claimed_completeness_flags_do_not_force_complete() -> None:
    """Reviewer P1: flipping the claimed completeness booleans must not manufacture
    a complete common-funder result — it stays partial-only."""
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    replay = _replay(fixture_id)
    replay["initial_inflow_complete"] = True
    replay["service_exclusion_complete"] = True
    replay["coverage_gaps"] = []
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "partial"
    assessment = next(
        item for item in result.root.results if item.result_type == "find_common_funder_assessment"
    )
    assert assessment.value["initial_inflow_complete"] is False


def test_common_funder_subject_set_must_match_exactly() -> None:
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    replay = _replay(fixture_id)
    replay["relations"] = replay["relations"][:1]
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_ens_unrelated_address_or_block_is_rejected() -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    replay = _replay(fixture_id)
    replay["block_number"] = 1
    replay["forward"]["address"] = "0x00000000000000000000000000000000000000ff"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_actor_unrequested_relation_source_fixture_is_rejected() -> None:
    fixture_id = "FX-ACTOR-RELATION-HUB-001"
    replay = _replay(fixture_id)
    replay["relations"][0]["source_fixture_id"] = "FX-UNRELATED-999"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_sanctions_dropped_official_action_is_rejected() -> None:
    fixture_id = "FX-OSINT-SANCTIONS-HISTORY-001"
    replay = _replay(fixture_id)
    replay["official_actions"] = replay["official_actions"][:1]
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_label_observation_block_mismatch_is_rejected() -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["inputs"])["observation_block"] = 1
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_provenance_source_outside_allowlist_is_rejected() -> None:
    """Reviewer P1: a replay source record outside the request allowlist must not
    be recorded as a real source of truth."""
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["source_policy"])["allowed_source_ids"] = ["DS-EVM-RPC-PUBLIC"]
    cast(dict[str, object], document["source_policy"])["source_order"] = ["DS-EVM-RPC-PUBLIC"]
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"


def test_ens_reverse_address_must_match_forward() -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    replay = _replay(fixture_id)
    replay["reverse"]["address"] = "0x00000000000000000000000000000000000000ff"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_ens_provider_replay_ref_must_bind_to_replay_source() -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["inputs"])["provider_replay_ref"] = (
        "artifact://sha256/" + "0" * 64
    )
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_actor_missing_relation_breaks_exact_subject_set() -> None:
    fixture_id = "FX-ACTOR-RELATION-HUB-001"
    replay = _replay(fixture_id)
    replay["relations"] = replay["relations"][:1]
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_actor_relation_weight_outside_request_is_rejected() -> None:
    fixture_id = "FX-ACTOR-RELATION-HUB-001"
    replay = _replay(fixture_id)
    replay["relations"][0]["relation"] = "unrelated_weight"
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_label_max_sources_budget_is_enforced() -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["inputs"])["max_sources"] = 1
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_sanctions_snapshot_ref_must_bind_to_replay_source() -> None:
    fixture_id = "FX-OSINT-SANCTIONS-HISTORY-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["inputs"])["current_list_snapshot_ref"] = (
        "artifact://sha256/" + "0" * 64
    )
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_common_funder_block_range_must_match_request() -> None:
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    document = _request_document(fixture_id)
    cast(dict[str, object], document["inputs"])["block_range"] = {"from": 1, "to": 2}
    request = validate_analysis_request(document).root
    assert isinstance(request, IntelContextAnalysisRequest)
    result = analyze_intel_context_replay(request, json.dumps(_replay(fixture_id)).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_artifact_ref_and_content_sha_mismatch_is_rejected() -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    replay = _replay(fixture_id)
    replay["sources"][0]["content_sha256"] = "0" * 64
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "decode_failed"


def test_binding_failures_are_not_retryable() -> None:
    fixture_id = "FX-OSINT-SANCTIONS-HISTORY-001"
    replay = _replay(fixture_id)
    replay["official_actions"] = replay["official_actions"][:1]
    result = analyze_intel_context_replay(_request(fixture_id), json.dumps(replay).encode())
    assert result.root.errors[0].retryable is False


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
