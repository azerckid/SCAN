# TASK-015 `intel_context` Analysis I/O 계약 (대안 B 확정안)
> Created: 2026-07-30 05:20
> Last Updated: 2026-07-30 05:20
> Status: Contract Draft · User Approval Pending · Runtime Not Implemented

## 0. 문서 위치

[TASK-015 Intelligence 계약 제안](./17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md)은
source role·claim·conflict·윤리 경계를 제안했다. 이 문서는 대안 B
`analysis_type: intel_context`를 request/result/error 단위로 확정하기 위한
docs-only 검토안이다.

이 문서만으로 공개 enum·Pydantic·JSON Schema·CLI를 변경하지 않는다.
사용자 계약 승인, Context Receipt `PASS`, 별도 analyzer 구현 승인이 모두
기록된 뒤에만 코드로 적용한다.

## 1. 대안 B 요지

- Analysis I/O `0.2`에 `intel_context`를 격리된 신규 variant로 추가한다.
- 기존 `0.1`, `evm_core`, `evm_special`, `flow_path` 계약은 바꾸지 않는다.
- `query_kind`는 다음 5종이다.
  - `collect_label_claims`
  - `check_sanctions_exposure`
  - `resolve_identity_clues`
  - `find_common_funder`
  - `score_actor_relations`
- Result 공통 envelope를 재사용하고 `results[].value`만 query별 strict
  object로 구분한다.
- 새 공개 오류 코드를 만들지 않는다. 기존 11개 `ErrorCode`와
  query별 `stage`를 사용한다.
- AI Planner 출력은 `heuristic_candidate`일 뿐 source/evidence가 아니다.

## 2. Request envelope

```json
{
  "$schema": "../05_QA_Validation/schemas/analysis-request.schema.json",
  "schema_version": "0.2",
  "analysis_id": "AN-FX-OSINT-LABEL-CONFLICT-001",
  "analysis_type": "intel_context",
  "query_kind": "collect_label_claims",
  "chain_id": 1,
  "fixture_id": "FX-OSINT-LABEL-CONFLICT-001",
  "requested_at": "2026-07-30T00:00:00+00:00",
  "inputs": {
    "subject_addresses": [
      "0xc3877028655ebe90b9447dd33de391c955ead267"
    ],
    "source_artifact_refs": [
      "artifact://sha256/15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475",
      "artifact://sha256/84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32",
      "artifact://sha256/762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b"
    ],
    "observation_block": 25640270,
    "max_sources": 3
  },
  "source_policy": {
    "rule_status": "allowed",
    "allowed_source_ids": [
      "DS-LABEL-PUBLIC",
      "DS-OSINT-WEB",
      "DS-ENS"
    ],
    "source_order": [
      "DS-LABEL-PUBLIC",
      "DS-OSINT-WEB",
      "DS-ENS"
    ],
    "allow_fallback": false,
    "offline_mode": true
  }
}
```

공통 불변조건:

- `analysis_type == intel_context`이면 `schema_version == 0.2`다.
- `query_kind`와 `inputs` variant는 Pydantic discriminator와 JSON Schema
  `if/then`으로 이중 고정한다.
- 주소는 소문자 normalized `0x` 20-byte 형식이다.
- artifact URI는 content-addressed `artifact://sha256/<64hex>`만 허용한다.
- `offline_mode: true`면 live adapter 호출은 0회다.
- `rule_status != allowed`이면 live source를 호출하기 전에
  `rule_restricted`로 중단한다.

## 3. Query별 inputs

| query_kind | inputs 모델 | 필수 범위 |
|:---|:---|:---|
| `collect_label_claims` | `LabelClaimsInputs` | `subject_addresses`, `source_artifact_refs`, `observation_block`, `max_sources` |
| `check_sanctions_exposure` | `SanctionsExposureInputs` | `subject_addresses`, `official_action_refs`, `current_list_snapshot_ref`, `max_hops: 0..1` |
| `resolve_identity_clues` | `IdentityCluesInputs` | `subject_addresses`, `names`, `observation_block`, `provider_replay_ref` |
| `find_common_funder` | `CommonFunderInputs` | `subject_addresses`, `block_range`, `source_fixture_ref`, completeness requirements |
| `score_actor_relations` | `ActorRelationsInputs` | `subject_addresses`, `hub_address`, `source_fixture_refs`, `component_weights` |

`find_common_funder`의 completeness requirements:

```json
{
  "require_initial_inflow_complete": true,
  "require_service_exclusion": true,
  "excluded_service_roles": [
    "cex_hot_wallet",
    "paymaster",
    "faucet",
    "bridge",
    "public_contract"
  ]
}
```

두 필수 조건을 증명하지 못하면 `complete`가 아니라 `partial`이다.

## 4. 공통 source·claim 모델

### 4.1 Source record

```json
{
  "source_record_id": "SRC-INTEL-001",
  "source_id": "DS-ENS",
  "source_role": "onchain_registry",
  "publisher": "ENS",
  "locator": "artifact://sha256/762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b",
  "retrieved_at": "2026-07-29T19:21:26+00:00",
  "content_sha256": "762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b",
  "address_explicit": true,
  "terms_mode": "artifact_only"
}
```

허용 `source_role`:

- `official_record`
- `first_party`
- `provider_label`
- `public_report`
- `onchain_registry`
- `heuristic`

### 4.2 Claim

```json
{
  "claim_id": "CLM-INTEL-001",
  "subject_address": "0xc3877028655ebe90b9447dd33de391c955ead267",
  "claim_type": "service_category",
  "claim_value": "Mixer",
  "assertion_class": "source_assertion",
  "source_refs": ["SRC-INTEL-001"],
  "evidence_refs": ["EV-INTEL-001"],
  "valid_from": null,
  "valid_to": null,
  "conflict_group_id": "CG-INTEL-001",
  "disposition": "accepted_as_source_claim"
}
```

`assertion_class`는 `source_assertion`, `onchain_observation`,
`heuristic_candidate`, `rejected`, `not_assessed` 중 하나다.
`heuristic_candidate`는 `confirmed_fact`로 승격할 수 없다.

## 5. Query별 result value

### 5.1 `collect_label_claims`

```json
{
  "subject_address": "0xc3877028655ebe90b9447dd33de391c955ead267",
  "assertions": [
    {
      "source_role": "provider_label",
      "claim_value": ["Mixer", "Sanctioned"],
      "truth_status": "source_assertion_only"
    },
    {
      "source_role": "first_party",
      "claim_value": "team4_vesting_contract",
      "truth_status": "role_assertion"
    },
    {
      "source_role": "onchain_registry",
      "claim_value": "team4.vesting.contract.tornadocash.eth",
      "block_number": 25640270,
      "truth_status": "confirmed_observation"
    }
  ],
  "conflict": {
    "kind": "category_role_conflict",
    "auto_merge": false,
    "ownership_assessment": "not_assessed",
    "criminality_assessment": "not_assessed"
  }
}
```

### 5.2 `check_sanctions_exposure`

```json
{
  "subject_address": "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc",
  "direct_matches": [
    {
      "date": "2022-08-08",
      "action": "designation",
      "address_explicit": true,
      "historical": true
    },
    {
      "date": "2025-03-21",
      "action": "removal",
      "address_explicit": true,
      "historical": true
    }
  ],
  "indirect_matches": [],
  "current_status": "not_assessed",
  "criminality_assessment": "not_assessed"
}
```

### 5.3 `resolve_identity_clues`

```json
{
  "block_number": 25640270,
  "forward": {
    "name": "nick.eth",
    "address": "0xb8c2c29ee19d8307cb7255e1cd9cbde883a267d5"
  },
  "reverse": {
    "address": "0xb8c2c29ee19d8307cb7255e1cd9cbde883a267d5",
    "name": "nick.eth"
  },
  "forward_reverse_match": true,
  "ownership_assessment": "not_assessed"
}
```

### 5.4 `find_common_funder` partial

```json
{
  "seed_address": "0xb66cd966670d962c227b3eaba30a872dbfb995db",
  "relation_count": 4,
  "common_funder_assessment": "candidate",
  "ownership_assessment": "not_assessed",
  "coordination_assessment": "not_assessed",
  "initial_inflow_complete": false,
  "service_exclusion_complete": false,
  "coverage_gaps": [
    "bounded_prehistory_unavailable",
    "service_exclusion_unavailable"
  ]
}
```

이 fixture는 두 completeness 필드가 `false`이므로 status가 반드시
`partial`이어야 한다.

### 5.5 `score_actor_relations`

```json
{
  "hub": {
    "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "role": "public_erc20_token_contract",
    "symbol": "USDC"
  },
  "relation_count": 2,
  "hub_excluded_from_actor_link": true,
  "ownership_assessment": "not_assessed",
  "coordination_assessment": "not_assessed",
  "score": {
    "status": "not_assessed",
    "components": []
  }
}
```

## 6. Complete·Partial·Failed

| 상태 | 계약 |
|:---|:---|
| `complete` | 승인된 bounded scope 전부 재현, 모든 결과에 evidence/source refs, conflict·stale·withdrawn 보존 |
| `partial` | 확인 사실 유지, `coverage_gaps`와 구조화 오류 포함, “없음”으로 해석 금지 |
| `failed` | `results: []`, 오류 1개 이상, 손상된 provenance로 사실 생성 금지 |

다음은 complete를 금지한다.

- source budget·rate limit·Terms 제한으로 일부 source만 조회
- fixed block/provider replay 중 일부 부재
- sanctions action 한쪽 또는 current list version 부재
- common-funder initial inflow/service exclusion 미완료
- actor hub role·source fixture binding 미확정

## 7. 오류 매핑

| 상황 | ErrorCode | stage |
|:---|:---|:---|
| query/inputs 결합·주소 오류 | `invalid_input` | `intel_input` |
| source hash·subject·version 불일치 | `reconciliation_failed` | `source_reconciliation` |
| allowed source/artifact 부재 | `source_unavailable` | `source_collection` |
| provider rate limit | `rate_limited` | `source_transport` |
| ENS fixed-block state 부재 | `archive_required` | `identity_state` |
| source decode 실패 | `decode_failed` | `source_decode` |
| 일부 source·prehistory·exclusion 미완료 | `evidence_incomplete` | `intel_coverage` |
| Rules가 live source를 금지 | `rule_restricted` | `source_policy` |
| 공개 Schema 위반 | `schema_invalid` | `contract_validation` |

새 `label_*`, `sanctions_*`, `actor_*` 공개 오류 코드는 추가하지 않는다.

## 8. 정렬·결정성

- sources: `(source_role, publisher, source_record_id)`
- claims: `(subject_address, claim_type, valid_from|null, claim_id)`
- conflicts: `(subject_address, conflict_group_id)`
- relations: `(subject_address, source_fixture_id, relation)`
- score components: `(component_type, counterpart_address, evidence_id)`

Canonical hash는 위 정렬 후 JSON
`sort_keys=true`, separators `(",", ":")`, ASCII encoding으로 계산한다.

## 9. Fixture·승격 경계

| Fixture | 현재 상태 | 계약 결과 |
|:---|:---:|:---|
| `FX-OSINT-LABEL-CONFLICT-001` | verifying | complete 가능 |
| `FX-OSINT-SANCTIONS-HISTORY-001` | verifying | complete 가능, current/criminality `not_assessed` |
| `FX-OSINT-ENS-CONFLICT-001` | verifying | complete 가능, ownership `not_assessed` |
| `FX-ACTOR-COMMON-FUNDER-001` | candidate | partial만 가능 |
| `FX-ACTOR-RELATION-HUB-001` | verifying | complete 가능, ownership/coordination `not_assessed` |

제품 analyzer 구현 전에는 네 verifying fixture도 confirmed가 아니다.
Benchmark는 11을 유지한다.

## 10. 구현 시 확장

- `AnalysisType.INTEL_CONTEXT = "intel_context"`
- query별 strict request inputs 5개
- query별 strict result value 5개
- `FixtureRequirementId`에 `REQ-INTEL-` 접두 허용
- static request/result Schema에 `intel_context` conditional variant
- Schema 의미 probe에 query family binding·cross-family rejection 추가
- CLI·Operations dispatcher에 explicit `IntelContextAnalysisRequest` guard 추가
- fixture analyzer hash ↔ 독립 Verifier hash 검증 Gate 추가

## 11. 승인 Gate

- [ ] 이 계약의 대안 B·필드·오류 매핑 사용자 승인
- [x] Preview 사용자 승인
- [x] negative oracle 30개·두 번 결정성
- [x] 네 fixture independent Verifier·provenance hardening
- [ ] common-funder partial 경계 승인
- [ ] Context Receipt `PASS`
- [ ] 사용자 analyzer 구현 명시 승인

## 12. Related Documents

- [TASK-015 Intelligence 제안](./17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md)
- [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md)
- [TASK-015 Fixture·Contract Gate](../05_QA_Validation/45_TASK_015_FIXTURE_CONTRACT_GATE.md)
- [Independent Verifier 보고서](../05_QA_Validation/51_TASK_015_INDEPENDENT_VERIFIER_REPORT.md)
- [Provenance Hardening Receipt](../05_QA_Validation/52_TASK_015_PROVENANCE_HARDENING_RECEIPT.md)
- [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md)
