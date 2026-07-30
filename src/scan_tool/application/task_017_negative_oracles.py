"""Offline negative-oracle classifier for TASK-017 Bitcoin boundaries."""

from typing import Literal

from pydantic import Field

from scan_tool.domain._types import ContractModel, NonEmptyString


class BitcoinOracleCase(ContractModel):
    oracle_id: NonEmptyString
    category: Literal[
        "fee_mismatch",
        "missing_prevout",
        "duplicate_outpoint",
        "change_overclaim",
        "coinjoin_overclaim",
        "equal_output_candidate",
        "complete_control",
    ]
    facts: dict[str, object] = Field(min_length=1)


class BitcoinOracleOutcome(ContractModel):
    status: Literal["complete", "partial", "failed"]
    code: NonEmptyString


def evaluate_bitcoin_oracle(case: BitcoinOracleCase) -> BitcoinOracleOutcome:
    if case.category in {"fee_mismatch", "duplicate_outpoint"}:
        return BitcoinOracleOutcome(status="failed", code="reconciliation_failed")
    if case.category == "missing_prevout":
        return BitcoinOracleOutcome(status="partial", code="source_unavailable")
    if case.category in {"change_overclaim", "coinjoin_overclaim"}:
        return BitcoinOracleOutcome(status="failed", code="evidence_incomplete")
    if case.category == "equal_output_candidate":
        return BitcoinOracleOutcome(status="partial", code="heuristic_candidate")
    return BitcoinOracleOutcome(status="complete", code="verified")
