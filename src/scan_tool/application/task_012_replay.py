"""Bounded provider replay for the four TASK-012 EVM candidate fixtures."""

import json
from collections.abc import Sequence
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    ERC20_TRANSFER_TOPIC,
    TASK_012_BLOCK_HEX,
    TASK_012_TX_HASH,
    TASK_012_USDC,
    ProviderRole,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.domain.source import JsonRpcSourceRequest

SUBJECT = "0xa406bc6e319cbe7ab2822cc55fa8376e9c3a7fdf"
ROUTER = "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b"
PADDED_SUBJECT = f"0x{'0' * 24}{SUBJECT[2:]}"
BALANCE_OF_SUBJECT = f"0x70a08231{'0' * 24}{SUBJECT[2:]}"


def task_012_requests(role: ProviderRole) -> tuple[JsonRpcSourceRequest, ...]:
    """Return the fixed request set needed for TASK-012 candidate replay."""
    common = (
        JsonRpcSourceRequest(
            "transaction",
            "eth_getTransactionByHash",
            [TASK_012_TX_HASH],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "receipt",
            "eth_getTransactionReceipt",
            [TASK_012_TX_HASH],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "block",
            "eth_getBlockByNumber",
            [TASK_012_BLOCK_HEX, False],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "subject_code",
            "eth_getCode",
            [SUBJECT, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "router_code",
            "eth_getCode",
            [ROUTER, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "native_balance",
            "eth_getBalance",
            [SUBJECT, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "usdc_balance",
            "eth_call",
            [{"to": TASK_012_USDC, "data": BALANCE_OF_SUBJECT}, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "usdc_decimals",
            "eth_call",
            [{"to": TASK_012_USDC, "data": "0x313ce567"}, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "subject_outgoing_usdc_logs",
            "eth_getLogs",
            [
                {
                    "address": TASK_012_USDC,
                    "fromBlock": TASK_012_BLOCK_HEX,
                    "toBlock": TASK_012_BLOCK_HEX,
                    "topics": [ERC20_TRANSFER_TOPIC, PADDED_SUBJECT],
                }
            ],
            TASK_012_BLOCK_HEX,
        ),
    )
    if role != "primary":
        return common
    return (
        *common,
        JsonRpcSourceRequest(
            "trace",
            "debug_traceTransaction",
            [TASK_012_TX_HASH, {"tracer": "callTracer", "timeout": "20s"}],
            TASK_012_BLOCK_HEX,
        ),
    )


async def run_task_012_replay(
    *,
    role: ProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    if role not in {"primary", "verify"}:
        raise ValueError("TASK-012 replay supports only primary and verify roles")
    return await run_read_only_probe(
        role=role,
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=task_012_requests(role),
        summary_decoder=_summary,
    )


def _summary(request: JsonRpcSourceRequest, raw_bytes: bytes) -> object:
    result = json.loads(raw_bytes)["result"]
    if request.capability == "transaction":
        return _select(
            result,
            "hash",
            "blockHash",
            "blockNumber",
            "from",
            "to",
            "value",
            "nonce",
            "transactionIndex",
        )
    if request.capability == "receipt":
        summary = _select(
            result,
            "transactionHash",
            "blockHash",
            "blockNumber",
            "status",
            "gasUsed",
            "effectiveGasPrice",
        )
        summary["selected_logs"] = [
            _select(item, "address", "topics", "data", "logIndex", "transactionIndex")
            for item in result.get("logs", [])
        ]
        return summary
    if request.capability == "block":
        return _select(result, "number", "hash", "timestamp")
    if request.capability in {"subject_code", "router_code"}:
        if not isinstance(result, str):
            raise ValueError("code result must be hex data")
        byte_length = 0 if result == "0x" else (len(result) - 2) // 2
        return {
            "result_rule": "empty" if result == "0x" else "non_empty",
            "byte_length": byte_length,
            "prefix": result[:22],
        }
    if request.capability in {"native_balance", "usdc_balance", "usdc_decimals"}:
        if not isinstance(result, str):
            raise ValueError("state result must be hex data")
        return {
            "result": result,
            "decoded_integer": int(result, 16) if result != "0x" else 0,
        }
    if request.capability == "subject_outgoing_usdc_logs":
        if not isinstance(result, list):
            raise ValueError("log result must be an array")
        return {
            "count": len(result),
            "logs": [
                _select(
                    item,
                    "address",
                    "topics",
                    "data",
                    "blockNumber",
                    "transactionHash",
                    "transactionIndex",
                    "logIndex",
                    "removed",
                )
                for item in result
            ],
        }
    if request.capability == "trace":
        if not isinstance(result, dict):
            raise ValueError("trace result must be an object")
        matches: list[dict[str, object]] = []
        _collect_inflows(result, matches, ())
        return {
            "root": _select(result, "type", "from", "to", "value", "error"),
            "matching_successful_inflows": matches,
        }
    raise ValueError(f"unsupported TASK-012 capability: {request.capability}")


def _collect_inflows(
    call: dict[str, object],
    matches: list[dict[str, object]],
    path: tuple[int, ...],
) -> None:
    to = str(call.get("to", "")).lower()
    value = str(call.get("value", "0x0"))
    if to == SUBJECT and value not in {"0x0", "0x"} and not call.get("error"):
        matches.append(
            {
                "path": list(path),
                "type": call.get("type"),
                "from": call.get("from"),
                "to": call.get("to"),
                "value_hex": value,
                "value_wei": str(int(value, 16)),
                "error": call.get("error"),
            }
        )
    children = call.get("calls", [])
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes)):
        return
    for index, child in enumerate(children):
        if isinstance(child, dict):
            _collect_inflows(child, matches, (*path, index))


def _select(value: object, *keys: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return {key: value[key] for key in keys if key in value}
