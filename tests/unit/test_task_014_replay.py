import asyncio
import json

import httpx

from scan_tool.application.task_014_replay import (
    INTERNAL_SOURCE,
    INTERNAL_VALUE,
    MERGE_NODE,
    SEED_NODE,
    SELECTED_TRANSACTIONS,
    run_task_014_replay,
    task_014_requests,
)


def test_request_sets_are_bounded_and_read_only() -> None:
    assert len(task_014_requests("primary")) == 21
    assert len(task_014_requests("verify")) == 20
    assert {item.method for item in task_014_requests("primary")} == {
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "debug_traceTransaction",
    }


def test_mock_replay_decodes_transactions_receipts_and_internal_edge(tmp_path) -> None:
    hashes = {transaction_hash for _, transaction_hash in SELECTED_TRANSACTIONS}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]
        params = payload["params"]
        if method == "eth_getTransactionByHash":
            assert params[0] in hashes
            result: object = {
                "hash": params[0],
                "blockHash": "0xblock",
                "blockNumber": "0x1",
                "transactionIndex": "0x2",
                "from": SEED_NODE,
                "to": MERGE_NODE,
                "value": "0x1",
            }
        elif method == "eth_getTransactionReceipt":
            assert params[0] in hashes
            result = {
                "transactionHash": params[0],
                "blockHash": "0xblock",
                "blockNumber": "0x1",
                "transactionIndex": "0x2",
                "status": "0x1",
            }
        elif method == "debug_traceTransaction":
            result = {
                "type": "CALL",
                "from": "0x0000000000000000000000000000000000000001",
                "to": "0x0000000000000000000000000000000000000002",
                "value": "0x0",
                "calls": [
                    {
                        "type": "CALL",
                        "from": INTERNAL_SOURCE,
                        "to": SEED_NODE,
                        "value": hex(int(INTERNAL_VALUE)),
                    }
                ],
            }
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_task_014_replay(
                role="primary",
                endpoint="https://rpc.example/provider-test-secret",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())
    assert report.status == "complete"
    assert report.network_calls == 21
    trace = report.observations[-1].decoded_summary
    assert trace["selected_internal_edge"]["value_raw"] == INTERNAL_VALUE


def test_verify_role_never_requests_trace() -> None:
    assert all(
        request.method != "debug_traceTransaction" for request in task_014_requests("verify")
    )
