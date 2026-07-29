# TASK-014 `flow_path` Analysis I/O 계약 (대안 B 확정안)

> Created: 2026-07-30
> Last Updated: 2026-07-30 10:52
> Status: **Proposed · docs-only · 사용자 승인 대기** · Fixture 3 Verifying · Runtime Not Implemented

## 0. 이 문서의 위치

[TASK-014 PATH 계약 제안](./15_TASK_014_PATH_CONTRACT_PROPOSAL.md) §5는 Analysis
I/O 대안 B(`flow_path` 신설)를 **제안**만 했다. 이 문서는 그 대안 B를
구현 착수 전에 **필드·상태·오류·예제 단위로 확정**한다. 목표는 fixture·
oracle·Verifier가 이미 준비된 상태에서 제품 analyzer를 짤 때 Schema·CLI·UI가
다시 흔들리지 않도록 계약 표면을 미리 닫는 것이다.

이 문서는 docs-only다. 공개 enum·Pydantic 모델·JSON Schema·CLI 코드는
사용자 정식 승인과 별도 구현 승인 전까지 **변경하지 않는다**. 아래 "구현 시
필요한 계약 확장"은 승인 이후에 적용할 변경의 명세일 뿐, 이 문서로 적용되지
않는다.

## 1. 대안 B 확정 요지

- 신규 `AnalysisType.FLOW_PATH = "flow_path"`를 `schema_version "0.2"`에
  추가한다. `evm_core`·`evm_special`·기존 `0.1` 분석기 결과는 바꾸지 않는다.
  (TASK-013이 `0.2`에 `evm_special`을 더한 것과 같은 격리 방식.)
- Query kind 3종: `trace_path`, `trace_remerge`, `aggregate_origins`.
- Request는 `analysis_type`으로 discriminate하고, `flow_path` 내부에서
  다시 `query_kind`로 `inputs` 모델을 discriminate한다(`evm_special`과 동일
  패턴).
- Result는 공통 envelope(`status`/`results`/`evidence`/`sources`/`warnings`/
  `errors`/`run`/`exports`)를 그대로 쓰고, `results[].value`만 query별로 다르다.
- **새 공개 오류 코드를 추가하지 않는다.** 기존 `ErrorCode` enum만 재사용하고
  PATH 고유 사유는 `stage`/`message`로 전달한다(§5). 이것이 §15 계약 §6의
  `path_*` 코드 초안을 대체한다.

## 2. Request envelope

공통 필드는 기존 `AnalysisRequestBase`와 동일하다.

```json
{
  "$schema": "../05_QA_Validation/schemas/analysis-request.schema.json",
  "schema_version": "0.2",
  "analysis_id": "AN-FX-FLOW-PATH-001",
  "analysis_type": "flow_path",
  "query_kind": "trace_path",
  "chain_id": 1,
  "fixture_id": "FX-FLOW-PATH-001",
  "requested_at": "2026-07-30T00:00:00+00:00",
  "inputs": { "...": "query_kind별 §3" },
  "source_policy": {
    "rule_status": "allowed",
    "allowed_source_ids": ["DS-EVM-RPC-ARCHIVE"],
    "source_order": ["DS-EVM-RPC-ARCHIVE"],
    "allow_fallback": false,
    "offline_mode": true
  }
}
```

- 위 예시는 **전체 request envelope의 규범 예시**다. `$schema`를 포함하며,
  구현 후 정적 `analysis-request.schema.json`과 Pydantic 모델 양쪽을 통과해야
  한다. 아래 query별 `inputs`와 `results[0].value` 예시는 전체 envelope 안에
  들어가는 **규범 fragment**다. 코드 블록에는 축약 주소·해시·`…` placeholder를
  사용하지 않는다.
- `query_kind`와 `inputs`의 결합은 `evm_special`처럼 `model_validator`와
  `json_schema_extra.allOf(if/then)`로 이중 고정한다. 잘못된 조합은
  `schema_invalid`(공개 Schema)·`ContractViolation`(runtime) 양쪽에서 거부돼야
  하며, 구현 시 `check_analysis_schema.py`에 교차 조합 probe를 추가한다
  (TASK-013 P1-4 재발 방지).

### 2.1 공통 입력 요소와 query별 `scope`

`asset_scope`와 `budgets`는 세 query가 공유한다. `scope`는 query별 replay
경계를 숨기지 않기 위해 query discriminator에 묶인 별도 모델로 고정한다.
`block_windows`와 `block_range`를 같은 모델에서 선택적으로 섞지 않는다.

| 모델 | 필수 필드 | 비고 |
|:---|:---|:---|
| 공통 `NativeAssetScope` | `kind: native`, `symbol: ETH`, `decimals: 18` | v1은 native만. ERC-20은 후속 |
| 공통 `TraversalBudgets` | `max_hops`, `max_nodes`, `max_edges` | 모두 양의 정수. 상한 도달은 `partial` |
| `TracePathScope` | `kind`, `block_windows[]` | 세 selected TX의 exact-block window. `from <= to`, 비어 있지 않음 |
| `TraceRemergeScope` | `kind`, `block_range`, `selected_transactions[]`, `excluded_context_transactions[]` | split/return TX와 unrelated inflow를 명시적으로 분리 |
| `AggregateOriginsScope` | `kind`, `selected_transactions[]` | origin별 contribution TX 집합. 비어 있지 않고 중복 금지 |

세 모델의 `kind`는 모두
`selected_transactions_and_exact_blocks`다. query별 Pydantic 모델이 다른
필드를 강제하므로 공통 `scope` union의 모호성은 없다.

| query_kind | inputs 모델 | scope 모델 | query 전용 필드 |
|:---|:---|:---|:---|
| `trace_path` | `TracePathInputs` | `TracePathScope` | `seed_node`, `direction`, `terminal_policy` |
| `trace_remerge` | `TraceRemergeInputs` | `TraceRemergeScope` | `seed_node`, `merge_node` |
| `aggregate_origins` | `AggregateOriginsInputs` | `AggregateOriginsScope` | `origin_nodes[]`, `exit_node` |

## 3. Query별 inputs·result value

결과 `value`는 세 fixture의 `expected.json`에서 확정한 실제 필드다. 아래
값은 `FX-FLOW-*-001`의 값을 그대로 인용한다.

### 3.1 `trace_path`

**inputs**

```json
{
  "seed_node": "0x036cec1a199234fc02f72d29e596a09440825f1c",
  "direction": "outbound",
  "asset_scope": { "kind": "native", "symbol": "ETH", "decimals": 18 },
  "terminal_policy": {
    "terminal_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
    "stop_on": "selected_terminal_reached"
  },
  "budgets": { "max_hops": 3, "max_nodes": 4, "max_edges": 3 },
  "scope": {
    "kind": "selected_transactions_and_exact_blocks",
    "block_windows": [
      { "from": 16818102, "to": 16818102 },
      { "from": 16905356, "to": 16905356 },
      { "from": 16920430, "to": 16920430 }
    ]
  }
}
```

**complete → `results[0].value`**

```json
{
  "graph": {
    "node_count": 4,
    "edge_count": 3,
    "nodes": [
      "0x036cec1a199234fc02f72d29e596a09440825f1c",
      "0xb66cd966670d962c227b3eaba30a872dbfb995db",
      "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
      "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5"
    ],
    "edges": [
      {
        "edge_id": "EDGE-PATH-001",
        "from_node": "0x036cec1a199234fc02f72d29e596a09440825f1c",
        "to_node": "0xb66cd966670d962c227b3eaba30a872dbfb995db",
        "amount_raw": "88752697459828535340019",
        "transaction_hash": "0x298bde3f9e53f7a5d870f7f5d56ee2f5e41fa25e6eb5e74611ac97025405db55",
        "block_number": 16818102,
        "transfer_kind": "native_internal",
        "scope_status": "included"
      },
      {
        "edge_id": "EDGE-PATH-002",
        "from_node": "0xb66cd966670d962c227b3eaba30a872dbfb995db",
        "to_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
        "amount_raw": "7738250000000000000000",
        "transaction_hash": "0x79c10cf538667a0a7de40ce54d2444c9e9e17b5c62b321e739020df0015baeda",
        "block_number": 16905356,
        "transaction_index": 23,
        "transfer_kind": "native_top_level",
        "scope_status": "included"
      },
      {
        "edge_id": "EDGE-PATH-003",
        "from_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
        "to_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
        "amount_raw": "7738050000000000000000",
        "transaction_hash": "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d",
        "block_number": 16920430,
        "transaction_index": 55,
        "transfer_kind": "native_top_level",
        "scope_status": "included"
      }
    ]
  },
  "path_candidates": [
    {
      "ordered_edge_ids": ["EDGE-PATH-001", "EDGE-PATH-002", "EDGE-PATH-003"],
      "hop_count": 3,
      "terminal_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
      "termination": "selected_terminal_reached"
    }
  ],
  "reconciliation": {
    "status": "unresolved_selected_path_scope",
    "reason": "The selected path does not claim a continuous scan of the seed's other outputs.",
    "raw_amounts_must_not_be_equalized": true
  }
}
```

- `raw_amounts_must_not_be_equalized: true`는 홉마다 raw가 다른 것(7738.25 →
  7738.05 ETH)을 "같은 금액" 휴리스틱으로 연결하지 못하게 하는 계약이다.
- 정렬: edges는 `(block_number, transaction_index, edge_id)`, path_candidates는
  `(hop_count, terminal_block, terminal_node, edge_id sequence)`.

**partial 예 (단일 trace 의존 실현)** — internal seed trace가 없을 때: 상위
top-level 2홉(`EDGE-PATH-002/003`)은 confirmed로 유지, seed inflow edge는
`unresolved`, 상태 `partial`:

```json
{
  "status": "partial",
  "results": [
    {
      "result_id": "RES-FLOW-PATH",
      "result_type": "trace_path",
      "classification": "confirmed_fact",
      "value": {
        "graph": {
          "node_count": 3,
          "edge_count": 2,
          "nodes": [
            "0xb66cd966670d962c227b3eaba30a872dbfb995db",
            "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
            "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5"
          ],
          "edges": [
            {
              "edge_id": "EDGE-PATH-002",
              "from_node": "0xb66cd966670d962c227b3eaba30a872dbfb995db",
              "to_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
              "amount_raw": "7738250000000000000000",
              "transaction_hash": "0x79c10cf538667a0a7de40ce54d2444c9e9e17b5c62b321e739020df0015baeda",
              "block_number": 16905356,
              "transaction_index": 23,
              "transfer_kind": "native_top_level",
              "scope_status": "included"
            },
            {
              "edge_id": "EDGE-PATH-003",
              "from_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
              "to_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
              "amount_raw": "7738050000000000000000",
              "transaction_hash": "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d",
              "block_number": 16920430,
              "transaction_index": 55,
              "transfer_kind": "native_top_level",
              "scope_status": "included"
            }
          ]
        },
        "path_candidates": [],
        "frontier": [
          {
            "edge_id": "EDGE-PATH-001",
            "scope_status": "unresolved",
            "reason": "internal_trace_unavailable"
          }
        ],
        "termination": "budget_or_frontier_open"
      },
      "tool_requirement_ids": ["REQ-P0-EVM-005", "REQ-P0-EVM-006", "REQ-P0-EVM-008"],
      "fixture_requirement_ids": ["REQ-FLOW-PATH-ORDER", "REQ-FLOW-PATH-SCOPE"],
      "evidence_refs": ["EV-FLOW-PATH-HOP-2", "EV-FLOW-PATH-HOP-3"]
    }
  ],
  "errors": [
    {
      "error_id": "ERR-FLOW-TRACE-UNAVAILABLE",
      "code": "trace_unavailable",
      "stage": "internal_edge_trace",
      "retryable": true,
      "attempt_count": 0,
      "message": "The seed's internal inflow trace is unavailable from the archive trace provider."
    }
  ]
}
```

**failed 예** — endpoint 불연속(무관 edge 삽입):

```json
{
  "status": "failed", "results": [],
  "errors": [{
    "error_id": "ERR-FLOW-PATH-TOPOLOGY", "code": "reconciliation_failed",
    "stage": "path_topology", "retryable": false, "attempt_count": 0,
    "message": "Ordered edge endpoints do not join into a single native path."
  }]
}
```

위 partial/failed 블록은 공통 `evidence`/`sources`/`warnings`/`run`/`exports`
필드를 생략한 **outcome fragment**다. 생략된 필드는
[Analysis I/O Schema](./05_ANALYSIS_IO_SCHEMA.md)의 공통 envelope를 그대로
따른다. `failed`에는 존재하지 않는 `data` 필드를 만들지 않으며
`results: []`와 한 개 이상의 구조화 `errors`를 사용한다.

### 3.2 `trace_remerge`

**inputs**

```json
{
  "seed_node": "0xb66cd966670d962c227b3eaba30a872dbfb995db",
  "merge_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
  "asset_scope": { "kind": "native", "symbol": "ETH", "decimals": 18 },
  "budgets": { "max_hops": 2, "max_nodes": 6, "max_edges": 9 },
  "scope": {
    "kind": "selected_transactions_and_exact_blocks",
    "block_range": { "from": 16905356, "to": 16920507 },
    "selected_transactions": [
      "0x79c10cf538667a0a7de40ce54d2444c9e9e17b5c62b321e739020df0015baeda",
      "0xd4c7c88944783f3c39695bc5e6c5fcd8a399c0a103d822ac8bd96fad41a41866",
      "0x03a06cfb99cf699dd5f61088fdf015e17b8c2f258a17882f6ff4de8607a3e46e",
      "0x77720ab2ab2bb6550e9b4e1cb4b6c2033c2200ae3abb7ae51f89898f86ac1e2a",
      "0xc9641dceab1311d219523e5d3914df31f6a97986d5e331db45387037ea06a07c",
      "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d",
      "0x9f3edbd1eb404dec2e4d9aae93c739136f79c87f6382af25413ce705cc431f59",
      "0x19f802affe24572bac3af47983f42bbec6055117c6a32c3fddc58bd7545e5240"
    ],
    "excluded_context_transactions": [
      "0xcfec4f86f6d81c83b9b3520d6966936d17490988739a794bf1391562ecb909b6"
    ]
  }
}
```

**complete → `results[0].value`** (값은 `FX-FLOW-REMERGE-001/expected.json`):

```json
{
  "branches": [
    { "branch_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676", "input_raw": "7738250000000000000000",
      "merge_output_raw": "7738050000000000000000", "residual_raw": "200000000000000000" },
    { "branch_node": "0xc4e04ac48639ff077ebb36e7cfe0c4993b7b208e", "input_raw": "7738250000000000000000",
      "merge_output_raw": "7738050000000000000000", "residual_raw": "200000000000000000" },
    { "branch_node": "0x46e0be2df97dac791fc8e30cf2b2e4f58c50cf55", "input_raw": "7738250000000000000000",
      "merge_output_raw": "7737250000000000000000", "residual_raw": "1000000000000000000" },
    { "branch_node": "0x8765a35394c98e81b9d56d44248e1199d8e38a4c",  "input_raw": "7738250000000000000000",
      "merge_output_raw": "7738050000000000000000", "residual_raw": "200000000000000000" }
  ],
  "reconciliation": {
    "confirmed_input_raw": "30953000000000000000000",
    "confirmed_included_output_raw": "30951400000000000000000",
    "confirmed_scoped_excluded_output_raw": "0",
    "explicit_fee_or_context_raw": "0",
    "unresolved_residual_raw": "1600000000000000000",
    "external_inflow_raw_not_in_seed_ledger": "1000000000000"
  },
  "excluded_edges": [
    {
      "transaction_hash": "0xcfec4f86f6d81c83b9b3520d6966936d17490988739a794bf1391562ecb909b6",
      "from_node": "0xfa24ea2318dbc719b9d1a0d8eb7f282255c5bde0",
      "to_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
      "amount_raw": "1000000000000",
      "reason": "external_inflow_not_from_seed",
      "scope_status": "excluded"
    }
  ]
}
```

- 보존식(§15 §7):
  `residual = input − included − scoped_excluded − explicit_fee_or_context`.
  여기서 `30953 − 30951.4 − 0 − 0 = 1.6 ETH`. 브랜치별 residual(`0.2×3 + 1.0`)
  합계와 일치.
- external dust `1000000000000 wei`는 `excluded_edges` + `external_inflow_
  raw_not_in_seed_ledger`로만 표시하고 seed ledger 보존식에는 넣지 않는다.

**partial 예** — 4개 branch 중 1개 return TX 미확인: 확인된 3개 branch 유지,
`unresolved_residual_raw`에 미해결분 반영, `code: source_unavailable`,
`stage: branch_return_binding`, `retryable: true`.

**failed 예** — external inflow를 seed ledger에서 차감:
`status: failed`, `results: []`, `code: reconciliation_failed`,
`stage: ledger_reconciliation`.

### 3.3 `aggregate_origins`

**inputs**

```json
{
  "origin_nodes": [
    "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
    "0xc4e04ac48639ff077ebb36e7cfe0c4993b7b208e",
    "0x46e0be2df97dac791fc8e30cf2b2e4f58c50cf55",
    "0x8765a35394c98e81b9d56d44248e1199d8e38a4c"
  ],
  "exit_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
  "asset_scope": { "kind": "native", "symbol": "ETH", "decimals": 18 },
  "budgets": { "max_hops": 1, "max_nodes": 5, "max_edges": 4 },
  "scope": {
    "kind": "selected_transactions_and_exact_blocks",
    "selected_transactions": [
      "0xc9641dceab1311d219523e5d3914df31f6a97986d5e331db45387037ea06a07c",
      "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d",
      "0x9f3edbd1eb404dec2e4d9aae93c739136f79c87f6382af25413ce705cc431f59",
      "0x19f802affe24572bac3af47983f42bbec6055117c6a32c3fddc58bd7545e5240"
    ]
  }
}
```

**complete → `results[0].value`** (값은 `FX-FLOW-MULTI-001/expected.json`):

```json
{
  "exit_node": "0xee009faf00cf54c1b4387829af7a8dc5f0c8c8c5",
  "contributions": [
    {
      "origin_node": "0x46e0be2df97dac791fc8e30cf2b2e4f58c50cf55",
      "amount_raw": "7737250000000000000000",
      "transaction_hash": "0xc9641dceab1311d219523e5d3914df31f6a97986d5e331db45387037ea06a07c",
      "block_number": 16905415
    },
    {
      "origin_node": "0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676",
      "amount_raw": "7738050000000000000000",
      "transaction_hash": "0xe3f67f8e50042f09a3d9b6873bd15c14fa8b8176cfa1069bc1d3ab71e4b3fd0d",
      "block_number": 16920430
    },
    {
      "origin_node": "0x8765a35394c98e81b9d56d44248e1199d8e38a4c",
      "amount_raw": "7738050000000000000000",
      "transaction_hash": "0x9f3edbd1eb404dec2e4d9aae93c739136f79c87f6382af25413ce705cc431f59",
      "block_number": 16920468
    },
    {
      "origin_node": "0xc4e04ac48639ff077ebb36e7cfe0c4993b7b208e",
      "amount_raw": "7738050000000000000000",
      "transaction_hash": "0x19f802affe24572bac3af47983f42bbec6055117c6a32c3fddc58bd7545e5240",
      "block_number": 16920507
    }
  ],
  "deduplicated_total_raw": "30951400000000000000000",
  "price_context": { "status": "not_assessed", "included_in_scoring": false },
  "attribution": { "common_control_claim": false, "criminal_or_victim_claim": false, "status": "not_assessed" }
}
```

- `deduplicated_total_raw`는 origin별 contribution의 raw 합(중복 TX 1회만).
- 가격은 `price_context`에만 두고 채점에서 제외한다. 가격 부재는 실패가 아니다.
- `attribution`은 항상 `not_assessed`. 공통 소유·범죄·피해자 판정을 결과가
  주장하지 않는다.

**partial 예** — origin 4개 중 1개 TX 미확인: 확인된 contribution 유지,
`deduplicated_total_raw`는 확인분만, `code: source_unavailable`,
`stage: origin_binding`, `retryable: true`.

**failed 예** — 같은 TX가 두 origin에 중복 집계:
`status: failed`, `results: []`, `code: reconciliation_failed`,
`stage: origin_dedup`.

## 4. 결과 항목 규약

- `results[].result_type` = query_kind(`trace_path` 등), `result_id` =
  `RES-FLOW-PATH` / `RES-FLOW-REMERGE` / `RES-FLOW-MULTI`.
- `classification` = `confirmed_fact`. 그래프 존재·edge·금액은 confirmed
  fact이며, 소유·의도·서비스는 결과에 넣지 않는다.
- `tool_requirement_ids`는 현재 등록된 `REQ-P0-EVM-005`(정합),
  `REQ-P0-EVM-006`(자산·raw 분리), `REQ-P0-EVM-008`(exact raw)를 사용한다.
  새 `REQ-P0-PATH-*` ID를 문서에서 임의로 만들지 않는다.
  `fixture_requirement_ids`는
  fixture의 `REQ-FLOW-PATH-ORDER`/`REQ-FLOW-PATH-SCOPE`/
  `REQ-FLOW-REMERGE-BRANCHES`/`REQ-FLOW-REMERGE-LEDGER`/
  `REQ-FLOW-MULTI-CONTRIBUTIONS`/`REQ-FLOW-MULTI-TOTAL`.

## 5. 오류 계약 — 기존 `ErrorCode` enum 재사용 (신규 코드 없음)

`ErrorCode`는 고정된 공개 vocabulary다:
`invalid_input, unsupported_chain, source_unavailable, rate_limited,
archive_required, trace_unavailable, decode_failed, evidence_incomplete,
reconciliation_failed, schema_invalid, rule_restricted`.

§15 §6의 `path_*` 초안 코드는 **채택하지 않는다.** 대신 아래처럼 매핑하고
PATH 고유 사유는 `stage`(그리고 `message`)로 표현한다. 왼쪽은 negative
oracle이 쓰는 **내부 classification 문자열**, 오른쪽은 **공개 result `code`**다.

| 내부 classification | 공개 `code` | `stage` | outcome |
|:---|:---|:---|:---|
| seed source 없음(필수) | `source_unavailable` | `seed_resolution` | failed |
| 요청 scope invalid | `invalid_input` | `scope_validation` | failed |
| `budget_exhausted` | `evidence_incomplete` | `budget_traversal` | partial |
| frontier 미해결 | `evidence_incomplete` | `frontier_resolution` | partial |
| `trace_unavailable`(internal edge) | `trace_unavailable` | `internal_edge_trace` | partial |
| `branch_unavailable` / `origin_unavailable` | `source_unavailable` | `branch_return_binding` / `origin_binding` | partial |
| `path_reconciliation_failed` | `reconciliation_failed` | `ledger_reconciliation` | failed |
| `asset_mismatch` | `reconciliation_failed` | `asset_scope` | failed |
| `cycle_detected` | `reconciliation_failed` | `path_topology` | failed |
| `unrelated_edge_included` / `external_inflow_contamination` | `reconciliation_failed` | `ledger_reconciliation` | failed |
| `duplicate_edge` / `duplicate_contribution` | `reconciliation_failed` | `edge_dedup` / `origin_dedup` | failed |
| `negative_residual` | `reconciliation_failed` | `ledger_reconciliation` | failed |
| `exit_mismatch` / `origin_scope_mismatch` | `reconciliation_failed` | `origin_scope` | failed |
| `raw_amount_required`(반올림 대체) | `decode_failed` | `raw_amount` | failed |
| 필수 source conflict | `source_unavailable` | `source_binding` | failed |

- 내부 classification 문자열은 negative-oracle 계약(이미 병합됨)의
  `classification`이며 공개 Schema에 노출되지 않는다. 공개로 나가는 것은
  `code`(enum)·`stage`·`message`뿐이므로 이 매핑이 지켜지면 Schema는 흔들리지
  않는다.
- `partial`은 확인된 graph/ledger를 버리지 않는다. `failed`는
  `results: []`와 구조화 오류만 반환한다. 현재 공개 Analysis Result에는
  `data` 필드가 없으므로 `data: null`을 새로 만들지 않는다.

## 6. 상태 판정 우선순위

analyzer가 결과 상태를 정할 때 다음 순서로 판정한다(negative-oracle 결정
함수와 동일한 우선순위).

1. 필수 결합 실패(seed/scope/asset/source conflict) → `failed`
2. topology/ledger 모순(cycle, 불연속, 중복, external 오염, 음수 residual) → `failed`
3. raw 정수 미보존(반올림) → `failed`
4. budget/frontier/internal-trace/비필수 source 한계 → `partial`(확인분 보존)
5. 그 외 필수 edge·terminal/merge·ledger 재현 → `complete`

## 7. 단일 trace 의존성 — `confirmed` 전 하드 게이트

`FX-FLOW-PATH-001`의 seed inflow edge(`EDGE-PATH-001`, 88752.7 ETH,
그래프의 뿌리)는 현재 **primary provider의 `debug_traceTransaction`
한 곳**에서만 재현된다. 상위 top-level TX·receipt는 두 공급자 decoded
일치(`decoded_match: true`)지만 internal edge는 단일 소스다. 이는
[replay·oracle 보고서](../05_QA_Validation/41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md)
§3에 disclosure돼 있고 `verifying`에는 적합하다.

**`confirmed` 승격 전 다음 중 하나를 반드시 닫는다(하드 게이트):**

- [ ] 두 번째 trace 공급자(예: 다른 archive `debug_traceTransaction`/
  `trace_transaction` dialect)가 같은 internal edge를 재현, 또는
- [ ] 독립 재구성 교차검증: seed 노드의 해당 block 전후 `eth_getBalance`
  delta 또는 Blockscout internal-tx API를 2차 소스로 대조.

둘 다 실패하면 `FX-FLOW-PATH-001`은 `verifying`에 머문다. 이 게이트는
`trace_path` complete가 단일 trace에 의존하지 않음을 보장하기 위한 것이며,
analyzer는 internal edge가 미확인이면 §5의 `trace_unavailable`·`partial`을
반환해야 한다(성공 결과를 단일 trace로 덮지 않는다).

## 8. 승인된 PATH Preview와의 필드 대조

[TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md)가 확정한 화면
필드가 이 계약과 1:1 대응함을 확인한다.

| Preview 요소 (UI §5·§4) | 계약 필드 | 대응 |
|:---|:---|:---|
| `[INCLUDED]` edge | `graph.edges[]` + `scope_status: included` | ✓ |
| `[EXCLUDED]` edge | `excluded_edges[]` + `scope_status: excluded` (reason 포함) | ✓ |
| `[UNRESOLVED]` frontier | `partial` + `frontier[]` + `scope_status: unresolved` | ✓ |
| ledger `input` | `reconciliation.confirmed_input_raw` | ✓ |
| ledger `included` | `confirmed_included_output_raw` | ✓ |
| ledger `excluded` | `confirmed_scoped_excluded_output_raw` (external은 별도) | ✓ |
| ledger `fee/context` | `explicit_fee_or_context_raw` | ✓ |
| ledger `residual` | `unresolved_residual_raw` | ✓ |
| termination badge | `path_candidates[].termination` / merge_confirmed | ✓ |
| `not_assessed` | `attribution.status` / `price_context.status` | ✓ |
| 상태 badge COMPLETE/PARTIAL/FAILED | `status` + `errors[].code/stage` | ✓ |

- `scope_status` enum은 `included|excluded|unresolved`로 고정한다.
  `graph.edges[]`는 `included`, `excluded_edges[]`는 `excluded`,
  `partial`의 `frontier[]`는 `unresolved`만 허용한다. 한 항목을 두 배열에
  중복 배치하지 않는다.
- `scope_status`는 구현 시 추가할 선택 필드가 아니라 `flow_path` 결과
  모델의 필수 필드다. §3의 complete·partial 예제가 이 규칙을 직접 보여준다.
- 그 외 Preview 요소는 모두 위 결과 필드로 표현되며 신규 UI 필드는 필요 없다.

## 9. 구현 시 필요한 계약 확장 (승인 후 적용, 이 문서로는 미적용)

- `AnalysisType`에 `FLOW_PATH` 추가, `FlowPathQueryKind`(3종),
  `TracePathInputs`/`TraceRemergeInputs`/`AggregateOriginsInputs`,
  `FlowPathAnalysisRequest`(discriminated), 결과 variant를 추가.
- `FixtureRequirementId` 정규식과 정적 `analysis-result.schema.json`의
  `fixture_requirement_ids` 패턴에 **`FLOW` 접두**를 추가한다. 현재
  `^REQ-(DEX|AUTH|FREEZE|BASIC|TOKEN|NFT721|NFT1155|PROXY)-…$`에는 `FLOW`가
  없어 `REQ-FLOW-…` 결과가 검증에서 막힌다(TASK-013의 NFT721/PROXY 추가와
  동일 절차).
- `check_analysis_schema.py`에 `flow_path` family probe(교차 조합 거부)와
  0.1 하위호환 probe를 추가한다.
- `operations-contract.schema.json`의 `AnalysisType` enum에 `flow_path` 동기화.
- `scope_status`가 필수 결과 필드가 되었으므로 세 fixture `expected.json`의
  `graph.edges[]`·`excluded_edges[]`에 적용 값을 추가하고,
  `task_014_independent_verifier.py`의 raw-first recompute와
  `_expected_projection`도 같은 값을 산출·대조하도록 갱신한다. 이후 기존
  pinned `calculated_fact_sha256` 3개를 재계산하고, analyzer 결과와 독립
  Verifier hash가 다시 일치함을 Verification Receipt에 기록한다.
- **새 공개 `ErrorCode`는 추가하지 않는다**(§5).

## 10. 남은 승인 Gate (이 문서 이후)

- [ ] 사용자가 이 `flow_path` 대안 B 확정안을 검토·승인
- [ ] [TASK-014 계약 제안 §11](./15_TASK_014_PATH_CONTRACT_PROPOSAL.md#11-구현-전-gate)의
  `flow_path 대안 B 정식 승인` 체크
- [ ] Backlog TASK-014 Context Receipt `PASS`
- [ ] 사용자 analyzer 구현 승인
- [ ] 그 후 제품 analyzer 구현 + 독립 Verification Receipt(canonical hash 대조)
- [ ] §7 단일-trace 하드 게이트 충족 시 `confirmed`·Benchmark 승격 별도 판단

## 11. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약 제안](./15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - graph·ledger·상태 계약(대안 B 제안 원본)
- **Technical_Specs**: [Analysis I/O Schema](./05_ANALYSIS_IO_SCHEMA.md) - 공통 envelope·버전 경계
- **UI_Screens**: [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - 승인된 화면 필드
- **QA_Validation**: [TASK-014 후보 보고서](../05_QA_Validation/40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 공개 사례·raw 정답
- **QA_Validation**: [TASK-014 replay·oracle 보고서](../05_QA_Validation/41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) - 단일 trace disclosure(§3)
- **QA_Validation**: [TASK-014 독립 Verifier 보고서](../05_QA_Validation/42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) - raw-first 재계산
- **Logic_Progress**: [Backlog TASK-014](../04_Logic_Progress/00_BACKLOG.md) - Context Receipt·구현 승인
