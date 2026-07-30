"""Analysis I/O result, evidence, source, and run models."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyUrl, ConfigDict, Field, RootModel, model_validator
from pydantic.experimental.missing_sentinel import MISSING
from pydantic_core import PydanticCustomError

from scan_tool.domain._types import (
    AnalysisId,
    BlockNumber,
    ContractBool,
    ContractDatetime,
    ContractModel,
    EvidenceId,
    FixtureRequirementId,
    JsonObject,
    NonEmptyJsonObject,
    NonEmptyString,
    NonEmptyUniqueList,
    NonNegativeInt,
    ProviderId,
    ResultId,
    Sha256,
    SnakeName,
    SourceId,
    SourceRecordId,
    ToolRequirementId,
    TransactionHash,
    UniqueList,
    WarningId,
    missing_references,
    raw_values_are_uint256,
)
from scan_tool.domain.analysis_error import AnalysisError
from scan_tool.domain.analysis_request import AnalysisType


class AnalysisStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class Classification(StrEnum):
    CONFIRMED_FACT = "confirmed_fact"
    EXTERNAL_CONTEXT = "external_context"
    HEURISTIC = "heuristic"
    NOT_ASSESSED = "not_assessed"


class EvidenceType(StrEnum):
    EVENT = "event"
    CALL = "call"
    STATE = "state"
    CONTEXT = "context"


class SourceRole(StrEnum):
    SCORING = "scoring"
    CONTEXT = "context"
    SUPPORTING = "supporting"


class ExecutionMode(StrEnum):
    LIVE = "live"
    OFFLINE_REPLAY = "offline_replay"
    FIXTURE_EXAMPLE = "fixture_example"


class ResultItem(ContractModel):
    result_id: ResultId
    result_type: SnakeName
    classification: Classification
    value: NonEmptyJsonObject
    tool_requirement_ids: NonEmptyUniqueList[ToolRequirementId]
    fixture_requirement_ids: UniqueList[FixtureRequirementId]
    evidence_refs: NonEmptyUniqueList[EvidenceId]


class Artifact(ContractModel):
    artifact_uri: NonEmptyString
    sha256: Sha256 | MISSING = MISSING
    media_type: NonEmptyString | MISSING = MISSING
    byte_length: NonNegativeInt | MISSING = MISSING


class EvidenceLocator(ContractModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"minProperties": 1})

    chain_id: BlockNumber | MISSING = MISSING
    block_number: BlockNumber | MISSING = MISSING
    transaction_hash: TransactionHash | MISSING = MISSING
    log_index: NonNegativeInt | MISSING = MISSING
    trace_address: list[NonNegativeInt] | MISSING = MISSING
    url: AnyUrl | MISSING = MISSING

    @model_validator(mode="after")
    def locator_is_not_empty(self) -> "EvidenceLocator":
        if not self.model_fields_set:
            raise PydanticCustomError(
                "schema_invalid",
                "locator must contain at least one property",
            )
        return self


class Evidence(ContractModel):
    evidence_id: EvidenceId
    evidence_type: EvidenceType
    source_id: SourceId
    source_record_ref: SourceRecordId
    method: NonEmptyString
    retrieved_at: ContractDatetime
    locator: EvidenceLocator
    decoded: JsonObject
    raw_artifact: Artifact


class SourceRecord(ContractModel):
    source_record_id: SourceRecordId
    source_id: SourceId
    provider_id: ProviderId
    role: SourceRole
    required: ContractBool
    capability: NonEmptyString
    endpoint_host: NonEmptyString
    retrieved_at: ContractDatetime
    fallback_from: SourceRecordId | MISSING = MISSING


class WarningItem(ContractModel):
    warning_id: WarningId
    code: SnakeName
    message: NonEmptyString
    related_result_ids: UniqueList[ResultId] | MISSING = MISSING
    related_evidence_ids: UniqueList[EvidenceId] | MISSING = MISSING


class RunRecord(ContractModel):
    tool_version: NonEmptyString
    execution_mode: ExecutionMode
    started_at: ContractDatetime
    finished_at: ContractDatetime
    cache_hits: NonNegativeInt
    cache_misses: NonNegativeInt
    retry_count: NonNegativeInt
    fallback_count: NonNegativeInt
    resumed: ContractBool
    checkpoint_id: NonEmptyString | MISSING = MISSING

    @model_validator(mode="after")
    def finish_is_not_before_start(self) -> "RunRecord":
        if self.finished_at < self.started_at:
            raise PydanticCustomError(
                "schema_invalid",
                "finished_at must not be before started_at",
            )
        return self


class ExportFile(ContractModel):
    artifact_uri: NonEmptyString
    sha256: Sha256 | MISSING = MISSING


class Exports(ContractModel):
    json_export: ExportFile = Field(alias="json")
    markdown: ExportFile
    csv: ExportFile | MISSING = MISSING


class AnalysisResultBase(ContractModel):
    schema_uri: Annotated[
        str,
        Field(alias="$schema", pattern=r"analysis-result\.schema\.json$"),
    ]
    schema_version: Literal["0.1", "0.2"]
    analysis_id: AnalysisId
    analysis_type: AnalysisType
    chain_id: Literal[1]
    results: list[ResultItem]
    evidence: list[Evidence]
    sources: list[SourceRecord]
    warnings: list[WarningItem]
    errors: list[AnalysisError]
    run: RunRecord
    exports: Exports


class CompleteAnalysisResult(AnalysisResultBase):
    status: Literal[AnalysisStatus.COMPLETE]
    results: list[ResultItem] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    sources: list[SourceRecord] = Field(min_length=1)
    errors: list[AnalysisError] = Field(max_length=0)


class PartialAnalysisResult(AnalysisResultBase):
    status: Literal[AnalysisStatus.PARTIAL]
    results: list[ResultItem] = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    sources: list[SourceRecord] = Field(min_length=1)
    errors: list[AnalysisError] = Field(min_length=1)


class FailedAnalysisResult(AnalysisResultBase):
    status: Literal[AnalysisStatus.FAILED]
    errors: list[AnalysisError] = Field(min_length=1)


LegacyAnalysisType = Literal[
    AnalysisType.DEX_SWAP,
    AnalysisType.AUTH_CONSUMPTION,
    AnalysisType.ADDRESS_FREEZE,
]


class LegacyCompleteAnalysisResult(CompleteAnalysisResult):
    schema_version: Literal["0.1"]
    analysis_type: LegacyAnalysisType


class LegacyPartialAnalysisResult(PartialAnalysisResult):
    schema_version: Literal["0.1"]
    analysis_type: LegacyAnalysisType


class LegacyFailedAnalysisResult(FailedAnalysisResult):
    schema_version: Literal["0.1"]
    analysis_type: LegacyAnalysisType


class EvmCompleteAnalysisResult(CompleteAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_CORE]


class EvmPartialAnalysisResult(PartialAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_CORE]


class EvmFailedAnalysisResult(FailedAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_CORE]


class EvmSpecialCompleteAnalysisResult(CompleteAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_SPECIAL]


class EvmSpecialPartialAnalysisResult(PartialAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_SPECIAL]


class EvmSpecialFailedAnalysisResult(FailedAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.EVM_SPECIAL]


class FlowPathCompleteAnalysisResult(CompleteAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.FLOW_PATH]


class FlowPathPartialAnalysisResult(PartialAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.FLOW_PATH]


class FlowPathFailedAnalysisResult(FailedAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.FLOW_PATH]


class IntelContextCompleteAnalysisResult(CompleteAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.INTEL_CONTEXT]


class IntelContextPartialAnalysisResult(PartialAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.INTEL_CONTEXT]


class IntelContextFailedAnalysisResult(FailedAnalysisResult):
    schema_version: Literal["0.2"]
    analysis_type: Literal[AnalysisType.INTEL_CONTEXT]


ResultVariant = (
    LegacyCompleteAnalysisResult
    | LegacyPartialAnalysisResult
    | LegacyFailedAnalysisResult
    | EvmCompleteAnalysisResult
    | EvmPartialAnalysisResult
    | EvmFailedAnalysisResult
    | EvmSpecialCompleteAnalysisResult
    | EvmSpecialPartialAnalysisResult
    | EvmSpecialFailedAnalysisResult
    | FlowPathCompleteAnalysisResult
    | FlowPathPartialAnalysisResult
    | FlowPathFailedAnalysisResult
    | IntelContextCompleteAnalysisResult
    | IntelContextPartialAnalysisResult
    | IntelContextFailedAnalysisResult
)


class AnalysisResult(RootModel[ResultVariant]):
    """Result envelope with status and reference invariants."""

    @model_validator(mode="before")
    @classmethod
    def raw_values_are_valid(cls, value: object) -> object:
        raw_values_are_uint256(value)
        return value

    @model_validator(mode="after")
    def references_are_valid(self) -> "AnalysisResult":
        result = self.root
        result_ids = [item.result_id for item in result.results]
        evidence_ids = [item.evidence_id for item in result.evidence]
        source_record_ids = [item.source_record_id for item in result.sources]
        warning_ids = [item.warning_id for item in result.warnings]
        error_ids = [item.error_id for item in result.errors]

        self._require_unique(result_ids, "result_id")
        self._require_unique(evidence_ids, "evidence_id")
        self._require_unique(source_record_ids, "source_record_id")
        self._require_unique(warning_ids, "warning_id")
        self._require_unique(error_ids, "error_id")

        evidence_id_set = set(evidence_ids)
        result_id_set = set(result_ids)
        source_by_record = {item.source_record_id: item for item in result.sources}
        referenced_evidence_ids: set[str] = set()

        for item in result.results:
            self._require_known(item.evidence_refs, evidence_id_set, item.result_id)
            referenced_evidence_ids.update(item.evidence_refs)
        for warning in result.warnings:
            if warning.related_result_ids is not MISSING:
                self._require_known(
                    warning.related_result_ids,
                    result_id_set,
                    warning.warning_id,
                )
            if warning.related_evidence_ids is not MISSING:
                self._require_known(
                    warning.related_evidence_ids,
                    evidence_id_set,
                    warning.warning_id,
                )
                referenced_evidence_ids.update(warning.related_evidence_ids)
        for error in result.errors:
            if error.related_evidence_ids is not MISSING:
                self._require_known(
                    error.related_evidence_ids,
                    evidence_id_set,
                    error.error_id,
                )
                referenced_evidence_ids.update(error.related_evidence_ids)
        if evidence_id_set - referenced_evidence_ids:
            raise PydanticCustomError(
                "schema_invalid",
                "every evidence item must be referenced",
            )

        referenced_source_records: set[str] = set()
        for evidence in result.evidence:
            source = source_by_record.get(evidence.source_record_ref)
            if source is None or source.source_id != evidence.source_id:
                raise PydanticCustomError(
                    "schema_invalid",
                    "evidence must reference a source record with the same source_id",
                )
            referenced_source_records.add(evidence.source_record_ref)
        if set(source_by_record) - referenced_source_records:
            raise PydanticCustomError(
                "schema_invalid",
                "every source record must be referenced by evidence",
            )
        for source in result.sources:
            if source.fallback_from is not MISSING and source.fallback_from not in source_by_record:
                raise PydanticCustomError(
                    "schema_invalid",
                    "fallback_from must reference an existing source record",
                )
        return self

    @staticmethod
    def _require_unique(values: list[str], label: str) -> None:
        if len(values) != len(set(values)):
            raise PydanticCustomError("schema_invalid", f"{label} values must be unique")

    @staticmethod
    def _require_known(references: list[str], known_ids: set[str], owner: str) -> None:
        if missing_references(references, known_ids):
            raise PydanticCustomError(
                "schema_invalid",
                f"{owner} contains a missing reference",
            )

    def to_contract_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True)
