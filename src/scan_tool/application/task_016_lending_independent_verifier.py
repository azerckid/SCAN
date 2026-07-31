"""Independent raw-first DeFi lending verifier for TASK-016.

This module is deliberately self-contained: it does not import anything from
``scan_tool.slices.defi_lending`` or ``scan_tool.domain.defi_lending``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

FIXTURE_IDS = ("FX-SVC-LEND-001",)
REQUIREMENTS = {
    "FX-SVC-LEND-001": ("REQ-LEND-EVENT", "REQ-LEND-LEDGER", "REQ-LEND-OUTFLOW"),
}
POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
TOPIC0 = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SUBJECT = "0x1b05437f4a5f6b21692e83af3eb5607683e6dead"
USER = "0xcdb238d68d8da74487711bc1f8f13f3d00667d1a"
COLL = "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
DEBT = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
DEBT_AMT = "364477506"
COLL_AMT = "87377757596420188410"
DEBT_SINK = "0x5ee5bf7ae06d1be5997a1a72006fe6c607ec6de8"
COLL_SRC = "0x0b925ed163218f6662a35e0f0371ac234f9e9371"
OUTFLOW_TO = "0x51c72848c68a965f66fa7a88855f9f7784502a7f"
OUTFLOW_AMT = "87377757596420177920"
TX = "0x207745c3f3cbcdc4f31a5a9d89810278e2e6cef385cb1bbf0b2c4b4ccdac4a37"
BLOCK = 21036015
WINDOW = (21036000, 21036030)
BLOCK_TAG = "0x140fbef"
BLOCK_HASH = "0x206a015aa99219d296473ac237aa87e57a97f55b286e2bd400d2aae842e58b25"
EXPECTED_PROVIDERS = {
    "PROVIDER-ETHEREUM-PUBLICNODE": ("PRIMARY", "https://ethereum.publicnode.com"),
    "PROVIDER-ETHEREUM-THIRDWEB": ("VERIFY", "https://ethereum.rpc.thirdweb.com"),
}
CAPABILITY_METHODS = {
    "transaction": "eth_getTransactionByHash",
    "receipt": "eth_getTransactionReceipt",
    "block": "eth_getBlockByNumber",
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
                package,
                load_json(package / "raw-replay.json"),
                load_json(package / "provider-replay.json"),
                load_json(package / "artifacts/capture-meta.json"),
                load_json(package / "expected.json"),
                load_json(package / "evidence.json"),
            )
        )
    return tuple(reports)


def verify_fixture(
    package: Path,
    raw: dict[str, Any],
    provider_replay: dict[str, Any],
    capture_meta: dict[str, Any],
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    fixture_id = _text(raw, "fixture_id")
    captured_at = datetime.fromisoformat(_text(raw, "captured_at").replace("Z", "+00:00"))
    if captured_at > datetime.now(UTC) + timedelta(minutes=5):
        raise ValueError("capture timestamp cannot be in the future")
    if _text(expected, "fixture_id") != fixture_id:
        raise ValueError("raw/expected fixture IDs differ")
    if _text(evidence, "fixture_id") != fixture_id:
        raise ValueError("raw/evidence fixture IDs differ")
    facts = recalculate_raw_facts(package, raw, provider_replay, capture_meta)
    if facts != _mapping(expected, "defi_lending"):
        raise ValueError(f"{fixture_id} independently calculated facts differ")
    _verify_requirements(fixture_id, expected)
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    calculated_sha256 = hashlib.sha256(canonical).hexdigest()
    provenance = _mapping(evidence, "verification_provenance")
    if provenance.get("canonical_sha256") != calculated_sha256:
        raise ValueError("canonical hash pin drifted")
    if provenance.get("independent_verifier_pass") is not True:
        raise ValueError("independent verifier pass flag is false")
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": calculated_sha256,
        "requirement_count": len(REQUIREMENTS[fixture_id]),
    }


def recalculate_raw_facts(
    package: Path,
    raw: dict[str, Any],
    provider_replay: dict[str, Any],
    capture_meta: dict[str, Any],
) -> dict[str, Any]:
    providers = provider_replay.get("providers")
    if not isinstance(providers, list) or len(providers) != 2:
        raise ValueError("exactly two providers are required")
    by_role = {}
    by_id = {}
    endpoints = []
    for item in providers:
        if not isinstance(item, dict):
            raise ValueError("provider entry malformed")
        role = item.get("role")
        endpoint = item.get("endpoint")
        provider_id = item.get("provider_id")
        if (
            role not in {"PRIMARY", "VERIFY"}
            or not isinstance(endpoint, str)
            or provider_id not in EXPECTED_PROVIDERS
        ):
            raise ValueError("provider role/endpoint malformed")
        if (role, endpoint) != EXPECTED_PROVIDERS[provider_id]:
            raise ValueError("provider role/endpoint differs from approved pin")
        endpoints.append(endpoint.rstrip("/").lower())
        by_role[role] = item
        by_id[provider_id] = item
    if set(by_role) != {"PRIMARY", "VERIFY"}:
        raise ValueError("PRIMARY/VERIFY roles required")
    if len(set(endpoints)) != 2:
        raise ValueError("provider endpoints must be distinct")
    if set(by_id) != set(EXPECTED_PROVIDERS):
        raise ValueError("approved provider IDs required")
    _verify_capture_meta(capture_meta, raw, by_id)

    observations = raw.get("raw_observations")
    if not isinstance(observations, list) or len(observations) != 2:
        raise ValueError("two raw observations required")
    decoded = {}
    selected_logs = {}
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError("observation malformed")
        role = observation.get("provider_role")
        provider_id = observation.get("provider_id")
        if (
            role not in by_role
            or provider_id not in by_id
            or by_id[provider_id] is not by_role[role]
        ):
            raise ValueError("observation provider identity/role mismatch")
        decoded[role], selected_logs[role] = _decode_role(package, observation, by_role[role], raw)
    if decoded["PRIMARY"] != decoded["VERIFY"]:
        raise ValueError("cross-provider immutable facts differ")
    if selected_logs["PRIMARY"] != selected_logs["VERIFY"]:
        raise ValueError("cross-provider selected raw logs differ")
    # reject identical artifact hashes
    primary_pins = by_role["PRIMARY"]["raw_sha256"]
    verify_pins = by_role["VERIFY"]["raw_sha256"]
    for key in ("transaction", "receipt", "block"):
        if primary_pins[key] == verify_pins[key]:
            raise ValueError(f"identical {key} artifact bytes")
    return decoded["PRIMARY"]


def _decode_role(
    package: Path,
    observation: dict[str, Any],
    provider: dict[str, Any],
    raw: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = observation.get("artifacts")
    pins = provider.get("raw_sha256")
    if not isinstance(artifacts, dict) or not isinstance(pins, dict):
        raise ValueError("artifacts/pins malformed")
    tx = _load_artifact(package, artifacts, pins, "transaction")["result"]
    receipt = _load_artifact(package, artifacts, pins, "receipt")["result"]
    block = _load_artifact(package, artifacts, pins, "block")["result"]
    if str(tx.get("hash")).lower() != TX:
        raise ValueError("tx hash mismatch")
    if int(str(tx.get("blockNumber")), 16) != BLOCK:
        raise ValueError("tx block mismatch")
    if str(tx.get("blockHash")).lower() != BLOCK_HASH:
        raise ValueError("tx block hash mismatch")
    if str(receipt.get("transactionHash")).lower() != TX:
        raise ValueError("receipt tx mismatch")
    if (
        str(receipt.get("blockHash")).lower() != BLOCK_HASH
        or str(receipt.get("blockNumber")).lower() != BLOCK_TAG
    ):
        raise ValueError("receipt block binding mismatch")
    if receipt.get("status") != "0x1":
        raise ValueError("tx failed")
    if (
        str(block.get("hash")).lower() != BLOCK_HASH
        or str(block.get("number")).lower() != BLOCK_TAG
    ):
        raise ValueError("block hash mismatch")
    tx_index = _hex_index(tx.get("transactionIndex"), "tx transactionIndex")
    receipt_tx_index = _hex_index(receipt.get("transactionIndex"), "receipt transactionIndex")
    if tx_index != receipt_tx_index:
        raise ValueError("tx/receipt transactionIndex mismatch")
    transactions = block.get("transactions")
    if (
        not isinstance(transactions, list)
        or tx_index >= len(transactions)
        or str(transactions[tx_index]).lower() != TX
    ):
        raise ValueError("transaction absent from fetched block")
    if not (WINDOW[0] <= BLOCK <= WINDOW[1]):
        raise ValueError("window violation")
    logs = receipt.get("logs")
    if not isinstance(logs, list):
        raise ValueError("logs malformed")
    liq = [
        item
        for item in logs
        if isinstance(item, dict)
        and isinstance(item.get("topics"), list)
        and item["topics"]
        and str(item["topics"][0]).lower() == TOPIC0
        and str(item.get("address")).lower() == POOL
    ]
    if len(liq) != 1:
        raise ValueError("expected one LiquidationCall")
    log = liq[0]
    _verify_log_binding(log, tx_index, "LiquidationCall")
    topics = log["topics"]
    if len(topics) != 4:
        raise ValueError("LiquidationCall topic count malformed")
    for topic in topics:
        _fixed_hex(topic, 32, "LiquidationCall topic")
    _fixed_hex(log.get("data"), 128, "LiquidationCall data")
    data = bytes.fromhex(str(log["data"])[2:])
    receive_a_token_raw = int.from_bytes(data[96:128], "big")
    if receive_a_token_raw not in {0, 1}:
        raise ValueError("LiquidationCall bool malformed")
    event = {
        "event_name": "LiquidationCall",
        "protocol": "aave_v3",
        "pool": POOL,
        "collateral_asset": "0x" + str(topics[1])[-40:].lower(),
        "debt_asset": "0x" + str(topics[2])[-40:].lower(),
        "user": "0x" + str(topics[3])[-40:].lower(),
        "liquidator": "0x" + data[76:96].hex(),
        "debt_to_cover_raw": str(int.from_bytes(data[0:32], "big")),
        "liquidated_collateral_amount_raw": str(int.from_bytes(data[32:64], "big")),
        "receive_a_token": bool(receive_a_token_raw),
        "block_number": BLOCK,
        "transaction_hash": TX,
        "transaction_index": int(str(log["transactionIndex"]), 16),
        "log_index": int(str(log["logIndex"]), 16),
        "topic0": TOPIC0,
    }
    if event["receive_a_token"]:
        raise ValueError("receiveAToken unexpected")
    if event["liquidator"] != SUBJECT or event["user"] != USER:
        raise ValueError("participant mismatch")
    if event["collateral_asset"] != COLL or event["debt_asset"] != DEBT:
        raise ValueError("asset mismatch")
    if (
        event["debt_to_cover_raw"] != DEBT_AMT
        or event["liquidated_collateral_amount_raw"] != COLL_AMT
    ):
        raise ValueError("amount mismatch")

    transfers = []
    for item in logs:
        if not isinstance(item, dict) or not isinstance(item.get("topics"), list):
            continue
        topics = item["topics"]
        if not topics or str(topics[0]).lower() != TRANSFER:
            continue
        if len(topics) != 3:
            raise ValueError("Transfer topic count malformed")
        for topic in topics:
            _fixed_hex(topic, 32, "Transfer topic")
        _fixed_hex(item.get("address"), 20, "Transfer address")
        _fixed_hex(item.get("data"), 32, "Transfer data")
        _verify_log_binding(item, tx_index, "Transfer")
        data_hex = str(item["data"])
        amount = str(int(data_hex, 16))
        transfers.append(
            {
                "token": str(item.get("address")).lower(),
                "from": "0x" + str(topics[1])[-40:].lower(),
                "to": "0x" + str(topics[2])[-40:].lower(),
                "amount": amount,
                "log_index": int(str(item["logIndex"]), 16),
                "raw_log": _log_signature(item),
            }
        )
    debt = next(
        item
        for item in transfers
        if item["token"] == DEBT
        and item["amount"] == DEBT_AMT
        and item["from"] == SUBJECT
        and item["to"] == DEBT_SINK
    )
    coll = next(
        item
        for item in transfers
        if item["token"] == COLL
        and item["amount"] == COLL_AMT
        and item["to"] == SUBJECT
        and item["from"] == COLL_SRC
    )
    outflow = next(
        item
        for item in transfers
        if item["token"] == COLL
        and item["from"] == SUBJECT
        and item["to"] == OUTFLOW_TO
        and item["amount"] == OUTFLOW_AMT
        and item["log_index"] > coll["log_index"]
    )
    facts = {
        "protocol": "aave_v3",
        "pool": POOL,
        "chain_id": 1,
        "subject_address": SUBJECT,
        "subject_roles": ["liquidator"],
        "events": [event],
        "net_asset_ledger": [
            {
                "asset_address": DEBT,
                "raw_amount": DEBT_AMT,
                "direction": "out",
                "counterparty": DEBT_SINK,
                "leg_kind": "liquidation_debt",
                "matched_transfer_log_index": debt["log_index"],
                "classification": "confirmed_fact",
            },
            {
                "asset_address": COLL,
                "raw_amount": COLL_AMT,
                "direction": "in",
                "counterparty": COLL_SRC,
                "leg_kind": "liquidation_collateral",
                "matched_transfer_log_index": coll["log_index"],
                "classification": "confirmed_fact",
            },
        ],
        "subsequent_outflow": {
            "status": "bounded",
            "seed_address": SUBJECT,
            "terminal_address": OUTFLOW_TO,
            "asset_address": COLL,
            "raw_amount": OUTFLOW_AMT,
            "transaction_hash": TX,
            "log_index": outflow["log_index"],
            "classification": "confirmed_fact",
        },
        "attribution": {
            "attack_vs_normal": "not_assessed",
            "service_attribution": "not_assessed",
            "criminality": "not_assessed",
        },
    }
    selected = {
        "liquidation": _log_signature(log),
        "debt_transfer": debt["raw_log"],
        "collateral_transfer": coll["raw_log"],
        "subsequent_outflow": outflow["raw_log"],
    }
    return facts, selected


def _load_artifact(
    package: Path, artifacts: dict[str, Any], pins: dict[str, Any], key: str
) -> dict[str, Any]:
    uri = artifacts.get(key)
    pin = pins.get(key)
    if not isinstance(uri, str) or not uri.startswith("artifact://sha256/"):
        raise ValueError(f"{key} artifact uri malformed")
    digest = uri.removeprefix("artifact://sha256/")
    if digest != pin:
        raise ValueError(f"{key} pin mismatch")
    path = package / "artifacts" / "sha256" / f"{digest}.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"{key} content hash mismatch")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{key} artifact must be object")
    return value


def _verify_capture_meta(
    capture_meta: dict[str, Any],
    raw: dict[str, Any],
    providers: dict[str, dict[str, Any]],
) -> None:
    if (
        capture_meta.get("schema_version") != "0.1"
        or capture_meta.get("fixture_id") != raw.get("fixture_id")
        or capture_meta.get("captured_at") != raw.get("captured_at")
    ):
        raise ValueError("capture metadata envelope mismatch")
    capabilities = capture_meta.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != 6:
        raise ValueError("capture metadata must contain six capabilities")
    observed = set()
    for item in capabilities:
        if not isinstance(item, dict):
            raise ValueError("capture capability malformed")
        provider_id = item.get("provider_id")
        capability = item.get("capability")
        if provider_id not in providers or capability not in CAPABILITY_METHODS:
            raise ValueError("capture capability provider/method malformed")
        provider = providers[provider_id]
        key = (provider_id, capability)
        if key in observed:
            raise ValueError("duplicate capture capability")
        observed.add(key)
        expected_params = [TX] if capability in {"transaction", "receipt"} else [BLOCK_TAG, False]
        if (
            item.get("provider_role") != provider.get("role")
            or item.get("endpoint") != provider.get("endpoint")
            or item.get("method") != CAPABILITY_METHODS[capability]
            or item.get("params") != expected_params
            or item.get("response_sha256") != provider["raw_sha256"][capability]
            or item.get("captured_at") != provider.get("retrieved_at")
        ):
            raise ValueError("capture capability differs from provider replay")
    expected = {
        (provider_id, capability)
        for provider_id in EXPECTED_PROVIDERS
        for capability in CAPABILITY_METHODS
    }
    if observed != expected:
        raise ValueError("capture capability coverage incomplete")


def _verify_log_binding(log: dict[str, Any], tx_index: int, label: str) -> None:
    if (
        log.get("removed") is not False
        or str(log.get("transactionHash")).lower() != TX
        or str(log.get("blockHash")).lower() != BLOCK_HASH
        or str(log.get("blockNumber")).lower() != BLOCK_TAG
        or _hex_index(log.get("transactionIndex"), f"{label} transactionIndex") != tx_index
    ):
        raise ValueError(f"{label} receipt binding mismatch")
    _hex_index(log.get("logIndex"), f"{label} logIndex")


def _log_signature(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": str(log.get("address")).lower(),
        "topics": [str(topic).lower() for topic in log.get("topics", [])],
        "data": str(log.get("data")).lower(),
        "log_index": _hex_index(log.get("logIndex"), "selected logIndex"),
        "transaction_index": _hex_index(log.get("transactionIndex"), "selected transactionIndex"),
        "transaction_hash": str(log.get("transactionHash")).lower(),
        "block_hash": str(log.get("blockHash")).lower(),
        "block_number": str(log.get("blockNumber")).lower(),
    }


def _hex_index(value: Any, label: str) -> int:
    if (
        not isinstance(value, str)
        or not value.startswith("0x")
        or len(value) < 3
        or any(char not in "0123456789abcdef" for char in value[2:].lower())
    ):
        raise ValueError(f"{label} malformed")
    return int(value, 16)


def _fixed_hex(value: Any, byte_length: int, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("0x")
        or len(value) != 2 + byte_length * 2
        or any(char not in "0123456789abcdef" for char in value[2:].lower())
    ):
        raise ValueError(f"{label} malformed")


def _verify_requirements(fixture_id: str, expected: dict[str, Any]) -> None:
    scoring = expected.get("scoring")
    if not isinstance(scoring, dict):
        raise ValueError("scoring missing")
    requirements = scoring.get("requirements")
    if not isinstance(requirements, list):
        raise ValueError("requirements missing")
    ids = [item.get("requirement_id") for item in requirements if isinstance(item, dict)]
    if tuple(ids) != REQUIREMENTS[fixture_id]:
        raise ValueError("requirement set drifted")


def _text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{key} must be string")
    return item


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"{key} must be object")
    return item
