# TASK-018 Case Reconciliation Implementation and Verification Report

> Created: 2026-07-31 11:00
> Status: Analyzer implemented · Euler fixture confirmed · CRIME-EXP assisted

## 1. Scope

This unit adds `case_reconciliation/reconstruct_incident`, one confirmed derived
Euler exit fixture, a static UI contract, negative oracles, an independent
Verifier, CLI wiring, and regression tests.

It does not implement phishing attribution, lookalike-address classification, LP
rug accounting, or open-ended mixed-case seed discovery.

## 2. Evidence and license boundary

The scoring facts are recomputed from two existing confirmed FLOW fixtures:

- `FX-FLOW-PATH-001`
- `FX-FLOW-REMERGE-001`

Their `expected.json` and `evidence.json` bytes are SHA-256 pinned and their
required projections are independently re-derived. They are reviewed composition
inputs, not a claim that TASK-018 re-ran the original RPC capture. Euler's public
article is a URL-only, unscored chronology locator. The replay stores locator
metadata only; its page body is not copied or redistributed. No new live provider
call or secret is used.

## 3. Verification

| Gate | Result |
|:---|:---|
| request↔replay seed/category/source exact binding | PASS |
| source fixture status and SHA-256 | PASS |
| timeline ordering and bounded budget | PASS |
| unrelated inflow exclusion | PASS |
| `not_assessed` attribution boundary | PASS |
| 11 negative oracles ×2 | PASS |
| stdlib-only independent Verifier ×2 | PASS |
| product↔Verifier canonical fact hash | `412ea7438bf0cd113c22ca472149cd20222550b04ed3e13716e7c57032068535` |
| CLI path-bound replay | PASS |
| Full Gate | 631 tests · fixture 23 · Schema 72 · links 2052 · security 287 |

## 4. Coverage decision

- Automated remains **15**.
- Assisted becomes **7**: `CRIME-EXP-001` gains bounded selected-exit support.
- Unsupported becomes **8**.
- The automated pass headline remains **15/15**.

The fixture is confirmed while the analyzer result is partial. These statements
are compatible: fixture truth is stable, but it intentionally describes only a
bounded subset of the larger expected problem.

## 5. Remaining work

- CRIME-PHISH: public-source and raw replay Gate
- CRIME-POISON: lookalike and recovery-path fixture
- CRIME-RUG: LP event/accounting fixture
- MIXED-CASE: open-ended seed discovery and hypothesis falsification
- full exploit decode/causation for CRIME-EXP
