import hashlib
import json
import shutil
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import MixerFlowAnalysisRequest
from scan_tool.slices.mixer_flow import analyze_mixer_flow_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-MIX-001"
PINNED_SHA256 = "4c8c4eb8041642ea514e4c7357d474bb4038b9f6eeea55a816aa2dae41484939"
PRIMARY_PINS = {
    "0": {
        "transaction": "6d4556a26faf403f738d09371afe621ea72398d213de0a7c7bef0e012b45b28c",
        "receipt": "c05e285c5fab70fe628353d47d48923c0808f460fd20bd3b8163b97ce0fb25aa",
        "block": "b43e9457e19acc4686b6c3eab5f9388c53d8152b48d26976268a730ddc7fe519",
    },
    "1": {
        "transaction": "06b7a41f8f9d5a3b719fb01a3298136ee6f66c17f74b4deaf44eac1154d8175a",
        "receipt": "00593586517777240226a13d32e1c6e83d29c364dd29346a8f60347f97ee07bd",
        "block": "e58aaa17c369214fe5f81b47c78777dd6d8b4b60d6bee9e06f628756630dd0ee",
    },
    "2": {
        "transaction": "2ec95572adb4e585b2f7acb0d2e9057af4fa8be974654e9243703b58c6416362",
        "receipt": "d417c24ea44e58105f7b5a5e0d8eee8ed9afa69e924e0b18855205918fee56b6",
        "block": "67a1110984b083bf47e80c29b2cec43509e552f963c3ace733714d887ddddce4",
    },
}


def _request_document() -> dict[str, object]:
    return json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))


def _request() -> MixerFlowAnalysisRequest:
    request = validate_analysis_request(_request_document()).root
    assert isinstance(request, MixerFlowAnalysisRequest)
    return request


def _hash(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _artifact_uri(sha256: str) -> str:
    return f"artifact://sha256/{sha256}"


def _tamper_package(tmp_path: Path) -> Path:
    package = tmp_path / "FX-SVC-MIX-001-tamper"
    shutil.copytree(PACKAGE, package)
    return package


def test_complete_mixer_flow_matches_the_pinned_fact_hash() -> None:
    result = analyze_mixer_flow_replay(
        _request(),
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "complete"
    assert _hash(result.root.results[0].value) == PINNED_SHA256
    assert result.root.results[0].value["attribution"] == {
        "ownership": "not_assessed",
        "criminality": "not_assessed",
    }


def test_same_endpoint_masquerading_as_two_providers_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][1]["endpoint"] = provider["providers"][0]["endpoint"]
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    result = analyze_mixer_flow_replay(
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

    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )

    assert result.root.status == "partial"
    assert result.root.errors[0].code == "evidence_incomplete"


def test_cross_provider_mismatch_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    mismatched = PRIMARY_PINS["1"]
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["event_index"] == 0:
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

    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_mixer_flow_requires_offline_source_binding() -> None:
    document = _request_document()
    document["source_policy"]["offline_mode"] = False
    request = validate_analysis_request(document).root
    assert isinstance(request, MixerFlowAnalysisRequest)

    result = analyze_mixer_flow_replay(
        request,
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"


def test_mixer_flow_is_deterministic_across_two_runs() -> None:
    raw_replay = (PACKAGE / "raw-replay.json").read_bytes()
    first = analyze_mixer_flow_replay(_request(), raw_replay, package_dir=PACKAGE)
    second = analyze_mixer_flow_replay(_request(), raw_replay, package_dir=PACKAGE)
    assert first.to_contract_dict() == second.to_contract_dict()


def test_mixer_flow_request_variant_parses() -> None:
    request = validate_analysis_request(_request_document())
    assert isinstance(request.root, MixerFlowAnalysisRequest)


def test_identical_primary_verify_hashes_are_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][1]["raw_sha256"]["0"] = dict(provider["providers"][0]["raw_sha256"]["0"])
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["event_index"] == 0:
            observation["artifacts"] = {
                capability: _artifact_uri(digest)
                for capability, digest in provider["providers"][1]["raw_sha256"]["0"].items()
            }
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_coordinated_role_endpoint_relabel_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    # Keep provider_ids fixed; swap only roles + endpoints (coordinated relabel).
    provider["providers"][0]["role"], provider["providers"][1]["role"] = "VERIFY", "PRIMARY"
    provider["providers"][0]["endpoint"], provider["providers"][1]["endpoint"] = (
        "https://eth.merkle.io",
        "https://ethereum-rpc.publicnode.com",
    )
    for observation in raw["raw_observations"]:
        if observation["provider_id"] == "PROVIDER-ETHEREUM-PUBLICNODE":
            observation["provider_role"] = "VERIFY"
        else:
            observation["provider_role"] = "PRIMARY"
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_capture_meta_tamper_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    meta = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    first_key = next(iter(meta["capabilities"]))
    meta["capabilities"][first_key]["response_sha"] = "0" * 64
    meta["capabilities"][first_key]["sha256"] = "0" * 64
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_future_capture_timestamp_is_rejected(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    meta = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    future = "2099-01-01T00:00:00Z"
    raw["captured_at"] = future
    provider["captured_at"] = future
    for item in provider["providers"]:
        item["retrieved_at"] = future
    meta["captured_at"] = future
    for entry in meta["capabilities"].values():
        entry["captured_at"] = future
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_mixer_flow_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"
