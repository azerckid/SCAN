"""OPS-IMPL-08 human-confirmed submission and SQLite Board integration."""

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
    OperationsSnapshotBuilder,
    SnapshotAlert,
)
from scan_tool.application.submission import SubmissionCommand, SubmissionRecorder
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_request, validate_operations_document
from scan_tool.domain.operations import CandidateStatus, ProblemStatus, SubmissionResponse
from scan_tool.domain.storage import ArtifactRecord

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/05_QA_Validation/examples/operations/rules-gated-bundle.json"
DEX_REQUEST = ROOT / "docs/05_QA_Validation/examples/analysis/dex-request.json"
DEX_REPLAY = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/raw-replay.json"
NOW = datetime(2026, 7, 29, 1, tzinfo=UTC)
runner = CliRunner()


def _completed_review_jobs() -> list[dict[str, object]]:
    return [
        {
            "job_id": "JOB-Q01-REPORTER",
            "problem_id": "PROB-Q01",
            "plan_id": "PLAN-Q01-GATED",
            "role": "reporter",
            "job_type": "candidate_build",
            "status": "complete",
            "priority": "normal",
            "idempotency_key": "d" * 64,
            "attempt": 1,
            "max_attempts": 1,
            "queued_at": "2026-07-28T03:01:00Z",
            "started_at": "2026-07-28T03:01:10Z",
            "finished_at": "2026-07-28T03:01:20Z",
        },
        {
            "job_id": "JOB-Q01-VERIFIER",
            "problem_id": "PROB-Q01",
            "plan_id": "PLAN-Q01-GATED",
            "role": "verifier",
            "job_type": "candidate_verification",
            "status": "complete",
            "priority": "normal",
            "idempotency_key": "e" * 64,
            "attempt": 1,
            "max_attempts": 1,
            "queued_at": "2026-07-28T03:02:00Z",
            "started_at": "2026-07-28T03:02:10Z",
            "finished_at": "2026-07-28T03:02:20Z",
        },
    ]


def _submission_ready_document(
    *,
    result_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
):
    selected_results = result_refs or ["RES-Q01-001"]
    selected_evidence = evidence_refs or ["EV-Q01-001"]
    payload = json.loads(EXAMPLE.read_text())
    payload["problems"][0]["status"] = "submission_ready"
    payload["ai_modes"][0].update(
        {
            "provider_id": "local.test",
            "model_id": "planner-test",
            "rule_state": "allowed",
        }
    )
    payload["plans"][0].update(
        {
            "status": "approved",
            "raw_output_artifact": "artifact://sha256/" + "c" * 64,
            "decided_at": "2026-07-28T03:01:00Z",
        }
    )
    payload["jobs"][0].update(
        {
            "status": "complete",
            "attempt": 1,
            "started_at": "2026-07-28T03:00:10Z",
            "finished_at": "2026-07-28T03:00:20Z",
        }
    )
    payload["jobs"].extend(_completed_review_jobs())
    payload["candidates"] = [
        {
            "candidate_id": "CAND-Q01-001",
            "problem_id": "PROB-Q01",
            "answer_format": "flag{...}",
            "answer_value": "flag{verified}",
            "status": "submission_ready",
            "result_refs": selected_results,
            "evidence_refs": selected_evidence,
            "verification_refs": ["VER-Q01-001"],
            "confidence": 100,
            "confidence_basis": "Independent evidence verification passed.",
            "uncertainties": [],
            "recommendation": "submit",
            "created_by_job_id": "JOB-Q01-REPORTER",
            "created_at": "2026-07-28T03:01:20Z",
            "updated_at": "2026-07-28T03:02:20Z",
        }
    ]
    payload["verifications"] = [
        {
            "verification_id": "VER-Q01-001",
            "problem_id": "PROB-Q01",
            "candidate_id": "CAND-Q01-001",
            "verifier_job_id": "JOB-Q01-VERIFIER",
            "status": "pass",
            "required_checks": ["answer_format"],
            "check_results": [
                {
                    "check": "answer_format",
                    "passed": True,
                    "result_refs": selected_results,
                    "evidence_refs": selected_evidence,
                }
            ],
            "independent_from_job_ids": ["JOB-Q01-REPORTER"],
            "conflicts": [],
            "missing_evidence": [],
            "created_at": "2026-07-28T03:02:00Z",
            "finished_at": "2026-07-28T03:02:20Z",
        }
    ]
    return validate_operations_document(payload)


def _command(**updates: object) -> SubmissionCommand:
    values: dict[str, object] = {
        "competition_id": "COMP-SCAN-2026",
        "candidate_id": "CAND-Q01-001",
        "response": SubmissionResponse.CORRECT,
        "operator_confirmed": True,
        "actor_id": "operator-local",
    }
    values.update(updates)
    return SubmissionCommand.model_validate(values)


def _prepare_database(path: Path) -> None:
    request = validate_analysis_request(json.loads(DEX_REQUEST.read_text()))
    with CliRuntime.open(path.parent) as runtime:
        runtime.register_request(request)
        result = runtime.execute_analysis(request, replay_path=DEX_REPLAY)
        runtime.save_result(request, result)
    selected_result = result.root.results[0]
    initialize_operations_database(path, backup_path=path.with_suffix(".v1.sqlite3"))
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
    with SQLiteOperationsRepository(path) as repository:
        repository.record_artifact(original)
        repository.record_artifact(planner)
        repository.save_document(
            _submission_ready_document(
                result_refs=[selected_result.result_id],
                evidence_refs=list(selected_result.evidence_refs),
            )
        )


def test_submission_requires_ready_candidate_and_explicit_human_confirmation() -> None:
    document = _submission_ready_document()
    not_ready = document.model_copy(
        update={
            "root": document.root.model_copy(
                update={
                    "candidates": [
                        document.root.candidates[0].model_copy(
                            update={"status": CandidateStatus.REVIEW_REQUIRED}
                        )
                    ],
                    "problems": [
                        document.root.problems[0].model_copy(
                            update={"status": ProblemStatus.REVIEW_REQUIRED}
                        )
                    ],
                }
            )
        }
    )

    with pytest.raises(ValueError, match="candidate_not_submission_ready"):
        SubmissionRecorder(clock=lambda: NOW).record(not_ready, _command())
    with pytest.raises(ValidationError):
        _command(operator_confirmed=False)


def test_submission_recorder_updates_document_without_network_action() -> None:
    execution = SubmissionRecorder(clock=lambda: NOW).record(
        _submission_ready_document(),
        _command(),
    )

    assert execution.document.root.problems[0].status is ProblemStatus.SUBMITTED
    assert execution.document.root.candidates[0].status is CandidateStatus.SUBMITTED
    assert execution.submission.operator_confirmed is True
    assert execution.submission.response is SubmissionResponse.CORRECT
    assert execution.event.actor_type.value == "operator"
    assert execution.event.safe_details_json["external_submission"] == "human_confirmed"
    assert execution.command_result.accepted is True
    assert execution.command_result.warnings == [
        "CTFd response was recorded locally; no network submission was made."
    ]


def test_submission_persists_atomically_and_snapshot_reads_submitted_state(
    tmp_path: Path,
) -> None:
    database = tmp_path / "scan.sqlite3"
    _prepare_database(database)

    with SQLiteOperationsRepository(database) as repository:
        source = repository.load_document("COMP-SCAN-2026")
        assert source is not None
        execution = SubmissionRecorder(clock=lambda: NOW).record(source, _command())
        persisted = repository.apply_submission(
            execution.document,
            execution.submission,
            execution.event,
        )

    snapshot = OperationsSnapshotBuilder(clock=lambda: NOW).build(
        persisted,
        snapshot_id="SNAP-SUBMISSION-PERSISTED",
        elapsed_seconds=1,
        remaining_seconds=2,
    )
    assert snapshot.summary.submitted == 1
    assert snapshot.submissions[0].human_state.value == "submitted"
    assert persisted.root.submissions == [execution.submission]


@pytest.mark.parametrize("tamper", ["event_entity", "problem_status"])
def test_submission_persistence_rejects_inconsistent_transition_and_rolls_back(
    tmp_path: Path,
    tamper: str,
) -> None:
    database = tmp_path / "scan.sqlite3"
    _prepare_database(database)

    with SQLiteOperationsRepository(database) as repository:
        source = repository.load_document("COMP-SCAN-2026")
        assert source is not None
        execution = SubmissionRecorder(clock=lambda: NOW).record(source, _command())
        if tamper == "event_entity":
            bad_event = execution.event.model_copy(update={"entity_id": "unrelated-audit-entity"})
            bad_bundle = execution.document.root.model_copy(
                update={
                    "events": [
                        bad_event if item.event_id == bad_event.event_id else item
                        for item in execution.document.root.events
                    ]
                }
            )
        else:
            bad_event = execution.event
            bad_problem = execution.document.root.problems[0].model_copy(
                update={"status": ProblemStatus.SUBMISSION_READY}
            )
            bad_bundle = execution.document.root.model_copy(update={"problems": [bad_problem]})
        bad_document = validate_operations_document(
            bad_bundle.model_dump(mode="json", by_alias=True)
        )

        with pytest.raises(ValueError, match="submission (event|problem)"):
            repository.apply_submission(
                bad_document,
                execution.submission,
                bad_event,
            )
        unchanged = repository.load_document("COMP-SCAN-2026")

    assert unchanged is not None
    assert unchanged.root.candidates[0].status is CandidateStatus.SUBMISSION_READY
    assert unchanged.root.problems[0].status is ProblemStatus.SUBMISSION_READY
    assert unchanged.root.submissions == []


def test_operations_cli_reads_explicit_sqlite_database(tmp_path: Path) -> None:
    database = tmp_path / "scan.sqlite3"
    _prepare_database(database)

    result = runner.invoke(
        app,
        [
            "operations",
            "--database",
            str(database),
            "--competition-id",
            "COMP-SCAN-2026",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["competition"]["competition_id"] == "COMP-SCAN-2026"
    assert str(tmp_path) not in result.stdout + result.stderr


def test_mark_submitted_cli_requires_confirm_and_records_only_local_response(
    tmp_path: Path,
) -> None:
    database = tmp_path / "scan.sqlite3"
    _prepare_database(database)
    arguments = [
        "mark-submitted",
        "--database",
        str(database),
        "--competition-id",
        "COMP-SCAN-2026",
        "--candidate-id",
        "CAND-Q01-001",
        "--response",
        "correct",
    ]

    rejected = runner.invoke(app, arguments)
    accepted = runner.invoke(app, [*arguments, "--confirm"])

    assert rejected.exit_code == 2
    assert "--confirm is required" in rejected.stderr
    assert accepted.exit_code == 0
    assert "network_calls 0" in accepted.stdout
    assert "flag{verified}" not in accepted.stdout
    assert (
        str(tmp_path) not in rejected.stdout + rejected.stderr + accepted.stdout + accepted.stderr
    )
    with SQLiteOperationsRepository(database) as repository:
        persisted = repository.load_document("COMP-SCAN-2026")
    assert persisted is not None
    assert persisted.root.submissions[0].response is SubmissionResponse.CORRECT


def test_mark_submitted_rejects_credential_like_actor_and_duplicate_record(
    tmp_path: Path,
) -> None:
    database = tmp_path / "scan.sqlite3"
    _prepare_database(database)
    base = [
        "mark-submitted",
        "--database",
        str(database),
        "--competition-id",
        "COMP-SCAN-2026",
        "--candidate-id",
        "CAND-Q01-001",
        "--response",
        "unknown",
        "--confirm",
    ]

    secret = runner.invoke(app, [*base, "--actor-id", "sk-secret-canary"])
    first = runner.invoke(app, base)
    duplicate = runner.invoke(app, base)

    assert secret.exit_code == 2
    assert "sk-secret-canary" not in secret.stdout + secret.stderr
    assert first.exit_code == 0
    assert duplicate.exit_code == 2
    assert "submission_record_failed" in duplicate.stderr


def test_snapshot_preserves_stale_and_rules_alerts_together() -> None:
    document = validate_operations_document(json.loads(EXAMPLE.read_text()))
    snapshot = OperationsSnapshotBuilder(clock=lambda: NOW).build(
        document,
        snapshot_id="SNAP-COMPOSITE-ALERTS",
        elapsed_seconds=0,
        remaining_seconds=0,
        viewed_at=NOW + timedelta(seconds=31),
    )

    assert snapshot.view_state.value == "stale"
    assert snapshot.alerts == [
        SnapshotAlert.STALE,
        SnapshotAlert.RULES_UNAVAILABLE,
    ]
