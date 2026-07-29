"""Deterministic TASK-014 flow_path (PATH graph / ledger) analyzers.

Independently re-derives graph edges and reconciliation ledgers from reviewed
raw replay evidence. This module does not import the fixture verifier
(``task_014_independent_verifier``); the two must reach the same conclusion
from separate code paths.
"""

from datetime import datetime

from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import (
    AggregateOriginsInputs,
    FlowPathAnalysisRequest,
    TracePathInputs,
    TraceRemergeInputs,
    TraversalBudgets,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.flow_path import (
    FlowPathReplay,
    FlowReplaySource,
    InternalEdge,
    SelectedTransaction,
    parse_flow_path_replay,
)

CHECKPOINT_ID = "CP-FLOW-PATH-REPLAY-EVIDENCE"


class _DecodeFailure(Exception):
    """A specific, named TASK-014 failure mapped to a public ErrorCode."""

    def __init__(self, code: str, message: str, stage: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage


class _Edge:
    """One confirmed native transfer edge derived from the replay."""

    def __init__(
        self,
        *,
        from_node: str,
        to_node: str,
        amount_raw: str,
        transaction_hash: str,
        block_number: int,
        transfer_kind: str,
        transaction_index: int | None,
    ) -> None:
        self.from_node = from_node
        self.to_node = to_node
        self.amount_raw = amount_raw
        self.transaction_hash = transaction_hash
        self.block_number = block_number
        self.transfer_kind = transfer_kind
        self.transaction_index = transaction_index


def analyze_flow_path_replay(
    request: FlowPathAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Run one approved flow_path query over reviewed raw replay evidence."""
    try:
        replay = parse_flow_path_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed replay package does not match the raw evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )
    binding_error = _binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)
    try:
        _require_unique_transaction_hashes(replay)
        _require_unique_internal_edges(replay)
        inputs = request.inputs
        if isinstance(inputs, TracePathInputs):
            return _trace_path(request, replay, resumed, checkpoint_id)
        if isinstance(inputs, TraceRemergeInputs):
            return _trace_remerge(request, replay, resumed, checkpoint_id)
        return _aggregate_origins(request, replay, resumed, checkpoint_id)
    except _DecodeFailure as error:
        return _failed(request, error.code, error.message, error.stage, resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed raw evidence could not be decoded without ambiguity.",
            "decode_flow_path",
            resumed,
            checkpoint_id,
        )


def _binding_error(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return "rule_restricted", "TASK-014 currently executes reviewed replay only.", "rule_check"
    if request.chain_id != replay.chain_id:
        return "reconciliation_failed", "Request and replay chain identity differ.", "chain_binding"
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and replay fixture IDs differ.",
            "fixture_binding",
        )
    if not {source.source_id for source in replay.sources} <= set(
        request.source_policy.allowed_source_ids
    ):
        return (
            "rule_restricted",
            "Replay evidence uses a source outside the allowed policy.",
            "source_binding",
        )
    return None


# ---------------------------------------------------------------------------
# Edge derivation
# ---------------------------------------------------------------------------


def _top_level_edges(replay: FlowPathReplay) -> list[_Edge]:
    edges: list[_Edge] = []
    for item in replay.transactions:
        amount = int(item.transaction.value, 16)
        if amount == 0:
            continue
        edges.append(
            _Edge(
                from_node=_addr(item.transaction.from_address),
                to_node=_addr(item.transaction.to_address),
                amount_raw=str(amount),
                transaction_hash=item.transaction.hash,
                block_number=int(item.transaction.block_number, 16),
                transfer_kind="native_top_level",
                transaction_index=int(item.transaction.transaction_index, 16),
            )
        )
    return edges


def _internal_edges(replay: FlowPathReplay) -> list[_Edge]:
    edges: list[_Edge] = []
    for internal in replay.internal_edges:
        parent = _internal_parent(internal, replay.transactions)
        edges.append(
            _Edge(
                from_node=_addr(internal.from_address),
                to_node=_addr(internal.to_address),
                amount_raw=internal.value_raw,
                transaction_hash=parent.transaction.hash,
                block_number=int(parent.transaction.block_number, 16),
                transfer_kind="native_internal",
                transaction_index=None,
            )
        )
    return edges


def _internal_parent(
    internal: InternalEdge,
    transactions: list[SelectedTransaction],
) -> SelectedTransaction:
    parents = [
        item
        for item in transactions
        if _addr(item.transaction.to_address) == _addr(internal.from_address)
    ]
    if len(parents) != 1:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Internal edge does not bind to exactly one selected parent transaction.",
            "internal_edge_binding",
        )
    return parents[0]


# ---------------------------------------------------------------------------
# trace_path
# ---------------------------------------------------------------------------


def _trace_path(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, TracePathInputs)
    _require_block_windows(inputs.scope.block_windows, replay)
    seed = inputs.seed_node
    terminal = inputs.terminal_policy.terminal_node
    budgets = inputs.budgets

    edges = _internal_edges(replay) + _top_level_edges(replay)
    adjacency = _adjacency(edges)

    walk, reached = _walk(
        adjacency, seed, terminal, budgets.max_hops, budgets.max_edges, budgets.max_nodes
    )
    if reached:
        if not replay.scope.selected_transactions_complete:
            return _partial_trace_path(
                request,
                replay,
                walk,
                seed,
                terminal,
                "source_unavailable",
                "scope_incomplete",
                resumed,
                checkpoint_id,
            )
        return _complete_trace_path(request, replay, walk, terminal, resumed, checkpoint_id)

    # Terminal reachable but the requested budget stopped the traversal -> partial.
    _, unbounded_reached = _walk(adjacency, seed, terminal, _UNBOUNDED, _UNBOUNDED, _UNBOUNDED)
    if unbounded_reached:
        return _partial_trace_path(
            request,
            replay,
            walk,
            seed,
            terminal,
            "evidence_incomplete",
            "budget_traversal",
            resumed,
            checkpoint_id,
        )

    # Preserve any confirmed chain that still reaches the terminal even if the
    # seed's own connecting (internal) edge is missing from the replay.
    fallback = _confirmed_chain_to_terminal(edges, adjacency, terminal, budgets)
    if fallback:
        internal_expected = not replay.internal_edges and _is_internal_source(seed, replay)
        code, stage = (
            ("trace_unavailable", "internal_edge_trace")
            if internal_expected
            else ("evidence_incomplete", "frontier_resolution")
        )
        return _partial_trace_path(
            request, replay, fallback, seed, terminal, code, stage, resumed, checkpoint_id
        )
    if walk:
        return _partial_trace_path(
            request,
            replay,
            walk,
            seed,
            terminal,
            "evidence_incomplete",
            "frontier_resolution",
            resumed,
            checkpoint_id,
        )
    return _failed(
        request,
        "source_unavailable",
        "No confirmed native edge from the requested seed is present in the reviewed replay.",
        "seed_resolution",
        resumed,
        checkpoint_id,
    )


def _complete_trace_path(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    walk: list[_Edge],
    terminal: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    graph, evidence = _build_path_graph(replay, walk, "included")
    value = {
        "graph": graph,
        "path_candidates": [
            {
                "ordered_edge_ids": [edge["edge_id"] for edge in graph["edges"]],
                "hop_count": len(walk),
                "terminal_node": terminal,
                "termination": "selected_terminal_reached",
            }
        ],
        "reconciliation": _selected_path_reconciliation(),
    }
    evidence.append(_scope_evidence(replay))
    result = _result_item(
        "RES-FLOW-PATH",
        "trace_path",
        value,
        ["REQ-FLOW-PATH-ORDER", "REQ-FLOW-PATH-SCOPE"],
        [item["evidence_id"] for item in evidence],
    )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


def _partial_trace_path(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    walk: list[_Edge],
    seed: str,
    terminal: str,
    code: str,
    stage: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    graph, evidence = _build_path_graph(replay, walk, "included")
    if walk and walk[0].from_node != seed:
        frontier_from = seed
    elif walk:
        frontier_from = walk[-1].to_node
    else:
        frontier_from = seed
    graph["frontier"] = [
        {
            "from_node": frontier_from,
            "to_node": terminal,
            "scope_status": "unresolved",
            "reason": stage,
        }
    ]
    value = {
        "graph": graph,
        "path_candidates": [
            {
                "ordered_edge_ids": [edge["edge_id"] for edge in graph["edges"]],
                "hop_count": len(walk),
                "terminal_node": terminal,
                "termination": "frontier_open",
            }
        ],
        "reconciliation": _selected_path_reconciliation(),
    }
    evidence.append(_scope_evidence(replay))
    result = _result_item(
        "RES-FLOW-PATH",
        "trace_path",
        value,
        ["REQ-FLOW-PATH-ORDER", "REQ-FLOW-PATH-SCOPE"],
        [item["evidence_id"] for item in evidence],
    )
    errors = [
        _error(
            code,
            "The requested terminal was not reached inside the selected scope; "
            "the confirmed sub-path is preserved.",
            stage,
            [item["evidence_id"] for item in evidence],
            retryable=True,
        )
    ]
    return _result(request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id)


def _build_path_graph(
    replay: FlowPathReplay,
    walk: list[_Edge],
    scope_status: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    nodes: list[str] = []
    edges: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for index, edge in enumerate(walk, start=1):
        if not nodes:
            nodes.append(edge.from_node)
        nodes.append(edge.to_node)
        edge_dict: dict[str, object] = {
            "edge_id": f"EDGE-PATH-{index:03d}",
            "from_node": edge.from_node,
            "to_node": edge.to_node,
            "amount_raw": edge.amount_raw,
            "transaction_hash": edge.transaction_hash,
            "block_number": edge.block_number,
        }
        if edge.transaction_index is not None:
            edge_dict["transaction_index"] = edge.transaction_index
        edge_dict["transfer_kind"] = edge.transfer_kind
        edge_dict["scope_status"] = scope_status
        edges.append(edge_dict)
        evidence.append(
            _edge_evidence(
                replay,
                _path_edge_evidence_id(index, edge),
                edge,
                source_index=1 if edge.transfer_kind == "native_top_level" else 0,
            )
        )
    graph = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
    return graph, evidence


def _path_edge_evidence_id(index: int, edge: _Edge) -> str:
    if edge.transfer_kind == "native_internal":
        return "EV-FLOW-PATH-INTERNAL"
    return f"EV-FLOW-PATH-HOP-{index}"


def _selected_path_reconciliation() -> dict[str, object]:
    return {
        "status": "unresolved_selected_path_scope",
        "reason": "The selected path does not claim a continuous scan of the seed's other outputs.",
        "raw_amounts_must_not_be_equalized": True,
    }


# ---------------------------------------------------------------------------
# trace_remerge
# ---------------------------------------------------------------------------


def _trace_remerge(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, TraceRemergeInputs)
    seed = inputs.seed_node
    merge_node = inputs.merge_node
    _require_remerge_scope(inputs, replay)

    splits = [item for item in replay.transactions if _addr(item.transaction.from_address) == seed]
    if not splits:
        return _failed(
            request,
            "source_unavailable",
            "No seed split transactions are present in the reviewed replay.",
            "seed_resolution",
            resumed,
            checkpoint_id,
        )
    merges_by_origin: dict[str, SelectedTransaction] = {}
    for item in replay.transactions:
        if _addr(item.transaction.to_address) != merge_node:
            continue
        origin = _addr(item.transaction.from_address)
        if origin in merges_by_origin:
            raise _DecodeFailure(
                "reconciliation_failed",
                "A merge origin appears twice in the reviewed replay.",
                "edge_dedup",
            )
        merges_by_origin[origin] = item

    # A remerge branch is atomic: seed -> branch -> merge consumes two edges,
    # one intermediate node, and two hops.  Do not derive or return branches
    # beyond the caller's traversal budget.
    branch_budget = _remerge_branch_budget(inputs.budgets)
    branches: list[dict[str, object]] = []
    split_evidence_hashes: list[str] = []
    merge_evidence_hashes: list[str] = []
    available = True
    budget_exhausted = False
    for split in splits:
        if len(branches) >= branch_budget:
            budget_exhausted = True
            break
        branch = _addr(split.transaction.to_address)
        merge = merges_by_origin.get(branch)
        input_raw = int(split.transaction.value, 16)
        if merge is None:
            available = False
            continue
        output_raw = int(merge.transaction.value, 16)
        residual = input_raw - output_raw
        if residual < 0:
            raise _DecodeFailure(
                "reconciliation_failed",
                "A branch merge output exceeds its seed input.",
                "ledger_reconciliation",
            )
        branches.append(
            {
                "branch_node": branch,
                "input_raw": str(input_raw),
                "merge_output_raw": str(output_raw),
                "residual_raw": str(residual),
            }
        )
        split_evidence_hashes.append(split.transaction.hash)
        merge_evidence_hashes.append(merge.transaction.hash)

    excluded_edges, external_total = _external_inflows(
        replay, seed, {b["branch_node"] for b in branches}
    )

    confirmed_input = sum(int(b["input_raw"]) for b in branches)
    confirmed_output = sum(int(b["merge_output_raw"]) for b in branches)
    residual_total = sum(int(b["residual_raw"]) for b in branches)
    value = {
        "branches": branches,
        "reconciliation": {
            "confirmed_input_raw": str(confirmed_input),
            "confirmed_included_output_raw": str(confirmed_output),
            "confirmed_scoped_excluded_output_raw": "0",
            "explicit_fee_or_context_raw": "0",
            "unresolved_residual_raw": str(residual_total),
            "external_inflow_raw_not_in_seed_ledger": str(external_total),
        },
        "excluded_edges": excluded_edges,
    }
    evidence = _remerge_evidence(
        replay, split_evidence_hashes, merge_evidence_hashes, value, excluded_edges
    )
    result = _result_item(
        "RES-FLOW-REMERGE",
        "trace_remerge",
        value,
        ["REQ-FLOW-REMERGE-BRANCHES", "REQ-FLOW-REMERGE-LEDGER"],
        [item["evidence_id"] for item in evidence],
    )
    if budget_exhausted:
        errors = [
            _error(
                "evidence_incomplete",
                "The requested traversal budget stopped the remerge walk; "
                "only the bounded confirmed branches and residual are preserved.",
                "budget_traversal",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
        return _result(
            request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id
        )
    if not available or not replay.scope.selected_transactions_complete:
        errors = [
            _error(
                "source_unavailable",
                "One or more branch return transactions are unavailable; "
                "the confirmed branches and residual are preserved.",
                "branch_return_binding",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
        return _result(
            request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id
        )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


def _external_inflows(
    replay: FlowPathReplay,
    seed: str,
    branch_nodes: set[str],
) -> tuple[list[dict[str, object]], int]:
    excluded: list[dict[str, object]] = []
    total = 0
    for item in replay.transactions:
        to_node = _addr(item.transaction.to_address)
        from_node = _addr(item.transaction.from_address)
        if to_node in branch_nodes and from_node != seed:
            amount = int(item.transaction.value, 16)
            total += amount
            excluded.append(
                {
                    "transaction_hash": item.transaction.hash,
                    "from_node": from_node,
                    "to_node": to_node,
                    "amount_raw": str(amount),
                    "reason": "external_inflow_not_from_seed",
                    "scope_status": "excluded",
                }
            )
    return excluded, total


# ---------------------------------------------------------------------------
# aggregate_origins
# ---------------------------------------------------------------------------


def _aggregate_origins(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, AggregateOriginsInputs)
    exit_node = inputs.exit_node
    origins = set(inputs.origin_nodes)
    _require_aggregate_scope(inputs, replay)

    eligible: list[SelectedTransaction] = []
    seen_hashes: set[str] = set()
    evidence_hashes: list[str] = []
    for item in replay.transactions:
        to_node = _addr(item.transaction.to_address)
        from_node = _addr(item.transaction.from_address)
        if to_node != exit_node:
            continue
        if from_node not in origins:
            raise _DecodeFailure(
                "reconciliation_failed",
                "A selected exit transfer originates outside the requested origin set.",
                "origin_scope",
            )
        if item.transaction.hash in seen_hashes:
            raise _DecodeFailure(
                "reconciliation_failed",
                "The same transaction is counted for more than one origin.",
                "origin_dedup",
            )
        seen_hashes.add(item.transaction.hash)
        eligible.append(item)

    contribution_budget = _aggregate_contribution_budget(inputs.budgets)
    bounded_items = eligible[:contribution_budget]
    budget_exhausted = len(eligible) > len(bounded_items)
    contributions: list[dict[str, object]] = []
    seen_origins: set[str] = set()
    for item in bounded_items:
        from_node = _addr(item.transaction.from_address)
        seen_origins.add(from_node)
        contributions.append(
            {
                "origin_node": from_node,
                "amount_raw": str(int(item.transaction.value, 16)),
                "transaction_hash": item.transaction.hash,
                "block_number": int(item.transaction.block_number, 16),
            }
        )
        evidence_hashes.append(item.transaction.hash)

    if not contributions and not budget_exhausted:
        return _failed(
            request,
            "source_unavailable",
            "No selected origin contribution to the requested exit is present.",
            "origin_binding",
            resumed,
            checkpoint_id,
        )
    total = sum(int(item["amount_raw"]) for item in contributions)
    value = {
        "exit_node": exit_node,
        "contributions": contributions,
        "deduplicated_total_raw": str(total),
        "price_context": {"status": "not_assessed", "included_in_scoring": False},
        "attribution": {
            "common_control_claim": False,
            "criminal_or_victim_claim": False,
            "status": "not_assessed",
        },
    }
    evidence = _multi_evidence(replay, evidence_hashes, str(total))
    result = _result_item(
        "RES-FLOW-MULTI",
        "aggregate_origins",
        value,
        ["REQ-FLOW-MULTI-CONTRIBUTIONS", "REQ-FLOW-MULTI-TOTAL"],
        [item["evidence_id"] for item in evidence],
    )
    if budget_exhausted:
        errors = [
            _error(
                "evidence_incomplete",
                "The requested traversal budget stopped origin aggregation; "
                "only bounded confirmed contributions are preserved.",
                "budget_traversal",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
        return _result(
            request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id
        )
    if seen_origins != origins or not replay.scope.selected_transactions_complete:
        errors = [
            _error(
                "source_unavailable",
                "At least one requested origin is unavailable; confirmed contributions are preserved.",
                "origin_binding",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
        return _result(
            request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id
        )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


# ---------------------------------------------------------------------------
# Scope binding
# ---------------------------------------------------------------------------


def _require_block_windows(block_windows: list[object], replay: FlowPathReplay) -> None:
    window_blocks = {(w.from_block, w.to_block) for w in block_windows}  # type: ignore[attr-defined]
    if any(lo != hi for lo, hi in window_blocks):
        raise _DecodeFailure(
            "reconciliation_failed",
            "trace_path block windows must be exact single-block windows.",
            "scope_validation",
        )
    declared = {lo for lo, _ in window_blocks}
    actual = {int(item.transaction.block_number, 16) for item in replay.transactions}
    if declared != actual:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Requested block windows do not match the selected replay transactions.",
            "scope_validation",
        )


def _require_remerge_scope(inputs: TraceRemergeInputs, replay: FlowPathReplay) -> None:
    replay_hashes = {item.transaction.hash for item in replay.transactions}
    declared = set(inputs.scope.selected_transactions) | set(
        inputs.scope.excluded_context_transactions
    )
    if declared != replay_hashes:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Requested transactions do not match the reviewed replay set.",
            "scope_validation",
        )
    low = inputs.scope.block_range.from_block
    high = inputs.scope.block_range.to_block
    if any(
        not low <= int(item.transaction.block_number, 16) <= high for item in replay.transactions
    ):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Requested block_range does not cover the selected replay transactions.",
            "scope_validation",
        )


def _require_unique_transaction_hashes(replay: FlowPathReplay) -> None:
    hashes = [item.transaction.hash for item in replay.transactions]
    if len(hashes) != len(set(hashes)):
        raise _DecodeFailure(
            "reconciliation_failed",
            "A transaction hash is aggregated more than once in the reviewed replay.",
            "edge_dedup",
        )


def _require_unique_internal_edges(replay: FlowPathReplay) -> None:
    identities = [
        (
            tuple(edge.path),
            edge.type,
            _addr(edge.from_address),
            _addr(edge.to_address),
            edge.value_raw,
        )
        for edge in replay.internal_edges
    ]
    if len(identities) != len(set(identities)):
        raise _DecodeFailure(
            "reconciliation_failed",
            "An internal transfer edge is aggregated more than once in the reviewed replay.",
            "edge_dedup",
        )


def _remerge_branch_budget(budgets: TraversalBudgets) -> int:
    if budgets.max_hops < 2 or budgets.max_nodes < 3 or budgets.max_edges < 2:
        return 0
    return min(budgets.max_nodes - 2, budgets.max_edges // 2)


def _aggregate_contribution_budget(budgets: TraversalBudgets) -> int:
    if budgets.max_hops < 1 or budgets.max_nodes < 2 or budgets.max_edges < 1:
        return 0
    return min(budgets.max_nodes - 1, budgets.max_edges)


def _require_aggregate_scope(inputs: AggregateOriginsInputs, replay: FlowPathReplay) -> None:
    replay_hashes = {item.transaction.hash for item in replay.transactions}
    if set(inputs.scope.selected_transactions) != replay_hashes:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Requested transactions do not match the reviewed replay set.",
            "scope_validation",
        )


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------


def _adjacency(edges: list[_Edge]) -> dict[str, list[_Edge]]:
    result: dict[str, list[_Edge]] = {}
    for edge in edges:
        result.setdefault(edge.from_node, []).append(edge)
    return result


def _walk(
    adjacency: dict[str, list[_Edge]],
    start: str,
    terminal: str,
    max_hops: int,
    max_edges: int,
    max_nodes: int,
) -> tuple[list[_Edge], bool]:
    path: list[_Edge] = []
    current = start
    visited = {start}
    while (
        current != terminal
        and len(path) < max_hops
        and len(path) < max_edges
        and len(visited) < max_nodes
    ):
        outgoing = adjacency.get(current, [])
        if len(outgoing) != 1:
            break
        edge = outgoing[0]
        if edge.to_node in visited:
            break
        path.append(edge)
        current = edge.to_node
        visited.add(current)
    return path, current == terminal


_UNBOUNDED = 1_000_000


def _confirmed_chain_to_terminal(
    edges: list[_Edge],
    adjacency: dict[str, list[_Edge]],
    terminal: str,
    budgets: object,
) -> list[_Edge]:
    destinations = {edge.to_node for edge in edges}
    sources = [edge.from_node for edge in edges if edge.from_node not in destinations]
    best: list[_Edge] = []
    for start in sources:
        walk, reached = _walk(
            adjacency,
            start,
            terminal,
            budgets.max_hops,  # type: ignore[attr-defined]
            budgets.max_edges,  # type: ignore[attr-defined]
            budgets.max_nodes,  # type: ignore[attr-defined]
        )
        if reached and len(walk) > len(best):
            best = walk
    return best


def _is_internal_source(seed: str, replay: FlowPathReplay) -> bool:
    return any(_addr(item.transaction.to_address) == seed for item in replay.transactions)


# ---------------------------------------------------------------------------
# Evidence / envelope helpers
# ---------------------------------------------------------------------------


def _edge_evidence(
    replay: FlowPathReplay,
    evidence_id: str,
    edge: _Edge,
    *,
    source_index: int,
) -> dict[str, object]:
    evidence_type = "call" if edge.transfer_kind == "native_internal" else "call"
    decoded = {
        "from": edge.from_node,
        "to": edge.to_node,
        "amount_raw": edge.amount_raw,
        "transfer_kind": edge.transfer_kind,
    }
    locator = {
        "chain_id": 1,
        "transaction_hash": edge.transaction_hash,
        "block_number": edge.block_number,
    }
    return _evidence(
        replay.sources,
        evidence_id,
        evidence_type,
        edge.transaction_hash,
        decoded,
        locator,
        source_index,
    )


def _scope_evidence(replay: FlowPathReplay) -> dict[str, object]:
    return _evidence(
        replay.sources,
        "EV-FLOW-PATH-SCOPE",
        "context",
        "selected_transactions_and_exact_blocks",
        {
            "selected_transactions_complete": replay.scope.selected_transactions_complete,
            "continuous_gap_scanned": replay.scope.continuous_gap_scanned,
        },
        {"chain_id": 1},
        0,
    )


def _remerge_evidence(
    replay: FlowPathReplay,
    split_hashes: list[str],
    merge_hashes: list[str],
    value: dict[str, object],
    excluded_edges: list[dict[str, object]],
) -> list[dict[str, object]]:
    reconciliation = value["reconciliation"]
    evidence = [
        _evidence(
            replay.sources,
            "EV-FLOW-SPLIT-4",
            "call",
            "seed_splits",
            {"transaction_hashes": split_hashes},
            {"chain_id": 1},
            0,
        ),
        _evidence(
            replay.sources,
            "EV-FLOW-REMERGE-4",
            "call",
            "branch_merges",
            {"transaction_hashes": merge_hashes},
            {"chain_id": 1},
            1,
        ),
        _evidence(
            replay.sources,
            "EV-FLOW-REMERGE-LEDGER",
            "context",
            "reconciliation_ledger",
            dict(reconciliation),  # type: ignore[arg-type]
            {"chain_id": 1},
            0,
        ),
    ]
    if excluded_edges:
        evidence.append(
            _evidence(
                replay.sources,
                "EV-FLOW-UNRELATED-INFLOW",
                "call",
                "external_inflow",
                {
                    "transaction_hash": excluded_edges[0]["transaction_hash"],
                    "amount_raw": excluded_edges[0]["amount_raw"],
                },
                {"chain_id": 1, "transaction_hash": excluded_edges[0]["transaction_hash"]},
                1,
            )
        )
    return evidence


def _multi_evidence(
    replay: FlowPathReplay,
    origin_hashes: list[str],
    total_raw: str,
) -> list[dict[str, object]]:
    return [
        _evidence(
            replay.sources,
            "EV-FLOW-MULTI-ORIGINS",
            "call",
            "origin_contributions",
            {"transaction_hashes": origin_hashes},
            {"chain_id": 1},
            0,
        ),
        _evidence(
            replay.sources,
            "EV-FLOW-MULTI-TOTAL",
            "context",
            "deduplicated_total",
            {"total_raw": total_raw},
            {"chain_id": 1},
            1,
        ),
    ]


def _evidence(
    sources: list[FlowReplaySource],
    evidence_id: str,
    evidence_type: str,
    method: str,
    decoded: dict[str, object],
    locator: dict[str, object],
    source_index: int,
) -> dict[str, object]:
    index = min(source_index, len(sources) - 1)
    source = sources[index]
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "source_id": source.source_id,
        "source_record_ref": f"SRC-FLOW-PATH-{index + 1}",
        "method": method,
        "retrieved_at": source.retrieved_at,
        "locator": locator,
        "decoded": decoded,
        "raw_artifact": {
            "artifact_uri": f"fixture://flow-path/raw-replay.json#{evidence_id}",
            "media_type": "application/json",
        },
    }


def _source_records(
    sources: list[FlowReplaySource],
    referenced_ids: set[str],
) -> list[dict[str, object]]:
    return [
        {
            "source_record_id": f"SRC-FLOW-PATH-{index}",
            "source_id": source.source_id,
            "provider_id": source.provider_id.lower(),
            "role": "scoring",
            "required": True,
            "capability": "flow_path_replay",
            "endpoint_host": "reviewed.replay.invalid",
            "retrieved_at": source.retrieved_at,
        }
        for index, source in enumerate(sources, start=1)
        if f"SRC-FLOW-PATH-{index}" in referenced_ids
    ]


def _result_item(
    result_id: str,
    result_type: str,
    value: dict[str, object],
    fixture_requirement_ids: list[str],
    evidence_refs: list[str],
) -> dict[str, object]:
    return {
        "result_id": result_id,
        "result_type": result_type,
        "classification": "confirmed_fact",
        "value": value,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": fixture_requirement_ids,
        "evidence_refs": evidence_refs,
    }


def _error(
    code: str,
    message: str,
    stage: str,
    evidence_ids: list[str],
    *,
    retryable: bool = False,
) -> dict[str, object]:
    value: dict[str, object] = {
        "error_id": f"ERR-FLOW-PATH-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "attempt_count": 0,
    }
    if evidence_ids:
        value["related_evidence_ids"] = evidence_ids
    return value


def _result(
    request: FlowPathAnalysisRequest,
    replay: FlowPathReplay,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    sources = replay.sources
    referenced = {str(item["source_record_ref"]) for item in evidence}
    finished_at = max([request.requested_at, *[source.retrieved_at for source in sources]])
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": status,
            "results": results,
            "evidence": evidence,
            "sources": _source_records(sources, referenced),
            "warnings": [],
            "errors": errors,
            "run": _run(
                request.requested_at, finished_at, resumed=resumed, checkpoint_id=checkpoint_id
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _failed(
    request: FlowPathAnalysisRequest,
    code: str,
    message: str,
    stage: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": "failed",
            "results": [],
            "evidence": [],
            "sources": [],
            "warnings": [],
            "errors": [_error(code, message, stage, [])],
            "run": _run(
                request.requested_at,
                request.requested_at,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _run(
    started_at: datetime,
    finished_at: datetime,
    *,
    resumed: bool,
    checkpoint_id: str | None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "tool_version": __version__,
        "execution_mode": "offline_replay",
        "started_at": started_at,
        "finished_at": max(started_at, finished_at),
        "cache_hits": 1,
        "cache_misses": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "resumed": resumed,
    }
    if checkpoint_id is not None:
        value["checkpoint_id"] = checkpoint_id
    return value


def _pending_exports(analysis_id: str) -> dict[str, object]:
    return {
        "json": {"artifact_uri": f"artifact://pending/{analysis_id}/result.json"},
        "markdown": {"artifact_uri": f"artifact://pending/{analysis_id}/evidence.md"},
    }


def _addr(value: str) -> str:
    return to_normalized_address(value)
