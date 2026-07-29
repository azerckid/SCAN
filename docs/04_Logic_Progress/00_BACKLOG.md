# SCAN 2026 P0·V1·Coverage 확장 및 대회 운영 Backlog
> Created: 2026-07-26 16:46
> Last Updated: 2026-07-30 03:37
> Status: TASK-001~014 Done · WP-INPUT Done · TASK-015 Source Resolution 5 Viable / Snapshot Basis · TASK-016~019 Proposed

## 1. 문서 목적

이 문서는 승인된 P0·V1 요구사항과 Benchmark 이후 Coverage 확장 계획,
Analysis I/O Schema, Python 개발 원칙, UI-First Gate와 fixture를 구현 가능한
원자적 작업으로 전환한다.

Backlog 범위와 `TASK-001`~`TASK-009` 구현은 별도로 승인되었다. 아홉 작업과
예상문제 benchmark `TASK-011`은 완료됐고 Rules-gated `TASK-010`은 offline
V1 범위가 완료됐다. live 후속 작업은 별도 승인 전에는 `In Progress`로
이동하지 않는다.

Benchmark 0.1 이후 Coverage 확장 `TASK-012`~`TASK-019`는 사용자 요청에
따라 계획됐지만 모두 `ToDo`다. fixture·Context Receipt·개별 구현 승인을
통과하기 전에는 코드를 작성하지 않는다.

`TASK-010`은 공식 Rules·Operations Board Preview·별도 구현 승인에 의존하는
비차단 운영 트랙이다. `TASK-001`~`TASK-009`의 P0·V1 의존 순서와 완료 Gate를
변경하지 않는다.

## 2. 범위와 작업 규칙

### 2.1 포함 범위

- Python project·quality tool 초기화
- Analysis I/O Pydantic model과 Schema diff
- source adapter·policy·retry·fallback
- SQLite cache·checkpoint와 SHA-256 artifact
- provenance·JSON·Markdown export
- `analyze`, `validate`, `resume`, `show` CLI
- DEX·AUTH·FREEZE vertical slice
- confirmed fixture 3개 회귀와 UI·보안 Gate
- Rules-gated 복수 문제 Queue·worker·독립 검증·수동 제출 운영
- Coverage 확장 `TASK-012`~`TASK-019`의 문서화된 계획 범위
  (구현·fixture·Context Receipt 승인은 미완료)

### 2.2 제외 범위

- P0·V1 구현 기준선에서는 PATH·LABEL·VIZ 범용 기능과
  Bitcoin·브리지·일반 OSINT·휴리스틱을 제외한다. 이 기능들은 Phase 2
  `TASK-014`~`TASK-018`의 **계획 범위에만** 포함되며, fixture·Context
  Receipt·개별 구현 승인 전에는 현재 구현 범위로 간주하지 않는다.
- Web Investigation Workbench 구현·노트북·그래프 DB
- 서명·거래 전송·private key 입력
- 새로운 fixture 정답·증거 변경

### 2.3 상태 규칙

| 상태 | 의미 |
|:---|:---|
| `ToDo` | 문서 승인 또는 선행 작업 대기 |
| `In Progress` | Implementation Preconditions를 다시 확인하고 구현 중 |
| `Done` | Acceptance Criteria·QA·Document Sync Check 완료 |

작업을 `In Progress`로 옮길 때 구현자는 해당 항목의 모든 관련 문서를 실제로
다시 읽고 Preconditions를 체크한다. 코드만 완료하고 문서·QA가 남으면 `Done`으로
이동할 수 없다.

### 2.4 오픈소스 사전조사 Gate

모든 구현 작업은 [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md)의
관련 `OSSR-*` 조사와 `OSS-*` 결정을 입력으로 사용한다. 적합한 기존 기능을
검색하지 않았거나 결정 근거가 없으면 해당 작업을 `In Progress`로 이동하지
않는다.

P2·P3 조사는 해당 단계 승격 전까지 보류할 수 있지만, P0·V1 구현에는 관련
P0·V1 조사 결정이 필수다.

## 3. 의존 순서

```mermaid
flowchart LR
    T1["TASK-001 Project"] --> T2["TASK-002 Contract Models"]
    T1 --> T3["TASK-003 Source Orchestration"]
    T1 --> T4["TASK-004 Storage and Export"]
    T2 --> T4
    T2 --> T5["TASK-005 CLI"]
    T3 --> T5
    T4 --> T5
    T3 --> T6["TASK-006 DEX"]
    T4 --> T6
    T2 --> T6
    T3 --> T7["TASK-007 AUTH"]
    T4 --> T7
    T2 --> T7
    T3 --> T8["TASK-008 FREEZE"]
    T4 --> T8
    T2 --> T8
    T5 --> T9["TASK-009 Integration Gate"]
    T6 --> T9
    T7 --> T9
    T8 --> T9
    T9 -. "Rules·Preview·별도 승인" .-> T10["TASK-010 Parallel Operations"]
    T9 --> T11["TASK-011 Coverage Benchmark"]
    T11 --> T12["TASK-012 EVM Core"]
    T12 --> T13["TASK-013 NFT·Proxy"]
    T12 --> T14["TASK-014 PATH"]
    T12 --> T15["TASK-015 Intel"]
    T14 --> T16["TASK-016 Service·XChain"]
    T15 --> T16
    T11 --> T17["TASK-017 Bitcoin"]
    T14 --> T18["TASK-018 Crime·Case"]
    T15 --> T18
    T16 --> T18
    T12 --> T19["TASK-019 Expansion Gate"]
    T13 --> T19
    T14 --> T19
    T15 --> T19
    T16 --> T19
    T17 --> T19
    T18 --> T19
```

TASK-002와 TASK-003은 TASK-001 뒤에 병렬 진행할 수 있다. TASK-004는
계약 model(TASK-002)에 의존하므로 TASK-002 이후에 시작한다. TASK-005는
TASK-002·003·004 모두에 의존한다. DEX·AUTH·FREEZE는 공통 계약을 재사용하되
서로의 내부 구현에 의존하지 않는다.
TASK-010은 통합된 Python leaf 분석을 사용하지만 P0·V1 완료를 차단하지 않는다.
TASK-012~019는 TASK-011의 3/6/21 측정 이후 별도 Phase 2다. TASK-012와
TASK-017은 fixture·source 준비가 독립적이면 병렬 가능하고, TASK-019는
실제로 승인·완료된 package만 통합한다.

`WP-INPUT-GATE`는 TASK-012~019의 공통 선행 조건이다. 입력 모드는
`external_rpc | contest_rpc | provided_artifact`, 체인 범위는
`evm | bitcoin | non_evm | cross_chain`이다. 첫 승인 단위에서 contest RPC
core adapter와 bounded JSON·JSONL·CSV importer를 구현했고, 두 번째 승인
단위에서 CLI·Operations offline handoff를 연결했다. 제품 analyzer는
TASK-012 EVM Core, TASK-013 NFT·Proxy, TASK-014 PATH까지 구현됐으며,
TASK-015~019의
Context Receipt·개별 구현 승인을 대체하지 않는다.

### 3.1 WP-INPUT-IMPL-01: Core input library

- Status: Done
- Approval: 2026-07-29 사용자 승인
- Scope:
  - [x] input mode·chain scope enum과 normalized evidence bundle
  - [x] contest HTTPS JSON-RPC adapter·기존 source port 재사용
  - [x] JSON·JSONL·CSV bounded importer와 raw/record SHA·locator
  - [x] chain mismatch·malformed·null·size/count·repr 비반사
  - [x] JSON-RPC unwrap 이후 내부 chain scope 재검사
  - [x] contest RPC read-only allowlist·금지 method 호출 전 차단
  - [x] RPC↔artifact normalized record 동등성
  - [x] 명시 contest endpoint 외 Explorer/network fallback 0건
- Excluded:
  - [ ] CLI·Operations input selection
  - [ ] 문제별 임의 artifact mapping
  - [ ] EVM Core·Bitcoin·non-EVM·cross-chain analyzer
- Context Receipt: PASS — 다중 입력 명세, source/evidence port, 보안 경계,
  Coverage QA를 확인했고 Analysis I/O `0.1`은 변경하지 않았다.
- Verification Receipt: focused 30 tests·전체 336 tests·Schema·traceability·
  security PASS, 상세는 구현 보고서 참조.

### 3.2 WP-INPUT-IMPL-02: CLI·Operations input wiring

- Status: Done
- Approval: 2026-07-29 사용자 구현 승인
- Scope:
  - [x] `scan analyze`에 input mode·chain scope·artifact 옵션을 연결했다.
  - [x] endpoint 값 대신 환경변수 이름만 받고 안전한 HTTPS 여부를 검사한다.
  - [x] 정규화 성공 뒤에만 raw bytes를 content-addressed artifact로 저장한다.
  - [x] `InputEvidenceEnvelope` hash·URI에서 `ApprovedReplay`를 재구성한다.
  - [x] Evidence Worker가 envelope↔replay hash·EVM scope를 adapter 호출 전에 검사한다.
  - [x] OperationEvent에 endpoint 없는 input provenance를 기록한다.
  - [x] 기존 옵션 없는 `--evidence` DEX·AUTH·FREEZE 경로를 보존한다.
- Excluded:
  - [ ] `contest_rpc` 문제별 query mapping과 live 실행
  - [ ] TASK-012 `evm_core` analyzer와 Analysis I/O version 변경
  - [ ] Bitcoin·non-EVM·cross-chain analyzer
- Context Receipt: PASS — 계약·Preview 사용자 승인, core input library,
  기존 Evidence Worker·artifact·SQLite 경계를 확인했다.
- Verification Receipt: focused CLI·input·Evidence Worker PASS, 전체 offline
  Gate PASS. 상세는 `31_WP_INPUT_CLI_OPERATIONS_REPORT.md` 참조.

## 4. Task Register

작업은 의존 순서를 보존하기 위해 ID 순으로 둔다. 실제 상태는 각 카드와
§5·§6에서 관리한다.

### [x] TASK-001: Python project와 기본 품질 Gate 초기화

- Status: Done
- Priority: P0 · High
- Depends On: 없음
- Requirement IDs: `TD-001`, `TD-002`, `TD-003`, `TD-008`, `TD-009`,
  `TD-010`, `TD-011`, `TD-012`
- Atomic Tasks:
  - [x] `.gitignore`에 `.scan/`, `.env*`, pytest·Ruff·coverage·build 산출물을 추가한다.
  - [x] 현재 환경변수가 없어 `.env.example`을 생성하지 않기로 결정했다.
  - [x] `pyproject.toml`에 Python `>=3.12,<3.15`, src layout과 package metadata를 정의한다.
  - [x] 최소 runtime dependency와 dev dependency를 Dependency Gate로 검토한다.
  - [x] `uv.lock`을 생성하고 독립 임시 환경 cold install을 재현한다.
  - [x] `src/scan_tool/`과 `tests/unit`, `tests/integration`, `tests/regression`를 만든다.
  - [x] `scripts/verify.py`로 Ruff·pytest와 기존 두 Schema 검증을 한 번에 실행한다.
- Related Concept Docs:
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0 공통 기반 선행 원칙
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 초기 package가 제공할 command surface
  - [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - UI-First Gate 통과와 FB-001
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 확인된 사용자 화면
- Related Technical Docs:
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 구조·dependency·Git·보안 기준
  - [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) - Python·uv·Typer·pytest·Ruff 결정
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-BOOT-*`, `QA-SEC-*`
- Implementation Preconditions:
  - [x] 관련 Concept·UI·Technical·QA 문서를 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 FB-001 기록을 확인했다.
  - [x] CLI 진입·전환·이탈과 loading·empty·error 상태를 확인했다.
  - [x] 데이터 소스·최소 필드·local mutation·상태 저장 경계를 확인했다.
  - [x] dependency license·취약점·공식 package를 확인했다.
  - [x] 구현 범위가 P0·V1과 충돌하지 않는다.
- Acceptance Criteria:
  - [x] 독립 임시 환경에서 `uv sync --locked`가 성공한다.
  - [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`가 성공한다.
  - [x] 기존 fixture·analysis Schema 검증이 모두 `PASS 3`이다.
  - [x] Git 추적 파일에서 secret·`.scan/`·로컬 DB가 0건이다.
  - [x] package import와 `scan --help`가 src layout 설치에서 성공한다.
- Document Sync Check:
  - [x] 실제 Python·dependency version과 명령을 개발 원칙·기술 선택 기록에 반영했다.
  - [x] 구현과 문서 차이를 검토하고 TASK-001 결과 보고서에 기록했다.

### [x] TASK-002: Analysis I/O 계약 model과 Schema diff 구현

- Status: Done
- Priority: P0 · High
- Depends On: TASK-001
- Requirement IDs: `REQ-COM-IN-*`, `REQ-COM-OUT-*`, `REQ-NFR-001`,
  `REQ-NFR-004`, `TD-003`, `TD-006`, `TD-019`
- Atomic Tasks:
  - [x] request·result·error Pydantic v2 model을 분리한다.
  - [x] 공통 model에 `extra="forbid"`를 적용한다.
  - [x] analysis type·status·classification·evidence type·error code enum을 정의한다.
  - [x] 주소·TX hash·RFC 3339·raw decimal string validator를 구현한다.
  - [x] complete·partial·failed 불변조건과 ID 유일성을 검증한다.
  - [x] result→evidence→source 참조 무결성을 검증한다.
  - [x] Pydantic 생성 Schema와 승인 Schema `0.1`의 의미상 diff 명령을 만든다.
  - [x] confirmed request/result 예제 3쌍을 model round-trip한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 완료·부분·실패와 증거 필드
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - model 상태가 표시되는 순서
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - raw·classification·error 표현
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - model 기반 terminal 상태
- Related Technical Docs:
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 규범적 공개 계약
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 입력·출력·오류 규칙
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - Pydantic·정밀도·시간 기준
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-SCHEMA-001`, `QA-SCHEMA-002`
  - [Analysis I/O 예제](../05_QA_Validation/examples/analysis/README.md) - round-trip 기준
  - [TASK-002 Contract 보고서](../05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md) - model·불변조건·Schema 의미 검사 증거
- Implementation Preconditions:
  - [x] 관련 문서와 승인 Schema 3종을 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview의 complete·partial·failed 표현을 확인했다.
  - [x] 입력·출력 최소 필드와 상태 변화를 확인했다.
  - [x] 외부 mutation 없음과 local model validation 경계를 확인했다.
  - [x] fixture schema와 analysis schema의 독립 버전을 확인했다.
  - [x] 구현 범위가 공개 계약 `0.1`을 임의 변경하지 않는다.
- Acceptance Criteria:
  - [x] 유효한 요청·결과 예제 3쌍이 round-trip 후 의미상 동일하다.
  - [x] 잘못된 주소·TX hash·블록·유형은 `invalid_input`으로 거부한다.
  - [x] extra field·float raw amount·naive datetime·깨진 참조는
        `schema_invalid`로 거부한다.
  - [x] 깨진 result→evidence→source 참조를 거부한다.
  - [x] 저장 Schema와 생성 Schema의 의미상 probe diff가 0이다.
  - [x] `complete`+error, `failed`+no error 조합을 거부한다.
- Document Sync Check:
  - [x] model 경로와 Schema 생성·diff 명령을 Schema 문서에 기록했다.
  - [x] 공개 Schema 변경 없이 계약 `0.1`을 구현했다.

### [x] TASK-003: Source port·policy·retry·fallback orchestration 구현

- Status: Done
- Priority: P0 · High
- Depends On: TASK-001
- Requirement IDs: `REQ-P0-PROV-001`, `REQ-P0-PROV-005`,
  `REQ-P0-CACHE-004`, `REQ-P0-CACHE-005`, `REQ-NFR-006`,
  `REQ-NFR-008`, `TD-013`, `TD-014`
- Atomic Tasks:
  - [x] source request·response·attempt Protocol을 정의한다.
  - [x] 주입 가능한 `httpx.AsyncClient`와 source별 timeout을 구성한다.
  - [x] public RPC·archive RPC·explorer·official context adapter 경계를 만든다.
  - [x] `allowed_source_ids`·`source_order`·offline·fallback 정책을 적용한다.
  - [x] restricted 요청을 네트워크 호출 전에 차단한다.
  - [x] timeout·429·일시적 5xx만 제한적으로 재시도한다.
  - [x] `Retry-After`, backoff·jitter, 최대 시도와 모든 attempt를 기록한다.
  - [x] fallback 시 최초 실패와 대체 provider를 모두 보존한다.
- Related Concept Docs:
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - source 교체·규정 위험을 포함한 P0
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - retry·fallback·규정 차단 흐름
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - source·attempt 표시와 FB-001
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - AUTH retry·FREEZE 차단 상태
- Related Technical Docs:
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source ID·능력·제약
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - provenance·retry·규정 계약
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - adapter·secret·orchestration 기준
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-SOURCE-*`, `QA-RETRY-*`, `QA-RULE-*`
  - [TASK-003 Source 보고서](../05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) - policy·retry·fallback·dependency 증거
- Implementation Preconditions:
  - [x] 등록부와 source policy·오류 계약을 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview의 retry·fallback·rule blocked 상태를 확인했다.
  - [x] source 입력·응답·attempt 최소 필드를 확인했다.
  - [x] 외부 mutation 없이 read-only 호출만 수행함을 확인했다.
  - [x] 공식 규정·provider plan·rate limit 미확정 값을 하드코딩하지 않는다.
  - [x] FB-001의 stderr 상세·stdout 압축 경계를 확인했다.
- Acceptance Criteria:
  - [x] restricted 정책에서 HTTP 호출이 0건이다.
  - [x] offline mode에서 cache miss가 구조화 오류로 종료되고 network 호출은 0건이다.
  - [x] timeout·429·일시적 5xx에만 제한된 재시도가 실행된다.
  - [x] fallback 전후 provider가 모두 source attempt에 남는다.
  - [x] endpoint query·header·API key가 결과 repr·구조화 오류에 나타나지 않는다.
- Document Sync Check:
  - [x] 실제 adapter 경계와 provider ID 정책을 데이터 소스 등록부에 반영했다.
  - [x] retry·fallback 기본값을 기술 선택·Schema 실행 정책·QA와 동기화했다.

### [x] TASK-004: SQLite cache·checkpoint·provenance·export 구현

- Status: Done
- Priority: P0 · High
- Depends On: TASK-001, TASK-002
- Requirement IDs: `REQ-P0-PROV-*`, `REQ-P0-EXPORT-*`,
  `REQ-P0-CACHE-001`, `REQ-P0-CACHE-002`, `REQ-P0-CACHE-003`,
  `REQ-P0-CACHE-006`, `REQ-P0-CACHE-007`, `TD-015`, `TD-016`,
  `TD-020`, `TD-021`
- Atomic Tasks:
  - [x] run·source attempt·cache·checkpoint·artifact 최소 SQLite DDL을 정의한다.
  - [x] WAL과 transaction 경계·parameter binding을 적용한다.
  - [x] canonical cache key와 immutable historical 응답 정책을 구현한다.
  - [x] raw body를 SHA-256 content-addressed artifact로 원자적 저장한다.
  - [x] checkpoint에 완료 stage와 evidence ID를 기록한다.
  - [x] JSON result를 단일 source of truth로 export한다.
  - [x] 같은 result model에서 Markdown evidence를 렌더링한다.
  - [x] export·DB·artifact·checkpoint의 secret redaction을 검사한다.
- Related Concept Docs:
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - BASE-CACHE·PROVENANCE·EXPORT 최우선 근거
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - cache·resume·export 사용자 흐름
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - RUN·EXPORTS 표시
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - cache hit·resume·artifact 경로
- Related Technical Docs:
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - SQLite·artifact·provenance·export 기준
  - [SQLite 논리 DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md) - 논리 엔티티·관계·mutation·보존 계약
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - run·sources·exports 계약
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - cache·export 완료 조건
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-CACHE-*`, `QA-EXPORT-*`, `QA-SEC-*`
  - [TASK-004 Storage 보고서](../05_QA_Validation/08_TASK_004_STORAGE_REPORT.md) - DDL·cache·checkpoint·artifact·export 증거
- Implementation Preconditions:
  - [x] 저장·복구·export 관련 문서를 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview의 cache·resume·export 상태를 확인했다.
  - [x] DB 최소 필드·artifact metadata·checkpoint 상태를 확인했다.
  - [x] local mutation 범위가 `.scan/` 아래임을 확인했다.
  - [x] WAL backup·migration·삭제에 사용자 승인 원칙을 확인했다.
  - [x] JSON·Markdown ID·값 일치 기준을 확인했다.
- Acceptance Criteria:
  - [x] 동일 immutable 요청 2회째 외부 호출이 0건이고 결과가 같다.
  - [x] 중단 후 완료 stage를 재호출하지 않고 `resumed: true`로 완료한다.
  - [x] artifact hash·byte length·source·retrieved time이 연결된다.
  - [x] JSON·Markdown의 analysis·result·evidence ID와 값이 일치한다.
  - [x] secret과 로컬 사용자 절대 경로가 export에서 0건이다.
  - [x] 임시 DB·디렉터리 기반 integration test가 사용자 `.scan/`을 건드리지 않는다.
- Document Sync Check:
  - [x] SQLite DDL·backup·artifact URI를 기술 문서에 기록했다.
  - [x] export 형식과 Analysis I/O `0.1` 비변경을 Schema·UI·QA에 동기화했다.

### [x] TASK-005: CLI command surface와 terminal renderer 구현

- Status: Done
- Priority: V1 · High
- Depends On: TASK-002, TASK-003, TASK-004
- Requirement IDs: `TD-009`, `TD-018`, `REQ-COM-*`, `REQ-NFR-005`
- Atomic Tasks:
  - [x] Typer app과 `analyze`, `validate`, `resume`, `show` 명령을 정의한다.
  - [x] CLI composition root에서 SQLite·artifact·export adapter를 생성·주입한다.
  - [x] 시작 400ms 이내 첫 피드백을 측정 가능한 시각으로 기록한다.
  - [x] progress·cache·retry·fallback·warning을 stderr로 출력한다.
  - [x] 최종 상태·결과·export 경로를 stdout으로 출력한다.
  - [x] complete·partial·failed·restricted·interrupted 종료 코드를 적용한다.
  - [x] `NO_COLOR`, non-TTY, 80 columns와 주소·TX 축약을 지원한다.
  - [x] FB-001에 따라 최종 stdout retry 이력을 압축한다.
- Related Concept Docs:
  - [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 빠른 문제 풀이와 재현성 목적
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - canonical 명령·종료 코드·사용자 동선
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 상태별 layout·접근성·FB-001
  - [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - 사용자 승인 기록
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 비교 기준
- Related Technical Docs:
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - composition root·stdout·stderr·logging
  - [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) - Typer·command surface
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - renderer 입력 model
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-CLI-001`~`QA-CLI-004`, `QA-SEC-001`의 CLI 범위
  - [TASK-005 CLI 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md) - 명령·renderer·exit code·보안·UI 대조 증거
- Implementation Preconditions:
  - [x] 관련 UI 문서·Preview·사용자 피드백을 다시 확인했다.
  - [x] 진입·전환·이탈과 complete·partial·failed 상태를 확인했다.
  - [x] renderer가 받는 최소 result·run·error 필드를 확인했다.
  - [x] CLI local mutation은 요청·run·export·checkpoint 저장으로 제한된다.
  - [x] core calculation을 CLI에 두지 않는 경계를 확인했다.
  - [x] FB-001을 Acceptance Criteria와 테스트에 연결했다.
- Acceptance Criteria:
  - [x] 네 명령의 `--help`와 잘못된 인자 동작이 명확하다.
  - [x] command 실행 후 400ms 이내 `STARTING`이 stderr에 나타난다.
  - [x] 최종 stdout에는 retry·fallback count와 첫 오류 code만 요약된다.
  - [x] detailed attempt는 stderr와 SQLite에, JSON에는 run 집계·source provenance로 보존된다.
  - [x] canary secret·Authorization 값과 사용자 이름을 포함한 로컬 절대 경로가 stdout·stderr·오류 출력에 노출되지 않는다.
  - [x] 종료 코드 `0`, `2`, `3`, `4`, `5`, `130`이 문서와 일치한다.
  - [x] `NO_COLOR`·non-TTY·80 columns에서 상태 의미와 핵심 값이 유지된다.
- Document Sync Check:
  - [x] 실제 `--help`·snapshot을 UI 문서·Preview와 대조했다.
  - [x] Typer help frame과 analyzer 미구현 경계를 의도된 차이로 기록했다.

### [x] TASK-006: DEX vertical slice 구현

- Status: Done
- Priority: V1 · High
- Depends On: TASK-002, TASK-003, TASK-004
- Requirement IDs: `REQ-P0-EVM-001`~`REQ-P0-EVM-008`,
  `REQ-V1-DEX-001`~`REQ-V1-DEX-006`
- Atomic Tasks:
  - [x] TX·receipt·Transfer·Swap·Withdrawal raw 증거를 수집한다.
  - [x] internal native ETH call을 별도 call evidence로 정규화한다.
  - [x] USDC input과 WETH pool output을 exact raw로 복원한다.
  - [x] WETH pool output과 native ETH user output을 분리한다.
  - [x] router·factory·pair metadata를 supporting provenance로 분리한다.
  - [x] partial·failed에서 확보 증거와 누락 요구사항을 보존한다.
  - [x] `FX-SVC-DEX-001` regression을 자동화한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - SVC-DEX 문제 조건
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - DEX vertical slice 선정
- Related UI Docs:
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - DEX result 3행 구분
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - DEX complete 기준 화면
- Related Technical Docs:
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - DEX exact-match 계약
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - DEX request·result model
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - RPC·explorer·DEX metadata
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-DEX-*`
  - [DEX fixture](../05_QA_Validation/fixtures/FX-SVC-DEX-001/README.md) - confirmed 정답·증거
  - [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - raw decode·정합·partial·resume·보안 증거
- Implementation Preconditions:
  - [x] DEX 요구사항·fixture·source 문서를 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview에서 pool output과 user output 분리를 확인했다.
  - [x] TX·event·call·metadata 최소 필드를 확인했다.
  - [x] 외부 mutation 없이 read-only 수집만 수행한다.
  - [x] raw amount에 float를 사용하지 않는다.
  - [x] 일반 N-hop·가격·범용 DEX 지원을 범위에 넣지 않는다.
- Acceptance Criteria:
  - [x] USDC `25000000000` raw input이 exact match한다.
  - [x] WETH `14449515027026387018` raw pool output이 exact match한다.
  - [x] native ETH `14449515027026387018` raw user output이 exact match한다.
  - [x] pool WETH와 user native ETH가 별도 result·evidence로 출력된다.
  - [x] JSON·Markdown과 terminal summary가 같은 세 결과를 표시한다.
  - [x] 한 필수 증거 누락 주입 시 complete가 아니라 partial이다.
- Document Sync Check:
  - [x] 실제 DEX result·evidence ID를 Schema 예제·QA와 대조했다.
  - [x] fixture 정답 변경 없이 raw replay adapter로 구현 차이를 해결했다.

### [x] TASK-007: AUTH vertical slice 구현

- Status: Done
- Priority: V1 · High
- Depends On: TASK-002, TASK-003, TASK-004
- Requirement IDs: `REQ-P0-EVM-001`~`REQ-P0-EVM-008`,
  `REQ-V1-AUTH-001`~`REQ-V1-AUTH-007`
- Atomic Tasks:
  - [x] Approval event와 approve calldata의 owner·spender·amount를 정합한다.
  - [x] 네 historical block의 allowance를 archive source에서 조회한다.
  - [x] 성공 trace의 `transferFrom`과 Transfer event를 연결한다.
  - [x] allowance 감소와 `4500000` raw 소비를 exact 정합한다.
  - [x] receipt status 0인 중간 거래 3개를 소비에서 제외한다.
  - [x] event·call·state evidence를 분리한다.
  - [x] 피싱·탈취 귀속을 `not_assessed`로 출력한다.
  - [x] `FX-EVM-AUTH-001` regression을 자동화한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - AUTH 권한 소비 문제 조건
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - AUTH vertical slice 선정
- Related UI Docs:
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - AUTH complete·partial·not assessed와 FB-001
  - [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - AUTH 정보량 피드백
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - AUTH partial·resume 화면
- Related Technical Docs:
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - AUTH exact-match·범위 계약
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - AUTH request·result model
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - archive·trace·explorer source
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-AUTH-*`
  - [AUTH fixture](../05_QA_Validation/fixtures/FX-EVM-AUTH-001/README.md) - confirmed 정답·증거
  - [TASK-007 AUTH 보고서](../05_QA_Validation/11_TASK_007_AUTH_REPORT.md) - 실제 raw replay·정합·partial·resume 증거
- Implementation Preconditions:
  - [x] AUTH 요구사항·fixture·source 문서를 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview의 partial·retry·resume와 FB-001을 확인했다.
  - [x] event·call·state·failed TX 최소 필드를 확인했다.
  - [x] external mutation 없이 historical read만 수행한다.
  - [x] archive·trace unavailable의 partial 기준을 확인했다.
  - [x] 피해·피싱·탈취를 자동 단정하지 않는다.
- Acceptance Criteria:
  - [x] 승인과 allowance 네 지점이 fixture와 exact match한다.
  - [x] 성공 소비·Transfer·allowance delta가 `4500000` raw로 일치한다.
  - [x] 실패 거래 3개가 결과에서 제외되고 실패 사실은 보존된다.
  - [x] theft·phishing은 `not_assessed`이며 victim 문구를 사용하지 않는다.
  - [x] archive state 누락 주입 시 확보한 승인 결과를 가진 partial이다.
  - [x] resume에서 기존 evidence ID와 완료 artifact를 재사용한다.
- Document Sync Check:
  - [x] FB-001을 CLI `SCOPE`·QA에 반영했다.
  - [x] 실제 AUTH 결과를 fixture·Schema 예제·문제은행 표현과 대조했다.

### [x] TASK-008: FREEZE vertical slice 구현

- Status: Done
- Priority: V1 · High
- Depends On: TASK-002, TASK-003, TASK-004
- Requirement IDs: `REQ-P0-EVM-001`~`REQ-P0-EVM-008`,
  `REQ-V1-FREEZE-001`~`REQ-V1-FREEZE-008`
- Atomic Tasks:
  - [x] blacklist·unBlacklist calldata와 event를 분리 수집한다.
  - [x] 네 historical block의 `isBlacklisted` 상태를 조회한다.
  - [x] false→true와 true→false 전이를 exact 정합한다.
  - [x] 주소 blacklist와 global pause를 구분한다.
  - [x] Circle·OFAC 공식 URL의 원문·주소 명시 여부를 context로 보존한다.
  - [x] 온체인 상태와 공식 맥락·현재 제재·범죄 의도를 분리한다.
  - [x] restricted 정책에서 네트워크 전 차단한다.
  - [x] `FX-EVM-FREEZE-001` regression을 자동화한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - FREEZE 문제 조건
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - FREEZE vertical slice 선정
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 규정 차단과 실패 흐름
  - [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 온체인·맥락·미평가 표현
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - FREEZE rule blocked 화면
- Related Technical Docs:
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - FREEZE exact-match·OSINT 경계
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - FREEZE request·result model
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - archive·explorer·공식 source
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - `QA-FREEZE-*`, `QA-RULE-*`
  - [FREEZE fixture](../05_QA_Validation/fixtures/FX-EVM-FREEZE-001/README.md) - confirmed 정답·증거
  - [TASK-008 FREEZE 보고서](../05_QA_Validation/12_TASK_008_FREEZE_REPORT.md) - raw replay·상태 전이·context·partial·resume 증거
- Implementation Preconditions:
  - [x] FREEZE 요구사항·fixture·source 문서를 다시 확인했다.
  - [x] HTML Preview 사용자 확인과 피드백 기록을 확인했다.
  - [x] HTML Preview의 rule blocked와 not assessed 표현을 확인했다.
  - [x] event·call·state·context 최소 필드를 확인했다.
  - [x] 입력 URL 수집 외 일반 OSINT 탐색을 하지 않는다.
  - [x] 규정 상태와 source policy를 실행 전에 확인한다.
  - [x] 현재 제재·범죄 의도를 자동 판정하지 않는다.
- Acceptance Criteria:
  - [x] false→true와 true→false 전이·네 state가 exact match한다.
  - [x] event·call·state·context가 서로 다른 evidence type이다.
  - [x] Circle과 OFAC의 주소 명시 여부가 각각 보존된다.
  - [x] current sanctions와 criminal intent가 `not_assessed`다.
  - [x] restricted 정책에서 source attempt와 network call이 0건이다.
  - [x] 한 전이만 확보하면 complete가 아니라 partial이다.
- Document Sync Check:
  - [x] 실제 context source와 라이선스·조회 시각을 등록부와 대조했다.
  - [x] FREEZE 결과를 fixture·Schema 예제·UI와 동기화했다.

### [x] TASK-009: 통합 회귀·보안·문서 동기화 Gate

- Status: Done
- Priority: V1 · High
- Depends On: TASK-005, TASK-006, TASK-007, TASK-008
- Requirement IDs: `REQ-NFR-001`~`REQ-NFR-008`, `TEST-SCHEMA-001`,
  `TEST-CACHE-001`, `TEST-RETRY-001`, `TEST-FALLBACK-001`,
  `TEST-EXPORT-001`, `TEST-DEX-001`, `TEST-AUTH-001`, `TEST-FREEZE-001`
- Atomic Tasks:
  - [x] unit·integration·regression suite를 네트워크 없이 실행한다.
  - [x] confirmed fixture 3개 exact-match를 반복 실행한다.
  - [x] cold·warm·resume와 400ms 첫 피드백을 측정한다.
  - [x] timeout·429·5xx·malformed JSON·정합 실패를 주입한다.
  - [x] secret·로컬 절대 경로·private key 문구를 scan한다.
  - [x] JSON·Markdown·terminal result 값을 교차 비교한다.
  - [x] UI Preview와 실제 CLI snapshot 차이를 검토한다.
  - [x] 365 rubric·Originality·Ethics와 공식 규정 상태를 기록한다.
- Related Concept Docs:
  - [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 빠르고 정확한 문제 해결 목표
  - [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1 완료 기준
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 전체 사용자 흐름
  - [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - 사용자 확인·FB-001
- Related HTML Preview:
  - [CLI Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 실제 CLI snapshot 비교 기준
- Related Technical Docs:
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - PR 완료·보안·테스트 Gate
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 전체 완료 기준
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 계약·참조 무결성
- Related QA Docs:
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 통합 실행 기준
  - [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed fixture 상태
  - [TASK-009 통합 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) - 결정성·오류 행렬·추적성·보안 증거
- Implementation Preconditions:
  - [x] 모든 선행 작업과 관련 문서를 다시 확인했다.
  - [x] HTML Preview·사용자 확인·FB-001 반영 여부를 확인했다.
  - [x] 전체 데이터 흐름·상태·오류·resume 경계를 확인했다.
  - [x] live test는 명시적 opt-in이며 기본 suite는 network 0건이다.
  - [x] 공식 규정·dependency·source license 상태를 확인했다.
  - [x] 미완료 항목을 성공으로 표시하지 않는다.
- Acceptance Criteria:
  - [x] lint·format·unit·integration·regression이 모두 통과한다.
  - [x] fixture·analysis Schema 검증이 `PASS 3`이다.
  - [x] DEX·AUTH·FREEZE exact-match와 오류 주입 시나리오가 통과한다.
  - [x] secret·인증 header·로컬 사용자 절대 경로가 0건이다.
  - [x] actual CLI와 Preview의 의도하지 않은 차이가 0건이다.
  - [x] 문서·코드·Schema·fixture version이 서로 일치한다.
- Document Sync Check:
  - [x] 구현 완료 상태를 Backlog·QA·기술 문서에 동기화했다.
  - [x] 잔여 위험·미평가·공식 규정 제한을 최종 보고서에 기록했다.

### [ ] TASK-010: AI-native Rules-gated 병렬 문제풀이 Operations 구현

- Status: Offline V1 Complete · OPS-IMPL-01~08 Done · Live Rules-Gated
- Work Type: code
- Priority: Tournament Operations · Conditional
- Depends On: TASK-005, TASK-009, Operations Board Preview 승인;
  live AI mode만 공식 Rules 확인 필요
- Requirement IDs: `REQ-OPS-IN-001`~`REQ-OPS-IN-004`,
  `REQ-OPS-QUEUE-001`~`REQ-OPS-QUEUE-006`,
  `REQ-OPS-VERIFY-001`~`REQ-OPS-VERIFY-006`,
  `REQ-OPS-SUBMIT-001`~`REQ-OPS-SUBMIT-004`
- Atomic Tasks:
  - [x] problem·job·analysis·verification·candidate ID와 상태 model을 정의한다.
  - [ ] AI Planner/Coordinator를 모든 문제의 필수 planning 단계로 구현한다.
  - [x] Rules Gate가 AI 사용 여부가 아니라 provider·model·data·tool mode를 선택하게 한다.
  - [x] AI가 해결 방법·leaf dependency·도구 계획을 구조화된 hypothesis로 생성하게 한다.
  - [ ] problem Queue와 dependency-aware job Queue를 분리한다.
  - [ ] AI Planner/Coordinator·EVM·Tracer·OSINT·Verifier·Reporter role adapter를 정의한다.
  - [x] AI plan에 따라 human-approved Python worker가 evidence job을 실행하게 한다.
  - [x] 문제 간 workspace·result·checkpoint를 격리한다.
  - [x] candidate의 problem·plan·job·Analysis 참조를 교차 문제에서 격리한다.
  - [x] 문제 내부 독립 leaf job을 제한된 동시성으로 실행한다.
  - [x] source request idempotency·in-flight dedup·capability별 concurrency budget을 구현한다.
  - [x] worker 실패를 해당 job·dependency에만 전파한다.
  - [x] conflict·missing evidence·self-check를 `review_required`로 보낸다.
  - [x] 독립 Verifier가 raw evidence를 재조회한 뒤에만 candidate를 승격한다.
  - [x] Operations Board의 problem·worker·verification·submission 상태를 read-only snapshot으로 연결한다.
  - [x] 답 전체 복사와 사람 `Mark submitted`를 분리한다.
  - [x] CTFd 자동 제출·credential·session·brute force 경로가 없음을 검증한다.
  - [x] 6개 Agentic Parallel Solve QA 시나리오를 자동화한다.
- Related Concept Docs:
  - [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 대회 당일 병렬 운영과 사람 제출 원칙
  - [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - AI·agent·자동화·문제 데이터 전송·제출 Gate
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - leaf 분석 기능과 단계 제한
- Related UI Docs:
  - [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 전체 문제·worker·검증·제출 화면
  - [Web Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - 선택한 leaf result의 증거 검토
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - leaf 실행·partial·resume 계약
- Related HTML Preview:
  - [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - 구현 전 사용자 확인 화면
  - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - evidence drill-down 경계
- Related Technical Docs:
  - [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - 역할·상태·Queue·검증·수동 제출 규범
  - [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - 최소 필드·mutation·SQLite v2·동시성·구현 분할 제안
  - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - leaf 분석 단일 source of truth
  - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - Python core·source·cache·evidence 계약
- Related QA Docs:
  - [Agentic Parallel Solve QA](../05_QA_Validation/03_AGENTIC_PARALLEL_SOLVE_QA.md) - 병렬성·격리·독립 검증·규정·수동 제출
  - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - leaf 분석 24개 기존 기준선
  - [OPS-IMPL-05 Evidence Worker 보고서](../05_QA_Validation/18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md) - 세 vertical·Queue·workspace·artifact·checkpoint 검증
  - [OPS-IMPL-06 Candidate·Verifier 보고서](../05_QA_Validation/19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md) - canonical answer·fresh replay·conflict·promotion Gate 검증
  - [OPS-IMPL-07 OperationsSnapshot 보고서](../05_QA_Validation/20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md) - SQLite read-back·strict snapshot·local view 검증
  - [OPS-IMPL-08 Final Integration 보고서](../05_QA_Validation/21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) - 사람 제출·leaf 병렬·보안·6개 offline 운영 QA
- Component & Library Plan:
  - shadcn/ui: N/A - OPS-IMPL-08은 승인된 HTML Preview를 바꾸지 않는 Python local runtime이다.
  - Custom components: strict `OperationsSnapshot`, terminal/JSON renderer, SQLite v2 read-back, human-confirmed submission recorder.
  - Reused components: Pydantic v2 contract model, Typer CLI, stdlib `sqlite3`·`hashlib`, 기존 Operations contract validator.
  - New libraries: 없음 - 승인된 dependency와 lockfile을 유지한다.
  - Excluded libraries: React graph/table·웹 상태관리·CTFd SDK - 웹 runtime과 자동 제출은 후속 별도 범위다.
  - State management: persisted OperationsDocument를 검증한 뒤 immutable snapshot 한 개를 terminal/JSON에 공통 투영한다.
  - shadcn preset: N/A - UI component 구현이 아닌 local CLI projection이다.
- Implementation Preconditions:
  - [x] 관련 Concept·UI·Preview·Technical·QA 문서를 다시 읽었다.
  - [x] Operations Board Preview를 사용자가 확인하고 피드백을 승인했다.
  - [x] TASK-010 Pre-Code Technical Brief를 검토·승인했다.
  - [ ] 공식 Rules에서 AI Planner용 provider·model·data·사전 도구 mode를 확인했다.
  - [x] 필수 AI Planner·role·Python evidence worker 구조를 승인했다.
  - [ ] 공식 Rules에 따라 실제 활성화할 source·AI mode를 승인했다.
  - [x] 운영 manifest·verification·candidate 최소 필드와 mutation을 승인했다.
  - [x] Draft 1 offline QA concurrency 기본값을 승인했다.
  - [ ] live job·provider·AI worker concurrency budget을 측정·승인했다.
  - [x] loading·empty·partial·failed·stale·rules unavailable 상태를 확인했다.
  - [x] CTFd credential·자동 제출·brute force가 범위 밖임을 확인했다.
  - [x] `OPS-IMPL-01` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-02` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-03` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-04` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-05` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-06` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-07` 구현 착수를 별도로 승인받았다.
  - [x] 후속 `OPS-IMPL-08` 구현 착수를 별도로 승인받았다.
- Acceptance Criteria:
  - [x] 두 개 이상의 문제를 동시에 처리하며 상태·결과·candidate가 격리된다.
  - [ ] 모든 문제에 AI method hypothesis와 승인된 leaf job plan이 존재한다.
  - [x] AI 자연어 답·confidence만으로 candidate가 `submission_ready`가 되지 않는다.
  - [x] AI plan을 Python 도구로 실행한 result·evidence가 candidate의 결정적 필드와 연결된다.
  - [x] 한 문제의 독립 leaf 두 개 이상이 병렬 실행되고 dependency 뒤에 정합된다.
  - [x] 동일 source request가 dedup되고 provider 동시성 제한을 초과하지 않는다.
  - [x] worker 하나의 실패가 다른 문제의 완료·제출 상태를 변경하지 않는다.
  - [x] 독립 검증 없는 후보와 충돌 후보가 `submission_ready`가 아니다.
  - [x] Operations Board snapshot과 persisted operations·candidate·verification 참조가 일치한다.
  - [x] CTFd network call·credential 저장·brute force가 0건이다.
  - [x] 6개 운영 QA의 구현된 범위가 통과하고 미실행 항목은 명시된다.
- Document Sync Check:
  - [x] OPS-IMPL-07 read model·상태 label·CLI·SQLite read-back을 UI·기술·QA 문서와 동기화했다.
  - [x] OPS-IMPL-08 leaf concurrency·submission record·security Gate를 동기화했다.
  - [ ] Rules 변경 시 활성 role·source·fallback과 Known Issue를 갱신했다.
  - [ ] Preview와 실제 Operations UI의 의도하지 않은 차이가 0건이다.
- Context Receipt:
  - Status: PASS
  - Required References Read:
    - [참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 대회 당일 병렬 운영과 사람 제출 경계를 확인했다.
    - [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - AI mode와 CTFd 자동 제출 제한을 확인했다.
    - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - leaf 분석 기능과 단계 제한을 확인했다.
    - [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 화면 정보 계층과 상태 label을 확인했다.
    - [Web Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - evidence drill-down 경계를 확인했다.
    - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - local 실행·partial·resume 계약을 확인했다.
    - [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - 승인된 Board 구성을 확인했다.
    - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - read-only evidence 화면 경계를 확인했다.
    - [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - role·Queue·검증·수동 제출 규범을 확인했다.
    - [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - snapshot·command·SQLite·동시성 계약을 확인했다.
    - [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - leaf 결과 단일 진실 원천을 확인했다.
    - [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - source·cache·evidence 불변조건을 확인했다.
    - [Agentic Parallel Solve QA](../05_QA_Validation/03_AGENTIC_PARALLEL_SOLVE_QA.md) - 병렬성·격리·Verifier·수동 제출 기준을 확인했다.
    - [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 기존 leaf 회귀 기준선을 확인했다.
    - [OPS-IMPL-05 Evidence Worker 보고서](../05_QA_Validation/18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md) - replay pin·workspace 경계를 확인했다.
    - [OPS-IMPL-06 Candidate·Verifier 보고서](../05_QA_Validation/19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md) - candidate·fresh replay 승격 기준을 확인했다.
    - [OPS-IMPL-07 OperationsSnapshot 보고서](../05_QA_Validation/20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md) - 구현 범위와 검증 결과를 확인했다.
    - [OPS-IMPL-08 Final Integration 보고서](../05_QA_Validation/21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) - 수동 제출·병렬성·보안·최종 offline Gate를 확인했다.
  - Constraints:
    - 동일 validated snapshot이 terminal과 JSON의 유일한 입력이어야 한다.
    - live AI·RPC·CTFd·사용자 DB 자동 migration과 mutation은 포함하지 않는다.
    - candidate 전체 답은 보존하되 independent verification 없이 submission-ready로 승격하지 않는다.
  - Conflicts: None
- Change Receipt:
  - Files Changed:
    - `src/scan_tool/application/operations_snapshot.py`
    - `src/scan_tool/application/operations_terminal.py`
    - `src/scan_tool/adapters/sqlite_operations.py`
    - `src/scan_tool/application/candidate_verifier.py`
    - `src/scan_tool/cli.py`
    - `src/scan_tool/application/submission.py`
    - `src/scan_tool/adapters/evidence.py`
    - `src/scan_tool/application/evidence_worker.py`
    - `tests/integration/test_operations_snapshot.py`
    - `tests/integration/test_candidate_verifier.py`
    - `tests/integration/test_evidence_worker.py`
    - `tests/integration/test_submission_flow.py`
    - OPS-IMPL-07 관련 UI·기술·Backlog·QA 문서
  - Requirements Covered:
    - SQLite v2 read-back, strict Board snapshot, terminal/JSON 공통 projection, 상태·격리·안전한 CLI.
    - OPS-IMPL-06 chain·교차 문제·dual-label·adapter/response P2 회귀.
    - OPS-IMPL-08 같은 문제 leaf 병렬·복합 alert·SQLite Board·사람 제출 기록·6개 offline QA.
  - Excluded Scope:
    - live provider·웹 runtime·priority/pause/reassign mutation·CTFd network 제출.
  - Basic Checks:
    - `uv run python scripts/verify.py` - PASS - 271 tests, Schema·fixture·traceability·security Gate 통과.
    - 변경 핵심 integration 묶음 - PASS - 64 passed.
  - Remaining Risks:
    - SQLite v2 candidate reference 순서는 insertion rowid에 의존하며 ordinal은 차기 명시적 migration 대상이다.
- Verification Receipt:
  - Status: PASS
  - Commands and Results:
    - `uv run python scripts/verify.py` - PASS - 271 tests, fixture·Analysis·Operations Schema, traceability, security 통과.
    - 변경 핵심 integration 묶음 - PASS - 64 passed.
    - `uv run pytest tests/integration/test_submission_flow.py -q` - PASS - 9 passed.
    - `git diff --check` - PASS - whitespace 오류 없음.
  - Unrun Checks:
    - N/A - 웹 runtime·live provider·CTFd network 제출·실대회 성능·DDL migration은 OPS-IMPL-08 승인 범위 밖이다.
  - Detailed Evidence:
    - [OPS-IMPL-08 Final Integration 보고서](../05_QA_Validation/21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) - 독립 검증 명령·local submission·병렬성·보안·잔여 P2 기록.

### [x] TASK-011: 예상문제 Offline Benchmark 0.1

- Status: Done · 3 Automated Pass / 6 Assisted / 21 Unsupported
- Work Type: code
- Priority: Coverage Validation · High
- Depends On: TASK-006, TASK-007, TASK-008, TASK-009
- Requirement IDs: `TEST-DEX-001`, `TEST-AUTH-001`, `TEST-FREEZE-001`,
  `REQ-NFR-001`, `REQ-NFR-003`, `REQ-NFR-004`, `REQ-NFR-007`
- Atomic Tasks:
  - [x] 예상문제 은행 Draft 2의 30문항 ID를 manifest에 한 번씩 등록한다.
  - [x] `automated / assisted / unsupported` 판정 기준을 고정한다.
  - [x] confirmed DEX·AUTH·FREEZE를 실제 raw replay로 두 번 실행한다.
  - [x] result value exact match·evidence ref·fixture requirement·결정성을 채점한다.
  - [x] 잘못된 answer oracle이 benchmark 실패로 판정되는지 검증한다.
  - [x] benchmark 경로가 저장소 밖으로 이탈하지 못하게 한다.
  - [x] CLI 실행 중 network call이 0건인지 검증한다.
  - [x] 30문항 coverage와 기능 공백을 QA 보고서에 기록한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - Draft 2 30문항과 완료·부분·실패 기준
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 기능별 빈도와 단계 제한
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - offline 명령·오류·출력 경계
- Related HTML Preview:
  - N/A - 기존 CLI에 QA 전용 summary 명령을 추가하며 새로운 사용자 화면·동선은 만들지 않는다.
- Related Technical Docs:
  - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - fixture-first·offline·최소 구현 기준
  - [공통 Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 자동 사례의 result·evidence 계약
- Related QA Docs:
  - [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed DEX·AUTH·FREEZE oracle
  - [예상문제 Offline Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - coverage·채점·공백 결과
- Component & Library Plan:
  - shadcn/ui: N/A - Python CLI benchmark이며 웹 UI를 변경하지 않는다.
  - Custom components: Pydantic manifest·runner·terminal/JSON summary.
  - Reused components: Analysis I/O validator, DEX·AUTH·FREEZE slice, Typer, confirmed fixture.
  - New libraries: 없음 - Pydantic·Typer·stdlib `json/pathlib/time`만 재사용한다.
  - Excluded libraries: benchmark framework·dataframe·statistics package - 30개 manifest와 3개 실행에는 불필요하다.
  - shadcn preset: N/A - UI 변경 없음.
- Implementation Preconditions:
  - [x] 사용자가 예상문제 실실행 benchmark를 승인했다.
  - [x] 예상문제 은행 30문항과 Challenge Pack 경계를 다시 확인했다.
  - [x] 현재 공개 Analysis type이 세 종류뿐임을 확인했다.
  - [x] confirmed fixture 외 문제의 정확도를 주장하지 않기로 했다.
  - [x] 입력은 reviewed repository fixture만 사용하고 live source를 호출하지 않는다.
  - [x] 새 화면이 없어 기존 CLI UI 경계와 terminal summary만 확인했다.
- Acceptance Criteria:
  - [x] manifest가 30개 고유 문제 ID를 포함한다.
  - [x] automated 3·assisted 6·unsupported 21 집계가 일치한다.
  - [x] automated 3개가 complete·answer exact·evidence·requirement·determinism을 통과한다.
  - [x] assisted·unsupported는 자동 성공률에 포함되지 않는다.
  - [x] benchmark CLI의 network call이 0건이다.
  - [x] 오류 oracle과 저장소 밖 path가 거부된다.
- Document Sync Check:
  - [x] 예상문제 은행·Backlog·Roadmap·README·QA 보고서를 동기화했다.
  - [x] 30문항 자동화율 10%와 기능 공백을 과장 없이 기록했다.
- Context Receipt:
  - Status: PASS
  - Required References Read:
    - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항 ID·난이도·기능 행렬을 확인했다.
    - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 원자적 기능과 Challenge Pack을 확인했다.
    - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - CLI 안전 출력 경계를 확인했다.
    - [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 최소 구현·fixture-first 기준을 확인했다.
    - [공통 Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - result·evidence 참조 계약을 확인했다.
    - [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed oracle 범위를 확인했다.
    - [예상문제 Offline Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 채점 결과와 잔여 공백을 확인했다.
  - Constraints:
    - 새 vertical·live adapter·fixture 정답을 만들지 않는다.
    - confirmed fixture가 없는 문제는 automated로 분류하지 않는다.
    - 실행 시간은 관찰값이며 SLA로 주장하지 않는다.
  - Conflicts: None
- Change Receipt:
  - Files Changed:
    - `src/scan_tool/application/expected_problem_benchmark.py`
    - `src/scan_tool/cli.py`
    - `docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json`
    - `tests/integration/test_expected_problem_benchmark.py`
    - 예상문제·Roadmap·Backlog·README·QA 보고서
  - Requirements Covered:
    - 30문항 coverage 분류, confirmed 3개 exact/evidence/requirement/determinism 채점, offline CLI.
  - Excluded Scope:
    - 새 analyzer, live source, Challenge Pack fixture, 실제 대회 처리량.
  - Basic Checks:
    - `uv run pytest tests/integration/test_expected_problem_benchmark.py -q` - PASS - 6 passed.
    - `uv run scan benchmark ...` - PASS - automated 3/3, network calls 0.
  - Remaining Risks:
    - assisted 6개와 unsupported 21개에는 reference fixture·전용 analyzer가 없다.
- Verification Receipt:
  - Status: PASS
  - Commands and Results:
    - `uv run python scripts/verify.py` - PASS - 277 tests와 Schema·traceability·security Gate.
    - expected-problem benchmark integration - PASS - 6 passed.
    - benchmark CLI - PASS - automated 3/3, assisted 6, unsupported 21.
    - `git diff --check` - PASS.
  - Unrun Checks:
    - N/A - live source·Challenge Pack·실대회 성능은 TASK-011 범위 밖이다.
  - Detailed Evidence:
    - [예상문제 Offline Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 채점 기준·30문항 coverage·우선 공백.

### [x] TASK-012: 범용 EVM Query·State·Transfer 엔진

- Status: Done
- Work Type: code
- Priority: Phase 2 · P0
- Depends On: TASK-011
- Common Input Gate: `WP-INPUT-IMPL-02` CLI·Evidence Worker wiring done
- Target Problems: `BASIC-EVM-001/002`, `EVM-TOKEN-001/002`
- Atomic Tasks:
  - [x] 네 문제의 공개 사례·reference answer·partial 조건을 확정한다.
    - [x] 후보 패키지 4개와 1차 재조회 결과를 작성했다.
    - [x] live provider 후보 topology·secret·capability smoke 계약을 문서화했다.
    - [x] 기본 network 0건·Rules/endpoint opt-in smoke runner를 준비했다.
    - [x] QuickNode primary 공통 6개+trace와 Alchemy verifier 공통 6개
      read-only smoke를 실행했다.
    - [x] 네 fixture의 공통 9개 조회를 QuickNode·Alchemy에서 독립 재현하고
      decoded 값 일치를 확인해 `verifying`으로 승격했다.
    - [x] 네 fixture의 합성 negative oracle 24개를 두 번 실행해 결정성을 확인했다.
    - [x] 독립 Trace 두 dialect 정규화·교차 동등성과 timeout·429·
      method-not-found(`invalid_response`)·malformed offline 주입 검증을 통과했다.
    - [x] Alchemy 두 dialect를 live 실행했으나 모두 HTTP 400 `permanent`로
      실패해 해당 endpoint를 독립 Trace 역할에서 제외했다.
    - [ ] 노출 credential 회전·live rate/timeout은 live 운영 Gate로 유지한다.
    - [x] 독립 trace는 fixture 승격의 비차단 후속으로 두고
      QuickNode 단일 Trace provenance를 명시한다.
    - [x] offline oracle과 필수 source Gate를 만족한 fixture의 승격 수준을
      provenance 정책에 따라 결정한다.
  - [x] TX·receipt·block·historical state·ERC-20/native flow 최소 입력을 승인한다.
    - [x] 네 query kind의 최소 입력과 complete·partial·failed 결과 제안
      12개를 작성했다.
    - [x] 제안 필드와 오류 매핑을 사용자 승인 후 정식 계약으로 고정한다.
  - [x] 기존 source/cache/decode/reconciliation을 재사용한 Analysis type을 승인한다.
    - [x] 격리된 `evm_core` `0.2-draft`와
      `object_summary`·`historical_balance`·`first_token_transfer`·
      `native_inflow` query kind를 제안했다.
    - [x] 제안 Schema 14개 probe와 12개 사례를 검증하고 기존 Analysis I/O
      `0.1`·runtime `AnalysisType` 비변경을 검사했다.
    - [x] Analysis I/O 0.2·runtime model을 승인하고 DDL migration 불필요를 확인했다.
  - [x] complete·partial·failed와 negative oracle을 구현·검증한다.
  - [x] 네 문제의 Benchmark 승격 여부를 독립 검증한다.
  - [x] `external_rpc | contest_rpc | provided_artifact` 중 허용 입력을
    normalized evidence로 연결한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 직접 대상 4문항
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - EVM-TX/STATE/LOG/TRACE 우선 근거
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 공통 analyze·partial·failed 흐름
  - [TASK-012 EVM Core UI](../02_UI_Screens/05_TASK_012_EVM_CORE_UI.md) - 4 query·12개 상태·입력·다음 행동
- Related HTML Preview:
  - [CLI Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 기존 terminal 결과 구조
  - [TASK-012 EVM Core Preview](../02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html) - 0.2 Draft 전용 사용자 검토 화면
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-EVM-CORE 계약
  - [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - Schema 변경 Gate
  - [오픈소스 조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - build/wrap 결정
  - [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - archive·logs·trace·AI Planner 선행 Gate
  - [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - `WP-INPUT-GATE`·contest RPC·artifact·체인별 경계
  - [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - `evm_core` 0.2 Draft·12개 사례·14개 probe·0.1 비변경
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-EVM-001/002
  - [Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - Assisted 4개 기준선
  - [TASK-012 Fixture 후보 보고서](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 후보 4개·reference answer·source 장애
  - [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 smoke·secret·독립성·반례
  - [TASK-012 Negative Oracle 보고서](../05_QA_Validation/27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 24개 offline 반례·결정성
  - [Smoke Runner 준비 보고서](../05_QA_Validation/26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) - 미실행 경계·unit·dry-run
  - [TASK-012 UI Preview 보고서](../05_QA_Validation/28_TASK_012_UI_PREVIEW_REPORT.md) - 자동·브라우저·사용자 Gate
  - [TASK-012 Provider Gate 준비 보고서](../05_QA_Validation/29_TASK_012_PROVIDER_GATE_PREPARATION_REPORT.md) - 독립 Trace dialect·offline failure Gate
- Implementation Preconditions:
  - [x] 관련 문서와 네 문제의 입력·출력·상태를 확인한다.
  - [x] primary·independent 일반 RPC와 primary trace capability smoke를 통과한다.
    - [x] primary·independent 공통 6개 decoded summary 일치와 primary trace 성공을 확인했다.
    - [x] 독립 Trace dialect·provider failure offline 검증을 통과했다.
    - [ ] credential 회전·live rate/timeout은 live 운영 Gate에 남아 있다.
    - [x] contest RPC core adapter·bounded artifact importer 구현 승인을 기록했다.
    - [x] TASK-012 analyzer의 reviewed replay consumer wiring을 구현했다.
  - [x] API key·endpoint가 저장소·DB·fixture·로그에 없음을 검증한다.
  - [x] confirmed fixture와 reference answer를 확보한다.
  - [x] CLI Preview 재검토와 사용자 UI 승인을 기록한다.
    - [x] TASK-012 전용 UI 문서·HTML Preview·정적 checker를 작성했다.
    - [x] 브라우저에서 12개 조합·방향키·모바일·console을 검증했다.
    - [x] 사용자 Preview 확인과 P2 2건 반영을 기록했다.
  - [x] TASK-012 제품 analyzer 구현 승인을 기록한다.
  - [x] CLI 진입·complete·partial·failed와 checkpoint resume를 확인한다.
  - [x] source 최소 필드·mutation 없음·checkpoint 상태 관리를 승인한다.
  - [x] Analysis I/O 0.2·source·storage DDL 무변경 영향을 승인한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python CLI leaf 분석기다.
  - Custom components: 범용 EVM request/analyzer/result projector.
  - Reused components: source port, cache, artifact, checkpoint, terminal renderer.
  - New libraries: N/A - OSS bake-off 전 설치 금지.
  - Libraries intentionally not added: graph DB·dataframe - 이 task에 불필요.
  - shadcn preset: N/A - 웹 UI 변경 없음.
- Acceptance Criteria:
  - [x] 네 fixture의 exact answer·evidence·determinism이 통과한다.
  - [x] archive/trace/range 누락과 malformed replay가 partial/failed로 보존된다.
  - [x] 입력 기대값 복사 없이 raw evidence에서 계산한다.
  - [x] Benchmark가 실제 승격 수 7만 반영한다.
- Document Sync Check:
  - [x] Analysis I/O·CLI·fixture·Benchmark·QA 문서를 동기화한다.
- Context Receipt:
  - Status: PASS - confirmed 4개·공통 RPC 재현·offline oracle 24개·
    계약 사례 12개·Analysis I/O 0.2 40개 probe·공통 입력 wiring 확인
  - Required References Read: 위 Related 문서 전체
  - Constraints: exact raw 수량, historical state block 고정, 귀속 미평가
  - Conflicts: None known
- Change Receipt:
  - `evm_core` request/replay/analyzer·CLI dispatcher·Operations enum 추가
  - Analysis I/O 0.2와 기존 0.1 호환, SQLite v2 DDL·새 dependency 변경 없음
- Verification Receipt:
  - 4 complete·4 partial·4 failed unit, Benchmark 7/7, 전체 offline Gate 통과

### [x] TASK-013: NFT·Proxy 결정적 Decoder

- Status: Done — Analyzer remediation 재검토와 PR #66 병합 완료. Fixture
  3개 `confirmed`, Benchmark automated 9/9. 최종 승격 근거는
  [Receipt](../05_QA_Validation/38_TASK_013_FINAL_PROMOTION_RECEIPT.md)에 고정
- Work Type: code
- Priority: Phase 2 · P1
- Depends On: TASK-012
- Target Problems: `EVM-NFT-001`, `EVM-PROXY-001`
- Atomic Tasks:
  - [x] ERC-721·ERC-1155·EIP-1967 fixture ID와 공개 사례 선정 기준을
    docs-only Draft로 고정한다.
  - [x] event/state/slot decode와 complete·partial·failed 계약 대안을
    docs-only Draft로 작성한다.
  - [x] ERC-721/1155와 EIP-1967 공개 candidate를 선정하고 두 공급자
    receipt/storage 기본 일치를 기록한다.
  - [x] raw/provider replay·capability별 SHA·명시 scope 완전성·raw
    integrity checker를 통과한다.
  - [x] 세 표준의 negative oracle 16개를 두 번 실행해 결정성을 확인한다.
  - [x] 독립 Verifier가 세 candidate의 raw facts·13개 evidence 값·7개
    requirement를 두 번 재계산한다.
  - [x] 세 candidate를 `후보`에서 `검증 중`으로 승격한다(승격은 여전히
    `확정`이 아니다).
  - [x] Analysis I/O 대안 B(`evm_special`)를 확정하고 전용 UI Preview를
    작성한다. 사용자 확인은 아직이다.
  - [x] NFT·Proxy analyzer(`slices/evm_special.py`)를 구현하고 독립
    Verifier와 canonical hash를 대조한다.
  - [x] 리뷰에서 발견한 P1 5건(subject/proxy 결합, receipt·block 정합,
    Schema 교차 조합, fixture 형태 고정, beacon 미구현)과 P2 2건(단일
    provider provenance, 계약 문서 stale 표기)을 수정한다.
  - [x] 리뷰 재현 시나리오를 그대로 반영한 변형 회귀 테스트 6건과
    ERC-1155 Batch subject CLI 통합 테스트를
    추가한다.
  - [x] ERC-721/1155와 EIP-1967 fixture를 `확정`으로 올린다.
  - [x] 두 문제를 Benchmark automated로 승격하고 9/9를 기록한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - NFT·Proxy 문제
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P3 전문 기능 승격 조건
- Related UI Docs:
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - decode 결과·오류 표시
  - [TASK-013 NFT·Proxy UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md) - 표준 3개·상태 3개 화면 계약
- Related HTML Preview:
  - [CLI Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - terminal 결과 기준
  - [NFT·Proxy Preview](../02_UI_Screens/previews/06_task_013_nft_proxy_preview.html) - 사용자 확인 대기 중인 전용 Preview
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-EVM-SPECIAL 계약
  - [TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - NFT·Proxy 표준·상태·오류, 대안 B 확정
  - [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 유형별 결과 확장
  - [오픈소스 조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - ABI·slot 도구 조사
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-SPECIAL-001
  - [TASK-013 Fixture 후보 보고서](../05_QA_Validation/32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 세 package ID·선정·승격 Gate
  - [TASK-013 Negative Oracle 보고서](../05_QA_Validation/33_TASK_013_NEGATIVE_ORACLE_REPORT.md) - 표준별 16개 반례·결정성
  - [TASK-013 독립 Verifier 보고서](../05_QA_Validation/34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md) - raw-first facts·13 evidence values·7 requirements 재계산
  - [TASK-013 Fixture 승격 검토 보고서](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) - `검증 중` 승격 판정
  - [TASK-013 Analyzer 검증 Receipt](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md) - canonical hash 일치(확정 판정은 철회)
  - [TASK-013 Analyzer P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md) - 리뷰 결함·수정·회귀 테스트·승격 철회 근거
  - [TASK-013 최종 승격 Receipt](../05_QA_Validation/38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - confirmed 3·Benchmark 9/9 근거
- Implementation Preconditions:
  - [x] fixture·계약·반례 문서 Draft를 작성한다.
  - [x] TASK-012 공통 EVM 입력이 안정됐다.
  - [x] 공개 candidate 주소·TX·block과 reference answer 골격을 선정한다.
  - [x] 명시 scope replay와 provider provenance를 고정한다.
  - [x] 세 fixture를 `검증 중`으로 승격한다(별도 승격 검토 문서로 판단).
  - [x] Analysis I/O 대안을 B(`evm_special`)로 확정한다.
  - [x] CLI 진입·전환·이탈과 complete·partial·failed 표시를 Preview로
    작성한다. loading·empty·stale·Rules는 기존 CLI 경계를 재사용한다.
  - [x] 사용자가 UI Preview를 확인하고 승인한다(2026-07-29 20:19).
  - [x] log/state 최소 필드·mutation 없음·decode 상태 관리를 analyzer와
    negative oracle로 재확인한다.
  - [x] ERC 표준 문서·기존 `eth-abi`/`eth-utils` 재사용과 신규 dependency
    없음으로 OSS/license 경계를 확인한다.
  - [x] 사용자 구현 승인을 기록한다(2026-07-29 20:19).
- Component & Library Plan:
  - shadcn/ui: N/A - Python CLI 분석기.
  - Custom components: NFT decoder, proxy slot/event resolver.
  - Reused components: EVM logs/state, provenance, artifact, renderer.
  - New libraries: N/A - OSS bake-off 전 설치 금지.
  - Libraries intentionally not added: 범용 ABI framework - fixture 요구 이상 금지.
  - shadcn preset: N/A - 웹 UI 변경 없음.
- Acceptance Criteria:
  - [x] NFT 표준·token ID·amount와 proxy implementation이 raw evidence에 연결된다.
  - [x] 잘못된 표준·slot·block은 decode 실패 또는 partial이다.
  - [x] 두 문제의 automated 승격은 confirmed fixture가 있을 때만 일어난다.
- Document Sync Check:
  - [x] Analysis I/O·fixture·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PASS — 세 fixture가 `검증 중`으로 승격되고(승격 검토 통과),
    Analysis I/O 대안 B가 확정되고, 전용 UI Preview가 작성·브라우저
    검증됐다(방향키·roving tabindex 포함). 사용자가 2026-07-29 20:19
    "TASK-013 UI Preview를 승인합니다. Context Receipt PASS 전환과
    analyzer 구현을 승인합니다." 요청에 "승인합니다"로 명시 승인했다.
  - Required References Read: 예상문제 은행·Coverage Brief·EIP-721/1155/1967·
    [TASK-013 Fixture 승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)·
    [TASK-013 NFT·Proxy UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)·
    [TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md)
  - Constraints: 소유권 분쟁·안전성 자동 판정 금지. analyzer 구현자는
    착수 시 log/state 최소 필드·mutation 없음·OSS/license를 다시 확인한다.
  - Conflicts: None known
- Change Receipt:
  - `src/scan_tool/domain/{analysis_request,analysis_result,evm_special,_types}.py`,
    `src/scan_tool/slices/evm_special.py`, `src/scan_tool/application/cli_runtime.py`,
    schema 3종, fixture 3개 `analysis-request.json`, 회귀 테스트 23건
    (unit 22 + integration 5 CLI 중 신규분). PR #66에서 구현.
  - 리뷰에서 발견한 P1 5건·P2 2건을 같은 PR에서 수정하고, 재현
    시나리오 회귀 테스트 6건과 Batch subject CLI 통합 테스트를 추가했다
    (§ TASK-013 Atomic Tasks 참고).
- Verification Receipt:
  - 427 tests PASS, fixture 10 PASS, Schema 44
    probes PASS, `scripts/verify.py` 전체 게이트 PASS.
  - PR #66 remediation 재검토 통과·merge commit `45afa7b` 이후 Fixture
    3개를 `confirmed`로 승격하고 Benchmark automated 9/9를 두 번
    결정적으로 재현했다.

### [x] TASK-014: PATH Graph·금액 정합 엔진

- Status: Done — Fixture 3 Confirmed · Benchmark 11/11 · FLOW-MULTI Assisted
- Work Type: code
- Priority: Phase 2 · P0
- Depends On: TASK-012
- Target Problems: `FLOW-EVM-001/002`, `FLOW-MULTI-001` 및 후속 범죄·복합 문제
- Atomic Tasks:
  - [x] proposed fixture 3개 ID와 공개 사례 선정 기준을 docs-only로 고정한다.
  - [x] `flow_path` Analysis type 대안·bounded graph·ledger·오류 계약을 작성한다.
  - [x] single·remerge·multi-origin × complete·partial·failed HTML Preview를 작성한다.
  - [x] 단일 path·분기/재병합·multi-origin 공개 사례를 `candidate`로 선정한다.
  - [x] 세 공개 fixture를 replay·oracle·Verifier 후 `verifying`으로 올린다.
  - [x] `flow_path` 대안 B와 bounded node/edge·hop/time·asset conservation 계약을 승인한다.
    (PR #71 검토·병합, [16_TASK_014_FLOW_PATH_IO_CONTRACT](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md)).
  - [x] `flow_path` analyzer(3 query)·domain·result variant를 구현하고 독립
    Verifier와 canonical hash를 대조한다([검증 Receipt](../05_QA_Validation/43_TASK_014_ANALYZER_VERIFICATION_RECEIPT.md)).
  - [x] cycle·unrelated fund·residual·budget partial·trace_unavailable을 구현하고
    회귀 테스트로 고정한다.
  - [x] path artifact와 read-only graph 출력 경계를 CLI persist/show/partial/
    resume 통합 테스트로 검증한다.
  - [x] Blockscout internal-tx 교차검증으로 단일-trace 하드 게이트를 닫고
    fixture 3개를 `확정`으로 승격한다.
  - [x] 완전한 문제 범위만 Benchmark에 반영해 FLOW-EVM-001/002를
    automated, FLOW-MULTI-001을 PRICE·귀속 잔여가 있는 assisted로 분류한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - FLOW 3문항
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - PATH 18개 필수 근거
- Related UI Docs:
  - [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - query·상태·edge·ledger 화면 계약
  - [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - graph·timeline read-only UX
  - [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - partial·export 흐름
- Related HTML Preview:
  - [TASK-014 PATH Preview](../02_UI_Screens/previews/07_task_014_path_preview.html) - query 3개·상태 3개 사용자 검토 화면
- Related Technical Docs:
  - [TASK-014 PATH 계약](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - graph·ledger·상태·오류 계약
  - [`flow_path` I/O 계약 확정안](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - 대안 B request/result/오류 매핑·scope_status·단일 trace 게이트(PR #71 병합)
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-PATH 계약
  - [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - path evidence 봉투
- Related QA Docs:
  - [TASK-014 Fixture·Contract Gate](../05_QA_Validation/39_TASK_014_FIXTURE_CONTRACT_GATE.md) - fixture·oracle·Verifier·UI Stop/Go
  - [TASK-014 Fixture 후보 보고서](../05_QA_Validation/40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - Euler 공개 3홉·재병합·multi-origin 후보
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-PATH-001/002
- Implementation Preconditions:
  - [x] 세 종류 path 공개 후보와 1차 exclusion·residual 정답 골격을 작성한다.
  - [x] 세 fixture의 두 공급자 replay·negative oracle·독립 Verifier를 통과한다.
  - [x] graph artifact·메모리 budget·partial 상태를 승인하고 반환 projection
    크기까지 회귀 테스트로 제한한다.
  - [x] CLI/Workbench 진입·전환·이탈과 complete·partial·failed를 확인한다.
  - [x] edge 최소 필드·artifact mutation·bounded graph 상태 관리를 승인한다.
  - [x] TASK-014 PATH Preview를 사용자가 검토하고 피드백을 승인한다
    (2026-07-29 23:09, runtime·fixture 승인은 아님).
  - [x] graph DB 미도입과 사용자 구현 승인을 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python engine 우선.
  - Custom components: bounded graph, path finder, reconciliation ledger.
  - Reused components: EVM core, cache, artifact, Operations Queue.
  - New libraries: N/A - stdlib 구조로 fixture 규모를 먼저 측정.
  - Libraries intentionally not added: graph DB/networkx - 측정된 필요 전 금지.
  - shadcn preset: N/A - 웹 runtime 구현 없음.
- Acceptance Criteria:
  - [x] 경로·분기·재병합·cycle·residual이 exact evidence로 재현된다.
  - [x] budget 초과는 중단 위치를 가진 partial이다.
  - [x] label 없이도 path 사실이 독립적으로 성립한다.
- Document Sync Check:
  - [x] Analysis I/O·Workbench·fixture·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PASS — 참조 문서 정독·Constraints·Conflicts 확정(2026-07-30).
    `flow_path` 대안 B 계약(doc 16) PR #71 병합. 사용자가 2026-07-30
    "Context Receipt PASS 전환을 승인합니다. TASK-014 analyzer 구현을
    진행해 주세요"로 PASS 전환과 구현 착수를 명시 승인함.
  - Required References Read:
    - [15 PATH 계약 제안](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) — graph 불변조건, bounded traversal, exclusion·residual 보존식(§7)
    - [16 flow_path I/O 계약 확정안](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md) — request/result variant, ErrorCode 재사용 매핑(§5), scope_status 필수(§8), 단일 trace 하드 게이트(§7), 구현 확장(§9)
    - [08 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) + [07 Preview](../02_UI_Screens/previews/07_task_014_path_preview.html) — query 3×상태 3 화면, edge/ledger/`not_assessed` 표현, 사용자 승인(2026-07-29 23:09)
    - [39 Fixture·Contract Gate](../05_QA_Validation/39_TASK_014_FIXTURE_CONTRACT_GATE.md) — Fixture Gate 통과, 계약 QA 10건 대부분 `not_executed`(구현 후 실행)
    - [40 후보 보고서](../05_QA_Validation/40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) · [41 replay·oracle](../05_QA_Validation/41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) · [42 독립 Verifier](../05_QA_Validation/42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) — Euler 공개 사례, 단일 trace disclosure(41 §3), raw-first canonical hash
    - [05 Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) — 0.2·0.1 하위호환·버전 규칙 / [02 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) — FLOW-EVM-001/002·FLOW-MULTI-001 정의
    - [04 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md)(PATH 18개 필수 근거) · [03 Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md)·[00 CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md)(read-only graph 상위 UX·partial/export 흐름) · [09 Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md)(WP-PATH 상위 계약) · [23 Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md)(QA-EXP-PATH-001/002)
    - 세 fixture(`FX-FLOW-PATH/REMERGE/MULTI-001`)의 input·expected·evidence·raw-replay
  - Verification(Context Receipt 준비, PR #72 시점): `scripts/verify.py` 전체 PASS — 436 tests, fixture 13 packages, traceability 1477 links, security 157 files (정독 시점 1471 → 정합 수정 후 1477, docs-only). analyzer 구현 이후 최신 수치는 아래 TASK-014 analyzer Verification Receipt를 따른다.
  - Constraints:
    - Bounded traversal(`max_hops`/`max_nodes`/`max_edges`), 상한 도달=`partial`, 무제한 BFS·graph DB 확장·Rules 밖 live 탐색 금지
    - external inflow/무관 자금은 seed ledger 보존식에서 분리(`excluded_edges` + external context), amount 유사성만으로 포함·제외 금지
    - **새 공개 `ErrorCode` 추가 금지** — 기존 enum + `stage`/`message`(doc 16 §5)
    - `scope_status`는 필수 결과 필드 → 구현 시 세 fixture expected.json·독립 Verifier recompute·pinned hash 3개 재계산(doc 16 §9)
    - `FixtureRequirementId`/정적 result schema에 `FLOW` 접두 추가 필요(NFT721/PROXY 선례)
    - label·price·attribution = `not_assessed`/별도 context(채점 밖); graph DB·networkx YAGNI; 공개 온체인만·서명/mutation 0
    - `confirmed`·Benchmark 승격 전 단일-trace 하드 게이트(doc 16 §7) 충족 필요
  - Conflicts:
    - (해소) `doc 39 §4 QA-PATH-FAILED-001`의 "data null"이 정정된 계약(`results: []`)과 불일치 → `results: []`로 수정
    - (해소) `doc 08 PATH UI §4.3`의 failed `data: null` 표기 → 승인 후 계약 동기화로 `results: []` + 구조화 오류로 수정(화면 재설계 아님, UI 승인 유지)
    - (해소) `doc 39 §8` Gate 순서 충돌(사용자 구현 승인을 Context Receipt PASS 선행 조건으로 둠) → PASS 조건(fixture·Verifier·계약·Preview)과 코드 착수 조건(PASS + 구현 승인)을 분리
    - (경계 고지) 문제은행 `FLOW-EVM-001`(서비스 라벨 교차검증·최종 도착 서비스)·`FLOW-MULTI-001`(시점 가격 환산 피해액)은 문제 전체 형태이나, `flow_path` v1 fixture는 **raw-path subset만 채점**하고 label/price/서비스 귀속은 `not_assessed`로 유예한다(TASK-015 PRICE/LABEL 연계). 구현·승격 문서에서 이 채점 경계를 명시할 것
    - (예정) doc 16 §9의 scope_status→fixture/verifier/hash 재계산은 구현 시 처리(현재 fixture·verifier는 scope_status 미보유)
- Change Receipt:
  - `src/scan_tool/domain/{flow_path,analysis_request,analysis_result,_types}.py`,
    `src/scan_tool/slices/flow_path.py`, `src/scan_tool/application/{cli_runtime,task_014_independent_verifier}.py`,
    schema 3종, `check_analysis_schema.py`·`check_task_012_analysis_contract_proposal.py`,
    fixture 3개 `analysis-request.json`(신규)·`expected.json`·`evidence.json`(scope_status·hash),
    `tests/unit/test_flow_path_slice.py`(25)·`tests/integration/test_flow_path_cli.py`(5),
    `scripts/verify_task_014_analyzer_independent_verification.py`(verify.py 연결).
  - 새 공개 `ErrorCode` 추가 없음(기존 enum + stage). `evm_core`·`evm_special`·
    기존 `0.1` 결과 불변.
- Verification Receipt:
  - 467 tests PASS, fixture 13, schema 48 probes, traceability 1489 links,
    security 162 files, TASK-014 negative oracle 18×2·독립 Verifier 3×2·
    **analyzer 독립 검증 3 fixtures canonical hash 일치** PASS.
    [TASK-014 Analyzer 검증 Receipt](../05_QA_Validation/43_TASK_014_ANALYZER_VERIFICATION_RECEIPT.md).
  - 최종 승격 기준 전체 Gate: 468 tests PASS, fixture 13, schema 48 probes,
    traceability 1507 links, security 162 files. PATH internal edge 독립
    교차검증과 Benchmark 11/11 회귀를 포함한다.
  - Fixture 3개 `확정`, Benchmark automated 11/11·assisted 1. 최종 근거는
    [TASK-014 최종 승격 Receipt](../05_QA_Validation/44_TASK_014_FINAL_PROMOTION_RECEIPT.md).

### [ ] TASK-015: Label·OSINT·Actor Intelligence 엔진

- Status: ToDo
- Work Type: code
- Priority: Phase 2 · P1
- Depends On: TASK-012
- Target Problems: `OSINT-LBL/SAN/ENS-001`, `ACTOR-REL-001/002`
- Atomic Tasks:
  - [x] official/first-party/provider/public-report/heuristic source role과
    Terms Gate 제안 계약을 docs-only로 작성한다.
  - [x] 주소 명시·조회 시각·충돌·폐기 라벨의 proposed fixture ID 5개와
    승격 Gate를 문서화한다.
  - [x] label·sanctions·ENS·common funder·actor relation ×
    complete·partial·failed HTML Preview를 작성한다.
  - [x] TASK-015 Preview를 사용자가 검토하고 추가 수정 없이 승인한다
    (2026-07-30 02:52, fixture·runtime 승인은 아님).
  - [x] 공개 source Terms·privacy와 다섯 fixture 후보를 bounded 조사한다
    (4 viable, label conflict 1 source-blocked; package 생성 아님).
  - [x] label source blocker를 OpenRAIL research sample·MIT config·onchain
    ENS conflict로 교체하고 다섯 후보 snapshot SHA 기준선을 기록한다.
  - [ ] 공개 사례를 선정하고 fixture package를 만든다.
  - [ ] actor relation 후보와 반례를 검증한다.
  - [ ] AI 가설과 Python/source 증명을 분리한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT·Actor 5문항
  - [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 외부 전송·API Rules
- Related UI Docs:
  - [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - claim·conflict·direct/indirect·relation 화면
  - [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - label provenance·충돌 표시
- Related HTML Preview:
  - [TASK-015 Intelligence Preview](../02_UI_Screens/previews/08_task_015_intelligence_preview.html) - query 5개·상태 3개 사용자 검토 화면
  - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - 상위 source inspector 흐름
- Related Technical Docs:
  - [TASK-015 Intelligence 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md) - source role·claim·conflict·actor relation 제안
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-INTEL 계약
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source role·Terms
- Related QA Docs:
  - [TASK-015 Fixture·Contract Gate](../05_QA_Validation/45_TASK_015_FIXTURE_CONTRACT_GATE.md) - fixture·oracle·UI Stop/Go
  - [TASK-015 공개 Source·Fixture 후보 조사](../05_QA_Validation/46_TASK_015_PUBLIC_SOURCE_CANDIDATE_REPORT.md) - Terms·privacy·4 viable·1 source-blocked
  - [TASK-015 Source 교체·Raw Snapshot 기준선](../05_QA_Validation/47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) - 5 viable·artifact hash
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-INTEL-001
- Implementation Preconditions:
  - [ ] 공식 대회 Rules와 채택 source snapshot의 Terms·privacy·최소 필드를 확정한다
    (후보 조사·label source 교체 완료, package별 재배포 범위 확정 대기).
  - [ ] 충돌·주소 비명시·폐기 라벨 fixture를 확정한다.
  - [x] TASK-015 Preview에서 진입·전환·이탈과
    loading·empty·stale·Rules·conflict·failed를 확인한다.
  - [ ] label 최소 필드·append-only provenance mutation·상태 관리를 승인한다.
  - [x] Intelligence Preview와 Workbench source 표시를 사용자 확인하고
    피드백을 기록한다(2026-07-30 02:52).
  - [ ] `intel_context` Analysis I/O 대안과 source artifact 입력을 승인한다.
  - [ ] 공개 source snapshot·negative oracle·독립 Verifier를 통과한다.
  - [ ] live mode와 사용자 구현 승인을 별도로 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python source/intelligence core 우선.
  - Custom components: source-role registry, label assertion/conflict model.
  - Reused components: provenance, context evidence, Planner mode Gate.
  - New libraries: N/A - provider 확정 전 설치 금지.
  - Libraries intentionally not added: scraping/LLM framework - Rules·Terms 전 금지.
  - shadcn preset: N/A - 웹 runtime 미구현.
- Acceptance Criteria:
  - [ ] source role·주소 명시·조회 시각·충돌이 보존된다.
  - [ ] direct/indirect, stale/withdrawn, onchain/heuristic이 분리된다.
  - [ ] heuristic/AI 가설이 confirmed fact로 자동 승격되지 않는다.
  - [ ] 다섯 문제의 승격은 문제별 confirmed fixture로 제한된다.
- Document Sync Check:
  - [ ] Rules·source registry·Workbench·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PENDING - Preview 승인 완료, 공개 fixture·계약 정식 승인 전 PASS 금지
  - Required References Read:
    - [TASK-015 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md)
    - [TASK-015 UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md)와
      [Preview](../02_UI_Screens/previews/08_task_015_intelligence_preview.html)
    - [TASK-015 Gate](../05_QA_Validation/45_TASK_015_FIXTURE_CONTRACT_GATE.md)
    - 위 Related Concept·Technical·QA 문서 전체
  - Constraints: privacy 최소 수집, Terms·Rules Gate, source assertion과
    ownership/crime truth 분리, AI hypothesis 비승격
  - Conflicts: 공식 대회 Rules 미확정, selected raw artifact를 포함한 fixture
    package 미작성, ENS 제2 provider replay·negative oracle 미실행. label
    source blocker와 다섯 후보 snapshot 기준선은 해소
- Change Receipt:
  - N/A - docs-only Gate, 구현 미시작
- Verification Receipt:
  - Docs-only Gate: 468 tests PASS, fixture 13, schema 48 probes,
    traceability 1543 links, security 162 files.
  - Preview static check: query 5 × state 3, duplicate ID 0,
    fetch/XHR/WebSocket/EventSource 0. 브라우저 사용자 검토·runtime은 미실행.
  - Public-source candidate research: 468 tests PASS, fixture 13,
    schema 48 probes, traceability 1554 links, security 162 files.
    4 viable·1 source-blocked이며 package·runtime은 미작성.
  - Source resolution·snapshot basis: 468 tests PASS, fixture 13,
    schema 48 probes, traceability 1569 links, security 162 files.
    label blocker를 교체해 5 viable이며 package·TASK-015 runtime은 미작성.

### [ ] TASK-016: Service·Bridge·XChain·DeFi Adapter

- Status: ToDo
- Work Type: code
- Priority: Phase 2 · P2
- Depends On: TASK-014, TASK-015
- Target Problems: `SVC-BRG/CEX/MIX/LEND-001`, `MIXED-XCHAIN-001`
- Atomic Tasks:
  - [ ] confirmed fixture가 있는 전문 adapter만 구현 대상으로 선택한다.
  - [ ] 양단 chain/message/asset/amount 또는 서비스 휴리스틱 계약을 확정한다.
  - [ ] adapter별 exact·partial·conflict를 검증한다.
  - [ ] Benchmark를 실제 완료 문제만 승격한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 서비스·크로스체인 5문항
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P2/P3 승격 조건
- Related UI Docs:
  - [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - 다중 체인 graph·evidence
- Related HTML Preview:
  - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - 다중 source 검토 후보
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-SERVICE 계약
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - chain/provider source
  - [오픈소스 조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - adapter 재사용 Gate
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-SERVICE-001
- Implementation Preconditions:
  - [ ] adapter별 confirmed fixture·official ABI/address를 확보한다.
  - [ ] PATH·INTEL 결과 계약이 안정됐다.
  - [ ] Workbench 진입·전환·이탈과 loading·empty·partial·failed를 확인한다.
  - [ ] chain/message 최소 필드·artifact mutation·adapter 상태 관리를 승인한다.
  - [ ] chain/source/Rules·UI·Schema 영향을 승인한다.
  - [ ] adapter별 사용자 구현 승인을 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python adapter 우선.
  - Custom components: 선택된 bridge/service/lending adapter.
  - Reused components: PATH, INTEL, source port, reconciliation.
  - New libraries: N/A - adapter별 OSS 결정 전 설치 금지.
  - Libraries intentionally not added: 범용 multi-chain SDK - 범위 폭발 방지.
  - shadcn preset: N/A - 웹 runtime 미구현.
- Acceptance Criteria:
  - [ ] 선택 adapter의 결정적 사실과 heuristic이 분리된다.
  - [ ] 양단·금액·시간 누락은 partial/conflict로 보존된다.
  - [ ] 서비스 귀속·불법성을 자동 단정하지 않는다.
- Document Sync Check:
  - [ ] source·ABI·Analysis I/O·fixture·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PENDING - adapter별 fixture·승인 전 착수 금지
  - Required References Read: 위 Related 문서 전체
  - Constraints: confirmed adapter only, multi-chain bounded scope
  - Conflicts: source/Rules unresolved
- Change Receipt:
  - N/A - 구현 미시작
- Verification Receipt:
  - N/A - 구현 미시작

### [ ] TASK-017: Bitcoin UTXO·CoinJoin 엔진

- Status: ToDo
- Work Type: code
- Priority: Phase 2 · P2
- Depends On: TASK-011
- Target Problems: `BTC-UTXO-001/002`, `BTC-CJ-001`
- Atomic Tasks:
  - [ ] UTXO·change·CoinJoin 후보/반례 fixture를 확정한다.
  - [ ] prevout·input/output·fee·script·satoshi 계약을 설계한다.
  - [ ] UTXO graph와 heuristic 경계를 구현한다.
  - [ ] 세 문제의 Benchmark 승격 여부를 기록한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - BTC 3문항
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - BTC-UTXO 승격 조건
- Related UI Docs:
  - [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - UTXO graph UX 후보
- Related HTML Preview:
  - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - graph 검토 후보
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-BTC 계약
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - Bitcoin source
  - [오픈소스 조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - parser 재사용 Gate
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-BTC-001/002
- Implementation Preconditions:
  - [ ] 공개 BTC source·fixture·반례를 확보한다.
  - [ ] chain-specific request/result와 공통 evidence 호환을 승인한다.
  - [ ] Workbench 진입·전환·이탈과 loading·empty·partial·failed를 확인한다.
  - [ ] prevout 최소 필드·artifact mutation·UTXO graph 상태 관리를 승인한다.
  - [ ] UTXO graph UI 필요성을 검토한다.
  - [ ] 사용자 구현 승인을 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python engine 우선.
  - Custom components: BTC parser projection, UTXO ledger, heuristic classifier.
  - Reused components: provenance, artifact, bounded graph, Verifier.
  - New libraries: N/A - OSS/parser bake-off 전 설치 금지.
  - Libraries intentionally not added: full node/indexer - fixture 단계 범위 밖.
  - shadcn preset: N/A - 웹 runtime 미구현.
- Acceptance Criteria:
  - [ ] prevout·outputs·fee가 exact satoshi로 정합된다.
  - [ ] change/CoinJoin은 heuristic과 반례를 포함한다.
  - [ ] 세 문제의 승격은 confirmed fixture로 제한된다.
- Document Sync Check:
  - [ ] source·Analysis I/O·fixture·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PENDING - fixture·source·사용자 구현 승인 전 착수 금지
  - Required References Read: 위 Related 문서 전체
  - Constraints: satoshi exact, heuristic 비단정
  - Conflicts: Bitcoin source selection unresolved
- Change Receipt:
  - N/A - 구현 미시작
- Verification Receipt:
  - N/A - 구현 미시작

### [ ] TASK-018: 범죄·복합 사건 Reconciliation

- Status: ToDo
- Work Type: code
- Priority: Phase 2 · P2
- Depends On: TASK-014, TASK-015, 필요 시 TASK-016
- Target Problems: `CRIME-PHISH/POISON/EXP/RUG-001`, `MIXED-CASE-001`
- Atomic Tasks:
  - [ ] 사건별 공개 사례·reference answer·반례를 확정한다.
  - [ ] seed discovery·timeline·unrelated fund exclusion 계약을 설계한다.
  - [ ] 기존 엔진 결과를 evidence ref로 조합한다.
  - [ ] 기술 사실·외부 귀속·범죄 의도를 분리 검증한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 범죄·복합 5문항
- Related UI Docs:
  - [Investigation Workbench](../02_UI_Screens/03_WEB_INVESTIGATION_WORKBENCH.md) - 사건 graph·timeline·inspector
  - [Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 복수 leaf·독립 검증
- Related HTML Preview:
  - [Workbench Preview](../02_UI_Screens/previews/02_investigation_workbench_preview.html) - 사건 검토 화면
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-CASE 계약
  - [Agentic Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - Planner·worker·Verifier 경계
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-CASE-001
- Implementation Preconditions:
  - [ ] 사건별 fixture·정답·attribution scope를 확정한다.
  - [ ] PATH·INTEL과 필요한 전문 adapter가 검증됐다.
  - [ ] Workbench 진입·전환·이탈과 loading·empty·conflict·failed를 확인한다.
  - [ ] case 최소 필드·bundle mutation·timeline 상태 관리를 승인한다.
  - [ ] Workbench 사용자 동선·상태·충돌 표시를 확인한다.
  - [ ] 사용자 구현 승인을 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - Python case reconciler 우선.
  - Custom components: seed resolver, timeline, case evidence bundle.
  - Reused components: PATH, INTEL, vertical results, Candidate/Verifier.
  - New libraries: N/A - 기존 계약으로 먼저 구현.
  - Libraries intentionally not added: 범용 case-management framework - 범위 밖.
  - shadcn preset: N/A - 웹 runtime 별도 승인.
- Acceptance Criteria:
  - [ ] 사건 결과가 실제 evidence ref와 timeline에 연결된다.
  - [ ] 관련 없는 자금·충돌·미확정 귀속을 보존한다.
  - [ ] 범죄 의도는 증거 범위 밖이면 not_assessed다.
- Document Sync Check:
  - [ ] Workbench·Operations·Analysis I/O·fixture·Benchmark·QA를 동기화한다.
- Context Receipt:
  - Status: PENDING - 선행 엔진·fixture·UI·사용자 승인 전 착수 금지
  - Required References Read: 위 Related 문서 전체
  - Constraints: attribution/intent 비단정, evidence-only composition
  - Conflicts: None known
- Change Receipt:
  - N/A - 구현 미시작
- Verification Receipt:
  - N/A - 구현 미시작

### [ ] TASK-019: Coverage Expansion 통합 Gate

- Status: ToDo
- Work Type: code
- Priority: Phase 2 · Final Gate
- Depends On: TASK-012~018 중 실제 승인·완료된 package
- Target Problems: 예상문제 30개 전체
- Atomic Tasks:
  - [ ] 새 confirmed fixture와 automated manifest mapping을 검증한다.
  - [ ] 전체 automated 사례를 두 번 replay하고 exact/evidence/determinism을 채점한다.
  - [ ] assisted·unsupported 잔여와 기능 공백을 다시 계산한다.
  - [ ] bounded Operations Queue에서 복수 문제 격리·Verifier를 검증한다.
  - [ ] regression·security·traceability·Rules Gate를 실행한다.
- Related Concept Docs:
  - [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 전체 coverage 기준
  - [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 구현 결과 재점수화
- Related UI Docs:
  - [Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 병렬 실행·검증·수동 제출
- Related HTML Preview:
  - [Operations Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - 운영 상태 기준
- Related Technical Docs:
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - 전체 package 계약
  - [Analysis I/O](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 계약
  - [Agentic Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - 병렬·Verifier Gate
- Related QA Docs:
  - [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-REG/SEC
  - [Offline Benchmark](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 최초 3/6/21, 현재 9/0/21 기준선
- Implementation Preconditions:
  - [ ] 완료 package의 Verification Receipt를 모두 확인한다.
  - [ ] Benchmark·Operations Preview와 사용자 동선을 확인한다.
  - [ ] Operations 진입·전환·이탈과 loading·empty·partial·failed를 확인한다.
  - [ ] snapshot 최소 필드·submission mutation·Queue 상태 관리를 재확인한다.
  - [ ] 새 Schema·fixture·source·Rules 상태를 동결한다.
  - [ ] 통합 Gate 실행 승인을 기록한다.
- Component & Library Plan:
  - shadcn/ui: N/A - offline integration Gate.
  - Custom components: Benchmark manifest/report 확장.
  - Reused components: 모든 승인 analyzer, Queue, Candidate, Verifier, scripts/verify.py.
  - New libraries: 없음 - 통합 Gate에서 dependency 추가 금지.
  - Libraries intentionally not added: benchmark/CI framework - 기존 pytest/script 재사용.
  - shadcn preset: N/A - 새 UI 없음.
- Acceptance Criteria:
  - [ ] 전체 automated 사례가 exact·evidence·determinism을 통과한다.
  - [ ] 남은 assisted·unsupported를 성공으로 계산하지 않는다.
  - [ ] 문제 간 workspace·result·artifact가 격리된다.
  - [ ] 독립 검증 없는 후보와 conflict 후보는 submission-ready가 아니다.
- Document Sync Check:
  - [ ] 문제은행·우선순위·Roadmap·README·QA·Benchmark를 동기화한다.
- Context Receipt:
  - Status: PENDING - 선행 package·사용자 통합 승인 전 착수 금지
  - Required References Read: 위 Related 문서 전체
  - Constraints: no automatic submission, no coverage overstatement
  - Conflicts: official live Rules unresolved
- Change Receipt:
  - N/A - 구현 미시작
- Verification Receipt:
  - N/A - 구현 미시작

## 5. In Progress

없음. 후속 작업은 별도 구현 승인 전에는 `In Progress`로 이동하지 않는다.

## 6. Done

- `TASK-001` — Python 3.13.7, uv lock, 최소 CLI package, offline 품질 Gate
  ([검증 보고서](../05_QA_Validation/05_TASK_001_BOOTSTRAP_REPORT.md))
- `TASK-002` — Analysis I/O Pydantic model, 참조·uint256 불변조건, Schema probe
  ([검증 보고서](../05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md))
- `TASK-003` — HTTPX source port, 규정·offline Gate, retry·fallback provenance
  ([검증 보고서](../05_QA_Validation/07_TASK_003_SOURCE_REPORT.md))
- `TASK-004` — SQLite WAL, immutable cache, checkpoint, artifact, export
  ([검증 보고서](../05_QA_Validation/08_TASK_004_STORAGE_REPORT.md))
- `TASK-005` — Typer 네 명령, composition root, terminal renderer, exit code
  ([검증 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md))
- `TASK-006` — raw DEX log decode, WETH/native 분리, partial·reconciliation
  ([검증 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md))
- `TASK-007` — Approval·allowance·transferFrom 정합, 실패 거래·귀속 범위 분리
  ([검증 보고서](../05_QA_Validation/11_TASK_007_AUTH_REPORT.md))
- `TASK-008` — blacklist lifecycle 정합, global pause·공식 맥락·현재 상태 분리
  ([검증 보고서](../05_QA_Validation/12_TASK_008_FREEZE_REPORT.md))
- `TASK-009` — 결정적 3-slice 회귀, 11-code 행렬, 추적성·보안 통합 Gate
  ([검증 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md))

## 7. Backlog 승인 Gate

- [x] [문서 완료 Roadmap](./00_ROADMAP.md)의 `DOC-M1`~`DOC-M5` 통과
- [x] P0·V1 9개 작업과 별도 Rules-gated `TASK-010`의 범위·의존 순서 승인
- [x] TASK-001을 첫 구현 작업으로 승인
- [x] TASK-002 Analysis I/O 계약 구현을 별도로 승인
- [x] TASK-003 source orchestration 구현을 별도로 승인
- [x] TASK-004 storage·artifact·export 구현을 별도로 승인
- [x] TASK-005 CLI command·renderer·exit code 구현을 별도로 승인
- [x] TASK-006 DEX vertical slice 구현을 별도로 승인
- [x] TASK-007 AUTH vertical slice 구현을 별도로 승인
- [x] TASK-008 FREEZE vertical slice 구현을 별도로 승인
- [x] TASK-009 통합 회귀·보안·문서 동기화 Gate를 별도로 승인
- [x] TASK-012~019 Coverage 확장 계획 문서 작성을 승인
- [x] TASK-012 fixture·Context Receipt·구현을 별도로 승인
- [ ] TASK-013~019 각 code task의 fixture·Context Receipt·구현을 별도로 승인
- [x] QA 시나리오와 Acceptance Criteria 정합 확인
- [x] P0·V1 관련 오픈소스 후보의 `OSS-*` 결정과 fixture 검증 계획 확인
- [ ] 공식 규정 확인 전 live source 범위 재확인
- [x] Backlog 승인 후 `codex/task-001-python-bootstrap` branch 사용
- [x] TASK-002 승인 후 `codex/task-002-analysis-contract-models` branch 사용
- [x] TASK-003 승인 후 `codex/task-003-source-orchestration` branch 사용
- [x] TASK-004 승인 후 `codex/task-004-storage-artifacts` branch 사용
- [x] TASK-005 승인 후 `codex/task-005-cli-analyze` branch 사용
- [x] TASK-006 승인 후 `codex/task-006-dex-vertical-slice` branch 사용
- [x] TASK-007 승인 후 `codex/task-007-auth-vertical-slice` branch 사용
- [x] TASK-008 승인 후 `codex/task-008-freeze-vertical-slice` branch 사용
- [x] TASK-009 승인 후 `codex/task-009-integration-gate` branch 사용

## 8. 365 글로벌 평가 기준

| 기준 | Backlog 반영 |
|:---|:---|
| Functionality | Schema·공통 기반·3개 vertical slice·통합 Gate·조건부 병렬 운영 |
| Potential Impact | source·contract·fixture 재사용 가능한 공통 구조 |
| Novelty | evidence·context·not_assessed·partial 분리 |
| UX | UI-First Gate·400ms 피드백·FB-001·Operations Board |
| Open-source | 공개 Schema·fixture·adapter·재현 가능한 lock |
| Business Plan | 대회 준비 구현 Backlog이므로 현재 범위 N/A |

## 9. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 구현 단계와 완료 기준
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 승인된 명령·상태 흐름
- **UI_Screens**: [CLI Prototype Review](../02_UI_Screens/02_CLI_PROTOTYPE_REVIEW.md) - Gate 통과·FB-001
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 확인 화면
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - `TASK-010` 화면·상태·사용자 흐름
- **UI_Screens**: [Operations Board Preview](../02_UI_Screens/previews/03_competition_operations_board_preview.html) - `TASK-010` UI-First Gate
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - 구현 규칙
- **Technical_Specs**: [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - 요구사항·검증 ID
- **Technical_Specs**: [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 공개 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](../03_Technical_Specs/06_OPEN_SOURCE_FORENSICS_REVIEW.md) - 구현 전 재사용·직접 구현 결정 Gate
- **Technical_Specs**: [SQLite 논리 DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md) - `TASK-004` 저장·artifact·resume 논리 계약
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - `TASK-010` 역할·Queue·검증·제출 요구사항
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - `TASK-012~019` 엔진·fixture·계약 경계
- **Technical_Specs**: [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - EVM Core 0.2 Draft와 승인 경계
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - Phase 2 source·AI Planner capability Gate
- **Logic_Progress**: [문서 완료 Roadmap](./00_ROADMAP.md) - 구현보다 먼저 통과할 문서 Gate
- **Logic_Progress**: [Coverage 확장 Execution Plan](./01_EXECUTION_PLAN.md) - Wave·Stop/Go·진척 측정
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 수용·회귀 기준
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - exact-match 입력
- **QA_Validation**: [Agentic Parallel Solve QA](../05_QA_Validation/03_AGENTIC_PARALLEL_SOLVE_QA.md) - `TASK-010` 별도 6개 QA
- **QA_Validation**: [TASK-009 통합 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) - P0·V1 최종 통합 Gate 증거
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 새 분석기의 자동화 승격 Gate
- **QA_Validation**: [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - TASK-012 선행 smoke·독립성
