"""Run an explicitly allowed read-only EVM provider capability smoke."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    ROLE_ENDPOINT_ENV,
    ProviderRole,
    dry_run_plan,
    require_execution_allowed,
    run_smoke,
    write_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("primary", "verify", "trace"), required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--rules-status",
        choices=("allowed", "restricted", "unclear"),
        default="unclear",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".scan/live-provider-smoke"),
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    role: ProviderRole = args.role
    if not args.execute:
        print(json.dumps(dry_run_plan(role), ensure_ascii=False, indent=2))
        return 0
    try:
        endpoint = require_execution_allowed(
            execute=True,
            rules_status=args.rules_status,
            environment=os.environ,
            role=role,
        )
    except PermissionError as error:
        print(json.dumps({"status": "rule_restricted", "message": str(error)}))
        return 5
    except ValueError as error:
        print(json.dumps({"status": "invalid_input", "message": str(error)}))
        return 2
    if endpoint is None:
        raise RuntimeError("execute mode requires an endpoint")
    async with httpx.AsyncClient() as client:
        report = await run_smoke(
            role=role,
            endpoint=endpoint,
            output_root=args.output_root,
            client=client,
        )
    report_path = write_report(report, args.output_root)
    print(
        json.dumps(
            {
                "status": report.status,
                "provider_id": report.provider_id,
                "network_calls": report.network_calls,
                "report": f"smoke-report://{report_path.name}",
                "endpoint_env": ROLE_ENDPOINT_ENV[role],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report.status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
