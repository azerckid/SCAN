# SCAN 2026 문서 완료 Roadmap
> Created: 2026-07-26 18:28
> Last Updated: 2026-07-26 22:38
> Status: Approved 1.0

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

### 2.1 2026-07-26 기준 산출물

| 구분 | 현재 수량 | 상태 |
|:---|---:|:---|
| 상위 Markdown 문서 | 19 | Approved 1, Confirmed 1, UI Gate Passed 3, Draft 14 |
| confirmed fixture 패키지 | 3 | DEX·AUTH·FREEZE `confirmed / 0.2` |
| 후보 fixture | 5 | DOC-M3에서 Deferred, 단계별 승격 조건 기록 |
| JSON Schema | 6 | fixture 3종·analysis 3종 |
| 독립 검증기 | 2 | fixture `PASS 3`, analysis `PASS 3` |
| HTML Preview | 1 | 사용자 확인·FB-001 반영 완료 |

이 Roadmap, Rules Register와 QA Checklist를 포함한 수량이다.

### 2.2 진행률 해석

| 관점 | 가안 | 근거 |
|:---|---:|:---|
| 문서 구조·연결 | 95% | 5개 Layer, 메타데이터, Related Documents, 상대 링크 정합 |
| P0·V1 핵심 설계 내용 | 85% | 문제·우선순위·요구사항·Schema·UI·기술·Backlog·QA 작성 |
| 문서 승인·확정 | 40% | 핵심 문서 다수가 Draft 또는 Approval Pending |
| 전체 대회 준비 문서 | 65% | 공식 규정·운영·제출·QA checklist·잔여 fixture 방침 미완 |

백분율은 작업량 예측을 위한 가안이며 문서 상태를 대신하지 않는다. 완료 판정은
섹션 7의 체크박스로만 한다.

## 3. 문서 상태 등록부

### 3.1 Concept Design

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) | Draft | 공식 규정·등록·팀·제출 사실 반영 후 승인 |
| [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) | Draft 2 | 미결정 사항과 후보 fixture 방침 확정 |
| [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) | Draft 1 · Awaiting Official Information | 2026-07-27 등록 페이지 공개 후 세부 규정 재확인 |
| [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) | Draft 1 | 규정 위험 점수와 구현 전제 갱신 후 승인 |

### 3.2 UI Screens

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) | UI-First Gate Passed | 실제 CLI 구현 전에는 현 상태 유지 |
| [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) | UI-First Gate Passed | 실제 snapshot과의 차이는 구현 후 기록 |
| [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) | UI-First Gate Passed | FB-001 구현 연결만 추적 |
| [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) | 사용자 확인 완료 | 구현 전 기준 화면으로 동결 |

### 3.3 Technical Specs

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) | Draft 1 | 공식 규정·LICENSE·실제 dependency 반영 시점 분리 후 승인 |
| [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) | Draft | 규정·provider plan·rate limit·최종 adapter 우선순위 갱신 |
| [Reference Fixture Schema](../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) | Confirmed 0.1 | fixture schema 변경 요구가 생길 때만 개정 |
| [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) | Draft 1 | 공식 규정과 source policy 반영 후 승인 |
| [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) | Draft 1 | LICENSE·정확한 버전·저장 세부는 구현 전/중 결정으로 분리 |
| [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) | Draft 1 | 문서 계약 0.1 승인, 생성 Schema diff는 구현 후 검증 |
| [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) | Draft 1 · Initial Survey | P0·V1 `OSS-*` 결정과 fixture bake-off 완료 |
| `01_DB_SCHEMA.md` | 미작성 | TD-007의 SQLite 결정을 논리 엔티티·관계·보존 경계로 문서화; 정확한 DDL은 구현 시 결정 |

### 3.4 Logic Progress

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [P0·V1 구현 Backlog](./00_BACKLOG.md) | Draft 1 · Approval Pending | 문서 Gate 통과 후 범위 승인; 구현은 별도 승인 |
| 이 문서 | Approved 1.0 | 승인 기준선 유지; 이후 Milestone 상태만 갱신 |
| `01_EXECUTION_PLAN.md` | 조건부 미작성 | 구현 일정이 필요할 때 Backlog를 날짜·담당자로 전환 |
| `02_ROADMAP_BACKLOG_SYNC.md` | 조건부 미작성 | 구현 시작 전 Roadmap↔Backlog 상태 동기화 규칙 작성 |

### 3.5 QA Validation

| 문서 | 현재 상태 | 완료를 위해 남은 일 |
|:---|:---|:---|
| [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) | Draft 1 · Fixture Scope Closed | 후보 5개 Deferred 결정; 단계별 승격 조건 유지 |
| [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) | Draft 1 · Approval Pending | 24개 시나리오 범위 승인 |
| [QA Checklist](../05_QA_Validation/02_QA_CHECKLIST.md) | Draft 1 · Approval Pending | 24개 시나리오 실행 시점·결과 기록 형식 승인 |
| DEX·AUTH·FREEZE fixture | Confirmed | V1 기준값으로 동결, 정답 임의 변경 금지 |

## 4. 표준 문서명과 기존 문서의 대응

solmate Gate가 요구하는 표준 문서와 이 저장소의 도메인 문서를 다음처럼
대응한다. 같은 내용을 복제하지 않고, 승인되지 않은 대응만 새 문서 후보로 둔다.

| 표준 문서 | 현재 대응 문서 | 판단 |
|:---|:---|:---|
| `01_VISION_CORE.md` | 참가·분석 도구 준비 전략 | 대체 승인 필요 |
| `02_LEAN_CANVAS.md` | 없음 | 공식 평가에 Business Plan이 포함될 때 작성 |
| `03_PRODUCT_SPECS.md` | 예상문제 은행 + P0·V1 요구사항 | 대체 승인 필요 |
| `00_ROADMAP.md` | 이 문서 | 충족 |
| `02_QA_CHECKLIST.md` | P0·V1 QA Checklist | 충족, 범위 승인 대기 |
| `01_DB_SCHEMA.md` | 미작성 | 필수 작성 — SQLite 논리 Schema는 Document Gate 전, 정확한 DDL·migration은 `TASK-004`에서 확정 |
| `02_API_SPECS.md` | 데이터 소스 등록부·Analysis I/O Schema | 외부 제공 API가 생길 때 별도 작성 |

`VISION_CORE`·`PRODUCT_SPECS`는 이름만 맞추기 위해 중복 생성하지 않는다.
기존 문서 대체 여부를 사용자가 승인하지 않거나 공식 제출에서 해당 파일이
필요하면 표준 문서로 분리한다.

## 5. 문서 완료 Milestone

### [x] DOC-M1 — Roadmap 기준선 승인

- [x] PR #9 승인 당시 기존 상위 Markdown 문서 15개와 이 Roadmap의 상태를 확인한다.
- [x] 작성률·확정률·전체 준비율의 해석을 승인한다.
- [x] 표준 문서 대체와 조건부 문서 방침을 승인한다.
- [x] 구현보다 문서 완료를 우선한다는 순서를 고정한다.

완료 조건: 이 Roadmap의 상태가 `Confirmed 1.0` 또는 `Approved`로 변경된다.

완료 기록: 사용자 승인과 PR #9 병합(`c115f7d`, 2026-07-26)을 기준으로
`Approved 1.0` 상태를 확정했다.

### [ ] DOC-M2 — 공식 규정·참가 운영 확정

- [x] `03_SCAN_2026_RULES_REGISTER.md`를 작성한다.
- [x] 공식 원문 URL·게시 시각·조회 시각·변경 이력을 기록한다.
- [x] API·자동화·AI·사전 제작 도구·상용 서비스 규정을
      `allowed / restricted / unclear`로 분리한다.
- [ ] 등록 마감·팀 구성·본인 확인·예선·본선 일정을 기록한다.
- [ ] 지원 체인·제공 데이터·정답 제출 형식·증거 제출 형식을 기록한다.
- [x] 불명확한 항목은 추정하지 않고 문의 대상·회신 상태를 기록한다.
- [ ] 규정 결과를 준비 전략·문제은행·우선순위·소스 등록부·요구사항에 역반영한다.

완료 조건: 규정상 사용할 수 있는 데이터·도구·팀·제출 범위를 문서만으로
설명할 수 있고, 미확정 항목에는 담당 확인 경로가 있다.

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
`Deferred`로 결정했다. 24개 QA 시나리오는 `Approval Pending / Not Executed`로
기록하고 작업별 실행 시점을 분리했다.

### [ ] DOC-M4 — Draft 승인·문서 패키지 마감

- [ ] Concept 문서의 Draft 상태와 미결정 사항을 검토한다.
- [ ] Technical 문서의 규범 부분과 구현 중 결정 부분을 분리한다.
- [ ] Backlog와 QA 시나리오의 문서 범위를 승인한다.
- [ ] P0·V1 오픈소스 사전조사의 `OSS-*` 결정과 구현 전 Gate를 확정한다.
- [ ] `01_DB_SCHEMA.md`에 SQLite 논리 엔티티·관계·보존·mutation 경계를 기록한다.
- [ ] 프로젝트 루트 `README.md`에 목적·문서 지도·검증 명령을 작성한다.
- [ ] Project LICENSE를 코드 공개 전에 결정한다.
- [ ] 모든 Markdown 메타데이터·Related Documents·상대 링크를 검증한다.
- [ ] 중복되거나 이미 완료된 “다음 단계” 문구를 현재 상태로 갱신한다.
- [ ] 문서 변경 이력과 잔여 Known Issue를 기록한다.

완료 조건: 핵심 문서가 승인 상태이거나, Draft 유지 사유와 결정 시점이
Roadmap에 명시되어 있다.

### [ ] DOC-M5 — Document Completion Gate

- [ ] `DOC-M1`~`DOC-M4`가 완료되었다.
- [ ] HTML UI Preview Gate와 UI-First Gate가 계속 통과 상태다.
- [ ] Pre-Code Technical Brief의 데이터·API·상태·acceptance 기준이 유효하다.
- [ ] 공식 규정 제한이 Backlog·QA·source policy에 반영되었다.
- [ ] P0·V1 오픈소스 `OSS-*` 결정과 fixture 검증 계획이 구현 전에 확정되었다.
- [ ] 문서·Schema·fixture 검증이 모두 통과한다.
- [ ] Backlog의 `TASK-001`~`TASK-009`가 모두 `ToDo` 상태로 유지된다.

완료 조건: 사용자가 문서 완료를 승인하면 이 Gate는 닫힌다. `TASK-001`
시작은 이 Gate와 별개의 후속 승인으로만 진행하며, 구현 보류는 문서 완료를
막지 않는다.

## 6. 일정 전략

| 순서 | 시점 | 작업 | 차단 관계 |
|:---:|:---|:---|:---|
| 1 | 완료 (2026-07-26) | `DOC-M1` Roadmap 승인 | 이후 문서 순서의 기준 |
| 2 | 2026-07-27 등록 시작 후 | `DOC-M2` 공식 규정 Register | 규정 정보 접근 필요 |
| 3 | 규정 1차 확인 직후 | 준비 전략·우선순위·소스·요구사항 동기화 | DOC-M2 의존 |
| 4 | 완료 (2026-07-26) | `DOC-M3` QA checklist·fixture 방침 | DOC-M2와 독립 완료 |
| 5 | M2·M3 이후 | `DOC-M4` Draft 승인·README·LICENSE | 규정·fixture 결정 의존 |
| 6 | 모든 문서 검증 후 | `DOC-M5` Document Completion Gate | M1~M4 의존 |
| 7 | 별도 승인 후 | Backlog `TASK-001` | Document Gate 의존 |

공식 등록 페이지가 열리지 않거나 세부 규정이 게시되지 않으면 `DOC-M2`를
완료로 표시하지 않는다. 이 경우 Roadmap에는 `Blocked`가 아니라
`Awaiting Official Information`으로 기록하고, 규정과 독립적인 M3 작업을
진행한다.

## 7. Document Completion Gate

### 7.1 필수 통과

- [ ] 공식 규정·등록·팀·제출 정보가 출처와 함께 기록됨
- [ ] API·자동화·AI·사전 제작 도구 허용 범위가 상태별로 기록됨
- [ ] 핵심 Concept·Technical 문서 승인 또는 Draft 유지 사유 기록
- [x] Roadmap·Backlog·QA checklist·QA scenarios 연결
- [x] confirmed fixture 3개와 후보 5개의 처리 방침 확정
- [ ] `01_DB_SCHEMA.md`에 SQLite 논리 엔티티·관계·보존·mutation 경계 기록
- [ ] 프로젝트 README 존재
- [ ] Project LICENSE 결정 시점 확정
- [ ] metadata·Related Documents·상대 링크 검증 통과
- [x] fixture·analysis Schema 검증 `PASS 3`
- [ ] 잔여 TODO·Known Issue·구현 중 결정 항목 분리

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
| 루트 README·LICENSE 부재 | 공개 저장소 진입·재사용 불명확 | M4에서 README 작성, LICENSE 사용자 결정 |
| 기존 오픈소스 조사 없이 직접 구현 | 시간 낭비·품질·라이선스 위험 | 기능별 `OSSR-*` 조사와 `OSS-*` 결정 Gate |

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
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 기준 화면
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 문서 우선·구현 Gate 원칙
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 규정·provider·rate limit 갱신 대상
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 규범 요구사항과 미결정 사항
- **Technical_Specs**: [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) - 구현 중 결정·LICENSE·dependency
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 작업 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - 기능별 재사용·직접 구현 결정 Gate
- **Logic_Progress**: [P0·V1 구현 Backlog](./00_BACKLOG.md) - Document Gate 이후 실행 순서
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed 3·후보 5 상태
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 24개 수용·회귀 기준
- **QA_Validation**: [QA Checklist](../05_QA_Validation/02_QA_CHECKLIST.md) - 문서·구현·회귀 실행 Gate
