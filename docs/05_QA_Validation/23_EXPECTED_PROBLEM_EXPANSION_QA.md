# 예상문제 Coverage 확장 QA 계획
> Created: 2026-07-29 01:55
> Last Updated: 2026-07-29 22:52
> Status: TASK-012·013 Passed · TASK-014 Contract Proposed · TASK-014~019 Runtime Not Executed

## 1. 목적

이 문서는 TASK-012~019가 새 예상문제를 automated로 승격할 때 적용할
검증 기준을 정의한다. TASK-012 EVM Core와 TASK-013 NFT·Proxy는
통과했으며, TASK-014~019 시나리오는 `not_executed`다.

## 2. 공통 자동화 승격 Gate

- [ ] 문제 ID와 Analysis type의 관계가 명시돼 있다.
- [ ] confirmed fixture와 reference answer가 있다.
- [ ] 실제 provider capability와 독립성 smoke가 통과했다.
- [ ] raw source/replay에서 답을 계산하고 expected 값을 복사하지 않는다.
- [ ] complete·partial·failed가 각각 검증된다.
- [ ] result→evidence→source 참조가 완전하다.
- [ ] confirmed fact·external context·heuristic·not assessed가 분리된다.
- [ ] 두 번 실행 결과가 결정적으로 같다.
- [ ] 잘못된 oracle·누락 evidence·source 장애가 검출된다.
- [ ] 독립 Verifier가 필수 check를 새로 계산한다.
- [ ] Benchmark 집계가 새 coverage를 과장 없이 반영한다.
- [ ] 선택된 `input_mode`와 `chain_scope`가 provenance에 기록된다.
- [ ] RPC·대회 RPC·artifact가 같은 normalized evidence 계약을 사용한다.

## 3. Work Package QA

| QA ID | Work Package | 필수 시나리오 | 상태 |
|:---|:---|:---|:---:|
| QA-EXP-EVM-001 | EVM Core | TX·receipt·block·state·ERC-20/native flow exact 정합 | pass |
| QA-EXP-EVM-002 | EVM Core | failed TX·archive/trace 누락 partial | pass |
| QA-EXP-SPECIAL-001 | NFT/Proxy | ERC-721/1155·EIP-1967 raw decode와 block state | pass |
| QA-EXP-PATH-001 | PATH | N홉 단일 경로·cycle·budget | not_executed |
| QA-EXP-PATH-002 | PATH | 분기·재병합·unrelated fund·residual | not_executed |
| QA-EXP-INTEL-001 | Intel | official/heuristic 충돌과 주소 비명시 | not_executed |
| QA-EXP-SERVICE-001 | Service | bridge 양단 또는 전문 adapter 결정적 정합 | not_executed |
| QA-EXP-BTC-001 | Bitcoin | prevout·fee·UTXO graph exact 정합 | not_executed |
| QA-EXP-BTC-002 | Bitcoin | change·CoinJoin heuristic과 반례 | not_executed |
| QA-EXP-CASE-001 | Case | 사건 timeline·귀속 경계·관련 없는 자금 제외 | not_executed |
| QA-EXP-REG-001 | Integration | 새 automated 전체 2회 replay·Benchmark 집계 | not_executed |
| QA-EXP-SEC-001 | Integration | secret/path 비노출·Rules·network Gate | not_executed |

## 4. Package별 핵심 판정

### 4.1 EVM Core

- 네 공개 fixture 패키지는 `confirmed 0.2`이며 제품 analyzer QA는
  `pass`다. 별도 fixture Gate에서 합성 negative oracle 24개도 두 번
  통과했다.
- raw uint256과 decimals를 분리한다.
- failed transaction을 성공 이동에서 제외한다.
- historical state에 `latest`를 사용하지 않는다.
- trace unavailable은 숨기지 않고 partial로 남긴다.
- filtered `eth_getLogs`는 receipt 복사가 아니라 독립 filter 요청으로 재현한다.
- endpoint·API key는 repo·DB·fixture·artifact·로그에 저장하지 않는다.

### 4.2 NFT·Proxy

- ERC-721과 ERC-1155를 signature·field 구조로 구분한다.
- token ID와 amount 의미를 혼합하지 않는다.
- proxy implementation은 명시 block의 slot/event로 입증한다.
- ERC-1155 Batch의 ids/values 길이·순서를 exact로 보존한다.
- implementation·beacon·admin slot을 서로 대체하거나 합산하지 않는다.
- contract·state·range가 누락되면 확인된 사실을 보존한 partial로 남긴다.
- 세 공개 package는 두 공급자 replay·negative oracle·독립 Verifier·제품
  analyzer 변형 회귀를 통과해 `confirmed`다.
- `QA-EXP-SPECIAL-001`은
  [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md)를
  근거로 `pass`다. Benchmark는 NFT·Proxy 두 문제를 automated로 집계하며
  ERC-1155는 같은 NFT 문제군의 별도 confirmed 회귀 package로 유지한다.

### 4.3 PATH

- node·edge에 chain·asset·raw amount·evidence ref가 있다.
- 분기 합과 재병합 합의 residual을 계산한다.
- hop/node/time budget을 넘으면 partial과 중단 위치를 보존한다.
- label은 경로 존재의 증거를 대체하지 않는다.

### 4.4 Intel·Service·Case

- 공식 출처와 heuristic이 충돌하면 조용히 하나를 선택하지 않는다.
- service/actor/crime attribution은 evidence 범위를 넘지 않는다.
- AI 가설은 Python/evidence 검증 전 confirmed fact가 아니다.

### 4.5 Bitcoin

- input의 prevout과 output·fee를 exact satoshi로 정합한다.
- change와 CoinJoin은 heuristic으로 분리하고 반례를 포함한다.

### 4.6 입력 모드·체인 격리

- [x] 같은 JSON-RPC 원자료의 `contest_rpc`·`provided_artifact` normalized
  record type·data·record SHA가 일치한다.
- [x] contest adapter는 명시 endpoint 한 곳만 호출하고 Explorer 요청을 만들지 않는다.
- [x] artifact 원본 SHA-256과 record/row locator를 bundle에 연결한다.
- [x] JSON·JSONL·CSV, 3MB·2,000 record 기본 한도와 오류를 검증한다.
- [x] chain scope mismatch와 Bitcoin→EVM analyzer routing을 거부한다.
- 누락 trace·prevout·cross-chain 반대편 message는 complete가 아니다.
- CLI·Operations input selection, 실제 contest endpoint/artifact와
  Bitcoin/non-EVM analyzer는 `not_executed`다.

## 5. 통합·병렬성

- [ ] 문제별 workspace·artifact·checkpoint가 격리된다.
- [ ] 같은 문제의 leaf dependency가 종료된 뒤 case reconciliation이 실행된다.
- [ ] provider별 concurrency budget과 request dedup이 유지된다.
- [ ] 한 문제 실패가 다른 문제 결과를 실패로 바꾸지 않는다.
- [ ] candidate와 verifier가 같은 worker 결과를 자기검증하지 않는다.
- [ ] CTFd 자동 제출과 credential 저장은 0건이다.

## 6. 365 글로벌 평가 기준

| 기준 | 현재 판정 | Phase 2 통과 증거 |
|:---|:---:|:---|
| Functionality | Partial | TASK-012·013 package의 confirmed fixture와 exact/partial/negative 회귀 |
| Potential Impact | Planned | 자동화 문항 증가와 공통 엔진당 coverage |
| Novelty | Planned | AI plan·Python proof·독립 Verifier 분리 |
| UX | Planned | 공통 CLI와 bounded Operations Queue, 필요 시 read-only path view |
| Open-source | Planned | 공개 Schema·fixture·재현 명령·license provenance |
| Business Plan | N/A | 대회 준비 범위, 제품화는 별도 승인 |

TASK-012의 `evm_core` 계약 12개와 제안 checker 14개, 공개 Analysis I/O
Schema probe 40개가 통과했다. 제품 analyzer와
QA-EXP-EVM-001/002도 통과했으며 fixture는 `confirmed 0.2`다.

TASK-013의 `evm_special` 제품 analyzer는 ERC-721·ERC-1155·EIP-1967
fixture 3개를 raw-first로 재계산하고, 16개 negative oracle과 독립
Verifier·변형 회귀를 통과했다. QA-EXP-SPECIAL-001은 `pass`이며 전체
Benchmark 기준선은 automated 9·assisted 0·unsupported 21이다.

## 7. Originality·Ethics

- [ ] 제3자 코드·ABI·데이터의 license와 출처를 기록한다.
- [ ] 범죄·제재·소유자 귀속을 증거 범위 이상으로 단정하지 않는다.
- [ ] 개인정보·비밀키·credential을 수집하거나 출력하지 않는다.
- [ ] 휴리스틱을 사실처럼 표시하지 않는다.

## 8. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제별 완료·부분·실패 기준
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 공통 병목 우선순위
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 상태·오류·결과 표시
- **UI_Screens**: [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - path·timeline UX 후보
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - package별 입력·출력·경계
- **Technical_Specs**: [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - result·evidence 계약
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - provider·secret·AI Planner Gate
- **Technical_Specs**: [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - 입력 정규화·체인 격리 계약
- **QA_Validation**: [WP-INPUT-GATE Core 보고서](./30_WP_INPUT_GATE_CORE_REPORT.md) - 집중·전체 검증과 잔여 범위
- **QA_Validation**: [WP-INPUT CLI·Operations 보고서](./31_WP_INPUT_CLI_OPERATIONS_REPORT.md) - envelope·artifact·Worker handoff 검증
- **Technical_Specs**: [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - `evm_core` 0.2 Draft·partial 오류 매핑
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 순서와 Stop/Go
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012~019 Context Lock
- **QA_Validation**: [Offline Benchmark](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 현재 coverage 기준선
- **QA_Validation**: [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - confirmed fixture 3개·Benchmark 9/9 근거
- **QA_Validation**: [TASK-014 Fixture·Contract Gate](./39_TASK_014_FIXTURE_CONTRACT_GATE.md) - PATH fixture·oracle·Verifier·UI Stop/Go
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 4개 candidate와 1차 source 재조회
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 smoke·독립성·반례
- **QA_Validation**: [TASK-012 Negative Oracle 보고서](./27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 제품 analyzer 전 24개 fixture 반례
- **QA_Validation**: [TASK-012 Analysis Contract Examples](./examples/task-012/README.md) - 12개 계약 사례·14개 Schema probe
