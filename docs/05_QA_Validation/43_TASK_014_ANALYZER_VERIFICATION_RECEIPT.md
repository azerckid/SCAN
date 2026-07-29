# TASK-014 flow_path Analyzer 독립 Verification Receipt

> Created: 2026-07-30
> Last Updated: 2026-07-30
> Status: Passed · Analyzer 구현·독립 검증 완료 · Fixture 3 Verifying 유지 · Benchmark 9/9 유지

## 1. 목적과 판정

사용자 Context Receipt `PASS`·구현 승인(2026-07-30) 이후 구현한 `flow_path`
제품 analyzer(`scan_tool.slices.flow_path`)가 독립 Verifier
(`task_014_independent_verifier.py`)와 별도 코드 경로로 같은 raw-first 결론에
도달하는지 검증한다. 두 코드는 서로 import하지 않는다.

**판정: 세 `검증 중` fixture 모두 analyzer가 `complete`를 산출했고, 그
결과 `results[0].value`의 canonical SHA-256이 독립 Verifier가 재계산해
evidence.json에 고정한 `calculated_fact_sha256`과 정확히 일치했다. 두 번의
결정적 실행도 통과했다.**

이 Receipt는 **구현·독립 검증 완료**만 기록한다. `확정(confirmed)` 승격과
Benchmark 자동화 승격은 [flow_path I/O 계약](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md)
§7의 **단일-trace 하드 게이트**가 닫힌 뒤 별도로 판단하며, 이 문서로는
승격하지 않는다.

## 2. 독립성 경계

- `slices/flow_path.py`(Pydantic 타입 모델)는
  `application/task_014_independent_verifier.py`(raw dict 파싱)를 import하지
  않는다. 두 모듈은 같은 `raw-replay.json`을 서로 다른 방식으로 재해석한다.
- `domain/flow_path.py`의 reviewed replay 모델은 raw JSON 구조를 그대로
  받고, verifier처럼 `expected.json`을 계산 입력으로 쓰지 않는다.
- `scripts/verify_task_014_analyzer_independent_verification.py`는 analyzer
  결과의 canonical hash를 evidence.json에 고정된 값과 비교하며 verifier
  모듈을 import하지 않는다. `scripts/verify.py`에 연결했다.

## 3. 검증 결과

| Fixture | query | analyzer 상태 | canonical hash | 고정된 verifier hash | 일치 |
|:---|:---|:---:|:---|:---|:---:|
| `FX-FLOW-PATH-001` | trace_path | complete | `a836b7d1…71bc` | 동일 | pass |
| `FX-FLOW-REMERGE-001` | trace_remerge | complete | `1a93d95a…67a5` | 동일 | pass |
| `FX-FLOW-MULTI-001` | aggregate_origins | complete | `e42146e1…483b` | 동일 | pass |

추가로 확인한 조건:

- 세 fixture 모두 `results[0].value`가 `expected.json`의 채점 필드와 정확히
  일치한다(graph/path_candidates/reconciliation, branches/reconciliation/
  excluded_edges, exit_node/contributions/deduplicated_total_raw/price_context/
  attribution).
- 두 번 실행한 `AnalysisResult.to_contract_dict()`가 완전히 동일해 결정적이다.
- `scan analyze --request … --evidence …` CLI로 세 fixture 모두 `COMPLETE`·
  `schema_version 0.2`·checkpoint 1개로 저장되고 `scan show`가 재현한다.
- internal seed trace를 제거하면 CLI가 `PARTIAL`·exit 3·`trace_unavailable`을
  반환하고 확인된 하위 경로를 보존한다(단일-trace 의존성의 정직한 처리).
- `scan analyze`를 KeyboardInterrupt로 중단한 뒤 `scan resume`이 저장된
  replay artifact에서 `resumed yes`로 완료한다(네트워크 재호출 없음).

## 4. scope_status 필수화에 따른 fixture·Verifier·hash 재계산

계약(doc 16 §8·§9)이 `scope_status`를 필수 결과 필드로 확정했으므로 다음을
반영했다.

- 세 fixture `expected.json`: `graph.edges[]`에 `scope_status: included`,
  `excluded_edges[]`에 `scope_status: excluded`를 추가(MULTI는 edge 배열이
  없어 변경 없음).
- 독립 Verifier(`_edge_from_internal`/`_edge_from_transaction`/`_remerge`)가
  같은 `scope_status`를 산출하도록 갱신하고, MULTI 결과에 `price_context`·
  `attribution` 상수를 포함해 analyzer 값과 동일 구조가 되게 했다.
- pinned `calculated_fact_sha256` 3개를 재계산해 evidence.json을 갱신
  (PATH·REMERGE·MULTI 모두 변경). analyzer 결과 hash와 재계산 hash가 다시
  일치함을 §3에서 확인했다.

## 5. 계약 확장 경계

- Analysis I/O `schema_version`은 계속 `{"0.1", "0.2"}`이며 `0.2`에 신규
  `flow_path`(`AnalysisType`, discriminated request/result variant)를 더했다.
  `evm_core`·`evm_special`·기존 `0.1` 분석기 결과는 변경하지 않았다.
- **새 공개 `ErrorCode`를 추가하지 않았다.** `source_unavailable`·
  `reconciliation_failed`·`trace_unavailable`·`evidence_incomplete`·
  `rule_restricted`·`decode_failed` 기존 enum만 재사용하고 PATH 고유 사유는
  `stage`로 전달한다(doc 16 §5 매핑).
- `FixtureRequirementId` 패턴과 정적 `analysis-result.schema.json`의
  `fixture_requirement_ids` 정규식에 `FLOW` 접두를 추가했다.
- `analysis-request.schema.json`에 `flow_path` type·query_kind family binding을
  추가하고 `check_analysis_schema.py`에 교차 조합 probe 4개를 더해 44→48
  probe로 확장했다. `operations-contract.schema.json`의 `AnalysisType` enum도
  동기화했다.

## 6. 산출물

- `src/scan_tool/domain/flow_path.py` — reviewed replay 모델
- `src/scan_tool/domain/analysis_request.py` — `FlowPathQueryKind`,
  `TracePath/TraceRemerge/AggregateOriginsInputs`, `FlowPathAnalysisRequest`
- `src/scan_tool/domain/analysis_result.py` — `FlowPathComplete/Partial/FailedAnalysisResult`
- `src/scan_tool/slices/flow_path.py` — `analyze_flow_path_replay`
- `src/scan_tool/application/cli_runtime.py` — dispatch·`FLOW_PATH_REPLAY_STAGE`
- `src/scan_tool/application/task_014_independent_verifier.py` — scope_status·MULTI 상수 반영
- `docs/05_QA_Validation/fixtures/FX-FLOW-*/analysis-request.json` — 신규
- `docs/05_QA_Validation/fixtures/FX-FLOW-*/expected.json`·`evidence.json` — scope_status·hash 갱신
- schema 3종·`check_analysis_schema.py`·`check_task_012_analysis_contract_proposal.py` — 갱신
- `tests/unit/test_flow_path_slice.py`(18)·`tests/integration/test_flow_path_cli.py`(5)
- `scripts/verify_task_014_analyzer_independent_verification.py` — verify.py 연결

## 7. 상태 경계와 다음 Gate

- Fixture 3개: `검증 중` 유지(확정 승격 안 함).
- Benchmark: 9/9 유지(자동화 승격 안 함).
- 전체 게이트: 459 tests PASS, fixture 13, traceability 1477 links, security
  162 files, TASK-014 negative oracle 18×2·독립 Verifier 3×2·analyzer 독립
  검증 3 fixtures PASS.
- **다음: [단일-trace 하드 게이트](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md#7-단일-trace-의존성--confirmed-전-하드-게이트)를
  닫은 뒤 `확정`·Benchmark 자동화 승격을 별도 판단한다.**

## 8. Related Documents

- **Technical_Specs**: [flow_path I/O 계약](../03_Technical_Specs/16_TASK_014_FLOW_PATH_IO_CONTRACT.md) - request/result·오류 매핑·단일-trace 게이트
- **Technical_Specs**: [TASK-014 PATH 계약](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - graph·ledger 계약
- **QA_Validation**: [TASK-014 독립 Verifier 보고서](./42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) - 고정 fact hash의 최초 근거
- **QA_Validation**: [TASK-014 replay·oracle 보고서](./41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) - 단일 trace disclosure
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 상태 registry
- **Logic_Progress**: [Backlog TASK-014](../04_Logic_Progress/00_BACKLOG.md) - 진행 상태
