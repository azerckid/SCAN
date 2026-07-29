"""Run the repository-wide offline quality gate."""

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    (sys.executable, "-m", "ruff", "check", "."),
    (sys.executable, "-m", "ruff", "format", "--check", "."),
    (sys.executable, "-m", "pytest"),
    (
        sys.executable,
        "docs/05_QA_Validation/scripts/validate_fixture_schemas.py",
    ),
    (
        sys.executable,
        "docs/05_QA_Validation/scripts/validate_analysis_schemas.py",
    ),
    (
        sys.executable,
        "scripts/check_analysis_schema.py",
    ),
    (
        sys.executable,
        "scripts/check_operations_schema.py",
    ),
    (
        sys.executable,
        "scripts/check_repository_traceability.py",
    ),
    (
        sys.executable,
        "scripts/check_repository_security.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_012_negative_oracles.py",
    ),
    (
        sys.executable,
        "scripts/check_task_012_analysis_contract_proposal.py",
    ),
    (
        sys.executable,
        "scripts/check_task_012_ui_preview.py",
    ),
    (
        sys.executable,
        "scripts/check_task_013_replay_gate.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_013_negative_oracles.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_013_independent_verifier.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_013_analyzer_independent_verification.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_014_negative_oracles.py",
    ),
    (
        sys.executable,
        "scripts/verify_task_014_independent_verifier.py",
    ),
)


def main() -> None:
    """Run each quality command and stop at the first failure."""
    for command in COMMANDS:
        subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


if __name__ == "__main__":
    main()
