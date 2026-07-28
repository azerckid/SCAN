from pathlib import Path

import pytest

from scan_tool.application.task_012_negative_oracles import (
    NegativeOracleCase,
    NegativeOracleManifest,
    evaluate_case,
    load_negative_oracle_manifest,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures/TASK-012-NEGATIVE-ORACLES.json"


def test_repository_manifest_verifies_all_required_oracles() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)

    verified = verify_manifest(manifest)

    assert len(verified) == 24
    assert len(verified) == len(set(verified))


def test_failed_transaction_is_excluded_before_first_transfer_selection() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    case = next(item for item in manifest.cases if item.oracle_id == "OR-TOKEN-FAILED-TX")

    assert evaluate_case(case) == {
        "outcome": "complete",
        "selected_id": "valid-next",
    }


def test_trace_unavailable_is_partial() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    case = next(item for item in manifest.cases if item.oracle_id == "OR-NATIVE-TRACE-UNAVAILABLE")

    assert evaluate_case(case) == {"outcome": "partial", "amount_wei": "0"}


def test_timestamp_between_blocks_selects_the_preceding_block() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    case = next(item for item in manifest.cases if item.oracle_id == "OR-TIME-BETWEEN")

    assert evaluate_case(case) == {"outcome": "complete", "block_number": 101}


def test_manifest_requires_the_complete_oracle_set() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)

    with pytest.raises(ValueError, match="required negative oracles are missing"):
        NegativeOracleManifest(
            schema_version="0.1",
            status="verified",
            execution_mode="synthetic_offline",
            cases=manifest.cases[:-1],
        )


def test_verifier_rejects_an_expected_result_drift() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = manifest.cases[0]
    changed = NegativeOracleCase(
        oracle_id=first.oracle_id,
        fixture_id=first.fixture_id,
        category=first.category,
        facts=first.facts,
        expected={"outcome": "failed", "classification": "address"},
    )
    drifted = manifest.model_copy(update={"cases": (changed, *manifest.cases[1:])})

    with pytest.raises(ValueError, match="OR-BASIC-OBJECT-MALFORMED mismatch"):
        verify_manifest(drifted)
