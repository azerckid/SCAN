"""Strict TASK-016 CEX cluster replay parsing and raw-first fact reconstruction."""

import hashlib
import json
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
    NonEmptyUniqueList,
    TransactionHash,
)

ArtifactRef = str
ProviderId = str
NATIVE_ETH = "native_eth"


class CexClusterIncomplete(ValueError):
    """Raised when a required transfer leg or label artifact is unavailable."""


class ObservationWindow(ContractModel):
    start_block: BlockNumber
    end_block: BlockNumber

    @model_validator(mode="after")
    def window_is_ordered(self) -> "ObservationWindow":
        if self.end_block < self.start_block:
            raise PydanticCustomError("invalid_input", "observation window end must follow start")
        return self


class CexTransferReference(ContractModel):
    source_address: Address
    transaction_hash: TransactionHash
    block_number: BlockNumber
    block_tag: str = Field(pattern=r"^0x(?:0|[1-9a-f][0-9a-f]*)$")


class CexObservationArtifacts(ContractModel):
    transaction: ArtifactRef | MISSING = MISSING
    receipt: ArtifactRef | MISSING = MISSING
    block: ArtifactRef | MISSING = MISSING

    @model_validator(mode="after")
    def artifact_refs_are_content_addressed(self) -> "CexObservationArtifacts":
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


class CexRawObservation(ContractModel):
    transfer_index: int = Field(ge=0)
    provider_id: ProviderId
    artifacts: CexObservationArtifacts


class CexLabelProvenance(ContractModel):
    artifact_path: str = Field(min_length=1)
    source_id: str = Field(pattern=r"^DS-[A-Z0-9-]+$")


class CexClusterReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    capture_status: Literal["complete", "partial"]
    captured_at: ContractDatetime
    network_calls: int = Field(ge=0)
    chain_id: Literal[1]
    observation_window: ObservationWindow
    hot_wallet_candidate: Address
    deposit_candidates: NonEmptyUniqueList[Address]
    methods_per_transfer: list[str] = Field(min_length=1)
    transfers: list[CexTransferReference] = Field(min_length=1)
    raw_observations: list[CexRawObservation] = Field(min_length=1)
    label_provenance: CexLabelProvenance
    reconciled_facts: JsonObject
    remaining_gate: list[str]

    @model_validator(mode="after")
    def observations_match_transfers(self) -> "CexClusterReplay":
        if len(self.raw_observations) != len(self.transfers):
            raise PydanticCustomError(
                "reconciliation_failed", "raw observations must cover every transfer"
            )
        indices = [item.transfer_index for item in self.raw_observations]
        if len(indices) != len(set(indices)):
            raise PydanticCustomError(
                "reconciliation_failed", "raw observation transfer indices must be unique"
            )
        return self


def parse_cex_cluster_replay(raw_bytes: bytes) -> CexClusterReplay:
    """Parse one reviewed CEX cluster replay package."""
    return CexClusterReplay.model_validate_json(raw_bytes)


def reconstruct_cex_cluster_facts(
    package: Path,
    replay: CexClusterReplay,
) -> dict[str, object]:
    """Re-decode native ETH sweeps and gov label assertions from pinned artifacts."""
    providers = _load_provider_pins(package / "provider-replay.json")
    transfers_by_index = {index: transfer for index, transfer in enumerate(replay.transfers)}
    observations = sorted(replay.raw_observations, key=lambda item: item.transfer_index)

    decoded_transfers: list[dict[str, object]] = []
    for observation in observations:
        transfer = transfers_by_index.get(observation.transfer_index)
        if transfer is None:
            raise ValueError("raw observation transfer index is out of range")
        decoded_transfers.append(
            _decode_native_transfer(
                package,
                observation,
                providers,
                transfer,
                replay,
            )
        )

    destination = replay.hot_wallet_candidate
    destinations = {item["destination_address"] for item in decoded_transfers}
    if len(destinations) != 1 or destination not in destinations:
        raise ValueError("transfers do not share the pinned hot wallet candidate")

    deposit_sources = {item["source_address"] for item in decoded_transfers}
    if len(deposit_sources) < 2:
        raise ValueError("at least two distinct deposit sources are required")

    deposit_set = {address.lower() for address in replay.deposit_candidates}
    for source in deposit_sources:
        if source not in deposit_set:
            raise ValueError("transfer source is outside deposit_candidates")

    label_assertions = _load_label_assertions(package, replay, deposit_sources)
    covered = {item["address"] for item in label_assertions}
    if not deposit_sources <= covered:
        raise CexClusterIncomplete("gov label assertions do not cover every deposit source")

    total_raw = sum(int(str(item["raw_amount"])) for item in decoded_transfers)
    block_numbers = [int(item["block_number"]) for item in decoded_transfers]
    pattern_evidence = {
        "transfer_count": len(decoded_transfers),
        "unique_deposit_sources": len(deposit_sources),
        "block_span": max(block_numbers) - min(block_numbers),
        "classification": "confirmed_fact",
    }

    cluster_judgment = "confirmed"
    if len(deposit_sources) >= 2 and label_assertions and len(decoded_transfers) >= 2:
        cluster_judgment = "confirmed"
    elif len(decoded_transfers) >= 2:
        cluster_judgment = "estimated"
    else:
        cluster_judgment = "unresolved"

    return {
        "cluster_judgment": cluster_judgment,
        "hot_wallet_candidates": [
            {
                "address": destination,
                "classification": "evidence_backed_candidate",
                "deposit_source_count": len(deposit_sources),
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
                    f"Hot wallet candidate {destination} is not on the pinned OFAC SDN "
                    "list; ownership remains not_assessed."
                ),
            },
        ],
        "pattern_evidence": pattern_evidence,
        "attribution": {
            "exchange_ownership": "not_assessed",
            "criminality": "not_assessed",
        },
    }


def _load_provider_pins(path: Path) -> dict[str, dict[str, object]]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise CexClusterIncomplete("provider replay pins are unavailable") from error
    if not isinstance(value, dict) or not isinstance(value.get("providers"), list):
        raise ValueError("provider replay pins are malformed")
    providers: dict[str, dict[str, object]] = {}
    for item in value["providers"]:
        if not isinstance(item, dict) or not isinstance(item.get("provider_id"), str):
            raise ValueError("provider replay entry is malformed")
        providers[item["provider_id"]] = item
    return providers


def _decode_native_transfer(
    package: Path,
    observation: CexRawObservation,
    providers: dict[str, dict[str, object]],
    transfer: CexTransferReference,
    replay: CexClusterReplay,
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

    tx = _mapping(transaction.get("result"), "transaction result")
    if _lower(tx.get("hash")) != transfer.transaction_hash:
        raise ValueError("cex transaction hash mismatch")
    if _lower(tx.get("blockNumber")) != transfer.block_tag:
        raise ValueError("cex transaction block mismatch")
    if _lower(tx.get("from")) != transfer.source_address:
        raise ValueError("cex transaction source mismatch")
    if _lower(tx.get("to")) != replay.hot_wallet_candidate:
        raise ValueError("cex transaction destination mismatch")
    tx_block_hash = _lower(tx.get("blockHash"))
    raw_amount = int(str(int(str(tx.get("value")), 16)))

    receipt_result = _mapping(receipt.get("result"), "receipt result")
    if _lower(receipt_result.get("transactionHash")) != transfer.transaction_hash:
        raise ValueError("cex receipt transaction mismatch")
    if _lower(receipt_result.get("blockNumber")) != transfer.block_tag:
        raise ValueError("cex receipt block mismatch")
    if receipt_result.get("status") != "0x1":
        raise ValueError("cex transaction was not successful")
    if _lower(receipt_result.get("blockHash")) != tx_block_hash:
        raise ValueError("cex transaction/receipt block hash mismatch")
    if _lower(receipt_result.get("from")) != transfer.source_address:
        raise ValueError("cex receipt source mismatch")
    if _lower(receipt_result.get("to")) != replay.hot_wallet_candidate:
        raise ValueError("cex receipt destination mismatch")

    block_result = _mapping(block.get("result"), "block result")
    if _lower(block_result.get("number")) != transfer.block_tag:
        raise ValueError("cex block response mismatch")
    if _lower(block_result.get("hash")) != tx_block_hash:
        raise ValueError("cex block hash reconciliation failed")

    block_number = transfer.block_number
    if not (
        replay.observation_window.start_block <= block_number <= replay.observation_window.end_block
    ):
        raise ValueError("cex transfer block is outside the observation window")

    transaction_index = tx.get("transactionIndex")
    if not isinstance(transaction_index, str):
        raise ValueError("cex transaction index is malformed")

    return {
        "source_address": transfer.source_address,
        "destination_address": replay.hot_wallet_candidate,
        "asset": NATIVE_ETH,
        "raw_amount": str(raw_amount),
        "block_number": block_number,
        "transaction_hash": transfer.transaction_hash,
        "transaction_index": int(transaction_index, 16),
    }


def _load_label_assertions(
    package: Path,
    replay: CexClusterReplay,
    deposit_sources: set[str],
) -> list[dict[str, object]]:
    provenance_path = package / replay.label_provenance.artifact_path
    try:
        raw_bytes = provenance_path.read_bytes()
        value = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise CexClusterIncomplete("label provenance artifact is unavailable") from error
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

    assertions: list[dict[str, object]] = []
    for address in sorted(deposit_sources):
        if address not in listed_set:
            raise ValueError(f"deposit source {address} is missing from label provenance")
        assertions.append(
            {
                "address": address,
                "claim": entity,
                "entity": entity,
                "source_id": source_id,
                "source_url": source_url,
                "lookup_key": address,
                "classification": "evidence_backed_assertion",
            }
        )
    return assertions


def _load_pinned_artifact(
    package: Path,
    artifacts: CexObservationArtifacts,
    pins: dict[str, object],
    capability: str,
) -> dict[str, object]:
    uri = getattr(artifacts, capability)
    if uri is MISSING:
        raise CexClusterIncomplete(f"{capability} artifact is unavailable")
    referenced_sha256 = str(uri).removeprefix("artifact://sha256/")
    if pins.get(capability) != referenced_sha256:
        raise ValueError(f"{capability} artifact differs from the provider pin")
    path = package / "artifacts" / "sha256" / f"{referenced_sha256}.json"
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise CexClusterIncomplete(f"{capability} artifact is unavailable") from error
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
