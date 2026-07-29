"""Strict reviewed replay models for the TASK-013 NFT/Proxy queries."""

from typing import Annotated, Literal

from pydantic import Discriminator, Field, RootModel, Tag

from scan_tool.domain._types import (
    Address,
    ContractBool,
    ContractDatetime,
    ContractModel,
    FixtureId,
    ProviderId,
    SourceId,
    TransactionHash,
)
from scan_tool.domain.dex import Hex32, HexData, HexQuantity


class EvmSpecialReplaySource(ContractModel):
    source_id: SourceId
    provider_id: ProviderId
    retrieved_at: ContractDatetime


class SpecialLog(ContractModel):
    address: Address
    topics: list[Hex32] = Field(min_length=1)
    data: HexData
    block_number: HexQuantity
    transaction_hash: TransactionHash
    transaction_index: HexQuantity
    log_index: HexQuantity
    removed: Literal[False]


class SpecialReceipt(ContractModel):
    transaction_hash: TransactionHash
    block_hash: Hex32
    block_number: HexQuantity
    transaction_index: HexQuantity
    status: Literal["0x1"]


class BlockWindow(ContractModel):
    from_block: HexQuantity = Field(alias="from")
    to_block: HexQuantity = Field(alias="to")


class NftScope(ContractModel):
    kind: Literal["selected_transactions_and_exact_block_windows"]
    selected_transactions_complete: ContractBool
    exact_block_windows_complete: ContractBool
    continuous_gap_scanned: ContractBool
    block_windows: list[BlockWindow] = Field(min_length=1)


class NftActivityReplay(ContractModel):
    """One reviewed raw replay package for an ERC-721 or ERC-1155 candidate."""

    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    standard_hint: Literal["erc721", "erc1155"]
    captured_at: ContractDatetime
    scope: NftScope
    receipts: list[SpecialReceipt] = Field(min_length=1)
    logs: list[SpecialLog] = Field(min_length=1)
    sources: list[EvmSpecialReplaySource] = Field(min_length=1)


class ProxyScope(ContractModel):
    kind: Literal["selected_upgrade_transaction_and_adjacent_state"]
    upgrade_transaction_complete: ContractBool
    adjacent_state_complete: ContractBool
    wider_history_scanned: ContractBool


class StorageSnapshot(ContractModel):
    role: Literal[
        "implementation_before",
        "implementation_after",
        "admin_before",
        "admin_after",
        "beacon_before",
        "beacon_after",
    ]
    block_number: HexQuantity
    slot: Hex32
    raw_word: Hex32


class ProxyHistoryReplay(ContractModel):
    """One reviewed raw replay package for an EIP-1967 proxy candidate."""

    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    chain_id: Literal[1]
    pattern_hint: Literal["eip1967"]
    captured_at: ContractDatetime
    scope: ProxyScope
    receipt: SpecialReceipt
    logs: list[SpecialLog] = Field(min_length=1)
    storage_snapshots: list[StorageSnapshot] = Field(min_length=1)
    sources: list[EvmSpecialReplaySource] = Field(min_length=1)


EvmSpecialReplayDocument = NftActivityReplay | ProxyHistoryReplay


def _replay_kind(value: object) -> str | None:
    if isinstance(value, dict):
        if "standard_hint" in value:
            return "nft_activity"
        if "pattern_hint" in value:
            return "proxy_history"
    elif isinstance(value, NftActivityReplay):
        return "nft_activity"
    elif isinstance(value, ProxyHistoryReplay):
        return "proxy_history"
    return None


EvmSpecialReplayVariant = Annotated[
    Annotated[NftActivityReplay, Tag("nft_activity")]
    | Annotated[ProxyHistoryReplay, Tag("proxy_history")],
    Discriminator(_replay_kind),
]


class EvmSpecialReplay(RootModel[EvmSpecialReplayVariant]):
    """One reviewed raw replay package selected by its declared hint field."""


def parse_evm_special_replay(raw_bytes: bytes) -> EvmSpecialReplayDocument:
    """Select the reviewed replay shape from its own content, not from a caller hint."""
    return EvmSpecialReplay.model_validate_json(raw_bytes).root
