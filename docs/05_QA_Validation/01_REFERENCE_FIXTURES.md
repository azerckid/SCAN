# SCAN 2026 Reference Fixtures
> Created: 2026-07-24 15:49
> Last Updated: 2026-07-29 23:25
> Status: Approved 1.6 · Phase 2 Confirmed Pack · TASK-014 공개 후보 3개 선정

## 1. 문서 목적

이 문서는 예상문제 은행 Draft 2의 대표 문제에 대해, 도구 정확성을 검증할 수
있는 reference fixture를 관리한다. 현재 15개 중 10개는 `확정`, 5개는
후속 Gate가 남은 `후보`다. TASK-013 세 공개 사례는 remediation
재검토와 [최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md)를
통과해 `확정`으로 관리한다.

TASK-014 세 공개 PATH 사례는 Euler 공개 사건의 서로 다른 request scope를
사용해 실제 TX·주소·raw 금액 골격을 고정했지만, 두 공급자 replay·negative
oracle·독립 Verifier 전이므로 `후보`로 유지한다.

입력 문서:

- [SCAN 2026 예상문제 은행 Draft 2](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md)
- [P0·V1 분석 도구 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md)

## 2. Rubric 정렬

| Rubric | 이 문서에서의 적용 |
|:---|:---|
| Functionality | fixture로 수집·디코딩·추적·환산 결과가 재현 가능한지 검증 |
| Potential Impact | 대회 문제 유형을 대표하는 최소 세트로 준비 효율을 높임 |
| Novelty | 확정/추정 분리, 불확실 연결, AUTH/PROXY/FREEZE 등 공백 기능을 포함 |
| UX | 증거 표·출처·허용 오차가 사람이 검수하기 쉽게 기록됨 |
| Open-source | 공개 사건·공개 온체인 데이터·자체 소규모 테스트 데이터를 우선 |
| Business Plan | 해당 없음 (대회 준비 QA). N/A |

## 3. 정보 구분 원칙

| 구분 | 적용 |
|:---|:---|
| 확정 사실 | 온체인에서 재조회 가능한 TX·로그·상태 |
| 과거 근거 | 공개 사건 보고서·사후분석 |
| 예상 | 아직 주소/TX를 고르지 않은 후보 구성 |
| 결정 | fixture 필드, 상태 코드, 허용 오차 정의 원칙 |
| 미결정 | 실제 주소·TX·기준 정답 값 |

## 4. Fixture 필드 표준

각 fixture는 아래 필드를 채운다. JSON의 규범적 구조와 증거 연결 규칙은
[Reference Fixture Schema](../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md)를
따른다.

| 필드 | 설명 |
|:---|:---|
| Fixture ID | `FX-...` |
| Schema Version | 공통 JSON 계약 버전. 현재 `0.1` |
| Fixture Version | 개별 사례 데이터 개정 버전. 현재 `0.1` |
| 연결 문제 ID | 예상문제 은행 ID |
| 상태 | 후보 / 검증 중 / 확정 / 폐기 |
| DOC-M3 결정 | `Confirm Now` / `Deferred` / `Drop`. fixture 생명주기 상태와 분리 |
| 데이터 형태 | 공개 사건 / 공개 온체인 / 자체 테스트 / JSON fixture |
| 체인 | 대상 체인 |
| 주소·TX | 시드 주소, TX 해시, 블록 |
| 기준 정답 | reference answer 요약 |
| 허용 오차 | raw 단위, 수수료, 가격 정밀도 규칙 |
| 확정 사실 | 재조회로 고정되는 사실. 필요 시 `확정 사실(이벤트)`와 `확정 사실(호출·상태)`처럼 증거 유형을 분행 |
| 증거 참조 | `expected.json`의 채점 요구사항과 `evidence.json`의 증거 ID 연결 |
| 소스 역할 | `scoring` / `context` / `supporting`과 필수 여부 |
| 휴리스틱 | 추정으로만 둘 항목. 문제 유형이 둘 이상이면 분기별로 나눔 |
| 필요 데이터 소스 | 등록부 소스 ID만 사용 (`DS-...`). 설명문·데이터 종류 나열 금지 |
| 재현 절차 | 단계 목록 |
| 저작권·출처 | URL, 라이선스/인용 주의 |
| 마지막 확인 | YYYY-MM-DD HH:mm |

### 4.1 허용 오차 정의 원칙

예상문제 은행 3.4와 동일하게, 금액·가격·수수료 오차는 fixture마다 명시한다.

| 유형 | 기본 원칙 |
|:---|:---|
| 네이티브/토큰 수량 | 가능하면 raw 정수 일치(오차 0). 사람이 읽는 단위는 decimals와 함께 병기 |
| 수수료 포함 경로 | 수수료를 제외한 자산 이동과 수수료를 분리 기록 |
| 스왑·브리지 | 수수료·슬리피지·브리지 비용을 명시한 뒤 net 금액 허용 범위를 적음 |
| 가격 환산 | 가격 출처, 시각, 통화, 소수점 자릿수를 고정. 허용 오차는 fixture에 수치로 기재 |
| 불확실 연결 | 정답 자체가 후보 집합인 경우 집합 포함 여부로 채점하고 단일 주소 단정은 실패 |

## 5. 대표 Fixture 목록

| Fixture ID | 문제 ID | Draft | 상태 | DOC-M3 결정 | 핵심 검증 기능 |
|:---|:---|:---:|:---|:---|:---|
| [FX-FLOW-PATH-001](./fixtures/FX-FLOW-PATH-001/README.md) | FLOW-EVM-001 | 1 | 후보 0.1 | 공개 3홉 선정 · replay pending | PATH, internal/top-level edge |
| [FX-FLOW-REMERGE-001](./fixtures/FX-FLOW-REMERGE-001/README.md) | FLOW-EVM-002 | 1 | 후보 0.1 | 공개 4분기·재병합 선정 · replay pending | PATH, RECON, exclusion |
| FX-SVC-DEX-001 | SVC-DEX-001 | 1 | 확정 | V1 기준선 | EVM-LOG, DECODE, RECON |
| FX-SVC-BRG-001 | SVC-BRG-001 | 1 | 후보 | Deferred | XCHAIN, BRIDGE, RECON |
| FX-EVM-AUTH-001 | EVM-AUTH-001 | 2 | 확정 | V1 기준선 | AUTH-DECODE, allowance 연결 |
| [FX-EVM-NFT-721-001](./fixtures/FX-EVM-NFT-721-001/README.md) | EVM-NFT-001 | 2 | 확정 0.1 | 두 RPC·16 oracle·독립 Verifier·analyzer remediation | ERC-721 event·tokenId |
| [FX-EVM-NFT-1155-001](./fixtures/FX-EVM-NFT-1155-001/README.md) | EVM-NFT-001 | 2 | 확정 0.1 | 두 RPC·16 oracle·독립 Verifier·subject 분리 | ERC-1155 Single·Batch |
| [FX-EVM-PROXY-001](./fixtures/FX-EVM-PROXY-001/README.md) | EVM-PROXY-001 | 2 | 확정 0.1 | 두 archive RPC·16 oracle·독립 Verifier·state 정합 | EIP-1967 slot·event |
| FX-EVM-FREEZE-001 | EVM-FREEZE-001 | 2 | 확정 | V1 기준선 | FREEZE, state/logs |
| [FX-FLOW-MULTI-001](./fixtures/FX-FLOW-MULTI-001/README.md) | FLOW-MULTI-001 | 2 | 후보 0.1 | 공개 4 origin→1 exit 선정 · replay pending | RECON, dedup, 다주소 집계 |
| FX-UNCERTAIN-001 | SVC-MIX-001 또는 BTC-CJ-001 | 2 | 후보 | Deferred | MIXER 또는 HEUR(CoinJoin), 불확실성 태그 |
| [FX-BASIC-EVM-001](./fixtures/FX-BASIC-EVM-001/README.md) | BASIC-EVM-001 | 1 | 확정 0.2 | provider replay·반례·consumer pass | EVM-TX, block, code |
| [FX-BASIC-EVM-002](./fixtures/FX-BASIC-EVM-002/README.md) | BASIC-EVM-002 | 1 | 확정 0.2 | archive replay·반례·consumer pass | EVM-STATE, decimals |
| [FX-EVM-TOKEN-001](./fixtures/FX-EVM-TOKEN-001/README.md) | EVM-TOKEN-001 | 1 | 확정 0.2 | filtered logs·ordering·consumer pass | EVM-LOG, first ordering |
| [FX-EVM-TOKEN-002](./fixtures/FX-EVM-TOKEN-002/README.md) | EVM-TOKEN-002 | 1 | 확정 0.2 | primary trace·cross-check·consumer pass | EVM-TRACE, native sum |

## 6. Fixture 상세

DOC-M3 Deferred `후보`는 필드 골격과 `TBD`만 가질 수 있다. TASK-012
Phase 2 네 패키지는 공개 값·provenance·두 공급자 공통 replay와 제품
consumer Gate를 통과해 `확정`이다. 독립 Trace는 엄격한 교차검증을 위한
비차단 후속이며 현재 확정 범위를 넓히지 않는다.

TASK-013 세 패키지는 공개 주소·TX·block, expected/evidence 골격과 두
공급자 receipt/log 또는 historical storage 일치, raw SHA와 명시 scope
replay, negative oracle 16개와 독립 Verifier의 13개 evidence 값·7개
requirement 두 번 재계산까지 확보했다. Analysis I/O·UI·Context·구현,
review remediation과 4개 subject-scoped analyzer 재검증을 모두 닫아
[최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md)에서 `확정`으로
승격했다. NFT는 두 선정 TX와 exact block window, Proxy는 선정 upgrade와
adjacent state만 완전성을 주장한다.

---

### FX-FLOW-PATH-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | FLOW-EVM-001 |
| 상태 | 후보 0.1 — 공개 사례 선정, replay·oracle·Verifier pending |
| DOC-M3 결정 | Phase 2 PATH 후보 — 구현 전 재검토 |
| 패키지 | [FX-FLOW-PATH-001](./fixtures/FX-FLOW-PATH-001/README.md) |
| 데이터 형태 | Euler 공개 사건 + Ethereum 공개 TX·internal transfer |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | `0x036cec...25f1c` → `0xb66cd9...995db` → `0xa1b44d...8e676` → `0xee009f...c8c5`; TX 3건 |
| 기준 정답 | internal 1 + top-level 2의 ordered 3-hop path와 hop별 raw amount |
| 허용 오차 | ETH raw 정수 오차 0. 홉별 금액을 임의로 같게 만들지 않음 |
| 확인 사실 | 선택 TX·block·from/to·value·성공 receipt, 첫 internal edge |
| 미결정 | 긴 block gap 연속 스캔·seed 전체 ledger·독립 trace |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`; `DS-OSINT-WEB`은 context |
| 재현 절차 | selected TX/trace 조회 → endpoint join → raw amount 보존 → terminal 확인 |
| 저작권·출처 | Euler 공식 사건 글·공개 Ethereum/Blockscout. 본문 복제 없음 |
| 마지막 확인 | 2026-07-29 23:25 |

---

### FX-FLOW-REMERGE-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | FLOW-EVM-002 |
| 상태 | 후보 0.1 — 공개 사례 선정, replay·oracle·Verifier pending |
| DOC-M3 결정 | Phase 2 PATH 후보 — 구현 전 재검토 |
| 패키지 | [FX-FLOW-REMERGE-001](./fixtures/FX-FLOW-REMERGE-001/README.md) |
| 데이터 형태 | Euler 공개 사건 + Ethereum 공개 TX |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | seed `0xb66cd9...995db` → branch 4 → merge `0xee009f...c8c5`; split/merge 8 TX |
| 기준 정답 | split `30953000000000000000000`, merge `30951400000000000000000`, unresolved residual `1600000000000000000` wei |
| Exclusion | 외부 주소→branch dust `1000000000000` wei는 seed ledger 밖 context |
| 허용 오차 | ETH raw 정수 오차 0 |
| 확인 사실 | 4개 동일 seed output·4개 공통 merge input·성공 receipt |
| 미결정 | 연속 range·residual 분류·두 공급자 raw SHA |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`; `DS-OSINT-WEB`은 context |
| 재현 절차 | split 수집 → branch identity 보존 → merge 수집 → unrelated inflow 분리 → residual 계산 |
| 저작권·출처 | Euler 공식 사건 글·공개 Ethereum. 본문 복제 없음 |
| 마지막 확인 | 2026-07-29 23:25 |

---

### FX-SVC-DEX-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | SVC-DEX-001 |
| 상태 | 확정 |
| DOC-M3 결정 | V1 기준선 |
| 패키지 | [FX-SVC-DEX-001](./fixtures/FX-SVC-DEX-001/README.md) |
| 데이터 형태 | 공개 온체인 / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | TX `0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5`, 라우터 `0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b`, 풀 `0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc` |
| 기준 정답 | USDC in `25000000000` raw; pool_output WETH `14449515027026387018`; user_net_output ETH 동일 raw |
| 허용 오차 | raw 오차 0 |
| 확정 사실 | Transfer·Swap·Withdrawal 로그 + Router→user internal ETH 전송 |
| 휴리스틱 | 해당 없음 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-DEX-META` |
| 재현 절차 | RPC 로그로 pool_output 계산 → Blockscout API로 user_net_output 확인 → Factory.getPair로 풀 provenance |
| 저작권·출처 | publicnode RPC, dRPC archive, Blockscout API, Uniswap 고정 deploy JSON(GPL-3.0)/V2 Deployments/Pair Addresses, Etherscan UI(교차만). 본문 복제 없음 |
| 마지막 확인 | 2026-07-25 15:13 (동일 입력 재현 통과) |

---

### FX-SVC-BRG-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | SVC-BRG-001 |
| 상태 | 후보 |
| DOC-M3 결정 | Deferred — P2 XCHAIN·BRIDGE 승격 전 재검토 |
| 데이터 형태 | 공개 온체인 |
| 체인 | 출발 TBD, 도착 TBD |
| 주소·TX | 출발 TX=TBD, 도착 TX=TBD, 브리지=TBD |
| 기준 정답 | 출발·도착 TX 쌍, 도착 주소, 매칭 키 |
| 허용 오차 | 브리지 수수료로 인한 금액 차이를 fixture에 명시. raw 기준 허용 범위 TBD |
| 확정 사실 | 양단 이벤트/전송 |
| 휴리스틱 | 유사 금액 후보 중 최종 선택 근거 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-BRIDGE-META` |
| 재현 절차 | 1) 출발 이벤트 2) destination 힌트 3) 도착 매칭 4) 교차검증 |
| 저작권·출처 | 브리지 탐색기/문서 URL=TBD |
| 마지막 확인 | 2026-07-24 15:49 |

---

### FX-EVM-AUTH-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-AUTH-001 |
| 상태 | 확정 |
| DOC-M3 결정 | V1 기준선 |
| 패키지 | [FX-EVM-AUTH-001](./fixtures/FX-EVM-AUTH-001/README.md) |
| 데이터 형태 | 공개 온체인 |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | V `0x193070...af59`, USDC, 승인 TX `0x3f7037...dabd`, 소비 TX `0x7b888f...af51` |
| 기준 정답 | `approve` calldata·Approval 로그 + Router의 `transferFrom` trace + USDC `4500000` raw 전송 + allowance 4지점 |
| 허용 오차 | allowance·전송량 raw 오차 0 |
| 확정 사실(이벤트) | `Approval` 로그. 소비 구간에 `Transfer` 등 전송 이벤트가 있으면 별도 행으로 기록. 호출 calldata와 한 줄로 합치지 않음 |
| 확정 사실(호출·상태) | `approve`/`permit` 호출 TX·calldata·nonce, allowance 전후 상태(archive), `TransferFrom`(또는 동등) 소비 호출 TX. 이벤트 로그와 한 줄로 합치지 않음 |
| 휴리스틱 | 피싱·탈취·피해자 여부는 판정하지 않음. fixture는 권한 소비 연결만 검증 |
| 필수 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM` |
| 보조 provenance | `DS-DEX-META` — Uniswap `sdk-core` 고정 커밋의 `SWAP_ROUTER_02_ADDRESSES(1)`로 주소를 확인하며 권한 소비 채점의 필수 소스는 아님 |
| 재현 절차 | Approval·approve calldata → archive allowance 전후 → 실패 TX 제외 → 성공 TX trace의 transferFrom → Transfer 로그·감소량 대조 |
| 저작권·출처 | publicnode RPC, dRPC archive/trace, Blockscout API, Uniswap `sdk-core` 고정 커밋(MIT), Deployments 교차확인. 본문 복제 없음 |
| 마지막 확인 | 2026-07-25 03:18 (동일 입력 재현 통과) |

---

### FX-EVM-PROXY-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-PROXY-001 |
| 상태 | 확정 0.1 — replay·negative oracle·독립 Verifier·analyzer remediation Gate 통과 |
| DOC-M3 결정 | TASK-013 공개 candidate 선정 · [최종 승격](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) 통과 |
| 패키지 | [FX-EVM-PROXY-001](./fixtures/FX-EVM-PROXY-001/README.md) |
| 데이터 형태 | 공개 온체인 |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | Aave V3 Pool proxy `0x87870bca...b4fa4e2`, upgrade TX `0xe9949c36...bc2b35`, block `25199939` |
| 기준 정답 | implementation `0x8147b99d...0f119bd` → `0x728a138a...6fe03cf`, Upgraded log `1041`, admin before/after zero |
| 허용 오차 | 해당 없음(주소·슬롯 exact match) |
| 확정 사실 | 두 공급자의 receipt/log·EIP-1967 implementation/admin historical slot·raw SHA 일치, 독립 Verifier와 제품 analyzer가 raw에서 재계산 |
| 휴리스틱 | 비표준 프록시는 자동 해석하지 않음 |
| 필요 데이터 소스 | `DS-EVM-RPC-ARCHIVE` |
| 재현 절차 | 1) 명시 block별 슬롯 조회 2) 이벤트 이력 3) before/after 정합 4) beacon이면 implementation() 분리 |
| 저작권·출처 | [EIP-1967](https://eips.ethereum.org/EIPS/eip-1967), 공개 Ethereum RPC. 원문·구현 코드 복제 없음 |
| 마지막 확인 | 2026-07-29 22:13 (remediation 재검토·최종 승격 Gate 통과) |

---

### FX-EVM-NFT-721-001 / FX-EVM-NFT-1155-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-NFT-001 |
| 상태 | 확정 0.1 — replay·negative oracle·독립 Verifier·subject-scoped analyzer Gate 통과 |
| 패키지 | [ERC-721](./fixtures/FX-EVM-NFT-721-001/README.md) · [ERC-1155](./fixtures/FX-EVM-NFT-1155-001/README.md) |
| 데이터 형태 | 공개 EVM log·transaction |
| 체인·주소·TX | Ethereum. BAYC `0xbc4ca0ed...a936f13d` 2 TX, Rarible `0xb66a603f...6518b8` 2 TX |
| 기준 정답 | ERC-721 token `9110` 승인·이동, ERC-1155 Single/Batch ids·amounts·ApprovalForAll. ERC-1155 Single과 Batch는 서로 다른 대상 주소이므로 두 subject-scoped 요청으로 재현 |
| 허용 오차 | 없음(raw integer·address·log order exact) |
| 확정 사실 | 두 공급자 receipt/filtered log의 표준 event·raw SHA·indexed/data field decode 일치, 독립 Verifier와 제품 analyzer가 raw에서 재계산 |
| 휴리스틱 | NFT 가치·소유권 분쟁·거래 의도는 판정하지 않음 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, 필요 시 `DS-EVM-RPC-ARCHIVE` |
| 공식 근거 | [ERC-721](https://eips.ethereum.org/EIPS/eip-721), [ERC-1155](https://eips.ethereum.org/EIPS/eip-1155) |
| 상세 Gate | [TASK-013 Fixture 후보 보고서](./32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) · [최종 승격](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) |
| 마지막 확인 | 2026-07-29 22:13 (remediation 재검토·최종 승격 Gate 통과) |

---

### FX-EVM-FREEZE-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-FREEZE-001 |
| 상태 | 확정 |
| DOC-M3 결정 | V1 기준선 |
| 패키지 | [FX-EVM-FREEZE-001](./fixtures/FX-EVM-FREEZE-001/README.md) |
| 데이터 형태 | 공개 온체인 + 발행사·규제기관 공식 자료 |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | USDC, 대상 `0xd96f2b...4307`, 설정 TX `0xc67cf2...af72`, 해제 TX `0xecf903...1537` |
| 기준 정답 | `Blacklisted`와 `UnBlacklisted` 이벤트 + archive 상태 `false→true→false` |
| 허용 오차 | 해당 없음(boolean/상태 exact) |
| 확정 사실(온체인) | 설정·해제 TX, 이벤트 로그, 네 블록의 `isBlacklisted` 상태 |
| 확정 사실(공식 맥락) | OFAC 2022 지정·2025 해제 원문에 대상 주소가 모두 명시됨 |
| 휴리스틱·제외 | Circle 자료는 주소별 공지가 아닌 정책·Tornado Cash 대응 맥락. 범죄 의도·현재 제재 상태는 채점하지 않음 |
| 필수 데이터 소스 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM`, `DS-OSINT-WEB` |
| 보조 provenance | `DS-EVM-RPC-PUBLIC`, `DS-SANCTIONS-PUBLIC` |
| 재현 절차 | 설정 이벤트·전후 상태 → 해제 이벤트·전후 상태 → Blockscout API → Circle·OFAC 원문 분리 검증 |
| 저작권·출처 | Circle 공식 문서·거래 이전 GitHub 고정 커밋(MIT), OFAC 공식 고시 URL. 원문 복제 없음 |
| 마지막 확인 | 2026-07-25 15:25 (동일 입력 재현 통과) |

---

### FX-FLOW-MULTI-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | FLOW-MULTI-001 |
| 상태 | 후보 0.1 — 공개 사례 선정, replay·oracle·Verifier pending |
| DOC-M3 결정 | Phase 2 PATH 후보 — 가격은 별도 context |
| 패키지 | [FX-FLOW-MULTI-001](./fixtures/FX-FLOW-MULTI-001/README.md) |
| 데이터 형태 | Euler 공개 사건 + Ethereum 공개 TX |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | origin 4개 → exit `0xee009f...c8c5`, 성공 TX 4건 |
| 기준 정답 | origin별 raw contribution과 dedup 합계 `30951400000000000000000` wei |
| 허용 오차 | native raw 오차 0 |
| 확인 사실 | 각 TX의 from/to/value·block·성공 receipt |
| 제외 | 가격·공통 소유·범죄·피해자 귀속은 `not_assessed` |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`; `DS-OSINT-WEB`은 context |
| 재현 절차 | origin별 TX 조회 → exit 일치 → hash dedup → raw 합계 |
| 저작권·출처 | Euler 공식 사건 글·공개 Ethereum. 본문 복제 없음 |
| 마지막 확인 | 2026-07-29 23:25 |

---

### FX-UNCERTAIN-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | `SVC-MIX-001` 또는 `BTC-CJ-001` (fixture 확정 시 하나로 고정. 둘을 한 카드의 동일 확정 사실로 쓰지 않음) |
| 상태 | 후보 |
| DOC-M3 결정 | Deferred — P2 HEUR 또는 P3 MIXER 검토 전에 한 분기로 고정 |
| 데이터 형태 | 공개 사례 |
| 체인 | `SVC-MIX-001`이면 EVM, `BTC-CJ-001`이면 Bitcoin |
| 주소·TX | 유입 TX=TBD, 유출/후속 후보=TBD |
| 기준 정답 | 유입 확정 + 유출 후보 집합 + 항목별 태그(확정/후보/불가). 채점 기준은 아래 분기 확정 사실만 사용 |
| 허용 오차 | 집합 채점. 단일 출구 단정은 실패 |
| 확정 사실 (`SVC-MIX-001`) | 믹서 유입 TX, 믹서 컨트랙트 주소, 라벨·출처 URL. 유출 주소는 확정 사실에 넣지 않음 |
| 확정 사실 (`BTC-CJ-001`) | 해당 TXID의 입출력 주소·금액·vout 등 재조회 가능 필드만. CoinJoin 여부 자체는 확정 사실이 아님 |
| 휴리스틱 (`SVC-MIX-001`) | 유출 후보 집합과 연결 강도 |
| 휴리스틱 (`BTC-CJ-001`) | CoinJoin(또는 유사 혼합) 가능성 점수, 이후 추적 후보 집합 |
| 필요 데이터 소스 | `DS-LABEL-PUBLIC`; EVM이면 `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`; Bitcoin이면 `DS-BTC-API` |
| 재현 절차 | 1) 문제 ID 분기 확정 2) 분기별 확정 사실만 기록 3) 휴리스틱 후보 생성 4) 태그 부여 5) 단정 금지 확인 |
| 저작권·출처 | TBD |
| 마지막 확인 | 2026-07-24 19:14 |

---

### FX-BASIC-EVM-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | BASIC-EVM-001 |
| 상태 | 확정 0.2 — provider replay·반례·consumer pass |
| 패키지 | [FX-BASIC-EVM-001](./fixtures/FX-BASIC-EVM-001/README.md) |
| 데이터 형태 | 공개 온체인 / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | EOA `0xa406bc6e...a7fdf`, Router `0xef1c6e67...54bf6b`, TX `0xbbdaad89...55fa5`, block `16642512` |
| 기준 정답 | EOA·contract·TX·block hash/number·invalid 분류, TX fee `8115326069137440` wei |
| 허용 오차 | 정수·주소·hash exact, 오차 0 |
| 확정 증거 | Publicnode TX·receipt·block, dRPC historical code |
| 부분·실패 | RPC/code 누락은 partial; malformed 강제 변환·gas limit fee 계산은 failed |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE`; `DS-EXPLORER-EVM`은 보조 |
| 승격 잔여 | 없음 |
| 마지막 확인 | 2026-07-29 03:55 |

---

### FX-BASIC-EVM-002

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | BASIC-EVM-002 |
| 상태 | 확정 0.2 — archive replay·반례·consumer pass |
| 패키지 | [FX-BASIC-EVM-002](./fixtures/FX-BASIC-EVM-002/README.md) |
| 데이터 형태 | 공개 historical state / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·블록 | `0xa406bc6e...a7fdf`, block `16642512`, post-state |
| 기준 정답 | ETH `148897435437879000853` wei, USDC `26470158088` raw, decimals `6` |
| 허용 오차 | native·token raw 오차 0 |
| 확정 증거 | dRPC `eth_getBalance`, historical `balanceOf`, `decimals`; Publicnode block |
| 부분·실패 | archive/decimals 누락은 partial; latest 대체·정밀도 손실은 failed |
| 필요 데이터 소스 | `DS-EVM-RPC-ARCHIVE`, `DS-EVM-RPC-PUBLIC` |
| 승격 잔여 | 없음 |
| 마지막 확인 | 2026-07-29 04:36 |

---

### FX-EVM-TOKEN-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-TOKEN-001 |
| 상태 | 확정 0.2 — filtered logs·ordering·consumer pass |
| 패키지 | [FX-EVM-TOKEN-001](./fixtures/FX-EVM-TOKEN-001/README.md) |
| 데이터 형태 | 공개 receipt event + explorer range / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 검색 조건 | from `0xa406bc6e...a7fdf`, USDC, start block `16642512`, ascending |
| 기준 정답 | TX `0xbbdaad89...55fa5`, log `275`, pool 수신, `25000000000` raw |
| 허용 오차 | token raw 오차 0 |
| 확정 증거 | raw receipt Transfer + Blockscout ascending token-transfer range |
| 부분·실패 | event만 있고 첫 순서 미입증은 partial; token/from/order 오선택은 failed |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM` 또는 범위 logs archive |
| 승격 잔여 | 없음 |
| 마지막 확인 | 2026-07-29 03:55 |

---

### FX-EVM-TOKEN-002

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-TOKEN-002 |
| 상태 | 확정 0.2 — primary trace·cross-check·consumer pass |
| 패키지 | [FX-EVM-TOKEN-002](./fixtures/FX-EVM-TOKEN-002/README.md) |
| 데이터 형태 | 공개 TX·receipt·internal call / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | 관심 주소 `0xa406bc6e...a7fdf`, TX `0xbbdaad89...55fa5` |
| 기준 정답 | outer value `0`; Router→관심 주소 internal ETH `14449515027026387018` wei |
| 허용 오차 | native raw 오차 0 |
| 확정 증거 | Publicnode outer TX·Withdrawal, Blockscout internal call, DEX raw replay의 call index |
| 부분·실패 | trace 누락은 partial; outer value만 답·실패 call 합산은 failed |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM` 또는 trace RPC |
| 승격 잔여 | 없음. 독립 trace는 비차단 후속 |
| 마지막 확인 | 2026-07-29 11:00 |

## 7. 승격 기준

| 상태 | 조건 |
|:---|:---|
| 후보 | Deferred 골격/TBD 또는 아직 독립 재현 전인 공개 사례 |
| 검증 중 | 공개 데이터·raw replay 확보, 수동 재현 1회 성공, 필요 소스 등록부에 연결 |
| 확정 | 기준 정답·허용 오차 수치 고정, 동일 입력 재현 성공, 출처·저작권 기록 완료 |
| 폐기 | 데이터 삭제·비공개 전환·중복·규정 위반 위험 |

## 8. DOC-M3 후보 처리 결정

### 8.1 결정 기준

| 결정 | 적용 기준 |
|:---|:---|
| `Confirm Now` | P0·V1 필수이며 공개 입력·정답·출처를 현재 범위에서 고정 가능 |
| `Deferred` | 후속 단계 기능이며 고유 검증 가치가 있으나 source·사례·허용 오차가 미확정 |
| `Drop` | 중복, 공개 재현 불가, 규정 위반 또는 검증 가치 부족이 확정 |

P0·V1은 DEX·AUTH·FREEZE confirmed fixture 3개로 검증 범위가 충족된다.
후보 5개는 모두 후속 단계의 고유 기능을 다루지만 주소·TX·정답 또는
공급자가 미확정이므로 `Deferred`로 결정한다. 현재 `Confirm Now`와 `Drop`은
각각 0개다.

### 8.2 Deferred 승격 조건

| Fixture ID | 단계 | 필요 소스 | 승격 조건 | 재검토 시점 |
|:---|:---:|:---|:---|:---|
| `FX-FLOW-PATH-001` | P1 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM` | primary replay·독립 internal trace·raw SHA·oracle·Verifier 통과 | TASK-014 구현 승인 전 |
| `FX-FLOW-REMERGE-001` | P1 | `DS-EVM-RPC-PUBLIC` | 두 공급자 edge 일치·range 결정·residual 분류·oracle·Verifier 통과 | TASK-014 구현 승인 전 |
| `FX-SVC-BRG-001` | P2 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-BRIDGE-META` | 브리지 양단 TX·공식 이벤트 매칭 키·수수료 허용 범위를 고정하고 1회 재현 | P2 XCHAIN·BRIDGE 승격 전 |
| `FX-EVM-PROXY-001` | P3 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM` | selected candidate의 raw replay·history 범위·반례를 완성해 upgrade TX·EIP-1967 슬롯 이력을 exact match로 재현 | TASK-013 fixture 승격 |
| `FX-FLOW-MULTI-001` | P3 | `DS-EVM-RPC-PUBLIC` | origin set 범위·두 공급자 replay·dedup oracle·Verifier 통과. 가격은 별도 context | TASK-014 구현 승인 전 |
| `FX-UNCERTAIN-001` | P2/P3 | BTC 분기 `DS-BTC-API`; 믹서 분기 `DS-LABEL-PUBLIC`과 EVM source | P2에서는 `BTC-CJ-001` 우선 여부를 결정하고, 한 문제 ID만 선택해 확정 사실·휴리스틱·반례 집합을 분리 | P2 HEUR 시작 전 또는 P3 MIXER 후보 검토 시 |

### 8.3 남은 미결정 사항

- `FX-UNCERTAIN-001`의 최종 문제 ID와 필요하면 별도 fixture ID로 분리할지
- 가격 아카이브 공급자와 재배포 조건
- 공개 사건 보고서의 허용 인용 범위
- 공식 대회 규정상 사전 fixture·cache 반입 가능 여부

## 9. 다음 단계

1. `FX-SVC-DEX-001`, `FX-EVM-AUTH-001`, `FX-EVM-FREEZE-001`은 동일
   입력 재현과 고정 provenance를 통과해 `fixture_version: 0.2`,
   `confirmed`로 승격했다.
2. 세 확정 fixture를 기능 우선순위 Draft 1의 V1 검증 입력으로 연결했다.
3. 세 fixture의 공통 분석 요청·결과 Schema 0.1 변환 예제를 작성했다.
4. 세 confirmed fixture를 소비하는 P0·V1 QA 시나리오 Draft를 작성했다.
5. 후보 5개는 DOC-M3에서 모두 `Deferred`로 결정하고 승격 조건·소스·시점을
   기록했다.
6. Document Completion Gate를 통과했으며 구현 회귀 자동화는 별도 구현 승인 후 진행한다.
7. P2 승격에 필요한 BRIDGE·BTC fixture는 Deferred 승격 조건에 따라 선정한다.
8. TASK-012용 EVM Core 4개는 공개 DEX 기준점을 재사용해 패키지화하고,
   QuickNode·Alchemy 공통 9개 replay 일치로 `검증 중`까지 승격했다.
   offline 반례는 통과했으며 정식 Schema·fixture provenance 정책·구현 승인
   전에는 `confirmed`로 올리지 않는다. 독립 Trace는 비차단 후속이다.
9. primary archive·trace와 independent TX·receipt·block·filtered
   logs·historical state capability smoke를 통과했다. endpoint·API key는
   fixture·artifact·DB에 저장하지 않으며 credential 회전은 후속 Gate다.
10. TASK-012 네 fixture의 합성 negative oracle 24개를 두 번 실행해
    complete·partial·failed 결정성을 통과했다. 제품 Analysis type 승인과
    독립 Trace 후속 검증은 별도다. QuickNode raw Trace를 가진 runtime
    `complete`와 fixture `confirmed`는 같은 상태가 아니다.
11. 네 fixture를 소비할 `evm_core` `0.2-draft` request/result 제안 12개와
    Schema probe 14개를 통과했다. 이는 consumer contract 검토 증거이며,
    정식 Analysis I/O 승인·제품 analyzer·fixture `confirmed`를 뜻하지 않는다.
12. TASK-013 NFT·Proxy 세 fixture의 합성 negative oracle 16개를 두 번
    실행해 표준 혼동·범위 누락·ABI·slot/state 충돌 경계를 고정했다.
13. TASK-013 독립 Verifier가 raw replay에서 당시 세 candidate의 필수 facts,
    13개 evidence 값과 7개 requirement를 두 번 재계산했다. Oracle·Verifier
    보고서 경로와 fact hash도 evidence provenance에 고정했다. UI·Context
    Receipt와 별도 승격 판단이 남아 당시 package는 `candidate`였다.
14. TASK-013 analyzer remediation 재검토와 4개 subject-scoped request의
    canonical hash·결정성 검증을 통과해 세 package를 `confirmed`로
    승격했다. Benchmark는 EVM-NFT-001·EVM-PROXY-001을 포함해 9/9다.
15. TASK-014는 Euler 공개 사건에서 단일 3홉·4분기 재병합·4 origin 공통
    exit 사례를 선정해 세 package를 `candidate`로 작성했다. replay·oracle·
    Verifier와 구현 승인은 남아 있다.

## 10. Related Documents

- **Concept_Design**: [SCAN 2026 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제·완료조건·대표 사례 후보의 기준
- **Concept_Design**: [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 준비 전략
- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - confirmed fixture 기반 V1 경로와 P2 승격 조건
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - fixture별 필요 소스와 제약
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - 실전 complete·fixture confirmed·독립 Trace 경계
- **Technical_Specs**: [Reference Fixture Schema](../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) - JSON 0.1 계약과 증거·소스 역할
- **Technical_Specs**: [P0·V1 도구 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - fixture를 소비하는 분석 계약
- **Technical_Specs**: [P0·V1 기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md) - 회귀 실행 기술과 저장·검증 경계
- **Technical_Specs**: [공통 분석 I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - fixture 입력·정답·증거의 실행 계약 매핑
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - TASK-012 독립 재현 선행 Gate
- **Technical_Specs**: [TASK-012 Analysis Contract](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - 네 confirmed fixture의 Analysis I/O 0.2 consumer contract
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - confirmed 3·후보 5 처리 방침 Gate
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - fixture별 구현 작업과 완료 기준
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - confirmed fixture exact-match·오류 주입 기준
- **QA_Validation**: [QA Checklist](./02_QA_CHECKLIST.md) - 문서·구현·회귀 실행 Gate
- **QA_Validation**: [분석 I/O 예제](./examples/analysis/README.md) - confirmed fixture 3개의 요청·결과 변환 예
- **QA_Validation**: [FX-SVC-DEX-001](./fixtures/FX-SVC-DEX-001/README.md), [FX-EVM-AUTH-001](./fixtures/FX-EVM-AUTH-001/README.md), [FX-EVM-FREEZE-001](./fixtures/FX-EVM-FREEZE-001/README.md) - 우선 구축 fixture 패키지
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - EVM Core 후보 4개와 승격 전 잔여 Gate
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 계정 smoke·secret·독립성
- **QA_Validation**: [TASK-012 Negative Oracle 보고서](./27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - 네 confirmed fixture의 24개 offline 반례
- **QA_Validation**: [TASK-012 Analysis Contract Examples](./examples/task-012/README.md) - complete·partial·failed 12개 제안 사례와 검증 명령
- **QA_Validation**: [TASK-013 Negative Oracle 보고서](./33_TASK_013_NEGATIVE_ORACLE_REPORT.md) - NFT·Proxy 16개 반례·결정성
- **QA_Validation**: [TASK-013 독립 Verifier 보고서](./34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md) - raw-first facts·requirement 재계산
- **QA_Validation**: [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - confirmed·Benchmark 9/9 근거
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 사전 fixture·cache와 source 허용 범위
