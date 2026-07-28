"""AI planner and raw-output persistence ports."""

from typing import Protocol

from scan_tool.domain.operations import AdapterKind
from scan_tool.domain.planning import PlannerAdapterResponse, PlannerContext
from scan_tool.domain.storage import ArtifactRecord


class PlannerAdapter(Protocol):
    adapter_kind: AdapterKind
    provider_id: str
    model_id: str

    async def plan(self, context: PlannerContext) -> PlannerAdapterResponse:
        """Produce one structured method hypothesis without executing evidence tools."""
        ...


class PlannerArtifactWriter(Protocol):
    def write(
        self,
        body: bytes,
        *,
        media_type: str,
        artifact_kind: str,
        redaction_status: str = "not_required",
        license_status: str = "unknown",
        source_id: str | None = None,
    ) -> ArtifactRecord:
        """Persist secret-checked raw planner bytes by content hash."""
        ...


class ArtifactMetadataRecorder(Protocol):
    def record_artifact(self, record: ArtifactRecord) -> None:
        """Persist immutable artifact metadata."""
        ...
