"""Offline negative-oracle contract for the TASK-016 lending candidate."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-LEND-WRONG-PROTOCOL",
        "OR-LEND-WINDOW-OUT-OF-SCOPE",
        "OR-LEND-TRACE-REQUIRED-PARTIAL",
        "OR-LEND-AMOUNT-MISMATCH",
        "OR-LEND-ATTACK-LABEL-REJECTED",
        "OR-LEND-SUBJECT-ROLE-MISMATCH",
        "OR-LEND-MULTIROLE-LEG-DROP",
        "OR-LEND-COMPLETE-MATCH",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-LEND-[A-Z0-9-]+$")
    fixture_id: Literal["FX-SVC-LEND-001"]
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
            raise ValueError("TASK-016 lending negative oracle set drifted")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    return _evaluate_lending(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    verified = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(f"{case.oracle_id} result differs")
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_lending(facts: dict[str, Any]) -> dict[str, Any]:
    """Mirror doc 19 section 6 complete/partial/failed decision boundary."""
    if _boolean(facts, "wrong_protocol_attribution"):
        return _failed("wrong_protocol_rejected")
    if _boolean(facts, "window_violation"):
        return _failed("observation_window_violation")
    if _boolean(facts, "attack_label_assessed"):
        return _failed("attack_label_rejected")
    if _boolean(facts, "subject_role_mismatch"):
        return _failed("reconciliation_failed")
    if _boolean(facts, "multirole_leg_dropped"):
        return _failed("multirole_leg_drop_rejected")
    if _boolean(facts, "amount_transfer_mismatch") and not _boolean(
        facts, "partial_allowed_for_mismatch"
    ):
        return _failed("amount_reconciliation_failed")
    if _boolean(facts, "amount_transfer_mismatch"):
        return _partial("transfer_mismatch_partial")
    if _boolean(facts, "trace_required_missing"):
        return _partial("trace_unavailable")
    if (
        _boolean(facts, "event_decoded")
        and _boolean(facts, "transfer_legs_matched")
        and _boolean(facts, "outflow_bounded")
        and not _boolean(facts, "attack_label_assessed")
    ):
        return _complete("lending_flow_confirmed")
    return _partial("estimated_incomplete")


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
