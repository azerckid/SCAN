"""In-process evidence analysis port for OPS-IMPL-05."""

from dataclasses import dataclass
from typing import Protocol

from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult


@dataclass(frozen=True, slots=True)
class EvidenceAdapterResponse:
    result: AnalysisResult
    export_uris: tuple[str, str]
    request_artifact_uri: str
    replay_artifact_uri: str
    reused: bool


class EvidenceWorkerPort(Protocol):
    async def analyze(
        self,
        *,
        workspace_key: str,
        request: AnalysisRequest,
        replay_body: bytes,
        replay_sha256: str,
    ) -> EvidenceAdapterResponse:
        """Run one approved Analysis I/O request without parsing CLI output."""
        ...
