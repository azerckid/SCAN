import json
import shutil
from pathlib import Path

import pytest

from scan_tool.application.task_016_mixer_independent_verifier import (
    recalculate_raw_facts,
    verify_repository,
)
from scan_tool.application.task_016_mixer_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"
PACKAGE = FIXTURE_ROOT / "FX-SVC-MIX-001"
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-016-mixer-negative-oracles-v0.1.json"
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
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tamper_package(tmp_path: Path) -> Path:
    package = tmp_path / "FX-SVC-MIX-001-tamper"
    shutil.copytree(PACKAGE, package)
    return package


def test_mixer_independent_verifier_matches_fixture() -> None:
    reports = verify_repository(FIXTURE_ROOT)
    assert len(reports) == 1
    assert reports[0]["fixture_id"] == "FX-SVC-MIX-001"
    assert reports[0]["calculated_sha256"] == PINNED_SHA256


def test_same_endpoint_masquerade_is_rejected_by_independent_verifier(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = _load(package / "provider-replay.json")
    provider["providers"][1]["endpoint"] = provider["providers"][0]["endpoint"]
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="provider endpoint must be"):
        recalculate_raw_facts(
            package,
            _load(package / "raw-replay.json"),
            provider,
        )


def test_missing_verify_role_is_rejected_by_independent_verifier(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = _load(package / "raw-replay.json")
    raw["raw_observations"] = [
        item for item in raw["raw_observations"] if item["provider_role"] == "PRIMARY"
    ]
    with pytest.raises(ValueError, match="VERIFY observations do not cover every event"):
        recalculate_raw_facts(
            package,
            raw,
            _load(package / "provider-replay.json"),
        )


def test_cross_provider_fact_mismatch_is_rejected_by_independent_verifier(
    tmp_path: Path,
) -> None:
    package = _tamper_package(tmp_path)
    raw = _load(package / "raw-replay.json")
    provider = _load(package / "provider-replay.json")
    meta = _load(package / "artifacts/capture-meta.json")
    mismatched = PRIMARY_PINS["1"]
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["event_index"] == 0:
            observation["artifacts"] = {
                capability: f"artifact://sha256/{digest}"
                for capability, digest in mismatched.items()
            }
    provider["providers"][1]["raw_sha256"]["0"] = mismatched
    # Keep capture-meta bound so the failure is the cross-provider decode mismatch.
    event0_tx = "0xc716eec2c710b22840d0cd877a61a83e9aacf628c79843a9505d53fa2e33f483"
    event0_block = "0x1821f4f"
    meta["capabilities"][f"VERIFY:tx:{event0_tx}"]["response_sha"] = mismatched["transaction"]
    meta["capabilities"][f"VERIFY:tx:{event0_tx}"]["sha256"] = mismatched["transaction"]
    meta["capabilities"][f"VERIFY:receipt:{event0_tx}"]["response_sha"] = mismatched["receipt"]
    meta["capabilities"][f"VERIFY:receipt:{event0_tx}"]["sha256"] = mismatched["receipt"]
    meta["capabilities"][f"VERIFY:block:{event0_block}"]["response_sha"] = mismatched["block"]
    meta["capabilities"][f"VERIFY:block:{event0_block}"]["sha256"] = mismatched["block"]
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="mixer transaction hash mismatch"):
        recalculate_raw_facts(package, raw, provider)


def test_mixer_negative_oracle_manifest_is_verified() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    verified = verify_manifest(manifest)
    assert len(verified) == 8


def test_identical_primary_verify_hashes_are_rejected_by_independent_verifier(
    tmp_path: Path,
) -> None:
    package = _tamper_package(tmp_path)
    provider = _load(package / "provider-replay.json")
    provider["providers"][1]["raw_sha256"]["0"] = dict(provider["providers"][0]["raw_sha256"]["0"])
    raw = _load(package / "raw-replay.json")
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["event_index"] == 0:
            observation["artifacts"] = {
                capability: f"artifact://sha256/{digest}"
                for capability, digest in provider["providers"][1]["raw_sha256"]["0"].items()
            }
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="artifact hashes must be distinct"):
        recalculate_raw_facts(package, raw, provider)


def test_coordinated_role_endpoint_relabel_is_rejected_by_independent_verifier(
    tmp_path: Path,
) -> None:
    package = _tamper_package(tmp_path)
    provider = _load(package / "provider-replay.json")
    raw = _load(package / "raw-replay.json")
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
    with pytest.raises(ValueError, match="provider must be"):
        recalculate_raw_facts(package, raw, provider)


def test_capture_meta_tamper_is_rejected_by_independent_verifier(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    meta = _load(package / "artifacts/capture-meta.json")
    meta["primary_rpc"] = "https://example.invalid/rpc"
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="capture-meta primary_rpc"):
        recalculate_raw_facts(
            package,
            _load(package / "raw-replay.json"),
            _load(package / "provider-replay.json"),
        )


def test_future_capture_timestamp_is_rejected_by_independent_verifier(
    tmp_path: Path,
) -> None:
    package = _tamper_package(tmp_path)
    raw = _load(package / "raw-replay.json")
    provider = _load(package / "provider-replay.json")
    meta = _load(package / "artifacts/capture-meta.json")
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
    with pytest.raises(ValueError, match="capture timestamp must not be in the future"):
        recalculate_raw_facts(package, raw, provider)
