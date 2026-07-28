# OPS-IMPL-08 Submission·Security·Final Integration 검증 보고서
> Created: 2026-07-29 00:41
> Last Updated: 2026-07-29 00:41
> Status: Passed · Offline Operations V1 Complete / Live Mode Rules-Gated

## 1. 목적과 범위

이 보고서는 OPS-IMPL-01~07의 계약·저장·Planner·Queue·Evidence·Verifier·
Snapshot을 사람의 수동 제출 기록까지 연결하고, 6개 Agentic Parallel Solve
QA를 offline 범위에서 닫았는지 기록한다.

포함 범위:

- 같은 문제의 독립 evidence leaf를 job별 하위 workspace에서 병렬 실행
- 모든 dependency가 끝난 뒤 Reporter reconciliation 실행
- 문제별·job별 SQLite workspace·Analysis result 격리
- stale과 Rules unavailable을 동시에 보존하는 snapshot alerts
- 명시적 SQLite v2 database의 read-only Operations Board 조회
- `submission_ready` candidate의 전체 답 복사와 별도 human-confirmed 제출 기록
- candidate·problem·submission·manifest·append-only event의 원자적 SQLite 갱신
- `correct`·`incorrect`·`unknown` CTFd 응답의 로컬 기록
- official fact와 heuristic label의 동일 replay에서도 confirmed 승격 차단
- problem·plan이 함께 어긋날 때 problem scope 오류를 우선하는 회귀

제외 범위:

- CTFd endpoint·credential·session·자동 submit·brute force
- live AI·RPC·외부 문제 데이터 전송
- Operations Board 웹 runtime과 HTTP API
- SQLite v3 migration과 candidate reference ordinal

## 2. 구현

| 위치 | 책임 |
|:---|:---|
| `src/scan_tool/application/submission.py` | 사람 확인·ready Gate·수동 응답·안전한 event와 updated document |
| `src/scan_tool/adapters/sqlite_operations.py` | 제출 전이의 guarded atomic persistence와 post-write 재검증 |
| `src/scan_tool/application/operations_snapshot.py` | primary view state와 stale·Rules alerts 동시 보존 |
| `src/scan_tool/adapters/evidence.py` | problem/job 하위 workspace와 job 단위 lock |
| `src/scan_tool/application/evidence_worker.py` | evidence job별 workspace key |
| `src/scan_tool/cli.py` | explicit SQLite Board read와 `mark-submitted` local record |
| `tests/integration/test_submission_flow.py` | 수동 제출·SQLite·CLI·credential·복합 alert·rollback 9 tests |

Operations Schema `0.1`, Analysis I/O `0.1`, SQLite schema v2와 dependency는
변경하지 않았다.

## 3. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-08 submission flow | 9 passed |
| Candidate Verifier integration | 23 passed |
| Evidence Worker integration | 20 passed |
| OperationsSnapshot integration | 12 passed |
| 변경 핵심 integration 묶음 | 64 passed |
| 전체 pytest | 271 passed |
| Ruff lint·format | pass |
| fixture Schema | PASS 3 |
| Analysis request/result | PASS 3 |
| generated Analysis Schema | PASS 3 · 35 probes |
| Operations contract | PASS · 17 probes |
| 저장소 추적성 | PASS · 806 links |
| 저장소 보안 검사 | PASS · 66 runtime/evidence files |

## 4. Agentic Parallel Solve QA

| QA | Offline 판정 | 근거 |
|:---|:---:|:---|
| `QA-OPS-PAR-001` | pass | 세 문제 bounded overlap·worker 실패 격리·problem/result/workspace 분리 |
| `QA-OPS-INTRA-001` | pass | 같은 문제의 두 leaf 동시 실행·Reporter dependency 후 reconciliation |
| `QA-OPS-VERIFY-001` | pass | fresh replay·필수 check·독립성 없는 승격 차단 |
| `QA-OPS-CONFLICT-001` | pass | conflict·heuristic·동일 dual-label replay를 review-required로 보존 |
| `QA-OPS-RULE-001` | pass / offline | fake/local Planner mode와 rules-gated·restricted pre-call 차단 |
| `QA-OPS-SUBMIT-001` | pass | 명시적 human confirm·전체 answer 보존·network call/credential 0 |

이 판정은 synthetic/offline Operations V1의 통과다. 공식 Rules에 따른 live
provider mode 승인이나 실제 대회 처리량 측정을 뜻하지 않는다.

## 5. 제출 안전 계약

- `mark-submitted`는 `--confirm` 없이는 exit `2`로 중단한다.
- candidate와 problem이 모두 `submission_ready`이고 독립 검증을 이미 통과한
  validated document만 제출 기록으로 전환한다.
- 명령은 CTFd 주소·method·credential을 받지 않으며 network adapter를 import하지
  않는다.
- 성공 출력은 submission ID·candidate ID·응답·`network_calls 0`만 표시하고
  candidate answer나 database 절대 경로를 반사하지 않는다.
- SQLite precondition update와 post-write OperationsDocument exact comparison이
  같은 transaction 안에서 실패하면 전체 기록을 rollback한다.

## 6. Known Issues

- `candidate_result_links`의 durable order는 SQLite v2 insertion `rowid`에
  의존한다. ordinal은 차기 명시적 migration에서만 추가한다.
- CLI는 사용자가 명시한 SQLite v2 path만 읽으며 `.scan/` 자동 탐색·migration을
  하지 않는다.
- 웹 Operations Board는 아직 Preview이며 이번 단위는 terminal/JSON local
  runtime만 검증한다.
- live AI/provider mode는 공식 Rules와 별도 승인 전까지 `rules_gated`다.

## 7. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Pass / Offline | Planner→Queue→Evidence→Verifier→Snapshot→수동 제출 기록 |
| Potential Impact | Partial | 병렬·격리 동작 확인, 실제 대회 처리시간 미측정 |
| Novelty | Pass | AI 방법 가설을 Python evidence와 독립 replay로 실증한 뒤 사람 제출 |
| UX | Pass / Local | 전체 answer·복합 alert·SQLite Board·명시적 human confirm |
| Open-source | Pass | Pydantic·Typer·stdlib SQLite/hashlib 재사용, 새 dependency 없음 |
| Business Plan | N/A | 대회 운영 runtime이며 수익 모델 검증 범위가 아님 |

## 8. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - live AI·API·자동화 mode Gate
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - Submission Queue·Mark submitted 계약
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - OPS-IMPL-08 범위
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-010 상태와 잔여 live 경계
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - 6개 수용 시나리오
- **QA_Validation**: [OPS-IMPL-07 OperationsSnapshot 보고서](./20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md) - 직전 read model 기준선
