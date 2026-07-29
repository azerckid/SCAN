"""Strict reviewed replay models for the TASK-014 flow_path queries.

The replay package mirrors the raw structure the independent verifier
(``task_014_independent_verifier.py``) consumes: labelled selected
transactions with their receipts, optional internal edges, and provider
provenance. The production analyzer parses this with Pydantic types while the
verifier parses plain dicts, so the two reach the same conclusion from
separate code paths.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    ContractBool,
    ContractDatetime,
    ContractModel,
    FixtureId,
    SnakeName,
    SourceId,
    TransactionHash,
)
from scan_tool.domain.dex import Hex32, HexQuantity

Uint256Decimal = Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]*)$")]
# Reviewed replays label providers in upper kebab case (PROVIDER-EVM-PRIMARY);
# the public result SourceRecord lower-cases this into the ProviderId shape.
ReplayProviderId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")]


class FlowReplaySource(ContractModel):
    source_id: SourceId
    provider_id: ReplayProviderId
    retrieved_at: ContractDatetime


class RawTransaction(ContractModel):
    hash: TransactionHash
    block_hash: Hex32 = Field(alias="blockHash")
    block_number: HexQuantity = Field(alias="blockNumber")
    transaction_index: HexQuantity = Field(alias="transactionIndex")
    from_address: Address = Field(alias="from")
    to_address: Address = Field(alias="to")
    value: HexQuantity


class RawReceipt(ContractModel):
    transaction_hash: TransactionHash = Field(alias="transactionHash")
    block_hash: Hex32 = Field(alias="blockHash")
    block_number: HexQuantity = Field(alias="blockNumber")
    transaction_index: HexQuantity = Field(alias="transactionIndex")
    status: Literal["0x1"]


class SelectedTransaction(ContractModel):
    label: SnakeName
    transaction: RawTransaction
    receipt: RawReceipt

    @model_validator(mode="after")
    def transaction_and_receipt_agree(self) -> "SelectedTransaction":
        tx = self.transaction
        rc = self.receipt
        if (
            tx.hash != rc.transaction_hash
            or tx.block_hash != rc.block_hash
            or tx.block_number != rc.block_number
            or tx.transaction_index != rc.transaction_index
        ):
            raise PydanticCustomError(
                "reconciliation_failed",
                "selected transaction and receipt identity differ",
            )
        return self


class InternalEdge(ContractModel):
    path: list[Annotated[int, Field(ge=0)]] = Field(min_length=1)
    type: Literal["call"]
    from_address: Address = Field(alias="from")
    to_address: Address = Field(alias="to")
    value_hex: HexQuantity
    value_raw: Uint256Decimal

    @model_validator(mode="after")
    def hex_matches_decimal(self) -> "InternalEdge":
        if int(self.value_hex, 16) != int(self.value_raw):
            raise PydanticCustomError(
                "reconciliation_failed",
                "internal edge value_hex and value_raw differ",
            )
        return self


class FlowScope(ContractModel):
    kind: Literal["selected_transactions_and_exact_blocks"]
    selected_transactions_complete: ContractBool
    continuous_gap_scanned: ContractBool


class FlowPathReplay(ContractModel):
    """One reviewed raw replay package for a flow_path candidate."""

    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    chain_id: Literal[1]
    captured_at: ContractDatetime
    scope: FlowScope
    transactions: list[SelectedTransaction] = Field(min_length=1)
    sources: list[FlowReplaySource] = Field(min_length=1)
    internal_edges: list[InternalEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def transaction_labels_are_unique(self) -> "FlowPathReplay":
        labels = [item.label for item in self.transactions]
        if len(labels) != len(set(labels)):
            raise PydanticCustomError(
                "reconciliation_failed",
                "selected transaction labels must be unique",
            )
        return self


def parse_flow_path_replay(raw_bytes: bytes) -> FlowPathReplay:
    return FlowPathReplay.model_validate_json(raw_bytes)
