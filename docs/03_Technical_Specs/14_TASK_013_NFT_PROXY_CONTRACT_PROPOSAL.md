# TASK-013 NFT·Proxy 분석 계약 제안
> Created: 2026-07-29
> Last Updated: 2026-07-29 21:40
> Status: In Progress · `evm_special` 구현 완료, 리뷰에서 발견된 P1 5건 수정 반영 · Fixture `검증 중` 유지 · Benchmark 7 유지(재검토 대기)

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
| NFT·Proxy fixture | 공개 사례 3개 · [승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)로 `검증 중` 유지, `확정` 승격은 재검토 이후로 보류 | raw SHA·exact scope·16 oracle·7 requirement 재계산 통과, analyzer 재검증은 [P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md) 이후 별도 판단 |
| Analysis I/O | 0.2 적용, 0.1 호환 | 변경하지 않음. 신규 `evm_special` 대안 B를 §5에서 확정 |
| Python runtime | NFT·Proxy analyzer 구현 완료 · 리뷰에서 발견된 subject/proxy 결합·receipt 정합 P1 5건 수정 반영, 재검토 대기 | [Analyzer 검증 Receipt](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md)와 [P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md) 참고 |
| UI | [TASK-013 전용 UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)·[Preview](../02_UI_Screens/previews/06_task_013_nft_proxy_preview.html) 작성 | 사용자 확인·승인 완료(2026-07-29 20:19) |

다음 항목이 모두 승인되어 TASK-013을 `In Progress`로 전환했다.

1. ~~공개 사례와 reference answer가 채워진 fixture를 `confirmed`로 승격~~ →
   [승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)로
   `검증 중` 완료, `확정`은 analyzer 구현·독립 검증 후 별도 판단
2. ~~아래 Analysis I/O 대안 중 하나를 정식 선택~~ → **대안 B로 확정**(§5.1)
3. ~~complete·partial·failed UI Preview 확인~~ → 작성·브라우저 검증 완료,
   사용자가 2026-07-29 20:19 승인
4. ~~Context Receipt `PASS`~~ → Backlog에 기록 완료
5. ~~사용자 구현 승인~~ → 완료. 다음 단계는 NFT·Proxy analyzer 구현.

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
| [`FX-EVM-NFT-721-001`](../05_QA_Validation/fixtures/FX-EVM-NFT-721-001/README.md) | EVM-NFT-001 | BAYC ApprovalForAll·Approval reset·Transfer와 token `9110` | 검증 중 |
| [`FX-EVM-NFT-1155-001`](../05_QA_Validation/fixtures/FX-EVM-NFT-1155-001/README.md) | EVM-NFT-001 | Rarible TransferSingle·TransferBatch·ApprovalForAll과 ids/values exact 배열 | 검증 중 |
| [`FX-EVM-PROXY-001`](../05_QA_Validation/fixtures/FX-EVM-PROXY-001/README.md) | EVM-PROXY-001 | Aave V3 Pool EIP-1967 slot before/after·Upgraded event·admin zero | 검증 중 |

세 fixture 모두 공개 주소·TX·block과 expected/evidence 골격, 두 논리
공급자의 raw SHA·receipt/log/storage replay 일치, negative oracle 16개,
독립 Verifier 두 번의 재계산까지 확인해 [승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)로
`검증 중`으로 승격했다. NFT·Proxy analyzer 구현과 canonical hash 일치
검증([Analyzer 검증 Receipt](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md))까지
마쳤으나, 이후 리뷰에서 subject/proxy 결합 누락과 receipt·block 정합
누락 등 P1 5건이 발견되어 `확정` 승격은 보류하고 수정·회귀 테스트를
반영했다([P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)).
범위 완전성은 명시한 selected transaction·exact block window 또는
selected upgrade·adjacent state에만 적용한다.

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
- [x] 승격 검토 통과 · `검증 중`으로 승격
- [x] 사용자 UI Gate 통과
- [x] NFT·Proxy analyzer 구현과 독립 Verification Receipt(canonical hash 일치)
- [ ] 리뷰에서 발견된 P1 5건(subject/proxy 결합, receipt·block 정합,
  Schema 교차 조합, fixture 형태 고정, beacon 미구현) 수정·회귀 테스트
  반영 후 재검토 → `확정` 승격은 재검토 이후로 보류

## 5. Analysis I/O 제안

### 5.1 대안과 결정

| 대안 | 장점 | 위험 |
|:---|:---|:---|
| A. `evm_core`에 query 2종 추가 | routing·입력 재사용이 단순 | 범용 Core와 전문 decoder의 책임 혼합, 0.2 변경 폭 확대 |
| B. `evm_special` type 신설 | TASK-012 0.2를 보존하고 전문 해석 격리 | 새 variant·dispatcher·UI routing 필요 |

**결정: B.** fixture 승격 검토(§4)와 UI Preview(§8, [07_TASK_013_NFT_PROXY_UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md))를
마친 뒤 이 계약 문서 안에서 확정한다. `evm_core`는 범용 TX/state/log/trace
query 4종의 책임을 유지하고, NFT·Proxy 표준 해석은 별도 `evm_special`
type으로 분리해 TASK-012 0.2의 범위를 넓히지 않는다. 이 결정은 설계
확정이며, 공개 enum·Schema·runtime 코드는 사용자 구현 승인 전까지
변경하지 않는다.

### 5.2 요청 후보

공통:

- `schema_version`: 다음 계약 버전 후보
- `analysis_type`: `evm_special` 후보
- `chain_scope`: `evm`
- `input_mode`: `external_rpc | contest_rpc | provided_artifact`
- `subject_address`, `block_range`, `source_policy`

`nft_activity`:

- `token_contract`
- `subject_address`: 반환하는 모든 movement의 `from` 또는 `to`와 결합
- `standard_hint`: `erc721 | erc1155 | auto`
- `include_approvals`
- `block_range`/reviewed replay의 exact block windows는 선택 receipt block
  집합과 일치해야 하며, 서로 다른 대상 주소의 사례는 별도 요청으로 실행

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

1. ~~replay·negative oracle·Verifier 근거로 fixture 승격을 별도 판단한다.~~ →
   [승격 검토](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) 완료, `검증 중`
2. ~~Analysis I/O 대안과 전용 Preview를 사용자에게 제시한다.~~ → 대안 B 확정,
   [UI 문서](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)·[Preview](../02_UI_Screens/previews/06_task_013_nft_proxy_preview.html) 작성 완료
3. ~~사용자가 Preview를 확인하고 승인한다.~~ → 2026-07-29 20:19 승인 완료
4. ~~Context Receipt와 별도 구현 승인을 받는다.~~ → Backlog에 `PASS`·승인
   기록 완료
5. ~~NFT·Proxy analyzer를 구현하고 독립 Verification Receipt를 확보한다.~~ →
   [Analyzer 검증 Receipt](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md)
   완료(canonical hash 일치)
6. **다음: 리뷰에서 발견된 P1 5건을 수정하고
   [P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)의
   변형 회귀 테스트가 통과한 상태로 재검토를 받은 뒤에만 fixture `확정`
   승격과 Benchmark automated 7 → 9 승격을 다시 판단한다. 그 전에는
   PR을 병합하지 않는다.**

TASK-013은 analyzer 구현 자체는 완료했으나, 리뷰가 지적한 correctness
문제를 수정하고 재검증받기 전까지 `In Progress`로 유지한다.

## 11. Related Documents

- [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md)
- [Analysis I/O Schema](./05_ANALYSIS_IO_SCHEMA.md)
- [Backlog TASK-013](../04_Logic_Progress/00_BACKLOG.md)
- [Coverage 확장 QA](../05_QA_Validation/23_EXPECTED_PROBLEM_EXPANSION_QA.md)
- [TASK-013 Fixture 후보 보고서](../05_QA_Validation/32_TASK_013_FIXTURE_CANDIDATE_REPORT.md)
- [TASK-013 Negative Oracle 보고서](../05_QA_Validation/33_TASK_013_NEGATIVE_ORACLE_REPORT.md)
- [TASK-013 독립 Verifier 보고서](../05_QA_Validation/34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md)
- [TASK-013 Fixture 승격 검토 보고서](../05_QA_Validation/35_TASK_013_FIXTURE_PROMOTION_REVIEW.md)
- [TASK-013 Analyzer 검증 Receipt](../05_QA_Validation/36_TASK_013_ANALYZER_VERIFICATION_RECEIPT.md)
- [TASK-013 Analyzer P1 정정 Receipt](../05_QA_Validation/37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)
- [TASK-013 NFT·Proxy UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)
- [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md)
