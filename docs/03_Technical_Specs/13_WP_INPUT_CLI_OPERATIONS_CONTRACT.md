# WP-INPUT-GATE CLI·Operations 연결 계약
> Created: 2026-07-29 12:20
> Last Updated: 2026-07-29 12:20
> Status: Proposed 0.1 · Docs-Only · CLI·Operations 구현 승인 대기

## 1. 목적

이 문서는 이미 구현된 공통 입력 core library를 실제 CLI 명령과 Competition
Operations Queue에 연결하기 위한 설계 계약이다. `external_rpc`,
`contest_rpc`, `provided_artifact` 세 입력 모드와 `evm | bitcoin | non_evm |
cross_chain` 체인 범위가 하나의 `NormalizedEvidenceBundle`로 수렴한 뒤,
동일한 Python analyzer와 독립 Verifier로 전달되는 경계를 고정한다.

이 계약은 **docs-only**다. 아래 wiring은 사용자가 이 계약과 연결된 HTML
Preview를 승인하기 전에는 구현하지 않는다. Analysis I/O `0.1`, Operations
`0.1`, SQLite v2, 기존 DEX·AUTH·FREEZE fixture와 결과는 변경하지 않는다.

## 2. 선행 상태

| 항목 | 상태 | 근거 |
|:---|:---:|:---|
| 입력 mode·chain scope enum | 구현됨 | `domain/input_source.py` |
| `contest_rpc` HTTPS adapter·read-only allowlist | 구현됨 | `adapters/input_source.py` |
| JSON·JSONL·CSV bounded importer | 구현됨 | `adapters/input_source.py` |
| RPC↔artifact record 동등성 | 구현됨 | `tests/unit/test_input_source.py` |
| CLI 입력 mode 선택 | **미구현** | 이 계약 §4 |
| Operations Queue→Evidence Worker 입력 전달 | **미구현** | 이 계약 §6 |
| 입력 출처·오류·partial UI 표시 | **미구현** | 이 계약 §7, UI 문서 |

`WP-INPUT-IMPL-01` core library는 2026-07-29 승인·구현됐다. 이 계약은 그
경계를 사용자 명령과 운영 화면까지 확장하되, TASK-012~019의 fixture·Schema·
Context Receipt·개별 구현 승인 Gate를 대체하지 않는다.

## 3. 정규화 수렴 원칙

세 입력 모드는 §5의 adapter/importer를 거쳐 단일 `NormalizedEvidenceBundle`을
만든다. 정규화 이후에는 입력 공급 방식이 분석 결과의 의미를 바꾸지 않는다.

```text
external_rpc ─┐
contest_rpc  ─┼─> input adapter/importer ─> NormalizedEvidenceBundle ─┬─> Python analyzer
artifact     ─┘   (§5 규칙, §8 보안)                                    └─> independent Verifier
```

- `input_mode`, `chain_scope`, `source_id`, `provider_id`, `raw_sha256`,
  record locator·`record_sha256`, `observed_at`는 provenance로 보존한다.
- `input_mode`·`chain_scope`는 provenance·source attempt·OperationEvent에만
  기록하고 Analysis I/O `0.1` result/evidence 봉투에는 추가하지 않는다.
- 동일 원자료의 세 모드 입력은 같은 정규화 record data와 `record_sha256`을
  만들어야 한다. (원본 `raw_sha256`은 직렬화가 달라 다를 수 있다.)
- 누락·절단·형식 오류는 조용히 보정하지 않고 구조화 오류 또는 partial이다.

## 4. CLI 입력 옵션 설계

### 4.1 `scan analyze` 확장

기존 `scan analyze --request PATH [--evidence PATH]`에 입력 계층 옵션을
추가한다. 요청 파일과 종료 코드 계약은 그대로 둔다.

| 옵션 | 값 | 기본값 | 규칙 |
|:---|:---|:---|:---|
| `--input-mode` | `external_rpc \| contest_rpc \| provided_artifact` | `external_rpc` | 선택한 모드만 아래 입력 소스를 요구한다. |
| `--chain-scope` | `evm \| bitcoin \| non_evm \| cross_chain` | `evm` | analyzer의 체인 모델과 반드시 일치한다. |
| `--contest-rpc-endpoint` | HTTPS URL | 없음 | `contest_rpc` 전용. 미지정 시 `SCAN_CONTEST_RPC_ENDPOINT` 환경변수. |
| `--artifact` | 파일 경로 | 없음 | `provided_artifact` 전용. |
| `--artifact-format` | `json \| jsonl \| csv` | 확장자 추론 | 추론 실패·불일치 시 명시 필수. |
| `--evidence` | 파일 경로 | 없음 | `external_rpc` offline replay(기존 계약 유지). |

배타 규칙: 선택한 `--input-mode`에 맞는 입력 소스를 **정확히 하나** 요구한다.
다른 모드의 옵션이 함께 오면 `invalid_input`(exit 2)으로 네트워크 호출 전에
종료한다. `--chain-scope`가 analyzer의 체인 모델과 다르면
`require_chain_scope`가 `chain_scope_mismatch`로 거부한다.

### 4.2 모드별 CLI 계약

- `external_rpc`: 사용자가 준비한 외부 공급자. 기존 source policy
  (`offline_mode`, `rule_status`, `allowed_source_ids`)와 `--evidence` offline
  replay 경로를 그대로 사용한다. Explorer 자동 fallback은 없다.
- `contest_rpc`: 주최 HTTPS endpoint를 composition root에서 주입한다. endpoint는
  §8에 따라 저장·로그·export·repr에 남기지 않는다. read-only allowlist(§5.1)
  외 method는 호출 전에 거부한다.
- `provided_artifact`: `--artifact` 파일을 bounded importer(§5.2)로 읽어
  normalized bundle을 만든다. 파일명·column 이름만으로 체인 의미를 추정하지
  않는다.

### 4.3 예시

```bash
# 주최 제공 read-only RPC
scan analyze --request requests/evm_core.json \
  --input-mode contest_rpc --chain-scope evm \
  --contest-rpc-endpoint "$SCAN_CONTEST_RPC_ENDPOINT"

# 문제 첨부 artifact
scan analyze --request requests/evm_core.json \
  --input-mode provided_artifact --chain-scope evm \
  --artifact problem/receipts.jsonl --artifact-format jsonl
```

## 5. endpoint 및 JSON/JSONL/CSV 입력 규칙

### 5.1 contest RPC endpoint 규칙

`ContestRpcSourceAdapter`(구현됨)의 계약을 CLI·Operations에서 그대로 강제한다.

- endpoint는 절대 HTTPS URL이어야 하며 URL userinfo(`user:pass@`)를 금지한다.
- 명시된 endpoint 한 곳만 호출한다. Explorer·network fallback은 0건이다.
- read-only method allowlist만 허용하고, 그 외 method는 네트워크 호출 전에
  `SourceFailure(PERMANENT)`로 거부한다. 허용 method:
  `debug_traceTransaction`, `eth_blockNumber`, `eth_call`, `eth_chainId`,
  `eth_getBalance`, `eth_getBlockByHash`, `eth_getBlockByNumber`,
  `eth_getCode`, `eth_getLogs`, `eth_getProof`, `eth_getStorageAt`,
  `eth_getTransactionByHash`, `eth_getTransactionCount`,
  `eth_getTransactionReceipt`, `trace_transaction`.
- send/sign/wallet/mutation method는 allowlist에 없으므로 자동 차단된다.

### 5.2 JSON/JSONL/CSV artifact 규칙

`ProvidedArtifactImporter`(구현됨)의 계약을 CLI·Operations에서 그대로 쓴다.

| 항목 | 규칙 |
|:---|:---|
| 인코딩 | UTF-8(-sig). 디코딩 실패는 `invalid_artifact`. |
| JSON | 배열은 `json:$[i]`, 단일 값은 `json:$` locator. 비유한 수(NaN·Infinity) 거부. |
| JSONL | 공백이 아닌 각 줄을 `jsonl:line=n`으로 파싱. |
| CSV | 헤더 필수·빈/중복 헤더 거부, 헤더보다 값이 많은 행 거부. `csv:row=n`. |
| 한도 | 기본 3MB·2,000 record. 초과 시 `artifact_too_large`·`too_many_records`. |
| null record | 개별 null record는 `invalid_artifact`. |
| JSON-RPC 봉투 | `{jsonrpc, result}` 형태면 `result`를 unwrap하고, unwrap 전후 모두 `chain_scope` record 검사. |
| chain 혼합 | record의 `chain_scope`가 요청 scope와 다르면 `chain_scope_mismatch`. |
| provenance | `raw_sha256`, record locator, `record_sha256`, `observed_at` 보존. |

문제별 임의 column mapping·provider envelope 자동 추론은 이 계약의 범위가
아니다. 필요한 매핑은 별도 승인으로 다룬다.

## 6. Operations Queue → Evidence Worker 전달 구조

### 6.1 입력 → 승인 replay 핸드오프

Competition Operations에서 입력 계층은 다음 순서로 `EvidenceWorkerCommand`에
연결된다. 기존 offline 실행 불변식(worker가 `offline_mode`·`rule_status`를
강제)을 유지한다.

```text
ProblemRecord
  (provided_urls, provided_file_artifacts[sha256], answer_format)
      │  Operator가 input_mode·chain_scope 선택
      ▼
input adapter/importer (§5)
      │
      ▼
NormalizedEvidenceBundle ──> content-addressed artifact (artifact://sha256/…)
      │                            │ raw_sha256
      ▼                            ▼
LeafJobSpec(inputs_projection == request.inputs)   ApprovedReplay(body, sha256)
      └──────────────┬──────────────────────────────────┘
                     ▼
        EvidenceWorkerCommand ─> EvidenceWorkerService.execute()
                     ▼
        Analysis I/O 0.1 result ─> independent Verifier
```

### 6.2 계약 규칙

- normalized bundle의 원본 bytes와 `raw_sha256`이 `ApprovedReplay.body`·
  `sha256`이 된다. `EvidenceWorkerService`의 기존 hash 검증과
  `SensitiveDataGuard`가 그대로 적용된다.
- `LeafJobSpec.inputs_projection`은 계속 `request.inputs`와 동일하다. 입력
  모드는 job 입력 계약을 바꾸지 않고 provenance로만 기록한다.
- `input_mode`·`chain_scope`·`source_id`·`provider_id`·record locator는
  `OperationEvent.safe_details_json`과 source attempt에 남긴다. endpoint·API
  key·전체 로컬 경로는 남기지 않는다.(§8)
- `contest_rpc` endpoint는 composition root에서만 주입하고 SQLite v2·export·
  snapshot에 저장하지 않는다.
- 라이브 `contest_rpc` 실행(offline_mode=false)은 현재 Evidence Worker가
  `rule_restricted`로 차단한다. 라이브 운영 실행은 Rules/AI mode Gate와 별도
  후속 승인이 필요하며, 이 계약의 초기 wiring 대상은 **입력 → normalized
  bundle → artifact → offline replay 동등 실행**이다.
- 문제 간 workspace(`problem_id/job_id`)·candidate 격리 규칙은 기존 OPS-IMPL
  계약을 그대로 유지한다.

## 7. 입력 출처·오류·partial 상태 UI 표시

### 7.1 CLI 표시

| 위치 | 표시 | 스트림 |
|:---|:---|:---:|
| `STARTING` | `input_mode`, `chain_scope`, `source_id`(endpoint 없음) | stderr |
| `INPUT` | record 수, `raw_sha256` 앞 12자, media type | stderr |
| terminal status | `COMPLETE`/`PARTIAL`/`FAILED` (기존 계약) | stdout |
| `PARTIAL` | 확보 record 수와 누락 요구·다음 행동 | stdout |
| `ERROR` | 입력 오류 코드·사유(원문 미반사) | stderr |

입력 실패는 InputFailureKind를 구조화 오류로 매핑한다.

| InputFailureKind | 종료 코드 | 계열 |
|:---|:---:|:---|
| `invalid_artifact` | 2 | 입력 경계 |
| `artifact_too_large` | 2 | 입력 경계 |
| `too_many_records` | 2 | 입력 경계 |
| `chain_scope_mismatch` | 2 | 입력 경계 |
| `unsupported_input` | 2 | 입력 경계 |

입력 경계 오류는 네트워크 호출 전에 종료한다. 필수 record(예: trace·prevout)
누락은 오류가 아니라 `PARTIAL`(exit 3)이며 확보 증거를 보존한다.

### 7.2 Operations Board 표시

- Problem row·Source health에 `input_mode` 배지와 `chain_scope`를 표시하되
  endpoint는 표시하지 않는다.
- 입력 실패는 해당 job에만 partial·error로 표시하고 다른 문제·후보는 유지한다.
- normalized bundle의 record locator·`record_sha256`을 evidence ref로 연결한다.

세부 화면 계약과 상태 조합은 [입력 소스 선택 UI](../02_UI_Screens/06_INPUT_SOURCE_SELECTION_UI.md)와
그 HTML Preview에서 정의한다.

## 8. endpoint·API 키 비저장·로그 비노출과 read-only allowlist

- endpoint·API key는 CLI 옵션 또는 환경변수로 composition root에 주입만 하고
  SQLite·artifact·export·checkpoint·OperationEvent·progress·result repr 어디에도
  저장·출력하지 않는다.
- `contest_rpc` adapter는 URL userinfo를 금지하고 명시 endpoint 한 곳만
  호출한다. Explorer/network fallback은 0건이다.
- read-only method allowlist(§5.1)를 유지하고 그 외 method는 네트워크 호출
  전에 거부한다.
- replay bytes와 export는 기존 `SensitiveDataGuard`로 canary secret·인증
  header·로컬 절대 경로를 검사한다.
- 잘못된 입력의 구조화 오류 메시지는 원본 artifact 내용을 반사하지 않는다.

## 9. QA 시나리오

### 9.1 세 모드 동등성

- 동일 EVM JSON-RPC `result`를 `external_rpc`, `contest_rpc`,
  `provided_artifact(json)`로 입력했을 때 normalized record data와
  `record_sha256`이 일치하고, analyzer의 결정적 결과가 동일하다.
- 같은 원자료를 JSON·JSONL·CSV로 제공해도 정규화 record가 의미상 일치한다.

### 9.2 격리·경계

- 잘못된 `--chain-scope`와 다른 체인 record 혼합을 `chain_scope_mismatch`로
  거부한다.
- 3MB·2,000 record 한도 초과, null record, 비유한 수, 잘못된 CSV 헤더를
  구조화 오류로 거부한다.
- 누락 trace·prevout·양단 message는 complete가 아니라 `PARTIAL`이다.

### 9.3 보안·규정

- restricted·Explorer 제한 모드에서 Explorer/network 호출이 0건이다.
- allowlist 외 RPC method가 네트워크 호출 전에 거부된다(HTTP 0건).
- canary endpoint·API key·인증 header·로컬 절대 경로가 stdout·stderr·export·
  snapshot·OperationEvent에 0건이다.

### 9.4 Operations 핸드오프

- normalized bundle artifact의 `raw_sha256`이 `ApprovedReplay.sha256`과 같고,
  Evidence Worker가 offline replay와 동등한 결과를 만든다.
- endpoint·secret이 SQLite v2·snapshot·export에 저장되지 않는다.

core library 범위(RPC↔artifact record 동등성, 단일 endpoint 호출, JSON/JSONL/
CSV, size/count, chain mismatch, repr 비반사)는 이미 자동화됐다. CLI·Operations
시나리오는 승인·구현 전까지 `not_executed`다.

## 10. Stop/Go와 승인 Gate

| 조건 | 판정 |
|:---|:---|
| chain scope 불명 | Stop — 분석 시작 금지 |
| endpoint HTTPS·userinfo 규칙 위반 | Stop — adapter 생성 거부 |
| allowlist 외 method 요청 | Block — 네트워크 호출 전 거부 |
| endpoint·secret이 저장/출력 경로에 노출 | Stop — 구현 금지 |
| 세 모드 record 동등성 미검증 | Stop — wiring 승격 금지 |
| HTML Preview 사용자 미승인 | Stop — CLI·Operations 구현 금지 |
| 이 계약·Preview 승인 | Go — wiring 구현 후 TASK-012 EVM Core로 이동 |

이 계약과 [입력 소스 선택 UI](../02_UI_Screens/06_INPUT_SOURCE_SELECTION_UI.md)
Preview가 승인되면 실제 CLI·Operations 연결을 구현하고, 이후 TASK-012 범용
EVM Core 분석기로 넘어간다.

## 11. Related Documents

- **Technical_Specs**: [다중 입력 모드와 체인 범위](./12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - 입력 모드·체인 범위 상위 설계
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - source ID·능력·제약
- **Technical_Specs**: [Agentic Parallel Solve Flow](./07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - Queue·worker·검증 계약
- **Technical_Specs**: [공통 분석 I/O Schema](./05_ANALYSIS_IO_SCHEMA.md) - 변경 금지 공개 계약
- **Technical_Specs**: [Python 개발 원칙](./00_DEVELOPMENT_PRINCIPLES.md) - CLI·log·secret 경계
- **UI_Screens**: [입력 소스 선택 UI](../02_UI_Screens/06_INPUT_SOURCE_SELECTION_UI.md) - 입력 출처·오류·partial 화면 계약
- **UI_Screens**: [입력 소스 선택 Preview](../02_UI_Screens/previews/05_input_source_selection_preview.html) - 구현 전 사용자 확인 화면
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 공통 명령·상태·종료 코드
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 병렬 운영 화면
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - WP-INPUT·TASK-012 승인 잠금
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 0 CLI·Operations 선행 순서
- **QA_Validation**: [WP-INPUT-GATE Core 보고서](../05_QA_Validation/30_WP_INPUT_GATE_CORE_REPORT.md) - core library 구현·테스트 경계
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 동등성·격리 승격 기준
