"""Strict raw replay models for the TASK-008 FREEZE vertical slice."""

from typing import Literal

from pydantic import AnyUrl, Field

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    NonEmptyString,
    SourceId,
    TransactionHash,
)
from scan_tool.domain.auth import TransactionEvidence
from scan_tool.domain.dex import HexData, HexQuantity, ReplaySource


class TokenMetadata(ContractModel):
    address: Address
    symbol: NonEmptyString
    decimals: int = Field(ge=0, le=255)


class FreezeSnapshot(ContractModel):
    label: Literal[
        "before_blacklist",
        "after_blacklist",
        "before_unblacklist",
        "after_unblacklist",
    ]
    block_number: int = Field(ge=0)
    block_tag: HexQuantity
    result: HexData


class FreezeStateQuery(ContractModel):
    to: Address
    data: HexData
    snapshots: list[FreezeSnapshot]


class ExplorerTransaction(ContractModel):
    transaction_hash: TransactionHash
    status: Literal["ok"]
    method: Literal["blacklist", "unBlacklist"]
    from_address: Address = Field(alias="from")
    to: Address
    raw_input: HexData
    log_index: int = Field(ge=0)


class OfficialContext(ContractModel):
    context_id: Literal[
        "circle_response",
        "circle_terms",
        "circle_contract",
        "ofac_designation",
        "ofac_removal",
    ]
    source_id: SourceId
    provider: NonEmptyString
    title: NonEmptyString
    url: AnyUrl
    address_specific: bool
    target_address_listed: bool | None
    role: NonEmptyString
    retrieved_at: ContractDatetime


class InterfaceMetadata(ContractModel):
    source_id: Literal["DS-OSINT-WEB"]
    provider: Literal["Circle GitHub"]
    url: AnyUrl
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    commit_date: ContractDatetime
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license: Literal["MIT"]
    license_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: ContractDatetime


class FreezeReplaySources(ContractModel):
    public_rpc: ReplaySource
    archive_rpc: ReplaySource
    explorer: ReplaySource
    issuer: ReplaySource
    sanctions: ReplaySource


class FreezeReplay(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    captured_at: ContractDatetime
    reverified_at: ContractDatetime
    target_address: Address
    mode: Literal["address_blacklist_lifecycle"]
    token: TokenMetadata
    blacklist: TransactionEvidence
    unblacklist: TransactionEvidence | None
    state_query: FreezeStateQuery
    explorer_cross_check: list[ExplorerTransaction]
    official_context: list[OfficialContext]
    interface_metadata: InterfaceMetadata
    global_pause_applicable: Literal[False]
    sources: FreezeReplaySources
