# SCAN 2026 예상문제 Coverage 확장 Technical Brief
> Created: 2026-07-29 01:55
> Last Updated: 2026-07-29 11:10
> Status: Proposed 0.1 · Implementation Not Started

## 1. 목적

이 문서는 Offline Benchmark 0.1에서 확인된 `3 automated / 6 assisted /
21 unsupported` 상태를 공통 분석 엔진 단위의 구현 계획으로 전환한다.
목표는 문제마다 일회용 프로그램을 만드는 것이 아니라, 소수의 결정적
엔진으로 여러 예상문제를 증거와 함께 해결하는 것이다.

이 문서는 구현 승인이 아니다. 각 엔진은 fixture Gate, Context Lock,
Analysis I/O 변경 검토와 별도 작업 승인을 통과한 뒤 시작한다.

## 2. 현재 기준선과 목표

| 항목 | 현재 | Phase 2 목표 |
|:---|---:|:---|
| 예상문제 | 30 | 30 유지 |
| Automated | 3 | confirmed fixture가 있는 범위만 단계적 증가 |
| Assisted | 6 | 범용 EVM 엔진으로 우선 승격 |
| Unsupported | 21 | 공통 병목 엔진부터 축소 |
| 공개 Analysis type | 3 | 엔진별 Schema 승인 후 증가 |
| confirmed fixture | 3 | 자동 승격 대상마다 reference answer 확보 |

`30/30 automated`는 방향이지 이번 문서의 완료 주장이나 일정 약속이 아니다.
실제 진척은 Benchmark의 `automated / assisted / unsupported` 집계로만 측정한다.

## 3. 공통 구현 원칙

1. 공개 사례·reference answer·필수 증거가 없는 분석기는 구현하지 않는다.
2. 새 Analysis type은 입력·결과·오류 계약을 먼저 승인하고 Schema version
   영향을 검토한다.
3. AI는 해결 방법 가설과 작업 분해를 담당하고, 정답 값은 Python 분석기와
   원본 증거가 실증한다.
4. `confirmed_fact`, `external_context`, `heuristic`, `not_assessed`를
   합치지 않는다.
5. partial 결과와 실패 지점을 보존하고, 증거 없는 후보를
   `submission_ready`로 승격하지 않는다.
6. 기존 source port·cache·artifact·checkpoint·Queue·Verifier를 재사용하고
   현재 요구가 없는 새 framework·DB·provider 추상화는 추가하지 않는다.
7. live source는 공식 Rules와 source policy가 허용된 경우에만 별도 활성화한다.
8. 입력은 `external_rpc | contest_rpc | provided_artifact`를 지원하는 공통
   정규화 계층을 먼저 통과한다. Explorer를 금지 시 자동 fallback으로
   가정하지 않는다.
9. 체인 범위는 `evm | bitcoin | non_evm | cross_chain`으로 관리하고,
   서로 다른 실행·상태 모델을 EVM decoder 하나로 일반화하지 않는다.

## 4. 엔진 묶음과 문제 매핑

| Work Package | 핵심 엔진 | 직접 대상 문제 | 선행 |
|:---|:---|:---|:---|
| WP-EVM-CORE | 범용 TX·state·ERC-20·native flow | BASIC-EVM-001/002, EVM-TOKEN-001/002 | 기존 P0 |
| WP-EVM-SPECIAL | NFT·proxy decode | EVM-NFT-001, EVM-PROXY-001 | WP-EVM-CORE |
| WP-PATH | N홉·분기·재병합·금액 정합 | FLOW-EVM-001/002, FLOW-MULTI-001 | WP-EVM-CORE |
| WP-INTEL | label·OSINT·actor·heuristic 경계 | OSINT-LBL/SAN/ENS-001, ACTOR-REL-001/002 | WP-EVM-CORE |
| WP-SERVICE | bridge·CEX·mixer·lending·xchain | SVC-BRG/CEX/MIX/LEND-001, MIXED-XCHAIN-001 | WP-PATH, WP-INTEL |
| WP-BTC | UTXO graph·change·CoinJoin | BTC-UTXO-001/002, BTC-CJ-001 | 공통 provenance |
| WP-CASE | phishing·poison·exploit·rug·mixed case | CRIME-PHISH/POISON/EXP/RUG-001, MIXED-CASE-001 | WP-PATH, WP-INTEL, 필요 전문 엔진 |
| WP-INTEGRATION | 전체 fixture·Benchmark·Operations 연결 | 위 27개 | 각 package |

문제 매핑은 구현 순서와 coverage 책임을 뜻한다. 공통 엔진을 구현했다는
이유만으로 해당 문제를 automated로 바꾸지 않는다.

모든 package의 공통 선행 조건은 `WP-INPUT-GATE`다. 외부 RPC, 주최 RPC,
제공 artifact를 normalized evidence로 변환한 뒤 같은 Python
analyzer·Verifier가 소비해야 한다. 현재 contest RPC adapter와 범용 artifact
importer의 core library는 구현됐고 CLI·Operations wiring과 문제별 임의
mapping은 미구현이다.

`MIXED-XCHAIN-001`의 양단 chain·bridge/service 정합과 직접 Benchmark 책임은
`WP-SERVICE`가 단독으로 가진다. `WP-CASE`는 그 결과가 더 큰 사건의 입력으로
주어질 때 timeline·evidence bundle 조합만 담당하며 이 문제를 중복 소유하지
않는다.

## 5. Work Package별 최소 계약

### 5.1 WP-EVM-CORE

- 입력: TX hash, address, block number/range, token address
- 결정적 기능: TX·receipt·block·balance/state·log·trace 수집,
  ERC-20 Transfer와 native value 이동 정합
- 출력: object summary, balance snapshot/delta, transfer ledger,
  실패 TX와 누락 trace 분리
- 금지: 주소 소유자·범죄 의도 자동 판정
- fixture Gate: 네 직접 대상 문제의 공개 사례와 exact raw answer
- 후보 상태: 동일한 confirmed DEX 기준점을 재사용한 4개 candidate package를
  선정했다. 독립 2차 재현·반례·Schema/UI/구현 승인 전에는 Gate 미통과다.
- provider Gate: primary archive·trace와 독립 TX·receipt·block·filtered
  logs·historical state 공급자의 capability smoke를 먼저 통과한다.
  trace-dependent answer에는 raw Trace와 provenance가 필요하다. 독립 Trace는
  엄격한 fixture 교차검증의 비차단 후속이며 runtime complete 여부를
  단독으로 결정하지 않는다.

### 5.2 WP-EVM-SPECIAL

- NFT: ERC-721 Transfer, ERC-1155 TransferSingle/Batch, token ID·수량·표준 구분
- Proxy: EIP-1967 implementation/admin/beacon slot, upgrade event, block별 구현 주소
- 출력: raw log/state와 decode 결과 연결
- 금지: proxy 구현의 안전성·NFT 소유권 분쟁 자동 판정
- fixture Gate: NFT와 proxy 각각 confirmed 사례 1개 이상

### 5.3 WP-PATH

- 입력: seed address/TX, asset, block/time range, hop·node·edge budget
- 기능: directed multigraph, N홉 탐색, 분기·재병합, cycle·change,
  unrelated fund 분리, raw amount conservation
- 출력: path candidates, excluded edges, reconciliation residual,
  source/evidence ref
- 안전 경계: 탐색 중단·budget 초과는 partial, label은 경로 사실과 분리
- fixture Gate: 단일 경로와 분기·재병합 사례

### 5.4 WP-INTEL

- source role: official, provider label, public record, heuristic
- 기능: 주소 명시 여부, 조회 시각, 인용 범위, 충돌·폐기 라벨 보존
- actor relation은 관찰 근거와 heuristic을 분리하고 confidence만으로
  confirmed fact를 만들지 않는다.
- 일반 웹·ENS·제재 검색은 공식 Rules와 Terms Gate를 통과해야 한다.
- fixture Gate: official/heuristic 충돌과 주소 비명시 반례 포함

### 5.5 WP-SERVICE

- Bridge/XChain: 양단 chain·message·nonce·asset·amount·time 정합
- CEX/Mixer: service 후보와 휴리스틱 근거를 confirmed fact와 분리
- Lending: borrow/repay/liquidation/collateral 이벤트·호출 정합
- 결과가 서비스 귀속이나 불법성 단정으로 자동 승격되지 않게 한다.
- fixture Gate: 각 활성화할 전문 adapter별 공개 사례

### 5.6 WP-BTC

- 입력: transaction ID, address/script, block/range
- 기능: inputs/outputs, prevout, fee, UTXO graph, change 후보,
  CoinJoin 후보 특징
- deterministic UTXO 사실과 change/CoinJoin heuristic을 분리한다.
- fixture Gate: 기본 UTXO, change 반례, CoinJoin 후보·비후보

### 5.7 WP-CASE

- 기존 엔진 결과를 사건 단위 timeline과 evidence bundle로 조합한다.
- phishing·poison·exploit·rug는 관찰 가능한 기술적 사실과 외부 귀속을
  분리한다.
- seed discovery와 관련 없는 자금 제외 규칙을 기록한다.
- fixture Gate: 사건별 reference answer와 반례

## 6. 공개 계약과 저장 경계

- Analysis I/O `0.1`에 유형을 바로 추가하지 않는다. 각 package 착수 시
  `0.2` 필요 여부와 backward compatibility를 먼저 결정한다.
- 공통 result/evidence/source/run 봉투는 유지하고 유형별 `inputs`와
  `result_type/value`만 최소 확장한다.
- SQLite v2 DDL은 기본적으로 유지한다. 새로운 관계형 탐색 캐시가 실제로
  필요하다는 증거가 있을 때만 migration을 별도 승인한다.
- 그래프는 우선 analysis artifact와 in-memory bounded structure로 처리한다.
  그래프 DB는 측정된 병목 전에는 도입하지 않는다.
- Operations Queue는 새 leaf analysis type을 동일한 승인 plan·problem/job
  격리·독립 Verifier Gate로 실행한다.

## 7. Fixture와 승격 Gate

각 문제의 Benchmark 승격은 다음 조건을 모두 만족해야 한다.

1. 공개 입력과 reference answer가 `confirmed` fixture로 승인된다.
2. 입력에서 답을 복사하지 않고 raw replay/source에서 계산한다.
3. complete·partial·failed와 필수 evidence가 자동 테스트된다.
4. 같은 입력을 두 번 실행해 결정적 결과가 같다.
5. 잘못된 oracle·누락 증거·source 장애가 실패 또는 partial로 검출된다.
6. 독립 Verifier가 같은 raw evidence로 필수 check를 다시 계산한다.
7. Benchmark manifest가 해당 문제를 `automated`로 변경하고 전체 집계를
   과장 없이 갱신한다.

## 8. 구현 우선순위

1. WP-INPUT-GATE — 공통 입력 mode·정규화·provenance
2. WP-EVM-CORE
3. WP-BTC
4. WP-PATH와 WP-EVM-SPECIAL
5. WP-SERVICE의 Cross-chain
6. 출제가 확인된 비EVM 체인 adapter
7. WP-INTEL·WP-CASE
8. WP-INTEGRATION

시간이 부족하면 전문 adapter 개수를 늘리기보다 EVM-CORE와 PATH의
정확도·partial·증거 완결성을 우선한다.

## 9. UI·운영 경계

- 새 엔진의 첫 인터페이스는 기존 `scan analyze`와 Analysis I/O JSON이다.
- result summary가 기존 terminal 행 구조로 표현되지 않을 때만 CLI Preview를
  먼저 갱신하고 사용자 확인을 받는다.
- path/timeline은 기존 Investigation Workbench Preview의 read-only 뷰를
  재사용 후보로 두되, Python 결과 계약보다 먼저 웹 runtime을 구현하지 않는다.
- 여러 문제는 Operations Queue에서 병렬 실행하되 한 문제 내부 dependency와
  source concurrency budget을 보존한다.
- CTFd 제출은 계속 사람이 수행한다.

## 10. 365 글로벌 평가 기준

| 기준 | Phase 2 적용 |
|:---|:---|
| Functionality | fixture·exact answer·partial·Verifier Gate로 자동화 승격 |
| Potential Impact | EVM-CORE·PATH처럼 다수 문항을 여는 엔진 우선 |
| Novelty | AI 계획과 Python 실증·독립 검증을 분리 |
| UX | 공통 CLI·Operations Queue·필요 시 read-only graph view |
| Open-source | Analysis I/O·fixture·재현 명령·license provenance 공개 |
| Business Plan | 대회 준비 단계에서는 N/A, 범용 포렌식 제품화는 별도 검토 |

## 11. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항과 기능 공백
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 원자 기능 빈도와 단계 제한
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 공통 분석 명령과 상태
- **UI_Screens**: [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - path·timeline read-only UX 후보
- **Technical_Specs**: [P0·V1 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md) - 기존 기반과 제외 범위
- **Technical_Specs**: [Analysis I/O](./05_ANALYSIS_IO_SCHEMA.md) - 공개 요청·결과·증거 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](./06_OPEN_SOURCE_FORENSICS_REVIEW.md) - build/wrap/borrow 결정 Gate
- **Technical_Specs**: [Live Provider Readiness](./10_LIVE_PROVIDER_READINESS.md) - WP-EVM-CORE 선행 source·AI Gate
- **Technical_Specs**: [다중 입력 모드와 체인 범위](./12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - `WP-INPUT-GATE`와 체인별 엔진 경계
- **Logic_Progress**: [Phase 2 Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 구현 순서와 승인 Gate
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012~019 Context Lock
- **QA_Validation**: [Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 최초 3/6/21, 현재 9/0/21 기준선
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - package별 승격 조건
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - WP-EVM-CORE 후보와 source 장애
- **QA_Validation**: [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - smoke·독립성·반례
