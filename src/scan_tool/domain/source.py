"""Pure source request, response, attempt, and error models."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import JsonValue

from scan_tool.domain.analysis_error import ErrorCode


class SourceFailureKind(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"
    PERMANENT = "permanent"


class SourceAttemptOutcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JsonRpcSourceRequest:
    capability: str
    method: str
    params: JsonValue
    block_tag: str | int | None = None

    def __post_init__(self) -> None:
        if not self.capability or not self.method:
            raise ValueError("source capability and method must not be empty")


@dataclass(frozen=True, slots=True)
class RestSourceRequest:
    capability: str
    method: Literal["GET", "POST"]
    path: str
    params: dict[str, JsonValue] | None = None
    json_body: JsonValue | None = None
    block_tag: str | int | None = None

    def __post_init__(self) -> None:
        if not self.capability:
            raise ValueError("source capability must not be empty")
        if not self.path.startswith("/") or "?" in self.path or "#" in self.path:
            raise ValueError("REST path must be an absolute path without query or fragment")


type SourceRequest = JsonRpcSourceRequest | RestSourceRequest


@dataclass(frozen=True, slots=True)
class SourcePayload:
    raw_bytes: bytes = field(repr=False)
    status_code: int
    media_type: str | None
    endpoint_host: str
    endpoint_path: str
    retrieved_at: datetime

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceAttempt:
    source_id: str
    provider_id: str
    attempt_number: int
    started_at: datetime
    finished_at: datetime
    outcome: SourceAttemptOutcome
    failure_kind: SourceFailureKind | None
    status_code: int | None
    retryable: bool
    wait_seconds: float | None
    raw_sha256: str | None


@dataclass(frozen=True, slots=True)
class SourceResponse:
    source_id: str
    provider_id: str
    request_fingerprint: str
    payload: SourcePayload
    attempts: tuple[SourceAttempt, ...]
    fallback_from: tuple[str, ...]
    cache_status: Literal["not_checked", "hit", "miss"] = "not_checked"


@dataclass(frozen=True, slots=True)
class SourceExecutionError:
    code: ErrorCode
    message: str
    stage: str
    source_id: str | None
    provider_id: str | None
    retryable: bool
    attempt_count: int


@dataclass(frozen=True, slots=True)
class SourceExecution:
    response: SourceResponse | None
    attempts: tuple[SourceAttempt, ...]
    error: SourceExecutionError | None

    def __post_init__(self) -> None:
        if (self.response is None) == (self.error is None):
            raise ValueError("source execution must contain exactly one response or error")

    @property
    def succeeded(self) -> bool:
        return self.response is not None


class SourceFailure(Exception):
    """Safe adapter failure that never includes a raw URL or credential."""

    def __init__(
        self,
        kind: SourceFailureKind,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: str | None = None,
        raw_bytes: bytes | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.retry_after = retry_after
        self.raw_bytes = raw_bytes


def source_request_fingerprint(request: SourceRequest) -> str:
    """Hash a provider-independent canonical request without credentials."""
    if isinstance(request, JsonRpcSourceRequest):
        payload: dict[str, JsonValue] = {
            "kind": "json_rpc",
            "capability": request.capability,
            "method": request.method,
            "params": request.params,
            "block_tag": request.block_tag,
        }
    else:
        payload = {
            "kind": "rest",
            "capability": request.capability,
            "method": request.method,
            "path": request.path,
            "params": request.params,
            "json_body": request.json_body,
            "block_tag": request.block_tag,
        }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()
