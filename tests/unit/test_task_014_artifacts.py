import json
from pathlib import Path

from scan_tool.application.task_014_artifacts import build_fixture_packages
from scan_tool.application.task_014_replay import (
    INTERNAL_SOURCE,
    INTERNAL_VALUE,
    SEED_NODE,
    SELECTED_TRANSACTIONS,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"


def _report(role: str) -> dict:
    provider = f"PROVIDER-EVM-{role.upper()}"
    observations = []
    for index, (label, transaction_hash) in enumerate(SELECTED_TRANSACTIONS):
        transaction = {
            "hash": transaction_hash,
            "blockHash": f"0xblock{index}",
            "blockNumber": hex(index + 1),
            "transactionIndex": hex(index),
            "from": "0x0000000000000000000000000000000000000001",
            "to": "0x0000000000000000000000000000000000000002",
            "value": "0x1",
        }
        receipt = {
            "transactionHash": transaction_hash,
            "blockHash": transaction["blockHash"],
            "blockNumber": transaction["blockNumber"],
            "transactionIndex": transaction["transactionIndex"],
            "status": "0x1",
        }
        observations.extend(
            (
                _observation(f"{label}_transaction", transaction, role),
                _observation(f"{label}_receipt", receipt, role),
            )
        )
    if role == "primary":
        observations.append(
            _observation(
                "internal_seed_trace",
                {
                    "selected_internal_edge": {
                        "path": [0],
                        "type": "call",
                        "from": INTERNAL_SOURCE,
                        "to": SEED_NODE,
                        "value_hex": hex(int(INTERNAL_VALUE)),
                        "value_raw": INTERNAL_VALUE,
                    },
                    "matching_edge_count": 1,
                },
                role,
            )
        )
    return {
        "status": "complete",
        "provider_id": provider,
        "role": role,
        "network_calls": len(observations),
        "started_at": "2026-07-29T00:00:00Z",
        "finished_at": "2026-07-29T00:00:01Z",
        "observations": observations,
    }


def _observation(capability: str, summary: dict, role: str) -> dict:
    return {
        "capability": capability,
        "outcome": "success",
        "raw_sha256": (role[0] * 63) + ("1" if role == "primary" else "2"),
        "decoded_summary": summary,
    }


def test_build_packages_requires_matching_two_provider_decodes() -> None:
    packages = build_fixture_packages(_report("primary"), _report("verify"))
    assert set(packages) == {
        "FX-FLOW-PATH-001",
        "FX-FLOW-REMERGE-001",
        "FX-FLOW-MULTI-001",
    }
    path_raw, path_provider = packages["FX-FLOW-PATH-001"]
    assert len(path_raw["transactions"]) == 3
    assert path_raw["internal_edges"][0]["value_raw"] == INTERNAL_VALUE
    assert path_provider["decoded_match"] is True
    assert path_provider["providers"][0]["raw_sha256"]["internal_seed_trace"]


def test_provider_mismatch_is_rejected() -> None:
    primary = _report("primary")
    verify = _report("verify")
    verify["observations"][0]["decoded_summary"]["value"] = "0x2"
    try:
        build_fixture_packages(primary, verify)
    except ValueError as error:
        assert "decoded values differ" in str(error)
    else:
        raise AssertionError("provider mismatch must be rejected")


def test_confirmed_path_internal_edge_has_independent_cross_check() -> None:
    package = FIXTURES / "FX-FLOW-PATH-001"
    replay = json.loads((package / "raw-replay.json").read_text())
    provider = json.loads((package / "provider-replay.json").read_text())
    evidence = json.loads((package / "evidence.json").read_text())

    assert replay["status"] == provider["status"] == evidence["status"] == "confirmed"
    internal = replay["internal_edges"][0]
    cross_check = provider["internal_edge_cross_check"]
    assert cross_check["status"] == "complete"
    assert cross_check["from"] == internal["from"]
    assert cross_check["to"] == internal["to"]
    assert cross_check["value_raw"] == internal["value_raw"]
    assert cross_check["index"] == internal["path"][0] + 1
    assert cross_check["is_error"] is False
    assert cross_check["decoded_match_to_primary_trace"] is True
    assert evidence["consistency_checks"]["internal_seed_edge_cross_checked"] is True
