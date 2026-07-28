# Fixture: FX-BASIC-EVM-002
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 04:32
> Status: Verifying

## 1. 목적

동일 Ethereum 블록에서 주소의 native ETH 잔액과 USDC `balanceOf`를
historical state로 조회하고 raw 정수와 decimals 적용값을 함께 검증한다.

## 2. 후보

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `BASIC-EVM-002` |
| 주소 | `0xa406bc6e...a7fdf` |
| 기준 블록 | `16642512` (`2023-02-16T16:34:23Z`) |
| ETH | `148897435437879000853` wei |
| USDC | `26470158088` raw, decimals `6` |
| 상태 | `verifying` — 두 archive 공급자 결과 일치 |

블록 태그의 상태는 블록 실행이 끝난 뒤의 post-state로 해석한다. 거래 직전
잔액과 혼동하지 않는다.

## 3. 부분·실패 경계

- archive state를 조회할 수 없으면 최신 잔액으로 대체하지 않고 `partial`이다.
- `decimals`만 누락되면 raw 잔액은 보존하되 사람이 읽는 수량은 `partial`이다.
- 부동소수점으로 raw 값을 손실하거나 조회 블록을 생략하면 실패다.

## 4. 승격 전 잔여

1. [x] QuickNode·Alchemy에서 ETH·USDC·decimals를 재현했다.
2. [x] timestamp exact·between·범위 밖·오선택 합성 oracle을 검증했다.
3. [ ] state 결과 계약과 `archive_required` 오류를 승인한다.

Provider별 raw SHA-256과 일치 결과는 [provider-replay.json](./provider-replay.json)에
고정했다.

## 5. Related Documents

- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `BASIC-EVM-002` 완료 조건
- **Technical_Specs**: [Reference Fixture Schema](../../../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) - 상태 증거 구조
- **QA_Validation**: [TASK-012 후보 보고서](../../24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 후보 선정 및 승격 조건
