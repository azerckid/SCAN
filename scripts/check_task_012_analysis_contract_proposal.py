"""Validate the isolated TASK-012 Analysis I/O 0.2 proposal."""

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scan_tool.domain.analysis_request import AnalysisType

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "docs/05_QA_Validation/schemas/task-012-analysis-contract-proposal.schema.json"
)
MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "docs/05_QA_Validation/examples/task-012/TASK-012-ANALYSIS-CONTRACT-PROPOSAL.json"
)
APPROVED_REQUEST_SCHEMA = (
    REPOSITORY_ROOT / "docs/05_QA_Validation/schemas/analysis-request.schema.json"
)

EXPECTED_QUERY_BY_FIXTURE = {
    "FX-BASIC-EVM-001": "object_summary",
    "FX-BASIC-EVM-002": "historical_balance",
    "FX-EVM-TOKEN-001": "first_token_transfer",
    "FX-EVM-TOKEN-002": "native_inflow",
}
EXPECTED_PARTIAL_ERROR = {
    "object_summary": "source_unavailable",
    "historical_balance": "archive_required",
    "first_token_transfer": "evidence_incomplete",
    "native_inflow": "trace_unavailable",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    schema = load_json(SCHEMA_PATH)
    manifest = load_json(MANIFEST_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(manifest)

    cases = manifest["cases"]
    _validate_case_matrix(cases)
    _validate_reference_values(cases)
    probes = _run_schema_probes(validator, manifest)
    _validate_approved_contract_is_unchanged()

    print(
        f"PASS TASK-012 Analysis Contract proposal: "
        f"{len(cases)} cases, {probes} probes, Analysis I/O 0.1 unchanged"
    )


def _validate_case_matrix(cases: list[dict[str, Any]]) -> None:
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("TASK-012 proposal case IDs must be unique")

    coverage: dict[str, set[str]] = {}
    for case in cases:
        request = case["request"]
        result = case["result"]
        fixture_id = case["fixture_id"]
        query_kind = request["query_kind"]
        if EXPECTED_QUERY_BY_FIXTURE.get(fixture_id) != query_kind:
            raise ValueError(f"{fixture_id} is mapped to the wrong query kind")
        if (
            request["analysis_id"] != result["analysis_id"]
            or request["analysis_type"] != result["analysis_type"]
            or request["chain_id"] != result["chain_id"]
            or query_kind != result["query_kind"]
        ):
            raise ValueError(f"{case['case_id']} request/result envelope mismatch")
        if case["scenario"] != result["status"]:
            raise ValueError(f"{case['case_id']} scenario/result status mismatch")
        source_policy = request["source_policy"]
        if not set(source_policy["source_order"]) <= set(source_policy["allowed_source_ids"]):
            raise ValueError(f"{case['case_id']} source_order is not allowed")
        if case["scenario"] == "partial":
            codes = {error["code"] for error in result["errors"]}
            if EXPECTED_PARTIAL_ERROR[query_kind] not in codes:
                raise ValueError(f"{case['case_id']} lacks its required partial error")
        coverage.setdefault(fixture_id, set()).add(case["scenario"])

    if set(coverage) != set(EXPECTED_QUERY_BY_FIXTURE):
        raise ValueError("TASK-012 proposal fixture coverage is incomplete")
    if any(scenarios != {"complete", "partial"} for scenarios in coverage.values()):
        raise ValueError("every TASK-012 fixture requires complete and partial cases")


def _validate_reference_values(cases: list[dict[str, Any]]) -> None:
    complete = {
        case["fixture_id"]: case["result"]["data"]
        for case in cases
        if case["scenario"] == "complete"
    }
    if complete["FX-BASIC-EVM-001"]["fee_paid_wei"] != "8115326069137440":
        raise ValueError("BASIC-EVM-001 fee proposal drift")
    balances = {
        item["symbol"]: item["amount_raw"] for item in complete["FX-BASIC-EVM-002"]["balances"]
    }
    if balances != {
        "ETH": "148897435437879000853",
        "USDC": "26470158088",
    }:
        raise ValueError("BASIC-EVM-002 balance proposal drift")
    transfer = complete["FX-EVM-TOKEN-001"]["transfer"]
    if transfer["log_index"] != 275 or transfer["amount_raw"] != "25000000000":
        raise ValueError("EVM-TOKEN-001 transfer proposal drift")
    inflow = complete["FX-EVM-TOKEN-002"]
    if inflow["internal_inflow_wei"] != "14449515027026387018":
        raise ValueError("EVM-TOKEN-002 inflow proposal drift")


def _run_schema_probes(
    validator: Draft202012Validator,
    manifest: dict[str, Any],
) -> int:
    probes: list[tuple[str, dict[str, Any], bool]] = []

    extra = copy.deepcopy(manifest)
    extra["cases"][0]["request"]["unexpected"] = True
    probes.append(("request extra property", extra, False))

    wrong_inputs = copy.deepcopy(manifest)
    wrong_inputs["cases"][0]["request"]["inputs"] = {"transaction_hash": "0x00"}
    probes.append(("query-specific input mismatch", wrong_inputs, False))

    complete_with_error = copy.deepcopy(manifest)
    complete_with_error["cases"][0]["result"]["errors"] = [
        {"code": "source_unavailable", "stage": "source", "retryable": True}
    ]
    probes.append(("complete with error", complete_with_error, False))

    partial_without_error = copy.deepcopy(manifest)
    partial_without_error["cases"][1]["result"]["errors"] = []
    probes.append(("partial without error", partial_without_error, False))

    failed = copy.deepcopy(manifest)
    failed_case = failed["cases"][7]
    failed_case["scenario"] = "partial"
    failed_case["result"]["status"] = "failed"
    failed_case["result"]["data"] = None
    probes.append(("failed envelope", failed, True))

    for name, document, expected in probes:
        actual = validator.is_valid(document)
        if actual != expected:
            raise ValueError(f"schema probe {name!r} expected {expected}, got {actual}")
    return len(probes)


def _validate_approved_contract_is_unchanged() -> None:
    approved = load_json(APPROVED_REQUEST_SCHEMA)
    approved_types = set(approved["$defs"]["analysisType"]["enum"])
    runtime_types = {item.value for item in AnalysisType}
    expected = {"dex_swap", "auth_consumption", "address_freeze"}
    if approved_types != expected or runtime_types != expected:
        raise ValueError("Analysis I/O 0.1 was modified by the proposal")


if __name__ == "__main__":
    main()
