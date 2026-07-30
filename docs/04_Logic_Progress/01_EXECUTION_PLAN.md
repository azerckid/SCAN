# SCAN 2026 예상문제 Coverage 확장 Execution Plan
> Created: 2026-07-29 01:55
> Last Updated: 2026-07-30 14:19
> Status: TASK-012~014 Complete · TASK-015 Analyzer Passed · Verifying 4 / Candidate 1 · Benchmark 11/11

## 1. 목적

이 문서는 Benchmark 0.1의 비자동 27문항을 공통 엔진 단위로 확장하는 실행
순서를 관리한다. 날짜 약속이 아니라 dependency·fixture·승인 Gate 기준의
순서다. 코드 작업은 해당 Backlog TASK의 별도 승인 후 시작한다.

## 2. 기준선

- [x] DEX·AUTH·FREEZE, EVM Core 네 query, NFT·Proxy, FLOW 두 문항 등
  11문항이 automated로 실증됐다.
- [x] assisted 1·unsupported 18의 기능 공백이 manifest에 기록됐다.
- [x] 공통 source·storage·artifact·Queue·Verifier 기반이 있다.
- [x] Wave 1의 새 4문항용 confirmed fixture가 확보됐다.
- [x] `evm_core` Analysis type과 Analysis I/O 0.2 변경이 승인됐다.
- [x] TASK-012 Phase 2 코드 구현이 승인·완료됐다.

## 3. 공통 선행 Gate

각 Work Package는 아래 순서에서 앞 단계를 건너뛰지 않는다.

- [ ] 대상 문제와 답 형식을 한 문장으로 고정한다.
- [ ] 공개 사례 후보와 사용 조건·license·조회 시각을 기록한다.
- [ ] 필요한 live source 역할을 고정하고 read-only capability smoke를 통과한다.
- [ ] reference answer와 완료·부분·실패 조건을 작성한다.
- [ ] fixture를 `candidate → verifying → confirmed`로 승격한다.
- [ ] 오픈소스 후보를 조사하고 `ADOPT/WRAP/BORROW/BUILD/REJECT`를 결정한다.
- [ ] Analysis I/O·source·storage·UI 영향과 migration 필요성을 검토한다.
- [ ] Backlog Context Receipt와 사용자 구현 승인을 확보한다.
- [ ] 최소 vertical을 구현하고 독립 Verification Receipt를 확보한다.
- [ ] Benchmark coverage를 다시 실행해 승격·잔여 공백을 기록한다.

### 3.1 WP-INPUT-GATE

모든 새 분석기는 다음 docs-only 선행 계약을 따른다.

- [x] 입력 모드를 `external_rpc | contest_rpc | provided_artifact`로 고정했다.
- [x] 체인 범위를 `evm | bitcoin | non_evm | cross_chain`으로 고정했다.
- [x] contest RPC를 source port에 즉시 연결하는 core adapter를 승인·구현한다.
- [x] JSON/JSONL/CSV를 normalized evidence로 변환하는 bounded importer를
  승인·구현한다.
- [x] 같은 원자료의 RPC·artifact 입력이 같은 evidence와 분석 값을 만드는지
  검증한다.
- [x] contest adapter가 명시 endpoint만 호출하고 Explorer fallback이 0건인지 검증한다.

이 체크리스트는 설계 Gate다. 미완료 구현 항목은 별도 Context Receipt와
사용자 승인을 받기 전 `In Progress`로 이동하지 않는다.

## 4. 실행 Wave

### [x] Wave 0 — 공통 입력 계층

- [x] 입력 mode·chain scope·정규화·provenance 계약을 문서화한다.
- [x] contest RPC core adapter의 HTTPS·secret·명시 endpoint 계약을 구현한다.
- [x] provided artifact core importer의 format·limit·hash·오류 계약을 구현한다.
- [x] 최소 RPC↔artifact 동등성 테스트와 library-only UI N/A를 확인한다.
- [x] 첫 구현 단위 승인과 집중 Verification Receipt를 확보한다.
- [x] CLI·Operations input selection과 offline raw-artifact handoff를 승인·구현한다.
- [ ] 실제 대회 artifact의 문제별 mapping은 문제 공개 뒤 별도 승인한다.

### [x] Wave 1 — 범용 EVM

- [x] `TASK-012` TX·state·ERC-20·native flow fixture 후보 4개를 선정한다.
- [x] primary·independent·supporting provider 후보 topology와 smoke 계약을 문서화한다.
- [x] 기본 network 0건·Rules/endpoint opt-in capability runner를 준비한다.
- [ ] 노출 credential을 회전하고 새 secret을 로컬 환경에만 구성한 뒤 실제 계정·plan을 확인한다.
- [x] QuickNode primary·Alchemy verify의 TX·receipt·block·filtered logs·historical state와 primary trace smoke를 실행한다.
- [x] 네 fixture의 공통 9개 조회를 두 공급자에서 재현하고 decoded 일치를
  확인해 `verifying`으로 승격한다.
- [x] 네 fixture의 합성 negative oracle 24개를 두 번 실행해 결정성을 고정한다.
- [x] 격리된 `evm_core` 0.2의 4개 query kind와
  complete·partial·failed 12개 사례·14개 Schema probe를 작성하고
  Analysis I/O 0.1 하위 호환을 확인한다.
- [x] TASK-012 전용 HTML Preview의 12개 조합·방향키·모바일·console을
  브라우저에서 검증한다.
- [x] 사용자가 TASK-012 HTML Preview를 확인하고 UI-First Gate를 승인한다.
- [x] 정식 contract·provider Gate 후 제품 analyzer 구현 승인을 별도로 기록한다.
- [ ] live rate-limit·timeout 반례를 실행한다. 독립 trace는 fixture의 엄격한
  승격을 위한 비차단 후속이며 실전 QuickNode 단일 Trace 경로를 막지 않는다.
  - [x] 두 Trace dialect 정규화·교차 동등성과 timeout·429·
    method-not-found(`invalid_response`)·malformed offline 주입 검증을 통과했다.
  - [x] 사용자 위험 수용 후 현재 Alchemy endpoint에서 두 dialect를 실행했으나
    모두 HTTP 400 `permanent`로 실패했다.
  - [x] Chainstack Developer endpoint의 chain ID는 성공했지만 두 trace
    dialect가 HTTP 403으로 실패해 독립 trace 역할에서 제외했다.
  - [ ] 필요 시 성공 가능한 별도 독립 trace endpoint를 후속 검증한다.
- [x] offline oracle과 필수 source Gate를 만족한 fixture의 승격 수준을
  provenance 정책에 따라 결정한다.
- [x] 네 문제 입력·정답 필드와 partial 조건을 승인한다.
- [x] 기존 EVM decoder·source·cache 재사용 범위를 확인한다.
- [x] `evm_core` Analysis type과 Analysis I/O 0.2·0.1 호환을 승인한다.
- [x] exact·evidence·determinism·negative oracle 회귀를 통과한다.

credential 회전·live rate-limit/timeout과 선택적 독립 Trace는 실전 live
운영 Gate로 남으며, reviewed replay 기반 TASK-012 완료를 되돌리지 않는다.

### [ ] Wave 2 — Bitcoin Core

- [ ] `TASK-017` BTC UTXO·prevout·fee fixture를 확정한다.
- [ ] change·CoinJoin heuristic과 deterministic 사실을 분리한다.
- [ ] `contest_rpc`/artifact 입력의 Bitcoin normalized evidence를 승인한다.

### [x] Wave 3 — NFT·Proxy·PATH 완료

- [x] `TASK-013`의 ERC-721·ERC-1155·EIP-1967 fixture ID와 선정 기준을
  docs-only Draft로 고정한다.
- [x] `TASK-013`의 전문 Analysis type 대안·결과·partial/failed 계약을
  docs-only Draft로 작성한다.
- [x] `TASK-013` 공개 candidate 3개를 선정하고 두 공급자 receipt/storage
  기본 일치를 기록한다.
- [x] `TASK-013` raw/provider replay와 selected TX·exact block 또는
  selected upgrade·adjacent state scope Gate를 통과한다.
- [x] `TASK-013` negative oracle 16개와 두 번의 결정성 재현을 완성한다.
- [x] `TASK-013` 독립 Verifier가 세 candidate의 13개 evidence 값과 7개
  requirement를 raw에서 두 번 재계산한다.
- [x] `TASK-013` 세 fixture를 [승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)로
  `후보`에서 `검증 중`으로 승격한다(`확정`은 아니다).
- [x] `TASK-013` Analysis I/O 대안 B(`evm_special`)를 확정하고
  [전용 UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)·[Preview](../02_UI_Screens/previews/06_task_013_nft_proxy_preview.html)를
  작성한다.
- [x] `TASK-013` 사용자가 UI Preview를 확인하고 승인한다(2026-07-29 20:19).
  Context Receipt `PASS`·사용자 구현 승인을 Backlog에 기록했다.
- [x] `TASK-013` NFT·Proxy analyzer를 구현하고 독립 Verification Receipt를
  확보한다([canonical hash 일치](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md)).
- [x] `TASK-013` 리뷰에서 발견한 P1 5건·P2 2건을 수정하고 재현 회귀
  테스트 6건과 Batch subject CLI 통합 테스트를 추가한다
  ([P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)).
- [x] `TASK-013` ERC-721/1155와 EIP-1967 fixture를 `확정`으로 올린다
  ([최종 승격 Receipt](../05_QA_Validation/38_TASK_013_FINAL_PROMOTION_RECEIPT.md)).
- [x] `TASK-013` Benchmark automated 7 → 9 승격과 9/9 통과를 기록한다.
- [x] `TASK-014` proposed fixture 3개 ID와 공개 사례 선정 기준을 docs-only로
  고정한다.
- [x] `TASK-014` `flow_path` 대안·bounded graph·reconciliation ledger·
  partial/failed 계약을 작성한다.
- [x] `TASK-014` query 3개 × 상태 3개 HTML Preview와 UI Gate를 작성한다.
- [x] `TASK-014` 단일 path·분기/재병합·multi-origin 공개 사례를
  `candidate` package로 작성한다.
- [x] `TASK-014` 세 fixture의 두 공급자 replay·negative oracle 18개·독립
  Verifier를 통과해 `verifying`으로 올린다.
- [x] 사용자가 PATH Preview를 승인한다(2026-07-29 23:09).
- [x] 사용자가 `flow_path` 대안 B를 정식 승인한다(계약 확정안 PR #71 병합).
- [x] graph node/edge·asset conservation·budget·partial 계약을 정식 승인한다
  ([16_TASK_014_FLOW_PATH_IO_CONTRACT](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md)).
- [x] Context Receipt `PASS`·사용자 analyzer 구현 승인을 기록한다(2026-07-30).
- [x] `flow_path` analyzer 3 query를 구현하고 독립 Verifier와 canonical hash를
  대조한다([검증 Receipt](../05_QA_Validation/43_TASK_014_ANALYZER_VERIFICATION_RECEIPT.md)).
- [x] path 결과가 label/price/heuristic과 분리되는지 검증한다(`not_assessed`·별도 context).
- [x] Blockscout internal-tx 독립 교차검증으로 단일-trace 하드 게이트를
  닫고 fixture 3개를 `확정`으로 승격한다.
- [x] FLOW-EVM-001/002를 Benchmark automated로 승격해 11/11을 통과하고,
  PRICE·피해자 귀속이 남은 FLOW-MULTI-001은 assisted로 유지한다.
- [x] 기존 Workbench는 상위 read-only 화면으로 유지하고 TASK-014 전용
  Preview를 별도로 사용하기로 결정한다.

### [ ] Wave 4 — Label·OSINT·Actor

- [x] `TASK-015` official/first-party/provider/public-report/heuristic source role,
  claim·conflict·시점 계약을 docs-only로 제안한다.
- [x] label·sanctions·ENS·common funder·actor relation의 proposed fixture ID와
  negative oracle 범주를 고정한다.
- [x] query 5개 × complete·partial·failed HTML Preview와 UI Gate를 작성한다.
- [x] 사용자 Preview 검토·피드백을 기록한다(2026-07-30 02:52).
- [x] 공개 source Terms·privacy와 다섯 후보를 bounded 조사한다
  (4 viable, label conflict 1 source-blocked; package·snapshot 아님).
- [x] label source blocker를 research-permitted OpenRAIL sample·MIT config·
  onchain ENS conflict로 교체하고 다섯 후보의 raw snapshot SHA 기준선을 고정한다.
- [x] selected raw artifact를 포함한 다섯 candidate package를 작성한다.
- [x] official·provider·heuristic·onchain 상충과 truth 비승격 반례 30개를
  오프라인에서 두 번 결정적으로 실행한다.
- [x] ENS 두 fixture를 Alchemy·Blockscout fixed block에서 재현하고 OFAC
  current SLS snapshot metadata를 고정한다.
- [x] LABEL·SANCTIONS·ENS·RELATION-HUB 4개를 독립 Verifier로 재계산하고
  `verifying`으로 승격한다.
- [x] `intel_context` 계약·Context Receipt·구현 승인을 기록하고 5 query
  analyzer와 독립 hash 대조를 통과한다.
- [x] AI가 만든 label 가설이 evidence 없는 confirmed fact가 되지 않게 한다.
- [x] source permission·live 필요성·fixture별 Promotion Hard Gate를
  docs-only Readiness로 분리한다.
- [ ] common-funder bounded prehistory·service exclusion을 닫는다.
- [ ] label exact OpenRAIL license text·notice·재배포 의무를 pin한다.
- [ ] 네 verifying fixture를 별도 Promotion Receipt로 판정하고, 실제 confirmed
  문제만 Benchmark에 반영한다.

### [ ] Wave 5 — 서비스·Cross-chain

- [ ] `TASK-016` bridge/CEX/mixer/lending 중 confirmed fixture가 있는 adapter만 선택한다.
- [ ] 양단 체인·message·amount 또는 서비스 휴리스틱 증거 계약을 승인한다.
- [ ] EVM과 Bitcoin 결과가 같은 공통 evidence 봉투를 유지하는지 검증한다.
- [ ] 양단 transaction·message·asset·amount 정합을 승인한다.

### [ ] Wave 6 — 출제가 확인된 비EVM

- [ ] 공식 문제에서 대상 chain과 제공 입력 형식을 확인한다.
- [ ] chain별 instruction/message·account/state 계약과 fixture를 승인한다.
- [ ] EVM analyzer로 잘못 일반화하지 않고 전용 decoder를 별도 승인한다.

### [ ] Wave 7 — 범죄·복합 사건

- [ ] `TASK-018` phishing/poison/exploit/rug/mixed case reference answer를 확정한다.
- [ ] 기술적 사실·외부 귀속·범죄 의도·현재 상태를 분리한다.
- [ ] seed discovery·관련 없는 자금 제외·사건 timeline 규칙을 승인한다.
- [ ] 기존 엔진 결과를 복사하지 않고 evidence ref로 조합한다.

### [ ] Wave 8 — 통합

- [ ] `TASK-019` 모든 새 automated 사례를 Benchmark manifest에 승격한다.
- [ ] assisted·unsupported 잔여를 숨기지 않고 새 집계를 기록한다.
- [ ] 복수 문제를 bounded Queue에서 병렬 실행한다.
- [ ] 독립 Verifier 없는 후보가 submission-ready가 아닌지 재확인한다.
- [ ] 전체 regression·security·traceability·offline Gate를 통과한다.

## 5. Stop/Go 규칙

| 조건 | 판정 |
|:---|:---|
| fixture·reference answer 없음 | Stop — 구현 금지 |
| 필수 live capability smoke 미통과 | Stop — fixture 재현·구현 승인 금지 |
| 공식 Rules가 source/AI 사용을 제한 | Stop 또는 offline 축소 |
| 외부 API·Explorer가 제한되고 대회 입력도 없음 | Stop — source-dependent 분석 대기 |
| 새 dependency가 기존 기능보다 이점 없음 | Stop — 기존 코드/stdlib 사용 |
| 한 engine이 두 문제 이상 공통 병목을 해소 | Go 우선 |
| 전문 adapter가 한 문제만 지원 | fixture·출제 중요도 확인 후 Go |
| partial·실패·반례가 검증되지 않음 | automated 승격 금지 |

## 6. 진척 측정

진척률은 코드 줄 수나 task 완료 개수가 아니라 다음 수치로 기록한다.

- automated / assisted / unsupported 문제 수
- confirmed fixture 수
- exact answer·evidence·determinism 통과 수
- partial·negative·source-failure 검증 수
- 공통 엔진 하나가 여는 문제 수

## 7. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 대상 30문항
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 구현 순서 근거
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 공통 명령과 상태
- **UI_Screens**: [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - path·timeline UX 후보
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - Work Package 계약
- **Technical_Specs**: [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 계약 변경 Gate
- **Technical_Specs**: [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - EVM Core 0.2 Draft와 0.1 비변경 검증
- **Technical_Specs**: [TASK-013 NFT·Proxy Contract Proposal](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - 전문 decoder 계약과 구현 잠금
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - Wave 1 source·AI Planner 선행 Gate
- **Logic_Progress**: [Backlog](./00_BACKLOG.md) - TASK-012~019 상태
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 승격 검증 기준
- **QA_Validation**: [Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 현재 9/0/21 기준선
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - Wave 1 후보 4개와 잔여 Gate
- **QA_Validation**: [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - smoke·secret·independence 체크
- **QA_Validation**: [TASK-013 Fixture 후보 보고서](../05_QA_Validation/32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - NFT 표준 2종·Proxy 선정 Gate
- **QA_Validation**: [TASK-013 Fixture 승격 검토 보고서](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) - `검증 중` 승격 판정
- **QA_Validation**: [TASK-013 최종 승격 Receipt](../05_QA_Validation/38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - confirmed fixture 3개·Benchmark 9/9 최종 판정
- **Technical_Specs**: [TASK-014 PATH Contract](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - bounded graph·ledger·오류 계약
- **UI_Screens**: [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - query 3개·상태 3개 UI Gate
- **QA_Validation**: [TASK-014 Fixture·Contract Gate](../05_QA_Validation/39_TASK_014_FIXTURE_CONTRACT_GATE.md) - fixture·oracle·Verifier Stop/Go
- **QA_Validation**: [TASK-014 Fixture 후보 보고서](../05_QA_Validation/40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 공개 3홉·재병합·multi-origin 선정 근거
- **QA_Validation**: [TASK-014 최종 승격 Receipt](../05_QA_Validation/44_TASK_014_FINAL_PROMOTION_RECEIPT.md) - FLOW confirmed·Benchmark 11/11 최종 판정
- **UI_Screens**: [TASK-013 NFT·Proxy UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md) - 표준 3개·상태 3개 화면 계약과 Preview
- **QA_Validation**: [Smoke Runner 준비 보고서](../05_QA_Validation/26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) - runner·dry-run·미실행 경계
