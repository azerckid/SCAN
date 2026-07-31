"""Compare TASK-018 product analyzer facts with the independent verifier."""

import json

from verify_task_018_case_independent_verifier import PACKAGE, canonical_hash, recompute

from scan_tool.domain import validate_analysis_request
from scan_tool.slices.case_reconciliation import analyze_case_reconciliation_replay


def main() -> int:
    request = validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    ).root
    result = analyze_case_reconciliation_replay(
        request,
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    ).root
    product = result.results[0].value
    independent = recompute()
    if product != independent:
        print("FAIL TASK-018 analyzer facts differ from independent verifier")
        return 1
    print(
        f"PASS TASK-018 analyzer independent verification · fact_sha256={canonical_hash(product)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
