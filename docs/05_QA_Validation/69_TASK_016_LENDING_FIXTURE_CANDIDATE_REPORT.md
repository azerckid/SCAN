# TASK-016 Lending 공개 Fixture 후보 선정 보고서
> Created: 2026-07-31 07:17
> Last Updated: 2026-07-31 07:35
> Status: Selected · FX-SVC-LEND-001 confirmed

## 1. 목적

사용자 batch approval(2026-07-31)에 따라 `SVC-LEND-001`용 `FX-SVC-LEND-001`의
공개 Aave V2/V3 Ethereum LiquidationCall 후보를 선정한다. confirmed-fixture-before-analyzer
규칙을 유지하며 Bridge early-analyzer 예외는 적용하지 않는다.

## 2. 선택 결과

| 필드 | 값 |
|:---|:---|
| Fixture | `FX-SVC-LEND-001` |
| 문제 | `SVC-LEND-001` |
| Protocol | Aave V3 Pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` |
| Chain | Ethereum mainnet (`chain_id` 1) |
| Seed TX | `0x207745c3f3cbcdc4f31a5a9d89810278e2e6cef385cb1bbf0b2c4b4ccdac4a37` |
| Block | `21036015` |
| `subject_address` | `0x1b05437f4a5f6b21692e83af3eb5607683e6dead` (liquidator) |
| `subject_roles` | `["liquidator"]` |
| Observation window | blocks `21036000`–`21036030` |
| Event-only complete | yes — debt/collateral value legs matched to ERC-20 Transfer logs |
| PRIMARY | `https://ethereum.publicnode.com` |
| VERIFY | `https://ethereum.rpc.thirdweb.com` |
| 상태 | **selected** → `confirmed 0.1` ([70 Receipt](./70_TASK_016_LENDING_FINAL_PROMOTION_RECEIPT.md)) |

## 3. 선정 기준 적용

- ≥1 `LiquidationCall` on official Aave V3 Pool with pinned topic0
- Clear subject (liquidator) and bounded window
- All lending value legs from logs+Transfer (`receiveAToken=false`)
- Dual-provider distinct endpoints and distinct artifact bytes
- Attack/normal left `not_assessed`

## 4. 제외·캡처 메모

- Merkle `https://eth.merkle.io` returned HTTP 429 during capture
- 1rpc returned **identical** PRIMARY transaction bytes and was rejected (CEX P1 lesson)
- thirdweb produced distinct PRIMARY/VERIFY artifact bytes with matching immutable decoded facts
- `artifacts/capture-meta.json`은 6개 capability 각각의 승인된 provider ID·role·
  endpoint·method·request params·response SHA-256·capture time을 고정한다.
- 2026-07-31 KST live read-only 재검증에서 transaction·receipt·block의 immutable
  fields가 저장 artifact와 일치했다. 다만 두 공개 endpoint는 동일 upstream 또는
  운영자 오응답 가능성을 암호학적으로 제거하지 못하므로 신뢰 경계로 남는다.

## 5. Related Documents

- [Lending 계약](../03_Technical_Specs/19_TASK_016_LENDING_CONTRACT_PROPOSAL.md)
- [70 Final Promotion Receipt](./70_TASK_016_LENDING_FINAL_PROMOTION_RECEIPT.md)
- [Contest Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
