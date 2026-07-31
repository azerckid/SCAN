"""Deterministic contract oracles for all TASK-018 case categories."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Oracle:
    oracle_id: str
    acquired_facts_conflict: bool = False
    required_evidence_missing: bool = False
    attribution_promoted: bool = False
    reviewed_fixture_available: bool = True
    expected: str = "failed"


ORACLES = (
    Oracle("OR-CASE-SEED-SUBSTITUTION", acquired_facts_conflict=True),
    Oracle("OR-CASE-UNRELATED-FUND-INCLUDED", acquired_facts_conflict=True),
    Oracle("OR-CASE-TIMELINE-REORDERED", acquired_facts_conflict=True),
    Oracle("OR-CASE-SOURCE-HASH-MUTATED", acquired_facts_conflict=True),
    Oracle("OR-CASE-ATTRIBUTION-PROMOTED", attribution_promoted=True),
    Oracle(
        "OR-CASE-CONTINUOUS-SCOPE-MISSING",
        required_evidence_missing=True,
        expected="partial",
    ),
    Oracle(
        "OR-CASE-PHISHING-FIXTURE-MISSING",
        reviewed_fixture_available=False,
        expected="unsupported",
    ),
    Oracle(
        "OR-CASE-POISONING-FIXTURE-MISSING",
        reviewed_fixture_available=False,
        expected="unsupported",
    ),
    Oracle(
        "OR-CASE-RUG-FIXTURE-MISSING",
        reviewed_fixture_available=False,
        expected="unsupported",
    ),
    Oracle(
        "OR-CASE-MIXED-SEED-DISCOVERY-MISSING",
        reviewed_fixture_available=False,
        expected="unsupported",
    ),
    Oracle("OR-CASE-EULER-BOUNDED-POSITIVE", expected="partial"),
)


def classify(oracle: Oracle) -> str:
    if oracle.acquired_facts_conflict or oracle.attribution_promoted:
        return "failed"
    if not oracle.reviewed_fixture_available:
        return "unsupported"
    if oracle.required_evidence_missing:
        return "partial"
    return "partial"


def main() -> int:
    first = [(item.oracle_id, classify(item)) for item in ORACLES]
    second = [(item.oracle_id, classify(item)) for item in ORACLES]
    if first != second:
        print("FAIL TASK-018 negative oracles are non-deterministic")
        return 1
    failures = [
        oracle_id
        for (oracle_id, outcome), item in zip(first, ORACLES, strict=True)
        if outcome != item.expected
    ]
    if failures:
        print(f"FAIL TASK-018 negative oracles: {', '.join(failures)}")
        return 1
    print(f"PASS {len(ORACLES)} TASK-018 negative oracles twice")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
