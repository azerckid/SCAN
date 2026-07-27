"""Deterministic approve-to-transferFrom AUTH replay for TASK-007."""

from datetime import datetime

from eth_abi import decode
from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import AuthAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.auth import (
    AllowanceSnapshot,
    AuthReplay,
    ConsumptionEvidence,
    TransactionEvidence,
)
from scan_tool.domain.dex import RawLog, RawTransaction, ReplaySource

APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVE_SELECTOR = "0x095ea7b3"
TRANSFER_FROM_SELECTOR = "0x23b872dd"
ALLOWANCE_SELECTOR = "0xdd62ed3e"
MULTICALL_SELECTOR = "0x5ae401dc"
SNAPSHOT_LABELS = (
    "before_approval",
    "after_approval",
    "before_consumption",
    "after_consumption",
)
EXCLUDED_NONCES = frozenset({327, 328, 329})


def analyze_auth_replay(
    request: AuthAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-AUTH-REPLAY-EVIDENCE",
) -> AnalysisResult:
    """Decode, reconcile, and classify one approved AUTH replay package."""
    try:
        replay = AuthReplay.model_validate_json(raw_replay)
    except ValidationError:
        return _failed_without_evidence(
            request,
            code="decode_failed",
            message="The AUTH replay package does not match the raw evidence contract.",
            stage="decode_replay",
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    binding_error = _binding_error(request, replay)
    if binding_error is not None:
        return _failed_without_evidence(
            request,
            code=binding_error[0],
            message=binding_error[1],
            stage="validate_replay",
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )
    return _analyze_valid_replay(
        request,
        replay,
        resumed=resumed,
        checkpoint_id=checkpoint_id,
    )


def _analyze_valid_replay(
    request: AuthAnalysisRequest,
    replay: AuthReplay,
    *,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    try:
        decoded = _decode_replay(replay)
    except (ValueError, OverflowError):
        return _failed_without_evidence(
            request,
            code="decode_failed",
            message="The raw AUTH evidence could not be decoded without ambiguity.",
            stage="decode_auth",
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    evidence = _evidence(replay, decoded)
    sources = _sources(replay)
    mismatches = _mismatches(request, replay, decoded)
    if mismatches:
        return _result(
            request,
            replay,
            status="failed",
            results=[],
            evidence=evidence,
            sources=sources,
            errors=[
                _error(
                    "reconciliation_failed",
                    "Approval, allowance, transferFrom, Transfer, and exclusion evidence differ.",
                    "reconcile_authorization",
                    [item["evidence_id"] for item in evidence],
                    {"mismatches": mismatches},
                )
            ],
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    snapshots = decoded["snapshots"]
    trace = decoded["trace"]
    missing_snapshots = [label for label in SNAPSHOT_LABELS if label not in snapshots]
    errors = []
    if missing_snapshots:
        errors.append(
            _error(
                "archive_required",
                "Approval is confirmed but historical allowance snapshots are incomplete.",
                "collect_allowance",
                ["EV-AUTH-APPROVAL-EVENT", "EV-AUTH-APPROVE-CALL"],
                {"missing_snapshot_labels": missing_snapshots},
            )
        )
    if trace is None:
        errors.append(
            _error(
                "trace_unavailable",
                "Approval evidence is preserved but transferFrom trace evidence is missing.",
                "collect_trace",
                ["EV-AUTH-TRANSFER-EVENT"],
                {"missing_requirement_ids": ["REQ-AUTH-CONSUMPTION"]},
            )
        )

    results = _confirmed_results(
        replay,
        decoded,
        include_allowance=not missing_snapshots,
        include_consumption=not missing_snapshots and trace is not None,
        scope_evidence_refs=[item["evidence_id"] for item in evidence],
    )
    return _result(
        request,
        replay,
        status="partial" if errors else "complete",
        results=results,
        evidence=evidence,
        sources=sources,
        errors=errors,
        resumed=resumed,
        checkpoint_id=checkpoint_id,
    )


def _binding_error(
    request: AuthAnalysisRequest,
    replay: AuthReplay,
) -> tuple[str, str] | None:
    policy = request.source_policy
    if not policy.offline_mode:
        return "rule_restricted", "TASK-007 supports offline replay only."
    inputs = request.inputs
    values_match = (
        request.chain_id == replay.chain_id
        and inputs.subject_address == replay.subject_address
        and inputs.token_address == replay.token.address
        and inputs.spender_address == replay.spender.address
        and inputs.approval_transaction_hash == replay.approval.transaction.hash
        and inputs.consumption_transaction_hash == replay.consumption.transaction.hash
    )
    if not values_match:
        return "reconciliation_failed", "Request and replay AUTH identifiers differ."
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return "reconciliation_failed", "Request and replay fixture IDs differ."
    required_sources = {
        replay.sources.public_rpc.source_id,
        replay.sources.archive_rpc.source_id,
        replay.sources.explorer.source_id,
        replay.sources.metadata.source_id,
    }
    if not required_sources <= set(policy.allowed_source_ids):
        return "rule_restricted", "Replay evidence uses a source outside the allowed policy."
    return None


def _decode_replay(replay: AuthReplay) -> dict[str, object]:
    approval_log = _one_log(
        replay.approval.receipt.selected_logs,
        APPROVAL_TOPIC,
        replay.token.address,
    )
    transfer_log = _one_log(
        replay.consumption.receipt.selected_logs,
        TRANSFER_TOPIC,
        replay.token.address,
    )
    approval_spender, approval_amount = _decode_call(
        replay.approval.transaction.input,
        APPROVE_SELECTOR,
        ["address", "uint256"],
    )
    query_owner, query_spender = _decode_call(
        replay.allowance_query.data,
        ALLOWANCE_SELECTOR,
        ["address", "address"],
    )
    trace = replay.consumption.transfer_from_trace
    trace_values = None
    if trace is not None:
        trace_values = _decode_call(
            trace.input,
            TRANSFER_FROM_SELECTOR,
            ["address", "address", "uint256"],
        )
    snapshots = {item.label: _snapshot_value(item) for item in replay.allowance_query.snapshots}
    if len(snapshots) != len(replay.allowance_query.snapshots):
        raise ValueError("duplicate allowance snapshot")
    return {
        "approval_log": approval_log,
        "approval_owner": _topic_address(approval_log.topics[1]),
        "approval_spender": _topic_address(approval_log.topics[2]),
        "approval_amount": _uint256(approval_log.data),
        "call_spender": approval_spender,
        "call_amount": approval_amount,
        "query_owner": query_owner,
        "query_spender": query_spender,
        "transfer_log": transfer_log,
        "transfer_from": _topic_address(transfer_log.topics[1]),
        "transfer_to": _topic_address(transfer_log.topics[2]),
        "transfer_amount": _uint256(transfer_log.data),
        "trace": trace,
        "trace_values": trace_values,
        "snapshots": snapshots,
    }


def _decode_call(
    value: str,
    selector: str,
    types: list[str],
) -> tuple[object, ...]:
    if not value.startswith(selector):
        raise ValueError("unexpected selector")
    return tuple(decode(types, bytes.fromhex(value[10:])))


def _one_log(logs: list[RawLog], topic: str, address: str) -> RawLog:
    candidates = [
        log for log in logs if log.address == address and log.topics and log.topics[0] == topic
    ]
    if len(candidates) != 1:
        raise ValueError("required AUTH log is missing or ambiguous")
    return candidates[0]


def _topic_address(topic: str) -> str:
    return to_normalized_address(f"0x{topic[-40:]}")


def _uint256(value: str) -> int:
    return int(decode(["uint256"], bytes.fromhex(value[2:]))[0])


def _snapshot_value(snapshot: AllowanceSnapshot) -> int:
    if int(snapshot.block_tag, 16) != snapshot.block_number:
        raise ValueError("snapshot block tag differs")
    return _uint256(snapshot.result)


def _mismatches(
    request: AuthAnalysisRequest,
    replay: AuthReplay,
    decoded: dict[str, object],
) -> list[str]:
    mismatches = []
    subject = replay.subject_address
    spender = replay.spender.address
    token = replay.token.address
    approval = replay.approval
    consumption = replay.consumption
    if not _transaction_receipt_match(approval) or approval.receipt.status != "0x1":
        mismatches.append("approval_transaction_receipt")
    if not _transaction_receipt_match(consumption) or consumption.receipt.status != "0x1":
        mismatches.append("consumption_transaction_receipt")
    expected_approval = (subject, spender, decoded["approval_amount"])
    if (
        decoded["approval_owner"],
        decoded["approval_spender"],
        decoded["call_amount"],
    ) != expected_approval or decoded["call_spender"] != spender:
        mismatches.append("approval_event_vs_call")
    if approval.transaction.from_address != subject or approval.transaction.to != token:
        mismatches.append("approval_transaction_identity")
    if (
        consumption.transaction.from_address != subject
        or consumption.transaction.to != spender
        or not consumption.transaction.input.startswith(MULTICALL_SELECTOR)
    ):
        mismatches.append("consumption_outer_call_identity")
    if decoded["query_owner"] != subject or decoded["query_spender"] != spender:
        mismatches.append("allowance_query_identity")
    if replay.allowance_query.to != token:
        mismatches.append("allowance_token")
    request_blocks = request.inputs.state_blocks
    expected_blocks = {
        "before_approval": request_blocks.before_approval,
        "after_approval": request_blocks.after_approval,
        "before_consumption": request_blocks.before_consumption,
        "after_consumption": request_blocks.after_consumption,
    }
    mismatches.extend(_state_and_consumption_mismatches(replay, decoded, expected_blocks))
    mismatches.extend(_excluded_and_explorer_mismatches(request, replay, decoded))
    return mismatches


def _transaction_receipt_match(
    value: TransactionEvidence | ConsumptionEvidence,
) -> bool:
    transaction = value.transaction
    receipt = value.receipt
    return (
        transaction.hash == receipt.transaction_hash
        and transaction.block_hash == receipt.block_hash
        and transaction.block_number == receipt.block_number
        and transaction.from_address == receipt.from_address
        and transaction.to == receipt.to
        and transaction.transaction_index == receipt.transaction_index
    )


def _state_and_consumption_mismatches(
    replay: AuthReplay,
    decoded: dict[str, object],
    expected_blocks: dict[str, int],
) -> list[str]:
    mismatches = []
    snapshots = decoded["snapshots"]
    state_blocks = {item.label: item.block_number for item in replay.allowance_query.snapshots}
    for label in set(SNAPSHOT_LABELS) & set(snapshots):
        if state_blocks[label] != expected_blocks[label]:
            mismatches.append(f"state_block_{label}")
    if set(SNAPSHOT_LABELS) <= set(snapshots):
        if snapshots["before_approval"] != 0:
            mismatches.append("allowance_before_approval")
        if snapshots["after_approval"] != decoded["approval_amount"]:
            mismatches.append("allowance_after_approval")
        if snapshots["before_consumption"] != snapshots["after_approval"]:
            mismatches.append("allowance_before_consumption")
        delta = snapshots["before_consumption"] - snapshots["after_consumption"]
        if delta < 0:
            mismatches.append("allowance_negative_delta")
        elif decoded["transfer_amount"] != delta:
            mismatches.append("allowance_delta_vs_transfer")
    trace = decoded["trace"]
    trace_values = decoded["trace_values"]
    if trace is not None and trace_values is not None:
        owner, recipient, amount = trace_values
        if (
            trace.transaction_hash != replay.consumption.transaction.hash
            or trace.block_hash != replay.consumption.transaction.block_hash
            or trace.block_number != int(replay.consumption.transaction.block_number, 16)
            or trace.from_address != replay.spender.address
            or trace.to != replay.token.address
            or trace.output != f"0x{'0' * 63}1"
        ):
            mismatches.append("transfer_from_trace_identity")
        if (
            owner != decoded["transfer_from"]
            or recipient != decoded["transfer_to"]
            or amount != decoded["transfer_amount"]
        ):
            mismatches.append("transfer_from_vs_event")
    return mismatches


def _excluded_and_explorer_mismatches(
    request: AuthAnalysisRequest,
    replay: AuthReplay,
    decoded: dict[str, object],
) -> list[str]:
    mismatches = []
    expected_hashes = (
        set(request.inputs.excluded_transaction_hashes)
        if request.inputs.excluded_transaction_hashes is not MISSING
        else set()
    )
    receipts = replay.excluded_receipts
    if {item.transaction_hash for item in receipts} != expected_hashes:
        mismatches.append("excluded_transaction_set")
    if any(
        item.status != "0x0"
        or item.from_address != replay.subject_address
        or item.to != replay.spender.address
        for item in receipts
    ):
        mismatches.append("excluded_transaction_status")
    if {int(item.nonce, 16) for item in receipts} != EXCLUDED_NONCES:
        mismatches.append("excluded_transaction_nonce_set")
    explorer = replay.explorer_cross_check
    if (
        explorer.approval_transaction_hash != replay.approval.transaction.hash
        or explorer.approval_nonce != int(replay.approval.transaction.nonce, 16)
        or explorer.consumption_transaction_hash != replay.consumption.transaction.hash
        or explorer.consumption_nonce != int(replay.consumption.transaction.nonce, 16)
        or explorer.transfer_log_index != int(decoded["transfer_log"].log_index, 16)
        or int(explorer.transfer_amount_raw) != decoded["transfer_amount"]
    ):
        mismatches.append("explorer_cross_check")
    return mismatches


def _evidence(replay: AuthReplay, decoded: dict[str, object]) -> list[dict[str, object]]:
    evidence = [
        _approval_event(replay, decoded),
        _call_evidence(
            replay,
            "EV-AUTH-APPROVE-CALL",
            replay.approval.transaction,
            "approve",
            {
                "owner": replay.approval.transaction.from_address,
                "spender": decoded["call_spender"],
                "amount_raw": str(decoded["call_amount"]),
            },
            "SRC-AUTH-PUBLIC",
            replay.sources.public_rpc,
        ),
        _call_evidence(
            replay,
            "EV-AUTH-OUTER-CALL",
            replay.consumption.transaction,
            "multicall",
            {
                "caller": replay.consumption.transaction.from_address,
                "spender": replay.consumption.transaction.to,
                "selector": MULTICALL_SELECTOR,
            },
            "SRC-AUTH-PUBLIC",
            replay.sources.public_rpc,
        ),
        _transfer_event(replay, decoded),
    ]
    trace = replay.consumption.transfer_from_trace
    if trace is not None:
        evidence.append(_trace_evidence(replay, decoded))
    for snapshot in replay.allowance_query.snapshots:
        evidence.append(_state_evidence(replay, snapshot))
    evidence.extend(_excluded_evidence(replay))
    evidence.append(_explorer_evidence(replay))
    evidence.append(_metadata_evidence(replay))
    return evidence


def _approval_event(replay: AuthReplay, decoded: dict[str, object]) -> dict[str, object]:
    log = decoded["approval_log"]
    return _event(
        replay,
        "EV-AUTH-APPROVAL-EVENT",
        log,
        {
            "event": "Approval",
            "owner": decoded["approval_owner"],
            "spender": decoded["approval_spender"],
            "amount_raw": str(decoded["approval_amount"]),
        },
    )


def _transfer_event(replay: AuthReplay, decoded: dict[str, object]) -> dict[str, object]:
    log = decoded["transfer_log"]
    return _event(
        replay,
        "EV-AUTH-TRANSFER-EVENT",
        log,
        {
            "event": "Transfer",
            "from": decoded["transfer_from"],
            "to": decoded["transfer_to"],
            "amount_raw": str(decoded["transfer_amount"]),
        },
    )


def _event(
    replay: AuthReplay,
    evidence_id: str,
    log: RawLog,
    decoded: dict[str, object],
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "event",
        "source_id": replay.sources.public_rpc.source_id,
        "source_record_ref": "SRC-AUTH-PUBLIC",
        "method": "eth_getTransactionReceipt",
        "retrieved_at": replay.sources.public_rpc.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(log.block_number, 16),
            "transaction_hash": log.transaction_hash,
            "log_index": int(log.log_index, 16),
        },
        "decoded": decoded,
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _call_evidence(
    replay: AuthReplay,
    evidence_id: str,
    transaction: RawTransaction,
    method: str,
    decoded: dict[str, object],
    source_record_ref: str,
    source: ReplaySource,
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "call",
        "source_id": source.source_id,
        "source_record_ref": source_record_ref,
        "method": method,
        "retrieved_at": source.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(transaction.block_number, 16),
            "transaction_hash": transaction.hash,
        },
        "decoded": decoded,
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _trace_evidence(replay: AuthReplay, decoded: dict[str, object]) -> dict[str, object]:
    trace = replay.consumption.transfer_from_trace
    assert trace is not None
    owner, recipient, amount = decoded["trace_values"]
    return {
        "evidence_id": "EV-AUTH-TRANSFER-FROM",
        "evidence_type": "call",
        "source_id": replay.sources.archive_rpc.source_id,
        "source_record_ref": "SRC-AUTH-ARCHIVE",
        "method": "trace_transaction",
        "retrieved_at": replay.sources.archive_rpc.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": trace.block_number,
            "transaction_hash": trace.transaction_hash,
            "trace_address": trace.trace_address,
        },
        "decoded": {
            "method": "transferFrom(address,address,uint256)",
            "from": owner,
            "to": recipient,
            "amount_raw": str(amount),
            "success": True,
        },
        "raw_artifact": _artifact(replay, "EV-AUTH-TRANSFER-FROM"),
    }


def _state_evidence(
    replay: AuthReplay,
    snapshot: AllowanceSnapshot,
) -> dict[str, object]:
    evidence_id = f"EV-AUTH-STATE-{snapshot.label.replace('_', '-').upper()}"
    return {
        "evidence_id": evidence_id,
        "evidence_type": "state",
        "source_id": replay.sources.archive_rpc.source_id,
        "source_record_ref": "SRC-AUTH-ARCHIVE",
        "method": "eth_call",
        "retrieved_at": replay.sources.archive_rpc.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": snapshot.block_number,
        },
        "decoded": {
            "label": snapshot.label,
            "owner": replay.subject_address,
            "spender": replay.spender.address,
            "amount_raw": str(_snapshot_value(snapshot)),
        },
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _excluded_evidence(replay: AuthReplay) -> list[dict[str, object]]:
    return [
        {
            "evidence_id": f"EV-AUTH-EXCLUDED-{index}",
            "evidence_type": "context",
            "source_id": replay.sources.public_rpc.source_id,
            "source_record_ref": "SRC-AUTH-PUBLIC",
            "method": "eth_getTransactionReceipt",
            "retrieved_at": replay.sources.public_rpc.retrieved_at,
            "locator": {
                "chain_id": replay.chain_id,
                "block_number": int(receipt.block_number, 16),
                "transaction_hash": receipt.transaction_hash,
            },
            "decoded": {
                "status": "reverted",
                "nonce": int(receipt.nonce, 16),
                "excluded_from_consumption": True,
            },
            "raw_artifact": _artifact(replay, f"EV-AUTH-EXCLUDED-{index}"),
        }
        for index, receipt in enumerate(replay.excluded_receipts, start=1)
    ]


def _explorer_evidence(replay: AuthReplay) -> dict[str, object]:
    cross = replay.explorer_cross_check
    return {
        "evidence_id": "EV-AUTH-EXPLORER-CROSS-CHECK",
        "evidence_type": "context",
        "source_id": replay.sources.explorer.source_id,
        "source_record_ref": "SRC-AUTH-EXPLORER",
        "method": "blockscout_transaction_and_token_transfers",
        "retrieved_at": replay.sources.explorer.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(replay.consumption.transaction.block_number, 16),
            "transaction_hash": cross.consumption_transaction_hash,
            "log_index": cross.transfer_log_index,
        },
        "decoded": {
            "approval_status": cross.approval_status,
            "consumption_status": cross.consumption_status,
            "transfer_amount_raw": cross.transfer_amount_raw,
        },
        "raw_artifact": _artifact(replay, "EV-AUTH-EXPLORER-CROSS-CHECK"),
    }


def _metadata_evidence(replay: AuthReplay) -> dict[str, object]:
    return {
        "evidence_id": "EV-AUTH-SPENDER-METADATA",
        "evidence_type": "context",
        "source_id": replay.sources.metadata.source_id,
        "source_record_ref": "SRC-AUTH-METADATA",
        "method": "pinned_swap_router_02_address",
        "retrieved_at": replay.sources.metadata.retrieved_at,
        "locator": {"chain_id": replay.chain_id},
        "decoded": {
            "spender": replay.spender.address,
            "label": replay.spender.label,
            "deployment_commit": replay.spender.deployment_commit,
            "license": replay.spender.license,
        },
        "raw_artifact": _artifact(replay, "EV-AUTH-SPENDER-METADATA"),
    }


def _artifact(replay: AuthReplay, evidence_id: str) -> dict[str, str]:
    return {
        "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#{evidence_id.lower()}",
        "media_type": "application/json",
    }


def _sources(replay: AuthReplay) -> list[dict[str, object]]:
    specs = (
        ("SRC-AUTH-PUBLIC", replay.sources.public_rpc, "scoring", True, "transaction_receipt"),
        ("SRC-AUTH-ARCHIVE", replay.sources.archive_rpc, "scoring", True, "state_and_trace"),
        ("SRC-AUTH-EXPLORER", replay.sources.explorer, "scoring", True, "cross_check"),
        ("SRC-AUTH-METADATA", replay.sources.metadata, "supporting", False, "spender_metadata"),
    )
    return [
        {
            "source_record_id": record_id,
            "source_id": source.source_id,
            "provider_id": source.provider_id,
            "role": role,
            "required": required,
            "capability": capability,
            "endpoint_host": source.endpoint_host,
            "retrieved_at": source.retrieved_at,
        }
        for record_id, source, role, required, capability in specs
    ]


def _confirmed_results(
    replay: AuthReplay,
    decoded: dict[str, object],
    *,
    include_allowance: bool,
    include_consumption: bool,
    scope_evidence_refs: list[str],
) -> list[dict[str, object]]:
    results = [
        {
            "result_id": "RES-AUTH-APPROVAL",
            "result_type": "approval",
            "classification": "confirmed_fact",
            "value": {
                "type": "approve",
                "owner": decoded["approval_owner"],
                "spender": decoded["approval_spender"],
                "amount_raw": str(decoded["approval_amount"]),
            },
            "tool_requirement_ids": ["REQ-V1-AUTH-001"],
            "fixture_requirement_ids": ["REQ-AUTH-APPROVAL"],
            "evidence_refs": ["EV-AUTH-APPROVAL-EVENT", "EV-AUTH-APPROVE-CALL"],
        }
    ]
    snapshots = decoded["snapshots"]
    if include_allowance:
        results.append(
            {
                "result_id": "RES-AUTH-ALLOWANCE",
                "result_type": "allowance_lifecycle",
                "classification": "confirmed_fact",
                "value": {
                    "before_approval_raw": str(snapshots["before_approval"]),
                    "after_approval_raw": str(snapshots["after_approval"]),
                    "before_consumption_raw": str(snapshots["before_consumption"]),
                    "after_consumption_raw": str(snapshots["after_consumption"]),
                    "consumed_delta_raw": str(
                        snapshots["before_consumption"] - snapshots["after_consumption"]
                    ),
                },
                "tool_requirement_ids": ["REQ-V1-AUTH-002", "REQ-V1-AUTH-004"],
                "fixture_requirement_ids": ["REQ-AUTH-ALLOWANCE"],
                "evidence_refs": [
                    "EV-AUTH-STATE-BEFORE-APPROVAL",
                    "EV-AUTH-STATE-AFTER-APPROVAL",
                    "EV-AUTH-STATE-BEFORE-CONSUMPTION",
                    "EV-AUTH-STATE-AFTER-CONSUMPTION",
                ],
            }
        )
    if include_consumption:
        results.append(
            {
                "result_id": "RES-AUTH-CONSUMPTION",
                "result_type": "authorization_consumption",
                "classification": "confirmed_fact",
                "value": {
                    "method": "transferFrom(address,address,uint256)",
                    "from": decoded["transfer_from"],
                    "to": decoded["transfer_to"],
                    "amount_raw": str(decoded["transfer_amount"]),
                    "excluded_failed_transaction_count": len(replay.excluded_receipts),
                },
                "tool_requirement_ids": [
                    "REQ-V1-AUTH-003",
                    "REQ-V1-AUTH-004",
                    "REQ-V1-AUTH-005",
                    "REQ-V1-AUTH-006",
                ],
                "fixture_requirement_ids": ["REQ-AUTH-CONSUMPTION"],
                "evidence_refs": [
                    "EV-AUTH-OUTER-CALL",
                    "EV-AUTH-TRANSFER-FROM",
                    "EV-AUTH-TRANSFER-EVENT",
                ],
            }
        )
    results.append(
        {
            "result_id": "RES-AUTH-ATTRIBUTION-SCOPE",
            "result_type": "theft_or_phishing_attribution",
            "classification": "not_assessed",
            "value": {
                "theft_or_phishing_claim": False,
                "reason": "The onchain replay proves authorization consumption only.",
            },
            "tool_requirement_ids": ["REQ-V1-AUTH-007"],
            "fixture_requirement_ids": [],
            "evidence_refs": scope_evidence_refs,
        }
    )
    return results


def _error(
    code: str,
    message: str,
    stage: str,
    related_evidence_ids: list[str],
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "error_id": f"ERR-AUTH-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": False,
        "attempt_count": 0,
        "related_evidence_ids": related_evidence_ids,
        "details": details,
    }


def _result(
    request: AuthAnalysisRequest,
    replay: AuthReplay,
    *,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    sources: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    finished_at = max(
        request.requested_at,
        replay.reverified_at,
        replay.sources.public_rpc.retrieved_at,
        replay.sources.archive_rpc.retrieved_at,
        replay.sources.explorer.retrieved_at,
        replay.sources.metadata.retrieved_at,
    )
    document = {
        "$schema": "../../schemas/analysis-result.schema.json",
        "schema_version": "0.1",
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
            finished_at,
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        ),
        "exports": _pending_exports(request.analysis_id),
    }
    return validate_analysis_result(document)


def _failed_without_evidence(
    request: AuthAnalysisRequest,
    *,
    code: str,
    message: str,
    stage: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    document = {
        "$schema": "../../schemas/analysis-result.schema.json",
        "schema_version": "0.1",
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
                "error_id": f"ERR-AUTH-{code.upper().replace('_', '-')}",
                "code": code,
                "message": message,
                "stage": stage,
                "retryable": False,
                "attempt_count": 0,
            }
        ],
        "run": _run(
            request.requested_at,
            request.requested_at,
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        ),
        "exports": _pending_exports(request.analysis_id),
    }
    return validate_analysis_result(document)


def _run(
    started_at: datetime,
    finished_at: datetime,
    *,
    resumed: bool,
    checkpoint_id: str | None,
) -> dict[str, object]:
    run = {
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
        run["checkpoint_id"] = checkpoint_id
    return run


def _pending_exports(analysis_id: str) -> dict[str, object]:
    return {
        "json": {"artifact_uri": f"artifact://pending/{analysis_id}/result.json"},
        "markdown": {"artifact_uri": f"artifact://pending/{analysis_id}/evidence.md"},
    }
