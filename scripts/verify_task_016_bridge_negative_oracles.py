"""Run the TASK-016 Bridge offline negative-oracle set twice."""

from pathlib import Path

from scan_tool.application.task_016_bridge_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    REPOSITORY_ROOT / "docs/05_QA_Validation/oracles/task-016-bridge-negative-oracles-v0.1.json"
)


def main() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = verify_manifest(manifest)
    second = verify_manifest(manifest)
    if first != second:
        raise RuntimeError("TASK-016 Bridge negative oracle replay is not deterministic")
    print(f"PASS {len(first)} TASK-016 Bridge negative oracles twice (offline deterministic)")


if __name__ == "__main__":
    main()
