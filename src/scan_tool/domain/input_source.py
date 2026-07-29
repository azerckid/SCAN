"""Input-mode and normalized evidence models shared by RPC and artifacts."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from pydantic import JsonValue


class InputMode(StrEnum):
    EXTERNAL_RPC = "external_rpc"
    CONTEST_RPC = "contest_rpc"
    PROVIDED_ARTIFACT = "provided_artifact"


class ChainScope(StrEnum):
    EVM = "evm"
    BITCOIN = "bitcoin"
    NON_EVM = "non_evm"
    CROSS_CHAIN = "cross_chain"


class ArtifactFormat(StrEnum):
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"


class InputFailureKind(StrEnum):
    INVALID_ARTIFACT = "invalid_artifact"
    ARTIFACT_TOO_LARGE = "artifact_too_large"
    TOO_MANY_RECORDS = "too_many_records"
    CHAIN_SCOPE_MISMATCH = "chain_scope_mismatch"
    UNSUPPORTED_INPUT = "unsupported_input"


class InputNormalizationError(ValueError):
    """Safe input failure that never reflects raw artifact content."""

    def __init__(self, kind: InputFailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True, slots=True)
class NormalizedEvidenceRecord:
    record_locator: str
    record_type: str
    data: JsonValue = field(repr=False)
    record_sha256: str

    def __post_init__(self) -> None:
        if not self.record_locator or not self.record_type:
            raise ValueError("record locator and type must not be empty")
        if re.fullmatch(r"[a-f0-9]{64}", self.record_sha256) is None:
            raise ValueError("record_sha256 must be a lowercase SHA-256")
        if self.data is None:
            raise ValueError("normalized evidence data must not be null")


@dataclass(frozen=True, slots=True)
class NormalizedEvidenceBundle:
    input_mode: InputMode
    chain_scope: ChainScope
    source_id: str
    provider_id: str
    media_type: str
    raw_sha256: str
    byte_length: int
    observed_at: datetime
    records: tuple[NormalizedEvidenceRecord, ...]

    def __post_init__(self) -> None:
        if re.fullmatch(r"DS-[A-Z0-9-]+", self.source_id) is None:
            raise ValueError("source_id must be a DS-* identifier")
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,63}", self.provider_id) is None:
            raise ValueError("provider_id is invalid")
        if not self.media_type:
            raise ValueError("media_type must not be empty")
        if re.fullmatch(r"[a-f0-9]{64}", self.raw_sha256) is None:
            raise ValueError("raw_sha256 must be a lowercase SHA-256")
        if self.byte_length <= 0:
            raise ValueError("byte_length must be positive")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        if not self.records:
            raise ValueError("normalized evidence must contain at least one record")
        locators = [record.record_locator for record in self.records]
        if len(locators) != len(set(locators)):
            raise ValueError("record locators must be unique")


@dataclass(frozen=True, slots=True)
class InputEvidenceEnvelope:
    """Bind normalized provenance to its content-addressed raw input."""

    bundle: NormalizedEvidenceBundle
    raw_artifact_uri: str

    def __post_init__(self) -> None:
        expected_uri = f"artifact://sha256/{self.bundle.raw_sha256}"
        if self.raw_artifact_uri != expected_uri:
            raise ValueError("raw artifact URI does not match the normalized input")

    def safe_details(self) -> dict[str, object]:
        """Return endpoint-free provenance suitable for an operation event."""
        return {
            "input_mode": self.bundle.input_mode.value,
            "chain_scope": self.bundle.chain_scope.value,
            "source_id": self.bundle.source_id,
            "provider_id": self.bundle.provider_id,
            "media_type": self.bundle.media_type,
            "raw_sha256": self.bundle.raw_sha256,
            "record_count": len(self.bundle.records),
            "record_locators": [record.record_locator for record in self.bundle.records],
            "record_sha256s": [record.record_sha256 for record in self.bundle.records],
        }


def canonical_record_sha256(data: JsonValue) -> str:
    """Hash one normalized JSON value independently of input serialization."""
    encoded = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def require_chain_scope(
    bundle: NormalizedEvidenceBundle,
    expected: ChainScope,
) -> NormalizedEvidenceBundle:
    """Reject routing a bundle into an analyzer for another chain model."""
    if bundle.chain_scope is not expected:
        raise InputNormalizationError(
            InputFailureKind.CHAIN_SCOPE_MISMATCH,
            "input chain scope does not match the analyzer",
        )
    return bundle
