import json
import shutil
from pathlib import Path

import pytest

from scan_tool.application.task_016_cex_independent_verifier import (
    recalculate_raw_facts,
    verify_repository,
)
from scan_tool.application.task_016_cex_negative_oracles import (
    load_negative_oracle_manifest,
    verify_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"
PACKAGE = FIXTURE_ROOT / "FX-SVC-CEX-001"
MANIFEST = ROOT / "docs/05_QA_Validation/oracles/task-016-cex-negative-oracles-v0.1.json"
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


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tamper_package(tmp_path: Path) -> Path:
    package = tmp_path / "FX-SVC-CEX-001-tamper"
    shutil.copytree(PACKAGE, package)
    return package


def test_cex_independent_verifier_matches_fixture() -> None:
    reports = verify_repository(FIXTURE_ROOT)
    assert len(reports) == 1
    assert reports[0]["fixture_id"] == "FX-SVC-CEX-001"
    assert reports[0]["calculated_sha256"] == PINNED_SHA256


def test_same_endpoint_masquerade_is_rejected_by_independent_verifier(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    provider = _load(package / "provider-replay.json")
    provider["providers"][1]["endpoint"] = provider["providers"][0]["endpoint"]
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="distinct endpoints"):
        recalculate_raw_facts(
            package,
            _load(package / "raw-replay.json"),
            provider,
        )


def test_missing_transfer_role_is_rejected_by_independent_verifier(tmp_path: Path) -> None:
    package = _tamper_package(tmp_path)
    raw = _load(package / "raw-replay.json")
    raw["raw_observations"] = [
        item
        for item in raw["raw_observations"]
        if not (item["provider_role"] == "VERIFY" and item["transfer_index"] == 2)
    ]
    with pytest.raises(ValueError, match="VERIFY observations do not cover every transfer"):
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
    mismatched = PRIMARY_PINS["1"]
    for observation in raw["raw_observations"]:
        if observation["provider_role"] == "VERIFY" and observation["transfer_index"] == 0:
            observation["artifacts"] = {
                capability: f"artifact://sha256/{digest}"
                for capability, digest in mismatched.items()
            }
    provider["providers"][1]["raw_sha256"]["0"] = mismatched
    with pytest.raises(ValueError, match="cex transaction hash mismatch"):
        recalculate_raw_facts(package, raw, provider)


def test_cex_negative_oracle_manifest_is_verified() -> None:
    manifest = load_negative_oracle_manifest(MANIFEST)
    verified = verify_manifest(manifest)
    assert len(verified) == 8
