# OPS-IMPL-05 Evidence Worker 검증 보고서
> Created: 2026-07-28 14:51
> Last Updated: 2026-07-28 15:08
> Status: Passed · QA-OPS-PAR-001 / QA-OPS-INTRA-001 / QA-OPS-RULE-001 Partial

## 1. 목적과 범위

이 보고서는 승인된 AI plan의 evidence leaf를 기존 DEX·AUTH·FREEZE
Analysis I/O `0.1` vertical slice로 실행하는 `OPS-IMPL-05` 결과를 기록한다.
AI가 제안한 방법은 정답으로 취급하지 않고, Python worker가 raw replay를
조회·디코딩·정합해 만든 result와 evidence만 후속 검증 입력으로 사용한다.

포함 범위:

- `EvidenceWorkerPort`와 in-process offline adapter
- 승인 plan·leaf·Analysis request의 problem·job·input projection 검증
- 승인 replay 본문·SHA-256과 checkpoint 재개 해시 고정
- 문제별 SQLite·artifact·checkpoint workspace 격리
- 같은 문제의 다중 evidence job에 대한 in-process workspace lock
- DEX·AUTH·FREEZE confirmed fixture의 실제 Analysis 실행
- Analysis complete·partial·failed를 Queue worker outcome으로 변환
- request·replay·JSON·Markdown artifact URI를 안전한 operation event에 연결
- bounded Queue와 세 vertical worker의 문제 간 병렬 실행
- adapter 실패의 구조화 오류 변환과 원문·경로 비노출

제외 범위:

- candidate builder와 독립 Verifier (`OPS-IMPL-06`)
- OperationsSnapshot·local CLI view (`OPS-IMPL-07`)
- 제출 기록·전체 운영 보안 Gate (`OPS-IMPL-08`)
- live AI·RPC·CTFd 호출과 실제 대회 문제 데이터

## 2. 구현

| 위치 | 책임 |
|:---|:---|
| `src/scan_tool/ports/evidence.py` | Evidence Worker port·artifact/result 응답 계약 |
| `src/scan_tool/adapters/evidence.py` | ProblemId 정합 workspace·문제별 lock에서 기존 `CliRuntime`을 실행하는 in-process adapter |
| `src/scan_tool/application/evidence_worker.py` | pre-call Gate·Analysis pair 검증·Queue outcome·event/error 변환 |
| `src/scan_tool/application/cli_runtime.py` | 승인 replay bytes·SHA-256과 저장 checkpoint 해시 검증 |
| `tests/integration/test_evidence_worker.py` | 세 fixture·병렬 Queue·동일 문제 lock·격리·재사용·partial·failure·보안 19 tests |

기존 DEX·AUTH·FREEZE analyzer를 복제하지 않았다. worker는 승인된
`inputs_projection`이 실제 Analysis request inputs와 정확히 일치할 때만
실행하며, restricted mode·미승인 plan·paused competition은 adapter 호출 전에
차단한다.

## 3. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-05 integration | 19 passed |
| 전체 pytest | 225 passed |
| Ruff lint·format | pass |
| fixture Schema | PASS 3 |
| Analysis request/result | PASS 3 |
| generated Analysis Schema | PASS 3 · 35 probes |
| Operations contract | PASS · 17 probes |
| 저장소 추적성 | PASS · 753 links |
| 저장소 보안 검사 | PASS · 62 runtime/evidence files |

주요 검증 결과:

1. DEX·AUTH·FREEZE confirmed raw replay를 expected result 복사 없이 기존
   Python vertical slice로 재생성했다.
2. 세 문제를 bounded Queue에서 겹쳐 실행했고 각 문제는 서로 다른 DB·artifact
   workspace를 사용했다.
3. 완료 result 재실행은 같은 analysis를 재사용하고 중복 result row를 만들지
   않았다.
4. 승인 replay SHA-256 불일치와 저장 checkpoint 이후 replay 교체를 거부했다.
5. restricted mode·미승인 plan·input projection 불일치·paused competition은
   adapter 호출 0건으로 차단됐다.
6. partial Analysis result는 job `partial`과 구조화 error로 보존됐다.
7. adapter 예외의 원문 secret과 로컬 절대 경로는 event·error에 반사되지 않았다.
8. 같은 문제의 DEX·AUTH job을 동시에 요청해도 workspace 임계 구간의 최대
   동시 실행은 1이었고 두 Analysis 모두 완료됐다.
9. `ProblemId` 최대 길이 workspace를 허용하고 `offline_mode=false`는 adapter
   호출 0건으로 차단했다.
10. adapter 실행 실패와 adapter 응답 검증 실패를 서로 다른 안전한 reason으로
    기록했다.

## 4. QA 판정

| QA | 판정 | 이번 단위의 증거와 남은 조건 |
|:---|:---:|:---|
| `QA-OPS-PAR-001` | partial | 세 Analysis worker의 겹친 실행·workspace/result/checkpoint/artifact 격리 통과; candidate 격리는 OPS-IMPL-06~07 |
| `QA-OPS-INTRA-001` | partial | Queue→Evidence Worker→Analysis I/O 연결 통과; 실제 한 문제의 복수 evidence leaf 정합은 OPS-IMPL-06 |
| `QA-OPS-RULE-001` | partial | 승인 offline Python evidence worker 통과; 공식 허용 live local/external adapter 미실행 |

`OPS-IMPL-05` 단위 자체는 Passed다. 독립 Verifier와 candidate 승격 전에는
전체 운영 QA를 Passed로 올리지 않는다.

## 5. 안전·범위 경계

- 외부 네트워크, live AI provider, live RPC, CTFd 호출을 추가하지 않았다.
- Analysis I/O `0.1`, Operations Schema `0.1`, SQLite schema v2를 변경하지 않았다.
- 새 runtime dependency를 추가하지 않았다.
- raw replay는 승인된 SHA-256과 함께 전달하며 다른 replay로 resume할 수 없다.
- credential·Authorization·session과 로컬 절대 경로를 operation record에
  저장하지 않는다.
- AI plan은 method hypothesis와 input projection만 제공하며 Analysis result나
  candidate를 직접 생성하지 않는다.

## 6. Known Issues와 다음 단계

- in-process adapter의 동기 vertical 실행은 `asyncio.to_thread`로 격리하고
  같은 problem workspace는 lock으로 직렬화한다. distributed worker와
  process 간 lock은 현재 범위가 아니다.
- event에는 request·replay·export artifact URI가 포함되지만 중앙 SQLite v2의
  cross-record 저장은 OPS-IMPL-07 composition root에서 연결한다.
- 실제 한 문제의 복수 evidence leaf reconciliation과 candidate 생성은 아직
  구현하지 않았다.
- independent Verifier가 raw evidence를 별도 실행으로 재검증하기 전에는
  `submission_ready`가 될 수 없다.

다음 구현 단위는 별도 승인 후 `OPS-IMPL-06` candidate builder·독립 Verifier
Gate다.

## 7. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Pass | 세 vertical·Queue·동일 문제 lock·격리·partial·resume 19 integration tests |
| Potential Impact | Partial | 복수 문제 동시 evidence 실행 확인, 실제 대회 처리량 미측정 |
| Novelty | Partial | AI 방법 가설을 결정적 Python evidence로 실증, 독립 Verifier 미구현 |
| UX | N/A | OperationsSnapshot·Board runtime은 OPS-IMPL-07 범위 |
| Open-source | Pass | port/adapter 교체 가능·기존 Analysis I/O 재사용·새 dependency 없음 |
| Business Plan | N/A | 대회 운영 기반 계층이며 수익 모델 검증 범위가 아님 |

## 8. Related Documents

- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - leaf request/result 계약
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - evidence worker·artifact 연결
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - OPS-IMPL 상태
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed DEX·AUTH·FREEZE 기준
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - PAR·INTRA·RULE 시나리오
- **QA_Validation**: [OPS-IMPL-04 bounded Queue 보고서](./17_OPS_IMPL_04_BOUNDED_QUEUE_REPORT.md) - scheduler 기준선
