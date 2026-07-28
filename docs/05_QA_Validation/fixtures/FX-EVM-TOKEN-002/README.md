# Fixture: FX-EVM-TOKEN-002
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 02:08
> Status: Candidate

## 1. 목적

top-level `value=0`인 contract 호출 안에서 관심 주소로 실제 유입된 native
ETH를 internal call 기준으로 복원한다.

## 2. 후보

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-TOKEN-002` |
| TX | `0xbbdaad89...55fa5` |
| 관심 주소 | `0xa406bc6e...a7fdf` |
| top-level value | `0` wei |
| internal path | Universal Router → 관심 주소 |
| 실제 유입 | `14449515027026387018` wei |
| 상태 | `candidate` — 독립 trace 재현 전 |

이 사례는 top-level value만 합산하면 `0`이라는 오답이 되고, 성공 internal
call을 포함해야 실제 유입을 얻는 명확한 반례다.

## 3. 부분·실패 경계

- transaction·receipt는 있으나 trace/internal API가 없으면 `partial`이다.
- `is_error != 0` 또는 revert된 하위 호출은 합산하지 않는다.
- WETH `Withdrawal` 이벤트는 internal ETH 이동의 보조 정합 증거이지 call
  자체의 대체 증거가 아니다.

## 4. 승격 전 잔여

1. `debug_traceTransaction` 또는 다른 trace 공급자로 internal path를 재현한다.
2. 실패 internal call과 복수 유입 합산 반례를 추가한다.
3. trace 누락 `partial`과 raw internal call 모델을 승인한다.

## 5. Related Documents

- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-TOKEN-002` 완료 조건
- **Technical_Specs**: [Coverage 확장 Brief](../../../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - trace 최소 계약
- **QA_Validation**: [TASK-012 후보 보고서](../../24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 후보 선정 및 승격 조건
