"""Candidate construction and independent replay verification for OPS-IMPL-06."""

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.application.evidence_worker import ApprovedReplay
from scan_tool.application.security import SensitiveDataError, SensitiveDataGuard
from scan_tool.domain import ContractViolation, validate_analysis_pair
from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import (
    AnalysisResult,
    AnalysisStatus,
    Classification,
    Evidence,
    ResultItem,
)
from scan_tool.domain.operations import (
    ActorType,
    CandidateRecord,
    CandidateStatus,
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
    Recommendation,
    VerificationCheck,
    VerificationRecord,
    VerificationStatus,
)
from scan_tool.ports.evidence import EvidenceWorkerPort

type Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class EvidenceRun:
    job: JobRecord
    request: AnalysisRequest
    result: AnalysisResult
    approved_replay: ApprovedReplay


@dataclass(frozen=True, slots=True)
class CandidateBuildCommand:
    manifest: CompetitionManifest
    problem: ProblemRecord
    plan: PlanHypothesis
    reporter_job: JobRecord
    evidence_runs: tuple[EvidenceRun, ...]
    candidate_id: str
    selected_result_ids: tuple[str, ...]
    confidence: int
    confidence_basis: str
    uncertainties: tuple[str, ...]
    worker_id: str
    event_id: str
    error_id: str


@dataclass(frozen=True, slots=True)
class CandidateBuildExecution:
    candidate: CandidateRecord | None
    event: OperationEvent
    error: OperationError | None


@dataclass(frozen=True, slots=True)
class VerificationCommand:
    manifest: CompetitionManifest
    problem: ProblemRecord
    plan: PlanHypothesis
    candidate: CandidateRecord
    reporter_job: JobRecord
    verifier_job: JobRecord
    evidence_runs: tuple[EvidenceRun, ...]
    verification_id: str
    worker_id: str
    event_id: str
    error_id: str


@dataclass(frozen=True, slots=True)
class VerificationExecution:
    verification: VerificationRecord | None
    event: OperationEvent
    error: OperationError | None
    adapter_calls: int


@dataclass(frozen=True, slots=True)
class CandidatePromotionCommand:
    manifest: CompetitionManifest
    problem: ProblemRecord
    candidate: CandidateRecord
    verification: VerificationRecord
    reporter_job: JobRecord
    verifier_job: JobRecord
    evidence_runs: tuple[EvidenceRun, ...]
    actor_id: str
    event_id: str
    error_id: str


@dataclass(frozen=True, slots=True)
class CandidatePromotionExecution:
    candidate: CandidateRecord | None
    event: OperationEvent
    error: OperationError | None


class CandidateBuilder:
    """Build a draft candidate only from scoped Analysis result references."""

    def __init__(
        self,
        *,
        guard: SensitiveDataGuard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._guard = guard or SensitiveDataGuard()
        self._clock = clock or (lambda: datetime.now(UTC))

    def build(self, command: CandidateBuildCommand) -> CandidateBuildExecution:
        reason = _candidate_policy_error(command)
        if reason is not None:
            return self._failed(command, reason)
        try:
            self._guard.check_text(command.confidence_basis)
            for uncertainty in command.uncertainties:
                self._guard.check_text(uncertainty)
            result_map, evidence_map = _scoped_analysis_maps(command.evidence_runs)
            selected_results = _select_results(result_map, command.selected_result_ids)
            evidence_refs = _evidence_refs(selected_results, evidence_map)
            answer_value = _canonical_answer(selected_results)
            self._guard.check_text(answer_value)
            now = self._clock()
            candidate = CandidateRecord(
                candidate_id=command.candidate_id,
                problem_id=command.problem.problem_id,
                answer_format=command.problem.answer_format,
                answer_value=answer_value,
                status=CandidateStatus.DRAFT,
                result_refs=list(command.selected_result_ids),
                evidence_refs=evidence_refs,
                verification_refs=[],
                confidence=command.confidence,
                confidence_basis=command.confidence_basis,
                uncertainties=list(command.uncertainties),
                recommendation=Recommendation.INVESTIGATE,
                created_by_job_id=command.reporter_job.job_id,
                created_at=now,
                updated_at=now,
            )
        except (ValueError, SensitiveDataError):
            return self._failed(command, "candidate_evidence_rejected")
        return CandidateBuildExecution(
            candidate=candidate,
            event=_event(
                command,
                entity_type="candidate",
                entity_id=candidate.candidate_id,
                event_type="candidate_built",
                actor_type=ActorType.WORKER,
                actor_id=command.worker_id,
                to_status=CandidateStatus.DRAFT.value,
                details={
                    "result_refs": list(candidate.result_refs),
                    "evidence_refs": list(candidate.evidence_refs),
                },
                clock=self._clock,
            ),
            error=None,
        )

    def _failed(
        self,
        command: CandidateBuildCommand,
        reason: str,
    ) -> CandidateBuildExecution:
        error = _error(command, reason, command.reporter_job.job_id)
        return CandidateBuildExecution(
            candidate=None,
            event=_event(
                command,
                entity_type="candidate",
                entity_id=command.candidate_id,
                event_type="candidate_build_failed",
                actor_type=ActorType.WORKER,
                actor_id=command.worker_id,
                details={"error_id": error.error_id, "reason": reason},
                clock=self._clock,
            ),
            error=error,
        )


class IndependentVerifier:
    """Replay raw evidence through a verifier-dedicated adapter."""

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

    async def verify(self, command: VerificationCommand) -> VerificationExecution:
        reason = _verification_policy_error(command)
        if reason is not None:
            return self._failed(command, reason, adapter_calls=0)
        try:
            original_results, original_evidence = _scoped_analysis_maps(command.evidence_runs)
            _select_results(original_results, tuple(command.candidate.result_refs))
            if set(command.candidate.evidence_refs) - original_evidence.keys():
                raise ValueError("candidate evidence is outside the scoped analysis")
        except ValueError:
            return self._failed(command, "candidate_scope_rejected", adapter_calls=0)

        replayed: list[AnalysisResult] = []
        adapter_calls = 0
        for run in command.evidence_runs:
            try:
                _validate_replay(run.approved_replay, self._guard)
                adapter_calls += 1
                response = await self._adapter.analyze(
                    workspace_key=command.problem.problem_id,
                    request=run.request,
                    replay_body=run.approved_replay.body,
                    replay_sha256=run.approved_replay.sha256,
                )
            except Exception:
                return self._incomplete(
                    command,
                    reason="independent_adapter_failed",
                    adapter_calls=adapter_calls,
                )
            try:
                if response.reused:
                    raise ValueError("independent verifier cannot reuse an existing result")
                validate_analysis_pair(
                    run.request.to_contract_dict(),
                    response.result.to_contract_dict(),
                )
                replayed.append(response.result)
            except (ContractViolation, ValueError):
                return self._incomplete(
                    command,
                    reason="independent_response_invalid",
                    adapter_calls=adapter_calls,
                )

        replay_results, replay_evidence = _analysis_maps(replayed)
        verification = _build_verification(
            command,
            original_results=original_results,
            original_evidence=original_evidence,
            replay_results=replay_results,
            replay_evidence=replay_evidence,
            replay_documents={item.root.analysis_id: item for item in replayed},
            finished_at=self._clock(),
        )
        return VerificationExecution(
            verification=verification,
            event=_event(
                command,
                entity_type="verification",
                entity_id=verification.verification_id,
                event_type=f"verification_{verification.status.value}",
                actor_type=ActorType.WORKER,
                actor_id=command.worker_id,
                to_status=verification.status.value,
                details={
                    "candidate_id": command.candidate.candidate_id,
                    "required_checks": list(verification.required_checks),
                    "conflicts": list(verification.conflicts),
                    "missing_evidence": list(verification.missing_evidence),
                },
                clock=self._clock,
            ),
            error=None,
            adapter_calls=adapter_calls,
        )

    def _incomplete(
        self,
        command: VerificationCommand,
        *,
        reason: str,
        adapter_calls: int,
    ) -> VerificationExecution:
        finished_at = self._clock()
        verification = VerificationRecord(
            verification_id=command.verification_id,
            problem_id=command.problem.problem_id,
            candidate_id=command.candidate.candidate_id,
            verifier_job_id=command.verifier_job.job_id,
            status=VerificationStatus.INCOMPLETE,
            required_checks=["independent_replay"],
            check_results=[],
            independent_from_job_ids=_independent_job_ids(command),
            conflicts=[],
            missing_evidence=list(command.candidate.evidence_refs),
            created_at=command.verifier_job.started_at
            if command.verifier_job.started_at is not MISSING
            else finished_at,
            finished_at=finished_at,
        )
        error = _error(command, reason, command.verifier_job.job_id)
        return VerificationExecution(
            verification=verification,
            event=_event(
                command,
                entity_type="verification",
                entity_id=verification.verification_id,
                event_type="verification_incomplete",
                actor_type=ActorType.WORKER,
                actor_id=command.worker_id,
                to_status=VerificationStatus.INCOMPLETE.value,
                details={"error_id": error.error_id, "reason": reason},
                clock=self._clock,
            ),
            error=error,
            adapter_calls=adapter_calls,
        )

    def _failed(
        self,
        command: VerificationCommand,
        reason: str,
        *,
        adapter_calls: int,
    ) -> VerificationExecution:
        error = _error(command, reason, command.verifier_job.job_id)
        return VerificationExecution(
            verification=None,
            event=_event(
                command,
                entity_type="verification",
                entity_id=command.verification_id,
                event_type="verification_rejected",
                actor_type=ActorType.WORKER,
                actor_id=command.worker_id,
                details={"error_id": error.error_id, "reason": reason},
                clock=self._clock,
            ),
            error=error,
            adapter_calls=adapter_calls,
        )


class CandidatePromotionGate:
    """Promote only independently verified, fully evidenced candidates."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def promote(
        self,
        command: CandidatePromotionCommand,
    ) -> CandidatePromotionExecution:
        reason = _promotion_policy_error(command)
        if reason is not None:
            return self._failed(command, reason)
        try:
            result_map, evidence_map = _scoped_analysis_maps(command.evidence_runs)
            _select_results(result_map, tuple(command.candidate.result_refs))
            if set(command.candidate.evidence_refs) - evidence_map.keys():
                raise ValueError("candidate evidence is outside the scoped analysis")
        except ValueError:
            return self._failed(command, "candidate_scope_rejected")

        verification_refs = list(
            dict.fromkeys(
                [
                    *command.candidate.verification_refs,
                    command.verification.verification_id,
                ]
            )
        )
        try:
            ready = _verification_allows_promotion(command)
        except ValueError:
            return self._failed(command, "candidate_scope_rejected")
        candidate = command.candidate.model_copy(
            update={
                "status": (
                    CandidateStatus.SUBMISSION_READY if ready else CandidateStatus.REVIEW_REQUIRED
                ),
                "verification_refs": verification_refs,
                "recommendation": (Recommendation.SUBMIT if ready else Recommendation.INVESTIGATE),
                "updated_at": self._clock(),
            }
        )
        return CandidatePromotionExecution(
            candidate=CandidateRecord.model_validate(candidate.model_dump(mode="json")),
            event=_event(
                command,
                entity_type="candidate",
                entity_id=candidate.candidate_id,
                event_type=("candidate_promoted" if ready else "candidate_review_required"),
                actor_type=ActorType.SYSTEM,
                actor_id=command.actor_id,
                from_status=command.candidate.status.value,
                to_status=candidate.status.value,
                details={"verification_id": command.verification.verification_id},
                clock=self._clock,
            ),
            error=None,
        )

    def _failed(
        self,
        command: CandidatePromotionCommand,
        reason: str,
    ) -> CandidatePromotionExecution:
        error = _error(command, reason, command.verifier_job.job_id)
        return CandidatePromotionExecution(
            candidate=None,
            event=_event(
                command,
                entity_type="candidate",
                entity_id=command.candidate.candidate_id,
                event_type="candidate_promotion_rejected",
                actor_type=ActorType.SYSTEM,
                actor_id=command.actor_id,
                from_status=command.candidate.status.value,
                details={"error_id": error.error_id, "reason": reason},
                clock=self._clock,
            ),
            error=error,
        )


def _candidate_policy_error(command: CandidateBuildCommand) -> str | None:
    common = _common_policy_error(command)
    if common is not None:
        return common
    job = command.reporter_job
    if job.role is not JobRole.REPORTER or job.status not in {
        JobStatus.RUNNING,
        JobStatus.COMPLETE,
    }:
        return "reporter_job_invalid"
    if not command.selected_result_ids:
        return "selected_results_required"
    return _evidence_run_policy_error(
        command.problem,
        command.plan,
        command.evidence_runs,
    )


def _verification_policy_error(command: VerificationCommand) -> str | None:
    common = _common_policy_error(command)
    if common is not None:
        return common
    if command.candidate.problem_id != command.problem.problem_id:
        return "candidate_problem_mismatch"
    if command.candidate.status not in {
        CandidateStatus.DRAFT,
        CandidateStatus.REVIEW_REQUIRED,
    }:
        return "candidate_status_invalid"
    if command.candidate.created_by_job_id != command.reporter_job.job_id:
        return "candidate_creator_mismatch"
    if (
        command.reporter_job.role is not JobRole.REPORTER
        or command.reporter_job.problem_id != command.problem.problem_id
        or command.reporter_job.plan_id != command.plan.plan_id
    ):
        return "reporter_job_invalid"
    if command.verifier_job.job_id == command.reporter_job.job_id:
        return "verifier_not_independent"
    if command.verifier_job.role is not JobRole.VERIFIER:
        return "verifier_role_invalid"
    if (
        command.verifier_job.problem_id != command.problem.problem_id
        or command.verifier_job.plan_id != command.plan.plan_id
    ):
        return "verifier_scope_invalid"
    if command.verifier_job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
        return "verifier_status_invalid"
    return _evidence_run_policy_error(
        command.problem,
        command.plan,
        command.evidence_runs,
    )


def _promotion_policy_error(command: CandidatePromotionCommand) -> str | None:
    if command.manifest.status is not CompetitionStatus.ACTIVE:
        return "competition_not_active"
    if command.problem.competition_id != command.manifest.competition_id:
        return "competition_scope_mismatch"
    if command.candidate.problem_id != command.problem.problem_id:
        return "candidate_problem_mismatch"
    if command.verification.problem_id != command.problem.problem_id:
        return "verification_problem_mismatch"
    if command.verification.candidate_id != command.candidate.candidate_id:
        return "verification_candidate_mismatch"
    if command.reporter_job.job_id != command.candidate.created_by_job_id:
        return "candidate_creator_mismatch"
    if command.verifier_job.job_id != command.verification.verifier_job_id:
        return "verifier_job_mismatch"
    if command.verifier_job.job_id == command.reporter_job.job_id:
        return "verifier_not_independent"
    if command.candidate.status not in {
        CandidateStatus.DRAFT,
        CandidateStatus.REVIEW_REQUIRED,
    }:
        return "candidate_status_invalid"
    if (
        command.reporter_job.role is not JobRole.REPORTER
        or command.reporter_job.problem_id != command.problem.problem_id
        or command.reporter_job.plan_id != command.verifier_job.plan_id
    ):
        return "reporter_job_invalid"
    if (
        command.verifier_job.role is not JobRole.VERIFIER
        or command.verifier_job.problem_id != command.problem.problem_id
        or command.reporter_job.job_id not in command.verification.independent_from_job_ids
    ):
        return "verifier_job_invalid"
    if any(run.job.problem_id != command.problem.problem_id for run in command.evidence_runs):
        return "evidence_problem_mismatch"
    if any(run.job.plan_id != command.reporter_job.plan_id for run in command.evidence_runs):
        return "evidence_plan_mismatch"
    return _evidence_run_policy_error(
        command.problem,
        None,
        command.evidence_runs,
    )


def _common_policy_error(
    command: CandidateBuildCommand | VerificationCommand,
) -> str | None:
    if command.manifest.status is not CompetitionStatus.ACTIVE:
        return "competition_not_active"
    if command.problem.competition_id != command.manifest.competition_id:
        return "competition_scope_mismatch"
    if command.problem.status not in {
        ProblemStatus.RUNNING,
        ProblemStatus.PARTIAL,
        ProblemStatus.VERIFYING,
        ProblemStatus.REVIEW_REQUIRED,
    }:
        return "problem_status_invalid"
    if command.plan.status is not PlanStatus.APPROVED:
        return "plan_not_approved"
    if command.problem.active_plan_id != command.plan.plan_id:
        return "plan_not_active"
    if command.plan.problem_id != command.problem.problem_id:
        return "plan_problem_mismatch"
    return None


def _evidence_run_policy_error(
    problem: ProblemRecord,
    plan: PlanHypothesis | None,
    runs: tuple[EvidenceRun, ...],
) -> str | None:
    if not runs:
        return "evidence_runs_required"
    for run in runs:
        if run.job.problem_id != problem.problem_id:
            return "evidence_problem_mismatch"
        if plan is not None and run.job.plan_id != plan.plan_id:
            return "evidence_plan_mismatch"
        if run.job.role is not JobRole.EVIDENCE:
            return "evidence_role_invalid"
        if run.job.status not in {JobStatus.COMPLETE, JobStatus.PARTIAL}:
            return "evidence_status_invalid"
        if run.job.analysis_id is MISSING:
            return "evidence_analysis_missing"
        if run.job.analysis_id != run.request.root.analysis_id:
            return "evidence_request_mismatch"
        if run.result.root.analysis_id != run.request.root.analysis_id:
            return "evidence_result_mismatch"
        if run.result.root.status is AnalysisStatus.FAILED:
            return "failed_analysis_has_no_candidate_evidence"
    return None


def _verification_allows_promotion(command: CandidatePromotionCommand) -> bool:
    verification = command.verification
    if verification.status is not VerificationStatus.PASS:
        return False
    if any(
        run.job.status is not JobStatus.COMPLETE
        or run.result.root.status is not AnalysisStatus.COMPLETE
        for run in command.evidence_runs
    ):
        return False
    if command.candidate.uncertainties:
        return False
    if command.reporter_job.job_id not in verification.independent_from_job_ids:
        return False
    evidence_job_ids = {run.job.job_id for run in command.evidence_runs}
    if not evidence_job_ids <= set(verification.independent_from_job_ids):
        return False
    result_refs = {
        result_ref
        for check in verification.check_results
        if check.passed
        for result_ref in check.result_refs
    }
    evidence_refs = {
        evidence_ref
        for check in verification.check_results
        if check.passed
        for evidence_ref in check.evidence_refs
    }
    if set(command.candidate.result_refs) - result_refs:
        return False
    if set(command.candidate.evidence_refs) - evidence_refs:
        return False
    result_map, evidence_map = _scoped_analysis_maps(command.evidence_runs)
    selected_results = _select_results(
        result_map,
        tuple(command.candidate.result_refs),
    )
    selected_evidence = [
        evidence_map[evidence_id] for evidence_id in command.candidate.evidence_refs
    ]
    required_checks = set(_required_checks(selected_results, selected_evidence))
    passed_checks = {check.check for check in verification.check_results if check.passed}
    if required_checks - passed_checks:
        return False
    if command.candidate.answer_value != _canonical_answer(selected_results):
        return False
    return all(
        result_map[result_id].classification is Classification.CONFIRMED_FACT
        for result_id in command.candidate.result_refs
    )


def _build_verification(
    command: VerificationCommand,
    *,
    original_results: dict[str, ResultItem],
    original_evidence: dict[str, Evidence],
    replay_results: dict[str, ResultItem],
    replay_evidence: dict[str, Evidence],
    replay_documents: dict[str, AnalysisResult],
    finished_at: datetime,
) -> VerificationRecord:
    selected_results = _select_results(
        original_results,
        tuple(command.candidate.result_refs),
    )
    selected_evidence = [
        original_evidence[evidence_id] for evidence_id in command.candidate.evidence_refs
    ]
    required_checks = _required_checks(selected_results, selected_evidence)

    result_matches = all(
        result_id in replay_results
        and original_results[result_id].model_dump(mode="json")
        == replay_results[result_id].model_dump(mode="json")
        for result_id in command.candidate.result_refs
    )
    evidence_matches = all(
        evidence_id in replay_evidence
        and original_evidence[evidence_id].model_dump(mode="json")
        == replay_evidence[evidence_id].model_dump(mode="json")
        for evidence_id in command.candidate.evidence_refs
    )
    replay_selected_results = (
        [replay_results[result_id] for result_id in command.candidate.result_refs]
        if not (set(command.candidate.result_refs) - replay_results.keys())
        else []
    )
    base_pass = {
        "answer_format": command.candidate.answer_format == command.problem.answer_format,
        "answer_value": bool(replay_selected_results)
        and command.candidate.answer_value == _canonical_answer(replay_selected_results),
        "chain_id": all(
            run.result.root.analysis_id in replay_documents
            and run.result.root.chain_id
            == replay_documents[run.result.root.analysis_id].root.chain_id
            for run in command.evidence_runs
        ),
        "result_values": result_matches,
        "evidence": evidence_matches,
        "address": result_matches,
        "transaction": evidence_matches,
        "raw_amount": result_matches,
        "decimals": result_matches,
    }
    check_results = [
        VerificationCheck(
            check=check,
            passed=base_pass[check],
            result_refs=list(command.candidate.result_refs),
            evidence_refs=list(command.candidate.evidence_refs),
        )
        for check in required_checks
    ]
    missing_evidence = [
        evidence_id
        for evidence_id in command.candidate.evidence_refs
        if evidence_id not in replay_evidence
    ]
    conflicts = [
        f"{check} differs from independent replay"
        for check in required_checks
        if not base_pass[check] and not (check == "evidence" and missing_evidence)
    ]
    if missing_evidence:
        status = VerificationStatus.INCOMPLETE
    elif conflicts or not all(base_pass[check] for check in required_checks):
        status = VerificationStatus.CONFLICT
    else:
        status = VerificationStatus.PASS
    return VerificationRecord(
        verification_id=command.verification_id,
        problem_id=command.problem.problem_id,
        candidate_id=command.candidate.candidate_id,
        verifier_job_id=command.verifier_job.job_id,
        status=status,
        required_checks=required_checks,
        check_results=check_results,
        independent_from_job_ids=_independent_job_ids(command),
        conflicts=conflicts,
        missing_evidence=missing_evidence,
        created_at=command.verifier_job.started_at
        if command.verifier_job.started_at is not MISSING
        else finished_at,
        finished_at=finished_at,
    )


def _scoped_analysis_maps(
    runs: tuple[EvidenceRun, ...],
) -> tuple[dict[str, ResultItem], dict[str, Evidence]]:
    return _analysis_maps([run.result for run in runs])


def _analysis_maps(
    results: Iterable[AnalysisResult],
) -> tuple[dict[str, ResultItem], dict[str, Evidence]]:
    result_map: dict[str, ResultItem] = {}
    evidence_map: dict[str, Evidence] = {}
    for document in results:
        for result in document.root.results:
            if result.result_id in result_map:
                raise ValueError("duplicate result_id across evidence runs")
            result_map[result.result_id] = result
        for evidence in document.root.evidence:
            if evidence.evidence_id in evidence_map:
                raise ValueError("duplicate evidence_id across evidence runs")
            evidence_map[evidence.evidence_id] = evidence
    return result_map, evidence_map


def _select_results(
    result_map: dict[str, ResultItem],
    selected_result_ids: tuple[str, ...],
) -> list[ResultItem]:
    if len(selected_result_ids) != len(set(selected_result_ids)):
        raise ValueError("duplicate selected result")
    if set(selected_result_ids) - result_map.keys():
        raise ValueError("selected result is outside the scoped analysis")
    return [result_map[result_id] for result_id in selected_result_ids]


def _evidence_refs(
    selected_results: list[ResultItem],
    evidence_map: dict[str, Evidence],
) -> list[str]:
    refs = list(
        dict.fromkeys(
            evidence_id for result in selected_results for evidence_id in result.evidence_refs
        )
    )
    if not refs or set(refs) - evidence_map.keys():
        raise ValueError("selected result evidence is incomplete")
    return refs


def _independent_job_ids(command: VerificationCommand) -> list[str]:
    return list(
        dict.fromkeys(
            [
                command.reporter_job.job_id,
                *(run.job.job_id for run in command.evidence_runs),
            ]
        )
    )


def _required_checks(
    selected_results: list[ResultItem],
    selected_evidence: list[Evidence],
) -> list[str]:
    required = [
        "answer_format",
        "answer_value",
        "chain_id",
        "result_values",
        "evidence",
    ]
    candidate_values = [item.value for item in selected_results]
    if _named_values(candidate_values, _is_address):
        required.append("address")
    if any(item.locator.transaction_hash is not MISSING for item in selected_evidence):
        required.append("transaction")
    if _named_values(candidate_values, lambda key, _: key.endswith("_raw")):
        required.append("raw_amount")
    if _named_values(candidate_values, lambda key, _: key == "decimals"):
        required.append("decimals")
    return required


def _canonical_answer(selected_results: list[ResultItem]) -> str:
    return json.dumps(
        [
            {
                "result_id": result.result_id,
                "result_type": result.result_type,
                "value": result.value,
            }
            for result in selected_results
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def _named_values(
    value: Any,
    predicate: Callable[[str, Any], bool],
) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if predicate(key, nested):
                found.append(nested)
            found.extend(_named_values(nested, predicate))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_named_values(nested, predicate))
    return found


def _is_address(_: str, value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 42
        and value.startswith("0x")
        and all(character in "0123456789abcdef" for character in value[2:].lower())
    )


def _validate_replay(replay: ApprovedReplay, guard: SensitiveDataGuard) -> None:
    if hashlib.sha256(replay.body).hexdigest() != replay.sha256:
        raise ValueError("approved replay hash mismatch")
    guard.check_bytes(replay.body)


def _event(
    command: CandidateBuildCommand | VerificationCommand | CandidatePromotionCommand,
    *,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_type: ActorType,
    actor_id: str,
    details: dict[str, object],
    clock: Clock,
    from_status: str | None = None,
    to_status: str | None = None,
) -> OperationEvent:
    values: dict[str, object] = {
        "event_id": command.event_id,
        "competition_id": command.manifest.competition_id,
        "problem_id": command.problem.problem_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "safe_details_json": details,
        "created_at": clock(),
    }
    if from_status is not None:
        values["from_status"] = from_status
    if to_status is not None:
        values["to_status"] = to_status
    return OperationEvent.model_validate(values)


def _error(
    command: CandidateBuildCommand | VerificationCommand | CandidatePromotionCommand,
    reason: str,
    job_id: str,
) -> OperationError:
    return OperationError(
        error_id=command.error_id,
        code=OperationErrorCode.VERIFICATION_FAILED,
        message="Candidate construction or verification was rejected or failed.",
        stage=OperationErrorStage.VERIFICATION,
        retryable=False,
        problem_id=command.problem.problem_id,
        job_id=job_id,
        details={"reason": reason},
    )
