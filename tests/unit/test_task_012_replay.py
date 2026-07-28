import asyncio
import json

import httpx

from scan_tool.application.task_012_replay import (
    ROUTER,
    SUBJECT,
    run_task_012_replay,
    task_012_requests,
)


def test_request_set_is_bounded_and_trace_is_primary_only() -> None:
    primary = task_012_requests("primary")
    verify = task_012_requests("verify")

    assert len(primary) == 10
    assert len(verify) == 9
    assert {item.method for item in primary} <= {
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "eth_getBlockByNumber",
        "eth_getCode",
        "eth_getBalance",
        "eth_call",
        "eth_getLogs",
        "debug_traceTransaction",
    }
    assert "debug_traceTransaction" not in {item.method for item in verify}


def test_mock_replay_decodes_state_logs_and_internal_inflow(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]
        params = payload["params"]
        if method == "eth_getTransactionByHash":
            result: object = {"hash": "0xtx", "blockNumber": "0xfdf1d0"}
        elif method == "eth_getTransactionReceipt":
            result = {"status": "0x1", "logs": []}
        elif method == "eth_getBlockByNumber":
            result = {"number": "0xfdf1d0", "hash": "0xblock", "timestamp": "0x1"}
        elif method == "eth_getCode":
            result = "0x" if params[0] == SUBJECT else "0x6000"
        elif method == "eth_getBalance":
            result = "0x2"
        elif method == "eth_call":
            result = "0x6"
        elif method == "eth_getLogs":
            result = [{"address": "0xtoken", "topics": [], "data": "0x0"}]
        elif method == "debug_traceTransaction":
            result = {
                "type": "CALL",
                "from": SUBJECT,
                "to": ROUTER,
                "value": "0x0",
                "calls": [
                    {
                        "type": "CALL",
                        "from": ROUTER,
                        "to": SUBJECT,
                        "value": "0x10",
                    }
                ],
            }
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_task_012_replay(
                role="primary",
                endpoint="https://rpc.example/v2/provider-test-secret",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())
    observations = {item.capability: item for item in report.observations}

    assert report.status == "complete"
    assert report.network_calls == 10
    assert observations["subject_code"].decoded_summary["result_rule"] == "empty"
    assert observations["router_code"].decoded_summary == {
        "result_rule": "non_empty",
        "byte_length": 2,
        "prefix": "0x6000",
    }
    assert observations["subject_outgoing_usdc_logs"].decoded_summary["count"] == 1
    assert observations["trace"].decoded_summary["matching_successful_inflows"] == [
        {
            "path": [0],
            "type": "CALL",
            "from": ROUTER,
            "to": SUBJECT,
            "value_hex": "0x10",
            "value_wei": "16",
            "error": None,
        }
    ]
