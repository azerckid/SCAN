"""Discriminated Analysis I/O request models (0.1 compatibility + EVM Core 0.2)."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyUrl, ConfigDict, Field, RootModel, StrictInt, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    AnalysisId,
    BitcoinTxId,
    BlockNumber,
    ContractBool,
    ContractDatetime,
    ContractModel,
    ExactlyTwoUniqueList,
    FixtureId,
    NonEmptyUniqueList,
    NonNegativeInt,
    SourceId,
    TransactionHash,
    UniqueList,
)


class AnalysisType(StrEnum):
    DEX_SWAP = "dex_swap"
    AUTH_CONSUMPTION = "auth_consumption"
    ADDRESS_FREEZE = "address_freeze"
    EVM_CORE = "evm_core"
    EVM_SPECIAL = "evm_special"
    FLOW_PATH = "flow_path"
    INTEL_CONTEXT = "intel_context"
    BRIDGE_TRANSFER = "bridge_transfer"
    BITCOIN_UTXO = "bitcoin_utxo"
    CEX_CLUSTER = "cex_cluster"
    MIXER_FLOW = "mixer_flow"


class EvmQueryKind(StrEnum):
    OBJECT_SUMMARY = "object_summary"
    HISTORICAL_BALANCE = "historical_balance"
    FIRST_TOKEN_TRANSFER = "first_token_transfer"
    NATIVE_INFLOW = "native_inflow"


class EvmSpecialQueryKind(StrEnum):
    NFT_ACTIVITY = "nft_activity"
    PROXY_HISTORY = "proxy_history"


class RuleStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    ALLOWED = "allowed"
    RESTRICTED = "restricted"


class ApprovalType(StrEnum):
    APPROVE = "approve"
    PERMIT = "permit"
    PERMIT2 = "permit2"


class SourcePolicy(ContractModel):
    rule_status: RuleStatus
    allowed_source_ids: NonEmptyUniqueList[SourceId]
    source_order: NonEmptyUniqueList[SourceId]
    allow_fallback: ContractBool
    offline_mode: ContractBool

    @model_validator(mode="after")
    def source_order_is_allowed(self) -> "SourcePolicy":
        if not set(self.source_order) <= set(self.allowed_source_ids):
            raise PydanticCustomError(
                "invalid_input",
                "source_order must be a subset of allowed_source_ids",
            )
        return self


class AuthStateBlocks(ContractModel):
    before_approval: BlockNumber
    after_approval: BlockNumber
    before_consumption: BlockNumber
    after_consumption: BlockNumber


class FreezeStateBlocks(ContractModel):
    before_blacklist: BlockNumber
    after_blacklist: BlockNumber
    before_unblacklist: BlockNumber
    after_unblacklist: BlockNumber


class DexInputs(ContractModel):
    transaction_hash: TransactionHash


class AuthInputs(ContractModel):
    subject_address: Address
    token_address: Address
    spender_address: Address
    approval_type: ApprovalType | MISSING = MISSING
    approval_transaction_hash: TransactionHash
    consumption_transaction_hash: TransactionHash
    state_blocks: AuthStateBlocks
    excluded_transaction_hashes: UniqueList[TransactionHash] | MISSING = MISSING


class FreezeInputs(ContractModel):
    token_address: Address
    target_address: Address
    mode: Literal["address_blacklist_lifecycle"]
    event_transaction_hashes: ExactlyTwoUniqueList[TransactionHash]
    state_blocks: FreezeStateBlocks
    context_urls: UniqueList[AnyUrl] | MISSING = MISSING


class ObjectSummaryInputs(ContractModel):
    values: list[str | BlockNumber] = Field(min_length=1)
    block_number: BlockNumber
    include_transaction_fee: ContractBool


class BalanceAsset(ContractModel):
    asset_type: Literal["native", "erc20"]
    symbol: Annotated[str, Field(pattern=r"^[A-Z0-9]{2,12}$")]
    token_address: Address | MISSING = MISSING

    @model_validator(mode="after")
    def token_address_matches_asset_type(self) -> "BalanceAsset":
        if self.asset_type == "erc20" and self.token_address is MISSING:
            raise PydanticCustomError(
                "invalid_input",
                "erc20 assets require token_address",
            )
        if self.asset_type == "native" and self.token_address is not MISSING:
            raise PydanticCustomError(
                "invalid_input",
                "native assets must not define token_address",
            )
        return self


class HistoricalBalanceInputs(ContractModel):
    subject_address: Address
    block_number: BlockNumber
    block_timestamp: BlockNumber
    state_semantics: Literal["post_state"]
    assets: list[BalanceAsset] = Field(min_length=1)


class FirstTokenTransferInputs(ContractModel):
    subject_address: Address
    token_address: Address
    start_block: BlockNumber
    direction: Literal["outgoing"]
    exclude_zero: Literal[True]
    require_success: Literal[True]
    ordering: Literal["block_transaction_log_asc"]


class NativeInflowInputs(ContractModel):
    interest_address: Address
    transaction_hash: TransactionHash
    require_trace: Literal[True]
    exclude_reverted: Literal[True]


EvmCoreInputs = (
    ObjectSummaryInputs | HistoricalBalanceInputs | FirstTokenTransferInputs | NativeInflowInputs
)


class NftActivityInputs(ContractModel):
    token_contract: Address
    subject_address: Address
    standard_hint: Literal["erc721", "erc1155", "auto"]
    include_approvals: ContractBool


class ProxyHistoryInputs(ContractModel):
    proxy_address: Address
    pattern_hint: Literal["eip1967", "auto"]
    include_admin: ContractBool
    # Beacon-path decoding (beacon address + implementation() cross-check) is
    # not implemented in this version. Restricted to False so the analyzer
    # never reports beacon.applicable without having verified anything.
    include_beacon: Literal[False]


EvmSpecialInputs = NftActivityInputs | ProxyHistoryInputs


class FlowPathQueryKind(StrEnum):
    TRACE_PATH = "trace_path"
    TRACE_REMERGE = "trace_remerge"
    AGGREGATE_ORIGINS = "aggregate_origins"


PositiveInt = Annotated[StrictInt, Field(gt=0)]


class NativeAssetScope(ContractModel):
    # v1 scores native ETH only; ERC-20/wrapped assets are a later contract.
    kind: Literal["native"]
    symbol: Literal["ETH"]
    decimals: Literal[18]


class TraversalBudgets(ContractModel):
    max_hops: PositiveInt
    max_nodes: PositiveInt
    max_edges: PositiveInt


class FlowBlockWindow(ContractModel):
    from_block: BlockNumber = Field(alias="from")
    to_block: BlockNumber = Field(alias="to")

    @model_validator(mode="after")
    def window_is_ordered(self) -> "FlowBlockWindow":
        if self.to_block < self.from_block:
            raise PydanticCustomError("invalid_input", "block window from must not exceed to")
        return self


class TracePathScope(ContractModel):
    kind: Literal["selected_transactions_and_exact_blocks"]
    block_windows: list[FlowBlockWindow] = Field(min_length=1)


class TraceRemergeScope(ContractModel):
    kind: Literal["selected_transactions_and_exact_blocks"]
    block_range: FlowBlockWindow
    selected_transactions: NonEmptyUniqueList[TransactionHash]
    excluded_context_transactions: UniqueList[TransactionHash]


class AggregateOriginsScope(ContractModel):
    kind: Literal["selected_transactions_and_exact_blocks"]
    selected_transactions: NonEmptyUniqueList[TransactionHash]


class TerminalPolicy(ContractModel):
    terminal_node: Address
    stop_on: Literal["selected_terminal_reached"]


class TracePathInputs(ContractModel):
    seed_node: Address
    direction: Literal["outbound"]
    asset_scope: NativeAssetScope
    terminal_policy: TerminalPolicy
    budgets: TraversalBudgets
    scope: TracePathScope


class TraceRemergeInputs(ContractModel):
    seed_node: Address
    merge_node: Address
    asset_scope: NativeAssetScope
    budgets: TraversalBudgets
    scope: TraceRemergeScope


class AggregateOriginsInputs(ContractModel):
    origin_nodes: NonEmptyUniqueList[Address]
    exit_node: Address
    asset_scope: NativeAssetScope
    budgets: TraversalBudgets
    scope: AggregateOriginsScope


FlowPathInputs = TracePathInputs | TraceRemergeInputs | AggregateOriginsInputs


class IntelContextQueryKind(StrEnum):
    COLLECT_LABEL_CLAIMS = "collect_label_claims"
    CHECK_SANCTIONS_EXPOSURE = "check_sanctions_exposure"
    RESOLVE_IDENTITY_CLUES = "resolve_identity_clues"
    FIND_COMMON_FUNDER = "find_common_funder"
    SCORE_ACTOR_RELATIONS = "score_actor_relations"


ArtifactRef = Annotated[str, Field(pattern=r"^artifact://sha256/[a-f0-9]{64}$")]


class CommonFunderCompleteness(ContractModel):
    require_initial_inflow_complete: ContractBool
    require_service_exclusion: ContractBool
    excluded_service_roles: NonEmptyUniqueList[str]


class LabelClaimsInputs(ContractModel):
    subject_addresses: NonEmptyUniqueList[Address]
    source_artifact_refs: NonEmptyUniqueList[ArtifactRef]
    observation_block: BlockNumber
    max_sources: PositiveInt


class SanctionsExposureInputs(ContractModel):
    subject_addresses: NonEmptyUniqueList[Address]
    official_action_refs: NonEmptyUniqueList[str]
    current_list_snapshot_ref: str
    max_hops: Literal[0, 1]


class IdentityCluesInputs(ContractModel):
    subject_addresses: NonEmptyUniqueList[Address]
    names: NonEmptyUniqueList[str]
    observation_block: BlockNumber
    provider_replay_ref: str


class CommonFunderInputs(ContractModel):
    subject_addresses: NonEmptyUniqueList[Address]
    block_range: FlowBlockWindow
    source_fixture_ref: FixtureId
    completeness: CommonFunderCompleteness


class ActorRelationsInputs(ContractModel):
    subject_addresses: NonEmptyUniqueList[Address]
    hub_address: Address
    source_fixture_refs: NonEmptyUniqueList[FixtureId]
    component_weights: NonEmptyUniqueList[str]


IntelContextInputs = (
    LabelClaimsInputs
    | SanctionsExposureInputs
    | IdentityCluesInputs
    | CommonFunderInputs
    | ActorRelationsInputs
)


class BridgeTransferQueryKind(StrEnum):
    LINK_BRIDGE_TRANSFER = "link_bridge_transfer"


class CexClusterQueryKind(StrEnum):
    EVALUATE_CEX_CLUSTER = "evaluate_cex_cluster"


class MixerFlowQueryKind(StrEnum):
    EVALUATE_MIXER_CANDIDATES = "evaluate_mixer_candidates"


class ObservationWindowInputs(ContractModel):
    start_block: BlockNumber
    end_block: BlockNumber

    @model_validator(mode="after")
    def window_is_ordered(self) -> "ObservationWindowInputs":
        if self.end_block < self.start_block:
            raise PydanticCustomError("invalid_input", "observation window end must follow start")
        return self


class EvaluateCexClusterInputs(ContractModel):
    deposit_candidates: NonEmptyUniqueList[Address]
    observation_window: ObservationWindowInputs
    expected_hot_wallet: Address | MISSING = MISSING


class EvaluateMixerFlowInputs(ContractModel):
    subject_address: Address
    pool_address: Address
    observation_window: ObservationWindowInputs


class LinkBridgeTransferInputs(ContractModel):
    source_subject: Address
    destination_chain_id: StrictInt
    origin_chain_id: StrictInt
    expected_recipient: Address | MISSING = MISSING
    source_transaction_hash: TransactionHash | MISSING = MISSING
    destination_transaction_hash: TransactionHash | MISSING = MISSING


class BitcoinQueryKind(StrEnum):
    SUMMARIZE_TRANSACTION = "summarize_transaction"
    ASSESS_HEURISTICS = "assess_heuristics"


class BitcoinTransactionInputs(ContractModel):
    transaction_id: BitcoinTxId
    network: Literal["bitcoin_mainnet"]
    start_vout: NonNegativeInt
    max_hops: PositiveInt


class BitcoinHeuristicInputs(BitcoinTransactionInputs):
    assess_change: ContractBool
    assess_coinjoin: ContractBool


BitcoinInputs = BitcoinTransactionInputs | BitcoinHeuristicInputs


class AnalysisRequestBase(ContractModel):
    schema_uri: Annotated[
        str,
        Field(alias="$schema", pattern=r"analysis-request\.schema\.json$"),
    ]
    schema_version: Literal["0.1", "0.2"]
    analysis_id: AnalysisId
    chain_id: StrictInt
    fixture_id: FixtureId | MISSING = MISSING
    requested_at: ContractDatetime
    source_policy: SourcePolicy


class DexAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    schema_version: Literal["0.1"]
    analysis_type: Literal[AnalysisType.DEX_SWAP]
    inputs: DexInputs


class AuthAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    schema_version: Literal["0.1"]
    analysis_type: Literal[AnalysisType.AUTH_CONSUMPTION]
    inputs: AuthInputs


class FreezeAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    schema_version: Literal["0.1"]
    analysis_type: Literal[AnalysisType.ADDRESS_FREEZE]
    inputs: FreezeInputs


class EvmCoreAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"query_kind": {"const": query_kind}}},
                    "then": {"properties": {"inputs": {"required": required_fields}}},
                }
                for query_kind, required_fields in (
                    ("object_summary", ["values"]),
                    ("historical_balance", ["assets"]),
                    ("first_token_transfer", ["token_address", "start_block"]),
                    ("native_inflow", ["interest_address", "transaction_hash"]),
                )
            ]
        }
    )
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_CORE]
    query_kind: EvmQueryKind
    inputs: EvmCoreInputs

    @model_validator(mode="after")
    def inputs_match_query_kind(self) -> "EvmCoreAnalysisRequest":
        expected = {
            EvmQueryKind.OBJECT_SUMMARY: ObjectSummaryInputs,
            EvmQueryKind.HISTORICAL_BALANCE: HistoricalBalanceInputs,
            EvmQueryKind.FIRST_TOKEN_TRANSFER: FirstTokenTransferInputs,
            EvmQueryKind.NATIVE_INFLOW: NativeInflowInputs,
        }[self.query_kind]
        if not isinstance(self.inputs, expected):
            raise PydanticCustomError(
                "invalid_input",
                "inputs must match query_kind",
            )
        return self


class EvmSpecialAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"query_kind": {"const": query_kind}}},
                    "then": {"properties": {"inputs": {"required": required_fields}}},
                }
                for query_kind, required_fields in (
                    ("nft_activity", ["token_contract", "subject_address"]),
                    ("proxy_history", ["proxy_address"]),
                )
            ]
        }
    )
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_SPECIAL]
    query_kind: EvmSpecialQueryKind
    inputs: EvmSpecialInputs

    @model_validator(mode="after")
    def inputs_match_query_kind(self) -> "EvmSpecialAnalysisRequest":
        expected = {
            EvmSpecialQueryKind.NFT_ACTIVITY: NftActivityInputs,
            EvmSpecialQueryKind.PROXY_HISTORY: ProxyHistoryInputs,
        }[self.query_kind]
        if not isinstance(self.inputs, expected):
            raise PydanticCustomError(
                "invalid_input",
                "inputs must match query_kind",
            )
        return self


class FlowPathAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"query_kind": {"const": query_kind}}},
                    "then": {"properties": {"inputs": {"required": required_fields}}},
                }
                for query_kind, required_fields in (
                    ("trace_path", ["seed_node", "terminal_policy"]),
                    ("trace_remerge", ["seed_node", "merge_node"]),
                    ("aggregate_origins", ["origin_nodes", "exit_node"]),
                )
            ]
        }
    )
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.FLOW_PATH]
    query_kind: FlowPathQueryKind
    inputs: FlowPathInputs

    @model_validator(mode="after")
    def inputs_match_query_kind(self) -> "FlowPathAnalysisRequest":
        expected = {
            FlowPathQueryKind.TRACE_PATH: TracePathInputs,
            FlowPathQueryKind.TRACE_REMERGE: TraceRemergeInputs,
            FlowPathQueryKind.AGGREGATE_ORIGINS: AggregateOriginsInputs,
        }[self.query_kind]
        if not isinstance(self.inputs, expected):
            raise PydanticCustomError(
                "invalid_input",
                "inputs must match query_kind",
            )
        return self


class IntelContextAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"query_kind": {"const": query_kind}}},
                    "then": {"properties": {"inputs": {"required": required_fields}}},
                }
                for query_kind, required_fields in (
                    ("collect_label_claims", ["subject_addresses", "source_artifact_refs"]),
                    ("check_sanctions_exposure", ["subject_addresses", "official_action_refs"]),
                    ("resolve_identity_clues", ["subject_addresses", "names"]),
                    ("find_common_funder", ["subject_addresses", "source_fixture_ref"]),
                    ("score_actor_relations", ["subject_addresses", "hub_address"]),
                )
            ]
        }
    )
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.INTEL_CONTEXT]
    query_kind: IntelContextQueryKind
    inputs: IntelContextInputs

    @model_validator(mode="after")
    def inputs_match_query_kind(self) -> "IntelContextAnalysisRequest":
        expected = {
            IntelContextQueryKind.COLLECT_LABEL_CLAIMS: LabelClaimsInputs,
            IntelContextQueryKind.CHECK_SANCTIONS_EXPOSURE: SanctionsExposureInputs,
            IntelContextQueryKind.RESOLVE_IDENTITY_CLUES: IdentityCluesInputs,
            IntelContextQueryKind.FIND_COMMON_FUNDER: CommonFunderInputs,
            IntelContextQueryKind.SCORE_ACTOR_RELATIONS: ActorRelationsInputs,
        }[self.query_kind]
        if not isinstance(self.inputs, expected):
            raise PydanticCustomError("invalid_input", "inputs must match query_kind")
        return self


class BridgeTransferAnalysisRequest(AnalysisRequestBase):
    chain_id: Literal[1]
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.BRIDGE_TRANSFER]
    query_kind: Literal[BridgeTransferQueryKind.LINK_BRIDGE_TRANSFER]
    inputs: LinkBridgeTransferInputs


class BitcoinUtxoAnalysisRequest(AnalysisRequestBase):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.BITCOIN_UTXO]
    chain_id: Literal[0]
    query_kind: BitcoinQueryKind
    inputs: BitcoinInputs

    @model_validator(mode="after")
    def inputs_match_query_kind(self) -> "BitcoinUtxoAnalysisRequest":
        expected = {
            BitcoinQueryKind.SUMMARIZE_TRANSACTION: BitcoinTransactionInputs,
            BitcoinQueryKind.ASSESS_HEURISTICS: BitcoinHeuristicInputs,
        }[self.query_kind]
        if type(self.inputs) is not expected:
            raise PydanticCustomError("invalid_input", "inputs must match query_kind")
        return self


class CexClusterAnalysisRequest(AnalysisRequestBase):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.CEX_CLUSTER]
    query_kind: Literal[CexClusterQueryKind.EVALUATE_CEX_CLUSTER]
    inputs: EvaluateCexClusterInputs


class MixerFlowAnalysisRequest(AnalysisRequestBase):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.MIXER_FLOW]
    query_kind: Literal[MixerFlowQueryKind.EVALUATE_MIXER_CANDIDATES]
    inputs: EvaluateMixerFlowInputs


RequestVariant = Annotated[
    DexAnalysisRequest
    | AuthAnalysisRequest
    | FreezeAnalysisRequest
    | EvmCoreAnalysisRequest
    | EvmSpecialAnalysisRequest
    | FlowPathAnalysisRequest
    | IntelContextAnalysisRequest
    | BridgeTransferAnalysisRequest
    | BitcoinUtxoAnalysisRequest
    | CexClusterAnalysisRequest
    | MixerFlowAnalysisRequest,
    Field(discriminator="analysis_type"),
]


class AnalysisRequest(RootModel[RequestVariant]):
    """Request envelope dispatched by ``analysis_type``."""

    def to_contract_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)
