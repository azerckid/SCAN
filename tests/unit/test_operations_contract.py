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


def test_rules_gated_bundle_round_trips_without_contract_changes() -> None:
    document = load_bundle()

    model = validate_operations_document(document)

    assert model.to_contract_dict() == document


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
