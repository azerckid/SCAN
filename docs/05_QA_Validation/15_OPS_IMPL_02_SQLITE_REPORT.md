# OPS-IMPL-02 SQLite v2 검증 보고서
> Created: 2026-07-28 13:31
> Last Updated: 2026-07-28 13:31
> Status: Passed · Offline Only · Explicit Migration

## 1. 범위

이 보고서는 `TASK-010`의 두 번째 구현 단위인 `OPS-IMPL-02`를 검증한다.

포함:

- 기존 Analysis 저장소 v1을 보존하는 명시적 SQLite `user_version=2` migration
- migration 전 v1 backup·source/backup/migrated DB `integrity_check`
- 15개 operations table·5개 index·append-only event trigger
- 검증된 `OperationsDocument`의 원자적 write-side repository
- v1 Analysis run·result·evidence·artifact 참조 재사용

제외:

- 실제 사용자 `.scan/scan.sqlite3` migration
- 운영 entity update command·read model·Operations Board runtime
- AI Planner adapter·scheduler·evidence worker·Verifier 실행
- live AI·RPC·CTFd 호출

## 2. 안전한 migration 계약

`initialize_operations_database()`와 `migrate_operations_database()`만 v2를
생성한다. 기존 `SQLiteStorage`는 계속 v1만 지원하며 v2 DB를 열면 명시적
version mismatch로 실패한다.

migration 순서는 다음과 같다.

1. source가 v1인지 확인한다.
2. source `integrity_check=ok`를 확인한다.
3. 지정한 새 경로에 backup하고 backup의 version·integrity를 확인한다.
4. `BEGIN IMMEDIATE` transaction에서 신규 DDL만 실행한다.
5. `foreign_key_check` 후 `user_version=2`를 commit한다.
6. 실패하면 전체 DDL과 version 변경을 rollback한다.

backup 경로가 source와 같거나 이미 존재하면 migration 전에 거부한다. 자동
migration, v1 table rewrite/drop, 사용자 경로 탐색은 구현하지 않았다.

## 3. 저장 구조

| 구분 | 구현 |
|:---|:---|
| 운영 기준선 | `competitions`, `operation_ai_modes` |
| 문제·계획·작업 | `problems`, `problem_artifacts`, `plans`, `jobs`, `job_dependencies` |
| Analysis 연결 | `problem_analysis_links`, `candidate_result_links` |
| 후보·검증·제출 | `candidates`, `verifications`, `verification_checks`, `submissions` |
| 감사·오류 | `operation_events`, `operation_errors` |

원문·첨부·AI raw output·submission note는 기존 `artifacts.sha256`가 먼저
존재해야 저장된다. job의 `analysis_id`는 기존 `analysis_runs`, candidate의
result/evidence는 실제 v1 row의 `analysis_id`를 조회해 연결한다.

`save_document()`는 upsert 없이 하나의 transaction으로 저장한다. 중간 참조가
없거나 artifact가 없으면 전체가 rollback된다. `operation_events`는 repository
API가 append만 제공하며 DB trigger도 update/delete를 거부한다.

## 4. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-02 integration tests | PASS 8 |
| 전체 pytest | PASS 170 |
| fixture·Analysis I/O·generated Analysis Schema | PASS 3 / PASS 3 / PASS 3 |
| operations contract runtime/Schema probes | PASS 17 |
| 신규 runtime dependency | 없음 |
| 실제 사용자 DB migration | 0건 |
| live network·AI·CTFd | 0건 |

통합 테스트는 다음을 직접 확인한다.

- 빈 임시 DB를 v1 기준선으로 만든 뒤 v2로 승격
- 데이터가 있는 임시 v1 DB의 row 보존과 v1 backup 복구 가능성
- DDL 중간 강제 오류 후 `user_version=1`, 신규 table 0, v1 재개방
- v1 코드가 v2 DB를 version mismatch로 거부
- operations bundle 원자 저장과 artifact 선행조건 실패 rollback
- event ID 중복·update·delete 차단
- backup overwrite·미지원 schema version 거부
- canary secret의 event 저장 전 차단

## 5. 잔여 Gate

- entity별 mutation과 AI mode policy는 `OPS-IMPL-03` application Gate에서
  시작한다.
- dependency Queue와 다중 문제 격리는 `OPS-IMPL-04` 범위다.
- operations read model과 화면 snapshot은 `OPS-IMPL-07` 범위다.
- 공식 Rules의 AI provider·model·data·tool mode는 여전히 `rules_gated`다.
- 실제 사용자 DB migration은 별도 승인·backup 경로 확인 없이는 실행하지
  않는다.

## 6. Related Documents

- [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md)
- [SQLite 논리 DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md)
- [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md)
- [P0·V1 및 Operations Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [OPS-IMPL-01 계약 보고서](./14_OPS_IMPL_01_CONTRACT_REPORT.md)
