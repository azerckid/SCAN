#!/usr/bin/env python3
"""Contest-day FLOW final-account candidate helper (offline MVP).

Implements docs/05_QA_Validation/76_FLOW_FINAL_ACCOUNT_CANDIDATE_METHOD.md:

1. Discover seed-reachable edges from a discovery edge set
2. Score candidates by residual (related_in - related_out) ≈ S + terminus
3. Independently verify seed→candidate connectivity on a *separate* edge set
4. Always emit verification_level=heuristic_candidates (|C|==1 included)

Does not modify production flow_path analyzers or Benchmark fixtures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scan_tool.application.security import SensitiveDataGuard  # noqa: E402

CollectionMethod = Literal["indexed_transfers", "trace_subtree", "block_window_scan"]
COLLECTION_METHODS: tuple[str, ...] = (
    "indexed_transfers",
    "trace_subtree",
    "block_window_scan",
)


@dataclass(frozen=True)
class Edge:
    tx_hash: str
    from_addr: str
    to_addr: str
    value_raw: int
    asset: str


@dataclass(frozen=True)
class RunConfig:
    seed: str
    chain_id: int
    asset_scope: str
    amount_raw: int
    tolerance_raw: int
    tolerance_cap_raw: int
    tolerance_rationale: str
    collection_method: CollectionMethod
    max_hops: int
    max_nodes: int
    max_edges: int


def _lower(value: object) -> str:
    return str(value).lower()


def _parse_int(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer, not bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text.startswith("0x"):
            return int(text, 16)
        return int(text, 10)
    raise ValueError(f"{field} must be an int or numeric string")


def load_edges(path: Path, *, asset_scope: str) -> list[Edge]:
    """Load a JSON edge list. Accepts {\"edges\": [...]} or a bare list."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_edges = payload.get("edges")
        if not isinstance(raw_edges, list):
            raise ValueError(f"{path}: expected object with edges array")
    elif isinstance(payload, list):
        raw_edges = payload
    else:
        raise ValueError(f"{path}: edge file must be object or array")

    edges: list[Edge] = []
    for index, item in enumerate(raw_edges):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: edges[{index}] must be an object")
        asset = _lower(item.get("asset", "native"))
        if asset != _lower(asset_scope):
            continue
        tx_hash = _lower(item.get("tx_hash") or item.get("hash") or "")
        from_addr = _lower(item.get("from") or item.get("from_addr") or "")
        to_addr = _lower(item.get("to") or item.get("to_addr") or "")
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            raise ValueError(f"{path}: edges[{index}] tx_hash is invalid")
        if not from_addr.startswith("0x") or len(from_addr) != 42:
            raise ValueError(f"{path}: edges[{index}] from is invalid")
        if not to_addr.startswith("0x") or len(to_addr) != 42:
            raise ValueError(f"{path}: edges[{index}] to is invalid")
        value_raw = _parse_int(
            item.get("value_raw", item.get("value")),
            field=f"{path}:edges[{index}].value",
        )
        if value_raw < 0:
            raise ValueError(f"{path}: edges[{index}] value_raw must be >= 0")
        edges.append(
            Edge(
                tx_hash=tx_hash,
                from_addr=from_addr,
                to_addr=to_addr,
                value_raw=value_raw,
                asset=asset,
            )
        )
    return edges


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_related_edges(
    edges: list[Edge],
    *,
    seed: str,
    max_hops: int,
    max_nodes: int,
    max_edges: int,
) -> tuple[list[Edge], dict[str, Any]]:
    """BFS outbound from seed; return related edges and budget metadata."""
    seed = _lower(seed)
    outbound: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outbound[edge.from_addr].append(edge)

    related: list[Edge] = []
    seen_edge_keys: set[tuple[str, str, str, int]] = set()
    visited_nodes = {seed}
    # queue items: (node, hops_from_seed)
    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    budget_exhausted = False

    while queue:
        node, hops = queue.popleft()
        if hops >= max_hops:
            if outbound.get(node):
                budget_exhausted = True
            continue
        for edge in outbound.get(node, []):
            key = (edge.tx_hash, edge.from_addr, edge.to_addr, edge.value_raw)
            if key in seen_edge_keys:
                continue
            if len(related) >= max_edges:
                budget_exhausted = True
                break
            seen_edge_keys.add(key)
            related.append(edge)
            if edge.to_addr not in visited_nodes:
                if len(visited_nodes) >= max_nodes:
                    budget_exhausted = True
                    continue
                visited_nodes.add(edge.to_addr)
                queue.append((edge.to_addr, hops + 1))
        if budget_exhausted and len(related) >= max_edges:
            break

    meta = {
        "related_edge_count": len(related),
        "visited_node_count": len(visited_nodes),
        "budget_exhausted": budget_exhausted,
        "max_hops": max_hops,
        "max_nodes": max_nodes,
        "max_edges": max_edges,
    }
    return related, meta


def aggregate_residuals(related: list[Edge]) -> dict[str, dict[str, int]]:
    """Per-address related_in / related_out / residual."""
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"related_in_raw": 0, "related_out_raw": 0}
    )
    for edge in related:
        totals[edge.to_addr]["related_in_raw"] += edge.value_raw
        totals[edge.from_addr]["related_out_raw"] += edge.value_raw
    result: dict[str, dict[str, int]] = {}
    for address, values in totals.items():
        result[address] = {
            "related_in_raw": values["related_in_raw"],
            "related_out_raw": values["related_out_raw"],
            "residual_raw": values["related_in_raw"] - values["related_out_raw"],
        }
    return result


def path_exists(
    edges: list[Edge],
    *,
    seed: str,
    target: str,
    max_hops: int,
) -> tuple[bool, list[str]]:
    """Return whether seed can reach target on edges; include one tx path."""
    seed = _lower(seed)
    target = _lower(target)
    if seed == target:
        return False, []
    outbound: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outbound[edge.from_addr].append(edge)

    # BFS storing predecessor edge
    prev: dict[str, Edge | None] = {seed: None}
    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    while queue:
        node, hops = queue.popleft()
        if node == target:
            break
        if hops >= max_hops:
            continue
        for edge in outbound.get(node, []):
            if edge.to_addr in prev:
                continue
            prev[edge.to_addr] = edge
            queue.append((edge.to_addr, hops + 1))

    if target not in prev:
        return False, []
    path_txs: list[str] = []
    cursor = target
    while cursor != seed:
        edge = prev[cursor]
        if edge is None:
            return False, []
        path_txs.append(edge.tx_hash)
        cursor = edge.from_addr
    path_txs.reverse()
    return True, path_txs


def select_candidates(
    residuals: dict[str, dict[str, int]],
    *,
    seed: str,
    amount_raw: int,
    tolerance_raw: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply residual≈S and terminus (no related outflow)."""
    seed = _lower(seed)
    draft: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for address, values in residuals.items():
        if address == seed:
            continue
        residual = values["residual_raw"]
        related_out = values["related_out_raw"]
        related_in = values["related_in_raw"]
        # Intermediate passthrough: received then forwarded (~0 residual)
        if abs(residual - amount_raw) > tolerance_raw:
            if related_in > 0 and related_out > 0 and abs(residual) <= tolerance_raw:
                excluded.append(
                    {
                        "address": address,
                        "reason": "intermediate_passthrough_residual_near_zero",
                        "related_in_raw": str(related_in),
                        "related_out_raw": str(related_out),
                        "residual_raw": str(residual),
                    }
                )
            elif related_in > 0 and abs(related_in - amount_raw) <= tolerance_raw:
                excluded.append(
                    {
                        "address": address,
                        "reason": "gross_inflow_near_s_but_residual_not",
                        "related_in_raw": str(related_in),
                        "related_out_raw": str(related_out),
                        "residual_raw": str(residual),
                    }
                )
            continue
        if related_out != 0:
            excluded.append(
                {
                    "address": address,
                    "reason": "residual_near_s_but_has_related_outflow",
                    "related_in_raw": str(related_in),
                    "related_out_raw": str(related_out),
                    "residual_raw": str(residual),
                }
            )
            continue
        draft.append(
            {
                "address": address,
                "related_in_raw": str(related_in),
                "related_out_raw": str(related_out),
                "residual_raw": str(residual),
                "terminus_kind": "no_further_related_outflow",
            }
        )
    draft.sort(key=lambda item: item["address"])
    return draft, excluded


def run_analysis(
    config: RunConfig,
    *,
    discovery_edges: list[Edge],
    independent_edges: list[Edge],
    discovery_sha256: str,
    independent_sha256: str,
) -> dict[str, Any]:
    if config.tolerance_raw > config.tolerance_cap_raw:
        raise ValueError("tolerance_raw exceeds tolerance_cap_raw")
    if config.tolerance_raw < 0 or config.tolerance_cap_raw < 0:
        raise ValueError("tolerance values must be >= 0")
    if config.amount_raw < 0:
        raise ValueError("amount_raw must be >= 0")

    related, budget_meta = discover_related_edges(
        discovery_edges,
        seed=config.seed,
        max_hops=config.max_hops,
        max_nodes=config.max_nodes,
        max_edges=config.max_edges,
    )
    residuals = aggregate_residuals(related)
    draft, excluded = select_candidates(
        residuals,
        seed=config.seed,
        amount_raw=config.amount_raw,
        tolerance_raw=config.tolerance_raw,
    )

    identical_graphs = discovery_sha256 == independent_sha256
    candidates: list[dict[str, Any]] = []
    for item in draft:
        address = item["address"]
        if identical_graphs:
            excluded.append(
                {
                    "address": address,
                    "reason": "independent_edges_identical_to_discovery",
                }
            )
            continue
        ok, path_txs = path_exists(
            independent_edges,
            seed=config.seed,
            target=address,
            max_hops=config.max_hops,
        )
        if not ok:
            excluded.append(
                {
                    "address": address,
                    "reason": "independent_path_not_found",
                }
            )
            continue
        candidates.append(
            {
                **item,
                "independent_verification": "independent_edge_set",
                "path_tx_hashes": path_txs,
                "forward_hops": len(path_txs),
            }
        )

    scope_complete = not budget_meta["budget_exhausted"]
    report: dict[str, Any] = {
        "verification_level": "heuristic_candidates",
        "seed": _lower(config.seed),
        "chain_id": config.chain_id,
        "asset_scope": _lower(config.asset_scope),
        "amount_target_raw": str(config.amount_raw),
        "tolerance_raw": str(config.tolerance_raw),
        "tolerance_cap_raw": str(config.tolerance_cap_raw),
        "tolerance_rationale": config.tolerance_rationale,
        "collection_method": config.collection_method,
        "scope_complete": scope_complete,
        "pagination_truncated": False,
        "budget_exhausted": budget_meta["budget_exhausted"],
        "budget": budget_meta,
        "discovery_edges_sha256": discovery_sha256,
        "independent_edges_sha256": independent_sha256,
        "candidates": candidates,
        "excluded": excluded,
        "attribution": {
            "ownership": "not_assessed",
            "criminality": "not_assessed",
        },
        "honesty": {
            "may_submit_as_confirmed": False,
            "single_candidate_is_not_confirmed": True,
            "note": (
                "Candidates are heuristic only. |C|==1 does not promote to "
                "confirmed without continuous scope completeness proven elsewhere."
            ),
        },
    }
    # Defense: refuse local path / accidental secret material in JSON output.
    SensitiveDataGuard().check_text(json.dumps(report, ensure_ascii=True))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline FLOW final-account candidate helper "
            "(residual + terminus + independent edge verification)."
        )
    )
    parser.add_argument("--seed", required=True)
    parser.add_argument("--chain-id", type=int, required=True)
    parser.add_argument("--asset-scope", default="native")
    parser.add_argument("--amount-raw", required=True, help="Target amount S as integer/hex")
    parser.add_argument("--tolerance-raw", required=True)
    parser.add_argument("--tolerance-cap-raw", required=True)
    parser.add_argument("--tolerance-rationale", required=True)
    parser.add_argument(
        "--collection-method",
        required=True,
        choices=COLLECTION_METHODS,
    )
    parser.add_argument("--discovery-edges", type=Path, required=True)
    parser.add_argument(
        "--independent-edges",
        type=Path,
        required=True,
        help="Separate edge set for seed→candidate path verification",
    )
    parser.add_argument("--max-hops", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=64)
    parser.add_argument("--max-edges", type=int, default=128)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = RunConfig(
        seed=_lower(args.seed),
        chain_id=args.chain_id,
        asset_scope=_lower(args.asset_scope),
        amount_raw=_parse_int(args.amount_raw, field="amount_raw"),
        tolerance_raw=_parse_int(args.tolerance_raw, field="tolerance_raw"),
        tolerance_cap_raw=_parse_int(args.tolerance_cap_raw, field="tolerance_cap_raw"),
        tolerance_rationale=args.tolerance_rationale,
        collection_method=args.collection_method,
        max_hops=args.max_hops,
        max_nodes=args.max_nodes,
        max_edges=args.max_edges,
    )
    discovery_path = args.discovery_edges.resolve()
    independent_path = args.independent_edges.resolve()
    discovery_edges = load_edges(discovery_path, asset_scope=config.asset_scope)
    independent_edges = load_edges(independent_path, asset_scope=config.asset_scope)
    report = run_analysis(
        config,
        discovery_edges=discovery_edges,
        independent_edges=independent_edges,
        discovery_sha256=file_sha256(discovery_path),
        independent_sha256=file_sha256(independent_path),
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if report.get("verification_level") != "heuristic_candidates":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
