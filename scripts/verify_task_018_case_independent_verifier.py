"""Stdlib-only independent verifier for the bounded TASK-018 case fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-CASE-EULER-EXIT-001"
FIXTURES = PACKAGE.parent
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


def canonical_hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def recompute() -> dict[str, object]:
    replay = _object(json.loads((PACKAGE / "raw-replay.json").read_bytes()))
    if replay.get("fixture_id") != "FX-CASE-EULER-EXIT-001":
        raise ValueError("case fixture ID is not approved")
    if replay.get("status") != "confirmed":
        raise ValueError("case fixture is not confirmed")
    sources = replay["source_pins"]
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("exactly two confirmed source fixture pins are required")
    loaded: dict[str, dict[str, object]] = {}
    for raw_pin in sources:
        pin = _object(raw_pin)
        fixture_id = str(pin["fixture_id"])
        source = (FIXTURES / fixture_id).resolve()
        if not source.is_relative_to(FIXTURES.resolve()):
            raise ValueError("fixture path escapes root")
        expected_body = (source / "expected.json").read_bytes()
        evidence_body = (source / "evidence.json").read_bytes()
        if hashlib.sha256(expected_body).hexdigest() != pin["expected_sha256"]:
            raise ValueError("expected hash mismatch")
        if hashlib.sha256(evidence_body).hexdigest() != pin["evidence_sha256"]:
            raise ValueError("evidence hash mismatch")
        expected = _object(json.loads(expected_body))
        evidence = _object(json.loads(evidence_body))
        if expected["status"] != "confirmed" or evidence["status"] != "confirmed":
            raise ValueError("source fixture is not confirmed")
        loaded[fixture_id] = expected
    observed_pins = {
        str(_object(pin)["fixture_id"]): (
            str(_object(pin)["expected_sha256"]),
            str(_object(pin)["evidence_sha256"]),
        )
        for pin in sources
    }
    if observed_pins != APPROVED_SOURCE_PIN_HASHES:
        raise ValueError("source pins differ from the approved registry")

    path = loaded["FX-FLOW-PATH-001"]
    remerge = loaded["FX-FLOW-REMERGE-001"]
    graph = _object(path["graph"])
    edges = [_object(item) for item in _list(graph["edges"])]
    edges.sort(
        key=lambda item: (
            int(item["block_number"]),
            int(item.get("transaction_index", -1)),
            str(item["edge_id"]),
        )
    )
    if edges[0]["transaction_hash"] != replay["seed_transaction_hash"]:
        raise ValueError("seed is not first path edge")
    excluded = [_object(item) for item in _list(remerge["excluded_edges"])]
    branches = [_object(item) for item in _list(remerge["branches"])]
    return {
        "case_category": str(replay["case_category"]),
        "case_scope": "selected_post_incident_exit",
        "seed_transaction_hash": str(replay["seed_transaction_hash"]),
        "timeline": [
            {
                "sequence": index,
                "block_number": int(edge["block_number"]),
                "transaction_hash": str(edge["transaction_hash"]),
                "from_address": str(edge["from_node"]),
                "to_address": str(edge["to_node"]),
                "amount_raw": str(edge["amount_raw"]),
                "event_kind": "selected_exit_transfer",
            }
            for index, edge in enumerate(edges, start=1)
        ],
        "reconciliation": {
            "selected_path_hop_count": len(edges),
            "branch_count": len(branches),
            "merge_node": str(remerge["merge_node"]),
            "unrelated_inflow_excluded": bool(excluded),
            "unresolved_residual_raw": str(
                _object(remerge["reconciliation"])["unresolved_residual_raw"]
            ),
        },
        "scope": {
            "source_fixture_refs": sorted(str(value) for value in replay["source_fixture_refs"]),
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


def verify() -> str:
    first = recompute()
    second = recompute()
    if first != second:
        raise ValueError("independent verifier is non-deterministic")
    expected = _object(json.loads((PACKAGE / "expected.json").read_bytes()))
    facts = _object(expected["expected_facts"])
    reconciliation = _object(first["reconciliation"])
    scope = _object(first["scope"])
    attribution = _object(first["attribution"])
    observed = {
        "selected_path_hop_count": reconciliation["selected_path_hop_count"],
        "branch_count": reconciliation["branch_count"],
        "merge_node": reconciliation["merge_node"],
        "unrelated_inflow_excluded": reconciliation["unrelated_inflow_excluded"],
        "continuous_scope_scanned": scope["continuous_scope_scanned"],
        "full_incident_reconstruction": scope["full_incident_reconstruction"],
        "address_ownership": attribution["address_ownership"],
        "criminal_intent": attribution["criminal_intent"],
        "exploit_causation": attribution["exploit_causation"],
    }
    if observed != facts:
        raise ValueError("independent facts differ from expected fixture facts")
    return canonical_hash(first)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("expected object")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("expected list")
    return value


if __name__ == "__main__":
    print(f"PASS TASK-018 independent verifier twice · fact_sha256={verify()}")
