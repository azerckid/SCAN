"""Strict TASK-016 mixer_flow replay parsing and raw-first fact reconstruction."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    BlockNumber,
    ContractDatetime,
    ContractModel,
    FixtureId,
    JsonObject,
    TransactionHash,
)

ArtifactRef = str
ProviderId = str
ProviderRole = Literal["PRIMARY", "VERIFY"]
NATIVE_ETH = "native_eth"
DEPOSIT_TOPIC0 = "0xa945e51eec50ab98c161376f0db4cf2aeba3ec92755fe2fcd388bdbbb80ff196"
WITHDRAW_TOPIC0 = "0xe9e508bad6d4c3227e881ca19068f099da81b5164dd6d62b2eaf1e8bc6c34931"
POOL_DENOMINATION = 10**17
CAPTURE_META_RELATIVE = "artifacts/capture-meta.json"
FUTURE_CAPTURE_SKEW = timedelta(minutes=5)
REQUIRED_PROVIDER_BY_ROLE: dict[ProviderRole, dict[str, str]] = {
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


class MixerFlowIncomplete(ValueError):
    """Raised when a required mixer event leg or label artifact is unavailable."""


class ObservationWindow(ContractModel):
    start_block: BlockNumber
    end_block: BlockNumber

    @model_validator(mode="after")
    def window_is_ordered(self) -> "ObservationWindow":
        if self.end_block < self.start_block:
            raise PydanticCustomError("invalid_input", "observation window end must follow start")
        return self


class MixerEventReference(ContractModel):
    event_kind: Literal["deposit", "withdraw"]
    transaction_hash: TransactionHash
    block_number: BlockNumber
    block_tag: str = Field(pattern=r"^0x(?:0|[1-9a-f][0-9a-f]*)$")
    subject_address: Address | MISSING = MISSING
    recipient_address: Address | MISSING = MISSING
    pool_address: Address
    router_address: Address | MISSING = MISSING
    raw_amount: str
    fee_raw_amount: str | MISSING = MISSING
    relayer_address: Address | MISSING = MISSING
    nullifier_hash: str | MISSING = MISSING
    asset: Literal["native_eth"] = NATIVE_ETH
    leaf_index: int | MISSING = MISSING
    deposit_timestamp: int | MISSING = MISSING
    transaction_index: int = Field(ge=0)


class MixerObservationArtifacts(ContractModel):
    transaction: ArtifactRef | MISSING = MISSING
    receipt: ArtifactRef | MISSING = MISSING
    block: ArtifactRef | MISSING = MISSING

    @model_validator(mode="after")
    def artifact_refs_are_content_addressed(self) -> "MixerObservationArtifacts":
        for name in self.model_fields_set:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("artifact://sha256/"):
                raise PydanticCustomError(
                    "invalid_input", f"{name} must be a content-addressed artifact reference"
                )
            sha256 = value.removeprefix("artifact://sha256/")
            if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
                raise PydanticCustomError("invalid_input", f"{name} artifact SHA-256 is invalid")
        return self


class MixerRawObservation(ContractModel):
    event_index: int = Field(ge=0)
    provider_id: ProviderId
    provider_role: ProviderRole
    artifacts: MixerObservationArtifacts


class MixerLabelProvenance(ContractModel):
    artifact_path: str = Field(min_length=1)
    source_id: str = Field(pattern=r"^DS-[A-Z0-9-]+$")


class MixerFlowReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    capture_status: Literal["complete", "partial"]
    captured_at: ContractDatetime
    network_calls: int = Field(ge=0)
    chain_id: Literal[1]
    observation_window: ObservationWindow
    subject_address: Address
    pool_address: Address
    deposit_topic0: str
    withdraw_topic0: str
    methods_per_event: list[str] = Field(min_length=1)
    events: list[MixerEventReference] = Field(min_length=1)
    raw_observations: list[MixerRawObservation] = Field(min_length=1)
    label_provenance: MixerLabelProvenance
    reconciled_facts: JsonObject
    remaining_gate: list[str]

    @model_validator(mode="after")
    def observations_match_events(self) -> "MixerFlowReplay":
        indices = [item.event_index for item in self.raw_observations]
        if any(index >= len(self.events) for index in indices):
            raise PydanticCustomError(
                "reconciliation_failed", "raw observation event index is out of range"
            )
        role_indices = [(item.provider_role, item.event_index) for item in self.raw_observations]
        if len(role_indices) != len(set(role_indices)):
            raise PydanticCustomError(
                "reconciliation_failed",
                "raw observation provider roles must be unique per event",
            )
        primary_indices = {
            item.event_index for item in self.raw_observations if item.provider_role == "PRIMARY"
        }
        if primary_indices != set(range(len(self.events))):
            raise PydanticCustomError(
                "reconciliation_failed", "PRIMARY observations must cover every event"
            )
        if self.events[0].event_kind != "deposit":
            raise PydanticCustomError("invalid_input", "first event must be a deposit")
        return self


def parse_mixer_flow_replay(raw_bytes: bytes) -> MixerFlowReplay:
    """Parse one reviewed mixer flow replay package."""
    return MixerFlowReplay.model_validate_json(raw_bytes)


def reconstruct_mixer_flow_facts(
    package: Path,
    replay: MixerFlowReplay,
) -> dict[str, object]:
    """Re-decode mixer pool deposit/withdraw facts and keep linkage heuristic."""
    providers = _load_provider_pins(package / "provider-replay.json")
    _validate_provider_diversity(providers)
    _reject_future_capture_timestamps(replay, providers)
    _bind_capture_meta(package, replay, providers)
    events_by_index = {index: event for index, event in enumerate(replay.events)}
    observations = sorted(replay.raw_observations, key=lambda item: item.event_index)

    decoded_by_role: dict[ProviderRole, dict[int, dict[str, object]]] = {
        "PRIMARY": {},
        "VERIFY": {},
    }
    for observation in observations:
        event = events_by_index.get(observation.event_index)
        if event is None:
            raise ValueError("raw observation event index is out of range")
        provider = providers.get(observation.provider_id)
        if provider is None or provider.get("role") != observation.provider_role:
            raise ValueError("raw observation provider role does not match its provider pin")
        decoded_by_role[observation.provider_role][observation.event_index] = _decode_mixer_event(
            package, observation, provider, event, replay
        )

    required_indices = set(events_by_index)
    for role in ("PRIMARY", "VERIFY"):
        if set(decoded_by_role[role]) != required_indices:
            raise MixerFlowIncomplete(f"{role} observations do not cover every event")

    decoded_events: list[dict[str, object]] = []
    for event_index in sorted(required_indices):
        primary = decoded_by_role["PRIMARY"][event_index]
        verify = decoded_by_role["VERIFY"][event_index]
        if primary != verify:
            raise ValueError(f"cross-provider immutable facts differ for event {event_index}")
        decoded_events.append(primary)

    deposit = next(item for item in decoded_events if item["event_kind"] == "deposit")
    withdraws = [item for item in decoded_events if item["event_kind"] == "withdraw"]
    if not withdraws:
        raise MixerFlowIncomplete("at least one withdraw event is required for candidate set")

    if deposit["subject_address"] != replay.subject_address:
        raise ValueError("deposit subject differs from replay subject_address")
    if deposit["pool_address"] != replay.pool_address:
        raise ValueError("deposit pool differs from replay pool_address")

    label_assertions = _load_label_assertions(package, replay)
    covered = {item["address"] for item in label_assertions}
    if replay.pool_address not in covered:
        raise MixerFlowIncomplete("gov label assertions do not cover the mixer pool")

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
            "asset": NATIVE_ETH,
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
            "asset": NATIVE_ETH,
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


def _load_provider_pins(path: Path) -> dict[str, dict[str, object]]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise MixerFlowIncomplete("provider replay pins are unavailable") from error
    if not isinstance(value, dict) or not isinstance(value.get("providers"), list):
        raise ValueError("provider replay pins are malformed")
    providers: dict[str, dict[str, object]] = {}
    for item in value["providers"]:
        if not isinstance(item, dict) or not isinstance(item.get("provider_id"), str):
            raise ValueError("provider replay entry is malformed")
        if item["provider_id"] in providers:
            raise ValueError("provider replay IDs must be unique")
        providers[item["provider_id"]] = item
    return providers


def _validate_provider_diversity(providers: dict[str, dict[str, object]]) -> None:
    if len(providers) != 2:
        raise MixerFlowIncomplete("exactly two independent RPC providers are required")
    roles = {provider.get("role") for provider in providers.values()}
    if roles != {"PRIMARY", "VERIFY"}:
        raise MixerFlowIncomplete("PRIMARY and VERIFY provider roles are required")
    for provider_id, provider in providers.items():
        role = provider.get("role")
        if role not in REQUIRED_PROVIDER_BY_ROLE:
            raise ValueError("provider role is invalid")
        required = REQUIRED_PROVIDER_BY_ROLE[role]  # type: ignore[index]
        if provider_id != required["provider_id"]:
            raise ValueError(f"{role} provider must be {required['provider_id']}")
        endpoint = provider.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("provider endpoint is malformed")
        if endpoint.rstrip("/").lower() != required["endpoint"].rstrip("/").lower():
            raise ValueError(f"{role} provider endpoint must be {required['endpoint']}")
    primary = next(p for p in providers.values() if p.get("role") == "PRIMARY")
    verify = next(p for p in providers.values() if p.get("role") == "VERIFY")
    primary_pins = primary.get("raw_sha256")
    verify_pins = verify.get("raw_sha256")
    if not isinstance(primary_pins, dict) or not isinstance(verify_pins, dict):
        raise ValueError("provider raw_sha256 pins are malformed")
    for index, p_pins in primary_pins.items():
        v_pins = verify_pins.get(index)
        if not isinstance(p_pins, dict) or not isinstance(v_pins, dict):
            raise MixerFlowIncomplete("provider pin coverage is incomplete")
        for capability in ("transaction", "receipt", "block"):
            if p_pins.get(capability) == v_pins.get(capability):
                raise ValueError("PRIMARY and VERIFY artifact hashes must be distinct")


def _reject_future_capture_timestamps(
    replay: MixerFlowReplay,
    providers: dict[str, dict[str, object]],
    *,
    now: datetime | None = None,
) -> None:
    deadline = (now or datetime.now(UTC)) + FUTURE_CAPTURE_SKEW
    timestamps: list[datetime] = [replay.captured_at]
    for provider in providers.values():
        retrieved_at = provider.get("retrieved_at")
        if isinstance(retrieved_at, str):
            timestamps.append(_parse_aware_datetime(retrieved_at))
        elif isinstance(retrieved_at, datetime):
            timestamps.append(
                retrieved_at if retrieved_at.tzinfo else retrieved_at.replace(tzinfo=UTC)
            )
    for value in timestamps:
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        if aware.astimezone(UTC) > deadline:
            raise ValueError("capture timestamp must not be in the future")


def _bind_capture_meta(
    package: Path,
    replay: MixerFlowReplay,
    providers: dict[str, dict[str, object]],
    *,
    now: datetime | None = None,
) -> None:
    path = package / CAPTURE_META_RELATIVE
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise MixerFlowIncomplete("capture-meta artifact is unavailable") from error
    if not isinstance(value, dict):
        raise ValueError("capture-meta artifact is malformed")
    if value.get("primary_rpc") != REQUIRED_PROVIDER_BY_ROLE["PRIMARY"]["endpoint"]:
        raise ValueError("capture-meta primary_rpc does not match PUBLICNODE")
    if value.get("verify_rpc") != REQUIRED_PROVIDER_BY_ROLE["VERIFY"]["endpoint"]:
        raise ValueError("capture-meta verify_rpc does not match MERKLE")
    meta_captured_at = value.get("captured_at")
    if not isinstance(meta_captured_at, str):
        raise ValueError("capture-meta captured_at is malformed")
    parsed_meta_captured_at = _parse_aware_datetime(meta_captured_at)
    if parsed_meta_captured_at != replay.captured_at.astimezone(UTC):
        raise ValueError("capture-meta captured_at does not match replay")
    deadline = (now or datetime.now(UTC)) + FUTURE_CAPTURE_SKEW
    if parsed_meta_captured_at > deadline:
        raise ValueError("capture timestamp must not be in the future")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError("capture-meta capabilities are malformed")
    for observation in replay.raw_observations:
        provider = providers[observation.provider_id]
        role = observation.provider_role
        required = REQUIRED_PROVIDER_BY_ROLE[role]
        if observation.provider_id != required["provider_id"]:
            raise ValueError(f"{role} observation provider_id must be {required['provider_id']}")
        endpoint = str(provider["endpoint"]).rstrip("/").lower()
        if endpoint != required["endpoint"].rstrip("/").lower():
            raise ValueError(f"{role} provider endpoint must be {required['endpoint']}")
        event = replay.events[observation.event_index]
        pins_by_event = provider.get("raw_sha256")
        if not isinstance(pins_by_event, dict):
            raise ValueError("provider raw_sha256 pins are malformed")
        pins = pins_by_event.get(str(observation.event_index))
        if not isinstance(pins, dict):
            raise MixerFlowIncomplete("provider pin coverage is incomplete")
        for capability, (key_prefix, method) in CAPABILITY_METHODS.items():
            digest = pins.get(capability)
            if not isinstance(digest, str):
                raise MixerFlowIncomplete(f"{capability} pin is unavailable")
            lookup_key = (
                f"{role}:{key_prefix}:{event.block_tag}"
                if capability == "block"
                else f"{role}:{key_prefix}:{event.transaction_hash}"
            )
            entry = capabilities.get(lookup_key)
            if not isinstance(entry, dict):
                raise ValueError(f"capture-meta is missing capability {lookup_key}")
            entry_role = entry.get("provider_role")
            entry_endpoint = entry.get("endpoint")
            entry_method = entry.get("method")
            entry_params = entry.get("params")
            response_sha = entry.get("response_sha") or entry.get("sha256")
            entry_captured_at = entry.get("captured_at")
            entry_provider_id = entry.get("provider_id")
            if entry_role != role:
                raise ValueError("capture-meta provider_role does not match observation")
            if entry_provider_id != observation.provider_id:
                raise ValueError("capture-meta provider_id does not match observation")
            if (
                not isinstance(entry_endpoint, str)
                or entry_endpoint.rstrip("/").lower() != endpoint
            ):
                raise ValueError("capture-meta endpoint does not match provider pin")
            if entry_method != method:
                raise ValueError("capture-meta method does not match capability")
            expected_params: list[object]
            if capability == "block":
                expected_params = [event.block_tag, False]
            else:
                expected_params = [event.transaction_hash]
            if entry_params != expected_params:
                raise ValueError("capture-meta params do not match capability")
            if response_sha != digest:
                raise ValueError("capture-meta response_sha does not match provider pin")
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


def _decode_mixer_event(
    package: Path,
    observation: MixerRawObservation,
    provider: dict[str, object],
    event: MixerEventReference,
    replay: MixerFlowReplay,
) -> dict[str, object]:
    if provider is None or not isinstance(provider.get("raw_sha256"), dict):
        raise ValueError("raw observation provider is not pinned")
    pins_by_event = provider["raw_sha256"]
    assert isinstance(pins_by_event, dict)
    pins = pins_by_event.get(str(observation.event_index))
    if not isinstance(pins, dict):
        raise MixerFlowIncomplete(
            f"{observation.provider_role} pins are unavailable for event {observation.event_index}"
        )
    artifacts = observation.artifacts
    transaction = _load_pinned_artifact(package, artifacts, pins, "transaction")
    receipt = _load_pinned_artifact(package, artifacts, pins, "receipt")
    block = _load_pinned_artifact(package, artifacts, pins, "block")

    tx = _mapping(transaction.get("result"), "transaction result")
    if _lower(tx.get("hash")) != event.transaction_hash:
        raise ValueError("mixer transaction hash mismatch")
    if _lower(tx.get("blockNumber")) != event.block_tag:
        raise ValueError("mixer transaction block mismatch")
    tx_block_hash = _lower(tx.get("blockHash"))

    receipt_result = _mapping(receipt.get("result"), "receipt result")
    if _lower(receipt_result.get("transactionHash")) != event.transaction_hash:
        raise ValueError("mixer receipt transaction mismatch")
    if _lower(receipt_result.get("blockNumber")) != event.block_tag:
        raise ValueError("mixer receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("mixer transaction was not successful")
    if _lower(receipt_result.get("blockHash")) != tx_block_hash:
        raise ValueError("mixer transaction/receipt block hash mismatch")

    block_result = _mapping(block.get("result"), "block result")
    if _lower(block_result.get("number")) != event.block_tag:
        raise ValueError("mixer block response mismatch")
    if _lower(block_result.get("hash")) != tx_block_hash:
        raise ValueError("mixer block hash reconciliation failed")

    block_number = event.block_number
    if not (
        replay.observation_window.start_block <= block_number <= replay.observation_window.end_block
    ):
        raise ValueError("mixer event block is outside the observation window")

    logs = receipt_result.get("logs")
    if not isinstance(logs, list):
        raise ValueError("mixer receipt logs are malformed")
    pool = replay.pool_address
    transaction_index = tx.get("transactionIndex")
    if not isinstance(transaction_index, str):
        raise ValueError("mixer transaction index is malformed")

    if event.event_kind == "deposit":
        deposit_logs = [
            item
            for item in logs
            if isinstance(item, dict)
            and _lower(item.get("address")) == pool
            and _lower((item.get("topics") or [None])[0]) == DEPOSIT_TOPIC0
        ]
        if not deposit_logs:
            raise ValueError("deposit event log is missing")
        data = str(deposit_logs[0].get("data") or "")
        leaf_index = int(data[2:66], 16)
        subject = _lower(tx.get("from"))
        if subject != replay.subject_address:
            raise ValueError("deposit subject mismatch")
        raw_amount = str(int(str(tx.get("value")), 16))
        if int(raw_amount) != POOL_DENOMINATION:
            raise ValueError("deposit amount is not the pool denomination")
        return {
            "event_kind": "deposit",
            "subject_address": subject,
            "pool_address": pool,
            "router_address": _lower(tx.get("to")),
            "transaction_hash": event.transaction_hash,
            "block_number": block_number,
            "raw_amount": raw_amount,
            "leaf_index": leaf_index,
            "transaction_index": int(transaction_index, 16),
        }

    withdraw_logs = [
        item
        for item in logs
        if isinstance(item, dict)
        and _lower(item.get("address")) == pool
        and _lower((item.get("topics") or [None])[0]) == WITHDRAW_TOPIC0
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
        "pool_address": pool,
        "transaction_hash": event.transaction_hash,
        "block_number": block_number,
        "raw_amount": str(POOL_DENOMINATION),
        "fee_raw_amount": fee,
        "relayer_address": relayer,
        "nullifier_hash": nullifier,
        "transaction_index": int(transaction_index, 16),
    }


def _load_label_assertions(
    package: Path,
    replay: MixerFlowReplay,
) -> list[dict[str, object]]:
    provenance_path = package / replay.label_provenance.artifact_path
    try:
        raw_bytes = provenance_path.read_bytes()
        value = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise MixerFlowIncomplete("label provenance artifact is unavailable") from error
    if not isinstance(value, dict):
        raise ValueError("label provenance artifact is malformed")
    listed = value.get("listed_eth_addresses")
    if not isinstance(listed, list):
        raise ValueError("label provenance listed addresses are malformed")
    listed_set = {str(item).lower() for item in listed if isinstance(item, str)}
    entity = value.get("entity")
    source_url = value.get("source_url")
    source_id = replay.label_provenance.source_id
    if not isinstance(entity, str) or not isinstance(source_url, str):
        raise ValueError("label provenance entity metadata is malformed")
    if replay.pool_address not in listed_set:
        raise ValueError("mixer pool is missing from label provenance")
    return [
        {
            "address": replay.pool_address,
            "claim": entity,
            "entity": entity,
            "source_id": source_id,
            "source_url": source_url,
            "lookup_key": replay.pool_address,
            "classification": "evidence_backed_assertion",
        }
    ]


def _load_pinned_artifact(
    package: Path,
    artifacts: MixerObservationArtifacts,
    pins: dict[str, object],
    capability: str,
) -> dict[str, object]:
    uri = getattr(artifacts, capability)
    if uri is MISSING:
        raise MixerFlowIncomplete(f"{capability} artifact is unavailable")
    referenced_sha256 = str(uri).removeprefix("artifact://sha256/")
    if pins.get(capability) != referenced_sha256:
        raise ValueError(f"{capability} artifact differs from the provider pin")
    path = package / "artifacts" / "sha256" / f"{referenced_sha256}.json"
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise MixerFlowIncomplete(f"{capability} artifact is unavailable") from error
    if hashlib.sha256(raw_bytes).hexdigest() != referenced_sha256:
        raise ValueError(f"{capability} artifact content hash mismatch")
    try:
        value = json.loads(raw_bytes)
    except json.JSONDecodeError as error:
        raise ValueError(f"{capability} artifact JSON is malformed") from error
    return _mapping(value, f"{capability} artifact")


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _lower(value: object) -> str:
    return value.lower() if isinstance(value, str) else ""
