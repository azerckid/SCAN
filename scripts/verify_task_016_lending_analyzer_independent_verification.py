#!/usr/bin/env python3
import ast
import hashlib
import json
from pathlib import Path

from scan_tool.application.task_016_lending_independent_verifier import verify_repository
from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import DefiLendingAnalysisRequest
from scan_tool.slices.defi_lending import analyze_defi_lending_replay

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-LEND-001"
PINNED = "6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c"

slice_source = (ROOT / "src/scan_tool/slices/defi_lending.py").read_text(encoding="utf-8")
verifier_source = (
    ROOT / "src/scan_tool/application/task_016_lending_independent_verifier.py"
).read_text(encoding="utf-8")
tree = ast.parse(verifier_source)
for node in ast.walk(tree):
    if (
        isinstance(node, ast.ImportFrom)
        and node.module
        and (
            node.module.startswith("scan_tool.slices.defi_lending")
            or node.module.startswith("scan_tool.domain.defi_lending")
        )
    ):
        raise RuntimeError("independent verifier imports product lending modules")

request = validate_analysis_request(
    json.loads((PACKAGE / "analysis-request.json").read_text())
).root
assert isinstance(request, DefiLendingAnalysisRequest)
replay = (PACKAGE / "raw-replay.json").read_bytes()
first = analyze_defi_lending_replay(request, replay, package_dir=PACKAGE)
second = analyze_defi_lending_replay(request, replay, package_dir=PACKAGE)
if first.to_contract_dict() != second.to_contract_dict():
    raise RuntimeError("analyzer is not deterministic")
if first.root.status != "complete":
    raise RuntimeError("analyzer did not reach complete")
value = first.root.results[0].value
canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
digest = hashlib.sha256(canonical).hexdigest()
if digest != PINNED:
    raise RuntimeError(f"analyzer hash drift: {digest}")
reports = verify_repository(ROOT / "docs/05_QA_Validation/fixtures")
if reports[0]["calculated_sha256"] != PINNED:
    raise RuntimeError("verifier hash drift")
print("PASS", digest)
