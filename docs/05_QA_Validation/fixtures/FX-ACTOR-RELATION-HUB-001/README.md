# Fixture: FX-ACTOR-RELATION-HUB-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30 04:00
> Status: Verifying 0.1 · Negative Oracle / Independent Verifier Passed

## 1. 목적

서로 다른 두 주소가 공개 USDC contract와 상호작용한 사실을 보존하되,
공용 hub 때문에 두 actor를 하나로 묶지 않는 false-positive 사례다.

## 2. 현재 근거

- confirmed `FX-SVC-DEX-001`의 USDC transfer
- confirmed `FX-EVM-AUTH-001`의 USDC approval·consumption
- 각 raw/expected artifact SHA-256

## 3. 남은 Gate

- [x] public-hub·subject-swap negative oracle — 6개·2회 결정성
- [x] 독립 Verifier·두 번 결정성
- [x] `verifying` 승격
- [ ] 제품 analyzer·최종 승격

## 4. Related Documents

- [DEX source fixture](../FX-SVC-DEX-001/README.md)
- [AUTH source fixture](../FX-EVM-AUTH-001/README.md)
- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
