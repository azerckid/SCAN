# TASK-015 LABEL Fixture Migration Receipt
> Created: 2026-07-30 16:28
> Last Updated: 2026-07-30 16:28
> Status: Applied · Replacement Verifying · Final Promotion Not Decided

## 1. 목적과 판정

`FX-OSINT-LABEL-CONFLICT-001`의 OpenRAIL selected row 채점 의존을
제거하고, 승인된 replacement route를 실제 fixture·oracle·Verifier·제품
analyzer에 적용한다.

**판정: migration은 통과했으나 fixture는 `verifying`을 유지한다.**
이번 Receipt는 source 교체와 계산 정합을 증명하며 `confirmed` 승격을
승인하지 않는다.

## 2. 적용 범위

| 구분 | 이전 | migration 이후 |
|:---|:---|:---|
| Subject | `0xc3877028655ebe90b9447dd33de391c955ead267` | `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc` |
| Source assertion | OpenRAIL selected row | confirmed OFAC 2022 historical action projection |
| Community role | team4 vesting contract | ETH `0.1` Tornado instance |
| ENS name | `team4.vesting.contract.tornadocash.eth` | `eth-01.tornadocash.eth` |
| Current status | `not_assessed` | `not_assessed` |
| Ownership·criminality | `not_assessed` | `not_assessed` |
| Fixture status | verifying | verifying |

기존 OpenRAIL artifact와 license 조사 기록은 history 보존을 위해 삭제하지
않지만, request·source replay·evidence requirement·canonical fact의
scoring/provenance dependency에서는 제거했다.

## 3. Fixed-block ENS 재현

Ethereum block `25,640,270`(`0x1873d4e`)에서 ENS registry
`resolver(bytes32)`와 resolver `addr(bytes32)`를 read-only `eth_call`로
실행했다.

| Provider | resolver | address | 판정 |
|:---|:---|:---|:---:|
| `PROVIDER-EVM-VERIFY` | `0x4976fb03…aba41` | `0x12d66f87…6b8fc` | complete |
| `BLOCKSCOUT-ETH-RPC` | 동일 | 동일 | complete |
| `PROVIDER-EVM-PRIMARY` | JSON-RPC `-32003` | 미실행 | failed |
| `PROVIDER-EVM-TRACE` | HTTP 403 이력 | 미실행 | failed |

실패 공급자를 성공으로 추론하지 않았다. 성공한 두 공급자의 raw response
SHA-256은 `provider-replay.json`에 별도로 보존했다.

## 4. Raw-first 재계산

독립 Verifier는 다음 경로를 제품 analyzer와 별도로 계산한다.

1. bounded official projection artifact의 content hash를 검증한다.
2. linked confirmed SANCTIONS fixture의 subject·action date·HTML hash·주소
   match count를 다시 대조한다.
3. pinned MIT `config.js`에서 mining rate `10`과
   `instances.netId1.eth.instanceAddress["0.1"]`을 별도 필드로 읽는다.
4. mining rate를 denomination으로 오인하지 않는다.
5. fixed-block ENS artifact와 두 provider decoded address를 대조한다.
6. official history·community role·onchain binding을 자동 병합하지 않는다.

새 canonical fact SHA-256은
`972a154d20846478774f9fb7b685f7db1d7c5c8eac37fa1c5cd2cb444514d1a9`다.
독립 Verifier와 제품 analyzer가 두 번 결정적으로 같은 값을 산출한다.

## 5. Oracle·회귀

- LABEL oracle의 selected-row integrity 조건을 official-history projection
  integrity 조건으로 교체했다.
- 전체 TASK-015 negative oracle 30개를 두 번 실행한다.
- ENS node는 `eth-01.tornadocash.eth` namehash로 고정한다.
- official projection·MIT config·ENS artifact 1-byte drift는 Verifier가
  content-address mismatch로 거부한다.
- 기존 SANCTIONS·ENS·RELATION-HUB·common-funder 및 다른 analyzer 경로는
  변경하지 않는다.

전체 offline Gate는 **542 tests**, fixture **18**, Analysis I/O **52 probes**,
traceability **1,742 links**, security **207 files**를 통과했다.

## 6. 승격 경계

이번 작업에서 다음은 수행하지 않았다.

- LABEL fixture `confirmed` 승격
- Benchmark automated/assisted/unsupported 집계 변경
- current sanctions status·소유권·범죄성 판정
- OpenRAIL historical artifact 삭제
- TASK-016 착수

별도 Promotion Review가 fixture 상태와 Benchmark 반영 여부를 판단한다.

## 7. 365 글로벌 평가 기준

| 기준 | 상태 | 근거 |
|:---|:---:|:---|
| Functionality | Pass | replay·oracle·Verifier·analyzer가 replacement fact를 결정적으로 재현 |
| Potential Impact | Pass | 불명확 license source 없이 재사용 가능한 bounded LABEL 검증 경로 |
| Novelty | Pass | 역사적 action·protocol role·ENS binding을 source별로 분리 |
| UX | Pass / Existing | 기존 conflict·`not_assessed` 출력 계약 유지 |
| Open-source | Pass | official locator·MIT config·onchain artifact로 재현 가능 |
| Business Plan | N/A | 대회 준비용 fixture migration |

## 8. Originality & Ethics Check

- repository license로 upstream data 권한을 세탁하지 않는다.
- 역사적 제재 action을 현재 제재·범죄성으로 확대하지 않는다.
- config role과 ENS binding을 소유권 사실로 확대하지 않는다.
- 실패 provider와 미평가 항목을 숨기지 않는다.

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT-LBL-001 채점 경계
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - source conflict·not_assessed 표시
- **Technical_Specs**: [intel_context I/O 계약](../03_Technical_Specs/18_TASK_015_INTEL_CONTEXT_IO_CONTRACT.md) - replacement request/result canonical fact
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source role·Terms 경계
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) · [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md)
- **QA_Validation**: [Source Replacement Review](./57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md) - migration 입력 결정
- **QA_Validation**: [Promotion Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) - 별도 final promotion Gate
- **Fixture**: [LABEL conflict fixture](./fixtures/FX-OSINT-LABEL-CONFLICT-001/README.md) · [confirmed SANCTIONS fixture](./fixtures/FX-OSINT-SANCTIONS-HISTORY-001/README.md)
