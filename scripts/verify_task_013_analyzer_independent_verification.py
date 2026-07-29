"""Cross-check the TASK-013 production analyzer against the pinned fact hash.

The pinned ``calculated_fact_sha256`` in each fixture's ``evidence.json`` was
produced by ``task_013_independent_verifier.py`` re-deriving raw facts from a
plain-dict parse of ``raw-replay.json``. This script runs the production
analyzer (``scan_tool.slices.evm_special``, a separate Pydantic-typed
implementation that does not import the verifier) over the same fixture
request/replay pair and asserts its canonical result hash matches the pinned
value exactly. Equality proves the two independent code paths agree without
either importing the other.
"""

import hashlib
import json
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import EvmSpecialAnalysisRequest
from scan_tool.slices.evm_special import analyze_evm_special_replay

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
FIXTURE_IDS = (
    "FX-EVM-NFT-721-001",
    "FX-EVM-NFT-1155-001",
    "FX-EVM-PROXY-001",
)


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    for fixture_id in FIXTURE_IDS:
        package = FIXTURES / fixture_id
        request = validate_analysis_request(
            json.loads((package / "analysis-request.json").read_text())
        ).root
        if not isinstance(request, EvmSpecialAnalysisRequest):
            raise ValueError(f"{fixture_id} analysis-request.json is not evm_special")
        raw_replay = (package / "raw-replay.json").read_bytes()

        first = analyze_evm_special_replay(request, raw_replay)
        second = analyze_evm_special_replay(request, raw_replay)
        if first.to_contract_dict() != second.to_contract_dict():
            raise ValueError(f"{fixture_id} analyzer is not deterministic")
        if first.root.status != "complete":
            raise ValueError(f"{fixture_id} analyzer did not reach complete status")

        analyzer_hash = _canonical_sha256(first.root.results[0].value)
        evidence = json.loads((package / "evidence.json").read_text())
        pinned_hash = evidence["verification_provenance"]["calculated_fact_sha256"]
        if analyzer_hash != pinned_hash:
            raise ValueError(
                f"{fixture_id} analyzer result hash {analyzer_hash} does not match "
                f"the independent verifier's pinned hash {pinned_hash}"
            )

    print(
        f"PASS TASK-013 analyzer independent verification: {len(FIXTURE_IDS)} fixtures, "
        "canonical result hash matches the independent verifier, 2 deterministic runs"
    )


if __name__ == "__main__":
    main()
