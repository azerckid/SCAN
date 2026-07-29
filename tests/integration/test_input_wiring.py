"""WP-INPUT CLI and Operations raw-artifact handoff tests."""

import json
from pathlib import Path

import pytest

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage
from scan_tool.application.input_wiring import InputEvidenceService
from scan_tool.application.security import SensitiveDataError
from scan_tool.domain.input_source import ArtifactFormat, ChainScope, InputMode

DEX_REPLAY = (
    Path(__file__).resolve().parents[2]
    / "docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/raw-replay.json"
)


def test_normalized_input_persists_once_and_rebuilds_approved_replay(
    tmp_path: Path,
) -> None:
    body = DEX_REPLAY.read_bytes()
    service = InputEvidenceService()
    prepared = service.prepare(
        body,
        input_mode=InputMode.PROVIDED_ARTIFACT,
        chain_scope=ChainScope.EVM,
        artifact_format=ArtifactFormat.JSON,
    )

    with SQLiteStorage(tmp_path / "scan.sqlite3") as storage:
        artifacts = ArtifactStore(tmp_path)
        persisted = service.persist(
            prepared,
            artifacts=artifacts,
            storage=storage,
        )
        replay = service.approved_replay(
            persisted,
            artifacts=artifacts,
            expected_chain_scope=ChainScope.EVM,
        )

        assert replay.body == body
        assert replay.sha256 == prepared.bundle.raw_sha256
        assert persisted.envelope.raw_artifact_uri == persisted.artifact.uri
        assert storage.get_artifact(replay.sha256) == persisted.artifact


def test_rejected_input_is_not_persisted(tmp_path: Path) -> None:
    service = InputEvidenceService()

    with pytest.raises(SensitiveDataError):
        service.prepare(
            json.dumps({"path": "/Users/private/source.json"}).encode(),
            input_mode=InputMode.PROVIDED_ARTIFACT,
            chain_scope=ChainScope.EVM,
            artifact_format=ArtifactFormat.JSON,
        )

    assert not (tmp_path / "artifacts").exists()
