"""TASK-013 evm_special CLI persistence, partial, and resume tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.cli_runtime import CliRuntime
from scan_tool.cli import app
from scan_tool.slices.evm_special import analyze_evm_special_replay

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"
CASES = (
    ("FX-EVM-NFT-721-001", "nft_activity"),
    ("FX-EVM-NFT-1155-001", "nft_activity"),
    ("FX-EVM-PROXY-001", "proxy_history"),
)
runner = CliRunner()


def _path(fixture_id: str, name: str) -> Path:
    return FIXTURES / fixture_id / name


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value))


@pytest.mark.parametrize(("fixture_id", "result_type"), CASES)
def test_evm_special_analyze_persists_and_show_renders_exact_result(
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
        [
            "analyze",
            "--request",
            str(request_path),
            "--evidence",
            str(replay_path),
        ],
    )
    analysis_id = f"AN-{fixture_id}"
    shown = runner.invoke(app, ["show", analysis_id])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    for output in (analyzed.stdout, shown.stdout):
        assert f"COMPLETE {analysis_id}" in output
        assert result_type in output
        assert "artifact://sha256/" in output
    assert str(tmp_path) not in analyzed.stdout + analyzed.stderr
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result(analysis_id)
        assert stored is not None
        assert stored.result.root.schema_version == "0.2"
        assert runtime.storage.count("checkpoints") == 1


def test_erc1155_batch_subject_request_persists_exact_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-EVM-NFT-1155-001"
    analysis_id = "AN-FX-EVM-NFT-1155-BATCH-001"

    analyzed = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request-batch.json")),
            "--evidence",
            str(_path(fixture_id, "raw-replay.json")),
        ],
    )
    shown = runner.invoke(app, ["show", analysis_id])

    assert analyzed.exit_code == 0
    assert shown.exit_code == 0
    assert f"COMPLETE {analysis_id}" in analyzed.stdout
    assert f"COMPLETE {analysis_id}" in shown.stdout
    with CliRuntime.open(tmp_path / ".scan") as runtime:
        stored = runtime.load_result(analysis_id)
        assert stored is not None
        value = stored.result.root.results[0].value
        assert "batch_case" in value
        assert "single_case" not in value


def test_evm_special_incomplete_proxy_state_is_partial_and_preserves_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-EVM-PROXY-001"
    replay = json.loads(_path(fixture_id, "raw-replay.json").read_text())
    replay["storage_snapshots"] = [
        item for item in replay["storage_snapshots"] if item["role"] != "implementation_before"
    ]
    replay_path = tmp_path / "incomplete-proxy.json"
    _write_json(replay_path, replay)

    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(_path(fixture_id, "analysis-request.json")),
            "--evidence",
            str(replay_path),
        ],
    )

    assert result.exit_code == 3
    assert "PARTIAL AN-FX-EVM-PROXY-001" in result.stdout
    assert "proxy_history" in result.stdout
    assert "archive_required" in result.stderr


def test_evm_special_keyboard_interrupt_resumes_from_saved_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_id = "FX-EVM-NFT-721-001"

    def interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_evm_special_replay",
        interrupt,
    )
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
    assert "INTERRUPTED AN-FX-EVM-NFT-721-001" in interrupted.stdout

    monkeypatch.setattr(
        "scan_tool.application.cli_runtime.analyze_evm_special_replay",
        analyze_evm_special_replay,
    )
    resumed = runner.invoke(app, ["resume", "AN-FX-EVM-NFT-721-001"])

    assert resumed.exit_code == 0
    assert "COMPLETE AN-FX-EVM-NFT-721-001" in resumed.stdout
    assert "resumed yes" in resumed.stdout
