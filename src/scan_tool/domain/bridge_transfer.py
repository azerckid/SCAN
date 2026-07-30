"""Strict TASK-016 bridge replay parsing and raw-first fact reconstruction."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    JsonObject,
    TransactionHash,
)

ArtifactRef = str
ProviderId = str

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_OUTPUT_TOKEN_MAP = {
    "0x4200000000000000000000000000000000000006": ("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"),
}
SOURCE_EVENT_TOPIC0 = "0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f"
DESTINATION_EVENT_TOPIC0 = "0x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7"


class BridgeTransferIncomplete(ValueError):
    """Raised when a required chain leg or artifact is unavailable."""


class BridgeChainReference(ContractModel):
    chain_id: int = Field(ge=0)
    transaction_hash: TransactionHash
    block_tag: str = Field(pattern=r"^0x(?:0|[1-9a-f][0-9a-f]*)$")
    spoke_pool: Address


class BridgeReplayChains(ContractModel):
    base: BridgeChainReference
    ethereum: BridgeChainReference


class BridgeObservationArtifacts(ContractModel):
    transaction: ArtifactRef | MISSING = MISSING
    receipt: ArtifactRef | MISSING = MISSING
    block: ArtifactRef | MISSING = MISSING
    bridge_logs: ArtifactRef | MISSING = MISSING

    @model_validator(mode="after")
    def artifact_refs_are_content_addressed(self) -> "BridgeObservationArtifacts":
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


class BridgeRawObservation(ContractModel):
    chain: Literal["base", "ethereum"]
    provider_id: ProviderId
    artifacts: BridgeObservationArtifacts


class BridgeTransferReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    capture_status: Literal["complete", "partial"]
    captured_at: ContractDatetime
    network_calls: int = Field(ge=0)
    chains: BridgeReplayChains
    methods_per_chain: list[str] = Field(min_length=1)
    raw_observations: list[BridgeRawObservation] = Field(min_length=1, max_length=2)
    reconciled_facts: JsonObject
    remaining_gate: list[str]

    @model_validator(mode="after")
    def observation_chains_are_unique(self) -> "BridgeTransferReplay":
        chains = [item.chain for item in self.raw_observations]
        if len(chains) != len(set(chains)):
            raise PydanticCustomError(
                "reconciliation_failed", "raw observation chains must be unique"
            )
        return self


def parse_bridge_transfer_replay(raw_bytes: bytes) -> BridgeTransferReplay:
    """Parse one reviewed bridge replay package."""
    return BridgeTransferReplay.model_validate_json(raw_bytes)


def reconstruct_bridge_transfer_facts(
    package: Path,
    replay: BridgeTransferReplay,
) -> dict[str, object]:
    """Re-decode both Across V3 event legs from pinned raw JSON-RPC artifacts."""
    observations = {item.chain: item for item in replay.raw_observations}
    if set(observations) != {"base", "ethereum"}:
        raise BridgeTransferIncomplete("both bridge chain legs are required")

    providers = _load_provider_pins(package / "provider-replay.json")
    source = _decode_chain_event(
        package,
        observations["base"],
        providers,
        replay.chains.base,
        SOURCE_EVENT_TOPIC0,
        _decode_v3_funds_deposited,
        require_destination_target=False,
    )
    destination = _decode_chain_event(
        package,
        observations["ethereum"],
        providers,
        replay.chains.ethereum,
        DESTINATION_EVENT_TOPIC0,
        _decode_filled_v3_relay,
        require_destination_target=True,
    )

    for key in (
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
    ):
        if source[key] != destination[key]:
            raise ValueError(f"bridge event mismatch: {key}")

    origin_chain_id = replay.chains.base.chain_id
    destination_chain_id = replay.chains.ethereum.chain_id
    if source["destination_chain_id"] != destination_chain_id:
        raise ValueError("source destination chain mismatch")
    if destination["origin_chain_id"] != origin_chain_id:
        raise ValueError("destination origin chain mismatch")

    source_output_token = source["output_token"]
    destination_output_token = destination["output_token"]
    if source_output_token == ZERO_ADDRESS:
        expected_output_token = DEFAULT_OUTPUT_TOKEN_MAP.get(str(source["input_token"]))
        if expected_output_token is None:
            raise BridgeTransferIncomplete("bridge default output token mapping is unavailable")
        if destination_output_token != expected_output_token:
            raise ValueError("bridge output asset mapping mismatch")
    elif source_output_token != destination_output_token:
        raise ValueError("bridge output asset mismatch")

    source_raw = int(str(source["input_amount_raw"]))
    destination_raw = int(str(destination["output_amount_raw"]))
    if source_raw < destination_raw:
        raise ValueError("bridge output exceeds input")

    return {
        "protocol": "across_v3",
        "origin_chain_id": origin_chain_id,
        "destination_chain_id": destination_chain_id,
        "deposit_id": source["deposit_id"],
        "source_spoke_pool": replay.chains.base.spoke_pool,
        "destination_spoke_pool": replay.chains.ethereum.spoke_pool,
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


def _load_provider_pins(path: Path) -> dict[str, dict[str, object]]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise BridgeTransferIncomplete("provider replay pins are unavailable") from error
    if not isinstance(value, dict) or not isinstance(value.get("providers"), list):
        raise ValueError("provider replay pins are malformed")
    providers: dict[str, dict[str, object]] = {}
    for item in value["providers"]:
        if not isinstance(item, dict) or not isinstance(item.get("provider_id"), str):
            raise ValueError("provider replay entry is malformed")
        providers[item["provider_id"]] = item
    return providers


def _decode_chain_event(
    package: Path,
    observation: BridgeRawObservation,
    providers: dict[str, dict[str, object]],
    chain: BridgeChainReference,
    expected_topic0: str,
    decode: object,
    *,
    require_destination_target: bool,
) -> dict[str, object]:
    provider = providers.get(observation.provider_id)
    if provider is None or not isinstance(provider.get("raw_sha256"), dict):
        raise ValueError("raw observation provider is not pinned")
    pins = provider["raw_sha256"]
    assert isinstance(pins, dict)
    artifacts = observation.artifacts
    transaction = _load_pinned_artifact(package, artifacts, pins, "transaction")
    receipt = _load_pinned_artifact(package, artifacts, pins, "receipt")
    block = _load_pinned_artifact(package, artifacts, pins, "block")
    logs_result = _load_pinned_artifact(package, artifacts, pins, "bridge_logs")

    tx = _mapping(transaction.get("result"), "transaction result")
    if _lower(tx.get("hash")) != chain.transaction_hash:
        raise ValueError("bridge transaction hash mismatch")
    if _lower(tx.get("blockNumber")) != chain.block_tag:
        raise ValueError("bridge transaction block mismatch")
    tx_block_hash = _lower(tx.get("blockHash"))

    receipt_result = _mapping(receipt.get("result"), "receipt result")
    if _lower(receipt_result.get("transactionHash")) != chain.transaction_hash:
        raise ValueError("bridge receipt transaction mismatch")
    if _lower(receipt_result.get("blockNumber")) != chain.block_tag:
        raise ValueError("bridge receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("bridge transaction was not successful")
    if _lower(receipt_result.get("blockHash")) != tx_block_hash:
        raise ValueError("bridge transaction/receipt block hash mismatch")

    block_result = _mapping(block.get("result"), "block result")
    if _lower(block_result.get("number")) != chain.block_tag:
        raise ValueError("bridge block response mismatch")
    if _lower(block_result.get("hash")) != tx_block_hash:
        raise ValueError("bridge block hash reconciliation failed")

    logs = logs_result.get("result")
    if logs is None or logs == []:
        raise BridgeTransferIncomplete("bridge event leg is unavailable")
    if not isinstance(logs, list) or len(logs) != 1:
        raise ValueError("bridge log query must return exactly one event")
    log = _mapping(logs[0], "bridge log")
    if _lower(log.get("address")) != chain.spoke_pool:
        raise ValueError("bridge event contract mismatch")
    if _lower(log.get("transactionHash")) != chain.transaction_hash:
        raise ValueError("bridge event transaction mismatch")
    if _lower(log.get("blockNumber")) != chain.block_tag:
        raise ValueError("bridge event block mismatch")
    if _lower(log.get("blockHash")) != tx_block_hash or log.get("removed") is not False:
        raise ValueError("bridge event chain binding mismatch")
    topics = log.get("topics")
    if not isinstance(topics, list) or not topics or _lower(topics[0]) != expected_topic0:
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
    for field in ("address", "blockHash", "transactionHash", "blockNumber", "data"):
        if _lower(matching.get(field)) != _lower(log.get(field)):
            raise ValueError(f"bridge receipt log {field} differs from the selected event")
    if matching.get("topics") != topics or matching.get("removed") is not False:
        raise ValueError("bridge receipt log differs from the selected event")

    if not callable(decode):
        raise TypeError("bridge event decoder is unavailable")
    decoded = decode(log)
    if not isinstance(decoded, dict):
        raise TypeError("bridge event decoder returned an invalid value")
    target = _lower(tx.get("to"))
    expected_target = chain.spoke_pool if require_destination_target else decoded["depositor"]
    if target != expected_target:
        raise ValueError("bridge transaction target mismatch")
    return decoded


def _load_pinned_artifact(
    package: Path,
    artifacts: BridgeObservationArtifacts,
    pins: dict[str, object],
    capability: str,
) -> dict[str, object]:
    uri = getattr(artifacts, capability)
    if uri is MISSING:
        raise BridgeTransferIncomplete(f"{capability} artifact is unavailable")
    referenced_sha256 = str(uri).removeprefix("artifact://sha256/")
    if pins.get(capability) != referenced_sha256:
        raise ValueError(f"{capability} artifact differs from the provider pin")
    path = package / "artifacts" / "sha256" / f"{referenced_sha256}.json"
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise BridgeTransferIncomplete(f"{capability} artifact is unavailable") from error
    if hashlib.sha256(raw_bytes).hexdigest() != referenced_sha256:
        raise ValueError(f"{capability} artifact content hash mismatch")
    try:
        value = json.loads(raw_bytes)
    except json.JSONDecodeError as error:
        raise ValueError(f"{capability} artifact JSON is malformed") from error
    return _mapping(value, f"{capability} artifact")


def _decode_v3_funds_deposited(log: dict[str, object]) -> dict[str, object]:
    topics = _topics(log, 4)
    words = _data_words(_text(log, "data"))
    if len(words) < 10:
        raise BridgeTransferIncomplete("V3FundsDeposited data is truncated")
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


def _decode_filled_v3_relay(log: dict[str, object]) -> dict[str, object]:
    topics = _topics(log, 4)
    words = _data_words(_text(log, "data"))
    if len(words) < 12:
        raise BridgeTransferIncomplete("FilledV3Relay data is truncated")
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


def _topics(log: dict[str, object], expected_count: int) -> list[str]:
    topics = log.get("topics")
    if not isinstance(topics, list) or len(topics) != expected_count:
        raise ValueError("log topics are malformed")
    if not all(isinstance(item, str) and item.startswith("0x") for item in topics):
        raise ValueError("log topics must be hex strings")
    return [item.lower() for item in topics]


def _data_words(value: str) -> list[str]:
    if not value.startswith("0x") or len(value[2:]) % 64:
        raise ValueError("log data is not word-aligned hex")
    body = value[2:]
    return [body[index : index + 64] for index in range(0, len(body), 64)]


def _dynamic_bytes(words: list[str], offset_index: int) -> str:
    offset = int(words[offset_index], 16)
    if offset % 32 or offset // 32 >= len(words):
        raise ValueError("dynamic bytes offset is invalid")
    length_index = offset // 32
    length = int(words[length_index], 16)
    body = "".join(words[length_index + 1 :])
    if length * 2 > len(body):
        raise BridgeTransferIncomplete("dynamic bytes are truncated")
    return f"0x{body[: length * 2]}"


def _address(word: str) -> str:
    if len(word) != 64:
        raise ValueError("ABI address word must contain 32 bytes")
    return f"0x{word[-40:].lower()}"


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _text(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{key} must be text")
    return item


def _lower(value: object) -> str:
    return value.lower() if isinstance(value, str) else ""
