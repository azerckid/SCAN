# TASK-013 NFT·Proxy Analyzer P1 정정 Receipt
> Created: 2026-07-29 21:40
> Last Updated: 2026-07-29 21:40
> Status: P1 5건·P2 2건 수정 완료 · 변형 회귀 테스트 추가 · Fixture `검증 중` 유지 · Benchmark 7 유지 · PR 병합 보류

## 1. 목적

[Analyzer 검증 Receipt](./36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md)가
canonical hash 일치를 근거로 세 fixture를 `확정`으로 승격하고 Benchmark
automated를 7→9로 올린 뒤, PR #66 리뷰에서 **hash 일치만으로는 잡히지
않는 P1 결함 5건**이 발견됐다. 이 문서는 그 결함, 적용한 수정, 추가한
회귀 테스트, 그리고 승격을 되돌린 근거를 기록한다.

## 2. 리뷰가 발견한 결함과 이유

hash 일치 검증은 "analyzer가 세 fixture에 대해 결정적으로 같은 값을
낸다"만 증명하며, 그 값이 **요청과 실제로 결합됐는지**는 증명하지
않는다. 세 fixture의 raw 데이터가 우연히 내부적으로 일관돼 있어 아래
결함이 fixture 대조에서는 드러나지 않았다.

| # | 결함 | 실패 시나리오 |
|:---:|:---|:---|
| P1-1 | `subject_address`가 replay 내용과 결합되지 않음 | 요청의 `subject_address`를 무관한 주소로 바꿔도 analyzer가 기존 결과를 그대로 `complete`로 반환 |
| P1-2 | `proxy_address`가 replay 내용과 결합되지 않음 | 요청의 `proxy_address`를 무관한 주소로 바꿔도 기존 Upgraded 이력을 `complete`로 반환 |
| P1-3 | receipt·범위·historical state 정합을 확인하지 않음 | NFT 로그의 `transaction_hash`를 receipts에 없는 값으로 바꿔도 `complete`; Proxy storage snapshot의 block을 event block과 다르게 바꿔도 `complete` |
| P1-4 | 공개 JSON Schema와 Pydantic runtime의 교차 조합 불일치 | `analysis_type=evm_core`에 `query_kind=nft_activity`를 조합하면 공개 Schema는 허용하지만 Pydantic은 거부 — Schema probe가 이 조합을 검사하지 않아 놓침 |
| P1-5 | 범용 분석기가 fixture 모양에 고정 | ERC-721 Transfer가 2건이면 정상 범위여도 실패, ERC-1155는 Single·Batch가 모두 있어야 `complete`, approval 두 종류가 모두 없으면 범위가 완전해도 `partial` — 세 fixture 전용 계산에 가까웠음 |
| P2-1 | Beacon 경로가 계약만 있고 구현되지 않음 | `include_beacon=true`를 받지만 값 검증 없이 `applicable: true`만 반환 |
| P2-2 | 두 provider 중 첫 번째만 provenance에 남음 | replay에 provider 2개가 있어도 결과 evidence의 `source_record_ref`가 항상 첫 provider만 가리킴 |

## 3. 적용한 수정

- **subject/proxy 결합**: `_erc721`/`_erc1155`가 `subject_address`와
  실제 topic(`from`/`to`/owner)이 일치하는 로그만 채택하고, 없으면
  `source_unavailable`로 `failed`. `_proxy_history`가 `Upgraded` 로그의
  `address`를 `proxy_address`와 비교해 걸러내고, 없으면 `failed`.
- **ERC-1155 주소별 요청 분리**: fixture의 Single/Approval과 Batch는
  대상 주소가 다르므로 각각 `analysis-request.json`과
  `analysis-request-batch.json`으로 실행한다. 제품 결과는 한 요청의
  subject에 결합된 사실만 반환하고, 독립 검증 Gate에서만 두 결과를
  합쳐 fixture 전체 고정 hash와 비교한다.
- **receipt·block 정합**: `_require_unique_receipts`/
  `_require_matching_receipt`를 추가해 모든 NFT 로그가 replay의 receipts
  중 하나와 `transaction_hash`·`block_number`가 일치하는지 확인하고,
  exact block window 집합도 receipt block 집합과 일치하는지 확인한다.
  불일치하면 `reconciliation_failed`. Proxy는 `Upgraded` 이벤트와
  receipt의 `transaction_hash`·`block_number`를 대조하고, 추가로
  implementation/admin storage snapshot의 block이 event block(및
  block-1)과 정확히 정렬되는지 확인 — 하나라도 어긋나면
  `reconciliation_failed`.
- **Schema 교차 조합**: `analysis-request.schema.json`에
  `analysis_type`↔`query_kind` family binding을 `evm_core`/`evm_special`
  양쪽에 추가하고, `check_analysis_schema.py`에 4개 probe
  (`evm_special_family_probes`)를 추가해 40→44 probe로 확장.
- **범용성 회복**: ERC-721이 subject와 관련된 Transfer를 모두 모아
  `movements[]` 리스트로 반환하도록 바꿔 2건 이상도 정상 처리. ERC-1155의
  `single_case`/`batch_case`는 서로 독립된 사실로 취급해, 한쪽이
  없다고 다른 쪽까지 `partial`로 만들지 않음(스코프 완전성만으로 판단).
- **Beacon**: `ProxyHistoryInputs.include_beacon`을 `Literal[False]`로
  제한해, 검증하지 않은 `applicable: true`를 절대 반환하지 않게 함(beacon
  decode 자체는 이번 버전에서 구현하지 않음. 정직하게 미지원으로 표시).
- **Provenance 분산**: `_evidence()`에 `source_index`를 추가해 두 번째
  provider가 실제로 evidence에 반영되도록 함(토큰 approval, ERC-1155
  batch, proxy admin-after evidence).

## 4. 추가한 회귀 테스트

`tests/unit/test_evm_special_slice.py`에 리뷰의 재현 시나리오를 그대로
반영한 6개 테스트를 추가했다(회귀 방지 목적 — 수정 전 코드였다면 모두
실패했을 케이스).

| 테스트 | 재현 시나리오 | 기대 결과 |
|:---|:---|:---|
| `test_unrelated_subject_address_does_not_return_complete` | `subject_address`를 무관한 주소로 교체 | `failed` / `source_unavailable` |
| `test_erc1155_unrelated_subject_address_does_not_return_complete` | ERC-1155 `subject_address`를 두 사례 모두와 무관한 주소로 교체 | `failed` / `source_unavailable` |
| `test_nft_block_windows_diverging_from_receipts_are_rejected` | NFT exact block windows를 receipt block과 다른 값으로 교체 | `failed` / `reconciliation_failed` |
| `test_unrelated_proxy_address_does_not_return_complete` | `proxy_address`를 무관한 주소로 교체 | `failed` / `source_unavailable` |
| `test_nft_log_transaction_hash_absent_from_receipts_is_rejected` | Transfer 로그의 `transaction_hash`를 receipts에 없는 값으로 교체 | `failed` / `reconciliation_failed` |
| `test_proxy_snapshot_block_diverging_from_event_block_is_rejected` | `implementation_after` snapshot의 block을 event block과 다르게 교체 | `failed` / `reconciliation_failed` |

## 5. 승격 철회 결정

리뷰의 명시적 권고를 그대로 따른다.

> "수정 후에는 fixture를 일단 verifying, Benchmark를 7로 유지한 상태에서
> 위 변형 회귀 테스트까지 통과한 뒤 다시 승격하는 것이 안전합니다.
> 현재는 병합하지 않는 것을 권합니다."

- Fixture 3개(`FX-EVM-NFT-721-001`, `FX-EVM-NFT-1155-001`,
  `FX-EVM-PROXY-001`): `확정` → **`검증 중`으로 되돌림**(input/expected/
  evidence/provider-replay.json·README 12+3개 파일, `01_REFERENCE_FIXTURES.md`,
  `check_task_013_replay_gate.py`, `verify_task_013_independent_verifier.py`).
- Benchmark automated: 9 → **7로 되돌림**(`APPROVED_AUTOMATED_PROBLEM_IDS`에서
  `EVM-NFT-001`·`EVM-PROXY-001` 제거, `expected-problem-v0.1.json`의 두
  case를 `coverage: assisted`로 되돌림, 통합 테스트 하드코딩 카운트 원복).
- Backlog TASK-013, Execution Plan Wave 3, 계약 문서(§14)의 `Done`/확정
  claim을 `In Progress`로 되돌리고 P1 수정·재검토 대기 상태를 명시.
- **PR #66은 병합하지 않는다.** 위 항목이 재검토를 통과한 뒤 별도
  판단한다.

## 6. 검증

- `uv run pytest`: 최신 전체 수치는 이번 보완 커밋의 `scripts/verify.py`
  실행 결과를 기준으로 하며, subject/block-window 회귀 테스트 2개와
  ERC-1155 Batch CLI 통합 테스트를 추가했다.
- `uv run python scripts/verify.py`: 전체 게이트 PASS(fixture 10,
  traceability, security, TASK-012/013 negative oracle, 독립 Verifier,
  analyzer 독립 검증 포함). fixture 상태가 `verifying`으로 되돌아간
  뒤에도 canonical hash 일치는 그대로 유지된다(hash는 `results[0].value`
  계산 결과에만 의존하며 fixture 메타데이터 `status` 필드와 무관).
- `scripts/check_analysis_schema.py`: 44 probes PASS(신규
  `evm_special_family_probes` 4개 포함).

## 7. Related Documents

- **QA_Validation**: [Analyzer 검증 Receipt](./36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md) - 철회된 원본 확정 판정과 canonical hash 근거
- **QA_Validation**: [Fixture 승격 검토](./35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) - `검증 중` 승격 판정(현재 유효)
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 상태 registry
- **Technical_Specs**: [TASK-013 분석 계약](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - 계약·경계 갱신
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-013 진행 상태
