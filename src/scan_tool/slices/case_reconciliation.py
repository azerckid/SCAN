"""Deterministic offline TASK-018 case reconciliation analyzer."""

from pathlib import Path

from pydantic import ValidationError

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import CaseReconciliationAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.case_reconciliation import (
    CaseReconciliationIncomplete,
    CaseReconciliationReplay,
    parse_case_reconciliation_replay,
    reconstruct_case_facts,
)

REQUIRED_SOURCE_IDS = {"DS-EVM-RPC-PUBLIC", "DS-EXPLORER-EVM", "DS-OSINT-WEB"}
REQUIRED_SOURCE_ORDER = (
    "DS-EVM-RPC-PUBLIC",
    "DS-EXPLORER-EVM",
    "DS-OSINT-WEB",
)


def analyze_case_reconciliation_replay(
    request: CaseReconciliationAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-CASE-RECONCILIATION",
) -> AnalysisResult:
    try:
        replay = parse_case_reconciliation_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(request, "decode_failed", "Case replay is invalid.", "decode_replay")
    binding = _binding_error(request, replay)
    if binding is not None:
        return _failed(request, *binding)
    try:
        facts = reconstruct_case_facts(
            package_dir,
            replay,
            max_timeline_entries=request.inputs.max_timeline_entries,
        )
    except CaseReconciliationIncomplete as error:
        return _failed(request, "source_unavailable", str(error), "case_scope")
    except (KeyError, OSError, TypeError, ValueError):
        return _failed(
            request,
            "reconciliation_failed",
            "Pinned case sources do not reconcile.",
            "source_reconciliation",
        )
    evidence = _evidence(replay)
    results = [
        {
            "result_id": "RES-CASE-TECHNICAL",
            "result_type": "case_reconciliation",
            "classification": "confirmed_fact",
            "value": facts,
            "tool_requirement_ids": ["REQ-P0-EVM-001"],
            "fixture_requirement_ids": [
                "REQ-CASE-TIMELINE",
                "REQ-CASE-UNRELATED-FUND",
                "REQ-CASE-ATTRIBUTION-BOUNDARY",
            ],
            "evidence_refs": [item["evidence_id"] for item in evidence],
        },
        {
            "result_id": "RES-CASE-CONTEXT",
            "result_type": "case_context",
            "classification": "external_context",
            "value": {
                "url": replay.incident_context_url,
                "use": "incident_chronology_only",
                "address_ownership": "not_assessed",
                "criminal_intent": "not_assessed",
            },
            "tool_requirement_ids": ["REQ-P0-EVM-001"],
            "fixture_requirement_ids": ["REQ-CASE-ATTRIBUTION-BOUNDARY"],
            "evidence_refs": ["EV-CASE-CONTEXT"],
        },
    ]
    return _partial_result(request, replay, results, evidence, resumed, checkpoint_id)


def _binding_error(
    request: CaseReconciliationAnalysisRequest,
    replay: CaseReconciliationReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return ("rule_restricted", "Case v1 requires reviewed offline replay.", "rule_check")
    if request.fixture_id != replay.fixture_id:
        return ("reconciliation_failed", "Request and replay fixture IDs differ.", "fixture")
    if request.inputs.case_category != replay.case_category:
        return ("reconciliation_failed", "Request and replay case categories differ.", "category")
    if request.inputs.seed_transaction_hash != replay.seed_transaction_hash:
        return ("reconciliation_failed", "Request and replay seed transactions differ.", "seed")
    if set(request.inputs.source_fixture_refs) != set(replay.source_fixture_refs):
        return (
            "reconciliation_failed",
            "Request and replay source fixture sets differ.",
            "source_fixture_binding",
        )
    if (
        set(request.source_policy.allowed_source_ids) != REQUIRED_SOURCE_IDS
        or tuple(request.source_policy.source_order) != REQUIRED_SOURCE_ORDER
    ):
        return ("rule_restricted", "Case replay source allowlist differs.", "source_binding")
    return None


def _evidence(replay: CaseReconciliationReplay) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, pin in enumerate(sorted(replay.source_pins, key=lambda item: item.fixture_id)):
        evidence_source_id = (
            "DS-EXPLORER-EVM" if pin.fixture_id == "FX-FLOW-PATH-001" else "DS-EVM-RPC-PUBLIC"
        )
        evidence_source_ref = (
            "SRC-CASE-EXPLORER" if evidence_source_id == "DS-EXPLORER-EVM" else "SRC-CASE-ONCHAIN"
        )
        records.append(
            {
                "evidence_id": f"EV-CASE-EXPECTED-{index}",
                "evidence_type": "context",
                "source_id": "DS-EVM-RPC-PUBLIC",
                "source_record_ref": "SRC-CASE-ONCHAIN",
                "method": "confirmed_fixture_composition",
                "retrieved_at": replay.captured_at,
                "locator": {"chain_id": replay.chain_id},
                "decoded": {
                    "fixture_id": pin.fixture_id,
                    "expected_sha256": pin.expected_sha256,
                    "evidence_sha256": pin.evidence_sha256,
                },
                "raw_artifact": {
                    "artifact_uri": f"artifact://sha256/{pin.expected_sha256}",
                    "sha256": pin.expected_sha256,
                    "media_type": "application/json",
                },
            }
        )
        records.append(
            {
                "evidence_id": f"EV-CASE-EVIDENCE-{index}",
                "evidence_type": "context",
                "source_id": evidence_source_id,
                "source_record_ref": evidence_source_ref,
                "method": "confirmed_fixture_evidence_pin",
                "retrieved_at": replay.captured_at,
                "locator": {"chain_id": replay.chain_id},
                "decoded": {
                    "fixture_id": pin.fixture_id,
                    "evidence_sha256": pin.evidence_sha256,
                },
                "raw_artifact": {
                    "artifact_uri": f"artifact://sha256/{pin.evidence_sha256}",
                    "sha256": pin.evidence_sha256,
                    "media_type": "application/json",
                },
            }
        )
    records.append(
        {
            "evidence_id": "EV-CASE-CONTEXT",
            "evidence_type": "context",
            "source_id": "DS-OSINT-WEB",
            "source_record_ref": "SRC-CASE-CONTEXT",
            "method": "official_incident_timeline_locator",
            "retrieved_at": replay.captured_at,
            "locator": {"url": replay.incident_context_url},
            "decoded": {
                "use": "incident_chronology_only",
                "attribution_scored": False,
                "article_bytes_stored": False,
            },
            "raw_artifact": {
                "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
                "media_type": "application/vnd.scan.source-locator+json",
            },
        }
    )
    return records


def _partial_result(
    request: CaseReconciliationAnalysisRequest,
    replay: CaseReconciliationReplay,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    observed = replay.captured_at.isoformat()
    return validate_analysis_result(
        {
            "$schema": "analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": "case_reconciliation",
            "chain_id": 1,
            "status": "partial",
            "results": results,
            "evidence": evidence,
            "sources": [
                {
                    "source_record_id": "SRC-CASE-ONCHAIN",
                    "source_id": "DS-EVM-RPC-PUBLIC",
                    "provider_id": "confirmed.fixture.bundle",
                    "role": "scoring",
                    "required": True,
                    "capability": "selected_case_timeline",
                    "endpoint_host": "offline.fixture",
                    "retrieved_at": replay.captured_at,
                },
                {
                    "source_record_id": "SRC-CASE-CONTEXT",
                    "source_id": "DS-OSINT-WEB",
                    "provider_id": "euler.official",
                    "role": "context",
                    "required": False,
                    "capability": "incident_chronology",
                    "endpoint_host": "euler.finance",
                    "retrieved_at": replay.captured_at,
                },
                {
                    "source_record_id": "SRC-CASE-EXPLORER",
                    "source_id": "DS-EXPLORER-EVM",
                    "provider_id": "confirmed.fixture.explorer",
                    "role": "supporting",
                    "required": True,
                    "capability": "internal_transfer_cross_check",
                    "endpoint_host": "offline.fixture",
                    "retrieved_at": replay.captured_at,
                },
            ],
            "warnings": [],
            "errors": [
                {
                    "error_id": "ERR-CASE-SCOPE",
                    "code": "evidence_incomplete",
                    "stage": "case_scope",
                    "message": (
                        "Selected transactions prove a bounded exit path, not full seed discovery, "
                        "continuous fund coverage, exploit causation, ownership, or intent."
                    ),
                    "retryable": False,
                    "attempt_count": 1,
                }
            ],
            "run": {
                "tool_version": __version__,
                "execution_mode": "offline_replay",
                "started_at": observed,
                "finished_at": observed,
                "cache_hits": 0,
                "cache_misses": len(evidence),
                "retry_count": 0,
                "fallback_count": 0,
                "resumed": resumed,
                **({"checkpoint_id": checkpoint_id} if checkpoint_id else {}),
            },
            "exports": {
                "json": {"artifact_uri": "artifact://pending/case-result"},
                "markdown": {"artifact_uri": "artifact://pending/case-evidence"},
            },
        }
    )


def _failed(
    request: CaseReconciliationAnalysisRequest,
    code: str,
    message: str,
    stage: str,
) -> AnalysisResult:
    observed = request.requested_at.isoformat()
    return validate_analysis_result(
        {
            "$schema": "analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": "case_reconciliation",
            "chain_id": 1,
            "status": "failed",
            "results": [],
            "evidence": [],
            "sources": [],
            "warnings": [],
            "errors": [
                {
                    "error_id": "ERR-CASE-ANALYSIS",
                    "code": code,
                    "stage": stage,
                    "message": message,
                    "retryable": False,
                    "attempt_count": 1,
                }
            ],
            "run": {
                "tool_version": __version__,
                "execution_mode": "offline_replay",
                "started_at": observed,
                "finished_at": observed,
                "cache_hits": 0,
                "cache_misses": 0,
                "retry_count": 0,
                "fallback_count": 0,
                "resumed": False,
            },
            "exports": {
                "json": {"artifact_uri": "artifact://pending/case-result"},
                "markdown": {"artifact_uri": "artifact://pending/case-evidence"},
            },
        }
    )
