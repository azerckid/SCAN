# TASK-016 Mixer Flow(SVC-MIX-001) Analysis 계약 제안 (docs-only)
> Created: 2026-07-31 08:00
> Last Updated: 2026-07-31 08:30
> Status: Confirmed · Benchmark Automated

## 0. 이 문서의 위치

이 문서는 TASK-016 Wave 5의 **Mixer Flow(`SVC-MIX-001`)** adapter를
대안 B `mixer_flow` leaf type으로 정의한다. [WP-SERVICE 공통 계약(doc 20)](./20_TASK_016_SERVICE_COMMON_CONTRACT.md)의
불변식을 deposit/withdraw candidate-set 상황에 적용한다.

**현재 전제.** `FX-SVC-MIX-001`은 OFAC Tornado Cash pool label assertion·
0.1 ETH deposit·동일 denomination withdraw candidate 2건·negative oracle·
독립 Verifier·analyzer hash `4c8c4eb8041642ea514e4c7357d474bb4038b9f6eeea55a816aa2dae41484939`로
`confirmed`·Benchmark automated(16/16)·ASSISTED 6·UNSUPPORTED 8이다. Mixer는 thaw 완료. Lending·`MIXED-XCHAIN-001`은 이 브랜치에서 freeze/unsupported 유지다(Lending은 Draft PR #113 별도).

## 1. 대상 문제·정답 범위

**문제(SVC-MIX-001).** subject가 mixer pool에 deposit한 사실과, 관찰 창 내
matching-denomination withdraw **candidate set**을 평가한다.

- request 필수: `subject_address`, `pool_address`, `observation_window`.
- result: `pool_flow_judgment`, `deposit_fact`, `withdraw_event_facts[]`,
  `withdraw_candidates[]`, `label_assertions[]`, `false_positive_exclusions[]`.
- deposit↔withdraw **ownership link는 on-chain 증명 불가** → candidate만 허용.

**판정 경계.**

- `attribution.ownership`·`attribution.criminality`는 항상 `not_assessed`.
- 단일 exit·matching amount만으로 confirmed ownership 승격 금지.
- pool label은 evidence-backed assertion(Treasury press release)이지 truth가 아님.

## 2. Analysis I/O (대안 B)

| 필드 | 값 |
|:---|:---|
| `analysis_type` | `mixer_flow` |
| `query_kind` | `evaluate_mixer_candidates` |
| `schema_version` | `0.2` |
| `chain_id` | `1` |

Fixture requirements: `REQ-MIX-DEPOSIT`, `REQ-MIX-WITHDRAW-CANDIDATES`, `REQ-MIX-LABEL`.

## 3. complete · partial · failed

**complete.** deposit fact·withdraw event facts·gov pool label assertion이
PRIMARY/VERIFY 교차검증되고 withdraw linkage는 `heuristic_candidate`만 유지.

**partial.** deposit 또는 withdraw leg·label artifact·VERIFY coverage 부족.

**failed.** scope 합성·window abuse·heuristic→fact 승격·attribution assessed·
single-exit ownership confirmed 승격.

## 4. negative oracle (8 cases)

`task-016-mixer-negative-oracles-v0.1.json` — scope synthesis, unlabeled pool,
heuristic→fact, window abuse, criminality assessed, evidence omission,
single-exit promotion, complete match. 2회 결정성 검증.

## 5. Related Documents

- [Mixer UI](../02_UI_Screens/13_TASK_016_MIXER_UI.md)
- [Fixture 후보 보고서](../05_QA_Validation/71_TASK_016_MIXER_FIXTURE_CANDIDATE_REPORT.md)
- [Final Promotion Receipt](../05_QA_Validation/72_TASK_016_MIXER_FINAL_PROMOTION_RECEIPT.md)
