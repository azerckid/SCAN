"""OPS-IMPL-03 planner port, fake adapter, and AI mode Gate tests."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.fake_planner import DeterministicFakePlanner
from scan_tool.application.planner import PlannerCommand, PlannerService
from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.operations import (
    AdapterKind,
    AIExecutionMode,
    AIRuleState,
    AIToolMode,
    CompetitionEnvironment,
    DataBoundary,
    JobRecord,
    JobStatus,
    OperationErrorCode,
    PlanStatus,
)
from scan_tool.domain.planning import (
    PlannerAdapterResponse,
    PlannerBudgets,
    PlannerContext,
    PlannerUsage,
)
from scan_tool.domain.storage import ArtifactRecord
from scan_tool.domain.validation import validate_operations_document

NOW = datetime(2026, 7, 28, 5, tzinfo=UTC)
EXAMPLE = Path("docs/05_QA_Validation/examples/operations/rules-gated-bundle.json")


class ArtifactRecorder:
    def __init__(self) -> None:
        self.records: list[ArtifactRecord] = []

    def record_artifact(self, record: ArtifactRecord) -> None:
        self.records.append(record)


class CountingAdapter:
    def __init__(self, delegate: DeterministicFakePlanner) -> None:
        self.delegate = delegate
        self.adapter_kind = delegate.adapter_kind
        self.provider_id = delegate.provider_id
        self.model_id = delegate.model_id
        self.calls = 0

    async def plan(self, context: PlannerContext) -> PlannerAdapterResponse:
        self.calls += 1
        return await self.delegate.plan(context)


class StaticAdapter:
    def __init__(
        self,
        response: PlannerAdapterResponse | None,
        *,
        adapter_kind: AdapterKind,
        provider_id: str,
        model_id: str,
        delay_seconds: float = 0,
    ) -> None:
        self.response = response
        self.adapter_kind = adapter_kind
        self.provider_id = provider_id
        self.model_id = model_id
        self.delay_seconds = delay_seconds
        self.calls = 0

    async def plan(self, context: PlannerContext) -> PlannerAdapterResponse:
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.response is None:
            raise AssertionError("adapter must not be called")
        return self.response


def _base_bundle():
    return validate_operations_document(json.loads(EXAMPLE.read_text())).root


def _mode(
    *,
    rule_state: AIRuleState = AIRuleState.ALLOWED,
    adapter_kind: AdapterKind = AdapterKind.FAKE_QA,
    data_boundary: DataBoundary = DataBoundary.SYNTHETIC_ONLY,
    provider_id: str = DeterministicFakePlanner.provider_id,
    model_id: str = DeterministicFakePlanner.model_id,
    tool_mode: AIToolMode = AIToolMode.PLANNING_ONLY,
) -> AIExecutionMode:
    return AIExecutionMode(
        mode_id="MODE-FAKE-QA",
        competition_id="COMP-SCAN-2026",
        provider_id=provider_id,
        model_id=model_id,
        adapter_kind=adapter_kind,
        data_boundary=data_boundary,
        tool_mode=tool_mode,
        rule_state=rule_state,
        affected_rule_ids=["RULE-AI"],
        rules_snapshot_ref="RULES-SNAPSHOT-20260728",
        created_at=NOW,
    )


def _command(
    *,
    mode: AIExecutionMode | None = None,
    environment: CompetitionEnvironment = CompetitionEnvironment.SYNTHETIC_TEST,
    data_boundary: DataBoundary | None = None,
    job_status: JobStatus = JobStatus.QUEUED,
    operator_approved_problem_data: bool = False,
    token_budget: int = 10_000,
    timeout_seconds: float = 1,
) -> PlannerCommand:
    bundle = _base_bundle()
    selected_mode = mode or _mode()
    manifest = bundle.manifest.model_copy(update={"environment": environment})
    planner_job = JobRecord.model_validate(
        {
            **bundle.jobs[0].model_dump(mode="json"),
            "plan_id": "PLAN-FAKE-Q01",
            "status": job_status,
        }
    )
    context = PlannerContext(
        plan_id="PLAN-FAKE-Q01",
        mode_id=selected_mode.mode_id,
        problem_id=bundle.problems[0].problem_id,
        planner_job_id=planner_job.job_id,
        analysis_type="dex_swap",
        data_boundary=data_boundary or selected_mode.data_boundary,
        problem_view={
            "problem_type_hint": "synthetic_dex",
            "transaction_hash": "0x" + "1" * 64,
        },
        available_capabilities=["receipt_decode", "transfer_reconcile"],
        prior_safe_context={},
        created_at=NOW,
    )
    return PlannerCommand(
        manifest=manifest,
        problem=bundle.problems[0],
        mode=selected_mode,
        planner_job=planner_job,
        context=context,
        budgets=PlannerBudgets(
            timeout_seconds=timeout_seconds,
            token_budget=token_budget,
            cost_budget_microunits=0,
        ),
        event_id="OEV-Q01-PLANNER",
        error_id="OERR-Q01-PLANNER",
        operator_approved_problem_data=operator_approved_problem_data,
    )


def _service(
    tmp_path: Path,
    adapter,
    recorder: ArtifactRecorder,
    *,
    guard: SensitiveDataGuard | None = None,
) -> PlannerService:
    return PlannerService(
        adapter,
        ArtifactStore(tmp_path, clock=lambda: NOW),
        recorder,
        guard=guard,
        clock=lambda: NOW,
    )


def test_allowed_fake_mode_creates_artifact_backed_method_and_leaf_plan(
    tmp_path: Path,
) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()

    execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(_command()))

    assert execution.succeeded is True
    assert execution.adapter_called is True
    assert adapter.calls == 1
    assert execution.plan is not None
    assert execution.plan.status is PlanStatus.PROPOSED
    assert len(execution.plan.leaf_job_specs) == 2
    assert {item.required_capabilities[0] for item in execution.plan.leaf_job_specs} == {
        "receipt_decode",
        "transfer_reconcile",
    }
    assert execution.plan.leaf_job_specs[0].depends_on == []
    assert execution.plan.leaf_job_specs[1].depends_on == [
        execution.plan.leaf_job_specs[0].leaf_job_id
    ]
    assert len(recorder.records) == 1
    assert recorder.records[0].uri == execution.plan.raw_output_artifact
    assert execution.event.safe_details_json["model_id"] == adapter.model_id
    assert execution.event.safe_details_json["tool_mode"] == "planning_only"


def test_rules_gated_mode_waits_without_adapter_or_artifact(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()
    gated = _mode(rule_state=AIRuleState.RULES_GATED)

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(
            _command(mode=gated, job_status=JobStatus.WAITING)
        )
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.RULES_GATED
    assert execution.adapter_called is False
    assert adapter.calls == 0
    assert recorder.records == []


def test_rules_gated_mode_requires_waiting_planner_job(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()
    gated = _mode(rule_state=AIRuleState.RULES_GATED)

    execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(_command(mode=gated)))

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.INVALID_OPERATIONS_INPUT
    assert adapter.calls == 0


def test_rule_restricted_mode_blocks_before_adapter_call(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()
    restricted = _mode(rule_state=AIRuleState.RULE_RESTRICTED)

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(
            _command(mode=restricted, job_status=JobStatus.WAITING)
        )
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.RULE_RESTRICTED
    assert adapter.calls == 0
    assert recorder.records == []


def test_fake_adapter_is_forbidden_for_live_competition(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(
            _command(environment=CompetitionEnvironment.LIVE)
        )
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.RULE_RESTRICTED
    assert adapter.calls == 0


def test_boundary_and_adapter_identity_mismatch_are_pre_call_restrictions(
    tmp_path: Path,
) -> None:
    for command in (
        _command(data_boundary=DataBoundary.LOCAL_ONLY),
        _command(mode=_mode(provider_id="fake.other")),
    ):
        adapter = CountingAdapter(DeterministicFakePlanner())
        recorder = ArtifactRecorder()

        execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(command))

        assert execution.error is not None
        assert execution.error.code is OperationErrorCode.RULE_RESTRICTED
        assert adapter.calls == 0
        assert recorder.records == []


def test_approved_problem_data_requires_operator_approval_before_external_call(
    tmp_path: Path,
) -> None:
    mode = _mode(
        adapter_kind=AdapterKind.EXTERNAL,
        data_boundary=DataBoundary.APPROVED_PROBLEM_DATA,
        provider_id="external.test",
        model_id="planner-test",
    )
    adapter = StaticAdapter(
        None,
        adapter_kind=AdapterKind.EXTERNAL,
        provider_id="external.test",
        model_id="planner-test",
    )
    recorder = ArtifactRecorder()

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(
            _command(mode=mode, job_status=JobStatus.WAITING)
        )
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.RULES_GATED
    assert adapter.calls == 0
    assert recorder.records == []

    invalid_execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(_command(mode=mode))
    )
    assert invalid_execution.error is not None
    assert invalid_execution.error.code is OperationErrorCode.INVALID_OPERATIONS_INPUT
    assert adapter.calls == 0


def test_unimplemented_approved_tool_mode_waits_without_adapter_call(
    tmp_path: Path,
) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()
    mode = _mode(tool_mode=AIToolMode.PLANNING_AND_APPROVED_TOOLS)

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(
            _command(mode=mode, job_status=JobStatus.WAITING)
        )
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.RULES_GATED
    assert adapter.calls == 0
    assert recorder.records == []


def test_budget_excess_fails_without_persisting_raw_output(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()

    execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(_command(token_budget=0)))

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.PLANNER_FAILED
    assert execution.error.details["failure_kind"] == "token_budget_exceeded"
    assert execution.adapter_called is True
    assert recorder.records == []


def test_cost_budget_excess_fails_without_persisting_raw_output(tmp_path: Path) -> None:
    fake = DeterministicFakePlanner()
    command = _command()
    safe_response = asyncio.run(fake.plan(command.context))
    adapter = StaticAdapter(
        replace(
            safe_response,
            usage=PlannerUsage(
                input_tokens=safe_response.usage.input_tokens,
                output_tokens=safe_response.usage.output_tokens,
                cost_microunits=1,
            ),
        ),
        adapter_kind=AdapterKind.FAKE_QA,
        provider_id=fake.provider_id,
        model_id=fake.model_id,
    )
    recorder = ArtifactRecorder()

    execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(command))

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.PLANNER_FAILED
    assert execution.error.details["failure_kind"] == "cost_budget_exceeded"
    assert recorder.records == []


def test_timeout_is_sanitized_and_does_not_persist(tmp_path: Path) -> None:
    mode = _mode(
        adapter_kind=AdapterKind.LOCAL,
        data_boundary=DataBoundary.LOCAL_ONLY,
        provider_id="local.test",
        model_id="planner-test",
    )
    adapter = StaticAdapter(
        None,
        adapter_kind=AdapterKind.LOCAL,
        provider_id="local.test",
        model_id="planner-test",
        delay_seconds=0.02,
    )
    recorder = ArtifactRecorder()

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(_command(mode=mode, timeout_seconds=0.001))
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.PLANNER_FAILED
    assert execution.error.details["failure_kind"] == "timeout"
    assert "AssertionError" not in execution.error.message
    assert recorder.records == []


def test_sensitive_raw_output_is_rejected_before_artifact_persistence(
    tmp_path: Path,
) -> None:
    fake = DeterministicFakePlanner()
    context = _command().context
    safe_response = asyncio.run(fake.plan(context))
    adapter = StaticAdapter(
        replace(safe_response, raw_output=b'{"note":"planner-secret-canary"}'),
        adapter_kind=AdapterKind.FAKE_QA,
        provider_id=fake.provider_id,
        model_id=fake.model_id,
    )
    recorder = ArtifactRecorder()

    execution = asyncio.run(
        _service(
            tmp_path,
            adapter,
            recorder,
            guard=SensitiveDataGuard(("planner-secret-canary",)),
        ).execute(_command())
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.PLANNER_FAILED
    assert execution.error.details["failure_kind"] == "security_rejected"
    assert "planner-secret-canary" not in execution.error.message
    assert recorder.records == []


def test_cross_problem_command_is_invalid_without_adapter_call(tmp_path: Path) -> None:
    adapter = CountingAdapter(DeterministicFakePlanner())
    recorder = ArtifactRecorder()
    command = _command()
    mismatched_context = command.context.model_copy(update={"problem_id": "PROB-Q99"})

    execution = asyncio.run(
        _service(tmp_path, adapter, recorder).execute(replace(command, context=mismatched_context))
    )

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.INVALID_OPERATIONS_INPUT
    assert adapter.calls == 0


def test_adapter_response_identity_mismatch_fails_before_artifact_persistence(
    tmp_path: Path,
) -> None:
    fake = DeterministicFakePlanner()
    command = _command()
    safe_response = asyncio.run(fake.plan(command.context))
    adapter = StaticAdapter(
        replace(
            safe_response,
            plan=safe_response.plan.model_copy(update={"mode_id": "MODE-OTHER"}),
        ),
        adapter_kind=AdapterKind.FAKE_QA,
        provider_id=fake.provider_id,
        model_id=fake.model_id,
    )
    recorder = ArtifactRecorder()

    execution = asyncio.run(_service(tmp_path, adapter, recorder).execute(command))

    assert execution.error is not None
    assert execution.error.code is OperationErrorCode.PLANNER_FAILED
    assert adapter.calls == 1
    assert recorder.records == []
