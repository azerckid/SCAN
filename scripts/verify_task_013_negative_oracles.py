"""Verify the bounded offline negative-oracle pack for TASK-013."""

from pathlib import Path

from scan_tool.application.task_013_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures/TASK-013-NEGATIVE-ORACLES.json"


def main() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = verify_manifest(manifest)
    second = verify_manifest(manifest)
    if first != second:
        raise RuntimeError("TASK-013 negative oracle replay is not deterministic")
    print(f"PASS {len(first)} TASK-013 negative oracles twice (offline deterministic)")


if __name__ == "__main__":
    main()
