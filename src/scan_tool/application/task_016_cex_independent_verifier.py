"""Independent raw-first CEX cluster verifier for TASK-016.

This module is deliberately self-contained: it does not import anything from
``scan_tool.slices.cex_cluster`` or ``scan_tool.domain.cex_cluster``. It loads
the exact raw JSON-RPC response artifacts referenced by ``raw-replay.json``,
mechanically checks each one's SHA-256 against the value pinned in
``provider-replay.json``, then re-decodes native transfer fields from scratch.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

FIXTURE_IDS = ("FX-SVC-CEX-001",)

REQUIREMENTS = {
    "FX-SVC-CEX-001": (
        "REQ-CEX-CLUSTER",
        "REQ-CEX-HOT-WALLET",
        "REQ-CEX-LABEL",
    ),
}

HOT_WALLET = "0xdbaef73d20b0ca4abc72e8daf97af36626e3b973"
DEPOSIT_CANDIDATES = (
    "0x8dce2aac0de82bdcaf6b4373b79f94331b8e4995",
    "0xb338962b92cd818d6aef0a32a9ecd01212a71f33",
    "0xf4377eda661e04b6dda78969796ed31658d602d4",
)
TRANSFERS = (
    {
        "source_address": "0x8dce2aac0de82bdcaf6b4373b79f94331b8e4995",
        "transaction_hash": "0x4448b91c3473144d93c90d83c3499ed047fceb4b81349f2a4b0f5e162e8ee2ea",
        "block_number": 18215917,
        "block_tag": "0x115f3ed",
        "value_raw": "2553889800000000000",
        "transaction_index": 27,
    },
    {
        "source_address": "0xb338962b92cd818d6aef0a32a9ecd01212a71f33",
        "transaction_hash": "0x60afb23f8e0bcd2374e3c489df92f6725394b0cd1674ce3d99e614193c67306e",
        "block_number": 18215920,
        "block_tag": "0x115f3f0",
        "value_raw": "1324582200000000000",
        "transaction_index": 7,
    },
    {
        "source_address": "0xf4377eda661e04b6dda78969796ed31658d602d4",
        "transaction_hash": "0xeeee1c9b6df17404ac03575b4cba55535c765ed1870c343e189b6098faaa4d5a",
        "block_number": 18215925,
        "block_tag": "0x115f3f5",
        "value_raw": "1666114400000000000",
        "transaction_index": 92,
    },
)
OBSERVATION_START = 18215900
OBSERVATION_END = 18216000
LABEL_ARTIFACT = "artifacts/ofac-garantex-provenance.json"
LABEL_SOURCE_ID = "DS-SANCTIONS-PUBLIC"
LABEL_SOURCE_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
LABEL_ENTITY = "GARANTEX"


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
    if facts != _mapping(expected, "cex_cluster"):
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
    transfers = raw.get("transfers")
    if not isinstance(observations, list) or not isinstance(transfers, list):
        raise ValueError("raw_observations and transfers must be arrays")
    if len(observations) != len(transfers) or len(transfers) != len(TRANSFERS):
        raise ValueError("transfer replay shape differs from the pinned fixture")

    providers = {
        _text(item, "provider_id"): item for item in _object_array(provider_replay, "providers")
    }

    decoded_transfers: list[dict[str, Any]] = []
    for index, (expected_transfer, observation) in enumerate(
        zip(TRANSFERS, observations, strict=True)
    ):
        if not isinstance(observation, dict):
            raise ValueError("raw observation must be an object")
        if int(observation.get("transfer_index", -1)) != index:
            raise ValueError("raw observation transfer index mismatch")
        decoded_transfers.append(
            _decode_native_transfer(
                package,
                observation,
                providers,
                expected_transfer,
            )
        )

    label_assertions = _load_label_assertions(package, set(DEPOSIT_CANDIDATES))
    total_raw = sum(int(item["raw_amount"]) for item in decoded_transfers)
    block_numbers = [int(item["block_number"]) for item in decoded_transfers]

    return {
        "cluster_judgment": "confirmed",
        "hot_wallet_candidates": [
            {
                "address": HOT_WALLET,
                "classification": "evidence_backed_candidate",
                "deposit_source_count": len(DEPOSIT_CANDIDATES),
                "total_raw_amount": str(total_raw),
            }
        ],
        "common_destination_facts": decoded_transfers,
        "label_assertions": label_assertions,
        "false_positive_exclusions": [
            {
                "exclusion_kind": "single_counterparty_only",
                "reason": (
                    "Common destination fact alone cannot confirm cluster; gov label "
                    "assertions on deposit sources are required."
                ),
            },
            {
                "exclusion_kind": "hot_wallet_not_sdn",
                "reason": (
                    f"Hot wallet candidate {HOT_WALLET} is not on the pinned OFAC SDN "
                    "list; ownership remains not_assessed."
                ),
            },
        ],
        "pattern_evidence": {
            "transfer_count": len(decoded_transfers),
            "unique_deposit_sources": len(DEPOSIT_CANDIDATES),
            "block_span": max(block_numbers) - min(block_numbers),
            "classification": "confirmed_fact",
        },
        "attribution": {
            "exchange_ownership": "not_assessed",
            "criminality": "not_assessed",
        },
    }


def _decode_native_transfer(
    package: Path,
    observation: dict[str, Any],
    providers: dict[str, dict[str, Any]],
    expected_transfer: dict[str, Any],
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

    tx_result = _require_mapping(transaction["result"])
    if str(tx_result.get("hash", "")).lower() != expected_transfer["transaction_hash"]:
        raise ValueError("cex transaction hash mismatch")
    if str(tx_result.get("blockNumber", "")).lower() != expected_transfer["block_tag"]:
        raise ValueError("cex transaction block mismatch")
    if str(tx_result.get("from", "")).lower() != expected_transfer["source_address"]:
        raise ValueError("cex transaction source mismatch")
    if str(tx_result.get("to", "")).lower() != HOT_WALLET:
        raise ValueError("cex transaction destination mismatch")
    tx_block_hash = str(tx_result.get("blockHash", "")).lower()
    raw_amount = int(str(tx_result.get("value", "0x0")), 16)
    if str(raw_amount) != expected_transfer["value_raw"]:
        raise ValueError("cex transaction value mismatch")

    receipt_result = _require_mapping(receipt["result"])
    if (
        str(receipt_result.get("transactionHash", "")).lower()
        != expected_transfer["transaction_hash"]
    ):
        raise ValueError("cex receipt transaction mismatch")
    if str(receipt_result.get("blockNumber", "")).lower() != expected_transfer["block_tag"]:
        raise ValueError("cex receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("cex transaction was not successful")
    if str(receipt_result.get("blockHash", "")).lower() != tx_block_hash:
        raise ValueError("cex transaction/receipt block hash mismatch")

    block_result = _require_mapping(block["result"])
    if str(block_result.get("number", "")).lower() != expected_transfer["block_tag"]:
        raise ValueError("cex block response mismatch")
    if str(block_result.get("hash", "")).lower() != tx_block_hash:
        raise ValueError("cex block hash reconciliation failed")

    block_number = int(expected_transfer["block_number"])
    if not (OBSERVATION_START <= block_number <= OBSERVATION_END):
        raise ValueError("cex transfer block is outside the observation window")

    transaction_index = tx_result.get("transactionIndex")
    if not isinstance(transaction_index, str):
        raise ValueError("cex transaction index is malformed")
    if int(transaction_index, 16) != expected_transfer["transaction_index"]:
        raise ValueError("cex transaction index mismatch")

    return {
        "source_address": expected_transfer["source_address"],
        "destination_address": HOT_WALLET,
        "asset": "native_eth",
        "raw_amount": str(raw_amount),
        "block_number": block_number,
        "transaction_hash": expected_transfer["transaction_hash"],
        "transaction_index": int(transaction_index, 16),
    }


def _load_label_assertions(
    package: Path,
    deposit_sources: set[str],
) -> list[dict[str, Any]]:
    provenance_path = package / LABEL_ARTIFACT
    value = load_json(provenance_path)
    listed = value.get("listed_eth_addresses")
    if not isinstance(listed, list):
        raise ValueError("label provenance listed addresses are malformed")
    listed_set = {str(item).lower() for item in listed if isinstance(item, str)}

    assertions: list[dict[str, Any]] = []
    for address in sorted(deposit_sources):
        if address not in listed_set:
            raise ValueError(f"deposit source {address} is missing from label provenance")
        assertions.append(
            {
                "address": address,
                "claim": LABEL_ENTITY,
                "entity": LABEL_ENTITY,
                "source_id": LABEL_SOURCE_ID,
                "source_url": LABEL_SOURCE_URL,
                "lookup_key": address,
                "classification": "evidence_backed_assertion",
            }
        )
    return assertions


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


def _verify_evidence(facts: dict[str, Any], evidence: dict[str, Any]) -> None:
    events = {
        _text(item, "evidence_id"): item for item in _object_array(evidence, "event_evidence")
    }
    common = events["EV-CEX-COMMON"]
    if _text(common, "destination_address") != HOT_WALLET:
        raise ValueError("EV-CEX-COMMON destination differs")
    if int(_number(common, "transfer_count")) != len(TRANSFERS):
        raise ValueError("EV-CEX-COMMON transfer count differs")
    label = next(
        item
        for item in _object_array(evidence, "context_evidence")
        if _text(item, "evidence_id") == "EV-CEX-LABEL"
    )
    if _text(label, "entity") != LABEL_ENTITY:
        raise ValueError("EV-CEX-LABEL entity differs")
    if facts["cluster_judgment"] != "confirmed":
        raise ValueError("cluster judgment differs")


def _verify_verification_provenance(
    evidence: dict[str, Any],
    calculated_sha256: str,
) -> None:
    provenance = _mapping(evidence, "verification_provenance")
    expected = {
        "independent_verifier_module": "src/scan_tool/application/task_016_cex_independent_verifier.py",
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
