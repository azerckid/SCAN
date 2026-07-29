"""Replay one TASK-013 candidate against one configured EVM provider."""

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
from scan_tool.application.task_013_replay import (
    FIXTURE_IDS,
    Task013FixtureId,
    run_task_013_replay,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=FIXTURE_IDS, required=True)
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
    fixture_id: Task013FixtureId = args.fixture
    role: ProviderRole = args.role
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "not_executed",
                    "fixture_id": fixture_id,
                    "role": role,
                    "network_calls": 0,
                    "required_endpoint_env": ROLE_ENDPOINT_ENV[role],
                }
            )
        )
        return 0
    try:
        endpoint = require_execution_allowed(
            execute=True,
            rules_status=args.rules_status,
            environment=os.environ,
            role=role,
        )
        output_root = resolve_output_root(
            Path(f".scan/live-provider-smoke/task-013-replay/{fixture_id}"),
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
            report = await run_task_013_replay(
                fixture_id=fixture_id,
                role=role,
                endpoint=endpoint,
                output_root=output_root,
                client=client,
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
                "report": f"task-013-replay://{fixture_id}/{report_path.name}",
            }
        )
    )
    return 0 if report.status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
