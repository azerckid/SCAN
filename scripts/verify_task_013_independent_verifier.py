"""Run the TASK-013 independent verifier twice without network access."""

from pathlib import Path

from scan_tool.application.task_013_independent_verifier import verify_repository

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/05_QA_Validation/fixtures"


def main() -> None:
    first = verify_repository(FIXTURES)
    second = verify_repository(FIXTURES)
    if first != second:
        raise RuntimeError("TASK-013 independent verifier is not deterministic")
    requirement_count = sum(len(item["requirement_checks"]) for item in first)
    evidence_count = sum(item["evidence_value_checks"] for item in first)
    hashes = ", ".join(f"{item['fixture_id']}={item['calculated_sha256']}" for item in first)
    print(
        f"PASS TASK-013 independent Verifier: {len(first)} fixtures (verifying), "
        f"{requirement_count} requirements, {evidence_count} evidence values, "
        "2 deterministic runs"
    )
    print(f"TASK-013 calculated fact hashes: {hashes}")


if __name__ == "__main__":
    main()
