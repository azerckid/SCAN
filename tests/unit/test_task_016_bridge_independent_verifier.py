import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from scan_tool.application.task_016_bridge_independent_verifier import (
    load_json,
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"
PACKAGE = FIXTURE_ROOT / "FX-SVC-BRG-001"


def _tampered_package(tmp_path: Path, chain: str, capability: str, mutate: Any) -> Path:
    """Copy the fixture, mutate one artifact's raw JSON-RPC result, and
    re-pin its SHA-256 consistently in the copied raw-replay/provider-replay
    documents. This proves the semantic checks (topic0, tx/block binding)
    catch bad data even when the SHA-256 layer is internally self-consistent
    — a tampered file with a stale hash would be caught earlier and more
    trivially, which is not what these tests are checking.
    """
    package = tmp_path / "FX-SVC-BRG-001"
    shutil.copytree(PACKAGE, package)
    raw = json.loads((package / "raw-replay.json").read_text())
    provider_replay = json.loads((package / "provider-replay.json").read_text())

    observation = next(item for item in raw["raw_observations"] if item["chain"] == chain)
    old_uri = observation["artifacts"][capability]
    old_sha256 = old_uri.removeprefix("artifact://sha256/")
    artifact_path = package / "artifacts" / "sha256" / f"{old_sha256}.json"
    document = json.loads(artifact_path.read_text())
    mutate(document["result"])
    new_bytes = json.dumps(document).encode()
    new_sha256 = hashlib.sha256(new_bytes).hexdigest()
    artifact_path.unlink()
    (package / "artifacts" / "sha256" / f"{new_sha256}.json").write_bytes(new_bytes)

    observation["artifacts"][capability] = f"artifact://sha256/{new_sha256}"
    (package / "raw-replay.json").write_text(json.dumps(raw))

    provider = next(
        item
        for item in provider_replay["providers"]
        if item["provider_id"] == observation["provider_id"]
    )
    provider["raw_sha256"][capability] = new_sha256
    (package / "provider-replay.json").write_text(json.dumps(provider_replay))
    return package


def test_repository_recalculates_the_bridge_fixture_deterministically() -> None:
    first = verify_repository(FIXTURE_ROOT)
    assert len(first) == 1
    assert first == verify_repository(FIXTURE_ROOT)


def test_wrong_topic0_is_rejected(tmp_path: Path) -> None:
    def mutate(result: list[dict[str, Any]]) -> None:
        result[0]["topics"][0] = f"0x{'11' * 32}"

    package = _tampered_package(tmp_path, "base", "bridge_logs", mutate)
    with pytest.raises(ValueError, match="topic0 mismatch"):
        verify_fixture(
            package,
            load_json(package / "raw-replay.json"),
            load_json(package / "provider-replay.json"),
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_wrong_transaction_hash_is_rejected(tmp_path: Path) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["hash"] = f"0x{'22' * 32}"

    package = _tampered_package(tmp_path, "base", "transaction", mutate)
    with pytest.raises(ValueError, match="transaction hash mismatch"):
        verify_fixture(
            package,
            load_json(package / "raw-replay.json"),
            load_json(package / "provider-replay.json"),
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_wrong_block_hash_is_rejected(tmp_path: Path) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["hash"] = f"0x{'33' * 32}"

    package = _tampered_package(tmp_path, "ethereum", "block", mutate)
    with pytest.raises(ValueError, match="block hash reconciliation failed"):
        verify_fixture(
            package,
            load_json(package / "raw-replay.json"),
            load_json(package / "provider-replay.json"),
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_artifact_sha256_must_match_pinned_provider_value(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-BRG-001"
    shutil.copytree(PACKAGE, package)
    raw = json.loads((package / "raw-replay.json").read_text())
    next(item for item in raw["raw_observations"] if item["chain"] == "base")["artifacts"][
        "bridge_logs"
    ] = f"artifact://sha256/{'44' * 32}"
    (package / "raw-replay.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="does not match the pinned provider raw_sha256"):
        verify_fixture(
            package,
            load_json(package / "raw-replay.json"),
            load_json(package / "provider-replay.json"),
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_destination_amount_mismatch_is_rejected(tmp_path: Path) -> None:
    def mutate(result: list[dict[str, Any]]) -> None:
        data = result[0]["data"]
        words = data[2:]
        replaced = f"{0:064x}"
        result[0]["data"] = f"0x{words[: 3 * 64]}{replaced}{words[4 * 64 :]}"

    package = _tampered_package(tmp_path, "ethereum", "bridge_logs", mutate)
    with pytest.raises(ValueError, match="bridge event mismatch"):
        verify_fixture(
            package,
            load_json(package / "raw-replay.json"),
            load_json(package / "provider-replay.json"),
            load_json(package / "expected.json"),
            load_json(package / "evidence.json"),
        )


def test_evidence_value_mismatch_is_rejected() -> None:
    evidence = copy.deepcopy(load_json(PACKAGE / "evidence.json"))
    evidence["event_evidence"][0]["deposit_id"] = 1
    with pytest.raises(ValueError, match="value differs"):
        verify_fixture(
            PACKAGE,
            load_json(PACKAGE / "raw-replay.json"),
            load_json(PACKAGE / "provider-replay.json"),
            load_json(PACKAGE / "expected.json"),
            evidence,
        )


def test_canonical_hash_drift_from_pinned_evidence_is_rejected() -> None:
    evidence = copy.deepcopy(load_json(PACKAGE / "evidence.json"))
    evidence["verification_provenance"]["calculated_fact_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="verification provenance differs"):
        verify_fixture(
            PACKAGE,
            load_json(PACKAGE / "raw-replay.json"),
            load_json(PACKAGE / "provider-replay.json"),
            load_json(PACKAGE / "expected.json"),
            evidence,
        )
