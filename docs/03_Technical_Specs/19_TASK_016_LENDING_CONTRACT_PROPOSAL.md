# TASK-016 Lending(SVC-LEND-001) Analysis 계약 제안 (docs-only)
> Created: 2026-07-30 20:45
> Last Updated: 2026-07-30 20:45
> Status: docs-only Proposal · 사용자 승인 전 · 코드·fixture 캡처 미착수

## 0. 이 문서의 위치

이 문서는 TASK-016 Wave 5의 첫 adapter인 **Lending(`SVC-LEND-001`)**을
docs-only로 제안한다. 코드·Schema·fixture 데이터·Analysis I/O를 변경하지
않으며, Context Receipt PASS나 구현 승인을 자가 판정하지 않는다. 여기서
검증된 구조만 이후 공통 요소로 추출해 Bridge·Mixer·CEX에 적용한다
(권장 순서: Lending → 공통 추출 → Bridge/XChain → Mixer/CEX).

**현재 전제(Context Receipt 요지).** `SVC-LEND-001`용 confirmed fixture는
없으며(서비스 fixture는 automated인 `FX-SVC-DEX-001`뿐), source/Rules는
미확정이다. 따라서 이 Gate의 achievable 범위는 문제·정답 계약, 공식
프로토콜·ABI·주소 **후보 조사**, candidate fixture ID·선정 기준, evidence
분리, complete/partial/failed·negative oracle 계약, UI Preview 요구까지이며,
실제 fixture 캡처·live 조회는 이후 별도 Gate로 유예한다.

## 1. 대상 문제·정답 범위 확정

**문제(은행 SVC-LEND-001).** 주어진 TX 또는 주소에서 플래시론·대출·청산이
포함된 자금 경로를 복원한다. 단서: 시드 TX 또는 주소, 시간 창, (선택)
프로토콜 이름.

**정답 형식(결정적 사실만).**

1. **이벤트 요약** — 시간·TX 순서로 정렬한 borrow·repay·liquidation·
   collateral(공급/인출)·flashloan 이벤트의 디코딩 요약(프로토콜, 자산,
   raw amount, 참여 주소, block/logIndex).
2. **순자산 변화** — subject scope 기준 자산별 raw 유입−유출 ledger(정합
   실패 시 partial).
3. **후속 유출 경로** — 청산/차입 이익이 이어지는 bounded outflow(기존 PATH
   계약 재사용, 라벨·귀속 없이 주소·금액·경로만).

**판정 경계(중요).** "공격 vs 정상 청산" 판별은 **사람 몫**이므로 자동
단정하지 않는다. analyzer는 이벤트·금액·경로라는 관찰 가능한 사실만 계산하고
공격성·불법성·서비스 귀속은 `not_assessed`로 둔다.

## 2. 공식 프로토콜·ABI·배포 주소 후보 조사

아래는 **후보**이며, 정확한 ABI·`topic0`·배포 주소는 capture 시 공식·검증된
컨트랙트에서 pin하고 독립 재계산으로 확정한다(이 문서는 주소·해시를 사실로
고정하지 않는다).

| 프로토콜 후보 | 관련 이벤트 계열(후보) | 비고 |
|:---|:---|:---|
| Aave V2 LendingPool | `Borrow`·`Repay`·`LiquidationCall`·`FlashLoan`·`Deposit`·`Withdraw` | 단일 pool, 청산 파라미터 풍부 |
| Aave V3 Pool | `Borrow`·`Repay`·`LiquidationCall`·`FlashLoan`·`Supply`·`Withdraw` | V2와 이벤트 유사 |
| Compound V2 cToken | `Borrow`·`RepayBorrow`·`LiquidateBorrow`·`Mint`·`Redeem` | 자산별 cToken 다중 컨트랙트 |
| Compound V3 (Comet) | `Supply`·`Withdraw`·`AbsorbDebt`·`BuyCollateral` | 청산 모델 상이 |

**선정 원칙.** ① 공개·검증(verified) 컨트랙트, ② 이벤트 스키마가 공식
문서/ABI로 확인 가능, ③ 재배포·조회 조건이 대회 Rules와 충돌하지 않음.
프로토콜별 청산 이벤트 의미가 다르므로 fixture는 **한 프로토콜·한 사건**으로
한정하고 일반화하지 않는다.

## 3. Candidate fixture ID와 공개 사례 선정 기준

**제안 fixture ID.** `FX-SVC-LEND-001`(candidate) — 단일 프로토콜의
차입→(플래시론)→청산→후속 유출이 한 시간 창에 관찰되는 공개 사례.

**선정 기준.**

- 시드 TX 또는 주소와 bounded 시간·block 창이 명확할 것.
- borrow·repay·liquidation·collateral 중 최소 청산 1건과 순자산 변화가
  로그만으로 재구성 가능할 것(trace는 선택 보강).
- 후속 유출이 기존 PATH 계약의 bounded scope로 이어질 것.
- 두 provider replay에서 decoded 값이 일치할 것(캡처 Gate에서 확인).
- "공격/정상" 라벨 없이 사실만으로 채점 가능한 사례일 것.

실제 사례·주소·TX 확정과 raw replay 캡처는 **캡처 Gate**로 유예한다.

## 4. event / call / state evidence 분리

기존 EVM Core·DEX evidence 봉투를 재사용하고 유형만 최소 확장한다.

- **event_evidence** — 디코딩된 lending 이벤트(log): 프로토콜, 이벤트명,
  자산, raw amount, 참여 주소, block·txHash·logIndex, `topic0`.
- **call_evidence(선택)** — flashloan/청산 경로 보강용 trace의 value-bearing
  internal call. 없으면 partial 사유로 남기고 이벤트만으로 계산.
- **state_evidence(선택)** — 필요 시 청산 전후 잔액/부채 상태(historical
  balance). 없으면 순자산 변화는 이벤트 amount 합산으로만 계산하고 부족분을
  partial로 표기.

세 evidence는 각각 `source_requirements`로 연결하고, 이벤트만으로 충분한
경우 call/state 부재가 `complete`를 막지 않는다.

## 5. Analysis I/O 영향 — 대안 제시(승인 대상)

Analysis I/O `0.1`에 유형을 바로 추가하지 않고 착수 시 `0.2` 확장을
결정한다는 Brief §6 원칙을 따른다. 두 대안을 제시하며 **대안 B를 권장**한다.

- **대안 A(합성 재사용).** 신규 leaf type 없이 `evm_core`/`evm_special`
  디코딩 + `flow_path` PATH를 조합해 사람이 정합. 장점: Schema 무변경. 단점:
  lending 이벤트 정합·순자산 ledger를 담을 전용 result가 없어 자동 채점 불가
  → `assisted`에 머문다.
- **대안 B(전용 leaf type, 권장).** 기존 vertical 패턴(evm_special·flow_path·
  intel_context)과 동일하게 전용 `AnalysisType`(예: `defi_lending`) 1종과
  query(예: `reconstruct_lending_flow`)를 추가하고, result에 이벤트 요약·
  순자산 ledger·후속 PATH를 담는다. 기존 공통 result/evidence/source/run
  봉투는 유지하고 `inputs`·`result_type/value`만 최소 확장한다. 장점:
  결정적 자동 채점·Benchmark 승격 경로 확보. 이 명칭·필드는 승인 후 최종 IO
  계약 문서에서 확정한다.

## 6. complete · partial · failed · negative oracle 계약

**complete.** 시드 scope의 lending 이벤트가 모두 디코딩되고, 순자산 변화가
자산별로 정합하며, 후속 유출 PATH가 bounded scope로 닫힌다. 공격성·귀속은
`not_assessed`를 유지한 채 사실만으로 정답 3필드가 채워진다.

**partial.** 이벤트는 디코딩됐으나 trace/state 부재로 순자산 변화 또는 유출
경로 일부가 미확정. 미확보 항목을 `partial_conditions`로 남기고 확정 사실만
보고한다.

**failed.**

- 정상 청산을 공격으로(또는 그 반대로) 자동 단정.
- 서비스 귀속·불법성을 확정 사실로 승격.
- 관련 없는 자금 이동을 lending 경로로 계산.
- 프로토콜 이벤트 스키마 불일치(잘못된 `topic0`)로 오디코딩.

**negative oracle(캡처 Gate에서 2회 결정성으로 고정).**

1. 다른 프로토콜의 유사 이벤트를 대상 프로토콜로 오귀속 → 거부.
2. 시간 창 밖 이벤트를 경로에 포함 → 거부.
3. trace 없는 순자산 주장 → partial 강제(complete 금지).
4. liquidation을 attack으로 라벨 → 거부(`not_assessed` 유지).
5. request scope에 없는 주소/자산으로 ledger 합성 → `reconciliation_failed`.

## 7. 오류 계약 — 기존 `ErrorCode` enum 재사용(신규 코드 없음)

새 public `ErrorCode`를 추가하지 않는다. 매핑: 입력 경계 위반
`invalid_input`, 디코딩 실패 `decode_failed`, trace 필요·부재 `trace_unavailable`
(선택 보강이 필수로 승격된 경우), 순자산·scope 정합 실패
`reconciliation_failed`, 증거 부족 `evidence_incomplete`. 프로토콜·단계
구체값은 `stage`/`message`로만 표현한다.

## 8. confirmed-fact vs heuristic 경계

- **confirmed fact**: 디코딩된 이벤트, raw amount, 순자산 ledger, bounded 유출
  경로(주소·금액).
- **heuristic / 사람 판단(자동 단정 금지)**: 공격 vs 정상 청산, 서비스 귀속,
  의도·불법성. 필요 시 별도 `assessment`로만 표기하고 확정 사실과 섞지
  않는다.

## 9. UI Preview 요구(다음 Gate)

이 제안 승인 후, lending 전용 HTML Preview를 별도로 작성해 사용자 승인을
받는다. Preview는 최소 아래를 보여야 한다.

- complete·partial·failed 3상태와 각 상태의 이벤트 타임라인·순자산 ledger·
  유출 경로 표시.
- 공격/정상 판별을 자동 표기하지 않고 `not_assessed`로 노출.
- 외부 fetch/XHR/WebSocket 0건(정적 검증).

## 10. 남은 Gate와 Blocker

1. (이 문서) Lending 계약 제안 사용자 검토·승인.
2. UI Preview 작성·사용자 승인.
3. 공식 프로토콜·ABI·주소 pin과 `FX-SVC-LEND-001` 공개 사례 확정.
4. 두 provider raw replay 캡처·decoded 일치·negative oracle 2회 결정성.
5. 독립 Verifier raw-first 재계산·canonical hash 대조.
6. `candidate → verifying → confirmed` 승격 검토(사용자 Gate).
7. Context Receipt PASS·구현 승인 후에만 analyzer 구현.

**Blocker.** 3·4의 실제 캡처·live 조회는 confirmed fixture와 source/Rules·
Terms 확정이 필요하며, 이는 live/archive source Gate로 유예된다
([Promotion Readiness](../05_QA_Validation/54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) §2 Retrieval permission).
따라서 `SVC-LEND-001`은 현재 `unsupported`이며 이 문서로 coverage를 바꾸지
않는다(Benchmark 12·4·14 무변동).

## 11. Related Documents

- **Concept_Design**: [예상문제 은행 SVC-LEND-001](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제·정답·증거 정의
- **Technical_Specs**: [Coverage 확장 Brief §5.5 WP-SERVICE](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - lending 계약 경계
- **Technical_Specs**: [flow_path IO Contract](./16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - 후속 유출 PATH 재사용
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - provider·chain source
- **Technical_Specs**: [오픈소스 조사](./06_OPEN_SOURCE_FORENSICS_REVIEW.md) - decoder/ABI 재사용 Gate
- **QA_Validation**: [예상문제 Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 12·4·14 coverage
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-SERVICE-001
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - adapter 범위·Context Receipt
- **Logic_Progress**: [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 서비스·Cross-chain 순서
