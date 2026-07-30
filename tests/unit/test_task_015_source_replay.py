import asyncio
import json
from pathlib import Path

import httpx
import pytest

from scan_tool.application.task_015_source_replay import (
    ENS_CONFLICT,
    LABEL_CONFLICT,
    _summary,
    run_task_015_ens_replay,
    task_015_ens_requests,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"


def test_label_replay_is_two_fixed_block_read_only_calls() -> None:
    requests = task_015_ens_requests(LABEL_CONFLICT)
    assert [request.capability for request in requests] == [
        "label_resolver",
        "label_address",
    ]
    assert {request.method for request in requests} == {"eth_call"}
    assert {request.params[-1] for request in requests} == {"0x1873d4e"}
    assert all(
        request.params[0]["data"].endswith(
            "c041982b4f77cbbd82ef3b9ea748738ac6c281d3f1af198770d29f75ac32d80a"
        )
        for request in requests
    )


def test_ens_replay_is_four_fixed_block_read_only_calls() -> None:
    requests = task_015_ens_requests(ENS_CONFLICT)
    assert [request.capability for request in requests] == [
        "forward_resolver",
        "forward_address",
        "reverse_resolver",
        "reverse_name",
    ]
    assert {request.method for request in requests} == {"eth_call"}
    assert {request.params[-1] for request in requests} == {"0x1873d4e"}


def test_summary_decodes_address_and_name() -> None:
    requests = task_015_ens_requests(ENS_CONFLICT)
    address = b'{"result":"0x000000000000000000000000b8c2c29ee19d8307cb7255e1cd9cbde883a267d5"}'
    name = {"result": ("0x" + "00" * 31 + "20" + "00" * 31 + "08" + "6e69636b2e657468" + "00" * 24)}
    assert _summary(requests[1], address) == {
        "address": "0xb8c2c29ee19d8307cb7255e1cd9cbde883a267d5"
    }
    assert _summary(requests[3], json.dumps(name).encode()) == {"name": "nick.eth"}


def test_summary_rejects_malformed_result() -> None:
    request = task_015_ens_requests(ENS_CONFLICT)[0]
    with pytest.raises(ValueError, match="one ABI word"):
        _summary(request, b'{"result":"0x01"}')


def test_trace_role_can_supply_independent_ens_calls(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        result = "0x" + "00" * 12 + "4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41"
        if body["params"][0]["to"] != "0x00000000000c2e074ec69a0dfb2997ba6c7d2e1e":
            result = "0x" + "00" * 12 + "12d66f87a04a9e220743712ce6d9bb1b5616b8fc"
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    async def execute() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_task_015_ens_replay(
                fixture_id=LABEL_CONFLICT,
                role="trace",
                endpoint="https://trace.example.invalid/rpc",
                output_root=tmp_path,
                client=client,
                provider_id_override="BLOCKSCOUT-ETH-RPC",
            )

    report = asyncio.run(execute())
    assert report.status == "complete"
    assert report.provider_id == "BLOCKSCOUT-ETH-RPC"


@pytest.mark.parametrize(
    ("fixture_id", "decoded_keys"),
    [
        (LABEL_CONFLICT, {"resolver", "address"}),
        (
            ENS_CONFLICT,
            {
                "forward_resolver",
                "forward_address",
                "reverse_resolver",
                "reverse_name",
            },
        ),
    ],
)
def test_pinned_provider_replay_has_two_matching_complete_providers(
    fixture_id: str,
    decoded_keys: set[str],
) -> None:
    replay = json.loads((FIXTURE_ROOT / fixture_id / "provider-replay.json").read_text())
    complete = [item for item in replay["providers"] if item["status"] == "complete"]
    failed = [item for item in replay["providers"] if item["status"] == "failed"]
    assert {item["provider_id"] for item in complete} == {
        "PROVIDER-EVM-VERIFY",
        "BLOCKSCOUT-ETH-RPC",
    }
    assert len({json.dumps(item["decoded"], sort_keys=True) for item in complete}) == 1
    assert set(complete[0]["decoded"]) == decoded_keys
    expected_failures = (
        {("invalid_response", 200), ("permanent", 403)}
        if fixture_id == LABEL_CONFLICT
        else {("rate_limited", 429), ("permanent", 403)}
    )
    assert {(item["failure_kind"], item["http_status"]) for item in failed} == expected_failures
    if fixture_id == LABEL_CONFLICT:
        primary = next(item for item in failed if item["provider_id"] == "PROVIDER-EVM-PRIMARY")
        assert primary.get("json_rpc_error_code") == -32003
    assert replay["decoded_match"] is True


def test_pinned_sls_snapshot_is_context_not_historical_rewrite() -> None:
    snapshot = json.loads(
        (FIXTURE_ROOT / "FX-OSINT-SANCTIONS-HISTORY-001/sls-snapshot.json").read_text()
    )
    assert snapshot["source"]["byte_length"] == 5_624_423
    assert snapshot["source"]["line_count"] == 19_175
    assert snapshot["source"]["raw_sha256"] == (
        "464a917d662b9de3a26588499a8f1a4cfea341a70f3ace64038a5f8cb2b85b65"
    )
    assert snapshot["query"]["case_insensitive_match_count"] == 0
    assert snapshot["interpretation"] == {
        "role": "context",
        "historical_designation_changed": False,
        "historical_removal_changed": False,
        "current_criminality_assessed": False,
    }
