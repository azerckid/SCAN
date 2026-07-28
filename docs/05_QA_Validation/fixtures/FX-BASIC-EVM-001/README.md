# Fixture: FX-BASIC-EVM-001
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 04:25
> Status: Verifying

## 1. 목적

Ethereum 입력 문자열을 주소, transaction hash, block hash/number와 잘못된
입력으로 구분하고, RPC에서 확인한 기본 필드를 재현하는 후보 fixture다.

## 2. 후보

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `BASIC-EVM-001` |
| 체인 | Ethereum (`chain_id` 1) |
| 기준 블록 | `16642512` (`0xfdf1d0`) |
| 기준 TX | `0xbbdaad89...55fa5` |
| EOA | `0xA406bC6E...A7FDF` |
| Contract | `0xEf1c6E67...4BF6B` |
| 상태 | `verifying` — QuickNode·Alchemy decoded 결과 일치 |
| 재사용 기준점 | confirmed `FX-SVC-DEX-001`의 공개 TX |

## 3. 채점 범위

- 길이만으로 단정하지 않고 RPC 조회 결과까지 연결한다.
- TX의 block, from/to, value, nonce, status와 실제 수수료를 raw 값으로
  채점한다.
- EOA와 contract는 같은 블록의 `eth_getCode` 결과로 구분한다.
- block hash와 number가 같은 block을 가리키는지 확인한다.
- 잘못된 짧은 hex는 `invalid`로 남기며 RPC 오류 원문을 답에 섞지 않는다.

## 4. 승격 전 잔여

1. [x] transaction·receipt·block·code를 QuickNode·Alchemy에서 재현했다.
2. [x] malformed/checksum 분류 합성 oracle을 두 번 검증했다.
3. [ ] fixture를 소비할 Analysis type과 오류 계약을 승인한다.

Provider별 raw SHA-256과 일치 결과는 [provider-replay.json](./provider-replay.json)에
고정했다.

## 5. Related Documents

- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `BASIC-EVM-001` 완료 조건
- **Technical_Specs**: [Coverage 확장 Brief](../../../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-EVM-CORE 범위
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - RPC·탐색기 제약
- **QA_Validation**: [TASK-012 후보 보고서](../../24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 선정 근거와 잔여 Gate
