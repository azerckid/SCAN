"""Strict raw replay models for the TASK-006 DEX vertical slice."""

from typing import Annotated, Literal

from pydantic import Field

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    NonEmptyString,
    ProviderId,
    SourceId,
    TransactionHash,
)

HexQuantity = Annotated[str, Field(pattern=r"^0x(?:0|[1-9a-f][0-9a-f]*)$")]
HexData = Annotated[str, Field(pattern=r"^0x(?:[0-9a-f]{2})*$")]
Hex32 = Annotated[str, Field(pattern=r"^0x[0-9a-f]{64}$")]
EndpointHost = Annotated[
    str,
    Field(pattern=r"^(?:[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)(?::[0-9]{1,5})?$"),
]


class RawTransaction(ContractModel):
    hash: TransactionHash
    block_hash: Hex32
    block_number: HexQuantity
    from_address: Address = Field(alias="from")
    to: Address
    value: HexQuantity
    input: HexData
    nonce: HexQuantity
    transaction_index: HexQuantity


class RawLog(ContractModel):
    address: Address
    topics: list[Hex32] = Field(min_length=1)
    data: HexData
    block_number: HexQuantity
    transaction_hash: TransactionHash
    transaction_index: HexQuantity
    block_hash: Hex32
    block_timestamp: HexQuantity
    log_index: HexQuantity
    removed: Literal[False]


class RawReceipt(ContractModel):
    transaction_hash: TransactionHash
    block_hash: Hex32
    block_number: HexQuantity
    from_address: Address = Field(alias="from")
    to: Address
    status: HexQuantity
    transaction_index: HexQuantity
    logs: list[RawLog]


class RawInternalCall(ContractModel):
    block_number: str = Field(pattern=r"^(0|[1-9][0-9]*)$")
    call_type: Literal["call"]
    from_address: Address = Field(alias="from")
    to: Address
    value: str = Field(pattern=r"^(0|[1-9][0-9]*)$")
    index: str = Field(pattern=r"^(0|[1-9][0-9]*)$")
    input: HexData
    is_error: Literal["0"]
    transaction_hash: TransactionHash


class RouterMetadata(ContractModel):
    address: Address
    label: NonEmptyString
    deployment_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    deployment_json_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    license: NonEmptyString


class FactoryMetadata(ContractModel):
    address: Address
    label: NonEmptyString


class PairMetadata(ContractModel):
    address: Address
    label: NonEmptyString
    historical_get_pair_result: HexData


class TokenMetadata(ContractModel):
    address: Address
    symbol: NonEmptyString
    decimals: int = Field(ge=0, le=255)


class NativeTokenMetadata(ContractModel):
    symbol: NonEmptyString
    decimals: int = Field(ge=0, le=255)


class DexTokens(ContractModel):
    asset_in: TokenMetadata
    pool_output: TokenMetadata
    user_output: NativeTokenMetadata


class DexMetadata(ContractModel):
    router: RouterMetadata
    factory: FactoryMetadata
    pair: PairMetadata
    tokens: DexTokens


class ReplaySource(ContractModel):
    source_id: SourceId
    provider_id: ProviderId
    endpoint_host: EndpointHost
    retrieved_at: ContractDatetime


class ReplaySources(ContractModel):
    receipt: ReplaySource
    internal_calls: ReplaySource
    metadata: ReplaySource


class DexReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    captured_at: ContractDatetime
    reverified_at: ContractDatetime
    transaction: RawTransaction
    receipt: RawReceipt
    internal_calls: list[RawInternalCall]
    metadata: DexMetadata
    sources: ReplaySources
