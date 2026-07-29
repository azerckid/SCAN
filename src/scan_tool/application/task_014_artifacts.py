"""Build secret-free TASK-014 replay packages from guarded provider reports."""

import json
from pathlib import Path
from typing import Any

from scan_tool.application.task_014_replay import SELECTED_TRANSACTIONS

FIXTURE_LABELS = {
    "FX-FLOW-PATH-001": ("internal_seed", "split_a", "merge_a"),
    "FX-FLOW-REMERGE-001": (
        "split_a",
        "split_b",
        "split_c",
        "split_d",
        "merge_c",
        "merge_a",
        "merge_d",
        "merge_b",
        "external_dust",
    ),
    "FX-FLOW-MULTI-001": ("merge_c", "merge_a", "merge_d", "merge_b"),
}


def load_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provider report must be an object")
    return value


def build_fixture_packages(
    primary: dict[str, Any],
    verify: dict[str, Any],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """Return raw/provider replay documents for the fixed fixture set."""
    _require_complete_report(primary, "PROVIDER-EVM-PRIMARY", 21)
    _require_complete_report(verify, "PROVIDER-EVM-VERIFY", 20)
    primary_items = _observations(primary)
    verify_items = _observations(verify)
    common_capabilities = set(verify_items)
    if common_capabilities != set(primary_items) - {"internal_seed_trace"}:
        raise ValueError("provider request sets differ")
    for capability in sorted(common_capabilities):
        if (
            primary_items[capability]["decoded_summary"]
            != verify_items[capability]["decoded_summary"]
        ):
            raise ValueError(f"provider decoded values differ for {capability}")

    transactions = _validated_transactions(primary_items)
    trace = primary_items["internal_seed_trace"]["decoded_summary"]
    if not isinstance(trace, dict) or trace.get("matching_edge_count") != 1:
        raise ValueError("primary internal trace is incomplete")

    packages = {}
    for fixture_id, labels in FIXTURE_LABELS.items():
        raw = {
            "schema_version": "0.1",
            "fixture_id": fixture_id,
            "status": "verifying",
            "chain_id": 1,
            "captured_at": verify["finished_at"],
            "scope": {
                "kind": "selected_transactions_and_exact_blocks",
                "selected_transactions_complete": True,
                "continuous_gap_scanned": False,
            },
            "transactions": [transactions[label] for label in labels],
            "sources": [
                {
                    "source_id": "DS-EVM-RPC-ARCHIVE",
                    "provider_id": "PROVIDER-EVM-PRIMARY",
                    "retrieved_at": primary["finished_at"],
                },
                {
                    "source_id": "DS-EVM-RPC-ARCHIVE",
                    "provider_id": "PROVIDER-EVM-VERIFY",
                    "retrieved_at": verify["finished_at"],
                },
            ],
        }
        if fixture_id == "FX-FLOW-PATH-001":
            raw["internal_edges"] = [trace["selected_internal_edge"]]
        provider = {
            "schema_version": "0.1",
            "fixture_id": fixture_id,
            "status": "verifying",
            "captured_at": verify["finished_at"],
            "scope_kind": "selected_transactions_and_exact_blocks",
            "providers": [
                _provider_projection(primary, primary_items, labels, fixture_id),
                _provider_projection(verify, verify_items, labels, fixture_id),
            ],
            "decoded_match": True,
            "selected_transaction_scope_complete": True,
            "continuous_gap_scanned": False,
            "internal_trace": (
                {
                    "provider_id": "PROVIDER-EVM-PRIMARY",
                    "status": "complete",
                    "capability": "internal_seed_trace",
                    "raw_sha256": primary_items["internal_seed_trace"]["raw_sha256"],
                    "decoded_match_to_expected_edge": True,
                }
                if fixture_id == "FX-FLOW-PATH-001"
                else None
            ),
            "remaining_gate": [
                "negative_oracle",
                "independent_verifier",
            ],
        }
        packages[fixture_id] = (raw, provider)
    return packages


def _validated_transactions(
    observations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected_hashes = dict(SELECTED_TRANSACTIONS)
    values: dict[str, dict[str, Any]] = {}
    for label, expected_hash in expected_hashes.items():
        transaction = observations[f"{label}_transaction"]["decoded_summary"]
        receipt = observations[f"{label}_receipt"]["decoded_summary"]
        if not isinstance(transaction, dict) or not isinstance(receipt, dict):
            raise ValueError(f"{label} decoded values must be objects")
        if transaction.get("hash") != expected_hash:
            raise ValueError(f"{label} transaction hash differs")
        if receipt.get("transactionHash") != expected_hash:
            raise ValueError(f"{label} receipt hash differs")
        for field in ("blockHash", "blockNumber", "transactionIndex"):
            if transaction.get(field) != receipt.get(field):
                raise ValueError(f"{label} transaction/receipt {field} differs")
        if receipt.get("status") != "0x1":
            raise ValueError(f"{label} receipt is not successful")
        values[label] = {
            "label": label,
            "transaction": transaction,
            "receipt": receipt,
        }
    return values


def _provider_projection(
    report: dict[str, Any],
    observations: dict[str, dict[str, Any]],
    labels: tuple[str, ...],
    fixture_id: str,
) -> dict[str, Any]:
    capabilities = [
        capability
        for label in labels
        for capability in (f"{label}_transaction", f"{label}_receipt")
    ]
    if fixture_id == "FX-FLOW-PATH-001" and report["role"] == "primary":
        capabilities.append("internal_seed_trace")
    return {
        "provider_id": report["provider_id"],
        "status": report["status"],
        "retrieved_at": report["finished_at"],
        "raw_sha256": {
            capability: observations[capability]["raw_sha256"] for capability in capabilities
        },
    }


def _observations(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = report.get("observations")
    if not isinstance(values, list):
        raise ValueError("provider observations must be an array")
    result = {}
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("capability"), str):
            raise ValueError("provider observation has an unexpected shape")
        if item.get("outcome") != "success" or not item.get("raw_sha256"):
            raise ValueError(f"{item.get('capability')} did not succeed")
        result[item["capability"]] = item
    if len(result) != len(values):
        raise ValueError("provider capabilities must be unique")
    return result


def _require_complete_report(
    report: dict[str, Any],
    provider_id: str,
    network_calls: int,
) -> None:
    if (
        report.get("status") != "complete"
        or report.get("provider_id") != provider_id
        or report.get("network_calls") != network_calls
    ):
        raise ValueError(f"{provider_id} report is incomplete")
