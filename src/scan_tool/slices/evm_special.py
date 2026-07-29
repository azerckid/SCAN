"""Deterministic TASK-013 NFT/Proxy replay analyzers.

Independently re-derives raw facts from reviewed replay evidence. This module
does not import the TASK-013 fixture verifier (``task_013_independent_verifier``);
the two must reach the same conclusion from separate code paths.
"""

from datetime import datetime

from eth_abi import decode
from eth_abi.exceptions import DecodingError
from eth_utils import to_normalized_address
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import (
    EvmSpecialAnalysisRequest,
    NftActivityInputs,
    ProxyHistoryInputs,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.evm_special import (
    BlockWindow,
    EvmSpecialReplayDocument,
    EvmSpecialReplaySource,
    NftActivityReplay,
    ProxyHistoryReplay,
    SpecialLog,
    SpecialReceipt,
    parse_evm_special_replay,
)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_FOR_ALL_TOPIC = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
TRANSFER_SINGLE_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
TRANSFER_BATCH_TOPIC = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
UPGRADED_TOPIC = "0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b"
IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
ZERO_ADDRESS = "0x" + ("0" * 40)


class _DecodeFailure(Exception):
    """A specific, named TASK-013 decode failure code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def analyze_evm_special_replay(
    request: EvmSpecialAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-EVM-SPECIAL-REPLAY-EVIDENCE",
) -> AnalysisResult:
    """Run one approved NFT/Proxy query over reviewed raw replay evidence."""
    try:
        replay = parse_evm_special_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed replay package does not match the raw evidence contract.",
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
        if isinstance(replay, NftActivityReplay):
            return _nft_activity(request, replay, resumed, checkpoint_id)
        return _proxy_history(request, replay, resumed, checkpoint_id)
    except _DecodeFailure as error:
        return _failed(
            request,
            error.code,
            error.message,
            "decode_evm_special",
            resumed,
            checkpoint_id,
        )
    except (KeyError, TypeError, ValueError, OverflowError, DecodingError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed raw evidence could not be decoded without ambiguity.",
            "decode_evm_special",
            resumed,
            checkpoint_id,
        )


def _binding_error(
    request: EvmSpecialAnalysisRequest,
    replay: EvmSpecialReplayDocument,
) -> tuple[str, str] | None:
    if not request.source_policy.offline_mode:
        return "rule_restricted", "TASK-013 currently executes reviewed replay only."
    if request.chain_id != replay.chain_id:
        return "reconciliation_failed", "Request and replay chain identity differ."
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return "reconciliation_failed", "Request and replay fixture IDs differ."
    inputs = request.inputs
    if isinstance(replay, NftActivityReplay) != isinstance(inputs, NftActivityInputs):
        return "reconciliation_failed", "Request query_kind and replay shape differ."
    if not {source.source_id for source in replay.sources} <= set(
        request.source_policy.allowed_source_ids
    ):
        return "rule_restricted", "Replay evidence uses a source outside the allowed policy."
    return None


def _nft_activity(
    request: EvmSpecialAnalysisRequest,
    replay: NftActivityReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, NftActivityInputs):
        raise TypeError
    if inputs.standard_hint != "auto" and inputs.standard_hint != replay.standard_hint:
        raise _DecodeFailure(
            "decode_failed",
            "Requested standard hint does not match the replay's declared standard.",
        )
    logs = _require_single_contract(replay.logs, inputs.token_contract)
    receipts_by_hash = _require_unique_receipts(replay.receipts)
    for log in logs:
        _require_matching_receipt(log, receipts_by_hash)
    _require_exact_block_windows(replay.scope.block_windows, replay.receipts)
    scope_complete = (
        replay.scope.selected_transactions_complete and replay.scope.exact_block_windows_complete
    )
    if replay.standard_hint == "erc721":
        return _erc721(request, replay, logs, scope_complete, resumed, checkpoint_id)
    return _erc1155(request, replay, logs, scope_complete, resumed, checkpoint_id)


def _erc721(
    request: EvmSpecialAnalysisRequest,
    replay: NftActivityReplay,
    logs: list[SpecialLog],
    scope_complete: bool,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, NftActivityInputs)
    subject = inputs.subject_address
    evidence_id_counts: dict[str, int] = {}
    evidence = []

    all_transfers = [
        _require_erc721_event(log, expected_topics=4) for log in _find_logs(logs, TRANSFER_TOPIC)
    ]
    subject_transfers = sorted(
        (
            log
            for log in all_transfers
            if subject in (_topic_address(log.topics[1]), _topic_address(log.topics[2]))
        ),
        key=_log_sort_key,
    )
    if not subject_transfers:
        return _failed(
            request,
            "source_unavailable",
            "No ERC-721 Transfer event for the requested subject_address is present "
            "in the reviewed replay.",
            "erc721_transfer_scan",
            resumed,
            checkpoint_id,
        )

    movements: list[dict[str, object]] = []
    token_ids: set[str] = set()
    for transfer in subject_transfers:
        token_id = str(_hex_int(transfer.topics[3]))
        token_ids.add(token_id)
        movement = {
            "event_kind": "transfer",
            **_log_location(transfer),
            "from": _topic_address(transfer.topics[1]),
            "to": _topic_address(transfer.topics[2]),
            "token_id_raw": token_id,
            "amount_raw": "1",
            "amount_origin": "normalized_unit",
        }
        movements.append(movement)
        evidence.append(
            _evidence(
                replay.sources,
                _next_evidence_id("EV-NFT721-TRANSFER", evidence_id_counts),
                "event",
                "eth_getLogs",
                {
                    "topic0": TRANSFER_TOPIC,
                    "transaction_hash": movement["transaction_hash"],
                    "block_number": movement["block_number"],
                    "log_index": movement["log_index"],
                    "from": movement["from"],
                    "to": movement["to"],
                    "token_id_raw": token_id,
                },
            )
        )

    approvals: list[dict[str, object]] = []
    operator_logs: list[SpecialLog] = []
    token_logs: list[SpecialLog] = []
    if inputs.include_approvals:
        operator_logs = [
            _require_erc721_event(log, expected_topics=3, expect_empty_data=False)
            for log in _find_logs(logs, APPROVAL_FOR_ALL_TOPIC)
            if _topic_address(log.topics[1]) == subject
        ]
        token_logs = [
            _require_erc721_event(log, expected_topics=4)
            for log in _find_logs(logs, APPROVAL_TOPIC)
            if _topic_address(log.topics[1]) == subject
            and str(_hex_int(log.topics[3])) in token_ids
        ]
        for operator in sorted(operator_logs, key=_log_sort_key):
            entry = {
                "event_kind": "approval_for_all",
                **_log_location(operator),
                "owner": _topic_address(operator.topics[1]),
                "operator": _topic_address(operator.topics[2]),
                "approved": _data_bool(operator),
            }
            approvals.append(entry)
            evidence.append(
                _evidence(
                    replay.sources,
                    _next_evidence_id("EV-NFT721-OPERATOR-APPROVAL", evidence_id_counts),
                    "event",
                    "eth_getLogs",
                    {
                        "topic0": APPROVAL_FOR_ALL_TOPIC,
                        **{
                            key: entry[key]
                            for key in (
                                "transaction_hash",
                                "block_number",
                                "log_index",
                                "owner",
                                "operator",
                                "approved",
                            )
                        },
                    },
                )
            )
        for token_approval in sorted(token_logs, key=_log_sort_key):
            approved_address = _topic_address(token_approval.topics[2])
            entry = {
                "event_kind": "token_approval",
                **_log_location(token_approval),
                "owner": _topic_address(token_approval.topics[1]),
                "approved_address": approved_address,
                "token_id_raw": str(_hex_int(token_approval.topics[3])),
                "meaning": (
                    "approval_reset" if approved_address == ZERO_ADDRESS else "approval_set"
                ),
            }
            approvals.append(entry)
            evidence.append(
                _evidence(
                    replay.sources,
                    _next_evidence_id("EV-NFT721-TOKEN-APPROVAL-RESET", evidence_id_counts),
                    "event",
                    "eth_getLogs",
                    {
                        "topic0": APPROVAL_TOPIC,
                        **{
                            key: entry[key]
                            for key in (
                                "transaction_hash",
                                "block_number",
                                "log_index",
                                "owner",
                                "approved_address",
                                "token_id_raw",
                            )
                        },
                    },
                    source_index=1,
                )
            )
        approvals.sort(key=lambda item: (item["block_number"], item["log_index"]))

    missing_approvals = inputs.include_approvals and (not operator_logs or not token_logs)
    value: dict[str, object] = {"standard": "erc721", "movements": movements}
    if inputs.include_approvals:
        value["approvals"] = approvals
    result = _result_item(
        "RES-EVM-SPECIAL-NFT-ACTIVITY",
        "nft_activity",
        value,
        ["REQ-P0-EVM-001"],
        ["REQ-NFT721-TRANSFER", *(["REQ-NFT721-APPROVALS"] if inputs.include_approvals else [])],
        [item["evidence_id"] for item in evidence],
    )
    errors: list[dict[str, object]] = []
    status = "complete"
    if not scope_complete or missing_approvals:
        status = "partial"
        errors = [
            _error(
                "source_unavailable",
                "Approval completeness could not be established in the explicit selected scope.",
                "erc721_approval_scope",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _erc1155(
    request: EvmSpecialAnalysisRequest,
    replay: NftActivityReplay,
    logs: list[SpecialLog],
    scope_complete: bool,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, NftActivityInputs)
    subject = inputs.subject_address
    evidence_id_counts: dict[str, int] = {}
    all_singles = _find_logs(logs, TRANSFER_SINGLE_TOPIC)
    for log in all_singles:
        _require_erc1155_single(log)
    singles = sorted(
        (
            log
            for log in all_singles
            if subject in (_topic_address(log.topics[2]), _topic_address(log.topics[3]))
        ),
        key=_log_sort_key,
    )
    approvals_logs = sorted(
        (
            log
            for log in _find_logs(logs, APPROVAL_FOR_ALL_TOPIC)
            if _topic_address(log.topics[1]) == subject
        ),
        key=_log_sort_key,
    )
    all_batches = _find_logs(logs, TRANSFER_BATCH_TOPIC)
    for log in all_batches:
        if len(log.topics) != 4:
            raise _DecodeFailure("decode_failed", "ERC-1155 Batch topic count differs.")
    batches = [
        log
        for log in all_batches
        if subject in (_topic_address(log.topics[2]), _topic_address(log.topics[3]))
    ]
    if len(batches) > 1:
        raise _DecodeFailure("decode_failed", "More than one ERC-1155 Batch was selected.")
    if not singles and not batches:
        return _failed(
            request,
            "source_unavailable",
            "No ERC-1155 Single or Batch transfer event for the requested subject_address "
            "or token contract is present in the reviewed replay.",
            "erc1155_transfer_scan",
            resumed,
            checkpoint_id,
        )

    evidence = []
    value: dict[str, object] = {"standard": "erc1155"}

    single_case_missing = not singles
    if singles:
        outgoing = singles[-1]
        single_case = {
            "transaction_hash": outgoing.transaction_hash,
            "block_number": _hex_int(outgoing.block_number),
            "token_id_raw": str(_data_word(outgoing, 0)),
            "amount_raw": str(_data_word(outgoing, 1)),
            "selected_outgoing_log_index": _hex_int(outgoing.log_index),
            "from": _topic_address(outgoing.topics[2]),
            "to": _topic_address(outgoing.topics[3]),
        }
        if inputs.include_approvals:
            single_case["approval_transitions"] = [
                {"log_index": _hex_int(item.log_index), "approved": _data_bool(item)}
                for item in approvals_logs
            ]
        value["single_case"] = single_case
        for item in singles:
            is_outgoing = item is outgoing
            evidence.append(
                _evidence(
                    replay.sources,
                    _next_evidence_id(
                        "EV-NFT1155-SINGLE-OUT" if is_outgoing else "EV-NFT1155-SINGLE-IN",
                        evidence_id_counts,
                    ),
                    "event",
                    "eth_getLogs",
                    {
                        **({} if is_outgoing else {"topic0": TRANSFER_SINGLE_TOPIC}),
                        **_log_location(item),
                        "from": _topic_address(item.topics[2]),
                        "to": _topic_address(item.topics[3]),
                        "token_id_raw": str(_data_word(item, 0)),
                        "amount_raw": str(_data_word(item, 1)),
                    },
                )
            )
        if inputs.include_approvals:
            for item in approvals_logs:
                approved = _data_bool(item)
                evidence.append(
                    _evidence(
                        replay.sources,
                        _next_evidence_id(
                            "EV-NFT1155-APPROVAL-TRUE" if approved else "EV-NFT1155-APPROVAL-FALSE",
                            evidence_id_counts,
                        ),
                        "event",
                        "eth_getLogs",
                        {
                            **_log_location(item),
                            "owner": _topic_address(item.topics[1]),
                            "operator": _topic_address(item.topics[2]),
                            "approved": approved,
                        },
                    )
                )

    batch_case_missing = not batches
    if batches:
        batch = batches[0]
        if len(batch.topics) != 4:
            raise _DecodeFailure("decode_failed", "ERC-1155 Batch topic count differs.")
        try:
            ids, amounts = decode(
                ["uint256[]", "uint256[]"],
                bytes.fromhex(batch.data.removeprefix("0x")),
            )
        except (DecodingError, ValueError) as error:
            raise _DecodeFailure("decode_failed", "ERC-1155 Batch ABI is malformed.") from error
        if len(ids) != len(amounts):
            raise _DecodeFailure(
                "decode_failed",
                "ERC-1155 Batch ids and amounts arrays have different lengths.",
            )
        batch_case = {
            **_log_location(batch),
            "operator": _topic_address(batch.topics[1]),
            "from": _topic_address(batch.topics[2]),
            "to": _topic_address(batch.topics[3]),
            "ids_raw": [str(item) for item in ids],
            "amounts_raw": [str(item) for item in amounts],
        }
        value["batch_case"] = batch_case
        evidence.append(
            _evidence(
                replay.sources,
                "EV-NFT1155-BATCH",
                "event",
                "eth_getLogs",
                {
                    "topic0": TRANSFER_BATCH_TOPIC,
                    **_log_location(batch),
                    "ids_raw": batch_case["ids_raw"],
                    "amounts_raw": batch_case["amounts_raw"],
                },
                source_index=1,
            )
        )

    requirement_ids = []
    if not single_case_missing:
        requirement_ids.append("REQ-NFT1155-SINGLE-APPROVAL")
    if not batch_case_missing:
        requirement_ids.append("REQ-NFT1155-BATCH")
    result = _result_item(
        "RES-EVM-SPECIAL-NFT-ACTIVITY",
        "nft_activity",
        value,
        ["REQ-P0-EVM-001"],
        requirement_ids,
        [item["evidence_id"] for item in evidence],
    )
    errors: list[dict[str, object]] = []
    status = "complete"
    if not scope_complete:
        status = "partial"
        errors = [
            _error(
                "source_unavailable",
                "Selected scope is incomplete; the resolved single/batch case is preserved.",
                "erc1155_case_scope",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _proxy_history(
    request: EvmSpecialAnalysisRequest,
    replay: ProxyHistoryReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    if not isinstance(inputs, ProxyHistoryInputs):
        raise TypeError
    if inputs.pattern_hint != "auto" and inputs.pattern_hint != "eip1967":
        raise _DecodeFailure("decode_failed", "Requested proxy pattern is unsupported.")

    all_upgraded_logs = _find_logs(replay.logs, UPGRADED_TOPIC)
    upgraded_logs = [
        log for log in all_upgraded_logs if _to_address(log.address) == inputs.proxy_address
    ]
    if len(upgraded_logs) > 1:
        raise _DecodeFailure("reconciliation_failed", "More than one Upgraded event was selected.")
    if not upgraded_logs:
        return _failed(
            request,
            "source_unavailable",
            "No Upgraded event for the requested proxy_address is present in the reviewed replay.",
            "proxy_event_scan",
            resumed,
            checkpoint_id,
        )
    upgraded = upgraded_logs[0]
    if len(upgraded.topics) != 2:
        raise _DecodeFailure("decode_failed", "Upgraded topic count differs.")
    proxy_address = _to_address(upgraded.address)
    event_implementation = _topic_address(upgraded.topics[1])
    event_block = _hex_int(upgraded.block_number)

    if (
        replay.receipt.transaction_hash != upgraded.transaction_hash
        or _hex_int(replay.receipt.block_number) != event_block
    ):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Upgraded event does not match the reviewed replay's receipt.",
        )

    snapshots = {item.role: item for item in replay.storage_snapshots}
    scope_complete = (
        replay.scope.upgrade_transaction_complete and replay.scope.adjacent_state_complete
    )

    change: dict[str, object] | None = None
    implementation_missing = False
    before_snapshot = snapshots.get("implementation_before")
    after_snapshot = snapshots.get("implementation_after")
    if after_snapshot is not None:
        if after_snapshot.slot != IMPLEMENTATION_SLOT:
            raise _DecodeFailure("reconciliation_failed", "Implementation slot differs.")
        if _hex_int(after_snapshot.block_number) != event_block:
            raise _DecodeFailure(
                "reconciliation_failed",
                "After-state implementation snapshot block differs from the Upgraded event block.",
            )
        after_address = _word_address(after_snapshot.raw_word)
        if after_address != event_implementation:
            raise _DecodeFailure(
                "reconciliation_failed",
                "Upgraded event and after-state implementation differ.",
            )
        change = {
            **_log_location(upgraded),
            "after_implementation": after_address,
            "event_implementation": event_implementation,
        }
        if before_snapshot is not None:
            if before_snapshot.slot != IMPLEMENTATION_SLOT:
                raise _DecodeFailure("reconciliation_failed", "Implementation slot differs.")
            if _hex_int(before_snapshot.block_number) != event_block - 1:
                raise _DecodeFailure(
                    "reconciliation_failed",
                    "Before-state implementation snapshot is not the block adjacent to "
                    "the Upgraded event.",
                )
            change["before_implementation"] = _word_address(before_snapshot.raw_word)
        else:
            implementation_missing = True
    else:
        implementation_missing = True

    admin: dict[str, object] | None = None
    admin_missing = False
    if inputs.include_admin:
        admin_before = snapshots.get("admin_before")
        admin_after = snapshots.get("admin_after")
        if admin_after is not None and admin_before is not None:
            if admin_before.slot != ADMIN_SLOT or admin_after.slot != ADMIN_SLOT:
                raise _DecodeFailure("reconciliation_failed", "Admin slot differs.")
            if (
                _hex_int(admin_after.block_number) != event_block
                or _hex_int(admin_before.block_number) != event_block - 1
            ):
                raise _DecodeFailure(
                    "reconciliation_failed",
                    "Admin snapshot blocks are not adjacent to the Upgraded event block.",
                )
            before_admin = _word_address(admin_before.raw_word)
            after_admin = _word_address(admin_after.raw_word)
            admin = {
                "slot": ADMIN_SLOT,
                "before": before_admin,
                "after": after_admin,
                "change": "not_applicable" if before_admin == after_admin else "changed",
            }
        else:
            admin_missing = True

    # Beacon-path decoding is not implemented in this version;
    # ProxyHistoryInputs.include_beacon is restricted to False so this is
    # always the honest answer rather than an unverified "applicable: True".
    beacon: dict[str, object] = {"applicable": False}

    evidence = [
        _evidence(
            replay.sources,
            "EV-PROXY-UPGRADED",
            "event",
            "eth_getLogs",
            {
                "topic0": UPGRADED_TOPIC,
                **_log_location(upgraded),
                "implementation": event_implementation,
            },
        )
    ]
    if change is not None:
        evidence.append(
            _evidence(
                replay.sources,
                "EV-PROXY-IMPLEMENTATION-AFTER",
                "state",
                "eth_getStorageAt",
                {
                    "block_number": _hex_int(after_snapshot.block_number),  # type: ignore[union-attr]
                    "slot": IMPLEMENTATION_SLOT,
                    "raw_word": after_snapshot.raw_word,  # type: ignore[union-attr]
                },
            )
        )
        if "before_implementation" in change:
            evidence.append(
                _evidence(
                    replay.sources,
                    "EV-PROXY-IMPLEMENTATION-BEFORE",
                    "state",
                    "eth_getStorageAt",
                    {
                        "block_number": _hex_int(before_snapshot.block_number),  # type: ignore[union-attr]
                        "slot": IMPLEMENTATION_SLOT,
                        "raw_word": before_snapshot.raw_word,  # type: ignore[union-attr]
                    },
                )
            )
    if admin is not None:
        evidence.append(
            _evidence(
                replay.sources,
                "EV-PROXY-ADMIN-BEFORE",
                "state",
                "eth_getStorageAt",
                {
                    "block_number": _hex_int(admin_before.block_number),  # type: ignore[union-attr]
                    "slot": ADMIN_SLOT,
                    "raw_word": admin_before.raw_word,  # type: ignore[union-attr]
                },
            )
        )
        evidence.append(
            _evidence(
                replay.sources,
                "EV-PROXY-ADMIN-AFTER",
                "state",
                "eth_getStorageAt",
                {
                    "block_number": _hex_int(admin_after.block_number),  # type: ignore[union-attr]
                    "slot": ADMIN_SLOT,
                    "raw_word": admin_after.raw_word,  # type: ignore[union-attr]
                },
                source_index=1,
            )
        )

    value: dict[str, object] = {
        "pattern": "eip1967_direct_implementation",
        "proxy_address": proxy_address,
        "implementation_slot": IMPLEMENTATION_SLOT,
    }
    if change is not None:
        value["change"] = change
    if admin is not None:
        value["admin"] = admin
    value["beacon"] = beacon

    requirement_ids = ["REQ-PROXY-UPGRADE-EVENT"]
    if not implementation_missing:
        requirement_ids.append("REQ-PROXY-HISTORICAL-SLOT")
    if admin is not None:
        requirement_ids.append("REQ-PROXY-ADMIN-SEPARATION")
    result = _result_item(
        "RES-EVM-SPECIAL-PROXY-HISTORY",
        "proxy_history",
        value,
        ["REQ-P0-EVM-001"],
        requirement_ids,
        [item["evidence_id"] for item in evidence],
    )
    errors: list[dict[str, object]] = []
    status = "complete"
    if not scope_complete or implementation_missing or (inputs.include_admin and admin_missing):
        status = "partial"
        errors = [
            _error(
                "archive_required",
                "One historical storage block is unavailable while the confirmed change is preserved.",
                "proxy_historical_slot",
                [item["evidence_id"] for item in evidence],
                retryable=True,
            )
        ]
    return _result(request, replay, status, [result], evidence, errors, resumed, checkpoint_id)


def _require_single_contract(logs: list[SpecialLog], token_contract: str) -> list[SpecialLog]:
    contracts = {log.address for log in logs}
    if len(contracts) != 1 or next(iter(contracts)) != token_contract:
        raise _DecodeFailure(
            "decode_failed",
            "Selected logs do not belong to the requested token contract.",
        )
    return logs


def _require_unique_receipts(receipts: list[SpecialReceipt]) -> dict[str, SpecialReceipt]:
    by_hash: dict[str, SpecialReceipt] = {}
    for receipt in receipts:
        if receipt.transaction_hash in by_hash:
            raise _DecodeFailure(
                "decode_failed",
                "Selected receipts contain a duplicate transaction hash.",
            )
        by_hash[receipt.transaction_hash] = receipt
    return by_hash


def _require_matching_receipt(
    log: SpecialLog,
    receipts_by_hash: dict[str, SpecialReceipt],
) -> None:
    receipt = receipts_by_hash.get(log.transaction_hash)
    if receipt is None or receipt.block_number != log.block_number:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Selected log does not match a receipt in the reviewed replay scope.",
        )


def _require_exact_block_windows(
    windows: list[BlockWindow],
    receipts: list[SpecialReceipt],
) -> None:
    window_blocks: list[int] = []
    for window in windows:
        from_block = _hex_int(window.from_block)
        to_block = _hex_int(window.to_block)
        if from_block != to_block:
            raise _DecodeFailure(
                "reconciliation_failed",
                "NFT replay block windows must each identify one exact block.",
            )
        window_blocks.append(from_block)
    receipt_blocks = [_hex_int(receipt.block_number) for receipt in receipts]
    if len(window_blocks) != len(set(window_blocks)) or set(window_blocks) != set(receipt_blocks):
        raise _DecodeFailure(
            "reconciliation_failed",
            "NFT replay block windows differ from the selected receipt blocks.",
        )


def _next_evidence_id(base: str, counts: dict[str, int]) -> str:
    counts[base] = counts.get(base, 0) + 1
    return base if counts[base] == 1 else f"{base}-{counts[base]}"


def _find_logs(logs: list[SpecialLog], topic0: str) -> list[SpecialLog]:
    return [log for log in logs if log.topics[0].lower() == topic0]


def _require_erc721_event(
    log: SpecialLog, *, expected_topics: int, expect_empty_data: bool = True
) -> SpecialLog:
    if len(log.topics) != expected_topics:
        raise _DecodeFailure("decode_failed", "ERC-721 event topic count differs.")
    if expect_empty_data and log.data != "0x":
        raise _DecodeFailure("decode_failed", "ERC-721 indexed values must not be read from data.")
    return log


def _require_erc1155_single(log: SpecialLog) -> None:
    if len(log.topics) != 4:
        raise _DecodeFailure("decode_failed", "ERC-1155 TransferSingle topic count differs.")


def _data_bool(log: SpecialLog) -> bool:
    return bool(_data_word(log, 0))


def _data_word(log: SpecialLog, index: int) -> int:
    body = log.data.removeprefix("0x")
    start = index * 64
    word = body[start : start + 64]
    if len(word) != 64:
        raise _DecodeFailure("decode_failed", "Event data word is truncated.")
    return int(word, 16)


def _topic_address(topic: str) -> str:
    return to_normalized_address("0x" + topic[-40:])


def _word_address(word: str) -> str:
    body = word.removeprefix("0x")
    if len(body) < 40:
        raise _DecodeFailure("reconciliation_failed", "Storage word is truncated.")
    return to_normalized_address("0x" + body[-40:])


def _to_address(value: str) -> str:
    return to_normalized_address(value)


def _hex_int(value: str) -> int:
    return int(value, 16)


def _log_location(log: SpecialLog) -> dict[str, object]:
    return {
        "transaction_hash": log.transaction_hash,
        "block_number": _hex_int(log.block_number),
        "log_index": _hex_int(log.log_index),
    }


def _log_sort_key(log: SpecialLog) -> tuple[int, int, int]:
    return (
        _hex_int(log.block_number),
        _hex_int(log.transaction_index),
        _hex_int(log.log_index),
    )


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
    sources: list[EvmSpecialReplaySource],
    evidence_id: str,
    evidence_type: str,
    method: str,
    decoded: dict[str, object],
    *,
    source_index: int = 0,
) -> dict[str, object]:
    source = sources[min(source_index, len(sources) - 1)]
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "source_id": source.source_id,
        "source_record_ref": f"SRC-EVM-SPECIAL-{min(source_index, len(sources) - 1) + 1}",
        "method": method,
        "retrieved_at": source.retrieved_at,
        "locator": {"chain_id": 1},
        "decoded": decoded,
        "raw_artifact": {
            "artifact_uri": f"fixture://evm-special/raw-replay.json#{evidence_id}",
            "media_type": "application/json",
        },
    }


def _source_records(
    sources: list[EvmSpecialReplaySource],
    referenced_ids: set[str],
) -> list[dict[str, object]]:
    return [
        {
            "source_record_id": f"SRC-EVM-SPECIAL-{index}",
            "source_id": source.source_id,
            "provider_id": source.provider_id,
            "role": "scoring",
            "required": True,
            "capability": "evm_special_replay",
            "endpoint_host": "reviewed.replay.invalid",
            "retrieved_at": source.retrieved_at,
        }
        for index, source in enumerate(sources, start=1)
        if f"SRC-EVM-SPECIAL-{index}" in referenced_ids
    ]


def _error(
    code: str,
    message: str,
    stage: str,
    evidence_ids: list[str],
    *,
    retryable: bool = False,
) -> dict[str, object]:
    value: dict[str, object] = {
        "error_id": f"ERR-EVM-SPECIAL-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "attempt_count": 0,
    }
    if evidence_ids:
        value["related_evidence_ids"] = evidence_ids
    return value


def _result(
    request: EvmSpecialAnalysisRequest,
    replay: EvmSpecialReplayDocument,
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
    request: EvmSpecialAnalysisRequest,
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
