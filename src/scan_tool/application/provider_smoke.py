"""Rules-gated read-only capability smoke for EVM providers."""

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

import httpx

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.http import JsonRpcSourceAdapter
from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.source import JsonRpcSourceRequest, SourceFailure

type ProviderRole = Literal["primary", "verify", "trace"]

TASK_012_TX_HASH = "0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5"
TASK_012_BLOCK_HEX = "0xfdf1d0"
TASK_012_USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ROLE_ENDPOINT_ENV: Mapping[ProviderRole, str] = {
    "primary": "SCAN_EVM_PRIMARY_RPC_URL",
    "verify": "SCAN_EVM_VERIFY_RPC_URL",
    "trace": "SCAN_EVM_TRACE_RPC_URL",
}
ROLE_PROVIDER_ID: Mapping[ProviderRole, str] = {
    "primary": "PROVIDER-EVM-PRIMARY",
    "verify": "PROVIDER-EVM-VERIFY",
    "trace": "PROVIDER-EVM-TRACE-VERIFY",
}
READ_ONLY_METHODS = frozenset(
    {
        "eth_chainId",
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "eth_getBlockByNumber",
        "eth_getLogs",
        "eth_call",
        "debug_traceTransaction",
    }
)


@dataclass(frozen=True, slots=True)
class SmokeObservation:
    capability: str
    method: str
    block_tag: str | None
    retrieved_at: str
    duration_ms: int
    outcome: str
    http_status: int | None
    failure_kind: str | None
    raw_sha256: str | None
    artifact_uri: str | None
    decoded_summary: object | None


@dataclass(frozen=True, slots=True)
class SmokeReport:
    status: Literal["complete", "partial", "failed"]
    provider_id: str
    role: ProviderRole
    network_calls: int
    started_at: str
    finished_at: str
    observations: tuple[SmokeObservation, ...]


def smoke_requests(role: ProviderRole) -> tuple[JsonRpcSourceRequest, ...]:
    common = (
        JsonRpcSourceRequest("chain_id", "eth_chainId", []),
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
            "filtered_logs",
            "eth_getLogs",
            [
                {
                    "address": TASK_012_USDC,
                    "fromBlock": TASK_012_BLOCK_HEX,
                    "toBlock": TASK_012_BLOCK_HEX,
                    "topics": [ERC20_TRANSFER_TOPIC],
                }
            ],
            TASK_012_BLOCK_HEX,
        ),
        JsonRpcSourceRequest(
            "historical_call",
            "eth_call",
            [{"to": TASK_012_USDC, "data": "0x313ce567"}, TASK_012_BLOCK_HEX],
            TASK_012_BLOCK_HEX,
        ),
    )
    if role == "verify":
        return common
    trace = JsonRpcSourceRequest(
        "trace",
        "debug_traceTransaction",
        [TASK_012_TX_HASH, {"tracer": "callTracer", "timeout": "20s"}],
        TASK_012_BLOCK_HEX,
    )
    if role == "trace":
        return (common[0], trace)
    return (*common, trace)


def dry_run_plan(role: ProviderRole) -> dict[str, object]:
    requests = smoke_requests(role)
    return {
        "status": "not_executed",
        "provider_id": ROLE_PROVIDER_ID[role],
        "role": role,
        "network_calls": 0,
        "required_endpoint_env": ROLE_ENDPOINT_ENV[role],
        "methods": [request.method for request in requests],
    }


def require_execution_allowed(
    *, execute: bool, rules_status: str, environment: Mapping[str, str], role: ProviderRole
) -> str | None:
    if not execute:
        return None
    if rules_status != "allowed":
        raise PermissionError("live provider smoke requires rules_status=allowed")
    endpoint_name = ROLE_ENDPOINT_ENV[role]
    endpoint = environment.get(endpoint_name)
    if not endpoint:
        raise ValueError(f"live provider smoke requires {endpoint_name}")
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(f"{endpoint_name} must be an absolute HTTPS URL")
    return endpoint


async def run_smoke(
    *,
    role: ProviderRole,
    endpoint: str,
    output_root: Path,
    client: httpx.AsyncClient,
) -> SmokeReport:
    provider_id = ROLE_PROVIDER_ID[role]
    guard = SensitiveDataGuard(_endpoint_secret_candidates(endpoint))
    artifacts = ArtifactStore(output_root, guard=guard)
    adapter = JsonRpcSourceAdapter(
        source_id="DS-EVM-RPC-ARCHIVE",
        provider_id=provider_id,
        endpoint=endpoint,
        client=client,
        timeout=httpx.Timeout(connect=5, read=30, write=5, pool=5),
    )
    started_at = datetime.now(UTC)
    observations: list[SmokeObservation] = []
    for request in smoke_requests(role):
        if request.method not in READ_ONLY_METHODS:
            raise ValueError("smoke request contains a non-read-only method")
        started = monotonic()
        try:
            payload = await adapter.execute(request)
            guard.check_bytes(payload.raw_bytes)
            record = artifacts.write(
                payload.raw_bytes,
                media_type=payload.media_type or "application/json",
                artifact_kind="live_provider_smoke",
                redaction_status="verified_no_configured_secret",
                source_id=adapter.source_id,
                retrieved_at=payload.retrieved_at,
            )
            try:
                decoded_summary = _decoded_summary(request.method, payload.raw_bytes)
            except (KeyError, TypeError, ValueError):
                observations.append(
                    SmokeObservation(
                        capability=request.capability,
                        method=request.method,
                        block_tag=_block_tag(request),
                        retrieved_at=payload.retrieved_at.isoformat(),
                        duration_ms=round((monotonic() - started) * 1000),
                        outcome="failed",
                        http_status=payload.status_code,
                        failure_kind="invalid_response",
                        raw_sha256=payload.raw_sha256,
                        artifact_uri=f"artifact://sha256/{record.sha256}",
                        decoded_summary=None,
                    )
                )
                continue
            observations.append(
                SmokeObservation(
                    capability=request.capability,
                    method=request.method,
                    block_tag=_block_tag(request),
                    retrieved_at=payload.retrieved_at.isoformat(),
                    duration_ms=round((monotonic() - started) * 1000),
                    outcome="success",
                    http_status=payload.status_code,
                    failure_kind=None,
                    raw_sha256=payload.raw_sha256,
                    artifact_uri=f"artifact://sha256/{record.sha256}",
                    decoded_summary=decoded_summary,
                )
            )
        except SourceFailure as error:
            observations.append(
                SmokeObservation(
                    capability=request.capability,
                    method=request.method,
                    block_tag=_block_tag(request),
                    retrieved_at=datetime.now(UTC).isoformat(),
                    duration_ms=round((monotonic() - started) * 1000),
                    outcome="failed",
                    http_status=error.status_code,
                    failure_kind=error.kind.value,
                    raw_sha256=None,
                    artifact_uri=None,
                    decoded_summary=None,
                )
            )
    finished_at = datetime.now(UTC)
    success_count = sum(item.outcome == "success" for item in observations)
    status: Literal["complete", "partial", "failed"]
    if success_count == len(observations):
        status = "complete"
    elif success_count:
        status = "partial"
    else:
        status = "failed"
    return SmokeReport(
        status=status,
        provider_id=provider_id,
        role=role,
        network_calls=len(observations),
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        observations=tuple(observations),
    )


def write_report(report: SmokeReport, output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n").encode()
    SensitiveDataGuard().check_bytes(body)
    destination = output_root / f"{report.provider_id.lower()}-latest.json"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_root,
            prefix=".smoke-report-",
            delete=False,
        ) as temporary:
            temporary.write(body)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination


def _endpoint_secret_candidates(endpoint: str) -> Sequence[str]:
    parts = urlsplit(endpoint)
    candidates = [value for _, value in parse_qsl(parts.query) if value]
    candidates.extend(
        segment
        for segment in parts.path.split("/")
        if len(segment) >= 16 and segment not in {"debug_traceTransaction"}
    )
    return tuple(candidates)


def _block_tag(request: JsonRpcSourceRequest) -> str | None:
    if request.block_tag is None:
        return None
    return str(request.block_tag)


def _decoded_summary(method: str, raw_bytes: bytes) -> object:
    body = json.loads(raw_bytes)
    result = body["result"]
    if method in {"eth_chainId", "eth_call"}:
        return {"result": result}
    if method == "eth_getTransactionByHash":
        return _select(result, "hash", "blockNumber", "from", "to", "value")
    if method == "eth_getTransactionReceipt":
        summary = _select(result, "transactionHash", "blockNumber", "status")
        summary["log_count"] = len(result.get("logs", []))
        return summary
    if method == "eth_getBlockByNumber":
        return _select(result, "number", "hash", "timestamp")
    if method == "eth_getLogs":
        return {
            "count": len(result),
            "logs": [
                _select(item, "address", "transactionHash", "logIndex", "topics")
                for item in result[:5]
            ],
        }
    if method == "debug_traceTransaction":
        return _select(result, "type", "from", "to", "value", "error")
    raise ValueError("unsupported smoke method")


def _select(value: object, *keys: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return {key: value[key] for key in keys if key in value}
