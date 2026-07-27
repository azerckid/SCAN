"""TASK-006 DEX raw replay decoding and reconciliation tests."""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import DexAnalysisRequest
from scan_tool.slices.dex import analyze_dex_replay

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/05_QA_Validation/examples/analysis"
RAW_REPLAY = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/raw-replay.json"


def request_model() -> DexAnalysisRequest:
    request = validate_analysis_request(
        json.loads((EXAMPLES / "dex-request.json").read_text())
    ).root
    assert isinstance(request, DexAnalysisRequest)
    return request


def replay_document() -> dict[str, object]:
    return json.loads(RAW_REPLAY.read_text())


def analyze(document: dict[str, object]):
    return analyze_dex_replay(
        request_model(),
        json.dumps(document).encode(),
        checkpoint_id="CP-DEX-TEST",
    )


def test_confirmed_dex_replay_exactly_matches_three_results_and_raw_logs() -> None:
    result = analyze(replay_document()).root

    assert result.status == "complete"
    values = {item.result_type: item.value for item in result.results}
    assert values["asset_in"]["amount_raw"] == "25000000000"
    assert values["pool_output"]["symbol"] == "WETH"
    assert values["pool_output"]["amount_raw"] == "14449515027026387018"
    assert values["user_net_output"]["symbol"] == "ETH"
    assert values["user_net_output"]["amount_raw"] == "14449515027026387018"
    assert {
        item.locator.log_index for item in result.evidence if item.evidence_type == "event"
    } == {
        275,
        276,
        278,
        279,
    }
    assert {item.source_id for item in result.sources} == {
        "DS-EVM-RPC-PUBLIC",
        "DS-EXPLORER-EVM",
        "DS-DEX-META",
    }
    assert result.errors == []


def test_missing_internal_native_call_returns_partial_with_pool_output() -> None:
    document = replay_document()
    document["internal_calls"] = []

    result = analyze(document).root

    assert result.status == "partial"
    assert [item.result_type for item in result.results] == ["asset_in", "pool_output"]
    assert result.errors[0].code == "trace_unavailable"
    assert result.errors[0].details == {"missing_requirement_ids": ["REQ-DEX-USER-NET-OUTPUT"]}
    assert all(item.result_type != "user_net_output" for item in result.results)


def test_swap_amount_changed_by_one_raw_fails_reconciliation() -> None:
    document = replay_document()
    swap = document["receipt"]["logs"][2]  # type: ignore[index]
    data = swap["data"]  # type: ignore[index]
    swap["data"] = f"{data[:-1]}b"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert result.results == []
    assert result.errors[0].code == "reconciliation_failed"
    assert "pool_output_transfer_vs_swap" in result.errors[0].details["mismatches"]


def test_pool_weth_without_native_call_cannot_be_user_final_output() -> None:
    document = replay_document()
    document["internal_calls"] = []

    result = analyze(document).root

    assert result.status != "complete"
    pool = next(item for item in result.results if item.result_type == "pool_output")
    assert pool.value["symbol"] == "WETH"
    assert not any(item.result_type == "user_net_output" for item in result.results)


def test_disallowed_scoring_source_is_rule_restricted() -> None:
    request = request_model()
    policy = request.source_policy.model_copy(
        update={
            "allowed_source_ids": ["DS-EVM-RPC-PUBLIC", "DS-DEX-META"],
            "source_order": ["DS-EVM-RPC-PUBLIC", "DS-DEX-META"],
        }
    )
    request = request.model_copy(update={"source_policy": policy})

    result = analyze_dex_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.status == "failed"
    assert result.errors[0].code == "rule_restricted"
    assert result.evidence == []


def test_malformed_replay_fails_without_echoing_unknown_fields() -> None:
    document = copy.deepcopy(replay_document())
    document["secret"] = "SCAN_CANARY_DEX_SECRET"

    result = analyze(document).root

    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"
    assert "SCAN_CANARY_DEX_SECRET" not in result.errors[0].message


def test_replay_endpoint_host_rejects_credentials_and_url_components() -> None:
    document = replay_document()
    document["sources"]["receipt"]["endpoint_host"] = (  # type: ignore[index]
        "https://api-key@ethereum.publicnode.com/rpc?secret=1"
    )

    result = analyze(document).root

    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"
    assert "api-key" not in result.errors[0].message


def test_run_never_finishes_before_a_later_request_timestamp() -> None:
    request = request_model().model_copy(
        update={"requested_at": datetime(2026, 8, 2, 2, 0, tzinfo=UTC)}
    )

    result = analyze_dex_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.run.finished_at >= result.run.started_at
