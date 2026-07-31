from pathlib import Path

from scan_tool.application.task_016_lending_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-016-lending-negative-oracles-v0.1.json"


def test_lending_negative_oracles_are_deterministic() -> None:
    first = verify_manifest(load_negative_oracle_manifest(MANIFEST))
    second = verify_manifest(load_negative_oracle_manifest(MANIFEST))
    assert first == second
    assert len(first) == 8
