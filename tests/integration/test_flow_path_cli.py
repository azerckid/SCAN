"""TASK-014 flow_path CLI persistence, partial, and resume tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import CliRuntime
from scan_tool.cli import app

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    ("FX-FLOW-PATH-001", "trace_path"),
    ("FX-FLOW-REMERGE-001", "trace_remerge"),
    ("FX-FLOW-MULTI-001", "aggregate_origins"),
)
runner = CliRunner()


def _path(fixture_id: str, name: str) -> Path:
    return FIXTURES / fixture_id / name


@pytest.mark.parametrize(("fixture_id", "result_type"), CASES)
def test_flow_path_analyze_persists_and_show_renders_exact_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture_id: str,
    result_type: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = _path(fixture_id, "analysis-request.json")
    replay_path = _path(fixture_id, "raw-replay.json")

    analyzed = runner.invoke(
        app,
        ["analyze", "--request", str(request_path), "--evidence", str(replay_path)],
    )
    analysis_id = f"AN-{fixture_id}"
    shown = runner.invoke(app, ["show", analysis_id])

    assert analyzed.exit_code == 0, analyzed.stdout
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert f"COMPLETE {analysis_id}" in output
        assert result_type in output
    assert str(tmp_path) not in analyzed.stdout + analyzed.stderr
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result(analysis_id)
        assert stored is not None
        assert stored.result.root.schema_version == "0.2"
        assert runtime.storage.count("checkpoints") == 1


def test_flow_path_partial_returns_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-FLOW-PATH-001"
    replay = json.loads(_path(fixture_id, "raw-replay.json").read_text())
    replay["internal_edges"] = []
    replay_path = tmp_path / "partial-replay.json"
    replay_path.write_text(json.dumps(replay))

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(replay_path),
        ],
    )

    assert analyzed.exit_code == 3
    assert "PARTIAL AN-FX-FLOW-PATH-001" in analyzed.stdout
    assert "trace_unavailable" in analyzed.stdout


def test_flow_path_keyboard_interrupt_resumes_from_saved_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-FLOW-MULTI-001"
    analysis_id = f"AN-{fixture_id}"

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_flow_path_replay", interrupt)
    interrupted = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(_path(fixture_id, "raw-replay.json")),
        ],
    )
    assert interrupted.exit_code == 130
    assert f"INTERRUPTED {analysis_id}" in interrupted.stdout

    from scan_tool.slices.flow_path import analyze_flow_path_replay

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_flow_path_replay",
        analyze_flow_path_replay,
    )
    resumed = runner.invoke(app, ["resume", analysis_id])

    assert resumed.exit_code == 0
    assert f"COMPLETE {analysis_id}" in resumed.stdout
    assert "resumed yes" in resumed.stdout
