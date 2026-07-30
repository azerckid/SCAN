# Fixture: FX-ACTOR-COMMON-FUNDER-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30 14:19
> Status: Candidate 0.1 · Negative Oracle Passed · Analyzer Partial · Verifier Pending

## 1. 목적

하나의 seed가 네 주소로 직접 보낸 동일 raw 금액을 관계 후보로 보존한다.
직접 funding만으로 소유·공모를 확정하지 않는다.

## 2. 현재 근거

- confirmed `FX-FLOW-REMERGE-001` raw replay
- 네 direct seed output과 raw amount
- immutable source/expected SHA-256

## 3. 남은 Gate

- [x] 완결성·제외·partial/failed/negative oracle 기준과 승격 blocker를 docs-only
  [완결성 계약](../../60_TASK_015_COMMON_FUNDER_COMPLETENESS_CONTRACT.md)으로 고정
- [ ] 각 주소의 bounded prehistory·initial-inflow completeness
  (continuous-scope archive 필요, live/archive Gate 대기)
- [ ] faucet·paymaster·service exclusion (reviewed 분류 source 필요)
- [x] common-funder scope·금액·truth-promotion negative oracle — 6개·2회 결정성
- [x] 제품 analyzer가 completeness 미증명을 `partial`로 보존
- [ ] 독립 Verifier
- [ ] `verifying` 승격 검토

## 4. Related Documents

- [Source FLOW fixture](../FX-FLOW-REMERGE-001/README.md)
- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
- [Promotion Readiness](../../54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md)
- [Completeness 계약·Blocker](../../60_TASK_015_COMMON_FUNDER_COMPLETENESS_CONTRACT.md)
