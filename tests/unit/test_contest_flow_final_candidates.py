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


def _edge(tx: str, frm: str, to: str, value: int) -> mod.Edge:
    return mod.Edge(
        tx_hash=tx,
        from_addr=frm,
        to_addr=to,
        value_raw=value,
        asset="native",
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
        max_hops=8,
        max_nodes=64,
        max_edges=128,
    )
    base.update(overrides)
    return mod.RunConfig(**base)  # type: ignore[arg-type]


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
    # B receives S but immediately forwards S (passthrough)
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


def test_identical_discovery_and_independent_graphs_reject_candidates(
    tmp_path: Path,
) -> None:
    edges = {
        "edges": [
            {
                "tx_hash": "0x" + "11" * 32,
                "from": SEED,
                "to": D,
                "value_raw": str(S),
                "asset": "native",
            }
        ]
    }
    path = tmp_path / "same.json"
    path.write_text(json.dumps(edges), encoding="utf-8")
    loaded = mod.load_edges(path, asset_scope="native")
    digest = mod.file_sha256(path)
    report = mod.run_analysis(
        _config(),
        discovery_edges=loaded,
        independent_edges=loaded,
        discovery_sha256=digest,
        independent_sha256=digest,
    )
    assert report["verification_level"] == "heuristic_candidates"
    assert report["candidates"] == []
    assert any(
        item["reason"] == "independent_edges_identical_to_discovery" for item in report["excluded"]
    )
    assert report["honesty"]["may_submit_as_confirmed"] is False
    assert report["honesty"]["single_candidate_is_not_confirmed"] is True


def test_independent_edge_set_verifies_path(tmp_path: Path) -> None:
    discovery = {
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
                "to": D,
                "value_raw": str(S),
                "asset": "native",
            },
        ]
    }
    # Independent set has same topology but different tx hashes / file bytes
    independent = {
        "edges": [
            {
                "tx_hash": "0x" + "aa" * 32,
                "from": SEED,
                "to": B,
                "value_raw": str(S),
                "asset": "native",
            },
            {
                "tx_hash": "0x" + "bb" * 32,
                "from": B,
                "to": D,
                "value_raw": str(S),
                "asset": "native",
            },
        ]
    }
    d_path = tmp_path / "discovery.json"
    i_path = tmp_path / "independent.json"
    d_path.write_text(json.dumps(discovery), encoding="utf-8")
    i_path.write_text(json.dumps(independent), encoding="utf-8")
    report = mod.run_analysis(
        _config(),
        discovery_edges=mod.load_edges(d_path, asset_scope="native"),
        independent_edges=mod.load_edges(i_path, asset_scope="native"),
        discovery_sha256=mod.file_sha256(d_path),
        independent_sha256=mod.file_sha256(i_path),
    )
    assert len(report["candidates"]) == 1
    cand = report["candidates"][0]
    assert cand["address"] == D
    assert cand["independent_verification"] == "independent_edge_set"
    assert cand["path_tx_hashes"] == ["0x" + "aa" * 32, "0x" + "bb" * 32]
    assert report["verification_level"] == "heuristic_candidates"
    # Even with a single candidate, confirmed promotion is forbidden.
    assert report["honesty"]["single_candidate_is_not_confirmed"] is True


def test_tolerance_cap_enforced() -> None:
    with pytest.raises(ValueError, match="tolerance_raw exceeds"):
        mod.run_analysis(
            _config(tolerance_raw=100, tolerance_cap_raw=10),
            discovery_edges=[],
            independent_edges=[],
            discovery_sha256="a" * 64,
            independent_sha256="b" * 64,
        )


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
            "--discovery-edges",
            str(d_path),
            "--independent-edges",
            str(i_path),
        ]
    )
    assert code == 0
