"""TASK-015 intel_context CLI persistence, partial, and resume tests."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import CliRuntime
from scan_tool.cli import app

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    ("FX-OSINT-LABEL-CONFLICT-001", "collect_label_claims"),
    ("FX-OSINT-SANCTIONS-HISTORY-001", "check_sanctions_exposure"),
    ("FX-OSINT-ENS-CONFLICT-001", "resolve_identity_clues"),
    ("FX-ACTOR-RELATION-HUB-001", "score_actor_relations"),
)
runner = CliRunner()


def _path(fixture_id: str, name: str) -> Path:
    return FIXTURES / fixture_id / name


@pytest.mark.parametrize(("fixture_id", "result_type"), CASES)
def test_intel_context_analyze_persists_and_show_renders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture_id: str,
    result_type: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(_path(fixture_id, "source-replay.json")),
        ],
    )
    analysis_id = f"AN-{fixture_id}"
    shown = runner.invoke(app, ["show", analysis_id])

    assert analyzed.exit_code == 0, analyzed.stdout
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert f"COMPLETE {analysis_id}" in output
        assert result_type in output
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result(analysis_id)
        assert stored is not None
        assert stored.result.root.schema_version == "0.2"
        assert runtime.storage.count("checkpoints") == 1


def test_common_funder_partial_returns_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-ACTOR-COMMON-FUNDER-001"
    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(_path(fixture_id, "source-replay.json")),
        ],
    )
    assert analyzed.exit_code == 3
    assert f"PARTIAL AN-{fixture_id}" in analyzed.stdout
    assert "evidence_incomplete" in analyzed.stdout


def test_intel_context_keyboard_interrupt_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-OSINT-ENS-CONFLICT-001"
    analysis_id = f"AN-{fixture_id}"

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("scan_tool.application.cli_runtime.analyze_intel_context_replay", interrupt)
    interrupted = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(_path(fixture_id, "source-replay.json")),
        ],
    )
    assert interrupted.exit_code == 130
    assert f"INTERRUPTED {analysis_id}" in interrupted.stdout

    from scan_tool.slices.intel_context import analyze_intel_context_replay

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_intel_context_replay",
        analyze_intel_context_replay,
    )
    resumed = runner.invoke(app, ["resume", analysis_id])
    assert resumed.exit_code == 0
    assert f"COMPLETE {analysis_id}" in resumed.stdout
    assert "resumed yes" in resumed.stdout
