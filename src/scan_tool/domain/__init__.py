"""Analysis contract models and validation helpers."""

from scan_tool.domain.analysis_error import AnalysisError, ErrorCode
from scan_tool.domain.analysis_request import AnalysisRequest, AnalysisType
from scan_tool.domain.analysis_result import (
    AnalysisResult,
    AnalysisStatus,
    Classification,
    EvidenceType,
)
from scan_tool.domain.validation import (
    ContractViolation,
    validate_analysis_error,
    validate_analysis_pair,
    validate_analysis_request,
    validate_analysis_result,
)

__all__ = [
    "AnalysisError",
    "AnalysisRequest",
    "AnalysisResult",
    "AnalysisStatus",
    "AnalysisType",
    "Classification",
    "ContractViolation",
    "ErrorCode",
    "EvidenceType",
    "validate_analysis_error",
    "validate_analysis_pair",
    "validate_analysis_request",
    "validate_analysis_result",
]
