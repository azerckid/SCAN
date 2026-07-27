"""Structured Analysis I/O 0.1 error model."""

from enum import StrEnum

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.domain._types import (
    ContractBool,
    ContractDatetime,
    ContractModel,
    ErrorId,
    EvidenceId,
    JsonObject,
    NonNegativeInt,
    ProviderId,
    SnakeName,
    SourceId,
    UniqueList,
)


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_CHAIN = "unsupported_chain"
    SOURCE_UNAVAILABLE = "source_unavailable"
    RATE_LIMITED = "rate_limited"
    ARCHIVE_REQUIRED = "archive_required"
    TRACE_UNAVAILABLE = "trace_unavailable"
    DECODE_FAILED = "decode_failed"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    RECONCILIATION_FAILED = "reconciliation_failed"
    SCHEMA_INVALID = "schema_invalid"
    RULE_RESTRICTED = "rule_restricted"


class AnalysisError(ContractModel):
    """Public structured error without credentials or raw provider secrets."""

    error_id: ErrorId
    code: ErrorCode
    message: str = Field(min_length=1, max_length=1000)
    stage: SnakeName
    source_id: SourceId | MISSING = MISSING
    provider_id: ProviderId | MISSING = MISSING
    retryable: ContractBool
    attempt_count: NonNegativeInt
    last_attempt_at: ContractDatetime | MISSING = MISSING
    related_evidence_ids: UniqueList[EvidenceId] | MISSING = MISSING
    details: JsonObject | MISSING = MISSING
