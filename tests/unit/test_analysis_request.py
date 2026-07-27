import copy
import json
from pathlib import Path

import pytest

from scan_tool.domain import (
    ContractViolation,
    ErrorCode,
    validate_analysis_request,
)

EXAMPLE_ROOT = Path("docs/05_QA_Validation/examples/analysis")


def load_request(name: str) -> dict[str, object]:
    return json.loads((EXAMPLE_ROOT / f"{name}-request.json").read_text())


@pytest.mark.parametrize("name", ("dex", "auth", "freeze"))
def test_confirmed_request_round_trips_without_contract_changes(name: str) -> None:
    document = load_request(name)

    model = validate_analysis_request(document)

    assert model.to_contract_dict() == document


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("analysis_type",), "unknown"),
        (("chain_id",), 2),
        (("inputs", "subject_address"), "0x1234"),
        (("inputs", "state_blocks", "before_approval"), -1),
    ),
)
def test_domain_input_errors_are_classified_as_invalid_input(
    path: tuple[str, ...],
    value: object,
) -> None:
    document = load_request("auth")
    target: dict[str, object] = document
    for part in path[:-1]:
        target = target[part]  # type: ignore[assignment]
    target[path[-1]] = value

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_request(document)

    assert captured.value.code is ErrorCode.INVALID_INPUT


def test_source_order_outside_allowed_sources_is_invalid_input() -> None:
    document = load_request("dex")
    document["source_policy"]["source_order"] = ["DS-NOT-ALLOWED"]  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_request(document)

    assert captured.value.code is ErrorCode.INVALID_INPUT


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("extra", True),
        ("requested_at", "2026-07-26T12:26:00"),
        ("fixture_id", None),
    ),
)
def test_structural_request_errors_are_schema_invalid(field: str, value: object) -> None:
    document = copy.deepcopy(load_request("dex"))
    document[field] = value

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_request(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID
