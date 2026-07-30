# Fixture: FX-OSINT-LABEL-CONFLICT-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30
> Status: Confirmed 0.1 · Replacement Migrated · OpenRAIL Artifact Removed

## 1. 목적

공식 역사적 action, MIT community config의 protocol instance role,
고정 블록 ENS binding을 출처별로 보존하고 하나의 현재 제재·소유·범죄
사실로 자동 병합하지 않는 사례다.

## 2. 현재 근거

- confirmed SANCTIONS fixture에 연결된 OFAC 2022 historical action
- pinned MIT config의 `eth-01.tornadocash.eth`와 ETH `0.1` instance address
- Ethereum block `25,640,270`의 ENS name → address raw replay

Etherscan label은 사용하지 않는다.

## 3. 남은 Gate

- [x] Alchemy·Blockscout fixed-block ENS decoded 값 일치
- [x] QuickNode JSON-RPC `-32003`·Chainstack 403 실패를 성공으로 추론하지 않고 보존
- [x] category conflict negative oracle — 6개·2회 결정성
- [x] 독립 Verifier·두 번 결정성
- [x] `verifying` 승격
- [x] 제품 analyzer·독립 canonical hash 대조
- [x] OpenRAIL scoring·provenance dependency 제거
- [x] official projection·MIT config·ENS artifact에서 Verifier와 analyzer hash 재계산
- [x] 재배포 허가 미확인 OpenRAIL CSV artifact 삭제(참조 0건)
- [x] 최종 승격 검토·`confirmed` 승격([Promotion Receipt](../../58_TASK_015_LABEL_CONFIRMED_PROMOTION_RECEIPT.md))

## 4. Artifacts

- [Official historical action projection](./artifacts/sha256/2ddb426a2d404d4984345fb6026ca02932cd4313dd0db79b36f41617f34a9a34.json)
- [ENS fixed-block replay](./artifacts/sha256/c5da8824427364b20cc4582cb15a3704f20e4b15bb16b81dd52f7e5d6203bf4d.json)
- [Pinned community config](./artifacts/sha256/84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32.js)
- [Superseded OpenRAIL license investigation](./license-resolution.json)
- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
- [Promotion Readiness](../../54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md)
- [OpenRAIL License Resolution Receipt](../../55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md)
- [Source Replacement Review](../../57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md)

## 5. Superseded Historical Artifacts

아래 항목은 migration 이전 기록 보존용이며 active regression·scoring·
provenance에서 참조하지 않는다.

- OpenRAIL selected row — **파일 제거됨**(재배포 허가 미확인, `promotion_allowed: false`).
  SHA-256 `15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475`
  이력만 [license-resolution.json](./license-resolution.json)·[Resolution Receipt](../../55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md)에 보존.
- [Previous fixed-block ENS replay](./artifacts/sha256/762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b.json) — former subject `0xc3877028655ebe90b9447dd33de391c955ead267`, name `team4.vesting.contract.tornadocash.eth`(온체인 데이터, 이력 보존)
