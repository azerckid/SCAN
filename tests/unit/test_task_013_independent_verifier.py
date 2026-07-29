import copy
from pathlib import Path

import pytest

from scan_tool.application.task_013_independent_verifier import (
    FIXTURE_IDS,
    load_json,
    recalculate_raw_facts,
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
VERIFIER_SOURCE = ROOT / "src/scan_tool/application/task_013_independent_verifier.py"


def _documents(fixture_id: str):
    package = FIXTURES / fixture_id
    return (
        load_json(package / "raw-replay.json"),
        load_json(package / "expected.json"),
        load_json(package / "evidence.json"),
    )


def test_repository_verifier_passes_three_candidates_deterministically() -> None:
    first = verify_repository(FIXTURES)
    second = verify_repository(FIXTURES)

    assert first == second
    assert tuple(item["fixture_id"] for item in first) == FIXTURE_IDS
    assert [len(item["requirement_checks"]) for item in first] == [2, 2, 3]
    assert [item["evidence_value_checks"] for item in first] == [3, 5, 5]
    assert all(item["status"] == "pass" for item in first)


def test_verifier_does_not_import_the_replay_decoder_or_checker() -> None:
    source = VERIFIER_SOURCE.read_text(encoding="utf-8")

    assert "task_013_replay" not in source
    assert "check_task_013_replay_gate" not in source


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_expected_drift_is_rejected_after_raw_calculation(fixture_id: str) -> None:
    raw, expected, evidence = _documents(fixture_id)
    drifted = copy.deepcopy(expected)
    if fixture_id == "FX-EVM-NFT-721-001":
        drifted["movements"][0]["token_id_raw"] = "9111"
    elif fixture_id == "FX-EVM-NFT-1155-001":
        drifted["batch_case"]["amounts_raw"][0] = "2"
    else:
        drifted["change"]["after_implementation"] = "0x" + ("1" * 40)

    with pytest.raises(ValueError, match="independently calculated facts differ"):
        verify_fixture(raw, drifted, evidence)


def test_erc721_raw_topic_drift_is_rejected() -> None:
    raw, expected, evidence = _documents("FX-EVM-NFT-721-001")
    drifted = copy.deepcopy(raw)
    drifted["logs"][2]["topics"][3] = "0x" + ("0" * 63) + "1"

    with pytest.raises(ValueError, match="token IDs differ"):
        verify_fixture(drifted, expected, evidence)


def test_erc1155_truncated_batch_is_rejected() -> None:
    raw, expected, evidence = _documents("FX-EVM-NFT-1155-001")
    drifted = copy.deepcopy(raw)
    drifted["logs"][4]["data"] = drifted["logs"][4]["data"][:-64]

    with pytest.raises(ValueError, match="ERC-1155 batch ABI is malformed"):
        verify_fixture(drifted, expected, evidence)


def test_proxy_event_state_conflict_is_rejected() -> None:
    raw, expected, evidence = _documents("FX-EVM-PROXY-001")
    drifted = copy.deepcopy(raw)
    drifted["logs"][0]["topics"][1] = (
        "0x0000000000000000000000008147b99df7672a21809c9093e6f6ce1a60f119bd"
    )

    with pytest.raises(ValueError, match="event and after-state"):
        verify_fixture(drifted, expected, evidence)


def test_missing_requirement_evidence_is_rejected() -> None:
    raw, expected, evidence = _documents("FX-EVM-NFT-721-001")
    drifted = copy.deepcopy(evidence)
    drifted["event_evidence"] = drifted["event_evidence"][:-1]

    with pytest.raises(ValueError, match="evidence item set differs"):
        verify_fixture(raw, expected, drifted)


def test_evidence_value_drift_is_rejected() -> None:
    raw, expected, evidence = _documents("FX-EVM-NFT-1155-001")
    drifted = copy.deepcopy(evidence)
    drifted["event_evidence"][4]["amounts_raw"][0] = "2"

    with pytest.raises(ValueError, match="EV-NFT1155-BATCH value differs"):
        verify_fixture(raw, expected, drifted)


def test_verification_provenance_is_required() -> None:
    raw, expected, evidence = _documents("FX-EVM-PROXY-001")
    drifted = copy.deepcopy(evidence)
    drifted.pop("verification_provenance")

    with pytest.raises(ValueError, match="verification_provenance must be an object"):
        verify_fixture(raw, expected, drifted)


def test_raw_calculation_does_not_accept_expected_document() -> None:
    _, expected, _ = _documents("FX-EVM-NFT-721-001")

    with pytest.raises(ValueError, match="scope must be an object"):
        recalculate_raw_facts(expected)
