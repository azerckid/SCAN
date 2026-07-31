"""TASK-017 Bitcoin CLI/runtime integration."""

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.adapters.artifacts import ArtifactStore
from scan_tool.adapters.sqlite_storage import DDL, SQLiteStorage
from scan_tool.cli import app
from scan_tool.domain import validate_analysis_request

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-BTC-UTXO-001"
runner = CliRunner()


def test_bitcoin_cli_requires_and_accepts_bitcoin_chain_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    args = [
        "analyze",
        "--request",
        str(PACKAGE / "analysis-request.json"),
        "--evidence",
        str(PACKAGE / "raw-replay.json"),
    ]
    mismatch = runner.invoke(app, args)
    complete = runner.invoke(app, [*args, "--chain-scope", "bitcoin"])

    assert mismatch.exit_code == 2
    assert "chain_scope_mismatch" in mismatch.stderr
    assert complete.exit_code == 0, complete.stdout
    assert "COMPLETE AN-BTC-UTXO-001" in complete.stdout
    assert "bitcoin_utxo_summary" in complete.stdout


def test_bitcoin_cli_never_calls_the_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    def blocked(*_: object, **__: object) -> None:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr("socket.socket", blocked)
    result = runner.invoke(
        app,
        [
            "analyze",
            "--request",
            str(PACKAGE / "analysis-request.json"),
            "--evidence",
            str(PACKAGE / "raw-replay.json"),
            "--chain-scope",
            "bitcoin",
        ],
    )
    assert result.exit_code == 0


def test_sqlite_v1_database_requires_explicit_migration_for_bitcoin(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy.sqlite3"
    legacy_ddl = DDL.replace(
        "CHECK(chain_id IN (0, 1))",
        "CHECK(chain_id = 1)",
        1,
    )
    with sqlite3.connect(database) as connection:
        connection.executescript(legacy_ddl)
        connection.execute("PRAGMA user_version = 1")

    request = validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    )
    artifact_store = ArtifactStore(tmp_path / "artifact-store")
    request_artifact = artifact_store.write(
        (PACKAGE / "analysis-request.json").read_bytes(),
        media_type="application/json",
        artifact_kind="request",
    )
    with (
        SQLiteStorage(database) as storage,
        pytest.raises(
            ValueError,
            match="explicitly approved backup-and-migration",
        ),
    ):
        storage.create_run(
            request,
            request_artifact,
            tool_version="task-017-test",
        )

    with sqlite3.connect(database) as connection:
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'analysis_runs'"
        ).fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        run_count = connection.execute("SELECT count(*) FROM analysis_runs").fetchone()[0]
        artifact_count = connection.execute("SELECT count(*) FROM artifacts").fetchone()[0]

    assert "chain_id = 1" in table_sql
    assert version == 1
    assert run_count == 0
    assert artifact_count == 0
