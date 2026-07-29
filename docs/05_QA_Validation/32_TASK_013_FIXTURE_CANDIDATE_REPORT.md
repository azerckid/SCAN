# TASK-013 NFT·Proxy Fixture 후보 보고서
> Created: 2026-07-29
> Last Updated: 2026-07-29
> Status: Proposed · Public Cases Not Selected · Implementation Not Approved

## 1. 목적

TASK-013의 코드를 만들기 전에 필요한 ERC-721, ERC-1155, EIP-1967
fixture의 최소 구성을 확정한다. 이 보고서는 fixture package 자체나 공개
사례를 확정하지 않는다.

## 2. 후보 구성

| Fixture ID | 문제 | 필수 범위 | 주소·TX | 상태 |
|:---|:---|:---|:---|:---|
| `FX-EVM-NFT-721-001` | EVM-NFT-001 | Transfer·Approval·ApprovalForAll, tokenId exact | TBD | proposed |
| `FX-EVM-NFT-1155-001` | EVM-NFT-001 | TransferSingle·TransferBatch·ApprovalForAll, ids/values exact | TBD | proposed |
| `FX-EVM-PROXY-001` | EVM-PROXY-001 | EIP-1967 implementation/admin 또는 beacon 변경 이력 | TBD | proposed |

NFT 한 건만으로 ERC-721과 ERC-1155를 모두 검증했다고 주장하지 않는다.
두 표준은 별도 package와 reference answer가 필요하다.

## 3. 선정 조건

### 3.1 ERC-721

- 공개 mainnet TX와 안정된 token contract
- 주체 주소와 block range가 명확
- Transfer 외 승인 event의 의미를 검증할 수 있는 범위
- ERC-20 동일 이름/유사 signature 오분류 반례
- tokenId·from·to·log index를 exact로 재현

### 3.2 ERC-1155

- TransferSingle과 TransferBatch를 모두 검증할 수 있는 공개 범위
- Batch `ids[]`와 `values[]` 순서·길이를 exact로 재현
- ApprovalForAll의 owner/operator/approved 분리
- zero value, mint/burn, 다른 contract log 반례

### 3.3 EIP-1967

- implementation 또는 beacon 경로가 표준 slot으로 입증되는 공개 proxy
- 한 번 이상의 upgrade event와 historical storage before/after
- admin 변경이 없다면 `not_applicable`을 증거로 명시
- 최신 state를 과거 state로 복사하지 않는 archive replay
- event/state conflict 또는 state unavailable 반례

## 4. 패키지 최소 파일

각 후보가 실제 사례로 선정되면 다음 파일을 추가한다.

- `README.md`: 범위·상태·재현·승격 조건
- `input.json`: 주소·block range·표준/pattern hint
- `expected.json`: raw answer·complete/partial/failed 조건
- `evidence.json`: event/state/source role과 requirement 연결
- `raw-replay.json`: normalized evidence 원본과 SHA-256
- `provider-replay.json`: provider별 method·params·retrieved_at·decoded match

endpoint·API key·credential·로컬 절대 경로는 어느 파일에도 넣지 않는다.

## 5. Reference Answer 필드

### 5.1 NFT

- 표준, contract, tx/block/log index
- from, to, operator/owner/approved
- tokenId raw, amount raw, batch index
- event signature와 indexed/data field 위치
- mint/burn/transfer/approval 구분
- evidence/source refs

### 5.2 Proxy

- proxy, implementation/admin/beacon slot
- 명시 block의 raw storage word와 decoded address
- upgrade/admin/beacon event와 TX
- before/after implementation
- event/state conflict와 missing evidence
- evidence/source refs

## 6. Negative Oracle 계획

| Oracle | 기대 판정 |
|:---|:---|
| ERC-20 event를 ERC-721로 입력 | failed 또는 표준 불일치 |
| ERC-1155 Batch 배열 길이 불일치 | failed |
| 다른 token contract의 동일 event | 제외 |
| 범위 밖 NFT event | 제외 |
| NFT log page 누락 | partial |
| 최신 proxy slot을 과거 block에 사용 | failed |
| implementation과 beacon을 동시에 확정 | conflict |
| event는 있으나 historical state 없음 | partial |
| admin slot을 implementation으로 decode | failed |
| 비표준 proxy | unsupported/failed, EIP-1967 단정 금지 |

각 oracle은 두 번 동일하게 실행되고, expected 값을 analyzer 입력으로
사용하지 않아야 한다.

## 7. 승격 Gate

- [x] 세 fixture ID와 표준별 책임을 분리했다.
- [x] 선정·reference answer·반례 기준을 문서화했다.
- [x] 공식 EIP 근거와 자동 판정 금지 범위를 고정했다.
- [ ] 공개 주소·TX·block을 선정했다.
- [ ] package JSON과 raw replay를 작성했다.
- [ ] provider 재현과 archive state를 통과했다.
- [ ] negative oracle을 실행했다.
- [ ] fixture Schema를 통과했다.
- [ ] Analysis I/O와 UI를 승인했다.
- [ ] Context Receipt가 `PASS`다.
- [ ] 사용자 구현 승인을 기록했다.

따라서 현재 fixture 수와 Benchmark 자동화 수는 변하지 않는다.

## 8. 위험과 완화

| 위험 | 완화 |
|:---|:---|
| ERC-20/721 event 혼동 | topic 개수·indexed field·contract standard 근거 결합 |
| ERC-1155 Batch 일부만 decode | 전체 ABI decode 실패 시 failed |
| proxy event만 보고 이력 단정 | historical slot/state를 필수 증거로 연결 |
| beacon 경로 누락 | implementation slot empty 조건과 beacon call 분리 |
| 최신 state 오용 | 모든 state에 block tag와 raw word 보존 |
| 악성·소유권 추론 과장 | `not_assessed` 유지, 별도 공식 근거 요구 |

## 9. 판정

**Fixture·계약 설계 단계 통과, 공개 fixture 선정 단계 미실행.**

다음 작업은 공개 사례 후보 조사다. 사례와 reference answer가 확보된 뒤에도
즉시 코드를 시작하지 않고, fixture 승격·UI·Context Receipt·사용자 구현
승인을 순서대로 닫는다.

## 10. Related Documents

- [TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md)
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md)
- [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [Backlog TASK-013](../04_Logic_Progress/00_BACKLOG.md)
