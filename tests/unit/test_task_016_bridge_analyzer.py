import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import AnalysisRequest, BridgeTransferAnalysisRequest
from scan_tool.slices.bridge_transfer import analyze_bridge_transfer_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-BRG-001"
PINNED_SHA256 = "d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac"


def _request_document() -> dict[str, object]:
    return json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))


def _request() -> BridgeTransferAnalysisRequest:
    request = validate_analysis_request(_request_document()).root
    assert isinstance(request, BridgeTransferAnalysisRequest)
    return request


def _hash(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_complete_bridge_transfer_matches_the_pinned_fact_hash() -> None:
    result = analyze_bridge_transfer_replay(
        _request(),
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "complete"
    assert _hash(result.root.results[0].value) == PINNED_SHA256
    assert result.root.results[0].value["attribution"] == {
        "recipient_ownership": "not_assessed",
        "criminality": "not_assessed",
    }


def test_bridge_transfer_requires_offline_source_binding() -> None:
    document = _request_document()
    document["source_policy"]["offline_mode"] = False
    request = validate_analysis_request(document).root
    assert isinstance(request, BridgeTransferAnalysisRequest)

    result = analyze_bridge_transfer_replay(
        request,
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"


def test_bridge_query_is_rejected_for_another_analysis_type() -> None:
    document = _request_document()
    document["analysis_type"] = "flow_path"

    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(document)


def test_bridge_transfer_is_deterministic_across_two_runs() -> None:
    raw_replay = (PACKAGE / "raw-replay.json").read_bytes()
    first = analyze_bridge_transfer_replay(_request(), raw_replay, package_dir=PACKAGE)
    second = analyze_bridge_transfer_replay(_request(), raw_replay, package_dir=PACKAGE)

    assert first.to_contract_dict() == second.to_contract_dict()
