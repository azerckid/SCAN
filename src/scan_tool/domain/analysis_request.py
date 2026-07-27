"""Discriminated Analysis I/O 0.1 request models."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyUrl, Field, RootModel, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    AnalysisId,
    BlockNumber,
    ContractBool,
    ContractDatetime,
    ContractModel,
    ExactlyTwoUniqueList,
    FixtureId,
    NonEmptyUniqueList,
    SourceId,
    TransactionHash,
    UniqueList,
)


class AnalysisType(StrEnum):
    DEX_SWAP = "dex_swap"
    AUTH_CONSUMPTION = "auth_consumption"
    ADDRESS_FREEZE = "address_freeze"


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


class AnalysisRequestBase(ContractModel):
    schema_uri: Annotated[
        str,
        Field(alias="$schema", pattern=r"analysis-request\.schema\.json$"),
    ]
    schema_version: Literal["0.1"]
    analysis_id: AnalysisId
    chain_id: Literal[1]
    fixture_id: FixtureId | MISSING = MISSING
    requested_at: ContractDatetime
    source_policy: SourcePolicy


class DexAnalysisRequest(AnalysisRequestBase):
    analysis_type: Literal[AnalysisType.DEX_SWAP]
    inputs: DexInputs


class AuthAnalysisRequest(AnalysisRequestBase):
    analysis_type: Literal[AnalysisType.AUTH_CONSUMPTION]
    inputs: AuthInputs


class FreezeAnalysisRequest(AnalysisRequestBase):
    analysis_type: Literal[AnalysisType.ADDRESS_FREEZE]
    inputs: FreezeInputs


RequestVariant = Annotated[
    DexAnalysisRequest | AuthAnalysisRequest | FreezeAnalysisRequest,
    Field(discriminator="analysis_type"),
]


class AnalysisRequest(RootModel[RequestVariant]):
    """Request envelope dispatched by ``analysis_type``."""

    def to_contract_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)
