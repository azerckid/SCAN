"""Contract validation entry points with stable public error classification."""

from collections.abc import Mapping

from pydantic import TypeAdapter, ValidationError

from scan_tool.domain._types import AnalysisId
from scan_tool.domain.analysis_error import AnalysisError, ErrorCode
from scan_tool.domain.analysis_request import AnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult


class ContractViolation(ValueError):
    """Redacted model validation failure with a stable Analysis I/O error code."""

    def __init__(self, code: ErrorCode, issues: tuple[str, ...]) -> None:
        self.code = code
        self.issues = issues
        super().__init__(f"{code.value}: {'; '.join(issues)}")


_ANALYSIS_ID_ADAPTER = TypeAdapter(AnalysisId)


def validate_analysis_id(value: str) -> str:
    try:
        return _ANALYSIS_ID_ADAPTER.validate_python(value)
    except ValidationError:
        raise ContractViolation(
            ErrorCode.INVALID_INPUT,
            ("analysis_id:string_pattern_mismatch:invalid analysis ID",),
        ) from None


def validate_analysis_request(data: object) -> AnalysisRequest:
    """Validate a request and classify domain inputs separately from schema errors."""
    try:
        return AnalysisRequest.model_validate(data)
    except ValidationError as error:
        code = _request_error_code(error)
        raise ContractViolation(code, _redacted_issues(error)) from None


def validate_analysis_result(data: object) -> AnalysisResult:
    """Validate a result and its single-document reference invariants."""
    try:
        return AnalysisResult.model_validate(data)
    except ValidationError as error:
        raise ContractViolation(
            ErrorCode.SCHEMA_INVALID,
            _redacted_issues(error),
        ) from None


def validate_analysis_error(data: object) -> AnalysisError:
    """Validate a standalone structured error."""
    try:
        return AnalysisError.model_validate(data)
    except ValidationError as error:
        raise ContractViolation(
            ErrorCode.SCHEMA_INVALID,
            _redacted_issues(error),
        ) from None


def validate_analysis_pair(
    request_data: object,
    result_data: object,
) -> tuple[AnalysisRequest, AnalysisResult]:
    """Validate request/result envelopes and cross-document source constraints."""
    request = validate_analysis_request(request_data)
    result = validate_analysis_result(result_data)
    request_value = request.root
    result_value = result.root

    if (
        request_value.analysis_id != result_value.analysis_id
        or request_value.analysis_type != result_value.analysis_type
        or request_value.chain_id != result_value.chain_id
        or request_value.schema_version != result_value.schema_version
    ):
        raise ContractViolation(
            ErrorCode.SCHEMA_INVALID,
            ("request and result envelopes must match",),
        )

    allowed_source_ids = set(request_value.source_policy.allowed_source_ids)
    actual_source_ids = {source.source_id for source in result_value.sources}
    if not actual_source_ids <= allowed_source_ids:
        raise ContractViolation(
            ErrorCode.SCHEMA_INVALID,
            ("result contains a source outside allowed_source_ids",),
        )
    return request, result


def _request_error_code(error: ValidationError) -> ErrorCode:
    issues = error.errors(include_input=False, include_url=False)
    if issues and all(_is_invalid_input_issue(issue) for issue in issues):
        return ErrorCode.INVALID_INPUT
    return ErrorCode.SCHEMA_INVALID


def _is_invalid_input_issue(issue: Mapping[str, object]) -> bool:
    error_type = str(issue["type"])
    if error_type in {"invalid_input", "union_tag_invalid"}:
        return True
    if error_type in {"extra_forbidden", "timezone_aware", "datetime_type"}:
        return False

    location = tuple(str(part) for part in issue["loc"])
    domain_fields = {
        "analysis_type",
        "chain_id",
        "inputs",
        "source_policy",
        "transaction_hash",
        "subject_address",
        "token_address",
        "spender_address",
        "approval_transaction_hash",
        "consumption_transaction_hash",
        "state_blocks",
        "event_transaction_hashes",
        "context_urls",
    }
    return bool(set(location) & domain_fields)


def _redacted_issues(error: ValidationError) -> tuple[str, ...]:
    return tuple(
        f"{'.'.join(str(part) for part in issue['loc']) or '<root>'}:{issue['type']}:{issue['msg']}"
        for issue in error.errors(include_input=False, include_url=False)
    )
