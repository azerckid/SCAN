# Fixture: FX-EVM-TOKEN-002
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 12:30
> Status: Confirmed 0.2

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
| 상태 | `confirmed` — primary trace·confirmed internal call·Withdrawal 정합·반례 통과 |

이 사례는 top-level value만 합산하면 `0`이라는 오답이 되고, 성공 internal
call을 포함해야 실제 유입을 얻는 명확한 반례다.

## 3. 부분·실패 경계

- transaction·receipt는 있으나 trace/internal API가 없으면 `partial`이다.
- `is_error != 0` 또는 revert된 하위 호출은 합산하지 않는다.
- WETH `Withdrawal` 이벤트는 internal ETH 이동의 보조 정합 증거이지 call
  자체의 대체 증거가 아니다.

## 4. 승격 기록과 비차단 한계

1. [x] QuickNode `debug_traceTransaction`으로 internal path를 재현했다.
2. [x] Alchemy debug·parity 두 dialect가 모두 HTTP 400임을 별도 보고서로 보존했다.
3. [x] 실패 call·복수 유입·trace 누락 합성 oracle을 두 번 검증했다.
4. [x] `evm_core/native_inflow` raw internal call과 partial 오류 계약을 승인했다.

독립 Trace 공급자 성공 재현은 provenance 강화 항목으로 남지만, 기존
confirmed internal-call replay와 WETH Withdrawal 정합 및 반례 검증을 갖춘
offline fixture 승격을 차단하지 않는다.

Primary raw SHA-256과 독립 trace 실패는
[provider-replay.json](./provider-replay.json)에 함께 기록했다.

## 5. Related Documents

- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-TOKEN-002` 완료 조건
- **Technical_Specs**: [Coverage 확장 Brief](../../../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - trace 최소 계약
- **QA_Validation**: [TASK-012 후보 보고서](../../24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 후보 선정 및 승격 조건
