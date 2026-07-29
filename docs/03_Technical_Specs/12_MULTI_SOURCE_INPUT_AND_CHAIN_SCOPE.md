# 다중 입력 모드와 체인 범위 설계
> Created: 2026-07-29 10:38
> Last Updated: 2026-07-29 11:10
> Status: Approved 0.2 · Core Input Library Implemented · CLI Wiring Pending

## 1. 목적

SCAN이 대회 규정과 제공 데이터에 따라 입력 공급자를 교체하면서도 동일한
증거 계약·Python 분석기·독립 Verifier를 사용할 수 있도록 입력 모드와 체인
범위를 고정한다.

사용자는 2026-07-29 `WP-INPUT-GATE` 첫 구현 단위를 승인했다. core library의
`contest_rpc` adapter와 bounded artifact importer는 구현됐지만 CLI·Operations
wiring, Bitcoin·비EVM 분석기는 아직 구현되지 않았다. Analysis I/O `0.1`,
기존 DEX·AUTH·FREEZE 분석기와 TASK-012 fixture 상태는 변경하지 않는다.

## 2. 입력 모드

| 입력 모드 | 공급 주체 | 허용 입력 예 | 현재 구현 상태 |
|:---|:---|:---|:---:|
| `external_rpc` | 사용자가 준비한 외부 공급자 | JSON-RPC, Debug/Trace RPC | smoke·저장 replay 기반 일부 가능 |
| `contest_rpc` | 주최 측 | read-only RPC endpoint, chain/fixture 전용 RPC | core adapter 구현, CLI 미연결 |
| `provided_artifact` | 주최 측 또는 문제 첨부 | JSON, JSONL, CSV, raw transaction, receipt, logs, trace | bounded importer 구현, CLI 미연결 |

`external_rpc`가 규정상 제한되면 Etherscan·Blockscout 같은 Explorer를 자동
fallback으로 가정하지 않는다. Explorer 역시 외부 API·웹서비스 제한에 함께
포함될 수 있다. 이때 허용 가능한 경로는 주최 제공 `contest_rpc` 또는
`provided_artifact`이며, 둘 다 없다면 해당 source-dependent 분석은
`rules_gated`, `partial` 또는 `failed`로 남긴다.

자체 노드는 운영 여건과 규정이 허용할 때 가능한 별도 source다. 그러나
SCAN의 목표는 EVM 실행·Trace 엔진이나 Bitcoin 노드를 처음부터 재구현하는
것이 아니다. 검증된 클라이언트가 제공하는 read-only 원자료를 기존 evidence
계약으로 가져오는 adapter 경계만 유지한다.

## 3. 정규화 경계

세 입력 모드는 다음 경로에서 하나로 합쳐진다.

```text
external_rpc ─┐
contest_rpc  ─┼─> input adapter/importer ─> normalized evidence
artifact     ─┘                            ├─> Python analyzer
                                             └─> independent Verifier
```

정규화 이후에는 입력 공급 방식이 분석 결과의 의미를 바꾸면 안 된다.

- 원본 bytes 또는 canonical serialization의 SHA-256을 보존한다.
- `source_id`, `input_mode`, `chain_scope`, `retrieved_at` 또는 제공 시각,
  block/tx/range와 method 또는 artifact locator를 기록한다.
- raw 사실과 decoded 값, heuristic, external context를 분리한다.
- 동일 원자료의 RPC·artifact 입력은 같은 결정적 분석 값을 만들어야 한다.
- 누락·절단·형식 오류는 조용히 보정하지 않고 `partial` 또는 `failed`다.
- Python analyzer와 Verifier는 공급자 전용 응답이 아니라 normalized
  evidence만 소비한다.

Analysis I/O `0.1`의 result/evidence/source/run 봉투는 현재 그대로 유지한다.
`input_mode`·`chain_scope`를 공개 계약에 추가할 필요가 확인되면 별도 version과
migration 승인을 먼저 받는다.

## 4. 입력 adapter 책임

### 4.1 `external_rpc`

- provider별 endpoint·인증·rate limit을 composition root에서 주입한다.
- core adapter의 명시적 read-only method allowlist로 send/sign/wallet/mutation
  메서드를 네트워크 호출 전에 거부하고, 상위 composition에서 Rules Gate를 적용한다.
- QuickNode는 현재 일반 RPC + Debug Trace 주 경로다.
- Alchemy 무료 경로는 일반 RPC 독립 교차검증에 사용하며 Trace 공급자로
  간주하지 않는다.
- 단일 공급자만 성공하면 분석을 수행할 수 있으나 provenance에 독립 재현
  수준을 명시하고 fixture 승격 기준과 실전 실행 기준을 분리한다.

### 4.2 `contest_rpc`

- 주최 endpoint를 외부 공급자와 동일한 source port에 주입한다.
- chain ID·지원 method·archive/trace 범위·timeout을 bounded smoke로 확인한다.
- endpoint 형식·인증 방식이 달라도 analyzer 코드를 변경하지 않는다.
- send/sign/mutation method는 허용하지 않는다.

교체형 core adapter는 구현됐다. HTTPS·URL userinfo 금지, 명시 endpoint
한 곳만 호출, 기존 JSON-RPC source port 재사용을 강제한다. 대회 당일
CLI/composition에서 endpoint를 선택하는 wiring은 아직 구현되지 않았다.

### 4.3 `provided_artifact`

- JSON/JSONL/CSV와 문제 첨부 raw transaction·receipt·logs·trace를 bounded
  reader로 읽는다.
- 파일명이나 column 이름만 신뢰하지 않고 명시적 mapping과 validation을
  거친다.
- 원본 artifact hash와 row/record locator를 evidence에 연결한다.
- 알 수 없는 필드·중복 record·잘못된 수량·chain 혼합을 구조화 오류로 남긴다.
- archive/trace가 없는 artifact에서는 필요한 결과를 complete로 승격하지
  않는다.

JSON·JSONL·CSV core importer는 구현됐다. 기본 한도는 3MB·2,000 record이며
raw SHA-256·record locator·record hash·observed time을 보존한다. 문제별
임의 column mapping과 CLI 파일 선택은 아직 구현되지 않았다.

## 5. 체인 범위

| 범위 | 최소 원자료 | 필요한 분석 엔진 | 현재 상태 |
|:---|:---|:---|:---:|
| `evm` | TX, receipt, block, logs, state, 필요 시 trace | 공통 EVM query/decode/reconciliation | DEX·AUTH·FREEZE만 구현, EVM Core 미구현 |
| `bitcoin` | raw TX, inputs/outputs, prevout, block | UTXO graph, fee, change, CoinJoin | 미구현 |
| `non_evm` | chain별 transaction, instruction/message, account/state | 체인별 decoder·state analyzer | 미구현 |
| `cross_chain` | 양단 chain의 transaction/event/message와 asset amount | message·nonce·asset·amount·time reconciliation | 미구현 |

EVM 계열은 ABI·event·state·trace 기반 공통 기능을 재사용할 수 있다.
Bitcoin은 account/EVM 모델로 처리하지 않고 prevout·satoshi·UTXO 소비
관계를 별도 엔진으로 계산한다. 비EVM은 출제가 확인된 체인의 instruction과
state 모델을 먼저 고정한다. Cross-chain은 한쪽 거래만으로 완료 처리하지
않고 양단의 message·amount·asset 정합을 요구한다.

## 6. 구현 우선순위

1. 공통 입력 계층
   - `external_rpc | contest_rpc | provided_artifact` 선택
   - normalized evidence와 provenance
   - contest RPC adapter와 artifact importer
2. EVM Core
   - TX·receipt·block·state·logs·native/token transfer·trace
3. Bitcoin Core
   - prevout·UTXO graph·fee·change·CoinJoin 경계
4. Cross-chain
   - 양단 transaction·message·asset·amount 정합
5. 출제가 확인된 비EVM 체인
   - 해당 체인의 instruction/state 분석기

전문 decoder나 UI를 입력 계층보다 먼저 구현하지 않는다. 단, 이 순서는
문서상 dependency이며 각 코드 작업의 승인으로 간주하지 않는다.

## 7. 정직한 현재 상태

현재 SCAN이 할 수 있는 일:

- QuickNode·Alchemy 외부 RPC의 bounded smoke와 일반 RPC 교차검증
- QuickNode Debug Trace
- 저장된 replay를 이용한 DEX·AUTH·FREEZE 분석과 독립 Verifier
- input/source/evidence/result artifact와 provenance 보존
- 주최 HTTPS JSON-RPC를 명시적으로 주입하고 normalized evidence로 변환
- JSON·JSONL·CSV artifact를 bounded import하고 chain scope를 검증

현재 SCAN이 아직 할 수 없는 일:

- CLI·Operations Board에서 contest RPC/artifact를 선택·실행
- 문제마다 다른 임의 CSV column·provider envelope의 mapping 자동 추론
- TASK-012 범용 EVM Core 제품 analyzer
- Bitcoin UTXO·CoinJoin 분석
- 비EVM instruction/state 분석
- Cross-chain 양단 reconciliation

이 미구현 범위를 예상문제 27개 준비 완료나 automated coverage로 계산하지
않는다.

## 8. Stop/Go와 승인 Gate

| 조건 | 판정 |
|:---|:---|
| 공식 규정이 외부 RPC·Explorer를 제한 | 둘 다 차단, `contest_rpc`/artifact 확인 |
| 주최 RPC 제공 | read-only capability 확인 후 adapter 후보 |
| artifact만 제공 | importer mapping·hash·validation 승인 후 분석 |
| chain scope 불명 | 분석 시작 금지 |
| normalized evidence 계약 불명 | analyzer 구현 금지 |
| chain-specific fixture 없음 | 해당 엔진 구현·automated 승격 금지 |
| Context Receipt PENDING | 코드 `In Progress` 이동 금지 |
| 별도 사용자 구현 승인 없음 | docs-only 상태 유지 |

TASK-012~019의 기존 fixture·UI·Schema·Context Receipt·개별 구현 승인 Gate를
그대로 유지한다. `WP-INPUT-GATE` 통과도 이 Gate들을 대체하지 않는다.

## 9. QA 제안

- 동일 EVM 원자료를 `external_rpc`, `contest_rpc`, `provided_artifact`로
  입력했을 때 normalized evidence와 결정적 결과가 일치한다.
- Explorer가 제한된 모드에서는 Explorer 자동 호출이 0건이다.
- 잘못된 chain scope와 다른 체인 record 혼합을 거부한다.
- 누락 trace·prevout·양단 message는 complete가 아니라 partial이다.
- artifact의 원본 hash와 record locator가 evidence ref로 연결된다.
- Bitcoin/non-EVM 입력을 EVM analyzer가 받으면 명시적 타입 오류다.

core library 범위의 RPC↔artifact 동등성, 명시 endpoint 단일 호출,
JSON·JSONL·CSV, size/count, chain mismatch와 repr 비반사는 자동화됐다.
CLI·Operations·실제 대회 artifact 시나리오는 `not_executed`다.

## 10. Related Documents

- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - source 유형·제약
- **Technical_Specs**: [Analysis I/O](./05_ANALYSIS_IO_SCHEMA.md) - 공통 evidence/result 봉투
- **Technical_Specs**: [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - Work Package와 체인 엔진
- **Technical_Specs**: [Live Provider Readiness](./10_LIVE_PROVIDER_READINESS.md) - 외부 RPC topology·Gate
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012~019 승인 잠금
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - `WP-INPUT-GATE` 선행 순서
- **QA_Validation**: [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 향후 동등성·격리 기준
- **QA_Validation**: [WP-INPUT-GATE Core 보고서](../05_QA_Validation/30_WP_INPUT_GATE_CORE_REPORT.md) - 구현·테스트·잔여 경계

## 11. 구현 Receipt

| 항목 | 결과 |
|:---|:---|
| 입력 enum | `external_rpc`, `contest_rpc`, `provided_artifact` |
| 체인 enum | `evm`, `bitcoin`, `non_evm`, `cross_chain` |
| contest RPC | 기존 HTTPX JSON-RPC adapter 재사용, HTTPS·userinfo·read-only allowlist 검증 |
| artifact | JSON·JSONL·CSV, 3MB·2,000 record 기본 한도 |
| provenance | input mode·chain scope·source/provider·media type·raw/record SHA·observed time·locator |
| 격리 | envelope/result chain mismatch·null·malformed·oversize·record 초과 거부 |
| 동등성 | 같은 JSON-RPC result의 RPC↔artifact normalized record 일치 |
| 외부 fallback | adapter가 명시 contest endpoint 한 곳만 호출, Explorer 호출 없음 |
| 집중 검증 | 30 tests PASS |

Implementation files:

- `src/scan_tool/domain/input_source.py`
- `src/scan_tool/adapters/input_source.py`
- `tests/unit/test_input_source.py`
- `tests/integration/test_contest_rpc_input.py`
