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
REQUEST_FILES = {
    "FX-EVM-NFT-721-001": ("analysis-request.json",),
    "FX-EVM-NFT-1155-001": (
        "analysis-request.json",
        "analysis-request-batch.json",
    ),
    "FX-EVM-PROXY-001": ("analysis-request.json",),
}


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
        raw_replay = (package / "raw-replay.json").read_bytes()
        values: list[dict[str, object]] = []
        for request_file in REQUEST_FILES[fixture_id]:
            request = validate_analysis_request(
                json.loads((package / request_file).read_text())
            ).root
            if not isinstance(request, EvmSpecialAnalysisRequest):
                raise ValueError(f"{fixture_id} {request_file} is not evm_special")

            first = analyze_evm_special_replay(request, raw_replay)
            second = analyze_evm_special_replay(request, raw_replay)
            if first.to_contract_dict() != second.to_contract_dict():
                raise ValueError(f"{fixture_id} {request_file} analyzer is not deterministic")
            if first.root.status != "complete":
                raise ValueError(f"{fixture_id} {request_file} did not reach complete status")
            values.append(first.root.results[0].value)

        if fixture_id == "FX-EVM-NFT-1155-001":
            single_value, batch_value = values
            if single_value.get("standard") != "erc1155":
                raise ValueError("ERC-1155 single request returned the wrong standard")
            if batch_value.get("standard") != "erc1155":
                raise ValueError("ERC-1155 batch request returned the wrong standard")
            analyzer_value = {
                "standard": "erc1155",
                "single_case": single_value["single_case"],
                "batch_case": batch_value["batch_case"],
            }
        else:
            analyzer_value = values[0]

        analyzer_hash = _canonical_sha256(analyzer_value)
        evidence = json.loads((package / "evidence.json").read_text())
        pinned_hash = evidence["verification_provenance"]["calculated_fact_sha256"]
        if analyzer_hash != pinned_hash:
            raise ValueError(
                f"{fixture_id} analyzer result hash {analyzer_hash} does not match "
                f"the independent verifier's pinned hash {pinned_hash}"
            )

    print(
        f"PASS TASK-013 analyzer independent verification: {len(FIXTURE_IDS)} fixtures, "
        "4 subject-scoped requests, canonical result hash matches the independent "
        "verifier, 2 deterministic runs"
    )


if __name__ == "__main__":
    main()
