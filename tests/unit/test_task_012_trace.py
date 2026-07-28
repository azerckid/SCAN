import asyncio
import json

import httpx
import pytest

from scan_tool.application.provider_smoke import TASK_012_TX_HASH
from scan_tool.application.task_012_replay import SUBJECT
from scan_tool.application.task_012_trace import (
    decode_trace_summary,
    dry_run_trace_plan,
    run_task_012_trace_replay,
    trace_request,
)

EXPECTED_INFLOW_WEI = "14449515027026387018"
EXPECTED_INFLOW_HEX = hex(int(EXPECTED_INFLOW_WEI))


def _body(result: object) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()


def test_trace_profiles_are_read_only_and_network_free_by_default() -> None:
    debug = dry_run_trace_plan("debug_call_tracer")
    parity = dry_run_trace_plan("parity_trace_transaction")

    assert debug["network_calls"] == parity["network_calls"] == 0
    assert debug["required_endpoint_env"] == parity["required_endpoint_env"]
    assert trace_request("debug_call_tracer").method == "debug_traceTransaction"
    assert trace_request("parity_trace_transaction").method == "trace_transaction"
    assert trace_request("parity_trace_transaction").params == [TASK_012_TX_HASH]


def test_debug_call_tracer_normalizes_successful_nested_inflow() -> None:
    result = {
        "type": "CALL",
        "from": SUBJECT,
        "to": "0xrouter",
        "value": "0x0",
        "calls": [
            {
                "type": "CALL",
                "from": "0xrouter",
                "to": SUBJECT.upper(),
                "value": EXPECTED_INFLOW_HEX,
            },
            {
                "type": "CALL",
                "from": "0xrouter",
                "to": SUBJECT,
                "value": "0x1",
                "error": "execution reverted",
            },
        ],
    }

    summary = decode_trace_summary("debug_call_tracer", _body(result))

    assert summary["dialect"] == "debug_call_tracer"
    assert summary["matching_successful_inflows"] == [
        {
            "path": [0],
            "type": "CALL",
            "from": "0xrouter",
            "to": SUBJECT.upper(),
            "value_hex": EXPECTED_INFLOW_HEX,
            "value_wei": EXPECTED_INFLOW_WEI,
            "error": None,
        }
    ]


def test_debug_call_tracer_accepts_documented_wrapped_response() -> None:
    wrapped = [
        {
            "name": "transaction trace",
            "value": {
                "type": "CALL",
                "from": "0xrouter",
                "to": SUBJECT,
                "value": EXPECTED_INFLOW_HEX,
            },
        }
    ]

    summary = decode_trace_summary("debug_call_tracer", _body(wrapped))

    assert summary["matching_successful_inflows"][0]["value_wei"] == EXPECTED_INFLOW_WEI


def test_parity_trace_normalizes_inflow_and_excludes_failed_trace() -> None:
    result = [
        {
            "type": "call",
            "action": {
                "callType": "call",
                "from": "0xrouter",
                "to": SUBJECT,
                "value": EXPECTED_INFLOW_HEX,
            },
            "traceAddress": [1, 0],
        },
        {
            "type": "call",
            "action": {
                "callType": "call",
                "from": "0xrouter",
                "to": SUBJECT,
                "value": "0x1",
            },
            "traceAddress": [2],
            "error": "Reverted",
        },
    ]

    summary = decode_trace_summary("parity_trace_transaction", _body(result))

    assert summary["root"] is None
    assert summary["matching_successful_inflows"] == [
        {
            "path": [1, 0],
            "type": "call",
            "from": "0xrouter",
            "to": SUBJECT,
            "value_hex": EXPECTED_INFLOW_HEX,
            "value_wei": EXPECTED_INFLOW_WEI,
            "error": None,
        }
    ]


@pytest.mark.parametrize(
    ("behavior", "expected_kind", "status_code"),
    [
        ("timeout", "timeout", None),
        ("rate_limited", "rate_limited", 429),
        ("unsupported", "invalid_response", 200),
        ("malformed", "invalid_response", 200),
    ],
)
def test_provider_failure_behaviors_are_bounded_and_structured(
    tmp_path,
    behavior: str,
    expected_kind: str,
    status_code: int | None,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if behavior == "timeout":
            raise httpx.ReadTimeout("canary timeout", request=request)
        if behavior == "rate_limited":
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "limited"})
        if behavior == "unsupported":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32601, "message": "method not found"},
                },
            )
        return httpx.Response(200, content=b"{not-json")

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_task_012_trace_replay(
                dialect="debug_call_tracer",
                endpoint="https://rpc.example/v2/provider-secret-canary",
                output_root=tmp_path,
                client=client,
            )

    report = asyncio.run(execute())

    assert report.status == "failed"
    assert report.network_calls == 1
    assert report.observations[0].failure_kind == expected_kind
    assert report.observations[0].http_status == status_code
    assert report.observations[0].raw_sha256 is None
    assert "provider-secret-canary" not in json.dumps(report, default=str)


@pytest.mark.parametrize(
    ("dialect", "result"),
    [
        ("debug_call_tracer", []),
        ("parity_trace_transaction", {}),
    ],
)
def test_trace_dialect_rejects_wrong_result_shape(dialect, result) -> None:
    with pytest.raises(ValueError, match="result"):
        decode_trace_summary(dialect, _body(result))
