"""Offline negative-oracle contract for the TASK-016 CEX cluster candidate."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-CEX-SCOPE-SYNTHESIS",
        "OR-CEX-LABEL-WITHOUT-SOURCE",
        "OR-CEX-SINGLE-COUNTERPARTY-CAP",
        "OR-CEX-EXPLORER-TAG-REJECTED",
        "OR-CEX-WINDOW-OUT-OF-SCOPE",
        "OR-CEX-HOT-WALLET-MISMATCH",
        "OR-CEX-ATTRIBUTION-ASSESSED-REJECTED",
        "OR-CEX-COMPLETE-MATCH",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-CEX-[A-Z0-9-]+$")
    fixture_id: Literal["FX-SVC-CEX-001"]
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
            raise ValueError("TASK-016 CEX negative oracle set drifted")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    return _evaluate_cex(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    verified = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(f"{case.oracle_id} result differs")
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_cex(facts: dict[str, Any]) -> dict[str, Any]:
    """Mirror doc 22 section 6 complete/partial/failed decision boundary."""
    if not _boolean(facts, "scope_bound"):
        return _failed("scope_synthesis_rejected")
    if _boolean(facts, "explorer_tag_as_truth"):
        return _failed("explorer_tag_rejected")
    if _boolean(facts, "attribution_assessed"):
        return _failed("attribution_assessed_rejected")
    if _boolean(facts, "window_violation"):
        return _failed("observation_window_violation")
    if _boolean(facts, "expected_hot_wallet_mismatch"):
        return _failed("hot_wallet_binding_failed")
    if _boolean(facts, "label_outbound_conflict"):
        return _failed("label_outbound_mismatch")
    if not _boolean(facts, "label_source_present"):
        if (
            _boolean(facts, "common_destination_present")
            and _number(facts, "deposit_source_count") >= 2
        ):
            return _partial("estimated_without_label")
        return _partial("label_missing")
    if _number(facts, "deposit_source_count") < 2:
        return _partial("insufficient_deposit_sources")
    if _boolean(facts, "single_counterparty_only") and not _boolean(facts, "label_covers_deposits"):
        return _partial("single_counterparty_capped")
    if (
        _boolean(facts, "common_destination_present")
        and _boolean(facts, "label_covers_deposits")
        and _number(facts, "deposit_source_count") >= 2
        and _boolean(facts, "pattern_present")
    ):
        return _complete("cex_cluster_confirmed")
    return _partial("estimated_pattern_only")


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


def _number(facts: dict[str, Any], key: str) -> int:
    value = facts.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value
