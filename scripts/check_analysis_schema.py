"""Compare generated Pydantic schemas with Analysis I/O 0.2 and 0.1 compatibility."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from scan_tool.domain.analysis_error import AnalysisError
from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPOSITORY_ROOT / "docs/05_QA_Validation/schemas"
EXAMPLE_ROOT = REPOSITORY_ROOT / "docs/05_QA_Validation/examples/analysis"
EVM_EXAMPLE = (
    REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures/FX-BASIC-EVM-001/analysis-request.json"
)
SCHEMA_FILES = {
    "request": "analysis-request.schema.json",
    "result": "analysis-result.schema.json",
    "error": "analysis-error.schema.json",
}


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    schema_name: str
    document: dict[str, object]
    expected: bool


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def generated_schemas() -> dict[str, dict[str, object]]:
    """Generate validation schemas from the three public model entry points."""
    return {
        "request": AnalysisRequest.model_json_schema(by_alias=True, mode="validation"),
        "result": AnalysisResult.model_json_schema(by_alias=True, mode="validation"),
        "error": AnalysisError.model_json_schema(by_alias=True, mode="validation"),
    }


def public_schemas() -> dict[str, dict[str, object]]:
    return {name: load_json(SCHEMA_ROOT / filename) for name, filename in SCHEMA_FILES.items()}


def schema_validators(
    schemas: dict[str, dict[str, object]],
    *,
    public: bool,
) -> dict[str, Draft202012Validator]:
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    registry = Registry()
    if public:
        resources = [
            (str(schema["$id"]), Resource.from_contents(schema)) for schema in schemas.values()
        ]
        registry = registry.with_resources(resources)
    return {
        name: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for name, schema in schemas.items()
    }


def valid_error() -> dict[str, object]:
    return {
        "error_id": "ERR-SCHEMA-001",
        "code": "schema_invalid",
        "message": "Contract validation failed.",
        "stage": "contract_validation",
        "retryable": False,
        "attempt_count": 0,
    }


def changed(
    document: dict[str, object],
    *path: str | int,
    value: object,
) -> dict[str, object]:
    clone = copy.deepcopy(document)
    target: object = clone
    for part in path[:-1]:
        target = child(target, part)
    assign(target, path[-1], value)
    return clone


def without(
    document: dict[str, object],
    *path: str | int,
) -> dict[str, object]:
    clone = copy.deepcopy(document)
    target: object = clone
    for part in path[:-1]:
        target = child(target, part)
    remove(target, path[-1])
    return clone


def child(target: object, part: str | int) -> object:
    if isinstance(part, int):
        return cast(list[object], target)[part]
    return cast(dict[str, object], target)[part]


def assign(target: object, part: str | int, value: object) -> None:
    if isinstance(part, int):
        cast(list[object], target)[part] = value
    else:
        cast(dict[str, object], target)[part] = value


def remove(target: object, part: str | int) -> None:
    if isinstance(part, int):
        del cast(list[object], target)[part]
    else:
        del cast(dict[str, object], target)[part]


def request_envelope_probes(
    dex_request: dict[str, object],
    auth_request: dict[str, object],
    freeze_request: dict[str, object],
    evm_request: dict[str, object],
) -> list[Probe]:
    return [
        Probe("dex request", "request", dex_request, True),
        Probe("auth request", "request", auth_request, True),
        Probe("freeze request", "request", freeze_request, True),
        Probe("evm core request", "request", evm_request, True),
        Probe("request top-level extra", "request", {**dex_request, "extra": True}, False),
        Probe(
            "request bad schema version",
            "request",
            changed(dex_request, "schema_version", value="0.2"),
            False,
        ),
        Probe(
            "evm core request legacy schema version",
            "request",
            changed(evm_request, "schema_version", value="0.1"),
            False,
        ),
        Probe(
            "request unsupported chain",
            "request",
            changed(dex_request, "chain_id", value=2),
            False,
        ),
        Probe(
            "request unknown analysis type",
            "request",
            changed(dex_request, "analysis_type", value="unknown"),
            False,
        ),
    ]


def request_input_probes(
    dex_request: dict[str, object],
    auth_request: dict[str, object],
    freeze_request: dict[str, object],
    evm_request: dict[str, object],
) -> list[Probe]:
    return [
        Probe(
            "request uppercase transaction hash",
            "request",
            changed(
                dex_request,
                "inputs",
                "transaction_hash",
                value=str(dex_request["inputs"]["transaction_hash"]).upper(),
            ),
            False,
        ),
        Probe(
            "request mismatched input type",
            "request",
            changed(dex_request, "inputs", value=auth_request["inputs"]),
            False,
        ),
        Probe(
            "request input extra",
            "request",
            changed(
                dex_request,
                "inputs",
                value={**dex_request["inputs"], "extra": True},
            ),
            False,
        ),
        Probe(
            "request invalid address",
            "request",
            changed(auth_request, "inputs", "subject_address", value="0x1234"),
            False,
        ),
        Probe(
            "request negative block",
            "request",
            changed(auth_request, "inputs", "state_blocks", "before_approval", value=-1),
            False,
        ),
        Probe(
            "request duplicate excluded hashes",
            "request",
            changed(
                auth_request,
                "inputs",
                "excluded_transaction_hashes",
                value=[
                    auth_request["inputs"]["excluded_transaction_hashes"][0],
                    auth_request["inputs"]["excluded_transaction_hashes"][0],
                ],
            ),
            False,
        ),
        Probe(
            "request freeze event count",
            "request",
            changed(
                freeze_request,
                "inputs",
                "event_transaction_hashes",
                value=[freeze_request["inputs"]["event_transaction_hashes"][0]],
            ),
            False,
        ),
        Probe(
            "request empty allowed sources",
            "request",
            changed(
                dex_request,
                "source_policy",
                "allowed_source_ids",
                value=[],
            ),
            False,
        ),
        Probe(
            "evm query input mismatch",
            "request",
            changed(evm_request, "query_kind", value="native_inflow"),
            False,
        ),
    ]


def result_status_probes(
    dex_result: dict[str, object],
    auth_result: dict[str, object],
    freeze_result: dict[str, object],
    error: dict[str, object],
    evm_result: dict[str, object],
) -> list[Probe]:
    partial_result = changed(dex_result, "status", value="partial")
    partial_result["errors"] = [error]
    failed_result = changed(dex_result, "status", value="failed")
    failed_result["results"] = []
    failed_result["evidence"] = []
    failed_result["sources"] = []
    failed_result["errors"] = [error]
    return [
        Probe("dex result", "result", dex_result, True),
        Probe("auth result", "result", auth_result, True),
        Probe("freeze result", "result", freeze_result, True),
        Probe("evm core result", "result", evm_result, True),
        Probe(
            "evm core result legacy schema version",
            "result",
            changed(evm_result, "schema_version", value="0.1"),
            False,
        ),
        Probe("partial result", "result", partial_result, True),
        Probe("failed result", "result", failed_result, True),
        Probe("result top-level extra", "result", {**dex_result, "extra": True}, False),
        Probe(
            "complete result without results",
            "result",
            changed(dex_result, "results", value=[]),
            False,
        ),
        Probe(
            "complete result with error",
            "result",
            changed(dex_result, "errors", value=[error]),
            False,
        ),
        Probe(
            "partial result without error",
            "result",
            changed(partial_result, "errors", value=[]),
            False,
        ),
        Probe(
            "failed result without error",
            "result",
            changed(failed_result, "errors", value=[]),
            False,
        ),
    ]


def result_component_probes(dex_result: dict[str, object]) -> list[Probe]:
    return [
        Probe(
            "result invalid classification",
            "result",
            changed(dex_result, "results", 0, "classification", value="opinion"),
            False,
        ),
        Probe(
            "result empty value",
            "result",
            changed(dex_result, "results", 0, "value", value={}),
            False,
        ),
        Probe(
            "result duplicate evidence refs",
            "result",
            changed(
                dex_result,
                "results",
                0,
                "evidence_refs",
                value=[
                    dex_result["results"][0]["evidence_refs"][0],
                    dex_result["results"][0]["evidence_refs"][0],
                ],
            ),
            False,
        ),
        Probe(
            "result empty locator",
            "result",
            changed(dex_result, "evidence", 0, "locator", value={}),
            False,
        ),
        Probe(
            "result invalid source role",
            "result",
            changed(dex_result, "sources", 0, "role", value="primary"),
            False,
        ),
        Probe(
            "result missing export",
            "result",
            without(dex_result, "exports", "markdown"),
            False,
        ),
    ]


def error_probes(error: dict[str, object]) -> list[Probe]:
    return [
        Probe("standalone error", "error", error, True),
        Probe(
            "error unknown code",
            "error",
            changed(error, "code", value="unknown"),
            False,
        ),
        Probe(
            "error missing required field",
            "error",
            without(error, "attempt_count"),
            False,
        ),
        Probe("error extra field", "error", {**error, "secret": "redacted"}, False),
    ]


def build_probes() -> list[Probe]:
    dex_request = load_json(EXAMPLE_ROOT / "dex-request.json")
    auth_request = load_json(EXAMPLE_ROOT / "auth-request.json")
    freeze_request = load_json(EXAMPLE_ROOT / "freeze-request.json")
    evm_request = load_json(EVM_EXAMPLE)
    dex_result = load_json(EXAMPLE_ROOT / "dex-result.json")
    auth_result = load_json(EXAMPLE_ROOT / "auth-result.json")
    freeze_result = load_json(EXAMPLE_ROOT / "freeze-result.json")
    evm_result = changed(dex_result, "schema_version", value="0.2")
    evm_result["analysis_type"] = "evm_core"
    error = valid_error()

    return [
        *request_envelope_probes(dex_request, auth_request, freeze_request, evm_request),
        *request_input_probes(dex_request, auth_request, freeze_request, evm_request),
        *result_status_probes(dex_result, auth_result, freeze_result, error, evm_result),
        *result_component_probes(dex_result),
        *error_probes(error),
    ]


def semantic_differences() -> list[str]:
    public = schema_validators(public_schemas(), public=True)
    generated = schema_validators(generated_schemas(), public=False)
    differences: list[str] = []
    for probe in build_probes():
        public_accepts = public[probe.schema_name].is_valid(probe.document)
        generated_accepts = generated[probe.schema_name].is_valid(probe.document)
        if public_accepts != probe.expected:
            differences.append(
                f"{probe.name}: approved schema returned {public_accepts}, "
                f"expected {probe.expected}"
            )
        if generated_accepts != probe.expected:
            differences.append(
                f"{probe.name}: generated schema returned {generated_accepts}, "
                f"expected {probe.expected}"
            )
    return differences


def main() -> int:
    differences = semantic_differences()
    if differences:
        for difference in differences:
            print(f"FAIL {difference}")
        return 1
    print(
        "PASS 3 generated schemas are semantically compatible with "
        f"Analysis I/O 0.2 (0.1 compatible) across {len(build_probes())} probes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
