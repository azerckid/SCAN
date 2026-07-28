"""Independent trace replay profiles for the TASK-012 native inflow fixture."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import httpx

from scan_tool.application.provider_smoke import (
    TASK_012_BLOCK_HEX,
    TASK_012_TX_HASH,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.application.task_012_replay import SUBJECT
from scan_tool.domain.source import JsonRpcSourceRequest

type TraceDialect = Literal["debug_call_tracer", "parity_trace_transaction"]


def trace_request(dialect: TraceDialect) -> JsonRpcSourceRequest:
    """Build one bounded read-only trace request for the selected provider dialect."""
    if dialect == "debug_call_tracer":
        return JsonRpcSourceRequest(
            "trace",
            "debug_traceTransaction",
            [
                TASK_012_TX_HASH,
                {
                    "tracer": "callTracer",
                    "tracerConfig": {"onlyTopCall": False},
                },
            ],
            TASK_012_BLOCK_HEX,
        )
    if dialect == "parity_trace_transaction":
        return JsonRpcSourceRequest(
            "trace",
            "trace_transaction",
            [TASK_012_TX_HASH],
            TASK_012_BLOCK_HEX,
        )
    raise ValueError(f"unsupported trace dialect: {dialect}")


def dry_run_trace_plan(dialect: TraceDialect) -> dict[str, object]:
    """Describe the planned request without reading an endpoint or making a call."""
    request = trace_request(dialect)
    return {
        "status": "not_executed",
        "provider_id": "PROVIDER-EVM-TRACE-VERIFY",
        "role": "trace",
        "dialect": dialect,
        "network_calls": 0,
        "required_endpoint_env": "SCAN_EVM_TRACE_RPC_URL",
        "method": request.method,
    }


async def run_task_012_trace_replay(
    *,
    dialect: TraceDialect,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    """Replay and normalize one independent trace without provider-specific claims."""
    return await run_read_only_probe(
        role="trace",
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=(trace_request(dialect),),
        summary_decoder=lambda _request, raw: decode_trace_summary(dialect, raw),
    )


def decode_trace_summary(dialect: TraceDialect, raw_bytes: bytes) -> dict[str, object]:
    """Normalize Geth callTracer and Parity trace arrays to the same inflow evidence."""
    body = json.loads(raw_bytes)
    result = body["result"]
    if dialect == "debug_call_tracer":
        root = _unwrap_debug_result(result)
        matches: list[dict[str, object]] = []
        _collect_debug_inflows(root, matches, ())
        return {
            "dialect": dialect,
            "root": _select(root, "type", "from", "to", "value", "error"),
            "matching_successful_inflows": matches,
        }
    if dialect == "parity_trace_transaction":
        if not isinstance(result, list):
            raise ValueError("trace_transaction result must be an array")
        matches = []
        for item in result:
            if not isinstance(item, Mapping):
                raise ValueError("trace_transaction entry must be an object")
            action = item.get("action")
            if not isinstance(action, Mapping):
                continue
            _append_inflow(
                matches,
                path=item.get("traceAddress", []),
                call_type=action.get("callType", item.get("type")),
                sender=action.get("from"),
                recipient=action.get("to"),
                value=action.get("value"),
                error=item.get("error"),
            )
        return {
            "dialect": dialect,
            "root": None,
            "matching_successful_inflows": matches,
        }
    raise ValueError(f"unsupported trace dialect: {dialect}")


def _unwrap_debug_result(result: object) -> Mapping[str, object]:
    if isinstance(result, Mapping):
        return result
    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], Mapping):
        value = result[0].get("value")
        if isinstance(value, Mapping):
            return value
    raise ValueError("debug trace result must be a call frame")


def _collect_debug_inflows(
    call: Mapping[str, object],
    matches: list[dict[str, object]],
    path: tuple[int, ...],
) -> None:
    _append_inflow(
        matches,
        path=path,
        call_type=call.get("type"),
        sender=call.get("from"),
        recipient=call.get("to"),
        value=call.get("value"),
        error=call.get("error"),
    )
    children = call.get("calls", [])
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes)):
        return
    for index, child in enumerate(children):
        if isinstance(child, Mapping):
            _collect_debug_inflows(child, matches, (*path, index))


def _append_inflow(
    matches: list[dict[str, object]],
    *,
    path: object,
    call_type: object,
    sender: object,
    recipient: object,
    value: object,
    error: object,
) -> None:
    if not isinstance(recipient, str) or recipient.lower() != SUBJECT:
        return
    if not isinstance(value, str) or value in {"0x", "0x0", "0x00"} or error:
        return
    value_wei = int(value, 16)
    if value_wei == 0:
        return
    matches.append(
        {
            "path": list(path) if isinstance(path, Sequence) else [],
            "type": call_type.lower() if isinstance(call_type, str) else call_type,
            "from": sender,
            "to": recipient,
            "value_hex": value,
            "value_wei": str(value_wei),
            "error": error,
        }
    )


def _select(value: Mapping[str, object], *keys: str) -> dict[str, object]:
    return {key: value[key] for key in keys if key in value}
