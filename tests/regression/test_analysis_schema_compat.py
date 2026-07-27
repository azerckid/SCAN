import subprocess
import sys


def test_generated_schemas_match_approved_contract_probes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_analysis_schema.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "across 35 probes" in completed.stdout
