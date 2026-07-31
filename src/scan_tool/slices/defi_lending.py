"""Deterministic offline TASK-016 defi_lending analyzer."""

from pathlib import Path

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import DefiLendingAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.defi_lending import (
    DefiLendingIncomplete,
    DefiLendingReplay,
    parse_defi_lending_replay,
    reconstruct_lending_flow_facts,
)

CHECKPOINT_ID = "CP-DEFI-LENDING-REPLAY-EVIDENCE"
REQUIRED_SOURCE_IDS = {"DS-EVM-RPC-ARCHIVE"}


def analyze_defi_lending_replay(
    request: DefiLendingAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Reconstruct one reviewed lending liquidation flow from content-addressed artifacts."""
    try:
        replay = parse_defi_lending_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed DeFi lending replay does not match the offline evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )

    binding_error = _replay_binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)

    try:
        facts = reconstruct_lending_flow_facts(package_dir, replay)
    except DefiLendingIncomplete as error:
        return _partial(request, replay, str(error), resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "reconciliation_failed",
            "The lending events do not satisfy the pinned pool, window, and Transfer bindings.",
            "lending_reconciliation",
            resumed,
            checkpoint_id,
        )

    input_error = _input_binding_error(request, replay, facts)
    if input_error is not None:
        return _failed(request, *input_error, resumed, checkpoint_id)

    evidence = _complete_evidence(replay, facts)
    result = {
        "result_id": "RES-DEFI-LENDING",
        "result_type": "defi_lending",
        "classification": "confirmed_fact",
        "value": facts,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [
            "REQ-LEND-EVENT",
            "REQ-LEND-LEDGER",
            "REQ-LEND-OUTFLOW",
        ],
        "evidence_refs": [item["evidence_id"] for item in evidence],
    }
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


def _replay_binding_error(
    request: DefiLendingAnalysisRequest,
    replay: DefiLendingReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return (
            "rule_restricted",
            "TASK-016 defi_lending currently executes offline artifact replay only.",
            "rule_check",
        )
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and DeFi lending replay fixture IDs differ.",
            "fixture_binding",
        )
    allowed_sources = set(request.source_policy.allowed_source_ids)
    ordered_sources = set(request.source_policy.source_order)
    if not allowed_sources >= REQUIRED_SOURCE_IDS or not ordered_sources >= REQUIRED_SOURCE_IDS:
        return (
            "rule_restricted",
            "DeFi lending replay requires the approved archive source.",
            "source_binding",
        )
    return None


def _input_binding_error(
    request: DefiLendingAnalysisRequest,
    replay: DefiLendingReplay,
    facts: dict[str, object],
) -> tuple[str, str, str] | None:
    inputs = request.inputs
    if inputs.subject_address.lower() != replay.subject_address.lower():
        return (
            "reconciliation_failed",
            "Requested subject_address differs from the replay package.",
            "subject_binding",
        )
    if sorted(str(role) for role in inputs.subject_roles) != sorted(
        str(role) for role in replay.subject_roles
    ):
        return (
            "reconciliation_failed",
            "Requested subject_roles differ from the replay package.",
            "subject_roles_binding",
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
    if inputs.seed_transaction_hash.lower() != replay.seed_transaction_hash.lower():
        return (
            "reconciliation_failed",
            "Requested seed transaction differs from the replay package.",
            "seed_tx_binding",
        )
    if inputs.protocol != replay.protocol:
        return (
            "reconciliation_failed",
            "Requested protocol differs from the replay package.",
            "protocol_binding",
        )
    if facts.get("subject_address") != replay.subject_address:
        return (
            "reconciliation_failed",
            "Reconstructed subject differs from the replay package.",
            "fact_subject_binding",
        )
    return None


def _complete_evidence(
    replay: DefiLendingReplay,
    facts: dict[str, object],
) -> list[dict[str, object]]:
    events = facts.get("events")
    ledger = facts.get("net_asset_ledger")
    outflow = facts.get("subsequent_outflow")
    if not isinstance(events, list) or not events:
        raise DefiLendingIncomplete("lending events are unavailable")
    if not isinstance(ledger, list) or len(ledger) < 2:
        raise DefiLendingIncomplete("lending ledger is unavailable")
    if not isinstance(outflow, dict):
        raise DefiLendingIncomplete("subsequent outflow is unavailable")
    event = events[0]
    assert isinstance(event, dict)
    receipt_uri = _primary_receipt_uri(replay)
    return [
        {
            "evidence_id": "EV-LEND-LIQUIDATION-EVENT",
            "evidence_type": "event",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-LEND-ETHEREUM",
            "method": "aave_v3_liquidation_call",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "block_number": event["block_number"],
                "transaction_hash": event["transaction_hash"],
                "log_index": event["log_index"],
            },
            "decoded": {
                "event_name": event["event_name"],
                "pool": event["pool"],
                "liquidator": event["liquidator"],
                "user": event["user"],
            },
            "raw_artifact": {"artifact_uri": receipt_uri, "media_type": "application/json"},
        },
        {
            "evidence_id": "EV-LEND-DEBT-TRANSFER",
            "evidence_type": "event",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-LEND-ETHEREUM",
            "method": "erc20_transfer_match",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "transaction_hash": replay.seed_transaction_hash,
                "log_index": ledger[0]["matched_transfer_log_index"],
            },
            "decoded": ledger[0],
            "raw_artifact": {"artifact_uri": receipt_uri, "media_type": "application/json"},
        },
        {
            "evidence_id": "EV-LEND-COLLATERAL-TRANSFER",
            "evidence_type": "event",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-LEND-ETHEREUM",
            "method": "erc20_transfer_match",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "transaction_hash": replay.seed_transaction_hash,
                "log_index": ledger[1]["matched_transfer_log_index"],
            },
            "decoded": ledger[1],
            "raw_artifact": {"artifact_uri": receipt_uri, "media_type": "application/json"},
        },
        {
            "evidence_id": "EV-LEND-SUBSEQUENT-OUTFLOW",
            "evidence_type": "event",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-LEND-ETHEREUM",
            "method": "bounded_collateral_outflow",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "transaction_hash": replay.seed_transaction_hash,
                "log_index": outflow["log_index"],
            },
            "decoded": outflow,
            "raw_artifact": {"artifact_uri": receipt_uri, "media_type": "application/json"},
        },
    ]


def _primary_receipt_uri(replay: DefiLendingReplay) -> str:
    for observation in replay.raw_observations:
        if observation.provider_role != "PRIMARY":
            continue
        uri = observation.artifacts.receipt
        if uri is MISSING:
            raise DefiLendingIncomplete("PRIMARY receipt artifact is unavailable")
        return str(uri)
    raise DefiLendingIncomplete("PRIMARY observation is unavailable")


def _partial(
    request: DefiLendingAnalysisRequest,
    replay: DefiLendingReplay,
    reason: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    evidence = [
        {
            "evidence_id": "EV-LEND-PARTIAL",
            "evidence_type": "context",
            "source_id": "DS-EVM-RPC-ARCHIVE",
            "source_record_ref": "SRC-LEND-ETHEREUM",
            "method": "available_lending_leg",
            "retrieved_at": replay.captured_at,
            "locator": {
                "chain_id": replay.chain_id,
                "transaction_hash": replay.seed_transaction_hash,
            },
            "decoded": {"status": "incomplete", "reason": reason},
            "raw_artifact": {
                "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json",
                "media_type": "application/json",
            },
        }
    ]
    result = {
        "result_id": "RES-DEFI-LENDING-PARTIAL",
        "result_type": "defi_lending",
        "classification": "confirmed_fact",
        "value": {
            "available_events": 0,
            "attribution": {
                "attack_vs_normal": "not_assessed",
                "service_attribution": "not_assessed",
                "criminality": "not_assessed",
            },
        },
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": [],
        "evidence_refs": [item["evidence_id"] for item in evidence],
    }
    errors = [
        {
            "error_id": "ERR-LEND-INCOMPLETE",
            "code": "evidence_incomplete",
            "message": f"At least one lending leg is incomplete: {reason}",
            "stage": "lending_transfer_availability",
            "retryable": True,
            "attempt_count": 0,
            "related_evidence_ids": [item["evidence_id"] for item in evidence],
        }
    ]
    return _result(request, replay, "partial", [result], evidence, errors, resumed, checkpoint_id)


def _failed(
    request: DefiLendingAnalysisRequest,
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
            "errors": [
                {
                    "error_id": f"ERR-LEND-{code.upper().replace('_', '-')}",
                    "code": code,
                    "message": message,
                    "stage": stage,
                    "retryable": False,
                    "attempt_count": 0,
                }
            ],
            "run": _run(request.requested_at, request.requested_at, resumed, checkpoint_id),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _result(
    request: DefiLendingAnalysisRequest,
    replay: DefiLendingReplay,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    referenced = {str(item["source_record_ref"]) for item in evidence}
    provider_id = (
        replay.raw_observations[0].provider_id.lower()
        if replay.raw_observations
        else "lend-ethereum-replay"
    )
    sources = []
    if "SRC-LEND-ETHEREUM" in referenced:
        sources.append(
            {
                "source_record_id": "SRC-LEND-ETHEREUM",
                "source_id": "DS-EVM-RPC-ARCHIVE",
                "provider_id": provider_id,
                "role": "scoring",
                "required": True,
                "capability": "ethereum_lending_replay",
                "endpoint_host": "reviewed.replay.invalid",
                "retrieved_at": replay.captured_at,
            }
        )
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
            "sources": sources,
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


def _run(started_at, finished_at, resumed: bool, checkpoint_id: str | None) -> dict[str, object]:
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
