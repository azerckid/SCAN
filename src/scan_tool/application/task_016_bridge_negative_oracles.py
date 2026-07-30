"""Offline negative-oracle contract for the TASK-016 Bridge candidate."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-BRIDGE-WRONG-DEPOSIT-MATCH",
        "OR-BRIDGE-HEURISTIC-NOT-PROMOTED",
        "OR-BRIDGE-TOLERANCE-WITHOUT-MAPPING",
        "OR-BRIDGE-DESTINATION-EVIDENCE-MISSING",
        "OR-BRIDGE-SCOPE-SYNTHESIS",
        "OR-BRIDGE-DOMAIN-COLLISION",
        "OR-BRIDGE-AMOUNT-FORMULA-MISMATCH",
        "OR-BRIDGE-COMPLETE-MATCH",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-BRIDGE-[A-Z0-9-]+$")
    fixture_id: Literal["FX-SVC-BRG-001"]
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
            raise ValueError("TASK-016 Bridge negative oracle set drifted")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    return _evaluate_bridge(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    verified = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(f"{case.oracle_id} result differs")
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_bridge(facts: dict[str, Any]) -> dict[str, Any]:
    """Mirror doc 21 §6's complete/partial/failed decision boundary.

    This is an independently authored reference classifier, not the product
    ``bridge_transfer`` analyzer (which doesn't exist yet per doc 21 §5). It
    freezes the fixture's decision boundary so the later analyzer can be
    checked against it, the same role TASK-014's oracle module played before
    the ``flow_path`` analyzer existed.
    """
    if not _boolean(facts, "scope_bound"):
        return _failed("scope_synthesis_rejected")
    if _boolean(facts, "keys_collide_across_domains") and not _boolean(facts, "domain_separated"):
        return _failed("domain_separation_violation")
    if not _boolean(facts, "correct_pair_selected"):
        return _failed("wrong_deposit_pair_matched")
    if not _boolean(facts, "deterministic_key_present"):
        return _partial("heuristic_candidate_only")
    if not _boolean(facts, "destination_evidence_available"):
        return _partial("destination_evidence_missing")
    if not _boolean(facts, "official_asset_mapping_present") or not _boolean(
        facts, "official_fee_mapping_present"
    ):
        # doc 21 §6 negative oracle 3: reject the promotion but keep the
        # destination at candidate/partial, not a hard failure — there is no
        # contradiction yet, only an unverifiable amount claim.
        return _partial("amount_mapping_unverified")
    if not _boolean(facts, "amount_matches_via_official_formula"):
        return _failed("amount_reconciliation_failed")
    return _complete("bridge_transfer_matched")


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
