"""Deterministic offline TASK-016 cex_cluster analyzer."""

from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import CexClusterAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.cex_cluster import (
    CexClusterIncomplete,
    CexClusterReplay,
    CexRawObservation,
    CexTransferReference,
    parse_cex_cluster_replay,
    reconstruct_cex_cluster_facts,
)

CHECKPOINT_ID = "CP-CEX-CLUSTER-REPLAY-EVIDENCE"
REQUIRED_SOURCE_IDS = {"DS-EVM-RPC-ARCHIVE", "DS-SANCTIONS-PUBLIC"}


def analyze_cex_cluster_replay(
    request: CexClusterAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Link one reviewed CEX deposit cluster from content-addressed artifacts."""
    try:
        replay = parse_cex_cluster_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed CEX cluster replay does not match the offline evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )

    binding_error = _replay_binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)

    try:
        facts = reconstruct_cex_cluster_facts(package_dir, replay)
    except CexClusterIncomplete as error:
        return _partial(request, replay, str(error), resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "reconciliation_failed",
            "The CEX cluster transfers do not satisfy the pinned chain, window, and label bindings.",
            "cex_reconciliation",
            resumed,
            checkpoint_id,
        )

    input_error = _input_binding_error(request, replay, facts)
    if input_error is not None:
        return _failed(request, *input_error, resumed, checkpoint_id)

    evidence = _complete_evidence(replay)
    result = {
        "result_id": "RES-CEX-CLUSTER",
        "result_type": "cex_cluster",
        "classification": "confirmed_fact",
        "value": facts,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [
            "REQ-CEX-CLUSTER",
            "REQ-CEX-HOT-WALLET",
            "REQ-CEX-LABEL",
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
    request: CexClusterAnalysisRequest,
    replay: CexClusterReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return (
            "rule_restricted",
            "TASK-016 cex_cluster currently executes offline artifact replay only.",
            "rule_check",
        )
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and CEX cluster replay fixture IDs differ.",
            "fixture_binding",
        )
    allowed_sources = set(request.source_policy.allowed_source_ids)
    ordered_sources = set(request.source_policy.source_order)
    if not allowed_sources >= REQUIRED_SOURCE_IDS or not ordered_sources >= REQUIRED_SOURCE_IDS:
        return (
            "rule_restricted",
            "CEX cluster replay requires the approved archive and sanctions sources.",
            "source_binding",
        )
    return None


def _input_binding_error(
    request: CexClusterAnalysisRequest,
    replay: CexClusterReplay,
    facts: dict[str, object],
) -> tuple[str, str, str] | None:
    inputs = request.inputs
    request_deposits = {address.lower() for address in inputs.deposit_candidates}
    replay_deposits = {address.lower() for address in replay.deposit_candidates}
    if request_deposits != replay_deposits:
        return (
            "reconciliation_failed",
            "Requested deposit candidates differ from the replay package.",
            "deposit_binding",
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
    if inputs.expected_hot_wallet is not MISSING:
        expected = inputs.expected_hot_wallet.lower()
        candidates = facts.get("hot_wallet_candidates")
        if not isinstance(candidates, list) or not candidates:
            return (
                "reconciliation_failed",
                "Expected hot wallet differs from the reconstructed cluster candidate.",
                "hot_wallet_binding",
            )
        first = candidates[0]
        if not isinstance(first, dict) or first.get("address") != expected:
            return (
                "reconciliation_failed",
                "Expected hot wallet differs from the reconstructed cluster candidate.",
                "hot_wallet_binding",
            )
    return None


def _complete_evidence(replay: CexClusterReplay) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    primary_observations = sorted(
        (
            observation
            for observation in replay.raw_observations
            if observation.provider_role == "PRIMARY"
        ),
        key=lambda item: item.transfer_index,
    )
    for index, (transfer, observation) in enumerate(
        zip(
            replay.transfers,
            primary_observations,
            strict=True,
        ),
        start=1,
    ):
        evidence.append(_transfer_evidence(replay, transfer, observation, index))
    evidence.append(_common_destination_evidence(replay))
    evidence.append(_label_evidence(replay))
    evidence.append(_pattern_evidence(replay))
    return evidence


def _transfer_evidence(
    replay: CexClusterReplay,
    transfer: CexTransferReference,
    observation: CexRawObservation,
    index: int,
) -> dict[str, object]:
    artifact_uri = observation.artifacts.transaction
    if artifact_uri is MISSING:
        raise CexClusterIncomplete("transfer transaction artifact is unavailable")
    return {
        "evidence_id": f"EV-CEX-OUT-{index}",
        "evidence_type": "event",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-CEX-ETHEREUM",
        "method": "native_outbound_transfer",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": transfer.block_number,
            "transaction_hash": transfer.transaction_hash,
        },
        "decoded": {
            "source_address": transfer.source_address,
            "destination_address": replay.hot_wallet_candidate,
            "provider_id": observation.provider_id,
        },
        "raw_artifact": {
            "artifact_uri": artifact_uri,
            "media_type": "application/json",
        },
    }


def _common_destination_evidence(replay: CexClusterReplay) -> dict[str, object]:
    return {
        "evidence_id": "EV-CEX-COMMON",
        "evidence_type": "context",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-CEX-ETHEREUM",
        "method": "common_destination_aggregate",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": replay.observation_window.end_block,
        },
        "decoded": {
            "destination_address": replay.hot_wallet_candidate,
            "transfer_count": len(replay.transfers),
            "deposit_source_count": len(replay.deposit_candidates),
            "classification": "confirmed_fact",
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
            "media_type": "application/json",
        },
    }


def _label_evidence(replay: CexClusterReplay) -> dict[str, object]:
    return {
        "evidence_id": "EV-CEX-LABEL",
        "evidence_type": "context",
        "source_id": "DS-SANCTIONS-PUBLIC",
        "source_record_ref": "SRC-CEX-SANCTIONS",
        "method": "gov_registry_label_assertion",
        "retrieved_at": replay.captured_at,
        "locator": {
            "url": "https://www.treasury.gov/ofac/downloads/sdn.xml",
        },
        "decoded": {
            "entity": "GARANTEX",
            "artifact_path": replay.label_provenance.artifact_path,
            "classification": "evidence_backed_assertion",
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/{replay.label_provenance.artifact_path}",
            "media_type": "application/json",
        },
    }


def _pattern_evidence(replay: CexClusterReplay) -> dict[str, object]:
    block_numbers = [transfer.block_number for transfer in replay.transfers]
    return {
        "evidence_id": "EV-CEX-PAT",
        "evidence_type": "context",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-CEX-ETHEREUM",
        "method": "collection_pattern",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": min(block_numbers),
        },
        "decoded": {
            "start_block": replay.observation_window.start_block,
            "end_block": replay.observation_window.end_block,
            "transfer_count": len(replay.transfers),
            "block_span": max(block_numbers) - min(block_numbers),
            "classification": "confirmed_fact",
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
            "media_type": "application/json",
        },
    }


def _partial(
    request: CexClusterAnalysisRequest,
    replay: CexClusterReplay,
    reason: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    evidence = [
        _partial_observation_evidence(replay, observation, index)
        for index, observation in enumerate(
            sorted(replay.raw_observations, key=lambda item: item.transfer_index),
            start=1,
        )
    ]
    result = {
        "result_id": "RES-CEX-CLUSTER-PARTIAL",
        "result_type": "cex_cluster",
        "classification": "confirmed_fact",
        "value": {
            "available_transfers": len(replay.raw_observations),
            "attribution": {
                "exchange_ownership": "not_assessed",
                "criminality": "not_assessed",
            },
        },
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [],
        "evidence_refs": [item["evidence_id"] for item in evidence],
    }
    errors = [
        _error(
            "evidence_incomplete",
            f"At least one CEX cluster leg is incomplete: {reason}",
            "cex_transfer_availability",
            [item["evidence_id"] for item in evidence],
            retryable=True,
        )
    ]
    return _result(
        request,
        replay,
        "partial",
        [result],
        evidence,
        errors,
        resumed,
        checkpoint_id,
    )


def _partial_observation_evidence(
    replay: CexClusterReplay,
    observation: CexRawObservation,
    index: int,
) -> dict[str, object]:
    transfer = replay.transfers[observation.transfer_index]
    artifact_uri = next(
        (
            value
            for name in ("receipt", "transaction", "block")
            if (value := getattr(observation.artifacts, name)) is not MISSING
        ),
        f"fixture://{replay.fixture_id}/raw-replay.json",
    )
    return {
        "evidence_id": f"EV-CEX-PARTIAL-{index}",
        "evidence_type": "context",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": "SRC-CEX-ETHEREUM",
        "method": "available_transfer_leg",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": replay.chain_id,
            "transaction_hash": transfer.transaction_hash,
        },
        "decoded": {"transfer_index": observation.transfer_index, "status": "incomplete"},
        "raw_artifact": {"artifact_uri": artifact_uri, "media_type": "application/json"},
    }


def _source_records(
    replay: CexClusterReplay,
    referenced: set[str],
) -> list[dict[str, object]]:
    provider_id = (
        replay.raw_observations[0].provider_id.lower()
        if replay.raw_observations
        else "cex-ethereum-replay"
    )
    candidates = [
        (
            "SRC-CEX-ETHEREUM",
            "DS-EVM-RPC-ARCHIVE",
            provider_id,
            "scoring",
            "ethereum_native_transfer_replay",
        ),
        (
            "SRC-CEX-SANCTIONS",
            "DS-SANCTIONS-PUBLIC",
            "ofac-sdn-public",
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
    request: CexClusterAnalysisRequest,
    replay: CexClusterReplay,
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
    request: CexClusterAnalysisRequest,
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
            "run": _run(
                request.requested_at,
                request.requested_at,
                resumed,
                checkpoint_id,
            ),
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
        "error_id": f"ERR-CEX-{code.upper().replace('_', '-')}",
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
