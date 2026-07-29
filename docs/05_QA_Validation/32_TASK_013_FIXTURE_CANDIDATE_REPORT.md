# TASK-013 NFT·Proxy Fixture 후보 보고서
> Created: 2026-07-29
> Last Updated: 2026-07-29 15:17
> Status: Candidate Replay and Negative Oracle Gates Passed · Verifier Pending

## 1. 목적

TASK-013의 코드를 만들기 전에 필요한 ERC-721, ERC-1155, EIP-1967
fixture의 공개 후보와 최소 구성을 기록한다. 세 package는 공개 사례,
두 공급자 재현, capability별 raw SHA와 명시 scope의 filtered log/state
Gate를 통과했다. negative oracle 15개도 두 번 통과했지만 독립 Verifier가
남아 있어 `candidate`이며,
fixture 확정이나 구현 승인을 뜻하지 않는다.

## 2. 후보 구성

| Fixture ID | 문제 | 필수 범위 | 주소·TX | 상태 |
|:---|:---|:---|:---|:---|
| [`FX-EVM-NFT-721-001`](./fixtures/FX-EVM-NFT-721-001/README.md) | EVM-NFT-001 | BAYC ApprovalForAll·Approval reset·Transfer, token `9110` | blocks `25008826`·`25023516` | candidate |
| [`FX-EVM-NFT-1155-001`](./fixtures/FX-EVM-NFT-1155-001/README.md) | EVM-NFT-001 | Rarible Single·Batch·ApprovalForAll, ids/values exact | blocks `23762140`·`24609794` | candidate |
| [`FX-EVM-PROXY-001`](./fixtures/FX-EVM-PROXY-001/README.md) | EVM-PROXY-001 | Aave V3 Pool implementation before/after·Upgraded·admin zero | block `25199939` | candidate |

NFT 한 건만으로 ERC-721과 ERC-1155를 모두 검증했다고 주장하지 않는다.
두 표준은 별도 package와 reference answer가 필요하다.

### 2.1 두 공급자 기본 재현

| Fixture | 재현 입력 | 일치한 값 | 미완료 |
|:---|:---|:---|:---|
| ERC-721 | 두 TX receipt + exact-block filtered logs | contract·block·log index·owner/operator·approved·from/to·tokenId | Verifier |
| ERC-1155 | 두 TX receipt + exact-block filtered logs | contract·block·log index·operator/from/to·ids·amounts | Verifier |
| Proxy | upgrade receipt/log + adjacent `eth_getStorageAt` | Upgraded implementation·implementation slot·admin zero | Verifier |

공급자 endpoint와 credential은 저장하지 않고 `primary`·`verify` 논리 역할만
사용했다. 탐색기 화면은 후보 발견 보조이며 scoring source가 아니다.

### 2.2 재현 도구

기본 실행은 네트워크를 호출하지 않는다.

```bash
uv run python scripts/replay_task_013_candidates.py \
  --fixture FX-EVM-NFT-721-001 \
  --role primary
```

실제 호출은 기존 Rules Gate, `--execute`, 논리 endpoint 환경변수가 모두
필요하다. 허용 method는 `eth_getTransactionReceipt`, `eth_getLogs`,
`eth_getStorageAt`뿐이다. request set 5+5+6을 각 provider에 실행해
총 **32 network calls**, 16 capability 쌍을 비교했다. 첫 ERC-721 primary 실행에서
receipt 한 건이 HTTP 429였고 bounded 재시도에서 5/5 complete가 됐다.

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

현재 candidate package에는 `README.md`, `input.json`, `expected.json`,
`evidence.json`, `raw-replay.json`, `provider-replay.json`을 추가했다.
provider replay는 endpoint가 아니라 논리 provider ID, method·scope,
retrieved_at, capability별 raw SHA-256과 decoded match만 보존한다.

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

## 6. Negative Oracle 결과

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

표준별 5개, 총 15개 oracle을 두 번 동일하게 실행해 모두 통과했다.
expected 값은 제품 analyzer 입력으로 사용하지 않는다. 상세 결과는
[TASK-013 Negative Oracle 보고서](./33_TASK_013_NEGATIVE_ORACLE_REPORT.md)에
고정했다.

## 7. 승격 Gate

- [x] 세 fixture ID와 표준별 책임을 분리했다.
- [x] 선정·reference answer·반례 기준을 문서화했다.
- [x] 공식 EIP 근거와 자동 판정 금지 범위를 고정했다.
- [x] 공개 주소·TX·block을 선정했다.
- [x] candidate package의 README·input·expected·evidence를 작성했다.
- [x] 두 공급자 receipt와 필요한 historical storage의 decoded 값을 대조했다.
- [x] raw replay·SHA-256·provider replay provenance를 작성했다.
- [x] selected TX·exact block window와 selected upgrade·adjacent state 범위를 검증했다.
- [x] replay integrity checker가 raw topic/data/storage에서 expected 핵심 값을 재계산했다.
- [x] negative oracle 15개를 두 번 실행해 결정성을 확인했다.
- [x] candidate package 3개를 포함한 fixture Schema 0.1을 통과했다.
- [ ] Analysis I/O와 UI를 승인했다.
- [ ] Context Receipt가 `PASS`다.
- [ ] 사용자 구현 승인을 기록했다.

따라서 Schema 검증 package 수는 10개로 늘지만, confirmed fixture 7개와
Benchmark 자동화 7문항은 변하지 않는다.

## 8. 위험과 완화

| 위험 | 완화 |
|:---|:---|
| ERC-20/721 event 혼동 | topic 개수·indexed field·contract standard 근거 결합 |
| ERC-1155 Batch 일부만 decode | 전체 ABI decode 실패 시 failed |
| proxy event만 보고 이력 단정 | historical slot/state를 필수 증거로 연결 |
| beacon 경로 누락 | implementation slot empty 조건과 beacon call 분리 |
| 최신 state 오용 | 모든 state에 block tag와 raw word 보존 |
| 악성·소유권 추론 과장 | `not_assessed` 유지, 별도 공식 근거 요구 |

## 9. 365 Rubric 검증

| 기준 | 상태 | 이번 단계의 증거 | 잔여 |
|:---|:---|:---|:---|
| Functionality | Partial | 세 표준의 두 공급자 raw SHA·명시 scope·expected 재계산·negative oracle 통과 | Verifier |
| Potential Impact | Partial | NFT·Proxy 두 예상문제의 구현 입력을 구체화 | Benchmark 승격 전 |
| Novelty | Partial | event와 historical slot을 분리하고 귀속을 판정하지 않음 | analyzer 비교 전 |
| UX | N/A | UI·runtime 변경 없음 | 전용 Preview 승인 |
| Open-source | Partial | 공식 EIP와 공개 온체인 자료만 사용 | 고정 replay provenance |
| Business Plan | N/A | 대회 준비 fixture 단계 | 상용성 주장 안 함 |

공개 온체인 사실을 자체 재현해 요약했으며 제3자 구현 코드를 복제하지
않았다. 주소 소유자·NFT 가치·거래 의도·upgrade의 악성 여부는
`not_assessed`로 유지한다.

## 10. 판정

**공개 candidate replay·명시 scope·raw integrity Gate 통과, fixture 승격 미실행.**

다음 작업은 독립 Verifier가 raw replay에서 필수 값을 다시 계산하는
Gate다. 그 뒤에도 즉시 제품 decoder를 시작하지 않고, fixture 승격·UI·Context
Receipt·사용자 구현 승인을 순서대로 닫는다.

## 11. Related Documents

- [TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md)
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md)
- [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [Backlog TASK-013](../04_Logic_Progress/00_BACKLOG.md)
- [TASK-013 Negative Oracle 보고서](./33_TASK_013_NEGATIVE_ORACLE_REPORT.md)
