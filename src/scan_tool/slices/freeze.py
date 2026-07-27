"""Deterministic USDC blacklist lifecycle replay for TASK-008."""

from datetime import datetime

from eth_abi import decode
from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import FreezeAnalysisRequest, RuleStatus
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.auth import TransactionEvidence
from scan_tool.domain.dex import RawLog, RawTransaction, ReplaySource
from scan_tool.domain.freeze import FreezeReplay, FreezeSnapshot, OfficialContext

BLACKLIST_TOPIC = "0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855"
UNBLACKLIST_TOPIC = "0x117e3210bb9aa7d9baff172026820255c6f6c30ba8999d1c2fd88e2848137c4e"
BLACKLIST_SELECTOR = "0xf9f92be4"
UNBLACKLIST_SELECTOR = "0x1a895266"
IS_BLACKLISTED_SELECTOR = "0xfe575a87"
SNAPSHOT_LABELS = (
    "before_blacklist",
    "after_blacklist",
    "before_unblacklist",
    "after_unblacklist",
)
PINNED_INTERFACE = {
    "commit_sha": "b42cf04b31639b8b05d53fea9995954d5f3659d9",
    "file_sha256": "d1e8fe82c7e77ca626c27c4205dac994e6c0c97e18f86cb17559d952df8425eb",
    "license_sha256": "ab49aea32292bcf2744f2a37bf8887feffeb124e04a76e1b99e0a1eae2a9053b",
}


def analyze_freeze_replay(
    request: FreezeAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-FREEZE-REPLAY-EVIDENCE",
) -> AnalysisResult:
    """Decode and reconcile one approved address-blacklist replay package."""
    try:
        replay = FreezeReplay.model_validate_json(raw_replay)
    except ValidationError:
        return _failed_without_evidence(
            request,
            code="decode_failed",
            message="The FREEZE replay package does not match the raw evidence contract.",
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
    request: FreezeAnalysisRequest,
    replay: FreezeReplay,
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
            message="The raw FREEZE evidence could not be decoded without ambiguity.",
            stage="decode_freeze",
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
                    "Blacklist calls, events, historical states, and context differ.",
                    "reconcile_freeze",
                    [item["evidence_id"] for item in evidence],
                    {"mismatches": mismatches},
                )
            ],
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    snapshots = decoded["snapshots"]
    missing_snapshots = [label for label in SNAPSHOT_LABELS if label not in snapshots]
    errors = []
    if missing_snapshots:
        errors.append(
            _error(
                "archive_required",
                "Historical isBlacklisted snapshots are incomplete.",
                "collect_freeze_state",
                [item["evidence_id"] for item in evidence if item["evidence_type"] == "state"],
                {"missing_snapshot_labels": missing_snapshots},
            )
        )
    if replay.unblacklist is None:
        errors.append(
            _error(
                "evidence_incomplete",
                "The blacklist transition is preserved but unblacklist evidence is missing.",
                "collect_unblacklist",
                ["EV-FREEZE-BLACKLIST-CALL", "EV-FREEZE-BLACKLIST-EVENT"],
                {"missing_requirement_ids": ["REQ-FREEZE-UNBLACKLIST"]},
            )
        )

    results = _results(
        replay,
        decoded,
        include_blacklist={"before_blacklist", "after_blacklist"} <= set(snapshots),
        include_unblacklist=(
            replay.unblacklist is not None
            and {"before_unblacklist", "after_unblacklist"} <= set(snapshots)
        ),
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
    request: FreezeAnalysisRequest,
    replay: FreezeReplay,
) -> tuple[str, str] | None:
    policy = request.source_policy
    if policy.rule_status == RuleStatus.RESTRICTED or not policy.offline_mode:
        return "rule_restricted", "TASK-008 supports approved offline replay only."
    inputs = request.inputs
    request_hashes = list(inputs.event_transaction_hashes)
    replay_hashes = [replay.blacklist.transaction.hash]
    if replay.unblacklist is not None:
        replay_hashes.append(replay.unblacklist.transaction.hash)
    if (
        request.chain_id != replay.chain_id
        or inputs.token_address != replay.token.address
        or inputs.target_address != replay.target_address
        or inputs.mode != replay.mode
        or request_hashes[: len(replay_hashes)] != replay_hashes
    ):
        return "reconciliation_failed", "Request and replay FREEZE identifiers differ."
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return "reconciliation_failed", "Request and replay fixture IDs differ."
    required_sources = {
        replay.sources.public_rpc.source_id,
        replay.sources.archive_rpc.source_id,
        replay.sources.explorer.source_id,
        replay.sources.issuer.source_id,
        replay.sources.sanctions.source_id,
    }
    if not required_sources <= set(policy.allowed_source_ids):
        return "rule_restricted", "Replay evidence uses a source outside the allowed policy."
    if inputs.context_urls is not MISSING:
        replay_urls = {str(item.url) for item in replay.official_context}
        if not {str(item) for item in inputs.context_urls} <= replay_urls:
            return "reconciliation_failed", "Requested context URL is absent from the replay."
    return None


def _decode_replay(replay: FreezeReplay) -> dict[str, object]:
    blacklist_log = _one_log(
        replay.blacklist.receipt.selected_logs,
        BLACKLIST_TOPIC,
        replay.token.address,
    )
    blacklist_target = _decode_target(replay.blacklist.transaction.input, BLACKLIST_SELECTOR)
    unblacklist_log = None
    unblacklist_target = None
    if replay.unblacklist is not None:
        unblacklist_log = _one_log(
            replay.unblacklist.receipt.selected_logs,
            UNBLACKLIST_TOPIC,
            replay.token.address,
        )
        unblacklist_target = _decode_target(
            replay.unblacklist.transaction.input,
            UNBLACKLIST_SELECTOR,
        )
    query_target = _decode_target(replay.state_query.data, IS_BLACKLISTED_SELECTOR)
    snapshots = {item.label: _snapshot_value(item) for item in replay.state_query.snapshots}
    if len(snapshots) != len(replay.state_query.snapshots):
        raise ValueError("duplicate FREEZE snapshot")
    return {
        "blacklist_log": blacklist_log,
        "blacklist_event_target": _topic_address(blacklist_log.topics[1]),
        "blacklist_call_target": blacklist_target,
        "unblacklist_log": unblacklist_log,
        "unblacklist_event_target": (
            _topic_address(unblacklist_log.topics[1]) if unblacklist_log is not None else None
        ),
        "unblacklist_call_target": unblacklist_target,
        "query_target": query_target,
        "snapshots": snapshots,
    }


def _decode_target(value: str, selector: str) -> str:
    if not value.startswith(selector):
        raise ValueError("unexpected selector")
    return to_normalized_address(decode(["address"], bytes.fromhex(value[10:]))[0])


def _one_log(logs: list[RawLog], topic: str, address: str) -> RawLog:
    candidates = [
        log for log in logs if log.address == address and log.topics and log.topics[0] == topic
    ]
    if len(candidates) != 1:
        raise ValueError("required FREEZE log is missing or ambiguous")
    return candidates[0]


def _topic_address(topic: str) -> str:
    return to_normalized_address(f"0x{topic[-40:]}")


def _snapshot_value(snapshot: FreezeSnapshot) -> bool:
    if int(snapshot.block_tag, 16) != snapshot.block_number:
        raise ValueError("snapshot block tag differs")
    return bool(decode(["bool"], bytes.fromhex(snapshot.result[2:]))[0])


def _mismatches(
    request: FreezeAnalysisRequest,
    replay: FreezeReplay,
    decoded: dict[str, object],
) -> list[str]:
    mismatches = []
    target = replay.target_address
    token = replay.token.address
    if not _transaction_receipt_match(replay.blacklist):
        mismatches.append("blacklist_transaction_receipt")
    if (
        replay.blacklist.receipt.status != "0x1"
        or replay.blacklist.transaction.to != token
        or decoded["blacklist_call_target"] != target
        or decoded["blacklist_event_target"] != target
    ):
        mismatches.append("blacklist_call_event_identity")
    if decoded["query_target"] != target or replay.state_query.to != token:
        mismatches.append("state_query_identity")
    if replay.unblacklist is not None:
        if not _transaction_receipt_match(replay.unblacklist):
            mismatches.append("unblacklist_transaction_receipt")
        if (
            replay.unblacklist.receipt.status != "0x1"
            or replay.unblacklist.transaction.to != token
            or decoded["unblacklist_call_target"] != target
            or decoded["unblacklist_event_target"] != target
        ):
            mismatches.append("unblacklist_call_event_identity")
    mismatches.extend(_state_mismatches(request, replay, decoded))
    mismatches.extend(_context_mismatches(replay))
    mismatches.extend(_explorer_mismatches(replay, decoded))
    return mismatches


def _transaction_receipt_match(value: TransactionEvidence) -> bool:
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


def _state_mismatches(
    request: FreezeAnalysisRequest,
    replay: FreezeReplay,
    decoded: dict[str, object],
) -> list[str]:
    mismatches = []
    snapshots = decoded["snapshots"]
    block_map = {item.label: item.block_number for item in replay.state_query.snapshots}
    request_blocks = request.inputs.state_blocks
    expected_blocks = {
        "before_blacklist": request_blocks.before_blacklist,
        "after_blacklist": request_blocks.after_blacklist,
        "before_unblacklist": request_blocks.before_unblacklist,
        "after_unblacklist": request_blocks.after_unblacklist,
    }
    expected_values = {
        "before_blacklist": False,
        "after_blacklist": True,
        "before_unblacklist": True,
        "after_unblacklist": False,
    }
    for label in set(SNAPSHOT_LABELS) & set(snapshots):
        if block_map[label] != expected_blocks[label]:
            mismatches.append(f"state_block_{label}")
        if snapshots[label] is not expected_values[label]:
            mismatches.append(f"state_value_{label}")
    return mismatches


def _context_mismatches(replay: FreezeReplay) -> list[str]:
    contexts = {item.context_id: item for item in replay.official_context}
    required = {
        "circle_response",
        "circle_terms",
        "circle_contract",
        "ofac_designation",
        "ofac_removal",
    }
    mismatches = []
    if set(contexts) != required:
        mismatches.append("official_context_set")
        return mismatches
    if any(contexts[item].address_specific for item in required if item.startswith("circle_")):
        mismatches.append("circle_address_specific")
    if any(
        not contexts[item].address_specific or contexts[item].target_address_listed is not True
        for item in ("ofac_designation", "ofac_removal")
    ):
        mismatches.append("ofac_address_specific")
    interface = replay.interface_metadata
    if (
        interface.commit_sha != PINNED_INTERFACE["commit_sha"]
        or interface.file_sha256 != PINNED_INTERFACE["file_sha256"]
        or interface.license_sha256 != PINNED_INTERFACE["license_sha256"]
        or interface.license != "MIT"
    ):
        mismatches.append("pinned_interface")
    if replay.global_pause_applicable:
        mismatches.append("global_pause_scope")
    return mismatches


def _explorer_mismatches(
    replay: FreezeReplay,
    decoded: dict[str, object],
) -> list[str]:
    expected = {
        "blacklist": (
            replay.blacklist.transaction,
            decoded["blacklist_log"],
        )
    }
    if replay.unblacklist is not None:
        expected["unBlacklist"] = (
            replay.unblacklist.transaction,
            decoded["unblacklist_log"],
        )
    if {item.method for item in replay.explorer_cross_check} != set(expected):
        return ["explorer_cross_check_set"]
    for item in replay.explorer_cross_check:
        transaction, log = expected[item.method]
        if (
            item.transaction_hash != transaction.hash
            or item.from_address != transaction.from_address
            or item.to != transaction.to
            or item.raw_input != transaction.input
            or item.log_index != int(log.log_index, 16)
        ):
            return ["explorer_cross_check"]
    return []


def _evidence(replay: FreezeReplay, decoded: dict[str, object]) -> list[dict[str, object]]:
    evidence = [
        _call_evidence(
            replay,
            "EV-FREEZE-BLACKLIST-CALL",
            replay.blacklist.transaction,
            "blacklist(address)",
            decoded["blacklist_call_target"],
        ),
        _event_evidence(
            replay,
            "EV-FREEZE-BLACKLIST-EVENT",
            decoded["blacklist_log"],
            "Blacklisted",
            decoded["blacklist_event_target"],
        ),
    ]
    if replay.unblacklist is not None:
        evidence.extend(
            [
                _call_evidence(
                    replay,
                    "EV-FREEZE-UNBLACKLIST-CALL",
                    replay.unblacklist.transaction,
                    "unBlacklist(address)",
                    decoded["unblacklist_call_target"],
                ),
                _event_evidence(
                    replay,
                    "EV-FREEZE-UNBLACKLIST-EVENT",
                    decoded["unblacklist_log"],
                    "UnBlacklisted",
                    decoded["unblacklist_event_target"],
                ),
            ]
        )
    evidence.extend(_state_evidence(replay, item) for item in replay.state_query.snapshots)
    evidence.extend(_context_evidence(replay, item) for item in replay.official_context)
    evidence.append(_interface_evidence(replay))
    evidence.append(_public_cross_check(replay))
    return evidence


def _call_evidence(
    replay: FreezeReplay,
    evidence_id: str,
    transaction: RawTransaction,
    method: str,
    target: object,
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "call",
        "source_id": replay.sources.explorer.source_id,
        "source_record_ref": "SRC-FREEZE-EXPLORER",
        "method": "get_transaction",
        "retrieved_at": replay.sources.explorer.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(transaction.block_number, 16),
            "transaction_hash": transaction.hash,
        },
        "decoded": {"method": method, "target": target},
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _event_evidence(
    replay: FreezeReplay,
    evidence_id: str,
    log: RawLog,
    event: str,
    target: object,
) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "event",
        "source_id": replay.sources.archive_rpc.source_id,
        "source_record_ref": "SRC-FREEZE-ARCHIVE",
        "method": "eth_getTransactionReceipt",
        "retrieved_at": replay.sources.archive_rpc.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(log.block_number, 16),
            "transaction_hash": log.transaction_hash,
            "log_index": int(log.log_index, 16),
        },
        "decoded": {"event": event, "target": target},
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _state_evidence(
    replay: FreezeReplay,
    snapshot: FreezeSnapshot,
) -> dict[str, object]:
    evidence_id = f"EV-FREEZE-STATE-{snapshot.label.replace('_', '-').upper()}"
    return {
        "evidence_id": evidence_id,
        "evidence_type": "state",
        "source_id": replay.sources.archive_rpc.source_id,
        "source_record_ref": "SRC-FREEZE-ARCHIVE",
        "method": "eth_call",
        "retrieved_at": replay.sources.archive_rpc.retrieved_at,
        "locator": {"chain_id": replay.chain_id, "block_number": snapshot.block_number},
        "decoded": {
            "method": "isBlacklisted(address)",
            "target": replay.target_address,
            "value": _snapshot_value(snapshot),
        },
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _context_evidence(
    replay: FreezeReplay,
    context: OfficialContext,
) -> dict[str, object]:
    evidence_id = f"EV-FREEZE-{context.context_id.replace('_', '-').upper()}"
    source_record_ref = (
        "SRC-FREEZE-ISSUER"
        if context.source_id == replay.sources.issuer.source_id
        else "SRC-FREEZE-SANCTIONS"
    )
    decoded = {
        "provider": context.provider,
        "title": context.title,
        "address_specific": context.address_specific,
        "role": context.role,
    }
    if context.target_address_listed is not None:
        decoded["target_address_listed"] = context.target_address_listed
    return {
        "evidence_id": evidence_id,
        "evidence_type": "context",
        "source_id": context.source_id,
        "source_record_ref": source_record_ref,
        "method": "reviewed_official_record",
        "retrieved_at": context.retrieved_at,
        "locator": {"url": str(context.url)},
        "decoded": decoded,
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _interface_evidence(replay: FreezeReplay) -> dict[str, object]:
    item = replay.interface_metadata
    evidence_id = "EV-FREEZE-CIRCLE-INTERFACE"
    return {
        "evidence_id": evidence_id,
        "evidence_type": "context",
        "source_id": item.source_id,
        "source_record_ref": "SRC-FREEZE-ISSUER",
        "method": "pinned_contract_interface",
        "retrieved_at": item.retrieved_at,
        "locator": {"url": str(item.url)},
        "decoded": {
            "commit_sha": item.commit_sha,
            "file_sha256": item.file_sha256,
            "license": item.license,
            "license_sha256": item.license_sha256,
        },
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _public_cross_check(replay: FreezeReplay) -> dict[str, object]:
    evidence_id = "EV-FREEZE-PUBLIC-RPC-CROSS-CHECK"
    hashes = [replay.blacklist.transaction.hash]
    if replay.unblacklist is not None:
        hashes.append(replay.unblacklist.transaction.hash)
    return {
        "evidence_id": evidence_id,
        "evidence_type": "context",
        "source_id": replay.sources.public_rpc.source_id,
        "source_record_ref": "SRC-FREEZE-PUBLIC",
        "method": "eth_getTransactionByHash_and_receipt",
        "retrieved_at": replay.sources.public_rpc.retrieved_at,
        "locator": {"chain_id": replay.chain_id},
        "decoded": {"transaction_hashes": hashes, "all_status_success": True},
        "raw_artifact": _artifact(replay, evidence_id),
    }


def _artifact(replay: FreezeReplay, evidence_id: str) -> dict[str, str]:
    return {
        "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#{evidence_id.lower()}",
        "media_type": "application/json",
    }


def _sources(replay: FreezeReplay) -> list[dict[str, object]]:
    specs = (
        ("SRC-FREEZE-ARCHIVE", replay.sources.archive_rpc, "scoring", True, "event_and_state"),
        ("SRC-FREEZE-EXPLORER", replay.sources.explorer, "scoring", True, "call_cross_check"),
        ("SRC-FREEZE-ISSUER", replay.sources.issuer, "context", True, "issuer_context"),
        (
            "SRC-FREEZE-SANCTIONS",
            replay.sources.sanctions,
            "context",
            False,
            "historical_sanctions_context",
        ),
        (
            "SRC-FREEZE-PUBLIC",
            replay.sources.public_rpc,
            "supporting",
            False,
            "transaction_receipt_cross_check",
        ),
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


def _results(
    replay: FreezeReplay,
    decoded: dict[str, object],
    *,
    include_blacklist: bool,
    include_unblacklist: bool,
    scope_evidence_refs: list[str],
) -> list[dict[str, object]]:
    results = []
    snapshots = decoded["snapshots"]
    if include_blacklist:
        results.append(
            {
                "result_id": "RES-FREEZE-BLACKLIST",
                "result_type": "blacklist_transition",
                "classification": "confirmed_fact",
                "value": {
                    "target_address": replay.target_address,
                    "before": snapshots["before_blacklist"],
                    "after": snapshots["after_blacklist"],
                    "before_block": _snapshot_block(replay, "before_blacklist"),
                    "after_block": _snapshot_block(replay, "after_blacklist"),
                },
                "tool_requirement_ids": ["REQ-V1-FREEZE-001", "REQ-V1-FREEZE-003"],
                "fixture_requirement_ids": ["REQ-FREEZE-BLACKLIST"],
                "evidence_refs": [
                    "EV-FREEZE-BLACKLIST-CALL",
                    "EV-FREEZE-BLACKLIST-EVENT",
                    "EV-FREEZE-STATE-BEFORE-BLACKLIST",
                    "EV-FREEZE-STATE-AFTER-BLACKLIST",
                ],
            }
        )
    if include_unblacklist:
        results.append(
            {
                "result_id": "RES-FREEZE-UNBLACKLIST",
                "result_type": "unblacklist_transition",
                "classification": "confirmed_fact",
                "value": {
                    "target_address": replay.target_address,
                    "before": snapshots["before_unblacklist"],
                    "after": snapshots["after_unblacklist"],
                    "before_block": _snapshot_block(replay, "before_unblacklist"),
                    "after_block": _snapshot_block(replay, "after_unblacklist"),
                },
                "tool_requirement_ids": ["REQ-V1-FREEZE-002", "REQ-V1-FREEZE-003"],
                "fixture_requirement_ids": ["REQ-FREEZE-UNBLACKLIST"],
                "evidence_refs": [
                    "EV-FREEZE-UNBLACKLIST-CALL",
                    "EV-FREEZE-UNBLACKLIST-EVENT",
                    "EV-FREEZE-STATE-BEFORE-UNBLACKLIST",
                    "EV-FREEZE-STATE-AFTER-UNBLACKLIST",
                ],
            }
        )
    results.append(
        {
            "result_id": "RES-FREEZE-CONTEXT",
            "result_type": "official_context_scope",
            "classification": "external_context",
            "value": {
                "circle_address_specific": False,
                "ofac_address_specific": True,
                "current_sanctions_status": "not_assessed",
                "criminal_intent": "not_assessed",
                "global_pause": {"applicable": False},
            },
            "tool_requirement_ids": [
                "REQ-V1-FREEZE-004",
                "REQ-V1-FREEZE-005",
                "REQ-V1-FREEZE-006",
                "REQ-V1-FREEZE-007",
                "REQ-V1-FREEZE-008",
            ],
            "fixture_requirement_ids": ["REQ-FREEZE-CONTEXT-SEPARATION"],
            "evidence_refs": scope_evidence_refs,
        }
    )
    return results


def _snapshot_block(replay: FreezeReplay, label: str) -> int:
    return next(item.block_number for item in replay.state_query.snapshots if item.label == label)


def _error(
    code: str,
    message: str,
    stage: str,
    related_evidence_ids: list[str],
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "error_id": f"ERR-FREEZE-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": False,
        "attempt_count": 0,
        "related_evidence_ids": related_evidence_ids,
        "details": details,
    }


def _result(
    request: FreezeAnalysisRequest,
    replay: FreezeReplay,
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
        *(item.retrieved_at for item in replay.official_context),
        *(source.retrieved_at for source in _replay_sources(replay)),
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


def _replay_sources(replay: FreezeReplay) -> tuple[ReplaySource, ...]:
    return (
        replay.sources.public_rpc,
        replay.sources.archive_rpc,
        replay.sources.explorer,
        replay.sources.issuer,
        replay.sources.sanctions,
    )


def _failed_without_evidence(
    request: FreezeAnalysisRequest,
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
                "error_id": f"ERR-FREEZE-{code.upper().replace('_', '-')}",
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
