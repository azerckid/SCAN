"""Normalize, persist, and hand off approved input evidence."""

from dataclasses import dataclass, field, replace
from pathlib import Path

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.input_source import ProvidedArtifactImporter
from scan_tool.application.evidence_worker import ApprovedReplay
from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.input_source import (
    ArtifactFormat,
    ChainScope,
    InputEvidenceEnvelope,
    InputFailureKind,
    InputMode,
    InputNormalizationError,
    NormalizedEvidenceBundle,
    require_chain_scope,
)
from scan_tool.domain.storage import ArtifactRecord
from scan_tool.ports.planner import ArtifactMetadataRecorder


@dataclass(frozen=True, slots=True)
class PreparedInputEvidence:
    """Validated input whose bytes have not yet crossed the persistence boundary."""

    bundle: NormalizedEvidenceBundle
    raw_bytes: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class PersistedInputEvidence:
    envelope: InputEvidenceEnvelope
    artifact: ArtifactRecord


class InputEvidenceService:
    """Apply input bounds before persistence and build an approved replay."""

    def __init__(
        self,
        *,
        importer: ProvidedArtifactImporter | None = None,
        guard: SensitiveDataGuard | None = None,
    ) -> None:
        self._importer = importer or ProvidedArtifactImporter()
        self._guard = guard or SensitiveDataGuard()

    def prepare(
        self,
        raw_bytes: bytes,
        *,
        input_mode: InputMode,
        chain_scope: ChainScope,
        artifact_format: ArtifactFormat,
    ) -> PreparedInputEvidence:
        if input_mode is InputMode.CONTEST_RPC:
            raise InputNormalizationError(
                InputFailureKind.UNSUPPORTED_INPUT,
                "contest RPC input requires a normalized source payload",
            )
        self._guard.check_bytes(raw_bytes)
        bundle = self._importer.import_bytes(
            raw_bytes,
            artifact_format=artifact_format,
            chain_scope=chain_scope,
        )
        if input_mode is InputMode.EXTERNAL_RPC:
            bundle = replace(
                bundle,
                input_mode=InputMode.EXTERNAL_RPC,
                source_id="DS-EVM-RPC-ARCHIVE",
                provider_id="reviewed-replay",
            )
        return PreparedInputEvidence(bundle=bundle, raw_bytes=raw_bytes)

    def persist(
        self,
        prepared: PreparedInputEvidence,
        *,
        artifacts: ArtifactStore,
        storage: ArtifactMetadataRecorder,
    ) -> PersistedInputEvidence:
        artifact = artifacts.write(
            prepared.raw_bytes,
            media_type=prepared.bundle.media_type,
            artifact_kind="input_evidence",
            redaction_status="reviewed",
            license_status="reviewed",
            source_id=prepared.bundle.source_id,
            retrieved_at=prepared.bundle.observed_at,
        )
        if (
            artifact.sha256 != prepared.bundle.raw_sha256
            or artifact.byte_length != prepared.bundle.byte_length
        ):
            raise ValueError("persisted input does not match normalized provenance")
        storage.record_artifact(artifact)
        return PersistedInputEvidence(
            envelope=InputEvidenceEnvelope(
                bundle=prepared.bundle,
                raw_artifact_uri=artifact.uri,
            ),
            artifact=artifact,
        )

    @staticmethod
    def approved_replay(
        persisted: PersistedInputEvidence,
        *,
        artifacts: ArtifactStore,
        expected_chain_scope: ChainScope,
    ) -> ApprovedReplay:
        require_chain_scope(persisted.envelope.bundle, expected_chain_scope)
        if persisted.artifact.uri != persisted.envelope.raw_artifact_uri:
            raise ValueError("input artifact does not match its envelope")
        body = artifacts.read(persisted.artifact)
        return ApprovedReplay(
            body=body,
            sha256=persisted.envelope.bundle.raw_sha256,
        )


def infer_artifact_format(path: Path) -> ArtifactFormat:
    """Infer only the three explicitly supported artifact suffixes."""
    suffixes = {
        ".json": ArtifactFormat.JSON,
        ".jsonl": ArtifactFormat.JSONL,
        ".csv": ArtifactFormat.CSV,
    }
    try:
        return suffixes[path.suffix.lower()]
    except KeyError as error:
        raise InputNormalizationError(
            InputFailureKind.UNSUPPORTED_INPUT,
            "provided artifact format must be specified",
        ) from error
