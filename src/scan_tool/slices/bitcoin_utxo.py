"""Deterministic offline Bitcoin UTXO analyzer."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import (
    BitcoinQueryKind,
    BitcoinUtxoAnalysisRequest,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.bitcoin_utxo import (
    BitcoinProviderObservation,
    BitcoinSpendHop,
    BitcoinUtxoReplay,
    assess_bitcoin_heuristics,
    parse_bitcoin_utxo_replay,
    reconstruct_bitcoin_facts,
)

REQUIRED_SOURCE_IDS = {"DS-BTC-NODE", "DS-BTC-API"}


def analyze_bitcoin_utxo_replay(
    request: BitcoinUtxoAnalysisRequest,
    raw_replay: bytes,
    *,
    package_dir: Path,
    resumed: bool = False,
    checkpoint_id: str | None = "CP-BITCOIN-UTXO-REPLAY",
) -> AnalysisResult:
    try:
        replay = parse_bitcoin_utxo_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(request, "decode_failed", "Bitcoin replay is invalid.", "decode_replay")
    binding = _binding_error(request, replay)
    if binding is not None:
        return _failed(request, *binding)

    artifact_error = _artifact_error(package_dir, replay)
    if artifact_error is not None:
        return _failed(request, *artifact_error)
    facts = reconstruct_bitcoin_facts(
        replay,
        start_vout=request.inputs.start_vout,
        max_hops=request.inputs.max_hops,
    )
    evidence = _evidence(replay)
    results = [
        {
            "result_id": "RES-BTC-UTXO-SUMMARY",
            "result_type": "bitcoin_utxo_summary",
            "classification": "confirmed_fact",
            "value": facts,
            "tool_requirement_ids": ["REQ-P0-BTC-001"],
            "fixture_requirement_ids": ["REQ-BTC-PREVOUT", "REQ-BTC-FEE"],
            "evidence_refs": [item["evidence_id"] for item in evidence],
        }
    ]
    if request.query_kind is BitcoinQueryKind.ASSESS_HEURISTICS:
        results.append(
            {
                "result_id": "RES-BTC-HEURISTIC-ASSESSMENT",
                "result_type": "bitcoin_heuristic_assessment",
                "classification": "heuristic",
                "value": assess_bitcoin_heuristics(replay),
                "tool_requirement_ids": ["REQ-P0-BTC-001"],
                "fixture_requirement_ids": ["REQ-BTC-HEURISTIC"],
                "evidence_refs": [item["evidence_id"] for item in evidence],
            }
        )
    return _result(request, replay, results, evidence, resumed, checkpoint_id)


def _binding_error(
    request: BitcoinUtxoAnalysisRequest,
    replay: BitcoinUtxoReplay,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return ("rule_restricted", "Bitcoin v1 requires reviewed offline replay.", "rule_check")
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return ("reconciliation_failed", "Request and replay fixture IDs differ.", "fixture")
    if request.inputs.transaction_id != replay.transaction.transaction_id:
        return ("reconciliation_failed", "Request and replay transaction IDs differ.", "txid")
    if request.inputs.network != replay.transaction.network:
        return ("reconciliation_failed", "Request and replay networks differ.", "network")
    if request.inputs.start_vout not in {item.vout for item in replay.transaction.outputs}:
        return (
            "invalid_input",
            "Requested Bitcoin start_vout does not exist.",
            "start_outpoint",
        )
    if not set(request.source_policy.allowed_source_ids) >= REQUIRED_SOURCE_IDS:
        return ("rule_restricted", "Approved Bitcoin node and API sources are required.", "source")
    if set(replay.source_ids) != set(request.source_policy.allowed_source_ids):
        return ("rule_restricted", "Replay and request source sets differ.", "source_binding")
    return None


def _artifact_error(
    package_dir: Path,
    replay: BitcoinUtxoReplay,
) -> tuple[str, str, str] | None:
    root = package_dir.resolve()
    try:
        root_artifacts = {
            item.provider_id: _read_provider_artifact(root, item)
            for item in replay.transaction.providers
        }
        primary = _publicnode_projection(root_artifacts["publicnode.bitcoin"])
        verify = _rest_transaction_projection(root_artifacts["mempool.space"])
        if "blockstream.info" in root_artifacts:
            supporting = _rest_transaction_projection(root_artifacts["blockstream.info"])
            if verify != supporting:
                raise ValueError("root supporting projection differs from verify")
        if verify != _replay_transaction_projection(replay):
            raise ValueError("root replay differs from provider artifacts")
        if primary != _publicnode_replay_projection(replay):
            raise ValueError("PublicNode projection differs from replay")

        derived_hops: list[dict[str, object]] = []
        for hop in replay.spend_path:
            hop_artifacts = {
                item.provider_id: _read_provider_artifact(root, item) for item in hop.providers
            }
            primary_hop = _publicnode_hop_projection(
                hop_artifacts["publicnode.bitcoin"],
                replay,
                hop.spent_transaction_id,
                hop.spent_vout,
            )
            verify_hop = _rest_hop_projection(
                hop_artifacts["mempool.space"],
                hop.spent_transaction_id,
                hop.spent_vout,
            )
            if _publicnode_hop_comparable(primary_hop) != _rest_hop_public_projection(verify_hop):
                raise ValueError("PublicNode spend projection differs from verify")
            if "blockstream.info" in hop_artifacts:
                supporting_hop = _rest_hop_projection(
                    hop_artifacts["blockstream.info"],
                    hop.spent_transaction_id,
                    hop.spent_vout,
                )
                if verify_hop != supporting_hop:
                    raise ValueError("spend supporting projection differs from verify")
            if verify_hop != _replay_hop_projection(hop):
                raise ValueError("spend replay differs from provider artifacts")
            derived_hops.append(verify_hop)
        _validate_artifact_path(verify, derived_hops)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return (
            "reconciliation_failed",
            "Bitcoin replay differs from reviewed provider artifacts.",
            "artifact_reconciliation",
        )
    return None


def _read_provider_artifact(
    root: Path,
    provider: BitcoinProviderObservation,
) -> dict[str, object]:
    artifact_file = str(provider.artifact_file)
    artifact_sha256 = str(provider.artifact_sha256)
    path = (root / artifact_file).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("provider artifact missing")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != artifact_sha256:
        raise ValueError("provider artifact hash mismatch")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("provider artifact must be an object")
    return value


def _rest_transaction_projection(body: dict[str, object]) -> dict[str, object]:
    status = _object(body["status"])
    inputs = [_object(item) for item in _list(body["vin"])]
    outputs = [_object(item) for item in _list(body["vout"])]
    return {
        "transaction_id": str(body["txid"]),
        "block_height": int(status["block_height"]),
        "block_hash": str(status["block_hash"]),
        "block_time": int(status["block_time"]),
        "fee_sat": int(body["fee"]),
        "inputs": [
            {
                "prevout": {
                    "transaction_id": str(item["txid"]),
                    "vout": int(item["vout"]),
                    "value_sat": int(_object(item["prevout"])["value"]),
                    "script_type": str(_object(item["prevout"])["scriptpubkey_type"]),
                    "address": str(_object(item["prevout"])["scriptpubkey_address"]),
                },
                "sequence": int(item["sequence"]),
            }
            for item in inputs
        ],
        "outputs": [
            {
                "vout": index,
                "value_sat": int(item["value"]),
                "script_type": str(item["scriptpubkey_type"]),
                "address": str(item["scriptpubkey_address"]),
            }
            for index, item in enumerate(outputs)
        ],
    }


def _rest_hop_projection(
    body: dict[str, object],
    spent_transaction_id: str,
    spent_vout: int,
) -> dict[str, object]:
    inputs = [_object(item) for item in _list(body["vin"])]
    outputs = [_object(item) for item in _list(body["vout"])]
    matches = [
        (index, item)
        for index, item in enumerate(inputs)
        if str(item["txid"]) == spent_transaction_id and int(item["vout"]) == spent_vout
    ]
    if len(matches) != 1:
        raise ValueError("spent outpoint is not uniquely present")
    spending_vin, spent_input = matches[0]
    status = _object(body["status"])
    return {
        "spent_transaction_id": spent_transaction_id,
        "spent_vout": spent_vout,
        "spent_value_sat": int(_object(spent_input["prevout"])["value"]),
        "spending_transaction_id": str(body["txid"]),
        "spending_vin": spending_vin,
        "block_height": int(status["block_height"]),
        "fee_sat": int(body["fee"]),
        "created_outputs": [
            {
                "vout": index,
                "value_sat": int(item["value"]),
                "script_type": str(item["scriptpubkey_type"]),
                "address": str(item["scriptpubkey_address"]),
            }
            for index, item in enumerate(outputs)
        ],
    }


def _publicnode_projection(body: dict[str, object]) -> dict[str, object]:
    result = _object(body["result"])
    inputs = [_object(item) for item in _list(result["vin"])]
    outputs = [_object(item) for item in _list(result["vout"])]
    return {
        "transaction_id": str(result["txid"]),
        "block_hash": str(result["blockhash"]),
        "block_time": int(result["blocktime"]),
        "inputs": [
            {
                "transaction_id": str(item["txid"]),
                "vout": int(item["vout"]),
                "sequence": int(item["sequence"]),
            }
            for item in inputs
        ],
        "outputs": [
            {
                "vout": int(item["n"]),
                "value_sat": int(Decimal(str(item["value"])) * Decimal(100_000_000)),
                "address": str(_object(item["scriptPubKey"])["address"]),
            }
            for item in outputs
        ],
    }


def _publicnode_hop_projection(
    body: dict[str, object],
    replay: BitcoinUtxoReplay,
    spent_transaction_id: str,
    spent_vout: int,
) -> dict[str, object]:
    result = _object(body["result"])
    inputs = [_object(item) for item in _list(result["vin"])]
    outputs = [_object(item) for item in _list(result["vout"])]
    matches = [
        (index, item)
        for index, item in enumerate(inputs)
        if str(item["txid"]) == spent_transaction_id and int(item["vout"]) == spent_vout
    ]
    if len(matches) != 1:
        raise ValueError("PublicNode spent outpoint is not uniquely present")
    spending_vin, _ = matches[0]
    root_output = next(
        (
            item
            for item in replay.transaction.outputs
            if replay.transaction.transaction_id == spent_transaction_id and item.vout == spent_vout
        ),
        None,
    )
    if root_output is None:
        raise ValueError("PublicNode spent value source is missing")
    created_outputs = [
        {
            "vout": int(item["n"]),
            "value_sat": int(Decimal(str(item["value"])) * Decimal(100_000_000)),
            "script_type": _publicnode_script_type(_object(item["scriptPubKey"])["type"]),
            "address": str(_object(item["scriptPubKey"])["address"]),
        }
        for item in outputs
    ]
    return {
        "spent_transaction_id": spent_transaction_id,
        "spent_vout": spent_vout,
        "spent_value_sat": root_output.value_sat,
        "spending_transaction_id": str(result["txid"]),
        "spending_vin": spending_vin,
        "block_hash": str(result["blockhash"]),
        "block_time": int(result["blocktime"]),
        "fee_sat": root_output.value_sat - sum(int(item["value_sat"]) for item in created_outputs),
        "created_outputs": created_outputs,
    }


def _publicnode_script_type(value: object) -> str:
    mapping = {
        "witness_v0_keyhash": "v0_p2wpkh",
        "witness_v0_scripthash": "v0_p2wsh",
        "witness_v1_taproot": "v1_p2tr",
        "pubkeyhash": "p2pkh",
        "scripthash": "p2sh",
    }
    script_type = str(value)
    if script_type not in mapping:
        raise ValueError("unsupported PublicNode script type")
    return mapping[script_type]


def _publicnode_hop_comparable(projection: dict[str, object]) -> dict[str, object]:
    return {
        key: projection[key]
        for key in (
            "spent_transaction_id",
            "spent_vout",
            "spent_value_sat",
            "spending_transaction_id",
            "spending_vin",
            "fee_sat",
            "created_outputs",
        )
    }


def _rest_hop_public_projection(projection: dict[str, object]) -> dict[str, object]:
    return {
        "spent_transaction_id": projection["spent_transaction_id"],
        "spent_vout": projection["spent_vout"],
        "spent_value_sat": projection["spent_value_sat"],
        "spending_transaction_id": projection["spending_transaction_id"],
        "spending_vin": projection["spending_vin"],
        "fee_sat": projection["fee_sat"],
        "created_outputs": [
            {
                "vout": item["vout"],
                "value_sat": item["value_sat"],
                "script_type": item["script_type"],
                "address": item["address"],
            }
            for item in (_object(value) for value in _list(projection["created_outputs"]))
        ],
    }


def _replay_transaction_projection(replay: BitcoinUtxoReplay) -> dict[str, object]:
    tx = replay.transaction
    return {
        "transaction_id": tx.transaction_id,
        "block_height": tx.block_height,
        "block_hash": tx.block_hash,
        "block_time": tx.block_time,
        "fee_sat": tx.fee_sat,
        "inputs": [item.model_dump(mode="json") for item in tx.inputs],
        "outputs": [item.model_dump(mode="json") for item in tx.outputs],
    }


def _publicnode_replay_projection(replay: BitcoinUtxoReplay) -> dict[str, object]:
    tx = replay.transaction
    return {
        "transaction_id": tx.transaction_id,
        "block_hash": tx.block_hash,
        "block_time": tx.block_time,
        "inputs": [
            {
                "transaction_id": item.prevout.transaction_id,
                "vout": item.prevout.vout,
                "sequence": item.sequence,
            }
            for item in tx.inputs
        ],
        "outputs": [
            {
                "vout": item.vout,
                "value_sat": item.value_sat,
                "address": item.address,
            }
            for item in tx.outputs
        ],
    }


def _replay_hop_projection(hop: BitcoinSpendHop) -> dict[str, object]:
    return {
        "spent_transaction_id": hop.spent_transaction_id,
        "spent_vout": hop.spent_vout,
        "spent_value_sat": hop.spent_value_sat,
        "spending_transaction_id": hop.spending_transaction_id,
        "spending_vin": hop.spending_vin,
        "block_height": hop.block_height,
        "fee_sat": hop.fee_sat,
        "created_outputs": [item.model_dump(mode="json") for item in hop.created_outputs],
    }


def _validate_artifact_path(
    root: dict[str, object],
    hops: list[dict[str, object]],
) -> None:
    previous_transaction_id = str(root["transaction_id"])
    previous_outputs = _list(root["outputs"])
    for hop in hops:
        if hop["spent_transaction_id"] != previous_transaction_id:
            raise ValueError("artifact spend path chain differs")
        matches = [
            _object(item)
            for item in previous_outputs
            if int(_object(item)["vout"]) == int(hop["spent_vout"])
        ]
        if len(matches) != 1 or int(matches[0]["value_sat"]) != int(hop["spent_value_sat"]):
            raise ValueError("artifact spent output differs")
        previous_transaction_id = str(hop["spending_transaction_id"])
        previous_outputs = _list(hop["created_outputs"])


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("expected object")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("expected list")
    return value


def _evidence(replay: BitcoinUtxoReplay) -> list[dict[str, object]]:
    tx = replay.transaction
    records: list[dict[str, object]] = []
    for index, item in enumerate(tx.providers):
        records.append(
            {
                "evidence_id": f"EV-BTC-TX-{index}",
                "evidence_type": "context",
                "source_id": ("DS-BTC-NODE" if item.role == "primary" else "DS-BTC-API"),
                "source_record_ref": f"SRC-BTC-{index}",
                "method": ("getrawtransaction" if item.role == "primary" else "GET /api/tx/:txid"),
                "retrieved_at": item.retrieved_at,
                "locator": {"block_number": tx.block_height},
                "decoded": {
                    "transaction_id": tx.transaction_id,
                    "input_count": len(tx.inputs),
                    "output_count": len(tx.outputs),
                    "fee_sat": tx.fee_sat,
                },
                "raw_artifact": {
                    "artifact_uri": f"artifact://sha256/{item.artifact_sha256}",
                    "sha256": item.artifact_sha256,
                    "media_type": "application/json",
                },
            }
        )
    for hop_index, hop in enumerate(replay.spend_path):
        for provider_index, item in enumerate(hop.providers):
            records.append(
                {
                    "evidence_id": f"EV-BTC-HOP-{hop_index}-{provider_index}",
                    "evidence_type": "context",
                    "source_id": ("DS-BTC-NODE" if item.role == "primary" else "DS-BTC-API"),
                    "source_record_ref": f"SRC-BTC-HOP-{hop_index}-{provider_index}",
                    "method": (
                        "getrawtransaction" if item.role == "primary" else "GET /api/tx/:txid"
                    ),
                    "retrieved_at": item.retrieved_at,
                    "locator": {"block_number": hop.block_height},
                    "decoded": {
                        "spent_transaction_id": hop.spent_transaction_id,
                        "spent_vout": hop.spent_vout,
                        "spending_transaction_id": hop.spending_transaction_id,
                        "spending_vin": hop.spending_vin,
                        "created_output_count": len(hop.created_outputs),
                    },
                    "raw_artifact": {
                        "artifact_uri": f"artifact://sha256/{item.artifact_sha256}",
                        "sha256": item.artifact_sha256,
                        "media_type": "application/json",
                    },
                }
            )
    return records


def _sources(replay: BitcoinUtxoReplay) -> list[dict[str, object]]:
    hosts = {
        "publicnode.bitcoin": "bitcoin-rpc.publicnode.com",
        "mempool.space": "mempool.space",
        "blockstream.info": "blockstream.info",
    }
    records: list[dict[str, object]] = []
    for index, item in enumerate(replay.transaction.providers):
        records.append(
            {
                "source_record_id": f"SRC-BTC-{index}",
                "source_id": ("DS-BTC-NODE" if item.role == "primary" else "DS-BTC-API"),
                "provider_id": item.provider_id,
                "role": "scoring" if item.role == "primary" else "supporting",
                "required": item.role in {"primary", "verify"},
                "capability": "bitcoin_transaction_prevouts",
                "endpoint_host": hosts[item.provider_id],
                "retrieved_at": item.retrieved_at,
            }
        )
    for hop_index, hop in enumerate(replay.spend_path):
        for provider_index, item in enumerate(hop.providers):
            records.append(
                {
                    "source_record_id": f"SRC-BTC-HOP-{hop_index}-{provider_index}",
                    "source_id": ("DS-BTC-NODE" if item.role == "primary" else "DS-BTC-API"),
                    "provider_id": item.provider_id,
                    "role": "scoring" if item.role == "primary" else "supporting",
                    "required": item.role in {"primary", "verify"},
                    "capability": "bitcoin_spend_path",
                    "endpoint_host": hosts[item.provider_id],
                    "retrieved_at": item.retrieved_at,
                }
            )
    return records


def _result(
    request: BitcoinUtxoAnalysisRequest,
    replay: BitcoinUtxoReplay,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    observed = replay.transaction.providers[0].retrieved_at.isoformat()
    is_partial = not replay.spend_path
    document = {
        "$schema": "analysis-result.schema.json",
        "schema_version": "0.2",
        "analysis_id": request.analysis_id,
        "analysis_type": "bitcoin_utxo",
        "chain_id": 0,
        "status": "partial" if is_partial else "complete",
        "results": results,
        "evidence": evidence,
        "sources": _sources(replay),
        "warnings": [],
        "errors": (
            [
                {
                    "error_id": "ERR-BTC-SPEND-EVIDENCE",
                    "code": "evidence_incomplete",
                    "stage": "spend_path",
                    "message": "No reviewed spend-path evidence is available.",
                    "retryable": False,
                    "attempt_count": 1,
                }
            ]
            if is_partial
            else []
        ),
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
            "json": {"artifact_uri": "artifact://pending/bitcoin-result"},
            "markdown": {"artifact_uri": "artifact://pending/bitcoin-evidence"},
        },
    }
    return validate_analysis_result(document)


def _failed(
    request: BitcoinUtxoAnalysisRequest,
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
            "analysis_type": "bitcoin_utxo",
            "chain_id": 0,
            "status": "failed",
            "results": [],
            "evidence": [],
            "sources": [],
            "warnings": [],
            "errors": [
                {
                    "error_id": "ERR-BTC-ANALYSIS",
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
                "json": {"artifact_uri": "artifact://pending/bitcoin-result"},
                "markdown": {"artifact_uri": "artifact://pending/bitcoin-evidence"},
            },
        }
    )
