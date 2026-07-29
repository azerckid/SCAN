# TASK-015 Negative Oracle 보고서
> Created: 2026-07-30 04:00
> Last Updated: 2026-07-30 04:00
> Status: Oracle Passed · Candidate Fixtures 5 · Verifier Pending · Runtime Not Implemented

## 1. 목적과 경계

이 문서는 TASK-015 Intelligence 후보 다섯 개의 claim·시점·관계 경계를
합성 오프라인 반례로 고정한다. 반례 통과는 source snapshot의 실제 사실을
독립 재계산했다는 뜻이 아니며, fixture를 `verifying` 또는 `confirmed`로
승격하지 않는다.

이번 단계에서 하지 않은 일:

- live source·RPC·검색 API 호출
- 독립 Verifier 또는 제품 `intel_context` analyzer
- Context Receipt 전환·구현 승인
- Benchmark 11/11 변경

## 2. Oracle 구성

| 범주 | Fixture | 사례 | 주요 경계 |
|:---|:---|---:|:---|
| label conflict | `FX-OSINT-LABEL-CONFLICT-001` | 6 | subject·row hash·자동 병합·truth 승격·ENS 부재 |
| sanctions history | `FX-OSINT-SANCTIONS-HISTORY-001` | 6 | direct match·timeline·stale current·범죄성 승격 |
| ENS resolution | `FX-OSINT-ENS-CONFLICT-001` | 6 | subject·forward/reverse·historical latest·소유권 승격 |
| common funder | `FX-ACTOR-COMMON-FUNDER-001` | 6 | seed scope·금액·prehistory·service exclusion·truth 승격 |
| relation hub | `FX-ACTOR-RELATION-HUB-001` | 6 | subject 분리·공용 hub 제외·source 부재·truth 승격 |
| **합계** | 5 candidate fixtures | **30** | category별 6개 |

결과 분포는 `failed` 18개, `partial` 7개, `complete` 5개다. 각 범주는
정상 경계 1개를 포함해, 반례만 맞히고 정상 입력을 전부 실패시키는 구현을
허용하지 않는다.

## 3. 결정성·정직성

`task-015-negative-oracles-v0.1.json`의 고정 ID 30개를 동일 프로세스에서
두 번 실행했고 순서·결과가 일치했다. manifest는 다음 drift를 거부한다.

- ID 누락·추가·중복
- category와 fixture ID 불일치
- boolean 계약 필드에 문자열·숫자 입력
- expected outcome·classification 불일치

Oracle은 synthetic facts만 평가한다. candidate의 `expected.json`을 계산
입력으로 쓰거나 source artifact의 값을 독립 재계산하지 않는다.

## 4. Verification Receipt

2026-07-30 04:00 KST 기준 focused Gate:

- TASK-015 unit: 4 tests PASS
- negative oracle: 30개 × 2회 PASS
- category 분포: 5 × 6
- outcome 분포: failed 18 · partial 7 · complete 5
- network call: 0
- fixture 상태: 5개 모두 `candidate`
- Benchmark: automated 11 · assisted 1 · unsupported 18 유지

Repository-wide Gate:

- 474 tests PASS
- fixture Schema 0.1: 18 packages PASS
- Analysis I/O: 48 probes PASS
- traceability: 1,602 links PASS
- security: 186 runtime/evidence files PASS

## 5. 다음 Gate

1. ENS 두 fixture의 제2 provider 또는 독립 저장 replay를 확보한다.
2. OFAC SLS version과 Actor bounded prehistory·service exclusion을 고정한다.
3. 독립 Verifier가 source/raw artifact에서 필수 사실을 재계산한다.
4. 조건을 충족한 fixture만 `verifying` 승격을 검토한다.
5. 그 뒤 `intel_context` 계약·Context Receipt·구현 승인을 진행한다.

## 6. Related Documents

- **QA_Validation**: [Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md) - oracle·Verifier Stop/Go
- **QA_Validation**: [Candidate Fixture Package 보고서](./48_TASK_015_CANDIDATE_FIXTURE_PACKAGE_REPORT.md) - 다섯 candidate package
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - 전체 fixture 상태
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock
