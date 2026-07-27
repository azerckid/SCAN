"""Cache-first source execution and append-only checkpoint helpers."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage, build_cache_key
from scan_tool.application.source_orchestration import SourceOrchestrator
from scan_tool.domain.analysis_request import SourcePolicy
from scan_tool.domain.source import (
    SourceExecution,
    SourcePayload,
    SourceRequest,
    SourceResponse,
    source_request_fingerprint,
)
from scan_tool.domain.storage import CacheRecord, CheckpointRecord

type Clock = Callable[[], datetime]
type StageOperation = Callable[[], Awaitable[tuple[dict[str, object], tuple[str, ...]]]]


class CachedSourceExecutor:
    """Read immutable cache before invoking the TASK-003 source orchestrator."""

    def __init__(
        self,
        orchestrator: SourceOrchestrator,
        storage: SQLiteStorage,
        artifacts: ArtifactStore,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._storage = storage
        self._artifacts = artifacts
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(
        self,
        *,
        analysis_id: str,
        chain_id: int,
        request: SourceRequest,
        policy: SourcePolicy,
    ) -> SourceExecution:
        cache_key = build_cache_key(chain_id, request)
        cached = self._storage.get_cache(
            cache_key,
            allowed_source_ids=policy.allowed_source_ids,
            now=self._clock(),
        )
        if cached is not None:
            return self._cached_execution(cached, request)

        execution = await self._orchestrator.execute(request, policy)
        if not execution.succeeded:
            persisted_attempts = self._storage.save_attempts(
                analysis_id,
                request,
                execution.attempts,
            )
            return SourceExecution(
                response=None,
                attempts=persisted_attempts,
                error=execution.error,
            )

        response = execution.response
        assert response is not None
        return self._persist_success(
            analysis_id=analysis_id,
            request=request,
            cache_key=cache_key,
            response=response,
            execution=execution,
        )

    def _cached_execution(
        self,
        cached: CacheRecord,
        request: SourceRequest,
    ) -> SourceExecution:
        artifact = self._storage.get_artifact(cached.artifact_sha256)
        if artifact is None:
            raise ValueError("cache entry references a missing artifact")
        payload = SourcePayload(
            raw_bytes=self._artifacts.read(artifact),
            status_code=cached.status_code,
            media_type=cached.media_type,
            endpoint_host=cached.endpoint_host,
            endpoint_path=cached.endpoint_path,
            retrieved_at=cached.retrieved_at,
        )
        return SourceExecution(
            response=SourceResponse(
                source_id=cached.source_id,
                provider_id=cached.provider_id,
                request_fingerprint=source_request_fingerprint(request),
                payload=payload,
                attempts=(),
                fallback_from=cached.fallback_from,
                cache_status="hit",
            ),
            attempts=(),
            error=None,
        )

    def _persist_success(
        self,
        *,
        analysis_id: str,
        request: SourceRequest,
        cache_key: str,
        response: SourceResponse,
        execution: SourceExecution,
    ) -> SourceExecution:
        artifact = self._artifacts.write(
            response.payload.raw_bytes,
            media_type=response.payload.media_type or "application/octet-stream",
            artifact_kind="raw_response",
            source_id=response.source_id,
            retrieved_at=response.payload.retrieved_at,
        )
        self._storage.record_artifact(artifact)
        persisted_attempts = self._storage.save_attempts(
            analysis_id,
            request,
            execution.attempts,
            artifact_sha256=artifact.sha256,
        )

        block_tag = None if request.block_tag is None else str(request.block_tag)
        if block_tag not in (None, "latest", "pending"):
            self._storage.put_cache(
                CacheRecord(
                    cache_key=cache_key,
                    source_id=response.source_id,
                    provider_id=response.provider_id,
                    capability=request.capability,
                    block_tag=block_tag,
                    artifact_sha256=artifact.sha256,
                    immutability="immutable",
                    created_at=self._clock(),
                    expires_at=None,
                    endpoint_host=response.payload.endpoint_host,
                    endpoint_path=response.payload.endpoint_path,
                    status_code=response.payload.status_code,
                    media_type=response.payload.media_type,
                    retrieved_at=response.payload.retrieved_at,
                    fallback_from=response.fallback_from,
                )
            )

        return SourceExecution(
            response=replace(
                response,
                attempts=persisted_attempts,
                cache_status="miss",
            ),
            attempts=persisted_attempts,
            error=None,
        )


@dataclass(frozen=True, slots=True)
class StageExecution:
    checkpoint: CheckpointRecord
    resumed: bool


class CheckpointRunner:
    """Run a completed stage once and reuse its latest checkpoint on resume."""

    def __init__(self, storage: SQLiteStorage) -> None:
        self._storage = storage

    async def run_once(
        self,
        *,
        analysis_id: str,
        stage: str,
        operation: StageOperation,
    ) -> StageExecution:
        checkpoint = self._storage.latest_checkpoint(analysis_id, stage)
        if checkpoint is not None:
            return StageExecution(checkpoint=checkpoint, resumed=True)
        cursor, completed_evidence_ids = await operation()
        checkpoint = self._storage.save_checkpoint(
            analysis_id,
            stage,
            cursor,
            completed_evidence_ids,
        )
        return StageExecution(checkpoint=checkpoint, resumed=False)
