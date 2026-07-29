import asyncio
import json

import httpx
import pytest

from scan_tool.application.task_013_replay import (
    AAVE_POOL,
    BAYC,
    FIXTURE_IDS,
    NFT_721,
    NFT_1155,
    PROXY,
    RARIBLE_1155,
    run_task_013_replay,
    task_013_requests,
)


def test_request_sets_are_bounded_and_read_only() -> None:
    allowed = {"eth_getTransactionReceipt", "eth_getLogs", "eth_getStorageAt"}
    assert [len(task_013_requests(item)) for item in FIXTURE_IDS] == [5, 5, 6]
    for fixture_id in FIXTURE_IDS:
        assert {item.method for item in task_013_requests(fixture_id)} <= allowed


def test_nft_inputs_use_exact_block_windows() -> None:
    for fixture_id in (NFT_721, NFT_1155):
        log_requests = [
            item for item in task_013_requests(fixture_id) if item.method == "eth_getLogs"
        ]
        assert log_requests
        for request in log_requests:
            query = request.params[0]
            assert query["fromBlock"] == query["toBlock"] == request.block_tag
            assert query["address"] in {BAYC, RARIBLE_1155}
            assert query["topics"]


def test_proxy_requests_pin_historical_blocks() -> None:
    storage = [item for item in task_013_requests(PROXY) if item.method == "eth_getStorageAt"]
    assert len(storage) == 4
    assert all(item.params[0] == AAVE_POOL for item in storage)
    assert all(item.params[2] == item.block_tag for item in storage)


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_mock_replay_decodes_receipts_logs_and_storage(tmp_path, fixture_id) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]
        params = payload["params"]
        if method == "eth_getTransactionReceipt":
            contract = {
                NFT_721: BAYC,
                NFT_1155: RARIBLE_1155,
                PROXY: AAVE_POOL,
            }[fixture_id]
            result: object = {
                "transactionHash": params[0],
                "blockNumber": "0x1",
                "status": "0x1",
                "logs": [
                    {
                        "address": contract,
                        "topics": ["0xtopic"],
                        "data": "0x",
                        "logIndex": "0x1",
                    },
                    {
                        "address": "0x0000000000000000000000000000000000000001",
                        "topics": ["0xother"],
                        "data": "0x",
                        "logIndex": "0x2",
                    },
                ],
            }
        elif method == "eth_getLogs":
            result = [
                {
                    "address": params[0]["address"],
                    "topics": params[0]["topics"],
                    "data": "0x",
                    "blockNumber": params[0]["fromBlock"],
                    "transactionHash": "0xtx",
                    "transactionIndex": "0x1",
                    "logIndex": "0x2",
                    "removed": False,
                }
            ]
        elif method == "eth_getStorageAt":
            result = "0x" + ("0" * 24) + "1234567890abcdef1234567890abcdef12345678"
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_task_013_replay(
                fixture_id=fixture_id,
                role="primary",
                endpoint="https://rpc.example/v2/provider-test-secret",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())
    assert report.status == "complete"
    for observation in report.observations:
        assert observation.outcome == "success"
        if "receipt" in observation.capability:
            assert len(observation.decoded_summary["selected_logs"]) == 1
        if observation.method == "eth_getStorageAt":
            assert (
                observation.decoded_summary["decoded_address"]
                == "0x1234567890abcdef1234567890abcdef12345678"
            )
