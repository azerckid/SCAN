# Fixture: FX-EVM-TOKEN-001
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 04:25
> Status: Verifying

## 1. 목적

검색 시작 블록 이후 주소에서 나간 첫 USDC `Transfer` 이벤트를 찾아
수신자·raw 수량·transaction을 결정적으로 복원한다.

## 2. 후보

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-TOKEN-001` |
| From | `0xa406bc6e...a7fdf` |
| Token | USDC `0xa0b86991...6eb48` |
| 시작 블록 | `16642512` |
| 첫 outgoing | TX `0xbbdaad89...55fa5`, log `275` |
| To | `0xb4e16d01...8c9dc` |
| 수량 | `25000000000` raw = `25000` USDC |
| 상태 | `verifying` — 독립 block/filter 로그 재현 일치 |

Blockscout 호환 API를 `startblock=16642512`, `sort=asc`로 조회했을 때 첫
결과가 위 TX였고, receipt의 raw `Transfer` 로그와 일치했다.

## 3. 부분·실패 경계

- 범위 로그 API가 없고 주어진 TX의 receipt만 있으면 전송 사실은 알 수 있지만
  “첫 전송”은 입증할 수 없어 `partial`이다.
- 실패 receipt, 다른 토큰, `from` 불일치 이벤트는 후보에서 제외한다.
- explorer의 현재 라벨이나 가격은 채점하지 않는다.

## 4. 승격 전 잔여

1. [x] QuickNode·Alchemy의 address+topic+block `eth_getLogs`가 1건으로 일치했다.
2. [x] zero-value·다른 token·같은 블록 다중 로그·pagination 합성 oracle을 검증했다.
3. [ ] 검색 범위·정렬·pagination 계약을 승인한다.

Provider별 raw SHA-256과 filter 범위는
[provider-replay.json](./provider-replay.json)에 고정했다.

## 5. Related Documents

- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-TOKEN-001` 완료 조건
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 로그 소스 제약
- **QA_Validation**: [TASK-012 후보 보고서](../../24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 후보 선정 및 잔여 Gate
