"""Offline negative-oracle contract for TASK-013 fixture promotion."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from scan_tool.domain._types import ContractModel

type OracleOutcome = Literal["complete", "partial", "failed"]
type OracleCategory = Literal["erc721", "erc1155", "eip1967"]

REQUIRED_ORACLE_IDS = frozenset(
    {
        "OR-NFT721-ERC20-SIGNATURE",
        "OR-NFT721-DIFFERENT-CONTRACT",
        "OR-NFT721-RANGE-INCOMPLETE",
        "OR-NFT721-TOKEN-ID-DATA",
        "OR-NFT721-TOPIC-COUNT",
        "OR-NFT1155-BATCH-LENGTH",
        "OR-NFT1155-ABI-TRUNCATED",
        "OR-NFT1155-DIFFERENT-CONTRACT",
        "OR-NFT1155-LOG-PAGE-INCOMPLETE",
        "OR-NFT1155-APPROVAL-INCOMPLETE",
        "OR-PROXY-LATEST-AS-BEFORE",
        "OR-PROXY-ADMIN-AS-IMPLEMENTATION",
        "OR-PROXY-EVENT-STATE-CONFLICT",
        "OR-PROXY-HISTORICAL-STATE-MISSING",
        "OR-PROXY-IMPLEMENTATION-BEACON-CONFLICT",
        "OR-PROXY-PATTERN-UNSUPPORTED",
    }
)


class NegativeOracleCase(ContractModel):
    oracle_id: str = Field(pattern=r"^OR-[A-Z0-9-]+$")
    fixture_id: str = Field(pattern=r"^FX-EVM-(NFT-(721|1155)|PROXY)-001$")
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
            missing = REQUIRED_ORACLE_IDS - set(ids)
            extra = set(ids) - REQUIRED_ORACLE_IDS
            raise ValueError(
                f"TASK-013 negative oracle set drifted: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        expected_fixtures = {
            "erc721": "FX-EVM-NFT-721-001",
            "erc1155": "FX-EVM-NFT-1155-001",
            "eip1967": "FX-EVM-PROXY-001",
        }
        for case in self.cases:
            if case.fixture_id != expected_fixtures[case.category]:
                raise ValueError(f"{case.oracle_id} fixture does not match {case.category}")
        return self


def load_negative_oracle_manifest(path: Path) -> NegativeOracleManifest:
    """Load the strict offline manifest without performing network I/O."""
    return NegativeOracleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_case(case: NegativeOracleCase) -> dict[str, Any]:
    """Evaluate one bounded synthetic counterexample."""
    match case.category:
        case "erc721":
            return _evaluate_erc721(case.facts)
        case "erc1155":
            return _evaluate_erc1155(case.facts)
        case "eip1967":
            return _evaluate_eip1967(case.facts)


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


def _evaluate_erc721(facts: dict[str, Any]) -> dict[str, Any]:
    if _text(facts, "observed_contract") != _text(facts, "target_contract"):
        return {"outcome": "complete", "classification": "excluded"}
    if not _boolean(facts, "range_complete"):
        return {"outcome": "partial", "classification": "erc721"}
    if _text(facts, "standard_evidence") != "erc721":
        return {"outcome": "failed", "classification": "standard_mismatch"}
    if _integer(facts, "topic_count") != 4:
        return {"outcome": "failed", "classification": "malformed_event"}
    if _text(facts, "token_id_source") != "topic3":
        return {"outcome": "failed", "classification": "malformed_event"}
    return {"outcome": "complete", "classification": "erc721"}


def _evaluate_erc1155(facts: dict[str, Any]) -> dict[str, Any]:
    if _text(facts, "observed_contract") != _text(facts, "target_contract"):
        return {"outcome": "complete", "classification": "excluded"}
    if not _boolean(facts, "log_page_complete"):
        return {"outcome": "partial", "classification": "erc1155"}
    if not _boolean(facts, "abi_complete"):
        return {"outcome": "failed", "classification": "malformed_event"}
    if _integer(facts, "ids_length") != _integer(facts, "values_length"):
        return {"outcome": "failed", "classification": "batch_length_mismatch"}
    if not _boolean(facts, "approval_scope_complete"):
        return {"outcome": "partial", "classification": "erc1155"}
    return {"outcome": "complete", "classification": "erc1155"}


def _evaluate_eip1967(facts: dict[str, Any]) -> dict[str, Any]:
    if _text(facts, "pattern") != "eip1967":
        return {"outcome": "failed", "classification": "pattern_unsupported"}
    if _optional_boolean(facts, "implementation_claimed") and _optional_boolean(
        facts, "beacon_claimed"
    ):
        return {"outcome": "failed", "classification": "proxy_route_conflict"}
    if not _boolean(facts, "historical_state_available"):
        return {"outcome": "partial", "classification": "state_unavailable"}
    if _text(facts, "before_block_tag") == "latest":
        return {"outcome": "failed", "classification": "historical_state_mismatch"}
    if _text(facts, "decoded_slot_role") != "implementation":
        return {"outcome": "failed", "classification": "slot_role_mismatch"}
    if _text(facts, "event_implementation") != _text(facts, "after_implementation"):
        return {"outcome": "failed", "classification": "event_state_conflict"}
    return {"outcome": "complete", "classification": "eip1967"}


def _text(facts: dict[str, Any], key: str) -> str:
    value = facts.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text")
    return value.lower()


def _boolean(facts: dict[str, Any], key: str) -> bool:
    value = facts.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _optional_boolean(facts: dict[str, Any], key: str) -> bool:
    value = facts.get(key, False)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _integer(facts: dict[str, Any], key: str) -> int:
    value = facts.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value
