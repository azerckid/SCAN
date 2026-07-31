#!/usr/bin/env python3
from pathlib import Path

from scan_tool.application.task_016_lending_independent_verifier import verify_repository

ROOT = Path(__file__).resolve().parents[1]
reports = verify_repository(ROOT / "docs/05_QA_Validation/fixtures")
for report in reports:
    print(report["fixture_id"], report["status"], report["calculated_sha256"])
if any(item["status"] != "pass" for item in reports):
    raise SystemExit(1)
