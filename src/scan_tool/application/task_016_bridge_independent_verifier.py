"""Independent raw-first Across V3 bridge verifier for TASK-016.

This module is deliberately self-contained: it does not import anything from
``task_016_bridge_replay.py``. It loads the exact raw JSON-RPC response
artifacts referenced by ``raw-replay.json``, mechanically checks each one's
SHA-256 against the value already pinned in ``provider-replay.json``, then
re-decodes the raw ``topics``/``data`` ABI log bytes and the tx/receipt/block
binding fields from scratch. Two separately authored implementations reaching
the same canonical hash from the same raw bytes is the actual verification —
recomputing from an already-decoded summary would not be independent.
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

# Independently re-declared expectations (not imported) for the one pinned
# Across V3 candidate. These are exactly what genuine ABI/chain binding is
# checked against below.
SOURCE_TX = "0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b"
SOURCE_BLOCK = "0x14e5a4b"
SOURCE_SPOKE_POOL = "0x09aea4b2242abc8bb4bb78d537a67a245a7bec64"
SOURCE_TRANSACTION_TARGET = "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae"
SOURCE_EVENT_TOPIC0 = "0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f"

DESTINATION_TX = "0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0"
DESTINATION_BLOCK = "0x1420a1e"
DESTINATION_SPOKE_POOL = "0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5"
DESTINATION_EVENT_TOPIC0 = "0x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7"

EXPECTED_ORIGIN_CHAIN_ID = 8453
EXPECTED_DESTINATION_CHAIN_ID = 1
EXPECTED_DEPOSIT_ID = 2395968


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
                package,
                load_json(package / "raw-replay.json"),
                load_json(package / "provider-replay.json"),
                load_json(package / "expected.json"),
                load_json(package / "evidence.json"),
            )
        )
    return tuple(reports)


def verify_fixture(
    package: Path,
    raw: dict[str, Any],
    provider_replay: dict[str, Any],
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    fixture_id = _text(raw, "fixture_id")
    if _text(expected, "fixture_id") != fixture_id:
        raise ValueError("raw/expected fixture IDs differ")
    if _text(evidence, "fixture_id") != fixture_id:
        raise ValueError("raw/evidence fixture IDs differ")
    facts = recalculate_raw_facts(package, raw, provider_replay)
    if facts != _mapping(expected, "bridge_transfer"):
        raise ValueError(f"{fixture_id} independently calculated facts differ")
    _verify_evidence(facts, evidence)
    _verify_requirements(fixture_id, expected, evidence)
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    calculated_sha256 = hashlib.sha256(canonical).hexdigest()
    _verify_verification_provenance(evidence, calculated_sha256)
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": calculated_sha256,
        "requirement_count": len(REQUIREMENTS[fixture_id]),
    }


def recalculate_raw_facts(
    package: Path,
    raw: dict[str, Any],
    provider_replay: dict[str, Any],
) -> dict[str, Any]:
    observations = raw.get("raw_observations")
    if not isinstance(observations, list) or len(observations) != 2:
        raise ValueError("raw_observations must contain exactly two chain entries")
    by_chain = {_text(item, "chain"): item for item in observations if isinstance(item, dict)}
    if set(by_chain) != {"base", "ethereum"}:
        raise ValueError("raw_observations must cover base and ethereum")

    providers = {
        _text(item, "provider_id"): item for item in _object_array(provider_replay, "providers")
    }

    source = _decode_chain_event(
        package,
        by_chain["base"],
        providers,
        expected_tx=SOURCE_TX,
        expected_block=SOURCE_BLOCK,
        expected_spoke_pool=SOURCE_SPOKE_POOL,
        expected_target=SOURCE_TRANSACTION_TARGET,
        expected_topic0=SOURCE_EVENT_TOPIC0,
        decode=_decode_v3_funds_deposited,
    )
    destination = _decode_chain_event(
        package,
        by_chain["ethereum"],
        providers,
        expected_tx=DESTINATION_TX,
        expected_block=DESTINATION_BLOCK,
        expected_spoke_pool=DESTINATION_SPOKE_POOL,
        expected_target=DESTINATION_SPOKE_POOL,
        expected_topic0=DESTINATION_EVENT_TOPIC0,
        decode=_decode_filled_v3_relay,
    )

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
    if source["destination_chain_id"] != EXPECTED_DESTINATION_CHAIN_ID:
        raise ValueError("source destination chain mismatch")
    if destination["origin_chain_id"] != EXPECTED_ORIGIN_CHAIN_ID:
        raise ValueError("destination origin chain mismatch")
    if source["deposit_id"] != EXPECTED_DEPOSIT_ID:
        raise ValueError("bridge deposit ID mismatch")

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
        "origin_chain_id": EXPECTED_ORIGIN_CHAIN_ID,
        "destination_chain_id": EXPECTED_DESTINATION_CHAIN_ID,
        "deposit_id": source["deposit_id"],
        "source_spoke_pool": SOURCE_SPOKE_POOL,
        "destination_spoke_pool": DESTINATION_SPOKE_POOL,
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


def _decode_chain_event(
    package: Path,
    observation: dict[str, Any],
    providers: dict[str, dict[str, Any]],
    *,
    expected_tx: str,
    expected_block: str,
    expected_spoke_pool: str,
    expected_target: str,
    expected_topic0: str,
    decode: Any,
) -> dict[str, Any]:
    provider_id = _text(observation, "provider_id")
    provider = providers.get(provider_id)
    if provider is None:
        raise ValueError(f"provider {provider_id} is not present in provider-replay.json")
    pinned_sha256 = _mapping(provider, "raw_sha256")

    artifacts = _mapping(observation, "artifacts")
    transaction = _load_pinned_artifact(package, artifacts, pinned_sha256, "transaction")
    receipt = _load_pinned_artifact(package, artifacts, pinned_sha256, "receipt")
    block = _load_pinned_artifact(package, artifacts, pinned_sha256, "block")
    logs_result = _load_pinned_artifact(package, artifacts, pinned_sha256, "bridge_logs")

    tx_result = _require_mapping(transaction["result"])
    if str(tx_result.get("hash", "")).lower() != expected_tx:
        raise ValueError("bridge transaction hash mismatch")
    if str(tx_result.get("blockNumber", "")).lower() != expected_block:
        raise ValueError("bridge transaction block mismatch")
    if str(tx_result.get("to", "")).lower() != expected_target:
        raise ValueError("bridge transaction target mismatch")
    tx_block_hash = str(tx_result.get("blockHash", "")).lower()

    receipt_result = _require_mapping(receipt["result"])
    if str(receipt_result.get("transactionHash", "")).lower() != expected_tx:
        raise ValueError("bridge receipt transaction mismatch")
    if str(receipt_result.get("blockNumber", "")).lower() != expected_block:
        raise ValueError("bridge receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("bridge transaction was not successful")
    if str(receipt_result.get("blockHash", "")).lower() != tx_block_hash:
        raise ValueError("bridge transaction/receipt block hash mismatch")

    block_result = _require_mapping(block["result"])
    if str(block_result.get("number", "")).lower() != expected_block:
        raise ValueError("bridge block response mismatch")
    if str(block_result.get("hash", "")).lower() != tx_block_hash:
        raise ValueError("bridge block hash reconciliation failed")

    logs = logs_result["result"]
    if not isinstance(logs, list) or len(logs) != 1:
        raise ValueError("bridge log query must return exactly one event")
    log = _require_mapping(logs[0])
    if str(log.get("address", "")).lower() != expected_spoke_pool:
        raise ValueError("bridge event contract mismatch")
    if str(log.get("transactionHash", "")).lower() != expected_tx:
        raise ValueError("bridge event transaction mismatch")
    if str(log.get("blockNumber", "")).lower() != expected_block:
        raise ValueError("bridge event block mismatch")
    if str(log.get("blockHash", "")).lower() != tx_block_hash:
        raise ValueError("bridge event block hash mismatch")
    if log.get("removed") is not False:
        raise ValueError("bridge event log was removed")
    topics = log.get("topics")
    if not isinstance(topics, list) or not topics or str(topics[0]).lower() != expected_topic0:
        raise ValueError("bridge event topic0 mismatch")

    receipt_logs = receipt_result.get("logs")
    if not isinstance(receipt_logs, list):
        raise ValueError("bridge receipt logs are malformed")
    matching = next(
        (
            item
            for item in receipt_logs
            if isinstance(item, dict) and item.get("logIndex") == log.get("logIndex")
        ),
        None,
    )
    if matching is None:
        raise ValueError("bridge event is not present in the receipt")
    for field in ("address", "blockHash", "transactionHash"):
        if str(matching.get(field, "")).lower() != str(log.get(field, "")).lower():
            raise ValueError(f"bridge receipt log {field} differs from the selected event")
    matching_topics = matching.get("topics")
    if not isinstance(matching_topics, list) or [str(item).lower() for item in matching_topics] != [
        str(item).lower() for item in topics
    ]:
        raise ValueError("bridge receipt log topics differ from the selected event")
    if str(matching.get("data", "")).lower() != str(log.get("data", "")).lower():
        raise ValueError("bridge receipt log data differs from the selected event")
    if str(matching.get("blockNumber", "")).lower() != str(log.get("blockNumber", "")).lower():
        raise ValueError("bridge receipt log block number differs from the selected event")
    if matching.get("removed") is not False:
        raise ValueError("bridge receipt log was removed")

    return decode(log)


def _load_pinned_artifact(
    package: Path,
    artifacts: dict[str, Any],
    pinned_sha256: dict[str, Any],
    capability: str,
) -> dict[str, Any]:
    uri = artifacts.get(capability)
    if not isinstance(uri, str) or not uri.startswith("artifact://sha256/"):
        raise ValueError(f"{capability} artifact reference is malformed")
    referenced_sha256 = uri.removeprefix("artifact://sha256/")
    expected_sha256 = pinned_sha256.get(capability)
    if not isinstance(expected_sha256, str) or expected_sha256 != referenced_sha256:
        raise ValueError(f"{capability} artifact does not match the pinned provider raw_sha256")
    artifact_path = package / "artifacts" / "sha256" / f"{referenced_sha256}.json"
    raw_bytes = artifact_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != referenced_sha256:
        raise ValueError(f"{capability} artifact content does not match its own SHA-256 name")
    value = json.loads(raw_bytes)
    if not isinstance(value, dict):
        raise ValueError(f"{capability} artifact must contain a JSON-RPC object")
    return value


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


def _verify_verification_provenance(
    evidence: dict[str, Any],
    calculated_sha256: str,
) -> None:
    provenance = _mapping(evidence, "verification_provenance")
    expected = {
        "independent_verifier_module": "src/scan_tool/application/task_016_bridge_independent_verifier.py",
        "calculated_fact_sha256": calculated_sha256,
    }
    if provenance != expected:
        raise ValueError("fixture verification provenance differs")


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


def _require_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("JSON-RPC result has an unexpected shape")
    return value


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
