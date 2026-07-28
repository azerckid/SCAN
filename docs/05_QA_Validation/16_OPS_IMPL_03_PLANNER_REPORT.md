# OPS-IMPL-03 AI Planner Gate 검증 보고서
> Created: 2026-07-28 13:55
> Last Updated: 2026-07-28 14:09
> Status: Passed · Offline Fake QA Only · Live Rules-Gated

## 1. 범위

이 보고서는 `TASK-010`의 세 번째 구현 단위인 `OPS-IMPL-03`을 검증한다.

포함:

- `PlannerAdapter` Protocol과 boundary가 표시된 strict `PlannerContext`
- provider·model·data boundary·tool mode·rule state를 선검사하는
  `PlannerService`
- synthetic competition 전용 deterministic fake QA adapter
- 방법 가설·Python leaf job plan·raw output artifact 생성
- timeout·token/cost budget·secret·출력 ID 검증과 safe event/error
- SQLite v2 operations repository의 planner artifact metadata 기록

제외:

- local/external AI provider adapter와 실제 model 호출
- scheduler·동시성·evidence worker 실행
- candidate·Verifier·Operations Board runtime
- live RPC·CTFd 호출

## 2. Planner와 답의 경계

Planner 성공 출력은 `PlanHypothesis(status=proposed)`다. 포함되는 값은 문제
유형 가설, 해결 방법 가설, 가정·누락 입력, Python evidence leaf job이다.
candidate·answer·confidence·confirmed result/evidence는 생성하지 않는다.

fake QA adapter는 실제 AI 품질 증거가 아니다. 같은 synthetic projection과
capability 입력에서 반복 가능한 plan을 만들어 mode Gate·후속 scheduler를
offline 검증하는 test double이다. 실제 대회 문제에는 사용할 수 없다.

raw adapter output은 다음 순서로 처리한다.

1. strict `PlanHypothesis`와 command의 plan/problem/mode/planner job ID를
   대조한다.
2. token/cost budget을 검사한다.
3. `SensitiveDataGuard`로 secret·로컬 경로를 검사한다.
4. 기존 content-addressed `ArtifactStore`에 기록한다.
5. 계산된 artifact URI가 plan의 URI와 같은지 확인한다.
6. SQLite v2의 기존 `artifacts` table에 immutable metadata를 기록한다.

중간 실패로 artifact 파일만 남는 경우 덮어쓰거나 삭제하지 않는다. 기존
artifact 복구 원칙에 따라 orphan 검토 대상으로 보존한다.
동일 SHA-256을 다시 기록할 때는 byte length·path뿐 아니라 media type·
artifact kind·redaction·license metadata도 일치해야 한다.

## 3. AI mode Gate

| mode·조건 | adapter 호출 | 결과 |
|:---|:---:|:---|
| `allowed` + 모든 ID·provider·model·boundary 일치 | 1회 | proposed plan 또는 safe `planner_failed` |
| `rules_gated` + waiting planner job | 0회 | `rules_gated` |
| `rule_restricted` + waiting planner job | 0회 | `rule_restricted` |
| provider/model/adapter/boundary 불일치 | 0회 | `rule_restricted` |
| `approved_problem_data` + Operator 미승인 + waiting job | 0회 | `rules_gated` |
| `approved_problem_data` + Operator 미승인 + queued job | 0회 | `invalid_operations_input` |
| `planning_and_approved_tools` + waiting job | 0회 | `rules_gated` |
| fake QA + live competition | 0회 | `rule_restricted` |
| cross-problem·plan·job·mode 참조 오류 | 0회 | `invalid_operations_input` |

allowed mode의 planner job은 `queued`, gated/restricted mode는 `waiting`이어야
한다. fake QA는 `synthetic_test + synthetic_only` 조합에서만 실행된다.

## 4. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-03 planner unit tests | PASS 14 |
| SQLite operations integration tests | PASS 11 |
| 전체 pytest | PASS 187 |
| fixture·Analysis I/O·generated Analysis Schema | PASS 3 / PASS 3 / PASS 3 |
| operations contract runtime/Schema probes | PASS 17 |
| repository traceability | PASS 734 links |
| repository security scan | PASS 58 files |
| 신규 runtime dependency | 없음 |
| live network·AI·CTFd | 0건 |

테스트는 allowed fake 성공, gated/restricted/tool-mode pre-call 차단, live
fake 금지, provider·boundary mismatch, Operator 승인·job 상태, token/cost
budget 초과, timeout, secret raw output, cross-problem command, adapter 출력
ID mismatch를 확인한다.

## 5. QA 판정과 잔여 Gate

`QA-OPS-RULE-001`은 **partial**이다.

완료:

- unclear/rules-gated에서 adapter 호출 0건
- allowed fake QA에서 method hypothesis와 leaf plan 생성
- restricted·boundary·provider mismatch의 pre-call 차단
- evidence 없는 AI 답을 candidate로 승격하는 경로 없음

미실행:

- 실제 local/external AI provider
- 생성된 leaf plan의 scheduler·Python evidence worker 연결
- result·evidence를 candidate·Verifier로 승격하는 통합 흐름

다음 구현 단위는 별도 승인 대상인 `OPS-IMPL-04` bounded Queue·dependency·
problem isolation·dedup이다. 공식 Rules가 확정되기 전 live adapter는 계속
`rules_gated`다.

## 6. Related Documents

- [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md)
- [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md)
- [P0·V1 및 Operations Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md)
- [OPS-IMPL-02 SQLite v2 보고서](./15_OPS_IMPL_02_SQLITE_REPORT.md)
