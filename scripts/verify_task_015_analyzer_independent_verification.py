"""Cross-check the TASK-015 production analyzer against the pinned fact hash.

The pinned ``calculated_fact_sha256`` in each verifying fixture's
``evidence.json`` was produced by ``task_015_independent_verifier.py``
re-deriving facts from the raw package files. This script runs the production
analyzer (``scan_tool.slices.intel_context``, a separate Pydantic-typed
implementation that does not import the verifier) over the fixture
request/source-replay pair and asserts its canonical ``results[0].value`` hash
matches the pinned value exactly. The common-funder fixture stays candidate and
is asserted to remain partial.
"""

import hashlib
import json
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import IntelContextAnalysisRequest
from scan_tool.slices.intel_context import analyze_intel_context_replay

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
VERIFYING = (
    "FX-OSINT-LABEL-CONFLICT-001",
    "FX-OSINT-SANCTIONS-HISTORY-001",
    "FX-OSINT-ENS-CONFLICT-001",
    "FX-ACTOR-RELATION-HUB-001",
)
CANDIDATE_PARTIAL = "FX-ACTOR-COMMON-FUNDER-001"


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _run(fixture_id: str):
    package = FIXTURES / fixture_id
    request = validate_analysis_request(
        json.loads((package / "analysis-request.json").read_text())
    ).root
    if not isinstance(request, IntelContextAnalysisRequest):
        raise ValueError(f"{fixture_id} analysis-request is not intel_context")
    replay = (package / "source-replay.json").read_bytes()
    first = analyze_intel_context_replay(request, replay)
    second = analyze_intel_context_replay(request, replay)
    if first.to_contract_dict() != second.to_contract_dict():
        raise RuntimeError(f"{fixture_id} analyzer is not deterministic")
    return package, first


def main() -> None:
    for fixture_id in VERIFYING:
        package, result = _run(fixture_id)
        if result.root.status != "complete":
            raise RuntimeError(f"{fixture_id} analyzer did not reach complete")
        pinned = json.loads((package / "evidence.json").read_text())["verification_provenance"][
            "calculated_fact_sha256"
        ]
        calculated = _canonical_sha256(result.root.results[0].value)
        if calculated != pinned:
            raise RuntimeError(
                f"{fixture_id} analyzer fact hash {calculated} differs from pinned {pinned}"
            )

    _, common_funder = _run(CANDIDATE_PARTIAL)
    if common_funder.root.status != "partial":
        raise RuntimeError("common-funder must stay partial until completeness is proven")

    print(
        "PASS TASK-015 analyzer independent verification: "
        f"{len(VERIFYING)} verifying fixtures canonical hash matches the independent "
        "verifier, common-funder partial, 2 deterministic runs"
    )


if __name__ == "__main__":
    main()
