import hashlib
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import AnalysisRequest, CexClusterAnalysisRequest
from scan_tool.slices.cex_cluster import analyze_cex_cluster_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-CEX-001"
PINNED_SHA256 = "20fc2777b75968e905af493f97bb56a5b24ccefad755f3a12ebc62662be283bf"
PRIMARY_PINS = {
    "0": {
        "transaction": "a8ebb52faf82ed5034ca8737d247598599f5db32b2c5d39cb63c49045c044347",
        "receipt": "3e99c46b0d90351891c47e6e35eb0acd1e446bfa066e02e8350e38284b97d6e8",
        "block": "b0f4d76f21f75795ce0a8a332551078a5a84479f51c45a2f14e0c3d4e4b0d753",
    },
    "1": {
        "transaction": "373bafa371bf74a64745f91a2f1d0588d5d7d0ee8fd4ffdf011ffa551b543dfb",
        "receipt": "bac92e7d58814d94da4695960115ff6dc264b7dbcd58a06f3635e9a5bc711562",
        "block": "22f69fda891f4c126a1c5572ee0a9cc9b76a5d4871964e3e2487a340de1efae4",
    },
    "2": {
        "transaction": "73b8545c2e1deb1526102fd6155c53372c874019f7416341f713a26d14c22548",
        "receipt": "9319547af44e979a245e80a7db44f854c7853803b441e907317d2420d9202c97",
        "block": "1bf88349d55512d865752258db411726444a7dea277870c58f32396cf3e50d6a",
    },
}


def _request_document() -> dict[str, object]:
    return json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))


def _request() -> CexClusterAnalysisRequest:
    request = validate_analysis_request(_request_document()).root
    assert isinstance(request, CexClusterAnalysisRequest)
    return request


def _hash(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _artifact_uri(sha256: str) -> str:
    return f"artifact://sha256/{sha256}"


def _tamper_package(tmp_path: Path) -> Path:
    package = tmp_path / "FX-SVC-CEX-001-tamper"
    shutil.copytree(PACKAGE, package)
    return package


def test_complete_cex_cluster_matches_the_pinned_fact_hash() -> None:
    result = analyze_cex_cluster_replay(
        _request(),
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "complete"
    assert _hash(result.root.results[0].value) == PINNED_SHA256
    assert result.root.results[0].value["attribution"] == {
        "exchange_ownership": "not_assessed",
        "criminality": "not_assessed",
    }


def test_same_endpoint_masquerading_as_two_providers_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][1]["endpoint"] = provider["providers"][0]["endpoint"]
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    result = analyze_cex_cluster_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_missing_verify_role_keeps_the_fixture_partial(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    raw["raw_observations"] = [
        item for item in raw["raw_observations"] if item["provider_role"] == "PRIMARY"
    ]
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    result = analyze_cex_cluster_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )

    assert result.root.status == "partial"
    assert result.root.results[0].value["available_transfers"] == 3
    assert "cluster_judgment" not in result.root.results[0].value
    assert result.root.errors[0].code == "evidence_incomplete"


def test_cross_provider_fact_mismatch_fails(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    mismatched = PRIMARY_PINS["1"]
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["transfer_index"] == 0:
            observation["artifacts"] = {
                capability: _artifact_uri(digest) for capability, digest in mismatched.items()
            }
    provider["providers"][1]["raw_sha256"]["0"] = mismatched
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    result = analyze_cex_cluster_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_cex_cluster_requires_offline_source_binding() -> None:
    document = _request_document()
    document["source_policy"]["offline_mode"] = False
    request = validate_analysis_request(document).root
    assert isinstance(request, CexClusterAnalysisRequest)

    result = analyze_cex_cluster_replay(
        request,
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"


def test_cex_query_is_rejected_for_another_analysis_type() -> None:
    document = _request_document()
    document["analysis_type"] = "flow_path"

    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(document)


def test_cex_cluster_is_deterministic_across_two_runs() -> None:
    raw_replay = (PACKAGE / "raw-replay.json").read_bytes()
    first = analyze_cex_cluster_replay(_request(), raw_replay, package_dir=PACKAGE)
    second = analyze_cex_cluster_replay(_request(), raw_replay, package_dir=PACKAGE)

    assert first.to_contract_dict() == second.to_contract_dict()
