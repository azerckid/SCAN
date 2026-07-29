# TASK-013 NFT·Proxy 분석 계약 제안
> Created: 2026-07-29
> Last Updated: 2026-07-29 15:49
> Status: Candidate Replay, Negative Oracle, and Verifier Gates Passed · Implementation Not Approved

## 1. 목적

이 문서는 `EVM-NFT-001`과 `EVM-PROXY-001`을 자동화하기 전에 필요한
fixture 선정 기준, 분석 입력·결과, partial/failed 경계와 증거 계약을
고정한다. 실제 공개 사례, Analysis I/O Schema 변경, Python decoder와
Benchmark 승격은 이 문서의 완료 범위가 아니다.

TASK-012가 제공하는 normalized EVM log/state evidence를 재사용하되,
NFT 표준과 EIP-1967의 의미 해석은 별도 전문 decoder가 담당한다.

## 2. 현재 기준선과 승인 경계

| 항목 | 현재 상태 | 이 문서의 결정 |
|:---|:---|:---|
| TASK-012 EVM Core | Done · Analysis I/O 0.2 | raw log/state 입력 재사용 |
| EVM-NFT-001 | Assisted | fixture·계약 후보만 정의 |
| EVM-PROXY-001 | Assisted | fixture·계약 후보만 정의 |
| NFT·Proxy fixture | 공개 사례 3개 · replay·negative·Verifier Gate 통과 · `candidate` | raw SHA·exact scope·16 oracle·7 requirement 재계산 통과, 승격 판단 유지 |
| Analysis I/O | 0.2 적용, 0.1 호환 | 변경하지 않음 |
| Python runtime | NFT·Proxy analyzer 없음 | 구현하지 않음 |
| UI | 공통 CLI Preview 존재 | TASK-013 전용 Preview는 별도 승인 |

다음 항목이 모두 승인되기 전에는 TASK-013을 `In Progress`로 바꾸지 않는다.

1. 공개 사례와 reference answer가 채워진 fixture를 `confirmed`로 승격
2. 아래 Analysis I/O 대안 중 하나를 정식 선택
3. complete·partial·failed UI Preview 확인
4. Context Receipt `PASS`
5. 사용자 구현 승인

## 3. 표준 근거와 해석 경계

### 3.1 ERC-721

- `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)`
- `Approval(address indexed owner, address indexed approved, uint256 indexed tokenId)`
- `ApprovalForAll(address indexed owner, address indexed operator, bool approved)`
- `tokenId`는 수량이 아니다. 이동 한 건의 amount는 의미상 `1`로만
  정규화하고 raw event에는 존재하지 않는 amount를 원본 값처럼 만들지 않는다.
- zero address의 `from`/`to`는 각각 mint/burn 사실로 표시할 수 있지만,
  자산의 법적 소유권이나 거래 의도는 판정하지 않는다.

### 3.2 ERC-1155

- `TransferSingle(operator, from, to, id, value)`
- `TransferBatch(operator, from, to, ids[], values[])`
- `ApprovalForAll(owner, operator, approved)`
- Batch는 `ids`와 `values`의 길이·순서를 exact로 보존한다. 길이가 다르거나
  ABI tail이 잘리면 일부 항목을 추측하지 않고 `failed`로 처리한다.
- zero-value transfer도 표준상 event일 수 있으므로 자동 제거하지 않는다.

### 3.3 EIP-1967

| 의미 | Slot | 대응 event |
|:---|:---|:---|
| implementation | `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | `Upgraded(address)` |
| beacon | `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` | `BeaconUpgraded(address)` |
| admin | `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | `AdminChanged(address,address)` |

- implementation slot이 비어 있을 때만 beacon 경로를 고려한다.
- beacon 경로는 beacon address와 해당 block의 `implementation()` 결과를
  별도 증거로 보존한다.
- event는 변경 후보를 제공하고, historical slot/state가 해당 block의
  실제 값을 입증한다. 둘이 충돌하면 조용히 하나를 선택하지 않는다.
- EIP-1967에 맞지 않는 비표준 proxy를 억지로 해석하지 않는다.

공식 근거:

- [ERC-721](https://eips.ethereum.org/EIPS/eip-721)
- [ERC-1155](https://eips.ethereum.org/EIPS/eip-1155)
- [ERC-1967](https://eips.ethereum.org/EIPS/eip-1967)

## 4. Fixture 후보 계약

| Fixture ID | 문제 | 반드시 포함할 공개 사실 | 현재 상태 |
|:---|:---|:---|:---|
| [`FX-EVM-NFT-721-001`](../05_QA_Validation/fixtures/FX-EVM-NFT-721-001/README.md) | EVM-NFT-001 | BAYC ApprovalForAll·Approval reset·Transfer와 token `9110` | candidate |
| [`FX-EVM-NFT-1155-001`](../05_QA_Validation/fixtures/FX-EVM-NFT-1155-001/README.md) | EVM-NFT-001 | Rarible TransferSingle·TransferBatch·ApprovalForAll과 ids/values exact 배열 | candidate |
| [`FX-EVM-PROXY-001`](../05_QA_Validation/fixtures/FX-EVM-PROXY-001/README.md) | EVM-PROXY-001 | Aave V3 Pool EIP-1967 slot before/after·Upgraded event·admin zero | candidate |

`candidate`는 공개 주소·TX·block과 expected/evidence 골격, 두 논리
공급자의 raw SHA·receipt/log/storage replay가 일치했다는 뜻이다.
범위 완전성은 명시한 selected transaction·exact block window 또는
selected upgrade·adjacent state에만 적용한다. negative oracle 16개와
독립 Verifier 두 번의 재계산은 통과했다. fixture 승격 판단과 UI·계약
승인이 남아 있으므로 `verifying`이나 `confirmed`로
부르지 않는다.

### 4.1 공통 승격 Gate

- [x] 주소·TX·block 범위를 공개 자료에서 선정
- [x] 두 논리 RPC 공급자의 receipt 또는 historical storage decoded 값 일치
- [x] `external_rpc`와 저장 raw replay에서 같은 normalized evidence 생성
- [x] raw SHA-256, method·params·block tag, retrieved_at과 provider role 기록
- [x] replay integrity checker가 raw topic/data/storage에서 expected 핵심 값을 재계산
- [x] 같은 signature의 무관 log, malformed ABI, 범위 누락 반례 포함
- [x] complete·partial·failed가 두 번 결정적으로 재현
- [x] fixture의 requirement→evidence→source 참조 무결성 통과
- [x] 독립 Verifier가 필수 raw facts·13개 evidence 값·7개 requirement를
  두 번 다시 계산
- [x] fixture Schema 통과
- [ ] 사용자 UI Gate 통과

## 5. Analysis I/O 제안

### 5.1 대안

| 대안 | 장점 | 위험 |
|:---|:---|:---|
| A. `evm_core`에 query 2종 추가 | routing·입력 재사용이 단순 | 범용 Core와 전문 decoder의 책임 혼합, 0.2 변경 폭 확대 |
| B. `evm_special` type 신설 | TASK-012 0.2를 보존하고 전문 해석 격리 | 새 variant·dispatcher·UI routing 필요 |

**제안은 B**다. 정식 결정은 fixture와 UI를 확인한 후 내린다. 승인 전에는
공개 enum·Schema·runtime을 변경하지 않는다.

### 5.2 요청 후보

공통:

- `schema_version`: 다음 계약 버전 후보
- `analysis_type`: `evm_special` 후보
- `chain_scope`: `evm`
- `input_mode`: `external_rpc | contest_rpc | provided_artifact`
- `subject_address`, `block_range`, `source_policy`

`nft_activity`:

- `token_contract`
- `standard_hint`: `erc721 | erc1155 | auto`
- `include_approvals`

`proxy_history`:

- `proxy_address`
- `pattern_hint`: `eip1967 | auto`
- `include_admin`, `include_beacon`

### 5.3 결과 후보

`nft_activity`:

- `standard`, `movements[]`, `approvals[]`
- movement: `tx_hash`, `block_number`, `log_index`, `from`, `to`,
  `token_id_raw`, `amount_raw`, `batch_index`, `event_kind`
- ERC-721의 `amount_raw`는 정규화 값임을 표시하고 raw event field로
  오인되지 않게 `amount_origin: normalized_unit`을 함께 둔다.

`proxy_history`:

- `proxy_address`, `pattern`, `current_implementation`
- `changes[]`: block·TX·event·slot before/after·implementation/admin/beacon
- `conflicts[]`: event와 state가 일치하지 않거나 필요한 state가 없는 경우

모든 결과는 기존 Analysis I/O와 같이 evidence/source refs, warnings,
run 정보를 가진다.

## 6. 상태와 오류 계약

| 상태 | NFT | Proxy |
|:---|:---|:---|
| complete | 요청 범위가 완전하고 모든 event가 표준별로 exact decode | 요청 범위의 event·historical slot이 정합하고 구현체 이력이 완전 |
| partial | range/log page 또는 선택적 approval 누락, 표준은 입증 가능 | archive/beacon call 일부 누락, 확인된 변경은 보존 |
| failed | 필수 topic/data malformed, 표준 판별 불가, Batch 배열 불일치 | proxy 주소·slot 값 malformed, EIP-1967 근거 없음 |

오류 후보:

- `nft_standard_ambiguous`
- `nft_event_malformed`
- `nft_batch_length_mismatch`
- `proxy_pattern_unsupported`
- `proxy_state_unavailable`
- `proxy_event_state_conflict`

partial은 확인된 사실을 버리지 않는다. failed는 `data: null`과 구조화 오류를
반환한다. 어떤 상태도 범죄·악성 upgrade·소유권 분쟁을 자동 판정하지 않는다.

## 7. 반례와 결정성

### 7.1 NFT

- ERC-20 `Transfer`와 ERC-721 `Transfer` signature/field 구조 혼동
- 동일 signature지만 token contract가 다른 log
- 범위 시작 직전 승인 또는 범위 종료 직후 이동
- ERC-1155 Batch의 ids/values 길이 불일치
- mint/burn zero address와 일반 이동 혼동
- 같은 block의 복수 log에서 log index 순서 누락

### 7.2 Proxy

- implementation slot과 beacon slot을 동시에 구현체로 합산
- `Upgraded` event는 있으나 지정 block state가 누락
- event 구현체와 slot 구현체 불일치
- admin address를 implementation으로 오해
- 최신 slot 값을 과거 block의 값으로 사용
- 비표준 proxy를 EIP-1967로 단정

정렬 키는 `(block_number, transaction_index, log_index, batch_index)`이며,
storage snapshot은 명시 block tag와 함께 비교한다.

## 8. UI 영향

공통 CLI Preview를 그대로 복사하지 않는다. 구현 승인 전 최소 Preview에서
다음을 확인한다.

- NFT: 표준 badge, tokenId/amount 출처, Batch 펼침, approval 분리
- Proxy: implementation/admin/beacon timeline, event/state 충돌
- complete·partial·failed와 missing source를 같은 화면에서 구분
- raw evidence와 다음 조치가 정답 요약보다 뒤로 숨지 않음
- 소유권·악성 여부가 `not_assessed`임을 명시

## 9. 365 평가 기준과 윤리

| 기준 | 이 설계의 대응 |
|:---|:---|
| Functionality | 두 예상문제의 raw decode·state history를 결정적으로 복원 |
| Potential Impact | 반복되는 NFT/Proxy 조사 시간을 줄이고 증거 재현성을 높임 |
| Novelty | AI 설명이 아니라 표준별 raw 증거와 독립 Verifier를 중심으로 함 |
| UX | Batch·timeline·partial을 조사자가 빠르게 검토할 수 있게 설계 |
| Open-source | EIP 원문을 근거로 하고 외부 코드 복제·미확인 ABI 의존을 피함 |
| Business Plan | 대회 단계에서는 N/A; 범용 상용 포렌식 제품을 주장하지 않음 |

공개 온체인 자료만 사용하고 비밀키·서명·mutation을 요구하지 않는다.
주소의 실제 소유자, 범죄 의도, 악성 upgrade는 별도 공식 근거 없이는
`not_assessed`다.

## 10. 다음 Gate

1. replay·negative oracle·Verifier 근거로 fixture 승격을 별도 판단한다.
2. Analysis I/O 대안과 전용 Preview를 사용자에게 제시한다.
3. Context Receipt와 별도 구현 승인을 받은 뒤 Python decoder를 시작한다.

## 11. Related Documents

- [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md)
- [Analysis I/O Schema](./05_ANALYSIS_IO_SCHEMA.md)
- [Backlog TASK-013](../04_Logic_Progress/00_BACKLOG.md)
- [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md)
- [TASK-013 Fixture 후보 보고서](../05_QA_Validation/32_TASK_013_FIXTURE_CANDIDATE_REPORT.md)
- [TASK-013 Negative Oracle 보고서](../05_QA_Validation/33_TASK_013_NEGATIVE_ORACLE_REPORT.md)
- [TASK-013 독립 Verifier 보고서](../05_QA_Validation/34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md)
- [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md)
