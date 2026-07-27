"""CLI composition helpers over the approved storage and Analysis I/O contracts."""

import json
from dataclasses import dataclass
from pathlib import Path

from scan_tool import __version__
from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage, canonical_json
from scan_tool.application.export import ResultExporter
from scan_tool.domain import (
    validate_analysis_pair,
    validate_analysis_request,
    validate_analysis_result,
)
from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult


class AnalysisUnavailable(RuntimeError):
    """Raised while vertical analyzers remain outside TASK-005."""


@dataclass(frozen=True, slots=True)
class StoredResult:
    result: AnalysisResult
    export_uris: tuple[str, str]


@dataclass(slots=True)
class CliRuntime:
    root: Path
    storage: SQLiteStorage
    artifacts: ArtifactStore

    @classmethod
    def open(cls, root: Path) -> "CliRuntime":
        root.mkdir(parents=True, exist_ok=True)
        return cls(
            root=root,
            storage=SQLiteStorage(root / "scan.sqlite3"),
            artifacts=ArtifactStore(root),
        )

    def close(self) -> None:
        self.storage.close()

    def __enter__(self) -> "CliRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def register_request(self, request: AnalysisRequest) -> None:
        body = (canonical_json(request.to_contract_dict()) + "\n").encode()
        artifact = self.artifacts.write(
            body,
            media_type="application/json",
            artifact_kind="request",
        )
        self.storage.create_run(
            request,
            artifact,
            tool_version=__version__,
        )

    def load_request(self, analysis_id: str) -> AnalysisRequest | None:
        artifact = self.storage.get_run_artifact(analysis_id, "request")
        if artifact is None:
            return None
        return validate_analysis_request(json.loads(self.artifacts.read(artifact)))

    def save_result(
        self,
        request: AnalysisRequest,
        result: AnalysisResult,
    ) -> StoredResult:
        validate_analysis_pair(request.to_contract_dict(), result.to_contract_dict())
        self.storage.save_result(result)
        bundle = ResultExporter(self.artifacts, self.storage).export(result)
        return StoredResult(
            result=result,
            export_uris=(bundle.json_export.artifact.uri, bundle.markdown_export.artifact.uri),
        )

    def load_result(self, analysis_id: str) -> StoredResult | None:
        json_artifact = self.storage.get_run_artifact(analysis_id, "result_json")
        markdown_artifact = self.storage.get_run_artifact(analysis_id, "evidence_markdown")
        if json_artifact is None or markdown_artifact is None:
            return None
        return StoredResult(
            result=validate_analysis_result(json.loads(self.artifacts.read(json_artifact))),
            export_uris=(json_artifact.uri, markdown_artifact.uri),
        )


def execute_analysis(_: AnalysisRequest) -> AnalysisResult:
    raise AnalysisUnavailable(
        "The selected vertical analyzer is not implemented; continue with TASK-006, "
        "TASK-007, or TASK-008."
    )
