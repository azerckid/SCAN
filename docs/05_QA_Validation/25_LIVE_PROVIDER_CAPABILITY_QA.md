# Live Provider·AI Planner Capability QA
> Created: 2026-07-29 02:35
> Last Updated: 2026-07-29 11:00
> Status: EVM Fixture Common Replay Passed · Overall Partial

## 1. 목적

이 문서는 TASK-012 fixture 4개의 독립 재현과 EVM read-only 공급자·AI
Planner가 필요한 능력을 제공하는지 검증하는 실행 체크리스트다. 사용자가
승인한 대회 전 공급자 준비 점검으로 primary 7건·verify 6건 smoke와,
네 fixture를 위한 primary 10건·verify 9건의 read-only replay를 실행했다.
이는 공식 대회 Rules를 `allowed`로 확정한 것이 아니며 대회 중 live mode는
계속 `rules_gated`다.

fixture 공통 9개 decoded summary와 primary trace는 성공했다. Alchemy의
독립 trace는 debug·parity 두 dialect 모두 HTTP 400으로 실패했다.
negative oracle 24개는 합성 offline 입력으로 두 번 통과했다. credential
회전, live rate/timeout 반례와 AI Planner capability는 아직 미실행이므로
최종 상태는 `partial`이다. 독립 Trace는 엄격한 fixture 교차검증의 비차단
후속이며 실전 QuickNode 단일 Trace 실행을 막지 않는다.

## 2. 실행 전 보안 Gate

- [ ] 공식 Rules의 provider·model·data·tool mode가 허용 상태다.
- [ ] primary·verify credential을 회전하고 새 값이 로컬 환경에만 있으며 저장소·SQLite·fixture·artifact·대화에 없다.
- [x] endpoint query token과 Authorization header를 기록·출력하지 않는다.
- [x] EVM method allowlist는 read-only이고 signing·send method가 없다.
- [ ] canary secret이 성공·실패·timeout·fallback 출력에 나타나지 않는다.
- [ ] 회전된 provider endpoint mapping이 로컬 설정에만 존재한다.
- [x] output은 저장소 `.scan/live-provider-smoke/` 하위에만 생성된다.
- [ ] URL userinfo는 거부되고 구성된 URL/header secret이 guard에 전달된다.
- [ ] secret 차단은 원문·traceback 없이 `security_blocked`로 종료된다.

하나라도 실패하면 smoke를 시작하지 않는다.

## 3. EVM capability 실행표

| 검사 | Primary 결과 | Independent 결과 | 필수 증거 |
|:---|:---:|:---:|:---|
| chain ID | pass | pass | `0x1`, raw SHA 기록 |
| transaction | pass | pass | hash·block·from/to/value 일치 |
| receipt | pass | pass | status `0x1`, log count 5 일치 |
| block | pass | pass | number·hash·timestamp 일치 |
| filtered logs | pass | pass | USDC Transfer 23건·첫 5개 요약 일치 |
| historical call/state | pass | pass | block `0xfdf1d0`, decimals `6` 일치 |
| trace | pass | deferred | primary callTracer 성공, Alchemy HTTP 400·Chainstack HTTP 403; 독립 trace는 비차단 후속 |
| rate/timeout | offline injected pass | live not_executed | timeout·429·method-not-found→`invalid_response`·malformed 구조화, 실제 provider 측정 잔여 |

결과는 provider 문서의 지원 표시가 아니라 실제 계정과 대상 block에서
관찰한 값으로 채운다. 무료·유료 plan 차이도 실제 계정 범위만 기록한다.

### 3.1 TASK-012 fixture replay

| 항목 | Primary | Independent | 판정 |
|:---|:---:|:---:|:---|
| 고정 TX·receipt·block | pass | pass | decoded 일치 |
| subject/router historical code | pass | pass | empty/non-empty·byte length 일치 |
| historical native balance | pass | pass | raw wei 일치 |
| historical USDC balance·decimals | pass | pass | raw 값 일치 |
| address·topic·block 제한 USDC logs | pass | pass | 1건·TX/log index·amount 일치 |
| internal native inflow trace | pass | deferred | QuickNode raw 값 확보, 독립 trace는 fixture 교차검증 후속 |

공통 9개 조회는 두 공급자의 raw response에서 각각 decode했다. 네 fixture는
처음 `verifying`으로 올렸고, 이후 §5 합성 반례와 package 참조·결정성을
통과해 offline provenance 정책상 `confirmed 0.2`로 승격했다. credential
회전과 live rate/timeout·fallback은 provider 운영 Gate로 남는다. 독립
Trace는 이 판정을 보강하는 비차단 후속이다.

### 3.2 Chainstack 독립 Trace 시도

| Provider | Method | 조회 시각(UTC) | HTTP | 판정 |
|:---|:---|:---|:---:|:---|
| Chainstack Developer/Full | `eth_chainId` | `2026-07-29T01:33:56Z` | 200 | Ethereum Mainnet `0x1`, endpoint 연결 성공 |
| Chainstack Developer/Full | `debug_traceTransaction(callTracer)` | `2026-07-29T01:32:46Z` | 403 | permanent, Trace 역할 제외 |
| Chainstack Developer/Full | `trace_transaction` | `2026-07-29T01:33:10Z` | 403 | permanent, Trace 역할 제외 |

각 method는 read-only로 한 번 실행했다. endpoint·credential·응답 원문은
문서와 Git에 넣지 않았고, 논리 provider 역할과 시각·HTTP·failure kind만
보존했다. 상세 상태 경계는
[Live Provider Readiness §7](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md)을
따른다. Chainstack 실패도 독립 Trace를 비차단 후속으로 두는 근거이지
QuickNode raw Trace의 실전 사용을 실패로 바꾸는 근거가 아니다.

## 4. 독립성·정확성 판정

- [x] primary와 independent 호출은 QuickNode·Alchemy로 분리했다.
- [x] `eth_getLogs`는 receipt 복사가 아닌 address·topic·block filter 호출이다.
- [x] block tag, address, topics와 calldata가 재현 가능하다.
- [x] raw artifact는 configured secret 검사를 거쳐 SHA-256으로 고정됐다.
- [x] decoded 값은 raw response에서 다시 계산됐다.
- [x] capability smoke에서 두 공급자의 공통 6개 decoded summary가 모두 일치했다.
- [x] TASK-012 fixture replay에서 두 공급자의 공통 9개 decoded summary가 모두 일치했다.
- [x] Alchemy 독립 Trace 두 dialect 실패를 각각 보존했다.
- [ ] mismatch·method-not-found·timeout·fallback 반례를 실행한다.
  - [x] timeout·429·method not found·malformed JSON offline 주입 검증
  - [ ] live provider rate/timeout·dialect method-not-found 검증
- [ ] supporting explorer는 제3의 교차확인이고 독립 RPC 대체물이 아니다.

## 5. TASK-012 반례

| 반례 | 기대 결과 | 현재 |
|:---|:---|:---:|
| 실패 transaction | 성공 flow에서 제외 | pass / synthetic offline |
| 같은 signature의 무관 log | contract/topic scope로 제외 | pass / synthetic offline |
| 다른 token Transfer | 대상 token ledger에서 제외 | pass / synthetic offline |
| internal value 없음 | native internal flow 생성 금지 | pass / synthetic offline |
| trace unavailable | partial + 원인 보존 | pass / synthetic offline |
| historical/latest 차이 | 고정 block 값만 채점 | pass / synthetic offline |

이 표와 [Live Provider Readiness §7](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md),
[TASK-012 Fixture 후보 보고서 §7](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md)에
기록된 반례의 합집합이 최소 실행 범위다.

합집합을 확장한 24개 oracle은
[TASK-012 Negative Oracle 보고서](./27_TASK_012_NEGATIVE_ORACLE_REPORT.md)에
고정했다. 이는 live provider의 timeout·rate-limit 또는 독립 trace 실행을
대체하지 않는다.

## 6. AI Planner capability

| 검사 | 기대 결과 | 현재 |
|:---|:---|:---:|
| primary plan | 문제→방법 가설·leaf job 구조화 | not_executed |
| schema reject | 자유문·답 단정·잘못된 leaf 거부 | not_executed |
| token/cost/timeout | 문제별 상한 초과 전 중단 | not_executed |
| provider fallback | 보조 provider가 같은 plan 계약을 반환 | not_executed |
| local fallback | 외부 provider 없이도 Planner 역할 유지 | not_executed |
| evidence boundary | LLM-only 결과는 review_required | not_executed |
| secret canary | prompt·응답·오류·artifact 비노출 | not_executed |

AI Planner의 품질은 정답 문장과의 유사도로 채점하지 않는다. 제안한 방법이
실행 가능한 leaf job인지, Python/RPC evidence와 독립 Verifier가 그 방법을
실증할 수 있는지로 평가한다.

## 7. 최종 판정

| 상태 | 조건 |
|:---|:---|
| pass | 필수 EVM smoke·보안·독립성 통과, 필요한 trace 경로와 Planner fallback 확보 |
| partial | 기본 조회는 통과했지만 trace·plan fallback 등 일부 역할 미확보 |
| failed | secret 노출, chain mismatch, raw 불일치, mutation method, 증거 없는 성공 |
| not_executed | 계정·Rules·승인 또는 live 호출 전 |

`partial`이면 가능한 fixture만 계속 검증하고, 공통 replay를 통과한 것은
`verifying`, 부족한 capability 때문에 재현하지 못한 것은 `candidate`로
둔다. `pass`도 TASK-012 구현 승인을 자동으로 뜻하지 않으며 fixture
`confirmed`와 Context Receipt가 별도로 필요하다.

## 8. 365 글로벌 평가 기준

| 기준 | 검증 관점 |
|:---|:---|
| Functionality | method·state·trace·Planner plan 실제 실행 |
| Potential Impact | 27문항 공통 source/AI 준비 범위 |
| Novelty | AI plan과 Python proof·독립 verification 분리 |
| UX | timeout·rate limit·fallback·partial 가시화 |
| Open-source | secret 없는 raw hash·재현 조건·출처 |
| Business Plan | N/A - 비용 상한만 운영 제약으로 검증 |

## 9. Related Documents

- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - topology·secret·Stop/Go
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source 상태
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - AI Planner 필수 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 구현 잠금
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Gate 실행 순서
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - automated 승격 기준
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 재현 대상 4개
- **QA_Validation**: [Smoke Runner 준비 보고서](./26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) - 코드·dry-run·network 0건 검증
- **QA_Validation**: [TASK-012 Negative Oracle 보고서](./27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 24개 offline 반례·결정성
- **QA_Validation**: [TASK-012 Provider Gate 준비 보고서](./29_TASK_012_PROVIDER_GATE_PREPARATION_REPORT.md) - Trace dialect·offline failure Gate
