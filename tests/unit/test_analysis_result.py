import copy
import json
from pathlib import Path

import pytest

from scan_tool.domain import (
    ContractViolation,
    ErrorCode,
    validate_analysis_pair,
    validate_analysis_result,
)

EXAMPLE_ROOT = Path("docs/05_QA_Validation/examples/analysis")


def load_document(name: str, kind: str) -> dict[str, object]:
    return json.loads((EXAMPLE_ROOT / f"{name}-{kind}.json").read_text())


@pytest.mark.parametrize("name", ("dex", "auth", "freeze"))
def test_confirmed_pair_round_trips_and_preserves_references(name: str) -> None:
    request_document = load_document(name, "request")
    result_document = load_document(name, "result")

    request, result = validate_analysis_pair(request_document, result_document)

    assert request.to_contract_dict() == request_document
    assert result.to_contract_dict() == result_document


@pytest.mark.parametrize("raw_value", (1.5, "01", str(2**256)))
def test_non_uint256_raw_values_are_schema_invalid(raw_value: object) -> None:
    document = load_document("auth", "result")
    document["results"][0]["value"]["amount_raw"] = raw_value  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_result(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_uint256_max_round_trips_without_precision_loss() -> None:
    document = load_document("auth", "result")
    maximum = str(2**256 - 1)

    model = validate_analysis_result(document)

    assert model.to_contract_dict()["results"][0]["value"]["amount_raw"] == maximum  # type: ignore[index]


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("results", 0, "evidence_refs"), ["EV-MISSING"]),
        (("evidence", 0, "source_record_ref"), "SRC-MISSING"),
        (("run", "started_at"), "2026-07-26T12:26:00"),
        (("status",), "failed"),
    ),
)
def test_result_invariant_failures_are_schema_invalid(
    path: tuple[str | int, ...],
    value: object,
) -> None:
    document = load_document("dex", "result")
    target: object = document
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_result(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_duplicate_result_ids_are_rejected() -> None:
    document = load_document("dex", "result")
    document["results"][1]["result_id"] = document["results"][0]["result_id"]  # type: ignore[index]

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_result(document)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_pair_rejects_result_source_outside_request_policy() -> None:
    request = load_document("dex", "request")
    result = copy.deepcopy(load_document("dex", "result"))
    source_record_id = result["sources"][0]["source_record_id"]  # type: ignore[index]
    result["sources"][0]["source_id"] = "DS-UNAPPROVED"  # type: ignore[index]
    for evidence in result["evidence"]:  # type: ignore[union-attr]
        if evidence["source_record_ref"] == source_record_id:
            evidence["source_id"] = "DS-UNAPPROVED"

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_pair(request, result)

    assert captured.value.code is ErrorCode.SCHEMA_INVALID


def test_validation_error_does_not_echo_input_secret() -> None:
    document = load_document("dex", "result")
    canary = "not-a-real-secret-value"
    document["secret"] = canary

    with pytest.raises(ContractViolation) as captured:
        validate_analysis_result(document)

    assert canary not in str(captured.value)
