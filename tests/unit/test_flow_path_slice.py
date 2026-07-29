"""TASK-014 flow_path (PATH graph/ledger) complete, partial, and failed tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import FlowPathAnalysisRequest
from scan_tool.slices.flow_path import analyze_flow_path_replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    "FX-FLOW-PATH-001",
    "FX-FLOW-REMERGE-001",
    "FX-FLOW-MULTI-001",
)
VALUE_KEYS = {
    "FX-FLOW-PATH-001": ("graph", "path_candidates", "reconciliation"),
    "FX-FLOW-REMERGE-001": ("branches", "reconciliation", "excluded_edges"),
    "FX-FLOW-MULTI-001": (
        "exit_node",
        "contributions",
        "deduplicated_total_raw",
        "price_context",
        "attribution",
    ),
}


def _request_document(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "analysis-request.json").read_text())


def _request(fixture_id: str) -> FlowPathAnalysisRequest:
    request = validate_analysis_request(_request_document(fixture_id)).root
    assert isinstance(request, FlowPathAnalysisRequest)
    return request


def _replay(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "raw-replay.json").read_text())


def _expected(fixture_id: str) -> dict[str, object]:
    document = json.loads((FIXTURES / fixture_id / "expected.json").read_text())
    return {key: document[key] for key in VALUE_KEYS[fixture_id]}


@pytest.mark.parametrize("fixture_id", CASES)
def test_complete_replays_are_deterministic(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    first = analyze_flow_path_replay(request, replay)
    second = analyze_flow_path_replay(request, replay)

    assert first.root.status == "complete"
    assert first.root.results
    assert first.root.evidence
    assert first.to_contract_dict() == second.to_contract_dict()


@pytest.mark.parametrize("fixture_id", CASES)
def test_complete_replays_match_the_fixture_reference_answer(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    result = analyze_flow_path_replay(request, replay)

    assert result.root.status == "complete"
    assert result.root.results[0].value == _expected(fixture_id)


@pytest.mark.parametrize("fixture_id", CASES)
def test_invalid_replay_is_structured_failed(fixture_id: str) -> None:
    result = analyze_flow_path_replay(_request(fixture_id), b"{}")

    assert result.root.status == "failed"
    assert result.root.results == []
    assert result.root.evidence == []
    assert result.root.errors[0].code == "decode_failed"


def test_path_missing_internal_trace_is_partial_trace_unavailable() -> None:
    """The seed inflow edge rests on a single-provider internal trace; when it is
    absent the analyzer must not claim complete, but must preserve the confirmed
    downstream sub-path and report trace_unavailable."""
    fixture_id = "FX-FLOW-PATH-001"
    replay = _replay(fixture_id)
    replay["internal_edges"] = []

    result = analyze_flow_path_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "trace_unavailable"
    edges = result.root.results[0].value["graph"]["edges"]
    assert [edge["transfer_kind"] for edge in edges] == ["native_top_level", "native_top_level"]


def test_path_budget_below_hops_is_partial_evidence_incomplete() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    request_document = _request_document(fixture_id)
    cast(dict[str, object], cast(dict[str, object], request_document["inputs"])["budgets"])[
        "max_hops"
    ] = 1
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "evidence_incomplete"


def test_path_unrelated_terminal_does_not_return_complete() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    request_document = _request_document(fixture_id)
    cast(dict[str, object], cast(dict[str, object], request_document["inputs"])["terminal_policy"])[
        "terminal_node"
    ] = "0x00000000000000000000000000000000000000ff"
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status != "complete"


def test_path_block_windows_diverging_from_replay_are_rejected() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    request_document = _request_document(fixture_id)
    windows = cast(
        list[dict[str, int]],
        cast(dict[str, object], cast(dict[str, object], request_document["inputs"])["scope"])[
            "block_windows"
        ],
    )
    windows[0]["from"] = 1
    windows[0]["to"] = 1
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_remerge_external_inflow_is_excluded_not_subtracted() -> None:
    fixture_id = "FX-FLOW-REMERGE-001"
    result = analyze_flow_path_replay(
        _request(fixture_id), json.dumps(_replay(fixture_id)).encode()
    )

    value = result.root.results[0].value
    excluded = value["excluded_edges"]
    assert len(excluded) == 1
    assert excluded[0]["reason"] == "external_inflow_not_from_seed"
    assert excluded[0]["scope_status"] == "excluded"
    reconciliation = value["reconciliation"]
    # external dust is reported separately and never reduces the seed ledger
    assert reconciliation["external_inflow_raw_not_in_seed_ledger"] == excluded[0]["amount_raw"]
    assert reconciliation["confirmed_scoped_excluded_output_raw"] == "0"


def test_remerge_missing_branch_return_is_partial_source_unavailable() -> None:
    fixture_id = "FX-FLOW-REMERGE-001"
    replay = _replay(fixture_id)
    transactions = cast(list[dict[str, object]], replay["transactions"])
    replay["transactions"] = [item for item in transactions if item["label"] != "merge_a"]
    request_document = _request_document(fixture_id)
    scope = cast(dict[str, object], cast(dict[str, object], request_document["inputs"])["scope"])
    dropped_hash = "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d"
    scope["selected_transactions"] = [
        h for h in cast(list[str], scope["selected_transactions"]) if h != dropped_hash
    ]
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(replay).encode())

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "source_unavailable"


def test_aggregate_duplicate_transaction_is_failed_reconciliation() -> None:
    fixture_id = "FX-FLOW-MULTI-001"
    replay = _replay(fixture_id)
    transactions = cast(list[dict[str, object]], replay["transactions"])
    # duplicate the same transfer under a second label -> same tx counted twice
    clone = json.loads(json.dumps(transactions[0]))
    clone["label"] = "merge_e"
    transactions.append(clone)

    result = analyze_flow_path_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_aggregate_unrequested_origin_is_failed_reconciliation() -> None:
    fixture_id = "FX-FLOW-MULTI-001"
    request_document = _request_document(fixture_id)
    inputs = cast(dict[str, object], request_document["inputs"])
    inputs["origin_nodes"] = cast(list[str], inputs["origin_nodes"])[:3]
    # keep the replay's fourth transfer so an unrequested origin reaches the exit
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


@pytest.mark.parametrize("fixture_id", CASES)
def test_traversal_budget_upper_bound_is_enforced(fixture_id: str) -> None:
    """A one-unit budget must bound both status and the returned projection."""
    request_document = _request_document(fixture_id)
    budgets = cast(dict[str, int], cast(dict[str, object], request_document["inputs"])["budgets"])
    budgets["max_nodes"] = 1
    budgets["max_edges"] = 1
    budgets["max_hops"] = 1
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "evidence_incomplete"
    assert result.root.errors[0].stage == "budget_traversal"
    value = result.root.results[0].value
    if fixture_id == "FX-FLOW-PATH-001":
        graph = cast(dict[str, object], value["graph"])
        assert cast(int, graph["node_count"]) <= budgets["max_nodes"]
        assert cast(int, graph["edge_count"]) <= budgets["max_edges"]
        candidates = cast(list[dict[str, object]], value["path_candidates"])
        assert cast(int, candidates[0]["hop_count"]) <= budgets["max_hops"]
    elif fixture_id == "FX-FLOW-REMERGE-001":
        branches = cast(list[dict[str, object]], value["branches"])
        assert 2 + len(branches) <= budgets["max_nodes"] or not branches
        assert 2 * len(branches) <= budgets["max_edges"]
        assert not branches  # each atomic branch requires two hops
    else:
        contributions = cast(list[dict[str, object]], value["contributions"])
        assert len(contributions) + 1 <= budgets["max_nodes"] or not contributions
        assert len(contributions) <= budgets["max_edges"]


def test_remerge_block_range_not_covering_replay_is_rejected() -> None:
    fixture_id = "FX-FLOW-REMERGE-001"
    request_document = _request_document(fixture_id)
    scope = cast(dict[str, object], cast(dict[str, object], request_document["inputs"])["scope"])
    scope["block_range"] = {"from": 1, "to": 1}
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_trace_path_incomplete_selected_scope_is_not_complete() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    replay = _replay(fixture_id)
    cast(dict[str, object], replay["scope"])["selected_transactions_complete"] = False

    result = analyze_flow_path_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "source_unavailable"


@pytest.mark.parametrize("fixture_id", ("FX-FLOW-REMERGE-001", "FX-FLOW-MULTI-001"))
def test_duplicate_transaction_hash_is_failed_reconciliation(fixture_id: str) -> None:
    replay = _replay(fixture_id)
    transactions = cast(list[dict[str, object]], replay["transactions"])
    clone = json.loads(json.dumps(transactions[0]))
    clone["label"] = "duplicate_label"
    transactions.append(clone)

    result = analyze_flow_path_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_duplicate_internal_edge_is_failed_as_edge_dedup() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    replay = _replay(fixture_id)
    internal_edges = cast(list[dict[str, object]], replay["internal_edges"])
    internal_edges.append(json.loads(json.dumps(internal_edges[0])))

    result = analyze_flow_path_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"
    assert result.root.errors[0].stage == "edge_dedup"


def test_restricted_source_policy_blocks_before_decode() -> None:
    fixture_id = "FX-FLOW-PATH-001"
    request_document = _request_document(fixture_id)
    cast(dict[str, object], request_document["source_policy"])["offline_mode"] = False
    request = validate_analysis_request(request_document).root
    assert isinstance(request, FlowPathAnalysisRequest)

    result = analyze_flow_path_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"
