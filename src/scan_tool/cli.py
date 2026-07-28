"""Command-line entry point for the SCAN tool."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from time import monotonic
from typing import Annotated, NoReturn

import typer
from pydantic import ValidationError

from scan_tool import __version__
from scan_tool.adapters.sqlite_operations import SQLiteOperationsRepository
from scan_tool.application.cli_runtime import (
    AnalysisUnavailable,
    CliRuntime,
)
from scan_tool.application.operations_snapshot import OperationsSnapshotBuilder
from scan_tool.application.operations_terminal import render_operations_snapshot
from scan_tool.application.submission import SubmissionCommand, SubmissionRecorder
from scan_tool.application.terminal import (
    EXIT_FAILED,
    EXIT_INPUT,
    EXIT_INTERRUPTED,
    EXIT_RESTRICTED,
    ProgressEvent,
    render_progress,
    render_result,
    safe_path_label,
)
from scan_tool.domain import (
    ContractViolation,
    validate_analysis_error,
    validate_analysis_id,
    validate_analysis_request,
    validate_analysis_result,
    validate_operations_document,
)
from scan_tool.domain.analysis_request import AnalysisRequest, RuleStatus
from scan_tool.domain.operations import OperationsDocument, SubmissionResponse

DATA_ROOT = Path(".scan")

app = typer.Typer(
    help="Evidence-first blockchain forensic tools for SCAN 2026.",
    invoke_without_command=True,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed package version and exit."),
    ] = False,
) -> None:
    """Run the SCAN command-line interface."""
    if version:
        typer.echo(__version__)
        raise typer.Exit


@app.command()
def validate(path: Annotated[Path, typer.Argument(help="Analysis I/O JSON file.")]) -> None:
    """Validate an Analysis I/O 0.1 request, result, or error document."""
    document = _read_json(path)
    schema = str(document.get("$schema", ""))
    try:
        if schema.endswith("analysis-request.schema.json"):
            model = validate_analysis_request(document)
            kind = f"request · {model.root.analysis_type}"
        elif schema.endswith("analysis-result.schema.json"):
            model = validate_analysis_result(document)
            kind = f"result · {model.root.status}"
        elif schema.endswith("analysis-error.schema.json"):
            model = validate_analysis_error(document)
            kind = f"error · {model.code}"
        else:
            _fail_input("schema_invalid", "unknown Analysis I/O schema")
    except ContractViolation as error:
        _fail_input(error.code.value, "; ".join(error.issues))
    typer.echo(f"VALID {safe_path_label(path)} · {kind}")


@app.command()
def analyze(
    request: Annotated[
        Path,
        typer.Option("--request", help="Analysis Request 0.1 JSON file."),
    ],
    evidence: Annotated[
        Path | None,
        typer.Option(
            "--evidence",
            help="Reviewed offline replay evidence JSON for a supported vertical slice.",
        ),
    ] = None,
) -> None:
    """Validate and dispatch a forensic analysis request."""
    started = monotonic()
    _progress("STARTING", f"request={safe_path_label(request)}")
    _progress("FEEDBACK", f"{(monotonic() - started) * 1000:.1f}ms")
    model = _validate_request_file(request)
    document = model.root
    _progress(
        "VALIDATED",
        f"{document.analysis_id} · {document.analysis_type} · "
        f"{'offline' if document.source_policy.offline_mode else 'live'}",
    )
    if evidence is not None:
        _progress("REPLAY", f"evidence={safe_path_label(evidence)}")
    try:
        with CliRuntime.open(DATA_ROOT) as runtime:
            try:
                runtime.register_request(model)
            except sqlite3.IntegrityError:
                _fail_input("invalid_input", "analysis_id already exists")

            if document.source_policy.rule_status == RuleStatus.RESTRICTED:
                runtime.storage.finish_run(document.analysis_id, "restricted")
                _progress("ERROR", "rule_restricted stage=source_policy attempts=0")
                typer.echo(f"FAILED {document.analysis_id} · first_error rule_restricted")
                raise typer.Exit(EXIT_RESTRICTED)

            try:
                result = runtime.execute_analysis(model, replay_path=evidence)
            except AnalysisUnavailable as error:
                runtime.storage.finish_run(document.analysis_id, "failed")
                _progress("ERROR", f"source_unavailable stage=analysis_dispatch · {error}")
                typer.echo(f"FAILED {document.analysis_id} · first_error source_unavailable")
                raise typer.Exit(EXIT_FAILED) from None
            except KeyboardInterrupt:
                runtime.storage.finish_run(document.analysis_id, "interrupted")
                _progress(
                    "INTERRUPTED",
                    f"{document.analysis_id} · checkpoint preservation attempted",
                )
                typer.echo(f"INTERRUPTED {document.analysis_id}")
                raise typer.Exit(EXIT_INTERRUPTED) from None
            except Exception:
                runtime.storage.finish_run(document.analysis_id, "failed")
                _fail_runtime(document.analysis_id, "analysis_dispatch")
            try:
                stored = runtime.save_result(model, result)
            except Exception:
                runtime.storage.finish_run(document.analysis_id, "failed")
                _fail_runtime(document.analysis_id, "result_persistence")
    except typer.Exit:
        raise
    except Exception:
        _fail_runtime(document.analysis_id, "cli_runtime")
    raise typer.Exit(
        render_result(
            stored.result,
            sys.stdout,
            sys.stderr,
            export_uris=stored.export_uris,
        )
    )


@app.command()
def resume(analysis_id: Annotated[str, typer.Argument(help="Existing analysis ID.")]) -> None:
    """Resume an existing analysis from its saved request and checkpoints."""
    analysis_id = _validated_analysis_id(analysis_id)
    _progress("STARTING", f"{analysis_id} · resume")
    if not (DATA_ROOT / "scan.sqlite3").exists():
        _not_found(analysis_id)
    try:
        with CliRuntime.open(DATA_ROOT) as runtime:
            request = runtime.load_request(analysis_id)
            if request is None:
                _not_found(analysis_id)
            try:
                result = runtime.execute_analysis(request)
            except AnalysisUnavailable as error:
                _progress("ERROR", f"source_unavailable stage=analysis_dispatch · {error}")
                typer.echo(f"FAILED {analysis_id} · first_error source_unavailable")
                raise typer.Exit(EXIT_FAILED) from None
            except Exception:
                runtime.storage.finish_run(analysis_id, "failed")
                _fail_runtime(analysis_id, "analysis_dispatch")
            try:
                stored = runtime.save_result(request, result)
            except Exception:
                runtime.storage.finish_run(analysis_id, "failed")
                _fail_runtime(analysis_id, "result_persistence")
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        _progress("INTERRUPTED", f"{analysis_id} · checkpoint preservation attempted")
        typer.echo(f"INTERRUPTED {analysis_id}")
        raise typer.Exit(EXIT_INTERRUPTED) from None
    except Exception:
        _fail_runtime(analysis_id, "cli_runtime")
    raise typer.Exit(
        render_result(
            stored.result,
            sys.stdout,
            sys.stderr,
            export_uris=stored.export_uris,
        )
    )


@app.command()
def show(analysis_id: Annotated[str, typer.Argument(help="Existing analysis ID.")]) -> None:
    """Show a persisted Analysis Result summary."""
    analysis_id = _validated_analysis_id(analysis_id)
    if not (DATA_ROOT / "scan.sqlite3").exists():
        _not_found(analysis_id)
    try:
        with CliRuntime.open(DATA_ROOT) as runtime:
            result = runtime.load_result(analysis_id)
    except Exception:
        _fail_runtime(analysis_id, "result_load")
    if result is None:
        _not_found(analysis_id)
    raise typer.Exit(
        render_result(
            result.result,
            sys.stdout,
            sys.stderr,
            export_uris=result.export_uris,
        )
    )


@app.command()
def operations(
    bundle: Annotated[
        Path | None,
        typer.Option("--bundle", help="Validated Operations contract 0.1 JSON bundle."),
    ] = None,
    database: Annotated[
        Path | None,
        typer.Option("--database", help="Explicit SQLite v2 database path."),
    ] = None,
    competition_id: Annotated[
        str | None,
        typer.Option("--competition-id", help="Competition ID for SQLite read-back."),
    ] = None,
    elapsed_seconds: Annotated[
        int,
        typer.Option("--elapsed-seconds", min=0, help="Elapsed competition time."),
    ] = 0,
    remaining_seconds: Annotated[
        int,
        typer.Option("--remaining-seconds", min=0, help="Remaining competition time."),
    ] = 0,
    output: Annotated[
        str,
        typer.Option("--output", help="Snapshot output: terminal or json."),
    ] = "terminal",
) -> None:
    """Render a local, read-only Competition Operations snapshot."""
    if output not in {"terminal", "json"}:
        _fail_input("invalid_input", "output must be terminal or json")
    if (bundle is None) == (database is None):
        _fail_input("invalid_input", "provide exactly one of --bundle or --database")
    if database is not None and competition_id is None:
        _fail_input("invalid_input", "--competition-id is required with --database")
    if bundle is not None and competition_id is not None:
        _fail_input("invalid_input", "--competition-id is valid only with --database")
    try:
        document = _load_operations_document(
            bundle=bundle,
            database=database,
            competition_id=competition_id,
        )
        manifest = document.root.manifest
        snapshot_suffix = hashlib.sha256(manifest.competition_id.encode()).hexdigest()[:16].upper()
        snapshot = OperationsSnapshotBuilder().build(
            document,
            snapshot_id=f"SNAP-LOCAL-{snapshot_suffix}",
            elapsed_seconds=elapsed_seconds,
            remaining_seconds=remaining_seconds,
        )
        render_operations_snapshot(snapshot, sys.stdout, output_format=output)
    except ContractViolation as error:
        _fail_input(error.code.value, "; ".join(error.issues))


@app.command("mark-submitted")
def mark_submitted(
    database: Annotated[
        Path,
        typer.Option("--database", help="Explicit SQLite v2 database path."),
    ],
    competition_id: Annotated[str, typer.Option("--competition-id")],
    candidate_id: Annotated[str, typer.Option("--candidate-id")],
    response: Annotated[SubmissionResponse, typer.Option("--response")],
    confirm: Annotated[
        bool,
        typer.Option("--confirm", help="Confirm the answer was submitted manually in CTFd."),
    ] = False,
    actor_id: Annotated[str, typer.Option("--actor-id")] = "operator-local",
) -> None:
    """Record a manual CTFd response locally without making a network call."""
    if not confirm:
        _fail_input("invalid_input", "--confirm is required after manual submission")
    try:
        with SQLiteOperationsRepository(database) as repository:
            document = repository.load_document(competition_id)
            if document is None:
                _fail_input("invalid_input", "competition was not found in the local database")
            execution = SubmissionRecorder().record(
                document,
                SubmissionCommand(
                    competition_id=competition_id,
                    candidate_id=candidate_id,
                    response=response,
                    operator_confirmed=True,
                    actor_id=actor_id,
                ),
            )
            repository.apply_submission(
                execution.document,
                execution.submission,
                execution.event,
            )
    except typer.Exit:
        raise
    except (OSError, sqlite3.Error, ValidationError, ValueError):
        _fail_input("submission_record_failed", "manual submission record was not stored")
    typer.echo(
        f"RECORDED {execution.submission.submission_id} · "
        f"{candidate_id} · response {response.value} · network_calls 0"
    )


def _load_operations_document(
    *,
    bundle: Path | None,
    database: Path | None,
    competition_id: str | None,
) -> OperationsDocument:
    if bundle is not None:
        return validate_operations_document(_read_json(bundle))
    if database is None or competition_id is None:
        raise ValueError("operations input is incomplete")
    try:
        with SQLiteOperationsRepository(database) as repository:
            document = repository.load_document(competition_id)
    except (OSError, sqlite3.Error, ValueError):
        _fail_input("source_unavailable", "cannot read the explicit operations database")
    if document is None:
        _fail_input("source_unavailable", "competition was not found in the local database")
    return document


def _validate_request_file(path: Path) -> AnalysisRequest:
    try:
        return validate_analysis_request(_read_json(path))
    except ContractViolation as error:
        _fail_input(error.code.value, "; ".join(error.issues))


def _validated_analysis_id(value: str) -> str:
    try:
        return validate_analysis_id(value)
    except ContractViolation as error:
        _fail_input(error.code.value, "; ".join(error.issues))


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail_input("invalid_input", f"cannot read valid JSON from {safe_path_label(path)}")
    if not isinstance(value, dict):
        _fail_input("schema_invalid", "top-level JSON value must be an object")
    return value


def _progress(status: str, detail: str) -> None:
    render_progress((ProgressEvent(status, detail),), sys.stderr)


def _fail_input(code: str, message: str) -> NoReturn:
    _progress("ERROR", f"{code} · {message}")
    raise typer.Exit(EXIT_INPUT)


def _not_found(analysis_id: str) -> NoReturn:
    _progress("ERROR", f"source_unavailable · analysis not found: {analysis_id}")
    typer.echo("Next: check the analysis ID and local data directory.")
    raise typer.Exit(EXIT_FAILED)


def _fail_runtime(analysis_id: str, stage: str) -> NoReturn:
    _progress("ERROR", f"source_unavailable stage={stage} attempts=0")
    typer.echo(f"FAILED {analysis_id} · first_error source_unavailable")
    raise typer.Exit(EXIT_FAILED)
