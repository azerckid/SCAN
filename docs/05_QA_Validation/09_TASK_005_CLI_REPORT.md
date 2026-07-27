# TASK-005 CLI 검증 보고서
> Created: 2026-07-27 23:32
> Last Updated: 2026-07-27 23:32
> Status: TASK-005 Scope Passed · Vertical Analyzers Deferred

## 1. 판정

TASK-005의 네 명령, `.scan/` composition root, terminal renderer,
stdout·stderr 경계와 종료 코드 구현은 통과했다. 공개 Analysis I/O Schema는
`0.1`을 유지하고 새 dependency를 추가하지 않았다.

DEX·AUTH·FREEZE 계산은 각각 TASK-006~008 범위다. 따라서 현재
`scan analyze`는 유효 요청을 검증·등록한 뒤 해당 analyzer가 없음을
`source_unavailable`, 종료 코드 `4`로 명시한다. 이 상태를 실제 분석 실패나
confirmed 결과로 위장하지 않는다.

## 2. 구현 범위

| 영역 | 구현 |
|:---|:---|
| Command | `analyze`, `validate`, `resume`, `show`, `--help`, `--version` |
| Composition | 상대 `.scan/`, SQLite schema v1, artifact store, result exporter |
| Validation | request·result·error Schema 식별, analysis ID 사전 검증 |
| Renderer | complete·partial·failed, result 요약, warning·error, run·export |
| Streams | 최종 요약은 stdout, 시작·진행·warning·error는 stderr |
| Exit code | complete `0`, input `2`, partial `3`, failed `4`, restricted `5`, interrupt `130` |
| Accessibility | 무색상 label, non-TTY 줄 단위 출력, 주소·TX만 축약, uint256 보존 |
| FB-001 | 상세 retry·fallback은 stderr, 최종 stdout은 count·첫 오류만 표시 |
| Persistence | request 등록, terminal status, result/export 조회와 `show` 재표시 |

## 3. 구현 경계

- CLI에 DEX·AUTH·FREEZE 계산 규칙을 넣지 않았다.
- live provider endpoint·API key·AI·agent·CTFd 제출 기능을 추가하지 않았다.
- fixture result를 production analyzer처럼 자동 반환하지 않는다.
- unknown `show`·`resume`은 `.scan/`이나 빈 DB를 만들지 않는다.
- detailed source attempt는 stderr와 SQLite `source_attempts`에 보존한다.
  Analysis I/O `0.1` JSON은 run 집계와 source provenance만 보존한다.

## 4. 자동 검증

실행 명령:

```bash
.venv/bin/python scripts/verify.py
```

결과:

```text
All checks passed!
75 files already formatted
77 passed
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
```

CLI 통합 테스트는 다음을 검증한다.

- 네 명령의 help와 request 검증
- complete·partial·failed·restricted·input·interrupt 종료 코드
- 첫 feedback `400ms` 미만
- retry 3건·fallback 1건의 stderr 상세와 stdout 압축
- confirmed result 저장 후 `show`의 ID·raw·artifact URI 일치
- unknown ID의 명시적 실패와 read-only 빈 상태
- canary secret·사용자 절대 경로의 stdout·stderr 0건
- 무색상·non-TTY에서 ANSI·carriage return 0건

## 5. QA 상태

| QA ID | 상태 | TASK-005 증거 |
|:---|:---:|:---|
| `QA-CLI-001` | pass | help·validate·unknown show·raw 보존 |
| `QA-CLI-002` | pass | stream 분리와 exit code 6종 |
| `QA-CLI-003` | pass | 400ms·FB-001·무색상·non-TTY |
| `QA-CLI-004` | partial | analyze 저장·show·interrupt 통과, 실제 DEX stage resume는 TASK-006 |
| `QA-RULE-001` | pass | dispatch 전 restricted·exit `5` |
| `QA-SOURCE-001` | partial | unavailable·exit `4`, 실제 analyzer Result 분기는 TASK-006~009 |
| `QA-SEC-001` | partial | CLI 출력 범위 통과, vertical 전체 통합 검색은 TASK-009 |

24개 전체 집계는 `12 pass / 3 partial / 9 not_executed`다.

## 6. Code Review

| 영역 | 판정 | 근거 |
|:---|:---:|:---|
| 로직 정확성 | Pass | status·error별 exit code와 저장·조회 round-trip |
| 타입·입력 안전성 | Pass | Pydantic 계약과 analysis ID TypeAdapter |
| YAGNI·KISS | Pass | 새 dependency·유형별 별칭·live 설정 없음 |
| 책임 분리 | Pass | command, runtime composition, renderer, storage read 분리 |
| Side effect | Pass | validate read-only, unknown show/resume 무변경 |
| 가독성 | Pass | 안정된 상태 label·상수 exit code·작은 helper |
| 불필요 코드 | Pass | debug 출력·dead code·미사용 import 없음 |
| UI-First | Pass | Preview·FB-001 대조, FB-002 의도된 help 표현 차이 기록 |

## 7. Security Review

| 점검 | 판정 | 근거 |
|:---|:---:|:---|
| Secret 노출 | Pass | canary 입력은 검증 오류 원문에 포함되지 않음 |
| 로컬 경로 | Pass | 입력은 basename, export는 `artifact://sha256/...` |
| 입력 검증 | Pass | JSON object·Schema·analysis ID를 외부 동작 전에 검증 |
| SQL injection | Pass | storage 조회·상태 변경은 parameter binding |
| 오류 노출 | Pass | stack trace·provider URL·header를 terminal에 출력하지 않음 |
| 외부 동작 | Pass | analyzer·live endpoint·서명·제출 호출 없음 |

## 8. 365 글로벌 평가 기준

| 기준 | 상태 | 증거 |
|:---|:---:|:---|
| Functionality | Pass | 네 명령·renderer·exit code·저장 조회, 77 tests |
| Potential Impact | Pass | 세 vertical slice가 공유할 안정된 CLI·Analysis I/O 경계 |
| Novelty | Pass | evidence-first·partial·not_assessed를 숨기지 않는 출력 |
| UX | Pass | 400ms 첫 feedback·FB-001·다음 행동·무색상 |
| Open-source | Pass | 공개 Schema·명령·exit code와 dependency 추가 없음 |
| Business Plan | N/A | 대회 준비용 CLI 기반 작업으로 별도 사업화 범위가 아님 |

## 9. Originality & Ethics Check

- 외부 상용 포렌식 CLI 출력 코드를 복제하지 않았다.
- fixture 정답을 production analyzer로 가장하지 않는다.
- 피싱·탈취·범죄·현재 제재를 CLI가 추가 판정하지 않는다.
- private key·credential·CTFd session을 입력·저장·출력하지 않는다.
- 공식 Rules 미확정 기능은 활성화하지 않는다.

## 10. Known Issues와 다음 작업

- 실제 DEX 분석과 checkpoint resume는 TASK-006에서 검증한다.
- AUTH·FREEZE vertical analyzer는 TASK-007·008 범위다.
- 성공·retry·fallback·partial 전체 데이터의 통합 secret 검색은 TASK-009다.
- 다음 구현은 별도 승인 후 TASK-006 DEX vertical slice다.

## 11. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - V1 CLI와 DEX 우선순위
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - command·stream·exit code 계약
- **UI_Screens**: [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - renderer·접근성·FB-001
- **UI_Screens**: [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - Preview 승인과 실제 구현 대조
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - composition root·출력·보안 기준
- **Technical_Specs**: [SQLite DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md) - `.scan/` run·artifact·export 저장
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - renderer 입력 계약
- **Logic_Progress**: [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-005 완료 조건과 TASK-006 경계
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - CLI·source·security 판정
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - 전체 24개 집계와 후속 Gate
- **QA_Validation**: [TASK-004 Storage 보고서](./08_TASK_004_STORAGE_REPORT.md) - CLI가 조립하는 SQLite·artifact·export 기준선
