"""Run the TASK-016 CEX independent raw-first verifier twice."""

from pathlib import Path

from scan_tool.application.task_016_cex_independent_verifier import verify_repository

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "docs/05_QA_Validation/fixtures"


def main() -> None:
    first = verify_repository(FIXTURE_ROOT)
    second = verify_repository(FIXTURE_ROOT)
    if first != second:
        raise RuntimeError("TASK-016 CEX independent Verifier is not deterministic")
    print(
        f"PASS TASK-016 CEX independent Verifier: {len(first)} fixtures, "
        f"{sum(item['requirement_count'] for item in first)} requirements, "
        "2 deterministic runs"
    )
    print(
        "TASK-016 CEX calculated fact hashes: "
        + ", ".join(f"{item['fixture_id']}={item['calculated_sha256']}" for item in first)
    )


if __name__ == "__main__":
    main()
