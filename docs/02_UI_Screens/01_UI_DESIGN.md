# SCAN 2026 CLI Terminal UI Design
> Created: 2026-07-26 15:31
> Last Updated: 2026-07-27 00:54
> Status: Draft 1 · UI-First Gate Passed

## 1. 문서 목적

이 문서는 SCAN CLI의 terminal 화면 구성, 정보 계층, 상태 표현, 접근성 규칙을
정의한다. 결과의 정확성과 증거 추적성을 유지하면서 해커톤 중 빠르게 읽고 다음
행동을 결정할 수 있게 하는 것이 목적이다.

HTML Preview는 실제 웹 제품이 아니라 terminal 출력을 브라우저에서 검토하기
위한 커뮤니케이션 산출물이다.

## 2. 디자인 원칙

### 2.1 Evidence first

핵심 결과는 항상 자산·raw 값·분류·증거 수와 함께 표시한다. 사람이 읽는
표시값만 보여주거나 근거 없는 결론 문구를 먼저 보여주지 않는다.

### 2.2 상태를 숨기지 않음

cache, retry, fallback, resume, partial, warning을 성공 화면 아래에 숨기지
않는다. 사용자가 결과 신뢰도를 판단하는 데 필요한 실행 상태로 취급한다.

### 2.3 색상은 보조 수단

모든 상태는 색상과 함께 대문자 label과 기호를 사용한다.

| 상태 | label | 기호 | 의미 |
|:---|:---|:---:|:---|
| 시작 | `STARTING` | `>` | 명령 접수 |
| 진행 | `RUNNING` | `·` | 정상 실행 |
| 캐시 | `CACHE HIT` | `=` | 저장 응답 사용 |
| 재시도 | `RETRY 1/3` | `~` | 같은 source 재시도 |
| 대체 | `FALLBACK` | `>` | 다른 source 사용 |
| 완료 | `COMPLETE` | `OK` | 필수 결과 충족 |
| 부분 | `PARTIAL` | `!` | 일부 결과만 입증 |
| 실패 | `FAILED` | `X` | 분석 완료 조건 미충족 |
| 미평가 | `NOT ASSESSED` | `-` | 도구 판정 범위 밖 |

Unicode 기호에 의존하지 않고 ASCII만으로도 같은 의미가 전달되어야 한다.

### 2.4 한 화면에서 다음 행동까지

오류 화면은 원인만 표시하지 않는다. 수정할 파일, 재개 명령, 확인할 규정처럼
사용자가 바로 수행할 한 가지 다음 행동을 마지막 줄에 표시한다.

## 3. 화면 골격

```text
SCAN / ANALYZE
[STATUS] analysis_id · analysis_type · chain

INPUT
  request        requests/dex.json
  mode           offline
  rule           unconfirmed

PROGRESS
  stage          ...

CONFIRMED RESULTS
  ...

SCOPE / WARNINGS / ERRORS
  ...

RUN
  cache 2 hit · retry 0 · fallback 0 · resumed no

EXPORTS
  JSON           .scan/runs/.../result.json
  Markdown       .scan/runs/.../evidence.md

NEXT
  ...
```

빈 섹션은 complete 결과에서 생략할 수 있다. 단, AUTH와 FREEZE의
`NOT ASSESSED` 범위는 빈 경고가 아니라 분석 경계이므로 항상 표시한다.

## 4. 정보 계층

### 4.1 첫 번째 시선

- 최종 상태
- analysis ID
- 분석 유형
- 실행 모드: offline·live

### 4.2 두 번째 시선

- 핵심 confirmed result
- partial에서 확보된 결과 수와 누락 요구사항
- failed에서 첫 번째 오류 코드

### 4.3 세 번째 시선

- source, evidence, run 통계
- export 경로
- next action

## 5. Typography와 폭

- 실제 CLI는 사용자의 terminal monospace font를 그대로 사용한다.
- HTML Preview는 system monospace stack을 사용하며 외부 font를 다운로드하지
  않는다.
- label column은 16자 안팎으로 맞추고 값은 왼쪽 정렬한다.
- 80 columns 이하에서는 표를 key-value list로 전환한다.
- 주소·TX hash는 화면에서 `0x12345678…90abcdef`로 축약할 수 있다.
- JSON·Markdown export에는 항상 전체 값을 저장한다.
- raw uint256은 줄바꿈하더라도 자릿수를 변경하거나 지수 표기로 바꾸지 않는다.

## 6. 색상 토큰

실제 구현에서는 terminal의 기본 배경을 존중한다. 아래 색상은 HTML Preview와
색상 지원 terminal의 의미 토큰이다.

| 토큰 | Preview 색상 | 용도 |
|:---|:---|:---|
| `fg` | `#d8dee9` | 기본 텍스트 |
| `muted` | `#8390a5` | 보조 설명 |
| `accent` | `#6ea8fe` | analysis ID·link·진행 |
| `success` | `#54d19a` | complete·confirmed |
| `warning` | `#f2c14e` | partial·retry·warning |
| `danger` | `#ff6b7a` | failed·restricted |
| `context` | `#b69cff` | external context·not assessed |
| `border` | `#293449` | section 구분 |

색상을 끄면 label과 섹션명이 동일한 구분을 제공해야 한다.

## 7. 상태 화면 명세

### 7.1 Starting

```text
> STARTING  AN-FX-SVC-DEX-001 · dex_swap · chain 1
  request   requests/dex.json
  mode      offline · rule unconfirmed
```

- spinner만 표시하지 않는다.
- analysis ID와 실행 모드를 첫 피드백에 포함한다.
- 요청 검증 전이면 민감하지 않은 파일명만 표시한다.

### 7.2 Running

```text
· RUNNING   collect.receipt   DS-EVM-RPC-PUBLIC   CACHE HIT
· RUNNING   reconcile.swap    3/4 evidence groups
```

- stage 이름은 `verb.object` 형식의 안정된 식별자로 표시한다.
- 진행률을 알 수 없는 외부 조회에 거짓 백분율을 사용하지 않는다.
- 병렬 조회는 완료된 단위와 현재 source를 요약한다.

### 7.3 Retry

```text
~ RETRY 2/3 DS-EVM-RPC-ARCHIVE · timeout · next 1.6s
```

- 현재 시도와 최대 시도를 모두 표시한다.
- secret이 포함될 수 있는 endpoint 전체 URL은 표시하지 않는다.
- `Retry-After` 사용 여부는 verbose log 또는 run record에 남긴다.

### 7.4 Fallback

```text
> FALLBACK  DS-EXPLORER-EVM:blockscout-v2
            -> DS-EXPLORER-EVM:blockscout-compat
```

같은 source ID 안의 공급자 변경도 provider ID로 구분한다.

### 7.5 Complete

```text
OK COMPLETE AN-FX-SVC-DEX-001 · dex_swap

CONFIRMED RESULTS
asset_in         USDC  25000000000 raw
pool_output      WETH  14449515027026387018 raw
user_net_output  ETH   14449515027026387018 raw

RUN              cache 2 · retry 0 · fallback 0 · resumed no
JSON             .scan/runs/AN-FX-SVC-DEX-001/result.json
Markdown         .scan/runs/AN-FX-SVC-DEX-001/evidence.md
```

`pool_output`과 `user_net_output`은 같은 raw 값이어도 합치지 않는다.

### 7.6 Partial

```text
! PARTIAL AN-FX-EVM-AUTH-001 · auth_consumption

CONFIRMED
approval         approve · uint256.max

MISSING
allowance        before/after consumption state

ERROR
archive_required stage=collect.state attempts=2

NEXT
scan resume AN-FX-EVM-AUTH-001
```

partial에서는 성공한 결과를 먼저 보여주되 `PARTIAL` label을 화면 최상단에서
유지한다.

구현 시(FB-001): Preview처럼 전체 retry·fallback 이력을 최종 화면에 모두
남기지 않는다. 상세 시도는 stderr 진행 출력에 두고, 최종 stdout의 RUN 요약은
`retry N · fallback N`과 첫 오류 code만 유지한다.

### 7.7 Failed

```text
X FAILED AN-20260726-FREEZE-002 · address_freeze

ERROR
rule_restricted  stage=policy
Network calls were not started.

NEXT
Confirm the official rule and update source_policy.rule_status.
```

규정 차단은 보안 실패처럼 보이게 하지 않고 실행 전 정책 차단임을 설명한다.

## 8. 분석 유형별 표현

### 8.1 DEX

| 결과 | 표시 label | 필수 구분 |
|:---|:---|:---|
| 입력 | `asset_in` | token·raw |
| 풀 출력 | `pool_output` | WETH |
| 사용자 출력 | `user_net_output` | native ETH |

### 8.2 AUTH

| 결과 | 표시 label | 필수 구분 |
|:---|:---|:---|
| 승인 | `approval` | owner·spender·raw |
| 허용량 | `allowance_lifecycle` | 네 상태와 감소량 |
| 소비 | `authorization_consumption` | 성공 TX와 실패 TX 제외 |
| 귀속 | `theft_or_phishing` | `NOT ASSESSED` |

`victim`, `theft detected` 같은 문구는 별도 근거 없이 사용하지 않는다.

### 8.3 FREEZE

| 결과 | 표시 label | 필수 구분 |
|:---|:---|:---|
| 설정 | `blacklist_transition` | false → true |
| 해제 | `unblacklist_transition` | true → false |
| 공식 맥락 | `official_context` | external context |
| 현재 제재·범죄 | `sanctions / criminal intent` | `NOT ASSESSED` |

## 9. Warning·error 문구

문구는 다음 구조를 사용한다.

```text
<code> · <stage>
<무엇이 확인되지 않았는지>
Impact: <어떤 결과가 complete가 될 수 없는지>
Next: <사용자 행동>
```

- 공급자 내부 stack trace를 기본 화면에 노출하지 않는다.
- “Unknown error”만 표시하지 않는다.
- 자동으로 복구할 수 없는 오류에 `retrying`을 표시하지 않는다.
- `not_assessed`를 warning이나 failed로 오해하게 만들지 않는다.

## 10. 상호작용과 키보드

V1 CLI는 비대화형 실행을 기본으로 하므로 실행 중 필수 키 입력을 요구하지 않는다.

- `Ctrl-C`: 현재 요청을 중단하고 가능한 경우 checkpoint 저장
- terminal text selection·copy: 기본 동작 보존
- 파일 열기: 경로를 출력하되 특정 editor를 자동 실행하지 않음
- 확인 prompt: destructive cache 삭제 같은 향후 관리 명령에서만 검토

## 11. 접근성·호환성

- `NO_COLOR`를 지원한다.
- 상태를 색상만으로 전달하지 않는다.
- screen reader와 log parser가 읽도록 상태 한 줄의 순서를 안정적으로 유지한다.
- spinner와 carriage return을 사용할 때 `CI`·non-TTY에서는 줄 단위 log로
  전환한다.
- terminal hyperlink escape sequence는 선택 기능이며 일반 경로 문자열을
  대체하지 않는다.
- 한국어 설명과 영문 error code를 함께 사용할 수 있지만 machine key는
  영문 Schema 값으로 유지한다.

## 12. HTML Preview 범위

[HTML Terminal Preview](./previews/01_cli_terminal_preview.html)는 다음 상태를
버튼으로 전환한다.

- DEX complete
- AUTH partial + retry
- FREEZE failed + rule restriction
- Resume complete
- Help·empty entry

Preview의 버튼은 구현 API가 아니라 검토 편의를 위한 상태 전환 장치다. Preview에
표시된 수치 중 DEX·AUTH의 기준값은 confirmed Analysis I/O 예제를 사용한다.

## 13. UI Design Gate

- [x] 정보 계층 정의
- [x] complete·partial·failed 시각 구분
- [x] loading·retry·fallback·resume 표현
- [x] 색상 비의존 label
- [x] 80 columns 대응 규칙
- [x] raw 값·표시값 구분
- [x] secret·경로 redaction 규칙
- [x] HTML Preview 연결
- [x] 사용자 preview 확인
- [x] 피드백 반영

이 Gate는 CLI V1에만 적용된다. 별도
[Web Workbench Preview](./previews/02_investigation_workbench_preview.html)는
시연 UX 탐색용 Draft이며 현재 Gate의 통과 상태나 Backlog 선행 조건을 바꾸지
않는다.

## 14. Web Workbench 시각 언어 경계

Web Workbench는 CLI와 같은 Analysis I/O 값을 다른 의미로 표현하지 않는다.
화면 공간이 넓어져도 확정 사실·외부 맥락·휴리스틱·미평가를 합치지 않는다.

| 분류 | 화면 label | 시각 표현 | 금지 |
|:---|:---|:---|:---|
| `confirmed_fact` | `CONFIRMED` | 실선·명시적 근거 수 | 범죄·귀속 의미 추가 |
| `external_context` | `CONTEXT` | 보라 계열·출처명 | 온체인 사실로 병합 |
| `heuristic` | `HEURISTIC` | 점선·score·반례 | 확정 경로처럼 표시 |
| `not_assessed` | `NOT ASSESSED` | 중립색·범위 설명 | 정상·무관으로 오해 |
| partial missing | `MISSING` | 경고색·영향·다음 행동 | 빈 값으로 숨김 |

그래프 edge를 선택하면 Evidence Inspector가 `evidence_id`, `source_id`,
method, block, TX·log·trace locator와 raw artifact 위치를 표시한다. 화면에서
계산한 별도 금액이나 라벨을 Analysis I/O 결과처럼 보여주지 않는다.

Challenge Preview의 노드 수는 UI 검토를 위한 축약 표현이다. “수백 주소·수천
TX 처리 완료”라는 성능 주장을 하지 않으며 실제 fixture·측정 전에는 규모
수치를 제품 성능으로 표시하지 않는다.

## 15. Competition Operations Board 시각 언어

Operations Board는 여러 문제의 진행 상태와 worker 부하를 보여주지만,
Workbench와 CLI의 사실 분류 의미를 변경하지 않는다.

| 운영 객체 | 첫 표시 | 두 번째 표시 | 금지 |
|:---|:---|:---|:---|
| Problem | ID·score·status | role·progress·age | confidence만으로 ready |
| Worker | role·job·stage | source·runtime·queue | AI 여부 숨김 |
| Verification | pass·missing·conflict | evidence refs·다음 행동 | self-check를 independent로 표시 |
| Candidate | 전체 answer·format | uncertainty·recommendation | 자동 제출처럼 보이는 CTA |
| Rules | allowed·restricted·unclear | rule ID·fallback | unclear를 enabled로 표시 |
| Source | health·limit | retry·cache·fallback | 실패를 조용히 숨김 |

`SUBMISSION READY`는 독립 검증을 통과한 운영 상태이고 `SUBMITTED`는 사람이
CTFd 제출을 완료했다고 기록한 상태다. 두 상태를 색상만으로 구분하지 않는다.

Operations Board Preview의 처리량·남은 시간·confidence는 UX 검토용 demo
data다. 실제 측정이나 대회 상태로 주장하지 않는다.

## 16. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - V1 사용자 가치
- **UI_Screens**: [CLI Screen Flow](./00_SCREEN_FLOW.md) - 명령과 상태 전환
- **UI_Screens**: [CLI Prototype Review](./02_CLI_PROTOTYPE_REVIEW.md) - 확인 결과와 피드백
- **UI_Screens**: [Web Investigation Workbench](./03_WEB_INVESTIGATION_WORKBENCH.md) - 선택적 시연 UX 구조와 승격 조건
- **UI_Screens**: [Competition Operations Board](./04_COMPETITION_OPERATIONS_BOARD.md) - 문제·worker·검증·제출 Queue 화면
- **UI_Screens**: [HTML Terminal Preview](./previews/01_cli_terminal_preview.html) - 상태별 화면
- **UI_Screens**: [HTML Workbench Preview](./previews/02_investigation_workbench_preview.html) - read-only 조사 화면 Draft
- **UI_Screens**: [Operations Board Preview](./previews/03_competition_operations_board_preview.html) - 병렬 운영 UI Draft
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - 운영 상태와 역할 규범
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - stdout·stderr·보안 원칙
- **Technical_Specs**: [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 화면 데이터의 source of truth
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - renderer·CLI 구현 책임
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - exact-match 기준
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - terminal·접근성·출력 채널 기준
