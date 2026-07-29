"""TASK-013 evm_special (NFT/Proxy) complete, partial, and failed replay tests."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import EvmSpecialAnalysisRequest
from scan_tool.slices.evm_special import analyze_evm_special_replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    "FX-EVM-NFT-721-001",
    "FX-EVM-NFT-1155-001",
    "FX-EVM-PROXY-001",
)


def _request(fixture_id: str) -> EvmSpecialAnalysisRequest:
    request = validate_analysis_request(_request_document(fixture_id)).root
    assert isinstance(request, EvmSpecialAnalysisRequest)
    return request


def _request_document(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "analysis-request.json").read_text())


def _replay(fixture_id: str) -> dict[str, object]:
    return json.loads((FIXTURES / fixture_id / "raw-replay.json").read_text())


def _expected(fixture_id: str, keys: tuple[str, ...]) -> dict[str, object]:
    document = json.loads((FIXTURES / fixture_id / "expected.json").read_text())
    return {key: document[key] for key in keys}


EXPECTED_KEYS = {
    "FX-EVM-NFT-721-001": ("standard", "movements", "approvals"),
    "FX-EVM-NFT-1155-001": ("standard", "single_case", "batch_case"),
    "FX-EVM-PROXY-001": (
        "pattern",
        "proxy_address",
        "implementation_slot",
        "change",
        "admin",
        "beacon",
    ),
}


@pytest.mark.parametrize("fixture_id", CASES)
def test_complete_replays_are_deterministic(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    first = analyze_evm_special_replay(request, replay)
    second = analyze_evm_special_replay(request, replay)

    assert first.root.status == "complete"
    assert first.root.results
    assert first.root.evidence
    assert first.to_contract_dict() == second.to_contract_dict()


@pytest.mark.parametrize("fixture_id", CASES)
def test_complete_replays_match_the_fixture_reference_answer(fixture_id: str) -> None:
    request = _request(fixture_id)
    replay = json.dumps(_replay(fixture_id)).encode()

    result = analyze_evm_special_replay(request, replay)

    assert result.root.status == "complete"
    assert result.root.results[0].value == _expected(fixture_id, EXPECTED_KEYS[fixture_id])


def _drop_log(replay: dict[str, object], topic0: str) -> None:
    logs = cast(list[dict[str, object]], replay["logs"])
    replay["logs"] = [item for item in logs if item["topics"][0] != topic0]


@pytest.mark.parametrize(
    ("fixture_id", "mutate", "error_code"),
    (
        (
            "FX-EVM-NFT-721-001",
            lambda value: _drop_log(
                value, "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
            ),
            "source_unavailable",
        ),
        (
            "FX-EVM-NFT-1155-001",
            lambda value: _drop_log(
                value, "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
            ),
            "source_unavailable",
        ),
        (
            "FX-EVM-PROXY-001",
            lambda value: cast(list[object], value["storage_snapshots"]).pop(0),
            "archive_required",
        ),
    ),
)
def test_incomplete_replays_preserve_partial_results(
    fixture_id: str,
    mutate: Callable[[dict[str, object]], object],
    error_code: str,
) -> None:
    replay = _replay(fixture_id)
    mutate(replay)

    result = analyze_evm_special_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "partial"
    assert result.root.results
    assert result.root.errors[0].code == error_code


@pytest.mark.parametrize("fixture_id", CASES)
def test_invalid_replay_is_structured_failed(fixture_id: str) -> None:
    result = analyze_evm_special_replay(_request(fixture_id), b"{}")

    assert result.root.status == "failed"
    assert result.root.results == []
    assert result.root.evidence == []
    assert result.root.errors[0].code == "decode_failed"


def test_erc20_transfer_shape_is_rejected_as_ambiguous() -> None:
    fixture_id = "FX-EVM-NFT-721-001"
    replay = _replay(fixture_id)
    logs = cast(list[dict[str, object]], replay["logs"])
    for log in logs:
        if log["topics"][0] == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":
            log["topics"] = log["topics"][:3]
            log["data"] = "0x0000000000000000000000000000000000000000000000000000000000002396"

    result = analyze_evm_special_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "decode_failed"


def test_erc1155_batch_length_mismatch_is_structured_failed() -> None:
    fixture_id = "FX-EVM-NFT-1155-001"
    replay = _replay(fixture_id)
    logs = cast(list[dict[str, object]], replay["logs"])
    for log in logs:
        if log["topics"][0] == "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb":
            log["data"] = cast(str, log["data"])[:-64]

    result = analyze_evm_special_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "decode_failed"


def test_proxy_event_state_conflict_is_structured_failed() -> None:
    fixture_id = "FX-EVM-PROXY-001"
    replay = _replay(fixture_id)
    logs = cast(list[dict[str, object]], replay["logs"])
    logs[0]["topics"][1] = "0x0000000000000000000000008147b99df7672a21809c9093e6f6ce1a60f119bd"

    result = analyze_evm_special_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


@pytest.mark.parametrize(
    ("fixture_id", "mutate"),
    (
        (
            "FX-EVM-NFT-721-001",
            lambda value: value.update(fixture_id="FX-EVM-NFT-721-999"),
        ),
        (
            "FX-EVM-PROXY-001",
            lambda value: value.update(fixture_id="FX-EVM-PROXY-999"),
        ),
    ),
)
def test_replay_fixture_id_mismatch_is_structured_failed(
    fixture_id: str,
    mutate: Callable[[dict[str, object]], object],
) -> None:
    replay = _replay(fixture_id)
    mutate(replay)

    result = analyze_evm_special_replay(_request(fixture_id), json.dumps(replay).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_restricted_source_policy_blocks_before_decode() -> None:
    fixture_id = "FX-EVM-NFT-721-001"
    request_document = _request_document(fixture_id)
    cast(dict[str, object], request_document["source_policy"])["offline_mode"] = False
    request = validate_analysis_request(request_document).root
    assert isinstance(request, EvmSpecialAnalysisRequest)

    result = analyze_evm_special_replay(request, json.dumps(_replay(fixture_id)).encode())

    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"
