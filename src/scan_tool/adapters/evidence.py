"""Local in-process Evidence Worker adapter over the approved CliRuntime."""

import asyncio
import re
from pathlib import Path
from threading import Lock

from scan_tool.application.cli_runtime import (
    AUTH_REPLAY_STAGE,
    BRIDGE_TRANSFER_REPLAY_STAGE,
    DEX_REPLAY_STAGE,
    FREEZE_REPLAY_STAGE,
    CliRuntime,
)
from scan_tool.domain.analysis_request import (
    AnalysisRequest,
    AnalysisType,
)
from scan_tool.ports.evidence import EvidenceAdapterResponse

_SAFE_WORKSPACE_KEY = re.compile(r"^PROB-[A-Z0-9][A-Z0-9-]{1,63}(?:/JOB-[A-Z0-9][A-Z0-9-]{2,63})?$")


class InProcessEvidenceWorker:
    """Execute each problem in an isolated local runtime workspace."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._workspace_locks: dict[str, Lock] = {}
        self._workspace_locks_guard = Lock()

    async def analyze(
        self,
        *,
        workspace_key: str,
        request: AnalysisRequest,
        replay_body: bytes,
        replay_sha256: str,
    ) -> EvidenceAdapterResponse:
        if _SAFE_WORKSPACE_KEY.fullmatch(workspace_key) is None:
            raise ValueError("workspace_key is invalid")
        return await asyncio.to_thread(
            self._analyze_sync,
            workspace_key,
            request,
            replay_body,
            replay_sha256,
        )

    def _analyze_sync(
        self,
        workspace_key: str,
        request: AnalysisRequest,
        replay_body: bytes,
        replay_sha256: str,
    ) -> EvidenceAdapterResponse:
        with self._workspace_lock(workspace_key):
            return self._analyze_locked(
                workspace_key,
                request,
                replay_body,
                replay_sha256,
            )

    def _analyze_locked(
        self,
        workspace_key: str,
        request: AnalysisRequest,
        replay_body: bytes,
        replay_sha256: str,
    ) -> EvidenceAdapterResponse:
        workspace = self._root.joinpath(*workspace_key.split("/"))
        with CliRuntime.open(workspace) as runtime:
            existing_request = runtime.load_request(request.root.analysis_id)
            if existing_request is None:
                runtime.register_request(request)
            elif existing_request.to_contract_dict() != request.to_contract_dict():
                raise ValueError("analysis_id conflicts with another request")
            else:
                existing_result = runtime.load_result(request.root.analysis_id)
                if existing_result is not None:
                    request_artifact = runtime.storage.get_run_artifact(
                        request.root.analysis_id,
                        "request",
                    )
                    if request_artifact is None:
                        raise ValueError("existing run is missing its request artifact")
                    return EvidenceAdapterResponse(
                        result=existing_result.result,
                        export_uris=existing_result.export_uris,
                        request_artifact_uri=request_artifact.uri,
                        replay_artifact_uri=self._replay_artifact_uri(
                            runtime,
                            request,
                            expected_sha256=replay_sha256,
                        ),
                        reused=True,
                    )

            result = runtime.execute_analysis(
                request,
                replay_body=replay_body,
                expected_replay_sha256=replay_sha256,
            )
            stored = runtime.save_result(request, result)
            request_artifact = runtime.storage.get_run_artifact(
                request.root.analysis_id,
                "request",
            )
            if request_artifact is None:
                raise ValueError("analysis run is missing its request artifact")
            return EvidenceAdapterResponse(
                result=stored.result,
                export_uris=stored.export_uris,
                request_artifact_uri=request_artifact.uri,
                replay_artifact_uri=self._replay_artifact_uri(
                    runtime,
                    request,
                    expected_sha256=replay_sha256,
                ),
                reused=False,
            )

    def _workspace_lock(self, workspace_key: str) -> Lock:
        with self._workspace_locks_guard:
            return self._workspace_locks.setdefault(workspace_key, Lock())

    def _replay_artifact_uri(
        self,
        runtime: CliRuntime,
        request: AnalysisRequest,
        *,
        expected_sha256: str,
    ) -> str:
        stages = {
            AnalysisType.DEX_SWAP: DEX_REPLAY_STAGE,
            AnalysisType.AUTH_CONSUMPTION: AUTH_REPLAY_STAGE,
            AnalysisType.ADDRESS_FREEZE: FREEZE_REPLAY_STAGE,
            AnalysisType.BRIDGE_TRANSFER: BRIDGE_TRANSFER_REPLAY_STAGE,
        }
        checkpoint = runtime.storage.latest_checkpoint(
            request.root.analysis_id,
            stages[request.root.analysis_type],
        )
        if checkpoint is None:
            raise ValueError("analysis run is missing its replay checkpoint")
        replay_sha256 = checkpoint.cursor.get("raw_artifact_sha256")
        if not isinstance(replay_sha256, str):
            raise ValueError("analysis replay checkpoint is invalid")
        if replay_sha256 != expected_sha256:
            raise ValueError("analysis replay differs from the approved input")
        artifact = runtime.storage.get_artifact(replay_sha256)
        if artifact is None:
            raise ValueError("analysis replay artifact is unavailable")
        return artifact.uri
