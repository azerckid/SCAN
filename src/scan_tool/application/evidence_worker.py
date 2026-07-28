"""Operations Evidence Worker orchestration for OPS-IMPL-05."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.application.scheduler import WorkerOutcome
from scan_tool.application.security import SensitiveDataError, SensitiveDataGuard
from scan_tool.domain import validate_analysis_pair
from scan_tool.domain.analysis_request import AnalysisRequest, RuleStatus
from scan_tool.domain.analysis_result import AnalysisResult, AnalysisStatus
from scan_tool.domain.operations import (
    ActorType,
    CompetitionManifest,
    CompetitionStatus,
    JobRecord,
    JobRole,
    JobStatus,
    OperationError,
    OperationErrorCode,
    OperationErrorStage,
    OperationEvent,
    PlanHypothesis,
    PlanStatus,
    ProblemRecord,
    ProblemStatus,
)
from scan_tool.ports.evidence import EvidenceAdapterResponse, EvidenceWorkerPort

type Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class ApprovedReplay:
    body: bytes
    sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceWorkerCommand:
    manifest: CompetitionManifest
    problem: ProblemRecord
    plan: PlanHypothesis
    job: JobRecord
    request: AnalysisRequest
    approved_replay: ApprovedReplay
    worker_id: str
    event_id: str
    error_id: str


@dataclass(frozen=True, slots=True)
class EvidenceWorkerExecution:
    worker_outcome: WorkerOutcome
    result: AnalysisResult | None
    event: OperationEvent
    error: OperationError | None
    export_uris: tuple[str, str]
    request_artifact_uri: str | None
    replay_artifact_uri: str | None
    adapter_called: bool
    reused: bool


class EvidenceWorkerService:
    """Validate operations scope before running one approved analysis request."""

    def __init__(
        self,
        adapter: EvidenceWorkerPort,
        *,
        guard: SensitiveDataGuard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._adapter = adapter
        self._guard = guard or SensitiveDataGuard()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, command: EvidenceWorkerCommand) -> EvidenceWorkerExecution:
        policy_error = self._policy_error(command)
        if policy_error is not None:
            return self._blocked(command, policy_error)
        try:
            self._validate_replay(command.approved_replay)
        except (ValueError, SensitiveDataError):
            return self._failed(command, "approved_replay_rejected", adapter_called=False)

        try:
            response = await self._adapter.analyze(
                workspace_key=command.problem.problem_id,
                request=command.request,
                replay_body=command.approved_replay.body,
                replay_sha256=command.approved_replay.sha256,
            )
        except Exception:
            return self._failed(command, "analysis_adapter_failed", adapter_called=True)
        try:
            self._validate_response(command, response)
        except Exception:
            return self._failed(command, "analysis_response_rejected", adapter_called=True)
        return self._completed(command, response)

    def _policy_error(
        self,
        command: EvidenceWorkerCommand,
    ) -> OperationErrorCode | None:
        request = command.request.root
        if command.manifest.status is not CompetitionStatus.ACTIVE:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.manifest.competition_id != command.problem.competition_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.status not in {
            ProblemStatus.QUEUED,
            ProblemStatus.RUNNING,
            ProblemStatus.PARTIAL,
        }:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.problem_id != command.plan.problem_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.active_plan_id != command.plan.plan_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.problem_id != command.job.problem_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.plan.plan_id != command.job.plan_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.plan.status is not PlanStatus.APPROVED:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.job.role is not JobRole.EVIDENCE:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.job.analysis_id is MISSING:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.job.analysis_id != request.analysis_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if (
            command.job.assigned_worker_id is not MISSING
            and command.job.assigned_worker_id != command.worker_id
        ):
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        leaf = next(
            (
                item
                for item in command.plan.leaf_job_specs
                if item.leaf_job_id == command.job.job_id
            ),
            None,
        )
        if (
            leaf is None
            or leaf.role is not JobRole.EVIDENCE
            or leaf.analysis_type is not request.analysis_type
            or leaf.inputs_projection != request.inputs.model_dump(mode="json")
        ):
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if request.source_policy.rule_status is RuleStatus.RESTRICTED:
            return OperationErrorCode.RULE_RESTRICTED
        if not request.source_policy.offline_mode:
            return OperationErrorCode.RULE_RESTRICTED
        return None

    def _validate_replay(self, replay: ApprovedReplay) -> None:
        if len(replay.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in replay.sha256
        ):
            raise ValueError("approved replay sha256 is invalid")
        if hashlib.sha256(replay.body).hexdigest() != replay.sha256:
            raise ValueError("approved replay hash mismatch")
        self._guard.check_bytes(replay.body)

    def _validate_response(
        self,
        command: EvidenceWorkerCommand,
        response: EvidenceAdapterResponse,
    ) -> None:
        request = command.request.root
        result = response.result.root
        validate_analysis_pair(
            command.request.to_contract_dict(),
            response.result.to_contract_dict(),
        )
        if result.analysis_id != request.analysis_id:
            raise ValueError("evidence adapter returned another analysis_id")
        if result.analysis_type is not request.analysis_type:
            raise ValueError("evidence adapter returned another analysis_type")
        if result.chain_id != request.chain_id:
            raise ValueError("evidence adapter returned another chain_id")
        result_by_id = {item.result_id for item in result.results}
        evidence_by_id = {item.evidence_id for item in result.evidence}
        source_by_id = {item.source_record_id for item in result.sources}
        if any(set(item.evidence_refs) - evidence_by_id for item in result.results):
            raise ValueError("result references missing evidence")
        if any(item.source_record_ref not in source_by_id for item in result.evidence):
            raise ValueError("evidence references a missing source")
        if not response.request_artifact_uri.startswith("artifact://sha256/"):
            raise ValueError("request artifact URI is invalid")
        if not response.replay_artifact_uri.startswith("artifact://sha256/"):
            raise ValueError("replay artifact URI is invalid")
        if len(response.export_uris) != 2 or any(
            not uri.startswith("artifact://sha256/") for uri in response.export_uris
        ):
            raise ValueError("result export URI is invalid")
        if result.status is not AnalysisStatus.FAILED and not result_by_id:
            raise ValueError("non-failed analysis must contain a result")

    def _completed(
        self,
        command: EvidenceWorkerCommand,
        response: EvidenceAdapterResponse,
    ) -> EvidenceWorkerExecution:
        result = response.result.root
        status_map = {
            AnalysisStatus.COMPLETE: JobStatus.COMPLETE,
            AnalysisStatus.PARTIAL: JobStatus.PARTIAL,
            AnalysisStatus.FAILED: JobStatus.FAILED,
        }
        job_status = status_map[result.status]
        first_error = result.errors[0].code.value if result.errors else None
        checkpoint_ref = (
            result.run.checkpoint_id if result.run.checkpoint_id is not MISSING else None
        )
        return EvidenceWorkerExecution(
            worker_outcome=WorkerOutcome(
                status=job_status,
                error_code=first_error,
                checkpoint_ref=checkpoint_ref,
                retryable=bool(result.errors and result.errors[0].retryable),
            ),
            result=response.result,
            event=self._event(
                command,
                event_type=f"evidence_{job_status.value}",
                to_status=job_status,
                details={
                    "analysis_id": result.analysis_id,
                    "result_ids": [item.result_id for item in result.results],
                    "evidence_ids": [item.evidence_id for item in result.evidence],
                    "source_record_ids": [item.source_record_id for item in result.sources],
                    "request_artifact_uri": response.request_artifact_uri,
                    "replay_artifact_uri": response.replay_artifact_uri,
                    "export_uris": list(response.export_uris),
                    "reused": response.reused,
                },
            ),
            error=None,
            export_uris=response.export_uris,
            request_artifact_uri=response.request_artifact_uri,
            replay_artifact_uri=response.replay_artifact_uri,
            adapter_called=True,
            reused=response.reused,
        )

    def _blocked(
        self,
        command: EvidenceWorkerCommand,
        code: OperationErrorCode,
    ) -> EvidenceWorkerExecution:
        error = self._error(command, code, reason=code.value)
        return EvidenceWorkerExecution(
            worker_outcome=WorkerOutcome(
                status=JobStatus.FAILED,
                error_code=code.value,
            ),
            result=None,
            event=self._event(
                command,
                event_type="evidence_blocked",
                to_status=JobStatus.FAILED,
                details={"error_id": error.error_id, "reason": code.value},
            ),
            error=error,
            export_uris=(),
            request_artifact_uri=None,
            replay_artifact_uri=None,
            adapter_called=False,
            reused=False,
        )

    def _failed(
        self,
        command: EvidenceWorkerCommand,
        reason: str,
        *,
        adapter_called: bool,
    ) -> EvidenceWorkerExecution:
        error = self._error(
            command,
            OperationErrorCode.EVIDENCE_WORKER_FAILED,
            reason=reason,
        )
        return EvidenceWorkerExecution(
            worker_outcome=WorkerOutcome(
                status=JobStatus.FAILED,
                error_code=OperationErrorCode.EVIDENCE_WORKER_FAILED.value,
            ),
            result=None,
            event=self._event(
                command,
                event_type="evidence_failed",
                to_status=JobStatus.FAILED,
                details={"error_id": error.error_id, "reason": reason},
            ),
            error=error,
            export_uris=(),
            request_artifact_uri=None,
            replay_artifact_uri=None,
            adapter_called=adapter_called,
            reused=False,
        )

    def _event(
        self,
        command: EvidenceWorkerCommand,
        *,
        event_type: str,
        to_status: JobStatus,
        details: dict[str, object],
    ) -> OperationEvent:
        return OperationEvent(
            event_id=command.event_id,
            competition_id=command.manifest.competition_id,
            problem_id=command.problem.problem_id,
            entity_type="job",
            entity_id=command.job.job_id,
            event_type=event_type,
            actor_type=ActorType.WORKER,
            actor_id=command.worker_id,
            from_status=command.job.status,
            to_status=to_status,
            safe_details_json=details,
            created_at=self._clock(),
        )

    def _error(
        self,
        command: EvidenceWorkerCommand,
        code: OperationErrorCode,
        *,
        reason: str,
    ) -> OperationError:
        stage = (
            OperationErrorStage.AI_MODE_POLICY
            if code is OperationErrorCode.RULE_RESTRICTED
            else OperationErrorStage.OPERATIONS_INPUT
            if code is OperationErrorCode.INVALID_OPERATIONS_INPUT
            else OperationErrorStage.EVIDENCE_WORKER
        )
        return OperationError(
            error_id=command.error_id,
            code=code,
            message="Evidence worker execution was rejected or failed.",
            stage=stage,
            retryable=False,
            problem_id=command.problem.problem_id,
            job_id=command.job.job_id,
            details={"reason": reason},
        )


class EvidenceQueueExecutor:
    """Adapt approved Evidence Worker commands to the bounded scheduler callable."""

    def __init__(
        self,
        service: EvidenceWorkerService,
        commands: dict[str, EvidenceWorkerCommand],
    ) -> None:
        self._service = service
        self._commands = dict(commands)
        self._executions: dict[str, EvidenceWorkerExecution] = {}

    async def __call__(self, job: JobRecord, _: int) -> WorkerOutcome:
        command = self._commands.get(job.job_id)
        if command is None or command.job != job:
            return WorkerOutcome(
                status=JobStatus.FAILED,
                error_code=OperationErrorCode.INVALID_OPERATIONS_INPUT.value,
            )
        execution = await self._service.execute(command)
        self._executions[job.job_id] = execution
        return execution.worker_outcome

    def execution_for(self, job_id: str) -> EvidenceWorkerExecution:
        return self._executions[job_id]
