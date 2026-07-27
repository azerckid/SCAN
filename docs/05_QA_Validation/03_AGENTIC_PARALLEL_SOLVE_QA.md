# SCAN 2026 Agentic Parallel Solve QA
> Created: 2026-07-27 00:54
> Last Updated: 2026-07-27 15:52
> Status: Draft 1 · Scope Approved · Not Executed · Rules-Gated

## 1. 문서 목적

이 문서는 Agentic Parallel Solve Flow와 Competition Operations Board의
문제 간 병렬성, 문제 내부 병렬성, 데이터 격리, 독립 검증, 규정 차단,
사람 수동 제출을 검증하는 6개 시나리오를 정의한다.

기존 P0·V1 QA 24개와 confirmed fixture 기준선을 변경하지 않는다. 본 문서의
6개 시나리오는 `TASK-010`을 별도로 승인·구현할 때만 실행한다.

## 2. QA 원칙

- 기본 실행은 `offline` 또는 `fault-injection`이다.
- 실제 AI·RPC·CTFd 호출은 명시적 `live` 승인 없이는 0건이어야 한다.
- 문제 원문·답안·credential을 외부 서비스에 전송하지 않는다.
- agent의 자연어 결론은 결정적 증거가 아니다.
- 같은 worker가 만든 후보를 같은 실행이 독립 검증했다고 표시하지 않는다.
- CTFd 자동 제출·brute force는 테스트 대상 구현 자체가 없어야 한다.

## 3. 병렬성·격리 Gate

### QA-OPS-PAR-001 — 문제 간 병렬 실행과 격리

- **Mode**: fault-injection
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-QUEUE-001`~`REQ-OPS-QUEUE-006`
- **Preconditions**: Q01 DEX, Q02 AUTH, Q03 FLOW 고정 request와 서로 다른 workspace
- **Steps**:
  1. 세 문제를 동시에 Queue에 넣고 서로 다른 worker에 배정한다.
  2. Q02 worker에 timeout을 주입한다.
  3. Q01·Q03을 완료하고 Q02를 partial·retry 상태로 유지한다.
  4. problem·analysis·artifact·checkpoint 참조를 교차 검사한다.
- **Expected**:
  - 두 개 이상의 문제가 실제로 겹치는 실행 구간을 가진다.
  - Q02 실패가 Q01·Q03 상태를 실패로 변경하지 않는다.
  - 다른 problem의 result·candidate·checkpoint가 혼합되지 않는다.
  - 공유 raw artifact는 hash로 재사용되며 problem별 evidence 참조가 존재한다.

### QA-OPS-INTRA-001 — 문제 내부 leaf job 병렬성과 dependency

- **Mode**: fault-injection
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-QUEUE-001`, `REQ-OPS-QUEUE-002`,
  `REQ-OPS-QUEUE-003`, `REQ-OPS-QUEUE-006`
- **Preconditions**: receipt·trace·state가 독립 leaf이고 reconciliation이 세 결과에 의존
- **Steps**:
  1. 세 leaf job을 동시에 시작한다.
  2. 같은 receipt request를 두 worker에서 요청한다.
  3. state job을 지연시키고 reconciliation 실행 조건을 확인한다.
  4. 모든 dependency 완료 후 reconciliation을 실행한다.
- **Expected**:
  - 독립 leaf는 병렬 실행되고 reconciliation은 dependency 전 실행되지 않는다.
  - 동일 source request의 외부 호출은 dedup되어 1건이다.
  - 지연 중 상태는 거짓 complete가 아니라 waiting 또는 partial이다.
  - leaf별 `analysis_id`와 source provenance가 유지된다.

## 4. 검증·충돌 Gate

### QA-OPS-VERIFY-001 — 독립 검증 없는 승격 차단

- **Mode**: offline
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-VERIFY-001`~`REQ-OPS-VERIFY-006`
- **Preconditions**: 정답 후보 1개, 결정적 result·evidence, Verifier 미실행
- **Steps**:
  1. Reporter가 후보를 생성한다.
  2. 같은 분석 worker의 self-check만 추가한다.
  3. 독립 Verifier가 raw evidence를 재조회해 필수 check를 완료한다.
- **Expected**:
  - 1·2의 후보는 `review_required`이며 `submission_ready`가 아니다.
  - 독립 검증의 role·verification ID·evidence refs가 기록된다.
  - 주소·TX·chain·raw amount·decimals·format 통과 후에만 승격된다.

### QA-OPS-CONFLICT-001 — 에이전트 결과 충돌 보존

- **Mode**: fault-injection
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-VERIFY-004`, `REQ-OPS-VERIFY-006`
- **Preconditions**: 동일 주소에 공식 label A와 heuristic label B가 존재
- **Steps**:
  1. 두 결과를 candidate builder에 전달한다.
  2. 높은 confidence의 heuristic을 주입한다.
  3. Operator가 추가 조사 job을 배정한다.
- **Expected**:
  - 공식 맥락과 heuristic을 합치거나 조용히 하나를 선택하지 않는다.
  - conflict field·출처·분류·다음 행동이 표시된다.
  - confidence만으로 `submission_ready`가 되지 않는다.

## 5. 규정·제출 Gate

### QA-OPS-RULE-001 — AI·외부 전송 사전 차단

- **Mode**: offline
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-IN-002`, `REQ-NFR-008`
- **Preconditions**: `RULE-AI-001=unclear`, 비공개 문제 원문, AI worker enabled 요청
- **Steps**:
  1. 문제를 등록하고 AI worker 배정을 요청한다.
  2. 외부 tool 호출 수와 저장 prompt를 검사한다.
  3. human·Python CLI fallback을 선택한다.
- **Expected**:
  - 외부 AI 호출은 0건이고 `rule_restricted` 또는 rules-gated 상태다.
  - 비공개 원문이 외부 prompt·artifact에 없다.
  - 문제는 폐기되지 않고 human·CLI 경로로 재배정할 수 있다.

### QA-OPS-SUBMIT-001 — 사람 제출 통제와 credential 비보존

- **Mode**: fault-injection
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-SUBMIT-001`~`REQ-OPS-SUBMIT-004`
- **Preconditions**: 검증 완료 후보, 가짜 CTFd endpoint·credential canary
- **Steps**:
  1. Operations Board에서 답을 복사한다.
  2. 자동 제출 action 존재 여부와 network log를 검사한다.
  3. 사람이 `Mark submitted`를 선택하고 제출 결과를 수동 기록한다.
  4. log·DB·artifact·UI state에서 credential canary를 검색한다.
- **Expected**:
  - CTFd network call은 0건이며 자동 submit·brute force action이 없다.
  - 복사값은 축약되지 않은 전체 answer다.
  - `submitted`는 사람 확인 후에만 전환된다.
  - credential·session·Authorization canary는 모든 저장 대상에서 0건이다.

## 6. UI Preview Gate

- [ ] 6개 이상의 문제 상태를 한 화면에서 구분할 수 있다.
- [ ] problem row와 worker 상태를 키보드로 탐색할 수 있다.
- [ ] Rules Gate·auto-submit off가 첫 화면에 보인다.
- [ ] `review_required`와 `submission_ready`가 색상 없이 구분된다.
- [ ] candidate의 전체 answer와 evidence 이동 경로가 있다.
- [ ] loading·empty·partial·failed·stale 상태가 문서에 정의되어 있다.
- [ ] Workbench 이동 후 Operations 상태가 유지되는 계약이 있다.
- [ ] Preview의 숫자가 실측 성능·정확도로 오인되지 않는다.

## 7. 365 글로벌 평가 기준

| Criterion | Status | Draft 검증 증거 |
|:---|:---:|:---|
| Functionality | Not Executed | 문제·leaf 병렬성, 격리, dedup, dependency 시나리오 |
| Potential Impact | Not Executed | 제한 시간 내 복수 문제 처리량과 Queue age 측정 |
| Novelty | Not Executed | evidence-first 독립 검증과 role fallback |
| UX | Not Executed | Operations Board 상태 판독·키보드·수동 제출 |
| Open-source | Not Executed | 교체 가능한 worker·CLI·Analysis I/O 계약 |
| Business Plan | N/A | 대회 운영 QA이며 수익 모델 검증 범위 아님 |

## 8. Originality & Ethics Check

- [ ] 외부 AI·API에 전송한 데이터와 Rules 근거가 감사 가능하다.
- [ ] agent 결과를 제3자 범죄·신원 확정으로 자동 승격하지 않는다.
- [ ] 공식·외부 맥락과 heuristic을 분리한다.
- [ ] 문제·답안·credential을 허용되지 않은 서비스에 저장하지 않는다.
- [ ] CTFd 자동 제출·brute force·팀 외부 답안 공유 기능이 없다.
- [ ] 사람이 최종 제출 책임과 불확실성을 확인한다.

## 9. 승인과 실행 Gate

- [ ] 사용자가 6개 운영 QA 시나리오를 승인했다.
- [ ] Operations Board Preview를 사용자가 확인했다.
- [ ] 공식 Rules에서 활성화할 worker·source 범위를 확인했다.
- [ ] `TASK-010` 구현을 별도로 승인했다.
- [ ] 구현된 시나리오만 `pass / partial / fail / blocked`로 기록한다.
- [ ] 실행하지 않은 시나리오는 `not_executed`로 유지한다.

## 10. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - AI·자동화·협업·데이터·제출 Gate
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 화면 상태·사용자 흐름
- **UI_Screens**: [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - 정적 UI 검토
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - `REQ-OPS-*` 규범
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - leaf result 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - `TASK-010` 책임
- **Logic_Progress**: [Roadmap](../04_Logic_Progress/00_ROADMAP.md) - Rules-gated 비차단 운영 트랙
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - 기존 24개 코어 QA 기준선
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - 운영 QA 승인·대회 전 실행 시점
