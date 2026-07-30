"""Strict reviewed-replay contract for Bitcoin UTXO analysis."""

import json
from typing import Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    BitcoinTxId,
    ContractDatetime,
    ContractModel,
    NonEmptyString,
    NonEmptyUniqueList,
    NonNegativeInt,
    ProviderId,
    Sha256,
)


class BitcoinPrevout(ContractModel):
    transaction_id: BitcoinTxId
    vout: NonNegativeInt
    value_sat: NonNegativeInt
    script_type: NonEmptyString
    address: NonEmptyString


class BitcoinInput(ContractModel):
    prevout: BitcoinPrevout
    sequence: NonNegativeInt


class BitcoinOutput(ContractModel):
    vout: NonNegativeInt
    value_sat: NonNegativeInt
    script_type: NonEmptyString
    address: NonEmptyString


class BitcoinProviderObservation(ContractModel):
    provider_id: ProviderId
    role: Literal["primary", "verify", "supporting"]
    retrieved_at: ContractDatetime
    artifact_file: NonEmptyString
    artifact_sha256: Sha256
    decoded_match: Literal[True]


class BitcoinTransactionReplay(ContractModel):
    transaction_id: BitcoinTxId
    network: Literal["bitcoin_mainnet"]
    block_height: NonNegativeInt
    block_hash: BitcoinTxId
    block_time: NonNegativeInt
    fee_sat: NonNegativeInt
    inputs: list[BitcoinInput] = Field(min_length=1)
    outputs: list[BitcoinOutput] = Field(min_length=1)
    providers: list[BitcoinProviderObservation] = Field(min_length=2)

    @model_validator(mode="after")
    def transaction_is_reconciled(self) -> "BitcoinTransactionReplay":
        if [item.vout for item in self.outputs] != list(range(len(self.outputs))):
            raise PydanticCustomError("reconciliation_failed", "output indexes must be contiguous")
        outpoints = [(item.prevout.transaction_id, item.prevout.vout) for item in self.inputs]
        if len(outpoints) != len(set(outpoints)):
            raise PydanticCustomError("reconciliation_failed", "spent outpoints must be unique")
        input_sum = sum(item.prevout.value_sat for item in self.inputs)
        output_sum = sum(item.value_sat for item in self.outputs)
        if input_sum - output_sum != self.fee_sat:
            raise PydanticCustomError("reconciliation_failed", "input-output fee equation differs")
        roles = {item.role for item in self.providers}
        if not {"primary", "verify"} <= roles:
            raise PydanticCustomError(
                "source_unavailable",
                "primary and verify Bitcoin observations are required",
            )
        return self


class BitcoinSpendHop(ContractModel):
    depth: NonNegativeInt
    spent_transaction_id: BitcoinTxId
    spent_vout: NonNegativeInt
    spent_value_sat: NonNegativeInt
    spending_transaction_id: BitcoinTxId
    spending_vin: NonNegativeInt
    block_height: NonNegativeInt
    fee_sat: NonNegativeInt
    created_outputs: list[BitcoinOutput] = Field(min_length=1)
    providers: list[BitcoinProviderObservation] = Field(min_length=2)

    @model_validator(mode="after")
    def provider_roles_are_distinct(self) -> "BitcoinSpendHop":
        if len({item.provider_id for item in self.providers}) != len(self.providers):
            raise PydanticCustomError("invalid_input", "hop provider IDs must be distinct")
        if {item.role for item in self.providers} != {"primary", "verify"}:
            raise PydanticCustomError("invalid_input", "hop requires primary and verify")
        return self


class BitcoinUtxoReplay(ContractModel):
    replay_version: Literal["0.1"]
    fixture_id: Literal["FX-BTC-UTXO-001"]
    observations_complete: Literal[True]
    transaction: BitcoinTransactionReplay
    spend_path: list[BitcoinSpendHop]
    source_ids: NonEmptyUniqueList[str]

    @model_validator(mode="after")
    def replay_bindings_are_exact(self) -> "BitcoinUtxoReplay":
        providers = self.transaction.providers
        if len({item.provider_id for item in providers}) != len(providers):
            raise PydanticCustomError("invalid_input", "provider IDs must be distinct")
        required = [item for item in providers if item.role in {"primary", "verify"}]
        if {item.role for item in required} != {"primary", "verify"} or len(required) != 2:
            raise PydanticCustomError(
                "invalid_input", "exactly one primary and verify are required"
            )
        previous_transaction_id = self.transaction.transaction_id
        previous_outputs = self.transaction.outputs
        for expected_depth, hop in enumerate(self.spend_path, start=1):
            if hop.depth != expected_depth:
                raise PydanticCustomError(
                    "reconciliation_failed",
                    "spend path depths must be contiguous",
                )
            if hop.spent_transaction_id != previous_transaction_id:
                raise PydanticCustomError("reconciliation_failed", "spend path chain differs")
            output = next(
                (item for item in previous_outputs if item.vout == hop.spent_vout),
                None,
            )
            if output is None or output.value_sat != hop.spent_value_sat:
                raise PydanticCustomError("reconciliation_failed", "spent output differs")
            previous_transaction_id = hop.spending_transaction_id
            previous_outputs = hop.created_outputs
        return self


def parse_bitcoin_utxo_replay(raw: bytes) -> BitcoinUtxoReplay:
    """Parse a reviewed Bitcoin replay without logging raw bytes."""
    value = json.loads(raw)
    return BitcoinUtxoReplay.model_validate(value)


def reconstruct_bitcoin_facts(
    replay: BitcoinUtxoReplay,
    *,
    start_vout: int,
    max_hops: int,
) -> dict[str, object]:
    """Recompute deterministic UTXO facts from prevouts and outputs."""
    tx = replay.transaction
    input_sum = sum(item.prevout.value_sat for item in tx.inputs)
    output_sum = sum(item.value_sat for item in tx.outputs)
    selected = [
        item
        for item in replay.spend_path
        if item.depth <= max_hops and (item.depth > 1 or item.spent_vout == start_vout)
    ]
    path = [
        {
            "depth": item.depth,
            "spent_outpoint": {
                "transaction_id": item.spent_transaction_id,
                "vout": item.spent_vout,
                "value_sat": item.spent_value_sat,
            },
            "spending_transaction_id": item.spending_transaction_id,
            "spending_vin": item.spending_vin,
            "created_outpoints": [
                {
                    "transaction_id": item.spending_transaction_id,
                    "vout": output.vout,
                    "value_sat": output.value_sat,
                }
                for output in item.created_outputs
            ],
        }
        for item in selected
    ]
    return {
        "transaction_id": tx.transaction_id,
        "network": tx.network,
        "block_height": tx.block_height,
        "block_hash": tx.block_hash,
        "input_count": len(tx.inputs),
        "output_count": len(tx.outputs),
        "input_sum_sat": input_sum,
        "output_sum_sat": output_sum,
        "fee_sat": input_sum - output_sum,
        "spent_outpoints": [
            {
                "transaction_id": item.prevout.transaction_id,
                "vout": item.prevout.vout,
                "value_sat": item.prevout.value_sat,
            }
            for item in tx.inputs
        ],
        "created_utxos": [
            {
                "transaction_id": tx.transaction_id,
                "vout": item.vout,
                "value_sat": item.value_sat,
                "script_type": item.script_type,
                "address": item.address,
            }
            for item in tx.outputs
        ],
        "start_outpoint": {
            "transaction_id": tx.transaction_id,
            "vout": start_vout,
        },
        "max_hops": max_hops,
        "spend_path": path,
        "frontier_outpoints": path[-1]["created_outpoints"] if path else [],
    }


def assess_bitcoin_heuristics(replay: BitcoinUtxoReplay) -> dict[str, object]:
    """Return reproducible candidates, never ownership or CoinJoin facts."""
    tx = replay.transaction
    input_addresses = {item.prevout.address for item in tx.inputs}
    change_candidates = [
        {
            "vout": item.vout,
            "address": item.address,
            "value_sat": item.value_sat,
            "signals": ["address_reuse"],
            "classification": "heuristic_candidate",
        }
        for item in tx.outputs
        if item.address in input_addresses
    ]
    counts: dict[int, int] = {}
    for output in tx.outputs:
        counts[output.value_sat] = counts.get(output.value_sat, 0) + 1
    equal_groups = [
        {"value_sat": value, "count": count}
        for value, count in sorted(counts.items())
        if count >= 2
    ]
    coinjoin_candidate = len(tx.inputs) >= 3 and any(item["count"] >= 3 for item in equal_groups)
    return {
        "transaction_id": tx.transaction_id,
        "change_candidates": change_candidates,
        "coinjoin_assessment": {
            "classification": "heuristic_candidate",
            "candidate": coinjoin_candidate,
            "equal_output_groups": equal_groups,
            "ownership": "not_assessed",
            "criminality": "not_assessed",
        },
    }
