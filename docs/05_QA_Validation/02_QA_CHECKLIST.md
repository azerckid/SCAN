# SCAN 2026 P0·V1 QA Checklist
> Created: 2026-07-26 20:28
> Last Updated: 2026-07-26 20:59
> Status: Draft 1 · Approval Pending

## 1. 문서 목적

이 문서는 SCAN 2026 분석 도구의 문서 완료, 구현 착수, 작업별 검증, 통합
회귀와 대회 전 점검을 같은 체크리스트에서 관리한다. 상세 입력·단계·기대
결과는 [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)가 규범이며, 이 문서는
언제 무엇을 실행하고 어떤 증거를 남겨야 하는지 정의한다.

현재 Python application code는 없으며 QA 시나리오 24개는
`Approval Pending / Not Executed` 상태다. 문서 검증 통과와 구현 테스트
통과를 같은 의미로 사용하지 않는다.

## 2. 상태와 판정

### 2.1 체크 상태

| 상태 | 의미 |
|:---|:---|
| `[ ]` | 아직 실행하지 않았거나 승인 대기 |
| `[x]` | 해당 시점의 증거를 확보하고 통과 |
| `N/A` | 적용하지 않는 이유와 승인자를 기록 |

### 2.2 결과 상태

| 상태 | 의미 |
|:---|:---|
| `not_executed` | 구현 또는 선행 Gate 대기 |
| `pass` | 기대 결과와 증거가 모두 일치 |
| `partial` | 일부 결과만 입증, 누락 조건 기록 |
| `fail` | 필수 조건 불충족 |
| `blocked` | 같은 외부 차단이 반복되고 대체 검증이 없음 |

공식 정보 대기는 `blocked`가 아니라 `awaiting_official_information`으로
별도 기록한다.

## 3. DOC-M3 문서 기준선

- [x] QA 시나리오 ID 24개가 중복 없이 정의되어 있다.
- [x] confirmed fixture 3개가 DEX·AUTH·FREEZE V1 exact-match 기준을 제공한다.
- [x] 후보 fixture 5개는 `Deferred`로 결정되었다.
- [x] 각 Deferred fixture에 필요 소스·승격 조건·재검토 시점이 있다.
- [x] fixture Schema 검증기가 `PASS 3`이다.
- [x] analysis Schema 검증기가 `PASS 3`이다.
- [x] Backlog `TASK-001`~`TASK-009`는 모두 `ToDo`다.
- [x] HTML UI Preview Gate와 UI-First Gate 통과 기록이 존재한다.
- [ ] 이 Checklist와 QA 시나리오 범위를 사용자가 승인한다.
- [ ] DOC-M2의 공식 규정·등록·제출 정보가 확정된다.

마지막 두 항목은 각각 DOC-M4 승인과 DOC-M2에 속하며 DOC-M3 fixture 범위
결정을 되돌리지 않는다.

## 4. 24개 QA 시나리오 승인·실행 시점

### 4.1 공통 상태

| 항목 | 값 |
|:---|:---|
| 정의 수 | 24 |
| 승인 상태 | Approval Pending |
| 실행 상태 | Not Executed |
| 구현 전 허용 실행 | 문서 링크·ID·Schema·fixture 정합 검사만 |
| 전체 실행 Gate | `TASK-009` 통합 회귀 |

### 4.2 실행 매트릭스

24개 QA ID는 아래 표에 모두 포함된다. 범위별 재실행이 필요한
`QA-REG-003`과 `QA-SEC-001`은 둘 이상의 Gate에 나타나지만 시나리오
개수에는 한 번만 포함한다.

| Gate | 실행 시점 | QA ID | 현재 상태 |
|:---|:---|:---|:---|
| Document Gate | 구현 전과 모든 문서 PR | `QA-REG-003`의 문서·Schema·fixture 부분 | not_executed: 문서 부분은 구현 전 실행 가능하나 실행 기록 없음 |
| Project Gate | `TASK-001` 완료 후 | `QA-BOOT-001` | not_executed |
| Contract Gate | `TASK-002` 완료 후 | `QA-SCHEMA-001`, `QA-SCHEMA-002` | not_executed |
| Source Gate | `TASK-003` 완료 후 | `QA-RULE-001`, `QA-SOURCE-001`, `QA-RETRY-001`, `QA-FALLBACK-001` | not_executed |
| Storage Gate | `TASK-004` 완료 후 | `QA-CACHE-001`, `QA-EXPORT-001`, `QA-ARTIFACT-001`, `QA-SEC-001`의 storage 범위 | not_executed |
| CLI Gate | `TASK-005` 완료 후 | `QA-CLI-001`, `QA-CLI-002`, `QA-CLI-003`, `QA-CLI-004`, `QA-SEC-001`의 CLI 범위 | not_executed |
| DEX Gate | `TASK-006` 완료 후 | `QA-DEX-001`, `QA-DEX-002` | not_executed |
| AUTH Gate | `TASK-007` 완료 후 | `QA-AUTH-001`, `QA-AUTH-002` | not_executed |
| FREEZE Gate | `TASK-008` 완료 후 | `QA-FREEZE-001`, `QA-FREEZE-002` | not_executed |
| Integration Gate | `TASK-009` 완료 전 | `QA-REG-001`, `QA-REG-002`, `QA-REG-003` 전체, `QA-SEC-001` 전체 | not_executed |

`QA-REG-003`과 `QA-SEC-001`은 범위별로 여러 Gate에서 실행하지만 시나리오
ID는 24개 집계에서 한 번만 센다.

## 5. 구현 착수 전 Gate

- [ ] Document Completion Gate가 사용자 승인으로 닫혔다.
- [ ] `TASK-001` 시작을 별도로 승인받았다.
- [ ] Backlog의 관련 Concept·UI·HTML Preview·Technical·QA 링크를 다시 읽었다.
- [ ] Rules Register의 API·자동화·AI·사전 도구 상태를 확인했다.
- [ ] 제한된 source와 동작이 실행 전 차단되는지 요구사항으로 확인했다.
- [ ] 실제 dependency·license·Python 범위를 결정했다.
- [ ] secret·private key·서명·거래 전송이 범위 밖임을 확인했다.
- [ ] 테스트가 사용자 실제 홈·credential·`.scan/`을 읽거나 변경하지 않게 한다.

이 Gate는 문서 완료 승인과 구현 승인 사이의 분리선이며, DOC-M3 완료만으로
체크할 수 없다.

## 6. 작업별 QA Gate

### 6.1 TASK-001~TASK-005 공통 기반

- [ ] clean checkout과 잠금 파일로 환경을 재현한다.
- [ ] Ruff·format·pytest와 두 Schema 검증기를 실행한다.
- [ ] Analysis I/O 모델과 승인 Schema의 의미상 diff가 0이다.
- [ ] offline cache miss에서 네트워크 호출이 0건이다.
- [ ] timeout·429·일시적 5xx만 제한적으로 재시도한다.
- [ ] fallback 전후 source와 모든 attempt를 보존한다.
- [ ] SQLite cache·checkpoint와 SHA-256 artifact를 임시 경로에서 검증한다.
- [ ] JSON·Markdown이 같은 result model에서 생성된다.
- [ ] CLI stdout·stderr·exit code가 UI 문서와 일치한다.
- [ ] secret canary와 사용자 절대 경로가 log·DB·artifact·export에 0건이다.

### 6.2 TASK-006 DEX

- [ ] USDC 입력 `25000000000` raw가 exact match다.
- [ ] pool output WETH `14449515027026387018` raw가 exact match다.
- [ ] user net output native ETH가 동일 raw로 별도 결과에 있다.
- [ ] internal call 제거 시 `partial`, 자산·수량 오판 시 complete 거부다.

### 6.3 TASK-007 AUTH

- [ ] Approval·calldata·allowance 4지점·성공 `transferFrom`을 연결한다.
- [ ] 소비량 `4500000` raw와 allowance 감소량이 exact match다.
- [ ] 실패 TX 3개를 소비에서 제외한다.
- [ ] 탈취·피싱은 근거 없이 true로 설정할 수 없다.

### 6.4 TASK-008 FREEZE

- [ ] blacklist와 unblacklist의 상태 전이가 exact match다.
- [ ] event·call·state·context evidence가 분리된다.
- [ ] Circle·OFAC 자료의 주소 명시 여부를 구분한다.
- [ ] 현재 제재·범죄 의도를 자동 판정하지 않는다.

### 6.5 TASK-009 통합

- [ ] 24개 QA 시나리오의 최종 결과가 기록된다.
- [ ] 세 confirmed fixture를 두 번 실행해 결정적 값이 같다.
- [ ] 오류 코드 11개의 result·error·exit code 행렬이 일치한다.
- [ ] 모든 result→evidence→source 참조가 유효하다.
- [ ] 문서·Backlog·Schema·fixture·구현 경로가 동기화된다.
- [ ] `live` 실패가 offline 회귀 정답을 변경하지 않는다.

## 7. PR·릴리스·대회 전 Gate

### 7.1 모든 문서 PR

- [ ] `git diff --check`가 통과한다.
- [ ] 변경 문서의 metadata와 Related Documents를 확인한다.
- [ ] 상대 링크와 ID 유일성을 확인한다.
- [ ] fixture·analysis Schema 검증이 각각 `PASS 3`이다.
- [ ] 완료·승인·실행 상태를 혼용하지 않는다.

### 7.2 모든 구현 PR

- [ ] 관련 작업의 unit·integration·regression을 실행한다.
- [ ] 새 오류·source·결과 필드가 승인 계약과 연결된다.
- [ ] mock·fixture 변경이 정답을 편의상 바꾸지 않는다.
- [ ] dependency 추가 시 라이선스·공식 배포·보안 근거를 기록한다.
- [ ] secret scan과 로컬 경로 비노출을 확인한다.
- [ ] UI 동작 변경 시 HTML Preview·UI 문서·피드백을 동기화한다.

### 7.3 대회 직전

- [ ] 공식 Rules의 최신 조회 시각과 변경 이력을 확인한다.
- [ ] API·자동화·AI·사전 제작 도구·fixture·cache 상태가 `allowed`인지 확인한다.
- [ ] `unclear` 항목은 공식 문의 또는 보수적 비활성화로 처리한다.
- [ ] API key·rate limit·fallback·offline cache를 점검한다.
- [ ] 정답·증거 제출 형식에 export를 맞춘다.
- [ ] 팀 장비에서 clean install과 confirmed fixture 회귀를 실행한다.
- [ ] CTFd 계정·팀·시간대·본인 확인 상태를 점검한다.

## 8. Fixture 처리 Gate

### 8.1 V1 기준선

| Fixture | 상태 | 역할 | 변경 원칙 |
|:---|:---|:---|:---|
| `FX-SVC-DEX-001` | confirmed / 0.2 | pool/user output 분리 | 정답 변경 금지, source 장애는 별도 기록 |
| `FX-EVM-AUTH-001` | confirmed / 0.2 | 승인·권한 소비 연결 | 탈취 판정 추가 금지 |
| `FX-EVM-FREEZE-001` | confirmed / 0.2 | 온체인 상태·공식 맥락 분리 | 현재 제재 판정 추가 금지 |

### 8.2 Deferred 후보

- [x] `FX-FLOW-EVM-001` — P1 PATH·LABEL 전 재검토
- [x] `FX-SVC-BRG-001` — P2 XCHAIN·BRIDGE 전 재검토
- [x] `FX-EVM-PROXY-001` — P3 PROXY 승격 시 재검토
- [x] `FX-FLOW-MULTI-001` — P3 PRICE·다주소 집계 전 재검토
- [x] `FX-UNCERTAIN-001` — P2 HEUR 또는 P3 MIXER 전에 한 분기로 고정

Deferred는 폐기가 아니며 V1 완료 조건도 아니다. 구체 소스·승격 조건은
[Reference Fixtures §8](./01_REFERENCE_FIXTURES.md#8-doc-m3-후보-처리-결정)을
따른다.

## 9. QA 결과 기록 표준

각 실행은 최소 아래 필드를 남긴다.

| 필드 | 내용 |
|:---|:---|
| `run_id` | 실행별 유일 ID |
| `qa_id` | `QA-...` |
| `task_id` | 책임 `TASK-...` |
| `mode` | offline / fault-injection / live |
| `status` | not_executed / pass / partial / fail / blocked |
| `started_at`, `finished_at` | RFC 3339 timezone 포함 |
| `commit_sha` | 검증한 코드·문서 상태 |
| `fixture_id`, `fixture_version` | 적용 시 기록 |
| `evidence` | 로그·report·artifact의 저장 위치와 hash |
| `environment` | Python·OS·dependency lock 식별자 |
| `known_issues` | 미해결 항목과 다음 행동 |

실행하지 않은 항목에 `pass`를 기록하지 않는다. `live` 결과는 source 상태를
설명할 수 있지만 결정적 offline regression을 대신하지 않는다.

## 10. 365 글로벌 평가 기준

| 기준 | QA Gate | 통과 증거 |
|:---|:---|:---|
| Functionality | Schema·fixture exact-match·오류 주입·회귀 | 테스트 report와 result/evidence/source 연결 |
| Potential Impact | 반복 분석의 cache·resume·export | 세 vertical slice의 재사용 가능한 실행 기록 |
| Novelty | pool/user·권한 소비/탈취·온체인/맥락 분리 | 분리 계약을 깨뜨리는 오류 주입 거부 |
| UX | UI-First·400ms 첫 피드백·FB-001·접근성 | CLI snapshot·stdout/stderr·exit code |
| Open-source | clean install·license·provenance·문서 지도 | lock·LICENSE·재현 명령·출처 |
| Business Plan | 현재 P0·V1 구현 Gate에는 N/A | 제출 전략에서 별도 평가하고 N/A 사유 유지 |

## 11. Originality & Ethics Check

- [ ] 공개 TX·문서·오픈소스 주소 자료의 URL·license·retrieved_at을 보존한다.
- [ ] 제3자의 신원·범죄 의도·피해 여부를 근거 없이 단정하지 않는다.
- [ ] AUTH 탈취·FREEZE 범죄·현재 제재를 `not_assessed` 경계 밖으로 확장하지 않는다.
- [ ] 비공개 문제·답안·개인정보를 저장소나 허용되지 않은 외부 서비스로 전송하지 않는다.
- [ ] API key·credential·private key·로컬 절대 경로가 산출물에 남지 않는다.
- [ ] 공식 규정에서 제한된 자동화·AI·source를 실행 전에 차단한다.

## 12. 승인과 완료 조건

이 Checklist의 승인과 테스트 실행은 별개다.

- [ ] 사용자가 Checklist와 24개 QA 시나리오 범위를 승인한다.
- [ ] Document Completion Gate 승인 후 구현 착수 여부를 별도로 결정한다.
- [ ] 구현된 QA만 `pass / partial / fail / blocked`로 기록한다.
- [ ] `TASK-009` 종료 전 24개 시나리오의 최종 상태와 증거를 기록한다.
- [ ] 구현하지 않은 범위는 `not_executed`로 남기고 통과로 계산하지 않는다.

문서 단계 완료 조건은 실행 시점·판정·증거 형식이 정해지고 fixture 처리
방침이 연결되는 것이다. 제품 QA 완료 조건은 구현 후 모든 mandatory Gate를
실제로 통과하는 것이다.

## 13. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제별 완료·부분·실패 기준
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1·P1·P2·P3 범위
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - API·자동화·AI·사전 도구 상태
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 명령·상태·종료 코드
- **UI_Screens**: [CLI UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 상태·오류·접근성 표시
- **UI_Screens**: [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - UI-First Gate와 FB-001
- **UI_Screens**: [CLI HTML Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 사용자 확인 화면
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 구현·테스트·보안 기준
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source 능력·제약
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - acceptance·오류·source 계약
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - request·result·error 계약
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - DOC-M3와 구현 분리 Gate
- **Logic_Progress**: [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK별 책임과 Preconditions
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - 24개 상세 검증 절차
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed 3·Deferred 5 처리 방침
