"""Tests for contest FLOW final-account candidate helper (method doc 76)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/contest/flow_final_candidates.py"
SPEC = importlib.util.spec_from_file_location("flow_final_candidates", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

SEED = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
C = "0xcccccccccccccccccccccccccccccccccccccccc"
D = "0xdddddddddddddddddddddddddddddddddddddddd"
E = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"  # unrelated address, no seed link
S = 1_000_000_000_000_000_000  # 1 ETH in wei


def _edge(tx: str, frm: str, to: str, value: int, **kwargs: object) -> mod.Edge:
    return mod.Edge(
        tx_hash=tx, from_addr=frm, to_addr=to, value_raw=value, asset="native", **kwargs
    )


def _chain_edges() -> list[mod.Edge]:
    # A -> B -> C -> D, each hop moves S (passthrough residuals ~0, D residual S)
    return [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, C, S),
        _edge("0x" + "33" * 32, C, D, S),
    ]


def _config(**overrides: object) -> mod.RunConfig:
    base = dict(
        seed=SEED,
        chain_id=1,
        asset_scope="native",
        amount_raw=S,
        tolerance_raw=0,
        tolerance_cap_raw=10**15,
        tolerance_rationale="exact native transfer in synthetic fixture",
        collection_method="block_window_scan",
        independent_collection_method="indexed_transfers",
        max_hops=8,
        max_nodes=64,
        max_edges=128,
    )
    base.update(overrides)
    return mod.RunConfig(**base)  # type: ignore[arg-type]


def _run(config: mod.RunConfig, *, discovery, independent, **hashes):
    hashes.setdefault("discovery_file_sha256", "d" * 64)
    hashes.setdefault("independent_file_sha256", "i" * 64)
    return mod.run_analysis(
        config, discovery_edges=discovery, independent_edges=independent, **hashes
    )


def _write(tmp_path: Path, name: str, edges: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"edges": edges}), encoding="utf-8")
    return path


def test_residual_filters_intermediates_keeps_terminus() -> None:
    related, _meta = mod.discover_related_edges(
        _chain_edges(), seed=SEED, max_hops=8, max_nodes=64, max_edges=128
    )
    residuals = mod.aggregate_residuals(related)
    assert residuals[B]["residual_raw"] == 0
    assert residuals[C]["residual_raw"] == 0
    assert residuals[D]["residual_raw"] == S
    draft, excluded = mod.select_candidates(residuals, seed=SEED, amount_raw=S, tolerance_raw=0)
    assert [item["address"] for item in draft] == [D]
    reasons = {item["address"]: item["reason"] for item in excluded}
    assert reasons[B] == "intermediate_passthrough_residual_near_zero"
    assert reasons[C] == "intermediate_passthrough_residual_near_zero"


def test_gross_inflow_near_s_alone_is_not_enough() -> None:
    edges = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    related, _ = mod.discover_related_edges(
        edges, seed=SEED, max_hops=8, max_nodes=64, max_edges=128
    )
    residuals = mod.aggregate_residuals(related)
    draft, excluded = mod.select_candidates(residuals, seed=SEED, amount_raw=S, tolerance_raw=0)
    assert [item["address"] for item in draft] == [D]
    assert any(item["address"] == B for item in excluded)


def test_identical_content_rejects_candidates_even_with_different_formatting(
    tmp_path: Path,
) -> None:
    """Whole edge-set duplication (even reformatted) is not independent."""
    edges = [
        {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": D, "value_raw": str(S), "asset": "native"}
    ]
    compact = tmp_path / "compact.json"
    compact.write_text(json.dumps({"edges": edges}), encoding="utf-8")
    spaced = tmp_path / "spaced.json"
    spaced.write_text(json.dumps({"edges": edges}, indent=4), encoding="utf-8")
    assert mod.file_sha256(compact) != mod.file_sha256(spaced)  # bytes really do differ

    discovery = mod.load_edges(compact, asset_scope="native")
    independent = mod.load_edges(spaced, asset_scope="native")
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["candidates"] == []
    assert any(
        item["reason"] == "independent_edges_identical_content_to_discovery"
        for item in report["excluded"]
    )


def test_same_tx_confirmed_by_independent_set_is_accepted() -> None:
    """P1 fix: the SAME real transaction, re-seen via a different collection
    method, must CONFIRM the candidate -- not be rejected as 'reused'."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    # independent set has one extra edge from an UNRELATED address (so
    # whole-set content differs) but must not touch D itself, or it would
    # (correctly) contradict D's terminus status -- see the dedicated test
    # below for that case.
    independent = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
        _edge("0x" + "99" * 32, E, SEED, 1),
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert len(report["candidates"]) == 1
    cand = report["candidates"][0]
    assert cand["address"] == D
    assert cand["independent_verification"] == "second_input_confirmed_same_tx"
    assert cand["path_tx_hashes"] == ["0x" + "11" * 32, "0x" + "22" * 32]


def test_different_tx_with_matching_topology_does_not_confirm() -> None:
    """An unrelated TX that merely connects the same addresses/amounts must
    NOT count as confirmation of the discovery path."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    independent = [
        _edge("0x" + "aa" * 32, SEED, B, S),
        _edge("0x" + "bb" * 32, B, D, S),
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["candidates"] == []
    reasons = {item["address"]: item["reason"] for item in report["excluded"]}
    assert reasons[D] == "independent_confirmation_missing_for_tx"


def test_independent_data_showing_further_outflow_rejects_candidate() -> None:
    """P1: discovery calls D terminal, but the independent set shows D
    itself sent funds onward -- that contradicts the terminus claim."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    independent = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
        _edge("0x" + "99" * 32, D, E, 1),  # D itself has related outflow here
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["candidates"] == []
    reasons = {item["address"]: item["reason"] for item in report["excluded"]}
    assert reasons[D] == "independent_data_shows_further_outflow"


def test_independent_residual_mismatch_rejects_candidate() -> None:
    """P1: independent set shows *seed-connected* extra inflow to D (via a
    second branch SEED->E->D), so its own residual no longer matches S even
    though related_out is still zero there."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    independent = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
        _edge("0x" + "77" * 32, SEED, E, 5),  # second seed-connected branch
        _edge("0x" + "99" * 32, E, D, 5),  # ...that also feeds into D
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["candidates"] == []
    reasons = {item["address"]: item["reason"] for item in report["excluded"]}
    assert reasons[D] == "independent_residual_mismatch"


def test_independent_unrelated_external_inflow_does_not_falsely_reject() -> None:
    """Doc 76 boundary: an inflow to D with NO path from seed in the
    independent graph must be ignored, not treated as a residual mismatch."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    independent = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
        _edge("0x" + "99" * 32, E, D, 5),  # E has no path from SEED here
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert len(report["candidates"]) == 1
    assert report["candidates"][0]["address"] == D


def test_scope_complete_is_always_false() -> None:
    discovery = [_edge("0x" + "11" * 32, SEED, D, S)]
    independent = [_edge("0x" + "11" * 32, SEED, D, S), _edge("0x" + "99" * 32, E, SEED, 1)]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["scope_complete"] is False


def test_same_collection_method_for_both_sets_is_rejected() -> None:
    with pytest.raises(ValueError, match="must differ"):
        _run(
            _config(independent_collection_method="block_window_scan"),
            discovery=[],
            independent=[],
        )


def test_tolerance_cap_enforced() -> None:
    with pytest.raises(ValueError, match="tolerance_raw exceeds"):
        _run(_config(tolerance_raw=100, tolerance_cap_raw=10), discovery=[], independent=[])


def test_non_positive_budget_values_are_rejected() -> None:
    for field in ("max_hops", "max_nodes", "max_edges"):
        with pytest.raises(ValueError, match="must be > 0"):
            _run(_config(**{field: 0}), discovery=[], independent=[])


def test_load_edges_rejects_malformed_hex(tmp_path: Path) -> None:
    bad_tx = _write(
        tmp_path,
        "bad_tx.json",
        [{"tx_hash": "0xnotvalidhex", "from": SEED, "to": D, "value_raw": str(S)}],
    )
    with pytest.raises(ValueError, match="tx_hash"):
        mod.load_edges(bad_tx, asset_scope="native")

    bad_addr = _write(
        tmp_path,
        "bad_addr.json",
        [{"tx_hash": "0x" + "11" * 32, "from": "0xshort", "to": D, "value_raw": str(S)}],
    )
    with pytest.raises(ValueError, match="from"):
        mod.load_edges(bad_addr, asset_scope="native")


def test_load_edges_rejects_conflicting_duplicate_tx_hash(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "conflict.json",
        [
            {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": B, "value_raw": str(S)},
            # Same tx_hash, no locator, different `to` -- impossible for one movement.
            {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": D, "value_raw": str(S)},
        ],
    )
    with pytest.raises(ValueError, match="conflicting"):
        mod.load_edges(path, asset_scope="native")


def test_load_edges_allows_same_tx_hash_with_distinct_log_index(tmp_path: Path) -> None:
    """One transaction can emit multiple Transfer events."""
    path = _write(
        tmp_path,
        "multi_transfer.json",
        [
            {
                "tx_hash": "0x" + "11" * 32,
                "from": SEED,
                "to": B,
                "value_raw": str(S),
                "log_index": 0,
            },
            {
                "tx_hash": "0x" + "11" * 32,
                "from": SEED,
                "to": D,
                "value_raw": str(S),
                "log_index": 1,
            },
        ],
    )
    edges = mod.load_edges(path, asset_scope="native")
    assert len(edges) == 2


def test_load_edges_dedups_exact_duplicate_rows(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "dup.json",
        [
            {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": B, "value_raw": str(S)},
            {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": B, "value_raw": str(S)},
        ],
    )
    edges = mod.load_edges(path, asset_scope="native")
    assert len(edges) == 1


def test_cli_smoke_a_to_d(tmp_path: Path) -> None:
    discovery = {
        "edges": [
            {
                "tx_hash": "0x" + "11" * 32,
                "from": SEED,
                "to": B,
                "value_raw": hex(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "22" * 32,
                "from": B,
                "to": C,
                "value_raw": hex(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "33" * 32,
                "from": C,
                "to": D,
                "value_raw": hex(S),
                "asset": "native",
            },
        ]
    }
    # A different collection method re-confirming the *same* transactions,
    # plus one unrelated edge so the whole file is not a byte-for-byte copy.
    independent = {
        "edges": [
            {
                "tx_hash": "0x" + "11" * 32,
                "from": SEED,
                "to": B,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "22" * 32,
                "from": B,
                "to": C,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "33" * 32,
                "from": C,
                "to": D,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "44" * 32,
                "from": E,
                "to": SEED,
                "value_raw": "1",
                "asset": "native",
            },
        ]
    }
    d_path = tmp_path / "d.json"
    i_path = tmp_path / "i.json"
    d_path.write_text(json.dumps(discovery), encoding="utf-8")
    i_path.write_text(json.dumps(independent), encoding="utf-8")
    code = mod.main(
        [
            "--seed",
            SEED,
            "--chain-id",
            "1",
            "--amount-raw",
            str(S),
            "--tolerance-raw",
            "0",
            "--tolerance-cap-raw",
            str(10**15),
            "--tolerance-rationale",
            "exact",
            "--collection-method",
            "block_window_scan",
            "--independent-collection-method",
            "indexed_transfers",
            "--discovery-edges",
            str(d_path),
            "--independent-edges",
            str(i_path),
        ]
    )
    assert code == 0
