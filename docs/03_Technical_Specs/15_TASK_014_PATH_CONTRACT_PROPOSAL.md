# TASK-014 PATH Graph·금액 정합 계약 제안
> Created: 2026-07-29 22:52
> Last Updated: 2026-07-29 23:05
> Status: Proposed 0.1 · Docs-only · Fixture 사례 미선정 · Implementation Not Approved

## 1. 목적

이 문서는 `FLOW-EVM-001`, `FLOW-EVM-002`, `FLOW-MULTI-001`을 자동화하기
전에 필요한 bounded graph, 금액 정합, exclusion, partial/failed 계약을
고정한다. 공개 TX 선정, fixture package 생성, Analysis I/O Schema 변경,
Python PATH analyzer 구현과 Benchmark 승격은 이 문서의 완료 범위가 아니다.

TASK-012 EVM Core가 만든 transaction·receipt·log·internal-call evidence를
재사용하되, PATH는 해당 사실을 임의로 다시 해석하지 않고 명시적 edge로
연결한다. 라벨·AI 가설·가격은 경로 존재와 분리한다.

## 2. 현재 기준선과 승인 경계

| 항목 | 현재 상태 | TASK-014 결정 |
|:---|:---|:---|
| Benchmark | automated 9 / assisted 0 / unsupported 21 | FLOW 3문항은 아직 unsupported |
| EVM 입력 | TASK-012 `evm_core`·WP-INPUT 완료 | normalized EVM evidence 재사용 |
| 전문 해석 | TASK-013 `evm_special` 완료 | PATH는 별도 analysis type 후보 |
| PATH fixture | 공개 사례 미선정 | 세 proposed package의 선정 조건만 고정 |
| UI | 기존 Workbench는 범용 Draft | TASK-014 전용 정적 Preview를 별도 작성 |
| Runtime | PATH analyzer 없음 | Context Receipt·사용자 구현 승인 전 코드 금지 |

## 3. 문제와 Fixture 후보

| Fixture ID | 대상 문제 | 공개 사례가 반드시 포함할 사실 | 상태 |
|:---|:---|:---|:---:|
| `FX-FLOW-PATH-001` | FLOW-EVM-001 | seed에서 3홉 이상 이어지는 단일 자산 경로, 명확한 terminal address, hop별 TX·raw amount | proposed |
| `FX-FLOW-REMERGE-001` | FLOW-EVM-002 | 한 seed의 2개 이상 분기, 공통 merge address, unrelated inflow 1건 이상, residual 정답 | proposed |
| `FX-FLOW-MULTI-001` | FLOW-MULTI-001 | 둘 이상 origin의 동일 exit 유입, origin별 contribution, 중복 방지, 가격은 별도 context | proposed |

선정할 공개 사례는 다음을 만족해야 한다.

- Ethereum mainnet 공개 TX·block·주소만 사용하고 서명·mutation을 요구하지 않는다.
- 두 논리 공급자 또는 공급자+고정 raw artifact가 동일 edge 집합을 재현한다.
- seed·range·asset·hop/node/edge budget을 명시한다.
- path 정답뿐 아니라 제외 edge와 중단·residual 정답을 가진다.
- 동일 주소로 간 무관 자금, cycle, dust 또는 범위 밖 edge 중 하나 이상을
  반례로 포함한다.
- 범죄·피해자·서비스 귀속은 fixture 정답이 아니라 `not_assessed`다.

## 4. 그래프 불변조건

### 4.1 Node

- `node_id`: `chain_scope + normalized address`
- `chain_scope`: 첫 버전은 `evm`만 허용한다.
- `first_seen_block`, `last_seen_block`
- label은 선택적 context이며 node identity를 바꾸지 않는다.

### 4.2 Edge

모든 edge는 다음 최소 필드를 가진다.

- `edge_id`: 결정적 content key
- `from_node`, `to_node`
- `asset_id`: native 또는 contract address
- `amount_raw`, `decimals`
- `transaction_hash`, `block_number`, `transaction_index`
- `evidence_refs[]`, `source_refs[]`
- `transfer_kind`: `native_top_level | native_internal | erc20_transfer`
- `scope_status`: `included | excluded | unresolved`

같은 자산·같은 원본 이동을 중복 edge로 만들지 않는다. top-level native와
internal native를 근거 없이 합산하지 않으며, ERC-20과 native/wrapped
자산을 환율 없이 한 ledger에 더하지 않는다.

### 4.3 Bounded traversal

요청은 다음 상한을 반드시 가진다.

- `max_hops`
- `max_nodes`
- `max_edges`
- `block_range` 또는 `time_range`
- `asset_scope`

상한 도달은 실패가 아니라 확인된 경로와 `termination`을 보존한
`partial`이다. 무제한 BFS/DFS, 자동 graph DB 확장, Rules 밖 live 탐색은
허용하지 않는다.

## 5. Analysis I/O 제안

### 5.1 대안

| 대안 | 장점 | 위험 |
|:---|:---|:---|
| A. `evm_core` query 확장 | 입력 routing 단순 | bounded graph·ledger 책임이 Core와 혼합 |
| B. `flow_path` analysis type 신설 | graph·reconciliation·Verifier 격리 | 새 request/result variant 필요 |

**제안: B.** `evm_core`는 원자적 온체인 사실을 만들고 `flow_path`가
그 evidence를 그래프로 조합한다. 정식 선택은 fixture 후보와 Preview를
사용자가 확인한 뒤 별도 승인한다.

### 5.2 Query 후보

`trace_path`

- 입력: `seed_node`, `direction`, `asset_scope`, range, budgets,
  terminal policy
- 결과: 정렬된 `path_candidates[]`, terminal, excluded edges

`trace_remerge`

- 입력: `seed_node`, branch threshold, merge threshold, range, budgets
- 결과: `branches[]`, `merge_candidates[]`, selected merge,
  reconciliation ledger

`aggregate_origins`

- 입력: `origin_nodes[]`, `exit_node`, asset scope, range, budgets
- 결과: origin별 contribution, deduplicated total, unresolved residual
- 가격 환산은 PATH 결과와 별도 PRICE context로 유지한다.

### 5.3 결과 후보

공통 결과:

- `graph`: nodes·edges와 범위
- `path_candidates[]`: ordered edge IDs, raw amount, termination
- `excluded_edges[]`: exclusion reason과 evidence
- `reconciliation[]`: asset별 input, included, excluded, fee/context,
  unresolved residual
- `warnings[]`, `evidence[]`, `sources[]`, `run`

정렬은 `(block_number, transaction_index, evidence_position, edge_id)`를
기본으로 하고, 후보 경로는 `(hop_count, terminal_block, terminal_node,
edge_id sequence)`로 결정적으로 정렬한다.

## 6. 상태와 오류 계약

| 상태 | 조건 | 데이터 |
|:---|:---|:---|
| complete | 요청 범위·budget 안에서 필수 edge와 terminal/merge가 재현되고 residual이 허용 범위 이내 | graph·path·ledger 전부 |
| partial | budget/range/비필수 source 한계로 일부 frontier가 미확인이나 확인된 edge는 유효 | 확인된 graph + termination + unresolved frontier |
| failed | seed/scope가 invalid, 필수 source 결합·reconciliation 실패, 필수 edge가 서로 모순 | `data: null` + 구조화 오류 |

오류 후보:

- `path_seed_unavailable`
- `path_scope_invalid`
- `path_budget_exhausted`
- `path_frontier_unresolved`
- `path_reconciliation_failed`
- `path_asset_mismatch`
- `path_cycle_only`
- `path_source_unavailable`

`path_budget_exhausted`와 `path_frontier_unresolved`는 확인된 graph가 있으면
`partial`이다. `path_source_unavailable`도 비필수 source 일부만 누락되고
확인된 edge가 유효하면 `partial`이다. 반대로 seed·asset·range를 입증할
필수 source가 없거나 source들이 서로 다른 raw 사실을 주장하거나 request
scope와 replay가 결합되지 않으면 `failed`다.

## 7. Exclusion·금액 정합

- unrelated edge는 조용히 버리지 않고 `excluded_edges[]`에 이유를 남긴다.
  단, seed/origin에서 시작하지 않은 external inflow는 보존식의
  `confirmed_excluded_output_raw`에 넣지 않고 별도 context로 표시한다.
- 포함·제외 규칙은 amount 유사성만으로 결정하지 않는다.
- branch별 contribution은 동일 원본 edge를 한 번만 집계한다.
- fee, swap, bridge, rebasing, fee-on-transfer는 검증된 전문 adapter 없이
  보존 법칙을 가정하지 않는다.
- 자산별 residual:

```text
residual_raw = confirmed_input_raw
             - confirmed_included_output_raw
             - confirmed_scoped_excluded_output_raw
             - explicit_fee_or_context_raw
```

여기서 `explicit_fee_or_context_raw`는 seed 자금에서 실제로 차감된 것으로
입증된 값만 허용한다. 다른 origin의 external inflow는 graph context일 뿐
seed ledger의 차감 항목이 아니다. 음수 residual, 서로 다른 asset 합산,
근거 없는 환율 변환은
`path_reconciliation_failed`다.

## 8. Negative Oracle 계획

최소 반례:

1. 같은 금액이지만 seed와 연결되지 않은 unrelated transfer
2. 동일 edge 중복 수집
3. A→B→A cycle
4. range 밖의 terminal 또는 merge
5. max hop/node/edge 초과
6. 다른 token contract의 같은 symbol
7. top-level/internal native 중복 집계
8. 일부 branch만 merge된 경우
9. merge address는 같지만 사건 자금과 무관한 inflow
10. price context 누락을 path 실패로 오판
11. provider 간 block/amount 불일치
12. origin 두 개가 같은 edge를 공유하는 중복 집계

각 fixture는 complete·partial·failed와 두 번의 결정성 실행, 독립
Verifier 재계산을 통과해야 한다.

## 9. UI·저장·성능 경계

- [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md)는 single,
  remerge, multi-origin과 complete·partial·failed를 비교한다.
- graph UI는 Analysis result의 read-only view다. 별도 브라우저 계산을
  진실 원천으로 만들지 않는다.
- 첫 버전은 in-memory bounded graph와 content-addressed artifact를
  사용한다. SQLite v2와 graph DB migration은 하지 않는다.
- `networkx`, Neo4j, DuckDB를 기본 의존성으로 추가하지 않는다. fixture
  규모에서 stdlib 구조가 부족하다는 측정 근거가 있을 때 별도 승인한다.

## 10. 365 평가 기준과 윤리

| 기준 | 이 설계의 대응 |
|:---|:---|
| Functionality | 세 FLOW 문제의 graph·exclusion·ledger를 결정적으로 검증 |
| Potential Impact | PATH가 18개 예상문제의 공통 병목을 줄임 |
| Novelty | 예쁜 graph보다 excluded edge·residual·독립 Verifier를 우선 |
| UX | 경로·분기·중단 frontier를 한 화면에서 검토 |
| Open-source | bounded 자료구조·JSON 계약·fixture를 재사용 가능하게 분리 |
| Business Plan | 대회 준비 범위에서는 N/A |

주소의 실제 소유자, 범죄 의도, 피해자 여부, 서비스 귀속은 PATH 결과가
아니다. AI Planner는 탐색 방법과 leaf job을 제안할 수 있지만 graph edge와
금액은 Python analyzer와 독립 Verifier가 실증한다.

## 11. 구현 전 Gate

- [ ] 공개 사례 3개를 선정하고 fixture package를 `candidate`로 작성
- [ ] 두 공급자 또는 공급자+artifact replay로 edge 집합 재현
- [ ] negative oracle과 독립 Verifier 작성
- [ ] `flow_path` 대안 B 정식 승인
- [ ] HTML Preview 사용자 확인·피드백 반영
- [ ] Context Receipt `PASS`
- [ ] 사용자 analyzer 구현 승인

## 12. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - FLOW 3문항의 완료·부분·실패 기준
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - PATH 18개 필수 근거
- **UI_Screens**: [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - 화면·상태·사용자 검토 Gate
- **UI_Screens**: [PATH HTML Preview](../02_UI_Screens/previews/07_task_014_path_preview.html) - docs-only 상호작용 화면
- **Technical_Specs**: [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-PATH 상위 계약
- **Technical_Specs**: [Analysis I/O](./05_ANALYSIS_IO_SCHEMA.md) - 공통 envelope와 버전 경계
- **Logic_Progress**: [Backlog TASK-014](../04_Logic_Progress/00_BACKLOG.md) - Context Lock·구현 승인
- **QA_Validation**: [TASK-014 Fixture·Contract Gate](../05_QA_Validation/39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 승격 전 QA 기준
