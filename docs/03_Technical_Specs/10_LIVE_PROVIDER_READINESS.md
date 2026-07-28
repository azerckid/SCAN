# Live Provider Integration 최소 준비와 Capability Gate
> Created: 2026-07-29 02:35
> Last Updated: 2026-07-29 04:16
> Status: Pre-event Smoke Partial Pass · Credential Rotation Pending · Competition Rules Unclear

## 1. 목적

이 문서는 Phase 2의 비자동 27문항을 준비할 때 공통으로 사용할 EVM 데이터
공급자와 AI Planner 공급자의 최소 준비·검증 Gate를 정의한다. 첫 적용 대상은
`TASK-012`의 verifying fixture 4개지만, 통과한 source·provenance·fallback
계약은 뒤의 PATH·Service·Case Work Package에서도 재사용한다.

이번 QuickNode·Alchemy·Blockscout topology는 **Ethereum 계열 source
역할에만** 적용한다. PATH·Service·Case가 EVM 원자료를 사용할 때는 이를
재사용할 수 있지만, Bitcoin은 UTXO/node 공급자, OSINT·label은 공식
목록·웹·Terms 공급자를 별도 선정한다. 모든 Work Package가 재사용하는 것은
특정 공급자 이름이 아니라 `Rules → secret → capability smoke → 독립 재현
→ 반례 → provenance` Gate 패턴이다.

이 문서는 공급자 가입·결제·API key 발급을 승인하거나 실제 live 호출을
실행하는 문서가 아니다. 현재 단계에서 확정하는 것은 후보 topology, 비밀정보
경계, smoke 항목, 증거 형식과 Stop/Go 기준이다.

## 2. 현재 범위와 정직한 상태

| 항목 | 현재 상태 |
|:---|:---|
| 예상문제 전체 | 30문항 |
| 자동 실증 완료 | DEX·AUTH·FREEZE 3문항 |
| Phase 2 준비 대상 | 나머지 27문항 |
| 직접 준비 중 | EVM Core 4문항의 verifying fixture |
| EVM 공급자 topology | QuickNode primary 7/7·Alchemy verifier 6/6 smoke 성공, credential 회전·독립 trace·rate behavior 미완료 |
| AI Planner 공급자 | 필수 역할 확정, provider/model/비용 smoke 미실행 |
| TASK-012 구현 | 미승인·미시작 |
| 안전한 smoke runner | 준비 완료, 기본 network 0건 |

`27문항 준비`는 27개의 개별 프로그램을 동시에 구현한다는 뜻이 아니다.
공통 수집·상태·로그·trace·경로·라벨·UTXO 엔진을 Work Package 순서로
확장하고, 각 문제는 confirmed fixture와 독립 검증을 통과할 때만 automated로
승격한다.

## 3. EVM 공급자 후보 topology

| 역할 | 후보 | 공식 문서로 확인한 능력 | 현재 제약 | 상태 |
|:---|:---|:---|:---|:---:|
| Primary | QuickNode Ethereum | archive, Ethereum JSON-RPC, Debug API, Trace API를 문서화 | 대상 method 7/7 성공, rate/timeout·credential 회전 미완료 | verifying |
| Independent verifier | Alchemy Ethereum | 기본 RPC·`eth_getLogs`·historical archive state 지원 | 대상 공통 method 6/6 성공, 독립 trace·rate/timeout·credential 회전 미완료 | verifying |
| Supporting explorer | Blockscout | 거래·로그·internal transaction 교차확인에 기존 fixture에서 사용 | 원본 RPC·독립 trace 대체물이 아님 | verifying/supporting |
| Independent trace | 미선정 | primary와 독립된 trace가 필요할 때 사용 | 공급자·plan·비용 미결정 | unresolved |

공식 근거:

- [QuickNode Ethereum API Overview](https://www.quicknode.com/docs/ethereum/api-overview)
- [QuickNode Ethereum chain capabilities](https://www.quicknode.com/chains/eth)
- [QuickNode debug_traceTransaction](https://www.quicknode.com/docs/ethereum/debug_traceTransaction)
- [Alchemy Ethereum API Overview](https://www.alchemy.com/docs/ethereum/ethereum-api-overview)
- [Alchemy Archive Data](https://www.alchemy.com/docs/what-is-archive-data-on-ethereum)
- [Alchemy Pricing Plans](https://www.alchemy.com/docs/reference/pricing-plans)
- [Alchemy eth_getLogs](https://www.alchemy.com/docs/node/stable/stable-api-endpoints/eth-get-logs?explorer=true)
- [Alchemy Trace API Quickstart](https://www.alchemy.com/docs/reference/trace-api-quickstart)

공식 문서의 지원 표시는 실제 계정 plan·rate limit·timeout 성공을 뜻하지
않는다. `adopted` 또는 fixture `confirmed` 판정은 capability smoke와 독립
재현 뒤에만 가능하다.

## 4. 비밀정보와 권한 경계

### 4.1 로컬 설정 이름

문서·코드·로그에는 값이 아닌 아래 논리 이름만 사용한다.

| 이름 | 용도 |
|:---|:---|
| `SCAN_EVM_PRIMARY_RPC_URL` | primary archive·trace RPC |
| `SCAN_EVM_VERIFY_RPC_URL` | 독립 TX·receipt·block·logs·state RPC |
| `SCAN_EVM_TRACE_RPC_URL` | 필요 시 별도 독립 trace RPC |
| `SCAN_EXPLORER_BASE_URL` | supporting explorer base URL |
| `SCAN_LLM_PRIMARY_PROVIDER` / `SCAN_LLM_PRIMARY_MODEL` | AI Planner 주 경로 |
| `SCAN_LLM_FALLBACK_PROVIDER` / `SCAN_LLM_FALLBACK_MODEL` | 보조 또는 local Planner |

실제 endpoint·token·API key는 로컬 secret 환경에만 보관한다. 저장소,
SQLite, fixture, artifact, request/result/error JSON, terminal, Preview,
PR 본문과 screenshot에 저장하지 않는다.

### 4.2 Read-only allowlist

Capability Gate에서 허용하는 EVM 호출은 조회 전용이다.

- `eth_chainId`
- `eth_getTransactionByHash`
- `eth_getTransactionReceipt`
- `eth_getBlockByNumber`
- `eth_getLogs`
- historical `eth_call` 및 필요한 read-only state method
- `debug_traceTransaction` 또는 공급자의 동등 read-only trace

`eth_sendRawTransaction`, 서명, wallet 연결, private key·seed 입력,
contract mutation은 금지한다. 공급자 endpoint를 오류 메시지나 provenance
URL로 그대로 출력하지 않고 논리 `provider_id`만 남긴다.

## 5. EVM capability smoke

| 검사 | Primary | Independent | 통과 조건 | 현재 |
|:---|:---:|:---:|:---|:---:|
| `eth_chainId` | 필수 | 필수 | 예상 chain ID 일치 | not_executed |
| TX by hash | 필수 | 필수 | hash·from·to·block 일치 | not_executed |
| receipt | 필수 | 필수 | status·logs·indices 일치 | not_executed |
| block by number | 필수 | 필수 | number·hash·timestamp 일치 | not_executed |
| filtered `eth_getLogs` | 필수 | 필수 | address·topics·block range 독립 조회 | not_executed |
| historical state/`eth_call` | 필수 | 필수 | 고정 block tag 재현, `latest` 대체 금지 | not_executed |
| trace | 필수 | 조건부 필수 | primary 성공, trace-dependent fixture는 독립 경로도 필요 | not_executed |
| timeout/rate behavior | 필수 | 필수 | 안전한 timeout·429/RPC 오류·`Retry-After` 기록 | not_executed |

`eth_getLogs`는 receipt의 logs를 복사하는 검증으로 대체하지 않는다.
address·topic·fromBlock·toBlock 조건을 고정해 별도 요청한다. capability
지원 여부와 해당 fixture 값의 정확성은 별개로 기록한다.

### 5.1 실행 도구

기본 실행은 endpoint를 읽거나 네트워크를 호출하지 않는 plan 출력이다.

```bash
uv run python scripts/smoke_live_provider.py --role primary
```

실제 호출은 `--execute`, `--rules-status allowed`, 역할별 endpoint 환경변수가
모두 있어야 열린다. primary·verify endpoint는 2026-07-29 03:32 KST에 로컬
`.env.local`로 구성됐지만 공식 Rules가 `unclear`이므로 live smoke는
**03:32 KST 당시에는** 실행하지 않았다. trace endpoint는 아직 미설정이다.
runner는 기존 HTTPX JSON-RPC adapter·content-addressed artifact·secret guard를 재사용하며
`eth_sendRawTransaction`이나 서명 method를 포함하지 않는다.

두 endpoint credential은 설정 과정에서 대화 채널에 노출됐다. 사용자는
대회 전 capability smoke 1회 실행을 승인하고 이후 credential을 직접
회전하기로 했다. 현재 값이 `.env.local`과 Git ignore 경계 안에 있다는
사실은 이미 노출된 credential을 안전한 것으로 되돌리지 않으므로 대회
사용과 후속 지속 호출 전에는 회전 상태를 다시 확인한다.

03:32 KST primary·verify dry-run은 각각 `status=not_executed`,
`network_calls=0`으로 끝났고, endpoint가 구성된 상태에서도
`--execute --rules-status unclear`는 실제 호출 전에 `rule_restricted`
(exit `5`)로 차단됐다. endpoint 값과 token은 조회 결과·문서·Git에 남기지
않았다.

03:39 KST 사용자가 승인한 **대회 전 공급자 준비 점검**으로 primary 7건과
verify 6건을 실행했다. 이때 CLI의 `--rules-status allowed`는 해당 pre-event
점검에 대한 operator 실행 허가로 사용했으며, `RULE-API-001`을 공식
`allowed`로 바꾸지 않는다. 두 공급자는 chain ID·TX·receipt·block·filtered
logs·historical call에서 동일 decoded summary를 반환했고, primary의
`debug_traceTransaction`도 성공했다. 독립 trace와 rate/timeout 동작은 아직
검증하지 않았으므로 전체 Gate는 `partial`이다.

`--output-root`는 저장소 `.scan/live-provider-smoke/`와 그 하위만 허용한다.
URL userinfo는 거부하고 URL path/query token 및 composition root가 전달한
header secret을 저장 전 guard한다. 이 검사는 구성해 전달한 secret만
대상으로 하므로 artifact 상태도 `checked_configured_secrets`로 기록한다.
보안 guard가 차단하면 traceback이나 원문을 출력하지 않고
`security_blocked`, exit `4`로 종료한다.

## 6. Smoke·재현 증거 레코드

각 호출은 secret이 없는 bounded record로 남긴다.

| 필드 | 의미 |
|:---|:---|
| `provider_id` | endpoint가 아닌 논리 ID |
| `capability` / `method` | 검사 능력과 JSON-RPC method |
| `request_scope` | chain·block tag·tx hash 또는 안전한 filter 요약 |
| `retrieved_at` | UTC offset이 있는 조회 시각 |
| `duration_ms` | 호출 시간 |
| `outcome` | success / timeout / rate_limited / unsupported / invalid_response |
| `http_status` / `rpc_code` | 해당 시 안전한 숫자만 |
| `raw_sha256` | secret 제거 후 raw artifact SHA-256 |
| `decoded_summary` | 기대값과 비교할 최소 decoded 값 |
| `match_status` | match / mismatch / not_applicable |
| `fallback_used` | 사용한 fallback 논리 ID, 없으면 null |

raw response는 content-addressed artifact로 보존하고 fixture에는 hash와
필요한 raw field만 연결한다. endpoint·Authorization header·query token은
hash 계산 전후 모두 artifact에 들어가면 안 된다.

## 7. TASK-012 독립 재현 Gate

네 `verifying` fixture는 아래를 모두 만족할 때만 `confirmed`로 승격한다.

1. primary와 independent provider가 TX·receipt·block 핵심 값을 일치시킨다.
2. `eth_getLogs`를 receipt와 독립적으로 조회해 address·topic·block·log index를
   일치시킨다.
3. historical state는 명시 block tag에서 재현하고 `latest`와 혼합하지 않는다.
4. trace-dependent answer는 raw trace와 decoded call/value를 연결한다.
5. provider ID·method·block tag·조회 시각·raw SHA-256·fallback을 남긴다.
6. 같은 raw replay를 두 번 실행해 동일 결과를 얻는다.
7. reference answer·requirement·evidence/source ref가 모두 연결된다.
8. 다음 반례가 complete로 잘못 승격되지 않는다.

반례 최소 세트:

- 실패 transaction
- 같은 event signature지만 무관한 contract/log
- 다른 token의 `Transfer`
- internal native value 이동 부재
- trace unavailable → partial
- historical state와 `latest` 차이

승격에 적용하는 반례는 이 목록만이 아니라
[Live Provider Capability QA §5](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md)와
[TASK-012 Fixture 후보 보고서 §7](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md)의
문제별 반례를 합친 **합집합**이다. 한 문서에만 적힌 반례도 생략할 수 없다.

독립 trace를 확보하지 못하면 trace-dependent 항목은 `partial` 또는
`candidate`를 유지한다. supporting explorer 일치는 독립 RPC 일치를
대체하지 않는다.

합성 offline 반례 19개는 두 번 실행해 결정성을 통과했다. 실행 근거는
[TASK-012 Negative Oracle 보고서](../05_QA_Validation/27_TASK_012_NEGATIVE_ORACLE_REPORT.md)다.
live rate/timeout 반례와 독립 trace는 이 결과로 대체할 수 없다.

## 8. AI Planner Provider Gate

AI Planner는 모든 문제에서 풀이 방법 가설과 leaf job을 제안하는 필수
역할이다. AI가 답을 단정하는 것이 아니라 Python/RPC 분석기와 독립
Verifier가 그 방법을 실행해 답을 실증한다.

| Gate | 통과 조건 | 현재 |
|:---|:---|:---:|
| Rules mode | 허용 provider·model·전송 데이터·tool mode가 선택됨 | pending |
| Structured plan | Operations 0.1 plan·leaf 계약으로 파싱됨 | not_executed |
| Evidence boundary | LLM 문장만으로 confirmed fact·answer 생성 금지 | specified |
| Budget | 문제별 token·비용·timeout 상한 기록 | not_executed |
| Fallback | 보조 provider 또는 local LLM Planner로 전환 | not_executed |
| Secret safety | prompt·artifact·오류에 credential 없음 | not_executed |

외부 LLM 장애 시 AI Planner를 제거하지 않는다. Rules가 허용한 보조
provider 또는 local LLM Planner로 전환하며, 둘 다 불가하면 문제는
`rules_gated` 또는 `review_required`에 머문다. Python evidence와 독립
Verifier가 없는 결과는 `submission_ready`가 될 수 없다.

## 9. Stop/Go

| 조건 | 판정 |
|:---|:---|
| key가 repo·DB·fixture·로그·대화 등 외부 채널에 노출 | Stop · 폐기/회전 후 보안 재검증 |
| archive 또는 filtered logs 미지원 | 해당 역할 제외 또는 fallback |
| trace 필요 fixture에 검증 trace 없음 | candidate/partial 유지 |
| 두 provider 값 불일치 | conflict 보존, confirmed 금지 |
| plan/rate limit이 문서와 다름 | 실제 smoke 값을 등록부에 반영 |
| Rules mode 미확정 | 외부 live/LLM 호출 대기 |
| EVM smoke·반례·fixture Gate 통과 | TASK-012 구현 승인 요청 가능 |

## 10. 365 글로벌 평가 기준

| 기준 | 이 Gate의 기여 |
|:---|:---|
| Functionality | 실제 archive/log/trace 능력을 실행 전 검증 |
| Potential Impact | 4문항에서 시작해 27문항 Work Package가 공유할 source 기반 |
| Novelty | AI 방법 가설과 Python 증명·독립 공급자 검증의 분리 |
| UX | 장애·fallback·partial을 숨기지 않는 운영 상태 |
| Open-source | secret 없는 재현 기록·Schema·fixture provenance |
| Business Plan | N/A - 공급자 비용은 대회 준비 budget으로만 관리 |

## 11. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항 범위
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - 논리 source와 공급자 상태
- **Technical_Specs**: [Agentic Parallel Solve Flow](./07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - AI Planner·Evidence·Verifier 역할
- **Technical_Specs**: [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - 27문항 Work Package
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 Context Lock
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 공급자 Gate 이후 순서
- **QA_Validation**: [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실행 전 체크와 기록 형식
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - verifying 4개
- **QA_Validation**: [TASK-012 Negative Oracle 보고서](../05_QA_Validation/27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 19개 offline 반례
- **QA_Validation**: [Smoke Runner 준비 보고서](../05_QA_Validation/26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) - network 0건·Gate·테스트 증거
