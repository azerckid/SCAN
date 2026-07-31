"""Independent raw-first mixer flow verifier for TASK-016.

This module is deliberately self-contained: it does not import anything from
``scan_tool.slices.mixer_flow`` or ``scan_tool.domain.mixer_flow``. It loads
the exact raw JSON-RPC response artifacts referenced by ``raw-replay.json``,
mechanically checks each one's SHA-256 against the value pinned in
``provider-replay.json``, then re-decodes mixer deposit/withdraw fields from scratch.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

FIXTURE_IDS = ("FX-SVC-MIX-001",)

REQUIREMENTS = {
    "FX-SVC-MIX-001": (
        "REQ-MIX-DEPOSIT",
        "REQ-MIX-WITHDRAW-CANDIDATES",
        "REQ-MIX-LABEL",
    ),
}

SUBJECT_ADDRESS = "0xe1fe63b019ddac3a448f97a3c0c21df9c3613893"
POOL_ADDRESS = "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc"
EVENTS = (
    {
        "event_kind": "deposit",
        "transaction_hash": "0xc716eec2c710b22840d0cd877a61a83e9aacf628c79843a9505d53fa2e33f483",
        "block_number": 25304911,
        "block_tag": "0x1821f4f",
        "router_address": "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
        "leaf_index": 56342,
        "transaction_index": 48,
    },
    {
        "event_kind": "withdraw",
        "transaction_hash": "0x2258d635180427608598a4ab208c440a4599db8923fd3678937285afcc2ef984",
        "block_number": 25305908,
        "block_tag": "0x1822334",
        "recipient_address": "0x3a6dd0c31d0868c8329b648061fd63f1c95535b4",
        "fee_raw_amount": "2147163212600000",
        "relayer_address": "0x4750bcfcc340aa4b31be7e71fa072716d28c29c5",
        "nullifier_hash": "0x26ea6d6c1795ddd31660ec9a8c068aa25bd0afdf8403e0e07601c52a3be9f055",
        "transaction_index": 49,
    },
    {
        "event_kind": "withdraw",
        "transaction_hash": "0x8232b56f4c4f4af74a5e25d150ac21a9c150601d5891dbb12891df6fa6669a5d",
        "block_number": 25305914,
        "block_tag": "0x182233a",
        "recipient_address": "0x3a6dd0c31d0868c8329b648061fd63f1c95535b4",
        "fee_raw_amount": "2146984842100000",
        "relayer_address": "0x4750bcfcc340aa4b31be7e71fa072716d28c29c5",
        "nullifier_hash": "0x2c349e843391d2501343c69e00a0ca316153d262bcf90ce857ec079baea02af5",
        "transaction_index": 0,
    },
)
OBSERVATION_START = 25304911
OBSERVATION_END = 25305914
LABEL_ARTIFACT = "artifacts/ofac-tornado-provenance.json"
LABEL_SOURCE_ID = "DS-SANCTIONS-PUBLIC"
LABEL_SOURCE_URL = "https://home.treasury.gov/news/press-releases/jy0916"
LABEL_ENTITY = "Tornado Cash"
DEPOSIT_TOPIC0 = "0xa945e51eec50ab98c161376f0db4cf2aeba3ec92755fe2fcd388bdbbb80ff196"
WITHDRAW_TOPIC0 = "0xe9e508bad6d4c3227e881ca19068f099da81b5164dd6d62b2eaf1e8bc6c34931"
POOL_DENOMINATION = 10**17
CAPTURE_META_RELATIVE = "artifacts/capture-meta.json"
FUTURE_CAPTURE_SKEW = timedelta(minutes=5)
REQUIRED_PROVIDER_BY_ROLE = {
    "PRIMARY": {
        "provider_id": "PROVIDER-ETHEREUM-PUBLICNODE",
        "endpoint": "https://ethereum-rpc.publicnode.com",
    },
    "VERIFY": {
        "provider_id": "PROVIDER-ETHEREUM-MERKLE",
        "endpoint": "https://eth.merkle.io",
    },
}
CAPABILITY_METHODS = {
    "transaction": ("tx", "eth_getTransactionByHash"),
    "receipt": ("receipt", "eth_getTransactionReceipt"),
    "block": ("block", "eth_getBlockByNumber"),
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
    if facts != _mapping(expected, "mixer_flow"):
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
    if not isinstance(observations, list):
        raise ValueError("raw_observations must be an array")
    if len(EVENTS) != 3:
        raise ValueError("mixer event replay shape differs from the pinned fixture")

    providers = {
        _text(item, "provider_id"): item for item in _object_array(provider_replay, "providers")
    }
    _verify_provider_diversity(providers)
    _reject_future_capture_timestamps(raw, providers)
    _bind_capture_meta(package, raw, providers)

    decoded_by_role: dict[str, dict[int, dict[str, Any]]] = {"PRIMARY": {}, "VERIFY": {}}
    seen_role_indices: set[tuple[str, int]] = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError("raw observation must be an object")
        event_index = int(observation.get("event_index", -1))
        if event_index not in range(len(EVENTS)):
            raise ValueError("raw observation event index mismatch")
        role = _text(observation, "provider_role")
        if role not in decoded_by_role:
            raise ValueError("raw observation provider role is invalid")
        if (role, event_index) in seen_role_indices:
            raise ValueError("provider role is duplicated for an event")
        seen_role_indices.add((role, event_index))
        provider_id = _text(observation, "provider_id")
        required = REQUIRED_PROVIDER_BY_ROLE[role]
        if provider_id != required["provider_id"]:
            raise ValueError(f"{role} observation provider_id must be {required['provider_id']}")
        provider = providers.get(provider_id)
        if provider is None or _text(provider, "role") != role:
            raise ValueError("raw observation provider role differs from its pin")
        decoded_by_role[role][event_index] = _decode_mixer_event(
            package,
            observation,
            provider,
            EVENTS[event_index],
        )

    required_indices = set(range(len(EVENTS)))
    for role in ("PRIMARY", "VERIFY"):
        if set(decoded_by_role[role]) != required_indices:
            raise ValueError(f"{role} observations do not cover every event")

    decoded_events = []
    for event_index in sorted(required_indices):
        primary = decoded_by_role["PRIMARY"][event_index]
        verify = decoded_by_role["VERIFY"][event_index]
        if primary != verify:
            raise ValueError(f"cross-provider immutable facts differ for event {event_index}")
        decoded_events.append(primary)

    deposit = next(item for item in decoded_events if item["event_kind"] == "deposit")
    withdraws = [item for item in decoded_events if item["event_kind"] == "withdraw"]
    if not withdraws:
        raise ValueError("at least one withdraw event is required")

    label_assertions = _load_label_assertions(package)
    withdraw_event_facts = [
        {
            "recipient_address": item["recipient_address"],
            "pool_address": item["pool_address"],
            "transaction_hash": item["transaction_hash"],
            "block_number": item["block_number"],
            "raw_amount": item["raw_amount"],
            "fee_raw_amount": item["fee_raw_amount"],
            "relayer_address": item["relayer_address"],
            "nullifier_hash": item["nullifier_hash"],
            "asset": "native_eth",
            "transaction_index": item["transaction_index"],
            "classification": "confirmed_fact",
        }
        for item in withdraws
    ]
    withdraw_candidates = [
        {
            "recipient_address": item["recipient_address"],
            "transaction_hash": item["transaction_hash"],
            "block_number": item["block_number"],
            "raw_amount": item["raw_amount"],
            "fee_raw_amount": item["fee_raw_amount"],
            "relayer_address": item["relayer_address"],
            "linkage_strength": "candidate",
            "classification": "heuristic_candidate",
            "reason": (
                "Amount/time-window pool withdraw is a candidate only; "
                "deposit↔withdraw ownership is not on-chain proven."
            ),
        }
        for item in withdraws
    ]

    return {
        "pool_flow_judgment": "confirmed",
        "deposit_fact": {
            "subject_address": deposit["subject_address"],
            "pool_address": deposit["pool_address"],
            "router_address": deposit["router_address"],
            "transaction_hash": deposit["transaction_hash"],
            "block_number": deposit["block_number"],
            "raw_amount": deposit["raw_amount"],
            "asset": "native_eth",
            "leaf_index": deposit["leaf_index"],
            "transaction_index": deposit["transaction_index"],
            "classification": "confirmed_fact",
        },
        "withdraw_event_facts": withdraw_event_facts,
        "withdraw_candidates": withdraw_candidates,
        "unresolvable_reasons": [
            "deposit_withdraw_ownership_link_not_provable_onchain",
            "single_exit_must_not_be_promoted_to_confirmed_ownership",
        ],
        "label_assertions": label_assertions,
        "false_positive_exclusions": [
            {
                "exclusion_kind": "single_exit_ownership",
                "reason": (
                    "A single matching-denomination withdraw cannot confirm ownership "
                    "of the deposit note."
                ),
            },
            {
                "exclusion_kind": "mixer_criminality",
                "reason": (
                    "OFAC pool label is an assertion about the contract, not a criminality "
                    "judgment of counterparties."
                ),
            },
        ],
        "attribution": {
            "ownership": "not_assessed",
            "criminality": "not_assessed",
        },
    }


def _decode_mixer_event(
    package: Path,
    observation: dict[str, Any],
    provider: dict[str, Any],
    expected_event: dict[str, Any],
) -> dict[str, Any]:
    event_index = int(observation.get("event_index", -1))
    pinned_by_event = _mapping(provider, "raw_sha256")
    pinned_sha256 = pinned_by_event.get(str(event_index))
    if not isinstance(pinned_sha256, dict):
        raise ValueError("provider SHA pins do not cover the observation event")
    artifacts = _mapping(observation, "artifacts")

    transaction = _load_pinned_artifact(package, artifacts, pinned_sha256, "transaction")
    receipt = _load_pinned_artifact(package, artifacts, pinned_sha256, "receipt")
    block = _load_pinned_artifact(package, artifacts, pinned_sha256, "block")

    tx_result = _require_mapping(transaction["result"])
    if str(tx_result.get("hash", "")).lower() != expected_event["transaction_hash"]:
        raise ValueError("mixer transaction hash mismatch")
    if str(tx_result.get("blockNumber", "")).lower() != expected_event["block_tag"]:
        raise ValueError("mixer transaction block mismatch")
    tx_block_hash = str(tx_result.get("blockHash", "")).lower()

    receipt_result = _require_mapping(receipt["result"])
    if str(receipt_result.get("transactionHash", "")).lower() != expected_event["transaction_hash"]:
        raise ValueError("mixer receipt transaction mismatch")
    if str(receipt_result.get("blockNumber", "")).lower() != expected_event["block_tag"]:
        raise ValueError("mixer receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("mixer transaction was not successful")
    if str(receipt_result.get("blockHash", "")).lower() != tx_block_hash:
        raise ValueError("mixer transaction/receipt block hash mismatch")

    block_result = _require_mapping(block["result"])
    if str(block_result.get("number", "")).lower() != expected_event["block_tag"]:
        raise ValueError("mixer block response mismatch")
    if str(block_result.get("hash", "")).lower() != tx_block_hash:
        raise ValueError("mixer block hash reconciliation failed")

    block_number = int(expected_event["block_number"])
    if not (OBSERVATION_START <= block_number <= OBSERVATION_END):
        raise ValueError("mixer event block is outside the observation window")

    logs = receipt_result.get("logs")
    if not isinstance(logs, list):
        raise ValueError("mixer receipt logs are malformed")
    transaction_index = tx_result.get("transactionIndex")
    if not isinstance(transaction_index, str):
        raise ValueError("mixer transaction index is malformed")

    if expected_event["event_kind"] == "deposit":
        deposit_logs = [
            item
            for item in logs
            if isinstance(item, dict)
            and str(item.get("address", "")).lower() == POOL_ADDRESS
            and str((item.get("topics") or [None])[0]).lower() == DEPOSIT_TOPIC0
        ]
        if not deposit_logs:
            raise ValueError("deposit event log is missing")
        data = str(deposit_logs[0].get("data") or "")
        leaf_index = int(data[2:66], 16)
        subject = str(tx_result.get("from", "")).lower()
        if subject != SUBJECT_ADDRESS:
            raise ValueError("deposit subject mismatch")
        raw_amount = str(int(str(tx_result.get("value", "0x0")), 16))
        if int(raw_amount) != POOL_DENOMINATION:
            raise ValueError("deposit amount is not the pool denomination")
        return {
            "event_kind": "deposit",
            "subject_address": subject,
            "pool_address": POOL_ADDRESS,
            "router_address": str(tx_result.get("to", "")).lower(),
            "transaction_hash": expected_event["transaction_hash"],
            "block_number": block_number,
            "raw_amount": raw_amount,
            "leaf_index": leaf_index,
            "transaction_index": int(transaction_index, 16),
        }

    withdraw_logs = [
        item
        for item in logs
        if isinstance(item, dict)
        and str(item.get("address", "")).lower() == POOL_ADDRESS
        and str((item.get("topics") or [None])[0]).lower() == WITHDRAW_TOPIC0
    ]
    if not withdraw_logs:
        raise ValueError("withdraw event log is missing")
    log = withdraw_logs[0]
    data = str(log.get("data") or "")
    recipient = "0x" + data[26:66]
    nullifier = "0x" + data[66:130]
    fee = str(int(data[130:194], 16))
    topics = log.get("topics")
    relayer = None
    if isinstance(topics, list) and len(topics) > 1 and isinstance(topics[1], str):
        relayer = "0x" + topics[1][-40:]
    return {
        "event_kind": "withdraw",
        "recipient_address": recipient,
        "pool_address": POOL_ADDRESS,
        "transaction_hash": expected_event["transaction_hash"],
        "block_number": block_number,
        "raw_amount": str(POOL_DENOMINATION),
        "fee_raw_amount": fee,
        "relayer_address": relayer,
        "nullifier_hash": nullifier,
        "transaction_index": int(transaction_index, 16),
    }


def _verify_provider_diversity(providers: dict[str, dict[str, Any]]) -> None:
    if len(providers) != 2:
        raise ValueError("exactly two independent RPC providers are required")
    roles = {_text(provider, "role") for provider in providers.values()}
    if roles != {"PRIMARY", "VERIFY"}:
        raise ValueError("PRIMARY and VERIFY provider roles are required")
    for provider_id, provider in providers.items():
        role = _text(provider, "role")
        required = REQUIRED_PROVIDER_BY_ROLE[role]
        if provider_id != required["provider_id"]:
            raise ValueError(f"{role} provider must be {required['provider_id']}")
        endpoint = _text(provider, "endpoint").rstrip("/").lower()
        if endpoint != required["endpoint"].rstrip("/").lower():
            raise ValueError(f"{role} provider endpoint must be {required['endpoint']}")
    primary = next(p for p in providers.values() if _text(p, "role") == "PRIMARY")
    verify = next(p for p in providers.values() if _text(p, "role") == "VERIFY")
    primary_pins = _mapping(primary, "raw_sha256")
    verify_pins = _mapping(verify, "raw_sha256")
    for index, p_pins in primary_pins.items():
        v_pins = verify_pins.get(index)
        if not isinstance(p_pins, dict) or not isinstance(v_pins, dict):
            raise ValueError("provider pin coverage is incomplete")
        for capability in ("transaction", "receipt", "block"):
            if p_pins.get(capability) == v_pins.get(capability):
                raise ValueError("PRIMARY and VERIFY artifact hashes must be distinct")


def _reject_future_capture_timestamps(
    raw: dict[str, Any],
    providers: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
) -> None:
    deadline = (now or datetime.now(UTC)) + FUTURE_CAPTURE_SKEW
    timestamps = [_parse_aware_datetime(_text(raw, "captured_at"))]
    for provider in providers.values():
        retrieved_at = provider.get("retrieved_at")
        if isinstance(retrieved_at, str):
            timestamps.append(_parse_aware_datetime(retrieved_at))
    for value in timestamps:
        if value > deadline:
            raise ValueError("capture timestamp must not be in the future")


def _bind_capture_meta(
    package: Path,
    raw: dict[str, Any],
    providers: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
) -> None:
    meta = load_json(package / CAPTURE_META_RELATIVE)
    if meta.get("primary_rpc") != REQUIRED_PROVIDER_BY_ROLE["PRIMARY"]["endpoint"]:
        raise ValueError("capture-meta primary_rpc does not match PUBLICNODE")
    if meta.get("verify_rpc") != REQUIRED_PROVIDER_BY_ROLE["VERIFY"]["endpoint"]:
        raise ValueError("capture-meta verify_rpc does not match MERKLE")
    meta_captured_at = _parse_aware_datetime(_text(meta, "captured_at"))
    if meta_captured_at != _parse_aware_datetime(_text(raw, "captured_at")):
        raise ValueError("capture-meta captured_at does not match replay")
    deadline = (now or datetime.now(UTC)) + FUTURE_CAPTURE_SKEW
    if meta_captured_at > deadline:
        raise ValueError("capture timestamp must not be in the future")
    capabilities = meta.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError("capture-meta capabilities are malformed")
    observations = raw.get("raw_observations")
    if not isinstance(observations, list):
        raise ValueError("raw_observations must be an array")
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError("raw observation must be an object")
        role = _text(observation, "provider_role")
        provider_id = _text(observation, "provider_id")
        required = REQUIRED_PROVIDER_BY_ROLE[role]
        if provider_id != required["provider_id"]:
            raise ValueError(f"{role} observation provider_id must be {required['provider_id']}")
        provider = providers[provider_id]
        endpoint = _text(provider, "endpoint").rstrip("/").lower()
        event_index = int(observation.get("event_index", -1))
        event = EVENTS[event_index]
        pins = _mapping(provider, "raw_sha256").get(str(event_index))
        if not isinstance(pins, dict):
            raise ValueError("provider pin coverage is incomplete")
        for capability, (key_prefix, method) in CAPABILITY_METHODS.items():
            digest = pins.get(capability)
            if not isinstance(digest, str):
                raise ValueError(f"{capability} pin is unavailable")
            lookup_key = (
                f"{role}:{key_prefix}:{event['block_tag']}"
                if capability == "block"
                else f"{role}:{key_prefix}:{event['transaction_hash']}"
            )
            entry = capabilities.get(lookup_key)
            if not isinstance(entry, dict):
                raise ValueError(f"capture-meta is missing capability {lookup_key}")
            if entry.get("provider_role") != role:
                raise ValueError("capture-meta provider_role does not match observation")
            if entry.get("provider_id") != provider_id:
                raise ValueError("capture-meta provider_id does not match observation")
            entry_endpoint = entry.get("endpoint")
            if (
                not isinstance(entry_endpoint, str)
                or entry_endpoint.rstrip("/").lower() != endpoint
            ):
                raise ValueError("capture-meta endpoint does not match provider pin")
            if entry.get("method") != method:
                raise ValueError("capture-meta method does not match capability")
            expected_params: list[object]
            if capability == "block":
                expected_params = [event["block_tag"], False]
            else:
                expected_params = [event["transaction_hash"]]
            if entry.get("params") != expected_params:
                raise ValueError("capture-meta params do not match capability")
            response_sha = entry.get("response_sha") or entry.get("sha256")
            if response_sha != digest:
                raise ValueError("capture-meta response_sha does not match provider pin")
            entry_captured_at = entry.get("captured_at")
            if not isinstance(entry_captured_at, str):
                raise ValueError("capture-meta capability captured_at is malformed")
            if _parse_aware_datetime(entry_captured_at) > deadline:
                raise ValueError("capture timestamp must not be in the future")


def _parse_aware_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("capture timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _load_label_assertions(package: Path) -> list[dict[str, Any]]:
    provenance_path = package / LABEL_ARTIFACT
    value = load_json(provenance_path)
    listed = value.get("listed_eth_addresses")
    if not isinstance(listed, list):
        raise ValueError("label provenance listed addresses are malformed")
    listed_set = {str(item).lower() for item in listed if isinstance(item, str)}
    entity = value.get("entity")
    source_url = value.get("source_url")
    if not isinstance(entity, str) or not isinstance(source_url, str):
        raise ValueError("label provenance entity metadata is malformed")
    if POOL_ADDRESS not in listed_set:
        raise ValueError("mixer pool is missing from label provenance")
    return [
        {
            "address": POOL_ADDRESS,
            "claim": entity,
            "entity": entity,
            "source_id": LABEL_SOURCE_ID,
            "source_url": source_url,
            "lookup_key": POOL_ADDRESS,
            "classification": "evidence_backed_assertion",
        }
    ]


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
    deposit = events["EV-MIX-DEPOSIT"]
    if _text(deposit, "subject_address") != SUBJECT_ADDRESS:
        raise ValueError("EV-MIX-DEPOSIT subject differs")
    if _text(deposit, "pool_address") != POOL_ADDRESS:
        raise ValueError("EV-MIX-DEPOSIT pool differs")
    withdraw_events = events["EV-MIX-WITHDRAW-EVENTS"]
    if int(withdraw_events["withdraw_event_count"]) != 2:
        raise ValueError("EV-MIX-WITHDRAW-EVENTS count differs")
    label = next(
        item
        for item in _object_array(evidence, "context_evidence")
        if _text(item, "evidence_id") == "EV-MIX-LABEL"
    )
    if _text(label, "entity") != LABEL_ENTITY:
        raise ValueError("EV-MIX-LABEL entity differs")
    if facts["pool_flow_judgment"] != "confirmed":
        raise ValueError("pool flow judgment differs")


def _verify_verification_provenance(
    evidence: dict[str, Any],
    calculated_sha256: str,
) -> None:
    provenance = _mapping(evidence, "verification_provenance")
    expected = {
        "independent_verifier_module": "src/scan_tool/application/task_016_mixer_independent_verifier.py",
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
