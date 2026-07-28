"""Explicit SQLite v2 migration and persistence for the operations contract."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from scan_tool.adapters.sqlite_storage import SCHEMA_VERSION as ANALYSIS_STORAGE_VERSION
from scan_tool.adapters.sqlite_storage import SQLiteStorage
from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.operations import OperationEvent, OperationsDocument

OPERATIONS_STORAGE_VERSION = 2


V2_DDL_STATEMENTS = (
    """
    CREATE TABLE competitions (
        competition_id TEXT PRIMARY KEY,
        operations_schema_version TEXT NOT NULL CHECK(operations_schema_version = '0.1'),
        name TEXT NOT NULL,
        phase TEXT NOT NULL,
        environment TEXT NOT NULL,
        rules_snapshot_ref TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE operation_ai_modes (
        mode_id TEXT PRIMARY KEY,
        competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
        provider_id TEXT,
        model_id TEXT,
        adapter_kind TEXT NOT NULL,
        data_boundary TEXT NOT NULL,
        tool_mode TEXT NOT NULL,
        rule_state TEXT NOT NULL,
        affected_rule_ids_json TEXT NOT NULL,
        rules_snapshot_ref TEXT NOT NULL,
        created_at TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE problems (
        problem_id TEXT PRIMARY KEY,
        competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
        title TEXT NOT NULL,
        provided_urls_json TEXT NOT NULL,
        score INTEGER NOT NULL CHECK(score >= 0),
        answer_format TEXT NOT NULL,
        priority TEXT NOT NULL,
        priority_source TEXT NOT NULL,
        status TEXT NOT NULL,
        active_plan_id TEXT REFERENCES plans(plan_id) DEFERRABLE INITIALLY DEFERRED,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE problem_artifacts (
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        artifact_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
        role TEXT NOT NULL CHECK(role IN ('original_text', 'provided_file')),
        filename TEXT,
        media_type TEXT,
        PRIMARY KEY(problem_id, artifact_sha256, role)
    ) STRICT
    """,
    """
    CREATE UNIQUE INDEX problem_original_artifact
    ON problem_artifacts(problem_id) WHERE role = 'original_text'
    """,
    """
    CREATE TABLE plans (
        plan_id TEXT PRIMARY KEY,
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        mode_id TEXT NOT NULL REFERENCES operation_ai_modes(mode_id),
        planner_job_id TEXT NOT NULL REFERENCES jobs(job_id)
            DEFERRABLE INITIALLY DEFERRED,
        status TEXT NOT NULL,
        problem_type_hypothesis TEXT NOT NULL,
        method_hypothesis TEXT NOT NULL,
        assumptions_json TEXT NOT NULL,
        missing_inputs_json TEXT NOT NULL,
        leaf_job_specs_json TEXT NOT NULL,
        raw_output_artifact_sha256 TEXT REFERENCES artifacts(sha256),
        created_at TEXT NOT NULL,
        decided_at TEXT
    ) STRICT
    """,
    """
    CREATE TABLE jobs (
        job_id TEXT PRIMARY KEY,
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        plan_id TEXT NOT NULL REFERENCES plans(plan_id) DEFERRABLE INITIALLY DEFERRED,
        role TEXT NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        priority TEXT NOT NULL,
        idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) = 64),
        analysis_id TEXT REFERENCES analysis_runs(analysis_id),
        attempt INTEGER NOT NULL CHECK(attempt >= 0),
        max_attempts INTEGER NOT NULL CHECK(max_attempts >= 1 AND attempt <= max_attempts),
        assigned_worker_id TEXT,
        error_code TEXT,
        checkpoint_ref TEXT,
        queued_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    ) STRICT
    """,
    """
    CREATE TABLE job_dependencies (
        job_id TEXT NOT NULL REFERENCES jobs(job_id),
        depends_on_job_id TEXT NOT NULL REFERENCES jobs(job_id),
        PRIMARY KEY(job_id, depends_on_job_id),
        CHECK(job_id <> depends_on_job_id)
    ) STRICT
    """,
    """
    CREATE TABLE problem_analysis_links (
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
        role TEXT NOT NULL,
        job_id TEXT NOT NULL REFERENCES jobs(job_id),
        PRIMARY KEY(problem_id, analysis_id, job_id)
    ) STRICT
    """,
    """
    CREATE TABLE candidates (
        candidate_id TEXT PRIMARY KEY,
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        answer_format TEXT NOT NULL,
        answer_value TEXT NOT NULL,
        status TEXT NOT NULL,
        verification_refs_json TEXT NOT NULL,
        confidence INTEGER NOT NULL CHECK(confidence BETWEEN 0 AND 100),
        confidence_basis TEXT NOT NULL,
        uncertainties_json TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        created_by_job_id TEXT NOT NULL REFERENCES jobs(job_id),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE TABLE candidate_result_links (
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
        ref_type TEXT NOT NULL CHECK(ref_type IN ('result', 'evidence')),
        ref_id TEXT NOT NULL,
        PRIMARY KEY(candidate_id, ref_type, ref_id)
    ) STRICT
    """,
    """
    CREATE TABLE verifications (
        verification_id TEXT PRIMARY KEY,
        problem_id TEXT NOT NULL REFERENCES problems(problem_id),
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        verifier_job_id TEXT NOT NULL REFERENCES jobs(job_id),
        status TEXT NOT NULL,
        required_checks_json TEXT NOT NULL,
        independent_from_job_ids_json TEXT NOT NULL,
        conflicts_json TEXT NOT NULL,
        missing_evidence_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        finished_at TEXT
    ) STRICT
    """,
    """
    CREATE TABLE verification_checks (
        verification_id TEXT NOT NULL REFERENCES verifications(verification_id),
        check_name TEXT NOT NULL,
        passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
        result_refs_json TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        PRIMARY KEY(verification_id, check_name)
    ) STRICT
    """,
    """
    CREATE TABLE submissions (
        submission_id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
        operator_confirmed INTEGER NOT NULL CHECK(operator_confirmed = 1),
        response TEXT NOT NULL,
        submitted_at TEXT NOT NULL,
        note_artifact_sha256 TEXT REFERENCES artifacts(sha256)
    ) STRICT
    """,
    """
    CREATE TABLE operation_events (
        event_id TEXT PRIMARY KEY,
        competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
        problem_id TEXT REFERENCES problems(problem_id),
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        actor_type TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        safe_details_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    ) STRICT
    """,
    """
    CREATE TRIGGER operation_events_no_update
    BEFORE UPDATE ON operation_events
    BEGIN
        SELECT RAISE(ABORT, 'operation_events is append-only');
    END
    """,
    """
    CREATE TRIGGER operation_events_no_delete
    BEFORE DELETE ON operation_events
    BEGIN
        SELECT RAISE(ABORT, 'operation_events is append-only');
    END
    """,
    """
    CREATE TABLE operation_errors (
        error_id TEXT PRIMARY KEY,
        competition_id TEXT NOT NULL REFERENCES competitions(competition_id),
        code TEXT NOT NULL,
        message TEXT NOT NULL,
        stage TEXT NOT NULL,
        retryable INTEGER NOT NULL CHECK(retryable IN (0, 1)),
        problem_id TEXT REFERENCES problems(problem_id),
        job_id TEXT REFERENCES jobs(job_id),
        details_json TEXT NOT NULL
    ) STRICT
    """,
    "CREATE INDEX operation_problem_status ON problems(competition_id, status)",
    "CREATE INDEX operation_job_queue ON jobs(status, priority, queued_at)",
    "CREATE INDEX operation_event_stream ON operation_events(competition_id, created_at)",
    "CREATE INDEX operation_analysis_lookup ON problem_analysis_links(analysis_id)",
)

V2_TABLES = frozenset(
    {
        "competitions",
        "operation_ai_modes",
        "problems",
        "problem_artifacts",
        "plans",
        "jobs",
        "job_dependencies",
        "problem_analysis_links",
        "candidates",
        "candidate_result_links",
        "verifications",
        "verification_checks",
        "submissions",
        "operation_events",
        "operation_errors",
    }
)


def initialize_operations_database(path: Path, *, backup_path: Path) -> None:
    """Create a v1 baseline when needed, then explicitly migrate it to v2."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with SQLiteStorage(path):
            pass
    migrate_operations_database(path, backup_path=backup_path)


def migrate_operations_database(path: Path, *, backup_path: Path) -> None:
    """Back up and transactionally migrate a v1 database to operations v2."""

    if not path.exists():
        raise FileNotFoundError("SQLite source database does not exist")
    if backup_path.resolve() == path.resolve():
        raise ValueError("backup destination must differ from the source database")
    if backup_path.exists():
        raise FileExistsError("backup destination already exists")

    with _connect(path) as connection:
        version = _schema_version(connection)
        if version != ANALYSIS_STORAGE_VERSION:
            raise ValueError(f"expected SQLite schema version 1, got {version}")
        _require_integrity(connection, "source")
        _backup_database(connection, backup_path)

        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in V2_DDL_STATEMENTS:
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {OPERATIONS_STORAGE_VERSION}")
            foreign_key_failures = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_failures:
                raise sqlite3.IntegrityError("SQLite migration failed foreign_key_check")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        if _schema_version(connection) != OPERATIONS_STORAGE_VERSION:
            raise sqlite3.DatabaseError("SQLite migration did not set schema version 2")
        _require_integrity(connection, "migrated database")


class SQLiteOperationsRepository:
    """Write-side repository for a validated operations contract bundle."""

    def __init__(
        self,
        path: Path,
        *,
        guard: SensitiveDataGuard | None = None,
    ) -> None:
        self.path = path
        self._guard = guard or SensitiveDataGuard()
        self._connection = _connect(path)
        version = _schema_version(self._connection)
        if version != OPERATIONS_STORAGE_VERSION:
            self._connection.close()
            raise ValueError(f"expected SQLite schema version 2, got {version}")
        _require_integrity(self._connection, "operations database")

    def __enter__(self) -> SQLiteOperationsRepository:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def save_document(self, document: OperationsDocument) -> None:
        """Atomically persist one validated operations snapshot without upserts."""

        payload = document.to_contract_dict()
        self._guard.check_text(_json(payload))
        manifest = payload["manifest"]
        assert isinstance(manifest, dict)

        with self._connection:
            self._insert_manifest(manifest)
            for mode in _records(payload, "ai_modes"):
                self._insert_mode(mode)
            for problem in _records(payload, "problems"):
                self._insert_problem(problem)
            for plan in _records(payload, "plans"):
                self._insert_plan(plan)
            for job in _records(payload, "jobs"):
                self._insert_job(job)
            self._insert_job_dependencies(payload)
            for candidate in _records(payload, "candidates"):
                self._insert_candidate(candidate)
            for verification in _records(payload, "verifications"):
                self._insert_verification(verification)
            for submission in _records(payload, "submissions"):
                self._insert_submission(submission)
            for event in _records(payload, "events"):
                self._insert_event(event)
            competition_id = str(manifest["competition_id"])
            for error in _records(payload, "errors"):
                self._insert_error(competition_id, error)

    def append_event(self, event: OperationEvent) -> None:
        """Append one audit event; duplicate IDs fail instead of mutating history."""

        payload = event.model_dump(mode="json")
        self._guard.check_text(_json(payload))
        with self._connection:
            self._insert_event(payload)

    def list_events(self, competition_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM operation_events
            WHERE competition_id = ?
            ORDER BY created_at, event_id
            """,
            (competition_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, table: str) -> int:
        if table not in V2_TABLES:
            raise ValueError("unknown operations table")
        row = self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])

    def integrity_check(self) -> str:
        return str(self._connection.execute("PRAGMA integrity_check").fetchone()[0])

    def _insert_manifest(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO competitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["competition_id"],
                record["operations_schema_version"],
                record["name"],
                record["phase"],
                record["environment"],
                record["rules_snapshot_ref"],
                record["status"],
                record["created_at"],
                record["updated_at"],
            ),
        )

    def _insert_mode(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO operation_ai_modes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["mode_id"],
                record["competition_id"],
                record.get("provider_id"),
                record.get("model_id"),
                record["adapter_kind"],
                record["data_boundary"],
                record["tool_mode"],
                record["rule_state"],
                _json(record["affected_rule_ids"]),
                record["rules_snapshot_ref"],
                record["created_at"],
            ),
        )

    def _insert_problem(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO problems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["problem_id"],
                record["competition_id"],
                record["title"],
                _json(record["provided_urls"]),
                record["score"],
                record["answer_format"],
                record["priority"],
                record["priority_source"],
                record["status"],
                record.get("active_plan_id"),
                record["created_at"],
                record["updated_at"],
            ),
        )
        original_sha = _artifact_sha(record["original_text_artifact"])
        self._require_artifact(original_sha)
        self._connection.execute(
            "INSERT INTO problem_artifacts VALUES (?, ?, 'original_text', NULL, NULL)",
            (record["problem_id"], original_sha),
        )
        for artifact in record["provided_file_artifacts"]:
            sha256 = artifact["sha256"]
            self._require_artifact(sha256)
            self._connection.execute(
                """
                INSERT INTO problem_artifacts
                VALUES (?, ?, 'provided_file', ?, ?)
                """,
                (
                    record["problem_id"],
                    sha256,
                    artifact["filename"],
                    artifact["media_type"],
                ),
            )

    def _insert_plan(self, record: dict[str, Any]) -> None:
        raw_sha = None
        if "raw_output_artifact" in record:
            raw_sha = _artifact_sha(record["raw_output_artifact"])
            self._require_artifact(raw_sha)
        self._connection.execute(
            """
            INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["plan_id"],
                record["problem_id"],
                record["mode_id"],
                record["planner_job_id"],
                record["status"],
                record["problem_type_hypothesis"],
                record["method_hypothesis"],
                _json(record["assumptions"]),
                _json(record["missing_inputs"]),
                _json(record["leaf_job_specs"]),
                raw_sha,
                record["created_at"],
                record.get("decided_at"),
            ),
        )

    def _insert_job(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO jobs VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                record["job_id"],
                record["problem_id"],
                record["plan_id"],
                record["role"],
                record["job_type"],
                record["status"],
                record["priority"],
                record["idempotency_key"],
                record.get("analysis_id"),
                record["attempt"],
                record["max_attempts"],
                record.get("assigned_worker_id"),
                record.get("error_code"),
                record.get("checkpoint_ref"),
                record["queued_at"],
                record.get("started_at"),
                record.get("finished_at"),
            ),
        )
        if "analysis_id" in record:
            self._connection.execute(
                """
                INSERT INTO problem_analysis_links(problem_id, analysis_id, role, job_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record["problem_id"],
                    record["analysis_id"],
                    record["job_type"],
                    record["job_id"],
                ),
            )

    def _insert_job_dependencies(self, payload: dict[str, Any]) -> None:
        job_ids = {str(job["job_id"]) for job in _records(payload, "jobs")}
        for plan in _records(payload, "plans"):
            for leaf in plan["leaf_job_specs"]:
                if leaf["leaf_job_id"] not in job_ids:
                    continue
                for dependency in leaf["depends_on"]:
                    if dependency in job_ids:
                        self._connection.execute(
                            "INSERT INTO job_dependencies VALUES (?, ?)",
                            (leaf["leaf_job_id"], dependency),
                        )

    def _insert_candidate(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["candidate_id"],
                record["problem_id"],
                record["answer_format"],
                record["answer_value"],
                record["status"],
                _json(record["verification_refs"]),
                record["confidence"],
                record["confidence_basis"],
                _json(record["uncertainties"]),
                record["recommendation"],
                record["created_by_job_id"],
                record["created_at"],
                record["updated_at"],
            ),
        )
        for ref_type, table, id_column, refs_key in (
            ("result", "results", "result_id", "result_refs"),
            ("evidence", "evidence_records", "evidence_id", "evidence_refs"),
        ):
            for ref_id in record[refs_key]:
                row = self._connection.execute(
                    f"SELECT analysis_id FROM {table} WHERE {id_column} = ?",
                    (ref_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"unknown {ref_type} reference")
                self._connection.execute(
                    "INSERT INTO candidate_result_links VALUES (?, ?, ?, ?)",
                    (record["candidate_id"], row["analysis_id"], ref_type, ref_id),
                )

    def _insert_verification(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO verifications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["verification_id"],
                record["problem_id"],
                record["candidate_id"],
                record["verifier_job_id"],
                record["status"],
                _json(record["required_checks"]),
                _json(record["independent_from_job_ids"]),
                _json(record["conflicts"]),
                _json(record["missing_evidence"]),
                record["created_at"],
                record.get("finished_at"),
            ),
        )
        for check in record["check_results"]:
            self._connection.execute(
                "INSERT INTO verification_checks VALUES (?, ?, ?, ?, ?)",
                (
                    record["verification_id"],
                    check["check"],
                    int(check["passed"]),
                    _json(check["result_refs"]),
                    _json(check["evidence_refs"]),
                ),
            )

    def _insert_submission(self, record: dict[str, Any]) -> None:
        note_sha = None
        if "note_artifact" in record:
            note_sha = _artifact_sha(record["note_artifact"])
            self._require_artifact(note_sha)
        self._connection.execute(
            "INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?)",
            (
                record["submission_id"],
                record["candidate_id"],
                int(record["operator_confirmed"]),
                record["response"],
                record["submitted_at"],
                note_sha,
            ),
        )

    def _insert_event(self, record: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO operation_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["event_id"],
                record["competition_id"],
                record.get("problem_id"),
                record["entity_type"],
                record["entity_id"],
                record["event_type"],
                record["actor_type"],
                record["actor_id"],
                record.get("from_status"),
                record.get("to_status"),
                _json(record["safe_details_json"]),
                record["created_at"],
            ),
        )

    def _insert_error(self, competition_id: str, record: dict[str, Any]) -> None:
        self._connection.execute(
            "INSERT INTO operation_errors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record["error_id"],
                competition_id,
                record["code"],
                record["message"],
                record["stage"],
                int(record["retryable"]),
                record.get("problem_id"),
                record.get("job_id"),
                _json(record["details"]),
            ),
        )

    def _require_artifact(self, sha256: str) -> None:
        row = self._connection.execute(
            "SELECT 1 FROM artifacts WHERE sha256 = ?",
            (sha256,),
        ).fetchone()
        if row is None:
            raise ValueError("operations artifact must already exist in v1 artifacts")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _backup_database(connection: sqlite3.Connection, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as backup:
        connection.backup(backup)
        _require_integrity(backup, "backup")
        version = _schema_version(backup)
    if version != ANALYSIS_STORAGE_VERSION:
        raise sqlite3.DatabaseError("SQLite backup is not schema version 1")


def _require_integrity(connection: sqlite3.Connection, label: str) -> None:
    result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if result != "ok":
        raise sqlite3.DatabaseError(f"SQLite {label} failed integrity_check")


def _schema_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _artifact_sha(uri: str) -> str:
    prefix = "artifact://sha256/"
    if not uri.startswith(prefix):
        raise ValueError("unsupported artifact URI")
    return uri.removeprefix(prefix)


def _records(payload: dict[str, Any], key: str) -> Iterable[dict[str, Any]]:
    records = payload[key]
    assert isinstance(records, list)
    return records


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
