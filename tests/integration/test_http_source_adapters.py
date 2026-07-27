"""HTTPX source adapter tests using only MockTransport."""

import asyncio

import httpx

from scan_tool.adapters.http import JsonRpcSourceAdapter, RestSourceAdapter
from scan_tool.application.source_orchestration import RetryPolicy, SourceOrchestrator
from scan_tool.domain.analysis_request import SourcePolicy
from scan_tool.domain.source import (
    JsonRpcSourceRequest,
    RestSourceRequest,
    SourceFailure,
    SourceFailureKind,
)

TIMEOUT = httpx.Timeout(connect=5, read=20, write=5, pool=5)


def test_json_rpc_adapter_returns_raw_payload_without_endpoint_secret() -> None:
    canary = "SCAN_SECRET_CANARY"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == canary
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": canary})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = JsonRpcSourceAdapter(
                source_id="DS-EVM-RPC-PUBLIC",
                provider_id="mock-rpc",
                endpoint=f"https://rpc.example/?api_key={canary}",
                client=client,
                timeout=TIMEOUT,
            )
            return await adapter.execute(
                JsonRpcSourceRequest(
                    capability="chain_id",
                    method="eth_chainId",
                    params=[],
                )
            )

    result = asyncio.run(execute())

    assert result.status_code == 200
    assert result.endpoint_host == "rpc.example"
    assert result.endpoint_path == "/"
    assert canary not in repr(result)


def test_http_503_retries_through_orchestration_then_succeeds() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, content=b"temporary")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x1"})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = JsonRpcSourceAdapter(
                source_id="DS-EVM-RPC-PUBLIC",
                provider_id="mock-rpc",
                endpoint="https://rpc.example/",
                client=client,
                timeout=TIMEOUT,
            )
            orchestrator = SourceOrchestrator(
                [adapter],
                retry_policy=RetryPolicy(jitter_ratio=0),
                sleep=_no_sleep,
            )
            policy = SourcePolicy.model_validate(
                {
                    "rule_status": "allowed",
                    "allowed_source_ids": ["DS-EVM-RPC-PUBLIC"],
                    "source_order": ["DS-EVM-RPC-PUBLIC"],
                    "allow_fallback": False,
                    "offline_mode": False,
                }
            )
            return await orchestrator.execute(
                JsonRpcSourceRequest(
                    capability="chain_id",
                    method="eth_chainId",
                    params=[],
                ),
                policy,
            )

    execution = asyncio.run(execute())

    assert execution.succeeded
    assert call_count == 2
    assert len(execution.attempts) == 2
    assert execution.attempts[0].failure_kind is SourceFailureKind.TRANSIENT
    assert execution.attempts[0].wait_seconds == 0.5


def test_rest_adapter_keeps_safe_path_and_does_not_record_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["address"] == "0xabc"
        assert request.headers["Authorization"] == "Bearer SCAN_SECRET_CANARY"
        return httpx.Response(200, content=b'{"items":[]}')

    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={"Authorization": "Bearer SCAN_SECRET_CANARY"},
        ) as client:
            adapter = RestSourceAdapter(
                source_id="DS-EXPLORER-EVM",
                provider_id="mock-explorer",
                base_url="https://explorer.example/api/",
                client=client,
                timeout=TIMEOUT,
            )
            return await adapter.execute(
                RestSourceRequest(
                    capability="address_transactions",
                    method="GET",
                    path="/v1/transactions",
                    params={"address": "0xabc"},
                )
            )

    result = asyncio.run(execute())

    assert result.endpoint_host == "explorer.example"
    assert result.endpoint_path == "/v1/transactions"
    assert "address" not in result.endpoint_path
    assert "SCAN_SECRET_CANARY" not in repr(result)


def test_http_429_is_a_safe_retryable_failure() -> None:
    canary = "SCAN_SECRET_CANARY"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            content=canary.encode(),
            headers={"Retry-After": "3"},
        )

    async def execute() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = RestSourceAdapter(
                source_id="DS-EXPLORER-EVM",
                provider_id="mock-explorer",
                base_url=f"https://explorer.example/?api_key={canary}",
                client=client,
                timeout=TIMEOUT,
            )
            try:
                await adapter.execute(
                    RestSourceRequest(
                        capability="transaction",
                        method="GET",
                        path="/v1/transaction",
                    )
                )
            except SourceFailure as error:
                assert error.kind is SourceFailureKind.RATE_LIMITED
                assert error.status_code == 429
                assert error.retry_after == "3"
                assert canary not in str(error)
                assert canary not in repr(error)
            else:
                raise AssertionError("429 must raise SourceFailure")

    asyncio.run(execute())


def test_http_501_is_permanent_not_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(501, content=b"not implemented")

    async def execute() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = RestSourceAdapter(
                source_id="DS-EXPLORER-EVM",
                provider_id="mock-explorer",
                base_url="https://explorer.example/",
                client=client,
                timeout=TIMEOUT,
            )
            try:
                await adapter.execute(
                    RestSourceRequest(
                        capability="transaction",
                        method="GET",
                        path="/v1/transaction",
                    )
                )
            except SourceFailure as error:
                assert error.kind is SourceFailureKind.PERMANENT
            else:
                raise AssertionError("501 must be a permanent failure")

    asyncio.run(execute())


def test_http_timeout_does_not_include_raw_url() -> None:
    canary = "SCAN_SECRET_CANARY"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider leaked its URL", request=request)

    async def execute() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = JsonRpcSourceAdapter(
                source_id="DS-EVM-RPC-PUBLIC",
                provider_id="mock-rpc",
                endpoint=f"https://rpc.example/{canary}",
                client=client,
                timeout=TIMEOUT,
            )
            try:
                await adapter.execute(
                    JsonRpcSourceRequest(
                        capability="chain_id",
                        method="eth_chainId",
                        params=[],
                    )
                )
            except SourceFailure as error:
                assert error.kind is SourceFailureKind.TIMEOUT
                assert canary not in str(error)
                assert canary not in repr(error)
            else:
                raise AssertionError("timeout must raise SourceFailure")

    asyncio.run(execute())


def test_rest_path_rejects_query_and_fragment() -> None:
    for path in ("relative", "/v1/items?api_key=secret", "/v1/items#fragment"):
        try:
            RestSourceRequest(
                capability="context",
                method="GET",
                path=path,
            )
        except ValueError:
            continue
        raise AssertionError(f"unsafe REST path was accepted: {path}")


async def _no_sleep(seconds: float) -> None:
    return None
