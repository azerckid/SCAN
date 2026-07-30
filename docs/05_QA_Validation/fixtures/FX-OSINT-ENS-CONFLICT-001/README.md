# Fixture: FX-OSINT-ENS-CONFLICT-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30 14:19
> Status: Verifying 0.1 · Negative Oracle / Independent Verifier Passed

## 1. 목적

`nick.eth`의 forward address와 해당 주소의 reverse primary name을 동일한
고정 block에서 대조한다. 일치 결과를 소유권 증거로 승격하지 않는다.

## 2. 현재 근거

- block `25,640,270`
- forward resolver/address raw result
- reverse resolver/name raw result
- 동일 probe 두 번의 SHA-256 일치

## 3. 남은 Gate

- [x] Alchemy·Blockscout fixed-block forward/reverse decoded 값 일치
- [x] QuickNode 429·Chainstack 403 실패를 성공으로 추론하지 않고 보존
- [x] forward/reverse mismatch·latest substitution negative oracle — 6개·2회 결정성
- [x] 독립 Verifier·두 번 결정성
- [x] `verifying` 승격
- [x] 제품 analyzer·독립 canonical hash 대조
- [ ] fixed-block fact와 현재 ownership을 동일시하지 않는 승격 문구 확인
- [ ] 최종 승격

## 4. Artifacts

- [Fixed-block raw replay](./artifacts/sha256/a1ed2bfc3bb65b0717afeb979fc92b68658f2ee9391f458a67ad2c5ef246ce2c.json)
- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
- [Promotion Readiness](../../54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md)
