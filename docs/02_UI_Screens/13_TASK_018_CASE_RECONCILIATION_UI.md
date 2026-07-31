# TASK-018 Case Reconciliation UI

> Created: 2026-07-31 11:00
> Status: Approved under TASK-018 blanket authorization · Static Preview

## 1. Screen contract

The screen presents five layers in order:

1. request boundary: category, seed transaction, source fixture set, budget
2. technical timeline: ordered acquired facts only
3. reconciliation: included/excluded/unresolved funds
4. external context: source assertion, visually separate from chain facts
5. assessment boundary: ownership, causation, and intent

## 2. State contract

- `partial`: selected path is valid, full case scope is incomplete.
- `failed`: hashes, seed, source set, endpoints, or acquired facts conflict.
- `unsupported`: selector-level availability state for a category with no
  reviewed fixture; it is not an Analysis result row status.

The UI must never label a partial case “solved” or replace `not_assessed` with a
criminal-attribution badge.

## 3. Interaction and accessibility

- category buttons use `aria-pressed`.
- state buttons use `aria-pressed`.
- ArrowLeft/ArrowRight/Home/End move within each button group.
- status, evidence source, exclusion, and next action are text, not color only.
- loading/empty/stale remain Workbench-level states and do not masquerade as
  analysis results.

## 4. Preview Gate

- [x] five categories are visible
- [x] partial/failed/unsupported boundaries are distinct
- [x] unrelated inflow exclusion is visible
- [x] external context and `not_assessed` are visible
- [x] synthetic preview values are explicitly labeled
- [x] external network calls are absent

This approval is covered by the user's explicit TASK-018 blanket authorization.
