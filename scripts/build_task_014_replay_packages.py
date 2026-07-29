"""Build TASK-014 fixture replay JSON from guarded local provider reports."""

import json
from pathlib import Path

from scan_tool.application.task_014_artifacts import (
    build_fixture_packages,
    load_report,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = REPOSITORY_ROOT / ".scan/live-provider-smoke/task-014-replay"
FIXTURE_ROOT = REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures"


def main() -> None:
    packages = build_fixture_packages(
        load_report(REPORT_ROOT / "provider-evm-primary-latest.json"),
        load_report(REPORT_ROOT / "provider-evm-verify-latest.json"),
    )
    for fixture_id, (raw, provider) in packages.items():
        package = FIXTURE_ROOT / fixture_id
        (package / "raw-replay.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (package / "provider-replay.json").write_text(
            json.dumps(provider, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"PASS TASK-014 replay packages: {len(packages)} fixtures, 2 providers, selected scope only"
    )


if __name__ == "__main__":
    main()
