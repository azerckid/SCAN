"""Strict TASK-018 case-bundle parsing and raw-first reconciliation."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    ContractDatetime,
    ContractModel,
    FixtureId,
    NonEmptyUniqueList,
    Sha256,
    TransactionHash,
)
from scan_tool.domain.analysis_request import CaseCategory

APPROVED_CASE_FIXTURE_ID = "FX-CASE-EULER-EXIT-001"
APPROVED_SOURCE_PIN_HASHES = {
    "FX-FLOW-PATH-001": (
        "b761531a1364ddc28e5c6bb6a1d0b3b1432ee053fa2591210570a6113a099504",
        "05f9cab3d8aad9ee66238339f3c2aa2626d3060a19634b377df48cb79149ec85",
    ),
    "FX-FLOW-REMERGE-001": (
        "627c47ffb39dcb8c5179883a8c84c1ac92fca14ef08cf23dd5cfbfd804437cad",
        "b5b193f0511a2d7dac327a33a1dd214ba41bb4aa0e9bb7e8f341c1ea7d5ffe88",
    ),
}


class CaseReconciliationIncomplete(ValueError):
    """Raised when a reviewed case bundle cannot prove full case scope."""


class CaseSourcePin(ContractModel):
    fixture_id: FixtureId
    expected_sha256: Sha256
    evidence_sha256: Sha256


class CaseReconciliationReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: Literal["FX-CASE-EULER-EXIT-001"]
    status: Literal["confirmed"]
    captured_at: ContractDatetime
    chain_id: Literal[1]
    case_category: CaseCategory
    seed_transaction_hash: TransactionHash
    source_fixture_refs: NonEmptyUniqueList[FixtureId]
    source_pins: list[CaseSourcePin] = Field(min_length=1)
    incident_context_url: Literal[
        "https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery"
    ]
    continuous_scope_scanned: Literal[False]
    attribution_assessed: Literal[False]

    @model_validator(mode="after")
    def pins_match_source_refs(self) -> "CaseReconciliationReplay":
        pin_ids = [pin.fixture_id for pin in self.source_pins]
        if len(pin_ids) != len(set(pin_ids)):
            raise PydanticCustomError("reconciliation_failed", "case source pins must be unique")
        if set(pin_ids) != set(self.source_fixture_refs):
            raise PydanticCustomError(
                "reconciliation_failed",
                "case source pins must exactly match source_fixture_refs",
            )
        observed = {
            pin.fixture_id: (pin.expected_sha256, pin.evidence_sha256) for pin in self.source_pins
        }
        if observed != APPROVED_SOURCE_PIN_HASHES:
            raise PydanticCustomError(
                "reconciliation_failed",
                "case source pins differ from the approved registry",
            )
        return self


def parse_case_reconciliation_replay(raw_bytes: bytes) -> CaseReconciliationReplay:
    return CaseReconciliationReplay.model_validate_json(raw_bytes)


def reconstruct_case_facts(
    package_dir: Path,
    replay: CaseReconciliationReplay,
    *,
    max_timeline_entries: int,
) -> dict[str, object]:
    """Recompute one bounded post-incident case from confirmed source fixtures."""
    if replay.case_category is not CaseCategory.EXPLOIT:
        raise CaseReconciliationIncomplete(
            "Only the reviewed exploit-exit composition has confirmed source fixtures."
        )
    fixtures_root = package_dir.resolve().parent
    loaded: dict[str, tuple[dict[str, object], dict[str, object]]] = {}
    for pin in replay.source_pins:
        source_dir = (fixtures_root / pin.fixture_id).resolve()
        if not source_dir.is_relative_to(fixtures_root):
            raise ValueError("source fixture escapes the fixture root")
        expected = _read_pinned_object(source_dir / "expected.json", pin.expected_sha256)
        evidence = _read_pinned_object(source_dir / "evidence.json", pin.evidence_sha256)
        if expected.get("fixture_id") != pin.fixture_id:
            raise ValueError("source expected fixture ID mismatch")
        if evidence.get("fixture_id") != pin.fixture_id:
            raise ValueError("source evidence fixture ID mismatch")
        if expected.get("status") != "confirmed" or evidence.get("status") != "confirmed":
            raise CaseReconciliationIncomplete("all case source fixtures must be confirmed")
        loaded[pin.fixture_id] = (expected, evidence)

    try:
        path_expected, _ = loaded["FX-FLOW-PATH-001"]
        remerge_expected, _ = loaded["FX-FLOW-REMERGE-001"]
    except KeyError as error:
        raise CaseReconciliationIncomplete(
            "The exploit-exit composition requires PATH and REMERGE fixtures."
        ) from error

    graph = _object(path_expected["graph"])
    raw_edges = [_object(item) for item in _list(graph["edges"])]
    if not raw_edges:
        raise ValueError("case path cannot be empty")
    if raw_edges[0].get("transaction_hash") != replay.seed_transaction_hash:
        raise ValueError("case seed transaction differs from the first confirmed path edge")
    ordered_edges = sorted(
        raw_edges,
        key=lambda item: (
            int(item["block_number"]),
            int(item.get("transaction_index", -1)),
            str(item["edge_id"]),
        ),
    )
    if ordered_edges != raw_edges:
        raise ValueError("source path timeline is not canonically ordered")

    branches = [_object(item) for item in _list(remerge_expected["branches"])]
    excluded_edges = [_object(item) for item in _list(remerge_expected["excluded_edges"])]
    timeline = [
        {
            "sequence": index,
            "block_number": int(edge["block_number"]),
            "transaction_hash": str(edge["transaction_hash"]),
            "from_address": str(edge["from_node"]),
            "to_address": str(edge["to_node"]),
            "amount_raw": str(edge["amount_raw"]),
            "event_kind": "selected_exit_transfer",
        }
        for index, edge in enumerate(ordered_edges, start=1)
    ]
    timeline = timeline[:max_timeline_entries]

    return {
        "case_category": replay.case_category.value,
        "case_scope": "selected_post_incident_exit",
        "seed_transaction_hash": replay.seed_transaction_hash,
        "timeline": timeline,
        "reconciliation": {
            "selected_path_hop_count": len(timeline),
            "branch_count": len(branches),
            "merge_node": str(remerge_expected["merge_node"]),
            "unrelated_inflow_excluded": bool(excluded_edges),
            "unresolved_residual_raw": str(
                _object(remerge_expected["reconciliation"])["unresolved_residual_raw"]
            ),
        },
        "scope": {
            "source_fixture_refs": sorted(replay.source_fixture_refs),
            "selected_transactions_only": True,
            "continuous_scope_scanned": False,
            "full_incident_reconstruction": False,
        },
        "attribution": {
            "incident_context": "external_context",
            "address_ownership": "not_assessed",
            "criminal_intent": "not_assessed",
            "exploit_causation": "not_assessed",
        },
    }


def _read_pinned_object(path: Path, expected_sha256: str) -> dict[str, object]:
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError(f"source fixture hash mismatch: {path.name}")
    value = json.loads(body)
    return _object(value)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("expected list")
    return value
