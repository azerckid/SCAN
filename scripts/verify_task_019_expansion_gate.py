"""Final offline coverage-integrity gate for TASK-019."""

import json
from pathlib import Path

from scan_tool.application.expected_problem_benchmark import (
    CoverageLevel,
    ExpectedProblemBenchmarkReport,
    ExpectedProblemBenchmarkRunner,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json"
EXPECTED_COUNTS = {
    CoverageLevel.AUTOMATED: 17,
    CoverageLevel.ASSISTED: 7,
    CoverageLevel.UNSUPPORTED: 6,
}
FROZEN_CASE_BOUNDARY = {
    "CRIME-PHISH-001": CoverageLevel.UNSUPPORTED,
    "CRIME-POISON-001": CoverageLevel.UNSUPPORTED,
    "CRIME-EXP-001": CoverageLevel.ASSISTED,
    "CRIME-RUG-001": CoverageLevel.UNSUPPORTED,
    "MIXED-CASE-001": CoverageLevel.UNSUPPORTED,
    "MIXED-XCHAIN-001": CoverageLevel.UNSUPPORTED,
}


def _stable_projection(report: ExpectedProblemBenchmarkReport) -> dict[str, object]:
    return {
        "counts": (
            report.total_problems,
            report.automated,
            report.assisted,
            report.unsupported,
            report.executed,
            report.passed,
            report.failed,
        ),
        "cases": [
            {
                key: value
                for key, value in item.model_dump(mode="json").items()
                if key != "elapsed_ms"
            }
            for item in report.cases
        ],
    }


def verify() -> tuple[int, int, int]:
    runner = ExpectedProblemBenchmarkRunner(ROOT)
    manifest = runner.load_manifest(MANIFEST)
    counts = {
        level: sum(item.coverage is level for item in manifest.cases) for level in CoverageLevel
    }
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"TASK-019 coverage drift: {counts!r}")

    case_by_id = {item.problem_id: item for item in manifest.cases}
    for problem_id, expected_level in FROZEN_CASE_BOUNDARY.items():
        if case_by_id[problem_id].coverage is not expected_level:
            raise RuntimeError(f"TASK-019 unsupported/assisted boundary drift: {problem_id}")
    mixed = case_by_id["MIXED-XCHAIN-001"]
    if "COMPOSITION" not in mixed.blocking_gaps or mixed.fixture is not None:
        raise RuntimeError("MIXED-XCHAIN must remain deferred without an executable fixture")

    for case in manifest.cases:
        if case.coverage is not CoverageLevel.AUTOMATED:
            if case.fixture is not None or not case.blocking_gaps:
                raise RuntimeError(f"non-automated case overstates support: {case.problem_id}")
            continue
        fixture = case.fixture
        if fixture is None:
            raise RuntimeError(f"automated case lacks a fixture: {case.problem_id}")
        input_path = ROOT / "docs/05_QA_Validation/fixtures" / fixture.fixture_id / "input.json"
        input_document = json.loads(input_path.read_text())
        if input_document.get("fixture_id") != fixture.fixture_id:
            raise RuntimeError(f"fixture ID binding drift: {case.problem_id}")
        if input_document.get("status") != "confirmed":
            raise RuntimeError(f"automated fixture is not confirmed: {fixture.fixture_id}")

    first = runner.run(manifest)
    second = runner.run(manifest)
    for report in (first, second):
        if report.executed != 17 or report.passed != 17 or report.failed != 0:
            raise RuntimeError("TASK-019 automated replay Gate failed")
        if not all(
            item.status_complete
            and item.answer_exact
            and item.evidence_complete
            and item.requirements_complete
            and item.deterministic
            for item in report.cases
        ):
            raise RuntimeError("TASK-019 exact/evidence/requirement/determinism Gate failed")
    if _stable_projection(first) != _stable_projection(second):
        raise RuntimeError("TASK-019 two-run Benchmark projection is not deterministic")
    return first.automated, first.assisted, first.unsupported


def main() -> None:
    automated, assisted, unsupported = verify()
    print(
        "PASS TASK-019 expansion Gate: "
        f"Benchmark {automated}/{automated} twice, assisted {assisted}, "
        f"unsupported {unsupported}, confirmed-fixture and freeze boundaries preserved"
    )


if __name__ == "__main__":
    main()
