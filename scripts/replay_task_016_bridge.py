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
    BridgeChain,
    BridgeProviderRole,
    SmokeReport,
    assert_matching_provider_facts,
    bridge_pair_facts,
    bridge_requests,
    resolve_bridge_endpoints,
    run_task_016_bridge_replay,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ALL_ROLES: tuple[BridgeProviderRole, ...] = ("primary", "verify")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("primary", "verify", "both"), required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--rules-status",
        choices=("allowed", "restricted", "unclear"),
        default="unclear",
    )
    return parser.parse_args()


def _roles_for(role_arg: str) -> tuple[BridgeProviderRole, ...]:
    if role_arg == "both":
        return ALL_ROLES
    return (role_arg,)  # type: ignore[return-value]


async def _run_role(
    role: BridgeProviderRole,
    endpoints: dict[BridgeChain, str],
    client: httpx.AsyncClient,
) -> dict[BridgeChain, SmokeReport]:
    reports: dict[BridgeChain, SmokeReport] = {}
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
    return reports


async def async_main() -> int:
    args = parse_args()
    roles = _roles_for(args.role)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "not_executed",
                    "fixture_id": FIXTURE_ID,
                    "roles": list(roles),
                    "network_calls": 0,
                    "required_endpoint_env": {role: BRIDGE_ENDPOINT_ENV[role] for role in roles},
                    "methods_by_chain": {
                        chain: [request.method for request in bridge_requests(chain)]
                        for chain in CHAINS
                    },
                }
            )
        )
        return 0
    endpoints_by_role: dict[BridgeProviderRole, dict[BridgeChain, str]] = {}
    try:
        for role in roles:
            resolved = resolve_bridge_endpoints(
                execute=True,
                rules_status=args.rules_status,
                role=role,
                environment=dict(os.environ),
            )
            if resolved is None:
                raise RuntimeError("execute mode requires bridge endpoints")
            endpoints_by_role[role] = resolved
    except PermissionError as error:
        print(json.dumps({"status": "rule_restricted", "message": str(error)}))
        return 5
    except ValueError as error:
        print(json.dumps({"status": "invalid_input", "message": str(error)}))
        return 2

    reports_by_role: dict[BridgeProviderRole, dict[BridgeChain, SmokeReport]] = {}
    try:
        async with httpx.AsyncClient() as client:
            for role in roles:
                reports_by_role[role] = await _run_role(role, endpoints_by_role[role], client)
    except SensitiveDataError:
        print(json.dumps({"status": "security_blocked"}))
        return 4

    status = (
        "complete"
        if all(
            report.status == "complete"
            for reports in reports_by_role.values()
            for report in reports.values()
        )
        else "partial"
    )
    facts_by_role: dict[BridgeProviderRole, dict[str, object]] = {}
    if status == "complete":
        try:
            for role in roles:
                facts_by_role[role] = bridge_pair_facts(
                    reports_by_role[role]["base"], reports_by_role[role]["ethereum"]
                )
        except (KeyError, TypeError, ValueError):
            print(json.dumps({"status": "invalid_response"}))
            return 4

    cross_provider_decoded_match: bool | None = None
    if len(roles) == 2 and facts_by_role:
        try:
            assert_matching_provider_facts(
                facts_by_role["primary"],
                facts_by_role["verify"],
            )
            cross_provider_decoded_match = True
        except ValueError as error:
            print(json.dumps({"status": "cross_provider_mismatch", "message": str(error)}))
            return 4

    network_calls = sum(
        report.network_calls for reports in reports_by_role.values() for report in reports.values()
    )
    print(
        json.dumps(
            {
                "status": status,
                "fixture_id": FIXTURE_ID,
                "roles": list(roles),
                "network_calls": network_calls,
                "decoded_pair_match": bool(facts_by_role),
                "cross_provider_decoded_match": cross_provider_decoded_match,
                "facts_by_role": facts_by_role,
            }
        )
    )
    return 0 if status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
