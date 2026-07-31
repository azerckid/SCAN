#!/usr/bin/env python3
from pathlib import Path

from scan_tool.application.task_016_lending_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "docs/05_QA_Validation/oracles/task-016-lending-negative-oracles-v0.1.json"
for _ in range(2):
    verified = verify_manifest(load_negative_oracle_manifest(path))
    print("pass", len(verified), ",".join(verified))
