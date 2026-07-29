# TASK-012 Negative Oracle 검증 보고서
> Created: 2026-07-29 04:16
> Last Updated: 2026-07-29 04:32
> Status: Offline 24 Passed Twice · Independent Trace Pending

## 1. 목적과 판정

TASK-012 범용 EVM 분석기 구현 전에 당시 `verifying` 상태였던 네 fixture의
complete·partial·failed 경계를 합성 반례로 고정한다. 이 작업은 제품
Analysis type이나 live adapter를 구현하지 않고, fixture 승격에 사용할
negative oracle 계약과 오프라인 판정기만 추가한다.

**판정: 24개 oracle을 동일 입력으로 두 번 실행해 모두 같은 결과를 얻었다.
당시 독립 trace와 credential 회전은 미완료였다. 이후 offline provenance
정책에 따라 fixture는 `confirmed 0.2`로 승격했다.**

## 2. 실행 범위

| Fixture | Oracle 수 | 검증 범위 | 결과 |
|:---|---:|:---|:---:|
| `FX-BASIC-EVM-001` | 4 | malformed/checksum, RPC 부재, gas limit fee 오용 | pass |
| `FX-BASIC-EVM-002` | 9 | state 4개 + timestamp exact/between/range/wrong selection 5개 | pass |
| `FX-EVM-TOKEN-001` | 5 | 실패 TX, 무관 signature, 다른 token, zero value, pagination | pass |
| `FX-EVM-TOKEN-002` | 6 | trace 부재, value 부재, 실패 call, 복수 inflow, truncation, top-level 대체 | pass |
| **합계** | **24** | synthetic offline · deterministic 2회 | **pass** |

## 3. 산출물

- `fixtures/TASK-012-NEGATIVE-ORACLES.json`
  - strict manifest, 24개 고유 oracle ID, expected outcome
- `src/scan_tool/application/task_012_negative_oracles.py`
  - 외부 I/O가 없는 순수 판정기와 필수 ID 집합
- `scripts/verify_task_012_negative_oracles.py`
  - manifest를 두 번 실행하고 결정성·expected 일치를 검사
- `tests/unit/test_task_012_negative_oracles.py`
  - 필수 집합 누락·expected drift·핵심 partial/filter 회귀
- `scripts/verify.py`
  - repository-wide offline Gate에 oracle 검증을 포함

## 4. 경계

- 네트워크 호출: `0`
- endpoint·credential 사용: 없음
- Analysis I/O·Operations Schema 변경: 없음
- TASK-012 제품 analyzer·CLI wiring: 이 보고서 실행 당시 미구현, 이후 적용
- live provider timeout/rate-limit 반례: 미실행
- Alchemy 독립 trace 실패: 미해결

합성 oracle 통과는 raw provider replay나 독립 trace를 대체하지 않는다.
`confirmed` 승격은 credential 회전, 필요한 독립 trace, package 참조
무결성, 사용자 승인을 별도로 요구한다.

## 5. 다음 Gate

1. 회전된 credential 또는 새 독립 provider만 사용한다.
2. `PROVIDER-EVM-TRACE-VERIFY`에서 고정 TX call trace를 두 번 재현한다.
3. provider ID·method·retrieved_at·raw SHA-256·decoded call/value를 남긴다.
4. TOKEN-002 primary·independent 결과가 일치할 때만 trace Gate를 닫는다.
5. 네 fixture별 package 참조와 Analysis type 소비 계약을 승인한다.

## 6. 365 글로벌 평가 기준

| 기준 | 판정 |
|:---|:---|
| Functionality | 24개 complete·partial·failed 반례 결정성 통과 |
| Potential Impact | 네 문제와 후속 EVM/PATH 분석기의 공통 실패 경계 |
| Novelty | AI 추론이 아니라 raw 조건을 실증하는 negative oracle |
| UX | partial·failed 이유를 명시적 상태로 보존 |
| Open-source | secret·live 의존 없는 재현 가능한 manifest와 판정기 |
| Business Plan | N/A |

## 7. Related Documents

- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - 독립 재현·secret Gate
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 잠금
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - 네 verifying fixture
- **QA_Validation**: [TASK-012 Fixture 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - provider replay
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - live·반례 상태
