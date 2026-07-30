"""Replay the TASK-016 bridge candidate across Base and Ethereum."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    resolve_output_root,
    write_report,
)
from scan_tool.application.security import SensitiveDataError
from scan_tool.application.task_016_bridge_replay import (
    BRIDGE_ENDPOINT_ENV,
    CHAINS,
    FIXTURE_ID,
    BridgeProviderRole,
    bridge_pair_facts,
    bridge_requests,
    resolve_bridge_endpoints,
    run_task_016_bridge_replay,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("primary", "verify"), required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--rules-status",
        choices=("allowed", "restricted", "unclear"),
        default="unclear",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    role: BridgeProviderRole = args.role
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "not_executed",
                    "fixture_id": FIXTURE_ID,
                    "role": role,
                    "network_calls": 0,
                    "required_endpoint_env": BRIDGE_ENDPOINT_ENV[role],
                    "methods_by_chain": {
                        chain: [request.method for request in bridge_requests(chain)]
                        for chain in CHAINS
                    },
                }
            )
        )
        return 0
    try:
        endpoints = resolve_bridge_endpoints(
            execute=True,
            rules_status=args.rules_status,
            role=role,
            environment=dict(os.environ),
        )
    except PermissionError as error:
        print(json.dumps({"status": "rule_restricted", "message": str(error)}))
        return 5
    except ValueError as error:
        print(json.dumps({"status": "invalid_input", "message": str(error)}))
        return 2
    if endpoints is None:
        raise RuntimeError("execute mode requires bridge endpoints")
    reports = {}
    try:
        async with httpx.AsyncClient() as client:
            for chain in CHAINS:
                output_root = resolve_output_root(
                    Path(f".scan/live-provider-smoke/task-016-bridge-replay/{role}/{chain}"),
                    REPOSITORY_ROOT,
                )
                report = await run_task_016_bridge_replay(
                    chain=chain,
                    role=role,
                    endpoint=endpoints[chain],
                    output_root=output_root,
                    client=client,
                )
                write_report(report, output_root)
                reports[chain] = report
    except SensitiveDataError:
        print(json.dumps({"status": "security_blocked"}))
        return 4
    status = (
        "complete" if all(report.status == "complete" for report in reports.values()) else "partial"
    )
    facts = None
    if status == "complete":
        try:
            facts = bridge_pair_facts(reports["base"], reports["ethereum"])
        except (KeyError, TypeError, ValueError):
            print(json.dumps({"status": "invalid_response"}))
            return 4
    print(
        json.dumps(
            {
                "status": status,
                "fixture_id": FIXTURE_ID,
                "role": role,
                "network_calls": sum(report.network_calls for report in reports.values()),
                "decoded_pair_match": facts is not None,
                "facts": facts,
            }
        )
    )
    return 0 if status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
