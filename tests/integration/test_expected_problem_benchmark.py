"""Expected-problem coverage and confirmed-fixture benchmark integration tests."""

import json
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scan_tool.application.expected_problem_benchmark import (
    APPROVED_EXPECTED_PROBLEM_IDS,
    CoverageLevel,
    ExpectedProblemBenchmarkManifest,
    ExpectedProblemBenchmarkRunner,
)
from scan_tool.cli import app

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json"


def _runner() -> ExpectedProblemBenchmarkRunner:
    return ExpectedProblemBenchmarkRunner(ROOT)


def test_manifest_covers_all_30_expected_problems_without_overstating_support() -> None:
    manifest = _runner().load_manifest(MANIFEST)
    counts = {
        level: sum(item.coverage is level for item in manifest.cases) for level in CoverageLevel
    }

    assert {item.problem_id for item in manifest.cases} == APPROVED_EXPECTED_PROBLEM_IDS
    assert counts == {
        CoverageLevel.AUTOMATED: 14,
        CoverageLevel.ASSISTED: 6,
        CoverageLevel.UNSUPPORTED: 10,
    }
    assert {
        item.problem_id for item in manifest.cases if item.coverage is CoverageLevel.AUTOMATED
    } == {
        "BASIC-EVM-001",
        "BASIC-EVM-002",
        "BTC-UTXO-001",
        "EVM-AUTH-001",
        "EVM-FREEZE-001",
        "EVM-NFT-001",
        "EVM-PROXY-001",
        "EVM-TOKEN-001",
        "EVM-TOKEN-002",
        "FLOW-EVM-001",
        "FLOW-EVM-002",
        "OSINT-LBL-001",
        "SVC-BRG-001",
        "SVC-DEX-001",
    }
    assert {
        item.problem_id for item in manifest.cases if item.coverage is CoverageLevel.ASSISTED
    } == {
        "ACTOR-REL-002",
        "BTC-CJ-001",
        "BTC-UTXO-002",
        "FLOW-MULTI-001",
        "OSINT-ENS-001",
        "OSINT-SAN-001",
    }


def test_confirmed_expected_problems_match_answers_evidence_and_requirements() -> None:
    report = _runner().run(_runner().load_manifest(MANIFEST))

    assert report.executed == report.passed == 14
    assert report.failed == 0
    assert report.automated_pass_rate == 1
    assert all(item.answer_exact for item in report.cases)
    assert all(item.evidence_complete for item in report.cases)
    assert all(item.requirements_complete for item in report.cases)
    assert all(item.deterministic for item in report.cases)
    bridge = next(item for item in report.cases if item.problem_id == "SVC-BRG-001")
    assert bridge.fixture_id == "FX-SVC-BRG-001"
    assert bridge.passed is True


def test_incorrect_answer_oracle_fails_the_automated_case() -> None:
    manifest = _runner().load_manifest(MANIFEST)
    target = next(item for item in manifest.cases if item.problem_id == "SVC-DEX-001")
    assert target.fixture is not None
    first_expected = target.fixture.expected_results[0].model_copy(
        update={"value": {"amount_raw": "1"}}
    )
    bad_fixture = target.fixture.model_copy(
        update={"expected_results": [first_expected, *target.fixture.expected_results[1:]]}
    )
    bad_target = target.model_copy(update={"fixture": bad_fixture})
    bad_manifest = manifest.model_copy(
        update={
            "cases": [
                bad_target if item.problem_id == bad_target.problem_id else item
                for item in manifest.cases
            ]
        }
    )

    report = _runner().run(bad_manifest)
    dex = next(item for item in report.cases if item.problem_id == "SVC-DEX-001")

    assert report.failed == 1
    assert dex.passed is False
    assert dex.findings == ["answer_exact"]


def test_manifest_cannot_escape_the_repository(tmp_path: Path) -> None:
    outside = tmp_path / "manifest.json"
    outside.write_text(json.dumps({"benchmark_version": "0.1"}))

    with pytest.raises(ValueError, match="repository file"):
        _runner().load_manifest(outside)


def test_manifest_rejects_a_substituted_problem_id() -> None:
    manifest_data = json.loads(MANIFEST.read_text())
    manifest_data["cases"][0]["problem_id"] = "BASIC-EVM-999"

    with pytest.raises(ValueError, match="approved expected-problem bank"):
        ExpectedProblemBenchmarkManifest.model_validate(manifest_data)


def test_benchmark_cli_runs_offline_and_reports_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*_: object, **__: object) -> socket.socket:
        raise AssertionError("benchmark attempted a network connection")

    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(socket, "socket", reject_network)
    result = CliRunner().invoke(
        app,
        ["benchmark", "--manifest", str(MANIFEST), "--output", "terminal"],
    )

    assert result.exit_code == 0
    assert "AUTOMATED 14 · ASSISTED 6 · UNSUPPORTED 10" in result.stdout
    assert "BENCHMARK 14/14 automated cases passed · network_mode offline" in result.stdout
