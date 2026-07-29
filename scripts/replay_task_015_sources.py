"""Replay one TASK-015 ENS source candidate against one configured provider."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    ROLE_ENDPOINT_ENV,
    ProviderRole,
    require_execution_allowed,
    resolve_output_root,
    write_report,
)
from scan_tool.application.security import SensitiveDataError
from scan_tool.application.task_015_source_replay import (
    FIXTURE_IDS,
    Task015EnsFixtureId,
    run_task_015_ens_replay,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BLOCKSCOUT_RPC = "https://eth.blockscout.com/api/eth-rpc"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=FIXTURE_IDS, required=True)
    parser.add_argument(
        "--role",
        choices=("primary", "verify", "trace", "blockscout"),
        required=True,
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--rules-status",
        choices=("allowed", "restricted", "unclear"),
        default="unclear",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    fixture_id: Task015EnsFixtureId = args.fixture
    role_name: str = args.role
    if not args.execute:
        endpoint_requirement = (
            "public_blockscout" if role_name == "blockscout" else ROLE_ENDPOINT_ENV[role_name]
        )
        print(
            json.dumps(
                {
                    "status": "not_executed",
                    "fixture_id": fixture_id,
                    "role": role_name,
                    "network_calls": 0,
                    "required_endpoint": endpoint_requirement,
                }
            )
        )
        return 0
    try:
        provider_id_override = None
        if role_name == "blockscout":
            if args.rules_status != "allowed":
                raise PermissionError("live provider replay requires rules_status=allowed")
            role: ProviderRole = "verify"
            endpoint = BLOCKSCOUT_RPC
            provider_id_override = "BLOCKSCOUT-ETH-RPC"
        else:
            role = role_name
            endpoint = require_execution_allowed(
                execute=True,
                rules_status=args.rules_status,
                environment=os.environ,
                role=role,
            )
        output_root = resolve_output_root(
            Path(f".scan/live-provider-smoke/task-015-replay/{fixture_id}"),
            REPOSITORY_ROOT,
        )
    except PermissionError as error:
        print(json.dumps({"status": "rule_restricted", "message": str(error)}))
        return 5
    except ValueError as error:
        print(json.dumps({"status": "invalid_input", "message": str(error)}))
        return 2
    if endpoint is None:
        raise RuntimeError("execute mode requires an endpoint")
    try:
        async with httpx.AsyncClient() as client:
            report = await run_task_015_ens_replay(
                fixture_id=fixture_id,
                role=role,
                endpoint=endpoint,
                output_root=output_root,
                client=client,
                provider_id_override=provider_id_override,
            )
        report_path = write_report(report, output_root)
    except SensitiveDataError:
        print(json.dumps({"status": "security_blocked"}))
        return 4
    except (TypeError, ValueError):
        print(json.dumps({"status": "invalid_response"}))
        return 4
    print(
        json.dumps(
            {
                "status": report.status,
                "fixture_id": fixture_id,
                "provider_id": report.provider_id,
                "network_calls": report.network_calls,
                "report": f"task-015-replay://{fixture_id}/{report_path.name}",
            }
        )
    )
    return 0 if report.status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
