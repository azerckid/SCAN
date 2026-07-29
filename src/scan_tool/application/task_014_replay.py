"""Bounded provider replay for TASK-014 PATH fixture candidates."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    ProviderRole,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.domain.source import JsonRpcSourceRequest

SEED_NODE = "0xb66cd966670d962c227b3eaba30a872dbfb995db"
INTERNAL_SOURCE = "0x036cec1a199234fc02f72d29e596a09440825f1c"
MERGE_NODE = "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5"
INTERNAL_TX = "0x298bde3f9e53f7a5d870f7f5d56ee2f5e41fa25e6eb5e74611ac97025405db55"
INTERNAL_VALUE = "88752697459828535340019"

SELECTED_TRANSACTIONS: tuple[tuple[str, str], ...] = (
    ("internal_seed", INTERNAL_TX),
    ("split_a", "0x79c10cf538667a0a7de40ce54d2444c9e9e17b5c62b321e739020df0015baeda"),
    ("split_b", "0xd4c7c88944783f3c39695bc5e6c5fcd8a399c0a103d822ac8bd96fad41a41866"),
    ("split_c", "0x03a06cfb99cf699dd5f61088fdf015e17b8c2f258a17882f6ff4de8607a3e46e"),
    ("split_d", "0x77720ab2ab2bb6550e9b4e1cb4b6c2033c2200ae3abb7ae51f89898f86ac1e2a"),
    ("merge_c", "0xc9641dceab1311d219523e5d3914df31f6a97986d5e331db45387037ea06a07c"),
    ("merge_a", "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d"),
    ("merge_d", "0x9f3edbd1eb404dec2e4d9aae93c739136f79c87f6382af25413ce705cc431f59"),
    ("merge_b", "0x19f802affe24572bac3af47983f42bbec6055117c6a32c3fddc58bd7545e5240"),
    ("external_dust", "0xcfec4f86f6d81c83b9b3520d6966936d17490988739a794bf1391562ecb909b6"),
)


def task_014_requests(role: ProviderRole) -> tuple[JsonRpcSourceRequest, ...]:
    """Return the fixed read-only request set for the selected PATH scope."""
    if role not in {"primary", "verify"}:
        raise ValueError("TASK-014 replay supports primary and verify roles")
    requests: list[JsonRpcSourceRequest] = []
    for label, transaction_hash in SELECTED_TRANSACTIONS:
        requests.extend(
            (
                JsonRpcSourceRequest(
                    f"{label}_transaction",
                    "eth_getTransactionByHash",
                    [transaction_hash],
                ),
                JsonRpcSourceRequest(
                    f"{label}_receipt",
                    "eth_getTransactionReceipt",
                    [transaction_hash],
                ),
            )
        )
    if role == "primary":
        requests.append(
            JsonRpcSourceRequest(
                "internal_seed_trace",
                "debug_traceTransaction",
                [
                    INTERNAL_TX,
                    {
                        "tracer": "callTracer",
                        "tracerConfig": {"onlyTopCall": False},
                    },
                ],
                "0x1009fb6",
            )
        )
    return tuple(requests)


async def run_task_014_replay(
    *,
    role: ProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    """Run the bounded PATH replay through the shared provider security guard."""
    return await run_read_only_probe(
        role=role,
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=task_014_requests(role),
        summary_decoder=_summary,
    )


def _summary(request: JsonRpcSourceRequest, raw_bytes: bytes) -> object:
    result = json.loads(raw_bytes)["result"]
    if request.method == "eth_getTransactionByHash":
        return _select(
            _mapping(result),
            "hash",
            "blockHash",
            "blockNumber",
            "transactionIndex",
            "from",
            "to",
            "value",
        )
    if request.method == "eth_getTransactionReceipt":
        return _select(
            _mapping(result),
            "transactionHash",
            "blockHash",
            "blockNumber",
            "transactionIndex",
            "status",
        )
    if request.method == "debug_traceTransaction":
        matches: list[dict[str, object]] = []
        _collect_internal_edges(_mapping(result), matches, ())
        selected = [
            item
            for item in matches
            if item["from"] == INTERNAL_SOURCE
            and item["to"] == SEED_NODE
            and item["value_raw"] == INTERNAL_VALUE
        ]
        if len(selected) != 1:
            raise ValueError("selected internal PATH edge must occur exactly once")
        return {"selected_internal_edge": selected[0], "matching_edge_count": 1}
    raise ValueError("unsupported TASK-014 capability")


def _collect_internal_edges(
    frame: Mapping[str, object],
    matches: list[dict[str, object]],
    path: tuple[int, ...],
) -> None:
    sender = frame.get("from")
    recipient = frame.get("to")
    value = frame.get("value")
    error = frame.get("error")
    if (
        isinstance(sender, str)
        and isinstance(recipient, str)
        and isinstance(value, str)
        and value.startswith("0x")
        and int(value, 16) > 0
        and not error
    ):
        matches.append(
            {
                "path": list(path),
                "type": str(frame.get("type", "")).lower(),
                "from": sender.lower(),
                "to": recipient.lower(),
                "value_hex": value.lower(),
                "value_raw": str(int(value, 16)),
            }
        )
    children = frame.get("calls", [])
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes)):
        return
    for index, child in enumerate(children):
        if isinstance(child, Mapping):
            _collect_internal_edges(child, matches, (*path, index))


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return value


def _select(value: Mapping[str, object], *keys: str) -> dict[str, object]:
    return {key: value[key] for key in keys if key in value}
