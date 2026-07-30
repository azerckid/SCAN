import copy
from pathlib import Path

import pytest

from scan_tool.application.task_016_bridge_independent_verifier import (
    load_json,
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"


def test_repository_recalculates_the_bridge_fixture_deterministically() -> None:
    first = verify_repository(FIXTURE_ROOT)
    assert len(first) == 1
    assert first == verify_repository(FIXTURE_ROOT)


def test_destination_amount_mismatch_is_rejected() -> None:
    package = FIXTURE_ROOT / "FX-SVC-BRG-001"
    raw = copy.deepcopy(load_json(package / "raw-replay.json"))
    for observation in raw["raw_observations"]:
        if observation["chain"] == "ethereum":
            words = observation["log"]["data"][2:]
            replaced = f"{0:064x}"
            observation["log"]["data"] = f"0x{words[: 3 * 64]}{replaced}{words[4 * 64 :]}"
    with pytest.raises(ValueError, match="bridge event mismatch"):
        verify_fixture(
            raw,
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_evidence_value_mismatch_is_rejected() -> None:
    package = FIXTURE_ROOT / "FX-SVC-BRG-001"
    evidence = copy.deepcopy(load_json(package / "evidence.json"))
    evidence["event_evidence"][0]["deposit_id"] = 1
    with pytest.raises(ValueError, match="value differs"):
        verify_fixture(
            load_json(package / "raw-replay.json"),
            load_json(package / "expected.json"),
            evidence,
        )
