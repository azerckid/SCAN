import copy
import json
import shutil
from pathlib import Path

import pytest

from scan_tool.application.task_015_independent_verifier import (
    load_json,
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"


def _copy_label_package_with_dependencies(tmp_path: Path) -> None:
    shutil.copytree(
        FIXTURE_ROOT / "FX-OSINT-LABEL-CONFLICT-001",
        tmp_path / "FX-OSINT-LABEL-CONFLICT-001",
    )
    shutil.copytree(
        FIXTURE_ROOT / "FX-OSINT-SANCTIONS-HISTORY-001",
        tmp_path / "FX-OSINT-SANCTIONS-HISTORY-001",
    )


def test_repository_verifies_four_reviewed_fixtures_deterministically() -> None:
    first = verify_repository(FIXTURE_ROOT)
    assert len(first) == 4
    assert first == verify_repository(FIXTURE_ROOT)
    assert {item["status"] for item in first} == {"pass"}


def test_label_request_no_longer_depends_on_openrail_selected_row() -> None:
    package = FIXTURE_ROOT / "FX-OSINT-LABEL-CONFLICT-001"
    request = load_json(package / "analysis-request.json")
    replay = load_json(package / "source-replay.json")
    refs = set(request["inputs"]["source_artifact_refs"])
    assert (
        "artifact://sha256/15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475"
        not in refs
    )
    assert {item["source_id"] for item in replay["sources"]} == {
        "DS-SANCTIONS-PUBLIC",
        "DS-OSINT-WEB",
        "DS-ENS",
    }


def test_provider_decoded_mismatch_is_rejected(tmp_path: Path) -> None:
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    package = tmp_path / fixture_id
    package.mkdir()
    source = FIXTURE_ROOT / fixture_id
    for name in ("expected.json", "evidence.json", "provider-replay.json"):
        (package / name).write_bytes((source / name).read_bytes())
    replay = load_json(package / "provider-replay.json")
    replay["providers"][1]["decoded"]["reverse_name"] = "wrong.eth"
    (package / "provider-replay.json").write_text(json.dumps(replay))
    with pytest.raises(ValueError, match="decoded values differ"):
        verify_fixture(tmp_path, fixture_id)


def test_sls_context_cannot_rewrite_history(tmp_path: Path) -> None:
    fixture_id = "FX-OSINT-SANCTIONS-HISTORY-001"
    package = tmp_path / fixture_id
    package.mkdir()
    source = FIXTURE_ROOT / fixture_id
    for name in ("input.json", "expected.json", "evidence.json", "sls-snapshot.json"):
        (package / name).write_bytes((source / name).read_bytes())
    snapshot = load_json(package / "sls-snapshot.json")
    snapshot["interpretation"]["historical_removal_changed"] = True
    (package / "sls-snapshot.json").write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match="rewrites historical facts"):
        verify_fixture(tmp_path, fixture_id)


def test_sls_context_must_match_fixture_subject(tmp_path: Path) -> None:
    fixture_id = "FX-OSINT-SANCTIONS-HISTORY-001"
    package = tmp_path / fixture_id
    package.mkdir()
    source = FIXTURE_ROOT / fixture_id
    for name in ("input.json", "expected.json", "evidence.json", "sls-snapshot.json"):
        (package / name).write_bytes((source / name).read_bytes())
    snapshot = load_json(package / "sls-snapshot.json")
    snapshot["query"]["address"] = "0x00000000000000000000000000000000000000ff"
    (package / "sls-snapshot.json").write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match="snapshot subject differs"):
        verify_fixture(tmp_path, fixture_id)


def test_community_config_content_hash_drift_is_rejected(tmp_path: Path) -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    _copy_label_package_with_dependencies(tmp_path)
    config = (
        tmp_path
        / fixture_id
        / "artifacts/sha256"
        / "84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32.js"
    )
    config.write_text(config.read_text() + "\n// drift\n")
    with pytest.raises(ValueError, match="content-addressed artifact hash differs"):
        verify_fixture(tmp_path, fixture_id)


def test_ens_snapshot_content_hash_drift_is_rejected(tmp_path: Path) -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    _copy_label_package_with_dependencies(tmp_path)
    snapshot = (
        tmp_path
        / fixture_id
        / "artifacts/sha256"
        / "c5da8824427364b20cc4582cb15a3704f20e4b15bb16b81dd52f7e5d6203bf4d.json"
    )
    snapshot.write_text(snapshot.read_text() + "\n")
    with pytest.raises(ValueError, match="content-addressed artifact hash differs"):
        verify_fixture(tmp_path, fixture_id)


def test_official_history_projection_content_hash_drift_is_rejected(
    tmp_path: Path,
) -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    _copy_label_package_with_dependencies(tmp_path)
    projection = (
        tmp_path
        / fixture_id
        / "artifacts/sha256"
        / "2ddb426a2d404d4984345fb6026ca02932cd4313dd0db79b36f41617f34a9a34.json"
    )
    projection.write_text(projection.read_text() + "\n")
    with pytest.raises(ValueError, match="content-addressed artifact hash differs"):
        verify_fixture(tmp_path, fixture_id)


@pytest.mark.parametrize(
    ("evidence_id", "field", "value"),
    [
        ("EV-INTEL-LABEL-OFFICIAL-HISTORY", "subject_address", "0x" + "11" * 20),
        ("EV-INTEL-LABEL-CONFIG", "denomination", "10"),
        ("EV-INTEL-LABEL-ENS", "resolved_address", "0x" + "22" * 20),
    ],
)
def test_label_cross_source_binding_drift_is_rejected(
    tmp_path: Path,
    evidence_id: str,
    field: str,
    value: str,
) -> None:
    fixture_id = "FX-OSINT-LABEL-CONFLICT-001"
    _copy_label_package_with_dependencies(tmp_path)
    evidence_path = tmp_path / fixture_id / "evidence.json"
    evidence = load_json(evidence_path)
    entries = [item for group in ("call_evidence", "context_evidence") for item in evidence[group]]
    next(item for item in entries if item["evidence_id"] == evidence_id)[field] = value
    evidence_path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="evidence differs|subject binding differs"):
        verify_fixture(tmp_path, fixture_id)


def test_requirement_without_evidence_is_rejected(tmp_path: Path) -> None:
    fixture_id = "FX-ACTOR-RELATION-HUB-001"
    fixture_root = tmp_path / "fixtures"
    for source_id in (fixture_id, "FX-SVC-DEX-001", "FX-EVM-AUTH-001"):
        source = FIXTURE_ROOT / source_id
        target = fixture_root / source_id
        target.mkdir(parents=True)
        for name in ("expected.json", "evidence.json", "raw-replay.json"):
            if (source / name).exists():
                (target / name).write_bytes((source / name).read_bytes())
    evidence = copy.deepcopy(load_json(fixture_root / fixture_id / "evidence.json"))
    evidence["context_evidence"] = evidence["context_evidence"][1:]
    (fixture_root / fixture_id / "evidence.json").write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="evidence reference differs"):
        verify_fixture(fixture_root, fixture_id)


def test_common_funder_is_outside_ready_verifier_set() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        verify_fixture(FIXTURE_ROOT, "FX-ACTOR-COMMON-FUNDER-001")
