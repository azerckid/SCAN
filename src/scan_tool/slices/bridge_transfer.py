"""Deterministic offline TASK-016 bridge_transfer analyzer."""

from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import BridgeTransferAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.bridge_transfer import (
    BridgeRawObservation,
    BridgeTransferIncomplete,
    BridgeTransferReplay,
    parse_bridge_transfer_replay,
    reconstruct_bridge_transfer_facts,
)

CHECKPOINT_ID = "CP-BRIDGE-TRANSFER-REPLAY-EVIDENCE"
REQUIRED_SOURCE_IDS = {"DS-EVM-RPC-ARCHIVE", "DS-BRIDGE-META"}


def analyze_bridge_transfer_replay(
    request: BridgeTransferAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Link one reviewed Across bridge transfer from content-addressed artifacts."""
    try:
        replay = parse_bridge_transfer_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed bridge replay does not match the offline evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )

    binding_error = _replay_binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)

    try:
        facts = reconstruct_bridge_transfer_facts(package_dir, replay)
    except BridgeTransferIncomplete as error:
        return _partial(request, replay, str(error), resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "reconciliation_failed",
            "The bridge legs do not satisfy the pinned chain, event, and amount bindings.",
            "bridge_reconciliation",
            resumed,
            checkpoint_id,
        )

    input_error = _input_binding_error(request, replay, facts)
    if input_error is not None:
        return _failed(request, *input_error, resumed, checkpoint_id)

    evidence = _complete_evidence(replay)
    result = {
        "result_id": "RES-BRIDGE-TRANSFER",
        "result_type": "bridge_transfer",
        "classification": "confirmed_fact",
        "value": facts,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [
            "REQ-BRIDGE-SOURCE",
            "REQ-BRIDGE-DESTINATION",
            "REQ-BRIDGE-DOMAIN",
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
    request: BridgeTransferAnalysisRequest,
    replay: BridgeTransferReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return (
            "rule_restricted",
            "TASK-016 bridge_transfer currently executes offline artifact replay only.",
            "rule_check",
        )
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and bridge replay fixture IDs differ.",
            "fixture_binding",
        )
    allowed_sources = set(request.source_policy.allowed_source_ids)
    ordered_sources = set(request.source_policy.source_order)
    if not allowed_sources >= REQUIRED_SOURCE_IDS or not ordered_sources >= REQUIRED_SOURCE_IDS:
        return (
            "rule_restricted",
            "Bridge replay requires the approved archive and bridge metadata sources.",
            "source_binding",
        )
    return None


def _input_binding_error(
    request: BridgeTransferAnalysisRequest,
    replay: BridgeTransferReplay,
    facts: dict[str, object],
) -> tuple[str, str, str] | None:
    inputs = request.inputs
    if inputs.origin_chain_id != facts["origin_chain_id"]:
        return (
            "reconciliation_failed",
            "Requested origin chain differs from the reconstructed source leg.",
            "origin_chain_binding",
        )
    if inputs.destination_chain_id != facts["destination_chain_id"]:
        return (
            "reconciliation_failed",
            "Requested destination chain differs from the reconstructed destination leg.",
            "destination_chain_binding",
        )
    if inputs.source_subject != facts["depositor"]:
        return (
            "reconciliation_failed",
            "Requested source subject differs from the reconstructed depositor.",
            "source_subject_binding",
        )
    if inputs.expected_recipient is not MISSING and inputs.expected_recipient != facts["recipient"]:
        return (
            "reconciliation_failed",
            "Expected recipient differs from the reconstructed bridge recipient.",
            "recipient_binding",
        )
    if (
        inputs.source_transaction_hash is not MISSING
        and inputs.source_transaction_hash != replay.chains.base.transaction_hash
    ):
        return (
            "reconciliation_failed",
            "Requested source transaction differs from the reconstructed source leg.",
            "source_transaction_binding",
        )
    if (
        inputs.destination_transaction_hash is not MISSING
        and inputs.destination_transaction_hash != replay.chains.ethereum.transaction_hash
    ):
        return (
            "reconciliation_failed",
            "Requested destination transaction differs from the reconstructed destination leg.",
            "destination_transaction_binding",
        )
    return None


def _complete_evidence(replay: BridgeTransferReplay) -> list[dict[str, object]]:
    by_chain = {item.chain: item for item in replay.raw_observations}
    return [
        _event_evidence(
            replay,
            by_chain["base"],
            "EV-BRIDGE-SOURCE-EVENT",
            replay.chains.base.chain_id,
            replay.chains.base.transaction_hash,
            replay.chains.base.block_tag,
            "V3FundsDeposited",
            "SRC-BRIDGE-BASE",
        ),
        _event_evidence(
            replay,
            by_chain["ethereum"],
            "EV-BRIDGE-DESTINATION-EVENT",
            replay.chains.ethereum.chain_id,
            replay.chains.ethereum.transaction_hash,
            replay.chains.ethereum.block_tag,
            "FilledV3Relay",
            "SRC-BRIDGE-ETHEREUM",
        ),
        {
            "evidence_id": "EV-BRIDGE-OFFICIAL-CONTRACTS",
            "evidence_type": "context",
            "source_id": "DS-BRIDGE-META",
            "source_record_ref": "SRC-BRIDGE-META",
            "method": "official_contract_registry",
            "retrieved_at": replay.captured_at,
            "locator": {"url": "https://docs.across.to/chains-and-contracts"},
            "decoded": {
                "origin_chain_id": replay.chains.base.chain_id,
                "destination_chain_id": replay.chains.ethereum.chain_id,
                "source_spoke_pool": replay.chains.base.spoke_pool,
                "destination_spoke_pool": replay.chains.ethereum.spoke_pool,
            },
            "raw_artifact": {
                "artifact_uri": "https://docs.across.to/chains-and-contracts",
                "media_type": "text/html",
            },
        },
        {
            "evidence_id": "EV-BRIDGE-MATCHING-RULE",
            "evidence_type": "context",
            "source_id": "DS-BRIDGE-META",
            "source_record_ref": "SRC-BRIDGE-META",
            "method": "official_protocol_rule",
            "retrieved_at": replay.captured_at,
            "locator": {"url": "https://docs.across.to/guides/migration/v2-to-v3"},
            "decoded": {
                "matching": "common_event_parameters_and_chain_separated_domain",
                "amount_tolerance_raw": "0",
            },
            "raw_artifact": {
                "artifact_uri": "https://docs.across.to/guides/migration/v2-to-v3",
                "media_type": "text/html",
            },
        },
    ]


def _event_evidence(
    replay: BridgeTransferReplay,
    observation: BridgeRawObservation,
    evidence_id: str,
    chain_id: int,
    transaction_hash: str,
    block_tag: str,
    method: str,
    source_record_ref: str,
) -> dict[str, object]:
    artifact_uri = observation.artifacts.bridge_logs
    if artifact_uri is MISSING:
        raise BridgeTransferIncomplete("bridge event artifact is unavailable")
    return {
        "evidence_id": evidence_id,
        "evidence_type": "event",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": source_record_ref,
        "method": method,
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": chain_id,
            "block_number": int(block_tag, 16),
            "transaction_hash": transaction_hash,
        },
        "decoded": {
            "chain": observation.chain,
            "provider_id": observation.provider_id,
        },
        "raw_artifact": {
            "artifact_uri": artifact_uri,
            "media_type": "application/json",
        },
    }


def _partial(
    request: BridgeTransferAnalysisRequest,
    replay: BridgeTransferReplay,
    reason: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    evidence = [
        _partial_observation_evidence(replay, observation, index)
        for index, observation in enumerate(replay.raw_observations, start=1)
    ]
    result = {
        "result_id": "RES-BRIDGE-TRANSFER-PARTIAL",
        "result_type": "bridge_transfer",
        "classification": "confirmed_fact",
        "value": {
            "available_legs": [item.chain for item in replay.raw_observations],
            "attribution": {
                "recipient_ownership": "not_assessed",
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
            f"At least one bridge leg is incomplete: {reason}",
            "bridge_leg_availability",
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
    replay: BridgeTransferReplay,
    observation: BridgeRawObservation,
    index: int,
) -> dict[str, object]:
    chain = replay.chains.base if observation.chain == "base" else replay.chains.ethereum
    artifact_uri = next(
        (
            value
            for name in ("bridge_logs", "receipt", "transaction", "block")
            if (value := getattr(observation.artifacts, name)) is not MISSING
        ),
        f"fixture://{replay.fixture_id}/raw-replay.json",
    )
    return {
        "evidence_id": f"EV-BRIDGE-PARTIAL-{index}",
        "evidence_type": "context",
        "source_id": "DS-EVM-RPC-ARCHIVE",
        "source_record_ref": (
            "SRC-BRIDGE-BASE" if observation.chain == "base" else "SRC-BRIDGE-ETHEREUM"
        ),
        "method": "available_bridge_leg",
        "retrieved_at": replay.captured_at,
        "locator": {
            "chain_id": chain.chain_id,
            "transaction_hash": chain.transaction_hash,
        },
        "decoded": {"chain": observation.chain, "status": "incomplete"},
        "raw_artifact": {"artifact_uri": artifact_uri, "media_type": "application/json"},
    }


def _source_records(
    replay: BridgeTransferReplay,
    referenced: set[str],
) -> list[dict[str, object]]:
    provider_by_chain = {item.chain: item.provider_id.lower() for item in replay.raw_observations}
    candidates = [
        (
            "SRC-BRIDGE-BASE",
            "DS-EVM-RPC-ARCHIVE",
            provider_by_chain.get("base", "bridge-base-replay"),
            "scoring",
            "base_bridge_event_replay",
        ),
        (
            "SRC-BRIDGE-ETHEREUM",
            "DS-EVM-RPC-ARCHIVE",
            provider_by_chain.get("ethereum", "bridge-ethereum-replay"),
            "scoring",
            "ethereum_bridge_event_replay",
        ),
        (
            "SRC-BRIDGE-META",
            "DS-BRIDGE-META",
            "across-official",
            "supporting",
            "bridge_contract_and_matching_rules",
        ),
    ]
    return [
        {
            "source_record_id": record_id,
            "source_id": source_id,
            "provider_id": provider_id,
            "role": role,
            "required": True,
            "capability": capability,
            "endpoint_host": "reviewed.replay.invalid",
            "retrieved_at": replay.captured_at,
        }
        for record_id, source_id, provider_id, role, capability in candidates
        if record_id in referenced
    ]


def _result(
    request: BridgeTransferAnalysisRequest,
    replay: BridgeTransferReplay,
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
    request: BridgeTransferAnalysisRequest,
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
        "error_id": f"ERR-BRIDGE-{code.upper().replace('_', '-')}",
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
