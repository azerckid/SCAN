"""Immutable records shared by local storage, artifact, and export services."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    sha256: str
    byte_length: int
    media_type: str
    relative_path: str
    artifact_kind: str
    redaction_status: str
    license_status: str
    created_at: datetime
    source_id: str | None = None
    retrieved_at: datetime | None = None

    @property
    def uri(self) -> str:
        return f"artifact://sha256/{self.sha256}"


@dataclass(frozen=True, slots=True)
class CacheRecord:
    cache_key: str
    source_id: str
    provider_id: str
    capability: str
    block_tag: str | None
    artifact_sha256: str
    immutability: str
    created_at: datetime
    expires_at: datetime | None
    endpoint_host: str
    endpoint_path: str
    status_code: int
    media_type: str | None
    retrieved_at: datetime
    fallback_from: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    checkpoint_id: str
    analysis_id: str
    stage: str
    revision: int
    cursor: dict[str, object]
    completed_evidence_ids: tuple[str, ...]
    state_sha256: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExportRecord:
    export_id: str
    analysis_id: str
    export_type: str
    artifact: ArtifactRecord
    schema_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExportBundle:
    json_export: ExportRecord
    markdown_export: ExportRecord
    markdown_text: str
