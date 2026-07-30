"""Cross-check the TASK-016 CEX cluster analyzer against its pinned fact hash."""

import ast
import hashlib
import json
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import CexClusterAnalysisRequest
from scan_tool.slices.cex_cluster import analyze_cex_cluster_replay

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-CEX-001"
PRODUCTION_FILES = (
    ROOT / "src/scan_tool/domain/cex_cluster.py",
    ROOT / "src/scan_tool/slices/cex_cluster.py",
)
FORBIDDEN_MODULES = {
    "scan_tool.application.task_016_cex_independent_verifier",
}


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _assert_independent_imports() -> None:
    for path in PRODUCTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        forbidden = imported & FORBIDDEN_MODULES
        if forbidden:
            raise RuntimeError(f"{path.name} imports forbidden verifier modules: {forbidden}")


def main() -> None:
    _assert_independent_imports()
    request = validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    ).root
    if not isinstance(request, CexClusterAnalysisRequest):
        raise ValueError("FX-SVC-CEX-001 analysis-request is not cex_cluster")

    raw_replay = (PACKAGE / "raw-replay.json").read_bytes()
    first = analyze_cex_cluster_replay(request, raw_replay, package_dir=PACKAGE)
    second = analyze_cex_cluster_replay(request, raw_replay, package_dir=PACKAGE)
    if first.to_contract_dict() != second.to_contract_dict():
        raise RuntimeError("FX-SVC-CEX-001 analyzer is not deterministic")
    if first.root.status != "complete":
        raise RuntimeError("FX-SVC-CEX-001 analyzer did not reach complete")

    pinned = json.loads((PACKAGE / "evidence.json").read_text(encoding="utf-8"))[
        "verification_provenance"
    ]["calculated_fact_sha256"]
    calculated = _canonical_sha256(first.root.results[0].value)
    if calculated != pinned:
        raise RuntimeError(f"cex analyzer fact hash {calculated} differs from pinned {pinned}")

    print(
        "PASS TASK-016 CEX analyzer independent verification: "
        f"canonical result hash {calculated}, 2 deterministic runs, forbidden imports absent"
    )


if __name__ == "__main__":
    main()
