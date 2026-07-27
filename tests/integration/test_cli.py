from typer.testing import CliRunner

from scan_tool.cli import app

runner = CliRunner()


def test_help_describes_evidence_first_cli() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Evidence-first blockchain forensic tools" in result.stdout


def test_version_matches_package_metadata() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"
