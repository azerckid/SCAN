from collections import Counter
from pathlib import Path

import pytest

from scan_tool.application.task_015_negative_oracles import (
    REQUIRED_ORACLE_IDS,
    NegativeOracleCase,
    evaluate_case,
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-015-negative-oracles-v0.1.json"


def test_manifest_has_fixed_deterministic_case_set() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = verify_manifest(manifest)
    assert set(first) == REQUIRED_ORACLE_IDS
    assert first == verify_manifest(manifest)


def test_manifest_balances_five_intelligence_categories() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    assert Counter(case.category for case in manifest.cases) == {
        "label_conflict": 6,
        "sanctions_history": 6,
        "ens_resolution": 6,
        "common_funder": 6,
        "relation_hub": 6,
    }


def test_manifest_preserves_complete_partial_failed_boundaries() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    assert Counter(case.expected["outcome"] for case in manifest.cases) == {
        "failed": 18,
        "partial": 7,
        "complete": 5,
    }


def test_non_boolean_fact_is_rejected() -> None:
    case = NegativeOracleCase(
        oracle_id="OR-INTEL-ENS-FORWARD-MISSING",
        fixture_id="FX-OSINT-ENS-CONFLICT-001",
        category="ens_resolution",
        facts={
            "subject_matches": True,
            "latest_substituted": False,
            "ownership_promoted": False,
            "forward_available": "false",
            "reverse_available": True,
            "forward_reverse_match": True,
        },
        expected={"outcome": "partial", "classification": "source_unavailable"},
    )
    with pytest.raises(ValueError, match="forward_available must be boolean"):
        evaluate_case(case)
