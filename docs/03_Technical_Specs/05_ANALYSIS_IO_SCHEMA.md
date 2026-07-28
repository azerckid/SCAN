# SCAN 2026 공통 분석 I/O Schema
> Created: 2026-07-26 12:26
> Last Updated: 2026-07-28 11:28
> Status: Contract Approved 0.1 · TASK-002·005·006·007·008·009 Applied
> Schema Version: 0.1

## 1. 문서 목적

이 문서는 DEX·AUTH·FREEZE 분석기가 공유하는 요청, 결과, 오류 JSON 계약
`0.1`을 정의한다. fixture 패키지는 회귀 검증의 입력·정답이며, 이 계약은 실제
도구 실행의 입력·출력이다. 두 스키마 버전은 독립적으로 관리한다.

공통 계약의 목표는 다음과 같다.

1. 분석 유형이 달라도 source policy, 증거, 오류, 실행 기록을 같은 방식으로
   처리한다.
2. 모든 결과에서 원본 증거와 실제 공급자 기록으로 역추적할 수 있게 한다.
3. `partial`·`failed`에서도 확보한 결과와 실패 지점을 잃지 않는다.
4. fixture 구조와 production domain model을 직접 결합하지 않는다.

## 2. 산출물

| 구분 | 경로 | 책임 |
|:---|:---|:---|
| 요청 스키마 | `../05_QA_Validation/schemas/analysis-request.schema.json` | 공통 봉투, 유형별 입력, source policy |
| 결과 스키마 | `../05_QA_Validation/schemas/analysis-result.schema.json` | 결과, 증거, 소스, 경고, 오류, 실행, export |
| 오류 스키마 | `../05_QA_Validation/schemas/analysis-error.schema.json` | 11개 오류 코드와 retry·source·attempt |
| 요청 모델 | `../../src/scan_tool/domain/analysis_request.py` | 분석 유형별 discriminated request와 source policy |
| 결과 모델 | `../../src/scan_tool/domain/analysis_result.py` | 상태·결과·증거·source·run·export와 참조 불변조건 |
| 오류 모델 | `../../src/scan_tool/domain/analysis_error.py` | 구조화 오류와 11개 오류 코드 |
| 검증 API | `../../src/scan_tool/domain/validation.py` | `invalid_input`·`schema_invalid` 분류와 pair 검증 |
| 예제 | `../05_QA_Validation/examples/analysis/` | confirmed fixture 3개의 요청·결과 변환 예 |
| 검증기 | `../05_QA_Validation/scripts/validate_analysis_schemas.py` | Schema와 ID·참조·요청↔결과 불변조건 검증 |
| Schema 의미 비교 | `../../scripts/check_analysis_schema.py` | 생성·승인 Schema의 35개 양성·음성 probe 비교 |

공개 계약은 JSON Schema Draft 2020-12를 사용한다. 구현 단계에서는 Pydantic
v2 모델에서 생성한 스키마와 저장된 파일의 의미 차이를 offline Gate에서
검사한다.

```bash
uv run python scripts/check_analysis_schema.py
```

Pydantic의 discriminated `oneOf`와 승인 Schema의 `if/then`은 문법 표현이
다르므로 JSON 텍스트를 동일하다고 가정하지 않는다. 세 유효 예제와 계약
경계의 35개 음성·양성 probe를 두 Schema에 모두 적용하고 수락 결과가 다르면
실패한다.

## 3. 요청 계약

### 3.1 공통 봉투

| 필드 | 필수 | 규칙 |
|:---|:---:|:---|
| `$schema` | 예 | 요청 스키마 상대 경로 |
| `schema_version` | 예 | `0.1` |
| `analysis_id` | 예 | 한 실행의 유일한 `AN-...` ID |
| `analysis_type` | 예 | `dex_swap`, `auth_consumption`, `address_freeze` |
| `chain_id` | 예 | V1은 Ethereum mainnet `1`만 허용 |
| `inputs` | 예 | 분석 유형별 strict object |
| `source_policy` | 예 | 허용 소스, 순서, fallback, offline, 규정 상태 |
| `fixture_id` | 아니요 | 회귀 실행이면 `FX-...` ID |
| `requested_at` | 예 | RFC 3339 date-time |

`additionalProperties: false`를 기본으로 한다. 주소와 TX 해시는 정규화된 소문자
`0x` 형식만 허용하며 raw 수량은 요청 입력에 필요한 경우 10진 문자열로
확장한다.

### 3.2 유형별 `inputs`

| 분석 유형 | 필수 시작점 |
|:---|:---|
| `dex_swap` | `transaction_hash` |
| `auth_consumption` | 대상·토큰·spender, 승인·소비 TX, 과거 상태 블록 |
| `address_freeze` | 토큰·대상·mode, 이벤트 TX 목록, 과거 상태 블록 |

AUTH의 `excluded_transaction_hashes`와 FREEZE의 `context_urls`는 선택 필드다.
과거 상태 블록은 이름이 있는 정수 map으로 받고 `latest` 문자열을 허용하지
않는다.

### 3.3 Source policy

| 필드 | 의미 |
|:---|:---|
| `rule_status` | `unconfirmed`, `allowed`, `restricted` |
| `allowed_source_ids` | 실행이 사용할 수 있는 데이터 소스 등록부 ID |
| `source_order` | orchestration의 우선 시도 순서 |
| `allow_fallback` | 주 소스 실패 후 다음 소스 사용 허용 |
| `offline_mode` | 네트워크 없이 저장 artifact·cache만 사용 |

`source_order`는 `allowed_source_ids`의 부분집합이어야 한다. JSON Schema가
배열 간 포함 관계를 표현하지 못하므로 검증기가 확인한다. `rule_status:
restricted`는 유효한 요청 문서일 수 있으나 실행기는 네트워크 호출 전에
`rule_restricted` 오류로 중단해야 한다.

`TASK-003` 실행 정책은 보수적 기본값을 적용한다. `unconfirmed`는 저장·검증
가능한 계약 값이지만 live transport 권한은 아니며, `offline_mode: false`에서
실제 HTTP 호출을 하려면 `rule_status: allowed`가 명시되어야 한다.
`offline_mode: true`는 source transport를 호출하지 않고 TASK-004의 cache 또는
fixture 경계로 넘긴다. 이 실행 정책은 Schema 필드나 버전을 변경하지 않는다.

`TASK-004`는 이 계약의 공개 필드를 변경하지 않는다. JSON export는
`AnalysisResult.to_contract_dict()`를 단일 source of truth로 사용하고,
Markdown은 같은 dict의 result·evidence·source 표와 canonical JSON을
렌더링한다. cache hit/miss는 `run.cache_hits`·`run.cache_misses`, 재개는
`run.resumed`·`checkpoint_id`에 반영하는 후속 composition 경계를 유지한다.

## 4. 결과 계약

### 4.1 공통 봉투

| 필드 | 규칙 |
|:---|:---|
| `analysis_id`, `analysis_type`, `chain_id` | 요청과 동일 |
| `status` | `complete`, `partial`, `failed` |
| `results` | 결정적 결과와 판단 범위 |
| `evidence` | event·call·state·context 정규화 증거 |
| `sources` | 실제 공급자 단위 provenance |
| `warnings` | 결과를 무효화하지 않는 한계 |
| `errors` | 공통 오류 객체 |
| `run` | tool version, 시각, cache·retry·fallback·resume |
| `exports` | JSON·Markdown artifact 참조 |

`complete`는 오류 배열이 비어 있어야 한다. `failed`는 오류가 하나 이상이어야
한다. `partial`은 확보한 결과·증거와 누락 이유를 함께 보존한다.

### 4.2 결과와 판단 범위

각 결과는 다음을 가진다.

- 고유한 `result_id`
- 분석기 확장점인 `result_type`과 `value`
- `confirmed_fact`, `external_context`, `heuristic`, `not_assessed` 중 하나
- 도구 요구사항 `REQ-COM/P0/V1/NFR-...`
- fixture 채점 요구사항 `REQ-DEX/AUTH/FREEZE-...`
- 하나 이상의 실제 `evidence_refs`

`value`만 유형별 확장 object로 허용한다. 공통 봉투의 필드 추가는 스키마
버전 변경 없이 허용하지 않는다. raw 수량은 `amount_raw`, `decimals`,
`symbol`로 분리하며 표시값은 채점 기준으로 사용하지 않는다.

### 4.3 증거와 소스

증거는 `evidence_id`, `evidence_type`, `source_id`,
`source_record_ref`, `method`, `retrieved_at`, `locator`, `decoded`,
`raw_artifact`를 가진다.

| 증거 유형 | 위치 예 |
|:---|:---|
| `event` | chain, block, TX, log index |
| `call` | chain, block, TX, trace address |
| `state` | chain, block, 조회 대상 |
| `context` | 공식 URL |

같은 `DS-EXPLORER-EVM`이어도 Blockscout API와 Etherscan UI는 서로 다른
`source_record_id`를 사용한다. 증거는 공급자 레코드 하나를 참조하고 그
레코드의 `source_id`와 일치해야 한다.

`raw_artifact.artifact_uri`는 필수다. live 실행에서는 content-addressed
artifact 경로와 SHA-256을 기록하고, 이 문서의 예제는 아직 실행 산출물이
아니므로 `fixture://...` 참조를 사용한다.

## 5. 오류 계약

| 코드 | 기본 의미 |
|:---|:---|
| `invalid_input` | 주소·해시·블록·유형 오류 |
| `unsupported_chain` | 지원하지 않는 chain ID |
| `source_unavailable` | 필수 소스 접근 불가 |
| `rate_limited` | 호출 제한과 재시도 소진 |
| `archive_required` | 과거 상태 소스 필요 |
| `trace_unavailable` | 필수 내부 호출 미확보 |
| `decode_failed` | ABI·calldata·log 디코딩 실패 |
| `evidence_incomplete` | 필수 결과의 증거 연결 부족 |
| `reconciliation_failed` | 수량·주소·블록·호출 불일치 |
| `schema_invalid` | 입력·출력 계약 검증 실패 |
| `rule_restricted` | 공식 규정상 자동화·소스 제한 |

모든 오류는 `error_id`, `code`, `message`, `stage`, `retryable`,
`attempt_count`를 가진다. 소스 관련 오류는 `source_id`, `provider_id`,
`last_attempt_at`을 추가한다. `details`는 redacted 진단 정보만 허용한다.

## 6. Fixture → 작업 입력 매핑

### 6.1 공통

| Fixture | 요청 |
|:---|:---|
| `fixture_id` | `fixture_id` |
| `chain.chain_id` | `chain_id` |
| 문제 유형 | `analysis_type`으로 변환 |
| `source_requirements[].source_id` | `source_policy.allowed_source_ids` 후보 |
| 등록부·실행 정책 | `source_order`, `allow_fallback`, `rule_status` |

fixture의 `status`, `fixture_version`, `selection_notes`는 분석 요청 필드가
아니다. fixture adapter와 회귀 보고서의 provenance로 보존한다.

### 6.2 유형별

| Fixture 필드 | 분석 요청 필드 |
|:---|:---|
| DEX `transaction_hash` | `inputs.transaction_hash` |
| AUTH `subject_address` | `inputs.subject_address` |
| AUTH `token_address` | `inputs.token_address` |
| AUTH `spender_address` | `inputs.spender_address` |
| AUTH 승인·소비 TX | `inputs.approval_transaction_hash`, `consumption_transaction_hash` |
| AUTH `state_blocks` | `inputs.state_blocks` |
| AUTH `excluded_intermediate_transactions` | `inputs.excluded_transaction_hashes` |
| FREEZE `token_address`, `target_address`, `mode` | 같은 이름의 `inputs` 필드 |
| FREEZE `event_transaction_hashes` | `inputs.event_transaction_hashes` |
| FREEZE `state_blocks` | `inputs.state_blocks` |
| FREEZE 공식 URL | fixture evidence에서 허용된 URL만 `inputs.context_urls`로 투영 |

### 6.3 정답·증거 매핑

| Fixture 패키지 | 분석 결과 |
|:---|:---|
| `expected.json` 기준 정답 | `results[].value` |
| 채점 `requirement_id` | `results[].fixture_requirement_ids` |
| `event_evidence` | `evidence_type: event` |
| `call_evidence` | `evidence_type: call` |
| `state_evidence` | `evidence_type: state` |
| `context_evidence` | `evidence_type: context` |
| `sources[]` | 공급자별 `sources[]` 레코드 |
| source requirement role·required | 해당 source record의 `role`, `required` |

## 7. 검증 불변조건

JSON Schema 검사 외에 검증기는 다음을 확인한다.

1. 요청과 결과의 `analysis_id`, `analysis_type`, `chain_id`,
   `schema_version`이 같다.
2. `result_id`, `evidence_id`, `source_record_id`, `warning_id`,
   `error_id`가 각 문서 안에서 유일하다.
3. 모든 result·warning·error 참조가 실제 ID를 가리킨다.
4. 모든 증거의 source record가 존재하고 두 `source_id`가 같다.
5. 실제 source ID가 요청의 `allowed_source_ids`에 포함된다.
6. `source_order`가 허용 소스의 부분집합이다.
7. `complete`에는 오류가 없고, `failed`에는 오류가 있다.
8. run 종료 시각이 시작 시각보다 이르지 않다.
9. 예제에서 `fixture_id`가 대응 fixture와 일치한다.

참조 무결성은 JSON Schema 단독으로 보장되지 않으므로 이 검증기가 공통 계약의
일부다.

`AwareDatetime`, source 순서 부분집합, run 시각 순서, ID 유일성·참조,
중첩 `*_raw` uint256 검증은 JSON Schema가 전부 표현하지 못하는 runtime
불변조건이다. `validate_analysis_request`, `validate_analysis_result`,
`validate_analysis_pair`가 이를 검증한다.

## 8. 호환성과 버전

### 8.1 Agentic orchestration과의 경계

Analysis I/O `0.1`은 병렬 문제풀이에서도 하나의 leaf 분석 요청·결과 계약으로
유지한다.

- 한 CTFd 문제는 여러 `analysis_id`를 가질 수 있다.
- `problem_id`, worker assignment, verification, submission candidate는
  별도 운영 manifest가 관리한다.
- Operations Board는 `analysis-result`의 result·evidence·source를 읽지만
  새로운 온체인 사실을 계산하지 않는다.
- 운영 필드를 이 Schema의 공통 필수 필드로 추가하지 않는다.
- 운영 manifest의 영구 JSON Schema는 `TASK-010` 구현 전 별도 승인한다.

따라서 Agentic Parallel Solve Flow 문서화만으로 Analysis I/O
`schema_version`을 올리지 않는다.

| 변경 | 버전 처리 |
|:---|:---|
| 설명·예제·검증 오류 문구 수정 | `0.1` 유지 |
| 선택 `value` 확장 | `0.1` 유지 |
| 공통 필수 필드 추가·삭제 | minor version 증가 |
| 기존 필드 의미·자료형 변경 | minor version 증가 |
| fixture 정답·증거 변경 | analysis schema와 무관, fixture version만 검토 |

Schema `0.1`은 Python 모델 구현 전에 승인한 설계 계약이다. `TASK-002`에서
Pydantic 생성본과 수기 스키마의 의미 probe diff 0을 확인했다. 차이가 생기면
코드가 아니라 승인된 공개 계약을 기준으로 결정한다.

## 9. 365 글로벌 평가 기준 연결

| 기준 | Schema 0.1 대응 |
|:---|:---|
| Functionality | strict 입력·결과·오류와 자동 참조 검증 |
| Potential Impact | 세 분석 유형과 복수 공급자가 공유하는 확장 경계 |
| Novelty | 확정 사실·맥락·휴리스틱·미평가와 raw evidence 분리 |
| UX | 부분 성공·구조화 오류·진행 기록을 CLI가 일관되게 표시 가능 |
| Open-source | 공개 JSON Schema·예제·독립 검증기 |
| Business Plan | 대회 준비 계약이므로 현재 범위 N/A |

## 10. 미결정 사항

- artifact URI scheme과 로컬 보존 기간
- Markdown evidence export의 렌더링 형식
- `partial` 상태에서 오류와 경고를 나누는 slice별 세부 기준
- 2026 공식 규정 확인 후 `rule_status` 기본값

## 11. 다음 단계

1. Schema 0.1과 세 fixture 예제의 자동 검증 `PASS 3`을 유지한다.
2. Python 개발 원칙 Draft 1에서 Pydantic 모델·adapter·artifact·secret 규칙을
   정리했다.
3. CLI command flow와 terminal HTML Preview Draft를 작성했다.
4. 사용자가 Preview를 확인하고 UI-First Gate를 통과시켰다.
5. 승인된 Schema·UI 경계를 원자적 backlog와 QA 시나리오 Draft로 전환했다.
6. SQLite 논리 DB Schema와 Document Completion Gate를 확정했다.
7. `TASK-001`에서 Python 프로젝트를 초기화했다.
8. `TASK-002`에서 Pydantic model·runtime 불변조건·생성 Schema 의미 검사를 연결했다.
9. `TASK-003`에서 source policy·retry·fallback 실행 경계를 연결했다.
10. `TASK-004`에서 SQLite·artifact·동일 모델 export 저장 경계를 연결했다.
11. `TASK-005`에서 Schema 변경 없이 CLI validate·renderer·exit code를 연결했다.
12. `TASK-006` DEX analyzer가 Schema 변경 없이 세 confirmed result와
    complete·partial·failed 결과를 생성한다.
13. CLI `--evidence`는 reviewed source artifact를 adapter에 주입하는 실행
    옵션이며 Analysis Request Schema 필드가 아니므로 버전은 `0.1`을 유지한다.
14. `TASK-007` AUTH analyzer가 Schema 변경 없이 approval·allowance lifecycle·
    authorization consumption·`not_assessed` attribution 결과를 생성한다.
15. `TASK-008` FREEZE analyzer가 Schema 변경 없이 blacklist·unblacklist
    transition과 `external_context` scope를 생성한다.
16. `TASK-009`에서 공개 오류 enum 11개 전체의 status·exit code, 세 fixture
    result 결정성, result→evidence→source 참조를 회귀했다.
17. 계약 변경이 없어 Schema 버전은 `0.1`을 유지한다.

## 12. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1 범위와 vertical slice
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - Schema 요청·결과·오류의 terminal 흐름
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - Schema 데이터의 상태별 표시
- **Technical_Specs**: [Python 개발 원칙](./00_DEVELOPMENT_PRINCIPLES.md) - Schema를 구현하는 Pydantic·검증·오류 원칙
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - `DS-...` ID와 공급자 제약
- **Technical_Specs**: [SQLite 논리 DB Schema](./01_DB_SCHEMA.md) - run·result·evidence·source·artifact 저장 매핑
- **Technical_Specs**: [Reference Fixture Schema](./02_REFERENCE_FIXTURE_SCHEMA.md) - 회귀 fixture의 독립 JSON 계약
- **Technical_Specs**: [P0·V1 분석 도구 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md) - 공통 입출력·오류 규범
- **Technical_Specs**: [P0·V1 기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md) - Pydantic·artifact·adapter 결정
- **Technical_Specs**: [Agentic Parallel Solve Flow](./07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - leaf analysis와 운영 manifest의 경계
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](./08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - Analysis I/O 0.1을 유지하는 운영 model·storage 경계
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 여러 leaf result의 운영 상태 표시
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - model·Schema 구현 작업과 완료 기준
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - 변환 대상 confirmed fixture
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - round-trip·무효 입력·참조 무결성 기준
- **QA_Validation**: [분석 I/O 예제](../05_QA_Validation/examples/analysis/README.md) - DEX·AUTH·FREEZE 요청·결과 예
- **QA_Validation**: [TASK-002 Contract 보고서](../05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md) - round-trip·오류·참조·Schema probe 증거
- **QA_Validation**: [TASK-003 Source 보고서](../05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) - source policy·attempt·fallback 증거
- **QA_Validation**: [TASK-004 Storage 보고서](../05_QA_Validation/08_TASK_004_STORAGE_REPORT.md) - 저장·export·checkpoint 증거
- **QA_Validation**: [TASK-005 CLI 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md) - Schema 기반 validate·renderer·exit code 증거
- **QA_Validation**: [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - Schema 0.1 DEX runtime 결과·참조 무결성
- **QA_Validation**: [TASK-007 AUTH 보고서](../05_QA_Validation/11_TASK_007_AUTH_REPORT.md) - Schema 0.1 AUTH runtime 결과·참조 무결성
- **QA_Validation**: [TASK-008 FREEZE 보고서](../05_QA_Validation/12_TASK_008_FREEZE_REPORT.md) - Schema 0.1 FREEZE runtime 결과·참조 무결성
- **QA_Validation**: [TASK-009 통합 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) - Schema 0.1 통합 결정성·오류 행렬·추적성
