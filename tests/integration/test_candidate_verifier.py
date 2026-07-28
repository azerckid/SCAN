"""OPS-IMPL-06 candidate construction and independent replay verification."""

import asyncio
import copy
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scan_tool.adapters.evidence import InProcessEvidenceWorker
from scan_tool.application.candidate_verifier import (
    CandidateBuildCommand,
    CandidateBuilder,
    CandidatePromotionCommand,
    CandidatePromotionGate,
    EvidenceRun,
    IndependentVerifier,
    VerificationCommand,
)
from scan_tool.application.evidence_worker import ApprovedReplay
from scan_tool.domain import (
    validate_analysis_request,
    validate_analysis_result,
    validate_operations_document,
)
from scan_tool.domain.analysis_request import (
    AnalysisRequest,
    AnalysisType,
    AuthAnalysisRequest,
    DexAnalysisRequest,
    FreezeAnalysisRequest,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.operations import (
    AdapterKind,
    AIExecutionMode,
    AIRuleState,
    AIToolMode,
    CandidateStatus,
    CompetitionEnvironment,
    CompetitionManifest,
    CompetitionPhase,
    CompetitionStatus,
    DataBoundary,
    JobRecord,
    JobRole,
    JobStatus,
    LeafJobSpec,
    OperationErrorCode,
    PlanHypothesis,
    PlanStatus,
    PrioritySource,
    ProblemPriority,
    ProblemRecord,
    ProblemStatus,
    Recommendation,
    VerificationRecord,
    VerificationStatus,
)
from scan_tool.ports.evidence import EvidenceAdapterResponse
from scan_tool.slices.auth import analyze_auth_replay
from scan_tool.slices.dex import analyze_dex_replay
from scan_tool.slices.freeze import analyze_freeze_replay

NOW = datetime(2026, 7, 28, 7, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/05_QA_Validation/examples/analysis"
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = {
    "dex": (
        AnalysisType.DEX_SWAP,
        FIXTURES / "FX-SVC-DEX-001/raw-replay.json",
    ),
    "auth": (
        AnalysisType.AUTH_CONSUMPTION,
        FIXTURES / "FX-EVM-AUTH-001/raw-replay.json",
    ),
    "freeze": (
        AnalysisType.ADDRESS_FREEZE,
        FIXTURES / "FX-EVM-FREEZE-001/raw-replay.json",
    ),
}


class StaticEvidencePort:
    def __init__(
        self,
        response: EvidenceAdapterResponse | None,
        *,
        failure: Exception | None = None,
    ) -> None:
        self.response = response
        self.failure = failure
        self.calls = 0

    async def analyze(
        self,
        *,
        workspace_key: str,
        request: AnalysisRequest,
        replay_body: bytes,
        replay_sha256: str,
    ) -> EvidenceAdapterResponse:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        assert workspace_key
        assert request
        assert replay_body
        assert replay_sha256
        assert self.response is not None
        return self.response


@dataclass(frozen=True, slots=True)
class Scenario:
    manifest: CompetitionManifest
    problem: ProblemRecord
    plan: PlanHypothesis
    evidence_run: EvidenceRun
    reporter_job: JobRecord
    verifier_job: JobRecord


def _request(name: str) -> AnalysisRequest:
    return validate_analysis_request(json.loads((EXAMPLES / f"{name}-request.json").read_text()))


def _result(name: str) -> AnalysisResult:
    request = _request(name)
    replay = _replay(name)
    if isinstance(request.root, DexAnalysisRequest):
        return analyze_dex_replay(request.root, replay.body)
    if isinstance(request.root, AuthAnalysisRequest):
        return analyze_auth_replay(request.root, replay.body)
    if isinstance(request.root, FreezeAnalysisRequest):
        return analyze_freeze_replay(request.root, replay.body)
    raise AssertionError("unsupported test analysis")


def _replay(name: str) -> ApprovedReplay:
    body = CASES[name][1].read_bytes()
    return ApprovedReplay(body=body, sha256=hashlib.sha256(body).hexdigest())


def _job(
    *,
    job_id: str,
    problem_id: str,
    plan_id: str,
    role: JobRole,
    status: JobStatus,
    analysis_id: str | None = None,
) -> JobRecord:
    values: dict[str, object] = {
        "job_id": job_id,
        "problem_id": problem_id,
        "plan_id": plan_id,
        "role": role,
        "job_type": f"{role.value}_work",
        "status": status,
        "priority": ProblemPriority.NORMAL,
        "idempotency_key": hashlib.sha256(job_id.encode()).hexdigest(),
        "attempt": 1,
        "max_attempts": 1,
        "queued_at": NOW,
        "started_at": NOW,
    }
    if analysis_id is not None:
        values["analysis_id"] = analysis_id
    if status in {
        JobStatus.COMPLETE,
        JobStatus.PARTIAL,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }:
        values["finished_at"] = NOW
    return JobRecord.model_validate(values)


def _scenario(name: str = "dex") -> Scenario:
    request = _request(name)
    result = _result(name)
    suffix = name.upper()
    problem_id = f"PROB-{suffix}"
    plan_id = f"PLAN-{suffix}-APPROVED"
    evidence_job = _job(
        job_id=f"JOB-{suffix}-EVIDENCE",
        problem_id=problem_id,
        plan_id=plan_id,
        role=JobRole.EVIDENCE,
        status=JobStatus.COMPLETE,
        analysis_id=request.root.analysis_id,
    )
    reporter_job = _job(
        job_id=f"JOB-{suffix}-REPORTER",
        problem_id=problem_id,
        plan_id=plan_id,
        role=JobRole.REPORTER,
        status=JobStatus.RUNNING,
    )
    verifier_job = _job(
        job_id=f"JOB-{suffix}-VERIFIER",
        problem_id=problem_id,
        plan_id=plan_id,
        role=JobRole.VERIFIER,
        status=JobStatus.RUNNING,
    )
    manifest = CompetitionManifest(
        competition_id="COMP-SCAN-2026",
        operations_schema_version="0.1",
        name="SCAN 2026 candidate verifier QA",
        phase=CompetitionPhase.QUALIFIER,
        environment=CompetitionEnvironment.SYNTHETIC_TEST,
        rules_snapshot_ref="RULES-SNAPSHOT-20260728",
        status=CompetitionStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    problem = ProblemRecord(
        problem_id=problem_id,
        competition_id=manifest.competition_id,
        title=f"{suffix} candidate verification",
        original_text_artifact="artifact://sha256/" + "1" * 64,
        provided_urls=[],
        provided_file_artifacts=[],
        score=100,
        answer_format="structured_analysis",
        priority=ProblemPriority.NORMAL,
        priority_source=PrioritySource.HUMAN,
        status=ProblemStatus.VERIFYING,
        active_plan_id=plan_id,
        created_at=NOW,
        updated_at=NOW,
    )
    plan = PlanHypothesis(
        plan_id=plan_id,
        problem_id=problem_id,
        mode_id=f"MODE-{suffix}-ALLOWED",
        planner_job_id=f"JOB-{suffix}-PLANNER",
        status=PlanStatus.APPROVED,
        problem_type_hypothesis=name,
        method_hypothesis="Replay raw evidence and verify exact result fields.",
        assumptions=[],
        missing_inputs=[],
        leaf_job_specs=[
            LeafJobSpec(
                leaf_job_id=evidence_job.job_id,
                role=JobRole.EVIDENCE,
                purpose="Build deterministic analysis evidence.",
                analysis_type=CASES[name][0],
                inputs_projection=request.root.inputs.model_dump(mode="json"),
                depends_on=[],
                required_capabilities=["offline_replay"],
                expected_output="Analysis I/O 0.1 result",
            )
        ],
        raw_output_artifact="artifact://sha256/" + "2" * 64,
        created_at=NOW,
        decided_at=NOW,
    )
    return Scenario(
        manifest=manifest,
        problem=problem,
        plan=plan,
        evidence_run=EvidenceRun(
            job=evidence_job,
            request=request,
            result=result,
            approved_replay=_replay(name),
        ),
        reporter_job=reporter_job,
        verifier_job=verifier_job,
    )


def _build_command(
    scenario: Scenario,
    *,
    selected_result_ids: tuple[str, ...] | None = None,
    uncertainties: tuple[str, ...] = (),
) -> CandidateBuildCommand:
    available = tuple(result.result_id for result in scenario.evidence_run.result.root.results)
    return CandidateBuildCommand(
        manifest=scenario.manifest,
        problem=scenario.problem,
        plan=scenario.plan,
        reporter_job=scenario.reporter_job,
        evidence_runs=(scenario.evidence_run,),
        candidate_id=f"CAND-{scenario.problem.problem_id.removeprefix('PROB-')}-001",
        selected_result_ids=selected_result_ids or available,
        confidence=90,
        confidence_basis="Selected confirmed Analysis I/O results.",
        uncertainties=uncertainties,
        worker_id="WORKER-REPORTER-01",
        event_id="OEV-CANDIDATE-BUILD-001",
        error_id="OERR-CANDIDATE-BUILD-001",
    )


def _candidate(scenario: Scenario, **kwargs):
    execution = CandidateBuilder(clock=lambda: NOW).build(_build_command(scenario, **kwargs))
    assert execution.error is None
    assert execution.candidate is not None
    return execution.candidate


def _verification_command(
    scenario: Scenario,
    candidate,
) -> VerificationCommand:
    return VerificationCommand(
        manifest=scenario.manifest,
        problem=scenario.problem,
        plan=scenario.plan,
        candidate=candidate,
        reporter_job=scenario.reporter_job,
        verifier_job=scenario.verifier_job,
        evidence_runs=(scenario.evidence_run,),
        verification_id=f"VER-{scenario.problem.problem_id.removeprefix('PROB-')}-001",
        worker_id="WORKER-VERIFIER-01",
        event_id="OEV-VERIFICATION-001",
        error_id="OERR-VERIFICATION-001",
    )


def _promotion_command(scenario: Scenario, candidate, verification):
    return CandidatePromotionCommand(
        manifest=scenario.manifest,
        problem=scenario.problem,
        candidate=candidate,
        verification=verification,
        reporter_job=scenario.reporter_job,
        verifier_job=scenario.verifier_job,
        evidence_runs=(scenario.evidence_run,),
        actor_id="SYSTEM-PROMOTION-GATE",
        event_id="OEV-CANDIDATE-PROMOTE-001",
        error_id="OERR-CANDIDATE-PROMOTE-001",
    )


def test_candidate_builder_derives_evidence_and_stays_draft() -> None:
    scenario = _scenario()
    execution = CandidateBuilder(clock=lambda: NOW).build(_build_command(scenario))

    assert execution.error is None
    assert execution.candidate is not None
    assert execution.candidate.status is CandidateStatus.DRAFT
    assert execution.candidate.verification_refs == []
    assert execution.candidate.result_refs
    assert execution.candidate.evidence_refs
    assert execution.candidate.answer_value.startswith('[{"result_id":')
    assert execution.candidate.recommendation is Recommendation.INVESTIGATE


def test_candidate_builder_rejects_unknown_result_reference() -> None:
    scenario = _scenario()
    execution = CandidateBuilder(clock=lambda: NOW).build(
        _build_command(scenario, selected_result_ids=("RES-UNKNOWN-001",))
    )

    assert execution.candidate is None
    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.VERIFICATION_FAILED
    assert execution.error.details == {"reason": "candidate_evidence_rejected"}


def test_candidate_builder_rejects_cross_problem_evidence() -> None:
    scenario = _scenario("dex")
    other_problem = _scenario("auth")
    command = replace(
        _build_command(scenario),
        evidence_runs=(other_problem.evidence_run,),
    )

    execution = CandidateBuilder(clock=lambda: NOW).build(command)

    assert execution.candidate is None
    assert execution.error is not None
    assert execution.error.details == {"reason": "evidence_problem_mismatch"}


def test_verifier_rejects_cross_problem_evidence_before_adapter() -> None:
    scenario = _scenario("dex")
    other_problem = _scenario("auth")
    candidate = _candidate(scenario)
    port = StaticEvidencePort(_response(other_problem.evidence_run.result))
    command = replace(
        _verification_command(scenario, candidate),
        evidence_runs=(other_problem.evidence_run,),
    )

    execution = asyncio.run(IndependentVerifier(port, clock=lambda: NOW).verify(command))

    assert execution.verification is None
    assert execution.adapter_calls == 0
    assert port.calls == 0
    assert execution.error is not None
    assert execution.error.details == {"reason": "evidence_problem_mismatch"}


def test_independent_dex_replay_passes_all_present_checks(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    verifier = IndependentVerifier(
        InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
        clock=lambda: NOW,
    )

    execution = asyncio.run(verifier.verify(_verification_command(scenario, candidate)))

    assert execution.error is None
    assert execution.adapter_calls == 1
    assert execution.verification is not None
    assert execution.verification.status is VerificationStatus.PASS
    assert set(execution.verification.required_checks) == {
        "answer_format",
        "answer_value",
        "chain_id",
        "result_values",
        "evidence",
        "address",
        "transaction",
        "raw_amount",
        "decimals",
    }
    assert set(execution.verification.independent_from_job_ids) == {
        scenario.reporter_job.job_id,
        scenario.evidence_run.job.job_id,
    }


@pytest.mark.parametrize("name", ("auth", "freeze"))
def test_other_vertical_replays_are_independently_reproduced(
    tmp_path: Path,
    name: str,
) -> None:
    scenario = _scenario(name)
    candidate = _candidate(scenario)

    execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / f"{name}-verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )

    assert execution.error is None
    assert execution.verification is not None
    assert execution.verification.status is VerificationStatus.PASS


def test_pass_verification_promotes_confirmed_candidate(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    verification_execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(
            scenario,
            candidate,
            verification_execution.verification,
        )
    )

    assert promoted.error is None
    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.SUBMISSION_READY
    assert promoted.candidate.recommendation is Recommendation.SUBMIT
    assert promoted.candidate.verification_refs == [
        verification_execution.verification.verification_id
    ]


def test_promoted_candidate_round_trips_in_operations_contract(tmp_path: Path) -> None:
    scenario = _scenario()
    build = CandidateBuilder(clock=lambda: NOW).build(_build_command(scenario))
    assert build.candidate is not None
    verified = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, build.candidate))
    )
    assert verified.verification is not None
    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(scenario, build.candidate, verified.verification)
    )
    assert promoted.candidate is not None
    planner_job = _job(
        job_id=scenario.plan.planner_job_id,
        problem_id=scenario.problem.problem_id,
        plan_id=scenario.plan.plan_id,
        role=JobRole.PLANNER,
        status=JobStatus.COMPLETE,
    )
    mode = AIExecutionMode(
        mode_id=scenario.plan.mode_id,
        competition_id=scenario.manifest.competition_id,
        provider_id="synthetic.local",
        model_id="planner-test",
        adapter_kind=AdapterKind.FAKE_QA,
        data_boundary=DataBoundary.SYNTHETIC_ONLY,
        tool_mode=AIToolMode.PLANNING_ONLY,
        rule_state=AIRuleState.ALLOWED,
        affected_rule_ids=[],
        rules_snapshot_ref=scenario.manifest.rules_snapshot_ref,
        created_at=NOW,
    )
    problem = scenario.problem.model_copy(update={"status": ProblemStatus.SUBMISSION_READY})
    document = validate_operations_document(
        {
            "$schema": "../../schemas/operations-contract.schema.json",
            "operations_schema_version": "0.1",
            "manifest": scenario.manifest.model_dump(mode="json"),
            "problems": [problem.model_dump(mode="json")],
            "ai_modes": [mode.model_dump(mode="json")],
            "plans": [scenario.plan.model_dump(mode="json")],
            "jobs": [
                planner_job.model_dump(mode="json"),
                scenario.evidence_run.job.model_dump(mode="json"),
                scenario.reporter_job.model_dump(mode="json"),
                scenario.verifier_job.model_dump(mode="json"),
            ],
            "verifications": [verified.verification.model_dump(mode="json")],
            "candidates": [promoted.candidate.model_dump(mode="json")],
            "submissions": [],
            "events": [
                build.event.model_dump(mode="json"),
                verified.event.model_dump(mode="json"),
                promoted.event.model_dump(mode="json"),
            ],
            "errors": [],
        }
    )

    assert document.root.candidates[0].status is CandidateStatus.SUBMISSION_READY
    assert document.root.verifications[0].status is VerificationStatus.PASS


def test_tampered_answer_value_conflicts_with_replayed_results(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario).model_copy(
        update={"answer_value": '{"answer":"not-derived-from-evidence"}'}
    )

    execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )

    assert execution.verification is not None
    assert execution.verification.status is VerificationStatus.CONFLICT
    assert "answer_value differs from independent replay" in execution.verification.conflicts


def test_narrow_pass_record_cannot_bypass_required_checks(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    verified = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verified.verification is not None
    answer_format_check = next(
        check for check in verified.verification.check_results if check.check == "answer_format"
    )
    narrow = verified.verification.model_copy(
        update={
            "required_checks": ["answer_format"],
            "check_results": [answer_format_check],
        }
    )

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(scenario, candidate, narrow)
    )

    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_unknown_candidate_reference_is_rejected_without_crashing(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    verified = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verified.verification is not None
    invalid_candidate = candidate.model_copy(
        update={"result_refs": [*candidate.result_refs, "RES-UNKNOWN-001"]}
    )

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(scenario, invalid_candidate, verified.verification)
    )

    assert promoted.candidate is None
    assert promoted.error is not None
    assert promoted.error.details == {"reason": "candidate_scope_rejected"}


def test_promotion_rejects_cross_problem_evidence() -> None:
    scenario = _scenario("dex")
    other_problem = _scenario("auth")
    candidate = _candidate(scenario)
    verification = VerificationRecord(
        verification_id="VER-DEX-CROSS-PROBLEM",
        problem_id=scenario.problem.problem_id,
        candidate_id=candidate.candidate_id,
        verifier_job_id=scenario.verifier_job.job_id,
        status=VerificationStatus.INCOMPLETE,
        required_checks=["independent_replay"],
        check_results=[],
        independent_from_job_ids=[
            scenario.reporter_job.job_id,
            scenario.evidence_run.job.job_id,
        ],
        conflicts=[],
        missing_evidence=list(candidate.evidence_refs),
        created_at=NOW,
        finished_at=NOW,
    )
    command = replace(
        _promotion_command(scenario, candidate, verification),
        evidence_runs=(other_problem.evidence_run,),
    )

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(command)

    assert promoted.candidate is None
    assert promoted.error is not None
    assert promoted.error.details == {"reason": "evidence_plan_mismatch"}


def test_conflicting_replay_is_preserved_and_not_promoted() -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    document = copy.deepcopy(scenario.evidence_run.result.to_contract_dict())
    document["results"][0]["value"]["amount_raw"] = "1"  # type: ignore[index]
    conflicting = validate_analysis_result(document)
    port = StaticEvidencePort(_response(conflicting))

    verification_execution = asyncio.run(
        IndependentVerifier(port, clock=lambda: NOW).verify(
            _verification_command(scenario, candidate)
        )
    )
    assert verification_execution.verification is not None
    verification = verification_execution.verification
    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(scenario, candidate, verification)
    )

    assert verification.status is VerificationStatus.CONFLICT
    assert verification.conflicts
    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED
    assert promoted.candidate.recommendation is Recommendation.INVESTIGATE


def test_official_and_heuristic_labels_are_not_silently_merged() -> None:
    scenario = _scenario("auth")
    document = copy.deepcopy(scenario.evidence_run.result.to_contract_dict())
    heuristic = copy.deepcopy(document["results"][-1])  # type: ignore[index]
    heuristic.update(
        {
            "result_id": "RES-AUTH-HEURISTIC-LABEL",
            "result_type": "address_label",
            "classification": "heuristic",
            "value": {"label": "suspected_spender_cluster"},
        }
    )
    document["results"].append(heuristic)  # type: ignore[union-attr]
    dual_label_result = validate_analysis_result(document)
    evidence_run = replace(scenario.evidence_run, result=dual_label_result)
    scenario = replace(scenario, evidence_run=evidence_run)
    candidate = _candidate(
        scenario,
        selected_result_ids=(
            "RES-AUTH-APPROVAL",
            "RES-AUTH-HEURISTIC-LABEL",
        ),
    )

    verification_execution = asyncio.run(
        IndependentVerifier(
            StaticEvidencePort(_response(_result("auth"))),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None
    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(
            scenario,
            candidate,
            verification_execution.verification,
        )
    )

    assert "RES-AUTH-APPROVAL" in candidate.answer_value
    assert "RES-AUTH-HEURISTIC-LABEL" in candidate.answer_value
    assert verification_execution.verification.status is VerificationStatus.CONFLICT
    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_missing_replay_evidence_is_incomplete_and_not_promoted() -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    document = copy.deepcopy(scenario.evidence_run.result.to_contract_dict())
    old_id = document["evidence"][0]["evidence_id"]  # type: ignore[index]
    new_id = "EV-DEX-INDEPENDENT-REPLACEMENT"
    document["evidence"][0]["evidence_id"] = new_id  # type: ignore[index]
    for result in document["results"]:  # type: ignore[assignment]
        result["evidence_refs"] = [  # type: ignore[index]
            new_id if value == old_id else value
            for value in result["evidence_refs"]  # type: ignore[index]
        ]
    incomplete = validate_analysis_result(document)

    verification_execution = asyncio.run(
        IndependentVerifier(
            StaticEvidencePort(_response(incomplete)),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None
    verification = verification_execution.verification
    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(scenario, candidate, verification)
    )

    assert verification.status is VerificationStatus.INCOMPLETE
    assert old_id in verification.missing_evidence
    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_same_reporter_and_verifier_job_is_rejected_before_adapter() -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    command = replace(
        _verification_command(scenario, candidate),
        verifier_job=scenario.reporter_job,
    )
    port = StaticEvidencePort(_response(scenario.evidence_run.result))

    execution = asyncio.run(IndependentVerifier(port, clock=lambda: NOW).verify(command))

    assert port.calls == 0
    assert execution.adapter_calls == 0
    assert execution.verification is None
    assert execution.error is not None
    assert execution.error.details == {"reason": "verifier_not_independent"}


def test_reused_evidence_result_is_not_independent_verification() -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    port = StaticEvidencePort(_response(scenario.evidence_run.result, reused=True))

    execution = asyncio.run(
        IndependentVerifier(port, clock=lambda: NOW).verify(
            _verification_command(scenario, candidate)
        )
    )

    assert port.calls == 1
    assert execution.verification is not None
    assert execution.verification.status is VerificationStatus.INCOMPLETE
    assert execution.error is not None
    assert execution.error.details == {"reason": "independent_response_invalid"}


def test_uncertainty_keeps_passing_candidate_in_review(tmp_path: Path) -> None:
    scenario = _scenario()
    candidate = _candidate(scenario, uncertainties=("Answer scope needs operator review.",))
    verification_execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(
            scenario,
            candidate,
            verification_execution.verification,
        )
    )

    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_partial_evidence_job_cannot_be_submission_ready(tmp_path: Path) -> None:
    scenario = _scenario()
    partial_job = scenario.evidence_run.job.model_copy(update={"status": JobStatus.PARTIAL})
    scenario = replace(
        scenario,
        evidence_run=replace(scenario.evidence_run, job=partial_job),
    )
    candidate = _candidate(scenario)
    verification_execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None
    assert verification_execution.verification.status is VerificationStatus.PASS

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(
            scenario,
            candidate,
            verification_execution.verification,
        )
    )

    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_not_assessed_result_cannot_be_submission_ready(tmp_path: Path) -> None:
    scenario = _scenario("auth")
    candidate = _candidate(
        scenario,
        selected_result_ids=("RES-AUTH-ATTRIBUTION-SCOPE",),
    )
    verification_execution = asyncio.run(
        IndependentVerifier(
            InProcessEvidenceWorker(tmp_path / "verifier-workspaces"),
            clock=lambda: NOW,
        ).verify(_verification_command(scenario, candidate))
    )
    assert verification_execution.verification is not None
    assert verification_execution.verification.status is VerificationStatus.PASS

    promoted = CandidatePromotionGate(clock=lambda: NOW).promote(
        _promotion_command(
            scenario,
            candidate,
            verification_execution.verification,
        )
    )

    assert promoted.candidate is not None
    assert promoted.candidate.status is CandidateStatus.REVIEW_REQUIRED


def test_verifier_adapter_failure_is_safe_incomplete_record() -> None:
    scenario = _scenario()
    candidate = _candidate(scenario)
    secret = "canary-verifier-secret"
    port = StaticEvidencePort(None, failure=RuntimeError(secret))

    execution = asyncio.run(
        IndependentVerifier(port, clock=lambda: NOW).verify(
            _verification_command(scenario, candidate)
        )
    )
    serialized = json.dumps(
        {
            "verification": (
                execution.verification.model_dump(mode="json") if execution.verification else None
            ),
            "error": execution.error.model_dump(mode="json") if execution.error else None,
            "event": execution.event.model_dump(mode="json"),
        }
    )

    assert execution.adapter_calls == 1
    assert execution.verification is not None
    assert execution.verification.status is VerificationStatus.INCOMPLETE
    assert execution.error is not None
    assert execution.error.details == {"reason": "independent_adapter_failed"}
    assert secret not in serialized
    assert str(ROOT) not in serialized


def _response(
    result: AnalysisResult,
    *,
    reused: bool = False,
) -> EvidenceAdapterResponse:
    return EvidenceAdapterResponse(
        result=result,
        export_uris=(
            "artifact://sha256/" + "3" * 64,
            "artifact://sha256/" + "4" * 64,
        ),
        request_artifact_uri="artifact://sha256/" + "5" * 64,
        replay_artifact_uri="artifact://sha256/" + "6" * 64,
        reused=reused,
    )
