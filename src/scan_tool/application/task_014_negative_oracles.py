"""Offline negative-oracle contract for TASK-014 PATH fixture promotion."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]
type OracleCategory = Literal["path", "remerge", "multi"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-PATH-CYCLE",
        "OR-PATH-ENDPOINT-DISCONTINUITY",
        "OR-PATH-UNRELATED-EDGE",
        "OR-PATH-BUDGET-TRUNCATED",
        "OR-PATH-INTERNAL-TRACE-MISSING",
        "OR-PATH-ASSET-MISMATCH",
        "OR-REMERGE-DUPLICATE-EDGE",
        "OR-REMERGE-EXTERNAL-INFLOW-INCLUDED",
        "OR-REMERGE-BRANCH-MISSING",
        "OR-REMERGE-NEGATIVE-RESIDUAL",
        "OR-REMERGE-CYCLE",
        "OR-REMERGE-BUDGET-TRUNCATED",
        "OR-MULTI-DUPLICATE-TRANSACTION",
        "OR-MULTI-ORIGIN-MISSING",
        "OR-MULTI-WRONG-EXIT",
        "OR-MULTI-PRICE-ABSENT",
        "OR-MULTI-ROUNDED-AMOUNT",
        "OR-MULTI-UNREQUESTED-ORIGIN",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-[A-Z0-9-]+$")
    fixture_id: str = Field(pattern=r"^FX-FLOW-(PATH|REMERGE|MULTI)-001$")
    category: OracleCategory
    facts: dict[str, Any]
    expected: dict[str, Any]


class NegativeOracleManifest(ContractModel):
    schema_version: Literal["0.1"]
    status: Literal["verified"]
    execution_mode: Literal["synthetic_offline"]
    cases: tuple[NegativeOracleCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_case_set(self) -> "NegativeOracleManifest":
        ids = [case.oracle_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("negative oracle IDs must be unique")
        if set(ids) != REQUIRED_ORACLE_IDS:
            raise ValueError("TASK-014 negative oracle set drifted")
        expected_fixtures = {
            "path": "FX-FLOW-PATH-001",
            "remerge": "FX-FLOW-REMERGE-001",
            "multi": "FX-FLOW-MULTI-001",
        }
        for case in self.cases:
            if case.fixture_id != expected_fixtures[case.category]:
                raise ValueError(f"{case.oracle_id} fixture/category differs")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    match case.category:
        case "path":
            return _evaluate_path(case.facts)
        case "remerge":
            return _evaluate_remerge(case.facts)
        case "multi":
            return _evaluate_multi(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    verified = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(f"{case.oracle_id} result differs")
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_path(facts: dict[str, Any]) -> dict[str, Any]:
    if not _boolean(facts, "asset_matches"):
        return _failed("asset_mismatch")
    if _boolean(facts, "cycle_detected"):
        return _failed("cycle_detected")
    if not _boolean(facts, "endpoints_join"):
        return _failed("path_reconciliation_failed")
    if _boolean(facts, "unrelated_edge_included"):
        return _failed("unrelated_edge_included")
    if not _boolean(facts, "internal_trace_available"):
        return _partial("trace_unavailable")
    if not _boolean(facts, "budget_complete"):
        return _partial("budget_exhausted")
    return _complete("trace_path")


def _evaluate_remerge(facts: dict[str, Any]) -> dict[str, Any]:
    if _boolean(facts, "cycle_detected"):
        return _failed("cycle_detected")
    if _boolean(facts, "duplicate_edge"):
        return _failed("duplicate_edge")
    if _boolean(facts, "external_inflow_in_seed_ledger"):
        return _failed("external_inflow_contamination")
    if _integer(facts, "residual_raw") < 0:
        return _failed("negative_residual")
    if not _boolean(facts, "all_branches_available"):
        return _partial("branch_unavailable")
    if not _boolean(facts, "budget_complete"):
        return _partial("budget_exhausted")
    return _complete("trace_remerge")


def _evaluate_multi(facts: dict[str, Any]) -> dict[str, Any]:
    if _boolean(facts, "duplicate_transaction"):
        return _failed("duplicate_contribution")
    if not _boolean(facts, "all_exit_nodes_match"):
        return _failed("exit_mismatch")
    if _boolean(facts, "unrequested_origin"):
        return _failed("origin_scope_mismatch")
    if not _boolean(facts, "raw_integer_preserved"):
        return _failed("raw_amount_required")
    if not _boolean(facts, "all_origins_available"):
        return _partial("origin_unavailable")
    return _complete("aggregate_origins")


def _complete(classification: str) -> dict[str, Any]:
    return {"outcome": "complete", "classification": classification}


def _partial(classification: str) -> dict[str, Any]:
    return {"outcome": "partial", "classification": classification}


def _failed(classification: str) -> dict[str, Any]:
    return {"outcome": "failed", "classification": classification}


def _boolean(facts: dict[str, Any], key: str) -> bool:
    value = facts.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _integer(facts: dict[str, Any], key: str) -> int:
    value = facts.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value
