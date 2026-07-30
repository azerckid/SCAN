# TASK-016 WP-SERVICE 공통 계약 요소 (Lending 검증분 추출)
> Created: 2026-07-30 20:45
> Last Updated: 2026-07-30 20:45
> Status: docs-only · Lending 리뷰 확정분만 추출 · adapter별 재검증 필요

## 0. 이 문서의 위치

이 문서는 Lending([계약 제안 doc 19](./19_TASK_016_LENDING_CONTRACT_PROPOSAL.md))와
[UI Gate(doc 10/preview 09)](../02_UI_Screens/10_TASK_016_LENDING_UI.md)에서
리뷰로 확정된 계약 구조 중 **여러 서비스 adapter에 일반화할 수 있는 요소만**
추출한다. 코드·Schema·fixture를 변경하지 않는다. 추출한 패턴은 설계 재사용
후보이며, 각 adapter(Bridge/XChain·Mixer·CEX)는 자신의 fixture·계약 Gate에서
다시 검증한다. Lending에서 실증되지 않은 구조는 여기 넣지 않는다.

권장 순서: Lending → (이 문서)공통 추출 → Bridge/XChain → Mixer/CEX.

## 1. 추출한 공통 불변식 (Lending 리뷰 확정분)

### 1.1 Subject scope와 역할 집합 binding
- 공통 계약은 subject를 **`scoped_subjects[]`**로 정의한다. 각 항목은
  `(chain, address, roles[])`이며, 단일 체인 adapter(Lending)는 항목 1개
  (`subject_address` + `subject_roles[]`)로, 양단 adapter(Bridge)는 source
  체인·destination 체인 subject를 각각의 항목으로 표현한다. source sender와
  destination recipient가 서로 다를 수 있다.
- 역할은 **표시·검증·request↔replay binding 용도**이며 leg/edge 선택 필터가
  아니다. 한 주소가 복수 역할을 가질 수 있으므로 단일 역할로 축소하면 다른
  역할의 value 이동이 누락된다.
- **집계 대상 = 각 scoped subject의 address가 실제 sender/receiver인 정합 통과
  leg 전부.**
- 관찰된 역할·subject 집합과 request 집합의 관계는 adapter가 선언한다. 완전한
  한 사건이 요구되는 경우(Lending 단일 체인)는 exact-set 불일치를
  `reconciliation_failed`로, **한쪽 정보만 확보된 경우(예: Bridge 목적지 체인
  replay 부재)는 `partial`**로 처리한다(무조건 실패가 아니다). 요청에 없는
  주소·역할로 합성하는 것은 언제나 거부한다.
- negative oracle: 복수 역할 주소를 단일 역할로 축소해 leg 누락 → 거부.

> Lending 고유: `scoped_subjects[]` 1개 + 역할 exact-set 강제. 다른 adapter는
> §3과 자신의 Gate에서 항목 수·부분 확보 허용 여부를 다시 정한다.

### 1.2 선언 이벤트 ↔ 실제 value 이동 정합
- 서비스 이벤트의 amount는 실제 자산 이동과 **항상 같다고 볼 수 없다.** 각
  leg는 protocol/service event ↔ 실제 value 기록(ERC-20 `Transfer`·native·
  internal·bridge message·mint/burn·lock/release 등 adapter가 정한 value
  근거)과 정합해야 집계에 포함한다.
- 의미가 다른 leg(예: Lending의 principal·fee·debt·collateral)는 **자산·방향
  별로 분리**한다. 하나의 이벤트가 서로 다른 자산의 유입·유출을 만들 수 있다.
- 정합되지 않는 leg → partial(과장 금지).

### 1.3 Value-movement evidence 완결성 (trace는 그 한 형태)
- 공통 규칙은 "집계에 필요한 각 leg의 **value-movement evidence가 확보될
  때만** `complete`"이다. 이 evidence는 adapter에 따라 log·state·message·
  Transfer일 수 있고 반드시 trace일 필요는 없다(예: Bridge mint/burn·lock/
  release, CEX 입금은 log/state/message로 완결될 수 있다).
- **adapter가 특정 leg에 call_evidence(trace)를 필수로 선언한 경우에만** trace
  부재를 partial로 처리한다.
- oracle는 "해당 adapter가 trace를 필수로 선언한 fixture"로 조건화해 event-
  only/log-only complete와 충돌하지 않게 한다.

### 1.4 사실·assertion·heuristic·not_assessed 4분
서비스 귀속을 일괄 not_assessed로 두지 않고 증거 강도로 나눈다.

- **confirmed fact**: 디코딩 이벤트, raw amount, 정합 leg, 순자산/그래프,
  bounded 경로(주소·금액).
- **evidence-backed assertion**: 공식·검증된 컨트랙트 식별(예: Bridge 공식
  bridge 컨트랙트), confirmed source-claim(예: CEX deposit-address가 confirmed
  INTEL/LABEL source에서 명시). **truth가 아니라 근거 있는 주장**으로 표기하고
  출처·시점을 함께 남긴다.
- **heuristic service candidate**: fan-out·clustering 등 패턴 기반 후보 →
  `assessment`로만, 확정 사실 아님.
- **not_assessed(자동 단정 금지)**: 소유, 실세계 본인성, 범죄성·불법성, 의도.

assertion·heuristic을 confirmed fact나 truth로 승격하지 않는다.

### 1.5 Evidence 봉투와 결정적 정렬
- 공통 result/evidence/source/run 봉투를 유지하고 `inputs`·`result_type/value`
  만 최소 확장한다.
- evidence: `event_evidence`·`transfer_evidence`·(선택)`call_evidence`·
  (선택)`state_evidence`를 각각 `source_requirements`로 연결.
- 이벤트 정렬 키는 `(block_number, transactionIndex, logIndex)`로 고정.
- 후속 PATH seed는 계산된 집계에서 subject가 실제 수령한 leg의 수령 주소에서
  유도한다(임의 주소 금지).

### 1.6 오류 계약 — 기존 `ErrorCode` 재사용
- 핵심 원칙은 **새 public `ErrorCode` 금지**이며 "5개만 허용"이 아니다.
- 아래는 Lending에서 추출한 **최소 집합**이다: `invalid_input`(입력 경계),
  `decode_failed`(이벤트 스키마·`topic0`), `trace_unavailable`(필수 trace
  부재), `reconciliation_failed`(scope·역할·정합 실패),
  `evidence_incomplete`(증거 부족).
- 다른 adapter는 필요 시 기존 enum의 나머지 코드
  (`source_unavailable`·`archive_required`·`rate_limited`·`rule_restricted`·
  `schema_invalid`·`unsupported_chain` 등)를 그대로 사용한다. 구체값은
  `stage`/`message`로만 표현한다.

### 1.7 상태·negative oracle 계열
- complete/partial/failed 정의(§1.2·§1.3 기준).
- oracle 계열: ①타 프로토콜/서비스 오귀속 ②시간창 밖 포함 ③adapter가 trace를
  필수로 선언한 fixture의 evidence-only complete ④event↔value 불일치 합산
  ⑤scope/역할 합성(요청에 없는 주소·역할) ⑥heuristic/assertion을 confirmed
  fact나 truth로 승격 ⑦소유·본인성·범죄성 자동 단정. 캡처 Gate에서 2회
  결정성으로 고정.

### 1.8 Analysis I/O 접근
- vertical 패턴(evm_special·flow_path·intel_context, 그리고 Lending의 전용
  leaf 방향 `defi_lending`)을 따른다. adapter 착수 시 **전용 leaf 신설 vs 공유
  service 유형**을 먼저 결정하고 공통 봉투는 유지한다.

## 2. adapter별 적용성 (일반화 경계)

| 공통 요소 | Bridge/XChain | Mixer | CEX |
|:---|:---|:---|:---|
| §1.1 scoped_subjects[] binding | 양단 source/dest 항목·한쪽 부재 partial | 적용 | 적용 |
| §1.2 event↔value 정합 | 적용 | 적용(제한적) | 적용 |
| §1.3 value-movement evidence 완결 | log/message/state로 완결 가능 | 적용 | log/state로 완결 가능 |
| §1.4 사실·assertion·heuristic·not_assessed | 공식 bridge 컨트랙트=assertion | **핵심**(대부분 heuristic/not_assessed) | 라벨=confirmed source-claim assertion |
| §1.5 evidence·정렬·PATH seed | 적용(체인별) | 적용 | 적용 |
| §1.6 ErrorCode 재사용 | 적용 | 적용 | 적용 |
| §1.7 oracle 계열 | 적용+양단 | 적용+반례 | 적용+반례 |

**adapter별 추가/차이(공통에서 다루지 않음).**

- **Bridge/XChain**: 양단 chain·message·nonce·asset·amount·time **대응**이 새
  축이다. Lending의 단일 체인 ledger를 두 체인에 그대로 확장하지 않고, 양단
  replay 간 message/amount binding을 별도 계약으로 세운다.
- **Mixer**: deposit/withdraw pool 상호작용은 사실이지만 **입금↔출금 귀속은
  heuristic**이다. 대부분 출력이 not_assessed/heuristic이며 확정 사실은 pool
  이벤트·금액에 한정된다. PATH 연결도 후보로만.
- **CEX**: deposit-address·cluster 귀속은 **INTEL/LABEL confirmed source에
  의존**하며 truth가 아니라 source-claim이다. 온체인 이동은 사실, 거래소
  소유·본인성은 not_assessed.

## 3. Lending 고유 요소 (일반화 금지)

- principal·flashloan premium·debt·collateral **leg 분류 taxonomy**는 lending
  전용이다. 다른 adapter는 §1.2의 일반 규칙(선언 leg ↔ 실제 value leg 분리)만
  가져가고 이 세부 분류를 이식하지 않는다.
- **단일 `scoped_subjects[]` 항목 + 역할 exact-set 강제**는 단일 체인·완전한 한
  사건을 전제한 lending 규칙이다. 양단·부분 확보 adapter는 §1.1대로 항목 수와
  부분 확보 partial 허용 여부를 자신의 Gate에서 다시 정한다.
- "공격 vs 정상 청산" 경계는 §1.4 not_assessed 규칙의 lending 사례일 뿐이며,
  각 adapter는 자신의 도메인 판단 항목을 not_assessed로 별도 식별한다.

## 4. 이 문서가 하지 않는 것

- 코드·Schema·Analysis I/O·fixture 변경 없음. coverage 무변동(12·4·14).
- adapter 계약 확정·fixture 캡처·Context Receipt PASS·구현 승인은 각 adapter
  Gate로 유예. live/archive source는 Rules·Terms 확정까지 후순위.
- 이 문서는 재사용 **후보 골격**이며, 각 요소는 adapter fixture에서 다시
  검증되기 전까지 확정 사실이 아니다.

## 5. Related Documents

- **Technical_Specs**: [Lending 계약 제안](./19_TASK_016_LENDING_CONTRACT_PROPOSAL.md) - 추출 원본
- **Technical_Specs**: [Coverage 확장 Brief §5.5 WP-SERVICE](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - 서비스 계약 경계
- **Technical_Specs**: [flow_path IO Contract](./16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - PATH·ErrorCode 재사용 선례
- **UI_Screens**: [Lending UI](../02_UI_Screens/10_TASK_016_LENDING_UI.md) - UI Gate 확정분
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - adapter 범위·Context Receipt
- **Logic_Progress**: [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md) - 서비스·Cross-chain 순서
