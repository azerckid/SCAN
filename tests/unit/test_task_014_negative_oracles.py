from pathlib import Path

from scan_tool.application.task_014_negative_oracles import (
    REQUIRED_ORACLE_IDS,
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-014-negative-oracles-v0.1.json"


def test_manifest_has_fixed_deterministic_case_set() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = verify_manifest(manifest)
    assert set(first) == REQUIRED_ORACLE_IDS
    assert first == verify_manifest(manifest)
