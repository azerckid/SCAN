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
S = 1_000_000_000_000_000_000  # 1 ETH in wei

COMPLETE_MANIFEST = mod.ScopeManifest(
    pagination_complete=True, continuous_scan=True, from_block=1, to_block=2
)
DEFAULT_MANIFEST = mod.ScopeManifest(
    pagination_complete=False, continuous_scan=False, from_block=None, to_block=None
)


def _edge(tx: str, frm: str, to: str, value: int) -> mod.Edge:
    return mod.Edge(tx_hash=tx, from_addr=frm, to_addr=to, value_raw=value, asset="native")


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


def _run(config: mod.RunConfig, *, discovery, independent, manifest=COMPLETE_MANIFEST, **hashes):
    hashes.setdefault("discovery_file_sha256", "d" * 64)
    hashes.setdefault("independent_file_sha256", "i" * 64)
    return mod.run_analysis(
        config,
        discovery_edges=discovery,
        independent_edges=independent,
        scope_manifest=manifest,
        **hashes,
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
    """P1: file bytes differ (reformatted) but logical edges are identical."""
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


def test_independent_path_reuses_discovery_tx_is_rejected() -> None:
    """P1: independent path must not cite discovery's own TX hashes as proof,
    even when the two edge sets are not byte/content identical overall."""
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    # independent set adds one extra irrelevant edge so canonical content differs,
    # but the seed->D path still resolves through the *same* discovery TX (0x11/0x22).
    independent = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
        _edge("0x" + "99" * 32, D, SEED, 1),
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert report["candidates"] == []
    reasons = {item["address"]: item["reason"] for item in report["excluded"]}
    assert reasons[D] == "independent_path_reuses_discovery_tx"


def test_independent_edge_set_verifies_path(tmp_path: Path) -> None:
    discovery = [
        _edge("0x" + "11" * 32, SEED, B, S),
        _edge("0x" + "22" * 32, B, D, S),
    ]
    independent = [
        _edge("0x" + "aa" * 32, SEED, B, S),
        _edge("0x" + "bb" * 32, B, D, S),
    ]
    report = _run(_config(), discovery=discovery, independent=independent)
    assert len(report["candidates"]) == 1
    cand = report["candidates"][0]
    assert cand["address"] == D
    assert cand["independent_verification"] == "independent_edge_set"
    assert cand["path_tx_hashes"] == ["0x" + "aa" * 32, "0x" + "bb" * 32]
    assert report["verification_level"] == "heuristic_candidates"
    assert report["honesty"]["single_candidate_is_not_confirmed"] is True
    assert "independent_verification_caveat" in report["honesty"]


def test_scope_complete_defaults_false_without_manifest() -> None:
    discovery = [_edge("0x" + "11" * 32, SEED, D, S)]
    independent = [_edge("0x" + "aa" * 32, SEED, D, S)]
    report = _run(
        _config(), discovery=discovery, independent=independent, manifest=DEFAULT_MANIFEST
    )
    assert report["scope_complete"] is False
    assert report["scope_manifest"]["pagination_complete"] is False
    assert report["scope_manifest"]["continuous_scan"] is False


def test_scope_complete_true_requires_full_manifest_and_unexhausted_budget() -> None:
    discovery = [_edge("0x" + "11" * 32, SEED, D, S)]
    independent = [_edge("0x" + "aa" * 32, SEED, D, S)]
    report = _run(
        _config(), discovery=discovery, independent=independent, manifest=COMPLETE_MANIFEST
    )
    assert report["scope_complete"] is True


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
            # Same tx_hash, different `to` -- impossible for a real TX.
            {"tx_hash": "0x" + "11" * 32, "from": SEED, "to": D, "value_raw": str(S)},
        ],
    )
    with pytest.raises(ValueError, match="conflicting"):
        mod.load_edges(path, asset_scope="native")


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
    independent = {
        "edges": [
            {
                "tx_hash": "0x" + "44" * 32,
                "from": SEED,
                "to": B,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "55" * 32,
                "from": B,
                "to": C,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "66" * 32,
                "from": C,
                "to": D,
                "value_raw": str(S),
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
            "--pagination-complete",
            "--continuous-scan",
        ]
    )
    assert code == 0
