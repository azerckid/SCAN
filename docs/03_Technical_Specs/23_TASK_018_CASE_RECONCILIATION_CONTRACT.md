# TASK-018 Crime·Case Reconciliation Contract

> Created: 2026-07-31 11:00
> Status: Approved by TASK-018 blanket implementation authorization · Runtime implemented

## 1. Purpose and boundary

`case_reconciliation` composes already-reviewed analyzer fixtures into a bounded
incident timeline. It does not turn a public incident narrative into an on-chain
fact. The v1 product query is:

```json
{
  "analysis_type": "case_reconciliation",
  "query_kind": "reconstruct_incident",
  "inputs": {
    "case_category": "exploit",
    "seed_transaction_hash": "0x...",
    "source_fixture_refs": ["FX-FLOW-PATH-001", "FX-FLOW-REMERGE-001"],
    "max_timeline_entries": 8
  }
}
```

`case_category` accepts `phishing`, `address_poisoning`, `exploit`, `rug_pull`,
and `mixed`, but a category executes only when its reviewed source bundle exists.
An enum value is not evidence.

## 2. Required invariants

1. request fixture/category/seed/source-set must exactly match replay.
2. every source fixture is `confirmed`; `expected.json` and `evidence.json` are
   independently SHA-256 pinned. These documents are reviewed composition inputs,
   not a claim that TASK-018 re-ran the original provider RPC.
3. timeline ordering is `(block_number, transaction_index, stable edge ID)`.
4. unrelated inflows remain excluded; unresolved residual is preserved.
5. bounded budget exhaustion returns the ordered prefix as `partial`; it never
   becomes `failed` or silently claims full coverage.
6. conflicting acquired facts are `reconciliation_failed`; missing scope is
   `partial` when useful facts remain, otherwise `failed/source_unavailable`.
7. external chronology is `external_context`.
8. ownership, victim identity, exploit causation, and criminal intent remain
   `not_assessed` unless separate reviewed evidence explicitly proves them.

## 3. Result status

| Status | Contract |
|:---|:---|
| complete | Full requested scope, continuous coverage, and all mandatory evidence proved |
| partial | Useful confirmed technical facts exist, but case scope or attribution is incomplete |
| failed | Acquired evidence conflicts, hashes drift, or request↔replay binding fails |
`unsupported` is a Benchmark and selector-availability state, not an Analysis
result status. A direct runtime request without a reviewed fixture returns
`failed/source_unavailable` with `results: []`.

The v1 case analyzer is CLI path-bound because it validates sibling confirmed
fixture packages. `case_reconciliation` is therefore excluded from Operations
leaf-job selection until the Evidence Worker receives an approved package
transport; Planner hypotheses may describe the method but may not queue this
analysis type.

The confirmed Euler composition intentionally returns `partial`: it proves a
selected post-incident exit timeline, not the entire exploit.

## 4. Analysis I/O

- Schema: `0.2`
- chain: Ethereum mainnet (`chain_id=1`)
- result types: `case_reconciliation`, `case_context`
- public error codes: existing enum only
- new fixture requirement namespace: `REQ-CASE-*`
- runtime input: path-bound offline replay; byte-only replay is rejected because
  sibling confirmed fixture files must be hash-verified.

## 5. Problem coverage

| Problem | Current outcome |
|:---|:---|
| CRIME-EXP-001 | assisted — selected Euler exit path only |
| CRIME-PHISH-001 | unsupported — public source candidate, no reviewed raw fixture |
| CRIME-POISON-001 | unsupported — address-similarity and recovery fixture absent |
| CRIME-RUG-001 | unsupported — LP accounting/attribution fixture absent |
| MIXED-CASE-001 | unsupported — open-ended seed discovery remains absent |

No claim is promoted merely because AI proposed it. AI remains the mandatory
method planner; Python replays and the independent verifier establish facts.

## 6. Verification

- 11 deterministic negative oracles across all five categories
- stdlib-only independent verifier validates upstream content hashes and required
  PATH/REMERGE projections, then recomputes the Euler fact object
- product analyzer canonical fact must match the independent verifier hash
- CLI and contract-family regression tests
- full offline repository Gate
