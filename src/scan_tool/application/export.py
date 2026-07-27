"""Deterministic JSON and Markdown exports from one Analysis Result model."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.storage import ExportBundle, ExportRecord

type Clock = Callable[[], datetime]


class ResultExporter:
    def __init__(
        self,
        artifacts: ArtifactStore,
        storage: SQLiteStorage,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._artifacts = artifacts
        self._storage = storage
        self._clock = clock or (lambda: datetime.now(UTC))

    def export(self, result: AnalysisResult) -> ExportBundle:
        document = result.to_contract_dict()
        json_body = (
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        markdown_text = render_evidence_markdown(document)
        created_at = self._clock()

        json_artifact = self._artifacts.write(
            json_body,
            media_type="application/json",
            artifact_kind="export",
        )
        markdown_artifact = self._artifacts.write(
            markdown_text.encode(),
            media_type="text/markdown",
            artifact_kind="export",
        )
        analysis_id = str(document["analysis_id"])
        schema_version = str(document["schema_version"])
        json_export = ExportRecord(
            export_id=f"EXP-{analysis_id}-JSON",
            analysis_id=analysis_id,
            export_type="result_json",
            artifact=json_artifact,
            schema_version=schema_version,
            created_at=created_at,
        )
        markdown_export = ExportRecord(
            export_id=f"EXP-{analysis_id}-MARKDOWN",
            analysis_id=analysis_id,
            export_type="evidence_markdown",
            artifact=markdown_artifact,
            schema_version=schema_version,
            created_at=created_at,
        )
        self._storage.record_export(json_export)
        self._storage.record_export(markdown_export)
        return ExportBundle(
            json_export=json_export,
            markdown_export=markdown_export,
            markdown_text=markdown_text,
        )


def render_evidence_markdown(document: dict[str, object]) -> str:
    lines = [
        f"# Analysis {document['analysis_id']}",
        "",
        f"- Analysis type: `{document['analysis_type']}`",
        f"- Status: `{document['status']}`",
        f"- Chain ID: `{document['chain_id']}`",
        f"- Schema version: `{document['schema_version']}`",
        f"- Tool version: `{_markdown_cell(document['run']['tool_version'])}`",  # type: ignore[index]
        "",
        "## Results",
        "",
        "| Result ID | Type | Classification | Value | Evidence |",
        "|:---|:---|:---|:---|:---|",
    ]
    for result in document["results"]:  # type: ignore[union-attr]
        value = _markdown_json(result["value"])
        evidence = ", ".join(f"`{item}`" for item in result["evidence_refs"])
        lines.append(
            f"| `{result['result_id']}` | `{result['result_type']}` | "
            f"`{result['classification']}` | `{value}` | {evidence} |"
        )

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Evidence ID | Type | Source record | Method | Locator | Decoded |",
            "|:---|:---|:---|:---|:---|:---|",
        ]
    )
    for evidence in document["evidence"]:  # type: ignore[union-attr]
        lines.append(
            f"| `{evidence['evidence_id']}` | `{evidence['evidence_type']}` | "
            f"`{evidence['source_record_ref']}` | "
            f"`{_markdown_cell(evidence['method'])}` | "
            f"`{_markdown_json(evidence['locator'])}` | "
            f"`{_markdown_json(evidence['decoded'])}` |"
        )

    lines.extend(
        [
            "",
            "## Sources",
            "",
            "| Source record | Source ID | Provider | Capability | Retrieved at |",
            "|:---|:---|:---|:---|:---|",
        ]
    )
    for source in document["sources"]:  # type: ignore[union-attr]
        lines.append(
            f"| `{source['source_record_id']}` | `{source['source_id']}` | "
            f"`{source['provider_id']}` | `{_markdown_cell(source['capability'])}` | "
            f"`{source['retrieved_at']}` |"
        )
    lines.extend(
        [
            "",
            "## Canonical Result JSON",
            "",
            "```json",
            _safe_json_for_markdown(document),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_json(value: object) -> str:
    return _markdown_cell(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _markdown_cell(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _safe_json_for_markdown(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
