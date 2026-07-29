from pathlib import Path

import pytest

from scan_tool.application.task_013_negative_oracles import (
    NegativeOracleCase,
    NegativeOracleManifest,
    evaluate_case,
    load_negative_oracle_manifest,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures/TASK-013-NEGATIVE-ORACLES.json"


def test_repository_manifest_verifies_all_required_oracles() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)

    verified = verify_manifest(manifest)

    assert len(verified) == 16
    assert len(verified) == len(set(verified))
    assert {case.category for case in manifest.cases} == {
        "erc721",
        "erc1155",
        "eip1967",
    }


@pytest.mark.parametrize(
    ("oracle_id", "expected"),
    [
        (
            "OR-NFT721-DIFFERENT-CONTRACT",
            {"outcome": "complete", "classification": "excluded"},
        ),
        (
            "OR-NFT1155-BATCH-LENGTH",
            {"outcome": "failed", "classification": "batch_length_mismatch"},
        ),
        (
            "OR-PROXY-HISTORICAL-STATE-MISSING",
            {"outcome": "partial", "classification": "state_unavailable"},
        ),
        (
            "OR-PROXY-EVENT-STATE-CONFLICT",
            {"outcome": "failed", "classification": "event_state_conflict"},
        ),
        (
            "OR-PROXY-IMPLEMENTATION-BEACON-CONFLICT",
            {"outcome": "failed", "classification": "proxy_route_conflict"},
        ),
    ],
)
def test_representative_oracle_outcomes(oracle_id: str, expected: dict[str, str]) -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    case = next(item for item in manifest.cases if item.oracle_id == oracle_id)

    assert evaluate_case(case) == expected


def test_manifest_requires_the_exact_oracle_set() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)

    with pytest.raises(ValueError, match="oracle set drifted"):
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
        expected={"outcome": "complete", "classification": "erc721"},
    )
    drifted = manifest.model_copy(update={"cases": (changed, *manifest.cases[1:])})

    with pytest.raises(ValueError, match="OR-NFT721-ERC20-SIGNATURE mismatch"):
        verify_manifest(drifted)
