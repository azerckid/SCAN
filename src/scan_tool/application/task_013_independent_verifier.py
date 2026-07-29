"""Independent raw-first verifier for TASK-013 candidate fixtures."""

import hashlib
import json
from pathlib import Path
from typing import Any

from eth_abi import decode
from eth_abi.exceptions import DecodingError

FIXTURE_IDS = (
    "FX-EVM-NFT-721-001",
    "FX-EVM-NFT-1155-001",
    "FX-EVM-PROXY-001",
)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_FOR_ALL_TOPIC = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
TRANSFER_SINGLE_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
TRANSFER_BATCH_TOPIC = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
UPGRADED_TOPIC = "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b"
IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"

REQUIREMENTS = {
    "FX-EVM-NFT-721-001": (
        "REQ-NFT721-TRANSFER",
        "REQ-NFT721-APPROVALS",
    ),
    "FX-EVM-NFT-1155-001": (
        "REQ-NFT1155-SINGLE-APPROVAL",
        "REQ-NFT1155-BATCH",
    ),
    "FX-EVM-PROXY-001": (
        "REQ-PROXY-UPGRADE-EVENT",
        "REQ-PROXY-HISTORICAL-SLOT",
        "REQ-PROXY-ADMIN-SEPARATION",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def recalculate_raw_facts(raw: dict[str, Any]) -> dict[str, Any]:
    """Calculate canonical facts from raw replay without reading expected values."""
    fixture_id = _text(raw, "fixture_id")
    if fixture_id == "FX-EVM-NFT-721-001":
        return _recalculate_erc721(raw)
    if fixture_id == "FX-EVM-NFT-1155-001":
        return _recalculate_erc1155(raw)
    if fixture_id == "FX-EVM-PROXY-001":
        return _recalculate_proxy(raw)
    raise ValueError("unsupported TASK-013 fixture")


def verify_fixture(
    raw: dict[str, Any],
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Recalculate raw facts, then compare them with the separate fixture contract."""
    fixture_id = _text(raw, "fixture_id")
    if _text(expected, "fixture_id") != fixture_id:
        raise ValueError("raw and expected fixture IDs differ")
    if _text(evidence, "fixture_id") != fixture_id:
        raise ValueError("raw and evidence fixture IDs differ")

    calculated = recalculate_raw_facts(raw)
    expected_facts = _expected_projection(fixture_id, expected)
    if calculated != expected_facts:
        raise ValueError(f"{fixture_id} independently calculated facts differ")

    requirement_checks = _verify_requirements(fixture_id, expected, evidence)
    canonical = json.dumps(
        calculated,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": hashlib.sha256(canonical).hexdigest(),
        "requirement_checks": requirement_checks,
    }


def verify_repository(fixtures_root: Path) -> tuple[dict[str, Any], ...]:
    """Verify the fixed TASK-013 fixture set in deterministic order."""
    reports = []
    for fixture_id in FIXTURE_IDS:
        package = fixtures_root / fixture_id
        reports.append(
            verify_fixture(
                load_json(package / "raw-replay.json"),
                load_json(package / "expected.json"),
                load_json(package / "evidence.json"),
            )
        )
    return tuple(reports)


def _recalculate_erc721(raw: dict[str, Any]) -> dict[str, Any]:
    _require_complete_nft_scope(raw)
    logs = _logs(raw)
    _require_single_contract(logs)
    _require_successful_receipts(raw, logs)

    transfer = _one_log(logs, TRANSFER_TOPIC, 4)
    approval = _one_log(logs, APPROVAL_TOPIC, 4)
    approval_for_all = _one_log(logs, APPROVAL_FOR_ALL_TOPIC, 3)
    if _text(transfer, "data") != "0x" or _text(approval, "data") != "0x":
        raise ValueError("ERC-721 indexed values must not be read from data")

    token_id = str(_hex_int(_topics(transfer)[3]))
    if str(_hex_int(_topics(approval)[3])) != token_id:
        raise ValueError("ERC-721 Approval and Transfer token IDs differ")

    movement = {
        "event_kind": "transfer",
        **_log_location(transfer),
        "from": _address(_topics(transfer)[1]),
        "to": _address(_topics(transfer)[2]),
        "token_id_raw": token_id,
        "amount_raw": "1",
        "amount_origin": "normalized_unit",
    }
    approvals = [
        {
            "event_kind": "approval_for_all",
            **_log_location(approval_for_all),
            "owner": _address(_topics(approval_for_all)[1]),
            "operator": _address(_topics(approval_for_all)[2]),
            "approved": bool(_data_word(approval_for_all, 0)),
        },
        {
            "event_kind": "token_approval",
            **_log_location(approval),
            "owner": _address(_topics(approval)[1]),
            "approved_address": _address(_topics(approval)[2]),
            "token_id_raw": token_id,
            "meaning": "approval_reset"
            if _address(_topics(approval)[2]) == "0x" + ("0" * 40)
            else "approval_set",
        },
    ]
    approvals.sort(key=lambda item: (item["block_number"], item["log_index"]))
    return {"standard": "erc721", "movements": [movement], "approvals": approvals}


def _recalculate_erc1155(raw: dict[str, Any]) -> dict[str, Any]:
    _require_complete_nft_scope(raw)
    logs = _logs(raw)
    _require_single_contract(logs)
    _require_successful_receipts(raw, logs)

    approvals = [item for item in logs if _topics(item)[0].lower() == APPROVAL_FOR_ALL_TOPIC]
    singles = [item for item in logs if _topics(item)[0].lower() == TRANSFER_SINGLE_TOPIC]
    batch = _one_log(logs, TRANSFER_BATCH_TOPIC, 4)
    if len(approvals) != 2 or len(singles) < 1:
        raise ValueError("ERC-1155 selected scope is incomplete")
    if any(_topics(item)[1:3] != _topics(approvals[0])[1:3] for item in approvals):
        raise ValueError("ERC-1155 approval owner or operator differs")

    owner = _address(_topics(approvals[0])[1])
    outgoing = [item for item in singles if _address(_topics(item)[2]) == owner]
    if len(outgoing) != 1:
        raise ValueError("ERC-1155 selected outgoing TransferSingle is ambiguous")
    selected = outgoing[0]

    try:
        ids, amounts = decode(
            ["uint256[]", "uint256[]"],
            bytes.fromhex(_text(batch, "data").removeprefix("0x")),
        )
    except (DecodingError, ValueError) as error:
        raise ValueError("ERC-1155 batch ABI is malformed") from error
    if len(ids) != len(amounts):
        raise ValueError("ERC-1155 batch arrays differ in length")

    approval_transitions = [
        {
            "log_index": _hex_int(_text(item, "log_index")),
            "approved": bool(_data_word(item, 0)),
        }
        for item in sorted(approvals, key=_log_sort_key)
    ]
    single_case = {
        "transaction_hash": _text(selected, "transaction_hash"),
        "block_number": _hex_int(_text(selected, "block_number")),
        "token_id_raw": str(_data_word(selected, 0)),
        "amount_raw": str(_data_word(selected, 1)),
        "selected_outgoing_log_index": _hex_int(_text(selected, "log_index")),
        "from": _address(_topics(selected)[2]),
        "to": _address(_topics(selected)[3]),
        "approval_transitions": approval_transitions,
    }
    batch_case = {
        **_log_location(batch),
        "operator": _address(_topics(batch)[1]),
        "from": _address(_topics(batch)[2]),
        "to": _address(_topics(batch)[3]),
        "ids_raw": [str(item) for item in ids],
        "amounts_raw": [str(item) for item in amounts],
    }
    return {
        "standard": "erc1155",
        "single_case": single_case,
        "batch_case": batch_case,
    }


def _recalculate_proxy(raw: dict[str, Any]) -> dict[str, Any]:
    scope = _mapping(raw, "scope")
    if (
        scope.get("upgrade_transaction_complete") is not True
        or scope.get("adjacent_state_complete") is not True
    ):
        raise ValueError("proxy selected scope is incomplete")
    receipt = _mapping(raw, "receipt")
    if _text(receipt, "status") != "0x1":
        raise ValueError("proxy upgrade transaction failed")

    upgraded = _one_log(_logs(raw), UPGRADED_TOPIC, 2)
    snapshots = {_text(item, "role"): item for item in _object_array(raw, "storage_snapshots")}
    required_roles = {
        "implementation_before",
        "implementation_after",
        "admin_before",
        "admin_after",
    }
    if set(snapshots) != required_roles:
        raise ValueError("proxy storage snapshot roles differ")
    event_block = _hex_int(_text(upgraded, "block_number"))
    if (
        _hex_int(_text(receipt, "block_number")) != event_block
        or _hex_int(_text(snapshots["implementation_after"], "block_number")) != event_block
        or _hex_int(_text(snapshots["implementation_before"], "block_number")) != event_block - 1
    ):
        raise ValueError("proxy receipt, event, and adjacent state blocks differ")
    if (
        _text(snapshots["implementation_before"], "slot") != IMPLEMENTATION_SLOT
        or _text(snapshots["implementation_after"], "slot") != IMPLEMENTATION_SLOT
        or _text(snapshots["admin_before"], "slot") != ADMIN_SLOT
        or _text(snapshots["admin_after"], "slot") != ADMIN_SLOT
    ):
        raise ValueError("proxy storage slot differs")

    before = _address(_text(snapshots["implementation_before"], "raw_word"))
    after = _address(_text(snapshots["implementation_after"], "raw_word"))
    event = _address(_topics(upgraded)[1])
    if after != event:
        raise ValueError("proxy event and after-state implementation differ")
    admin_before = _address(_text(snapshots["admin_before"], "raw_word"))
    admin_after = _address(_text(snapshots["admin_after"], "raw_word"))
    zero = "0x" + ("0" * 40)
    if admin_before != zero or admin_after != zero:
        raise ValueError("proxy admin separation failed")

    return {
        "pattern": "eip1967_direct_implementation",
        "proxy_address": _text(upgraded, "address"),
        "implementation_slot": IMPLEMENTATION_SLOT,
        "change": {
            **_log_location(upgraded),
            "before_implementation": before,
            "after_implementation": after,
            "event_implementation": event,
        },
        "admin": {
            "slot": ADMIN_SLOT,
            "before": admin_before,
            "after": admin_after,
            "change": "not_applicable",
        },
        "beacon": {"applicable": False},
    }


def _expected_projection(fixture_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    if fixture_id == "FX-EVM-NFT-721-001":
        return {
            "standard": expected["standard"],
            "movements": expected["movements"],
            "approvals": expected["approvals"],
        }
    if fixture_id == "FX-EVM-NFT-1155-001":
        return {
            "standard": expected["standard"],
            "single_case": expected["single_case"],
            "batch_case": expected["batch_case"],
        }
    if fixture_id == "FX-EVM-PROXY-001":
        return {
            "pattern": expected["pattern"],
            "proxy_address": expected["proxy_address"],
            "implementation_slot": expected["implementation_slot"],
            "change": expected["change"],
            "admin": expected["admin"],
            "beacon": expected["beacon"],
        }
    raise ValueError("unsupported TASK-013 expected fixture")


def _verify_requirements(
    fixture_id: str,
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, str]]:
    scoring = _mapping(expected, "scoring")
    requirements = scoring.get("requirements")
    if not isinstance(requirements, list):
        raise ValueError("scoring requirements must be an array")
    actual_ids = tuple(item["requirement_id"] for item in requirements)
    if actual_ids != REQUIREMENTS[fixture_id]:
        raise ValueError("fixture requirement IDs differ")

    evidence_ids = {
        item["evidence_id"]
        for name in (
            "event_evidence",
            "call_evidence",
            "state_evidence",
            "context_evidence",
        )
        for item in _object_array(evidence, name)
    }
    checks = []
    for requirement in requirements:
        refs = requirement.get("evidence_refs")
        if (
            requirement.get("mandatory") is not True
            or not isinstance(refs, list)
            or not refs
            or any(ref not in evidence_ids for ref in refs)
        ):
            raise ValueError(f"{requirement['requirement_id']} evidence linkage failed")
        checks.append({"requirement_id": requirement["requirement_id"], "status": "pass"})
    return checks


def _require_complete_nft_scope(raw: dict[str, Any]) -> None:
    scope = _mapping(raw, "scope")
    if (
        scope.get("selected_transactions_complete") is not True
        or scope.get("exact_block_windows_complete") is not True
    ):
        raise ValueError("NFT selected scope is incomplete")
    windows = _object_array(scope, "block_windows")
    window_blocks = {
        _text(item, "from") for item in windows if _text(item, "from") == _text(item, "to")
    }
    receipt_blocks = {_text(item, "block_number") for item in _object_array(raw, "receipts")}
    if len(window_blocks) != len(windows) or window_blocks != receipt_blocks:
        raise ValueError("NFT exact block windows differ from selected receipts")


def _require_successful_receipts(
    raw: dict[str, Any],
    logs: list[dict[str, Any]],
) -> None:
    receipts = _object_array(raw, "receipts")
    successful = {
        _text(item, "transaction_hash"): _text(item, "block_number")
        for item in receipts
        if _text(item, "status") == "0x1"
    }
    if len(successful) != len(receipts):
        raise ValueError("selected receipt failed")
    for item in logs:
        transaction_hash = _text(item, "transaction_hash")
        if transaction_hash not in successful:
            raise ValueError("log has no successful selected receipt")
        if _text(item, "block_number") != successful[transaction_hash]:
            raise ValueError("log and receipt blocks differ")


def _require_single_contract(logs: list[dict[str, Any]]) -> None:
    contracts = {_text(item, "address").lower() for item in logs}
    if len(contracts) != 1:
        raise ValueError("selected logs contain multiple contracts")


def _one_log(
    logs: list[dict[str, Any]],
    topic0: str,
    topic_count: int,
) -> dict[str, Any]:
    matches = [item for item in logs if _topics(item)[0].lower() == topic0]
    if len(matches) != 1:
        raise ValueError(f"expected one {topic0} log")
    if len(_topics(matches[0])) != topic_count:
        raise ValueError(f"{topic0} topic count differs")
    return matches[0]


def _logs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    logs = _object_array(raw, "logs")
    if any(item.get("removed") is not False for item in logs):
        raise ValueError("removed log is not scoring evidence")
    return logs


def _log_location(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "transaction_hash": _text(log, "transaction_hash"),
        "block_number": _hex_int(_text(log, "block_number")),
        "log_index": _hex_int(_text(log, "log_index")),
    }


def _log_sort_key(log: dict[str, Any]) -> tuple[int, int, int]:
    return (
        _hex_int(_text(log, "block_number")),
        _hex_int(_text(log, "transaction_index")),
        _hex_int(_text(log, "log_index")),
    )


def _topics(log: dict[str, Any]) -> list[str]:
    topics = log.get("topics")
    if (
        not isinstance(topics, list)
        or not topics
        or any(not isinstance(item, str) for item in topics)
    ):
        raise ValueError("log topics must be a non-empty text array")
    return topics


def _data_word(log: dict[str, Any], index: int) -> int:
    body = _text(log, "data").removeprefix("0x")
    start = index * 64
    word = body[start : start + 64]
    if len(word) != 64:
        raise ValueError("event data word is truncated")
    return int(word, 16)


def _address(value: str) -> str:
    body = value.removeprefix("0x")
    if len(body) < 40:
        raise ValueError("address word is truncated")
    address = body[-40:].lower()
    int(address, 16)
    return f"0x{address}"


def _hex_int(value: str) -> int:
    if not value.startswith("0x"):
        raise ValueError("hex integer must start with 0x")
    return int(value, 16)


def _text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{key} must be text")
    return item


def _mapping(
    value: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"{key} must be an object")
    return item


def _object_array(value: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = value.get(key)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must be an object array")
    return items
