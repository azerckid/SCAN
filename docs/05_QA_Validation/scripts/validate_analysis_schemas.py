#!/usr/bin/env python3
"""Validate SCAN analysis I/O schemas, examples, and reference invariants."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


QA_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = QA_ROOT / "schemas"
EXAMPLES_ROOT = QA_ROOT / "examples" / "analysis"
FIXTURES_ROOT = QA_ROOT / "fixtures"
ANALYSIS_SCHEMAS = (
    "analysis-request.schema.json",
    "analysis-result.schema.json",
    "analysis-error.schema.json",
)
EXAMPLE_PAIRS = {
    "dex": "FX-SVC-DEX-001",
    "auth": "FX-EVM-AUTH-001",
    "freeze": "FX-EVM-FREEZE-001",
}
EXPECTED_ERROR_CODES = {
    "invalid_input",
    "unsupported_chain",
    "source_unavailable",
    "rate_limited",
    "archive_required",
    "trace_unavailable",
    "decode_failed",
    "evidence_incomplete",
    "reconciliation_failed",
    "schema_invalid",
    "rule_restricted",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def duplicate_values(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def schema_registry(schemas: dict[str, dict[str, Any]]) -> Registry:
    resources = [
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
    ]
    return Registry().with_resources(resources)


def validate_document(
    document: dict[str, Any],
    schema: dict[str, Any],
    registry: Registry,
    label: str,
) -> list[str]:
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    return [
        f"{label}:{'.'.join(str(part) for part in error.path) or '<root>'}: "
        f"{error.message}"
        for error in sorted(
            validator.iter_errors(document),
            key=lambda item: list(item.path),
        )
    ]


def assert_unique(
    values: list[str],
    label: str,
    errors: list[str],
) -> None:
    duplicates = duplicate_values(values)
    if duplicates:
        errors.append(f"{label}: duplicate IDs: {sorted(duplicates)}")


def validate_fixture_mapping(
    request: dict[str, Any],
    result: dict[str, Any],
    fixture_id: str,
) -> list[str]:
    errors: list[str] = []
    fixture_root = FIXTURES_ROOT / fixture_id
    fixture_input = load_json(fixture_root / "input.json")
    fixture_expected = load_json(fixture_root / "expected.json")
    inputs = request["inputs"]

    if request.get("fixture_id") != fixture_id:
        errors.append(f"{fixture_id}: request fixture_id differs")
    if request["chain_id"] != fixture_input["chain"]["chain_id"]:
        errors.append(f"{fixture_id}: request chain_id differs from fixture")

    expected_type = {
        "FX-SVC-DEX-001": "dex_swap",
        "FX-EVM-AUTH-001": "auth_consumption",
        "FX-EVM-FREEZE-001": "address_freeze",
    }[fixture_id]
    if request["analysis_type"] != expected_type:
        errors.append(f"{fixture_id}: analysis_type differs from fixture mapping")

    if fixture_id == "FX-SVC-DEX-001":
        if inputs["transaction_hash"] != fixture_input["transaction_hash"]:
            errors.append(f"{fixture_id}: DEX transaction hash mapping differs")
        result_values = {
            item["result_type"]: item["value"] for item in result["results"]
        }
        for result_type in ("asset_in", "pool_output", "user_net_output"):
            expected_value = fixture_expected[result_type]
            actual_value = result_values.get(result_type, {})
            for key in ("symbol", "decimals", "amount_raw"):
                if actual_value.get(key) != expected_value.get(key):
                    errors.append(
                        f"{fixture_id}: {result_type}.{key} differs from expected"
                    )

    if fixture_id == "FX-EVM-AUTH-001":
        mappings = {
            "subject_address": "subject_address",
            "token_address": "token_address",
            "spender_address": "spender_address",
            "approval_transaction_hash": "approval_transaction_hash",
            "consumption_transaction_hash": "consumption_transaction_hash",
            "state_blocks": "state_blocks",
        }
        for request_key, fixture_key in mappings.items():
            if inputs[request_key] != fixture_input[fixture_key]:
                errors.append(f"{fixture_id}: AUTH {request_key} mapping differs")
        if inputs.get("excluded_transaction_hashes") != fixture_input[
            "excluded_intermediate_transactions"
        ]:
            errors.append(f"{fixture_id}: AUTH excluded transaction mapping differs")
        result_values = {
            item["result_type"]: item["value"] for item in result["results"]
        }
        allowance = result_values.get("allowance_lifecycle", {})
        expected_allowance = fixture_expected["allowance"]
        if allowance.get("consumed_delta_raw") != expected_allowance[
            "consumed_delta_raw"
        ]:
            errors.append(f"{fixture_id}: AUTH allowance delta differs")
        consumption = result_values.get("authorization_consumption", {})
        if (
            consumption.get("amount_raw")
            != fixture_expected["consumption"]["amount_raw"]
        ):
            errors.append(f"{fixture_id}: AUTH consumption amount differs")

    if fixture_id == "FX-EVM-FREEZE-001":
        for key in (
            "token_address",
            "target_address",
            "mode",
            "event_transaction_hashes",
            "state_blocks",
        ):
            if inputs[key] != fixture_input[key]:
                errors.append(f"{fixture_id}: FREEZE {key} mapping differs")
        transitions = {
            item["result_type"]: item["value"] for item in result["results"]
        }
        expected_transitions = fixture_expected["address_freeze"]["transitions"]
        for result_type, expected_transition in zip(
            ("blacklist_transition", "unblacklist_transition"),
            expected_transitions,
        ):
            actual = transitions.get(result_type, {})
            if actual.get("before") != expected_transition["state_before"]:
                errors.append(f"{fixture_id}: {result_type}.before differs")
            if actual.get("after") != expected_transition["state_after"]:
                errors.append(f"{fixture_id}: {result_type}.after differs")

    expected_requirements = {
        item["requirement_id"]
        for item in fixture_expected["scoring"]["requirements"]
        if item["mandatory"]
    }
    actual_requirements = {
        requirement_id
        for item in result["results"]
        for requirement_id in item["fixture_requirement_ids"]
    }
    if actual_requirements != expected_requirements:
        errors.append(
            f"{fixture_id}: fixture requirement coverage differs: "
            f"expected {sorted(expected_requirements)}, "
            f"got {sorted(actual_requirements)}"
        )

    return errors


def validate_pair(
    prefix: str,
    fixture_id: str,
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    request_path = EXAMPLES_ROOT / f"{prefix}-request.json"
    result_path = EXAMPLES_ROOT / f"{prefix}-result.json"
    request = load_json(request_path)
    result = load_json(result_path)
    errors = validate_document(
        request,
        schemas["analysis-request.schema.json"],
        registry,
        request_path.name,
    )
    errors.extend(
        validate_document(
            result,
            schemas["analysis-result.schema.json"],
            registry,
            result_path.name,
        )
    )

    for key in ("schema_version", "analysis_id", "analysis_type", "chain_id"):
        if request.get(key) != result.get(key):
            errors.append(f"{prefix}: request/result {key} differs")

    source_order = set(request["source_policy"]["source_order"])
    allowed_sources = set(request["source_policy"]["allowed_source_ids"])
    if not source_order <= allowed_sources:
        errors.append(f"{prefix}: source_order contains a disallowed source")

    results = result["results"]
    evidence = result["evidence"]
    sources = result["sources"]
    warnings = result["warnings"]
    result_ids = [item["result_id"] for item in results]
    evidence_ids = [item["evidence_id"] for item in evidence]
    source_record_ids = [item["source_record_id"] for item in sources]
    warning_ids = [item["warning_id"] for item in warnings]
    error_ids = [item["error_id"] for item in result["errors"]]
    assert_unique(result_ids, f"{prefix} result", errors)
    assert_unique(evidence_ids, f"{prefix} evidence", errors)
    assert_unique(source_record_ids, f"{prefix} source record", errors)
    assert_unique(warning_ids, f"{prefix} warning", errors)
    assert_unique(error_ids, f"{prefix} error", errors)

    result_id_set = set(result_ids)
    evidence_id_set = set(evidence_ids)
    source_by_record = {item["source_record_id"]: item for item in sources}
    referenced_evidence: set[str] = set()
    for item in results:
        missing = set(item["evidence_refs"]) - evidence_id_set
        if missing:
            errors.append(
                f"{prefix}: {item['result_id']} references missing evidence "
                f"{sorted(missing)}"
            )
        referenced_evidence.update(item["evidence_refs"])

    for item in evidence:
        source = source_by_record.get(item["source_record_ref"])
        if source is None:
            errors.append(
                f"{prefix}: {item['evidence_id']} references missing source record"
            )
        elif source["source_id"] != item["source_id"]:
            errors.append(
                f"{prefix}: {item['evidence_id']} source_id differs from source record"
            )

    actual_source_ids = {item["source_id"] for item in sources}
    if not actual_source_ids <= allowed_sources:
        errors.append(f"{prefix}: result uses a source disallowed by request")

    for item in warnings:
        missing_results = set(item.get("related_result_ids", [])) - result_id_set
        missing_evidence = set(item.get("related_evidence_ids", [])) - evidence_id_set
        if missing_results or missing_evidence:
            errors.append(f"{prefix}: {item['warning_id']} has missing references")
        referenced_evidence.update(item.get("related_evidence_ids", []))

    for item in result["errors"]:
        missing_evidence = set(item.get("related_evidence_ids", [])) - evidence_id_set
        if missing_evidence:
            errors.append(f"{prefix}: {item['error_id']} has missing evidence refs")
        referenced_evidence.update(item.get("related_evidence_ids", []))

    orphan_evidence = evidence_id_set - referenced_evidence
    if orphan_evidence:
        errors.append(f"{prefix}: unreferenced evidence IDs: {sorted(orphan_evidence)}")

    referenced_source_records = {item["source_record_ref"] for item in evidence}
    orphan_sources = set(source_record_ids) - referenced_source_records
    if orphan_sources:
        errors.append(
            f"{prefix}: unreferenced source records: {sorted(orphan_sources)}"
        )

    started_at = datetime.fromisoformat(result["run"]["started_at"])
    finished_at = datetime.fromisoformat(result["run"]["finished_at"])
    if finished_at < started_at:
        errors.append(f"{prefix}: run.finished_at precedes run.started_at")

    errors.extend(validate_fixture_mapping(request, result, fixture_id))
    return errors


def main() -> int:
    schemas = {
        name: load_json(SCHEMAS_ROOT / name)
        for name in ANALYSIS_SCHEMAS
    }
    errors: list[str] = []
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            errors.append(f"{name}: invalid schema: {error}")

    error_codes = set(
        schemas["analysis-error.schema.json"]["properties"]["code"]["enum"]
    )
    if error_codes != EXPECTED_ERROR_CODES:
        errors.append(
            "analysis-error.schema.json: error code set differs from requirements"
        )

    registry = schema_registry(schemas)
    for prefix, fixture_id in EXAMPLE_PAIRS.items():
        errors.extend(validate_pair(prefix, fixture_id, schemas, registry))

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print(
        "PASS 3 analysis request/result pairs validated against schema 0.1 "
        "with reference integrity"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
