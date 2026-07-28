# SCAN 2026 Python 개발 원칙
> Created: 2026-07-26 13:20
> Last Updated: 2026-07-29 01:16
> Status: Approved 2.8 · TASK-001~011 · OPS-IMPL-01~08 Applied

## 1. 문서 목적

이 문서는 SCAN 분석 도구를 Python으로 구현할 때 지킬 공통 원칙을 정의한다.
무엇을 만들지는 기능 우선순위와 P0·V1 요구사항이 결정하며, 이 문서는 정해진
기능을 어떤 구조·품질·보안 기준으로 구현할지를 제한한다.

적용 범위는 다음과 같다.

- Python package와 CLI
- DEX·AUTH·FREEZE vertical slice
- RPC·탐색기·공식 URL source adapter
- Pydantic 모델과 공개 JSON Schema
- SQLite cache·run metadata와 raw artifact
- 테스트, lint, dependency, Git 작업

웹 UI·TypeScript·그래프 DB·P1 이후 기능은 현재 범위가 아니다.

## 2. 현재 기준선

저장소에는 최소 application package와 offline 품질 Gate, Analysis I/O
runtime model, source port·HTTP adapter·policy·retry·fallback orchestration,
SQLite WAL 저장·immutable cache·checkpoint·content-addressed artifact·
JSON/Markdown export와 Typer CLI renderer, DEX·AUTH·FREEZE offline vertical
slice가 있다.

| 영역 | TASK-001~005 기준 |
|:---|:---|
| Runtime | Python 단일 core + CLI |
| Package | `src/scan_tool/` src layout |
| Project·lock | `uv`, `pyproject.toml`, `uv.lock` |
| Model | Pydantic `2.13.4` |
| Transport | HTTPX `0.28.1`, 주입된 `httpx.AsyncClient` 기반 직접 adapter |
| EVM | `eth-abi 5.2.0`, `eth-utils 5.3.1` · TASK-006/007 DEX·AUTH strict decode·주소 정규화 |
| Storage | 표준 `sqlite3` WAL + SHA-256 content-addressed artifact |
| CLI | Typer |
| Test | pytest + 기존 jsonschema 검증기 |
| Lint·format | Ruff |
| 공개 계약 | Analysis I/O Schema `0.1` |

Python 지원 범위는 `>=3.12,<3.15`, 재현 기준 patch는 `.python-version`의
`3.13.7`이다. `uv 0.11.32`로 macOS arm64 환경에서 lock 해석과 독립 임시
환경 cold install을 통과했다.

## 3. 규범 우선순위

충돌이 생기면 다음 순서로 판단한다.

1. 공식 대회 규정과 법적·이용약관 제한
2. P0·V1 도구 요구사항의 `MUST`
3. 승인된 Analysis I/O JSON Schema
4. 기술 선택 기록의 `TD-*`
5. 이 개발 원칙
6. 개별 모듈의 편의

코드가 승인된 JSON Schema와 다르면 코드를 임의로 기준으로 삼지 않는다.
계약 변경이 필요한지 먼저 문서에서 검토하고 버전 규칙에 따라 승인한다.

## 4. 최소 구현 Gate

구현 전 다음 순서를 적용한다.

1. 현재 요구사항·fixture에 없는 기능은 만들지 않는다.
2. Python 표준 라이브러리로 충분한지 먼저 확인한다.
3. 승인된 기존 dependency로 해결되는지 확인한다.
4. 필요한 최소 코드로 한 vertical slice를 끝낸다.
5. 같은 지식과 같은 변경 이유를 가진 중복만 추출한다.

다음은 V1에서 금지한다.

- 구현체 하나만을 위한 factory·registry·strategy 계층
- 사용되지 않는 옵션·feature flag·환경변수
- P1~P3를 예상한 빈 adapter·폴더·추상 클래스
- 표준 `json`, `hashlib`, `datetime`, `sqlite3`, `logging`으로 충분한 기능의
  별도 패키지 추가
- fixture 통과와 무관한 범용 그래프·OSINT·trace 프레임워크

source port는 복수 RPC·탐색기와 test double을 교체해야 하는 현재 요구가 있어
허용한다. 새 추상화는 최소 두 구현 또는 명확한 테스트 경계가 있을 때만
추가한다.

## 5. 패키지와 의존 방향

### 5.1 목표 구조

```text
src/scan_tool/
├── domain/             # 순수 모델, enum, 정합 규칙
├── application/        # use case, orchestration, retry, fallback, resume
├── ports/              # source·cache·artifact·export Protocol
├── adapters/
│   ├── rpc/
│   ├── explorer/
│   ├── context/
│   └── storage/
├── slices/
│   ├── dex/
│   ├── auth/
│   └── freeze/
├── export/
└── cli/

tests/
├── unit/
├── integration/
└── regression/
```

### 5.2 의존 규칙

```text
CLI (composition root) -> application + adapters
application -> slices + domain + ports
slices -----> domain + ports
adapters ---> ports + domain
export -----> domain
```

- `domain`은 HTTPX, SQLite, Typer, 환경변수를 import하지 않는다.
- `application`은 구체 adapter가 아니라 port를 받는다.
- adapter는 외부 응답을 domain 입력으로 변환하고 raw provenance를 보존한다.
- CLI는 composition root로서 구체 adapter를 생성해 application port에 주입할
  수 있다.
- CLI는 이 조립과 입력 검증·use case 호출·표시만 담당하고 분석 계산을
  포함하지 않는다.
- fixture adapter는 회귀 테스트 경계이며 production domain model을 fixture
  구조에 직접 결합하지 않는다.
- cross-package import는 `scan_tool...` 절대 import를 사용한다. 한 package
  내부의 private module에 한해 명시적 상대 import를 허용한다.
- 순환 import는 금지한다.

## 6. Python 코딩 기준

### 6.1 이름과 타입

- module·함수·변수는 `snake_case`, class·Protocol은 `PascalCase`, 상수는
  `UPPER_SNAKE_CASE`를 사용한다.
- public 함수·method·dataclass·Pydantic field에는 타입을 명시한다.
- `Any`는 외부 raw JSON을 받는 adapter 경계에서만 허용하며, 검증 후 구체
  타입으로 바꾼다.
- nullable과 누락을 구분한다. 의미 없는 `None`을 기본값으로 남발하지 않는다.
- boolean 이름은 `is_`, `has_`, `allow_`, `required_`처럼 의미가 드러나게 한다.
- module 전역의 변경 가능한 상태와 singleton client를 두지 않는다.

### 6.2 함수와 class

- 함수는 한 책임과 한 추상화 수준을 유지한다.
- I/O와 순수 계산을 분리한다. 디코딩·정합·수량 계산은 저장·HTTP 호출 없이
  단위 테스트할 수 있어야 한다.
- class는 상태나 protocol 경계가 필요할 때만 사용한다. namespace 용 class는
  만들지 않는다.
- mutable 기본 인자를 사용하지 않는다.
- broad `except Exception`으로 오류를 삼키지 않는다. 최상위 orchestration
  경계에서 구조화 오류로 변환하는 경우에도 원인과 stage를 보존한다.

### 6.3 주석과 문서 문자열

- 이름과 타입으로 설명되는 내용을 주석으로 반복하지 않는다.
- 복잡한 정합 조건, 공급자 차이, 규정 제한에는 “왜”를 기록한다.
- public port와 해석이 어려운 domain rule에는 짧은 docstring을 작성한다.
- 코드에 fixture 수치를 복사해 설명하지 않고 fixture ID·요구사항 ID로 연결한다.

## 7. 모델·Schema·정밀도

### 7.1 Pydantic

- 실행 시 모델 검증은 Pydantic v2를 사용한다.
- 공통 모델은 기본적으로 `extra="forbid"`를 적용한다.
- JSON 입력은 model validation을 거친 뒤 domain에 전달한다.
- `analysis_type`, 오류 코드, 상태, 증거 분류는 문자열 상수 대신 enum으로
  관리하고 공개 값은 Schema `0.1`과 일치시킨다.
- validation error는 redaction 후 `schema_invalid` 또는 `invalid_input`으로
  변환한다.

### 7.2 공개 Schema

- 저장소의 세 `analysis-*.schema.json`이 승인된 공개 계약이다.
- Python 모델은 공개 계약을 재현해야 하며 임의로 필드를 추가하지 않는다.
- 초기화 후 Pydantic 생성 Schema와 저장된 Schema의 의미상 diff를 검사하는
  명령을 만든다.
- 생성 순서·description 같은 비규범 차이는 정규화한 뒤 비교한다.
- 호환되지 않는 변경은 문서 승인과 schema version 변경 없이 머지하지 않는다.

### 7.3 EVM 값

- raw 토큰·네이티브 수량은 JSON 경계에서 10진 문자열로 유지한다.
- 계산 시 Python `int`를 사용하고 출력 시 다시 10진 문자열로 직렬화한다.
- `float`로 raw 수량·환율·채점값을 계산하지 않는다.
- 주소와 TX hash는 검증 후 소문자 `0x` 형식으로 정규화하고 원 입력은
  provenance에 보존한다.
- historical state는 명시적 block number 또는 block hash만 허용한다.
  `latest`로 과거 상태를 대체하지 않는다.
- wrapped asset과 native asset, 서로 다른 token address를 자동 합산하지 않는다.

## 8. 시간과 ID

- 내부 시각은 timezone-aware `datetime`을 사용하고 UTC로 저장한다.
- JSON은 RFC 3339 형식으로 직렬화하며 naive `datetime`을 금지한다.
- provider 시각과 block timestamp를 구분하고 각각의 출처를 기록한다.
- `analysis_id`, `result_id`, `evidence_id`, `source_record_id`는 한 run 안에서
  결정적으로 생성하거나 충돌을 검사한다.
- fixture 회귀에서는 같은 입력으로 채점 ID·핵심 raw 결과가 반복 가능해야 한다.

## 9. HTTP·source adapter

- 한 실행 수명에서 관리되는 `httpx.AsyncClient`를 주입하고 요청마다 새 client를
  만들지 않는다.
- connect·read·write·pool timeout을 명시한다.
- adapter는 한 번의 source 요청과 raw 응답 보존만 책임진다.
- retry·backoff·fallback 순서는 application orchestration이 관리한다.
- 자동 재시도는 idempotent read의 timeout, 429, 일시적 5xx에만 적용한다.
- `Retry-After`가 있으면 우선하고, 최대 시도와 모든 attempt를 기록한다.
- fallback은 최초 실패를 지우지 않으며 공급자 변경을 source provenance에 남긴다.
- HTTP status 성공만으로 유효한 데이터라고 판단하지 않고 JSON-RPC error,
  receipt status, decode 결과를 별도로 검증한다.
- rate limit과 동시성은 source별 정책으로 제한한다. 무제한 `gather`를 금지한다.

## 10. 오류와 부분 성공

- 예상 가능한 실패는 공통 11개 error code로 표현한다.
- domain rule은 provider 예외 문자열에 의존하지 않는다.
- adapter 예외는 source·provider·attempt·stage를 보존한 내부 오류로 변환한다.
- 필수 결과가 일부 증거로 입증되면 `partial`, 유효한 결과가 없거나 정합이
  깨지면 `failed`를 사용한다.
- `partial`·`failed`에서도 이미 확보한 증거와 source attempt를 보존한다.
- 실패 TX는 성공 자산 이동에서 제외하지만 실패 사실 자체는 버리지 않는다.
- 조용한 fallback, 빈 배열로 성공 위장, `None` 반환으로 오류 은폐를 금지한다.

## 11. Cache·SQLite·artifact

### 11.1 Cache

- cache key는 `chain_id + capability + method + normalized parameters +
  block tag`를 포함한다.
- canonical JSON은 key 정렬과 고정 구분자를 사용하며 secret을 포함하지 않는다.
- 확정 block hash의 historical 응답은 immutable로 취급할 수 있다.
- `latest`·미확정 데이터는 기본 cache 대상이 아니며 필요 시 명시적 TTL을 둔다.
- negative cache는 성공 cache와 분리하고 짧게 유지하거나 저장하지 않는다.
- checkpoint는 완료된 조회 단위까지만 기록하고 재개 시 같은 요청을 중복 호출하지
  않는다.

### 11.2 SQLite

- SQL에는 parameter binding을 사용하며 문자열 조합으로 값을 삽입하지 않는다.
- run·attempt·cache·artifact 연결은 transaction 단위로 기록한다.
- WAL 사용 중 DB를 복사해 백업하지 않는다. checkpoint 또는 정상 종료 후
  일관된 백업 절차를 사용한다.
- schema 변경·migration·삭제 전에 백업과 복구 절차를 확인한다.
- `DROP`, reset, cache 전체 삭제는 명시적 사용자 승인 없이 실행하지 않는다.

### 11.3 Raw artifact

- raw body는 SHA-256 content-addressed 경로에 저장하고 SQLite에는 hash와
  metadata만 둔다.
- byte를 먼저 hash한 뒤 임시 파일에 쓰고 같은 filesystem에서 atomic rename한다.
- 기존 hash 파일이 있으면 내용을 다시 덮어쓰지 않고 무결성을 확인한다.
- artifact에는 media type, byte length, source, retrieval time, redaction 상태를
  연결한다.
- fixture 승격 전 라이선스·개인정보·ToS와 secret redaction을 검토한다.

## 12. Provenance와 export

- 모든 외부 조회는 `DS-...` source ID와 별도 provider ID를 기록한다.
- 요청 method·정규화 파라미터·block tag·조회 시각·raw hash를 보존한다.
- endpoint는 host와 안전한 path만 export하고 query·header secret을 제거한다.
- JSON이 결과의 단일 source of truth다.
- Markdown evidence는 같은 Pydantic result model에서 렌더링하고 별도 계산하지
  않는다.
- JSON·Markdown은 같은 analysis·result·evidence ID를 사용한다.
- export에 API key, 인증 header, 로컬 사용자 절대 경로를 포함하지 않는다.
- 사람이 각 결과에서 raw TX·log·call·state 또는 공식 URL로 역추적할 수 있어야
  한다.

## 13. 보안과 공식 규정 Gate

- V1은 read-only RPC·HTTP만 허용한다. 서명·거래 전송 기능을 구현하지 않는다.
- private key, seed phrase, 서명 payload를 입력 모델로 받지 않는다.
- secret은 환경변수 또는 OS secret store의 참조로만 주입한다.
- secret 값을 Pydantic repr, exception, log, SQLite, cache key, artifact,
  checkpoint, export에 남기지 않는다.
- `.env*`는 로컬 전용이며 Git에 커밋하지 않는다. 공유 예제가 필요하면 값이
  비어 있는 `.env.example`만 허용한다.
- `source_policy.rule_status`가 `restricted`이면 네트워크 호출 전에
  `rule_restricted`로 중단한다.
- 공식 규정 확인 전 자동화·API 사용을 `allowed`로 기본 설정하지 않는다.
- dependency와 공식 ABI·배포 주소는 버전·commit·license provenance를
  기록한다.

## 14. Log와 CLI 출력 경계

- core module은 `print()`를 사용하지 않고 표준 `logging` 또는 결과 객체를 쓴다.
- CLI의 stdout은 결과 요약과 export 경로, stderr는 진행·경고·오류에 사용한다.
- log에는 analysis ID, stage, source ID, provider ID, attempt를 구조화해 넣는다.
- 주소·TX·source ID는 감사에 필요한 범위에서 기록할 수 있으나 secret·인증
  정보·전체 endpoint query는 기록하지 않는다.
- 시작 피드백은 400ms 이내를 목표로 하지만 외부 네트워크 완료 시간으로
  해석하지 않는다.
- 캐시 hit, retry, fallback, partial 상태를 숨기지 않고 사용자에게 표시한다.

## 15. 테스트 원칙

### 15.1 계층

| 계층 | 대상 | 네트워크 |
|:---|:---|:---:|
| Unit | 정규화, decode, 수량, 정합, cache key | 금지 |
| Integration | adapter, SQLite, artifact, export | 기본 금지, test double·임시 DB 사용 |
| Regression | confirmed fixture 3개와 Analysis Schema | 금지, 저장 fixture 사용 |
| Live verification | 실제 RPC·탐색기 공급자 | 명시적 opt-in만 허용 |

### 15.2 규칙

- 테스트 이름은 행동과 기대 결과를 설명한다.
- Arrange·Act·Assert를 구분하되 불필요한 주석으로 반복하지 않는다.
- unit test는 실행 순서·공유 전역 상태·실제 사용자 환경에 의존하지 않는다.
- filesystem 테스트는 임시 디렉터리를 사용하고 `.scan/` 실제 데이터를 건드리지
  않는다.
- SQLite 테스트는 임시 DB를 사용하고 각 테스트가 상태를 정리한다.
- 공급자 장애는 timeout·429·5xx·malformed JSON·JSON-RPC error로 구분해
  주입한다.
- exact-match 테스트는 주소·TX·블록·log/trace index·raw 수량·boolean·공식
  URL과 증거 참조를 검사한다.
- schema validator와 세 confirmed fixture 회귀는 PR 전 항상 실행한다.
- live verification은 별도 marker와 환경 opt-in이 없으면 skip한다.
- coverage 수치는 구현 baseline 측정 전 임의 목표를 확정하지 않는다.

## 16. Tooling과 dependency

### 16.1 기본 명령

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python docs/05_QA_Validation/scripts/validate_fixture_schemas.py
uv run python docs/05_QA_Validation/scripts/validate_analysis_schemas.py
uv run python scripts/verify.py
```

마지막 명령은 Ruff·pytest·두 Schema 검증과 생성 Schema 의미 검사를 순서대로
실행하는 저장소 공통 offline Gate다.

### 16.2 Dependency Gate

새 dependency를 추가하기 전에 다음을 기록한다.

1. 해결할 승인 요구사항
2. 관련 기능의 오픈소스 `OSSR-*` 조사와 `OSS-*` 결정
3. 표준 라이브러리와 기존 dependency로 해결할 수 없는 이유
4. 공식 배포 package와 유지보수 상태
5. 직접·간접 license와 알려진 취약점
6. lockfile과 cold install 재현 결과

사용하지 않는 dependency는 즉시 제거한다. `uv.lock`은 재현성 산출물이므로
Git에 포함하고 수동 편집하지 않는다.

## 17. Git·review·완료 기준

### 17.1 Git

- 한 branch와 PR은 한 문서·기능 목적만 다룬다.
- commit은 `type(scope): 한글 요약` 형식을 사용한다.
- commit 본문은 `- `로 시작하는 구체적인 한국어 설명을 최소 3줄 기록한다.
- generated Schema, lockfile, migration처럼 재현성에 필요한 파일은 생성 명령과
  함께 검토한다.
- unrelated 사용자 변경을 staging하거나 수정하지 않는다.
- secret·`.scan/`·로컬 DB·raw response를 commit하지 않는다.

### 17.2 PR 전 필수 확인

- Ruff lint·format 통과
- pytest 통과
- fixture schema와 analysis schema 검증 통과
- JSON과 Markdown export ID·값 일치
- secret·로컬 절대 경로 0건
- dependency·license·규정 제한 확인
- `git diff --check` 통과
- 관련 요구사항·Schema·QA 문서 동기화

## 18. Git 제외 대상과 로컬 데이터

`.gitignore`는 다음 로컬·생성 산출물을 제외한다.

```gitignore
.scan/
.env
.env.*
!.env.example
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
build/
dist/
*.egg-info/
```

`.scan/`은 local run·cache·artifact 저장소이며 fixture와 다르다. 공유해야 하는
검증 데이터만 검토 후 `docs/05_QA_Validation/fixtures/`로 복사한다.

## 19. [TODO] 미확정 구현 항목

| 우선순위 | 항목 | 완료 조건 |
|:---:|:---|:---|
| Done | `.gitignore` 보강 | `.scan/`, `.env*`, test·build cache, 로컬 DB 제외 완료 |
| Done | Python project 초기화 | Python 3.13.7, `pyproject.toml`, `uv.lock`, src layout, offline Gate 완료 |
| Done | Schema 생성·diff 명령 | Pydantic 생성본과 승인 Schema `0.1`의 35개 의미 probe diff 0 |
| Done | Source port·policy·retry·fallback | HTTPX one-attempt adapter와 rules-gated orchestration, fault injection 통과 |
| Done | SQLite·artifact·export | schema v1, WAL, immutable cache, checkpoint, backup·restore, JSON/Markdown 통과 |
| Done | CLI flow·terminal preview | UI-First Gate 및 TASK-005 renderer·TASK-006~008 세 slice 실제 출력 대조 완료 |
| Medium | 정적 타입 검사 채택 여부 | pytest·Ruff만으로 부족한 실제 사례가 있으면 도구 비교 후 결정 |
| Done | SQLite DDL·backup 절차 | schema v1·11 tables, 새 대상 backup, integrity restore rehearsal |
| Medium | 공급자별 rate limit | 공식 규정·계정·plan 확인 후 source policy에 수치 반영 |
| Low | 웹 UI | CLI 검토 병목 또는 공식 제출 필요가 확인될 때 재검토 |

## 20. 365 글로벌 평가 기준 연결

| 기준 | 개발 원칙의 대응 |
|:---|:---|
| Functionality | strict model, 계층별 테스트, fixture exact match, PR gate |
| Potential Impact | source port와 공개 계약을 통한 다른 온체인 조사 재사용 |
| Novelty | evidence-first와 사실·맥락·휴리스틱·미평가 분리 보존 |
| UX | 400ms 첫 피드백, 진행·부분·오류·fallback 가시화 |
| Open-source | src layout, 공개 Schema, lockfile, license provenance |
| Business Plan | 대회 준비 개발 원칙이므로 현재 범위 N/A |

## 21. 다음 단계

1. 이 Draft의 Python 구조·오류·저장·테스트 원칙을 검토한다.
2. CLI command flow와 terminal HTML Preview Draft를 작성했다.
3. 사용자가 Preview를 확인하고 UI-First Gate를 통과시켰다.
4. 승인된 문서와 preview를 원자적 backlog·QA 시나리오 Draft로 전환했다.
5. P0·V1 `OSS-*` 재사용·직접 구현 경계를 확정했다.
6. SQLite 논리 DB Schema·README·MIT License와 Document Completion Gate를 닫았다.
7. 공식 규정은 Active Watch로 유지하며 제한 기능을 기본 비활성화한다.
8. 별도 구현 승인에 따라 Python project와 offline 품질 Gate를 초기화했다.
9. `TASK-002`에서 Analysis I/O Pydantic model과 Schema 의미 검사를 구현했다.
10. `TASK-003`에서 HTTPX source port·policy·retry·fallback을 구현했다.
11. `TASK-004`에서 SQLite·cache·checkpoint·artifact·export를 구현했다.
12. `TASK-005`에서 CLI composition root·네 명령·renderer·exit code를 구현했다.
13. `TASK-006`에서 raw receipt·transaction·internal call을 엄격히
    디코딩하고 DEX 세 결과를 재조정하는 offline vertical slice를 구현했다.
14. `TASK-007`에서 Approval·allowance·transferFrom·Transfer·실패 거래를
    엄격히 정합하고 attribution을 `not_assessed`로 분리했다.
15. `TASK-008`에서 blacklist·unBlacklist call/event와 네 state를 정합하고
    issuer·OFAC context, global pause, 현재 상태 미평가를 분리했다.
16. `TASK-009`에서 133개 test, 세 Schema `PASS 3`, 저장소 추적성·보안
    검사를 dependency 추가 없이 통합 Gate에 연결했다.
17. `OPS-IMPL-01`에서 operations contract `0.1`, 생성 JSON Schema,
    cross-record 불변조건, 상태 전이 validator를 구현했다.
18. `OPS-IMPL-02`에서 명시적 SQLite v2 migration, v1 backup·rollback,
    operations repository와 append-only event log를 구현했다.
19. `OPS-IMPL-03`에서 Planner port, synthetic fake QA adapter, provider·
    model·data·tool mode의 pre-call Gate와 raw output artifact를 구현했다.
20. `OPS-IMPL-04`에서 bounded in-process Queue, dependency DAG, 문제별 실패
    격리, 재시도, idempotency dedup과 source capability request pool을 구현했다.
21. `OPS-IMPL-05`에서 승인 plan의 input projection을 DEX·AUTH·FREEZE
    Python evidence worker, 문제별 workspace, Analysis I/O와 artifact에 연결했다.
22. `OPS-IMPL-06`에서 canonical candidate, fresh independent replay,
    conflict 보존과 Application-only promotion Gate를 구현했다.
23. `OPS-IMPL-07`에서 SQLite v2 read-back, strict OperationsSnapshot,
    JSON/terminal 공통 view와 read-only local CLI를 구현했다.
24. `OPS-IMPL-08`에서 job-scoped evidence workspace, 복합 snapshot alert,
    explicit SQLite Board input과 사람 확인 수동 제출 기록을 구현했다.
25. live AI mode와 CTFd network submission은 공식 Rules·별도 승인 전까지
    `rules_gated` 또는 미구현 상태다.
26. `TASK-011` benchmark는 confirmed fixture와 전용 analyzer가 모두 있는
    문항만 자동 채점한다. 재사용 primitive만 있는 문항은 `assisted`, 핵심
    기능이 없는 문항은 `unsupported`로 유지하며 어느 쪽도 통과율 분모에
    숨겨 넣지 않는다.

## 22. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 구현 범위와 단계 제한
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 명령·상태·종료 흐름
- **UI_Screens**: [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 정보 계층·상태 표현·접근성
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - 구현 전 사용자 확인 화면
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - source ID·rate limit·규정 제약
- **Technical_Specs**: [SQLite 논리 DB Schema](./01_DB_SCHEMA.md) - run·cache·artifact·evidence·checkpoint 저장 경계
- **Technical_Specs**: [P0·V1 분석 도구 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md) - 구현이 만족해야 할 규범
- **Technical_Specs**: [P0·V1 기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md) - Python·adapter·저장·도구 결정
- **Technical_Specs**: [공통 분석 I/O Schema](./05_ANALYSIS_IO_SCHEMA.md) - 모델·오류·증거 공개 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](./06_OPEN_SOURCE_FORENSICS_REVIEW.md) - dependency·재사용·직접 구현 결정 Gate
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - Python 초기화 전에 통과할 문서 Gate
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - 구현 순서·전제조건·완료 기준
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - DEX·AUTH·FREEZE 회귀 기준
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 구현 전 승인할 자동·수동 검증 기준
- **QA_Validation**: [분석 I/O 예제](../05_QA_Validation/examples/analysis/README.md) - 모델·증거·source 참조 예
- **QA_Validation**: [TASK-001 Bootstrap 보고서](../05_QA_Validation/05_TASK_001_BOOTSTRAP_REPORT.md) - 실제 Python·lock·dependency·품질 Gate
- **QA_Validation**: [TASK-002 Contract 보고서](../05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md) - model·runtime 불변조건·Schema 의미 검사
- **QA_Validation**: [TASK-003 Source 보고서](../05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) - policy·retry·fallback·secret 비노출 검증
- **QA_Validation**: [TASK-004 Storage 보고서](../05_QA_Validation/08_TASK_004_STORAGE_REPORT.md) - SQLite·cache·checkpoint·artifact·export 검증
- **QA_Validation**: [TASK-005 CLI 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md) - command·renderer·exit code·보안 검증
- **QA_Validation**: [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - raw replay·정합·partial·checkpoint·dependency 검증
- **QA_Validation**: [TASK-007 AUTH 보고서](../05_QA_Validation/11_TASK_007_AUTH_REPORT.md) - allowance·trace·scope·partial·checkpoint·보안 검증
- **QA_Validation**: [TASK-008 FREEZE 보고서](../05_QA_Validation/12_TASK_008_FREEZE_REPORT.md) - 상태 전이·context·partial·checkpoint·보안 검증
- **QA_Validation**: [TASK-009 통합 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) - 24 QA·결정성·오류·추적성·보안 검증
- **QA_Validation**: [OPS-IMPL-01 계약 보고서](../05_QA_Validation/14_OPS_IMPL_01_CONTRACT_REPORT.md) - operations model·Schema·상태 validator 검증
- **QA_Validation**: [OPS-IMPL-03 AI Planner Gate 보고서](../05_QA_Validation/16_OPS_IMPL_03_PLANNER_REPORT.md) - fake QA·mode policy·artifact·budget·보안 검증
- **QA_Validation**: [OPS-IMPL-04 bounded Queue 보고서](../05_QA_Validation/17_OPS_IMPL_04_BOUNDED_QUEUE_REPORT.md) - dependency·격리·재시도·dedup·동시성 검증
- **QA_Validation**: [OPS-IMPL-05 Evidence Worker 보고서](../05_QA_Validation/18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md) - 승인 projection·세 vertical·workspace·artifact·checkpoint 검증
- **QA_Validation**: [OPS-IMPL-06 Candidate·Verifier 보고서](../05_QA_Validation/19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md) - canonical answer·fresh replay·conflict·promotion 검증
- **QA_Validation**: [OPS-IMPL-07 OperationsSnapshot 보고서](../05_QA_Validation/20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md) - SQLite read-back·strict snapshot·local view 검증
- **QA_Validation**: [OPS-IMPL-08 Final Integration 보고서](../05_QA_Validation/21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) - leaf 병렬·수동 제출·보안·6개 운영 QA
- **QA_Validation**: [예상문제 Offline Benchmark 보고서](../05_QA_Validation/22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - confirmed fixture 자동 채점과 미지원 범위 공개
