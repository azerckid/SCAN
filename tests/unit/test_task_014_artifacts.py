from scan_tool.application.task_014_artifacts import build_fixture_packages
from scan_tool.application.task_014_replay import (
    INTERNAL_SOURCE,
    INTERNAL_VALUE,
    SEED_NODE,
    SELECTED_TRANSACTIONS,
)


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
