"""Contest RPC and bounded provided-artifact input adapters."""

import csv
import hashlib
import io
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from pydantic import JsonValue

from scan_tool.adapters.http import JsonRpcSourceAdapter
from scan_tool.domain.input_source import (
    ArtifactFormat,
    ChainScope,
    InputFailureKind,
    InputMode,
    InputNormalizationError,
    NormalizedEvidenceBundle,
    NormalizedEvidenceRecord,
    canonical_record_sha256,
)
from scan_tool.domain.source import (
    JsonRpcSourceRequest,
    SourceFailure,
    SourceFailureKind,
    SourcePayload,
    SourceRequest,
    source_request_fingerprint,
)

DEFAULT_MAX_ARTIFACT_BYTES = 3 * 1024 * 1024
DEFAULT_MAX_RECORDS = 2_000
CONTEST_RPC_READ_ONLY_METHODS = frozenset(
    {
        "debug_traceTransaction",
        "eth_blockNumber",
        "eth_call",
        "eth_chainId",
        "eth_getBalance",
        "eth_getBlockByHash",
        "eth_getBlockByNumber",
        "eth_getCode",
        "eth_getLogs",
        "eth_getProof",
        "eth_getStorageAt",
        "eth_getTransactionByHash",
        "eth_getTransactionCount",
        "eth_getTransactionReceipt",
        "trace_transaction",
    }
)


class ProvidedArtifactImporter:
    """Import bounded JSON, JSONL, or CSV without guessing chain semantics."""

    def __init__(
        self,
        *,
        max_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
        max_records: int = DEFAULT_MAX_RECORDS,
    ) -> None:
        if max_bytes <= 0 or max_records <= 0:
            raise ValueError("artifact limits must be positive")
        self._max_bytes = max_bytes
        self._max_records = max_records

    def import_bytes(
        self,
        raw_bytes: bytes,
        *,
        artifact_format: ArtifactFormat,
        chain_scope: ChainScope,
        source_id: str = "DS-CONTEST-ARTIFACT",
        provider_id: str = "contest-artifact",
        record_type: str = "provided_record",
        observed_at: datetime | None = None,
    ) -> NormalizedEvidenceBundle:
        if not raw_bytes:
            raise InputNormalizationError(
                InputFailureKind.INVALID_ARTIFACT,
                "provided artifact must not be empty",
            )
        if len(raw_bytes) > self._max_bytes:
            raise InputNormalizationError(
                InputFailureKind.ARTIFACT_TOO_LARGE,
                "provided artifact exceeds the configured byte limit",
            )
        records = self._parse(raw_bytes, artifact_format)
        if not records:
            raise InputNormalizationError(
                InputFailureKind.INVALID_ARTIFACT,
                "provided artifact contains no records",
            )
        if len(records) > self._max_records:
            raise InputNormalizationError(
                InputFailureKind.TOO_MANY_RECORDS,
                "provided artifact exceeds the configured record limit",
            )
        normalized = tuple(
            self._record(
                locator=locator,
                value=value,
                record_type=record_type,
                expected_scope=chain_scope,
            )
            for locator, value in records
        )
        return NormalizedEvidenceBundle(
            input_mode=InputMode.PROVIDED_ARTIFACT,
            chain_scope=chain_scope,
            source_id=source_id,
            provider_id=provider_id,
            media_type=_media_type(artifact_format),
            raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            byte_length=len(raw_bytes),
            observed_at=observed_at or datetime.now(UTC),
            records=normalized,
        )

    def _parse(
        self,
        raw_bytes: bytes,
        artifact_format: ArtifactFormat,
    ) -> list[tuple[str, JsonValue]]:
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise InputNormalizationError(
                InputFailureKind.INVALID_ARTIFACT,
                "provided artifact is not valid UTF-8",
            ) from error
        try:
            if artifact_format is ArtifactFormat.JSON:
                value = json.loads(text, parse_constant=_reject_non_finite)
                if isinstance(value, list):
                    return [(f"json:$[{index}]", item) for index, item in enumerate(value)]
                return [("json:$", value)]
            if artifact_format is ArtifactFormat.JSONL:
                return [
                    (
                        f"jsonl:line={line_number}",
                        json.loads(line, parse_constant=_reject_non_finite),
                    )
                    for line_number, line in enumerate(text.splitlines(), start=1)
                    if line.strip()
                ]
            if artifact_format is ArtifactFormat.CSV:
                reader = csv.DictReader(io.StringIO(text))
                fieldnames = reader.fieldnames
                if (
                    not fieldnames
                    or any(not fieldname for fieldname in fieldnames)
                    or len(fieldnames) != len(set(fieldnames))
                ):
                    raise ValueError("CSV header is invalid")
                records = []
                for row_number, row in enumerate(reader, start=2):
                    if None in row:
                        raise ValueError("CSV row has more values than its header")
                    records.append((f"csv:row={row_number}", dict(row)))
                return records
        except (csv.Error, json.JSONDecodeError, ValueError) as error:
            raise InputNormalizationError(
                InputFailureKind.INVALID_ARTIFACT,
                "provided artifact could not be parsed",
            ) from error
        raise InputNormalizationError(
            InputFailureKind.UNSUPPORTED_INPUT,
            "provided artifact format is unsupported",
        )

    @staticmethod
    def _record(
        *,
        locator: str,
        value: JsonValue,
        record_type: str,
        expected_scope: ChainScope,
    ) -> NormalizedEvidenceRecord:
        if value is None:
            raise InputNormalizationError(
                InputFailureKind.INVALID_ARTIFACT,
                "provided artifact contains a null record",
            )
        if isinstance(value, Mapping):
            _require_record_chain_scope(value, expected_scope)
            if "jsonrpc" in value and "result" in value:
                value = value["result"]
                if value is None:
                    raise InputNormalizationError(
                        InputFailureKind.INVALID_ARTIFACT,
                        "JSON-RPC artifact result must not be null",
                    )
                if isinstance(value, Mapping):
                    _require_record_chain_scope(value, expected_scope)
        return NormalizedEvidenceRecord(
            record_locator=locator,
            record_type=record_type,
            data=value,
            record_sha256=canonical_record_sha256(value),
        )


class ContestRpcSourceAdapter(JsonRpcSourceAdapter):
    """Strict HTTPS JSON-RPC adapter tagged as a contest-provided input."""

    input_mode = InputMode.CONTEST_RPC

    def __init__(
        self,
        *,
        endpoint: str,
        client: httpx.AsyncClient,
        timeout: httpx.Timeout,
        chain_scope: ChainScope = ChainScope.EVM,
        source_id: str = "DS-CONTEST-RPC",
        provider_id: str = "contest-rpc",
    ) -> None:
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("contest RPC endpoint must be an absolute HTTPS URL")
        if parts.username is not None or parts.password is not None:
            raise ValueError("contest RPC endpoint must not contain URL userinfo")
        self.chain_scope = chain_scope
        super().__init__(
            source_id=source_id,
            provider_id=provider_id,
            endpoint=endpoint,
            client=client,
            timeout=timeout,
        )

    async def execute(self, request: SourceRequest) -> SourcePayload:
        if (
            not isinstance(request, JsonRpcSourceRequest)
            or request.method not in CONTEST_RPC_READ_ONLY_METHODS
        ):
            raise SourceFailure(
                SourceFailureKind.PERMANENT,
                "contest RPC method is not allowed",
            )
        return await super().execute(request)

    def normalize(
        self,
        request: JsonRpcSourceRequest,
        payload: SourcePayload,
    ) -> NormalizedEvidenceBundle:
        return normalize_json_rpc_payload(
            request=request,
            payload=payload,
            input_mode=self.input_mode,
            chain_scope=self.chain_scope,
            source_id=self.source_id,
            provider_id=self.provider_id,
        )


def normalize_json_rpc_payload(
    *,
    request: JsonRpcSourceRequest,
    payload: SourcePayload,
    input_mode: InputMode,
    chain_scope: ChainScope,
    source_id: str,
    provider_id: str,
) -> NormalizedEvidenceBundle:
    """Normalize one validated JSON-RPC payload without retaining its endpoint."""
    if input_mode not in {InputMode.EXTERNAL_RPC, InputMode.CONTEST_RPC}:
        raise InputNormalizationError(
            InputFailureKind.UNSUPPORTED_INPUT,
            "JSON-RPC payload requires an RPC input mode",
        )
    try:
        body = json.loads(payload.raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InputNormalizationError(
            InputFailureKind.INVALID_ARTIFACT,
            "JSON-RPC payload could not be parsed",
        ) from error
    if not isinstance(body, Mapping) or "error" in body or body.get("result") is None:
        raise InputNormalizationError(
            InputFailureKind.INVALID_ARTIFACT,
            "JSON-RPC payload does not contain a usable result",
        )
    value = body["result"]
    fingerprint = source_request_fingerprint(request)
    record = NormalizedEvidenceRecord(
        record_locator=f"rpc:{request.method}:{fingerprint}",
        record_type=request.capability,
        data=value,
        record_sha256=canonical_record_sha256(value),
    )
    return NormalizedEvidenceBundle(
        input_mode=input_mode,
        chain_scope=chain_scope,
        source_id=source_id,
        provider_id=provider_id,
        media_type=payload.media_type or "application/json",
        raw_sha256=payload.raw_sha256,
        byte_length=len(payload.raw_bytes),
        observed_at=payload.retrieved_at,
        records=(record,),
    )


def _require_record_chain_scope(
    value: Mapping[object, object],
    expected_scope: ChainScope,
) -> None:
    declared_scope = value.get("chain_scope")
    if declared_scope is not None and declared_scope != expected_scope.value:
        raise InputNormalizationError(
            InputFailureKind.CHAIN_SCOPE_MISMATCH,
            "provided artifact record has another chain scope",
        )


def _media_type(artifact_format: ArtifactFormat) -> str:
    return {
        ArtifactFormat.JSON: "application/json",
        ArtifactFormat.JSONL: "application/x-ndjson",
        ArtifactFormat.CSV: "text/csv",
    }[artifact_format]


def _reject_non_finite(value: str) -> JsonValue:
    raise ValueError(f"non-finite JSON number is unsupported: {value}")
