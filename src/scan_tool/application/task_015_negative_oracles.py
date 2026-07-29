"""Offline negative-oracle contract for TASK-015 Intelligence fixtures."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleCategory = Literal[
    "label_conflict",
    "sanctions_history",
    "ens_resolution",
    "common_funder",
    "relation_hub",
]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-INTEL-LABEL-SUBJECT-SWAP",
        "OR-INTEL-LABEL-ROW-HASH-MISMATCH",
        "OR-INTEL-LABEL-AUTO-MERGE",
        "OR-INTEL-LABEL-TRUTH-PROMOTION",
        "OR-INTEL-LABEL-ENS-MISSING",
        "OR-INTEL-LABEL-VALID-CONFLICT",
        "OR-INTEL-SAN-INDIRECT-AS-DIRECT",
        "OR-INTEL-SAN-REMOVAL-MISSING",
        "OR-INTEL-SAN-TIMELINE-REVERSED",
        "OR-INTEL-SAN-STALE-CURRENT",
        "OR-INTEL-SAN-CRIMINALITY-PROMOTION",
        "OR-INTEL-SAN-VALID-HISTORY",
        "OR-INTEL-ENS-SUBJECT-SWAP",
        "OR-INTEL-ENS-FORWARD-MISSING",
        "OR-INTEL-ENS-MISMATCH",
        "OR-INTEL-ENS-LATEST-SUBSTITUTION",
        "OR-INTEL-ENS-OWNERSHIP-PROMOTION",
        "OR-INTEL-ENS-VALID-BINDING",
        "OR-INTEL-FUNDER-NONSEED-INCLUDED",
        "OR-INTEL-FUNDER-AMOUNT-MISMATCH",
        "OR-INTEL-FUNDER-PREHISTORY-MISSING",
        "OR-INTEL-FUNDER-SERVICE-UNKNOWN",
        "OR-INTEL-FUNDER-OWNERSHIP-PROMOTION",
        "OR-INTEL-FUNDER-VALID-CANDIDATE",
        "OR-INTEL-HUB-SOURCE-MISSING",
        "OR-INTEL-HUB-SUBJECT-MERGED",
        "OR-INTEL-HUB-PUBLIC-ROLE-UNKNOWN",
        "OR-INTEL-HUB-NOT-EXCLUDED",
        "OR-INTEL-HUB-TRUTH-PROMOTION",
        "OR-INTEL-HUB-VALID-EXCLUSION",
    }
)

FIXTURE_BY_CATEGORY = {
    "label_conflict": "FX-OSINT-LABEL-CONFLICT-001",
    "sanctions_history": "FX-OSINT-SANCTIONS-HISTORY-001",
    "ens_resolution": "FX-OSINT-ENS-CONFLICT-001",
    "common_funder": "FX-ACTOR-COMMON-FUNDER-001",
    "relation_hub": "FX-ACTOR-RELATION-HUB-001",
}


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-INTEL-[A-Z0-9-]+$")
    fixture_id: str = Field(
        pattern=r"^FX-(OSINT-(LABEL-CONFLICT|SANCTIONS-HISTORY|ENS-CONFLICT)|"
        r"ACTOR-(COMMON-FUNDER|RELATION-HUB))-001$"
    )
    category: OracleCategory
    facts: dict[str, Any]
    expected: dict[str, str]


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
            missing = REQUIRED_ORACLE_IDS - set(ids)
            extra = set(ids) - REQUIRED_ORACLE_IDS
            raise ValueError(
                f"TASK-015 negative oracle set drifted: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for case in self.cases:
            if case.fixture_id != FIXTURE_BY_CATEGORY[case.category]:
                raise ValueError(f"{case.oracle_id} fixture/category differs")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    """Load the strict offline manifest without network I/O."""
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, str]:
    """Evaluate one source/claim/relation counterexample."""
    match case.category:
        case "label_conflict":
            return _evaluate_label(case.facts)
        case "sanctions_history":
            return _evaluate_sanctions(case.facts)
        case "ens_resolution":
            return _evaluate_ens(case.facts)
        case "common_funder":
            return _evaluate_funder(case.facts)
        case "relation_hub":
            return _evaluate_hub(case.facts)


def verify_manifest(manifest: NegativeOracleManifest) -> tuple[str, ...]:
    """Return verified IDs or raise at the first contract mismatch."""
    verified: list[str] = []
    for case in manifest.cases:
        actual = evaluate_case(case)
        if actual != case.expected:
            raise ValueError(
                f"{case.oracle_id} mismatch: expected {case.expected!r}, got {actual!r}"
            )
        verified.append(case.oracle_id)
    return tuple(verified)


def _evaluate_label(facts: dict[str, Any]) -> dict[str, str]:
    if not _boolean(facts, "subject_matches"):
        return _failed("subject_mismatch")
    if not _boolean(facts, "selected_row_hash_matches"):
        return _failed("source_integrity_failed")
    if _boolean(facts, "auto_merged"):
        return _failed("source_assertion_merged")
    if _boolean(facts, "ownership_promoted") or _boolean(facts, "criminality_promoted"):
        return _failed("unsupported_truth_promotion")
    if not _boolean(facts, "conflict_preserved"):
        return _failed("conflict_suppressed")
    if not _boolean(facts, "ens_binding_available"):
        return _partial("source_unavailable")
    return _complete("label_conflict")


def _evaluate_sanctions(facts: dict[str, Any]) -> dict[str, str]:
    if not _boolean(facts, "direct_address_match"):
        return _failed("direct_match_mismatch")
    if not _boolean(facts, "timeline_ordered"):
        return _failed("timeline_reconciliation_failed")
    if _boolean(facts, "current_status_promoted"):
        return _failed("stale_status_promotion")
    if _boolean(facts, "criminality_promoted"):
        return _failed("unsupported_truth_promotion")
    if not _boolean(facts, "designation_available") or not _boolean(facts, "removal_available"):
        return _partial("source_unavailable")
    return _complete("sanctions_history")


def _evaluate_ens(facts: dict[str, Any]) -> dict[str, str]:
    if not _boolean(facts, "subject_matches"):
        return _failed("subject_mismatch")
    if _boolean(facts, "latest_substituted"):
        return _failed("historical_state_mismatch")
    if _boolean(facts, "ownership_promoted"):
        return _failed("unsupported_truth_promotion")
    if not _boolean(facts, "forward_available") or not _boolean(facts, "reverse_available"):
        return _partial("source_unavailable")
    if not _boolean(facts, "forward_reverse_match"):
        return _failed("ens_resolution_conflict")
    return _complete("ens_resolution")


def _evaluate_funder(facts: dict[str, Any]) -> dict[str, str]:
    if _boolean(facts, "nonseed_inflow_included"):
        return _failed("relation_scope_mismatch")
    if not _boolean(facts, "amounts_match"):
        return _failed("amount_reconciliation_failed")
    if _boolean(facts, "ownership_promoted") or _boolean(facts, "coordination_promoted"):
        return _failed("unsupported_truth_promotion")
    if not _boolean(facts, "prehistory_complete"):
        return _partial("prehistory_unavailable")
    if not _boolean(facts, "service_exclusion_complete"):
        return _partial("service_exclusion_unavailable")
    return _complete("common_funder_candidate")


def _evaluate_hub(facts: dict[str, Any]) -> dict[str, str]:
    if not _boolean(facts, "subjects_distinct"):
        return _failed("subject_merge")
    if _boolean(facts, "ownership_promoted") or _boolean(facts, "coordination_promoted"):
        return _failed("unsupported_truth_promotion")
    if not _boolean(facts, "hub_excluded"):
        return _failed("public_hub_false_positive")
    if not _boolean(facts, "both_relations_available"):
        return _partial("source_unavailable")
    if not _boolean(facts, "public_hub_role_confirmed"):
        return _partial("hub_role_unavailable")
    return _complete("public_hub_exclusion")


def _complete(classification: str) -> dict[str, str]:
    return {"outcome": "complete", "classification": classification}


def _partial(classification: str) -> dict[str, str]:
    return {"outcome": "partial", "classification": classification}


def _failed(classification: str) -> dict[str, str]:
    return {"outcome": "failed", "classification": classification}


def _boolean(facts: dict[str, Any], key: str) -> bool:
    value = facts.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value
