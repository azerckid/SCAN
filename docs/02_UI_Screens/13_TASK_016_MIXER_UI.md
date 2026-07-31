# TASK-016 Mixer Flow(SVC-MIX-001) Evaluation UI
> Created: 2026-07-31 08:00
> Last Updated: 2026-07-31 08:30
> Status: Static Preview · Fixture Confirmed

## 1. 목적

`SVC-MIX-001`의 mixer deposit/withdraw candidate 평가 화면 계약을 정의한다.
[Mixer Flow 계약](../03_Technical_Specs/23_TASK_016_MIXER_CONTRACT_PROPOSAL.md)의
request/result 분리, candidate strength tags, `not_assessed` attribution 경계를
시각화한다.

Preview: [12_task_016_mixer_preview.html](./previews/12_task_016_mixer_preview.html)

## 2. 화면 구조

- 좌측 Request: `subject_address`, `pool_address`, `observation_window`.
- 중앙 Result: `pool_flow_judgment`, deposit fact, withdraw candidates, exclusions.
- 우측 Evidence: deposit event, withdraw events, candidate set, pool label.

## 3. 상태 표현

### Complete
deposit fact + withdraw event facts + pool label assertion 교차검증.
`linkage_strength=candidate` 유지. ownership/criminality `not_assessed`.

### Partial
deposit 또는 withdraw leg·label artifact 미확보.

### Failed
scope 합성·window abuse·single-exit confirmed 승격·attribution assessed.

## 4. Fact · Assertion · Heuristic · Not assessed

- **confirmed fact**: deposit TX, withdraw event logs, pool denomination match.
- **evidence-backed assertion**: OFAC/Tornado Cash pool label.
- **heuristic candidate**: withdraw linkage (`linkage_strength=candidate`).
- **not_assessed**: `attribution.ownership`, `attribution.criminality`.

## 5. Related Documents

- [Mixer 계약](../03_Technical_Specs/23_TASK_016_MIXER_CONTRACT_PROPOSAL.md)
- [Final Promotion Receipt](../05_QA_Validation/72_TASK_016_MIXER_FINAL_PROMOTION_RECEIPT.md)
