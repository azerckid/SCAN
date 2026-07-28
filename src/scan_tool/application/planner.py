"""Rules-gated planner orchestration for OPS-IMPL-03."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.application.security import SensitiveDataError, SensitiveDataGuard
from scan_tool.domain.operations import (
    ActorType,
    AdapterKind,
    AIExecutionMode,
    AIRuleState,
    AIToolMode,
    CompetitionEnvironment,
    CompetitionManifest,
    DataBoundary,
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
)
from scan_tool.domain.planning import PlannerBudgets, PlannerContext, safe_planner_details
from scan_tool.ports.planner import (
    ArtifactMetadataRecorder,
    PlannerAdapter,
    PlannerArtifactWriter,
)

type Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class PlannerCommand:
    manifest: CompetitionManifest
    problem: ProblemRecord
    mode: AIExecutionMode
    planner_job: JobRecord
    context: PlannerContext
    budgets: PlannerBudgets
    event_id: str
    error_id: str
    operator_approved_problem_data: bool = False


@dataclass(frozen=True, slots=True)
class PlannerExecution:
    plan: PlanHypothesis | None
    event: OperationEvent
    error: OperationError | None
    adapter_called: bool

    @property
    def succeeded(self) -> bool:
        return self.plan is not None and self.error is None


class PlannerService:
    """Enforce AI mode policy before invoking exactly one planner adapter."""

    def __init__(
        self,
        adapter: PlannerAdapter,
        artifact_writer: PlannerArtifactWriter,
        artifact_recorder: ArtifactMetadataRecorder,
        *,
        guard: SensitiveDataGuard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._adapter = adapter
        self._artifact_writer = artifact_writer
        self._artifact_recorder = artifact_recorder
        self._guard = guard or SensitiveDataGuard()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, command: PlannerCommand) -> PlannerExecution:
        policy_error = self._policy_error(command)
        if policy_error is not None:
            return self._blocked(command, policy_error)

        try:
            response = await asyncio.wait_for(
                self._adapter.plan(command.context),
                timeout=command.budgets.timeout_seconds,
            )
        except TimeoutError:
            return self._failed(command, "timeout")
        except Exception:
            return self._failed(command, "adapter_error")

        try:
            self._validate_response(command, response.plan)
        except ValueError:
            return self._failed(command, "contract_invalid")
        if response.usage.total_tokens > command.budgets.token_budget:
            return self._failed(command, "token_budget_exceeded")
        if response.usage.cost_microunits > command.budgets.cost_budget_microunits:
            return self._failed(command, "cost_budget_exceeded")
        try:
            self._guard.check_bytes(response.raw_output)
        except SensitiveDataError:
            return self._failed(command, "security_rejected")
        try:
            artifact = self._artifact_writer.write(
                response.raw_output,
                media_type="application/json",
                artifact_kind="planner_raw_output",
                redaction_status="checked",
                license_status="generated",
                source_id=None,
            )
            if artifact.uri != response.plan.raw_output_artifact:
                raise ValueError("planner raw output artifact hash mismatch")
            self._artifact_recorder.record_artifact(artifact)
        except Exception:
            return self._failed(command, "artifact_persistence_failed")

        return PlannerExecution(
            plan=response.plan,
            event=self._event(
                command,
                event_type="planner_completed",
                actor_type=ActorType.AI,
                to_status=PlanStatus.PROPOSED,
                details={
                    **self._mode_details(command),
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "cost_microunits": response.usage.cost_microunits,
                },
            ),
            error=None,
            adapter_called=True,
        )

    def _policy_error(self, command: PlannerCommand) -> OperationErrorCode | None:
        if command.manifest.competition_id != command.problem.competition_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.manifest.competition_id != command.mode.competition_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.problem_id != command.planner_job.problem_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.problem.problem_id != command.context.problem_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.planner_job.job_id != command.context.planner_job_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.planner_job.plan_id != command.context.plan_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.mode.mode_id != command.context.mode_id:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.planner_job.role is not JobRole.PLANNER:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if command.mode.rule_state is AIRuleState.RULES_GATED:
            if command.planner_job.status is not JobStatus.WAITING:
                return OperationErrorCode.INVALID_OPERATIONS_INPUT
            return OperationErrorCode.RULES_GATED
        if command.mode.rule_state is AIRuleState.RULE_RESTRICTED:
            if command.planner_job.status is not JobStatus.WAITING:
                return OperationErrorCode.INVALID_OPERATIONS_INPUT
            return OperationErrorCode.RULE_RESTRICTED
        if command.context.data_boundary is not command.mode.data_boundary:
            return OperationErrorCode.RULE_RESTRICTED
        if command.mode.tool_mode is not AIToolMode.PLANNING_ONLY:
            if command.planner_job.status is not JobStatus.WAITING:
                return OperationErrorCode.INVALID_OPERATIONS_INPUT
            return OperationErrorCode.RULES_GATED
        if (
            command.mode.data_boundary is DataBoundary.APPROVED_PROBLEM_DATA
            and not command.operator_approved_problem_data
        ):
            if command.planner_job.status is not JobStatus.WAITING:
                return OperationErrorCode.INVALID_OPERATIONS_INPUT
            return OperationErrorCode.RULES_GATED
        if command.planner_job.status is not JobStatus.QUEUED:
            return OperationErrorCode.INVALID_OPERATIONS_INPUT
        if self._adapter.adapter_kind is not command.mode.adapter_kind:
            return OperationErrorCode.RULE_RESTRICTED
        if (
            command.mode.provider_id is MISSING
            or command.mode.model_id is MISSING
            or self._adapter.provider_id != command.mode.provider_id
            or self._adapter.model_id != command.mode.model_id
        ):
            return OperationErrorCode.RULE_RESTRICTED
        if (
            command.mode.adapter_kind is AdapterKind.FAKE_QA
            and command.manifest.environment is not CompetitionEnvironment.SYNTHETIC_TEST
        ):
            return OperationErrorCode.RULE_RESTRICTED
        return None

    def _validate_response(
        self,
        command: PlannerCommand,
        plan: PlanHypothesis,
    ) -> None:
        if plan.plan_id != command.context.plan_id:
            raise ValueError("planner returned another plan_id")
        if plan.problem_id != command.problem.problem_id:
            raise ValueError("planner returned another problem_id")
        if plan.mode_id != command.mode.mode_id:
            raise ValueError("planner returned another mode_id")
        if plan.planner_job_id != command.planner_job.job_id:
            raise ValueError("planner returned another planner_job_id")
        if plan.status is not PlanStatus.PROPOSED:
            raise ValueError("planner must return a proposed plan")
        if not plan.leaf_job_specs:
            raise ValueError("planner plan must contain at least one leaf job")

    def _blocked(
        self,
        command: PlannerCommand,
        code: OperationErrorCode,
    ) -> PlannerExecution:
        stage = (
            OperationErrorStage.OPERATIONS_INPUT
            if code is OperationErrorCode.INVALID_OPERATIONS_INPUT
            else OperationErrorStage.AI_MODE_POLICY
        )
        message = {
            OperationErrorCode.INVALID_OPERATIONS_INPUT: "planner command references are invalid",
            OperationErrorCode.RULES_GATED: "planner is waiting for an allowed AI mode",
            OperationErrorCode.RULE_RESTRICTED: "planner adapter call is restricted by policy",
        }[code]
        return PlannerExecution(
            plan=None,
            event=self._event(
                command,
                event_type="planner_blocked",
                actor_type=ActorType.SYSTEM,
                to_status=None,
                details={**self._mode_details(command), "error_code": code.value},
            ),
            error=OperationError(
                error_id=command.error_id,
                code=code,
                message=message,
                stage=stage,
                retryable=False,
                problem_id=command.problem.problem_id,
                job_id=command.planner_job.job_id,
                details=safe_planner_details(self._mode_details(command)),
            ),
            adapter_called=False,
        )

    def _failed(self, command: PlannerCommand, failure_kind: str) -> PlannerExecution:
        details = {**self._mode_details(command), "failure_kind": failure_kind}
        return PlannerExecution(
            plan=None,
            event=self._event(
                command,
                event_type="planner_failed",
                actor_type=ActorType.SYSTEM,
                to_status=None,
                details={**details, "error_code": "planner_failed"},
            ),
            error=OperationError(
                error_id=command.error_id,
                code=OperationErrorCode.PLANNER_FAILED,
                message="planner execution failed contract, budget, timeout, or security checks",
                stage=OperationErrorStage.PLANNER,
                retryable=False,
                problem_id=command.problem.problem_id,
                job_id=command.planner_job.job_id,
                details=safe_planner_details(details),
            ),
            adapter_called=True,
        )

    def _event(
        self,
        command: PlannerCommand,
        *,
        event_type: str,
        actor_type: ActorType,
        to_status: PlanStatus | None,
        details: dict[str, object],
    ) -> OperationEvent:
        payload = {
            "event_id": command.event_id,
            "competition_id": command.manifest.competition_id,
            "problem_id": command.problem.problem_id,
            "entity_type": "plan",
            "entity_id": command.context.plan_id,
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": (
                self._adapter.provider_id if actor_type is ActorType.AI else "planner_gate"
            ),
            "safe_details_json": safe_planner_details(details),
            "created_at": self._clock(),
        }
        if to_status is not None:
            payload["to_status"] = to_status.value
        return OperationEvent.model_validate(payload)

    def _mode_details(self, command: PlannerCommand) -> dict[str, object]:
        return {
            "mode_id": command.mode.mode_id,
            "adapter_kind": command.mode.adapter_kind.value,
            "provider_id": (
                None if command.mode.provider_id is MISSING else command.mode.provider_id
            ),
            "model_id": None if command.mode.model_id is MISSING else command.mode.model_id,
            "data_boundary": command.mode.data_boundary.value,
            "tool_mode": command.mode.tool_mode.value,
            "rule_state": command.mode.rule_state.value,
            "timeout_seconds": command.budgets.timeout_seconds,
            "token_budget": command.budgets.token_budget,
            "cost_budget_microunits": command.budgets.cost_budget_microunits,
        }
