"""Stable terminal rendering for Analysis I/O 0.1."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from pydantic.experimental.missing_sentinel import MISSING

from scan_tool.domain.analysis_error import ErrorCode
from scan_tool.domain.analysis_result import AnalysisResult, AnalysisStatus, Classification

EXIT_COMPLETE = 0
EXIT_INPUT = 2
EXIT_PARTIAL = 3
EXIT_FAILED = 4
EXIT_RESTRICTED = 5
EXIT_INTERRUPTED = 130


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    status: str
    detail: str


def exit_code_for_result(result: AnalysisResult) -> int:
    document = result.root
    if document.status == AnalysisStatus.COMPLETE:
        return EXIT_COMPLETE
    if document.status == AnalysisStatus.PARTIAL:
        return EXIT_PARTIAL
    first_code = document.errors[0].code
    if first_code in {ErrorCode.INVALID_INPUT, ErrorCode.SCHEMA_INVALID}:
        return EXIT_INPUT
    if first_code == ErrorCode.RULE_RESTRICTED:
        return EXIT_RESTRICTED
    return EXIT_FAILED


def render_progress(events: Iterable[ProgressEvent], stream: TextIO) -> None:
    for event in events:
        stream.write(f"{event.status.upper():<10} {event.detail}\n")
    stream.flush()


def render_result(
    result: AnalysisResult,
    stdout: TextIO,
    stderr: TextIO,
    *,
    export_uris: tuple[str, str] | None = None,
) -> int:
    document = result.root
    status = str(document.status).upper()
    stdout.write(
        f"{status} {document.analysis_id} · {document.analysis_type} · chain {document.chain_id}\n"
    )

    confirmed = [
        item for item in document.results if item.classification == Classification.CONFIRMED_FACT
    ]
    scoped = [
        item for item in document.results if item.classification != Classification.CONFIRMED_FACT
    ]
    if confirmed:
        stdout.write("\nCONFIRMED RESULTS\n")
        for item in confirmed:
            stdout.write(f"{item.result_type:<20} {_compact_value(item.value)}\n")
    if scoped:
        stdout.write("\nSCOPE\n")
        for item in scoped:
            label = str(item.classification).upper().replace("_", " ")
            stdout.write(f"{label:<14} {item.result_type} · {_compact_value(item.value)}\n")

    for warning in document.warnings:
        stderr.write(f"WARNING    {warning.code} · {_single_line(warning.message)}\n")
    for error in document.errors:
        source = "" if error.source_id is MISSING else f" source={error.source_id}"
        stderr.write(
            f"ERROR      {error.code} stage={error.stage}{source} attempts={error.attempt_count}\n"
        )

    first_error = "none" if not document.errors else str(document.errors[0].code)
    stdout.write(
        "\nRUN "
        f"cache {document.run.cache_hits} hit/{document.run.cache_misses} miss · "
        f"retry {document.run.retry_count} · fallback {document.run.fallback_count} · "
        f"resumed {'yes' if document.run.resumed else 'no'} · first_error {first_error}\n"
    )
    json_uri, markdown_uri = export_uris or (
        document.exports.json_export.artifact_uri,
        document.exports.markdown.artifact_uri,
    )
    stdout.write(f"JSON       {json_uri}\n")
    stdout.write(f"Markdown   {markdown_uri}\n")
    stdout.flush()
    stderr.flush()
    return exit_code_for_result(result)


def safe_path_label(path: Path) -> str:
    return path.name or "<input>"


def _compact_value(value: dict[str, object]) -> str:
    preferred = (
        "symbol",
        "amount_raw",
        "before",
        "after",
        "target_address",
        "theft_or_phishing_claim",
        "circle_address_specific",
        "ofac_address_specific",
        "current_sanctions_status",
        "criminal_intent",
        "global_pause",
    )
    parts = []
    for key in value:
        if key in preferred or key.endswith("_raw"):
            parts.append(f"{key}={_compact_scalar(value[key])}")
    if not parts:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return _truncate(body, 56)
    return " · ".join(parts)


def _compact_scalar(value: object) -> str:
    if isinstance(value, str) and value.startswith("0x") and len(value) > 22:
        return f"{value[:10]}…{value[-8:]}"
    if isinstance(value, str) and value.isdecimal():
        return value
    return _truncate(_single_line(str(value)), 40)


def _single_line(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return f"{value[: width - 1]}…"
