# TASK-007 AUTH Vertical Slice 검증 보고서
> Created: 2026-07-28 01:34
> Last Updated: 2026-07-28 01:34
> Status: TASK-007 Scope Passed · Offline Raw Replay Only

## 1. 판정

TASK-007 AUTH vertical slice는 통과했다. confirmed Ethereum 공개 사례의
Approval event, approve calldata, historical allowance, 성공 transferFrom
trace와 Transfer event를 독립 디코딩해 Analysis I/O Schema `0.1` 결과로
재현한다. 범죄·피싱·피해 귀속은 판정하지 않는다.

| 결과 ID | 상태 | 핵심 값 |
|:---|:---:|:---|
| `RES-AUTH-APPROVAL` | confirmed | `approve`, `uint256.max` |
| `RES-AUTH-ALLOWANCE` | confirmed | `0 → max → max → max-4500000` |
| `RES-AUTH-CONSUMPTION` | confirmed | USDC `4500000` raw |
| `RES-AUTH-ATTRIBUTION` | not_assessed | `theft_or_phishing_claim=false` |

live RPC·탐색기 endpoint, private key, CTFd, AI 기능은 추가하지 않았다.

## 2. 구현 범위

| 영역 | 구현 |
|:---|:---|
| Raw contract | strict Pydantic transaction·receipt·log·trace·state·cross-check |
| Decode | `approve`, `Approval`, `allowance`, `transferFrom`, `Transfer` |
| Reconciliation | owner·spender·token·block·amount·allowance delta 양방향 정합 |
| Failed TX | nonce 327~329, receipt status 0을 소비에서 제외하고 context 보존 |
| Evidence | event·call·state·context와 scoring·supporting source 분리 |
| Result | complete·partial·failed와 result→evidence→source 참조 무결성 |
| CLI | reviewed `--evidence`, terminal `SCOPE / NOT ASSESSED`, stable exit code |
| Persistence | content-addressed raw artifact·checkpoint·JSON·Markdown·resume |

## 3. Raw evidence와 재확인

승인 TX는
`0x3f7037014b8709f02bf2032d70ce4ec6854a53ed141b63d6a7ea359a9dccdabd`,
소비 TX는
`0x7b888fbf7ee76c99ec1e1a31d8bc1d43806f7f5e7fcfd4121a6a21a768e9af51`다.

read-only 검증에서 다음을 확인했다.

- Approval owner·spender와 `uint256.max`가 approve calldata와 일치
- allowance block 24500452·24500453·24500504·24500505가
  `0 → max → max → max-4500000`
- trace address `[0,0,2,0]`의 Router→USDC `transferFrom`
- Transfer log index 363과 allowance delta가 `4500000` raw
- 중간 거래 세 건의 nonce `327`, `328`, `329`와 receipt status `0`
- Blockscout transaction·Transfer 교차 확인과 pinned SwapRouter02 metadata

원시 값은
[`raw-replay.json`](./fixtures/FX-EVM-AUTH-001/raw-replay.json)에 보존한다.
분석기는 이 reviewed artifact만 읽으며 네트워크를 호출하지 않는다.

## 4. 상태·오류 검증

| 조건 | 상태 | 오류 | 종료 코드 |
|:---|:---:|:---|:---:|
| 모든 raw 증거 정합 | complete | 없음 | `0` |
| allowance state 누락 | partial | `archive_required` | `3` |
| transferFrom trace 누락 | partial | `trace_unavailable` | `3` |
| raw 값·성공 상태 불일치 | failed | `reconciliation_failed` | `4` |
| source policy 위반 | failed | `rule_restricted` | `5` |
| raw replay Schema 위반 | failed | `decode_failed` | `4` |

partial은 입증된 Approval과 가용 evidence를 보존하되 권한 소비를 확정 결과로
승격하지 않는다. malformed 입력은 저장 전에 차단하고 원문·전체 경로·secret을
오류에 반사하지 않는다.

## 5. 자동 검증

```bash
.venv/bin/python scripts/verify.py
.venv/bin/python -m pip check
```

최종 기준:

```text
All checks passed!
101 passed
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
No broken Markdown links
```

TASK-007은 직접 dependency와 `uv.lock`을 변경하지 않는다.

## 6. 핵심 회귀 테스트

- approval·allowance 네 지점·소비·실패 거래·scope exact match
- state 두 지점 누락과 trace 누락의 서로 다른 partial
- transferFrom 수량 1 raw 변경과 성공 실패거래 주입의 complete 거부
- restricted archive source의 선행 차단
- malformed canary secret·전체 경로 비노출 및 미저장
- 중단 후 immutable artifact checkpoint resume complete
- terminal·JSON·Markdown의 결과·scope 일치

## 7. Code Review

| 영역 | 판정 | 근거 |
|:---|:---:|:---|
| 정확성 | Pass | event·call·state·trace·delta 양방향 정합 |
| 타입 안전성 | Pass | strict Pydantic raw contract와 uint256 Python int |
| 책임 분리 | Pass | domain·slice·CLI runtime·storage 분리 |
| YAGNI/KISS/DRY | Pass | 한 confirmed AUTH 경로만, 범용 attribution 미구현 |
| 오류 보존 | Pass | partial·failed evidence와 source 보존 |
| Schema | Pass | 공개 Analysis I/O `0.1` 변경 없음 |

## 8. Security Review

| 점검 | 판정 | 근거 |
|:---|:---:|:---|
| Secret·경로 | Pass | canary·절대 경로 stdout·stderr·오류 0건 |
| 입력 검증 | Pass | strict 검증 후 artifact·checkpoint 저장 |
| 외부 동작 | Pass | offline read-only, live provider 구성 없음 |
| 저장 | Pass | 기존 parameter binding·SHA-256 artifact 재사용 |
| 민감 기능 | Pass | private key·서명·자동 제출 없음 |
| 귀속 과장 | Pass | theft/phishing `not_assessed`, claim `false` |

## 9. 365 글로벌 평가 기준

| 기준 | 상태 | 증거 |
|:---|:---:|:---|
| Functionality | Pass | raw decode·exact 정합·partial·resume·101 tests |
| Potential Impact | Pass | 승인 권한 소비 조사에 재사용 가능한 증거 계약 |
| Novelty | Pass | 권한 소비 사실과 범죄 귀속을 명시적으로 분리 |
| UX | Pass | confirmed 결과와 `SCOPE / NOT ASSESSED` 분리 |
| Open-source | Pass | MIT 코드·fixture·Schema·재현 명령 |
| Business Plan | N/A | 대회 준비용 vertical slice |

## 10. Originality & Ethics Check

- 공개 ABI와 raw evidence로 작은 decoder를 직접 구현했다.
- fixture expected JSON을 결과로 복사하지 않고 raw calldata·log·state·trace를
  매번 디코딩한다.
- 승인·소비 사실을 피싱·탈취·피해 사실로 확대 해석하지 않는다.
- 규정 미확정 live 자동화·AI·CTFd 제출을 활성화하지 않는다.

## 11. Known Issues와 다음 작업

- 한 confirmed USDC approve→SwapRouter02 transferFrom 사례만 지원한다.
- permit, Permit2, proxy approval, 일반 spender discovery는 범위 밖이다.
- live provider는 Rules·source plan 승인 전 비활성이다.
- 다음 구현은 별도 승인 후 `TASK-008` FREEZE vertical slice다.

## 12. Related Documents

- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - AUTH complete·partial·resume 동선
- **UI_Screens**: [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - confirmed·scope 표시
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - decoder·보안·dependency 원칙
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - public·archive·trace·explorer 경계
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 결과·증거·오류 계약
- **Logic_Progress**: [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-007 완료 조건과 TASK-008 경계
- **QA_Validation**: [AUTH fixture](./fixtures/FX-EVM-AUTH-001/README.md) - confirmed 사례·정답·raw replay
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - AUTH·CLI·보안 판정
- **QA_Validation**: [TASK-006 DEX 보고서](./10_TASK_006_DEX_REPORT.md) - 선행 vertical slice 기준선
