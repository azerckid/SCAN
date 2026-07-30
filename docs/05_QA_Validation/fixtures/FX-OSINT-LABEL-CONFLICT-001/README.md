# Fixture: FX-OSINT-LABEL-CONFLICT-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30 04:23
> Status: Candidate 0.1 · Negative Oracle Passed · Verifier pending

## 1. 목적

서로 다른 공개 source가 같은 주소에 부여한 category·role assertion을
출처별로 보존하고, 하나의 소유·범죄 사실로 자동 병합하지 않는 사례다.

## 2. 현재 근거

- pinned OpenRAIL research/testing sample의 선택 행
- pinned MIT community config
- Ethereum block `25,640,270`의 ENS name → address raw replay

Etherscan label은 사용하지 않는다.

## 3. 남은 Gate

- [x] Alchemy·Blockscout fixed-block ENS decoded 값 일치
- [x] QuickNode 429·Chainstack 403 실패를 성공으로 추론하지 않고 보존
- [x] category conflict negative oracle — 6개·2회 결정성
- [ ] 독립 Verifier·두 번 결정성
- [ ] `verifying` 승격 검토

## 4. Artifacts

- [Selected dataset row](./artifacts/sha256/15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475.csv)
- [ENS fixed-block replay](./artifacts/sha256/762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b.json)
- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
