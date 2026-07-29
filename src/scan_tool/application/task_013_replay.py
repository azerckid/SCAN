"""Bounded provider replay for TASK-013 NFT and EIP-1967 candidates."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import httpx

from scan_tool.application.provider_smoke import (
    ProviderRole,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.domain.source import JsonRpcSourceRequest

type Task013FixtureId = Literal[
    "FX-EVM-NFT-721-001",
    "FX-EVM-NFT-1155-001",
    "FX-EVM-PROXY-001",
]

NFT_721 = "FX-EVM-NFT-721-001"
NFT_1155 = "FX-EVM-NFT-1155-001"
PROXY = "FX-EVM-PROXY-001"
FIXTURE_IDS: tuple[Task013FixtureId, ...] = (NFT_721, NFT_1155, PROXY)

BAYC = "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d"
BAYC_SUBJECT = "0x28dda46bdc0aeb3b4e58e6a9a3774875729367a0"
BAYC_APPROVAL_TX = "0x4501b47b05689704ee2c2524bc9cb69bcbea0ca3ab71f2a4fc6db97d71af9379"
BAYC_TRANSFER_TX = "0x07ae8c28ff8109cbe3051308ecd00568ee5539d40c72154ad3412bbe14a727d7"
BAYC_APPROVAL_BLOCK = "0x17d9aba"
BAYC_TRANSFER_BLOCK = "0x17dd41c"

RARIBLE_1155 = "0xb66a603f4cfe17e3d27b87a8bfcad319856518b8"
RARIBLE_SINGLE_TX = "0x49f0ce147dd81bb250569f8f6d44c467e79452ba6fdb739165e03cf15fcfe2f0"
RARIBLE_BATCH_TX = "0x94fcb6337f5cae9223146caf50f92d9e1af4342ea7cb21bb16792d032e3a230e"
RARIBLE_SINGLE_BLOCK = "0x1778402"
RARIBLE_BATCH_BLOCK = "0x16a94dc"

AAVE_POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
AAVE_UPGRADE_TX = "0xe9949c36e86fc9f481897dbac8de33d655bff20b267955a303e2e5643fbc2b35"
AAVE_BEFORE_BLOCK = "0x1808542"
AAVE_AFTER_BLOCK = "0x1808543"
IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_FOR_ALL_TOPIC = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
TRANSFER_SINGLE_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
TRANSFER_BATCH_TOPIC = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
UPGRADED_TOPIC = "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b"
PADDED_BAYC_SUBJECT = f"0x{'0' * 24}{BAYC_SUBJECT[2:]}"

CONTRACT_BY_FIXTURE: Mapping[Task013FixtureId, str] = {
    NFT_721: BAYC,
    NFT_1155: RARIBLE_1155,
    PROXY: AAVE_POOL,
}


def task_013_requests(fixture_id: Task013FixtureId) -> tuple[JsonRpcSourceRequest, ...]:
    """Return the fixed, read-only request set for one TASK-013 candidate."""
    if fixture_id == NFT_721:
        return (
            _receipt("approval_receipt", BAYC_APPROVAL_TX, BAYC_APPROVAL_BLOCK),
            _receipt("transfer_receipt", BAYC_TRANSFER_TX, BAYC_TRANSFER_BLOCK),
            _logs(
                "approval_for_all_logs",
                BAYC,
                BAYC_APPROVAL_BLOCK,
                [APPROVAL_FOR_ALL_TOPIC, PADDED_BAYC_SUBJECT],
            ),
            _logs(
                "approval_logs",
                BAYC,
                BAYC_TRANSFER_BLOCK,
                [APPROVAL_TOPIC, PADDED_BAYC_SUBJECT],
            ),
            _logs(
                "transfer_logs",
                BAYC,
                BAYC_TRANSFER_BLOCK,
                [TRANSFER_TOPIC, PADDED_BAYC_SUBJECT],
            ),
        )
    if fixture_id == NFT_1155:
        return (
            _receipt("single_receipt", RARIBLE_SINGLE_TX, RARIBLE_SINGLE_BLOCK),
            _receipt("batch_receipt", RARIBLE_BATCH_TX, RARIBLE_BATCH_BLOCK),
            _logs(
                "single_logs",
                RARIBLE_1155,
                RARIBLE_SINGLE_BLOCK,
                [TRANSFER_SINGLE_TOPIC],
            ),
            _logs(
                "approval_for_all_logs",
                RARIBLE_1155,
                RARIBLE_SINGLE_BLOCK,
                [APPROVAL_FOR_ALL_TOPIC],
            ),
            _logs(
                "batch_logs",
                RARIBLE_1155,
                RARIBLE_BATCH_BLOCK,
                [TRANSFER_BATCH_TOPIC],
            ),
        )
    if fixture_id == PROXY:
        return (
            _receipt("upgrade_receipt", AAVE_UPGRADE_TX, AAVE_AFTER_BLOCK),
            _logs("upgraded_logs", AAVE_POOL, AAVE_AFTER_BLOCK, [UPGRADED_TOPIC]),
            _storage(
                "implementation_before",
                IMPLEMENTATION_SLOT,
                AAVE_BEFORE_BLOCK,
            ),
            _storage(
                "implementation_after",
                IMPLEMENTATION_SLOT,
                AAVE_AFTER_BLOCK,
            ),
            _storage("admin_before", ADMIN_SLOT, AAVE_BEFORE_BLOCK),
            _storage("admin_after", ADMIN_SLOT, AAVE_AFTER_BLOCK),
        )
    raise ValueError("unsupported TASK-013 fixture")


async def run_task_013_replay(
    *,
    fixture_id: Task013FixtureId,
    role: ProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    """Run one bounded candidate replay through the shared provider guard."""
    if role not in {"primary", "verify"}:
        raise ValueError("TASK-013 replay supports only primary and verify roles")
    contract = CONTRACT_BY_FIXTURE[fixture_id]
    return await run_read_only_probe(
        role=role,
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=task_013_requests(fixture_id),
        summary_decoder=lambda request, raw: _summary(request, raw, contract),
    )


def _receipt(
    capability: str,
    transaction_hash: str,
    block_tag: str,
) -> JsonRpcSourceRequest:
    return JsonRpcSourceRequest(
        capability,
        "eth_getTransactionReceipt",
        [transaction_hash],
        block_tag,
    )


def _logs(
    capability: str,
    address: str,
    block_tag: str,
    topics: list[str],
) -> JsonRpcSourceRequest:
    return JsonRpcSourceRequest(
        capability,
        "eth_getLogs",
        [
            {
                "address": address,
                "fromBlock": block_tag,
                "toBlock": block_tag,
                "topics": topics,
            }
        ],
        block_tag,
    )


def _storage(
    capability: str,
    slot: str,
    block_tag: str,
) -> JsonRpcSourceRequest:
    return JsonRpcSourceRequest(
        capability,
        "eth_getStorageAt",
        [AAVE_POOL, slot, block_tag],
        block_tag,
    )


def _summary(
    request: JsonRpcSourceRequest,
    raw_bytes: bytes,
    contract: str,
) -> object:
    result = json.loads(raw_bytes)["result"]
    if request.method == "eth_getTransactionReceipt":
        receipt = _require_mapping(result)
        selected_logs = [
            _selected_log(item)
            for item in receipt.get("logs", [])
            if isinstance(item, dict) and str(item.get("address", "")).lower() == contract
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
            "selected_logs": selected_logs,
        }
    if request.method == "eth_getLogs":
        if not isinstance(result, list):
            raise ValueError("log result must be an array")
        return {
            "count": len(result),
            "logs": [_selected_log(item) for item in result],
        }
    if request.method == "eth_getStorageAt":
        if not isinstance(result, str) or not result.startswith("0x"):
            raise ValueError("storage result must be hex data")
        return {
            "raw_word": result,
            "decoded_address": f"0x{result[-40:]}" if len(result) >= 42 else None,
        }
    raise ValueError("unsupported TASK-013 capability")


def _selected_log(value: object) -> dict[str, object]:
    return _select(
        _require_mapping(value),
        "address",
        "topics",
        "data",
        "blockNumber",
        "transactionHash",
        "transactionIndex",
        "logIndex",
        "removed",
    )


def _require_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return value


def _select(value: Mapping[str, object], *keys: str) -> dict[str, object]:
    return {key: value[key] for key in keys if key in value}
