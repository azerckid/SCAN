"""Strict Operations Board read model and command response for OPS-IMPL-07."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    ContractBool,
    ContractModel,
    NonEmptyString,
    NonNegativeInt,
    ProviderId,
    SnakeName,
    UniqueList,
)
from scan_tool.domain.operations import (
    AIExecutionMode,
    AIRuleState,
    CandidateRecord,
    CandidateStatus,
    CompetitionId,
    CompetitionPhase,
    JobRecord,
    JobRole,
    JobStatus,
    OperationEvent,
    OperationEventId,
    OperationsDocument,
    ProblemId,
    ProblemPriority,
    ProblemRecord,
    ProblemStatus,
    Recommendation,
    SubmissionRecord,
    UtcDatetime,
    VerificationRecord,
    VerificationStatus,
)

SnapshotId = Annotated[
    str,
    StringConstraints(pattern=r"^SNAP-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
CommandId = Annotated[
    str,
    StringConstraints(pattern=r"^CMD-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
type Clock = Callable[[], datetime]


class SnapshotViewState(StrEnum):
    DEFAULT = "default"
    EMPTY = "empty"
    PARTIAL = "partial"
    FAILED = "failed"
    STALE = "stale"
    RULES_UNAVAILABLE = "rules_unavailable"


class WorkerHealth(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    STOPPED = "stopped"
    FAILED = "failed"


class HumanState(StrEnum):
    REVIEW_PENDING = "review_pending"
    READY = "ready"
    SUBMITTED = "submitted"


class SnapshotCompetition(ContractModel):
    competition_id: CompetitionId
    phase: CompetitionPhase
    rules_snapshot_ref: NonEmptyString
    elapsed_seconds: NonNegativeInt
    remaining_seconds: NonNegativeInt


class SnapshotAIMode(ContractModel):
    provider_id: ProviderId | None
    model_id: NonEmptyString | None
    data_boundary: SnakeName
    tool_mode: SnakeName
    rule_state: AIRuleState
    rules_snapshot_ref: NonEmptyString


class SnapshotSummary(ContractModel):
    total: NonNegativeInt
    active: NonNegativeInt
    verifying: NonNegativeInt
    ready: NonNegativeInt
    submitted: NonNegativeInt
    queue_age_seconds: NonNegativeInt


class SnapshotProblem(ContractModel):
    problem_id: ProblemId
    title: NonEmptyString
    score: NonNegativeInt
    priority: ProblemPriority
    status: ProblemStatus
    owner: NonEmptyString
    progress: NonEmptyString
    active_jobs: NonNegativeInt
    age_seconds: NonNegativeInt
    next_action: NonEmptyString


class SnapshotWorker(ContractModel):
    worker_id: NonEmptyString
    role: JobRole
    job_id: NonEmptyString
    stage: NonEmptyString
    health: WorkerHealth
    queue_reason: NonEmptyString | None
    attempt: NonNegativeInt
    max_attempts: Annotated[int, Field(strict=True, ge=1)]


class SnapshotVerification(ContractModel):
    verification_id: NonEmptyString
    candidate_id: NonEmptyString
    status: VerificationStatus
    passed_checks: NonNegativeInt
    required_checks: NonNegativeInt
    conflicts: UniqueList[NonEmptyString]
    missing_evidence: UniqueList[NonEmptyString]


class SnapshotSubmission(ContractModel):
    problem_id: ProblemId
    candidate_id: NonEmptyString
    answer_format: NonEmptyString
    answer_value: NonEmptyString
    confidence: Annotated[int, Field(strict=True, ge=0, le=100)]
    evidence_count: NonNegativeInt
    uncertainty_count: NonNegativeInt
    recommendation: Recommendation
    human_state: HumanState


class SnapshotSource(ContractModel):
    capability: SnakeName
    provider_id: ProviderId
    health: SnakeName
    concurrency_limit: Annotated[int, Field(strict=True, ge=1)]
    in_flight: NonNegativeInt
    retry_after_seconds: NonNegativeInt | None
    cache_status: SnakeName

    @model_validator(mode="after")
    def in_flight_does_not_exceed_limit(self) -> "SnapshotSource":
        if self.in_flight > self.concurrency_limit:
            raise PydanticCustomError(
                "schema_invalid",
                "source in_flight exceeds concurrency_limit",
            )
        return self


class SnapshotActivity(ContractModel):
    event_id: OperationEventId
    problem_id: ProblemId | None
    event_type: SnakeName
    actor_type: SnakeName
    actor_id: NonEmptyString
    created_at: UtcDatetime


class OperationsSnapshot(ContractModel):
    operations_schema_version: Literal["0.1"]
    snapshot_id: SnapshotId
    generated_at: UtcDatetime
    stale_at: UtcDatetime
    view_state: SnapshotViewState
    competition: SnapshotCompetition
    ai_mode: SnapshotAIMode | None
    summary: SnapshotSummary
    problems: list[SnapshotProblem]
    workers: list[SnapshotWorker]
    verifications: list[SnapshotVerification]
    submissions: list[SnapshotSubmission]
    sources: list[SnapshotSource]
    activity: list[SnapshotActivity]

    def to_contract_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class CommandResult(ContractModel):
    command_id: CommandId
    accepted: ContractBool
    entity_id: NonEmptyString
    new_status: SnakeName | None
    event_id: OperationEventId | None
    warnings: UniqueList[NonEmptyString]

    @model_validator(mode="after")
    def accepted_command_has_event_and_status(self) -> "CommandResult":
        if self.accepted and (self.event_id is None or self.new_status is None):
            raise PydanticCustomError(
                "schema_invalid",
                "accepted command requires event_id and new_status",
            )
        return self


class OperationsSnapshotBuilder:
    """Build one deterministic local Board projection from a validated bundle."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        freshness_seconds: int = 30,
        activity_limit: int = 20,
    ) -> None:
        if freshness_seconds < 1:
            raise ValueError("freshness_seconds must be positive")
        if activity_limit < 1:
            raise ValueError("activity_limit must be positive")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._freshness_seconds = freshness_seconds
        self._activity_limit = activity_limit

    def build(
        self,
        document: OperationsDocument,
        *,
        snapshot_id: str,
        elapsed_seconds: int,
        remaining_seconds: int,
        viewed_at: datetime | None = None,
        sources: Sequence[SnapshotSource] = (),
    ) -> OperationsSnapshot:
        bundle = document.root
        generated_at = self._clock()
        stale_at = generated_at + timedelta(seconds=self._freshness_seconds)
        observed_at = viewed_at or generated_at
        jobs_by_problem = _jobs_by_problem(bundle.jobs)
        latest_mode = max(bundle.ai_modes, key=lambda item: item.created_at, default=None)
        problems = [
            _problem_row(problem, jobs_by_problem.get(problem.problem_id, ()), generated_at)
            for problem in bundle.problems
        ]
        submissions_by_candidate = {item.candidate_id: item for item in bundle.submissions}
        snapshot = OperationsSnapshot(
            operations_schema_version=bundle.operations_schema_version,
            snapshot_id=snapshot_id,
            generated_at=generated_at,
            stale_at=stale_at,
            view_state=_view_state(document, latest_mode, observed_at, stale_at),
            competition=SnapshotCompetition(
                competition_id=bundle.manifest.competition_id,
                phase=bundle.manifest.phase,
                rules_snapshot_ref=bundle.manifest.rules_snapshot_ref,
                elapsed_seconds=elapsed_seconds,
                remaining_seconds=remaining_seconds,
            ),
            ai_mode=_ai_mode_row(latest_mode),
            summary=_summary(bundle.problems, bundle.jobs, generated_at),
            problems=problems,
            workers=[_worker_row(job) for job in bundle.jobs],
            verifications=_verification_rows(bundle.verifications),
            submissions=_submission_rows(bundle.candidates, submissions_by_candidate),
            sources=list(sources),
            activity=_activity_rows(bundle.events, self._activity_limit),
        )
        return snapshot


def _ai_mode_row(mode: AIExecutionMode | None) -> SnapshotAIMode | None:
    if mode is None:
        return None
    return SnapshotAIMode(
        provider_id=None if mode.provider_id is MISSING else mode.provider_id,
        model_id=None if mode.model_id is MISSING else mode.model_id,
        data_boundary=mode.data_boundary.value,
        tool_mode=mode.tool_mode.value,
        rule_state=mode.rule_state,
        rules_snapshot_ref=mode.rules_snapshot_ref,
    )


def _verification_rows(items: list[VerificationRecord]) -> list[SnapshotVerification]:
    return [
        SnapshotVerification(
            verification_id=item.verification_id,
            candidate_id=item.candidate_id,
            status=item.status,
            passed_checks=sum(check.passed for check in item.check_results),
            required_checks=len(item.required_checks),
            conflicts=list(item.conflicts),
            missing_evidence=list(item.missing_evidence),
        )
        for item in items
    ]


def _submission_rows(
    candidates: list[CandidateRecord],
    submissions_by_candidate: dict[str, SubmissionRecord],
) -> list[SnapshotSubmission]:
    return [
        SnapshotSubmission(
            problem_id=item.problem_id,
            candidate_id=item.candidate_id,
            answer_format=item.answer_format,
            answer_value=item.answer_value,
            confidence=item.confidence,
            evidence_count=len(item.evidence_refs),
            uncertainty_count=len(item.uncertainties),
            recommendation=item.recommendation,
            human_state=(
                HumanState.SUBMITTED
                if item.candidate_id in submissions_by_candidate
                else (
                    HumanState.READY
                    if item.status is CandidateStatus.SUBMISSION_READY
                    else HumanState.REVIEW_PENDING
                )
            ),
        )
        for item in candidates
    ]


def _activity_rows(items: list[OperationEvent], limit: int) -> list[SnapshotActivity]:
    return [
        SnapshotActivity(
            event_id=item.event_id,
            problem_id=None if item.problem_id is MISSING else item.problem_id,
            event_type=item.event_type,
            actor_type=item.actor_type.value,
            actor_id=item.actor_id,
            created_at=item.created_at,
        )
        for item in sorted(
            items,
            key=lambda event: (event.created_at, event.event_id),
            reverse=True,
        )[:limit]
    ]


def _jobs_by_problem(jobs: list[JobRecord]) -> dict[str, tuple[JobRecord, ...]]:
    grouped: dict[str, list[JobRecord]] = {}
    for job in jobs:
        grouped.setdefault(job.problem_id, []).append(job)
    return {problem_id: tuple(items) for problem_id, items in grouped.items()}


def _problem_row(
    problem: ProblemRecord,
    jobs: tuple[JobRecord, ...],
    generated_at: datetime,
) -> SnapshotProblem:
    completed = sum(job.status is JobStatus.COMPLETE for job in jobs)
    active = sum(
        job.status in {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.WAITING} for job in jobs
    )
    assigned = next(
        (
            job.assigned_worker_id
            for job in jobs
            if job.assigned_worker_id is not MISSING and job.status is JobStatus.RUNNING
        ),
        None,
    )
    if assigned is None:
        assigned = next(
            (job.assigned_worker_id for job in jobs if job.assigned_worker_id is not MISSING),
            "unassigned",
        )
    return SnapshotProblem(
        problem_id=problem.problem_id,
        title=problem.title,
        score=problem.score,
        priority=problem.priority,
        status=problem.status,
        owner=assigned,
        progress=f"{completed}/{len(jobs)} jobs",
        active_jobs=active,
        age_seconds=_age_seconds(problem.created_at, generated_at),
        next_action=_next_action(problem.status),
    )


def _worker_row(job: JobRecord) -> SnapshotWorker:
    worker_id = (
        job.assigned_worker_id
        if job.assigned_worker_id is not MISSING
        else f"unassigned-{job.role.value}"
    )
    queue_reason = None
    if job.status is JobStatus.QUEUED:
        queue_reason = "awaiting scheduler slot or dependency"
    elif job.status is JobStatus.WAITING:
        queue_reason = "awaiting retry, source, or operator input"
    return SnapshotWorker(
        worker_id=worker_id,
        role=job.role,
        job_id=job.job_id,
        stage=job.job_type,
        health=_worker_health(job.status),
        queue_reason=queue_reason,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
    )


def _summary(
    problems: list[ProblemRecord],
    jobs: list[JobRecord],
    generated_at: datetime,
) -> SnapshotSummary:
    queue_ages = [
        _age_seconds(job.queued_at, generated_at)
        for job in jobs
        if job.status in {JobStatus.QUEUED, JobStatus.WAITING}
    ]
    return SnapshotSummary(
        total=len(problems),
        active=sum(
            item.status
            not in {
                ProblemStatus.CAPTURED,
                ProblemStatus.SUBMISSION_READY,
                ProblemStatus.SUBMITTED,
            }
            for item in problems
        ),
        verifying=sum(item.status is ProblemStatus.VERIFYING for item in problems),
        ready=sum(item.status is ProblemStatus.SUBMISSION_READY for item in problems),
        submitted=sum(item.status is ProblemStatus.SUBMITTED for item in problems),
        queue_age_seconds=max(queue_ages, default=0),
    )


def _view_state(
    document: OperationsDocument,
    latest_mode: AIExecutionMode | None,
    observed_at: datetime,
    stale_at: datetime,
) -> SnapshotViewState:
    bundle = document.root
    if observed_at > stale_at:
        return SnapshotViewState.STALE
    if latest_mode is not None and latest_mode.rule_state is not AIRuleState.ALLOWED:
        return SnapshotViewState.RULES_UNAVAILABLE
    if not bundle.problems:
        return SnapshotViewState.EMPTY
    if bundle.errors and not any(
        job.status in {JobStatus.RUNNING, JobStatus.COMPLETE, JobStatus.PARTIAL}
        for job in bundle.jobs
    ):
        return SnapshotViewState.FAILED
    if (
        bundle.errors
        or any(item.status is ProblemStatus.PARTIAL for item in bundle.problems)
        or any(item.status in {JobStatus.PARTIAL, JobStatus.FAILED} for item in bundle.jobs)
        or any(
            item.status in {VerificationStatus.CONFLICT, VerificationStatus.INCOMPLETE}
            for item in bundle.verifications
        )
    ):
        return SnapshotViewState.PARTIAL
    return SnapshotViewState.DEFAULT


def _worker_health(status: JobStatus) -> WorkerHealth:
    return {
        JobStatus.QUEUED: WorkerHealth.QUEUED,
        JobStatus.RUNNING: WorkerHealth.RUNNING,
        JobStatus.WAITING: WorkerHealth.WAITING,
        JobStatus.COMPLETE: WorkerHealth.IDLE,
        JobStatus.PARTIAL: WorkerHealth.STOPPED,
        JobStatus.CANCELLED: WorkerHealth.STOPPED,
        JobStatus.FAILED: WorkerHealth.FAILED,
    }[status]


def _next_action(status: ProblemStatus) -> str:
    return {
        ProblemStatus.CAPTURED: "confirm an allowed AI execution mode",
        ProblemStatus.TRIAGED: "approve the plan and queue leaf jobs",
        ProblemStatus.QUEUED: "monitor dependency and worker capacity",
        ProblemStatus.RUNNING: "review incoming evidence and checkpoints",
        ProblemStatus.PARTIAL: "resolve missing evidence or failed jobs",
        ProblemStatus.VERIFYING: "complete independent verification",
        ProblemStatus.REVIEW_REQUIRED: "resolve conflicts and uncertainties",
        ProblemStatus.SUBMISSION_READY: "copy the full answer for human submission",
        ProblemStatus.SUBMITTED: "record the manual CTFd response",
    }[status]


def _age_seconds(start: datetime, finish: datetime) -> int:
    return max(0, int((finish - start).total_seconds()))
