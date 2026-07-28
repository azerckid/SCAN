# OPS-IMPL-07 OperationsSnapshot·Local View 검증 보고서
> Created: 2026-07-28 15:58
> Last Updated: 2026-07-28 16:26
> Status: Passed · Strict Read Model / SQLite Read-Back / Local CLI Passed

## 1. 목적과 범위

이 보고서는 persisted Operations contract가 엄격한 OperationsSnapshot으로
투영되고, 같은 snapshot을 local terminal과 JSON view가 소비하는지 기록한다.

포함 범위:

- SQLite schema v2 Operations bundle read-back과 runtime 재검증
- `OperationsSnapshot` strict Pydantic read model
- competition·AI mode·summary·problem·worker·verification·submission
  queue·source health·activity projection
- elapsed/remaining time, queue age와 freshness `stale_at`
- default·empty·partial·failed·stale·rules unavailable 상태
- accepted command의 ID·entity·new status·event·warning 응답 계약
- read-only `scan operations --bundle ...` terminal/JSON 출력
- 두 problem의 job·activity row 격리
- OPS-IMPL-06 P2의 chain 비교·dual-label conflict·verify/promote scope
  회귀와 adapter/response 실패 사유 분리

제외 범위:

- Operations Board 웹 runtime과 HTTP API
- priority·pause·resume·reassign mutation
- 사람 `Mark submitted`와 submission record
- live AI·RPC·CTFd 호출
- 실제 사용자 `.scan/` database 자동 migration

## 2. 구현

| 위치 | 책임 |
|:---|:---|
| `src/scan_tool/application/operations_snapshot.py` | strict snapshot·command result·상태·요약 projection |
| `src/scan_tool/application/operations_terminal.py` | 동일 snapshot의 terminal/JSON renderer |
| `src/scan_tool/adapters/sqlite_operations.py` | SQLite v2 Operations bundle read-back과 재검증 |
| `src/scan_tool/cli.py` | read-only local `operations` command |
| `tests/integration/test_operations_snapshot.py` | 12개 snapshot·SQLite·CLI·상태 mapping tests |
| `tests/integration/test_candidate_verifier.py` | OPS-IMPL-06 P2 회귀 3건 추가 |

Operations Schema `0.1`, Analysis I/O `0.1`, SQLite schema v2와 dependency는
변경하지 않았다. snapshot은 validated `OperationsDocument`만 입력으로 받고
온체인 사실이나 candidate 답을 새로 계산하지 않는다.

## 3. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-07 integration | 12 passed |
| OPS-IMPL-06 P2 추가 회귀 | 3 passed |
| 전체 pytest | 260 passed |
| Ruff lint·format | pass |
| fixture Schema | PASS 3 |
| Analysis request/result | PASS 3 |
| generated Analysis Schema | PASS 3 · 35 probes |
| Operations contract | PASS · 17 probes |
| 저장소 추적성 | PASS · 793 links |
| 저장소 보안 검사 | PASS · 65 runtime/evidence files |

주요 결과:

1. SQLite v2에서 읽은 bundle이 Operations contract validator를 다시 통과하고
   원본 rules-gated bundle과 일치했다.
2. terminal과 JSON renderer가 동일한 strict snapshot을 사용했다.
3. Rules unavailable·stale·empty·partial·failed 상태가 별도 label로
   판정됐으며 거짓 completion percentage를 생성하지 않았다.
4. 두 problem의 problem row·job row·activity row가 섞이지 않았다.
5. source in-flight가 concurrency limit을 초과하면 snapshot 입력을 거부했다.
6. accepted command result는 new status와 append-only event ID 없이는
   생성되지 않았다.
7. local CLI는 입력 파일의 절대 경로를 출력하지 않고 unknown output을
   exit `2`로 거부했으며 최대 길이 competition ID도 bounded hash snapshot
   ID로 안전하게 투영했다.
8. chain check는 original과 independent replay를 비교하며 Ethereum chain
   상수에만 의존하지 않는다.
9. 공식 fact와 heuristic label이 함께 들어오면 조용히 병합하지 않고
   independent replay conflict와 `review_required`를 유지했다.
10. build뿐 아니라 verify·promote도 교차 problem evidence를 차단하고,
    adapter failure와 invalid/reused response를 다른 안전 사유로 기록했다.

## 4. Preview 상태 대응

| Preview 상태·영역 | Runtime projection | 판정 |
|:---|:---|:---:|
| Rules unavailable | AI mode rule state·rules snapshot | pass |
| Empty | problem·worker·verification·submission empty 안내 | pass |
| Partial / Failed | scoped error·job·verification 상태 | pass |
| Stale | `generated_at`·`stale_at`·observed time | pass |
| Problem Board | score·priority·status·owner·progress·next action | pass |
| Worker Pool | role·job·stage·health·queue reason·attempt budget | pass |
| Verification | check count·conflict·missing evidence | pass |
| Submission Queue | 전체 answer·format·confidence·evidence·human state | pass |
| Source Health | provider·capability·health·concurrency·retry·cache | pass |
| Activity | 최신 append-only event | pass |

이 판정은 terminal/JSON local view의 데이터·label 정합을 뜻한다. 브라우저
runtime interaction과 submission mutation 통과를 뜻하지 않는다.

## 5. 안전·범위 경계

- `scan operations`는 local bundle을 읽기만 하며 network·DB mutation을
  수행하지 않는다.
- SQLite read-back은 explicit database path를 요구하며 사용자 DB를 자동
  migration하지 않는다.
- SQLite v2 `candidate_result_links`에는 순서 컬럼이 없어 현재 read-back은
  같은 트랜잭션의 insertion `rowid`를 사용한다. durable ordering을 별도
  계약으로 올릴 경우 차기 명시적 migration에서 ordinal을 추가한다.
- snapshot·terminal·JSON에 credential·Authorization·local absolute path를
  넣지 않는다.
- 전체 candidate answer는 사람의 복사를 위해 보존하지만 CTFd endpoint나
  submit method는 없다.
- 새 dependency·Schema·migration·웹 UI를 추가하지 않았다.

## 6. Known Issues와 다음 단계

- 현재 CLI는 validated bundle을 직접 읽는다. SQLite read-back은 application
  composition에서 사용할 준비가 됐지만 사용자 DB 자동 선택은 의도적으로 없다.
- source health는 live provider 상태가 아니라 호출자가 주입하는 strict
  snapshot input이다. 실제 provider wiring은 공식 Rules와 별도 승인이 필요하다.
- command result 계약은 확정됐지만 priority·pause·resume·reassign mutation은
  구현하지 않았다.
- 실제 한 문제의 복수 leaf end-to-end reconciliation과 submission record는
  OPS-IMPL-08 통합 Gate에 남아 있다.

다음 구현 단위는 별도 승인 후 `OPS-IMPL-08`
security·submission record·최종 integration report다.

## 7. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Pass | SQLite read-back·strict snapshot·terminal/JSON·12 integration tests |
| Potential Impact | Partial | 복수 문제 상태 판독과 queue age 제공, 실제 대회 처리시간 미측정 |
| Novelty | Pass | AI 결론이 아닌 persisted evidence·verification을 직접 읽는 운영 view |
| UX | Pass / Local | Preview 상태 label과 terminal/JSON projection 일치, 웹 runtime 미구현 |
| Open-source | Pass | Pydantic·stdlib·기존 SQLite repository 재사용, 새 dependency 없음 |
| Business Plan | N/A | 대회 운영 read model이며 수익 모델 검증 범위가 아님 |

## 8. Related Documents

- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 상태·정보 계층·Preview label
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - OperationsSnapshot·command result 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - OPS-IMPL 상태와 잔여 submission 범위
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - PAR·INTRA·VERIFY·CONFLICT 상태
- **QA_Validation**: [OPS-IMPL-06 Candidate·Verifier 보고서](./19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md) - candidate·fresh replay 기준선
