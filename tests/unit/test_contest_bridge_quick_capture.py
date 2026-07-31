"""Regression tests for the contest-day Bridge quick-capture helper.

This is a deliberately isolated tool (scripts/contest/) that must never be
mistaken for a production analyzer: it only calls the existing, unmodified
``analyze_bridge_transfer_replay`` and always reports
``verification_level: single_source_unverified``.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/contest/bridge_quick_capture.py"
SPEC = importlib.util.spec_from_file_location("bridge_quick_capture", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge_quick_capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bridge_quick_capture
SPEC.loader.exec_module(bridge_quick_capture)


def test_self_check_matches_pinned_fact_hash() -> None:
    report = bridge_quick_capture.self_check()
    assert report["self_check"]["matched_pinned_hash"] is True
    assert report["verification_level"] == "single_source_unverified"
    assert report["honesty"]["may_submit_as_confirmed"] is False
    assert "package_dir" not in report
    assert "package_id" in report


def test_resolve_rpc_endpoint_requires_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCAN_CONTEST_BASE_RPC_URL", raising=False)
    with pytest.raises(bridge_quick_capture.EndpointSecretError, match="requires env var"):
        bridge_quick_capture.resolve_rpc_endpoint("SCAN_CONTEST_BASE_RPC_URL", role="base")


def test_resolve_rpc_endpoint_rejects_non_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCAN_CONTEST_BASE_RPC_URL", "http://example.invalid/v3/secret")
    with pytest.raises(bridge_quick_capture.EndpointSecretError, match="HTTPS"):
        bridge_quick_capture.resolve_rpc_endpoint("SCAN_CONTEST_BASE_RPC_URL", role="base")


def test_resolve_rpc_endpoint_rejects_userinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCAN_CONTEST_BASE_RPC_URL", "https://user:pass@example.invalid/v3/secret")
    with pytest.raises(bridge_quick_capture.EndpointSecretError, match="userinfo"):
        bridge_quick_capture.resolve_rpc_endpoint("SCAN_CONTEST_BASE_RPC_URL", role="base")


def test_rpc_call_error_never_leaks_the_endpoint_secret() -> None:
    secret_url = "https://mainnet.infura.io/v3/SUPER_SECRET_KEY_ABCDEF123456"
    with pytest.raises(RuntimeError) as excinfo:
        bridge_quick_capture.rpc_call(secret_url, "eth_chainId", [], role="base RPC")
    assert "SUPER_SECRET_KEY_ABCDEF123456" not in str(excinfo.value)
    assert secret_url not in str(excinfo.value)


def test_verify_chain_id_rejects_mismatched_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_rpc_call(
        url: str, method: str, params: list, *, request_id: int = 1, role: str = "rpc"
    ):
        assert method == "eth_chainId"
        return {"jsonrpc": "2.0", "id": request_id, "result": "0x1"}

    monkeypatch.setattr(bridge_quick_capture, "rpc_call", fake_rpc_call)
    with pytest.raises(RuntimeError, match="endpoints may be swapped"):
        bridge_quick_capture.verify_chain_id("https://fake", chain="base", role="base RPC")


def test_verify_chain_id_accepts_matching_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_rpc_call(
        url: str, method: str, params: list, *, request_id: int = 1, role: str = "rpc"
    ):
        return {"jsonrpc": "2.0", "id": request_id, "result": "0x2105"}  # 8453

    monkeypatch.setattr(bridge_quick_capture, "rpc_call", fake_rpc_call)
    bridge_quick_capture.verify_chain_id("https://fake", chain="base", role="base RPC")
