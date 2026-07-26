# SCAN 2026 P0·V1 QA 시나리오
> Created: 2026-07-26 16:46
> Last Updated: 2026-07-27 00:54
> Status: Draft 1 · Approval Pending

## 1. 문서 목적

이 문서는 P0 공통 기반과 DEX·AUTH·FREEZE V1 구현을 승인된 요구사항,
Analysis I/O Schema `0.1`, CLI UI-First Gate, confirmed fixture 3개에 대조하는
실행 가능한 QA 기준을 정의한다.

현재는 구현 전 Draft다. 모든 시나리오는 backlog의 Acceptance Criteria를
구체화하지만 Python project나 테스트 코드를 생성하지 않는다.

현재 정의된 시나리오는 24개이며 승인 상태는 `Approval Pending`, 실행 상태는
`Not Executed`다. 구현 전·작업별·통합 실행 시점은
[QA Checklist](./02_QA_CHECKLIST.md)에서 관리한다.

병렬 문제풀이 `TASK-010`의 6개 시나리오는
[Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md)에 별도로
정의하며 이 문서의 24개 P0·V1 기준선에 합산하지 않는다.

## 2. QA 원칙

### 2.1 실행 모드

| 모드 | 기본 여부 | 목적 | 외부 네트워크 |
|:---|:---:|:---|:---:|
| `offline` | 기본 | 고정 응답·fixture·cache 기반 결정적 회귀 | 0회 |
| `fault-injection` | 기본 | timeout·429·5xx·손상 응답·중단 재현 | test double만 |
| `live` | 명시적 opt-in | source adapter의 현재 접근성과 provenance 확인 | 허용 |

- 일반 test suite는 `offline`과 `fault-injection`만 실행한다.
- `live`는 CI 필수 Gate가 아니며 API key·provider 상태로 fixture 정답을 바꾸지 않는다.
- destructive action, 서명, 거래 전송, private key 입력은 모든 모드에서 금지한다.
- 시간·provider 응답처럼 변할 수 있는 값은 fixture artifact로 고정하고 채점 raw 값과
  분리한다.

### 2.2 상태와 판정

| 판정 | 조건 |
|:---|:---|
| `complete` | 모든 mandatory result가 evidence와 source에 연결되고 export까지 완료 |
| `partial` | 입증된 일부 결과가 있으나 mandatory requirement가 하나 이상 누락 |
| `failed` | 유효 결과가 없거나 입력·정합·규정 Gate가 실패 |
| `interrupted` | 사용자 중단을 받고 checkpoint 보존을 시도 |

### 2.3 공통 시나리오 양식

각 시나리오는 다음 필드를 가진다.

- **Mode**: `offline`, `fault-injection`, `live` 중 하나
- **Backlog**: 구현 책임 TASK ID
- **Requirements**: 추적하는 REQ·TD·TEST ID
- **Preconditions**: 고정 입력·환경·source policy
- **Steps**: 실행 순서
- **Expected**: 상태·종료 코드·증거·부작용의 통과 기준

## 3. Project·Schema Gate

### QA-BOOT-001 — clean project 품질 Gate

- **Mode**: offline
- **Backlog**: `TASK-001`, `TASK-009`
- **Requirements**: `TD-001`, `TD-002`, `TD-008`, `TD-009`, `TD-010`
- **Preconditions**: clean checkout, 잠금 파일 존재, 외부 secret 없음
- **Steps**:
  1. 잠금 파일로 개발 환경을 동기화한다.
  2. Ruff lint·format check와 pytest를 실행한다.
  3. fixture·analysis Schema 검증기를 실행한다.
- **Expected**:
  - `uv sync --locked`, Ruff, pytest가 모두 성공한다.
  - 기존 검증기는 각각 `PASS 3`을 출력한다.
  - package import와 `scan --help`가 성공한다.
  - Git 추적 파일에 `.scan/`, DB, cache, secret이 없다.

### QA-SCHEMA-001 — 유효한 request·result round-trip

- **Mode**: offline
- **Backlog**: `TASK-002`
- **Requirements**: `REQ-COM-IN-*`, `REQ-COM-OUT-*`, `TEST-SCHEMA-001`,
  `REQ-NFR-001`
- **Preconditions**: confirmed DEX·AUTH·FREEZE analysis 예제 3쌍
- **Steps**:
  1. 저장 JSON Schema와 Pydantic model로 각 예제를 검증한다.
  2. model→JSON→model round-trip을 수행한다.
  3. 생성 Schema와 승인 Schema의 의미상 diff를 계산한다.
- **Expected**:
  - 세 예제 모두 유효하고 round-trip 전후 의미가 같다.
  - `analysis_id`, result→evidence→source 참조가 보존된다.
  - 승인 Schema `0.1`과 호환되지 않는 diff가 0이다.

### QA-SCHEMA-002 — 잘못된 계약과 참조 거부

- **Mode**: fault-injection
- **Backlog**: `TASK-002`
- **Requirements**: `REQ-NFR-004`, `invalid_input`, `schema_invalid`
- **Preconditions**: 유효 예제의 독립 복사본
- **Steps**:
  1. 잘못된 주소·TX hash·블록·분석 유형을 각각 주입한다.
  2. extra field, naive datetime, float raw amount, uint256 경계 초과를
     각각 주입한다.
  3. 중복 ID와 존재하지 않는 evidence·source 참조를 주입한다.
  4. `complete`+error와 `failed`+error 없음 조합을 주입한다.
- **Expected**:
  - 1의 변형은 `invalid_input`, 상태 `failed`, 종료 코드 `2`로 거부된다.
  - 2·3·4의 변형은 `schema_invalid`, 상태 `failed`, 종료 코드 `2`로 거부된다.
  - `uint256.max`는 문자열로 손실 없이 왕복한다.
  - 오류에 secret·원본 provider credential이 포함되지 않는다.

## 4. CLI·Terminal Gate

### QA-CLI-001 — 도움말·검증·조회 흐름

- **Mode**: offline
- **Backlog**: `TASK-005`
- **Requirements**: `REQ-COM-IN-*`, `TD-006`, `TD-007`
- **Preconditions**: terminal 폭 80 columns, 빈 임시 data directory
- **Steps**:
  1. `scan`, `scan --help`, `scan validate PATH`를 실행한다.
  2. `scan show UNKNOWN_ID`를 실행한다.
  3. 유효·무효 request 파일을 각각 validate한다.
- **Expected**:
  - 인자 없는 실행은 네트워크 호출 없이 목적·canonical 명령·3개 유형을 표시한다.
  - 알 수 없는 ID는 빈 표 대신 명시적 실패와 다음 행동을 표시한다.
  - 유효 입력은 종료 코드 `0`, 무효 입력은 `2`다.
  - 80 columns에서 핵심 ID·raw 값이 잘리거나 덮이지 않는다.

### QA-CLI-002 — stdout·stderr·종료 코드

- **Mode**: fault-injection
- **Backlog**: `TASK-005`, `TASK-009`
- **Requirements**: `invalid_input`, `source_unavailable`, `rule_restricted`,
  `evidence_incomplete`
- **Preconditions**: complete·partial·failed·restricted 고정 결과
- **Steps**:
  1. 네 결과를 terminal renderer에 전달한다.
  2. stdout, stderr, 파일 출력을 별도로 캡처한다.
- **Expected**:
  - stdout에는 최종 상태·핵심 결과·export 경로만 표시된다.
  - stderr에는 진행·cache·retry·fallback·warning·error가 표시된다.
  - complete=`0`, 입력 오류=`2`, partial=`3`, 실행 실패=`4`,
    규정 차단=`5`, 사용자 중단=`130`이다.
  - JSON 전체를 stdout에 암묵적으로 출력하지 않는다.

### QA-CLI-003 — retry 압축과 접근성

- **Mode**: fault-injection
- **Backlog**: `TASK-003`, `TASK-005`
- **Requirements**: `FB-001`, `REQ-NFR-008`
- **Preconditions**: 3회 실패 후 fallback 성공 attempt sequence
- **Steps**:
  1. TTY·non-TTY와 `NO_COLOR=1`에서 같은 실행을 렌더링한다.
  2. 첫 CLI 피드백까지 시간을 측정한다.
  3. stdout과 stderr의 attempt 표현을 비교한다.
- **Expected**:
  - 첫 피드백은 명령 실행 시점부터 목표 `400ms` 이내다.
  - stdout은 retry를 한 줄 요약하고 stderr는 attempt별 상세를 보존한다.
  - 색상 없이 상태·경고·실패를 텍스트로 구분할 수 있다.
  - non-TTY에는 animation·carriage return이 남지 않는다.

### QA-CLI-004 — analyze·partial·resume·show

- **Mode**: fault-injection
- **Backlog**: `TASK-004`, `TASK-005`
- **Requirements**: `REQ-P0-CACHE-006`, `REQ-P0-CACHE-007`
- **Preconditions**: DEX 실행을 pool output 이후 중단하도록 설정
- **Steps**:
  1. `scan analyze --request REQUEST`를 중단한다.
  2. 생성된 analysis ID로 `scan resume ID`를 실행한다.
  3. 완료 후 `scan show ID`를 실행한다.
- **Expected**:
  - 첫 실행은 checkpoint 보존을 시도하고 종료 코드 `130`이다.
  - resume은 완료 stage를 재호출하지 않고 `resumed: true`를 기록한다.
  - show는 저장된 result와 동일한 상태·ID·raw 값을 표시한다.

## 5. Source·Policy·Retry Gate

### QA-RULE-001 — restricted source 사전 차단

- **Mode**: offline
- **Backlog**: `TASK-003`
- **Requirements**: `REQ-NFR-008`, `rule_restricted`
- **Preconditions**: request source policy가 실행에 필요한 source를 제한
- **Steps**: orchestration을 실행하고 HTTP mock 호출 수를 확인한다.
- **Expected**:
  - 네트워크 호출은 0건이다.
  - 상태 `failed`, 종료 코드 `5`, 오류 `rule_restricted`다.
  - 차단 규칙과 stage는 남지만 credential은 남지 않는다.

### QA-SOURCE-001 — offline cache miss

- **Mode**: offline
- **Backlog**: `TASK-003`, `TASK-004`
- **Requirements**: `REQ-P0-CACHE-004`, `source_unavailable`
- **Preconditions**: offline=true, 빈 cache, 유효 request
- **Steps**: 분석을 실행한다.
- **Expected**:
  - 외부 호출은 0건이다.
  - 필수 결과가 없으면 `failed`, 일부 저장 결과가 있으면 `partial`이다.
  - 오류에 `source_unavailable`, stage, retryable=false가 기록된다.

### QA-RETRY-001 — 제한 재시도

- **Mode**: fault-injection
- **Backlog**: `TASK-003`
- **Requirements**: `TEST-RETRY-001`, `rate_limited`, `source_unavailable`
- **Preconditions**: timeout, 429+`Retry-After`, 503, 400 응답 sequence
- **Steps**: 응답 유형별로 adapter를 실행하고 attempt를 수집한다.
- **Expected**:
  - timeout·429·503만 설정된 최대 횟수 안에서 재시도한다.
  - 400과 schema 오류는 재시도하지 않는다.
  - backoff·jitter·`Retry-After` 적용과 모든 attempt가 provenance에 남는다.
  - 무한 재시도가 없다.

### QA-FALLBACK-001 — provider fallback provenance

- **Mode**: fault-injection
- **Backlog**: `TASK-003`
- **Requirements**: `TEST-FALLBACK-001`, `REQ-NFR-006`
- **Preconditions**: 주 provider 실패, 허용된 대체 provider 성공
- **Steps**: 동일 capability를 source order에 따라 실행한다.
- **Expected**:
  - 최초 실패 source·attempt와 대체 source 성공이 모두 기록된다.
  - 결과 계약과 evidence ID는 provider 이름에 종속되지 않는다.
  - 허용 목록 밖 provider는 호출하지 않는다.

## 6. Cache·Artifact·Export·Security Gate

### QA-CACHE-001 — immutable cache hit

- **Mode**: offline
- **Backlog**: `TASK-004`
- **Requirements**: `TEST-CACHE-001`, `REQ-NFR-003`
- **Preconditions**: 첫 실행의 고정 source response와 임시 SQLite DB
- **Steps**:
  1. 같은 정규화 request를 두 번 실행한다.
  2. 두 번째 실행을 network-disabled 상태에서 재검증한다.
- **Expected**:
  - 두 번째 실행의 외부 호출은 0건이다.
  - 채점 raw 값·boolean·evidence 참조가 첫 실행과 같다.
  - `cache_hit: true`와 원본 source provenance를 모두 보존한다.

### QA-EXPORT-001 — JSON·Markdown 동일성

- **Mode**: offline
- **Backlog**: `TASK-004`, `TASK-009`
- **Requirements**: `TEST-EXPORT-001`, `REQ-NFR-002`, `REQ-NFR-007`
- **Preconditions**: complete DEX·AUTH·FREEZE result
- **Steps**:
  1. JSON과 Markdown을 같은 result model에서 export한다.
  2. analysis·result·evidence·source ID와 raw 값을 비교한다.
- **Expected**:
  - 모든 ID·값·classification·warning이 의미상 동일하다.
  - JSON이 단일 source of truth이고 Markdown의 독립 계산이 없다.
  - export만으로 입력·source·block·evidence·tool version을 역추적할 수 있다.

### QA-ARTIFACT-001 — content-addressed raw artifact

- **Mode**: offline
- **Backlog**: `TASK-004`
- **Requirements**: `REQ-P0-PROV-*`, `TD-015`, `TD-020`
- **Preconditions**: 동일 body 2개와 1-byte가 다른 body 1개
- **Steps**: 세 body를 임시 artifact directory에 저장한다.
- **Expected**:
  - 동일 body는 같은 SHA-256 artifact를 재사용한다.
  - 다른 body는 다른 hash를 가진다.
  - hash, byte length, media type, source, retrieved time이 연결된다.
  - 부분 파일이 최종 artifact 경로에 남지 않는다.

### QA-SEC-001 — secret·로컬 경로 비노출

- **Mode**: fault-injection
- **Backlog**: `TASK-001`, `TASK-003`, `TASK-004`, `TASK-005`, `TASK-009`
- **Requirements**: `REQ-NFR-005`
- **Preconditions**: canary API key, Authorization header, 사용자 절대 경로 포함 입력
- **Steps**: 성공·retry·fallback·failed 실행 후 CLI stdout·stderr와 log·DB·cache·error·export를 검색한다.
- **Expected**:
  - canary secret과 Authorization 값은 모든 검색 대상에서 0건이다.
  - 사용자 이름이 포함된 로컬 절대 경로는 stdout·stderr·error·export에서 0건이다.
  - endpoint query secret은 redacted 형태로만 남는다.
  - 테스트는 사용자 실제 `.scan/`을 읽거나 변경하지 않는다.

## 7. DEX Vertical Slice

### QA-DEX-001 — confirmed exact match

- **Mode**: offline
- **Backlog**: `TASK-006`, `TASK-009`
- **Requirements**: `REQ-V1-DEX-*`, `TEST-DEX-001`
- **Preconditions**: `FX-SVC-DEX-001` confirmed input·expected·evidence
- **Steps**: 고정 receipt·logs·internal call·getPair 응답으로 DEX 분석을 실행한다.
- **Expected**:
  - 입력은 USDC `25000000000` raw다.
  - pool output은 WETH `14449515027026387018` raw다.
  - user net output은 native ETH `14449515027026387018` raw다.
  - WETH와 native ETH를 서로 다른 자산·결과로 보존한다.
  - 필수 log index `275`, `276`, `278`, `279`와 source가 연결된다.
  - 상태 `complete`, 종료 코드 `0`, tolerance는 raw `0`이다.

### QA-DEX-002 — 부분 성공과 자산 오판 방지

- **Mode**: fault-injection
- **Backlog**: `TASK-006`
- **Requirements**: `trace_unavailable`, `evidence_incomplete`,
  `reconciliation_failed`
- **Preconditions**: DEX confirmed 응답의 독립 복사본
- **Steps**:
  1. internal native ETH call만 제거한다.
  2. pool WETH를 사용자 최종 자산으로 주입한다.
  3. Swap 수량을 1 raw 변경한다.
- **Expected**:
  - 1은 입증된 pool output과 `partial`, 종료 코드 `3`이다.
  - 2와 3은 `complete`가 될 수 없고 정합 실패로 종료된다.
  - 누락 requirement와 관련 evidence ID가 오류에 연결된다.

## 8. AUTH Vertical Slice

### QA-AUTH-001 — confirmed exact match와 실패 TX 제외

- **Mode**: offline
- **Backlog**: `TASK-007`, `TASK-009`
- **Requirements**: `REQ-V1-AUTH-*`, `TEST-AUTH-001`
- **Preconditions**: `FX-EVM-AUTH-001` confirmed input·expected·evidence
- **Steps**: 고정 Approval·calldata·trace·Transfer·archive state로 AUTH 분석을 실행한다.
- **Expected**:
  - approval은 `uint256.max` raw이며 allowance 네 지점은 fixture와 exact match다.
  - 성공 소비·Transfer·allowance 감소량은 모두 `4500000` raw다.
  - nonce `327`~`329`의 실패 TX 3건은 소비에서 제외된다.
  - event·call·state evidence가 분리된다.
  - `offchain_attribution=not_assessed`, `theft_or_phishing_claim=false`다.
  - 상태 `complete`, 종료 코드 `0`이다.

### QA-AUTH-002 — archive 누락·resume·탈취 단정 방지

- **Mode**: fault-injection
- **Backlog**: `TASK-007`
- **Requirements**: `archive_required`, `evidence_incomplete`,
  `REQ-V1-AUTH-*`
- **Preconditions**: event·call은 존재하고 allowance state 일부는 중단
- **Steps**:
  1. archive state 두 지점을 누락한다.
  2. checkpoint 이후 state를 복구해 resume한다.
  3. 근거 없이 theft classification을 true로 주입한다.
- **Expected**:
  - 1은 승인·소비 사실만 `partial`, 종료 코드 `3`이다.
  - 2는 기존 event·call source를 재호출하지 않고 complete로 복구한다.
  - 3은 classification 계약 위반으로 거부된다.

## 9. FREEZE Vertical Slice

### QA-FREEZE-001 — confirmed lifecycle와 맥락 분리

- **Mode**: offline
- **Backlog**: `TASK-008`, `TASK-009`
- **Requirements**: `REQ-V1-FREEZE-*`, `TEST-FREEZE-001`
- **Preconditions**: `FX-EVM-FREEZE-001` confirmed input·expected·evidence
- **Steps**: 고정 call·event·archive state·Circle·OFAC artifact로 분석을 실행한다.
- **Expected**:
  - blacklist는 `false→true`, unblacklist는 `true→false`다.
  - 네 historical state와 두 event·call이 exact match다.
  - event·call·state·context evidence가 각각 분리된다.
  - Circle은 `address_specific=false`, OFAC 공식 action은 주소 포함=true다.
  - current sanctions·범죄 의도는 `not_assessed` 또는 `not_scored`다.
  - global pause는 `applicable=false`다.
  - 상태 `complete`, 종료 코드 `0`이다.

### QA-FREEZE-002 — 한 전이 누락과 restricted context

- **Mode**: fault-injection
- **Backlog**: `TASK-003`, `TASK-008`
- **Requirements**: `archive_required`, `evidence_incomplete`,
  `rule_restricted`
- **Preconditions**: unblacklist state가 없는 응답, 별도의 restricted URL policy
- **Steps**:
  1. blacklist 전이만 유지해 분석한다.
  2. 공식 context URL 접근이 제한된 요청을 offline으로 실행한다.
- **Expected**:
  - 1은 한 전이를 입증한 `partial`, 종료 코드 `3`이다.
  - 2는 네트워크 호출 0건이며 규정 차단이면 종료 코드 `5`다.
  - context 누락을 온체인 상태 누락이나 현재 제재 판정으로 바꾸지 않는다.

## 10. 통합·회귀 Gate

### QA-REG-001 — confirmed fixture 결정성

- **Mode**: offline
- **Backlog**: `TASK-009`
- **Requirements**: `REQ-NFR-001`, `REQ-NFR-003`
- **Preconditions**: 고정 clock·UUID·source response, 빈 임시 환경
- **Steps**: 세 fixture를 각각 두 번 실행하고 volatile run metadata를 제외해 비교한다.
- **Expected**:
  - 채점 raw 값·boolean·classification·evidence 연결이 byte-stable하다.
  - 두 번째 실행은 외부 호출이 0건이다.
  - fixture·analysis 기존 검증기는 계속 `PASS 3`이다.

### QA-REG-002 — 오류 코드·상태·종료 코드 행렬

- **Mode**: fault-injection
- **Backlog**: `TASK-002`, `TASK-005`, `TASK-009`
- **Requirements**: 요구사항 §11의 오류 코드 11개
- **Preconditions**: 각 오류를 단독 유발하는 고정 입력
- **Steps**: 11개 오류를 각각 실행해 result·error·process exit를 수집한다.
- **Expected**:
  - 모든 오류는 승인된 code만 사용한다.
  - partial 가능 오류도 입증 결과가 없으면 failed로 내려간다.
  - mandatory requirement 누락 결과는 complete가 아니다.
  - error의 evidence·source 참조가 존재하거나 명시적으로 비어 있다.

### QA-REG-003 — 문서·Schema·fixture 추적성

- **Mode**: offline
- **Backlog**: `TASK-009`
- **Requirements**: `REQ-NFR-002`, `REQ-NFR-007`
- **Preconditions**: repository 문서·Schema·fixture·backlog
- **Steps**:
  1. 상대 링크와 ID 유일성을 검사한다.
  2. backlog requirement·QA ID가 실제 문서에 존재하는지 검사한다.
  3. fixture expected와 QA hardcode 값을 대조한다.
- **Expected**:
  - 깨진 상대 링크·중복 TASK·QA ID가 0건이다.
  - DEX·AUTH·FREEZE hardcode 값이 fixture와 일치한다.
  - 구현 변경 시 관련 Concept·UI·Technical·QA 문서가 동기화된다.

## 11. 365 글로벌 평가 기준

QA 계층은 6개 기준을 모두 검증 대상으로 둔다.

| 기준 | QA 연결 |
|:---|:---|
| Functionality | exact-match, 오류 주입, 종료 코드, partial·resume |
| Potential Impact | 반복 수작업을 줄이는 cache·export·fixture 회귀 |
| Novelty | pool/user, 권한 소비/탈취, 온체인/맥락의 명시적 분리 |
| UX | UI-First Gate, FB-001, 80 columns, non-TTY, 다음 행동 |
| Open-source | clean checkout, 잠금 파일, 재현 명령, fixture provenance |
| Business Plan | 현재 채점·구현 Gate에는 `N/A`; 별도 제출 전략에서 평가 |

## 12. Originality & Ethics Check

- 기존 공개 TX·공식 문서·오픈소스 주소 자료는 provenance와 license를 보존한다.
- fixture는 정답과 증거를 재현하기 위한 것이며 제3자의 범죄 의도·신원을 추정하지 않는다.
- AUTH의 탈취·피싱, FREEZE의 범죄 의도·현재 제재는 별도 근거 없이는
  `not_assessed` 또는 `not_scored`다.
- API key·개인 credential·private key를 fixture, log, cache, export에 넣지 않는다.
- 대회 규정이 자동화·API·AI 사용을 제한하면 실행 전에 차단하고 제한을 숨기지 않는다.

## 13. 승인 Gate와 실행 순서

1. 이 문서와 [Backlog](../04_Logic_Progress/00_BACKLOG.md)의 범위·ID를 함께 승인한다.
2. [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md)의 QA checklist·fixture
   방침·Draft 승인 Gate를 통과한다.
3. 별도 구현 승인 후 `TASK-001`부터 각 작업의 Preconditions를 다시 확인한다.
4. unit → integration → regression 순서로 관련 QA ID를 자동화한다.
5. `live` 검증은 명시적으로 분리하고 offline 결과를 필수 Gate로 유지한다.
6. `TASK-009`에서 전 시나리오와 문서 동기화를 통과해야 P0·V1 완료로 판정한다.

## 14. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 완료·부분·실패 기준
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1 범위
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 명령·상태·종료 코드
- **UI_Screens**: [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 표시·접근성 기준
- **UI_Screens**: [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - UI-First Gate·FB-001
- **UI_Screens**: [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 승인된 HTML preview
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 규범 요구사항
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 구현·테스트 원칙
- **Technical_Specs**: [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 JSON 계약
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source 능력·제약
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - QA checklist·fixture 방침·문서 승인 순서
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - QA별 구현 책임
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed 사례와 승격 기준
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - 24개 시나리오의 승인·실행 시점과 결과 기록
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - `TASK-010` 별도 병렬성·격리·독립 검증·수동 제출 QA
- **QA_Validation**: [분석 I/O 예제](./examples/analysis/README.md) - request·result 기준
- **QA_Validation**: [DEX fixture](./fixtures/FX-SVC-DEX-001/README.md), [AUTH fixture](./fixtures/FX-EVM-AUTH-001/README.md), [FREEZE fixture](./fixtures/FX-EVM-FREEZE-001/README.md) - exact-match 원본
