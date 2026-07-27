# SCAN 2026 P0·V1 QA Checklist
> Created: 2026-07-26 20:28
> Last Updated: 2026-07-28 02:22
> Status: Approved 1.8 · TASK-008 FREEZE Scope Passed

## 1. 문서 목적

이 문서는 SCAN 2026 분석 도구의 문서 완료, 구현 착수, 작업별 검증, 통합
회귀와 대회 전 점검을 같은 체크리스트에서 관리한다. 상세 입력·단계·기대
결과는 [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)가 규범이며, 이 문서는
언제 무엇을 실행하고 어떤 증거를 남겨야 하는지 정의한다.

최소 Python package와 offline 품질 Gate, Analysis I/O runtime 계약이
구현됐고 source policy·retry·fallback 및 SQLite storage 계층이 추가됐다.
QA 시나리오 24개 중 19개는 `pass`, source/security 교차 시나리오 2개는
`partial`, 나머지 3개는 `not_executed`다. TASK-008 FREEZE 범위 통과를
전체 통합 Gate 통과와 같은 의미로 사용하지 않는다.

`TASK-010`의 Agentic Parallel Solve QA 6개는 별도
`Scope Approved / Not Executed` 상태이며 기존 24개 P0·V1 집계를 변경하지
않는다.

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
- [x] 이 Checklist와 QA 시나리오 범위를 사용자가 승인했다.
- [x] DOC-M2가 확인 사실·`unclear`·Notification Intake 기준선으로 완료되었다.

미공개 규정은 `allowed`로 확정한 것이 아니다. Active Watch와 보수적
비활성화로 처리하며 DOC-M3 fixture 범위 결정을 되돌리지 않는다.

## 4. 24개 QA 시나리오 승인·실행 시점

### 4.1 공통 상태

| 항목 | 값 |
|:---|:---|
| 정의 수 | 24 |
| 승인 상태 | Scope Approved |
| 실행 상태 | 19 pass / 2 partial / 3 not_executed |
| 구현 전 허용 실행 | 문서 링크·ID·Schema·fixture 정합 검사만 |
| 전체 실행 Gate | `TASK-009` 통합 회귀 |

### 4.2 실행 매트릭스

24개 QA ID는 아래 표에 모두 포함된다. 범위별 재실행이 필요한
`QA-REG-003`과 `QA-SEC-001`은 둘 이상의 Gate에 나타나지만 시나리오
개수에는 한 번만 포함한다.

| Gate | 실행 시점 | QA ID | 현재 상태 |
|:---|:---|:---|:---|
| Document Gate | 구현 전과 모든 문서 PR | `QA-REG-003`의 문서·Schema·fixture 부분 | pass: 2026-07-27 문서 완료 보고서 |
| Project Gate | `TASK-001` 완료 후 | `QA-BOOT-001` | pass: 2026-07-27 |
| Contract Gate | `TASK-002` 완료 후 | `QA-SCHEMA-001`, `QA-SCHEMA-002` | pass: 2026-07-27 |
| Source Gate | `TASK-003` 완료 후 | `QA-RULE-001`, `QA-SOURCE-001`, `QA-RETRY-001`, `QA-FALLBACK-001` | TASK-003 scope pass: retry/fallback pass, rule/source partial |
| Storage Gate | `TASK-004` 완료 후 | `QA-CACHE-001`, `QA-EXPORT-001`, `QA-ARTIFACT-001`, `QA-SEC-001`의 storage 범위 | storage scope pass: cache/export/artifact pass, security partial |
| CLI Gate | `TASK-005` 완료 후 | `QA-CLI-001`, `QA-CLI-002`, `QA-CLI-003`, `QA-CLI-004`, `QA-SEC-001`의 CLI 범위 | CLI-001~003 pass, CLI-004·security partial |
| DEX Gate | `TASK-006` 완료 후 | `QA-DEX-001`, `QA-DEX-002`, `QA-CLI-004`의 실제 DEX resume 범위 | DEX-001·002와 CLI-004 pass: 2026-07-28 |
| AUTH Gate | `TASK-007` 완료 후 | `QA-AUTH-001`, `QA-AUTH-002` | pass: 2026-07-28 |
| FREEZE Gate | `TASK-008` 완료 후 | `QA-FREEZE-001`, `QA-FREEZE-002` | pass: 2026-07-28 |
| Integration Gate | `TASK-009` 완료 전 | `QA-REG-001`, `QA-REG-002`, `QA-REG-003` 전체, `QA-SEC-001` 전체 | not_executed |

`QA-REG-003`과 `QA-SEC-001`은 범위별로 여러 Gate에서 실행하지만 시나리오
ID는 24개 집계에서 한 번만 센다.

## 5. 구현 착수 전 Gate

- [x] Document Completion Gate가 사용자 승인으로 닫혔다.
- [x] `TASK-001` 시작을 별도로 승인받았다.
- [x] Backlog의 관련 Concept·UI·HTML Preview·Technical·QA 링크를 다시 읽었다.
- [x] Rules Register의 API·자동화·AI·사전 도구 상태를 확인했다.
- [x] P0·V1 관련 오픈소스 후보의 고정 commit·license·`OSS-*` 결정을 확인했다.
- [x] TASK-001 dependency는 공식 package와 공개 metadata로 검증했다.
- [x] 제한된 source와 동작이 실행 전 차단되는지 요구사항으로 확인했다.
- [x] 실제 dependency·license·Python 범위를 결정했다.
- [x] secret·private key·서명·거래 전송이 범위 밖임을 확인했다.
- [x] 테스트가 사용자 실제 홈·credential·`.scan/`을 읽거나 변경하지 않게 한다.

이 Gate는 문서 완료 승인과 구현 승인 사이의 분리선이며, DOC-M3 완료만으로
체크할 수 없다.

## 6. 작업별 QA Gate

### 6.1 TASK-001~TASK-008 공통 기반

- [x] TASK-001 범위에서 독립 임시 환경과 잠금 파일로 설치를 재현했다.
- [x] TASK-001 범위에서 Ruff·format·pytest와 두 Schema 검증기를 실행했다.
- [x] Analysis I/O 모델과 승인 Schema의 35개 의미 probe가 모두 일치한다.
- [x] TASK-003 transport 범위의 offline cache miss에서 네트워크 호출이 0건이다.
- [x] timeout·429·HTTP 500·502·503·504만 제한적으로 재시도한다.
- [x] fallback 전후 source·provider와 모든 attempt를 보존한다.
- [x] SQLite cache·checkpoint와 SHA-256 artifact를 임시 경로에서 검증한다.
- [x] JSON·Markdown이 같은 result model에서 생성된다.
- [x] CLI stdout·stderr·exit code가 UI 문서와 일치한다.
- [x] TASK-004 storage 범위에서 secret canary와 사용자 절대 경로가 DB·artifact·export에 0건이다.
- [x] TASK-005 CLI 범위에서 secret canary와 사용자 절대 경로가 stdout·stderr·오류에 0건이다.
- [x] TASK-003 source payload repr·오류·attempt에는 query·header secret이 0건이다.
- [x] TASK-006 raw replay 입력의 미검증 extra·로컬 절대 경로가 artifact와 terminal에 남지 않는다.
- [x] TASK-007 AUTH raw replay의 시크릿·provider URL·전체 로컬 경로가 terminal·오류에 남지 않는다.
- [x] TASK-008 FREEZE raw replay의 시크릿·provider URL·전체 로컬 경로가 terminal·오류에 남지 않는다.

### 6.2 TASK-006 DEX

- [x] USDC 입력 `25000000000` raw가 exact match다.
- [x] pool output WETH `14449515027026387018` raw가 exact match다.
- [x] user net output native ETH가 동일 raw로 별도 결과에 있다.
- [x] internal call 제거 시 `partial`, 자산·수량 오판 시 complete 거부다.

### 6.3 TASK-007 AUTH

- [x] Approval·calldata·allowance 4지점·성공 `transferFrom`을 연결한다.
- [x] 소비량 `4500000` raw와 allowance 감소량이 exact match다.
- [x] nonce 327~329의 실패 TX 3개를 소비에서 제외하고 context로 보존한다.
- [x] 탈취·피싱은 근거 없이 true로 설정할 수 없다.

### 6.4 TASK-008 FREEZE

- [x] blacklist와 unblacklist의 상태 전이가 exact match다.
- [x] event·call·state·context evidence가 분리된다.
- [x] Circle·OFAC 자료의 주소 명시 여부를 구분한다.
- [x] 현재 제재·범죄 의도를 자동 판정하지 않는다.

### 6.5 TASK-009 통합

- [ ] 24개 QA 시나리오의 최종 결과가 기록된다.
- [ ] 세 confirmed fixture를 두 번 실행해 결정적 값이 같다.
- [ ] 오류 코드 11개의 result·error·exit code 행렬이 일치한다.
- [ ] 모든 result→evidence→source 참조가 유효하다.
- [ ] 문서·Backlog·Schema·fixture·구현 경로가 동기화된다.
- [ ] `live` 실패가 offline 회귀 정답을 변경하지 않는다.

### 6.6 TASK-010 병렬 문제풀이 운영

- [ ] 공식 Rules에서 AI·agent·자동화·외부 문제 데이터 전송 범위를 확인한다.
- [ ] Operations Board Preview를 사용자가 확인하고 피드백을 기록한다.
- [ ] 문제 간 상태·result·checkpoint·candidate가 격리된다.
- [ ] 문제 내부 leaf job dependency와 source request dedup이 일치한다.
- [ ] provider·worker별 동시성 제한과 Queue age가 표시된다.
- [ ] worker 하나의 실패가 다른 문제 상태로 전파되지 않는다.
- [ ] 독립 검증 없는 후보와 충돌 후보가 `submission_ready`가 아니다.
- [ ] AI 제한 시 human·Python CLI fallback이 동작한다.
- [ ] CTFd 자동 제출·credential·session·brute force가 0건이다.
- [ ] Agentic Parallel Solve QA 6개의 구현된 범위를 실행·기록한다.

## 7. PR·릴리스·대회 전 Gate

### 7.1 모든 문서 PR

- [x] `git diff --check`가 통과한다.
- [x] 변경 문서의 metadata와 Related Documents를 확인한다.
- [x] 상대 링크와 ID 유일성을 확인한다.
- [x] fixture·analysis Schema 검증이 각각 `PASS 3`이다.
- [x] 완료·승인·실행 상태를 혼용하지 않는다.

문서 완료 통과는 application unit·integration·live test 통과를 뜻하지 않는다.
해당 결과는 `TASK-001` 이후에만 기록한다.

### 7.2 모든 구현 PR

- [x] TASK-001의 unit·integration·regression을 실행했다.
- [x] 새 오류·source·결과 필드가 승인 계약과 연결된다.
- [x] mock·fixture 변경이 정답을 편의상 바꾸지 않는다.
- [x] TASK-002 범위의 오류·source·결과 필드를 승인 계약과 연결했다.
- [x] TASK-002는 fixture 정답을 변경하지 않고 example을 round-trip했다.
- [x] TASK-003 source·provider·attempt·오류 필드를 승인 요구사항과 연결했다.
- [x] TASK-003 test double은 fixture 정답을 변경하지 않았다.
- [x] TASK-001 dependency의 라이선스·공식 배포·취약점 점검 근거를 기록했다.
- [x] TASK-002 Pydantic dependency의 라이선스·취약점 점검 근거를 기록했다.
- [x] TASK-003 HTTPX dependency의 라이선스·취약점 점검 근거를 기록했다.
- [x] TASK-004가 새 dependency 없이 Python·SQLite 표준 API만 사용함을 확인했다.
- [x] TASK-005가 새 dependency 없이 기존 Typer·Pydantic·stdlib을 사용함을 확인했다.
- [x] TASK-006이 승인된 `eth-abi`·`eth-utils`만 추가하고 lockfile로 고정했다.
- [x] TASK-007이 기존 `eth-abi`·`eth-utils`를 재사용하고 dependency·lockfile을 변경하지 않았다.
- [x] TASK-008이 기존 `eth-abi`·`eth-utils`를 재사용하고 dependency·lockfile을 변경하지 않았다.
- [x] TASK-001 직접 구현 범위가 `OSS-*` 결정과 일치한다.
- [x] TASK-003 구현이 `TD-013`·`TD-014`의 adapter/orchestration 분리와 일치한다.
- [x] TASK-001~008 추적 파일에서 secret·`.scan/`·로컬 DB가 0건임을 확인했다.
- [x] UI 동작 변경 시 HTML Preview·UI 문서·피드백을 동기화한다.
- [x] TASK-003은 UI 동작을 변경하지 않고 기존 retry/fallback 표시 계약을 유지했다.
- [x] TASK-004는 UI 동작을 변경하지 않고 기존 cache/resume/export 표시 계약을 유지했다.
- [x] TASK-005 실제 help·snapshot과 Preview의 의도된 차이를 FB-002로 기록했다.
- [x] TASK-006 `--evidence` offline replay와 DEX complete·partial 출력을 UI 문서에 동기화했다.
- [x] TASK-007 AUTH complete·partial·resume과 `SCOPE / NOT ASSESSED` 출력을 UI 문서에 동기화했다.
- [x] TASK-008 FREEZE complete·partial·resume과 온체인 상태·공식 맥락 분리 출력을 UI 문서에 동기화했다.

### 7.3 대회 직전

- [ ] 공식 Rules의 최신 조회 시각과 변경 이력을 확인한다.
- [ ] API·자동화·AI·사전 제작 도구·fixture·cache 상태가 `allowed`인지 확인한다.
- [ ] `unclear` 항목은 공식 문의 또는 보수적 비활성화로 처리한다.
- [ ] API key·rate limit·fallback·offline cache를 점검한다.
- [ ] 정답·증거 제출 형식에 export를 맞춘다.
- [ ] 팀 장비에서 clean install과 confirmed fixture 회귀를 실행한다.
- [ ] CTFd 계정·팀·시간대·본인 확인 상태를 점검한다.
- [ ] Operations Board의 problem·worker·verification·submission Queue를 모의 실행한다.
- [ ] 사람 제출자와 `Mark submitted` 운영 책임을 확인한다.
- [ ] AI·agent가 비활성화되어도 Python CLI로 핵심 문제를 풀 수 있다.

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

`TASK-001`의 실행 환경·dependency·명령·결과는
[Bootstrap 검증 보고서](./05_TASK_001_BOOTSTRAP_REPORT.md)에 기록한다.
`TASK-002`의 model·runtime 불변조건·Schema 의미 probe·dependency 결과는
[Contract 검증 보고서](./06_TASK_002_CONTRACT_REPORT.md)에 기록한다.
`TASK-003`의 HTTPX dependency·policy·retry·fallback·secret 결과는
[Source 검증 보고서](./07_TASK_003_SOURCE_REPORT.md)에 기록한다.
`TASK-004`의 SQLite·cache·checkpoint·artifact·export·backup 결과는
[Storage 검증 보고서](./08_TASK_004_STORAGE_REPORT.md)에 기록한다.
`TASK-005`의 command·renderer·exit code·CLI security 결과는
[CLI 검증 보고서](./09_TASK_005_CLI_REPORT.md)에 기록한다.
`TASK-006`의 raw decode·정합·partial·resume·DEX security 결과는
[DEX 검증 보고서](./10_TASK_006_DEX_REPORT.md)에 기록한다.
`TASK-007`의 권한 소비·귀속 경계·partial·resume·AUTH security 결과는
[AUTH 검증 보고서](./11_TASK_007_AUTH_REPORT.md)에 기록한다.
`TASK-008`의 상태 전이·공식 맥락·partial·resume·FREEZE security 결과는
[FREEZE 검증 보고서](./12_TASK_008_FREEZE_REPORT.md)에 기록한다.

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

- [x] 사용자가 Checklist와 24개 QA 시나리오 범위를 승인했다.
- [x] Document Completion Gate를 닫고 구현 착수는 별도 승인으로 분리했다.
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
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - `TASK-010` 화면·상태·수동 제출 기준
- **UI_Screens**: [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - `TASK-010` UI-First Gate
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 구현·테스트·보안 기준
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source 능력·제약
- **Technical_Specs**: [SQLite 논리 DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md) - 저장·artifact·mutation 논리 계약
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - acceptance·오류·source 계약
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - request·result·error 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - dependency·재사용·직접 구현 검증 Gate
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - 역할·Queue·격리·독립 검증·수동 제출 요구사항
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - DOC-M3와 구현 분리 Gate
- **Logic_Progress**: [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK별 책임과 Preconditions
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - 24개 상세 검증 절차
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed 3·Deferred 5 처리 방침
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - 기존 24개와 분리된 `TASK-010` 6개 QA
- **QA_Validation**: [Document Completion Report](./04_DOCUMENT_COMPLETION_REPORT.md) - DOC-M5 문서 검증 결과
- **QA_Validation**: [TASK-001 Bootstrap 보고서](./05_TASK_001_BOOTSTRAP_REPORT.md) - Python project·dependency·Project Gate 증거
- **QA_Validation**: [TASK-002 Contract 보고서](./06_TASK_002_CONTRACT_REPORT.md) - Pydantic model·runtime 불변조건·Contract Gate 증거
- **QA_Validation**: [TASK-003 Source 보고서](./07_TASK_003_SOURCE_REPORT.md) - HTTPX·policy·retry·fallback·TASK-003 source 범위 증거
- **QA_Validation**: [TASK-004 Storage 보고서](./08_TASK_004_STORAGE_REPORT.md) - SQLite·cache·checkpoint·artifact·export·storage security 증거
- **QA_Validation**: [TASK-005 CLI 보고서](./09_TASK_005_CLI_REPORT.md) - 네 명령·renderer·exit code·CLI security 증거
- **QA_Validation**: [TASK-006 DEX 보고서](./10_TASK_006_DEX_REPORT.md) - raw decode·정합·partial·resume·DEX security 증거
- **QA_Validation**: [TASK-007 AUTH 보고서](./11_TASK_007_AUTH_REPORT.md) - exact 정합·실패 TX·scope·partial·resume·AUTH security 증거
- **QA_Validation**: [TASK-008 FREEZE 보고서](./12_TASK_008_FREEZE_REPORT.md) - 상태 전이·공식 맥락·scope·partial·resume·FREEZE security 증거
