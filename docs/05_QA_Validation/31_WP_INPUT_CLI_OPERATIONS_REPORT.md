# WP-INPUT-IMPL-02 CLI·Operations Wiring 구현 보고서
> Created: 2026-07-29 12:54
> Last Updated: 2026-07-29 12:54
> Status: Passed · Offline Wiring Applied · TASK-012 Applied Later

## 1. 목적과 승인 범위

사용자가 승인한 WP-INPUT 계약과 HTML Preview를 기준으로 공통 입력 core를
기존 `scan analyze`와 Operations Evidence Worker에 연결했다. 이 작업은
새 분석기를 만들지 않으며 Analysis I/O `0.1`, Operations `0.1`, SQLite v2,
DEX·AUTH·FREEZE 계산 규칙을 변경하지 않는다.

## 2. 구현

### 2.1 입력 envelope

- `InputEvidenceEnvelope`가 normalized bundle과
  `artifact://sha256/<raw_sha256>`를 결합한다.
- `SensitiveDataGuard`와 bounded importer가 성공한 뒤에만 raw bytes를
  content-addressed artifact에 저장한다.
- artifact hash·byte length·URI가 bundle과 다르면 handoff를 거부한다.
- 저장 artifact에서 `ApprovedReplay(body, sha256)`를 재구성한다.

### 2.2 CLI

- `--input-mode`, `--chain-scope`, `--contest-rpc-endpoint-env`, `--artifact`,
  `--artifact-format`을 추가했다.
- 명시적 `external_rpc` replay와 `provided_artifact`가 기존 analyzer를
  같은 raw replay로 실행한다.
- 옵션 없는 기존 `--evidence` 경로는 회귀 호환을 위해 유지한다.
- 이 보고서 실행 당시 분석기는 EVM 세 종류뿐이었으며 다른 chain scope는 실행 전에
  `chain_scope_mismatch`로 종료한다.
- `contest_rpc` endpoint는 환경변수에서만 읽고 안전한 HTTPS 여부를
  확인한다. 문제별 query mapping이 승인되지 않았으므로 네트워크 호출 없이
  `unsupported_input`으로 종료한다.

### 2.3 Operations

- `EvidenceWorkerCommand.input_evidence`가 선택적으로 envelope를 받는다.
- Worker는 envelope raw hash와 `ApprovedReplay` hash, 현재 EVM scope를
  adapter 호출 전에 검사한다.
- 성공 event에는 endpoint·API key·로컬 절대 경로 없이 mode·scope·source·
  provider·media type·raw/record hash·locator만 기록한다.

## 3. 검증

집중 검증은 다음을 포함한다.

- explicit `external_rpc`·`provided_artifact` DEX complete
- legacy `--evidence` DEX·AUTH·FREEZE 회귀
- mode 옵션 충돌과 chain mismatch의 persistence 전 exit 2
- contest endpoint 환경변수 비노출·network 0
- envelope URI·hash 불일치 거부
- 정규화→artifact→ApprovedReplay byte/hash 일치
- Operations event의 safe input provenance
- envelope mismatch의 adapter 0회

전체 offline Gate 결과:

```text
345 passed
PASS 7 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
PASS operations contract 0.1 generated Schema and runtime agree across 17 probes
PASS repository traceability: 1197 links, 19 TASK IDs, 36 QA IDs, 3 fixture/example mappings
PASS repository security scan: 97 runtime/evidence files
```

## 4. 보안·회귀 판정

| 항목 | 결과 |
|:---|:---:|
| endpoint 값 CLI 인자·stdout·stderr·SQLite·event 비노출 | pass |
| invalid raw input artifact 미저장 | pass |
| contest RPC query mapping 전 network 호출 | 0 |
| allowlist·HTTPS·userinfo core Gate 재사용 | pass |
| 기존 DEX·AUTH·FREEZE 결과·Schema | unchanged |
| 새 dependency·lockfile | 없음 |

## 5. 잔여 범위

- 실제 대회 문제의 contest RPC method·params mapping
- vendor·문제별 JSON/CSV/trace mapping
- `evm_core` Analysis I/O 정식 version과 TASK-012 analyzer
- Bitcoin·non-EVM·cross-chain consumer
- live AI·CTFd 자동 제출

다음 구현은 이 보고서가 아니라 TASK-012의 별도 Context Receipt와 사용자
승인을 따른다.

## 6. Related Documents

- **Technical_Specs**: [CLI·Operations 연결 계약](../03_Technical_Specs/13_WP_INPUT_CLI_OPERATIONS_CONTRACT.md) - 옵션·envelope·보안 규범
- **Technical_Specs**: [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - 상위 input·chain 계약
- **UI_Screens**: [입력 소스 선택 UI](../02_UI_Screens/06_INPUT_SOURCE_SELECTION_UI.md) - 승인된 표시·오류 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - WP-INPUT-IMPL-02 Receipt
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 0 완료·문제별 mapping 잔여
- **QA_Validation**: [Core Input Library 보고서](./30_WP_INPUT_GATE_CORE_REPORT.md) - WP-INPUT-IMPL-01 선행 구현
