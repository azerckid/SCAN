# OPS-IMPL-01 Operations Contract 검증 보고서
> Created: 2026-07-28 12:20
> Last Updated: 2026-07-28 12:20
> Status: Passed · Offline Only · Rules-Gated

## 1. 범위

이 보고서는 `TASK-010`의 첫 구현 단위인 `OPS-IMPL-01`을 검증한다.

포함:

- operations 공개 계약 `0.1` Pydantic model
- 생성 JSON Schema와 저장본 drift 검사
- cross-record·lifecycle·AI mode 불변조건
- Problem·Plan·Job·Verification·Candidate 상태 전이 validator
- rules-gated 초기 상태 예제와 positive/negative contract probe

제외:

- SQLite v2 migration·repository
- AI Planner adapter·scheduler·evidence worker·Verifier 실행
- Operations Board runtime
- live AI·RPC·CTFd 호출

## 2. 구현 산출물

| 산출물 | 역할 |
|:---|:---|
| `src/scan_tool/domain/operations.py` | 순수 operations model·참조·상태 규칙 |
| `operations-contract.schema.json` | 공개 구조 계약 `0.1` |
| `rules-gated-bundle.json` | 공식 Rules 미확정 초기 상태 예제 |
| `scripts/check_operations_schema.py` | 생성 Schema drift·12개 contract probe |
| `tests/unit/test_operations_contract.py` | 상태·보안·참조 불변조건 21개 test |

## 3. 확인된 불변조건

- 모든 operations 시각은 UTC `Z` 형식이다.
- 선언하지 않은 field와 credential 값은 계약에서 거부되고 오류에 원문 값이
  재출력되지 않는다.
- `fake_qa`는 synthetic test competition에서만 `allowed`일 수 있다.
- AI adapter와 data boundary 조합이 승인 표와 일치한다.
- `allowed` AI mode는 provider와 model을 고정한다.
- `rules_gated` plan은 실행 가능한 leaf job이나 AI raw output을 가질 수 없다.
- problem·plan·job·candidate·verification의 cross-problem 참조를 거부한다.
- 실행 중 evidence job은 승인된 plan을 요구한다.
- candidate creator와 verifier job은 독립적이어야 한다.
- `submission_ready`는 result·evidence·passing verification을 요구한다.
- terminal entity의 역방향 상태 전이를 거부한다.

## 4. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| operations unit tests | PASS 21 |
| runtime/generated Schema probes | PASS 12 |
| 전체 pytest | PASS 154 |
| fixture·Analysis I/O·generated Analysis Schema | PASS 3 / PASS 3 / PASS 3 |
| repository traceability | PASS 720 links |
| repository security scan | PASS 53 files |
| 신규 dependency | 없음 |
| live network·AI·CTFd | 0건 |

JSON Schema는 구조·형식 검증을 담당한다. cross-record reference, lifecycle
조건, 상태 전이는 Python validator가 추가로 강제하며 Schema `$comment`에 이
경계를 명시했다.

## 5. 잔여 Gate

- 공식 Rules의 AI provider·model·data·tool mode는 아직 미확정이다.
- `OPS-IMPL-02` SQLite v2 migration·repository는 별도 승인이 필요하다.
- 실제 AI Planner·scheduler·Verifier는 각각 후속 구현 단위다.

## 6. Related Documents

- [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md)
- [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md)
- [P0·V1 및 Operations Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md)
