"""Strict reviewed source replay models for the TASK-015 intel_context queries.

Each bundle carries the reviewed raw source fields (label dataset row, ENS
resolution, community config, official sanctions actions, current-list snapshot,
actor relation sources). The production analyzer parses this with Pydantic and
independently derives the query result; the fixture verifier
(``task_015_independent_verifier``) reaches the same facts from the raw package
files through a separate plain-dict code path.
"""

from typing import Annotated, Literal

from pydantic import Discriminator, Field, RootModel, Tag, model_validator
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    Address,
    ContractDatetime,
    ContractModel,
    FixtureId,
    NonEmptyString,
    SourceId,
)

Uint256Decimal = Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]*)$")]
IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
ArtifactRef = Annotated[str, Field(pattern=r"^artifact://sha256/[a-f0-9]{64}$")]
Sha256Hex = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class IntelSourceRecord(ContractModel):
    source_record_id: Annotated[str, Field(pattern=r"^SRC-[A-Z0-9][A-Z0-9-]{2,127}$")]
    source_id: SourceId
    source_role: NonEmptyString
    artifact_ref: ArtifactRef
    content_sha256: Sha256Hex

    @model_validator(mode="after")
    def artifact_ref_matches_content_hash(self) -> "IntelSourceRecord":
        if self.artifact_ref.removeprefix("artifact://sha256/") != self.content_sha256:
            raise PydanticCustomError(
                "reconciliation_failed",
                "content-addressed artifact_ref must equal its content_sha256",
            )
        return self


class BundleBlockRange(ContractModel):
    from_block: int = Field(alias="from", ge=0)
    to_block: int = Field(alias="to", ge=0)

    @model_validator(mode="after")
    def range_is_ordered(self) -> "BundleBlockRange":
        if self.to_block < self.from_block:
            raise PydanticCustomError("reconciliation_failed", "block range from exceeds to")
        return self


class IntelReplayBase(ContractModel):
    schema_version: Literal["0.1"]
    fixture_id: FixtureId
    status: Literal["candidate", "verifying", "confirmed"]
    captured_at: ContractDatetime
    sources: list[IntelSourceRecord] = Field(min_length=1)

    @model_validator(mode="after")
    def source_records_are_unique(self) -> "IntelReplayBase":
        ids = [item.source_record_id for item in self.sources]
        refs = [item.artifact_ref for item in self.sources]
        if len(ids) != len(set(ids)) or len(refs) != len(set(refs)):
            raise PydanticCustomError(
                "reconciliation_failed",
                "reviewed source records must have unique ids and artifact refs",
            )
        return self


# --- collect_label_claims -------------------------------------------------


class LabelDataset(ContractModel):
    entity: NonEmptyString
    categories: list[NonEmptyString] = Field(min_length=1)
    source_value: NonEmptyString


class LabelEnsResolution(ContractModel):
    name: str
    address: Address
    block_number: int = Field(ge=0)


class LabelCommunityConfig(ContractModel):
    name: str
    role: str


class LabelSourceReplay(IntelReplayBase):
    query_kind: Literal["collect_label_claims"]
    subject_address: Address
    dataset: LabelDataset
    ens: LabelEnsResolution
    community_config: LabelCommunityConfig


# --- check_sanctions_exposure ---------------------------------------------


class OfficialAction(ContractModel):
    date: IsoDate
    action: Literal["designation", "removal"]
    address_match_count: int = Field(ge=0)


class CurrentSanctionsSnapshot(ContractModel):
    case_insensitive_match_count: int = Field(ge=0)
    historical_designation_changed: Literal[False]
    historical_removal_changed: Literal[False]
    current_criminality_assessed: Literal[False]


class SanctionsSourceReplay(IntelReplayBase):
    query_kind: Literal["check_sanctions_exposure"]
    subject_address: Address
    official_actions: list[OfficialAction] = Field(min_length=1)
    current_snapshot: CurrentSanctionsSnapshot


# --- resolve_identity_clues -----------------------------------------------


class EnsSide(ContractModel):
    name: str
    address: Address
    resolver: Address


class IdentitySourceReplay(IntelReplayBase):
    query_kind: Literal["resolve_identity_clues"]
    block_number: int = Field(ge=0)
    forward: EnsSide
    reverse: EnsSide


# --- find_common_funder ---------------------------------------------------


class CommonFunderRelation(ContractModel):
    subject_address: Address
    relation: Literal["direct_seed_output"]
    amount_raw: Uint256Decimal


class CommonFunderSourceReplay(IntelReplayBase):
    query_kind: Literal["find_common_funder"]
    seed_address: Address
    source_fixture_ref: FixtureId
    block_range: BundleBlockRange
    relations: list[CommonFunderRelation] = Field(min_length=1)
    # Completeness is a claimed input flag only; the analyzer does not treat it
    # as proof and keeps common-funder partial until a real completeness
    # evidence structure exists.
    initial_inflow_complete: bool
    service_exclusion_complete: bool
    coverage_gaps: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def relation_subjects_are_unique(self) -> "CommonFunderSourceReplay":
        subjects = [item.subject_address for item in self.relations]
        if len(subjects) != len(set(subjects)):
            raise PydanticCustomError(
                "reconciliation_failed",
                "common-funder relation subjects must be unique",
            )
        return self


# --- score_actor_relations ------------------------------------------------


class ActorHub(ContractModel):
    address: Address
    role: str
    symbol: str


class ActorRelation(ContractModel):
    subject_address: Address
    source_fixture_id: FixtureId
    relation: NonEmptyString


class ActorRelationsSourceReplay(IntelReplayBase):
    query_kind: Literal["score_actor_relations"]
    hub: ActorHub
    relations: list[ActorRelation] = Field(min_length=1)
    hub_excluded_from_actor_link: Literal[True]

    @model_validator(mode="after")
    def relation_subjects_are_unique(self) -> "ActorRelationsSourceReplay":
        subjects = [item.subject_address for item in self.relations]
        if len(subjects) != len(set(subjects)):
            raise PydanticCustomError(
                "reconciliation_failed",
                "actor relation subjects must be unique",
            )
        return self


IntelSourceReplayDocument = (
    LabelSourceReplay
    | SanctionsSourceReplay
    | IdentitySourceReplay
    | CommonFunderSourceReplay
    | ActorRelationsSourceReplay
)

_REPLAY_BY_KIND = {
    "collect_label_claims": "collect_label_claims",
    "check_sanctions_exposure": "check_sanctions_exposure",
    "resolve_identity_clues": "resolve_identity_clues",
    "find_common_funder": "find_common_funder",
    "score_actor_relations": "score_actor_relations",
}


def _replay_kind(value: object) -> str | None:
    if isinstance(value, dict):
        return _REPLAY_BY_KIND.get(value.get("query_kind"))
    return getattr(value, "query_kind", None)


IntelSourceReplayVariant = Annotated[
    Annotated[LabelSourceReplay, Tag("collect_label_claims")]
    | Annotated[SanctionsSourceReplay, Tag("check_sanctions_exposure")]
    | Annotated[IdentitySourceReplay, Tag("resolve_identity_clues")]
    | Annotated[CommonFunderSourceReplay, Tag("find_common_funder")]
    | Annotated[ActorRelationsSourceReplay, Tag("score_actor_relations")],
    Discriminator(_replay_kind),
]


class IntelSourceReplay(RootModel[IntelSourceReplayVariant]):
    pass


def parse_intel_source_replay(raw_bytes: bytes) -> IntelSourceReplayDocument:
    return IntelSourceReplay.model_validate_json(raw_bytes).root
