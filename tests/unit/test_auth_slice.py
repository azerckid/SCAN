"""TASK-007 AUTH raw replay decoding and reconciliation tests."""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import AuthAnalysisRequest
from scan_tool.slices.auth import analyze_auth_replay

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/05_QA_Validation/examples/analysis"
RAW_REPLAY = ROOT / "docs/05_QA_Validation/fixtures/FX-EVM-AUTH-001/raw-replay.json"
UINT256_MAX = 2**256 - 1


def request_model() -> AuthAnalysisRequest:
    request = validate_analysis_request(
        json.loads((EXAMPLES / "auth-request.json").read_text())
    ).root
    assert isinstance(request, AuthAnalysisRequest)
    return request


def replay_document() -> dict[str, object]:
    return json.loads(RAW_REPLAY.read_text())


def analyze(document: dict[str, object]):
    return analyze_auth_replay(
        request_model(),
        json.dumps(document).encode(),
        checkpoint_id="CP-AUTH-TEST",
    )


def test_confirmed_auth_replay_matches_approval_allowance_consumption_and_scope() -> None:
    result = analyze(replay_document()).root

    assert result.status == "complete"
    assert [
        item.decoded["nonce"]
        for item in result.evidence
        if item.evidence_id.startswith("EV-AUTH-EXCLUDED-")
    ] == [327, 328, 329]
    trace_evidence = next(
        item for item in result.evidence if item.evidence_id == "EV-AUTH-TRANSFER-FROM"
    )
    assert trace_evidence.locator.trace_address == [0, 0, 2, 0]
    values = {item.result_type: item.value for item in result.results}
    assert values["approval"]["amount_raw"] == str(UINT256_MAX)
    assert values["allowance_lifecycle"] == {
        "before_approval_raw": "0",
        "after_approval_raw": str(UINT256_MAX),
        "before_consumption_raw": str(UINT256_MAX),
        "after_consumption_raw": str(UINT256_MAX - 4_500_000),
        "consumed_delta_raw": "4500000",
    }
    assert values["authorization_consumption"]["amount_raw"] == "4500000"
    assert values["authorization_consumption"]["excluded_failed_transaction_count"] == 3
    assert values["theft_or_phishing_attribution"]["theft_or_phishing_claim"] is False
    assert (
        next(
            item for item in result.results if item.result_type == "theft_or_phishing_attribution"
        ).classification
        == "not_assessed"
    )
    assert {item.evidence_type for item in result.evidence} == {
        "event",
        "call",
        "state",
        "context",
    }
    assert result.errors == []


def test_missing_allowance_snapshot_is_partial_with_approval_preserved() -> None:
    document = replay_document()
    document["allowance_query"]["snapshots"] = document["allowance_query"]["snapshots"][:2]  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "partial"
    assert [item.result_type for item in result.results] == [
        "approval",
        "theft_or_phishing_attribution",
    ]
    assert result.errors[0].code == "archive_required"
    assert result.errors[0].details == {
        "missing_snapshot_labels": ["before_consumption", "after_consumption"]
    }


def test_missing_transfer_from_trace_is_partial_without_consumption_claim() -> None:
    document = replay_document()
    document["consumption"]["transfer_from_trace"] = None  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "partial"
    assert [item.result_type for item in result.results] == [
        "approval",
        "allowance_lifecycle",
        "theft_or_phishing_attribution",
    ]
    assert result.errors[0].code == "trace_unavailable"


def test_transfer_from_amount_changed_by_one_raw_fails_reconciliation() -> None:
    document = replay_document()
    trace = document["consumption"]["transfer_from_trace"]  # type: ignore[index]
    trace["input"] = f"{trace['input'][:-1]}1"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert result.results == []
    assert result.errors[0].code == "reconciliation_failed"
    assert "transfer_from_vs_event" in result.errors[0].details["mismatches"]
    assert result.evidence


def test_successful_intermediate_receipt_cannot_be_excluded() -> None:
    document = replay_document()
    document["excluded_receipts"][0]["status"] = "0x1"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert "excluded_transaction_status" in result.errors[0].details["mismatches"]


def test_excluded_transaction_nonce_set_must_be_exact() -> None:
    document = replay_document()
    document["excluded_receipts"][0]["nonce"] = "0x14b"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert "excluded_transaction_nonce_set" in result.errors[0].details["mismatches"]


def test_disallowed_archive_source_is_rule_restricted() -> None:
    request = request_model()
    policy = request.source_policy.model_copy(
        update={
            "allowed_source_ids": [
                "DS-EVM-RPC-PUBLIC",
                "DS-EXPLORER-EVM",
                "DS-DEX-META",
            ],
            "source_order": [
                "DS-EVM-RPC-PUBLIC",
                "DS-EXPLORER-EVM",
                "DS-DEX-META",
            ],
        }
    )
    request = request.model_copy(update={"source_policy": policy})

    result = analyze_auth_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.status == "failed"
    assert result.errors[0].code == "rule_restricted"
    assert result.evidence == []


def test_malformed_auth_replay_does_not_echo_unknown_secret() -> None:
    document = copy.deepcopy(replay_document())
    document["secret"] = "SCAN_CANARY_AUTH_SECRET"

    result = analyze(document).root

    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"
    assert "SCAN_CANARY_AUTH_SECRET" not in result.errors[0].message


def test_run_never_finishes_before_later_request_timestamp() -> None:
    request = request_model().model_copy(
        update={"requested_at": datetime(2026, 8, 2, 2, 0, tzinfo=UTC)}
    )

    result = analyze_auth_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.run.finished_at >= result.run.started_at
