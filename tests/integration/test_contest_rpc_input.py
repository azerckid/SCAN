"""Contest RPC injection and RPC/artifact normalization equivalence."""

import asyncio
import json

import httpx
import pytest

from scan_tool.adapters.input_source import (
    ContestRpcSourceAdapter,
    ProvidedArtifactImporter,
    normalize_json_rpc_payload,
)
from scan_tool.domain.input_source import ArtifactFormat, ChainScope, InputMode
from scan_tool.domain.source import JsonRpcSourceRequest, SourceFailure, SourceFailureKind

TIMEOUT = httpx.Timeout(connect=5, read=20, write=5, pool=5)


def test_contest_rpc_uses_only_the_explicit_endpoint_and_normalizes() -> None:
    called_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_hosts.append(request.url.host)
        assert request.url.path == "/rpc"
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"number": "0x10"}},
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ContestRpcSourceAdapter(
                endpoint="https://contest-rpc.example/rpc",
                client=client,
                timeout=TIMEOUT,
            )
            request = JsonRpcSourceRequest("block", "eth_getBlockByNumber", ["0x10", False])
            payload = await adapter.execute(request)
            return adapter.normalize(request, payload)

    bundle = asyncio.run(execute())

    assert called_hosts == ["contest-rpc.example"]
    assert bundle.input_mode is InputMode.CONTEST_RPC
    assert bundle.chain_scope is ChainScope.EVM
    assert bundle.records[0].data == {"number": "0x10"}
    assert "contest-rpc.example" not in repr(bundle)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://contest-rpc.example/rpc",
        "https://user:password@contest-rpc.example/rpc",
        "relative",
    ],
)
def test_contest_rpc_requires_safe_https_endpoint(endpoint: str) -> None:
    async def construct() -> None:
        async with httpx.AsyncClient() as client:
            ContestRpcSourceAdapter(
                endpoint=endpoint,
                client=client,
                timeout=TIMEOUT,
            )

    with pytest.raises(ValueError):
        asyncio.run(construct())


@pytest.mark.parametrize(
    "method",
    [
        "eth_sendRawTransaction",
        "eth_sendTransaction",
        "eth_sign",
        "personal_sign",
        "wallet_addEthereumChain",
        "debug_setHead",
        "evm_mine",
    ],
)
def test_contest_rpc_rejects_mutating_or_signing_methods_before_network(
    method: str,
) -> None:
    network_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": True})

    async def execute() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ContestRpcSourceAdapter(
                endpoint="https://contest-rpc.example/rpc",
                client=client,
                timeout=TIMEOUT,
            )
            with pytest.raises(SourceFailure) as captured:
                await adapter.execute(JsonRpcSourceRequest("forbidden", method, []))
            assert captured.value.kind is SourceFailureKind.PERMANENT
            assert str(captured.value) == "contest RPC method is not allowed"

    asyncio.run(execute())
    assert network_calls == 0


def test_all_three_input_modes_share_normalized_record_data() -> None:
    result = {"number": "0x10", "hash": "0xabc"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute_rpc():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ContestRpcSourceAdapter(
                endpoint="https://contest-rpc.example/rpc",
                client=client,
                timeout=TIMEOUT,
            )
            request = JsonRpcSourceRequest("block", "eth_getBlockByNumber", ["0x10", False])
            payload = await adapter.execute(request)
            return request, payload, adapter.normalize(request, payload)

    request, payload, contest_bundle = asyncio.run(execute_rpc())
    external_bundle = normalize_json_rpc_payload(
        request=request,
        payload=payload,
        input_mode=InputMode.EXTERNAL_RPC,
        chain_scope=ChainScope.EVM,
        source_id="DS-EVM-RPC-PUBLIC",
        provider_id="external-rpc",
    )
    artifact_bundle = ProvidedArtifactImporter().import_bytes(
        json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode(),
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.EVM,
        record_type="block",
    )

    records = (
        external_bundle.records[0],
        contest_bundle.records[0],
        artifact_bundle.records[0],
    )
    assert {record.record_type for record in records} == {"block"}
    assert all(record.data == result for record in records)
    assert len({record.record_sha256 for record in records}) == 1
