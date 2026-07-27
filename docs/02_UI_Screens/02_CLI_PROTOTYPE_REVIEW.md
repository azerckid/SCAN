# SCAN 2026 CLI Prototype Review
> Created: 2026-07-26 15:31
> Last Updated: 2026-07-28 00:58
> Status: Approved 1.2 · UI-First Gate Passed · TASK-006 DEX Compared

## 1. HTML UI Preview

- Preview: [CLI Terminal Preview](./previews/01_cli_terminal_preview.html)
- 확인 방식: 브라우저에서 로컬 HTML 파일 열람
- 확인 목적: 명령 구조, 정보 계층, 상태별 화면, 다음 행동의 명확성 확인
- 구현 상태: TASK-005 CLI command·renderer 구현 및 Preview 대조 완료

Preview 왼쪽의 시나리오 버튼으로 다음 다섯 화면을 전환할 수 있다.

1. DEX complete
2. AUTH partial + retry·fallback
3. FREEZE failed + rule restriction
4. AUTH resume complete
5. Entry·help

## 2. 검토 대상 결정

| 결정 | Draft 1 제안 | 확인 상태 |
|:---|:---|:---:|
| canonical 명령 | `scan analyze --request PATH` | 승인 |
| 보조 명령 | `validate`, `resume`, `show`, `--help` | 승인 |
| 유형별 별칭 | V1 제외 | 승인 |
| 입력 방식 | Analysis Request Schema `0.1` JSON | 승인 |
| 진행 출력 | stderr | 승인 |
| 결과 요약·경로 | stdout | 승인 |
| 결과 source of truth | JSON | 기존 승인 |
| 사람용 증거 | Markdown | 기존 승인 |
| 종료 상태 | complete·partial·failed | 기존 승인 |
| 종료 코드 | 0·2·3·4·5·130 | 승인 |

## 3. Key User Flows

### 3.1 새 분석

```text
요청 작성
  -> scan validate request.json
  -> scan analyze --request request.json
  -> progress 확인
  -> complete·partial·failed 확인
  -> JSON·Markdown 검토
```

### 3.2 부분 성공 복구

```text
partial 결과와 확보 증거 확인
  -> 오류 code·source·stage 확인
  -> source 상태 또는 정책 확인
  -> scan resume ANALYSIS_ID
  -> 기존 cache·checkpoint 재사용
```

### 3.3 규정 차단

```text
rule_status: restricted
  -> Schema 검증
  -> 네트워크 호출 전 중단
  -> rule_restricted 표시
  -> 공식 규정 확인 전 자동 변경 없음
```

## 4. Screen States

| 상태 | Preview | 확인할 내용 |
|:---|:---:|:---|
| Default·help | 포함 | 첫 명령과 지원 유형을 찾을 수 있는가 |
| Starting | 포함 | 400ms 안에 표시할 정보가 충분한가 |
| Running | 포함 | 현재 stage·source·cache가 과하지 않은가 |
| Retry | 포함 | 현재/최대 시도와 원인이 명확한가 |
| Fallback | 포함 | 최초·대체 공급자가 모두 보이는가 |
| Complete | 포함 | 핵심 결과와 export가 한 화면에 보이는가 |
| Partial | 포함 | 확보 결과와 missing이 혼동되지 않는가 |
| Failed | 포함 | 원인·영향·다음 행동이 명확한가 |
| Resume | 포함 | 재사용·재시작 지점이 명확한가 |
| Result not found | 문서만 | 구현 QA에서 별도 확인 |
| Permission unavailable | 규정 차단으로 포함 | 네트워크 전 차단이 분명한가 |

## 5. Data Flow

### 5.1 Inputs

- Analysis Request Schema `0.1`
- request file path
- resume에서는 기존 analysis ID와 checkpoint
- secret은 환경 참조로만 주입되며 화면·export에 표시되지 않음

### 5.2 Displayed data

- analysis ID·type·chain·mode·rule status
- result classification·자산·raw 값
- evidence·source 수
- cache·retry·fallback·resume 통계
- 구조화 오류와 누락 요구사항
- JSON·Markdown artifact 경로

### 5.3 Mutations·saved data

- read-only 온체인·HTTP 조회만 수행
- local SQLite run·checkpoint·cache 기록
- raw artifact와 JSON·Markdown export 저장
- blockchain transaction·서명·외부 데이터 수정 없음

### 5.4 External dependencies

- 허용된 RPC·explorer·공식 URL source
- source policy와 공식 규정 Gate
- SQLite cache와 local artifact storage

## 6. 기준값 대조

| Preview 값 | 기준 문서 |
|:---|:---|
| DEX USDC input `25000000000` | `dex-result.json` |
| DEX WETH pool output `14449515027026387018` | `dex-result.json` |
| DEX native ETH user output `14449515027026387018` | `dex-result.json` |
| AUTH consumption·allowance delta `4500000` | `auth-result.json` |
| AUTH 탈취·피싱 `not_assessed` | `auth-result.json` |
| FREEZE current sanctions·criminal intent `not_assessed` | `freeze-result.json` |

Partial과 failed 시나리오는 UI 상태를 검토하기 위한 오류 주입 예다. confirmed
fixture가 실제로 실패했다는 의미가 아니다.

Preview의 `feedback 29ms·34ms·41ms`는 배치 위치와 형식을 확인하기 위한 예시
표시이며 실제 성능 측정값이 아니다. 구현 후 cold·warm benchmark로 교체한다.

## 7. 사용자 확인

- 화면/UI 선확인 여부: 확인
- HTML Preview 확인 여부: 확인
- 확인자: 사용자
- 확인 일시: 2026-07-26 16:33
- Gate 상태: UI-First Gate 통과
- 확인 URL: `http://127.0.0.1:8766/docs/02_UI_Screens/previews/01_cli_terminal_preview.html`

확인 항목 결과:

- [x] canonical 명령이 이해하기 쉬운가
- [x] complete에서 가장 먼저 봐야 할 값이 보이는가
- [x] partial이 complete로 오해되지 않는가
- [x] retry와 fallback 정보가 충분한가
- [x] error 다음 행동이 실행 가능하게 구체적인가
- [x] terminal 정보량이 과하거나 부족하지 않은가

## 8. Feedback & Improvements

| ID | 우선순위 | 피드백 | 결정 | 반영 위치 |
|:---|:---:|:---|:---|:---|
| FB-001 | Medium | AUTH partial Preview가 실행 중 retry·fallback 이력과 최종 요약을 한 프레임에 합쳐 빽빽해 보인다. Draft 화면은 유지하되, 구현 시 상세 retry는 stderr에만 남기고 최종 stdout RUN 요약은 `retry N · fallback N`으로 압축한다. | 채택 | [CLI Terminal UI Design](./01_UI_DESIGN.md) §7.6, 이후 backlog |
| FB-002 | Low | 실제 Typer `--help`는 TTY에서 frame을 사용하지만 Preview의 help는 plain text다. 명령·설명·종료 의미가 같고 non-TTY·무색상에서도 텍스트가 유지되므로 의도된 표현 차이로 수용한다. | 채택 | TASK-005 CLI snapshot·QA |

Draft Preview HTML은 Gate 확인용으로 변경하지 않는다. FB-001의 실제 구현
결과는 아래와 같이 별도 기록한다.

TASK-005에서 FB-001을 반영했다. 상세 retry·fallback event는 stderr에 남고
최종 stdout은 count와 첫 오류 code만 표시한다. TASK-006은 DEX confirmed
fixture의 세 raw 값을 실제 decoder 결과로 생성하고 complete·partial·failed·
resume 출력을 Preview와 대조했다. AUTH·FREEZE analyzer 미구현 요청은
TASK-007·008 전까지 종료 코드 `4`로 명시한다.

## 9. Gate 판정

### HTML UI Preview Gate

- [x] 주요 사용자 흐름 Preview 존재
- [x] Screen Flow·UI Design·Review 문서에서 상대 링크
- [x] complete·partial·failed·loading·retry·fallback 상태 포함
- [x] 사용자가 Preview를 직접 확인
- [x] 피드백과 보완 결과 기록

### UI-First Gate

- [x] 주요 화면 목적과 CTA 정의
- [x] 진입·전환·이탈 흐름 정의
- [x] 입력·출력·상태 변화 정의
- [x] 오류·규정 차단·resume 정의
- [x] 사용자 확인 기록

현재 판정은 **UI-First Gate 통과**이다. 승인된 Schema·CLI 경계를 원자적
backlog와 QA 시나리오 Draft로 전환했다. Python project 초기화는 두 Draft 승인
후 시작한다.

## 10. 365 글로벌 평가 기준

| 기준 | 상태 | Prototype 근거 |
|:---|:---:|:---|
| Functionality | Pass | 요청 검증부터 export·resume까지 흐름 정의 |
| Potential Impact | Pass | 공통 요청으로 분석 유형과 source 확장 가능 |
| Novelty | Pass | evidence·scope·not_assessed·partial 분리 |
| UX | Pass | Preview 사용자 확인 완료, 명령·상태·다음 행동 명확 |
| Open-source | Pass | 명령·상태·Schema·종료 코드 공개 가능 |
| Business Plan | N/A | 대회 준비용 CLI Preview |

## 11. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - V1 범위
- **UI_Screens**: [CLI Screen Flow](./00_SCREEN_FLOW.md) - 명령·상태 동선
- **UI_Screens**: [CLI Terminal UI Design](./01_UI_DESIGN.md) - 화면 구성 원칙
- **UI_Screens**: [HTML Terminal Preview](./previews/01_cli_terminal_preview.html) - 사용자 확인 대상
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - CLI 구현 경계
- **Technical_Specs**: [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 화면 데이터 계약
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - Preview를 구현으로 전환하는 작업 목록
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - UI-First Gate 회귀 기준
- **QA_Validation**: [분석 I/O 예제](../05_QA_Validation/examples/analysis/README.md) - confirmed 기준값
- **QA_Validation**: [TASK-005 CLI 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md) - 실제 help·출력·exit code 대조
- **QA_Validation**: [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - Preview 세 값·partial·resume 실제 대조
