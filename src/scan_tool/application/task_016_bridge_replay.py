"""Bounded two-chain replay for the TASK-016 Across bridge candidate."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import httpx

from scan_tool.application.provider_smoke import (
    ProviderRole,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.domain.source import JsonRpcSourceRequest

type BridgeChain = Literal["base", "ethereum"]
type BridgeProviderRole = Literal["primary", "verify"]

FIXTURE_ID = "FX-SVC-BRG-001"
CHAINS: tuple[BridgeChain, ...] = ("base", "ethereum")

SOURCE_TX = "0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b"
SOURCE_BLOCK = "0x14e5a4b"
SOURCE_TRANSACTION_TARGET = "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae"
SOURCE_SPOKE_POOL = "0x09aea4b2242abc8bb4bb78d537a67a245a7bec64"
SOURCE_EVENT_TOPIC = "0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f"

DESTINATION_TX = "0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0"
DESTINATION_BLOCK = "0x1420a1e"
DESTINATION_SPOKE_POOL = "0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5"
DESTINATION_EVENT_TOPIC = "0x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7"

EXPECTED_ORIGIN_CHAIN_ID = 8453
EXPECTED_DESTINATION_CHAIN_ID = 1
EXPECTED_DEPOSIT_ID = 2395968

BRIDGE_ENDPOINT_ENV: Mapping[BridgeProviderRole, Mapping[BridgeChain, str]] = {
    "primary": {
        "base": "SCAN_BASE_PRIMARY_RPC_URL",
        "ethereum": "SCAN_EVM_PRIMARY_RPC_URL",
    },
    "verify": {
        "base": "SCAN_BASE_VERIFY_RPC_URL",
        "ethereum": "SCAN_EVM_VERIFY_RPC_URL",
    },
}


def resolve_bridge_endpoints(
    *,
    execute: bool,
    rules_status: str,
    role: BridgeProviderRole,
    environment: Mapping[str, str],
) -> dict[BridgeChain, str] | None:
    """Resolve two chain endpoints only after the explicit live Rules gate."""
    if not execute:
        return None
    if rules_status != "allowed":
        raise PermissionError("live bridge replay requires rules_status=allowed")
    result: dict[BridgeChain, str] = {}
    for chain, name in BRIDGE_ENDPOINT_ENV[role].items():
        endpoint = environment.get(name)
        if not endpoint:
            raise ValueError(f"live bridge replay requires {name}")
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError(f"{name} must be an absolute HTTPS URL")
        if parts.username is not None or parts.password is not None:
            raise ValueError(f"{name} must not contain URL userinfo")
        result[chain] = endpoint
    return result


def bridge_requests(chain: BridgeChain) -> tuple[JsonRpcSourceRequest, ...]:
    """Return the fixed read-only request set for one side of the bridge."""
    transaction_hash, block_tag, spoke_pool, topic0 = _chain_constants(chain)
    return (
        JsonRpcSourceRequest(
            f"{chain}_transaction",
            "eth_getTransactionByHash",
            [transaction_hash],
            block_tag,
        ),
        JsonRpcSourceRequest(
            f"{chain}_receipt",
            "eth_getTransactionReceipt",
            [transaction_hash],
            block_tag,
        ),
        JsonRpcSourceRequest(
            f"{chain}_block",
            "eth_getBlockByNumber",
            [block_tag, False],
            block_tag,
        ),
        JsonRpcSourceRequest(
            f"{chain}_bridge_logs",
            "eth_getLogs",
            [
                {
                    "address": spoke_pool,
                    "fromBlock": block_tag,
                    "toBlock": block_tag,
                    "topics": [topic0],
                }
            ],
            block_tag,
        ),
    )


async def run_task_016_bridge_replay(
    *,
    chain: BridgeChain,
    role: BridgeProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    """Run one bounded chain-side replay through the shared provider guard."""
    provider_role: ProviderRole = role
    return await run_read_only_probe(
        role=provider_role,
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=bridge_requests(chain),
        summary_decoder=lambda request, raw: _summary(chain, request, raw),
        provider_id_override=f"PROVIDER-{chain.upper()}-{role.upper()}",
    )


def bridge_pair_facts(
    source_report: SmokeReport,
    destination_report: SmokeReport,
) -> dict[str, object]:
    """Validate and return the deterministic Across facts for one provider role."""
    if source_report.status != "complete" or destination_report.status != "complete":
        raise ValueError("both bridge chain reports must be complete")
    source = _validated_chain_event(source_report, "base")
    destination = _validated_chain_event(destination_report, "ethereum")
    required_equal = (
        "deposit_id",
        "input_token",
        "input_amount_raw",
        "output_amount_raw",
        "fill_deadline",
        "exclusivity_deadline",
        "depositor",
        "recipient",
        "message",
    )
    for key in required_equal:
        if source[key] != destination[key]:
            raise ValueError(f"bridge event mismatch: {key}")
    if source["destination_chain_id"] != EXPECTED_DESTINATION_CHAIN_ID:
        raise ValueError("source destination chain mismatch")
    if destination["origin_chain_id"] != EXPECTED_ORIGIN_CHAIN_ID:
        raise ValueError("destination origin chain mismatch")
    if source["deposit_id"] != EXPECTED_DEPOSIT_ID:
        raise ValueError("bridge deposit ID mismatch")
    source_raw = int(str(source["input_amount_raw"]))
    destination_raw = int(str(destination["output_amount_raw"]))
    if source_raw < destination_raw:
        raise ValueError("bridge output exceeds input")
    return {
        "protocol": "across_v3",
        "origin_chain_id": EXPECTED_ORIGIN_CHAIN_ID,
        "destination_chain_id": EXPECTED_DESTINATION_CHAIN_ID,
        "source_spoke_pool": SOURCE_SPOKE_POOL,
        "destination_spoke_pool": DESTINATION_SPOKE_POOL,
        "deposit_id": EXPECTED_DEPOSIT_ID,
        "depositor": source["depositor"],
        "recipient": source["recipient"],
        "input_token": source["input_token"],
        "destination_token": destination["output_token"],
        "input_amount_raw": str(source_raw),
        "output_amount_raw": str(destination_raw),
        "fee_difference_raw": str(source_raw - destination_raw),
        "message": source["message"],
    }


def _summary(
    chain: BridgeChain,
    request: JsonRpcSourceRequest,
    raw_bytes: bytes,
) -> object:
    result = json.loads(raw_bytes)["result"]
    if request.method == "eth_getTransactionByHash":
        return _select(result, "hash", "blockHash", "blockNumber", "from", "to", "value")
    if request.method == "eth_getTransactionReceipt":
        receipt = _require_mapping(result)
        spoke_pool = _chain_constants(chain)[2]
        topic0 = _chain_constants(chain)[3]
        selected_logs = [
            {
                "transaction_hash": item.get("transactionHash"),
                "log_index": item.get("logIndex"),
                "topic0": item.get("topics", [None])[0]
                if isinstance(item.get("topics"), list) and item.get("topics")
                else None,
            }
            for item in receipt.get("logs", [])
            if isinstance(item, dict)
            and str(item.get("address", "")).lower() == spoke_pool
            and isinstance(item.get("topics"), list)
            and bool(item.get("topics"))
            and str(item["topics"][0]).lower() == topic0
        ]
        return {
            **_select(
                receipt,
                "transactionHash",
                "blockHash",
                "blockNumber",
                "status",
                "transactionIndex",
            ),
            "selected_log_count": len(selected_logs),
            "selected_logs": selected_logs,
        }
    if request.method == "eth_getBlockByNumber":
        return _select(result, "number", "hash", "timestamp")
    if request.method == "eth_getLogs":
        if not isinstance(result, list) or len(result) != 1:
            raise ValueError("bridge log query must return exactly one event")
        return {
            "count": 1,
            "event": _decode_bridge_event(chain, _require_mapping(result[0])),
        }
    raise ValueError("unsupported TASK-016 bridge capability")


def _decode_bridge_event(
    chain: BridgeChain,
    value: Mapping[str, object],
) -> dict[str, object]:
    topics = value.get("topics")
    data = value.get("data")
    if not isinstance(topics, list) or len(topics) != 4:
        raise ValueError("bridge event topics are malformed")
    if not all(isinstance(item, str) and item.startswith("0x") for item in topics):
        raise ValueError("bridge event topics must be hex strings")
    expected_topic = _chain_constants(chain)[3]
    if str(topics[0]).lower() != expected_topic:
        raise ValueError("bridge event topic0 mismatch")
    if str(value.get("address", "")).lower() != _chain_constants(chain)[2]:
        raise ValueError("bridge event contract mismatch")
    words = _data_words(data)
    common = {
        "input_token": _address(words[0]),
        "output_token": _address(words[1]),
        "input_amount_raw": str(int(words[2], 16)),
        "output_amount_raw": str(int(words[3], 16)),
        "deposit_id": int(str(topics[2]), 16),
        "log_index": value.get("logIndex"),
        "transaction_hash": value.get("transactionHash"),
    }
    if chain == "base":
        if len(words) < 10:
            raise ValueError("V3FundsDeposited data is truncated")
        return {
            **common,
            "destination_chain_id": int(str(topics[1]), 16),
            "depositor": _address(str(topics[3])[2:]),
            "quote_timestamp": int(words[4], 16),
            "fill_deadline": int(words[5], 16),
            "exclusivity_deadline": int(words[6], 16),
            "recipient": _address(words[7]),
            "exclusive_relayer": _address(words[8]),
            "message": _dynamic_bytes(words, 9),
        }
    if len(words) < 12:
        raise ValueError("FilledV3Relay data is truncated")
    return {
        **common,
        "origin_chain_id": int(str(topics[1]), 16),
        "relayer": _address(str(topics[3])[2:]),
        "repayment_chain_id": int(words[4], 16),
        "fill_deadline": int(words[5], 16),
        "exclusivity_deadline": int(words[6], 16),
        "exclusive_relayer": _address(words[7]),
        "depositor": _address(words[8]),
        "recipient": _address(words[9]),
        "message": _dynamic_bytes(words, 10),
    }


def _data_words(value: object) -> list[str]:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("bridge event data must be hex")
    body = value[2:]
    if len(body) % 64:
        raise ValueError("bridge event data is not word-aligned")
    return [body[index : index + 64] for index in range(0, len(body), 64)]


def _dynamic_bytes(words: list[str], offset_index: int) -> str:
    offset = int(words[offset_index], 16)
    if offset % 32 or offset // 32 >= len(words):
        raise ValueError("bridge dynamic bytes offset is invalid")
    length_index = offset // 32
    length = int(words[length_index], 16)
    body = "".join(words[length_index + 1 :])
    if length * 2 > len(body):
        raise ValueError("bridge dynamic bytes are truncated")
    return f"0x{body[: length * 2]}"


def _observation_summary(report: SmokeReport, capability: str) -> Mapping[str, object]:
    for observation in report.observations:
        if observation.capability != capability:
            continue
        summary = observation.decoded_summary
        if not isinstance(summary, dict):
            raise ValueError("bridge observation summary is unavailable")
        return summary
    raise ValueError(f"bridge observation is missing: {capability}")


def _validated_chain_event(report: SmokeReport, chain: BridgeChain) -> Mapping[str, object]:
    transaction_hash, block_tag, spoke_pool, _ = _chain_constants(chain)
    transaction = _observation_summary(report, f"{chain}_transaction")
    receipt = _observation_summary(report, f"{chain}_receipt")
    block = _observation_summary(report, f"{chain}_block")
    logs = _observation_summary(report, f"{chain}_bridge_logs")
    if str(transaction.get("hash", "")).lower() != transaction_hash:
        raise ValueError("bridge transaction hash mismatch")
    if str(transaction.get("blockNumber", "")).lower() != block_tag:
        raise ValueError("bridge transaction block mismatch")
    expected_target = SOURCE_TRANSACTION_TARGET if chain == "base" else spoke_pool
    if str(transaction.get("to", "")).lower() != expected_target:
        raise ValueError("bridge transaction target mismatch")
    if str(receipt.get("transactionHash", "")).lower() != transaction_hash:
        raise ValueError("bridge receipt transaction mismatch")
    if str(receipt.get("blockNumber", "")).lower() != block_tag:
        raise ValueError("bridge receipt block mismatch")
    block_hash = str(block.get("hash", "")).lower()
    if (
        not block_hash.startswith("0x")
        or str(transaction.get("blockHash", "")).lower() != block_hash
        or str(receipt.get("blockHash", "")).lower() != block_hash
    ):
        raise ValueError("bridge block hash reconciliation failed")
    if receipt.get("status") != "0x1":
        raise ValueError("bridge transaction was not successful")
    if int(receipt.get("selected_log_count", 0)) < 1:
        raise ValueError("bridge receipt does not contain SpokePool logs")
    if str(block.get("number", "")).lower() != block_tag:
        raise ValueError("bridge block response mismatch")
    event = logs.get("event")
    if not isinstance(event, dict):
        raise ValueError("bridge event summary is unavailable")
    if str(event.get("transaction_hash", "")).lower() != transaction_hash:
        raise ValueError("bridge event transaction mismatch")
    selected_logs = receipt.get("selected_logs")
    if not isinstance(selected_logs, list) or not any(
        isinstance(item, dict)
        and str(item.get("transaction_hash", "")).lower() == transaction_hash
        and item.get("log_index") == event.get("log_index")
        and str(item.get("topic0", "")).lower() == _chain_constants(chain)[3]
        for item in selected_logs
    ):
        raise ValueError("bridge event is not present in the receipt")
    return event


def _chain_constants(chain: BridgeChain) -> tuple[str, str, str, str]:
    if chain == "base":
        return SOURCE_TX, SOURCE_BLOCK, SOURCE_SPOKE_POOL, SOURCE_EVENT_TOPIC
    return (
        DESTINATION_TX,
        DESTINATION_BLOCK,
        DESTINATION_SPOKE_POOL,
        DESTINATION_EVENT_TOPIC,
    )


def _address(word: str) -> str:
    if len(word) != 64:
        raise ValueError("ABI address word must contain 32 bytes")
    return f"0x{word[-40:].lower()}"


def _require_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return value


def _select(value: object, *keys: str) -> dict[str, object]:
    mapping = _require_mapping(value)
    return {key: mapping[key] for key in keys if key in mapping}
