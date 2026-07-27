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
from scan_tool.slices.auth import analyze_auth_replay
from scan_tool.slices.dex import analyze_dex_replay
from scan_tool.slices.freeze import analyze_freeze_replay

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/05_QA_Validation/examples/analysis"
DEX_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/raw-replay.json"
)
AUTH_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "docs/05_QA_Validation/fixtures/FX-EVM-AUTH-001/raw-replay.json"
)
FREEZE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "docs/05_QA_Validation/fixtures/FX-EVM-FREEZE-001/raw-replay.json"
)
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
    assert "--evidence" in result.stderr


def test_dex_analyze_persists_and_show_renders_the_same_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(DEX_FIXTURE),
        ],
    )
    shown = runner.invoke(app, ["show", "AN-FX-SVC-DEX-001"])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert "COMPLETE AN-FX-SVC-DEX-001" in output
        assert "asset_in" in output and "amount_raw=25000000000" in output
        assert "pool_output" in output
        assert "amount_raw=14449515027026387018" in output
        assert "user_net_output" in output
        assert "artifact://sha256/" in output
    assert ".scan/" not in analyzed.stdout + shown.stdout
    assert "ethereum.publicnode.com" not in analyzed.stdout + analyzed.stderr
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result("AN-FX-SVC-DEX-001")
        assert stored is not None
        assert [item.result_type for item in stored.result.root.results] == [
            "asset_in",
            "pool_output",
            "user_net_output",
        ]
        markdown = runtime.storage.get_run_artifact("AN-FX-SVC-DEX-001", "evidence_markdown")
        assert markdown is not None
        markdown_text = runtime.artifacts.read(markdown).decode()
        assert "25000000000" in markdown_text
        assert markdown_text.count("14449515027026387018") >= 2
        assert runtime.storage.count("checkpoints") == 1


def test_dex_missing_internal_call_is_partial_and_preserves_pool_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "missing-call.json"
    write_json(request_path, load_document("dex", "request"))
    replay = json.loads(DEX_FIXTURE.read_text())
    replay["internal_calls"] = []
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 3
    assert "PARTIAL AN-FX-SVC-DEX-001" in result.stdout
    assert "pool_output" in result.stdout
    assert "user_net_output" not in result.stdout
    assert "trace_unavailable" in result.stderr


def test_dex_reconciliation_failure_is_structured_failed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "mismatch.json"
    write_json(request_path, load_document("dex", "request"))
    replay = json.loads(DEX_FIXTURE.read_text())
    swap = replay["receipt"]["logs"][2]
    swap["data"] = f"{swap['data'][:-1]}b"
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 4
    assert "FAILED AN-FX-SVC-DEX-001" in result.stdout
    assert "reconciliation_failed" in result.stderr
    assert "source_unavailable" not in result.stdout + result.stderr


def test_invalid_dex_replay_does_not_persist_or_echo_local_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "unsafe.json"
    write_json(request_path, load_document("dex", "request"))
    replay = json.loads(DEX_FIXTURE.read_text())
    replay["local_path"] = "/Users/private-evidence/source.json"
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )
    combined = result.stdout + result.stderr

    assert result.exit_code == 4
    assert "decode_failed" in combined
    assert "/Users/private-evidence/" not in combined
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.storage.count("checkpoints") == 0
        assert runtime.storage.count("artifacts") == 3


def test_auth_analyze_persists_and_show_renders_exact_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("auth", "request"))

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(AUTH_FIXTURE),
        ],
    )
    shown = runner.invoke(app, ["show", "AN-FX-EVM-AUTH-001"])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert "COMPLETE AN-FX-EVM-AUTH-001" in output
        assert "approval" in output
        assert "consumed_delta_raw=4500000" in output
        assert "authorization_consumption" in output
        assert "amount_raw=4500000" in output
        assert "theft_or_phishing_attribution" in output
        assert "theft_or_phishing_claim=False" in output
        assert "artifact://sha256/" in output
    assert "eth.drpc.org" not in analyzed.stdout + analyzed.stderr
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result("AN-FX-EVM-AUTH-001")
        assert stored is not None
        assert [item.result_type for item in stored.result.root.results] == [
            "approval",
            "allowance_lifecycle",
            "authorization_consumption",
            "theft_or_phishing_attribution",
        ]
        assert runtime.storage.count("checkpoints") == 1


def test_auth_missing_archive_state_is_partial_and_preserves_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "missing-state.json"
    write_json(request_path, load_document("auth", "request"))
    replay = json.loads(AUTH_FIXTURE.read_text())
    replay["allowance_query"]["snapshots"] = replay["allowance_query"]["snapshots"][:2]
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 3
    assert "PARTIAL AN-FX-EVM-AUTH-001" in result.stdout
    assert "approval" in result.stdout
    assert "authorization_consumption" not in result.stdout
    assert "archive_required" in result.stderr


def test_auth_keyboard_interrupt_resumes_from_saved_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("auth", "request"))

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_auth_replay", interrupt)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(AUTH_FIXTURE),
        ],
    )

    assert result.exit_code == 130
    assert "INTERRUPTED AN-FX-EVM-AUTH-001" in result.stdout
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.storage.count("checkpoints") == 1

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_auth_replay",
        analyze_auth_replay,
    )
    resumed = runner.invoke(app, ["resume", "AN-FX-EVM-AUTH-001"])
    assert resumed.exit_code == 0
    assert "COMPLETE AN-FX-EVM-AUTH-001" in resumed.stdout
    assert "resumed yes" in resumed.stdout


def test_invalid_auth_replay_is_not_persisted_or_echoed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "unsafe.json"
    write_json(request_path, load_document("auth", "request"))
    replay = json.loads(AUTH_FIXTURE.read_text())
    replay["local_path"] = "/Users/private-auth/source.json"
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )
    combined = result.stdout + result.stderr

    assert result.exit_code == 4
    assert "decode_failed" in combined
    assert "/Users/private-auth/" not in combined
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.storage.count("checkpoints") == 0
        assert runtime.storage.count("artifacts") == 3


def test_freeze_analyze_persists_and_show_renders_transitions_and_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("freeze", "request"))

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(FREEZE_FIXTURE),
        ],
    )
    shown = runner.invoke(app, ["show", "AN-FX-EVM-FREEZE-001"])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert "COMPLETE AN-FX-EVM-FREEZE-001" in output
        assert "blacklist_transition" in output
        assert "before=False" in output
        assert "after=True" in output
        assert "unblacklist_transition" in output
        assert "before=True" in output
        assert "after=False" in output
        assert "official_context_scope" in output
        assert "current_sanctions_status=not_assessed" in output
        assert "criminal_intent=not_assessed" in output
        assert "artifact://sha256/" in output
    assert "eth.drpc.org" not in analyzed.stdout + analyzed.stderr
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result("AN-FX-EVM-FREEZE-001")
        assert stored is not None
        assert [item.result_type for item in stored.result.root.results] == [
            "blacklist_transition",
            "unblacklist_transition",
            "official_context_scope",
        ]
        assert runtime.storage.count("checkpoints") == 1


def test_freeze_missing_unblacklist_is_partial_and_preserves_blacklist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "missing-unblacklist.json"
    write_json(request_path, load_document("freeze", "request"))
    replay = json.loads(FREEZE_FIXTURE.read_text())
    replay["unblacklist"] = None
    replay["state_query"]["snapshots"] = replay["state_query"]["snapshots"][:2]
    replay["explorer_cross_check"] = replay["explorer_cross_check"][:1]
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 3
    assert "PARTIAL AN-FX-EVM-FREEZE-001" in result.stdout
    assert "blacklist_transition" in result.stdout
    assert "unblacklist_transition" not in result.stdout
    assert "evidence_incomplete" in result.stderr


def test_freeze_keyboard_interrupt_resumes_from_saved_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("freeze", "request"))

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_freeze_replay", interrupt)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(FREEZE_FIXTURE),
        ],
    )

    assert result.exit_code == 130
    assert "INTERRUPTED AN-FX-EVM-FREEZE-001" in result.stdout
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.storage.count("checkpoints") == 1

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_freeze_replay",
        analyze_freeze_replay,
    )
    resumed = runner.invoke(app, ["resume", "AN-FX-EVM-FREEZE-001"])
    assert resumed.exit_code == 0
    assert "COMPLETE AN-FX-EVM-FREEZE-001" in resumed.stdout
    assert "resumed yes" in resumed.stdout


def test_invalid_freeze_replay_is_not_persisted_or_echoed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    evidence_path = tmp_path / "unsafe.json"
    write_json(request_path, load_document("freeze", "request"))
    replay = json.loads(FREEZE_FIXTURE.read_text())
    replay["local_path"] = "/Users/private-freeze/source.json"
    write_json(evidence_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(evidence_path),
        ],
    )
    combined = result.stdout + result.stderr

    assert result.exit_code == 4
    assert "decode_failed" in combined
    assert "/Users/private-freeze/" not in combined
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.storage.count("checkpoints") == 0
        assert runtime.storage.count("artifacts") == 3


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


def test_dex_keyboard_interrupt_resumes_from_saved_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_dex_replay", interrupt)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(DEX_FIXTURE),
        ],
    )

    assert result.exit_code == 130
    assert "INTERRUPTED AN-FX-SVC-DEX-001" in result.stdout
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        assert runtime.load_request("AN-FX-SVC-DEX-001") is not None
        assert runtime.storage.count("checkpoints") == 1

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_dex_replay",
        analyze_dex_replay,
    )
    resumed = runner.invoke(app, ["resume", "AN-FX-SVC-DEX-001"])
    assert resumed.exit_code == 0
    assert "COMPLETE AN-FX-SVC-DEX-001" in resumed.stdout
    assert "resumed yes" in resumed.stdout


def test_unexpected_runtime_error_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = tmp_path / "request.json"
    write_json(request_path, load_document("dex", "request"))
    canary = "SCAN_CANARY_SECRET_RUNTIME"

    def fail(*_: object, **__: object) -> None:
        raise RuntimeError(f"{canary} /Users/private-user/provider.json")

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_dex_replay", fail)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(DEX_FIXTURE),
        ],
    )
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
