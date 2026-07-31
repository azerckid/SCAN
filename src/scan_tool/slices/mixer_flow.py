"""Deterministic offline TASK-016 mixer_flow analyzer."""

from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import MixerFlowAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.mixer_flow import (
    MixerEventReference,
    MixerFlowIncomplete,
    MixerFlowReplay,
    MixerRawObservation,
    parse_mixer_flow_replay,
    reconstruct_mixer_flow_facts,
)

CHECKPOINT_ID = "CP-MIXER-FLOW-REPLAY-EVIDENCE"
REQUIRED_SOURCE_IDS = {"DS-EVM-RPC-ARCHIVE", "DS-SANCTIONS-PUBLIC"}


def analyze_mixer_flow_replay(
    request: MixerFlowAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Evaluate one reviewed mixer deposit/withdraw candidate package."""
    try:
        replay = parse_mixer_flow_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed mixer flow replay does not match the offline evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )

    binding_error = _replay_binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)

    try:
        facts = reconstruct_mixer_flow_facts(package_dir, replay)
    except MixerFlowIncomplete as error:
        return _partial(request, replay, str(error), resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "reconciliation_failed",
            "The mixer flow events do not satisfy the pinned chain, window, and label bindings.",
            "mixer_reconciliation",
            resumed,
            checkpoint_id,
        )

    input_error = _input_binding_error(request, replay, facts)
    if input_error is not None:
        return _failed(request, *input_error, resumed, checkpoint_id)

    candidates = facts.get("withdraw_candidates")
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict) and item.get("linkage_strength") == "confirmed":
                return _failed(
                    request,
                    "reconciliation_failed",
                    "Mixer withdraw linkage cannot be promoted to confirmed ownership.",
                    "linkage_promotion_rejected",
                    resumed,
                    checkpoint_id,
                )

    evidence = _complete_evidence(replay)
    result = {
        "result_id": "RES-MIXER-FLOW",
        "result_type": "mixer_flow",
        "classification": "confirmed_fact",
        "value": facts,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [
            "REQ-MIX-DEPOSIT",
            "REQ-MIX-WITHDRAW-CANDIDATES",
            "REQ-MIX-LABEL",
        ],
        "evidence_refs": [item["evidence_id"] for item in evidence],
    }
    return _result(
        request,
        replay,
        "complete",
        [result],
        evidence,
        [],
        resumed,
        checkpoint_id,
    )


def _replay_binding_error(
    request: MixerFlowAnalysisRequest,
    replay: MixerFlowReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return (
            "rule_restricted",
            "TASK-016 mixer_flow currently executes offline artifact replay only.",
            "rule_check",
        )
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and mixer flow replay fixture IDs differ.",
            "fixture_binding",
        )
    allowed_sources = set(request.source_policy.allowed_source_ids)
    ordered_sources = set(request.source_policy.source_order)
    if not allowed_sources >= REQUIRED_SOURCE_IDS or not ordered_sources >= REQUIRED_SOURCE_IDS:
        return (
            "rule_restricted",
            "Mixer flow replay requires the approved archive and sanctions sources.",
            "source_binding",
        )
    return None


def _input_binding_error(
    request: MixerFlowAnalysisRequest,
    replay: MixerFlowReplay,
    facts: dict[str, object],
) -> tuple[str, str, str] | None:
    inputs = request.inputs
    if inputs.subject_address.lower() != replay.subject_address.lower():
        return (
            "reconciliation_failed",
            "Requested subject address differs from the replay package.",
            "subject_binding",
        )
    if inputs.pool_address.lower() != replay.pool_address.lower():
        return (
            "reconciliation_failed",
            "Requested pool address differs from the replay package.",
            "pool_binding",
        )
    if inputs.observation_window.start_block != replay.observation_window.start_block:
        return (
            "reconciliation_failed",
            "Requested observation window start differs from the replay package.",
            "window_start_binding",
        )
    if inputs.observation_window.end_block != replay.observation_window.end_block:
        return (
            "reconciliation_failed",
            "Requested observation window end differs from the replay package.",
            "window_end_binding",
        )
    attribution = facts.get("attribution")
    if not isinstance(attribution, dict):
        return (
            "reconciliation_failed",
            "Mixer attribution envelope is missing.",
            "attribution_binding",
        )
    if (
        attribution.get("ownership") != "not_assessed"
        or attribution.get("criminality") != "not_assessed"
    ):
        return (
            "reconciliation_failed",
            "Mixer ownership and criminality must remain not_assessed.",
            "attribution_assessed_rejected",
        )
    return None


def _complete_evidence(replay: MixerFlowReplay) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    primary_observations = sorted(
        (
            observation
            for observation in replay.raw_observations
            if observation.provider_role == "PRIMARY"
        ),
        key=lambda item: item.event_index,
    )
    for index, (event, observation) in enumerate(
        zip(replay.events, primary_observations, strict=True),
        start=1,
    ):
        evidence.append(_event_evidence(replay, event, observation, index))
    evidence.append(_candidate_evidence(replay))
    evidence.append(_label_evidence(replay))
    return evidence


def _event_evidence(
    replay: MixerFlowReplay,
    event: MixerEventReference,
    observation: MixerRawObservation,
    index: int,
) -> dict[str, object]:
    artifact_uri = observation.artifacts.transaction
    if artifact_uri is MISSING:
        raise MixerFlowIncomplete("event transaction artifact is unavailable")
    return {
        "evidence_id": f"EV-MIX-EVT-{index}",
        "evidence_type": "event",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-MIX-ETHEREUM",
        "method": f"mixer_{event.event_kind}_event",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": event.block_number,
            "transaction_hash": event.transaction_hash,
        },
        "decoded": {
            "event_kind": event.event_kind,
            "pool_address": event.pool_address,
            "provider_id": observation.provider_id,
            "classification": "confirmed_fact",
        },
        "raw_artifact": {
            "artifact_uri": artifact_uri,
            "media_type": "application/json",
        },
    }


def _candidate_evidence(replay: MixerFlowReplay) -> dict[str, object]:
    withdraw_count = sum(1 for event in replay.events if event.event_kind == "withdraw")
    return {
        "evidence_id": "EV-MIX-CANDIDATES",
        "evidence_type": "context",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-MIX-ETHEREUM",
        "method": "withdraw_candidate_set",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": replay.observation_window.end_block,
        },
        "decoded": {
            "candidate_count": withdraw_count,
            "linkage_strength": "candidate",
            "classification": "heuristic_candidate",
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
            "media_type": "application/json",
        },
    }


def _label_evidence(replay: MixerFlowReplay) -> dict[str, object]:
    return {
        "evidence_id": "EV-MIX-LABEL",
        "evidence_type": "context",
        "source_id": "DS-SANCTIONS-PUBLIC",
        "source_record_ref": "SRC-MIX-SANCTIONS",
        "method": "gov_registry_label_assertion",
        "retrieved_at": replay.captured_at,
        "locator": {
            "url": "https://home.treasury.gov/news/press-releases/jy0916",
        },
        "decoded": {
            "entity": "Tornado Cash",
            "artifact_path": replay.label_provenance.artifact_path,
            "classification": "evidence_backed_assertion",
        },
        "raw_artifact": {
            "artifact_uri": (
                f"fixture://{replay.fixture_id}/{replay.label_provenance.artifact_path}"
            ),
            "media_type": "application/json",
        },
    }


def _partial(
    request: MixerFlowAnalysisRequest,
    replay: MixerFlowReplay,
    reason: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    evidence = [
        {
            "evidence_id": f"EV-MIX-PARTIAL-{index}",
            "evidence_type": "context",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-MIX-ETHEREUM",
            "method": "available_mixer_leg",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "transaction_hash": replay.events[observation.event_index].transaction_hash,
            },
            "decoded": {"event_index": observation.event_index, "status": "incomplete"},
            "raw_artifact": {
                "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
                "media_type": "application/json",
            },
        }
        for index, observation in enumerate(
            sorted(replay.raw_observations, key=lambda item: item.event_index),
            start=1,
        )
    ]
    result = {
        "result_id": "RES-MIXER-FLOW-PARTIAL",
        "result_type": "mixer_flow",
        "classification": "confirmed_fact",
        "value": {
            "available_events": len(replay.raw_observations),
            "attribution": {"ownership": "not_assessed", "criminality": "not_assessed"},
        },
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [],
        "evidence_refs": [item["evidence_id"] for item in evidence],
    }
    errors = [
        _error(
            "evidence_incomplete",
            f"At least one mixer flow leg is incomplete: {reason}",
            "mixer_event_availability",
            [item["evidence_id"] for item in evidence],
            retryable=True,
        )
    ]
    return _result(request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id)


def _source_records(
    replay: MixerFlowReplay,
    referenced: set[str],
) -> list[dict[str, object]]:
    provider_id = (
        replay.raw_observations[0].provider_id.lower()
        if replay.raw_observations
        else "mixer-ethereum-replay"
    )
    candidates = [
        (
            "SRC-MIX-ETHEREUM",
            "DS-EVM-RPC-ARCHIVE",
            provider_id,
            "scoring",
            "ethereum_mixer_event_replay",
        ),
        (
            "SRC-MIX-SANCTIONS",
            "DS-SANCTIONS-PUBLIC",
            "ofac-tornado-public",
            "supporting",
            "gov_registry_label_assertion",
        ),
    ]
    return [
        {
            "source_record_id": record_id,
            "source_id": source_id,
            "provider_id": provider_id_value,
            "role": role,
            "required": True,
            "capability": capability,
            "endpoint_host": "reviewed.replay.invalid",
            "retrieved_at": replay.captured_at,
        }
        for record_id, source_id, provider_id_value, role, capability in candidates
        if record_id in referenced
    ]


def _result(
    request: MixerFlowAnalysisRequest,
    replay: MixerFlowReplay,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    referenced = {str(item["source_record_ref"]) for item in evidence}
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": status,
            "results": results,
            "evidence": evidence,
            "sources": _source_records(replay, referenced),
            "warnings": [],
            "errors": errors,
            "run": _run(
                request.requested_at,
                max(request.requested_at, replay.captured_at),
                resumed,
                checkpoint_id,
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _failed(
    request: MixerFlowAnalysisRequest,
    code: str,
    message: str,
    stage: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": "failed",
            "results": [],
            "evidence": [],
            "sources": [],
            "warnings": [],
            "errors": [_error(code, message, stage, [])],
            "run": _run(request.requested_at, request.requested_at, resumed, checkpoint_id),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _error(
    code: str,
    message: str,
    stage: str,
    evidence_ids: list[str],
    *,
    retryable: bool = False,
) -> dict[str, object]:
    error: dict[str, object] = {
        "error_id": f"ERR-MIX-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "attempt_count": 0,
    }
    if evidence_ids:
        error["related_evidence_ids"] = evidence_ids
    return error


def _run(
    started_at: datetime,
    finished_at: datetime,
    resumed: bool,
    checkpoint_id: str | None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "tool_version": __version__,
        "execution_mode": "offline_replay",
        "started_at": started_at,
        "finished_at": max(started_at, finished_at),
        "cache_hits": 1,
        "cache_misses": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "resumed": resumed,
    }
    if checkpoint_id is not None:
        value["checkpoint_id"] = checkpoint_id
    return value


def _pending_exports(analysis_id: str) -> dict[str, object]:
    return {
        "json": {"artifact_uri": f"artifact://pending/{analysis_id}/result.json"},
        "markdown": {"artifact_uri": f"artifact://pending/{analysis_id}/evidence.md"},
    }
