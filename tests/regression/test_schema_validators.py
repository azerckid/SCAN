import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS = (
    (
        "docs/05_QA_Validation/scripts/validate_fixture_schemas.py",
        "PASS 3 fixture packages",
    ),
    (
        "docs/05_QA_Validation/scripts/validate_analysis_schemas.py",
        "PASS 3 analysis request/result pairs",
    ),
)


@pytest.mark.parametrize(("script", "expected_output"), VALIDATORS)
def test_schema_validator_passes(script: str, expected_output: str) -> None:
    completed = subprocess.run(
        [sys.executable, script],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert expected_output in completed.stdout
