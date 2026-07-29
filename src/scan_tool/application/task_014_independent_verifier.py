"""Independent raw-first graph and ledger verifier for TASK-014 fixtures."""

import hashlib
import json
from pathlib import Path
from typing import Any

FIXTURE_IDS = (
    "FX-FLOW-PATH-001",
    "FX-FLOW-REMERGE-001",
    "FX-FLOW-MULTI-001",
)

REQUIREMENTS = {
    "FX-FLOW-PATH-001": ("REQ-FLOW-PATH-ORDER", "REQ-FLOW-PATH-SCOPE"),
    "FX-FLOW-REMERGE-001": (
        "REQ-FLOW-REMERGE-BRANCHES",
        "REQ-FLOW-REMERGE-LEDGER",
    ),
    "FX-FLOW-MULTI-001": (
        "REQ-FLOW-MULTI-CONTRIBUTIONS",
        "REQ-FLOW-MULTI-TOTAL",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def verify_repository(fixtures_root: Path) -> tuple[dict[str, Any], ...]:
    reports = []
    for fixture_id in FIXTURE_IDS:
        package = fixtures_root / fixture_id
        reports.append(
            verify_fixture(
                load_json(package / "raw-replay.json"),
                load_json(package / "expected.json"),
                load_json(package / "evidence.json"),
            )
        )
    return tuple(reports)


def verify_fixture(
    raw: dict[str, Any],
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    fixture_id = _text(raw, "fixture_id")
    if _text(expected, "fixture_id") != fixture_id:
        raise ValueError("raw/expected fixture IDs differ")
    if _text(evidence, "fixture_id") != fixture_id:
        raise ValueError("raw/evidence fixture IDs differ")
    facts = recalculate_raw_facts(raw)
    if facts != _expected_projection(fixture_id, expected):
        raise ValueError(f"{fixture_id} independently calculated facts differ")
    _verify_evidence(fixture_id, facts, evidence)
    _verify_requirements(fixture_id, expected, evidence)
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": hashlib.sha256(canonical).hexdigest(),
        "requirement_count": len(REQUIREMENTS[fixture_id]),
    }


def recalculate_raw_facts(raw: dict[str, Any]) -> dict[str, Any]:
    fixture_id = _text(raw, "fixture_id")
    scope = _mapping(raw, "scope")
    if (
        scope.get("selected_transactions_complete") is not True
        or scope.get("kind") != "selected_transactions_and_exact_blocks"
    ):
        raise ValueError("selected transaction scope is incomplete")
    transactions = _validated_transactions(raw)
    if fixture_id == "FX-FLOW-PATH-001":
        return _path(transactions, raw)
    if fixture_id == "FX-FLOW-REMERGE-001":
        return _remerge(transactions)
    if fixture_id == "FX-FLOW-MULTI-001":
        return _multi(transactions)
    raise ValueError("unsupported TASK-014 fixture")


def _path(transactions: dict[str, dict[str, Any]], raw: dict[str, Any]) -> dict[str, Any]:
    if set(transactions) != {"internal_seed", "split_a", "merge_a"}:
        raise ValueError("PATH selected transaction set differs")
    internal_edges = _object_array(raw, "internal_edges")
    if len(internal_edges) != 1:
        raise ValueError("PATH internal edge count differs")
    internal = internal_edges[0]
    first = _edge_from_internal(internal, transactions["internal_seed"])
    second = _edge_from_transaction("EDGE-PATH-002", transactions["split_a"])
    third = _edge_from_transaction("EDGE-PATH-003", transactions["merge_a"])
    first["edge_id"] = "EDGE-PATH-001"
    if first["to_node"] != second["from_node"] or second["to_node"] != third["from_node"]:
        raise ValueError("PATH endpoints do not join")
    nodes = [first["from_node"], first["to_node"], second["to_node"], third["to_node"]]
    return {
        "graph": {
            "node_count": 4,
            "edge_count": 3,
            "nodes": nodes,
            "edges": [first, second, third],
        },
        "path_candidates": [
            {
                "ordered_edge_ids": ["EDGE-PATH-001", "EDGE-PATH-002", "EDGE-PATH-003"],
                "hop_count": 3,
                "terminal_node": third["to_node"],
                "termination": "selected_terminal_reached",
            }
        ],
        "reconciliation": {
            "status": "unresolved_selected_path_scope",
            "reason": "The selected path does not claim a continuous scan of the seed's other outputs.",
            "raw_amounts_must_not_be_equalized": True,
        },
    }


def _remerge(transactions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected_labels = {
        "split_a",
        "split_b",
        "split_c",
        "split_d",
        "merge_c",
        "merge_a",
        "merge_d",
        "merge_b",
        "external_dust",
    }
    if set(transactions) != expected_labels:
        raise ValueError("REMERGE selected transaction set differs")
    split_order = ("split_a", "split_b", "split_c", "split_d")
    merge_by_origin = {
        _text(item["transaction"], "from"): item
        for label, item in transactions.items()
        if label.startswith("merge_")
    }
    branches = []
    for label in split_order:
        split = transactions[label]
        branch = _text(split["transaction"], "to")
        merge = merge_by_origin.get(branch)
        if merge is None:
            raise ValueError("REMERGE branch is missing")
        input_raw = _hex_raw(split["transaction"], "value")
        output_raw = _hex_raw(merge["transaction"], "value")
        branches.append(
            {
                "branch_node": branch,
                "input_raw": input_raw,
                "merge_output_raw": output_raw,
                "residual_raw": str(int(input_raw) - int(output_raw)),
            }
        )
    dust = transactions["external_dust"]["transaction"]
    return {
        "branches": branches,
        "reconciliation": {
            "confirmed_input_raw": str(sum(int(item["input_raw"]) for item in branches)),
            "confirmed_included_output_raw": str(
                sum(int(item["merge_output_raw"]) for item in branches)
            ),
            "confirmed_scoped_excluded_output_raw": "0",
            "explicit_fee_or_context_raw": "0",
            "unresolved_residual_raw": str(sum(int(item["residual_raw"]) for item in branches)),
            "external_inflow_raw_not_in_seed_ledger": _hex_raw(dust, "value"),
        },
        "excluded_edges": [
            {
                "transaction_hash": _text(dust, "hash"),
                "from_node": _text(dust, "from"),
                "to_node": _text(dust, "to"),
                "amount_raw": _hex_raw(dust, "value"),
                "reason": "external_inflow_not_from_seed",
                "scope_status": "excluded",
            }
        ],
    }


def _multi(transactions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    labels = ("merge_c", "merge_a", "merge_d", "merge_b")
    if set(transactions) != set(labels):
        raise ValueError("MULTI selected transaction set differs")
    contributions = []
    hashes = set()
    for label in labels:
        transaction = transactions[label]["transaction"]
        transaction_hash = _text(transaction, "hash")
        if transaction_hash in hashes:
            raise ValueError("MULTI transaction is duplicated")
        hashes.add(transaction_hash)
        contributions.append(
            {
                "origin_node": _text(transaction, "from"),
                "amount_raw": _hex_raw(transaction, "value"),
                "transaction_hash": transaction_hash,
                "block_number": int(_text(transaction, "blockNumber"), 16),
            }
        )
    exits = {_text(transactions[label]["transaction"], "to") for label in labels}
    if len(exits) != 1:
        raise ValueError("MULTI exits differ")
    return {
        "exit_node": exits.pop(),
        "contributions": contributions,
        "deduplicated_total_raw": str(sum(int(item["amount_raw"]) for item in contributions)),
        "price_context": {"status": "not_assessed", "included_in_scoring": False},
        "attribution": {
            "common_control_claim": False,
            "criminal_or_victim_claim": False,
            "status": "not_assessed",
        },
    }


def _validated_transactions(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in _object_array(raw, "transactions"):
        label = _text(item, "label")
        if label in result:
            raise ValueError("transaction labels must be unique")
        transaction = _mapping(item, "transaction")
        receipt = _mapping(item, "receipt")
        if _text(transaction, "hash") != _text(receipt, "transactionHash"):
            raise ValueError("transaction/receipt hashes differ")
        for field in ("blockHash", "blockNumber", "transactionIndex"):
            if _text(transaction, field) != _text(receipt, field):
                raise ValueError(f"transaction/receipt {field} differs")
        if _text(receipt, "status") != "0x1":
            raise ValueError("selected transaction failed")
        result[label] = {"transaction": transaction, "receipt": receipt}
    return result


def _edge_from_internal(
    edge: dict[str, Any],
    parent: dict[str, Any],
) -> dict[str, Any]:
    return {
        "from_node": _text(edge, "from"),
        "to_node": _text(edge, "to"),
        "amount_raw": _text(edge, "value_raw"),
        "transaction_hash": _text(parent["transaction"], "hash"),
        "block_number": int(_text(parent["transaction"], "blockNumber"), 16),
        "transfer_kind": "native_internal",
        "scope_status": "included",
    }


def _edge_from_transaction(edge_id: str, item: dict[str, Any]) -> dict[str, Any]:
    transaction = item["transaction"]
    return {
        "edge_id": edge_id,
        "from_node": _text(transaction, "from"),
        "to_node": _text(transaction, "to"),
        "amount_raw": _hex_raw(transaction, "value"),
        "transaction_hash": _text(transaction, "hash"),
        "block_number": int(_text(transaction, "blockNumber"), 16),
        "transaction_index": int(_text(transaction, "transactionIndex"), 16),
        "transfer_kind": "native_top_level",
        "scope_status": "included",
    }


def _expected_projection(fixture_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    if fixture_id == "FX-FLOW-PATH-001":
        return {
            "graph": expected["graph"],
            "path_candidates": expected["path_candidates"],
            "reconciliation": expected["reconciliation"],
        }
    if fixture_id == "FX-FLOW-REMERGE-001":
        return {
            "branches": expected["branches"],
            "reconciliation": expected["reconciliation"],
            "excluded_edges": expected["excluded_edges"],
        }
    return {
        "exit_node": expected["exit_node"],
        "contributions": expected["contributions"],
        "deduplicated_total_raw": expected["deduplicated_total_raw"],
        "price_context": expected["price_context"],
        "attribution": expected["attribution"],
    }


def _verify_evidence(
    fixture_id: str,
    facts: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    calls = {_text(item, "evidence_id"): item for item in _object_array(evidence, "call_evidence")}
    if fixture_id == "FX-FLOW-PATH-001":
        edges = facts["graph"]["edges"]
        mapping = (
            ("EV-FLOW-PATH-INTERNAL", edges[0]),
            ("EV-FLOW-PATH-HOP-2", edges[1]),
            ("EV-FLOW-PATH-HOP-3", edges[2]),
        )
        for evidence_id, edge in mapping:
            item = calls[evidence_id]
            if (
                _text(item, "transaction_hash") != edge["transaction_hash"]
                or _text(item, "from") != edge["from_node"]
                or _text(item, "to") != edge["to_node"]
                or _text(item, "amount_raw") != edge["amount_raw"]
            ):
                raise ValueError(f"{evidence_id} value differs")
    elif fixture_id == "FX-FLOW-REMERGE-001":
        ledger = calls["EV-FLOW-REMERGE-LEDGER"]
        reconciliation = facts["reconciliation"]
        for field in (
            "confirmed_input_raw",
            "confirmed_included_output_raw",
            "unresolved_residual_raw",
        ):
            if _text(ledger, field) != reconciliation[field]:
                raise ValueError(f"REMERGE evidence {field} differs")
        dust = calls["EV-FLOW-UNRELATED-INFLOW"]
        excluded = facts["excluded_edges"][0]
        if _text(dust, "amount_raw") != excluded["amount_raw"]:
            raise ValueError("REMERGE dust evidence differs")
    else:
        total = calls["EV-FLOW-MULTI-TOTAL"]
        if _text(total, "total_raw") != facts["deduplicated_total_raw"]:
            raise ValueError("MULTI total evidence differs")


def _verify_requirements(
    fixture_id: str,
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    evidence_ids = {
        _text(item, "evidence_id")
        for key in ("event_evidence", "call_evidence", "state_evidence", "context_evidence")
        for item in _object_array(evidence, key)
    }
    requirements = _mapping(expected, "scoring").get("requirements")
    if not isinstance(requirements, list):
        raise ValueError("requirements must be an array")
    found = []
    for item in requirements:
        if not isinstance(item, dict):
            raise ValueError("requirement must be an object")
        found.append(_text(item, "requirement_id"))
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= evidence_ids:
            raise ValueError("requirement evidence references differ")
    if tuple(found) != REQUIREMENTS[fixture_id]:
        raise ValueError("requirement IDs differ")


def _hex_raw(value: dict[str, Any], key: str) -> str:
    return str(int(_text(value, key), 16))


def _object_array(value: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = value.get(key)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must be an object array")
    return items


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"{key} must be an object")
    return item


def _text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{key} must be text")
    return item
