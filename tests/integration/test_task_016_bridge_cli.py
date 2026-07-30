"""TASK-016 bridge_transfer CLI/runtime file-path requirement tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import AnalysisUnavailable, CliRuntime
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_request

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-BRG-001"
runner = CliRunner()


def test_bridge_transfer_cli_completes_with_evidence_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    request_path = PACKAGE / "analysis-request.json"
    replay_path = PACKAGE / "raw-replay.json"

    analyzed = runner.invoke(
        app,
        ["analyze", "--request", str(request_path), "--evidence", str(replay_path)],
    )

    assert analyzed.exit_code == 0, analyzed.stdout
    assert "COMPLETE AN-FX-SVC-BRG-001" in analyzed.stdout


def test_bridge_transfer_rejects_byte_only_replay_without_file_path(tmp_path: Path) -> None:
    """Evidence Worker only ever supplies replay bytes, never a file path. Bridge
    Transfer's replay references sibling content-addressed artifacts that a bare
    byte string cannot resolve, so this must fail loudly instead of silently
    degrading to a partial result.
    """
    request = validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    )
    replay_body = (PACKAGE / "raw-replay.json").read_bytes()

    with CliRuntime.open(tmp_path / ".scan") as runtime:
        runtime.register_request(request)
        with pytest.raises(AnalysisUnavailable, match="requires --evidence"):
            runtime.execute_analysis(request, replay_body=replay_body)
