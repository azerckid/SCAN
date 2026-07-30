"""Independent raw-first Across V3 bridge verifier for TASK-016.

This module is deliberately self-contained: it does not import anything from
``task_016_bridge_replay.py``. It re-decodes the raw ``topics``/``data`` ABI
log bytes from scratch and independently recomputes the reconciled bridge
facts, so a bug shared by both code paths (e.g. a wrong constant) cannot
silently cancel out. Two separately authored implementations reaching the
same canonical hash from the same raw bytes is the actual verification.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

FIXTURE_IDS = ("FX-SVC-BRG-001",)

REQUIREMENTS = {
    "FX-SVC-BRG-001": (
        "REQ-BRIDGE-SOURCE",
        "REQ-BRIDGE-DESTINATION",
        "REQ-BRIDGE-DOMAIN",
    ),
}

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_OUTPUT_TOKEN_MAP = {
    "0x4200000000000000000000000000000000000006": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def verify_repository(fixtures_root: Path) -> tuple[dict[str, Any], ...]:
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


def verify_fixture(
    raw: dict[str, Any],
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    fixture_id = _text(raw, "fixture_id")
    if _text(expected, "fixture_id") != fixture_id:
        raise ValueError("raw/expected fixture IDs differ")
    if _text(evidence, "fixture_id") != fixture_id:
        raise ValueError("raw/evidence fixture IDs differ")
    facts = recalculate_raw_facts(raw)
    if facts != _expected_projection(expected):
        raise ValueError(f"{fixture_id} independently calculated facts differ")
    _verify_evidence(facts, evidence)
    _verify_requirements(fixture_id, expected, evidence)
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": hashlib.sha256(canonical).hexdigest(),
        "requirement_count": len(REQUIREMENTS[fixture_id]),
    }


def recalculate_raw_facts(raw: dict[str, Any]) -> dict[str, Any]:
    observations = raw.get("raw_observations")
    if not isinstance(observations, list) or len(observations) != 2:
        raise ValueError("raw_observations must contain exactly two chain entries")
    by_chain = {_text(item, "chain"): item for item in observations if isinstance(item, dict)}
    if set(by_chain) != {"base", "ethereum"}:
        raise ValueError("raw_observations must cover base and ethereum")
    source_log = _mapping(by_chain["base"], "log")
    destination_log = _mapping(by_chain["ethereum"], "log")
    source = _decode_v3_funds_deposited(source_log)
    destination = _decode_filled_v3_relay(destination_log)

    required_equal = (
        "deposit_id",
        "input_token",
        "input_amount_raw",
        "output_amount_raw",
        "fill_deadline",
        "exclusivity_deadline",
        "exclusive_relayer",
        "depositor",
        "recipient",
        "message",
    )
    for key in required_equal:
        if source[key] != destination[key]:
            raise ValueError(f"bridge event mismatch: {key}")
    if source["destination_chain_id"] != 1:
        raise ValueError("source destination chain mismatch")
    if destination["origin_chain_id"] != 8453:
        raise ValueError("destination origin chain mismatch")

    source_output_token = source["output_token"]
    destination_output_token = destination["output_token"]
    if source_output_token == ZERO_ADDRESS:
        expected_output_token = DEFAULT_OUTPUT_TOKEN_MAP.get(source["input_token"])
        if expected_output_token is None:
            raise ValueError("bridge default output token mapping is not pinned")
        if destination_output_token != expected_output_token:
            raise ValueError("bridge output asset mapping mismatch")
    elif source_output_token != destination_output_token:
        raise ValueError("bridge output asset mismatch")

    source_raw = int(source["input_amount_raw"])
    destination_raw = int(destination["output_amount_raw"])
    if source_raw < destination_raw:
        raise ValueError("bridge output exceeds input")

    return {
        "protocol": "across_v3",
        "origin_chain_id": 8453,
        "destination_chain_id": 1,
        "deposit_id": source["deposit_id"],
        "source_spoke_pool": source_log["address"],
        "destination_spoke_pool": destination_log["address"],
        "depositor": source["depositor"],
        "recipient": source["recipient"],
        "source_asset": source["input_token"],
        "destination_asset": destination_output_token,
        "source_raw": str(source_raw),
        "protocol_fee_raw_candidate": str(source_raw - destination_raw),
        "expected_destination_raw": str(destination_raw),
        "observed_destination_raw": str(destination_raw),
        "message": source["message"],
        "attribution": {
            "recipient_ownership": "not_assessed",
            "criminality": "not_assessed",
        },
    }


def _decode_v3_funds_deposited(log: dict[str, Any]) -> dict[str, Any]:
    topics = _topics(log, expected_count=4)
    words = _data_words(_text(log, "data"))
    if len(words) < 10:
        raise ValueError("V3FundsDeposited data is truncated")
    return {
        "input_token": _address(words[0]),
        "output_token": _address(words[1]),
        "input_amount_raw": str(int(words[2], 16)),
        "output_amount_raw": str(int(words[3], 16)),
        "deposit_id": int(topics[2], 16),
        "destination_chain_id": int(topics[1], 16),
        "depositor": _address(topics[3][2:]),
        "fill_deadline": int(words[5], 16),
        "exclusivity_deadline": int(words[6], 16),
        "recipient": _address(words[7]),
        "exclusive_relayer": _address(words[8]),
        "message": _dynamic_bytes(words, 9),
    }


def _decode_filled_v3_relay(log: dict[str, Any]) -> dict[str, Any]:
    topics = _topics(log, expected_count=4)
    words = _data_words(_text(log, "data"))
    if len(words) < 12:
        raise ValueError("FilledV3Relay data is truncated")
    return {
        "input_token": _address(words[0]),
        "output_token": _address(words[1]),
        "input_amount_raw": str(int(words[2], 16)),
        "output_amount_raw": str(int(words[3], 16)),
        "deposit_id": int(topics[2], 16),
        "origin_chain_id": int(topics[1], 16),
        "fill_deadline": int(words[5], 16),
        "exclusivity_deadline": int(words[6], 16),
        "exclusive_relayer": _address(words[7]),
        "depositor": _address(words[8]),
        "recipient": _address(words[9]),
        "message": _dynamic_bytes(words, 10),
    }


def _expected_projection(expected: dict[str, Any]) -> dict[str, Any]:
    return _mapping(expected, "bridge_transfer")


def _verify_evidence(facts: dict[str, Any], evidence: dict[str, Any]) -> None:
    events = {
        _text(item, "evidence_id"): item for item in _object_array(evidence, "event_evidence")
    }
    source_evidence = events["EV-BRIDGE-SOURCE-EVENT"]
    if (
        int(_number(source_evidence, "chain_id")) != facts["origin_chain_id"]
        or _text(source_evidence, "spoke_pool") != facts["source_spoke_pool"]
        or int(_number(source_evidence, "deposit_id")) != facts["deposit_id"]
    ):
        raise ValueError("EV-BRIDGE-SOURCE-EVENT value differs")
    destination_evidence = events["EV-BRIDGE-DESTINATION-EVENT"]
    if (
        int(_number(destination_evidence, "chain_id")) != facts["destination_chain_id"]
        or _text(destination_evidence, "spoke_pool") != facts["destination_spoke_pool"]
        or int(_number(destination_evidence, "deposit_id")) != facts["deposit_id"]
    ):
        raise ValueError("EV-BRIDGE-DESTINATION-EVENT value differs")


def _verify_requirements(
    fixture_id: str,
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    evidence_ids = {
        _text(item, "evidence_id")
        for key in ("event_evidence", "call_evidence", "state_evidence", "context_evidence")
        for item in _object_array(evidence, key)
    }
    requirements = _mapping(expected, "scoring").get("requirements")
    if not isinstance(requirements, list):
        raise ValueError("requirements must be an array")
    found = []
    for item in requirements:
        if not isinstance(item, dict):
            raise ValueError("requirement must be an object")
        found.append(_text(item, "requirement_id"))
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= evidence_ids:
            raise ValueError("requirement evidence references differ")
    if tuple(found) != REQUIREMENTS[fixture_id]:
        raise ValueError("requirement IDs differ")


def _topics(log: dict[str, Any], *, expected_count: int) -> list[str]:
    topics = log.get("topics")
    if not isinstance(topics, list) or len(topics) != expected_count:
        raise ValueError("log topics are malformed")
    if not all(isinstance(item, str) and item.startswith("0x") for item in topics):
        raise ValueError("log topics must be hex strings")
    return [item.lower() for item in topics]


def _data_words(value: str) -> list[str]:
    if not value.startswith("0x"):
        raise ValueError("log data must be hex")
    body = value[2:]
    if len(body) % 64:
        raise ValueError("log data is not word-aligned")
    return [body[index : index + 64] for index in range(0, len(body), 64)]


def _dynamic_bytes(words: list[str], offset_index: int) -> str:
    offset = int(words[offset_index], 16)
    if offset % 32 or offset // 32 >= len(words):
        raise ValueError("dynamic bytes offset is invalid")
    length_index = offset // 32
    length = int(words[length_index], 16)
    body = "".join(words[length_index + 1 :])
    if length * 2 > len(body):
        raise ValueError("dynamic bytes are truncated")
    return f"0x{body[: length * 2]}"


def _address(word: str) -> str:
    if len(word) != 64:
        raise ValueError("ABI address word must contain 32 bytes")
    return f"0x{word[-40:].lower()}"


def _object_array(value: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = value.get(key)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must be an object array")
    return items


def _mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"{key} must be an object")
    return item


def _text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{key} must be text")
    return item


def _number(value: dict[str, Any], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ValueError(f"{key} must be an integer")
    return item
