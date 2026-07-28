# OPS-IMPL-04 Bounded Queue 검증 보고서
> Created: 2026-07-28 14:23
> Last Updated: 2026-07-28 14:23
> Status: Passed · QA-OPS-PAR-001 / QA-OPS-INTRA-001 Partial

## 1. 목적과 범위

이 보고서는 `OPS-IMPL-04`의 in-process bounded Queue가 승인된
`REQ-OPS-QUEUE-001`~`006` 중 scheduler 책임을 충족하는지 기록한다.

포함 범위:

- 사람 우선순위·queued 시각·job ID의 결정적 배정 순서
- 전체·active problem·problem별·Planner·Verifier 동시성 제한
- 같은 문제 안의 dependency DAG와 cycle·교차 문제 dependency 차단
- worker 예외의 문제별 격리와 dependency 대기
- `max_attempts` 기반 제한 재시도와 checkpoint 참조 보존
- 같은 작업 범위의 idempotency 중복 억제
- source capability별 semaphore와 같은 in-flight request 공유
- queued job의 pause·cancel snapshot

제외 범위:

- DEX·AUTH·FREEZE Analysis I/O 실행과 artifact 연결 (`OPS-IMPL-05`)
- candidate·독립 Verifier (`OPS-IMPL-06`)
- 실시간 priority/pause mutation·Queue age·Operations Board (`OPS-IMPL-07`)
- live AI·RPC·CTFd 호출

## 2. 구현

| 위치 | 책임 |
|:---|:---|
| `src/scan_tool/application/scheduler.py` | `BoundedJobScheduler`, 제한·dependency·retry·격리·job dedup |
| 같은 파일 `InFlightRequestPool` | source capability 제한과 동일 요청 in-flight dedup |
| `tests/unit/test_bounded_queue.py` | fault-injection·경계·결정성 19 tests |

공개 Operations Schema `0.1`, Analysis I/O `0.1`, SQLite schema v2와 dependency는
변경하지 않았다. worker는 `Callable[[JobRecord, attempt], WorkerOutcome]`로
주입해 OPS-IMPL-05 구현 전에는 테스트 대역만 실행한다.

## 3. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-04 unit | 19 passed |
| 전체 pytest | 206 passed |
| Ruff lint·format | pass |
| fixture Schema | PASS 3 |
| Analysis request/result | PASS 3 |
| generated Analysis Schema | PASS 3 · 35 probes |
| Operations contract | PASS · 17 probes |
| 저장소 추적성 | PASS · 742 links |
| 저장소 보안 검사 | PASS · 59 runtime/evidence files |

주요 fault-injection 결과:

1. 서로 다른 두 문제의 worker가 겹쳐 실행되고 한 worker의 예외가 다른 결과를
   실패·cancel로 바꾸지 않았다.
2. 세 독립 leaf가 먼저 시작되고 reconciliation은 세 dependency가
   `complete`가 된 뒤에만 배정됐다.
3. 전체·problem·role 제한이 설정값을 넘지 않았다.
4. dependency 실패 시 downstream job은 실행되지 않고 `waiting /
   dependency_incomplete`로 남았다.
5. retryable 실패는 `max_attempts`까지만 재배정됐다.
   소진 후에는 마지막 error·checkpoint와 함께 `failed`로 끝났다.
6. 같은 scope의 idempotency key는 한 번만 실행됐고 duplicate 결과에
   canonical job ID와 checkpoint가 보존됐다.
7. 같은 source request key의 동시 구독은 operation 1회만 실행됐고
   capability semaphore 상한을 넘지 않았다.

## 4. QA 판정

| QA | 판정 | 남은 조건 |
|:---|:---:|:---|
| `QA-OPS-PAR-001` | partial | result·artifact·checkpoint·candidate의 실제 problem link는 OPS-IMPL-05~07 |
| `QA-OPS-INTRA-001` | partial | Analysis I/O·source provenance를 실제 evidence worker와 연결 |
| `QA-OPS-RULE-001` | partial 유지 | scheduler 통과, 실제 evidence worker·live 허용 adapter 미실행 |

`OPS-IMPL-04` 단위 자체는 Passed다. 전체 운영 QA를 Passed로 올리지 않는다.

## 5. 안전·범위 경계

- 외부 네트워크, AI provider, RPC, CTFd 호출은 추가하지 않았다.
- credential·session·Authorization을 받거나 저장하는 필드가 없다.
- worker 예외 원문은 결과에 반사하지 않고 `worker_failed`로 축약한다.
- cross-problem dependency와 다른 scope의 idempotency 충돌을 실행 전에 거부한다.
- in-process scheduler만 구현했으며 distributed queue·새 dependency·미래용
  provider registry를 추가하지 않았다.

## 6. Known Issues와 다음 단계

- pause·cancel은 실행 시작 전 snapshot만 적용한다. running job의 cooperative
  cancel과 UI mutation은 OPS-IMPL-07에서 다룬다.
- source pool은 OPS-IMPL-05 worker가 기존 `build_cache_key`를 전달할 때 실제
  source provenance 경로와 연결된다.
- Queue age와 runtime snapshot은 아직 생성하지 않는다.
- job dedup은 같은 problem·role·job type에만 허용한다. 서로 다른 문제의
  evidence link 공유는 source artifact 계층에서만 수행한다.

다음 구현 단위는 별도 승인 후 `OPS-IMPL-05` DEX·AUTH·FREEZE evidence worker
adapter다.

## 7. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Pass | bounded Queue·dependency·격리·retry·dedup 19 tests |
| Potential Impact | Partial | 복수 문제 동시 실행 확인, 실제 대회 처리량·Queue age 미측정 |
| Novelty | Partial | AI plan과 결정적 worker 사이의 격리된 실행 계약, 전체 Verifier 흐름 미완성 |
| UX | N/A | runtime read model·Operations Board는 OPS-IMPL-07 범위 |
| Open-source | Pass | 표준 `asyncio` 기반·새 dependency 없음·worker callable 교체 가능 |
| Business Plan | N/A | 대회 운영 기반 계층이며 수익 모델 검증 범위가 아님 |

## 8. Related Documents

- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - Queue 요구사항
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - §9 동시성·dependency·dedup
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - OPS-IMPL 상태
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - PAR·INTRA·RULE 시나리오
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - TASK-010 Gate
