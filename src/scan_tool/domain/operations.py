"""Public operations contract and pure state invariants for OPS-IMPL-01."""

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, AnyUrl, Field, RootModel, StringConstraints, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    AnalysisId,
    ContractBool,
    ContractDatetime,
    ContractModel,
    EvidenceId,
    JsonObject,
    NonEmptyString,
    NonEmptyUniqueList,
    NonNegativeInt,
    ProviderId,
    ResultId,
    Sha256,
    SnakeName,
    UniqueList,
)
from scan_tool.domain.analysis_request import AnalysisType

OPERATIONS_SCHEMA_VERSION = "0.1"

OperationsLeafAnalysisType = Literal[
    AnalysisType.DEX_SWAP,
    AnalysisType.AUTH_CONSUMPTION,
    AnalysisType.ADDRESS_FREEZE,
    AnalysisType.EVM_CORE,
    AnalysisType.EVM_SPECIAL,
    AnalysisType.FLOW_PATH,
    AnalysisType.INTEL_CONTEXT,
    AnalysisType.BRIDGE_TRANSFER,
    AnalysisType.BITCOIN_UTXO,
    AnalysisType.CEX_CLUSTER,
]

CompetitionId = Annotated[
    str,
    StringConstraints(pattern=r"^COMP-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
ProblemId = Annotated[
    str,
    StringConstraints(pattern=r"^PROB-[A-Z0-9][A-Z0-9-]{1,63}$"),
]
ModeId = Annotated[
    str,
    StringConstraints(pattern=r"^MODE-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
PlanId = Annotated[
    str,
    StringConstraints(pattern=r"^PLAN-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
JobId = Annotated[
    str,
    StringConstraints(pattern=r"^JOB-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
VerificationId = Annotated[
    str,
    StringConstraints(pattern=r"^VER-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
CandidateId = Annotated[
    str,
    StringConstraints(pattern=r"^CAND-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
SubmissionId = Annotated[
    str,
    StringConstraints(pattern=r"^SUB-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
OperationEventId = Annotated[
    str,
    StringConstraints(pattern=r"^OEV-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
OperationErrorId = Annotated[
    str,
    StringConstraints(pattern=r"^OERR-[A-Z0-9][A-Z0-9-]{2,63}$"),
]
RuleId = Annotated[str, StringConstraints(pattern=r"^RULE-[A-Z0-9-]+$")]
WorkerId = Annotated[
    str,
    StringConstraints(pattern=r"^WORKER-[A-Z0-9][A-Z0-9-]{1,63}$"),
]
ArtifactUri = Annotated[
    str,
    StringConstraints(pattern=r"^artifact://sha256/[a-f0-9]{64}$"),
]


def _utc_datetime(value: ContractDatetime) -> ContractDatetime:
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise PydanticCustomError("schema_invalid", "operations timestamps must use UTC")
    return value


UtcDatetime = Annotated[
    ContractDatetime,
    Field(json_schema_extra={"pattern": r"Z$"}),
    AfterValidator(_utc_datetime),
]

_SENSITIVE_DETAIL_KEYS = {
    "access_token",
    "api_key",
    "auth_token",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "private_key",
    "seed_phrase",
    "session",
}


def _safe_json(value: JsonObject) -> JsonObject:
    def inspect(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key.lower() in _SENSITIVE_DETAIL_KEYS:
                    raise PydanticCustomError(
                        "schema_invalid",
                        "operations JSON contains a prohibited sensitive field",
                    )
                inspect(nested)
        elif isinstance(item, list):
            for nested in item:
                inspect(nested)
        elif isinstance(item, str) and (
            item.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", item) is not None
        ):
            raise PydanticCustomError(
                "schema_invalid",
                "operations JSON contains a prohibited local absolute path",
            )

    inspect(value)
    return value


SafeJsonObject = Annotated[JsonObject, AfterValidator(_safe_json)]


class CompetitionPhase(StrEnum):
    QUALIFIER = "qualifier"
    FINAL = "final"


class CompetitionStatus(StrEnum):
    SETUP = "setup"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class CompetitionEnvironment(StrEnum):
    LIVE = "live"
    SYNTHETIC_TEST = "synthetic_test"


class ProblemPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    DEFERRED = "deferred"


class PrioritySource(StrEnum):
    HUMAN = "human"
    DERIVED = "derived"


class ProblemStatus(StrEnum):
    CAPTURED = "captured"
    TRIAGED = "triaged"
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    VERIFYING = "verifying"
    REVIEW_REQUIRED = "review_required"
    SUBMISSION_READY = "submission_ready"
    SUBMITTED = "submitted"


class AdapterKind(StrEnum):
    FAKE_QA = "fake_qa"
    LOCAL = "local"
    EXTERNAL = "external"


class DataBoundary(StrEnum):
    SYNTHETIC_ONLY = "synthetic_only"
    LOCAL_ONLY = "local_only"
    REDACTED_EXTERNAL = "redacted_external"
    APPROVED_PROBLEM_DATA = "approved_problem_data"


class AIToolMode(StrEnum):
    PLANNING_ONLY = "planning_only"
    PLANNING_AND_APPROVED_TOOLS = "planning_and_approved_tools"


class AIRuleState(StrEnum):
    ALLOWED = "allowed"
    RULES_GATED = "rules_gated"
    RULE_RESTRICTED = "rule_restricted"


class PlanStatus(StrEnum):
    RULES_GATED = "rules_gated"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class JobRole(StrEnum):
    PLANNER = "planner"
    EVIDENCE = "evidence"
    VERIFIER = "verifier"
    REPORTER = "reporter"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASS = "pass"
    FAIL = "fail"
    CONFLICT = "conflict"
    INCOMPLETE = "incomplete"


class CandidateStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    SUBMISSION_READY = "submission_ready"
    SUBMITTED = "submitted"
    REJECTED = "rejected"


class Recommendation(StrEnum):
    HOLD = "hold"
    INVESTIGATE = "investigate"
    SUBMIT = "submit"


class SubmissionResponse(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNKNOWN = "unknown"


class ActorType(StrEnum):
    OPERATOR = "operator"
    AI = "ai"
    WORKER = "worker"
    SYSTEM = "system"


class OperationErrorStage(StrEnum):
    OPERATIONS_INPUT = "operations_input"
    AI_MODE_POLICY = "ai_mode_policy"
    PLANNER = "planner"
    SCHEDULER = "scheduler"
    EVIDENCE_WORKER = "evidence_worker"
    VERIFICATION = "verification"
    SUBMISSION_RECORD = "submission_record"


class OperationErrorCode(StrEnum):
    INVALID_OPERATIONS_INPUT = "invalid_operations_input"
    RULES_GATED = "rules_gated"
    RULE_RESTRICTED = "rule_restricted"
    PLANNER_FAILED = "planner_failed"
    DEPENDENCY_CYCLE = "dependency_cycle"
    BUDGET_EXHAUSTED = "budget_exhausted"
    EVIDENCE_WORKER_FAILED = "evidence_worker_failed"
    VERIFICATION_FAILED = "verification_failed"
    SUBMISSION_RECORD_FAILED = "submission_record_failed"


class ProvidedFileArtifact(ContractModel):
    filename: NonEmptyString
    sha256: Sha256
    media_type: NonEmptyString


class CompetitionManifest(ContractModel):
    competition_id: CompetitionId
    operations_schema_version: Literal["0.1"]
    name: NonEmptyString
    phase: CompetitionPhase
    environment: CompetitionEnvironment
    rules_snapshot_ref: NonEmptyString
    status: CompetitionStatus
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> "CompetitionManifest":
        _require_ordered(self.created_at, self.updated_at)
        return self


class ProblemRecord(ContractModel):
    problem_id: ProblemId
    competition_id: CompetitionId
    title: NonEmptyString
    original_text_artifact: ArtifactUri
    provided_urls: UniqueList[AnyUrl]
    provided_file_artifacts: list[ProvidedFileArtifact]
    score: NonNegativeInt
    answer_format: NonEmptyString
    priority: ProblemPriority
    priority_source: PrioritySource
    status: ProblemStatus
    active_plan_id: PlanId | MISSING = MISSING
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> "ProblemRecord":
        _require_ordered(self.created_at, self.updated_at)
        return self


class AIExecutionMode(ContractModel):
    mode_id: ModeId
    competition_id: CompetitionId
    provider_id: ProviderId | MISSING = MISSING
    model_id: NonEmptyString | MISSING = MISSING
    adapter_kind: AdapterKind
    data_boundary: DataBoundary
    tool_mode: AIToolMode
    rule_state: AIRuleState
    affected_rule_ids: UniqueList[RuleId]
    rules_snapshot_ref: NonEmptyString
    created_at: UtcDatetime

    @model_validator(mode="after")
    def adapter_and_boundary_are_compatible(self) -> "AIExecutionMode":
        allowed_boundaries = {
            AdapterKind.FAKE_QA: {DataBoundary.SYNTHETIC_ONLY},
            AdapterKind.LOCAL: {DataBoundary.LOCAL_ONLY},
            AdapterKind.EXTERNAL: {
                DataBoundary.REDACTED_EXTERNAL,
                DataBoundary.APPROVED_PROBLEM_DATA,
            },
        }
        if self.data_boundary not in allowed_boundaries[self.adapter_kind]:
            raise PydanticCustomError(
                "schema_invalid",
                "adapter_kind and data_boundary are incompatible",
            )
        if self.rule_state is AIRuleState.ALLOWED and (
            self.provider_id is MISSING or self.model_id is MISSING
        ):
            raise PydanticCustomError(
                "schema_invalid",
                "allowed AI mode requires provider_id and model_id",
            )
        return self


class LeafJobSpec(ContractModel):
    leaf_job_id: JobId
    role: JobRole
    purpose: NonEmptyString
    analysis_type: OperationsLeafAnalysisType
    inputs_projection: SafeJsonObject
    depends_on: UniqueList[JobId]
    required_capabilities: UniqueList[SnakeName]
    expected_output: NonEmptyString

    @model_validator(mode="after")
    def does_not_depend_on_itself(self) -> "LeafJobSpec":
        if self.leaf_job_id in self.depends_on:
            raise PydanticCustomError("schema_invalid", "leaf job cannot depend on itself")
        return self


class PlanHypothesis(ContractModel):
    plan_id: PlanId
    problem_id: ProblemId
    mode_id: ModeId
    planner_job_id: JobId
    status: PlanStatus
    problem_type_hypothesis: NonEmptyString
    method_hypothesis: NonEmptyString
    assumptions: UniqueList[NonEmptyString]
    missing_inputs: UniqueList[NonEmptyString]
    leaf_job_specs: list[LeafJobSpec]
    raw_output_artifact: ArtifactUri | MISSING = MISSING
    created_at: UtcDatetime
    decided_at: UtcDatetime | MISSING = MISSING

    @model_validator(mode="after")
    def lifecycle_fields_match_status(self) -> "PlanHypothesis":
        leaf_job_ids = [item.leaf_job_id for item in self.leaf_job_specs]
        if len(leaf_job_ids) != len(set(leaf_job_ids)):
            raise PydanticCustomError("schema_invalid", "duplicate leaf_job_id")
        known_leaf_jobs = set(leaf_job_ids)
        if any(set(item.depends_on) - known_leaf_jobs for item in self.leaf_job_specs):
            raise PydanticCustomError(
                "schema_invalid",
                "leaf job dependency must reference the same plan",
            )
        if self.status is PlanStatus.RULES_GATED:
            if self.raw_output_artifact is not MISSING:
                raise PydanticCustomError(
                    "schema_invalid",
                    "rules_gated plan cannot contain raw AI output",
                )
            if self.leaf_job_specs:
                raise PydanticCustomError(
                    "schema_invalid",
                    "rules_gated plan cannot contain executable leaf jobs",
                )
        elif self.raw_output_artifact is MISSING:
            raise PydanticCustomError(
                "schema_invalid",
                "non-gated plan requires raw_output_artifact",
            )
        if (
            self.status in {PlanStatus.APPROVED, PlanStatus.REJECTED, PlanStatus.SUPERSEDED}
            and self.decided_at is MISSING
        ):
            raise PydanticCustomError(
                "schema_invalid",
                "decided plan requires decided_at",
            )
        return self


class JobRecord(ContractModel):
    job_id: JobId
    problem_id: ProblemId
    plan_id: PlanId
    role: JobRole
    job_type: SnakeName
    status: JobStatus
    priority: ProblemPriority
    idempotency_key: Sha256
    analysis_id: AnalysisId | MISSING = MISSING
    attempt: NonNegativeInt
    max_attempts: Annotated[int, Field(strict=True, ge=1)]
    assigned_worker_id: WorkerId | MISSING = MISSING
    error_code: SnakeName | MISSING = MISSING
    checkpoint_ref: NonEmptyString | MISSING = MISSING
    queued_at: UtcDatetime
    started_at: UtcDatetime | MISSING = MISSING
    finished_at: UtcDatetime | MISSING = MISSING

    @model_validator(mode="after")
    def lifecycle_fields_match_status(self) -> "JobRecord":
        if self.attempt > self.max_attempts:
            raise PydanticCustomError("schema_invalid", "attempt exceeds max_attempts")
        if self.status is JobStatus.RUNNING and self.started_at is MISSING:
            raise PydanticCustomError("schema_invalid", "running job requires started_at")
        terminal = {
            JobStatus.COMPLETE,
            JobStatus.PARTIAL,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
        if self.status in terminal and self.finished_at is MISSING:
            raise PydanticCustomError("schema_invalid", "terminal job requires finished_at")
        if self.started_at is not MISSING:
            _require_ordered(self.queued_at, self.started_at)
        if self.finished_at is not MISSING:
            _require_ordered(
                self.started_at if self.started_at is not MISSING else self.queued_at,
                self.finished_at,
            )
        return self


class VerificationCheck(ContractModel):
    check: SnakeName
    passed: ContractBool
    result_refs: UniqueList[ResultId]
    evidence_refs: UniqueList[EvidenceId]


class VerificationRecord(ContractModel):
    verification_id: VerificationId
    problem_id: ProblemId
    candidate_id: CandidateId
    verifier_job_id: JobId
    status: VerificationStatus
    required_checks: NonEmptyUniqueList[SnakeName]
    check_results: list[VerificationCheck]
    independent_from_job_ids: UniqueList[JobId]
    conflicts: UniqueList[NonEmptyString]
    missing_evidence: UniqueList[EvidenceId]
    created_at: UtcDatetime
    finished_at: UtcDatetime | MISSING = MISSING

    @model_validator(mode="after")
    def lifecycle_fields_match_status(self) -> "VerificationRecord":
        checks = [item.check for item in self.check_results]
        if len(checks) != len(set(checks)):
            raise PydanticCustomError("schema_invalid", "duplicate verification check")
        terminal = {
            VerificationStatus.PASS,
            VerificationStatus.FAIL,
            VerificationStatus.CONFLICT,
            VerificationStatus.INCOMPLETE,
        }
        if self.status in terminal and self.finished_at is MISSING:
            raise PydanticCustomError(
                "schema_invalid",
                "terminal verification requires finished_at",
            )
        if self.finished_at is not MISSING:
            _require_ordered(self.created_at, self.finished_at)
        if self.status is VerificationStatus.PASS:
            if self.conflicts or self.missing_evidence:
                raise PydanticCustomError(
                    "schema_invalid",
                    "passing verification cannot have conflicts or missing evidence",
                )
            check_results = {item.check: item.passed for item in self.check_results}
            if set(self.required_checks) - check_results.keys() or not all(
                check_results[check] for check in self.required_checks
            ):
                raise PydanticCustomError(
                    "schema_invalid",
                    "passing verification requires every required check to pass",
                )
        return self


class CandidateRecord(ContractModel):
    candidate_id: CandidateId
    problem_id: ProblemId
    answer_format: NonEmptyString
    answer_value: NonEmptyString
    status: CandidateStatus
    result_refs: UniqueList[ResultId]
    evidence_refs: UniqueList[EvidenceId]
    verification_refs: UniqueList[VerificationId]
    confidence: Annotated[int, Field(strict=True, ge=0, le=100)]
    confidence_basis: NonEmptyString
    uncertainties: UniqueList[NonEmptyString]
    recommendation: Recommendation
    created_by_job_id: JobId
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @model_validator(mode="after")
    def ready_candidate_has_evidence(self) -> "CandidateRecord":
        _require_ordered(self.created_at, self.updated_at)
        if self.status in {CandidateStatus.SUBMISSION_READY, CandidateStatus.SUBMITTED}:
            if not self.result_refs or not self.evidence_refs or not self.verification_refs:
                raise PydanticCustomError(
                    "schema_invalid",
                    "submission-ready candidate requires result, evidence, and verification refs",
                )
            if self.recommendation is not Recommendation.SUBMIT:
                raise PydanticCustomError(
                    "schema_invalid",
                    "submission-ready candidate requires submit recommendation",
                )
        return self


class SubmissionRecord(ContractModel):
    submission_id: SubmissionId
    candidate_id: CandidateId
    operator_confirmed: Literal[True]
    response: SubmissionResponse
    submitted_at: UtcDatetime
    note_artifact: ArtifactUri | MISSING = MISSING


class OperationEvent(ContractModel):
    event_id: OperationEventId
    competition_id: CompetitionId
    problem_id: ProblemId | MISSING = MISSING
    entity_type: SnakeName
    entity_id: NonEmptyString
    event_type: SnakeName
    actor_type: ActorType
    actor_id: NonEmptyString
    from_status: SnakeName | MISSING = MISSING
    to_status: SnakeName | MISSING = MISSING
    safe_details_json: SafeJsonObject
    created_at: UtcDatetime


class OperationError(ContractModel):
    error_id: OperationErrorId
    code: OperationErrorCode
    message: Annotated[str, Field(min_length=1, max_length=1000)]
    stage: OperationErrorStage
    retryable: ContractBool
    problem_id: ProblemId | MISSING = MISSING
    job_id: JobId | MISSING = MISSING
    details: SafeJsonObject

    @model_validator(mode="after")
    def code_matches_stage(self) -> "OperationError":
        expected_stages = {
            OperationErrorCode.INVALID_OPERATIONS_INPUT: OperationErrorStage.OPERATIONS_INPUT,
            OperationErrorCode.RULES_GATED: OperationErrorStage.AI_MODE_POLICY,
            OperationErrorCode.RULE_RESTRICTED: OperationErrorStage.AI_MODE_POLICY,
            OperationErrorCode.PLANNER_FAILED: OperationErrorStage.PLANNER,
            OperationErrorCode.DEPENDENCY_CYCLE: OperationErrorStage.SCHEDULER,
            OperationErrorCode.BUDGET_EXHAUSTED: OperationErrorStage.SCHEDULER,
            OperationErrorCode.EVIDENCE_WORKER_FAILED: OperationErrorStage.EVIDENCE_WORKER,
            OperationErrorCode.VERIFICATION_FAILED: OperationErrorStage.VERIFICATION,
            OperationErrorCode.SUBMISSION_RECORD_FAILED: OperationErrorStage.SUBMISSION_RECORD,
        }
        if self.stage is not expected_stages[self.code]:
            raise PydanticCustomError(
                "schema_invalid",
                "operations error code and stage are inconsistent",
            )
        return self


class OperationsContractBundle(ContractModel):
    """Versioned public export containing operations records and safe errors."""

    schema_uri: Annotated[
        str,
        Field(alias="$schema", pattern=r"operations-contract\.schema\.json$"),
    ]
    operations_schema_version: Literal["0.1"]
    manifest: CompetitionManifest
    problems: list[ProblemRecord]
    ai_modes: list[AIExecutionMode]
    plans: list[PlanHypothesis]
    jobs: list[JobRecord]
    verifications: list[VerificationRecord]
    candidates: list[CandidateRecord]
    submissions: list[SubmissionRecord]
    events: list[OperationEvent]
    errors: list[OperationError]

    @model_validator(mode="after")
    def references_are_valid(self) -> "OperationsContractBundle":
        manifest = self.manifest
        if manifest.operations_schema_version != self.operations_schema_version:
            raise PydanticCustomError("schema_invalid", "bundle and manifest versions must match")

        problems = _unique_map(self.problems, "problem_id")
        modes = _unique_map(self.ai_modes, "mode_id")
        plans = _unique_map(self.plans, "plan_id")
        jobs = _unique_map(self.jobs, "job_id")
        verifications = _unique_map(self.verifications, "verification_id")
        candidates = _unique_map(self.candidates, "candidate_id")
        _unique_map(self.submissions, "submission_id")
        _unique_map(self.events, "event_id")
        _unique_map(self.errors, "error_id")

        for record in [*self.problems, *self.ai_modes]:
            if record.competition_id != manifest.competition_id:
                raise PydanticCustomError("schema_invalid", "record belongs to another competition")
        for mode in self.ai_modes:
            if (
                mode.adapter_kind is AdapterKind.FAKE_QA
                and mode.rule_state is AIRuleState.ALLOWED
                and manifest.environment is not CompetitionEnvironment.SYNTHETIC_TEST
            ):
                raise PydanticCustomError(
                    "schema_invalid",
                    "fake_qa can be allowed only for a synthetic test competition",
                )
        for problem in self.problems:
            if problem.active_plan_id is not MISSING:
                plan = _require_ref(plans, problem.active_plan_id, "active_plan_id")
                _require_same_problem(problem.problem_id, plan.problem_id)
        for plan in self.plans:
            _require_ref(problems, plan.problem_id, "plan.problem_id")
            mode = _require_ref(modes, plan.mode_id, "plan.mode_id")
            planner = _require_ref(jobs, plan.planner_job_id, "plan.planner_job_id")
            _require_same_problem(plan.problem_id, planner.problem_id)
            if planner.role is not JobRole.PLANNER:
                raise PydanticCustomError(
                    "schema_invalid",
                    "planner_job_id must reference a planner job",
                )
            if (
                plan.status is PlanStatus.RULES_GATED
                and mode.rule_state is not AIRuleState.RULES_GATED
            ):
                raise PydanticCustomError(
                    "schema_invalid",
                    "rules_gated plan requires a rules_gated AI mode",
                )
            if plan.status is PlanStatus.RULES_GATED and planner.status is not JobStatus.WAITING:
                raise PydanticCustomError(
                    "schema_invalid",
                    "rules_gated plan requires a waiting planner job",
                )
        for job in self.jobs:
            _require_ref(problems, job.problem_id, "job.problem_id")
            plan = _require_ref(plans, job.plan_id, "job.plan_id")
            _require_same_problem(job.problem_id, plan.problem_id)
            if (
                job.role is JobRole.EVIDENCE
                and job.status is JobStatus.RUNNING
                and plan.status is not PlanStatus.APPROVED
            ):
                raise PydanticCustomError(
                    "schema_invalid",
                    "running evidence job requires an approved plan",
                )
        for candidate in self.candidates:
            _require_ref(problems, candidate.problem_id, "candidate.problem_id")
            creator = _require_ref(jobs, candidate.created_by_job_id, "candidate.created_by_job_id")
            _require_same_problem(candidate.problem_id, creator.problem_id)
            for verification_id in candidate.verification_refs:
                verification = _require_ref(
                    verifications,
                    verification_id,
                    "candidate.verification_refs",
                )
                _require_same_problem(candidate.problem_id, verification.problem_id)
                if (
                    candidate.status
                    in {
                        CandidateStatus.SUBMISSION_READY,
                        CandidateStatus.SUBMITTED,
                    }
                    and verification.status is not VerificationStatus.PASS
                ):
                    raise PydanticCustomError(
                        "schema_invalid",
                        "submission-ready candidate requires passing verifications",
                    )
        for verification in self.verifications:
            candidate = _require_ref(
                candidates,
                verification.candidate_id,
                "verification.candidate_id",
            )
            verifier = _require_ref(jobs, verification.verifier_job_id, "verifier_job_id")
            _require_same_problem(verification.problem_id, candidate.problem_id)
            _require_same_problem(verification.problem_id, verifier.problem_id)
            if verifier.role is not JobRole.VERIFIER:
                raise PydanticCustomError(
                    "schema_invalid",
                    "verifier_job_id must reference a verifier job",
                )
            if candidate.created_by_job_id == verification.verifier_job_id:
                raise PydanticCustomError(
                    "schema_invalid",
                    "candidate creator and verifier must be independent",
                )
            if candidate.created_by_job_id not in verification.independent_from_job_ids:
                raise PydanticCustomError(
                    "schema_invalid",
                    "verification must declare independence from candidate creator",
                )
            for independent_job_id in verification.independent_from_job_ids:
                independent_job = _require_ref(
                    jobs,
                    independent_job_id,
                    "verification.independent_from_job_ids",
                )
                _require_same_problem(verification.problem_id, independent_job.problem_id)
        for submission in self.submissions:
            candidate = _require_ref(candidates, submission.candidate_id, "submission.candidate_id")
            if candidate.status is not CandidateStatus.SUBMITTED:
                raise PydanticCustomError(
                    "schema_invalid",
                    "submission record requires submitted candidate",
                )
        for event in self.events:
            if event.competition_id != manifest.competition_id:
                raise PydanticCustomError(
                    "schema_invalid",
                    "event belongs to another competition",
                )
            if event.problem_id is not MISSING:
                _require_ref(problems, event.problem_id, "event.problem_id")
        for error in self.errors:
            error_problem = None
            if error.problem_id is not MISSING:
                error_problem = _require_ref(problems, error.problem_id, "error.problem_id")
            if error.job_id is not MISSING:
                error_job = _require_ref(jobs, error.job_id, "error.job_id")
                if error_problem is not None:
                    _require_same_problem(error_problem.problem_id, error_job.problem_id)

        return self

    def to_contract_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)


class StateEntity(StrEnum):
    PROBLEM = "problem"
    PLAN = "plan"
    JOB = "job"
    VERIFICATION = "verification"
    CANDIDATE = "candidate"


_TRANSITIONS: dict[StateEntity, dict[str, frozenset[str]]] = {
    StateEntity.PROBLEM: {
        "captured": frozenset({"triaged"}),
        "triaged": frozenset({"queued"}),
        "queued": frozenset({"running"}),
        "running": frozenset({"partial", "verifying", "review_required"}),
        "partial": frozenset({"verifying", "review_required"}),
        "verifying": frozenset({"review_required", "submission_ready"}),
        "review_required": frozenset({"verifying", "submission_ready"}),
        "submission_ready": frozenset({"submitted"}),
        "submitted": frozenset(),
    },
    StateEntity.PLAN: {
        "rules_gated": frozenset({"proposed"}),
        "proposed": frozenset({"approved", "rejected"}),
        "approved": frozenset({"superseded"}),
        "rejected": frozenset(),
        "superseded": frozenset(),
    },
    StateEntity.JOB: {
        "queued": frozenset({"running", "waiting", "cancelled"}),
        "running": frozenset({"waiting", "complete", "partial", "failed", "cancelled"}),
        "waiting": frozenset({"queued", "running", "failed", "cancelled"}),
        "complete": frozenset(),
        "partial": frozenset(),
        "failed": frozenset(),
        "cancelled": frozenset(),
    },
    StateEntity.VERIFICATION: {
        "queued": frozenset({"running"}),
        "running": frozenset({"pass", "fail", "conflict", "incomplete"}),
        "pass": frozenset(),
        "fail": frozenset(),
        "conflict": frozenset(),
        "incomplete": frozenset(),
    },
    StateEntity.CANDIDATE: {
        "draft": frozenset({"review_required", "submission_ready", "rejected"}),
        "review_required": frozenset({"draft", "rejected"}),
        "submission_ready": frozenset({"submitted"}),
        "submitted": frozenset(),
        "rejected": frozenset(),
    },
}


class StateTransition(ContractModel):
    entity: StateEntity
    from_status: SnakeName
    to_status: SnakeName

    @model_validator(mode="after")
    def transition_is_allowed(self) -> "StateTransition":
        allowed = _TRANSITIONS[self.entity].get(self.from_status)
        if allowed is None or self.to_status not in allowed:
            raise PydanticCustomError(
                "invalid_state_transition",
                "state transition is not allowed",
            )
        return self


class OperationsDocument(RootModel[OperationsContractBundle]):
    """Validation entry point for the operations public contract."""

    def to_contract_dict(self) -> dict[str, object]:
        return self.root.to_contract_dict()


def _require_ordered(start: ContractDatetime, finish: ContractDatetime) -> None:
    if finish < start:
        raise PydanticCustomError("schema_invalid", "timestamps are out of order")


def _unique_map[T: ContractModel](items: list[T], field_name: str) -> dict[str, T]:
    mapped: dict[str, T] = {}
    for item in items:
        value = str(getattr(item, field_name))
        if value in mapped:
            raise PydanticCustomError("schema_invalid", f"duplicate {field_name}")
        mapped[value] = item
    return mapped


def _require_ref[T](items: dict[str, T], reference: str, field_name: str) -> T:
    if reference not in items:
        raise PydanticCustomError("schema_invalid", f"unknown reference in {field_name}")
    return items[reference]


def _require_same_problem(expected: str, actual: str) -> None:
    if expected != actual:
        raise PydanticCustomError("schema_invalid", "cross-problem reference is forbidden")
