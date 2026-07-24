#!/usr/bin/env python3
"""Validate SCAN reference fixture schemas and package invariants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


QA_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = QA_ROOT / "fixtures"
SCHEMAS_ROOT = QA_ROOT / "schemas"
FILE_TO_SCHEMA = {
    "input.json": "fixture-input.schema.json",
    "expected.json": "fixture-expected.schema.json",
    "evidence.json": "fixture-evidence.schema.json",
}
EVIDENCE_ARRAYS = (
    "event_evidence",
    "call_evidence",
    "state_evidence",
    "context_evidence",
)


def load_json(path: Path) -> dict:
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


def validate_package(package: Path) -> list[str]:
    errors: list[str] = []
    documents: dict[str, dict] = {}

    for filename, schema_filename in FILE_TO_SCHEMA.items():
        document_path = package / filename
        if not document_path.exists():
            errors.append(f"{package.name}: missing {filename}")
            continue

        document = load_json(document_path)
        schema = load_json(SCHEMAS_ROOT / schema_filename)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{package.name}/{filename}:{location}: {error.message}")
        documents[filename] = document

    if len(documents) != len(FILE_TO_SCHEMA):
        return errors

    common_keys = ("fixture_id", "schema_version", "fixture_version", "status")
    for key in common_keys:
        values = {document[key] for document in documents.values()}
        if len(values) != 1:
            errors.append(f"{package.name}: {key} differs across package: {sorted(values)}")

    evidence = documents["evidence.json"]
    expected = documents["expected.json"]
    evidence_ids = [
        item["evidence_id"]
        for array_name in EVIDENCE_ARRAYS
        for item in evidence[array_name]
    ]
    duplicate_evidence_ids = duplicate_values(evidence_ids)
    if duplicate_evidence_ids:
        errors.append(
            f"{package.name}: duplicate evidence IDs: {sorted(duplicate_evidence_ids)}"
        )

    requirements = expected["scoring"]["requirements"]
    requirement_ids = [item["requirement_id"] for item in requirements]
    duplicate_requirement_ids = duplicate_values(requirement_ids)
    if duplicate_requirement_ids:
        errors.append(
            f"{package.name}: duplicate requirement IDs: "
            f"{sorted(duplicate_requirement_ids)}"
        )

    evidence_id_set = set(evidence_ids)
    for requirement in requirements:
        missing_refs = set(requirement["evidence_refs"]) - evidence_id_set
        if missing_refs:
            errors.append(
                f"{package.name}: {requirement['requirement_id']} references "
                f"missing evidence IDs: {sorted(missing_refs)}"
            )

    source_ids = {source["source_id"] for source in evidence["sources"]}
    evidence_source_ids = {
        item["source_id"]
        for array_name in EVIDENCE_ARRAYS
        for item in evidence[array_name]
    }
    missing_evidence_sources = evidence_source_ids - source_ids
    if missing_evidence_sources:
        errors.append(
            f"{package.name}: evidence uses source IDs without provenance: "
            f"{sorted(missing_evidence_sources)}"
        )

    for requirement in evidence["source_requirements"]:
        if requirement["source_id"] not in source_ids:
            errors.append(
                f"{package.name}: source requirement {requirement['source_id']} "
                "has no matching provenance source"
            )

    return errors


def main() -> int:
    schema_errors: list[str] = []
    for schema_path in sorted(SCHEMAS_ROOT.glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(load_json(schema_path))
        except Exception as error:
            schema_errors.append(f"{schema_path.name}: invalid schema: {error}")

    packages = sorted(path for path in FIXTURES_ROOT.iterdir() if path.is_dir())
    errors = schema_errors + [
        error
        for package in packages
        for error in validate_package(package)
    ]
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print(f"PASS {len(packages)} fixture packages validated against schema 0.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
