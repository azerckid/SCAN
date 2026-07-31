# FX-CASE-EULER-EXIT-001

> Status: Confirmed · Derived offline composition · Analyzer result: Partial

This fixture proves a bounded, selected post-incident ETH exit timeline by
recomputing two confirmed FLOW packages. It deliberately does **not** claim that
the selected transaction caused the exploit, that any address has a particular
owner, or that criminal intent is proven.

## Sources

- `FX-FLOW-PATH-001`: confirmed three-hop selected path
- `FX-FLOW-REMERGE-001`: confirmed four-branch remerge and unrelated-inflow exclusion
- Euler Finance public incident article: chronology context only; no page body is redistributed

The two source fixture `expected.json` and `evidence.json` files are pinned by
SHA-256 in `raw-replay.json`. Any mutation is rejected before reconciliation.

## Outcome boundary

- confirmed facts: selected transfers, ordering, branch count, merge node, exclusion
- external context: public incident chronology
- not assessed: ownership, victim identity, exploit causation, criminal intent
- partial reason: no open-ended seed discovery or continuous all-funds scan
