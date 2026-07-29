"""Cross-check the TASK-014 production analyzer against the pinned fact hash.

The pinned ``calculated_fact_sha256`` in each fixture's ``evidence.json`` was
produced by ``task_014_independent_verifier.py`` re-deriving graph/ledger facts
from a plain-dict parse of ``raw-replay.json``. This script runs the production
analyzer (``scan_tool.slices.flow_path``, a separate Pydantic-typed
implementation that does not import the verifier) over the same fixture
request/replay pair and asserts its canonical ``results[0].value`` hash matches
the pinned value exactly. Equality proves the two independent code paths agree
without either importing the other.
"""

import hashlib
import json
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import FlowPathAnalysisRequest
from scan_tool.slices.flow_path import analyze_flow_path_replay

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
FIXTURE_IDS = (
    "FX-FLOW-PATH-001",
    "FX-FLOW-REMERGE-001",
    "FX-FLOW-MULTI-001",
)


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    for fixture_id in FIXTURE_IDS:
        package = FIXTURES / fixture_id
        raw_replay = (package / "raw-replay.json").read_bytes()
        request = validate_analysis_request(
            json.loads((package / "analysis-request.json").read_text())
        ).root
        if not isinstance(request, FlowPathAnalysisRequest):
            raise ValueError(f"{fixture_id} analysis-request is not flow_path")

        first = analyze_flow_path_replay(request, raw_replay)
        second = analyze_flow_path_replay(request, raw_replay)
        if first.to_contract_dict() != second.to_contract_dict():
            raise RuntimeError(f"{fixture_id} analyzer is not deterministic")
        if first.root.status != "complete":
            raise RuntimeError(f"{fixture_id} analyzer did not reach complete")

        pinned = json.loads((package / "evidence.json").read_text())["verification_provenance"][
            "calculated_fact_sha256"
        ]
        calculated = _canonical_sha256(first.root.results[0].value)
        if calculated != pinned:
            raise RuntimeError(
                f"{fixture_id} analyzer fact hash {calculated} differs from pinned {pinned}"
            )

    print(
        "PASS TASK-014 analyzer independent verification: "
        f"{len(FIXTURE_IDS)} fixtures, canonical result hash matches the independent "
        "verifier, 2 deterministic runs"
    )


if __name__ == "__main__":
    main()
