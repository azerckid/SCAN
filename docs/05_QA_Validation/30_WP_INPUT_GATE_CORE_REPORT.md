# WP-INPUT-GATE Core Input Library 구현 보고서
> Created: 2026-07-29 11:10
> Last Updated: 2026-07-29 11:31
> Status: Core Library Passed · CLI/Operations Wiring Not Executed

## 1. 목적

외부 공급자 사용 가능 여부와 무관하게 주최 RPC 또는 문제 첨부 artifact를
같은 normalized evidence 경계로 가져오는 최소 입력 계층을 구현한다. 이
보고서는 체인별 정답 분석기가 아니라 analyzer 전단의 입력 adapter/importer
범위만 검증한다.

## 2. 승인과 Context

- 사용자 착수 승인: 2026-07-29
- Context Receipt: PASS
- 확인 문서:
  - [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md)
  - [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md)
  - [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md)
  - [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md)
  - [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md)

Analysis I/O `0.1`, Operations `0.1`, SQLite v2와 기존 fixture 상태는 변경하지
않았다.

## 3. 구현 범위

### 3.1 Domain

- `InputMode`: `external_rpc | contest_rpc | provided_artifact`
- `ChainScope`: `evm | bitcoin | non_evm | cross_chain`
- normalized bundle:
  - source/provider ID
  - input mode·chain scope
  - media type·byte length·observed time
  - raw SHA-256
  - record locator·type·canonical record SHA-256
  - normalized JSON data
- 안전한 구조화 실패:
  - `invalid_artifact`
  - `artifact_too_large`
  - `too_many_records`
  - `chain_scope_mismatch`
  - `unsupported_input`

### 3.2 Contest RPC

- 기존 `JsonRpcSourceAdapter`를 상속해 source port와 HTTPX transport를 재사용
- 절대 HTTPS URL만 허용
- URL userinfo 거부
- 명시적 read-only allowlist 적용
- send/sign/wallet/mutation 메서드는 네트워크 호출 전에 거부
- 명시 endpoint 한 곳만 호출
- validated JSON-RPC result를 normalized bundle로 변환
- Explorer·다른 RPC 자동 fallback 없음

### 3.3 Provided artifact

- JSON object/array, JSONL, CSV 지원
- 기본 3MB·2,000 record 제한
- UTF-8·null·malformed·빈 record·한도 초과 거부
- JSON-RPC envelope의 `result`를 RPC와 동일한 record data로 정규화
- artifact envelope와 JSON-RPC `result` 내부 `chain_scope`를 각각 검사하고
  요청 scope와 다르면 거부
- normalized record data는 repr에 노출하지 않음

## 4. 검증

집중 suite:

```bash
uv run pytest tests/unit/test_input_source.py \
  tests/integration/test_contest_rpc_input.py -q
```

결과: **30 passed**

| 검증 | 결과 |
|:---|:---:|
| JSON·JSONL·CSV parsing·locator | pass |
| byte·record bounds | pass |
| malformed·null·UTF-8 failure | pass |
| chain scope mismatch·analyzer guard | pass |
| JSON-RPC unwrap 이후 chain scope 재검사 | pass |
| normalized data repr 비반사 | pass |
| contest HTTPS·userinfo Gate | pass |
| send/sign/wallet/mutation 7종 호출 전 차단·network 0 | pass |
| 명시 endpoint 단일 호출·Explorer 0건 | pass |
| RPC↔artifact record data/hash 동등성 | pass |

전체 suite:

```bash
uv run python scripts/verify.py
```

결과:

- **336 passed**
- fixture Schema PASS 7
- Analysis I/O `0.1` compatibility PASS
- Operations `0.1` probe PASS
- repository traceability 1,159 links PASS
- security scan 96 runtime/evidence files PASS
- TASK-012 oracle·contract·UI 회귀 PASS

## 5. 제외 범위

- CLI `scan analyze` input mode 옵션
- Operations Board problem 입력과 adapter wiring
- 실제 주최 RPC capability smoke
- 임의 vendor/문제별 CSV column 자동 mapping
- binary RLP·protobuf·압축 파일
- EVM Core 제품 analyzer
- Bitcoin UTXO·비EVM·Cross-chain 분석기

이 항목은 후속 승인 전 완료로 계산하지 않는다.

## 6. 다음 Gate

1. core library 전체 회귀 검증
2. CLI/Operations input selection 계약과 UI 영향 승인
3. TASK-012 EVM Core analyzer가 normalized evidence를 소비하도록 별도 승인
4. 실제 문제 공개 시 contest RPC/artifact mapping을 fixture로 고정

## 7. Related Documents

- **Technical_Specs**: [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - 규범 계약·구현 Receipt
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - `WP-INPUT-IMPL-01`
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 0
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 입력 동등성·체인 격리
