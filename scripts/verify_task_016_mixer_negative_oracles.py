"""Run the TASK-016 mixer negative oracles twice."""

from pathlib import Path

from scan_tool.application.task_016_mixer_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    REPOSITORY_ROOT / "docs/05_QA_Validation/oracles/task-016-mixer-negative-oracles-v0.1.json"
)


def main() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    first = verify_manifest(manifest)
    second = verify_manifest(manifest)
    if first != second:
        raise RuntimeError("TASK-016 mixer negative oracles are not deterministic")
    print(f"PASS TASK-016 mixer negative oracles: {len(first)} cases, 2 deterministic runs")


if __name__ == "__main__":
    main()
