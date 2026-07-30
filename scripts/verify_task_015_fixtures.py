"""Run the independent TASK-015 verifier twice and print the pinned result hashes."""

from pathlib import Path

from scan_tool.application.task_015_independent_verifier import verify_repository

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"


def main() -> None:
    first = verify_repository(FIXTURE_ROOT)
    second = verify_repository(FIXTURE_ROOT)
    if first != second:
        raise SystemExit("FAIL TASK-015 independent Verifier is not deterministic")
    hashes = ", ".join(f"{item['fixture_id']}={item['calculated_sha256']}" for item in first)
    print(
        "PASS TASK-015 independent Verifier: "
        f"{len(first)} reviewed fixtures, "
        f"{sum(item['requirement_count'] for item in first)} requirements, "
        "2 deterministic runs"
    )
    print(f"TASK-015 calculated fact hashes: {hashes}")


if __name__ == "__main__":
    main()
