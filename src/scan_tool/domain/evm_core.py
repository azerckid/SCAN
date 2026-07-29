"""Strict reviewed replay models for the TASK-012 EVM Core queries."""

from typing import Annotated, Literal

from pydantic import Field, RootModel

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    ProviderId,
    SourceId,
    TransactionHash,
)
from scan_tool.domain.analysis_request import EvmQueryKind
from scan_tool.domain.dex import Hex32, HexData, HexQuantity, RawInternalCall, RawLog


class EvmReplaySource(ContractModel):
    source_id: SourceId
    provider_id: ProviderId
    endpoint_host: str = Field(pattern=r"^[a-z0-9.-]+$")
    retrieved_at: ContractDatetime


class ObjectTransaction(ContractModel):
    hash: TransactionHash
    block_hash: Hex32
    block_number: HexQuantity
    from_address: Address = Field(alias="from")
    to: Address
    value: HexQuantity
    nonce: HexQuantity
    transaction_index: HexQuantity


class ObjectReceipt(ContractModel):
    transaction_hash: TransactionHash
    block_hash: Hex32
    block_number: HexQuantity
    status: Literal["0x1"]
    transaction_index: HexQuantity
    gas_used: HexQuantity
    effective_gas_price: HexQuantity


class ObjectBlock(ContractModel):
    hash: Hex32
    number: HexQuantity
    timestamp: HexQuantity


class CodeObservation(ContractModel):
    address: Address
    block_number: HexQuantity
    code: HexData


class ObjectSummaryReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    query_kind: Literal[EvmQueryKind.OBJECT_SUMMARY]
    captured_at: ContractDatetime
    transaction: ObjectTransaction
    receipt: ObjectReceipt
    block: ObjectBlock
    codes: list[CodeObservation] = Field(min_length=1)
    sources: list[EvmReplaySource] = Field(min_length=1)


class BalanceBlock(ContractModel):
    number: HexQuantity
    timestamp: HexQuantity


class TokenStateObservation(ContractModel):
    token_address: Address
    symbol: str = Field(pattern=r"^[A-Z0-9]{2,12}$")
    balance_result: HexData
    decimals_result: HexData


class HistoricalBalanceReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    query_kind: Literal[EvmQueryKind.HISTORICAL_BALANCE]
    captured_at: ContractDatetime
    subject_address: Address
    block: BalanceBlock
    native_balance: HexQuantity
    token_states: list[TokenStateObservation]
    sources: list[EvmReplaySource] = Field(min_length=1)


class FirstTokenTransferReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    query_kind: Literal[EvmQueryKind.FIRST_TOKEN_TRANSFER]
    captured_at: ContractDatetime
    start_block: HexQuantity
    end_block: HexQuantity
    range_complete: bool
    logs: list[RawLog]
    sources: list[EvmReplaySource] = Field(min_length=1)


class NativeInflowReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    query_kind: Literal[EvmQueryKind.NATIVE_INFLOW]
    captured_at: ContractDatetime
    transaction: ObjectTransaction
    transaction_status: Literal["0x1"]
    trace_complete: bool
    internal_calls: list[RawInternalCall]
    sources: list[EvmReplaySource] = Field(min_length=1)


EvmCoreReplayVariant = Annotated[
    ObjectSummaryReplay | HistoricalBalanceReplay | FirstTokenTransferReplay | NativeInflowReplay,
    Field(discriminator="query_kind"),
]
EvmCoreReplayDocument = (
    ObjectSummaryReplay | HistoricalBalanceReplay | FirstTokenTransferReplay | NativeInflowReplay
)


class EvmCoreReplay(RootModel[EvmCoreReplayVariant]):
    """One reviewed raw replay package selected by EVM query kind."""
