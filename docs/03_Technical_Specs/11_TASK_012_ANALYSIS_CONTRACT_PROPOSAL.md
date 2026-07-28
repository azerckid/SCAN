# TASK-012 범용 EVM Analysis Contract 제안
> Created: 2026-07-29 04:46
> Last Updated: 2026-07-29 05:12
> Status: Proposed 0.2 Draft · Analysis I/O 0.1 Unchanged · Runtime Not Implemented

## 1. 목적과 판정

TASK-012의 네 `verifying` fixture를 하나의 범용 EVM 분석기가 소비할 수
있도록 request·result·partial/error 계약을 제안한다. 이 문서는 승인된
Analysis I/O 0.1이나 Python runtime을 변경하지 않는다.

**제안: `analysis_type: evm_core` 하나와 네 `query_kind`를 사용한다.**

문제별 Analysis type 네 개를 추가하지 않는 이유는 source·cache·block
pin·evidence·partial 처리가 같기 때문이다. `query_kind`별 입력과 결과는
JSON Schema의 조건부 구조로 분리해 서로의 필드가 섞이지 않게 한다.

## 2. 문제와 Query 매핑

| 문제·Fixture | query_kind | 결정적 입력 | 결정적 결과 |
|:---|:---|:---|:---|
| BASIC-EVM-001 / FX-BASIC-EVM-001 | `object_summary` | 값 목록·고정 block·fee 여부 | 객체 분류·EOA/contract·정확한 fee |
| BASIC-EVM-002 / FX-BASIC-EVM-002 | `historical_balance` | 주소·block number/timestamp·asset | post-state ETH/ERC-20 raw balance |
| EVM-TOKEN-001 / FX-EVM-TOKEN-001 | `first_token_transfer` | 주소·token·start block·정렬 정책 | 첫 성공·양수 outgoing Transfer |
| EVM-TOKEN-002 / FX-EVM-TOKEN-002 | `native_inflow` | 주소·TX·trace/revert 정책 | top-level과 internal native inflow 분리 |

## 3. Request 계약

공통 필드:

| 필드 | 규칙 |
|:---|:---|
| `analysis_id` | 요청·결과가 동일해야 함 |
| `analysis_type` | 제안값 `evm_core` |
| `chain_id` | 현재 Ethereum `1`만 |
| `query_kind` | 위 네 값 중 하나 |
| `inputs` | query별 strict object, 추가 필드 금지 |
| `source_policy` | 기존 0.1의 rule/source/fallback/offline 의미 유지 |

핵심 불변조건:

- historical state는 `block_number`, `block_timestamp`,
  `state_semantics: post_state`를 함께 보존한다.
- token transfer는 성공 transaction·양수·outgoing·
  `block_transaction_log_asc`를 계약으로 고정한다.
- native inflow는 trace를 필수로 요청하고 reverted call을 제외한다.
- source order는 allowed source의 부분집합이다.

## 4. Result 계약

공통 필드:

| 필드 | 규칙 |
|:---|:---|
| `status` | `complete`, `partial`, `failed` |
| `data` | complete/partial은 query별 object, failed는 `null` |
| `errors` | complete는 0개, partial/failed는 1개 이상 |
| `evidence_refs` | complete/partial은 1개 이상 |
| `source_record_refs` | complete/partial은 1개 이상 |

결과의 raw 금액은 JSON number가 아니라 uint256 decimal string으로 둔다.
`first_token_transfer`는 범위가 불완전하면 보이는 후보를 보존하되
`range_complete: false`와 `partial`을 반환한다. `native_inflow`는
top-level value와 internal sum을 절대 합치지 않는다.

조건부 불변조건:

- `historical_balance`의 `erc20` asset은 `token_address`가 필수이며
  `native` asset에는 넣지 않는다.
- `include_transaction_fee: true`인 complete/partial 결과에는
  `fee_paid_wei`가 필수이고, `false`이면 해당 필드를 넣지 않는다.
- `first_token_transfer`의 complete는 `range_complete: true`, partial은
  `false`다.
- `native_inflow`의 complete는 `trace_complete: true`, partial은
  `false`다.

## 5. Partial·Failed 오류 매핑

| query_kind | 대표 partial | 대표 failed | 오류 코드 |
|:---|:---|:---|:---|
| `object_summary` | historical code 일부 부재 | object 조회 전체 실패 | `source_unavailable` |
| `historical_balance` | 일부 asset archive state 부재 | 고정 block state 전체 부재 | `archive_required` |
| `first_token_transfer` | pagination/range 불완전 | transfer log scan 전체 실패 | `evidence_incomplete` / `source_unavailable` |
| `native_inflow` | 보조 trace 불완전 | 필수 trace 전체 부재 | `trace_unavailable` |

negative oracle이 검출한 latest 대체, gas limit fee, 잘못된 token/순서,
실패 call 합산은 `failed` 또는 실행 전 계약 거부다. 구체 stage와 공개
메시지는 구현 Brief에서 고정하며 provider 원문·credential은 포함하지 않는다.

## 6. 버전·Migration 판정

현재 승인 계약은 `schema_version: 0.1`이며 세 Analysis type만 허용한다.
이 제안은 별도 `proposal_version: 0.2-draft` 파일로 격리했다.

구현 승인 시 선택지는 다음 둘이다.

1. Analysis I/O를 `0.2`로 올리고 `evm_core` discriminated variant 추가
2. 0.1 envelope를 유지하면서 payload extension 규칙을 별도 승인

**권장안은 1번**이다. 승인 Schema와 runtime enum이 같은 truth source를
유지하고 unknown type을 0.1에서 계속 거부할 수 있기 때문이다. SQLite
Schema v2는 analysis type 문자열을 저장하므로 DDL migration은 현재
필요하지 않지만, runtime model·CLI dispatcher·operations planner는 함께
변경해야 한다.

## 7. CLI·UI 영향

- 문제 입력에서 `query_kind`에 따라 필수 필드만 표시한다.
- 결과 상단에 고정 block·source·evidence completeness를 표시한다.
- `archive_required`, `trace_unavailable`, `evidence_incomplete`를
  `partial` 이유로 노출한다.
- 독립 verification 전에는 `confirmed`·submission-ready로 보이지 않게 한다.
- 기존 DEX·AUTH·FREEZE CLI 출력은 0.1 경로를 유지한다.

기존 V1 Preview는 변경하지 않는다. 별도
[TASK-012 EVM Core UI](../02_UI_Screens/05_TASK_012_EVM_CORE_UI.md)와
[HTML Preview](../02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html)를
작성했으며, 자동 검증 후 사용자 UI-First 확인을 별도 Gate로 둔다.

## 8. 검증 증거

- proposal Schema Draft 2020-12 자체 검증
- 네 fixture × complete/partial/failed = 12 case
- query별 input/result 조건, status/error 조건
- ERC-20 token address·fee 요청·range/trace completeness 조건
- request/result ID·type·chain·query 일치
- source order 부분집합
- fixture exact raw 값 drift 검사
- extra field·wrong input·status/error·failed null/error·ERC-20·fee·range·trace
  조건을 다루는 14 probes
- 현재 Analysis I/O 0.1 Schema와 runtime enum 미변경 검사

실행:

```bash
uv run python scripts/check_task_012_analysis_contract_proposal.py
```

## 9. 승인 전 잔여

- [ ] 사용자 계약 승인
- [x] TASK-012 전용 HTML Preview 작성·정적 검증
- [ ] CLI Preview의 네 query 입력·complete·partial·failed 사용자 검토
- [ ] Analysis I/O 0.2 정식 Schema·Pydantic 모델 승인
- [ ] credential 회전·독립 trace·live rate/timeout Gate
- [ ] fixture conditional confirmed
- [ ] TASK-012 제품 analyzer 구현 승인

## 10. 365 글로벌 평가 기준

| 기준 | 기여 |
|:---|:---|
| Functionality | 네 문제의 strict request/result/partial 계약 |
| Potential Impact | 후속 EVM·PATH leaf가 공유할 query envelope |
| Novelty | AI 방법 제안과 raw evidence 소비 계약 분리 |
| UX | archive/trace/range 불완전성을 숨기지 않는 상태 |
| Open-source | 공개 Schema·예제·probe, secret 없음 |
| Business Plan | N/A |

## 11. Related Documents

- **Technical_Specs**: [Analysis I/O Schema 0.1](./05_ANALYSIS_IO_SCHEMA.md) - 현재 승인 기준선
- **Technical_Specs**: [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-EVM-CORE
- **Technical_Specs**: [Live Provider Readiness](./10_LIVE_PROVIDER_READINESS.md) - source·Trace Gate
- **UI_Screens**: [TASK-012 EVM Core UI](../02_UI_Screens/05_TASK_012_EVM_CORE_UI.md) - 4 query·3상태 Draft
- **UI_Screens**: [TASK-012 EVM Core Preview](../02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html) - 사용자 확인 대상
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 Context Lock
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - 네 verifying fixture
- **QA_Validation**: [제안 예제](../05_QA_Validation/examples/task-012/README.md) - 12개 contract case
- **QA_Validation**: [Negative Oracle 보고서](../05_QA_Validation/27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 24개 offline 반례
- **QA_Validation**: [TASK-012 UI Preview 보고서](../05_QA_Validation/28_TASK_012_UI_PREVIEW_REPORT.md) - 자동·브라우저·사용자 Gate
