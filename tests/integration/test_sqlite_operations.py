"""OPS-IMPL-02 migration, repository, and append-only event tests."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scan_tool.adapters import sqlite_operations
from scan_tool.adapters.sqlite_operations import (
    OPERATIONS_STORAGE_VERSION,
    SQLiteOperationsRepository,
    initialize_operations_database,
    migrate_operations_database,
)
from scan_tool.adapters.sqlite_storage import SQLiteStorage
from scan_tool.application.security import SensitiveDataError, SensitiveDataGuard
from scan_tool.domain.operations import OperationEvent, OperationsDocument
from scan_tool.domain.storage import ArtifactRecord

EXAMPLE = (
    Path(__file__).parents[2]
    / "docs"
    / "05_QA_Validation"
    / "examples"
    / "operations"
    / "rules-gated-bundle.json"
)
ORIGINAL_SHA = "a" * 64


def _version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }


def _record_original_artifact(storage: SQLiteStorage) -> None:
    storage.record_artifact(
        ArtifactRecord(
            sha256=ORIGINAL_SHA,
            byte_length=42,
            media_type="text/plain",
            relative_path=f"sha256/{ORIGINAL_SHA[:2]}/{ORIGINAL_SHA}",
            artifact_kind="problem_text",
            redaction_status="not_required",
            license_status="competition_input",
            created_at=datetime(2026, 7, 28, 3, tzinfo=UTC),
        )
    )


def _document() -> OperationsDocument:
    return OperationsDocument.model_validate(json.loads(EXAMPLE.read_text()))


def test_empty_database_initializes_v1_then_migrates_to_v2(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    backup = tmp_path / "scan-v1.sqlite3"

    initialize_operations_database(database, backup_path=backup)

    assert _version(database) == OPERATIONS_STORAGE_VERSION
    assert _version(backup) == 1
    assert _tables(database) >= sqlite_operations.V2_TABLES
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_populated_v1_migration_preserves_data_and_backup(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    backup = tmp_path / "scan-v1.sqlite3"
    with SQLiteStorage(database) as storage:
        _record_original_artifact(storage)

    migrate_operations_database(database, backup_path=backup)

    for path, expected_version in ((database, 2), (backup, 1)):
        with sqlite3.connect(path) as connection:
            assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == expected_version
            assert (
                connection.execute(
                    "SELECT byte_length FROM artifacts WHERE sha256 = ?",
                    (ORIGINAL_SHA,),
                ).fetchone()[0]
                == 42
            )
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_failed_migration_rolls_back_and_v1_remains_openable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "scan.sqlite3"
    backup = tmp_path / "scan-v1.sqlite3"
    with SQLiteStorage(database):
        pass
    failing = (
        sqlite_operations.V2_DDL_STATEMENTS[0],
        "CREATE TABLE intentionally_broken(",
        *sqlite_operations.V2_DDL_STATEMENTS[1:],
    )
    monkeypatch.setattr(sqlite_operations, "V2_DDL_STATEMENTS", failing)

    with pytest.raises(sqlite3.OperationalError):
        migrate_operations_database(database, backup_path=backup)

    assert _version(database) == 1
    assert _version(backup) == 1
    assert "competitions" not in _tables(database)
    with SQLiteStorage(database) as storage:
        assert storage.integrity_check() == "ok"


def test_v1_storage_explicitly_rejects_v2_database(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    initialize_operations_database(database, backup_path=tmp_path / "backup.sqlite3")

    with pytest.raises(ValueError, match="unsupported SQLite schema version: 2"):
        SQLiteStorage(database)


def test_repository_persists_gated_bundle_and_append_only_events(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    backup = tmp_path / "scan-v1.sqlite3"
    with SQLiteStorage(database) as storage:
        _record_original_artifact(storage)
    migrate_operations_database(database, backup_path=backup)

    with SQLiteOperationsRepository(database) as repository:
        repository.save_document(_document())
        assert repository.count("competitions") == 1
        assert repository.count("problems") == 1
        assert repository.count("plans") == 1
        assert repository.count("jobs") == 1
        assert repository.count("operation_events") == 1
        assert repository.integrity_check() == "ok"
        events = repository.list_events("COMP-SCAN-2026")
        assert [event["event_id"] for event in events] == ["OEV-Q01-CAPTURED"]

        duplicate = OperationEvent.model_validate(_document().to_contract_dict()["events"][0])
        with pytest.raises(sqlite3.IntegrityError):
            repository.append_event(duplicate)
        assert repository.count("operation_events") == 1

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE operation_events SET actor_id = 'other' WHERE event_id = ?",
                ("OEV-Q01-CAPTURED",),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM operation_events WHERE event_id = ?",
                ("OEV-Q01-CAPTURED",),
            )


def test_document_insert_is_atomic_when_artifact_is_missing(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    initialize_operations_database(database, backup_path=tmp_path / "backup.sqlite3")

    with SQLiteOperationsRepository(database) as repository:
        with pytest.raises(ValueError, match="artifact must already exist"):
            repository.save_document(_document())
        assert repository.count("competitions") == 0
        assert repository.count("problems") == 0


def test_migration_refuses_overwrite_and_wrong_versions(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    with SQLiteStorage(database):
        pass
    backup.write_bytes(b"keep")

    with pytest.raises(FileExistsError):
        migrate_operations_database(database, backup_path=backup)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 9")
    with pytest.raises(ValueError, match="expected SQLite schema version 1, got 9"):
        migrate_operations_database(database, backup_path=tmp_path / "other.sqlite3")


def test_event_secret_is_rejected_before_persistence(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    with SQLiteStorage(database) as storage:
        _record_original_artifact(storage)
    migrate_operations_database(database, backup_path=tmp_path / "backup.sqlite3")
    document = _document()

    with SQLiteOperationsRepository(
        database,
        guard=SensitiveDataGuard(("canary-secret",)),
    ) as repository:
        repository.save_document(document)
        event = document.root.events[0].model_copy(
            update={
                "event_id": "OEV-Q01-SECRET",
                "safe_details_json": {"note": "canary-secret"},
            }
        )
        with pytest.raises(SensitiveDataError):
            repository.append_event(event)
        assert repository.count("operation_events") == 1
