"""Human-confirmed local submission recording for OPS-IMPL-08."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import StringConstraints

from scan_tool.application.operations_snapshot import CommandResult
from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain._types import ContractModel
from scan_tool.domain.operations import (
    ActorType,
    CandidateId,
    CandidateRecord,
    CandidateStatus,
    CompetitionId,
    CompetitionStatus,
    OperationEvent,
    OperationsDocument,
    ProblemRecord,
    ProblemStatus,
    SubmissionRecord,
    SubmissionResponse,
)

type Clock = Callable[[], datetime]
OperatorId = Annotated[
    str,
    StringConstraints(pattern=r"^operator-[a-z0-9][a-z0-9-]{0,47}$"),
]


class SubmissionCommand(ContractModel):
    competition_id: CompetitionId
    candidate_id: CandidateId
    response: SubmissionResponse
    operator_confirmed: Literal[True]
    actor_id: OperatorId


@dataclass(frozen=True, slots=True)
class SubmissionExecution:
    document: OperationsDocument
    submission: SubmissionRecord
    event: OperationEvent
    command_result: CommandResult


class SubmissionRecorder:
    """Record an external human submission without calling the competition service."""

    def __init__(
        self,
        *,
        guard: SensitiveDataGuard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._guard = guard or SensitiveDataGuard()
        self._clock = clock or (lambda: datetime.now(UTC))

    def record(
        self,
        document: OperationsDocument,
        command: SubmissionCommand,
    ) -> SubmissionExecution:
        self._guard.check_text(command.actor_id)
        bundle = document.root
        if bundle.manifest.competition_id != command.competition_id:
            raise ValueError("competition_scope_mismatch")
        if bundle.manifest.status is not CompetitionStatus.ACTIVE:
            raise ValueError("competition_not_active")
        if any(item.candidate_id == command.candidate_id for item in bundle.submissions):
            raise ValueError("candidate_already_recorded")

        candidate = _candidate(bundle.candidates, command.candidate_id)
        problem = _problem(bundle.problems, candidate.problem_id)
        if candidate.status is not CandidateStatus.SUBMISSION_READY:
            raise ValueError("candidate_not_submission_ready")
        if problem.status is not ProblemStatus.SUBMISSION_READY:
            raise ValueError("problem_not_submission_ready")

        now = self._clock()
        suffix = (
            hashlib.sha256(
                f"{command.competition_id}:{command.candidate_id}:{now.isoformat()}".encode()
            )
            .hexdigest()[:20]
            .upper()
        )
        submission = SubmissionRecord(
            submission_id=f"SUB-{suffix}",
            candidate_id=candidate.candidate_id,
            operator_confirmed=True,
            response=command.response,
            submitted_at=now,
        )
        event = OperationEvent(
            event_id=f"OEV-SUB-{suffix}",
            competition_id=command.competition_id,
            problem_id=problem.problem_id,
            entity_type="submission",
            entity_id=submission.submission_id,
            event_type="submission_recorded",
            actor_type=ActorType.OPERATOR,
            actor_id=command.actor_id,
            from_status=CandidateStatus.SUBMISSION_READY,
            to_status=CandidateStatus.SUBMITTED,
            safe_details_json={
                "candidate_id": candidate.candidate_id,
                "response": command.response.value,
                "external_submission": "human_confirmed",
            },
            created_at=now,
        )
        updated = _updated_document(document, candidate, problem, submission, event, now)
        command_result = CommandResult(
            command_id=f"CMD-SUB-{suffix}",
            accepted=True,
            entity_id=candidate.candidate_id,
            new_status=CandidateStatus.SUBMITTED,
            event_id=event.event_id,
            warnings=["CTFd response was recorded locally; no network submission was made."],
        )
        return SubmissionExecution(
            document=updated,
            submission=submission,
            event=event,
            command_result=command_result,
        )


def _candidate(candidates: list[CandidateRecord], candidate_id: str) -> CandidateRecord:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise ValueError("candidate_not_found")


def _problem(problems: list[ProblemRecord], problem_id: str) -> ProblemRecord:
    for problem in problems:
        if problem.problem_id == problem_id:
            return problem
    raise ValueError("problem_not_found")


def _updated_document(
    document: OperationsDocument,
    candidate: CandidateRecord,
    problem: ProblemRecord,
    submission: SubmissionRecord,
    event: OperationEvent,
    now: datetime,
) -> OperationsDocument:
    bundle = document.root
    updated_candidate = candidate.model_copy(
        update={"status": CandidateStatus.SUBMITTED, "updated_at": now}
    )
    updated_problem = problem.model_copy(
        update={"status": ProblemStatus.SUBMITTED, "updated_at": now}
    )
    updated_manifest = bundle.manifest.model_copy(update={"updated_at": now})
    updated_bundle = bundle.model_copy(
        update={
            "manifest": updated_manifest,
            "problems": [
                updated_problem if item.problem_id == problem.problem_id else item
                for item in bundle.problems
            ],
            "candidates": [
                updated_candidate if item.candidate_id == candidate.candidate_id else item
                for item in bundle.candidates
            ],
            "submissions": [*bundle.submissions, submission],
            "events": [*bundle.events, event],
        }
    )
    return OperationsDocument.model_validate(updated_bundle.model_dump(mode="json", by_alias=True))
