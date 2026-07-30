# TASK-016 Bridge/XChain(SVC-BRG-001) Analysis 계약 제안 (docs-only)
> Created: 2026-07-30 20:45
> Last Updated: 2026-07-31 04:25
> Status: Docs Contract Approved · Fixture Verifying · Offline Analyzer Implemented · Verification Receipt PASS · confirmed Pending

## 0. 이 문서의 위치

이 문서는 TASK-016 Wave 5의 두 번째 adapter인 **Bridge/XChain(`SVC-BRG-001`)**을
docs-only로 제안한다. [WP-SERVICE 공통 계약 요소(doc 20)](./20_TASK_016_SERVICE_COMMON_CONTRACT.md)의
불변식을 양단(cross-chain) 상황에 적용하고, Lending에서 일반화한 부분과
Bridge 고유 축을 구분한다. 승인된 대안 B에 따라 offline analyzer와
Analysis I/O Schema가 구현됐으며 fixture·Benchmark 승격은 별도 Gate로 유지한다.

`MIXED-XCHAIN-001`(스왑→브리지→거래소)은 DEX(기존)+Bridge(이 문서)+CEX(미구현)
합성이므로, Bridge leg 확정 후 별도 **조합 Gate**로 둔다. 이 문서 범위는
단일 bridge hop(출발↔도착 연결)이다.

**현재 전제(Context Receipt 요지).** `SVC-BRG-001` fixture는 양단 replay·
negative oracle·독립 Verifier를 통과한 `verifying`이며 아직 `confirmed`는
아니다. source/Rules 미확정은 live adapter blocker로 유지하되,
content-addressed artifact 기반 offline analyzer는 2026-07-31 Context Receipt
PASS·사용자 구현 승인을 받았다. 다른 TASK-016 adapter와 `MIXED-XCHAIN-001`,
fixture·Benchmark 승격은 승인 범위가 아니다.

## 1. 대상 문제·정답 범위 확정

**문제(은행 SVC-BRG-001).** 체인 X의 주소 A에서 브리지로 잠긴 자산이 체인 Y의
어느 주소로 도착했는지 연결한다. 단서: 출발 체인 X·주소 A, 출발 TX 또는 시간
창, 도착 체인 Y 후보.

**Request와 Result scope 분리.** 발견해야 할 recipient를 request에 미리 넣어
정답을 누출하지 않는다.

- request 필수: `source_subject={chain,address,roles:[sender]}`,
  `destination_chain`, `source_tx_hash` 또는 bounded source window.
- request 선택: `expected_recipient`. 사용자가 이미 recipient 후보를 제공해
  검증하는 mode에서만 사용하며, 없으면 discovery mode다.
- result: `resolved_scoped_subjects[]`에 source subject와 발견된 destination
  recipient `(chain,address,roles:[receiver])`를 넣는다. `expected_recipient`가
  있으면 result recipient와 exact binding하고, 없으면 양단 evidence에서
  recipient를 계산한다.
- destination recipient를 찾지 못한 경우 request에 placeholder 주소를 만들지
  않고 `partial`과 `partial_conditions`로 보존한다.

**정답 형식(결정적 사실 + 근거 있는 매칭).**

1. **출발 leg** — 출발 TX·브리지 컨트랙트·잠금/소각(lock/burn/deposit) 이벤트·
   자산·raw amount·destination 힌트(dstChainId·recipient).
2. **도착 leg** — 도착 체인·주소·TX·해제/발행(unlock/mint/release) 이벤트·
   자산·raw amount.
3. **연결 근거** — 매칭 키(§4): bridge domain으로 namespace된 message/nonce
   또는 공식 derivation 우선, 없으면 금액·시간·자산 상관에 기반한
   **candidate**.

**판정 경계.** "유사 금액의 다른 브리지 전송 구분"과 "새 브리지 프로토콜
해석"은 사람 몫이다. 결정적 매칭 키가 없으면 도착 leg를 확정하지 않고
candidate로만 둔다(§4·§6).

## 2. 브리지 프로토콜·컨트랙트·체인 ID 후보 조사

아래는 **후보**이며 정확한 컨트랙트 주소·체인 ID·메시지 스키마는 capture 시
공식·검증 소스에서 pin한다(이 문서는 사실로 고정하지 않는다).

| 브리지 유형(후보) | 결정적 매칭 키(후보) | 비고 |
|:---|:---|:---|
| Canonical L1↔L2 (Arbitrum·Optimism·Polygon PoS) | deposit index/hash·L2 tx | lock on L1 → mint on L2 |
| Wormhole 계열 | emitter + sequence (VAA) | message-passing |
| LayerZero 계열 | srcChainId + nonce | message-passing |
| Liquidity 브리지 (Across·Hop·Stargate) | depositId·transferId | 유동성 풀, 금액 수수료 차감 가능 |

**선정 원칙.** ① 공개·검증 컨트랙트, ② 메시지/이벤트 스키마가 공식 문서로
확인 가능, ③ 양단 체인 raw 데이터가 확보 가능, ④ 재배포·조회가 Rules와 충돌
없음. fixture는 **한 브리지·한 전송**으로 한정한다.

## 3. Candidate fixture ID와 공개 사례 선정 기준

**제안 fixture ID.** `FX-SVC-BRG-001`(candidate) — 출발 체인 lock/burn과 도착
체인 mint/unlock이 결정적 매칭 키로 연결되는 단일 공개 전송.

**선정 기준.**

- 출발 TX·브리지 컨트랙트·destination 힌트가 명확할 것.
- 도착 체인 TX가 domain-separated 결정적 키 또는 공식 derivation으로 연결될
  것(금액·시간만이 아니라).
- 수수료 차감·자산 표현·지연 도착이 있으면 §4의 정수 fee 식·asset mapping·
  arrival window가 공식 근거와 함께 문서화될 것.
- 양단 raw 데이터가 두 provider replay로 재현될 것(캡처 Gate).
- 라벨 없이 사실·근거로 채점 가능할 것.

실제 사례·주소·TX·체인 ID 확정과 raw 캡처는 캡처 Gate로 유예한다.

### 3.1 공개 후보 선정(캡처 전)

docs-only 후보 조사에서 Across V3 Base→Ethereum 전송 한 건을
`FX-SVC-BRG-001`의 공개 후보로 선정했다.

- Base `8453` SpokePool `0x09aea4b2242abc8bb4bb78d537a67a245a7bec64`
  source TX `0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b`
- Ethereum `1` SpokePool `0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5`
  destination TX `0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0`
- Across V3 domain: origin `8453`, destination `1`, deposit ID `2395968`;
  source `330000000000000000`, destination `329132286989970407`,
  difference `867713010029593` wei

공식 Across 문서는 chain ID·SpokePool·event/matching 규칙을, 공개
BaseScan/Etherscan 화면은 양단 TX 후보를 뒷받침한다. 이 값은 아직 Explorer
supporting 확인뿐이다. 두 RPC raw replay·SHA·negative oracle·Verifier 전에는
package를 만들거나 `verifying`으로 올리지 않는다. 상세 경계는
[후보 선정 보고서](../05_QA_Validation/61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md)를
따른다.

## 4. 양단 evidence 분리와 매칭 키 (공통 §1.1·§1.2·§1.5 적용)

**scoped subject binding(doc 20 §1.1).** request에는 알려진 source subject와
destination chain만 필수로 둔다. destination recipient는 양단 evidence에서
계산해 result `resolved_scoped_subjects[]`의 두 번째 항목으로 추가한다.
`expected_recipient`가 제공된 검증 mode에서만 exact binding한다. 한쪽(도착)
정보가 부족하면 placeholder를 합성하거나 `reconciliation_failed`로 만들지
않고 `partial`이다.

- **source_event_evidence** — 출발 체인 lock/burn/deposit 이벤트(브리지
  컨트랙트, 자산, raw amount, dstChainId·recipient 힌트, message/nonce).
- **destination_event_evidence** — 도착 체인 mint/unlock/release 이벤트(자산,
  raw amount, 수령 주소, 매칭 키).
- **transfer_evidence** — 각 체인의 실제 ERC-20/native 이동(이벤트 amount ↔
  실제 이동 정합, doc 20 §1.2).
- (선택) **message_evidence** — 브리지 메시지/VAA/논스 원본(결정적 매칭 근거).

**매칭 키(연결 근거).**

- **결정적(confirmed)**: 단독 nonce/message 값이 아니라 아래 composite
  domain으로 namespace된 키가 양단에서 일치해야 한다.
  `protocol_or_source_contract + source_chain + destination_chain + key_type +
  key_value + emitter_or_sender(프로토콜이 요구할 때)`.
- source와 destination에서 키 표현이 다른 브리지는 공식 message schema가
  정의한 deterministic derivation을 사용하고 `source_key`·`destination_key`·
  `derivation_rule_ref`·양단 evidence를 함께 보존한다. 임의 문자열 변환이나
  금액·시간 상관으로 key를 만들지 않는다.
- 위 domain과 derivation을 통과한 경우만 **evidence-backed deterministic
  matching**이며 도착 leg를 확정한다.
- **candidate(heuristic)**: 결정적 키 없이 금액·시간·자산 상관만 있는 경우.
  도착 leg를 확정하지 않고 candidate로 표기(사람 판단 필요).

**미확보와 모순 분리(doc 20 §1.2).**

- 도착 evidence가 **빠짐** → `partial`(도착 후보만 제시).
- 양단 amount(§4 정수 fee·asset mapping 반영 후)·asset·message가 **실제 충돌** →
  `reconciliation_failed`로 보존(잘못된 쌍을 partial로 덮지 않음).

**수수료·자산·지연 정합 계약.** 자유 형식 tolerance를 금지한다. fixture는
아래 필드와 공식 근거를 고정하며, 모든 금액은 부호 없는 decimal string이다.

- 자산: `source_asset_ref`·`destination_asset_ref`·각 `decimals`와 공식
  `asset_mapping_ref`. 래핑·자산 변경은 이 mapping 없이는 candidate를 넘지
  못한다.
- 금액: `source_raw`·`protocol_fee_raw`·`expected_destination_raw`·
  `observed_destination_raw`. 1:1 mapping은 정수 산술로
  `(source_raw - protocol_fee_raw) × 10^destination_decimals ==
  expected_destination_raw × 10^source_decimals`를 검증한다.
- 비율 변환이 필요한 공식 route는 `ratio_numerator/ratio_denominator`와
  반올림 규칙을 pin하고 정수 산술로 expected 값을 재계산한다.
- `max_abs_delta_raw` 기본값은 `0`이다. 공식 프로토콜 문서·검증된 이벤트로
  허용 오차가 입증된 경우에만 0보다 크게 설정한다. 근거가 없으면 tolerance
  match는 candidate만 가능하다.
- 지연: `arrival_window_start/end`를 block 또는 UTC timestamp로 고정한다.
  창 밖 도착은 결정적 key가 같아도 `partial`로 판정하고 late-arrival
  conflict/evidence를 보존하며, 자동 `complete`로 승격하지 않는다.

위 계산 뒤 expected와 observed가 다르거나 asset mapping이 모순되면
`reconciliation_failed`다.

**PATH seed(doc 20 §1.5).** 결정적으로 매칭된 도착 recipient leg를 seed로
유도한다. 결정적 매칭이 없으면 PATH를 만들지 않거나 candidate로만 둔다.

## 5. Analysis I/O 영향 — 대안 확정 (사용자 승인 완료)

- **대안 A(합성 재사용, 기각).** 신규 leaf 없이 양단을 각각 evm_core/flow_path로
  조회 후 사람이 매칭. 장점: Schema 무변경. 단점: 양단 매칭·근거를 담을 전용
  result가 없어 자동 채점 불가 → `assisted`.
- **대안 B(전용 leaf type) — 확정.** 전용 `AnalysisType.BRIDGE_TRANSFER`
  1종과 query `link_bridge_transfer`를 추가한다. Lending의 `defi_lending`
  전용 leaf 선례와 동일한 방향이다. 공통 result/evidence/source/run 봉투는
  유지하고 `inputs`·`result_type/value`만 확장한다.
  - `inputs`: §1의 `source_subject`·`origin_chain_id`·
    `destination_chain_id`와 선택 `expected_recipient`·양단 TX hash를 분리한다.
  - complete `result.value`: Verifier와 같은 flat fact object를 사용한다.
    `protocol`, 양단 chain ID·SpokePool, `deposit_id`, `depositor`, `recipient`,
    양단 asset, `source_raw`, protocol fee candidate, expected/observed
    destination raw, `message`, `attribution`을 담는다. 필드 자체가 양단 leg와
    matching 사실을 인코딩하므로 별도 nested leg를 중복하지 않는다.
  - complete/partial/failed 상태는 공통 result 봉투의 `status`로 표현한다.

Context Receipt PASS·사용자 구현 승인·offline analyzer 구현·독립
Verification Receipt는 완료됐다. 남은 Gate는 별도 fixture
`verifying → confirmed` 승격 검토와 Benchmark 판정이다(§10 참고).

## 6. complete · partial · failed · negative oracle 계약

**complete.** 출발·도착 leg가 모두 디코딩되고 **domain-separated 결정적
매칭 키로 연결**되며, 양단 event↔transfer와 §4 정수 수수료·자산 mapping·
arrival window 정합을 통과한다. 공식 브리지 컨트랙트 식별은
evidence-backed assertion으로, recipient 소유·본인성·불법성은
`not_assessed`로 유지한 채 정답 3필드가 채워진다.

**partial.** 출발 TX·브리지는 확정됐으나 (a) 도착 evidence 미확보로 도착
후보만, 또는 (b) 도착 주소는 있으나 message/nonce 근거 미확보. 미확보 항목을
`partial_conditions`로 남긴다(은행 부분 점수 조건과 일치).

**failed / conflict 보존.**

- 라벨 출처 없이 주소 소유자·서비스 단정.
- 확정 사실과 휴리스틱 후보를 구분하지 않음.
- 양단 amount(§4 정수 fee·mapping 적용 후)·asset·message **모순** →
  `reconciliation_failed`.
- 잘못된 도착 쌍을 결정적 매칭으로 승격.

**negative oracle(캡처 Gate 2회 결정성).**

1. 유사 금액의 **다른** 브리지 전송을 도착 leg로 오매칭(결정적 키 불일치) → 거부.
2. 결정적 키 없이 금액·시간만으로 도착을 confirmed로 승격 → candidate 강제.
3. 공식 fee·asset mapping 없이 임의 tolerance를 근거로 destination candidate를
   결정적 매칭으로 승격 → 거부(candidate 유지).
4. 도착 evidence 미확보를 complete로 처리 → partial 강제.
5. request source subject 또는 destination chain에 없는 주소·체인으로 합성 →
   `reconciliation_failed`.
6. 같은 nonce/key_value이지만 다른 bridge contract·emitter·source chain인
   전송을 같은 결정적 키로 연결 → 거부(domain separation 필수).
7. 결정적 key가 있더라도 공식 fee/asset mapping 없이 임의 tolerance·잘못된
   decimals·symbol 일치만으로 amount 정합을 통과 → `reconciliation_failed`.

## 7. 오류 계약 — 기존 `ErrorCode` 재사용(신규 코드 없음)

doc 20 §1.6을 따른다. 매핑: 입력 경계 `invalid_input`, 지원 안 되는 체인
`unsupported_chain`, 이벤트 디코딩 실패 `decode_failed`, 양단 정합·매칭 모순
`reconciliation_failed`, 도착/메시지 evidence 부족 `evidence_incomplete`,
아카이브 필요 `archive_required`. 브리지·단계 구체값은 `stage`/`message`로만.

## 8. 사실·assertion·heuristic·not_assessed 4분 (doc 20 §1.4)

- **confirmed fact**: 양단 이벤트·raw amount·결정적 매칭·정합 leg.
- **evidence-backed assertion**: 공식·검증된 브리지 컨트랙트 식별(출처·시점
  포함).
- **heuristic candidate**: 금액·시간 상관 도착 후보.
- **not_assessed**: 수령 주소 소유·본인성, 자금의 불법성·의도.

## 9. UI Preview 요구(다음 Gate)

승인 후 Bridge 전용 HTML Preview를 작성해 사용자 승인을 받는다. 최소:

- complete·partial·failed 3상태와 출발 leg·도착 leg·매칭 키·근거 표시.
- 결정적 매칭과 candidate(금액·시간) 매칭을 시각적으로 구분.
- request의 미지 recipient와 result의 resolved recipient를 분리해 표시.
- 양단 raw 정수식·수수료·asset mapping·arrival window를 표시하고 모순은
  conflict로 노출.
- 외부 fetch/XHR/WebSocket/EventSource 0건(정적 검증).

## 10. 남은 Gate와 Blocker

1. (이 문서) Bridge 계약 제안 사용자 검토·승인.
2. UI Preview 작성·사용자 승인.
3. 완료 — 공식 문서 기준 브리지·chain·event schema와 `FX-SVC-BRG-001`
   공개 후보를 선정한다(docs-only, package 없음).
4. 완료 — 양단 두 source role의 16개 read-only raw replay·SHA·decoded
   match와, `assert_matching_provider_facts`로 두 role의 canonical facts가
   실제로 동일함을 코드로 재확인했다([62 보고서](../05_QA_Validation/62_TASK_016_BRIDGE_RAW_REPLAY_REPORT.md) §8).
   §6의 negative oracle 7개 범주를 8개 synthetic case·2회 결정성으로
   [manifest](../05_QA_Validation/oracles/task-016-bridge-negative-oracles-v0.1.json)에
   고정했다.
5. 완료 — 독립 작성된 raw-first Verifier가 `raw-replay.json`의 raw
   `topics`/`data`를 처음부터 다시 디코딩해 canonical hash를 계산했다
   ([62 보고서](../05_QA_Validation/62_TASK_016_BRIDGE_RAW_REPLAY_REPORT.md) §10).
   candidate-capture 모듈과 코드를 공유하지 않는다.
6. 완료 — `FX-SVC-BRG-001`을 `candidate → verifying`으로 승격했다
   ([63 승격 검토](../05_QA_Validation/63_TASK_016_BRIDGE_FIXTURE_PROMOTION_REVIEW.md)).
   `verifying → confirmed`는 9의 analyzer 구현·독립 검증 이후 별도 판정한다.
7. 완료 — Analysis I/O 대안 B(`bridge_transfer` 전용 leaf)를 정식
   확정했다(§5).
8. 완료 — Context Receipt PASS·offline/artifact analyzer 구현 승인을
   기록했다(2026-07-31). live Rules 미확정 범위와 다른 adapter는 제외한다.
9. 완료 — `bridge_transfer` analyzer 구현과 독립 Verification Receipt를
   기록했다([64 Receipt](../05_QA_Validation/64_TASK_016_BRIDGE_ANALYZER_VERIFICATION_RECEIPT.md)).
   공개 Schema `FixtureRequirementId`에 `BRIDGE`를 추가하고 probe를
   보강했다. `verifying → confirmed`는 별도 판정한다.
10. (별도) `MIXED-XCHAIN-001` 조합 Gate — DEX+Bridge+CEX leg 결합.

**Blocker(해소됨).** 4의 양단 캡처·live 조회는 이미 완료됐다(§10 4번).
Context Receipt·구현 승인·offline analyzer·독립 Verification Receipt는
완료됐다. fixture는 계속 `verifying`이고 Benchmark 12·4·14 및
`MIXED-XCHAIN-001` 분류는 변경하지 않는다. 남은 잔여는
`verifying → confirmed`와 Benchmark 자동화 승격 판정이다.

## 11. Related Documents

- **Concept_Design**: [예상문제 은행 SVC-BRG-001](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제·정답·증거 정의
- **Technical_Specs**: [WP-SERVICE 공통 계약 요소](./20_TASK_016_SERVICE_COMMON_CONTRACT.md) - scoped_subjects·정합·attribution 불변식
- **Technical_Specs**: [Lending 계약 제안](./19_TASK_016_LENDING_CONTRACT_PROPOSAL.md) - 첫 adapter 선례
- **Technical_Specs**: [flow_path IO Contract](./16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - 도착 후 PATH 재사용
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - 체인·provider source
- **QA_Validation**: [예상문제 Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 12·4·14 coverage
- **QA_Validation**: [Bridge Analyzer Verification Receipt](../05_QA_Validation/64_TASK_016_BRIDGE_ANALYZER_VERIFICATION_RECEIPT.md) - analyzer 독립 검증 PASS
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - adapter 범위·Context Receipt
- **Logic_Progress**: [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 서비스·Cross-chain 순서
