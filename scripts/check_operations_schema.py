"""Generate and probe the approved OPS-IMPL-01 operations contract."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from scan_tool.domain.operations import OperationsDocument, VerificationRecord

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPOSITORY_ROOT / "docs/05_QA_Validation/schemas/operations-contract.schema.json"
EXAMPLE_PATH = REPOSITORY_ROOT / "docs/05_QA_Validation/examples/operations/rules-gated-bundle.json"
SCHEMA_ID = "https://scan.local/schemas/operations-contract.schema.json"


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    document: dict[str, object]
    runtime_expected: bool
    schema_expected: bool
    model_kind: Literal["bundle", "verification"] = "bundle"


def generated_schema() -> dict[str, object]:
    schema = OperationsDocument.model_json_schema(by_alias=True, mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    schema["title"] = "SCAN Operations Contract 0.1"
    schema["$comment"] = (
        "Cross-record references, lifecycle conditions, and state transitions "
        "require the Python operations validator."
    )
    return schema


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def changed(
    document: dict[str, object],
    *path: str | int,
    value: object,
) -> dict[str, object]:
    clone = copy.deepcopy(document)
    target: object = clone
    for part in path[:-1]:
        target = target[part] if isinstance(part, str) else target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return clone


def without(
    document: dict[str, object],
    *path: str | int,
) -> dict[str, object]:
    clone = copy.deepcopy(document)
    target: object = clone
    for part in path[:-1]:
        target = target[part] if isinstance(part, str) else target[part]  # type: ignore[index]
    del target[path[-1]]  # type: ignore[index]
    return clone


def probes(example: dict[str, object]) -> list[Probe]:
    valid_verification = {
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
    return [
        Probe("rules-gated bundle", example, True, True),
        Probe("top-level extra", {**example, "credential": "forbidden"}, False, False),
        Probe(
            "bad operations version",
            changed(example, "operations_schema_version", value="0.2"),
            False,
            False,
        ),
        Probe(
            "non-UTC timestamp",
            changed(
                example,
                "manifest",
                "updated_at",
                value="2026-07-28T12:00:00+09:00",
            ),
            False,
            False,
        ),
        Probe(
            "adapter boundary mismatch",
            changed(example, "ai_modes", 0, "data_boundary", value="local_only"),
            False,
            True,
        ),
        Probe(
            "allowed mode without provider",
            changed(example, "ai_modes", 0, "rule_state", value="allowed"),
            False,
            True,
        ),
        Probe(
            "gated plan with raw output",
            changed(
                example,
                "plans",
                0,
                "raw_output_artifact",
                value="artifact://sha256/"
                "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            ),
            False,
            True,
        ),
        Probe(
            "unknown active plan",
            changed(example, "problems", 0, "active_plan_id", value="PLAN-UNKNOWN"),
            False,
            True,
        ),
        Probe(
            "missing planner job",
            without(example, "jobs", 0),
            False,
            True,
        ),
        Probe(
            "secret in safe event details",
            changed(
                example,
                "events",
                0,
                "safe_details_json",
                value={"authorization": "Bearer secret"},
            ),
            False,
            True,
        ),
        Probe(
            "operations error stage mismatch",
            changed(
                example,
                "errors",
                value=[
                    {
                        "error_id": "OERR-PLANNER-001",
                        "code": "planner_failed",
                        "message": "Planner output failed contract validation.",
                        "stage": "scheduler",
                        "retryable": False,
                        "problem_id": "PROB-Q01",
                        "job_id": "JOB-Q01-PLANNER",
                        "details": {},
                    }
                ],
            ),
            False,
            True,
        ),
        Probe(
            "event competition mismatch",
            changed(
                example,
                "events",
                0,
                "competition_id",
                value="COMP-OTHER-2026",
            ),
            False,
            True,
        ),
        Probe(
            "rules-gated planner running",
            changed(
                changed(example, "jobs", 0, "status", value="running"),
                "jobs",
                0,
                "started_at",
                value="2026-07-28T03:00:10Z",
            ),
            False,
            True,
        ),
        Probe(
            "unknown error job",
            changed(
                example,
                "errors",
                value=[
                    {
                        "error_id": "OERR-PLANNER-001",
                        "code": "planner_failed",
                        "message": "Planner output failed contract validation.",
                        "stage": "planner",
                        "retryable": False,
                        "problem_id": "PROB-Q01",
                        "job_id": "JOB-Q01-UNKNOWN",
                        "details": {},
                    }
                ],
            ),
            False,
            True,
        ),
        Probe(
            "verification with required check",
            valid_verification,
            True,
            True,
            "verification",
        ),
        Probe(
            "passing verification without required checks",
            changed(
                valid_verification,
                "required_checks",
                value=[],
            ),
            False,
            False,
            "verification",
        ),
        Probe(
            "backward state is not a document field",
            {**example, "transition": {"entity": "job", "from": "complete", "to": "running"}},
            False,
            False,
        ),
    ]


def document_is_valid(
    document: dict[str, object],
    model_kind: Literal["bundle", "verification"],
) -> bool:
    try:
        if model_kind == "verification":
            VerificationRecord.model_validate(document)
        else:
            OperationsDocument.model_validate(document)
    except ValidationError:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the generated public Schema before validation",
    )
    args = parser.parse_args()

    generated = generated_schema()
    if args.write:
        SCHEMA_PATH.write_text(json.dumps(generated, indent=2, sort_keys=True) + "\n")

    public = load_json(SCHEMA_PATH)
    if public != generated:
        raise SystemExit(
            "operations public Schema differs from the generated contract; "
            "run scripts/check_operations_schema.py --write and review the diff"
        )

    Draft202012Validator.check_schema(public)
    validator = Draft202012Validator(public, format_checker=FormatChecker())
    verification_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": public["$defs"],
        "$ref": "#/$defs/VerificationRecord",
    }
    verification_validator = Draft202012Validator(
        verification_schema,
        format_checker=FormatChecker(),
    )
    probe_items = probes(load_json(EXAMPLE_PATH))
    for probe in probe_items:
        runtime_valid = document_is_valid(probe.document, probe.model_kind)
        schema_validator = (
            verification_validator if probe.model_kind == "verification" else validator
        )
        schema_valid = schema_validator.is_valid(probe.document)
        if runtime_valid != probe.runtime_expected or schema_valid != probe.schema_expected:
            raise SystemExit(
                f"FAIL {probe.name}: runtime_expected={probe.runtime_expected} "
                f"schema_expected={probe.schema_expected} "
                f"runtime={runtime_valid} schema={schema_valid}"
            )

    print(
        "PASS operations contract 0.1 generated Schema and runtime agree "
        f"across {len(probe_items)} probes"
    )


if __name__ == "__main__":
    main()
