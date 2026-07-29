"""Bounded fixed-block ENS replay for TASK-015 source candidates."""

import json
from pathlib import Path
from typing import Literal

import httpx

from scan_tool.application.provider_smoke import (
    ProviderRole,
    SmokeReport,
    run_read_only_probe,
)
from scan_tool.domain.source import JsonRpcSourceRequest

type Task015EnsFixtureId = Literal[
    "FX-OSINT-LABEL-CONFLICT-001",
    "FX-OSINT-ENS-CONFLICT-001",
]

LABEL_CONFLICT = "FX-OSINT-LABEL-CONFLICT-001"
ENS_CONFLICT = "FX-OSINT-ENS-CONFLICT-001"
FIXTURE_IDS: tuple[Task015EnsFixtureId, ...] = (LABEL_CONFLICT, ENS_CONFLICT)

BLOCK_TAG = "0x1873d4e"
ENS_REGISTRY = "0x00000000000c2e074ec69a0dfb2997ba6c7d2e1e"
PUBLIC_RESOLVER = "0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41"
REVERSE_RESOLVER = "0xa2c122be93b0074270ebee7f6b7292c7deb45047"

TEAM4_NODE = "89658e012376b43a5108744fbe66ad3c8c14d2713bd74e4d9109b3e7a4b496d4"
NICK_NODE = "05a67c0ee82964c4f7394cdd47fee7f4d9503a23c09c38341779ea012afe6e00"
NICK_REVERSE_NODE = "e78fb51f6a12a1a1675dd4dc3cbae52b360fd1b58a4725fd03abff93586071d1"


def task_015_ens_requests(
    fixture_id: Task015EnsFixtureId,
) -> tuple[JsonRpcSourceRequest, ...]:
    """Return the fixed read-only call set for one ENS candidate."""
    if fixture_id == LABEL_CONFLICT:
        return (
            _call("label_resolver", ENS_REGISTRY, f"0x0178b8bf{TEAM4_NODE}"),
            _call("label_address", PUBLIC_RESOLVER, f"0x3b3b57de{TEAM4_NODE}"),
        )
    if fixture_id == ENS_CONFLICT:
        return (
            _call("forward_resolver", ENS_REGISTRY, f"0x0178b8bf{NICK_NODE}"),
            _call("forward_address", PUBLIC_RESOLVER, f"0x3b3b57de{NICK_NODE}"),
            _call(
                "reverse_resolver",
                ENS_REGISTRY,
                f"0x0178b8bf{NICK_REVERSE_NODE}",
            ),
            _call(
                "reverse_name",
                REVERSE_RESOLVER,
                f"0x691f3431{NICK_REVERSE_NODE}",
            ),
        )
    raise ValueError("unsupported TASK-015 ENS fixture")


async def run_task_015_ens_replay(
    *,
    fixture_id: Task015EnsFixtureId,
    role: ProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
    provider_id_override: str | None = None,
) -> SmokeReport:
    """Run one fixed-block ENS replay through the shared provider guard."""
    if role not in {"primary", "verify", "trace"}:
        raise ValueError("TASK-015 ENS replay received an unsupported provider role")
    return await run_read_only_probe(
        role=role,
        endpoint=endpoint,
        output_root=output_root,
        client=client,
        requests=task_015_ens_requests(fixture_id),
        summary_decoder=_summary,
        provider_id_override=provider_id_override,
    )


def _call(capability: str, to: str, data: str) -> JsonRpcSourceRequest:
    return JsonRpcSourceRequest(
        capability,
        "eth_call",
        [{"to": to, "data": data}, BLOCK_TAG],
        BLOCK_TAG,
    )


def _summary(request: JsonRpcSourceRequest, raw_bytes: bytes) -> object:
    result = json.loads(raw_bytes)["result"]
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("ENS eth_call result must be hex")
    if request.capability == "reverse_name":
        return {"name": _decode_string(result)}
    return {"address": _decode_address(result)}


def _decode_address(value: str) -> str:
    body = value[2:]
    if len(body) != 64 or any(character not in "0123456789abcdefABCDEF" for character in body):
        raise ValueError("ENS address result must be one ABI word")
    return f"0x{body[-40:].lower()}"


def _decode_string(value: str) -> str:
    body = bytes.fromhex(value[2:])
    if len(body) < 64:
        raise ValueError("ENS string result is truncated")
    offset = int.from_bytes(body[:32])
    if offset + 32 > len(body):
        raise ValueError("ENS string offset is outside the result")
    length = int.from_bytes(body[offset : offset + 32])
    start = offset + 32
    end = start + length
    if end > len(body):
        raise ValueError("ENS string payload is truncated")
    return body[start:end].decode("utf-8")
