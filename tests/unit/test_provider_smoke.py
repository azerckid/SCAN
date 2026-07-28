import asyncio
import json

import httpx
import pytest

from scan_tool.application.provider_smoke import (
    READ_ONLY_METHODS,
    TASK_012_TX_HASH,
    dry_run_plan,
    require_execution_allowed,
    run_smoke,
    smoke_requests,
    write_report,
)
from scan_tool.application.security import SensitiveDataError


def test_dry_run_is_network_free_and_lists_only_read_methods() -> None:
    plan = dry_run_plan("primary")

    assert plan["status"] == "not_executed"
    assert plan["network_calls"] == 0
    assert set(plan["methods"]) <= READ_ONLY_METHODS
    assert "debug_traceTransaction" in plan["methods"]


def test_execute_requires_allowed_rules_before_endpoint() -> None:
    with pytest.raises(PermissionError, match="rules_status=allowed"):
        require_execution_allowed(
            execute=True,
            rules_status="unclear",
            environment={},
            role="primary",
        )


def test_execute_requires_role_endpoint_and_https() -> None:
    with pytest.raises(ValueError, match="SCAN_EVM_VERIFY_RPC_URL"):
        require_execution_allowed(
            execute=True,
            rules_status="allowed",
            environment={},
            role="verify",
        )
    with pytest.raises(ValueError, match="absolute HTTPS"):
        require_execution_allowed(
            execute=True,
            rules_status="allowed",
            environment={"SCAN_EVM_VERIFY_RPC_URL": "http://rpc.example"},
            role="verify",
        )


def test_verify_role_does_not_request_trace() -> None:
    methods = {request.method for request in smoke_requests("verify")}

    assert "debug_traceTransaction" not in methods
    assert methods == READ_ONLY_METHODS - {"debug_traceTransaction"}


def test_mock_smoke_writes_hashed_artifacts_and_redacted_report(tmp_path) -> None:
    secret = "provider-secret-canary-1234"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(secret)
        payload = json.loads(request.content)
        method = payload["method"]
        if method == "eth_chainId":
            result: object = "0x1"
        elif method == "eth_getTransactionByHash":
            result = {
                "hash": TASK_012_TX_HASH,
                "blockNumber": "0xfdf1d0",
                "from": "0xfrom",
                "to": "0xto",
                "value": "0x0",
            }
        elif method == "eth_getTransactionReceipt":
            result = {
                "transactionHash": TASK_012_TX_HASH,
                "blockNumber": "0xfdf1d0",
                "status": "0x1",
                "logs": [],
            }
        elif method == "eth_getBlockByNumber":
            result = {"number": "0xfdf1d0", "hash": "0xblock", "timestamp": "0x1"}
        elif method == "eth_getLogs":
            result = []
        elif method == "eth_call":
            result = "0x6"
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_smoke(
                role="verify",
                endpoint=f"https://rpc.example/v2/{secret}",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())
    path = write_report(report, tmp_path)
    report_body = path.read_text()

    assert report.status == "complete"
    assert report.network_calls == 6
    assert all(item.raw_sha256 for item in report.observations)
    assert all(item.artifact_uri for item in report.observations)
    assert secret not in report_body
    assert "rpc.example" not in report_body
    assert len([item for item in (tmp_path / "artifacts").rglob("*") if item.is_file()]) == 6


def test_malformed_result_is_recorded_without_crashing(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        result: object = "0x1" if payload["method"] == "eth_chainId" else None
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_smoke(
                role="trace",
                endpoint="https://rpc.example/v2/provider-test-secret",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())

    assert report.status == "partial"
    assert report.observations[1].failure_kind == "invalid_response"
    assert report.observations[1].raw_sha256


def test_provider_echoing_endpoint_secret_is_blocked_before_artifact_write(tmp_path) -> None:
    secret = "provider-secret-canary-5678"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": secret})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_smoke(
                role="trace",
                endpoint=f"https://rpc.example/v2/{secret}",
                output_root=tmp_path,
                client=client,
            )

    with pytest.raises(SensitiveDataError, match="forbidden value"):
        asyncio.run(execute())
    assert not (tmp_path / "artifacts").exists()
