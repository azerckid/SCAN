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
PLAN_SHA = "c" * 64
ANALYSIS_ID = "AN-Q01-001"


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


def _record_artifact(storage: SQLiteStorage, sha256: str, kind: str) -> None:
    storage.record_artifact(
        ArtifactRecord(
            sha256=sha256,
            byte_length=42,
            media_type="text/plain",
            relative_path=f"sha256/{sha256[:2]}/{sha256}",
            artifact_kind=kind,
            redaction_status="not_required",
            license_status="competition_input",
            created_at=datetime(2026, 7, 28, 3, tzinfo=UTC),
        )
    )


def _record_original_artifact(storage: SQLiteStorage) -> None:
    _record_artifact(storage, ORIGINAL_SHA, "problem_text")


def _document() -> OperationsDocument:
    return OperationsDocument.model_validate(json.loads(EXAMPLE.read_text()))


def _dependency_document() -> OperationsDocument:
    payload = json.loads(EXAMPLE.read_text())
    payload["problems"][0]["status"] = "running"
    payload["ai_modes"][0].update(
        {
            "provider_id": "local.test",
            "model_id": "planner-test",
            "rule_state": "allowed",
        }
    )
    payload["plans"][0].update(
        {
            "status": "approved",
            "raw_output_artifact": f"artifact://sha256/{PLAN_SHA}",
            "decided_at": "2026-07-28T03:01:00Z",
            "leaf_job_specs": [
                {
                    "leaf_job_id": "JOB-Q01-EVIDENCE",
                    "role": "evidence",
                    "purpose": "Decode the transaction evidence.",
                    "analysis_type": "dex_swap",
                    "inputs_projection": {},
                    "depends_on": [],
                    "required_capabilities": ["receipt_decode"],
                    "expected_output": "Evidence-backed decoded result.",
                },
                {
                    "leaf_job_id": "JOB-Q01-TRACE",
                    "role": "evidence",
                    "purpose": "Trace the decoded result.",
                    "analysis_type": "dex_swap",
                    "inputs_projection": {},
                    "depends_on": ["JOB-Q01-EVIDENCE"],
                    "required_capabilities": ["trace_decode"],
                    "expected_output": "Dependency-aware trace result.",
                },
            ],
        }
    )
    payload["jobs"][0].update(
        {
            "status": "complete",
            "attempt": 1,
            "started_at": "2026-07-28T03:00:10Z",
            "finished_at": "2026-07-28T03:00:20Z",
        }
    )
    payload["jobs"].extend(
        [
            {
                "job_id": "JOB-Q01-EVIDENCE",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "evidence",
                "job_type": "dex_decode",
                "status": "complete",
                "priority": "normal",
                "idempotency_key": "d" * 64,
                "analysis_id": ANALYSIS_ID,
                "attempt": 1,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:01:00Z",
                "started_at": "2026-07-28T03:01:10Z",
                "finished_at": "2026-07-28T03:01:20Z",
            },
            {
                "job_id": "JOB-Q01-TRACE",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "evidence",
                "job_type": "path_trace",
                "status": "queued",
                "priority": "normal",
                "idempotency_key": "e" * 64,
                "attempt": 0,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:01:00Z",
            },
        ]
    )
    payload["errors"] = [
        {
            "error_id": "OERR-Q01-EVIDENCE",
            "code": "evidence_worker_failed",
            "message": "A prior evidence worker attempt failed safely.",
            "stage": "evidence_worker",
            "retryable": True,
            "problem_id": "PROB-Q01",
            "job_id": "JOB-Q01-EVIDENCE",
            "details": {"attempt": 0},
        }
    ]
    return OperationsDocument.model_validate(payload)


def _record_analysis_run(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs(
                analysis_id, analysis_type, chain_id, fixture_id, status,
                schema_version, tool_version, request_artifact_sha256,
                started_at, finished_at, created_at, updated_at
            ) VALUES (?, 'dex_swap', 1, NULL, 'complete', '0.1', '0.1.0', ?,
                      '2026-07-28T03:01:10+00:00', '2026-07-28T03:01:20+00:00',
                      '2026-07-28T03:01:00+00:00', '2026-07-28T03:01:20+00:00')
            """,
            (ANALYSIS_ID, PLAN_SHA),
        )


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


def test_repository_persists_dependencies_errors_and_analysis_link(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    with SQLiteStorage(database) as storage:
        _record_original_artifact(storage)
        _record_artifact(storage, PLAN_SHA, "planner_output")
    _record_analysis_run(database)
    migrate_operations_database(database, backup_path=tmp_path / "backup.sqlite3")

    with SQLiteOperationsRepository(database) as repository:
        repository.save_document(_dependency_document())

        assert repository.count("job_dependencies") == 1
        assert repository.count("operation_errors") == 1
        assert repository.count("problem_analysis_links") == 1
    with sqlite3.connect(database) as connection:
        dependency = connection.execute(
            "SELECT job_id, depends_on_job_id FROM job_dependencies"
        ).fetchone()
        assert tuple(dependency) == ("JOB-Q01-TRACE", "JOB-Q01-EVIDENCE")
        link = connection.execute(
            "SELECT problem_id, analysis_id, job_id FROM problem_analysis_links"
        ).fetchone()
        assert tuple(link) == ("PROB-Q01", ANALYSIS_ID, "JOB-Q01-EVIDENCE")


def test_unknown_analysis_fk_rolls_back_operations_document(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    with SQLiteStorage(database) as storage:
        _record_original_artifact(storage)
        _record_artifact(storage, PLAN_SHA, "planner_output")
    migrate_operations_database(database, backup_path=tmp_path / "backup.sqlite3")

    with SQLiteOperationsRepository(database) as repository:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            repository.save_document(_dependency_document())
        assert repository.count("competitions") == 0
        assert repository.count("jobs") == 0
        assert repository.count("operation_errors") == 0
