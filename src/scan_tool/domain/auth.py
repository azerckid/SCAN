"""Strict raw replay models for the TASK-007 AUTH vertical slice."""

from typing import Literal

from pydantic import Field

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    NonEmptyString,
    TransactionHash,
)
from scan_tool.domain.dex import HexData, HexQuantity, RawLog, RawTransaction, ReplaySource


class AuthReceipt(ContractModel):
    transaction_hash: TransactionHash
    block_hash: str = Field(pattern=r"^0x[0-9a-f]{64}$")
    block_number: HexQuantity
    from_address: Address = Field(alias="from")
    to: Address
    status: HexQuantity
    transaction_index: HexQuantity
    selected_logs: list[RawLog]


class TransactionEvidence(ContractModel):
    transaction: RawTransaction
    receipt: AuthReceipt


class TransferFromTrace(ContractModel):
    transaction_hash: TransactionHash
    block_hash: str = Field(pattern=r"^0x[0-9a-f]{64}$")
    block_number: int = Field(ge=0)
    trace_address: list[int] = Field(min_length=1)
    call_type: Literal["call"]
    from_address: Address = Field(alias="from")
    to: Address
    input: HexData
    output: HexData


class ConsumptionEvidence(TransactionEvidence):
    transfer_from_trace: TransferFromTrace | None


class TokenMetadata(ContractModel):
    address: Address
    symbol: NonEmptyString
    decimals: int = Field(ge=0, le=255)


class SpenderMetadata(ContractModel):
    address: Address
    label: NonEmptyString
    deployment_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: NonEmptyString


class AllowanceSnapshot(ContractModel):
    label: Literal[
        "before_approval",
        "after_approval",
        "before_consumption",
        "after_consumption",
    ]
    block_number: int = Field(ge=0)
    block_tag: HexQuantity
    result: HexData


class AllowanceQuery(ContractModel):
    to: Address
    data: HexData
    snapshots: list[AllowanceSnapshot]


class ExcludedReceipt(ContractModel):
    transaction_hash: TransactionHash
    nonce: HexQuantity
    block_number: HexQuantity
    from_address: Address = Field(alias="from")
    to: Address
    status: HexQuantity


class ExplorerCrossCheck(ContractModel):
    approval_transaction_hash: TransactionHash
    approval_status: Literal["ok"]
    approval_method: Literal["approve"]
    approval_nonce: int = Field(ge=0)
    consumption_transaction_hash: TransactionHash
    consumption_status: Literal["ok"]
    consumption_method: Literal["multicall"]
    consumption_nonce: int = Field(ge=0)
    transfer_log_index: int = Field(ge=0)
    transfer_amount_raw: str = Field(pattern=r"^(0|[1-9][0-9]*)$")


class AuthReplaySources(ContractModel):
    public_rpc: ReplaySource
    archive_rpc: ReplaySource
    explorer: ReplaySource
    metadata: ReplaySource


class AuthReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    captured_at: ContractDatetime
    reverified_at: ContractDatetime
    subject_address: Address
    token: TokenMetadata
    spender: SpenderMetadata
    approval: TransactionEvidence
    consumption: ConsumptionEvidence
    allowance_query: AllowanceQuery
    excluded_receipts: list[ExcludedReceipt]
    explorer_cross_check: ExplorerCrossCheck
    sources: AuthReplaySources
