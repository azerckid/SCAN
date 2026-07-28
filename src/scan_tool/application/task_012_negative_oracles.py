"""Offline negative-oracle contract for TASK-012 fixture promotion."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]
type OracleCategory = Literal[
    "object_classification",
    "transaction_fee",
    "historical_state",
    "token_transfer",
    "native_inflow",
]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-BASIC-OBJECT-MALFORMED",
        "OR-BASIC-OBJECT-CHECKSUM",
        "OR-BASIC-OBJECT-RPC-UNAVAILABLE",
        "OR-BASIC-FEE-GAS-LIMIT",
        "OR-BASIC-STATE-LATEST",
        "OR-BASIC-STATE-BLOCK-MISMATCH",
        "OR-BASIC-STATE-DECIMALS",
        "OR-BASIC-STATE-PRECISION",
        "OR-TOKEN-FAILED-TX",
        "OR-TOKEN-UNRELATED-LOG",
        "OR-TOKEN-DIFFERENT-ASSET",
        "OR-TOKEN-ZERO-VALUE",
        "OR-TOKEN-PAGINATION",
        "OR-NATIVE-TRACE-UNAVAILABLE",
        "OR-NATIVE-NO-VALUE",
        "OR-NATIVE-FAILED-CALL",
        "OR-NATIVE-MULTIPLE-INFLOWS",
        "OR-NATIVE-TRUNCATED",
        "OR-NATIVE-TOP-LEVEL-SUBSTITUTION",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-[A-Z0-9-]+$")
    fixture_id: str = Field(pattern=r"^FX-(BASIC-EVM|EVM-TOKEN)-00[12]$")
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
        missing = REQUIRED_ORACLE_IDS - set(ids)
        if missing:
            raise ValueError(f"required negative oracles are missing: {sorted(missing)}")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    """Load the strict offline manifest without performing any network I/O."""
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    """Evaluate one bounded synthetic counterexample."""
    match case.category:
        case "object_classification":
            return _evaluate_object(case.facts)
        case "transaction_fee":
            return _evaluate_fee(case.facts)
        case "historical_state":
            return _evaluate_state(case.facts)
        case "token_transfer":
            return _evaluate_transfer(case.facts)
        case "native_inflow":
            return _evaluate_native_inflow(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    """Return verified oracle IDs or raise on the first contract mismatch."""
    verified: list[str] = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(
                f"{case.oracle_id} mismatch: expected {case.expected!r}, got {actual!r}"
            )
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_object(facts: dict[str, Any]) -> dict[str, Any]:
    lexical_type = _text(facts, "lexical_type")
    reported_type = _text(facts, "reported_type")
    if lexical_type == "malformed":
        outcome: OracleOutcome = "complete" if reported_type == "invalid" else "failed"
        return {"outcome": outcome, "classification": reported_type}
    if not _boolean(facts, "rpc_available") or not _boolean(facts, "code_available"):
        return {"outcome": "partial", "classification": reported_type}
    return {"outcome": "complete", "classification": reported_type}


def _evaluate_fee(facts: dict[str, Any]) -> dict[str, Any]:
    exact_fee = _integer(facts, "gas_used") * _integer(facts, "effective_gas_price")
    reported_fee = _integer(facts, "reported_fee")
    return {
        "outcome": "complete" if reported_fee == exact_fee else "failed",
        "fee_paid_wei": str(reported_fee),
    }


def _evaluate_state(facts: dict[str, Any]) -> dict[str, Any]:
    requested_tag = _text(facts, "requested_block_tag")
    observed_tag = _text(facts, "observed_block_tag")
    amount_raw = _text(facts, "amount_raw")
    if observed_tag == "latest" or observed_tag != requested_tag:
        return {"outcome": "failed", "amount_raw": amount_raw}
    if not _boolean(facts, "raw_available") or not _boolean(facts, "decimals_available"):
        return {"outcome": "partial", "amount_raw": amount_raw}
    if not _boolean(facts, "precision_preserved"):
        return {"outcome": "failed", "amount_raw": amount_raw}
    return {"outcome": "complete", "amount_raw": amount_raw}


def _evaluate_transfer(facts: dict[str, Any]) -> dict[str, Any]:
    candidates = facts.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("token_transfer candidates must be an array")
    matching = [
        item
        for item in candidates
        if isinstance(item, dict)
        and str(item.get("token", "")).lower() == _text(facts, "target_token").lower()
        and str(item.get("sender", "")).lower() == _text(facts, "target_sender").lower()
        and int(item.get("amount_raw", 0)) > 0
        and item.get("receipt_status") == "success"
    ]
    matching.sort(
        key=lambda item: (
            int(item["block_number"]),
            int(item["transaction_index"]),
            int(item["log_index"]),
        )
    )
    selected_id = matching[0]["event_id"] if matching else None
    if not _boolean(facts, "pagination_complete"):
        return {"outcome": "partial", "selected_id": selected_id}
    return {"outcome": "complete", "selected_id": selected_id}


def _evaluate_native_inflow(facts: dict[str, Any]) -> dict[str, Any]:
    if not _boolean(facts, "trace_available"):
        return {"outcome": "partial", "amount_wei": "0"}
    calls = facts.get("calls")
    if not isinstance(calls, list):
        raise ValueError("native_inflow calls must be an array")
    target = _text(facts, "target").lower()
    amount = sum(
        int(item.get("value_wei", 0))
        for item in calls
        if isinstance(item, dict)
        and str(item.get("to", "")).lower() == target
        and item.get("status") == "success"
    )
    outcome: OracleOutcome = "partial" if _boolean(facts, "trace_truncated") else "complete"
    if "reported_amount_wei" in facts and int(facts["reported_amount_wei"]) != amount:
        outcome = "failed"
    return {"outcome": outcome, "amount_wei": str(amount)}


def _text(facts: dict[str, Any], key: str) -> str:
    value = facts.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text")
    return value


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
