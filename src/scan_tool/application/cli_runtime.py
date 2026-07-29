"""CLI composition helpers over the approved storage and Analysis I/O contracts."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from scan_tool import __version__
from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage, canonical_json
from scan_tool.application.export import ResultExporter
from scan_tool.domain import (
    validate_analysis_pair,
    validate_analysis_request,
    validate_analysis_result,
)
from scan_tool.domain.analysis_request import (
    AnalysisRequest,
    AuthAnalysisRequest,
    DexAnalysisRequest,
    EvmCoreAnalysisRequest,
    EvmSpecialAnalysisRequest,
    FlowPathAnalysisRequest,
    FreezeAnalysisRequest,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.auth import AuthReplay
from scan_tool.domain.dex import DexReplay
from scan_tool.domain.evm_core import EvmCoreReplay
from scan_tool.domain.evm_special import EvmSpecialReplay
from scan_tool.domain.flow_path import FlowPathReplay
from scan_tool.domain.freeze import FreezeReplay
from scan_tool.slices.auth import analyze_auth_replay
from scan_tool.slices.dex import analyze_dex_replay
from scan_tool.slices.evm_core import analyze_evm_core_replay
from scan_tool.slices.evm_special import analyze_evm_special_replay
from scan_tool.slices.flow_path import analyze_flow_path_replay
from scan_tool.slices.freeze import analyze_freeze_replay

DEX_REPLAY_STAGE = "dex_replay_loaded"
AUTH_REPLAY_STAGE = "auth_replay_loaded"
FREEZE_REPLAY_STAGE = "freeze_replay_loaded"
EVM_CORE_REPLAY_STAGE = "evm_core_replay_loaded"
EVM_SPECIAL_REPLAY_STAGE = "evm_special_replay_loaded"
FLOW_PATH_REPLAY_STAGE = "flow_path_replay_loaded"


class AnalysisUnavailable(RuntimeError):
    """Raised when the selected vertical slice lacks an approved execution input."""


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

    def execute_analysis(
        self,
        request: AnalysisRequest,
        *,
        replay_path: Path | None = None,
        replay_body: bytes | None = None,
        expected_replay_sha256: str | None = None,
    ) -> AnalysisResult:
        document = request.root
        if isinstance(document, DexAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=DEX_REPLAY_STAGE,
                replay_model=DexReplay,
                analysis_label="DEX",
            )
            return analyze_dex_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        if isinstance(document, AuthAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=AUTH_REPLAY_STAGE,
                replay_model=AuthReplay,
                analysis_label="AUTH",
            )
            return analyze_auth_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        if isinstance(document, FreezeAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=FREEZE_REPLAY_STAGE,
                replay_model=FreezeReplay,
                analysis_label="FREEZE",
            )
            return analyze_freeze_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        if isinstance(document, EvmCoreAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=EVM_CORE_REPLAY_STAGE,
                replay_model=EvmCoreReplay,
                analysis_label="EVM Core",
            )
            return analyze_evm_core_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        if isinstance(document, EvmSpecialAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=EVM_SPECIAL_REPLAY_STAGE,
                replay_model=EvmSpecialReplay,
                analysis_label="EVM Special",
            )
            return analyze_evm_special_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        if isinstance(document, FlowPathAnalysisRequest):
            replay_body, checkpoint_id, resumed = self._load_replay(
                document.analysis_id,
                replay_path,
                replay_body,
                expected_replay_sha256,
                stage=FLOW_PATH_REPLAY_STAGE,
                replay_model=FlowPathReplay,
                analysis_label="Flow Path",
            )
            return analyze_flow_path_replay(
                document,
                replay_body,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            )
        raise AnalysisUnavailable("The selected vertical analyzer is not implemented.")

    def _load_replay(
        self,
        analysis_id: str,
        replay_path: Path | None,
        replay_body: bytes | None,
        expected_replay_sha256: str | None,
        *,
        stage: str,
        replay_model: (
            type[DexReplay]
            | type[AuthReplay]
            | type[FreezeReplay]
            | type[EvmCoreReplay]
            | type[EvmSpecialReplay]
            | type[FlowPathReplay]
        ),
        analysis_label: str,
    ) -> tuple[bytes, str | None, bool]:
        checkpoint = self.storage.latest_checkpoint(analysis_id, stage)
        if checkpoint is not None:
            raw_sha256 = checkpoint.cursor.get("raw_artifact_sha256")
            if not isinstance(raw_sha256, str):
                raise AnalysisUnavailable("The saved replay checkpoint is invalid.")
            if expected_replay_sha256 is not None and raw_sha256 != expected_replay_sha256:
                raise AnalysisUnavailable("The saved replay does not match the approved input.")
            artifact = self.storage.get_artifact(raw_sha256)
            if artifact is None:
                raise AnalysisUnavailable("The saved replay artifact is unavailable.")
            return self.artifacts.read(artifact), checkpoint.checkpoint_id, True

        if replay_path is not None and replay_body is not None:
            raise AnalysisUnavailable("Replay path and replay bytes cannot be used together.")
        if replay_body is None and replay_path is None:
            raise AnalysisUnavailable(
                f"{analysis_label} analysis requires --evidence RAW_REPLAY.json in offline mode."
            )
        if replay_body is None:
            if replay_path is None:
                raise AnalysisUnavailable(
                    f"The {analysis_label} replay evidence file is unavailable."
                )
            try:
                replay_body = replay_path.read_bytes()
            except OSError as error:
                raise AnalysisUnavailable(
                    f"The {analysis_label} replay evidence file is unavailable."
                ) from error
        if (
            expected_replay_sha256 is not None
            and hashlib.sha256(replay_body).hexdigest() != expected_replay_sha256
        ):
            raise AnalysisUnavailable("The replay evidence does not match the approved input.")
        try:
            replay_model.model_validate_json(replay_body)
        except ValidationError:
            return replay_body, None, False
        artifact = self.artifacts.write(
            replay_body,
            media_type="application/json",
            artifact_kind=f"{analysis_label.lower()}_replay",
            redaction_status="reviewed",
            license_status="reviewed",
        )
        self.storage.record_artifact(artifact)
        checkpoint = self.storage.save_checkpoint(
            analysis_id,
            stage,
            {"raw_artifact_sha256": artifact.sha256},
            (),
        )
        return replay_body, checkpoint.checkpoint_id, False
