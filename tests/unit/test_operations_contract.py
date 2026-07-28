import copy
import json
from pathlib import Path

import pytest

from scan_tool.domain import (
    ContractViolation,
    ErrorCode,
    validate_operations_document,
    validate_state_transition,
)

EXAMPLE = Path("docs/05_QA_Validation/examples/operations/rules-gated-bundle.json")


def load_bundle() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text())


def submission_ready_bundle() -> dict[str, object]:
    document = load_bundle()
    document["problems"][0]["status"] = "submission_ready"  # type: ignore[index]
    mode = document["ai_modes"][0]  # type: ignore[index]
    mode.update(
        {
            "provider_id": "local.test",
            "model_id": "planner-test",
            "rule_state": "allowed",
        }
    )
    plan = document["plans"][0]  # type: ignore[index]
    plan.update(
        {
            "status": "approved",
            "raw_output_artifact": "artifact://sha256/"
            "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "decided_at": "2026-07-28T03:01:00Z",
        }
    )
    planner = document["jobs"][0]  # type: ignore[index]
    planner.update(
        {
            "status": "complete",
            "attempt": 1,
            "started_at": "2026-07-28T03:00:10Z",
            "finished_at": "2026-07-28T03:00:20Z",
        }
    )
    document["jobs"].extend(  # type: ignore[union-attr]
        [
            {
                "job_id": "JOB-Q01-REPORTER",
                "problem_id": "PROB-Q01",
                "plan_id": "PLAN-Q01-GATED",
                "role": "reporter",
                "job_type": "candidate_build",
                "status": "complete",
                "priority": "normal",
                "idempotency_key": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
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
                "idempotency_key": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "attempt": 1,
                "max_attempts": 1,
                "queued_at": "2026-07-28T03:02:00Z",
                "started_at": "2026-07-28T03:02:10Z",
                "finished_at": "2026-07-28T03:02:20Z",
            },
        ]
    )
    document["candidates"] = [
        {
            "candidate_id": "CAND-Q01-001",
            "problem_id": "PROB-Q01",
            "answer_format": "flag{...}",
            "answer_value": "flag{verified}",
            "status": "submission_ready",
            "result_refs": ["RES-Q01-001"],
            "evidence_refs": ["EV-Q01-001"],
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
    document["verifications"] = [
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
                    "result_refs": ["RES-Q01-001"],
                    "evidence_refs": ["EV-Q01-001"],
                }
            ],
            "independent_from_job_ids": ["JOB-Q01-REPORTER"],
            "conflicts": [],
            "missing_evidence": [],
            "created_at": "2026-07-28T03:02:00Z",
            "finished_at": "2026-07-28T03:02:20Z",
        }
    ]
    return document


def test_rules_gated_bundle_round_trips_without_contract_changes() -> None:
    document = load_bundle()

    model = validate_operations_document(document)

    assert model.to_contract_dict() == document


def test_submission_ready_bundle_has_non_vacuous_independent_verification() -> None:
    document = submission_ready_bundle()

    model = validate_operations_document(document)

    verification = model.root.verifications[0]
    assert verification.required_checks == ["answer_format"]
    assert verification.check_results[0].passed is True
    assert verification.independent_from_job_ids == ["JOB-Q01-REPORTER"]


@pytest.mark.parametrize(
    ("entity", "from_status", "to_status"),
    (
        ("problem", "captured", "triaged"),
        ("plan", "rules_gated", "proposed"),
        ("job", "waiting", "queued"),
        ("verification", "running", "pass"),
        ("candidate", "submission_ready", "submitted"),
    ),
)
def test_approved_state_transitions_are_valid(
    entity: str,
    from_status: str,
    to_status: str,
) -> None:
    transition = validate_state_transition(
        {
            "entity": entity,
            "from_status": from_status,
            "to_status": to_status,
        }
    )

    assert transition.to_status == to_status


@pytest.mark.parametrize(
    ("entity", "from_status", "to_status"),
    (
        ("problem", "submitted", "running"),
        ("plan", "approved", "proposed"),
        ("job", "complete", "running"),
        ("verification", "pass", "running"),
        ("candidate", "submitted", "draft"),
    ),
)
def test_terminal_or_backward_state_transitions_are_rejected(
    entity: str,
    from_status: str,
    to_status: str,
) -> None:
    with pytest.raises(ContractViolation) as captured:
        validate_state_transition(
            {
                "entity": entity,
                "from_status": from_status,
                "to_status": to_status,
            }
        )

    assert captured.value.code is ErrorCode.SCHEMA_INVALID
    assert "invalid_state_transition" in str(captured.value)


def test_operations_contract_forbids_unknown_fields() -> None:
    document = load_bundle()
    document["credential"] = "must-not-be-modeled"

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID
    assert "must-not-be-modeled" not in str(captured.value)


@pytest.mark.parametrize(
    "unsafe_details",
    (
        {"authorization": "Bearer secret"},
        {"nested": {"api_key": "secret"}},
        {"path": "/Users/operator/private/problem.txt"},
    ),
)
def test_operations_safe_details_reject_secrets_and_local_paths(
    unsafe_details: dict[str, object],
) -> None:
    document = load_bundle()
    document["events"][0]["safe_details_json"] = unsafe_details  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID
    assert "Bearer secret" not in str(captured.value)


def test_operations_timestamps_require_utc() -> None:
    document = load_bundle()
    document["manifest"]["updated_at"] = "2026-07-28T12:00:00+09:00"  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_ai_adapter_and_data_boundary_must_match() -> None:
    document = load_bundle()
    document["ai_modes"][0]["data_boundary"] = "local_only"  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_allowed_ai_mode_requires_pinned_provider_and_model() -> None:
    document = load_bundle()
    document["ai_modes"][0]["rule_state"] = "allowed"  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_passing_verification_requires_at_least_one_required_check() -> None:
    document = submission_ready_bundle()
    document["verifications"][0]["required_checks"] = []  # type: ignore[index]
    document["verifications"][0]["check_results"] = []  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_verification_independence_references_must_resolve() -> None:
    document = submission_ready_bundle()
    document["verifications"][0]["independent_from_job_ids"] = [  # type: ignore[index]
        "JOB-Q01-UNKNOWN"
    ]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_fake_qa_cannot_be_allowed_for_live_competition() -> None:
    document = submission_ready_bundle()
    mode = document["ai_modes"][0]  # type: ignore[index]
    mode["adapter_kind"] = "fake_qa"
    mode["data_boundary"] = "synthetic_only"

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_running_evidence_job_requires_approved_plan() -> None:
    document = load_bundle()
    document["jobs"].append(  # type: ignore[union-attr]
        {
            "job_id": "JOB-Q01-EVIDENCE",
            "problem_id": "PROB-Q01",
            "plan_id": "PLAN-Q01-GATED",
            "role": "evidence",
            "job_type": "dex_analysis",
            "status": "running",
            "priority": "normal",
            "idempotency_key": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "attempt": 1,
            "max_attempts": 1,
            "queued_at": "2026-07-28T03:01:00Z",
            "started_at": "2026-07-28T03:01:10Z",
        }
    )

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_rules_gated_planner_job_must_wait() -> None:
    document = load_bundle()
    planner = document["jobs"][0]  # type: ignore[index]
    planner["status"] = "running"
    planner["started_at"] = "2026-07-28T03:00:10Z"

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_event_must_belong_to_manifest_competition() -> None:
    document = load_bundle()
    document["events"][0]["competition_id"] = "COMP-OTHER-2026"  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_operations_error_code_must_match_stage() -> None:
    document = load_bundle()
    document["errors"] = [
        {
            "error_id": "OERR-PLANNER-001",
            "code": "planner_failed",
            "message": "Planner output did not satisfy the contract.",
            "stage": "scheduler",
            "retryable": False,
            "problem_id": "PROB-Q01",
            "job_id": "JOB-Q01-PLANNER",
            "details": {},
        }
    ]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_operations_error_job_reference_must_resolve() -> None:
    document = load_bundle()
    document["errors"] = [
        {
            "error_id": "OERR-PLANNER-001",
            "code": "planner_failed",
            "message": "Planner output did not satisfy the contract.",
            "stage": "planner",
            "retryable": False,
            "problem_id": "PROB-Q01",
            "job_id": "JOB-Q01-UNKNOWN",
            "details": {},
        }
    ]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_cross_problem_job_reference_is_rejected() -> None:
    document = load_bundle()
    second = copy.deepcopy(document["problems"][0])  # type: ignore[index]
    second["problem_id"] = "PROB-Q02"
    second.pop("active_plan_id")
    document["problems"].append(second)  # type: ignore[union-attr]
    document["jobs"][0]["problem_id"] = "PROB-Q02"  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_rules_gated_plan_cannot_contain_executable_leaf_jobs() -> None:
    document = load_bundle()
    document["plans"][0]["leaf_job_specs"] = [  # type: ignore[index]
        {
            "leaf_job_id": "JOB-Q01-EVIDENCE",
            "role": "evidence",
            "purpose": "Run DEX evidence analysis.",
            "analysis_type": "dex_swap",
            "inputs_projection": {},
            "depends_on": [],
            "required_capabilities": ["rpc_read"],
            "expected_output": "Analysis I/O result",
        }
    ]

    with pytest.raises(ContractViolation) as captured:
        validate_operations_document(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID
