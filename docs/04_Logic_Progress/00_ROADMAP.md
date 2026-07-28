# SCAN 2026 문서 완료 Roadmap
> Created: 2026-07-26 18:28
> Last Updated: 2026-07-29 04:48
> Status: Approved 2.7 Baseline · Phase 2 Coverage Expansion Proposed

## 1. 문서 목적

이 문서는 SCAN 2026 준비 과정에서 필요한 문서를 빠짐없이 작성·검토·확정하기
위한 문서 전용 Roadmap이다. 구현 일정이 아니라 다음 네 가지를 관리한다.

- 현재 문서의 작성·검증·승인 상태
- 아직 없거나 미결정인 문서와 정보
- 공식 규정 공개 후 갱신해야 할 범위
- Python 구현을 시작할 수 있는 Document Completion Gate

[구현 Backlog](./00_BACKLOG.md)의 `TASK-001`은 이 Roadmap의 Gate가 통과된
뒤에만 시작한다. 문서 정리가 목표인 동안에는 Backlog의 모든 구현 작업을
`ToDo`로 유지한다.

## 2. 기준선과 진행률

### 2.1 2026-07-27 문서 완료 기준 산출물

| 구분 | 현재 수량 | 상태 |
|:---|---:|:---|
| 상위 Markdown 문서 | 26 | 승인·확정 기준선과 목적이 명시된 Draft를 포함 |
| confirmed fixture 패키지 | 3 | DEX·AUTH·FREEZE `confirmed / 0.2` |
| 후보 fixture | 5 | DOC-M3에서 Deferred, 단계별 승격 조건 기록 |
| JSON Schema | 6 | fixture 3종·analysis 3종 |
| 독립 검증기 | 2 | fixture `PASS 3`, analysis `PASS 3` |
| HTML Preview | 3 | CLI·Operations Board 2개 확인 완료, Workbench 1개 비차단 Draft |

이 Roadmap, Rules Register와 QA Checklist를 포함한 수량이다.

### 2.2 진행률 해석

| 관점 | 가안 | 근거 |
|:---|---:|:---|
| 문서 구조·연결 | 100% | 5개 Layer, 메타데이터, Related Documents, 상대 링크 검증 |
| P0·V1 핵심 설계 내용 | 100% | 문제·우선순위·요구사항·Schema·UI·기술·DB·Backlog·QA 작성 |
| 문서 승인·확정 | 100% | Draft 유지 사유와 구현 중 결정 항목을 포함해 사용자 승인 |
| 공식 정보 충족 | 진행 중 | 미공개 규정은 `unclear`·Active Watch로 유지 |

백분율은 작업량 예측을 위한 가안이며 문서 상태를 대신하지 않는다. 완료 판정은
섹션 7의 체크박스로만 한다.

## 3. 문서 상태 등록부

### 3.1 Concept Design

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) | Draft · Approved Baseline | 공식 규정 변경 시에만 영향 항목 갱신 |
| [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) | Draft 2 · Benchmark 0.1 Applied | 30문항 중 자동화 3·보조 6·미지원 21; 공백 우선순위 유지 |
| [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) | Baseline Confirmed 1.0 · Active Watch | Notification·이메일·공식 Rules 공개 시 Intake 실행 |
| [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) | Draft 1 · Approved Baseline | 공식 규정 변경 시 위험 점수 갱신 |

### 3.2 UI Screens

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) | UI-First Gate Passed · TASK-008 Applied | DEX·AUTH·FREEZE complete·partial·resume 연결 |
| [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) | UI-First Gate Passed · TASK-008 Applied | FREEZE confirmed와 external context scope 분리 |
| [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) | TASK-009 Regression Compared | 세 vertical·오류·resume와 실제 terminal 재대조 |
| [Web Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) | Draft 1 · Non-Blocking UX Track | 정적 Preview 사용자 검토, 구현 승격은 Python 엔진 안정화 후 별도 승인 |
| [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) | Approved 1.2 · OPS-IMPL-08 Local Submission Applied · Rules-Gated | live/web runtime은 별도 승인 |
| [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) | 사용자 확인 완료 | 구현 전 기준 화면으로 동결 |
| [HTML Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) | Draft · Review Pending | read-only 시연 UX 검토용, Document Completion Gate 비차단 |
| [HTML Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) | User Review Passed · PR #27 | 문제·worker·검증·수동 제출 UX 승인 기준선, `TASK-010` 전용 |

### 3.3 Technical Specs

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) | Approved 2.8 · TASK-011 Applied | confirmed fixture만 자동 채점하고 미지원 범위를 성공으로 계산하지 않음 |
| [SQLite 논리 DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md) | Approved 1.3 · Schema v2 Applied | 실제 사용자 DB migration은 별도 승인 |
| [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) | Draft · Approved Baseline | 규정·provider plan·rate limit은 live 사용 전 갱신 |
| [Reference Fixture Schema](../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) | Confirmed 0.1 | fixture schema 변경 요구가 생길 때만 개정 |
| [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) | Draft 1 · Approved Baseline | 공식 규정 변경은 source policy로 역반영 |
| [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) | Approved 1.9 · TASK-001~009 Applied | 통합 Gate는 stdlib script로 dependency 추가 없음 |
| [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) | Contract Approved 0.1 · TASK-002·005·006·007·008·009 Applied | 11-code·참조·Schema probe PASS 유지 |
| [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) | Approved 1.0 · P0/V1 Closed | 이후 단계 그룹은 Deferred |
| [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) | AI-Native Contract Approved 1.0 · UI-First Gate Passed · Rules-Gated | 구현은 `TASK-010` 별도 승인 |
| [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) | Approved 1.8 · OPS-IMPL-01~08 Offline Implemented | live mode는 Rules-Gated |
| [Coverage 확장 Technical Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) | Proposed 0.1 | TASK-012~019 개별 fixture·Context·구현 승인 필요 |
| [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) | Pre-event Smoke Partial Pass · Fixture Common 9/9 Match · Primary Trace Pass | TASK-012 전 credential 회전·독립 trace·반례 |
| [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) | Proposed 0.2 Draft · 8 Cases · 5 Probes | Analysis I/O 0.1·runtime 비변경, 정식 계약·UI·구현 승인 대기 |

### 3.4 Logic Progress

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [P0·V1 구현 Backlog](./00_BACKLOG.md) | TASK-001~009·011 Done · TASK-012~019 Proposed | Phase 2 code는 개별 승인 대기 |
| 이 문서 | Approved 2.7 Baseline · Phase 2 Proposed | Phase 2 계획과 구현 승인 경계 유지 |
| [Coverage 확장 Execution Plan](./01_EXECUTION_PLAN.md) | Proposed 0.1 | fixture·dependency 기반 Wave, 날짜 약속 아님 |
| `02_ROADMAP_BACKLOG_SYNC.md` | 조건부 미작성 | 구현 시작 전 Roadmap↔Backlog 상태 동기화 규칙 작성 |

### 3.5 QA Validation

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) | Approved 1.1 · Phase 2 Verifying Pack | confirmed 3·TASK-012 verifying 4·Deferred 5의 승격 조건 유지 |
| [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) | Approved 1.9 · Integration Passed | 24 pass·0 partial·0 not_executed |
| [QA Checklist](../05_QA_Validation/02_QA_CHECKLIST.md) | Approved 2.9 · OPS-IMPL-01~08 Offline Passed | live Rules·실대회 성능 미실행 |
| [Agentic Parallel Solve QA](../05_QA_Validation/03_AGENTIC_PARALLEL_SOLVE_QA.md) | Contract Approved · Offline 6 QA Passed | live Rules·실대회 성능 별도 |
| [OPS-IMPL-08 Final Integration Report](../05_QA_Validation/21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) | Passed · Offline Operations V1 | 수동 제출·보안·leaf 병렬·6 QA |
| [예상문제 Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) | Passed · 3 Automated / 6 Assisted / 21 Unsupported | 자동화 3개 exact·evidence·결정성 통과, 30문항 전체 정확도로 해석 금지 |
| [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) | Proposed 0.1 · Not Executed | TASK-012~019 승격·반례·통합 Gate |
| [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) | EVM Common Smoke Passed · Overall Partial | credential 회전·독립 trace·반례·AI Planner Gate |
| [TASK-012 Negative Oracle](../05_QA_Validation/27_TASK_012_NEGATIVE_ORACLE_REPORT.md) | Offline 24 Passed Twice | live rate/timeout·독립 trace는 별도 |
| [TASK-012 Analysis Contract Examples](../05_QA_Validation/examples/task-012/README.md) | Proposal 8 Cases · 5 Probes Passed | 제품 analyzer·fixture confirmed 성과로 계산 금지 |
| [Live Provider Smoke 준비 보고서](../05_QA_Validation/26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) | Pre-event Smoke Executed · Overall Partial | fixture별 재현·독립 trace·rate behavior |
| [Document Completion Report](../05_QA_Validation/04_DOCUMENT_COMPLETION_REPORT.md) | Pass | 문서 검증 증거·Known Issue·승인 경계 |
| DEX·AUTH·FREEZE fixture | Confirmed | V1 기준값으로 동결, 정답 임의 변경 금지 |

## 4. 표준 문서명과 기존 문서의 대응

solmate Gate가 요구하는 표준 문서와 이 저장소의 도메인 문서를 다음처럼
대응한다. 같은 내용을 복제하지 않고, 승인되지 않은 대응만 새 문서 후보로 둔다.

| 표준 문서 | 현재 대응 문서 | 판단 |
|:---|:---|:---|
| `01_VISION_CORE.md` | 참가·분석 도구 준비 전략 | 도메인 문서 대체 승인 |
| `02_LEAN_CANVAS.md` | 없음 | N/A 승인 — 현재 목표는 대회 분석 도구 준비; 공식 제출 요건 또는 사업화 트랙에서 작성 |
| `03_PRODUCT_SPECS.md` | 예상문제 은행 + P0·V1 요구사항 | 도메인 문서 조합 대체 승인 |
| `00_ROADMAP.md` | 이 문서 | 충족 |
| `02_QA_CHECKLIST.md` | P0·V1 QA Checklist | 충족, 범위 승인 완료 |
| `01_DB_SCHEMA.md` | SQLite 논리 DB Schema | 충족 — 정확한 DDL·migration은 `TASK-004`에서 확정 |
| `02_API_SPECS.md` | 데이터 소스 등록부·Analysis I/O Schema | 외부 제공 API가 생길 때 별도 작성 |

`VISION_CORE`·`PRODUCT_SPECS`는 이름만 맞추기 위해 중복 생성하지 않는다.
사용자는 기존 도메인 문서의 대체를 문서 완료 기준선으로 승인했다. 공식
제출에서 정확한 파일명이 필요해질 때만 표준 파일로 분리한다.

## 5. 문서 완료 Milestone

### [x] DOC-M1 — Roadmap 기준선 승인

- [x] PR #9 승인 당시 기존 상위 Markdown 문서 15개와 이 Roadmap의 상태를 확인한다.
- [x] 작성률·확정률·전체 준비율의 해석을 승인한다.
- [x] 표준 문서 대체와 조건부 문서 방침을 승인한다.
- [x] 구현보다 문서 완료를 우선한다는 순서를 고정한다.

완료 조건: 이 Roadmap의 상태가 `Confirmed 1.0` 또는 `Approved`로 변경된다.

완료 기록: 사용자 승인과 PR #9 병합(`c115f7d`, 2026-07-26)을 기준으로
`Approved 1.0` 상태를 확정했다.

### [x] DOC-M2 — 공식 규정·참가 운영 기준선 확정

- [x] `03_SCAN_2026_RULES_REGISTER.md`를 작성한다.
- [x] 공식 원문 URL·게시 시각·조회 시각·변경 이력을 기록한다.
- [x] API·자동화·AI·사전 제작 도구·상용 서비스 규정을
      `allowed / restricted / unclear`로 분리한다.
- [x] 등록·팀·본인 확인·예선·본선 항목을 확인값 또는 `unclear`로 기록한다.
- [x] 지원 체인·제공 데이터·정답·증거 제출 형식을 확인값 또는 `unclear`로 기록한다.
- [x] 불명확한 항목은 추정하지 않고 문의 대상·회신 상태를 기록한다.
- [x] 미공개 규정은 기존 문서의 `unclear`·비활성 Gate와 일치함을 확인한다.
- [x] Notification Intake와 공식 정보 Active Watch 절차를 기록한다.

완료 조건: 규정상 사용할 수 있는 데이터·도구·팀·제출 범위를 문서만으로
설명할 수 있고, 미확정 항목에는 담당 확인 경로가 있다.

완료 기록: 2026-07-27 등록·팀 생성 작동과 Challenge 잠금, Notification·
세부 Rules 부재를 기록했다. 규정 내용을 임의 확정하지 않고 `unclear`와
기능 비활성화를 유지한다. 이후 공지는 DOC-M2를 다시 여는 것이 아니라 Active
Watch 변경으로 처리한다.

### [x] DOC-M3 — QA·fixture 범위 마감

- [x] `02_QA_CHECKLIST.md`를 작성한다.
- [x] QA 시나리오 24개의 승인 상태와 구현 전/후 실행 시점을 구분한다.
- [x] confirmed fixture 3개가 V1 필수 범위를 충족함을 재확인한다.
- [x] 후보 fixture 5개 각각을 `Confirm Now / Deferred / Drop`으로 결정한다.
- [x] Deferred fixture에 승격 조건·필요 소스·재검토 시점을 기록한다.
- [x] fixture·analysis 검증기의 `PASS 3`을 재확인한다.

완료 조건: 후보 fixture의 TBD가 “미처리”가 아니라 명시적인 확정 또는 보류
결정으로 바뀌고, 실행용 QA checklist가 존재한다.

완료 기록: confirmed fixture 3개는 V1 기준선으로 유지하고 후보 5개는 모두
`Deferred`로 결정했다. 24개 QA 시나리오는 `Scope Approved / Not Executed`로
기록하고 작업별 실행 시점을 분리했다.

### [x] DOC-M4 — Draft 승인·문서 패키지 마감

- [x] Concept 문서의 Draft 상태와 미결정 사항을 승인 기준선으로 검토한다.
- [x] Technical 문서의 규범 부분과 구현 중 결정 부분을 분리한다.
- [x] Backlog와 QA 시나리오의 문서 범위를 승인한다.
- [x] P0·V1 오픈소스 사전조사의 `OSS-*` 결정과 구현 전 Gate를 확정한다.
- [x] `01_DB_SCHEMA.md`에 SQLite 논리 엔티티·관계·보존·mutation 경계를 기록한다.
- [x] 프로젝트 루트 `README.md`에 목적·문서 지도·검증 명령을 작성한다.
- [x] Project LICENSE를 MIT로 결정하고 제3자 자료 경계를 기록한다.
- [x] 모든 Markdown 메타데이터·Related Documents·상대 링크를 검증한다.
- [x] 중복되거나 이미 완료된 “다음 단계” 문구를 현재 상태로 갱신한다.
- [x] 문서 변경 이력과 잔여 Known Issue를 기록한다.

완료 조건: 핵심 문서가 승인 상태이거나, Draft 유지 사유와 결정 시점이
Roadmap에 명시되어 있다.

완료 기록: Draft는 구현 결과를 거짓으로 확정하지 않기 위해 유지하되 문서
입력 기준선으로 승인했다. 정확한 dependency version·DDL·실측값은 담당
Backlog로 분리했다.

### [x] DOC-M5 — Document Completion Gate

- [x] `DOC-M1`~`DOC-M4`가 완료되었다.
- [x] HTML UI Preview Gate와 UI-First Gate가 계속 통과 상태다.
- [x] Pre-Code Technical Brief의 데이터·API·상태·acceptance 기준이 유효하다.
- [x] 공식 규정 미확정 상태가 Backlog·QA·source policy에 반영되었다.
- [x] P0·V1 오픈소스 `OSS-*` 결정과 fixture 검증 계획이 구현 전에 확정되었다.
- [x] 문서·Schema·fixture 검증이 모두 통과한다.
- [x] Backlog의 `TASK-001`~`TASK-010` 10개가 모두 `ToDo` 상태로 유지된다.

위 항목은 Document Completion Gate가 닫힌 시점의 기준선이다. Gate 이후 별도
구현 승인으로 `TASK-001`~`TASK-009`와 `TASK-010`의
`OPS-IMPL-01`~`OPS-IMPL-08`이 완료됐으며 현재 상태는
[Backlog](./00_BACKLOG.md)가 관리한다.

완료 조건: 사용자가 문서 완료를 승인하면 이 Gate는 닫힌다. `TASK-001`
시작은 이 Gate와 별개의 후속 승인으로만 진행하며, 구현 보류는 문서 완료를
막지 않는다.

완료 기록: 사용자는 2026-07-27에 권장 순서 1~8의 별도 승인 없는 진행을
승인했다. 이 승인은 문서 완료만 닫으며 `TASK-001` 구현 시작이나 live
API·AI·agent 활성화를 승인하지 않는다.

## 6. 일정 전략

| 순서 | 시점 | 작업 | 차단 관계 |
|:---:|:---|:---|:---|
| 1 | 완료 (2026-07-26) | `DOC-M1` Roadmap 승인 | 이후 문서 순서의 기준 |
| 2 | 완료 (2026-07-27) | `DOC-M2` 공식 규정 기준선·Active Watch | 미공개 항목은 `unclear` 유지 |
| 3 | 상시 | Notification Intake·영향 문서 동기화 | 새 공식 정보가 있을 때만 실행 |
| 4 | 완료 (2026-07-26) | `DOC-M3` QA checklist·fixture 방침 | DOC-M2와 독립 완료 |
| 5 | 완료 (2026-07-27) | `DOC-M4` DB·OSS·README·LICENSE·Draft 승인 | M2 기준선·M3 완료 |
| 6 | 완료 (2026-07-27) | `DOC-M5` Document Completion Gate | M1~M4 완료 |
| 7 | 완료 (2026-07-27) | Backlog `TASK-001`~`TASK-005` | 별도 구현 승인·Project/Contract/Source/Storage/CLI Scope |
| 8 | 완료 (2026-07-28) | Backlog `TASK-006` DEX vertical slice | raw replay·exact match·partial·resume |
| 9 | 완료 (2026-07-28) | Backlog `TASK-007` AUTH vertical slice | Approval·allowance·transferFrom·실패 TX·scope |
| 10 | 완료 (2026-07-28) | Backlog `TASK-008` FREEZE vertical slice | blacklist lifecycle·context scope·partial·resume |
| 11 | 완료 (2026-07-28) | Backlog `TASK-009` 통합 회귀·보안·문서 Gate | 24 QA·11-code·추적성·보안 통과 |
| 12 | 완료 (2026-07-29, offline V1) | Backlog `TASK-010` 병렬 문제풀이 운영 | live mode는 공식 Rules·별도 승인 |
| 13 | 완료 (2026-07-29) | Backlog `TASK-011` 예상문제 Offline Benchmark | 자동화 3/3 실증, 보조 6·미지원 21 공백 기록 |
| 14 | 계획 승인 대기 | `TASK-012~019` Coverage 확장 | fixture·Context Receipt·개별 code 승인 전 미착수 |

Web Workbench 문서·Preview는 위 순서와 병렬인 비차단 시연 UX 트랙이다.
`DOC-M2`~`DOC-M5`나 `TASK-001`의 선행 조건으로 추가하지 않는다. 실제 웹
구현 일정·Backlog·기술 선택은 Python 엔진과 CLI의 Analysis I/O 출력이
안정된 뒤 별도 승인으로만 생성한다.

Agentic Parallel Solve·Operations Board 문서·Preview도 위 순서와 병렬인
Rules-gated 운영 트랙이다. 관련 구현은 `TASK-010`으로만 추적하며,
`TASK-001`~`TASK-009`의 P0·V1 완료와 `DOC-M5`를 차단하지 않는다.
AI·agent·자동화·외부 문제 데이터 전송 규정과 Preview 사용자 확인, 별도
구현 승인을 모두 통과해야 시작한다.

세부 규정이 게시되지 않아도 “미확정 상태·확인 경로·기능 비활성화”가
문서화되면 DOC-M2 기준선은 완료할 수 있다. 이후 상태는 `Blocked`가 아니라
Rules Register의 `Active Official-Information Watch`로 관리하며 DB·README·
offline 검증 같은 독립 작업을 막지 않는다.

## 7. Document Completion Gate

### 7.1 필수 통과

- [x] 공식 규정·등록·팀·제출 정보가 확인값 또는 `unclear`와 출처로 기록됨
- [x] API·자동화·AI·사전 제작 도구 허용 범위가 상태별로 기록됨
- [x] 핵심 Concept·Technical 문서 승인 또는 Draft 유지 사유 기록
- [x] Roadmap·Backlog·QA checklist·QA scenarios 연결
- [x] confirmed fixture 3개와 후보 5개의 처리 방침 확정
- [x] `01_DB_SCHEMA.md`에 SQLite 논리 엔티티·관계·보존·mutation 경계 기록
- [x] 프로젝트 README 존재
- [x] Project LICENSE를 MIT로 확정, 제3자 자료 제외 경계 기록
- [x] metadata·Related Documents·상대 링크 검증 통과
- [x] fixture·analysis Schema 검증 `PASS 3`
- [x] 잔여 TODO·Known Issue·구현 중 결정 항목 분리

### 7.2 구현 전까지 보류 가능

- [ ] 정확한 dependency patch version과 `uv.lock`
- [ ] 논리 Schema를 구현한 정확한 SQLite DDL·migration·backup 명령
- [ ] provider별 실측 성능·rate limit
- [ ] 실제 CLI snapshot과 HTML Preview 차이
- [ ] P1·P2 기능용 추가 adapter와 전체 후보 fixture 자동화

위 항목은 코드를 통해서만 검증할 수 있으므로 문서 완료를 막지 않는다. 대신
담당 Backlog·QA ID와 결정 시점을 반드시 유지한다.

## 8. 위험과 대응

| 위험 | 영향 | 문서 대응 |
|:---|:---|:---|
| 공식 규정 지연·변경 | 도구·AI·API 준비 범위가 뒤집힘 | Rules Register에 상태·변경 이력·문의 기록 |
| Draft 상태 장기 유지 | 어떤 내용이 규범인지 불명확 | M4에서 규범·가안·구현 중 결정 분리 |
| 후보 fixture 무기한 TBD | 준비 범위와 완료율 왜곡 | M3에서 Confirm/Deferred/Drop 강제 |
| 표준 문서 중복 작성 | 서로 다른 진실 원본 발생 | 섹션 4 대응표와 대체 승인 |
| 문서 완료와 구현 승인 혼동 | 사용자의 우선순위 이탈 | M5에서 별도 승인 강제 |
| 루트 README·LICENSE 부재 | 해소 | README와 MIT License 추가, 제3자 자료 권리 분리 |
| 기존 오픈소스 조사 없이 직접 구현 | 시간 낭비·품질·라이선스 위험 | 기능별 `OSSR-*` 조사와 `OSS-*` 결정 Gate |
| Web Workbench 범위가 V1을 잠식 | Python 코어·Schema·OSS 검증 지연 | 정적 read-only Preview만 허용, Backlog·Gate·기술 스택 미변경 |
| Agentic 운영이 AI 의존 코어가 됨 | 허용 AI mode가 없으면 전체 운영 흐름 차단 | Python leaf는 독립 재현 가능하게 유지하되 full `TASK-010` 완료로 대체하지 않음 |
| 병렬 worker가 provider 제한 초과 | rate limit·ban·오분석 | 전체·provider별 concurrency budget, dedup·Queue age·fallback |
| 자동 제출로 오답·규정 위반 | 감점·실격·credential 노출 | 제출 Queue는 복사·수동 확인만, CTFd 호출 0건 QA |

## 9. 365 글로벌 평가 기준

| 기준 | Roadmap 반영 |
|:---|:---|
| Functionality | 요구사항·Schema·fixture·QA의 완료 Gate |
| Potential Impact | 재사용 가능한 문서 지도·source·evidence 계약 |
| Novelty | pool/user·권한 소비/탈취·온체인/맥락 분리 보존 |
| UX | UI-First Gate·400ms·FB-001을 구현 전 동결 |
| Open-source | README·LICENSE·출처·검증 명령 마감 |
| Business Plan | 공식 평가 기준 확인 후 Lean Canvas·제출 전략 작성 여부 결정 |

## 10. Related Documents

- **Concept_Design**: [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 공식 규정 전후 준비 순서
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 확인 사실·규정 상태·문의·변경 이력
- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항·후보 fixture·미결정 사항
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1과 규정 위험 점수
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - UI-First Gate·명령 흐름
- **UI_Screens**: [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - 사용자 확인·FB-001
- **UI_Screens**: [Web Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - 비차단 시연 UX와 별도 구현 승인 조건
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 기준 화면
- **UI_Screens**: [HTML Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - read-only 그래프·타임라인·증거 Draft
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 병렬 문제·worker·검증·제출 운영 UX
- **UI_Screens**: [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - `TASK-010` UI-First Gate
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 문서 우선·구현 Gate 원칙
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 규정·provider·rate limit 갱신 대상
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 규범 요구사항과 미결정 사항
- **Technical_Specs**: [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) - 구현 중 결정·LICENSE·dependency
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 작업 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - 기능별 재사용·직접 구현 결정 Gate
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - Rules-gated 병렬 운영 계약
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - 27개 비자동 문항의 엔진 묶음
- **Logic_Progress**: [P0·V1 구현 Backlog](./00_BACKLOG.md) - Document Gate 이후 실행 순서
- **Logic_Progress**: [Coverage 확장 Execution Plan](./01_EXECUTION_PLAN.md) - TASK-012~019 Wave와 Stop/Go
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed 3·후보 5 상태
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 24개 수용·회귀 기준
- **QA_Validation**: [QA Checklist](../05_QA_Validation/02_QA_CHECKLIST.md) - 문서·구현·회귀 실행 Gate
- **QA_Validation**: [Agentic Parallel Solve QA](../05_QA_Validation/03_AGENTIC_PARALLEL_SOLVE_QA.md) - 별도 6개 운영 QA
- **QA_Validation**: [예상문제 Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 30문항 coverage·실행 채점·우선 공백
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 새 분석기 fixture·승격·통합 기준
- **QA_Validation**: [Document Completion Report](../05_QA_Validation/04_DOCUMENT_COMPLETION_REPORT.md) - DOC-M5 검증 결과와 후속 경계
- **QA_Validation**: [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - raw replay·정합·partial·resume 검증
