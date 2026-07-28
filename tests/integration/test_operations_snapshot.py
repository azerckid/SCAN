"""OPS-IMPL-07 OperationsSnapshot, SQLite read-back, and local CLI tests."""

import copy
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from scan_tool.adapters.sqlite_operations import (
    SQLiteOperationsRepository,
    initialize_operations_database,
)
from scan_tool.application.cli_runtime import CliRuntime
from scan_tool.application.operations_snapshot import (
    CommandResult,
    OperationsSnapshotBuilder,
    SnapshotSource,
    SnapshotViewState,
)
from scan_tool.application.operations_terminal import render_operations_snapshot
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_request, validate_operations_document
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.operations import OperationsDocument
from scan_tool.domain.storage import ArtifactRecord

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/05_QA_Validation/examples/operations/rules-gated-bundle.json"
DEX_REQUEST = ROOT / "docs/05_QA_Validation/examples/analysis/dex-request.json"
DEX_REPLAY = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/raw-replay.json"
NOW = datetime(2026, 7, 28, 7, tzinfo=UTC)
runner = CliRunner()


def _payload() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text())


def _document() -> OperationsDocument:
    return validate_operations_document(_payload())


def _builder() -> OperationsSnapshotBuilder:
    return OperationsSnapshotBuilder(clock=lambda: NOW)


def _state_document(
    job_status: str,
    *,
    problem_status: str = "partial",
    with_error: bool = True,
) -> OperationsDocument:
    payload = _payload()
    payload["problems"][0]["status"] = problem_status  # type: ignore[index]
    payload["ai_modes"][0].update(  # type: ignore[index]
        {
            "provider_id": "local.test",
            "model_id": "planner-test",
            "rule_state": "allowed",
        }
    )
    payload["plans"][0].update(  # type: ignore[index]
        {
            "status": "proposed",
            "raw_output_artifact": "artifact://sha256/" + "c" * 64,
        }
    )
    payload["jobs"][0].update(  # type: ignore[index]
        {
            "status": job_status,
            "attempt": 1,
            "started_at": "2026-07-28T03:00:01Z",
            "finished_at": "2026-07-28T03:00:02Z",
        }
    )
    if with_error:
        payload["errors"] = [
            {
                "error_id": f"OERR-Q01-{job_status.upper()}",
                "code": "planner_failed",
                "message": "The planner stopped without exposing its exception.",
                "stage": "planner",
                "retryable": False,
                "problem_id": "PROB-Q01",
                "job_id": "JOB-Q01-PLANNER",
                "details": {"reason": "safe_failure"},
            }
        ]
    return validate_operations_document(payload)


def _candidate_document(result: AnalysisResult) -> OperationsDocument:
    payload = _payload()
    payload["problems"][0]["status"] = "verifying"  # type: ignore[index]
    payload["ai_modes"][0].update(  # type: ignore[index]
        {
            "provider_id": "local.test",
            "model_id": "planner-test",
            "rule_state": "allowed",
        }
    )
    payload["plans"][0].update(  # type: ignore[index]
        {
            "status": "approved",
            "raw_output_artifact": "artifact://sha256/" + "c" * 64,
            "decided_at": "2026-07-28T03:00:02Z",
        }
    )
    payload["jobs"][0].update(  # type: ignore[index]
        {
            "status": "complete",
            "attempt": 1,
            "started_at": "2026-07-28T03:00:01Z",
            "finished_at": "2026-07-28T03:00:02Z",
        }
    )
    analysis = result.root
    selected = analysis.results[0]
    payload["jobs"].extend(  # type: ignore[union-attr]
        [
            {
                "job_id": "JOB-Q01-EVIDENCE",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "evidence",
                "job_type": "dex_replay",
                "status": "complete",
                "priority": "normal",
                "idempotency_key": "d" * 64,
                "analysis_id": analysis.analysis_id,
                "attempt": 1,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:00:02Z",
                "started_at": "2026-07-28T03:00:03Z",
                "finished_at": "2026-07-28T03:00:04Z",
            },
            {
                "job_id": "JOB-Q01-REPORTER",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "reporter",
                "job_type": "candidate_build",
                "status": "running",
                "priority": "normal",
                "idempotency_key": "e" * 64,
                "attempt": 1,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:00:04Z",
                "started_at": "2026-07-28T03:00:05Z",
            },
            {
                "job_id": "JOB-Q01-VERIFIER",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "verifier",
                "job_type": "independent_verification",
                "status": "running",
                "priority": "normal",
                "idempotency_key": "f" * 64,
                "attempt": 1,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:00:05Z",
                "started_at": "2026-07-28T03:00:06Z",
            },
        ]
    )
    payload["candidates"] = [
        {
            "candidate_id": "CAND-Q01-001",
            "problem_id": "PROB-Q01",
            "answer_format": "flag{...}",
            "answer_value": "evidence-backed-candidate",
            "status": "review_required",
            "result_refs": [selected.result_id],
            "evidence_refs": list(selected.evidence_refs),
            "verification_refs": ["VER-Q01-001"],
            "confidence": 80,
            "confidence_basis": "Derived from a confirmed Analysis result.",
            "uncertainties": ["Independent replay is incomplete."],
            "recommendation": "investigate",
            "created_by_job_id": "JOB-Q01-REPORTER",
            "created_at": "2026-07-28T03:00:05Z",
            "updated_at": "2026-07-28T03:00:06Z",
        }
    ]
    payload["verifications"] = [
        {
            "verification_id": "VER-Q01-001",
            "problem_id": "PROB-Q01",
            "candidate_id": "CAND-Q01-001",
            "verifier_job_id": "JOB-Q01-VERIFIER",
            "status": "incomplete",
            "required_checks": ["independent_replay"],
            "check_results": [],
            "independent_from_job_ids": [
                "JOB-Q01-REPORTER",
                "JOB-Q01-EVIDENCE",
            ],
            "conflicts": [],
            "missing_evidence": list(selected.evidence_refs),
            "created_at": "2026-07-28T03:00:06Z",
            "finished_at": "2026-07-28T03:00:07Z",
        }
    ]
    return validate_operations_document(payload)


def test_rules_gated_snapshot_maps_preview_sections_without_paths() -> None:
    source = SnapshotSource(
        capability="receipt_decode",
        provider_id="offline.fixture",
        health="healthy",
        concurrency_limit=2,
        in_flight=1,
        retry_after_seconds=None,
        cache_status="hit",
    )

    snapshot = _builder().build(
        _document(),
        snapshot_id="SNAP-SCAN-2026-001",
        elapsed_seconds=120,
        remaining_seconds=600,
        sources=(source,),
    )
    serialized = json.dumps(snapshot.to_contract_dict())

    assert snapshot.view_state is SnapshotViewState.RULES_UNAVAILABLE
    assert snapshot.summary.total == 1
    assert snapshot.summary.queue_age_seconds == 14400
    assert snapshot.problems[0].next_action == "confirm an allowed AI execution mode"
    assert snapshot.workers[0].queue_reason
    assert snapshot.sources == [source]
    assert str(ROOT) not in serialized


def test_stale_and_empty_states_are_explicit() -> None:
    stale = _builder().build(
        _document(),
        snapshot_id="SNAP-SCAN-2026-STALE",
        elapsed_seconds=0,
        remaining_seconds=0,
        viewed_at=NOW + timedelta(seconds=31),
    )
    empty_document = _document().model_copy(
        update={
            "root": _document().root.model_copy(
                update={
                    "problems": [],
                    "ai_modes": [],
                    "plans": [],
                    "jobs": [],
                    "events": [],
                }
            )
        }
    )
    empty = _builder().build(
        empty_document,
        snapshot_id="SNAP-SCAN-2026-EMPTY",
        elapsed_seconds=0,
        remaining_seconds=0,
    )

    assert stale.view_state is SnapshotViewState.STALE
    assert empty.view_state is SnapshotViewState.EMPTY
    assert empty.summary.total == 0
    assert empty.problems == []


def test_partial_and_failed_states_are_derived_from_scoped_runtime_records() -> None:
    default = _builder().build(
        _state_document("complete", problem_status="running", with_error=False),
        snapshot_id="SNAP-SCAN-2026-DEFAULT",
        elapsed_seconds=0,
        remaining_seconds=0,
    )
    partial = _builder().build(
        _state_document("partial"),
        snapshot_id="SNAP-SCAN-2026-PARTIAL",
        elapsed_seconds=0,
        remaining_seconds=0,
    )
    failed = _builder().build(
        _state_document("failed"),
        snapshot_id="SNAP-SCAN-2026-FAILED",
        elapsed_seconds=0,
        remaining_seconds=0,
    )

    assert default.view_state is SnapshotViewState.DEFAULT
    assert partial.view_state is SnapshotViewState.PARTIAL
    assert partial.workers[0].health.value == "stopped"
    assert failed.view_state is SnapshotViewState.FAILED
    assert failed.workers[0].health.value == "failed"


def test_multiple_problems_keep_jobs_and_activity_in_their_own_rows() -> None:
    payload = _payload()
    second_problem = copy.deepcopy(payload["problems"][0])  # type: ignore[index]
    second_problem.update(
        {
            "problem_id": "PROB-Q02",
            "title": "Second isolated challenge",
            "active_plan_id": "PLAN-Q02-GATED",
        }
    )
    second_plan = copy.deepcopy(payload["plans"][0])  # type: ignore[index]
    second_plan.update(
        {
            "plan_id": "PLAN-Q02-GATED",
            "problem_id": "PROB-Q02",
            "planner_job_id": "JOB-Q02-PLANNER",
        }
    )
    second_job = copy.deepcopy(payload["jobs"][0])  # type: ignore[index]
    second_job.update(
        {
            "job_id": "JOB-Q02-PLANNER",
            "problem_id": "PROB-Q02",
            "plan_id": "PLAN-Q02-GATED",
            "idempotency_key": "d" * 64,
        }
    )
    second_event = copy.deepcopy(payload["events"][0])  # type: ignore[index]
    second_event.update(
        {
            "event_id": "OEV-Q02-CAPTURED",
            "problem_id": "PROB-Q02",
            "entity_id": "PROB-Q02",
        }
    )
    payload["problems"].append(second_problem)  # type: ignore[union-attr]
    payload["plans"].append(second_plan)  # type: ignore[union-attr]
    payload["jobs"].append(second_job)  # type: ignore[union-attr]
    payload["events"].append(second_event)  # type: ignore[union-attr]

    snapshot = _builder().build(
        validate_operations_document(payload),
        snapshot_id="SNAP-SCAN-2026-MULTI",
        elapsed_seconds=0,
        remaining_seconds=0,
    )

    assert snapshot.summary.total == 2
    assert {item.problem_id for item in snapshot.problems} == {"PROB-Q01", "PROB-Q02"}
    assert {item.job_id for item in snapshot.workers} == {
        "JOB-Q01-PLANNER",
        "JOB-Q02-PLANNER",
    }
    assert {item.problem_id for item in snapshot.activity} == {"PROB-Q01", "PROB-Q02"}


def test_terminal_and_json_renderers_use_the_same_snapshot() -> None:
    snapshot = _builder().build(
        _document(),
        snapshot_id="SNAP-SCAN-2026-RENDER",
        elapsed_seconds=10,
        remaining_seconds=20,
    )
    terminal = io.StringIO()
    json_stream = io.StringIO()

    render_operations_snapshot(snapshot, terminal, output_format="terminal")
    render_operations_snapshot(snapshot, json_stream, output_format="json")
    rendered_json = json.loads(json_stream.getvalue())

    assert "RULES_UNAVAILABLE" in terminal.getvalue()
    assert "PROB-Q01" in terminal.getvalue()
    assert "SUBMISSION QUEUE" in terminal.getvalue()
    assert rendered_json == snapshot.to_contract_dict()


def test_command_result_requires_event_and_status_when_accepted() -> None:
    accepted = CommandResult(
        command_id="CMD-Q01-PRIORITY",
        accepted=True,
        entity_id="PROB-Q01",
        new_status="triaged",
        event_id="OEV-Q01-TRIAGED",
        warnings=[],
    )

    assert accepted.accepted is True
    with pytest.raises(ValidationError):
        CommandResult(
            command_id="CMD-Q01-BROKEN",
            accepted=True,
            entity_id="PROB-Q01",
            new_status=None,
            event_id=None,
            warnings=[],
        )


def test_source_concurrency_limit_is_enforced() -> None:
    with pytest.raises(ValidationError):
        SnapshotSource(
            capability="receipt_decode",
            provider_id="offline.fixture",
            health="healthy",
            concurrency_limit=1,
            in_flight=2,
            retry_after_seconds=None,
            cache_status="miss",
        )


def test_sqlite_v2_round_trip_revalidates_operations_document(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    initialize_operations_database(database, backup_path=tmp_path / "scan-v1.sqlite3")
    original = ArtifactRecord(
        sha256="a" * 64,
        byte_length=42,
        media_type="text/plain",
        relative_path="sha256/aa/" + "a" * 64,
        artifact_kind="problem_text",
        redaction_status="not_required",
        license_status="competition_input",
        created_at=NOW,
    )

    with SQLiteOperationsRepository(database) as repository:
        repository.record_artifact(original)
        repository.save_document(_document())
        loaded = repository.load_document("COMP-SCAN-2026")

    assert loaded is not None
    assert loaded.to_contract_dict() == _document().to_contract_dict()


def test_sqlite_read_back_preserves_candidate_and_verification_refs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    request = validate_analysis_request(json.loads(DEX_REQUEST.read_text()))
    with CliRuntime.open(root) as runtime:
        runtime.register_request(request)
        result = runtime.execute_analysis(request, replay_path=DEX_REPLAY)
        runtime.save_result(request, result)
    initialize_operations_database(
        root / "scan.sqlite3",
        backup_path=tmp_path / "scan-v1.sqlite3",
    )
    original = ArtifactRecord(
        sha256="a" * 64,
        byte_length=42,
        media_type="text/plain",
        relative_path="operations/aa/" + "a" * 64,
        artifact_kind="problem_text",
        redaction_status="not_required",
        license_status="competition_input",
        created_at=NOW,
    )
    planner = ArtifactRecord(
        sha256="c" * 64,
        byte_length=42,
        media_type="application/json",
        relative_path="operations/cc/" + "c" * 64,
        artifact_kind="planner_output",
        redaction_status="checked",
        license_status="generated",
        created_at=NOW,
    )
    document = _candidate_document(result)

    with SQLiteOperationsRepository(root / "scan.sqlite3") as repository:
        repository.record_artifact(original)
        repository.record_artifact(planner)
        repository.save_document(document)
        loaded = repository.load_document("COMP-SCAN-2026")

    assert loaded is not None
    assert loaded.root.candidates[0].result_refs == document.root.candidates[0].result_refs
    assert loaded.root.candidates[0].evidence_refs == document.root.candidates[0].evidence_refs
    assert loaded.root.verifications[0].candidate_id == "CAND-Q01-001"
    snapshot = _builder().build(
        loaded,
        snapshot_id="SNAP-SCAN-2026-PERSISTED",
        elapsed_seconds=0,
        remaining_seconds=0,
    )
    assert snapshot.submissions[0].candidate_id == "CAND-Q01-001"
    assert snapshot.verifications[0].status.value == "incomplete"


def test_local_operations_cli_renders_terminal_and_json(tmp_path: Path) -> None:
    bundle = tmp_path / "operations.json"
    bundle.write_text(json.dumps(_payload()))

    terminal = runner.invoke(
        app,
        [
            "operations",
            "--bundle",
            str(bundle),
            "--elapsed-seconds",
            "10",
            "--remaining-seconds",
            "20",
        ],
    )
    json_result = runner.invoke(
        app,
        ["operations", "--bundle", str(bundle), "--output", "json"],
    )

    assert terminal.exit_code == 0
    assert "OPERATIONS COMP-SCAN-2026" in terminal.stdout
    assert "RULES_UNAVAILABLE" in terminal.stdout
    assert str(tmp_path) not in terminal.stdout + terminal.stderr
    assert json_result.exit_code == 0
    assert json.loads(json_result.stdout)["operations_schema_version"] == "0.1"


def test_local_operations_cli_rejects_unknown_output_without_exposing_path(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "operations.json"
    bundle.write_text(json.dumps(_payload()))

    result = runner.invoke(
        app,
        ["operations", "--bundle", str(bundle), "--output", "html"],
    )

    assert result.exit_code == 2
    assert "output must be terminal or json" in result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr


def test_local_operations_cli_bounds_snapshot_id_for_long_competition_id(
    tmp_path: Path,
) -> None:
    payload = _payload()
    competition_id = "COMP-" + "A" * 59
    payload["manifest"]["competition_id"] = competition_id  # type: ignore[index]
    for key in ("problems", "ai_modes", "events"):
        payload[key][0]["competition_id"] = competition_id  # type: ignore[index]
    bundle = tmp_path / "operations.json"
    bundle.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        ["operations", "--bundle", str(bundle), "--output", "json"],
    )

    assert result.exit_code == 0
    snapshot_id = json.loads(result.stdout)["snapshot_id"]
    assert snapshot_id.startswith("SNAP-LOCAL-")
    assert len(snapshot_id) <= 64
