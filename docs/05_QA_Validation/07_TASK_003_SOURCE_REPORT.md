# TASK-003 Source Orchestration 검증 보고서
> Created: 2026-07-27 21:50
> Last Updated: 2026-07-27 21:50
> Status: TASK-003 Scope Passed · QA-RETRY/FALLBACK Pass · QA-RULE/SOURCE Partial

## 1. 판정

`TASK-003`의 source port, HTTPX JSON-RPC·REST adapter, rules/offline policy,
retry와 fallback orchestration은 승인된 TASK-003 범위를 통과했다. 모든 자동
검증은 HTTPX `MockTransport`와 scripted adapter로 실행했으며 실제
RPC·탐색기·공식 URL에는 연결하지 않았다. TASK-004·005에 걸친 QA 두 개는
`partial`로 남겼다.

| 항목 | 결과 |
|:---|:---|
| 기준 code commits | `aaf6a02`, `483819e` |
| branch | `codex/task-003-source-orchestration` |
| Python | `3.13.7` |
| HTTPX | `0.28.1` |
| Analysis I/O Schema | `0.1` 유지 |
| QA | retry/fallback 2 pass, rule/source 2 partial |

SQLite cache·checkpoint·artifact·export와 CLI renderer, DEX/AUTH/FREEZE
분석기는 구현하지 않았다. live provider endpoint·API key·정확한 rate limit도
구성하지 않았다.

## 2. 구현 경계

| 영역 | 구현 |
|:---|:---|
| Domain | provider-independent JSON-RPC·REST request, payload, attempt, response, safe error |
| Port | 한 번의 read attempt만 수행하는 `SourceAdapter` Protocol |
| Adapter | 주입된 `httpx.AsyncClient`와 source별 timeout을 쓰는 JSON-RPC·REST 구현 |
| Policy | allowed source/order, fallback, offline, rules 상태 사전 검사 |
| Retry | 최초 1회+retry 2회, 0.5초 지수 backoff+jitter, `Retry-After` 우선 |
| Fallback | primary 실패와 secondary 성공 attempt·provider를 모두 보존 |
| Provenance | request fingerprint, raw SHA-256, source/provider, 시각, status, delay |

구현 위치:

- `src/scan_tool/domain/source.py`
- `src/scan_tool/ports/source.py`
- `src/scan_tool/adapters/http.py`
- `src/scan_tool/application/source_orchestration.py`
- `tests/unit/test_source_orchestration.py`
- `tests/integration/test_http_source_adapters.py`

adapter는 retry와 fallback을 수행하지 않는다. application orchestration만
정책 순서와 모든 attempt를 관리하며, injected client의 lifecycle도 소유하지
않는다.

## 3. 규정·offline Gate

| 입력 정책 | transport 호출 | 구조화 결과 |
|:---|---:|:---|
| `rule_status: restricted` | 0 | `rule_restricted`, stage=`source_policy` |
| `rule_status: unconfirmed`, live | 0 | `rule_restricted`, stage=`source_policy` |
| `offline_mode: true` | 0 | `source_unavailable`, stage=`source_transport`, retryable=false |
| `rule_status: allowed`, live | 허용된 source만 | retry/fallback 규칙 적용 |

`unconfirmed`는 유효한 Analysis Request 값이지만 live 호출 권한으로 해석하지
않는다. 이 보수적 실행 정책은 공식 Rules가 아직 `unclear`인 현재 저장소
기준선과 일치한다. `QA-RULE-001`의 process exit code 5는 TASK-005,
`QA-SOURCE-001`의 cache·partial 분기는 TASK-004에서 재검증하므로 두
시나리오의 전체 상태는 현재 `partial`이다.

## 4. Retry·fallback 판정

| 오류 | 자동 retry | 검증 |
|:---|:---:|:---|
| HTTPX timeout | 예 | 제한된 attempt와 backoff 기록 |
| HTTP 429 | 예 | 숫자 `Retry-After` 우선 |
| HTTP 500·502·503·504 | 예 | transient로 분류 |
| HTTP 400·501 | 아니요 | 첫 attempt 후 source fallback 또는 실패 |
| malformed/invalid JSON-RPC | 아니요 | invalid response로 종료 |
| 기타 request error | 아니요 | source unavailable로 종료 |

provider 고유 JSON-RPC transient code는 공식 공급자 정의를 확인하기 전
추측으로 추가하지 않았다. fallback이 허용되면 primary의 실패 attempt를
지우지 않고 다음 source를 호출한다. fallback이 꺼져 있으면 두 번째 adapter의
call count는 0이다.

## 5. Secret·부작용 검증

- URL query의 canary API key는 payload·attempt·error repr에 없다.
- injected HTTP client의 Authorization header는 source 결과에 없다.
- timeout 예외의 원문·request URL을 구조화 오류에 복사하지 않는다.
- raw body는 SHA-256을 계산하지만 `SourcePayload` repr에는 표시하지 않는다.
- REST provenance path는 query·fragment를 거부하고 안전한 path만 보존한다.
- 테스트는 외부 네트워크, 사용자 credential, `.scan/`, DB, artifact를
  읽거나 변경하지 않는다.

raw artifact 영구 저장과 redaction은 `TASK-004` 범위다. 현재 source 계층은
성공 raw bytes를 호출자에게 반환하고 attempt에는 hash만 남긴다.

## 6. Dependency Gate

| package | version | 역할 | license |
|:---|:---:|:---|:---|
| `httpx` | `0.28.1` | async JSON-RPC·REST transport | BSD-3-Clause |
| `httpcore` | `1.0.9` | HTTPX transport core | BSD-3-Clause |
| `anyio` | `4.14.2` | async compatibility | MIT |
| `certifi` | `2026.7.22` | CA bundle | MPL-2.0 |
| `h11` | `0.16.0` | HTTP/1.1 protocol | MIT |
| `idna` | `3.18` | IDNA handling | BSD-3-Clause |

직접 dependency는 HTTPX 하나만 추가했다. HTTPX 1.0 pre-release나 별도 provider
SDK를 채택하지 않고 승인 기술 결정의 안정 버전 `0.28.1`을 lock했다.

`uv export --locked --no-hashes --no-emit-project` 결과를
`pip-audit --disable-pip --no-deps`로 조회한 결과는
`No known vulnerabilities found`였다. 일반 pip-audit 모드는 임시
가상환경의 `ensurepip`가 macOS `SIGABRT`로 종료되어, 완전 고정 목록을
재설치하지 않는 모드로 다시 확인했다.

## 7. 실행 증거

| 검증 | 결과 |
|:---|:---|
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass |
| `uv run pytest` | `47 passed` |
| fixture Schema validator | `PASS 3` |
| analysis Schema validator | `PASS 3` |
| generated Schema compatibility | `PASS 3`, 35 probes |
| Markdown link | 33 files, missing 0 |
| `git diff --check` | pass |

재현 명령:

```bash
uv sync --locked
uv run python scripts/verify.py
```

## 8. 코드 품질 검토

| 영역 | 판정 | 근거 |
|:---|:---:|:---|
| 로직 정확성 | Pass | policy→retry→fallback 순서와 오류별 attempt 검증 |
| 타입 안전성 | Pass | typed union·immutable dataclass·Protocol 사용 |
| YAGNI/KISS/DRY | Pass | JSON-RPC·REST 두 adapter와 현재 test boundary만 구현 |
| 중복·책임 | Pass | adapter=1회 I/O, orchestration=policy/retry/fallback 분리 |
| Side effect | Pass | 외부 network·DB·filesystem write 0 |
| 가독성 | Pass | retry 정책·transient status·safe error 명시 |
| 불필요 코드 | Pass | provider SDK·env·factory·unused option 없음 |
| UI-First | N/A | CLI 화면 구현 변경 없음, 기존 retry/fallback 상태 계약 유지 |

## 9. 365 글로벌 평가 기준

| 기준 | 상태 | TASK-003 증거 |
|:---|:---:|:---|
| Functionality | Pass | TASK-003 scope, 47 tests, retry/fallback pass, cross-task 2 partial |
| Potential Impact | Pass | RPC·REST와 test double이 공유하는 provider-independent port |
| Novelty | Pass | 실패 attempt를 지우지 않는 evidence-first fallback provenance |
| UX | Pass | retry 원인·attempt·wait·fallback을 renderer가 사용할 구조로 보존 |
| Open-source | Pass | HTTPX BSD-3, lockfile, 재현 명령, dependency audit |
| Business Plan | N/A | source 기반 구현 작업이며 수익 모델 범위가 아님 |

## 10. Originality & Ethics Check

- HTTPX 공개 API를 사용했으며 외부 포렌식 제품 코드를 복제하지 않았다.
- 실제 대회 문제·답안·개인정보를 외부 서비스에 전송하지 않았다.
- 규정이 미확정인 live API를 기본 허용으로 추정하지 않았다.
- API key·Authorization·원본 예외 URL을 결과와 오류에 남기지 않았다.
- 서명·거래 전송·자동 제출·brute force 기능을 추가하지 않았다.
- dependency license와 공식 package provenance를 보존했다.

## 11. 남은 경계

- `TASK-004`: SQLite cache·checkpoint·artifact·export와 attempt 영구 저장
- `TASK-005`: retry/fallback의 stdout·stderr renderer
- `TASK-006`~`TASK-008`: 실제 EVM source request와 분석 vertical slice
- provider별 rate limit·endpoint·credential: 공식 Rules·plan 확인 후 별도 구성
- live API·AI·agent·CTFd 자동 제출: Rules 확인과 별도 승인 전 비활성

## 12. Related Documents

- [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md)
- [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md)
- [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md)
- [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md)
- [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md)
- [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md)
- [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)
- [P0·V1 QA Checklist](./02_QA_CHECKLIST.md)
