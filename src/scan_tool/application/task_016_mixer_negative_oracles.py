"""Offline negative-oracle contract for the TASK-016 mixer flow candidate."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-MIX-SCOPE-SYNTHESIS",
        "OR-MIX-UNLABELED-POOL",
        "OR-MIX-HEURISTIC-TO-FACT",
        "OR-MIX-WINDOW-ABUSE",
        "OR-MIX-CRIMINALITY-ASSESSED",
        "OR-MIX-EVIDENCE-OMISSION",
        "OR-MIX-SINGLE-EXIT-PROMOTION",
        "OR-MIX-COMPLETE-MATCH",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-MIX-[A-Z0-9-]+$")
    fixture_id: Literal["FX-SVC-MIX-001"]
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
            raise ValueError("TASK-016 mixer negative oracle set drifted")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    return _evaluate_mixer(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    verified = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(f"{case.oracle_id} result differs")
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_mixer(facts: dict[str, Any]) -> dict[str, Any]:
    """Mirror doc 23 section 6 complete/partial/failed decision boundary."""
    if not _boolean(facts, "scope_bound"):
        return _failed("scope_synthesis_rejected")
    if _boolean(facts, "explorer_tag_as_truth"):
        return _failed("explorer_tag_rejected")
    if _boolean(facts, "attribution_assessed"):
        return _failed("attribution_assessed_rejected")
    if _boolean(facts, "window_violation"):
        return _failed("observation_window_violation")
    if _boolean(facts, "single_exit_promoted"):
        return _failed("single_exit_ownership_rejected")
    if _boolean(facts, "heuristic_promoted_to_fact"):
        return _failed("heuristic_promotion_rejected")
    if not _boolean(facts, "label_source_present"):
        if _boolean(facts, "deposit_present") and _boolean(facts, "withdraw_present"):
            return _partial("estimated_without_label")
        return _partial("label_missing")
    if not _boolean(facts, "pool_labeled"):
        return _partial("unlabeled_pool")
    if _boolean(facts, "evidence_omitted"):
        return _partial("evidence_incomplete")
    if (
        _boolean(facts, "deposit_present")
        and _boolean(facts, "withdraw_present")
        and _boolean(facts, "label_covers_pool")
        and _boolean(facts, "candidates_heuristic_only")
    ):
        return _complete("mixer_flow_confirmed")
    return _partial("estimated_candidates_only")


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
