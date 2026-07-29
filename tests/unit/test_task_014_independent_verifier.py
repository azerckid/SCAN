import copy
from pathlib import Path

import pytest

from scan_tool.application.task_014_independent_verifier import (
    load_json,
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"


def test_repository_recalculates_all_three_fixtures_deterministically() -> None:
    first = verify_repository(FIXTURE_ROOT)
    assert len(first) == 3
    assert first == verify_repository(FIXTURE_ROOT)


def test_transaction_receipt_mismatch_is_rejected() -> None:
    package = FIXTURE_ROOT / "FX-FLOW-MULTI-001"
    raw = load_json(package / "raw-replay.json")
    raw["transactions"][0]["receipt"]["blockHash"] = "0xwrong"
    with pytest.raises(ValueError, match="blockHash differs"):
        verify_fixture(
            raw,
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_evidence_value_mismatch_is_rejected() -> None:
    package = FIXTURE_ROOT / "FX-FLOW-PATH-001"
    evidence = copy.deepcopy(load_json(package / "evidence.json"))
    evidence["call_evidence"][0]["amount_raw"] = "1"
    with pytest.raises(ValueError, match="value differs"):
        verify_fixture(
            load_json(package / "raw-replay.json"),
            load_json(package / "expected.json"),
            evidence,
        )
