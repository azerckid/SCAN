"""SQLite WAL storage for runs, provenance, cache, checkpoints, and exports."""

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult, AnalysisResultBase
from scan_tool.domain.source import SourceAttempt, SourceRequest, source_request_fingerprint
from scan_tool.domain.storage import (
    ArtifactRecord,
    CacheRecord,
    CheckpointRecord,
    ExportRecord,
)

SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS artifacts (
    sha256 TEXT PRIMARY KEY CHECK(length(sha256) = 64),
    byte_length INTEGER NOT NULL CHECK(byte_length >= 0),
    media_type TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE CHECK(substr(relative_path, 1, 1) <> '/'),
    artifact_kind TEXT NOT NULL,
    redaction_status TEXT NOT NULL,
    license_status TEXT NOT NULL,
    source_id TEXT,
    retrieved_at TEXT,
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS analysis_runs (
    analysis_id TEXT PRIMARY KEY,
    analysis_type TEXT NOT NULL,
    chain_id INTEGER NOT NULL CHECK(chain_id IN (0, 1)),
    fixture_id TEXT,
    status TEXT NOT NULL CHECK(
        status IN ('queued', 'running', 'complete', 'partial', 'failed',
                   'interrupted', 'restricted')
    ),
    schema_version TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    request_artifact_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(
        (status IN ('complete', 'partial', 'failed', 'interrupted', 'restricted')
         AND finished_at IS NOT NULL)
        OR
        (status IN ('queued', 'running') AND finished_at IS NULL)
    )
) STRICT;

CREATE TABLE IF NOT EXISTS run_source_policies (
    analysis_id TEXT PRIMARY KEY REFERENCES analysis_runs(analysis_id),
    rule_status TEXT NOT NULL,
    allowed_source_ids_json TEXT NOT NULL,
    source_order_json TEXT NOT NULL,
    allow_fallback INTEGER NOT NULL CHECK(allow_fallback IN (0, 1)),
    offline_mode INTEGER NOT NULL CHECK(offline_mode IN (0, 1)),
    rules_snapshot_ref TEXT,
    canonical_sha256 TEXT NOT NULL CHECK(length(canonical_sha256) = 64)
) STRICT;

CREATE TABLE IF NOT EXISTS source_attempts (
    source_attempt_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    source_record_id TEXT,
    source_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    method TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    block_tag TEXT,
    attempt_number INTEGER NOT NULL CHECK(attempt_number >= 1),
    outcome TEXT NOT NULL CHECK(outcome IN ('success', 'failed')),
    failure_kind TEXT,
    http_status INTEGER,
    retryable INTEGER NOT NULL CHECK(retryable IN (0, 1)),
    wait_seconds REAL CHECK(wait_seconds IS NULL OR wait_seconds >= 0),
    raw_sha256 TEXT CHECK(raw_sha256 IS NULL OR length(raw_sha256) = 64),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    artifact_sha256 TEXT REFERENCES artifacts(sha256),
    UNIQUE(analysis_id, request_fingerprint, provider_id, attempt_number)
) STRICT;

CREATE INDEX IF NOT EXISTS source_attempt_lookup
ON source_attempts(source_id, provider_id, request_fingerprint);

CREATE TABLE IF NOT EXISTS cache_entries (
    cache_key TEXT PRIMARY KEY CHECK(length(cache_key) = 64),
    source_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    block_tag TEXT,
    artifact_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
    immutability TEXT NOT NULL CHECK(immutability IN ('immutable', 'ttl', 'negative')),
    created_at TEXT NOT NULL,
    expires_at TEXT,
    last_verified_at TEXT,
    endpoint_host TEXT NOT NULL,
    endpoint_path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    media_type TEXT,
    retrieved_at TEXT NOT NULL,
    fallback_from_json TEXT NOT NULL,
    CHECK(
        (immutability = 'immutable' AND expires_at IS NULL)
        OR (immutability IN ('ttl', 'negative') AND expires_at IS NOT NULL)
    )
) STRICT;

CREATE INDEX IF NOT EXISTS cache_expiry_lookup
ON cache_entries(expires_at);

CREATE TABLE IF NOT EXISTS source_records (
    source_record_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    source_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    role TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0, 1)),
    capability TEXT NOT NULL,
    endpoint_host TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    fallback_from TEXT,
    UNIQUE(source_record_id, analysis_id)
) STRICT;

CREATE TABLE IF NOT EXISTS results (
    result_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    result_type TEXT NOT NULL,
    classification TEXT NOT NULL,
    requirement_ids_json TEXT NOT NULL,
    fixture_requirement_ids_json TEXT NOT NULL,
    value_json TEXT NOT NULL,
    value_sha256 TEXT NOT NULL CHECK(length(value_sha256) = 64),
    created_at TEXT NOT NULL,
    UNIQUE(result_id, analysis_id)
) STRICT;

CREATE INDEX IF NOT EXISTS result_run_lookup ON results(analysis_id);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    evidence_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_attempt_id TEXT REFERENCES source_attempts(source_attempt_id),
    method TEXT NOT NULL,
    locator_json TEXT NOT NULL,
    decoded_json TEXT NOT NULL,
    artifact_sha256 TEXT,
    retrieved_at TEXT NOT NULL,
    UNIQUE(evidence_id, analysis_id),
    FOREIGN KEY(source_record_id, analysis_id)
        REFERENCES source_records(source_record_id, analysis_id)
) STRICT;

CREATE INDEX IF NOT EXISTS evidence_run_lookup ON evidence_records(analysis_id);

CREATE TABLE IF NOT EXISTS result_evidence_links (
    result_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    analysis_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(result_id, evidence_id),
    FOREIGN KEY(result_id, analysis_id) REFERENCES results(result_id, analysis_id),
    FOREIGN KEY(evidence_id, analysis_id)
        REFERENCES evidence_records(evidence_id, analysis_id)
) STRICT;

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    stage TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision >= 1),
    cursor_json TEXT NOT NULL,
    completed_evidence_ids_json TEXT NOT NULL,
    state_sha256 TEXT NOT NULL CHECK(length(state_sha256) = 64),
    created_at TEXT NOT NULL,
    UNIQUE(analysis_id, stage, revision)
) STRICT;

CREATE INDEX IF NOT EXISTS checkpoint_latest_lookup
ON checkpoints(analysis_id, stage, revision DESC);

CREATE TABLE IF NOT EXISTS exports (
    export_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
    export_type TEXT NOT NULL CHECK(export_type IN ('result_json', 'evidence_markdown')),
    artifact_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(analysis_id, export_type)
) STRICT;
"""


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def build_cache_key(chain_id: int, request: SourceRequest) -> str:
    return canonical_sha256(
        {
            "chain_id": chain_id,
            "request_fingerprint": source_request_fingerprint(request),
        }
    )


class SQLiteStorage:
    def __init__(
        self,
        path: Path,
        *,
        guard: SensitiveDataGuard | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._guard = guard or SensitiveDataGuard()
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._initialize()

    def __enter__(self) -> "SQLiteStorage":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _initialize(self) -> None:
        version = int(self._connection.execute("PRAGMA user_version").fetchone()[0])
        if version not in (0, SCHEMA_VERSION):
            raise ValueError(f"unsupported SQLite schema version: {version}")
        if version == 0:
            with self._connection:
                self._connection.executescript(DDL)
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _assert_chain_id_supported(self, chain_id: int) -> None:
        if chain_id != 0:
            return
        row = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
        ).fetchone()
        table_sql = "" if row is None else str(row["sql"])
        normalized_sql = " ".join(table_sql.lower().split())
        if "check(chain_id = 1)" in normalized_sql:
            raise ValueError(
                "legacy SQLite v1 permits only chain_id=1; use a new database or "
                "an explicitly approved backup-and-migration flow for Bitcoin"
            )

    def integrity_check(self) -> str:
        return str(self._connection.execute("PRAGMA integrity_check").fetchone()[0])

    def backup_to(self, destination: Path) -> None:
        if destination.resolve() == self.path.resolve():
            raise ValueError("backup destination must differ from the source database")
        if destination.exists():
            raise FileExistsError("backup destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(destination) as backup:
            self._connection.backup(backup)
            result = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise sqlite3.DatabaseError("SQLite backup failed integrity_check")

    def record_artifact(self, record: ArtifactRecord) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO artifacts(
                    sha256, byte_length, media_type, relative_path, artifact_kind,
                    redaction_status, license_status, source_id, retrieved_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sha256) DO NOTHING
                """,
                (
                    record.sha256,
                    record.byte_length,
                    record.media_type,
                    record.relative_path,
                    record.artifact_kind,
                    record.redaction_status,
                    record.license_status,
                    record.source_id,
                    _datetime_text(record.retrieved_at),
                    _datetime_text(record.created_at),
                ),
            )
            row = self._connection.execute(
                "SELECT byte_length, relative_path FROM artifacts WHERE sha256 = ?",
                (record.sha256,),
            ).fetchone()
            if (
                row["byte_length"] != record.byte_length
                or row["relative_path"] != record.relative_path
            ):
                raise ValueError("artifact metadata conflicts with an existing hash")

    def get_artifact(self, sha256: str) -> ArtifactRecord | None:
        row = self._connection.execute(
            "SELECT * FROM artifacts WHERE sha256 = ?",
            (sha256,),
        ).fetchone()
        if row is None:
            return None
        return ArtifactRecord(
            sha256=row["sha256"],
            byte_length=row["byte_length"],
            media_type=row["media_type"],
            relative_path=row["relative_path"],
            artifact_kind=row["artifact_kind"],
            redaction_status=row["redaction_status"],
            license_status=row["license_status"],
            source_id=row["source_id"],
            retrieved_at=_parse_datetime(row["retrieved_at"]),
            created_at=_parse_datetime(row["created_at"]),
        )

    def get_run_artifact(
        self,
        analysis_id: str,
        artifact_kind: str,
    ) -> ArtifactRecord | None:
        if artifact_kind == "request":
            row = self._connection.execute(
                """
                SELECT request_artifact_sha256 AS sha256
                FROM analysis_runs
                WHERE analysis_id = ?
                """,
                (analysis_id,),
            ).fetchone()
        elif artifact_kind in {"result_json", "evidence_markdown"}:
            row = self._connection.execute(
                """
                SELECT artifact_sha256 AS sha256
                FROM exports
                WHERE analysis_id = ? AND export_type = ?
                """,
                (analysis_id, artifact_kind),
            ).fetchone()
        else:
            raise ValueError("unsupported run artifact kind")
        if row is None:
            return None
        return self.get_artifact(str(row["sha256"]))

    def finish_run(
        self,
        analysis_id: str,
        status: str,
        *,
        now: datetime | None = None,
    ) -> None:
        if status not in {"failed", "interrupted", "restricted"}:
            raise ValueError("finish_run only accepts non-result terminal statuses")
        timestamp = now or datetime.now(UTC)
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE analysis_runs
                SET status = ?, started_at = COALESCE(started_at, ?),
                    finished_at = ?, updated_at = ?
                WHERE analysis_id = ?
                """,
                (
                    status,
                    _datetime_text(timestamp),
                    _datetime_text(timestamp),
                    _datetime_text(timestamp),
                    analysis_id,
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError("analysis run not found")

    def create_run(
        self,
        request: AnalysisRequest,
        request_artifact: ArtifactRecord,
        *,
        tool_version: str,
        now: datetime | None = None,
    ) -> None:
        run = request.root
        self._assert_chain_id_supported(run.chain_id)
        self.record_artifact(request_artifact)
        timestamp = now or datetime.now(UTC)
        self._guard.check_text(canonical_json(request.to_contract_dict()))
        policy_document = run.source_policy.model_dump(mode="json")
        policy_text = canonical_json(policy_document)
        self._guard.check_text(policy_text)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO analysis_runs(
                    analysis_id, analysis_type, chain_id, fixture_id, status,
                    schema_version, tool_version, request_artifact_sha256,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
                """,
                (
                    run.analysis_id,
                    run.analysis_type,
                    run.chain_id,
                    _missing_to_none(getattr(run, "fixture_id", None)),
                    run.schema_version,
                    tool_version,
                    request_artifact.sha256,
                    _datetime_text(timestamp),
                    _datetime_text(timestamp),
                ),
            )
            self._connection.execute(
                """
                INSERT INTO run_source_policies(
                    analysis_id, rule_status, allowed_source_ids_json,
                    source_order_json, allow_fallback, offline_mode, canonical_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.analysis_id,
                    run.source_policy.rule_status,
                    canonical_json(run.source_policy.allowed_source_ids),
                    canonical_json(run.source_policy.source_order),
                    int(run.source_policy.allow_fallback),
                    int(run.source_policy.offline_mode),
                    hashlib.sha256(policy_text.encode()).hexdigest(),
                ),
            )

    def save_attempts(
        self,
        analysis_id: str,
        request: SourceRequest,
        attempts: Iterable[SourceAttempt],
        *,
        artifact_sha256: str | None = None,
    ) -> tuple[SourceAttempt, ...]:
        request_fingerprint = source_request_fingerprint(request)
        method = request.method
        block_tag = None if request.block_tag is None else str(request.block_tag)
        self._guard.check_text(
            canonical_json(
                {
                    "analysis_id": analysis_id,
                    "capability": request.capability,
                    "method": method,
                    "block_tag": block_tag,
                }
            )
        )
        rows = []
        persisted_attempts: list[SourceAttempt] = []
        offsets: dict[str, int] = {}
        for attempt in attempts:
            if attempt.provider_id not in offsets:
                offsets[attempt.provider_id] = int(
                    self._connection.execute(
                        """
                        SELECT COALESCE(MAX(attempt_number), 0)
                        FROM source_attempts
                        WHERE analysis_id = ? AND request_fingerprint = ?
                          AND provider_id = ?
                        """,
                        (analysis_id, request_fingerprint, attempt.provider_id),
                    ).fetchone()[0]
                )
            persisted_attempt_number = offsets[attempt.provider_id] + attempt.attempt_number
            persisted_attempts.append(replace(attempt, attempt_number=persisted_attempt_number))
            stable_id = canonical_sha256(
                {
                    "analysis_id": analysis_id,
                    "request_fingerprint": request_fingerprint,
                    "provider_id": attempt.provider_id,
                    "attempt_number": persisted_attempt_number,
                }
            )[:24]
            rows.append(
                (
                    f"ATT-{stable_id}",
                    analysis_id,
                    None,
                    attempt.source_id,
                    attempt.provider_id,
                    request.capability,
                    method,
                    request_fingerprint,
                    block_tag,
                    persisted_attempt_number,
                    attempt.outcome,
                    attempt.failure_kind,
                    attempt.status_code,
                    int(attempt.retryable),
                    attempt.wait_seconds,
                    attempt.raw_sha256,
                    _datetime_text(attempt.started_at),
                    _datetime_text(attempt.finished_at),
                    artifact_sha256 if attempt.outcome == "success" else None,
                )
            )
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO source_attempts(
                    source_attempt_id, analysis_id, source_record_id, source_id,
                    provider_id, capability, method, request_fingerprint, block_tag,
                    attempt_number, outcome, failure_kind, http_status, retryable,
                    wait_seconds, raw_sha256, started_at, finished_at, artifact_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return tuple(persisted_attempts)

    def list_source_attempts(self, analysis_id: str) -> tuple[dict[str, object], ...]:
        rows = self._connection.execute(
            """
            SELECT source_attempt_id, source_record_id, source_id, provider_id, capability, method,
                   request_fingerprint, block_tag, attempt_number, outcome,
                   failure_kind, http_status, retryable, wait_seconds, raw_sha256,
                   started_at, finished_at, artifact_sha256
            FROM source_attempts
            WHERE analysis_id = ?
            ORDER BY started_at, provider_id, attempt_number
            """,
            (analysis_id,),
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def put_cache(self, record: CacheRecord) -> None:
        if record.immutability == "immutable" and (
            record.block_tag is None or record.block_tag in {"latest", "pending"}
        ):
            raise ValueError("immutable cache requires a fixed historical block tag")
        if record.immutability != "immutable" and record.expires_at is None:
            raise ValueError("ttl and negative cache entries require expires_at")
        self._guard.check_text(
            canonical_json(
                {
                    "source_id": record.source_id,
                    "provider_id": record.provider_id,
                    "capability": record.capability,
                    "block_tag": record.block_tag,
                    "endpoint_host": record.endpoint_host,
                    "endpoint_path": record.endpoint_path,
                }
            )
        )
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO cache_entries(
                    cache_key, source_id, provider_id, capability, block_tag,
                    artifact_sha256, immutability, created_at, expires_at,
                    endpoint_host, endpoint_path, status_code, media_type,
                    retrieved_at, fallback_from_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO NOTHING
                """,
                (
                    record.cache_key,
                    record.source_id,
                    record.provider_id,
                    record.capability,
                    record.block_tag,
                    record.artifact_sha256,
                    record.immutability,
                    _datetime_text(record.created_at),
                    _datetime_text(record.expires_at),
                    record.endpoint_host,
                    record.endpoint_path,
                    record.status_code,
                    record.media_type,
                    _datetime_text(record.retrieved_at),
                    canonical_json(record.fallback_from),
                ),
            )
            row = self._connection.execute(
                """
                SELECT source_id, provider_id, artifact_sha256
                FROM cache_entries WHERE cache_key = ?
                """,
                (record.cache_key,),
            ).fetchone()
            if (
                row["source_id"] != record.source_id
                or row["provider_id"] != record.provider_id
                or row["artifact_sha256"] != record.artifact_sha256
            ):
                raise ValueError("cache key conflicts with existing provenance")

    def get_cache(
        self,
        cache_key: str,
        *,
        allowed_source_ids: Iterable[str],
        now: datetime | None = None,
    ) -> CacheRecord | None:
        row = self._connection.execute(
            "SELECT * FROM cache_entries WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None or row["source_id"] not in set(allowed_source_ids):
            return None
        expires_at = _parse_datetime(row["expires_at"])
        if expires_at is not None and expires_at <= (now or datetime.now(UTC)):
            return None
        return CacheRecord(
            cache_key=row["cache_key"],
            source_id=row["source_id"],
            provider_id=row["provider_id"],
            capability=row["capability"],
            block_tag=row["block_tag"],
            artifact_sha256=row["artifact_sha256"],
            immutability=row["immutability"],
            created_at=_parse_datetime(row["created_at"]),
            expires_at=expires_at,
            endpoint_host=row["endpoint_host"],
            endpoint_path=row["endpoint_path"],
            status_code=row["status_code"],
            media_type=row["media_type"],
            retrieved_at=_parse_datetime(row["retrieved_at"]),
            fallback_from=tuple(json.loads(row["fallback_from_json"])),
        )

    def save_checkpoint(
        self,
        analysis_id: str,
        stage: str,
        cursor: dict[str, object],
        completed_evidence_ids: Iterable[str],
        *,
        now: datetime | None = None,
    ) -> CheckpointRecord:
        completed = tuple(completed_evidence_ids)
        state = {
            "analysis_id": analysis_id,
            "stage": stage,
            "cursor": cursor,
            "completed_evidence_ids": completed,
        }
        state_text = canonical_json(state)
        self._guard.check_text(state_text)
        revision = int(
            self._connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM checkpoints WHERE analysis_id = ? AND stage = ?
                """,
                (analysis_id, stage),
            ).fetchone()[0]
        )
        state_sha256 = hashlib.sha256(state_text.encode()).hexdigest()
        checkpoint_id = f"CP-{state_sha256[:24]}-{revision}"
        created_at = now or datetime.now(UTC)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO checkpoints(
                    checkpoint_id, analysis_id, stage, revision, cursor_json,
                    completed_evidence_ids_json, state_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    analysis_id,
                    stage,
                    revision,
                    canonical_json(cursor),
                    canonical_json(completed),
                    state_sha256,
                    _datetime_text(created_at),
                ),
            )
        return CheckpointRecord(
            checkpoint_id=checkpoint_id,
            analysis_id=analysis_id,
            stage=stage,
            revision=revision,
            cursor=cursor,
            completed_evidence_ids=completed,
            state_sha256=state_sha256,
            created_at=created_at,
        )

    def latest_checkpoint(self, analysis_id: str, stage: str) -> CheckpointRecord | None:
        row = self._connection.execute(
            """
            SELECT * FROM checkpoints
            WHERE analysis_id = ? AND stage = ?
            ORDER BY revision DESC LIMIT 1
            """,
            (analysis_id, stage),
        ).fetchone()
        if row is None:
            return None
        return CheckpointRecord(
            checkpoint_id=row["checkpoint_id"],
            analysis_id=row["analysis_id"],
            stage=row["stage"],
            revision=row["revision"],
            cursor=json.loads(row["cursor_json"]),
            completed_evidence_ids=tuple(json.loads(row["completed_evidence_ids_json"])),
            state_sha256=row["state_sha256"],
            created_at=_parse_datetime(row["created_at"]),
        )

    def save_result(self, result: AnalysisResult, *, now: datetime | None = None) -> None:
        document = result.root
        created_at = now or datetime.now(UTC)
        self._guard.check_text(canonical_json(result.to_contract_dict()))
        with self._connection:
            self._save_sources(document)
            self._save_result_items(document, created_at)
            self._save_evidence(document)
            self._save_result_evidence_links(document, created_at)
            self._connection.execute(
                """
                UPDATE analysis_runs
                SET status = ?, started_at = ?, finished_at = ?, updated_at = ?
                WHERE analysis_id = ?
                """,
                (
                    document.status,
                    _datetime_text(document.run.started_at),
                    _datetime_text(document.run.finished_at),
                    _datetime_text(created_at),
                    document.analysis_id,
                ),
            )

    def _save_sources(self, document: AnalysisResultBase) -> None:
        for source in document.sources:
            self._connection.execute(
                """
                INSERT INTO source_records(
                    source_record_id, analysis_id, source_id, provider_id, role,
                    required, capability, endpoint_host, retrieved_at, fallback_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.source_record_id,
                    document.analysis_id,
                    source.source_id,
                    source.provider_id,
                    source.role,
                    int(source.required),
                    source.capability,
                    source.endpoint_host,
                    _datetime_text(source.retrieved_at),
                    _missing_to_none(source.fallback_from),
                ),
            )

    def _save_result_items(
        self,
        document: AnalysisResultBase,
        created_at: datetime,
    ) -> None:
        for item in document.results:
            value_text = canonical_json(item.value)
            self._connection.execute(
                """
                INSERT INTO results(
                    result_id, analysis_id, result_type, classification,
                    requirement_ids_json, fixture_requirement_ids_json,
                    value_json, value_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.result_id,
                    document.analysis_id,
                    item.result_type,
                    item.classification,
                    canonical_json(item.tool_requirement_ids),
                    canonical_json(item.fixture_requirement_ids),
                    value_text,
                    hashlib.sha256(value_text.encode()).hexdigest(),
                    _datetime_text(created_at),
                ),
            )

    def _save_evidence(self, document: AnalysisResultBase) -> None:
        for evidence in document.evidence:
            self._connection.execute(
                """
                INSERT INTO evidence_records(
                    evidence_id, analysis_id, evidence_type, source_id,
                    source_record_id, method, locator_json, decoded_json,
                    artifact_sha256, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    document.analysis_id,
                    evidence.evidence_type,
                    evidence.source_id,
                    evidence.source_record_ref,
                    evidence.method,
                    canonical_json(evidence.locator.model_dump(mode="json")),
                    canonical_json(evidence.decoded),
                    _missing_to_none(evidence.raw_artifact.sha256),
                    _datetime_text(evidence.retrieved_at),
                ),
            )

    def _save_result_evidence_links(
        self,
        document: AnalysisResultBase,
        created_at: datetime,
    ) -> None:
        for item in document.results:
            self._connection.executemany(
                """
                INSERT INTO result_evidence_links(
                    result_id, evidence_id, analysis_id, role, created_at
                ) VALUES (?, ?, ?, 'scoring', ?)
                """,
                (
                    (
                        item.result_id,
                        evidence_id,
                        document.analysis_id,
                        _datetime_text(created_at),
                    )
                    for evidence_id in item.evidence_refs
                ),
            )

    def record_export(self, record: ExportRecord) -> None:
        self.record_artifact(record.artifact)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO exports(
                    export_id, analysis_id, export_type, artifact_sha256,
                    schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(export_id) DO NOTHING
                """,
                (
                    record.export_id,
                    record.analysis_id,
                    record.export_type,
                    record.artifact.sha256,
                    record.schema_version,
                    _datetime_text(record.created_at),
                ),
            )
            row = self._connection.execute(
                """
                SELECT artifact_sha256, schema_version
                FROM exports WHERE export_id = ?
                """,
                (record.export_id,),
            ).fetchone()
            if (
                row["artifact_sha256"] != record.artifact.sha256
                or row["schema_version"] != record.schema_version
            ):
                raise ValueError("export ID conflicts with an existing artifact")

    def link_result_evidence(
        self,
        *,
        analysis_id: str,
        result_id: str,
        evidence_id: str,
        role: str,
        created_at: datetime,
    ) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO result_evidence_links(
                    result_id, evidence_id, analysis_id, role, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    evidence_id,
                    analysis_id,
                    role,
                    _datetime_text(created_at),
                ),
            )

    def count(self, table: str) -> int:
        allowed = {
            "analysis_runs",
            "run_source_policies",
            "source_attempts",
            "artifacts",
            "cache_entries",
            "source_records",
            "results",
            "evidence_records",
            "result_evidence_links",
            "checkpoints",
            "exports",
        }
        if table not in allowed:
            raise ValueError("unsupported table name")
        return int(self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _datetime_text(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _missing_to_none(value: object) -> object | None:
    if value is None or value is MISSING:
        return None
    return value
