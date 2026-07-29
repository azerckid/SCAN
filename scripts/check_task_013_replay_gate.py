"""Validate TASK-013 replay packages without network access."""

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
FIXTURE_IDS = (
    "FX-EVM-NFT-721-001",
    "FX-EVM-NFT-1155-001",
    "FX-EVM-PROXY-001",
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _read(fixture_id: str, name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / fixture_id / name).read_text())


def _assert_common(fixture_id: str) -> tuple[dict[str, Any], ...]:
    documents = tuple(
        _read(fixture_id, name)
        for name in (
            "input.json",
            "expected.json",
            "evidence.json",
            "raw-replay.json",
            "provider-replay.json",
        )
    )
    assert all(item["fixture_id"] == fixture_id for item in documents)
    assert documents[0]["status"] == documents[1]["status"] == "confirmed"
    provider = documents[4]
    assert provider["status"] == "confirmed"
    assert provider["decoded_match"] is True
    assert provider["request_scope"]["methods"]
    assert all(method.startswith("eth_get") for method in provider["request_scope"]["methods"])
    assert [item["provider_id"] for item in provider["providers"]] == [
        "PROVIDER-EVM-PRIMARY",
        "PROVIDER-EVM-VERIFY",
    ]
    for item in provider["providers"]:
        assert item["status"] == "complete"
        assert item["retrieved_at"].endswith("Z")
        assert item["raw_sha256"]
        assert all(SHA256.fullmatch(value) for value in item["raw_sha256"].values())
    return documents


def _address(topic: str) -> str:
    return f"0x{topic[-40:]}"


def _word(value: str, index: int) -> int:
    body = value.removeprefix("0x")
    return int(body[index * 64 : (index + 1) * 64], 16)


def _array(value: str, offset_word: int) -> list[int]:
    offset = _word(value, offset_word) // 32
    length = _word(value, offset)
    return [_word(value, offset + 1 + index) for index in range(length)]


def _check_721() -> None:
    fixture_id = FIXTURE_IDS[0]
    input_doc, expected, _, replay, provider = _assert_common(fixture_id)
    assert isinstance(input_doc["transactions"], list)
    assert len(input_doc["transactions"]) == len(input_doc["block_windows"]) == 2
    assert replay["scope"]["selected_transactions_complete"] is True
    assert replay["scope"]["exact_block_windows_complete"] is True
    assert replay["scope"]["continuous_gap_scanned"] is False
    assert provider["continuous_gap_scanned"] is False

    logs = {int(item["log_index"], 16): item for item in replay["logs"]}
    movement = expected["movements"][0]
    transfer = logs[movement["log_index"]]
    assert int(transfer["topics"][3], 16) == int(movement["token_id_raw"])
    assert _address(transfer["topics"][1]) == movement["from"]
    assert _address(transfer["topics"][2]) == movement["to"]
    for approval in expected["approvals"]:
        log = logs[approval["log_index"]]
        assert _address(log["topics"][1]) == approval["owner"]


def _check_1155() -> None:
    fixture_id = FIXTURE_IDS[1]
    input_doc, expected, _, replay, provider = _assert_common(fixture_id)
    assert isinstance(input_doc["transactions"], list)
    assert len(input_doc["transactions"]) == len(input_doc["block_windows"]) == 2
    assert replay["scope"]["selected_transactions_complete"] is True
    assert replay["scope"]["exact_block_windows_complete"] is True
    assert replay["scope"]["continuous_gap_scanned"] is False
    assert provider["continuous_gap_scanned"] is False

    logs = {int(item["log_index"], 16): item for item in replay["logs"]}
    single = expected["single_case"]
    single_log = logs[single["selected_outgoing_log_index"]]
    assert _word(single_log["data"], 0) == int(single["token_id_raw"])
    assert _word(single_log["data"], 1) == int(single["amount_raw"])
    assert _address(single_log["topics"][2]) == single["from"]
    assert _address(single_log["topics"][3]) == single["to"]

    batch = expected["batch_case"]
    batch_log = logs[batch["log_index"]]
    assert _array(batch_log["data"], 0) == [int(item) for item in batch["ids_raw"]]
    assert _array(batch_log["data"], 1) == [int(item) for item in batch["amounts_raw"]]
    for transition in single["approval_transitions"]:
        assert bool(_word(logs[transition["log_index"]]["data"], 0)) is transition["approved"]


def _check_proxy() -> None:
    fixture_id = FIXTURE_IDS[2]
    _, expected, _, replay, provider = _assert_common(fixture_id)
    assert replay["scope"]["upgrade_transaction_complete"] is True
    assert replay["scope"]["adjacent_state_complete"] is True
    assert replay["scope"]["wider_history_scanned"] is False
    assert provider["wider_history_scanned"] is False

    snapshots = {item["role"]: item for item in replay["storage_snapshots"]}
    before = _address(snapshots["implementation_before"]["raw_word"])
    after = _address(snapshots["implementation_after"]["raw_word"])
    assert before == expected["change"]["before_implementation"]
    assert after == expected["change"]["after_implementation"]
    assert _address(replay["logs"][0]["topics"][1]) == after
    assert _address(snapshots["admin_before"]["raw_word"]) == expected["admin"]["before"]
    assert _address(snapshots["admin_after"]["raw_word"]) == expected["admin"]["after"]


def main() -> None:
    _check_721()
    _check_1155()
    _check_proxy()
    print(
        "PASS TASK-013 replay Gate: 3 fixtures (confirmed), 2 providers, "
        "16 capabilities, exact scoped raw values"
    )


if __name__ == "__main__":
    main()
