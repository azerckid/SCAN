"""Deterministic Uniswap V2 single-hop DEX replay for TASK-006."""

from datetime import datetime

from eth_abi import decode
from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import DexAnalysisRequest
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.dex import DexReplay, RawInternalCall, RawLog, ReplaySource

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SWAP_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
WITHDRAWAL_TOPIC = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"


def analyze_dex_replay(
    request: DexAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-DEX-REPLAY-EVIDENCE",
) -> AnalysisResult:
    """Decode, reconcile, and classify one approved DEX replay package."""
    try:
        replay = DexReplay.model_validate_json(raw_replay)
    except ValidationError:
        return _failed_without_evidence(
            request,
            code="decode_failed",
            message="The DEX replay package does not match the raw evidence contract.",
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
    request: DexAnalysisRequest,
    replay: DexReplay,
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
            message="The raw DEX logs could not be decoded without ambiguity.",
            stage="decode_logs",
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    evidence = _event_evidence(replay, decoded)
    sources = [_source_record(replay.sources.receipt, "SRC-DEX-PUBLICNODE", "scoring", True)]
    metadata_evidence = _metadata_evidence(replay)
    evidence.append(metadata_evidence)
    sources.append(_source_record(replay.sources.metadata, "SRC-DEX-UNISWAP", "supporting", True))

    mismatches = _reconciliation_mismatches(replay, decoded)
    try:
        internal_call = _matching_internal_call(replay)
    except ValueError:
        mismatches.append("ambiguous_internal_native_output")
        internal_call = None
    if internal_call is not None:
        evidence.append(_call_evidence(replay, internal_call))
        sources.append(
            _source_record(
                replay.sources.internal_calls,
                "SRC-DEX-BLOCKSCOUT",
                "scoring",
                True,
            )
        )
        if int(internal_call.value) != decoded["withdrawal"]:
            mismatches.append("internal_native_output")

    if mismatches:
        evidence_ids = [item["evidence_id"] for item in evidence]
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
                    "Raw Transfer, Swap, Withdrawal, and native-call amounts do not reconcile.",
                    "reconcile_swap",
                    evidence_ids,
                    {"mismatches": mismatches},
                )
            ],
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    results = _confirmed_results(replay, decoded, include_user_output=internal_call is not None)
    if internal_call is None:
        withdrawal_id = "EV-DEX-WITHDRAWAL"
        return _result(
            request,
            replay,
            status="partial",
            results=results,
            evidence=evidence,
            sources=sources,
            errors=[
                _error(
                    "trace_unavailable",
                    "Pool output is confirmed but the required native ETH call is missing.",
                    "collect_internal_calls",
                    [withdrawal_id],
                    {"missing_requirement_ids": ["REQ-DEX-USER-NET-OUTPUT"]},
                )
            ],
            resumed=resumed,
            checkpoint_id=checkpoint_id,
        )

    return _result(
        request,
        replay,
        status="complete",
        results=results,
        evidence=evidence,
        sources=sources,
        errors=[],
        resumed=resumed,
        checkpoint_id=checkpoint_id,
    )


def _binding_error(
    request: DexAnalysisRequest,
    replay: DexReplay,
) -> tuple[str, str] | None:
    policy = request.source_policy
    if not policy.offline_mode:
        return "rule_restricted", "TASK-006 supports offline replay only."
    if request.inputs.transaction_hash != replay.transaction.hash:
        return "reconciliation_failed", "Request and replay transaction hashes differ."
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return "reconciliation_failed", "Request and replay fixture IDs differ."
    required_sources = {
        replay.sources.receipt.source_id,
        replay.sources.metadata.source_id,
    }
    if replay.internal_calls:
        required_sources.add(replay.sources.internal_calls.source_id)
    if not required_sources <= set(policy.allowed_source_ids):
        return "rule_restricted", "Replay evidence uses a source outside the allowed policy."
    tx = replay.transaction
    receipt = replay.receipt
    if (
        replay.chain_id != request.chain_id
        or receipt.status != "0x1"
        or tx.hash != receipt.transaction_hash
        or tx.block_hash != receipt.block_hash
        or tx.block_number != receipt.block_number
        or tx.from_address != receipt.from_address
        or tx.to != receipt.to
        or tx.transaction_index != receipt.transaction_index
    ):
        return "reconciliation_failed", "Transaction and receipt identity fields differ."
    return None


def _decode_replay(replay: DexReplay) -> dict[str, object]:
    metadata = replay.metadata
    tx = replay.transaction
    pair = metadata.pair.address
    router = metadata.router.address
    asset_in = metadata.tokens.asset_in.address
    pool_output = metadata.tokens.pool_output.address

    transfer_in = _one_log(
        replay,
        TRANSFER_TOPIC,
        asset_in,
        from_address=tx.from_address,
        to_address=pair,
    )
    transfer_out = _one_log(
        replay,
        TRANSFER_TOPIC,
        pool_output,
        from_address=pair,
        to_address=router,
    )
    swap = _one_log(replay, SWAP_TOPIC, pair)
    withdrawal = _one_log(
        replay,
        WITHDRAWAL_TOPIC,
        pool_output,
        from_address=router,
    )

    swap_values = decode(["uint256", "uint256", "uint256", "uint256"], _data_bytes(swap))
    return {
        "transfer_in_log": transfer_in,
        "transfer_in": _uint256(transfer_in),
        "transfer_out_log": transfer_out,
        "transfer_out": _uint256(transfer_out),
        "swap_log": swap,
        "swap_amount0_in": swap_values[0],
        "swap_amount1_in": swap_values[1],
        "swap_amount0_out": swap_values[2],
        "swap_amount1_out": swap_values[3],
        "withdrawal_log": withdrawal,
        "withdrawal": _uint256(withdrawal),
    }


def _one_log(
    replay: DexReplay,
    topic: str,
    address: str,
    *,
    from_address: str | None = None,
    to_address: str | None = None,
) -> RawLog:
    candidates = [
        log
        for log in replay.receipt.logs
        if log.address == address
        and log.topics[0] == topic
        and log.transaction_hash == replay.transaction.hash
        and log.block_hash == replay.transaction.block_hash
        and log.block_number == replay.transaction.block_number
    ]
    if from_address is not None:
        candidates = [log for log in candidates if _topic_address(log.topics[1]) == from_address]
    if to_address is not None:
        candidates = [log for log in candidates if _topic_address(log.topics[2]) == to_address]
    if len(candidates) != 1:
        raise ValueError("required raw log is missing or ambiguous")
    return candidates[0]


def _topic_address(topic: str) -> str:
    return to_normalized_address(f"0x{topic[-40:]}")


def _data_bytes(log: RawLog) -> bytes:
    return bytes.fromhex(log.data[2:])


def _uint256(log: RawLog) -> int:
    return int(decode(["uint256"], _data_bytes(log))[0])


def _matching_internal_call(replay: DexReplay) -> RawInternalCall | None:
    calls = [
        call
        for call in replay.internal_calls
        if call.from_address == replay.metadata.router.address
        and call.to == replay.transaction.from_address
        and call.transaction_hash == replay.transaction.hash
        and int(call.block_number) == int(replay.transaction.block_number, 16)
    ]
    if len(calls) > 1:
        raise ValueError("native output call is ambiguous")
    return calls[0] if calls else None


def _reconciliation_mismatches(
    replay: DexReplay,
    decoded: dict[str, object],
) -> list[str]:
    mismatches = []
    pairs = (
        ("asset_in_transfer_vs_swap", decoded["transfer_in"], decoded["swap_amount0_in"]),
        ("pool_output_transfer_vs_swap", decoded["transfer_out"], decoded["swap_amount1_out"]),
        ("pool_output_vs_withdrawal", decoded["transfer_out"], decoded["withdrawal"]),
    )
    for label, left, right in pairs:
        if left != right:
            mismatches.append(label)
    if decoded["swap_amount1_in"] != 0 or decoded["swap_amount0_out"] != 0:
        mismatches.append("unexpected_swap_legs")
    historical_pair = to_normalized_address(
        f"0x{replay.metadata.pair.historical_get_pair_result[-40:]}"
    )
    if historical_pair != replay.metadata.pair.address:
        mismatches.append("factory_pair_identity")
    return mismatches


def _event_evidence(
    replay: DexReplay,
    decoded: dict[str, object],
) -> list[dict[str, object]]:
    specs = (
        (
            "EV-DEX-TRANSFER-IN",
            "transfer_event",
            decoded["transfer_in_log"],
            {"event": "Transfer", "amount_raw": str(decoded["transfer_in"])},
        ),
        (
            "EV-DEX-TRANSFER-OUT",
            "transfer_event",
            decoded["transfer_out_log"],
            {"event": "Transfer", "amount_raw": str(decoded["transfer_out"])},
        ),
        (
            "EV-DEX-SWAP",
            "swap_event",
            decoded["swap_log"],
            {
                "event": "Swap",
                "amount0_in_raw": str(decoded["swap_amount0_in"]),
                "amount1_in_raw": str(decoded["swap_amount1_in"]),
                "amount0_out_raw": str(decoded["swap_amount0_out"]),
                "amount1_out_raw": str(decoded["swap_amount1_out"]),
            },
        ),
        (
            "EV-DEX-WITHDRAWAL",
            "withdrawal_event",
            decoded["withdrawal_log"],
            {"event": "Withdrawal", "amount_raw": str(decoded["withdrawal"])},
        ),
    )
    return [
        {
            "evidence_id": evidence_id,
            "evidence_type": "event",
            "source_id": replay.sources.receipt.source_id,
            "source_record_ref": "SRC-DEX-PUBLICNODE",
            "method": "eth_getTransactionReceipt",
            "retrieved_at": replay.sources.receipt.retrieved_at,
            "locator": {
                "chain_id": replay.chain_id,
                "block_number": int(log.block_number, 16),
                "transaction_hash": log.transaction_hash,
                "log_index": int(log.log_index, 16),
            },
            "decoded": decoded_value,
            "raw_artifact": {
                "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#log-{int(log.log_index, 16)}",
                "media_type": "application/json",
            },
        }
        for evidence_id, _kind, log, decoded_value in specs
    ]


def _call_evidence(
    replay: DexReplay,
    call: RawInternalCall,
) -> dict[str, object]:
    return {
        "evidence_id": "EV-DEX-INTERNAL-ETH",
        "evidence_type": "call",
        "source_id": replay.sources.internal_calls.source_id,
        "source_record_ref": "SRC-DEX-BLOCKSCOUT",
        "method": "get_internal_transactions",
        "retrieved_at": replay.sources.internal_calls.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(call.block_number),
            "transaction_hash": call.transaction_hash,
            "trace_address": [int(call.index)],
        },
        "decoded": {
            "asset_type": "native",
            "from": call.from_address,
            "to": call.to,
            "amount_raw": call.value,
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#internal-{call.index}",
            "media_type": "application/json",
        },
    }


def _metadata_evidence(replay: DexReplay) -> dict[str, object]:
    metadata = replay.metadata
    return {
        "evidence_id": "EV-DEX-METADATA",
        "evidence_type": "context",
        "source_id": replay.sources.metadata.source_id,
        "source_record_ref": "SRC-DEX-UNISWAP",
        "method": "pinned_deployment_and_factory_get_pair",
        "retrieved_at": replay.sources.metadata.retrieved_at,
        "locator": {
            "chain_id": replay.chain_id,
            "block_number": int(replay.transaction.block_number, 16),
        },
        "decoded": {
            "router_address": metadata.router.address,
            "router_label": metadata.router.label,
            "factory_address": metadata.factory.address,
            "pair_address": metadata.pair.address,
            "deployment_commit": metadata.router.deployment_commit,
            "deployment_json_sha256": metadata.router.deployment_json_sha256,
            "license": metadata.router.license,
        },
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#metadata",
            "media_type": "application/json",
        },
    }


def _confirmed_results(
    replay: DexReplay,
    decoded: dict[str, object],
    *,
    include_user_output: bool,
) -> list[dict[str, object]]:
    metadata = replay.metadata
    results = [
        {
            "result_id": "RES-DEX-ASSET-IN",
            "result_type": "asset_in",
            "classification": "confirmed_fact",
            "value": {
                "token_address": metadata.tokens.asset_in.address,
                "symbol": metadata.tokens.asset_in.symbol,
                "decimals": metadata.tokens.asset_in.decimals,
                "amount_raw": str(decoded["transfer_in"]),
            },
            "tool_requirement_ids": ["REQ-V1-DEX-001"],
            "fixture_requirement_ids": ["REQ-DEX-ASSET-IN"],
            "evidence_refs": ["EV-DEX-TRANSFER-IN", "EV-DEX-SWAP"],
        },
        {
            "result_id": "RES-DEX-POOL-OUTPUT",
            "result_type": "pool_output",
            "classification": "confirmed_fact",
            "value": {
                "token_address": metadata.tokens.pool_output.address,
                "symbol": metadata.tokens.pool_output.symbol,
                "decimals": metadata.tokens.pool_output.decimals,
                "amount_raw": str(decoded["transfer_out"]),
            },
            "tool_requirement_ids": ["REQ-V1-DEX-002", "REQ-V1-DEX-004"],
            "fixture_requirement_ids": ["REQ-DEX-POOL-OUTPUT"],
            "evidence_refs": ["EV-DEX-TRANSFER-OUT", "EV-DEX-SWAP", "EV-DEX-METADATA"],
        },
    ]
    if include_user_output:
        call = _matching_internal_call(replay)
        assert call is not None
        results.append(
            {
                "result_id": "RES-DEX-USER-NET-OUTPUT",
                "result_type": "user_net_output",
                "classification": "confirmed_fact",
                "value": {
                    "asset_type": "native",
                    "token_address": None,
                    "symbol": metadata.tokens.user_output.symbol,
                    "decimals": metadata.tokens.user_output.decimals,
                    "amount_raw": call.value,
                    "from": call.from_address,
                    "to": call.to,
                },
                "tool_requirement_ids": ["REQ-V1-DEX-003", "REQ-V1-DEX-004"],
                "fixture_requirement_ids": ["REQ-DEX-USER-NET-OUTPUT"],
                "evidence_refs": ["EV-DEX-WITHDRAWAL", "EV-DEX-INTERNAL-ETH"],
            }
        )
    return results


def _source_record(
    source: ReplaySource,
    source_record_id: str,
    role: str,
    required: bool,
) -> dict[str, object]:
    capability = {
        "SRC-DEX-PUBLICNODE": "transaction_receipt",
        "SRC-DEX-BLOCKSCOUT": "internal_transactions",
        "SRC-DEX-UNISWAP": "dex_metadata",
    }[source_record_id]
    return {
        "source_record_id": source_record_id,
        "source_id": source.source_id,
        "provider_id": source.provider_id,
        "role": role,
        "required": required,
        "capability": capability,
        "endpoint_host": source.endpoint_host,
        "retrieved_at": source.retrieved_at,
    }


def _error(
    code: str,
    message: str,
    stage: str,
    related_evidence_ids: list[str],
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "error_id": f"ERR-DEX-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": False,
        "attempt_count": 0,
        "related_evidence_ids": related_evidence_ids,
        "details": details,
    }


def _result(
    request: DexAnalysisRequest,
    replay: DexReplay,
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
        replay.sources.receipt.retrieved_at,
        replay.sources.internal_calls.retrieved_at,
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
    request: DexAnalysisRequest,
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
                "error_id": f"ERR-DEX-{code.upper().replace('_', '-')}",
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
