#!/usr/bin/env python3
"""Contest-day Across V3 bridge helper (Base -> Ethereum).

Captures single-source RPC responses, content-addresses them under
``artifacts/sha256/``, assembles ``raw-replay.json`` + ``provider-replay.json``
+ ``analysis-request.json``, then calls ``analyze_bridge_transfer_replay``
without modifying production analyzers.

Honesty: this path is single-source only. Output always carries
``verification_level: single_source_unverified`` and must not be treated as a
dual-provider confirmed fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scan_tool.application.security import SensitiveDataGuard  # noqa: E402
from scan_tool.domain import validate_analysis_request  # noqa: E402
from scan_tool.domain.analysis_request import BridgeTransferAnalysisRequest  # noqa: E402
from scan_tool.domain.bridge_transfer import (  # noqa: E402
    DESTINATION_EVENT_TOPIC0,
    SOURCE_EVENT_TOPIC0,
)
from scan_tool.slices.bridge_transfer import analyze_bridge_transfer_replay  # noqa: E402

BridgeChain = Literal["base", "ethereum"]

DEFAULT_RPC_URL_ENV: dict[BridgeChain, str] = {
    "base": "SCAN_CONTEST_BASE_RPC_URL",
    "ethereum": "SCAN_CONTEST_ETHEREUM_RPC_URL",
}

PINNED_FX_BRG_001_FACT_HASH = "d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac"
FX_BRG_001 = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-BRG-001"

OFFICIAL_SPOKE_POOL: dict[BridgeChain, str] = {
    "base": "0x09aea4b2242abc8bb4bb78d537a67a245a7bec64",
    "ethereum": "0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5",
}
TOPIC0: dict[BridgeChain, str] = {
    "base": SOURCE_EVENT_TOPIC0,
    "ethereum": DESTINATION_EVENT_TOPIC0,
}
CHAIN_ID: dict[BridgeChain, int] = {"base": 8453, "ethereum": 1}
PROVIDER_ID: dict[BridgeChain, str] = {
    "base": "PROVIDER-BASE-PRIMARY",
    "ethereum": "PROVIDER-ETHEREUM-PRIMARY",
}
OFFLINE_REUSE_METHODS = (
    "eth_getTransactionByHash",
    "eth_getTransactionReceipt",
    "eth_getBlockByNumber",
    "eth_getLogs",
)
LIVE_CAPTURE_METHODS = ("eth_chainId", *OFFLINE_REUSE_METHODS)


class EndpointSecretError(ValueError):
    """Raised when an RPC endpoint fails the offline safety checks."""


def _endpoint_secret_candidates(endpoint: str) -> tuple[str, ...]:
    """Extract query-param values and long path segments that may be API keys."""
    parts = urlsplit(endpoint)
    candidates = [value for _, value in parse_qsl(parts.query) if value]
    candidates.extend(segment for segment in parts.path.split("/") if len(segment) >= 16)
    return tuple(candidates)


def resolve_rpc_endpoint(env_name: str, *, role: str) -> str:
    """Read an RPC URL from an environment variable only, never a CLI argument.

    Mirrors ``provider_smoke.require_execution_allowed``: HTTPS-only, no URL
    userinfo. The raw URL is never returned in an exception message.
    """
    endpoint = os.environ.get(env_name)
    if not endpoint:
        raise EndpointSecretError(f"{role} RPC endpoint requires env var {env_name}")
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.netloc:
        raise EndpointSecretError(f"{env_name} must be an absolute HTTPS URL")
    if parts.username is not None or parts.password is not None:
        raise EndpointSecretError(f"{env_name} must not contain URL userinfo")
    return endpoint


def _redact(message: str, endpoint: str) -> str:
    """Strip an endpoint URL (and any embedded secret substrings) from a message."""
    redacted = message.replace(endpoint, "[redacted-endpoint]")
    for candidate in _endpoint_secret_candidates(endpoint):
        redacted = redacted.replace(candidate, "[redacted]")
    return redacted


def _guard_output(payload: dict[str, Any], *, secrets: tuple[str, ...]) -> None:
    """Refuse to print output containing an RPC secret or a local filesystem path."""
    guard = SensitiveDataGuard(forbidden_values=secrets)
    guard.check_text(json.dumps(payload, ensure_ascii=True))


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_fact_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _lower(value: object) -> str:
    return str(value).lower()


def _write_bytes(path: Path, raw: bytes) -> str:
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.parent / f"{digest}.json"
    if not target.exists():
        target.write_bytes(raw)
    elif target.read_bytes() != raw:
        raise RuntimeError(f"artifact collision for {digest}")
    return digest


def store_json_rpc_artifact(package: Path, payload: dict[str, Any]) -> str:
    """Persist one JSON-RPC response envelope; return content SHA-256."""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    return _write_bytes(package / "artifacts" / "sha256" / "placeholder.json", raw)


def rpc_call(
    url: str, method: str, params: list[Any], *, request_id: int = 1, role: str = "rpc"
) -> dict[str, Any]:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        separators=(",", ":"),
    ).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.URLError as error:
        # Never interpolate the raw endpoint into an exception message: it may
        # embed an API key and this message can reach terminals/logs/chat.
        raise RuntimeError(_redact(f"RPC {method} failed against {role}: {error}", url)) from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"RPC {method} returned a non-object payload")
    if payload.get("error") is not None:
        raise RuntimeError(_redact(f"RPC {method} error: {payload['error']}", url))
    return payload


def verify_chain_id(result: object, *, chain: BridgeChain, role: str) -> None:
    """Validate an already-fetched eth_chainId result against the declared chain.

    Prevents a swapped/misconfigured endpoint from silently producing a
    confidently-wrong result under the wrong chain_id. Takes the RPC result
    (not a URL) so the fetch and the artifact pinning stay in one place
    (``capture_chain_leg``) and this stays trivially unit-testable offline.
    """
    if not isinstance(result, str) or not result.startswith("0x"):
        raise RuntimeError(f"{role}: eth_chainId returned a malformed result")
    observed = int(result, 16)
    expected = CHAIN_ID[chain]
    if observed != expected:
        raise RuntimeError(
            f"{role}: eth_chainId={observed} does not match declared chain "
            f"{chain} (expected {expected}) -- endpoints may be swapped"
        )


def _select_bridge_log(
    logs: list[Any],
    *,
    spoke_pool: str,
    topic0: str,
    transaction_hash: str,
) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        topics = item.get("topics")
        if not isinstance(topics, list) or not topics:
            continue
        if _lower(item.get("address")) != _lower(spoke_pool):
            continue
        if _lower(topics[0]) != _lower(topic0):
            continue
        if _lower(item.get("transactionHash")) != _lower(transaction_hash):
            continue
        if item.get("removed") is True:
            continue
        matched.append(item)
    if len(matched) != 1:
        raise RuntimeError(
            f"expected exactly one bridge log for {transaction_hash}, found {len(matched)}"
        )
    return matched[0]


def capture_chain_leg(
    package: Path,
    *,
    chain: BridgeChain,
    transaction_hash: str,
    rpc_url: str,
    spoke_pool: str | None = None,
) -> dict[str, Any]:
    """Fetch five RPC capabilities for one chain (chain-id check + four
    capture capabilities) and pin them as artifacts."""
    tx_hash = _lower(transaction_hash)
    pool = _lower(spoke_pool or OFFICIAL_SPOKE_POOL[chain])
    topic0 = TOPIC0[chain]
    role = f"{chain} RPC"

    # P1: confirm the endpoint actually serves the declared chain before
    # trusting anything it returns (a swapped/misconfigured URL must fail
    # loudly, not produce a confidently-wrong result). The response itself is
    # pinned as an artifact below so the check is independently reviewable,
    # not just a code assertion.
    chain_id_payload = rpc_call(rpc_url, "eth_chainId", [], request_id=0, role=role)
    verify_chain_id(chain_id_payload.get("result"), chain=chain, role=role)
    chain_id_digest = store_json_rpc_artifact(package, chain_id_payload)

    tx_payload = rpc_call(rpc_url, "eth_getTransactionByHash", [tx_hash], request_id=1, role=role)
    tx_result = tx_payload.get("result")
    if not isinstance(tx_result, dict):
        raise RuntimeError(f"{chain}: transaction not found: {tx_hash}")
    block_tag = _lower(tx_result.get("blockNumber"))
    if not block_tag.startswith("0x"):
        raise RuntimeError(f"{chain}: transaction has no blockNumber")

    receipt_payload = rpc_call(
        rpc_url, "eth_getTransactionReceipt", [tx_hash], request_id=2, role=role
    )
    receipt_result = receipt_payload.get("result")
    if not isinstance(receipt_result, dict):
        raise RuntimeError(f"{chain}: receipt not found: {tx_hash}")
    if receipt_result.get("status") != "0x1":
        raise RuntimeError(f"{chain}: transaction was not successful")

    block_payload = rpc_call(
        rpc_url, "eth_getBlockByNumber", [block_tag, False], request_id=3, role=role
    )

    # Prefer getLogs; if the node returns multiple same-topic events in the
    # block, narrow to this transaction so the analyzer's len==1 rule holds.
    logs_payload = rpc_call(
        rpc_url,
        "eth_getLogs",
        [
            {
                "address": pool,
                "fromBlock": block_tag,
                "toBlock": block_tag,
                "topics": [topic0],
            }
        ],
        request_id=4,
        role=role,
    )
    logs_result = logs_payload.get("result")
    if not isinstance(logs_result, list):
        raise RuntimeError(f"{chain}: eth_getLogs result is not a list")
    selected = _select_bridge_log(
        logs_result,
        spoke_pool=pool,
        topic0=topic0,
        transaction_hash=tx_hash,
    )
    logs_payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "result": [selected],
    }

    # NOTE: `digests` maps 1:1 to the strict, extra="forbid" schema the real
    # analyzer validates raw_observations[chain].artifacts against
    # (BridgeObservationArtifacts: transaction/receipt/block/bridge_logs
    # only). The chain-id artifact must NOT go in here or replay validation
    # breaks; it is carried separately as `chain_id_sha256` and only merged
    # into provider-replay.json's permissive `raw_sha256` provenance below.
    digests = {
        "transaction": store_json_rpc_artifact(package, tx_payload),
        "receipt": store_json_rpc_artifact(package, receipt_payload),
        "block": store_json_rpc_artifact(package, block_payload),
        "bridge_logs": store_json_rpc_artifact(package, logs_payload),
    }
    return {
        "chain": chain,
        "chain_id": CHAIN_ID[chain],
        "transaction_hash": tx_hash,
        "block_tag": block_tag,
        "spoke_pool": pool,
        "provider_id": PROVIDER_ID[chain],
        "raw_sha256": digests,
        "chain_id_sha256": chain_id_digest,
        "retrieved_at": _utc_now(),
        "network_calls": len(LIVE_CAPTURE_METHODS),
        "methods": list(LIVE_CAPTURE_METHODS),
    }


def pin_leg_from_existing_artifacts(
    package: Path,
    *,
    chain: BridgeChain,
    source_package: Path,
    provider_id: str,
    digests: dict[str, str],
    transaction_hash: str,
    block_tag: str,
    spoke_pool: str,
    chain_id: int,
) -> dict[str, Any]:
    """Copy already-pinned artifacts into ``package`` (offline assembly path)."""
    artifact_dir = package / "artifacts" / "sha256"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for digest in digests.values():
        src = source_package / "artifacts" / "sha256" / f"{digest}.json"
        dst = artifact_dir / f"{digest}.json"
        if not src.is_file():
            raise FileNotFoundError(src)
        if not dst.exists():
            shutil.copyfile(src, dst)
        elif hashlib.sha256(dst.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"corrupt artifact copy for {digest}")
    return {
        "chain": chain,
        "chain_id": chain_id,
        "transaction_hash": _lower(transaction_hash),
        "block_tag": _lower(block_tag),
        "spoke_pool": _lower(spoke_pool),
        "provider_id": provider_id,
        "raw_sha256": digests,
        "retrieved_at": _utc_now(),
        # No live RPC call happens on this offline-reuse path; the count and
        # methods reflect the original source fixture's capture, not a new
        # eth_chainId verification.
        "network_calls": len(OFFLINE_REUSE_METHODS),
        "methods": list(OFFLINE_REUSE_METHODS),
    }


def build_provider_replay(
    fixture_id: str, legs: list[dict[str, Any]], captured_at: str
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "fixture_id": fixture_id,
        "status": "candidate",
        "captured_at": captured_at,
        "providers": [
            {
                "provider_id": leg["provider_id"],
                "chain_id": leg["chain_id"],
                "status": "complete",
                "network_calls": leg["network_calls"],
                "source_class": "contest_single_source_rpc",
                "retrieved_at": leg["retrieved_at"],
                # provider-replay.json's raw_sha256 is a permissive dict (not
                # the strict analyzer-facing artifacts schema), so the
                # eth_chainId artifact is safe to include here for
                # provenance even though it must stay out of raw-replay.json.
                "raw_sha256": (
                    {**leg["raw_sha256"], "chain_id": leg["chain_id_sha256"]}
                    if leg.get("chain_id_sha256")
                    else dict(leg["raw_sha256"])
                ),
            }
            for leg in legs
        ],
        "decoded_match": False,
        "same_role_chain_pair_match": False,
        "cross_provider_decoded_match": False,
        "cross_provider_verification": {
            "status": "skipped",
            "reason": "single_source_unverified contest capture",
        },
        "failed_attempts": [],
        "negative_oracle": {},
        "independent_verifier": {
            "module": "scripts.contest.bridge_quick_capture",
            "method": "single_source_unverified",
            "requirements_verified": [],
            "deterministic_runs": 1,
            "status": "skipped_single_source",
        },
        "remaining_gate": [
            "independent_verify_provider_missing",
            "cross_provider_decoded_match_unproven",
        ],
    }


def build_raw_replay(
    fixture_id: str, legs: list[dict[str, Any]], captured_at: str
) -> dict[str, Any]:
    by_chain = {leg["chain"]: leg for leg in legs}
    if set(by_chain) != {"base", "ethereum"}:
        raise ValueError("both base and ethereum legs are required")
    return {
        "schema_version": "0.1",
        "fixture_id": fixture_id,
        "status": "candidate",
        "capture_status": "complete",
        "captured_at": captured_at,
        "network_calls": sum(int(leg["network_calls"]) for leg in legs),
        "chains": {
            chain: {
                "chain_id": by_chain[chain]["chain_id"],
                "transaction_hash": by_chain[chain]["transaction_hash"],
                "block_tag": by_chain[chain]["block_tag"],
                "spoke_pool": by_chain[chain]["spoke_pool"],
            }
            for chain in ("base", "ethereum")
        },
        "methods_per_chain": list(dict.fromkeys(m for leg in legs for m in leg["methods"])),
        "raw_observations": [
            {
                "chain": chain,
                "provider_id": by_chain[chain]["provider_id"],
                "artifacts": {
                    capability: f"artifact://sha256/{digest}"
                    for capability, digest in by_chain[chain]["raw_sha256"].items()
                },
            }
            for chain in ("base", "ethereum")
        ],
        "reconciled_facts": {},
        "remaining_gate": [
            "independent_verify_provider_missing",
            "cross_provider_decoded_match_unproven",
        ],
    }


def build_analysis_request(
    fixture_id: str,
    *,
    source_subject: str,
    source_tx: str,
    destination_tx: str,
    requested_at: str,
) -> dict[str, Any]:
    return {
        "$schema": "../../schemas/analysis-request.schema.json",
        "schema_version": "0.2",
        "analysis_id": f"AN-{fixture_id}",
        "analysis_type": "bridge_transfer",
        "query_kind": "link_bridge_transfer",
        "chain_id": 1,
        "fixture_id": fixture_id,
        "requested_at": requested_at,
        "inputs": {
            "source_subject": _lower(source_subject),
            "destination_chain_id": 1,
            "origin_chain_id": 8453,
            "source_transaction_hash": _lower(source_tx),
            "destination_transaction_hash": _lower(destination_tx),
        },
        "source_policy": {
            "rule_status": "allowed",
            "allowed_source_ids": ["DS-EVM-RPC-ARCHIVE", "DS-BRIDGE-META"],
            "source_order": ["DS-EVM-RPC-ARCHIVE", "DS-BRIDGE-META"],
            "allow_fallback": False,
            "offline_mode": True,
        },
    }


def write_package(
    package: Path,
    *,
    fixture_id: str,
    legs: list[dict[str, Any]],
    source_subject: str,
) -> None:
    captured_at = _utc_now()
    by_chain = {leg["chain"]: leg for leg in legs}
    request = build_analysis_request(
        fixture_id,
        source_subject=source_subject,
        source_tx=by_chain["base"]["transaction_hash"],
        destination_tx=by_chain["ethereum"]["transaction_hash"],
        requested_at=captured_at,
    )
    raw_replay = build_raw_replay(fixture_id, legs, captured_at)
    provider_replay = build_provider_replay(fixture_id, legs, captured_at)
    package.mkdir(parents=True, exist_ok=True)
    (package / "analysis-request.json").write_text(
        json.dumps(request, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "raw-replay.json").write_text(
        json.dumps(raw_replay, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "provider-replay.json").write_text(
        json.dumps(provider_replay, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def run_analyzer(package: Path) -> dict[str, Any]:
    request = validate_analysis_request(
        json.loads((package / "analysis-request.json").read_text(encoding="utf-8"))
    ).root
    if not isinstance(request, BridgeTransferAnalysisRequest):
        raise TypeError("analysis-request is not BridgeTransferAnalysisRequest")
    raw_replay = (package / "raw-replay.json").read_bytes()
    result = analyze_bridge_transfer_replay(request, raw_replay, package_dir=package)
    contract = result.to_contract_dict()
    fact_hash = None
    facts = None
    if contract.get("status") == "complete" and contract.get("results"):
        facts = contract["results"][0].get("value")
        if isinstance(facts, dict):
            fact_hash = _canonical_fact_sha256(facts)
    return {
        "verification_level": "single_source_unverified",
        "honesty": {
            "dual_provider_verified": False,
            "may_submit_as_confirmed": False,
            "submit_as": "computed, independent re-verification not performed",
            "note": (
                "Analyzer may emit classification=confirmed_fact for complete "
                "offline reconstruction; contest output must still treat this "
                "run as single_source_unverified."
            ),
        },
        "analyzer_status": contract.get("status"),
        "analyzer_classification": (
            contract.get("results", [{}])[0].get("classification")
            if contract.get("results")
            else None
        ),
        "canonical_fact_sha256": fact_hash,
        "facts": facts,
        "analyzer_result": contract,
        # P2: a logical tag, never the absolute local filesystem path.
        "package_id": package.name,
    }


def _depositor_from_facts_or_fixture(package: Path) -> str:
    """Best-effort depositor for request binding when reusing a fixture package."""
    expected = package / "expected.json"
    if expected.is_file():
        payload = json.loads(expected.read_text(encoding="utf-8"))
        depositor = payload.get("bridge_transfer", {}).get("depositor")
        if isinstance(depositor, str):
            return depositor
    request_path = package / "analysis-request.json"
    if request_path.is_file():
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        subject = payload.get("inputs", {}).get("source_subject")
        if isinstance(subject, str):
            return subject
    raise RuntimeError("cannot determine source_subject/depositor")


def self_check() -> dict[str, Any]:
    """Rebuild FX-SVC-BRG-001 into a temp package via contest writers and analyze."""
    source = FX_BRG_001
    raw = json.loads((source / "raw-replay.json").read_text(encoding="utf-8"))
    legs: list[dict[str, Any]] = []
    for observation in raw["raw_observations"]:
        chain: BridgeChain = observation["chain"]
        chain_ref = raw["chains"][chain]
        digests = {
            name: uri.removeprefix("artifact://sha256/")
            for name, uri in observation["artifacts"].items()
        }
        legs.append(
            {
                "chain": chain,
                "chain_id": chain_ref["chain_id"],
                "transaction_hash": chain_ref["transaction_hash"],
                "block_tag": chain_ref["block_tag"],
                "spoke_pool": chain_ref["spoke_pool"],
                "provider_id": observation["provider_id"],
                "raw_sha256": digests,
                "retrieved_at": _utc_now(),
                "network_calls": 4,
                "_source_package": source,
            }
        )

    out = Path(tempfile.mkdtemp(prefix="bridge-quick-selfcheck-"))
    try:
        rebuilt: list[dict[str, Any]] = []
        for leg in legs:
            rebuilt.append(
                pin_leg_from_existing_artifacts(
                    out,
                    chain=leg["chain"],
                    source_package=leg["_source_package"],
                    provider_id=leg["provider_id"],
                    digests=leg["raw_sha256"],
                    transaction_hash=leg["transaction_hash"],
                    block_tag=leg["block_tag"],
                    spoke_pool=leg["spoke_pool"],
                    chain_id=leg["chain_id"],
                )
            )
        fixture_id = "FX-CONTEST-BRG-SELFCHECK"
        write_package(
            out,
            fixture_id=fixture_id,
            legs=rebuilt,
            source_subject=_depositor_from_facts_or_fixture(source),
        )
        report = run_analyzer(out)
        report["self_check"] = {
            "expected_fact_sha256": PINNED_FX_BRG_001_FACT_HASH,
            "matched_pinned_hash": report.get("canonical_fact_sha256")
            == PINNED_FX_BRG_001_FACT_HASH,
        }
        if report["self_check"]["matched_pinned_hash"] is not True:
            raise RuntimeError(
                "self-check fact hash mismatch: "
                f"{report.get('canonical_fact_sha256')} != {PINNED_FX_BRG_001_FACT_HASH}"
            )
        if report.get("verification_level") != "single_source_unverified":
            raise RuntimeError("self-check missing single_source_unverified marker")
        return report
    except Exception:
        shutil.rmtree(out, ignore_errors=True)
        raise


def capture_and_analyze(args: argparse.Namespace) -> dict[str, Any]:
    if args.origin_chain_id != 8453 or args.destination_chain_id != 1:
        raise SystemExit("this helper only supports Across V3 Base(8453) -> Ethereum(1)")

    # P1: RPC URLs are never accepted as CLI arguments (shell history, `ps`,
    # and this process's own argv are all untrusted for secrets). Only the
    # *name* of an environment variable holding the URL is accepted.
    base_rpc_url = resolve_rpc_endpoint(args.base_rpc_url_env, role="base")
    ethereum_rpc_url = resolve_rpc_endpoint(args.ethereum_rpc_url_env, role="ethereum")
    secrets = _endpoint_secret_candidates(base_rpc_url) + _endpoint_secret_candidates(
        ethereum_rpc_url
    )

    package = Path(args.output_dir).resolve()
    if package.exists() and any(package.iterdir()):
        raise SystemExit(f"output dir is not empty: {package}")
    package.mkdir(parents=True, exist_ok=True)

    base_leg = capture_chain_leg(
        package,
        chain="base",
        transaction_hash=args.source_tx,
        rpc_url=base_rpc_url,
        spoke_pool=args.base_spoke_pool,
    )
    eth_leg = capture_chain_leg(
        package,
        chain="ethereum",
        transaction_hash=args.destination_tx,
        rpc_url=ethereum_rpc_url,
        spoke_pool=args.ethereum_spoke_pool,
    )

    source_subject = args.source_subject or _depositor_from_source_log(package, base_leg)
    write_package(
        package,
        fixture_id=args.fixture_id,
        legs=[base_leg, eth_leg],
        source_subject=source_subject,
    )
    report = run_analyzer(package)
    # P1/defense-in-depth: refuse to emit output containing either endpoint's
    # secret substrings or a local filesystem path, even if some code path
    # upstream forgot to redact.
    _guard_output(report, secrets=secrets)
    return report


def _depositor_from_source_log(package: Path, base_leg: dict[str, Any]) -> str:
    digest = base_leg["raw_sha256"]["bridge_logs"]
    payload = json.loads(
        (package / "artifacts" / "sha256" / f"{digest}.json").read_text(encoding="utf-8")
    )
    log = payload["result"][0]
    topics = log["topics"]
    # V3FundsDeposited topic3 embeds depositor address
    depositor = "0x" + topics[3][-40:]
    return _lower(depositor)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Contest helper: single-source Across V3 Base->Ethereum capture + "
            "analyze_bridge_transfer_replay (no analyzer modifications)."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "self-check",
        help="Rebuild FX-SVC-BRG-001 via contest writers and assert pinned fact hash",
    )
    check.set_defaults(func=lambda _args: self_check())

    offline = sub.add_parser(
        "analyze-package",
        help="Analyze an already-assembled package (still marked single_source_unverified)",
    )
    offline.add_argument("package_dir", type=Path)
    offline.set_defaults(func=lambda args: run_analyzer(args.package_dir.resolve()))

    capture = sub.add_parser(
        "capture",
        help="Fetch both legs over RPC, assemble package, analyze",
    )
    capture.add_argument("--source-tx", required=True)
    capture.add_argument("--destination-tx", required=True)
    capture.add_argument(
        "--base-rpc-url-env",
        default=DEFAULT_RPC_URL_ENV["base"],
        help=(
            "Name of the environment variable holding the Base RPC URL "
            f"(default: {DEFAULT_RPC_URL_ENV['base']}). The URL itself must "
            "never be passed as a CLI argument."
        ),
    )
    capture.add_argument(
        "--ethereum-rpc-url-env",
        default=DEFAULT_RPC_URL_ENV["ethereum"],
        help=(
            "Name of the environment variable holding the Ethereum RPC URL "
            f"(default: {DEFAULT_RPC_URL_ENV['ethereum']})."
        ),
    )
    capture.add_argument("--output-dir", required=True)
    capture.add_argument("--fixture-id", default="FX-CONTEST-BRG-LIVE")
    capture.add_argument("--source-subject", default=None)
    capture.add_argument("--origin-chain-id", type=int, default=8453)
    capture.add_argument("--destination-chain-id", type=int, default=1)
    capture.add_argument("--base-spoke-pool", default=None)
    capture.add_argument("--ethereum-spoke-pool", default=None)
    capture.set_defaults(func=capture_and_analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = args.func(args)
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if args.command == "self-check":
        matched = report.get("self_check", {}).get("matched_pinned_hash")
        return 0 if matched else 1
    if report.get("verification_level") != "single_source_unverified":
        return 1
    return 0 if report.get("analyzer_status") in {"complete", "partial", "failed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
