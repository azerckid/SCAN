# TASK-016 bridge_transfer Analyzer 독립 Verification Receipt

> Created: 2026-07-31 04:20
> Last Updated: 2026-07-31 04:20
> Status: Passed · Offline Analyzer 독립 검증 완료 · Fixture Verifying 유지 · Benchmark 12·4·14 유지

## 1. 목적과 판정

사용자 Context Receipt `PASS`·offline 구현 승인(2026-07-31)과 PR #108
병합(`1f1e4ea`) 이후 구현한 `bridge_transfer` 제품 analyzer
(`scan_tool.slices.bridge_transfer`)가 독립 Verifier
(`task_016_bridge_independent_verifier.py`)와 별도 코드 경로로 같은
raw-first 결론에 도달하는지 검증한다. 두 코드는 서로 import하지 않는다.

**판정: `FX-SVC-BRG-001` analyzer가 `complete`를 산출했고,
`results[0].value`의 canonical SHA-256이 독립 Verifier가
`evidence.json`에 고정한
`d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac`과
정확히 일치했다. 두 번의 결정적 실행, CLI `--evidence` 경로, AST
forbidden-import 검사도 통과했다.**

이 Receipt는 **구현·독립 검증 완료**만 기록한다.
`확정(confirmed)` 승격과 Benchmark 자동화 승격은 별도 Gate이며 이
문서로 승격하지 않는다.

## 2. 독립성 경계

- `slices/bridge_transfer.py`·`domain/bridge_transfer.py`는
  `application/task_016_bridge_independent_verifier.py`와
  `application/task_016_bridge_replay.py`를 import하지 않는다
  (`scripts/verify_task_016_bridge_analyzer_independent_verification.py` AST
  검사).
- analyzer와 verifier는 같은 content-addressed raw JSON-RPC artifact를
  서로 다른 구현으로 재디코딩한다. `expected.json`을 계산 입력으로 쓰지
  않는다.
- analyzer hash gate는 verifier 모듈을 import하지 않고
  `evidence.json.verification_provenance.calculated_fact_sha256`과만
  대조한다. `scripts/verify.py`에 연결됐다.

## 3. 검증 결과

| Fixture | query | analyzer 상태 | canonical hash | verifier pin | 일치 |
|:---|:---|:---:|:---|:---|:---:|
| `FX-SVC-BRG-001` | link_bridge_transfer | complete | `d6609bb4…00ac` | 동일 | pass |

추가로 확인한 조건:

- topic0 signature와 log↔receipt↔transaction↔block exact binding
  (`blockHash`·전체 `topics`·`data`·`blockNumber`·`removed==false`)을
  통과한 뒤 ABI를 처음부터 재디코딩한다.
- attribution `recipient_ownership`·`criminality`는 `not_assessed`.
- offline_mode=false는 `rule_restricted`로 거부된다.
- CLI `--evidence` 파일 경로로 `COMPLETE`를 산출한다. `replay_body`만
  전달하면 `AnalysisUnavailable`로 명확히 거부한다(Evidence Worker
  byte-only·silent partial 금지, PR #108 P1 Option 2).
- `adapters/evidence.py` stage map에는 `BRIDGE_TRANSFER`가 없다
  (FLOW/INTEL과 동일).
- `REQ-BRIDGE-SOURCE`·`REQ-BRIDGE-DESTINATION`·`REQ-BRIDGE-DOMAIN`이
  complete result에 채워지고 공개 `analysis-result.schema.json` 패턴이
  이를 허용한다.

## 4. 독립 검증 중 발견한 Schema 결함과 정정

독립 Verification Agent가 공개 Schema와 runtime 불일치를 발견했다.

| # | 결함 | 정정 |
|:---|:---|:---|
| P1 | 공개 `analysis-result.schema.json`의 `FixtureRequirementId` 패턴에 `BRIDGE`가 없어 complete `REQ-BRIDGE-*`가 공개 Schema에서 거부됨. `check_analysis_schema.py` bridge result probe가 EVM fixture_requirement만 재사용해 이 구멍을 놓침 | 공개 Schema 패턴에 `BRIDGE` 추가. bridge result probe가 `REQ-BRIDGE-SOURCE/DESTINATION/DOMAIN`을 포함하도록 정정 |

정정 후 공개 Schema가 analyzer `to_contract_dict()`를 수락한다. 이 정정은
fixture lifecycle·Benchmark·canonical hash를 바꾸지 않는다.

## 5. Commands and Results

| Command | Result |
|:---|:---|
| `uv run python scripts/verify_task_016_bridge_analyzer_independent_verification.py` | PASS — hash `d6609bb4…00ac`, 2 deterministic runs, forbidden imports absent |
| `uv run python scripts/verify_task_016_bridge_independent_verifier.py` | PASS — 1 fixture, 3 requirements, 2 deterministic runs, same hash |
| `uv run python scripts/verify_task_016_bridge_negative_oracles.py` | PASS — 8 oracles × 2 |
| `uv run pytest tests/unit/test_task_016_bridge_analyzer.py tests/integration/test_task_016_bridge_cli.py` | PASS — 6 tests |
| `uv run python scripts/check_analysis_schema.py` | PASS — 57 probes (bridge result now exercises `REQ-BRIDGE-*`) |
| `uv run python scripts/verify.py` | PASS — 570 tests, traceability 1925, security 226 |
| public JSON Schema validate of complete bridge result | PASS after Schema P1 sync |

### Unrun Checks

- N/A — planned independent checks above ran.
- live Rules·network fetch는 offline 승인 범위 밖이라 실행하지 않았다.

## 6. Confirmed invariants / non-goals

| Item | Verdict |
|:---|:---|
| Analyzer ↔ verifier isolation | Confirmed |
| Exact binding + canonical hash `d6609bb4…00ac` | Confirmed |
| Offline-only + CLI `--evidence` path requirement | Confirmed |
| Type/query dispatch isolation | Confirmed |
| Public Schema accepts `REQ-BRIDGE-*` | Confirmed after P1 sync |
| Fixture remains `verifying` | Confirmed |
| Benchmark remains 12 / 4 / 14 | Confirmed |
| No confirmed promotion in this Gate | Confirmed non-goal |
| No Benchmark flip / MIXED-XCHAIN | Confirmed non-goal |

## 7. Residual (다음 Gate)

1. `verifying → confirmed` 별도 승격 검토
2. Benchmark automated 승격 여부 별도 판정
3. `MIXED-XCHAIN-001` 조합 Gate는 계속 별도

## 8. Related Documents

- **Technical_Specs**: [Bridge/XChain 계약](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md) - 대안 B·offline 구현 경계
- **QA_Validation**: [Bridge 승격 검토](./63_TASK_016_BRIDGE_FIXTURE_PROMOTION_REVIEW.md) - verifying 유지·잔여 Gate
- **QA_Validation**: [Bridge Raw Replay](./62_TASK_016_BRIDGE_RAW_REPLAY_REPORT.md) - 16 call·oracle·독립 Verifier
- **QA_Validation**: [Fixture FX-SVC-BRG-001](./fixtures/FX-SVC-BRG-001/README.md) - verifying package
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - Context·Change·Verification Receipt
- **Logic_Progress**: [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md) - confirmed/Benchmark 별도 판정
- **Implementation**: PR #108 · merge `1f1e4ea`

## 9. Harness Verification Receipt summary

- Verification Receipt:
  - Status: PASS
  - Commands and Results:
    - `scripts/verify_task_016_bridge_analyzer_independent_verification.py` - PASS - hash `d6609bb4…00ac`, 2 runs, AST isolation
    - `scripts/verify_task_016_bridge_independent_verifier.py` - PASS - same hash
    - focused bridge analyzer/CLI pytest - PASS - 6
    - `scripts/verify.py` - PASS - 570 tests, 1925 links, 226 security
    - public analysis-result schema validate complete bridge result - PASS after BRIDGE pattern sync
  - Unrun Checks:
    - N/A - planned checks ran; live Rules/network remain out of approved offline scope
  - Detailed Evidence:
    - [64 Bridge Analyzer Verification Receipt](./64_TASK_016_BRIDGE_ANALYZER_VERIFICATION_RECEIPT.md) - this document
    - [PR #108](https://github.com/azerckid/SCAN/pull/108) - analyzer implementation and P1 Evidence Worker boundary
