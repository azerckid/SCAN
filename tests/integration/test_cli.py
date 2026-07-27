"""TASK-005 CLI command, renderer, exit-code, and redaction tests."""

import copy
import io
import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import CliRuntime
from scan_tool.application.terminal import ProgressEvent, render_progress, render_result
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_result

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/05_QA_Validation/examples/analysis"
runner = CliRunner()


def load_document(name: str, kind: str) -> dict[str, object]:
    return json.loads((EXAMPLES / f"{name}-{kind}.json").read_text())


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value))


def structured_error(code: str = "source_unavailable") -> dict[str, object]:
    return {
        "error_id": f"ERR-{code.upper().replace('_', '-')}",
        "code": code,
        "message": "The required source did not return a usable result.",
        "stage": "analysis_dispatch",
        "retryable": False,
        "attempt_count": 0,
    }


def result_with_status(status: str, *, code: str = "source_unavailable"):
    document = copy.deepcopy(load_document("dex", "result"))
    document["status"] = status
    if status == "partial":
        document["errors"] = [structured_error(code)]
    elif status == "failed":
        document["results"] = []
        document["evidence"] = []
        document["sources"] = []
        document["warnings"] = []
        document["errors"] = [structured_error(code)]
    return validate_analysis_result(document)


def test_help_describes_all_approved_commands() -> None:
    result = runner.invoke(
        app,
        ["--help"],
        env={"NO_COLOR": "1", "COLUMNS": "80"},
    )

    assert result.exit_code == 0
    assert "Evidence-first blockchain forensic tools" in result.stdout
    assert "\x1b" not in result.stdout
    assert max(len(line) for line in result.stdout.splitlines()) <= 80
    for command in ("analyze", "validate", "resume", "show"):
        assert command in result.stdout


@pytest.mark.parametrize("command", ("analyze", "validate", "resume", "show"))
def test_each_approved_command_has_help(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_version_matches_package_metadata() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_validate_accepts_request_and_rejects_invalid_json(tmp_path: Path) -> None:
    valid = tmp_path / "request.json"
    invalid = tmp_path / "broken.json"
    write_json(valid, load_document("dex", "request"))
    invalid.write_text("{")

    accepted = runner.invoke(app, ["validate", str(valid)])
    rejected = runner.invoke(app, ["validate", str(invalid)])

    assert accepted.exit_code == 0
    assert "VALID request.json · request · dex_swap" in accepted.stdout
    assert rejected.exit_code == 2
    assert "invalid_input" in rejected.stderr
    assert str(tmp_path) not in rejected.stdout + rejected.stderr


@pytest.mark.parametrize(
    ("status", "error_code", "exit_code"),
    (
        ("complete", "source_unavailable", 0),
        ("partial", "evidence_incomplete", 3),
        ("failed", "source_unavailable", 4),
        ("failed", "rule_restricted", 5),
        ("failed", "schema_invalid", 2),
    ),
)
def test_renderer_maps_status_and_error_to_exit_code(
    status: str,
    error_code: str,
    exit_code: int,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    actual = render_result(
        result_with_status(status, code=error_code),
        stdout,
        stderr,
    )

    assert actual == exit_code
    assert status.upper() in stdout.getvalue()
    assert "retry 0 · fallback 0" in stdout.getvalue()
    assert "\x1b" not in stdout.getvalue() + stderr.getvalue()
    assert "\r" not in stdout.getvalue() + stderr.getvalue()


def test_renderer_preserves_uint256_raw_value() -> None:
    result = validate_analysis_result(load_document("auth", "result"))
    stdout = io.StringIO()

    render_result(result, stdout, io.StringIO())

    assert (
        "115792089237316195423570985008687907853269984665640564039457584007913129639935"
        in stdout.getvalue()
    )
    assert "consumed_delta_raw=4500000" in stdout.getvalue()
    assert (
        "after_consumption_raw="
        "115792089237316195423570985008687907853269984665640564039457584007913125139935"
        in stdout.getvalue()
    )


def test_retry_details_stay_in_progress_and_final_summary_is_compressed() -> None:
    document = copy.deepcopy(load_document("dex", "result"))
    document["run"]["retry_count"] = 3  # type: ignore[index]
    document["run"]["fallback_count"] = 1  # type: ignore[index]
    result = validate_analysis_result(document)
    stdout = io.StringIO()
    stderr = io.StringIO()

    render_progress(
        (
            ProgressEvent("retry 1/3", "DS-EVM-RPC-PUBLIC · timeout"),
            ProgressEvent("retry 2/3", "DS-EVM-RPC-PUBLIC · timeout"),
            ProgressEvent("retry 3/3", "DS-EVM-RPC-PUBLIC · rate_limited"),
            ProgressEvent("fallback", "DS-EVM-RPC-PUBLIC -> DS-EXPLORER-EVM"),
        ),
        stderr,
    )
    render_result(result, stdout, stderr)

    assert stderr.getvalue().count("RETRY") == 3
    assert "FALLBACK" in stderr.getvalue()
    assert "retry 3 · fallback 1" in stdout.getvalue()
    assert "RETRY 1/3" not in stdout.getvalue()


def test_analyze_restricts_before_dispatch_and_returns_exit_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request = load_document("dex", "request")
    request["source_policy"]["rule_status"] = "restricted"  # type: ignore[index]
    request_path = tmp_path / "restricted.json"
    write_json(request_path, request)

    result = runner.invoke(app, ["analyze", "--request", str(request_path)])

    assert result.exit_code == 5
    assert "STARTING" in result.stderr
    assert "FEEDBACK" in result.stderr
    feedback = re.search(r"FEEDBACK\s+([0-9.]+)ms", result.stderr)
    assert feedback is not None and float(feedback.group(1)) < 400
    assert "rule_restricted" in result.stdout + result.stderr
    assert "FAILED AN-FX-SVC-DEX-001" in result.stdout
    assert (tmp_path / ".scan" / "scan.sqlite3").exists()


def test_analyze_reports_unavailable_vertical_slice_without_live_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))

    result = runner.invoke(app, ["analyze", "--request", str(request_path)])

    assert result.exit_code == 4
    assert "source_unavailable" in result.stdout + result.stderr
    assert "TASK-006" in result.stderr


def test_analyze_persists_and_show_renders_the_same_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))
    expected = validate_analysis_result(load_document("dex", "result"))
    monkeypatch.setattr("scan_tool.cli.execute_analysis", lambda _: expected)

    analyzed = runner.invoke(app, ["analyze", "--request", str(request_path)])
    shown = runner.invoke(app, ["show", "AN-FX-SVC-DEX-001"])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert "COMPLETE AN-FX-SVC-DEX-001" in output
        assert "pool_output" in output
        assert "artifact://sha256/" in output
    assert ".scan/" not in analyzed.stdout + shown.stdout


def test_show_unknown_id_has_no_empty_table_or_absolute_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["show", "AN-UNKNOWN-001"])

    assert result.exit_code == 4
    assert "analysis not found" in result.stderr
    assert "Next:" in result.stdout
    assert str(tmp_path) not in result.stdout + result.stderr
    assert not (tmp_path / ".scan").exists()


def test_resume_unknown_id_is_explicit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["resume", "AN-UNKNOWN-001"])

    assert result.exit_code == 4
    assert "STARTING" in result.stderr
    assert "analysis not found" in result.stderr


def test_keyboard_interrupt_maps_to_130_and_preserves_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))

    def interrupt(_: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.cli.execute_analysis", interrupt)
    result = runner.invoke(app, ["analyze", "--request", str(request_path)])

    assert result.exit_code == 130
    assert "INTERRUPTED AN-FX-SVC-DEX-001" in result.stdout
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.load_request("AN-FX-SVC-DEX-001") is not None


def test_unexpected_runtime_error_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))
    canary = "SCAN_CANARY_SECRET_RUNTIME"

    def fail(_: object) -> None:
        raise RuntimeError(f"{canary} /Users/private-user/provider.json")

    monkeypatch.setattr("scan_tool.cli.execute_analysis", fail)
    result = runner.invoke(app, ["analyze", "--request", str(request_path)])
    combined = result.stdout + result.stderr

    assert result.exit_code == 4
    assert "source_unavailable" in combined
    assert canary not in combined
    assert "/Users/private-user/" not in combined
    assert "Traceback" not in combined


def test_invalid_input_does_not_echo_secret_or_local_user_path(
    tmp_path: Path,
) -> None:
    canary = "SCAN_CANARY_SECRET_123"
    request = load_document("dex", "request")
    request["unexpected_secret"] = canary
    request_path = tmp_path / "secret.json"
    write_json(request_path, request)

    invalid_request = runner.invoke(app, ["validate", str(request_path)])
    missing_path = runner.invoke(app, ["validate", "/Users/private-user/request.json"])
    invalid_id = runner.invoke(app, ["show", "SCAN_CANARY_SECRET_123"])
    combined = (
        invalid_request.stdout
        + invalid_request.stderr
        + missing_path.stdout
        + missing_path.stderr
        + invalid_id.stdout
        + invalid_id.stderr
    )

    assert invalid_request.exit_code == 2
    assert missing_path.exit_code == 2
    assert invalid_id.exit_code == 2
    assert canary not in combined
    assert "/Users/private-user/" not in combined
