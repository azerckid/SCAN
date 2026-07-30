# TASK-016 CEX Cluster(SVC-CEX-001) Analysis 계약 제안 (docs-only)
> Created: 2026-07-31 05:14
> Last Updated: 2026-07-31 05:40
> Status: Confirmed · Benchmark Automated

## 0. 이 문서의 위치

이 문서는 TASK-016 Wave 5의 세 번째 adapter인 **CEX Cluster(`SVC-CEX-001`)**을
docs-only로 제안한다. [WP-SERVICE 공통 계약 요소(doc 20)](./20_TASK_016_SERVICE_COMMON_CONTRACT.md)의
불변식을 입금주소 집합·집금 패턴 상황에 적용하고, Bridge에서 일반화한 부분과
CEX 고유 축을 구분한다. 승인된 대안 B에 따라 전용 leaf type을 추가하되,
이 Gate에서는 계약·UI·fixture 선정 기준만 다루며 코드·Schema·fixture package는
별도 Gate로 유예한다.

`MIXED-XCHAIN-001`(스왑→브리지→거래소)은 DEX(기존)+Bridge(확정)+CEX(이 문서)
합성이므로, CEX leg 확정 후 별도 **조합 Gate**로 둔다. 이 문서 범위는
단일 체인·단일 관찰 창에서의 **입금주소군 클러스터 평가**이다.

**현재 전제(Context Receipt 요지).** `FX-SVC-CEX-001`은 OFAC SDN GARANTEX
label assertion·세 deposit→공통 hot wallet candidate·negative oracle·독립
Verifier·analyzer hash `20fc2777b75968e905af493f97bb56a5b24ccefad755f3a12ebc62662be283bf`로
`confirmed`·Benchmark automated(14/14)다. 2026-07-31 사용자 batch approval로
CEX docs Gate를 thaw한 뒤 fixture·analyzer Gate를 완료했다. live adapter·Rules
확정 전까지 offline/artifact replay로 제한한다. Mixer·Lending·TASK-018·
`MIXED-XCHAIN-001` 조합은 freeze 유지다.

## 1. 대상 문제·정답 범위 확정

**문제(은행 SVC-CEX-001).** 주소 집합 D가 동일 거래소의 입금주소군인지 평가하고,
집금 핫월렛 후보를 제시한다. 단서: 입금 후보 주소 집합 D, 관찰 기간.

**Request와 Result scope 분리.** 발견해야 할 핫월렛·클러스터 판정을 request에
미리 넣어 정답을 누출하지 않는다.

- request 필수: `deposit_candidates[]`(중복 없는 주소 집합 D),
  `observation_window={start_block,end_block}`.
- request 선택: `expected_hot_wallet`. 사용자가 이미 핫월렛 후보를 제공해
  검증하는 mode에서만 사용하며, 없으면 **discovery mode**다.
- result: `cluster_judgment`(confirmed|estimated|unresolved),
  `hot_wallet_candidates[]`, `common_destination_facts[]`,
  `label_assertions[]`, `false_positive_exclusions[]`.
- 핫월렛을 찾지 못하거나 클러스터 귀속이 미확정이면 placeholder 주소를
  만들지 않고 `partial`과 `partial_conditions`로 보존한다.

**정답 형식(결정적 사실 + 근거 있는 매칭·assertion).**

1. **공통 목적지 사실** — D 내 다주소 출금이 공유하는 destination 주소·TX·
   block·raw amount·자산. 온체인 이동은 **confirmed fact**다.
2. **집금 패턴** — 입금주소 재사용·집금 주기·관찰 창 내 반복 유출. 패턴
   강도는 fact와 heuristic을 구분한다.
3. **라벨 assertion** — 거래소·서비스 식별 claim은 **evidence-backed assertion**
   (출처·시점·조회 키 포함). truth가 아니다.
4. **클러스터 판정** — `cluster_judgment`: evidence-backed label + 공통 목적지 +
   패턴이 모두 정합하면 `confirmed`, 라벨 없이 패턴만이면 `estimated`, 근거
   부족이면 `unresolved`.
5. **오탐 제외** — 공용 서비스·무관 허브·단일 공통 상대만으로 클러스터를
   확정하지 않은 사유를 `false_positive_exclusions[]`에 기록한다.

**판정 경계(중요).**

- **소유·귀속은 자동 단정할 수 없다.** `attribution.exchange_ownership`과
  `attribution.criminality`는 항상 `not_assessed`다.
- **라벨은 evidence-backed assertion이지 truth가 아니다.** first-party 또는
  정부 공개 도메인 출처만 assertion으로 허용하며, Etherscan community tag 등
  탐색기 3rd-party tag는 fixture scoring source로 사용하지 않는다.
- **단일 공통 counterparty(목적지)만으로 클러스터를 confirmed로 확정할 수
  없다.** 공통 목적지는 necessary fact이지만, label assertion 또는 다주소
  반복 집금 패턴 중 하나 이상의 추가 근거 없이는 `estimated`를 넘지 못한다.

## 2. 거래소·라벨·집금 패턴 후보 조사

아래는 **후보**이며 정확한 라벨 출처·주소·체인은 capture 시 공식·검증
소스에서 pin한다(이 문서는 사실로 고정하지 않는다).

| 축(후보) | 결정적/보조 근거(후보) | 비고 |
|:---|:---|:---|
| 다주소 → 공통 destination | outbound TX·Transfer log | confirmed fact |
| 입금주소 재사용·집금 주기 | block/time 간격·반복 패턴 | fact + heuristic 경계 |
| 거래소 라벨 | first-party disclosure·gov registry | evidence-backed assertion |
| 공용 서비스 허브 | 다 tenant 공유 contract/router | false_positive 후보 |

**선정 원칙.** ① 공개·검증 가능한 온체인 이동, ② 라벨 출처가 first-party 또는
정부 공개 도메인, ③ 재배포·조회가 Rules와 충돌 없음, ④ 단일 공통 상대만으로
확정하지 않을 추가 패턴 존재. fixture는 **한 거래소·한 관찰 창·한 체인**으로
한정한다.

## 3. Candidate fixture ID와 공개 사례 선정 기준

**제안 fixture ID.** `FX-SVC-CEX-001`(candidate) — 다주소 입금 후보가 공통
집금 destination과 first-party/gov 라벨 assertion으로 연결되는 공개 사례.

**선정 기준.**

- `deposit_candidates[]`와 bounded `observation_window`가 명확할 것.
- D 내 2개 이상 주소가 동일 destination으로 반복 유출될 것.
- first-party 또는 정부 공개 도메인 라벨 assertion이 교차검증 가능할 것.
- Etherscan community tag·익명 3rd-party DB만으로는 채점 불가.
- 공용 서비스 허브 오탐을 제외할 근거가 문서화될 것.
- 두 provider replay에서 outbound TX·Transfer가 일치할 것(캡처 Gate).
- 거래소 소유·불법성 라벨 없이 사실·assertion으로 채점 가능할 것.

실제 사례·주소·TX는 GARANTEX OFAC SDN 후보로 확정됐다. 후보 조사·선정은
[67 보고서](../05_QA_Validation/67_TASK_016_CEX_FIXTURE_CANDIDATE_REPORT.md)를,
confirmed·Benchmark automated 판정은
[68 Receipt](../05_QA_Validation/68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md)를
따른다.

## 4. outbound / label / pattern evidence 분리 (공통 §1.1·§1.2·§1.4 적용)

**scoped subject binding(doc 20 §1.1).** request에는 `deposit_candidates[]`와
`observation_window`만 필수로 둔다. 핫월렛·클러스터 판정은 evidence에서
계산해 result에 추가한다. `expected_hot_wallet`은 verify mode에서만 exact
binding한다.

- **outbound_transfer_evidence** — D 각 주소에서 destination으로의 ERC-20/native
  Transfer(주소, 자산, raw amount, block, txHash, txIndex, logIndex).
- **common_destination_evidence** — D 내 2개 이상 출처가 공유하는 destination
  주소와 집계 TX 목록. **confirmed fact**.
- **pattern_evidence** — 집금 주기·반복 횟수·창 내 block/time 분포. 강한
  반복은 fact, 단일 TX 상관은 heuristic.
- **label_evidence** — first-party/gov 출처의 거래소·서비스 claim(출처 URL·
  시점·조회 키). **evidence-backed assertion**, truth 아님.

**클러스터 판정 경계.**

- **confirmed**: first-party/gov label assertion + 공통 destination fact +
  다주소 반복 집금 패턴이 모두 정합.
- **estimated**: label 없이 공통 destination + 반복 패턴만, 또는 label +
  공통 destination이나 반복 패턴 미약.
- **unresolved**: 공통 destination fact조차 부족하거나 상충.

**미확보와 모순 분리(doc 20 §1.2).**

- outbound evidence **빠짐** → `partial`(후보만 제시).
- label assertion 출처 **없음** → label 없이 거래소 단정 금지, `estimated` 상한.
- 공통 destination은 있으나 **단일 counterparty만** → `estimated` 상한,
  confirmed 금지.
- scope 밖 주소·창 밖 TX를 합성 → `reconciliation_failed`.

**PATH seed(doc 20 §1.5).** confirmed common destination leg를 seed로 유도한다.
`estimated`/`unresolved`에서는 PATH를 만들지 않거나 candidate로만 둔다.

## 5. Analysis I/O 영향 — 대안 확정 (docs-only 제안)

- **대안 A(합성 재사용, 기각).** 신규 leaf 없이 `flow_path` + `intel_context`
  조합 후 사람이 클러스터 판정. 장점: Schema 무변경. 단점: cluster_judgment·
  hot_wallet·false_positive를 담을 전용 result가 없어 자동 채점 불가 →
  `assisted`.
- **대안 B(전용 leaf type) — 확정.** 전용 `AnalysisType.CEX_CLUSTER` 1종과
  query `evaluate_cex_cluster`를 추가한다. Bridge의 `bridge_transfer`·Lending의
  `defi_lending` 전용 leaf 선례와 동일한 방향이다. 공통 result/evidence/source/
  run 봉투는 유지하고 `inputs`·`result_type/value`만 확장한다.
  - `inputs`: `deposit_candidates[]`, `observation_window`, 선택
    `expected_hot_wallet`.
  - `result_type`: `cex_cluster`.
  - complete `result.value`: flat fact object —
    `cluster_judgment`, `hot_wallet_candidates[]`, `common_destination_facts[]`,
    `label_assertions[]`, `false_positive_exclusions[]`, `attribution`.
  - `attribution.exchange_ownership`: `not_assessed`.
  - `attribution.criminality`: `not_assessed`.
  - complete/partial/failed 상태는 공통 result 봉투의 `status`로 표현한다.

Schema·코드 변경·analyzer 구현은 UI Preview·fixture 후보 승인 **이후** Gate다.

## 6. complete · partial · failed · negative oracle 계약

**complete.** D 내 outbound transfer가 디코딩되고 공통 destination fact가
2주소 이상에서 정합하며, first-party/gov label assertion과 반복 집금 패턴이
교차검증된다. `cluster_judgment=confirmed`, `hot_wallet_candidates[]`가
evidence-backed이며, `false_positive_exclusions[]`에 단일-counterparty·허브
오탐 배제가 기록된다. 거래소 소유·불법성은 `not_assessed`.

**partial.** (a) 공통 destination fact는 있으나 label assertion 미확보 또는
(b) label은 있으나 반복 패턴 미약, 또는 (c) `cluster_judgment=estimated` 상한.
미확보 항목을 `partial_conditions`로 남긴다(은행 부분 점수 조건과 일치:
공통 목적지는 맞지만 거래소 귀속 미확정).

**failed / conflict 보존.**

- 라벨 출처 없이 주소 소유자·서비스·거래소 단정.
- 확정 사실과 휴리스틱 추정을 구분하지 않음.
- 단일 공통 counterparty만으로 `cluster_judgment=confirmed` 승격.
- 무관한 공용 허브를 hot wallet으로 단정.
- Etherscan community tag를 truth로 승격.
- scope 밖 주소·창 밖 TX 합성 → `reconciliation_failed`.

**negative oracle(캡처 Gate 2회 결정성).**

1. 라벨 출처 없이 거래소·소유자를 confirmed fact로 단정 → 거부.
2. 단일 공통 destination만으로 `cluster_judgment=confirmed` → `estimated` 상한
   강제.
3. Etherscan community tag·익명 3rd-party DB를 label truth로 승격 → 거부.
4. 공용 서비스·router 허브를 hot wallet으로 단정 → `false_positive_exclusion`
   또는 거부.
5. `observation_window` 밖 TX를 집금 패턴에 포함 → 거부.
6. request `deposit_candidates[]`에 없는 주소 outbound를 합성 →
   `reconciliation_failed`.
7. label assertion과 outbound fact가 상충(다른 서비스 귀속) →
   `reconciliation_failed`.
8. `expected_hot_wallet`(verify mode)과 evidence hot wallet 불일치 →
   `reconciliation_failed`.
9. heuristic 패턴을 confirmed fact로 승격 → 거부.
10. `attribution.exchange_ownership` 또는 `criminality`를 assessed로 설정 →
    거부(`not_assessed` 강제).

## 7. 오류 계약 — 기존 `ErrorCode` 재사용(신규 코드 없음)

doc 20 §1.6을 따른다. 매핑: 입력 경계 `invalid_input`, 지원 안 되는 체인
`unsupported_chain`, 이벤트 디코딩 실패 `decode_failed`, scope·판정 모순
`reconciliation_failed`, outbound/label evidence 부족 `evidence_incomplete`,
라벨 source 불가 `source_unavailable`, 아카이브 필요 `archive_required`.
CEX·단계 구체값은 `stage`/`message`로만.

## 8. 사실·assertion·heuristic·not_assessed 4분 (doc 20 §1.4)

- **confirmed fact**: outbound Transfer, 공통 destination TX·block·raw amount,
  관찰 창 내 반복 횟수(로그로 재현 가능한 범위).
- **evidence-backed assertion**: first-party/gov 라벨 claim(출처·시점·조회 키).
- **heuristic candidate**: 단일 TX 상관, label 없는 패턴 추정, hot wallet
  순위(근거 강도 미달).
- **not_assessed**: 거래소 소유·본인성(`exchange_ownership`), 자금의 불법성·
  의도(`criminality`).

## 9. UI Preview 요구(다음 Gate)

승인 후 CEX 전용 HTML Preview를 작성해 사용자 승인을 받는다. 최소:

- complete·partial·failed 3상태와 deposit set·common destination·hot wallet
  후보·label assertion·false_positive exclusion 표시.
- discovery vs verify mode와 request의 미지 hot wallet vs result 후보 분리.
- fact / assertion / heuristic / not_assessed 시각적 구분.
- 단일 counterparty만으로 confirmed 승격하지 않음을 표시.
- 외부 fetch/XHR/WebSocket/EventSource 0건(정적 검증).

## 10. 남은 Gate와 Blocker

1. (이 문서) CEX 계약 제안 사용자 검토·승인.
2. UI Preview 작성·사용자 static preview check.
3. `FX-SVC-CEX-001` 공개 후보 선정·first-party/gov 라벨 출처 pin(docs-only).
4. raw replay·negative oracle·독립 Verifier Gate.
5. Analysis I/O 대안 B Schema 확장·offline analyzer 구현 Gate.
6. `verifying → confirmed`·Benchmark automated 승격 Gate.
7. (별도) `MIXED-XCHAIN-001` 조합 Gate — DEX+Bridge+CEX leg 결합.

**Blocker.** live Rules 미확정, confirmed fixture 없음, Etherscan tag를 scoring
source로 쓸 수 없음. CEX docs Gate만 2026-07-31 batch approval로 thaw됐으며
구현은 offline/artifact replay로 제한한다.

## 11. Related Documents

- **Concept_Design**: [예상문제 은행 SVC-CEX-001](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제·정답·증거 정의
- **Technical_Specs**: [WP-SERVICE 공통 계약 요소](./20_TASK_016_SERVICE_COMMON_CONTRACT.md) - scoped_subjects·정합·attribution 불변식
- **Technical_Specs**: [Bridge 계약 제안](./21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md) - 전용 leaf·discovery/verify 선례
- **Technical_Specs**: [Lending 계약 제안](./19_TASK_016_LENDING_CONTRACT_PROPOSAL.md) - 첫 adapter 선례
- **Technical_Specs**: [flow_path IO Contract](./16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - 집금 후 PATH 재사용
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - 체인·provider source
- **QA_Validation**: [예상문제 Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - coverage
- **QA_Validation**: [CEX Fixture 후보 보고서](../05_QA_Validation/67_TASK_016_CEX_FIXTURE_CANDIDATE_REPORT.md) - FX-SVC-CEX-001 선정
- **QA_Validation**: [CEX Final Promotion Receipt](../05_QA_Validation/68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md) - confirmed·Benchmark 14/14
- **QA_Validation**: [Contest Stabilization Runbook](../05_QA_Validation/66_CONTEST_STABILIZATION_RUNBOOK.md) - freeze·CEX confirmed
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - adapter 범위·Context Receipt
- **Logic_Progress**: [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 서비스·Cross-chain 순서
