import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from scan_tool.application.task_016_bridge_replay import (
    CHAINS,
    DESTINATION_BLOCK,
    DESTINATION_EVENT_TOPIC,
    DESTINATION_SPOKE_POOL,
    DESTINATION_TX,
    EXPECTED_DEPOSIT_ID,
    SOURCE_BLOCK,
    SOURCE_EVENT_TOPIC,
    SOURCE_SPOKE_POOL,
    SOURCE_TX,
    assert_matching_provider_facts,
    bridge_pair_facts,
    bridge_requests,
    resolve_bridge_endpoints,
    run_task_016_bridge_replay,
)


def _word(value: int | str) -> str:
    if isinstance(value, str):
        value = int(value.removeprefix("0x"), 16)
    return f"{value:064x}"


def _address(value: str) -> str:
    return ("0" * 24) + value.removeprefix("0x").lower()


DEPOSITOR = "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae"
RECIPIENT = "0xdd8591007149631190f1013ac1067305f191cd0a"
SOURCE_ROUTER = DEPOSITOR
BASE_WETH = "0x4200000000000000000000000000000000000006"
ETH_WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
INPUT = 330000000000000000
OUTPUT = 329132286989970407


def _event(chain: str) -> dict[str, object]:
    if chain == "base":
        static = [
            _address(BASE_WETH),
            _address("0x0000000000000000000000000000000000000000"),
            _word(INPUT),
            _word(OUTPUT),
            _word(1730613371),
            _word(4294967295),
            _word(0),
            _address(RECIPIENT),
            _address("0x0000000000000000000000000000000000000000"),
            _word(320),
            _word(0),
        ]
        topics = [
            SOURCE_EVENT_TOPIC,
            f"0x{_word(1)}",
            f"0x{_word(EXPECTED_DEPOSIT_ID)}",
            f"0x{_address(DEPOSITOR)}",
        ]
    else:
        static = [
            _address(BASE_WETH),
            _address(ETH_WETH),
            _word(INPUT),
            _word(OUTPUT),
            _word(8453),
            _word(4294967295),
            _word(0),
            _address("0x0000000000000000000000000000000000000000"),
            _address(DEPOSITOR),
            _address(RECIPIENT),
            _word(384),
            _word(416),
            _word(0),
            _word(0),
        ]
        topics = [
            DESTINATION_EVENT_TOPIC,
            f"0x{_word(8453)}",
            f"0x{_word(EXPECTED_DEPOSIT_ID)}",
            f"0x{_address('0x18105a39db36eb6f865704be858bcc7954c66467')}",
        ]
    return {
        "address": SOURCE_SPOKE_POOL if chain == "base" else DESTINATION_SPOKE_POOL,
        "topics": topics,
        "data": f"0x{''.join(static)}",
        "transactionHash": SOURCE_TX if chain == "base" else DESTINATION_TX,
        "logIndex": "0x1",
    }


def _handler(chain: str):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]
        params = payload["params"]
        block = SOURCE_BLOCK if chain == "base" else DESTINATION_BLOCK
        spoke_pool = SOURCE_SPOKE_POOL if chain == "base" else DESTINATION_SPOKE_POOL
        if method == "eth_getTransactionByHash":
            result: object = {
                "hash": params[0],
                "blockHash": "0xblock",
                "blockNumber": block,
                "from": DEPOSITOR,
                "to": SOURCE_ROUTER if chain == "base" else spoke_pool,
                "value": "0x0",
            }
        elif method == "eth_getTransactionReceipt":
            result = {
                "transactionHash": params[0],
                "blockHash": "0xblock",
                "blockNumber": block,
                "status": "0x1",
                "transactionIndex": "0x1",
                "logs": [_event(chain)],
            }
        elif method == "eth_getBlockByNumber":
            result = {"number": block, "hash": "0xblock", "timestamp": "0x1"}
        elif method == "eth_getLogs":
            result = [_event(chain)]
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    return handler


def test_request_sets_are_bounded_exact_block_and_read_only() -> None:
    allowed = {
        "eth_getTransactionByHash",
        "eth_getTransactionReceipt",
        "eth_getBlockByNumber",
        "eth_getLogs",
    }
    for chain in CHAINS:
        requests = bridge_requests(chain)
        assert len(requests) == 4
        assert {request.method for request in requests} == allowed
        log_query = requests[-1].params[0]
        assert log_query["fromBlock"] == log_query["toBlock"] == requests[-1].block_tag


def test_live_endpoint_gate_requires_rules_and_both_chains() -> None:
    with pytest.raises(PermissionError, match="rules_status=allowed"):
        resolve_bridge_endpoints(
            execute=True,
            rules_status="unclear",
            role="primary",
            environment={},
        )
    with pytest.raises(ValueError, match="SCAN_BASE_PRIMARY_RPC_URL"):
        resolve_bridge_endpoints(
            execute=True,
            rules_status="allowed",
            role="primary",
            environment={"SCAN_EVM_PRIMARY_RPC_URL": "https://eth.example/key"},
        )
    assert resolve_bridge_endpoints(
        execute=True,
        rules_status="allowed",
        role="verify",
        environment={
            "SCAN_BASE_VERIFY_RPC_URL": "https://base.example/key",
            "SCAN_EVM_VERIFY_RPC_URL": "https://eth.example/key",
        },
    ) == {
        "base": "https://base.example/key",
        "ethereum": "https://eth.example/key",
    }


def test_mock_replay_matches_two_chain_facts(tmp_path) -> None:
    async def execute():
        reports = {}
        for chain in CHAINS:
            async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(chain))) as client:
                reports[chain] = await run_task_016_bridge_replay(
                    chain=chain,
                    role="primary",
                    endpoint=f"https://{chain}.example/provider-test-secret",
                    output_root=tmp_path / chain,
                    client=client,
                )
        return reports

    reports = asyncio.run(execute())
    facts = bridge_pair_facts(reports["base"], reports["ethereum"])
    assert facts["deposit_id"] == EXPECTED_DEPOSIT_ID
    assert facts["recipient"] == RECIPIENT
    assert facts["fee_difference_raw"] == "867713010029593"


def test_cross_chain_recipient_mismatch_is_rejected(tmp_path) -> None:
    original = _event("ethereum")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "eth_getLogs":
            event = dict(original)
            words = event["data"][2:]
            replacement = _address("0x0000000000000000000000000000000000000001")
            event["data"] = f"0x{words[: 9 * 64]}{replacement}{words[10 * 64 :]}"
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": [event]})
        return _handler("ethereum")(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler("base"))) as c:
            source = await run_task_016_bridge_replay(
                chain="base",
                role="primary",
                endpoint="https://base.example/provider-test-secret",
                output_root=tmp_path / "base",
                client=c,
            )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            destination = await run_task_016_bridge_replay(
                chain="ethereum",
                role="primary",
                endpoint="https://eth.example/provider-test-secret",
                output_root=tmp_path / "ethereum",
                client=c,
            )
        return source, destination

    source, destination = asyncio.run(execute())
    with pytest.raises(ValueError, match="recipient"):
        bridge_pair_facts(source, destination)


def test_source_router_target_is_bound(tmp_path) -> None:
    async def execute():
        reports = {}
        for chain in CHAINS:
            async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(chain))) as client:
                reports[chain] = await run_task_016_bridge_replay(
                    chain=chain,
                    role="primary",
                    endpoint=f"https://{chain}.example/provider-test-secret",
                    output_root=tmp_path / chain,
                    client=client,
                )
        return reports

    reports = asyncio.run(execute())
    observations = list(reports["base"].observations)
    transaction = observations[0]
    summary = dict(transaction.decoded_summary)
    summary["to"] = "0x0000000000000000000000000000000000000001"
    observations[0] = replace(transaction, decoded_summary=summary)
    source = replace(reports["base"], observations=tuple(observations))
    with pytest.raises(ValueError, match="target"):
        bridge_pair_facts(source, reports["ethereum"])


def test_exact_event_must_exist_in_receipt(tmp_path) -> None:
    async def execute():
        reports = {}
        for chain in CHAINS:
            async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(chain))) as client:
                reports[chain] = await run_task_016_bridge_replay(
                    chain=chain,
                    role="primary",
                    endpoint=f"https://{chain}.example/provider-test-secret",
                    output_root=tmp_path / chain,
                    client=client,
                )
        return reports

    reports = asyncio.run(execute())
    observations = list(reports["base"].observations)
    receipt = observations[1]
    summary = dict(receipt.decoded_summary)
    summary["selected_logs"] = [
        {
            "transaction_hash": SOURCE_TX,
            "log_index": "0x2",
            "topic0": SOURCE_EVENT_TOPIC,
        }
    ]
    observations[1] = replace(receipt, decoded_summary=summary)
    source = replace(reports["base"], observations=tuple(observations))
    with pytest.raises(ValueError, match="not present"):
        bridge_pair_facts(source, reports["ethereum"])


def test_exclusive_relayer_mismatch_is_rejected(tmp_path) -> None:
    original = _event("ethereum")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "eth_getLogs":
            event = dict(original)
            words = event["data"][2:]
            replacement = _address("0x0000000000000000000000000000000000000002")
            event["data"] = f"0x{words[: 7 * 64]}{replacement}{words[8 * 64 :]}"
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": [event]})
        return _handler("ethereum")(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler("base"))) as c:
            source = await run_task_016_bridge_replay(
                chain="base",
                role="primary",
                endpoint="https://base.example/provider-test-secret",
                output_root=tmp_path / "base",
                client=c,
            )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            destination = await run_task_016_bridge_replay(
                chain="ethereum",
                role="primary",
                endpoint="https://eth.example/provider-test-secret",
                output_root=tmp_path / "ethereum",
                client=c,
            )
        return source, destination

    source, destination = asyncio.run(execute())
    with pytest.raises(ValueError, match="exclusive_relayer"):
        bridge_pair_facts(source, destination)


def test_zero_output_token_must_match_pinned_default_mapping(tmp_path) -> None:
    original = _event("ethereum")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["method"] == "eth_getLogs":
            event = dict(original)
            words = event["data"][2:]
            replacement = _address("0x0000000000000000000000000000000000000003")
            event["data"] = f"0x{words[:64]}{replacement}{words[2 * 64 :]}"
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": [event]})
        return _handler("ethereum")(request)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler("base"))) as c:
            source = await run_task_016_bridge_replay(
                chain="base",
                role="primary",
                endpoint="https://base.example/provider-test-secret",
                output_root=tmp_path / "base",
                client=c,
            )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            destination = await run_task_016_bridge_replay(
                chain="ethereum",
                role="primary",
                endpoint="https://eth.example/provider-test-secret",
                output_root=tmp_path / "ethereum",
                client=c,
            )
        return source, destination

    source, destination = asyncio.run(execute())
    with pytest.raises(ValueError, match="asset mapping mismatch"):
        bridge_pair_facts(source, destination)


def test_cross_provider_matching_facts_are_accepted() -> None:
    facts = {"deposit_id": EXPECTED_DEPOSIT_ID, "recipient": RECIPIENT, "input_amount_raw": "1"}
    assert_matching_provider_facts(facts, dict(facts))


def test_cross_provider_fact_mismatch_is_rejected() -> None:
    primary = {"deposit_id": EXPECTED_DEPOSIT_ID, "recipient": RECIPIENT}
    verify = {"deposit_id": EXPECTED_DEPOSIT_ID, "recipient": "0xdifferent"}
    with pytest.raises(ValueError, match="recipient"):
        assert_matching_provider_facts(primary, verify)
