"""Replay one TASK-012 trace dialect after explicit Rules and credential Gates."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from scan_tool.application.provider_smoke import (
    require_execution_allowed,
    resolve_output_root,
    write_report,
)
from scan_tool.application.security import SensitiveDataError
from scan_tool.application.task_012_trace import (
    TraceDialect,
    dry_run_trace_plan,
    run_task_012_trace_replay,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dialect",
        choices=("debug_call_tracer", "parity_trace_transaction"),
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
    dialect: TraceDialect = args.dialect
    if not args.execute:
        print(json.dumps(dry_run_trace_plan(dialect), ensure_ascii=False, indent=2))
        return 0
    try:
        endpoint = require_execution_allowed(
            execute=True,
            rules_status=args.rules_status,
            environment=os.environ,
            role="trace",
        )
        output_root = resolve_output_root(
            Path(".scan/live-provider-smoke/task-012-trace"),
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
            report = await run_task_012_trace_replay(
                dialect=dialect,
                endpoint=endpoint,
                output_root=output_root,
                client=client,
            )
        report_path = write_report(report, output_root)
    except SensitiveDataError:
        print(json.dumps({"status": "security_blocked"}))
        return 4
    print(
        json.dumps(
            {
                "status": report.status,
                "provider_id": report.provider_id,
                "dialect": dialect,
                "network_calls": report.network_calls,
                "report": f"task-012-trace://{report_path.name}",
            }
        )
    )
    return 0 if report.status == "complete" else 4


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
