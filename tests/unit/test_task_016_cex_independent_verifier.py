from pathlib import Path

from scan_tool.application.task_016_cex_independent_verifier import verify_repository
from scan_tool.application.task_016_cex_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-016-cex-negative-oracles-v0.1.json"


def test_cex_independent_verifier_matches_fixture() -> None:
    reports = verify_repository(FIXTURE_ROOT)
    assert len(reports) == 1
    assert reports[0]["fixture_id"] == "FX-SVC-CEX-001"
    assert reports[0]["calculated_sha256"] == (
        "20fc2777b75968e905af493f97bb56a5b24ccefad755f3a12ebc62662be283bf"
    )


def test_cex_negative_oracle_manifest_is_verified() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    verified = verify_manifest(manifest)
    assert len(verified) == 8
