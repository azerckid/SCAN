"""TASK-018 CLI composition tests."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import AnalysisUnavailable, CliRuntime
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_request

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-CASE-EULER-EXIT-001"
runner = CliRunner()


def test_case_cli_returns_honest_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(PACKAGE / "analysis-request.json"),
            "--evidence",
            str(PACKAGE / "raw-replay.json"),
        ],
    )
    assert result.exit_code == 3, result.stdout
    assert "PARTIAL AN-FX-CASE-EULER-EXIT-001" in result.stdout
    assert "evidence_incomplete" in result.stdout


def test_case_runtime_rejects_byte_only_replay(tmp_path: Path) -> None:
    request = validate_analysis_request_json(PACKAGE / "analysis-request.json")
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        runtime.register_request(request)
        with pytest.raises(AnalysisUnavailable, match="requires --evidence"):
            runtime.execute_analysis(
                request,
                replay_body=(PACKAGE / "raw-replay.json").read_bytes(),
            )


def validate_analysis_request_json(path: Path):
    import json

    return validate_analysis_request(json.loads(path.read_text(encoding="utf-8")))
