"""OPS-IMPL-05 in-process DEX, AUTH, and FREEZE Evidence Worker tests."""

import asyncio
import copy
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scan_tool.adapters.evidence import InProcessEvidenceWorker
from scan_tool.application.cli_runtime import AnalysisUnavailable, CliRuntime
from scan_tool.application.evidence_worker import (
    ApprovedReplay,
    EvidenceQueueExecutor,
    EvidenceWorkerCommand,
    EvidenceWorkerService,
)
from scan_tool.application.scheduler import BoundedJobScheduler
from scan_tool.domain import validate_analysis_request, validate_analysis_result
from scan_tool.domain.analysis_request import AnalysisRequest, AnalysisType, RuleStatus
from scan_tool.domain.analysis_result import AnalysisResult, AnalysisStatus
from scan_tool.domain.operations import (
    CompetitionEnvironment,
    CompetitionManifest,
    CompetitionPhase,
    CompetitionStatus,
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
)
from scan_tool.ports.evidence import EvidenceAdapterResponse

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


def _request(name: str) -> AnalysisRequest:
    return validate_analysis_request(json.loads((EXAMPLES / f"{name}-request.json").read_text()))


def _replay(name: str) -> ApprovedReplay:
    body = CASES[name][1].read_bytes()
    return ApprovedReplay(body=body, sha256=hashlib.sha256(body).hexdigest())


def _command(
    name: str,
    *,
    request: AnalysisRequest | None = None,
    replay: ApprovedReplay | None = None,
    plan_status: PlanStatus = PlanStatus.APPROVED,
    job_status: JobStatus = JobStatus.QUEUED,
) -> EvidenceWorkerCommand:
    selected_request = request or _request(name)
    analysis_type = CASES[name][0]
    suffix = name.upper()
    problem_id = f"PROB-{suffix}"
    plan_id = f"PLAN-{suffix}-ACTIVE"
    job_id = f"JOB-{suffix}-EVIDENCE"
    manifest = CompetitionManifest(
        competition_id="COMP-SCAN-2026",
        operations_schema_version="0.1",
        name="SCAN 2026 synthetic evidence QA",
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
        title=f"{suffix} fixture replay",
        original_text_artifact="artifact://sha256/" + "1" * 64,
        provided_urls=[],
        provided_file_artifacts=[],
        score=100,
        answer_format="structured_analysis",
        priority=ProblemPriority.NORMAL,
        priority_source=PrioritySource.HUMAN,
        status=ProblemStatus.QUEUED,
        active_plan_id=plan_id,
        created_at=NOW,
        updated_at=NOW,
    )
    leaf = LeafJobSpec(
        leaf_job_id=job_id,
        role=JobRole.EVIDENCE,
        purpose=f"Execute {name} fixture evidence replay",
        analysis_type=analysis_type,
        inputs_projection=selected_request.root.inputs.model_dump(mode="json"),
        depends_on=[],
        required_capabilities=[f"{name}_replay"],
        expected_output="Analysis I/O result with evidence and source records",
    )
    plan = PlanHypothesis(
        plan_id=plan_id,
        problem_id=problem_id,
        mode_id="MODE-LOCAL-QA",
        planner_job_id=f"JOB-{suffix}-PLANNER",
        status=plan_status,
        problem_type_hypothesis=f"{name}_fixture",
        method_hypothesis=f"Replay approved {name} evidence with the Python analyzer",
        assumptions=[],
        missing_inputs=[],
        leaf_job_specs=[leaf],
        raw_output_artifact="artifact://sha256/" + "2" * 64,
        created_at=NOW,
        decided_at=NOW,
    )
    job = JobRecord(
        job_id=job_id,
        problem_id=problem_id,
        plan_id=plan_id,
        role=JobRole.EVIDENCE,
        job_type=f"{name}_evidence",
        status=job_status,
        priority=ProblemPriority.NORMAL,
        idempotency_key=hashlib.sha256(f"{name}:evidence".encode()).hexdigest(),
        analysis_id=selected_request.root.analysis_id,
        attempt=0,
        max_attempts=2,
        queued_at=NOW,
    )
    return EvidenceWorkerCommand(
        manifest=manifest,
        problem=problem,
        plan=plan,
        job=job,
        request=selected_request,
        approved_replay=replay or _replay(name),
        worker_id=f"WORKER-{suffix}-01",
        event_id=f"OEV-{suffix}-EVIDENCE",
        error_id=f"OERR-{suffix}-EVIDENCE",
    )


def _service(tmp_path: Path, port=None) -> EvidenceWorkerService:
    return EvidenceWorkerService(
        port or InProcessEvidenceWorker(tmp_path / "workspaces"),
        clock=lambda: NOW,
    )


@pytest.mark.parametrize("name", ("dex", "auth", "freeze"))
def test_confirmed_fixture_runs_through_in_process_worker(
    tmp_path: Path,
    name: str,
) -> None:
    command = _command(name)
    execution = asyncio.run(_service(tmp_path).execute(command))

    assert execution.adapter_called is True
    assert execution.reused is False
    assert execution.error is None
    assert execution.result is not None
    assert execution.result.root.status is AnalysisStatus.COMPLETE
    assert execution.worker_outcome.status is JobStatus.COMPLETE
    assert execution.result.root.analysis_id == command.request.root.analysis_id
    assert execution.result.root.analysis_type is CASES[name][0]
    assert execution.result.root.results
    assert execution.result.root.evidence
    assert execution.result.root.sources
    assert all(evidence.raw_artifact.artifact_uri for evidence in execution.result.root.evidence)
    assert execution.request_artifact_uri is not None
    assert execution.request_artifact_uri.startswith("artifact://sha256/")
    assert execution.replay_artifact_uri is not None
    assert execution.replay_artifact_uri.startswith("artifact://sha256/")
    assert all(uri.startswith("artifact://sha256/") for uri in execution.export_uris)
    assert execution.event.safe_details_json["analysis_id"] == command.request.root.analysis_id
    assert execution.event.safe_details_json["result_ids"]
    assert execution.event.safe_details_json["evidence_ids"]
    assert execution.event.safe_details_json["source_record_ids"]
    workspace = tmp_path / "workspaces" / command.problem.problem_id
    assert (workspace / "scan.sqlite3").exists()


def test_three_vertical_workers_connect_to_bounded_scheduler(tmp_path: Path) -> None:
    commands = {command.job.job_id: command for command in map(_command, CASES)}
    queue_executor = EvidenceQueueExecutor(_service(tmp_path), commands)
    scheduler = BoundedJobScheduler(queue_executor)

    scheduled = asyncio.run(scheduler.execute([command.job for command in commands.values()]))

    assert all(result.status is JobStatus.COMPLETE for result in scheduled.results)
    assert scheduled.max_observed_active_problems == 3
    executions = [queue_executor.execution_for(command.job.job_id) for command in commands.values()]
    assert (
        len({execution.result.root.analysis_id for execution in executions if execution.result})
        == 3
    )
    assert len({command.problem.problem_id for command in commands.values()}) == 3
    for command in commands.values():
        assert (tmp_path / command.problem.problem_id / "scan.sqlite3").exists() is False
        assert (tmp_path / "workspaces" / command.problem.problem_id / "scan.sqlite3").exists()


def test_completed_analysis_is_reused_without_duplicate_rows(tmp_path: Path) -> None:
    command = _command("dex")
    service = _service(tmp_path)

    first = asyncio.run(service.execute(command))
    second = asyncio.run(service.execute(command))

    assert first.reused is False
    assert second.reused is True
    assert first.result is not None
    assert second.result is not None
    assert first.result.to_contract_dict() == second.result.to_contract_dict()
    assert first.export_uris == second.export_uris
    assert second.event.safe_details_json["reused"] is True


def test_completed_analysis_reuse_rejects_changed_approved_replay(
    tmp_path: Path,
) -> None:
    command = _command("dex")
    service = _service(tmp_path)
    first = asyncio.run(service.execute(command))
    changed_body = b"{}"
    changed = replace(
        command,
        approved_replay=ApprovedReplay(
            body=changed_body,
            sha256=hashlib.sha256(changed_body).hexdigest(),
        ),
    )

    second = asyncio.run(service.execute(changed))

    assert first.worker_outcome.status is JobStatus.COMPLETE
    assert second.worker_outcome.status is JobStatus.FAILED
    assert second.adapter_called is True
    assert second.reused is False
    assert second.error is not None
    assert second.error.code is OperationErrorCode.EVIDENCE_WORKER_FAILED


@pytest.mark.parametrize(
    "reason",
    (
        "hash",
        "restricted",
        "unapproved_plan",
        "projection_mismatch",
        "paused_competition",
    ),
)
def test_pre_call_gate_rejects_invalid_execution(
    tmp_path: Path,
    reason: str,
) -> None:
    response = _static_response("dex")
    port = StaticEvidencePort(response)
    command = _command("dex")
    if reason == "hash":
        command = replace(
            command,
            approved_replay=ApprovedReplay(
                body=command.approved_replay.body,
                sha256="0" * 64,
            ),
        )
        expected_code = OperationErrorCode.EVIDENCE_WORKER_FAILED
    elif reason == "restricted":
        document = command.request.to_contract_dict()
        document["source_policy"]["rule_status"] = RuleStatus.RESTRICTED.value
        command = _command("dex", request=validate_analysis_request(document))
        expected_code = OperationErrorCode.RULE_RESTRICTED
    elif reason == "unapproved_plan":
        command = _command("dex", plan_status=PlanStatus.PROPOSED)
        expected_code = OperationErrorCode.INVALID_OPERATIONS_INPUT
    elif reason == "projection_mismatch":
        leaf = command.plan.leaf_job_specs[0].model_copy(
            update={"inputs_projection": {"unexpected": "input"}}
        )
        command = replace(
            command,
            plan=command.plan.model_copy(update={"leaf_job_specs": [leaf]}),
        )
        expected_code = OperationErrorCode.INVALID_OPERATIONS_INPUT
    else:
        command = replace(
            command,
            manifest=command.manifest.model_copy(update={"status": CompetitionStatus.PAUSED}),
        )
        expected_code = OperationErrorCode.INVALID_OPERATIONS_INPUT

    execution = asyncio.run(_service(tmp_path, port).execute(command))

    assert port.calls == 0
    assert execution.adapter_called is False
    assert execution.error is not None
    assert execution.error.code is expected_code
    assert execution.worker_outcome.status is JobStatus.FAILED
    assert execution.result is None


def test_partial_analysis_maps_to_partial_job_and_preserves_error() -> None:
    response = _static_response("dex", status=AnalysisStatus.PARTIAL)
    port = StaticEvidencePort(response)
    command = _command("dex")

    execution = asyncio.run(EvidenceWorkerService(port, clock=lambda: NOW).execute(command))

    assert execution.error is None
    assert execution.result is not None
    assert execution.result.root.status is AnalysisStatus.PARTIAL
    assert execution.worker_outcome.status is JobStatus.PARTIAL
    assert execution.worker_outcome.error_code == "evidence_incomplete"
    assert execution.event.to_status == JobStatus.PARTIAL


def test_adapter_exception_is_redacted_from_error_and_event() -> None:
    secret = "canary-adapter-secret"
    port = StaticEvidencePort(None, failure=RuntimeError(secret))
    command = _command("dex")

    execution = asyncio.run(EvidenceWorkerService(port, clock=lambda: NOW).execute(command))
    serialized = json.dumps(
        {
            "error": execution.error.model_dump(mode="json") if execution.error else None,
            "event": execution.event.model_dump(mode="json"),
        }
    )

    assert execution.adapter_called is True
    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.EVIDENCE_WORKER_FAILED
    assert secret not in serialized
    assert str(ROOT) not in serialized


def test_queue_executor_rejects_unregistered_or_changed_job(tmp_path: Path) -> None:
    command = _command("dex")
    executor = EvidenceQueueExecutor(_service(tmp_path), {command.job.job_id: command})
    other = _command("auth").job
    changed = command.job.model_copy(update={"max_attempts": 1})

    missing = asyncio.run(executor(other, 1))
    mismatch = asyncio.run(executor(changed, 1))

    assert missing.status is JobStatus.FAILED
    assert mismatch.status is JobStatus.FAILED
    assert missing.error_code == OperationErrorCode.INVALID_OPERATIONS_INPUT.value
    assert mismatch.error_code == OperationErrorCode.INVALID_OPERATIONS_INPUT.value


def test_checkpoint_rejects_changed_approved_replay(tmp_path: Path) -> None:
    request = _request("dex")
    replay_body = _replay("dex").body
    replay_sha256 = hashlib.sha256(replay_body).hexdigest()

    with CliRuntime.open(tmp_path / ".scan") as runtime:
        runtime.register_request(request)
        runtime.execute_analysis(
            request,
            replay_body=replay_body,
            expected_replay_sha256=replay_sha256,
        )

        changed_replay = b"{}"
        with pytest.raises(AnalysisUnavailable, match="saved replay"):
            runtime.execute_analysis(
                request,
                replay_body=changed_replay,
                expected_replay_sha256=hashlib.sha256(changed_replay).hexdigest(),
            )


def _static_response(
    name: str,
    *,
    status: AnalysisStatus = AnalysisStatus.COMPLETE,
) -> EvidenceAdapterResponse:
    document = copy.deepcopy(json.loads((EXAMPLES / f"{name}-result.json").read_text()))
    if status is AnalysisStatus.PARTIAL:
        document["status"] = "partial"
        document["errors"] = [
            {
                "error_id": "ERR-EVIDENCE-INCOMPLETE",
                "code": "evidence_incomplete",
                "message": "One required evidence branch is incomplete.",
                "stage": "evidence_worker",
                "retryable": False,
                "attempt_count": 1,
            }
        ]
    result: AnalysisResult = validate_analysis_result(document)
    return EvidenceAdapterResponse(
        result=result,
        export_uris=(
            "artifact://sha256/" + "3" * 64,
            "artifact://sha256/" + "4" * 64,
        ),
        request_artifact_uri="artifact://sha256/" + "5" * 64,
        replay_artifact_uri="artifact://sha256/" + "6" * 64,
        reused=False,
    )
