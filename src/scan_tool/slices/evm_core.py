"""Deterministic TASK-012 EVM Core replay analyzers."""

from datetime import datetime

from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import (
    EvmCoreAnalysisRequest,
    FirstTokenTransferInputs,
    HistoricalBalanceInputs,
    NativeInflowInputs,
    ObjectSummaryInputs,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.evm_core import (
    EvmCoreReplay,
    EvmCoreReplayDocument,
    EvmReplaySource,
    FirstTokenTransferReplay,
    HistoricalBalanceReplay,
    NativeInflowReplay,
    ObjectSummaryReplay,
)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def analyze_evm_core_replay(
    request: EvmCoreAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-EVM-CORE-REPLAY-EVIDENCE",
) -> AnalysisResult:
    """Run one approved EVM Core query over reviewed raw replay evidence."""
    try:
        replay = EvmCoreReplay.model_validate_json(raw_replay).root
    except ValidationError:
        return _failed(
            request,
            "decode_failed",
            "The EVM Core replay package does not match the raw evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )
    binding_error = _binding_error(request, replay)
    if binding_error is not None:
        return _failed(
            request,
            binding_error[0],
            binding_error[1],
            "validate_replay",
            resumed,
            checkpoint_id,
        )
    try:
        if isinstance(replay, ObjectSummaryReplay):
            return _object_summary(request, replay, resumed, checkpoint_id)
        if isinstance(replay, HistoricalBalanceReplay):
            return _historical_balance(request, replay, resumed, checkpoint_id)
        if isinstance(replay, FirstTokenTransferReplay):
            return _first_token_transfer(request, replay, resumed, checkpoint_id)
        return _native_inflow(request, replay, resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed raw evidence could not be decoded without ambiguity.",
            "decode_evm_core",
            resumed,
            checkpoint_id,
        )


def _binding_error(
    request: EvmCoreAnalysisRequest,
    replay: (
        ObjectSummaryReplay
        | HistoricalBalanceReplay
        | FirstTokenTransferReplay
        | NativeInflowReplay
    ),
) -> tuple[str, str] | None:
    if not request.source_policy.offline_mode:
        return "rule_restricted", "TASK-012 currently executes reviewed replay only."
    if request.query_kind != replay.query_kind or request.chain_id != replay.chain_id:
        return "reconciliation_failed", "Request and replay query identity differ."
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return "reconciliation_failed", "Request and replay fixture IDs differ."
    if not {source.source_id for source in replay.sources} <= set(
        request.source_policy.allowed_source_ids
    ):
        return "rule_restricted", "Replay evidence uses a source outside the allowed policy."
    return None


def _object_summary(
    request: EvmCoreAnalysisRequest,
    replay: ObjectSummaryReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, ObjectSummaryInputs):
        raise TypeError
    tx = replay.transaction
    receipt = replay.receipt
    block = replay.block
    if (
        tx.hash != receipt.transaction_hash
        or tx.block_hash != receipt.block_hash
        or tx.block_number != receipt.block_number
        or tx.transaction_index != receipt.transaction_index
        or block.hash != tx.block_hash
        or block.number != tx.block_number
        or int(block.number, 16) != inputs.block_number
    ):
        raise ValueError
    codes = {item.address: item for item in replay.codes}
    if any(int(item.block_number, 16) != inputs.block_number for item in replay.codes):
        raise ValueError
    objects: list[dict[str, object]] = []
    missing_code = False
    for value in inputs.values:
        if isinstance(value, int):
            objects.append({"input": value, "classification": "block_number"})
        elif len(value) == 42 and value.startswith("0x"):
            normalized = to_normalized_address(value)
            item: dict[str, object] = {"input": value, "classification": "address"}
            code = codes.get(normalized)
            if code is None:
                missing_code = True
            else:
                item["account_kind"] = "eoa" if code.code == "0x" else "contract"
            objects.append(item)
        elif value == tx.hash:
            objects.append({"input": value, "classification": "transaction_hash"})
        elif value == block.hash:
            objects.append({"input": value, "classification": "block_hash"})
        else:
            objects.append({"input": value, "classification": "invalid"})

    value: dict[str, object] = {"objects": objects}
    if inputs.include_transaction_fee:
        value["fee_paid_wei"] = str(
            int(receipt.gas_used, 16) * int(receipt.effective_gas_price, 16)
        )
    evidence = [
        _evidence(
            replay,
            "EV-BASIC-EVM-TX",
            "state",
            "eth_getTransactionByHash",
            {
                "transaction_hash": tx.hash,
                "block_hash": tx.block_hash,
                "block_number": int(tx.block_number, 16),
            },
        ),
        _evidence(
            replay,
            "EV-BASIC-EVM-RECEIPT",
            "state",
            "eth_getTransactionReceipt",
            {
                "gas_used": str(int(receipt.gas_used, 16)),
                "effective_gas_price_wei": str(int(receipt.effective_gas_price, 16)),
            },
        ),
        _evidence(
            replay,
            "EV-BASIC-EVM-BLOCK",
            "state",
            "eth_getBlockByNumber",
            {
                "block_hash": block.hash,
                "block_number": int(block.number, 16),
                "timestamp": int(block.timestamp, 16),
            },
        ),
    ]
    evidence_id_counts: dict[str, int] = {}
    for index, code in enumerate(replay.codes):
        base_evidence_id = (
            "EV-BASIC-EVM-EOA-CODE" if code.code == "0x" else "EV-BASIC-EVM-CONTRACT-CODE"
        )
        evidence.append(
            _evidence(
                replay,
                _next_evidence_id(base_evidence_id, evidence_id_counts),
                "state",
                "eth_getCode",
                {"address": code.address, "code": code.code},
                source_index=min(index + 1, len(replay.sources) - 1),
            )
        )
    result = _result_item(
        "RES-EVM-OBJECT-SUMMARY",
        "object_summary",
        value,
        ["REQ-P0-EVM-001", "REQ-P0-EVM-002"],
        [
            "REQ-BASIC-EVM-OBJECT-TYPES",
            "REQ-BASIC-EVM-TX-SUMMARY",
            "REQ-BASIC-EVM-BLOCK-LINK",
        ],
        [item["evidence_id"] for item in evidence],
    )
    errors = []
    status = "complete"
    if missing_code:
        status = "partial"
        errors = [
            _error(
                "source_unavailable",
                "Historical code is unavailable for at least one address.",
                "historical_code",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _historical_balance(
    request: EvmCoreAnalysisRequest,
    replay: HistoricalBalanceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, HistoricalBalanceInputs):
        raise TypeError
    if (
        replay.subject_address != inputs.subject_address
        or int(replay.block.number, 16) != inputs.block_number
        or int(replay.block.timestamp, 16) != inputs.block_timestamp
    ):
        raise ValueError
    balances: list[dict[str, object]] = []
    evidence = [
        _evidence(
            replay,
            "EV-BASIC-STATE-BLOCK",
            "state",
            "eth_getBlockByNumber",
            {
                "block_number": inputs.block_number,
                "timestamp": inputs.block_timestamp,
            },
        )
    ]
    requested_native = any(asset.asset_type == "native" for asset in inputs.assets)
    if requested_native:
        native_symbol = next(
            asset.symbol for asset in inputs.assets if asset.asset_type == "native"
        )
        balances.append(
            {
                "symbol": native_symbol,
                "decimals": 18,
                "amount_raw": str(int(replay.native_balance, 16)),
            }
        )
        evidence.append(
            _evidence(
                replay,
                "EV-BASIC-STATE-ETH",
                "state",
                "eth_getBalance",
                {
                    "address": inputs.subject_address,
                    "amount_raw": str(int(replay.native_balance, 16)),
                },
            )
        )
    states = {item.token_address: item for item in replay.token_states}
    missing_tokens: list[str] = []
    evidence_id_counts: dict[str, int] = {}
    for asset in inputs.assets:
        if asset.asset_type != "erc20" or asset.token_address is MISSING:
            continue
        state = states.get(asset.token_address)
        if state is None:
            missing_tokens.append(asset.symbol)
            continue
        balance = str(int(state.balance_result, 16))
        decimals = int(state.decimals_result, 16)
        balances.append(
            {
                "symbol": asset.symbol,
                "token_address": asset.token_address,
                "decimals": decimals,
                "amount_raw": balance,
            }
        )
        evidence.extend(
            [
                _evidence(
                    replay,
                    _next_evidence_id(
                        f"EV-BASIC-STATE-{asset.symbol}-BALANCE",
                        evidence_id_counts,
                    ),
                    "state",
                    "eth_call",
                    {"token_address": asset.token_address, "amount_raw": balance},
                ),
                _evidence(
                    replay,
                    _next_evidence_id(
                        f"EV-BASIC-STATE-{asset.symbol}-DECIMALS",
                        evidence_id_counts,
                    ),
                    "state",
                    "eth_call",
                    {"token_address": asset.token_address, "decimals": decimals},
                ),
            ]
        )
    value = {
        "block_number": inputs.block_number,
        "block_timestamp": inputs.block_timestamp,
        "state_semantics": inputs.state_semantics,
        "balances": balances,
    }
    fixture_requirement_ids = ["REQ-BASIC-STATE-BLOCK"]
    if requested_native:
        fixture_requirement_ids.append("REQ-BASIC-STATE-NATIVE")
    if any(asset.asset_type == "erc20" for asset in inputs.assets):
        fixture_requirement_ids.append("REQ-BASIC-STATE-USDC")
    result = _result_item(
        "RES-EVM-HISTORICAL-BALANCE",
        "historical_balance",
        value,
        ["REQ-P0-EVM-004"],
        fixture_requirement_ids,
        [item["evidence_id"] for item in evidence],
    )
    errors = []
    status = "complete"
    if missing_tokens:
        status = "partial"
        errors = [
            _error(
                "archive_required",
                "Historical token state is unavailable.",
                "historical_token_state",
                [item["evidence_id"] for item in evidence],
                details={"missing_assets": missing_tokens},
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _first_token_transfer(
    request: EvmCoreAnalysisRequest,
    replay: FirstTokenTransferReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, FirstTokenTransferInputs):
        raise TypeError
    if (
        int(replay.start_block, 16) != inputs.start_block
        or int(replay.end_block, 16) < inputs.start_block
    ):
        raise ValueError
    matches = []
    for log in replay.logs:
        if (
            log.address == inputs.token_address
            and log.topics[0] == TRANSFER_TOPIC
            and len(log.topics) >= 3
            and _topic_address(log.topics[1]) == inputs.subject_address
            and int(log.block_number, 16) >= inputs.start_block
            and int(log.data, 16) > 0
        ):
            matches.append(log)
    matches.sort(
        key=lambda item: (
            int(item.block_number, 16),
            int(item.transaction_index, 16),
            int(item.log_index, 16),
        )
    )
    if not matches:
        return _failed(
            request,
            "source_unavailable",
            "No matching successful token transfer was found in the reviewed range.",
            "transfer_log_scan",
            resumed,
            checkpoint_id,
        )
    log = matches[0]
    value = {
        "range_complete": replay.range_complete,
        "transfer": {
            "transaction_hash": log.transaction_hash,
            "block_number": int(log.block_number, 16),
            "transaction_index": int(log.transaction_index, 16),
            "log_index": int(log.log_index, 16),
            "token_address": log.address,
            "from": _topic_address(log.topics[1]),
            "to": _topic_address(log.topics[2]),
            "amount_raw": str(int(log.data, 16)),
        },
    }
    evidence = [
        _evidence(
            replay,
            "EV-TOKEN-FIRST-RANGE",
            "state",
            "eth_getLogs",
            {
                "start_block": int(replay.start_block, 16),
                "end_block": int(replay.end_block, 16),
                "range_complete": replay.range_complete,
            },
        ),
        _evidence(
            replay,
            "EV-TOKEN-FIRST-TRANSFER",
            "event",
            "eth_getLogs",
            value["transfer"],
            transaction_hash=log.transaction_hash,
            log_index=int(log.log_index, 16),
        ),
    ]
    result = _result_item(
        "RES-EVM-FIRST-TOKEN-TRANSFER",
        "first_token_transfer",
        value,
        ["REQ-P0-EVM-005"],
        ["REQ-TOKEN-FIRST-ORDER", "REQ-TOKEN-FIRST-EVENT"],
        [item["evidence_id"] for item in evidence],
    )
    errors = []
    status = "complete"
    if not replay.range_complete:
        status = "partial"
        errors = [
            _error(
                "evidence_incomplete",
                "A matching transfer exists, but pagination does not prove it is first.",
                "range_pagination",
                ["EV-TOKEN-FIRST-TRANSFER"],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _native_inflow(
    request: EvmCoreAnalysisRequest,
    replay: NativeInflowReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, NativeInflowInputs):
        raise TypeError
    if replay.transaction.hash != inputs.transaction_hash:
        raise ValueError
    calls = [
        item
        for item in replay.internal_calls
        if item.transaction_hash == inputs.transaction_hash
        and item.to == inputs.interest_address
        and int(item.value) > 0
    ]
    value = {
        "top_level_value_wei": str(int(replay.transaction.value, 16)),
        "internal_inflow_wei": str(sum(int(item.value) for item in calls)),
        "successful_call_count": len(calls),
        "trace_complete": replay.trace_complete,
    }
    evidence = [
        _evidence(
            replay,
            "EV-TOKEN-INTERNAL-TX",
            "call",
            "eth_getTransactionByHash",
            {
                "transaction_hash": replay.transaction.hash,
                "top_level_value_wei": value["top_level_value_wei"],
            },
            transaction_hash=replay.transaction.hash,
        )
    ]
    for index, call in enumerate(calls, start=1):
        evidence_id = "EV-TOKEN-INTERNAL-ETH" if index == 1 else f"EV-TOKEN-INTERNAL-ETH-{index}"
        evidence.append(
            _evidence(
                replay,
                evidence_id,
                "call",
                "debug_traceTransaction",
                {
                    "from": call.from_address,
                    "to": call.to,
                    "amount_raw": call.value,
                },
                transaction_hash=call.transaction_hash,
                trace_address=[int(call.index)],
            )
        )
    result = _result_item(
        "RES-EVM-NATIVE-INFLOW",
        "native_inflow",
        value,
        ["REQ-P0-EVM-006"],
        ["REQ-TOKEN-INTERNAL-OUTER", "REQ-TOKEN-INTERNAL-INFLOW"],
        [item["evidence_id"] for item in evidence],
    )
    errors = []
    status = "complete"
    if not replay.trace_complete:
        status = "partial"
        errors = [
            _error(
                "trace_unavailable",
                "Top-level value is known, but the internal-call trace is incomplete.",
                "internal_call_trace",
                ["EV-TOKEN-INTERNAL-TX"],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _topic_address(topic: str) -> str:
    return to_normalized_address("0x" + topic[-40:])


def _next_evidence_id(base: str, counts: dict[str, int]) -> str:
    counts[base] = counts.get(base, 0) + 1
    return base if counts[base] == 1 else f"{base}-{counts[base]}"


def _result_item(
    result_id: str,
    result_type: str,
    value: dict[str, object],
    tool_requirement_ids: list[str],
    fixture_requirement_ids: list[str],
    evidence_refs: list[str],
) -> dict[str, object]:
    return {
        "result_id": result_id,
        "result_type": result_type,
        "classification": "confirmed_fact",
        "value": value,
        "tool_requirement_ids": tool_requirement_ids,
        "fixture_requirement_ids": fixture_requirement_ids,
        "evidence_refs": evidence_refs,
    }


def _evidence(
    replay: EvmCoreReplayDocument,
    evidence_id: str,
    evidence_type: str,
    method: str,
    decoded: dict[str, object],
    *,
    source_index: int = 0,
    transaction_hash: str | None = None,
    log_index: int | None = None,
    trace_address: list[int] | None = None,
) -> dict[str, object]:
    sources: list[EvmReplaySource] = replay.sources
    source = sources[source_index]
    locator: dict[str, object] = {"chain_id": replay.chain_id}
    if transaction_hash is not None:
        locator["transaction_hash"] = transaction_hash
    if log_index is not None:
        locator["log_index"] = log_index
    if trace_address is not None:
        locator["trace_address"] = trace_address
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "source_id": source.source_id,
        "source_record_ref": f"SRC-EVM-CORE-{source_index + 1}",
        "method": method,
        "retrieved_at": source.retrieved_at,
        "locator": locator,
        "decoded": decoded,
        "raw_artifact": {
            "artifact_uri": f"fixture://{replay.fixture_id}/raw-replay.json#{evidence_id}",
            "media_type": "application/json",
        },
    }


def _source_records(
    sources: list[EvmReplaySource],
    referenced_ids: set[str],
) -> list[dict[str, object]]:
    return [
        {
            "source_record_id": f"SRC-EVM-CORE-{index}",
            "source_id": source.source_id,
            "provider_id": source.provider_id,
            "role": "scoring",
            "required": True,
            "capability": "evm_core_replay",
            "endpoint_host": source.endpoint_host,
            "retrieved_at": source.retrieved_at,
        }
        for index, source in enumerate(sources, start=1)
        if f"SRC-EVM-CORE-{index}" in referenced_ids
    ]


def _error(
    code: str,
    message: str,
    stage: str,
    evidence_ids: list[str],
    *,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "error_id": f"ERR-EVM-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "attempt_count": 0,
    }
    if evidence_ids:
        value["related_evidence_ids"] = evidence_ids
    if details:
        value["details"] = details
    return value


def _result(
    request: EvmCoreAnalysisRequest,
    replay: EvmCoreReplayDocument,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    sources = replay.sources
    referenced = {str(item["source_record_ref"]) for item in evidence}
    finished_at = max([request.requested_at, *[source.retrieved_at for source in sources]])
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
            "sources": _source_records(sources, referenced),
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
    )


def _failed(
    request: EvmCoreAnalysisRequest,
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
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _run(
    started_at: datetime,
    finished_at: datetime,
    *,
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
