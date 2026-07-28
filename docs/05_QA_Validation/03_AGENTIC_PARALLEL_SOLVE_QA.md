# SCAN 2026 Agentic Parallel Solve QA
> Created: 2026-07-27 00:54
> Last Updated: 2026-07-28 11:28
> Status: AI-Native Contract Approved 1.0 · UI Preview Gate Passed · Runtime Not Executed · Rules-Gated

## 1. 문서 목적

이 문서는 Agentic Parallel Solve Flow와 Competition Operations Board의
문제 간 병렬성, 문제 내부 병렬성, 데이터 격리, 독립 검증, 규정 차단,
사람 수동 제출을 검증하는 6개 시나리오를 정의한다.

기존 P0·V1 QA 24개와 confirmed fixture 기준선을 변경하지 않는다. 본 문서의
6개 시나리오는 `TASK-010`을 별도로 승인·구현할 때만 실행한다.

## 2. QA 원칙

- 기본 실행은 `offline` 또는 `fault-injection`이다.
- `TASK-010`은 AI Planner를 필수로 사용한다. offline QA는 fake/local AI
  adapter를 사용하고 실제 external AI·RPC·CTFd 호출은 명시적 `live`
  승인 없이는 0건이어야 한다.
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

### QA-OPS-RULE-001 — 필수 AI Planner와 실행 mode Gate

- **Mode**: offline
- **Backlog**: `TASK-010`
- **Requirements**: `REQ-OPS-IN-002`, `REQ-NFR-008`
- **Preconditions**: 필수 AI Planner, 비공개 문제 원문, fake/local·external
  AI adapter, `RULE-AI-001` 상태 전환
- **Steps**:
  1. `unclear`에서 문제를 등록하고 AI planning job 생성 여부를 확인한다.
  2. Rules Gate를 `allowed` fake/local mode로 전환해 해결 방법·leaf job
     hypothesis를 생성한다.
  3. AI plan에 따라 Python evidence tool을 실행하고 result·evidence를 연결한다.
  4. external provider가 `restricted`일 때 해당 호출의
     `rule_restricted` 거부와 공식 허용 adapter로만 교체되는지 확인한다.
  5. AI가 evidence 없는 정답 문장과 높은 confidence를 반환하도록 주입한다.
- **Expected**:
  - AI planning job은 모든 문제에 존재하며 `unclear`에서는 허용 mode를
    기다리는 `rules_gated`다.
  - fake/local mode에서 AI method hypothesis와 leaf plan이 생성되고 Python
    도구 result·evidence로 이어진다.
  - 허용되지 않은 external AI 호출과 비공개 원문 전송은 0건이다.
  - evidence 없는 AI 답은 `review_required`이며 `submission_ready`가 아니다.

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

- [x] 문제 원문·ID·배점·답 형식·파일·URL을 입력하고 AI Planner의 방법 가설을 검토할 수 있다.
- [x] AI Planner가 필수이며 Rules Gate가 provider·model·data mode를 선택하는 것으로 표시된다.
- [x] provider·model·data boundary·tool mode와 현재 `rules_gated` 상태가 한 화면에 보인다.
- [x] `rules_gated` 대기와 `rule_restricted` 호출 거부의 의미가 구분된다.
- [x] Operator가 leaf job·사람 우선순위를 승인한 후에만 Queue로 이동한다.
- [x] 6개 이상의 문제 상태를 한 화면에서 구분할 수 있다.
- [x] problem row는 `Tab`·`Enter`·`Space`, worker는
  `Tab`·`Shift+Tab`·`Enter`·`Space`로 탐색할 수 있다.
- [x] priority 변경, pause·resume, 재배정이 다른 문제 상태를 변경하지 않는다.
- [x] Rules Gate·auto-submit off가 첫 화면에 보인다.
- [x] `review_required`와 `submission_ready`가 색상 없이 구분된다.
- [x] candidate의 전체 answer·format·confidence·uncertainty·recommendation과 evidence 이동 경로가 있다.
- [x] independent verifier ID·check 수·evidence refs·conflict가 표시된다.
- [x] human approval 전 `Mark submitted`가 비활성이고 승인 후 수동 결과·시각을 기록할 수 있다.
- [x] selector에서 loading·empty·stale·Rules unavailable 상태를 확인할 수 있다.
- [x] Problem Board 행에서 partial·failed 상태와 다음 행동을 확인할 수 있다.
- [x] Workbench 이동 후 선택 problem과 filter가 복원된다.
- [x] Preview의 숫자가 실측 성능·정확도로 오인되지 않는다.

UI Preview 체크박스는 2026-07-28 사용자 브라우저 검토와 승인 후 닫았다.
이는 화면 계약의 통과 기록이며, HTML에 demo interaction이 존재한다는
사실만으로 `TASK-010` runtime QA를 `pass`로 변경하지 않는다.

## 7. 365 글로벌 평가 기준

| Criterion | Status | Draft 검증 증거 |
|:---|:---:|:---|
| Functionality | Not Executed | 문제·leaf 병렬성, 격리, dedup, dependency 시나리오 |
| Potential Impact | Not Executed | 제한 시간 내 복수 문제 처리량과 Queue age 측정 |
| Novelty | Not Executed | evidence-first 독립 검증과 role fallback |
| UX | Preview Passed / Runtime Not Executed | 사용자 브라우저 검토 통과; runtime 상태 판독·키보드·수동 제출은 미실행 |
| Open-source | Not Executed | 교체 가능한 worker·CLI·Analysis I/O 계약 |
| Business Plan | N/A | 대회 운영 QA이며 수익 모델 검증 범위 아님 |

## 8. Originality & Ethics Check

- [ ] AI Planner의 method hypothesis·실행 mode·전송 데이터와 Rules 근거가 감사 가능하다.
- [ ] agent 결과를 제3자 범죄·신원 확정으로 자동 승격하지 않는다.
- [ ] 공식·외부 맥락과 heuristic을 분리한다.
- [ ] 문제·답안·credential을 허용되지 않은 서비스에 저장하지 않는다.
- [ ] CTFd 자동 제출·brute force·팀 외부 답안 공유 기능이 없다.
- [ ] 사람이 최종 제출 책임과 불확실성을 확인한다.

## 9. 승인과 실행 Gate

- [ ] 사용자가 6개 운영 QA 시나리오를 승인했다.
- [x] Operations Board Preview를 사용자가 확인했다.
- [ ] 공식 Rules에서 AI provider·model·data mode와 worker·source 범위를 확인했다.
- [ ] `TASK-010` 구현을 별도로 승인했다.
- [ ] 구현된 시나리오만 `pass / partial / fail / blocked`로 기록한다.
- [ ] 실행하지 않은 시나리오는 `not_executed`로 유지한다.

## 10. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - AI·자동화·협업·데이터·제출 Gate
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 화면 상태·사용자 흐름
- **UI_Screens**: [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - 정적 UI 검토
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - `REQ-OPS-*` 규범
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - 구현 model·mutation·동시성·adapter 제안
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - leaf result 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - `TASK-010` 책임
- **Logic_Progress**: [Roadmap](../04_Logic_Progress/00_ROADMAP.md) - Rules-gated 비차단 운영 트랙
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - 기존 24개 코어 QA 기준선
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - 운영 QA 승인·대회 전 실행 시점
