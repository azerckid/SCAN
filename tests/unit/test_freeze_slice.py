"""TASK-008 FREEZE raw replay decoding and reconciliation tests."""

import json
from datetime import UTC, datetime
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import FreezeAnalysisRequest, RuleStatus
from scan_tool.slices.freeze import analyze_freeze_replay

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/05_QA_Validation/examples/analysis"
RAW_REPLAY = ROOT / "docs/05_QA_Validation/fixtures/FX-EVM-FREEZE-001/raw-replay.json"


def request_model() -> FreezeAnalysisRequest:
    request = validate_analysis_request(
        json.loads((EXAMPLES / "freeze-request.json").read_text())
    ).root
    assert isinstance(request, FreezeAnalysisRequest)
    return request


def replay_document() -> dict[str, object]:
    return json.loads(RAW_REPLAY.read_text())


def analyze(document: dict[str, object]):
    return analyze_freeze_replay(
        request_model(),
        json.dumps(document).encode(),
        checkpoint_id="CP-FREEZE-TEST",
    )


def test_confirmed_freeze_replay_matches_transitions_context_and_scope() -> None:
    result = analyze(replay_document()).root

    assert result.status == "complete"
    values = {item.result_type: item.value for item in result.results}
    assert values["blacklist_transition"] == {
        "target_address": "0xd96f2b1c14db8458374d9aca76e26c3d18364307",
        "before": False,
        "after": True,
        "before_block": 15302548,
        "after_block": 15302549,
    }
    assert values["unblacklist_transition"] == {
        "target_address": "0xd96f2b1c14db8458374d9aca76e26c3d18364307",
        "before": True,
        "after": False,
        "before_block": 22099071,
        "after_block": 22099072,
    }
    assert values["official_context_scope"] == {
        "circle_address_specific": False,
        "ofac_address_specific": True,
        "current_sanctions_status": "not_assessed",
        "criminal_intent": "not_assessed",
        "global_pause": {"applicable": False},
    }
    assert {item.evidence_type for item in result.evidence} == {
        "event",
        "call",
        "state",
        "context",
    }
    assert len(result.evidence) == 15
    assert result.errors == []


def test_missing_unblacklist_transition_is_partial_with_blacklist_preserved() -> None:
    document = replay_document()
    document["unblacklist"] = None
    document["state_query"]["snapshots"] = document["state_query"]["snapshots"][:2]  # type: ignore[index]
    document["explorer_cross_check"] = document["explorer_cross_check"][:1]  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "partial"
    assert [item.result_type for item in result.results] == [
        "blacklist_transition",
        "official_context_scope",
    ]
    assert {item.code for item in result.errors} == {
        "archive_required",
        "evidence_incomplete",
    }


def test_missing_one_state_is_partial_without_affected_transition() -> None:
    document = replay_document()
    del document["state_query"]["snapshots"][3]  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "partial"
    assert [item.result_type for item in result.results] == [
        "blacklist_transition",
        "official_context_scope",
    ]
    assert result.errors[0].code == "archive_required"


def test_blacklist_call_target_change_fails_reconciliation() -> None:
    document = replay_document()
    transaction = document["blacklist"]["transaction"]  # type: ignore[index]
    transaction["input"] = f"{transaction['input'][:-1]}8"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert result.results == []
    assert "blacklist_call_event_identity" in result.errors[0].details["mismatches"]
    assert result.evidence


def test_state_transition_change_fails_reconciliation() -> None:
    document = replay_document()
    document["state_query"]["snapshots"][1]["result"] = f"0x{'0' * 64}"  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert "state_value_after_blacklist" in result.errors[0].details["mismatches"]


def test_circle_context_cannot_be_promoted_to_address_specific() -> None:
    document = replay_document()
    document["official_context"][0]["address_specific"] = True  # type: ignore[index]

    result = analyze(document).root

    assert result.status == "failed"
    assert "circle_address_specific" in result.errors[0].details["mismatches"]


def test_global_pause_cannot_be_promoted_from_address_blacklist() -> None:
    document = replay_document()
    document["global_pause_applicable"] = True

    result = analyze(document).root

    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"


def test_restricted_policy_is_blocked_before_reconciliation() -> None:
    request = request_model()
    policy = request.source_policy.model_copy(update={"rule_status": RuleStatus.RESTRICTED})
    request = request.model_copy(update={"source_policy": policy})

    result = analyze_freeze_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.status == "failed"
    assert result.errors[0].code == "rule_restricted"
    assert result.evidence == []


def test_malformed_replay_does_not_echo_secret() -> None:
    document = replay_document()
    document["secret"] = "SCAN_CANARY_FREEZE_SECRET"

    result = analyze(document).root

    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"
    assert "SCAN_CANARY_FREEZE_SECRET" not in result.errors[0].message


def test_finished_at_never_precedes_request_time() -> None:
    request = request_model().model_copy(update={"requested_at": datetime(2030, 1, 1, tzinfo=UTC)})

    result = analyze_freeze_replay(request, RAW_REPLAY.read_bytes()).root

    assert result.run.finished_at >= result.run.started_at
