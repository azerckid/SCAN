# TASK-013 Fixture 승격 검토 보고서
> Created: 2026-07-29 19:53
> Last Updated: 2026-07-29 20:19
> Status: Promoted to 검증 중 (Verifying) · UI 사용자 승인 완료 · Analyzer 구현 대기

> **후속 상태:** 이 문서는 `candidate → verifying` 당시 판정을 보존한다.
> 이후 analyzer remediation 재검토까지 통과해 세 fixture는 `confirmed`,
> Benchmark는 9/9로 승격됐다. 현재 판정은
> [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md)를
> 따른다.

## 1. 목적

이 문서는 [TASK-013 Fixture 후보 보고서](./32_TASK_013_FIXTURE_CANDIDATE_REPORT.md)가
`판정` 절에서 미룬 **별도 승격 판단**을 내린다. 세 candidate package
(`FX-EVM-NFT-721-001`, `FX-EVM-NFT-1155-001`, `FX-EVM-PROXY-001`)가
`후보(candidate)`에서 `검증 중(verifying)`으로 승격할 자격을 갖췄는지만
판단하며, `확정(confirmed)` 승격은 이 문서의 범위가 아니다.

## 2. 승격 기준 근거

[Reference Fixtures](./01_REFERENCE_FIXTURES.md) §3의 상태 구분과 TASK-012
Wave 1 선례를 기준으로 삼는다. TASK-012의 네 fixture는 "두 공급자 교차
재현과 negative oracle을 확보해 `검증 중`이며, fixture 승격 정책·정식 계약
Gate가 남아 있다"는 조건으로 승격됐다(§9 TASK-012 항목). TASK-013은 그
기준에 더해 raw-first 독립 Verifier 재계산까지 갖춘 상태이므로, 최소한
같은 문턱은 충족한다.

`검증 중`으로 인정하는 최소 조건:

1. 공개 주소·TX·block이 실제 mainnet 자료에서 선정됨
2. 두 개의 독립 논리 공급자(primary·verify)가 같은 decoded 값을 재현
3. negative oracle이 표준별 실패·경계 조건을 반례로 검증
4. 결과가 두 번 실행에서 결정적으로 동일
5. requirement→evidence→source 참조 무결성이 破손 없이 성립

`확정`으로 올리려면 위에 더해 다음이 필요하며, 이 문서는 이 항목들을
승격 조건이 아니라 **잔여 Gate**로 명시한다.

6. Analysis I/O 계약 정식 결정과 Schema 반영
7. 사용자가 확인한 UI Preview 승인
8. Context Receipt `PASS`
9. 사용자 구현 승인 기록
10. Python decoder 구현과 독립 Verification Receipt

## 3. Fixture별 검토

### 3.1 FX-EVM-NFT-721-001

| 조건 | 근거 |
|:---|:---|
| 공개 사례 | BAYC(`0xe445283d46d814af9ab554d5afb40afb28b91935`이 `to`인 실제 mainnet TX 2건) |
| 두 공급자 재현 | `primary`·`verify` receipt·filtered logs가 contract·block·log index·from/to/tokenId 일치 |
| negative oracle | ERC-20/721 signature 혼동, 다른 contract log, data 필드 오독 등 5개, 2회 결정적 통과 |
| 독립 Verifier | raw topics에서 `token_id_raw=9110`, `Approval` reset(`0x0`), `ApprovalForAll` 재계산이 `expected.json`과 일치, 3개 evidence 값 재대조 |
| 참조 무결성 | `REQ-NFT721-TRANSFER`→`EV-NFT721-TRANSFER`, `REQ-NFT721-APPROVALS`→`EV-NFT721-OPERATOR-APPROVAL`+`EV-NFT721-TOKEN-APPROVAL-RESET` 모두 존재 확인 |

**판정: 검증 중 승격 자격 충족.**

### 3.2 FX-EVM-NFT-1155-001

| 조건 | 근거 |
|:---|:---|
| 공개 사례 | Rarible 계열 token(`token_id_raw`가 uint256 원본, 10진수 큰 값), Single 1건 + Batch 1건 |
| 두 공급자 재현 | `primary`·`verify`가 Single(log 1033·1034·1035·1038)과 Batch(log 646) 모두 일치 |
| negative oracle | Batch 배열 길이 불일치, approval transition 누락 등 5개, 2회 결정적 통과 |
| 독립 Verifier | `ids_raw`/`amounts_raw` 2개 배열 순서·길이, SINGLE-IN/OUT과 APPROVAL-TRUE/FALSE 4건 log_index 정렬이 raw와 정확히 일치, 5개 evidence 값 재대조 |
| 참조 무결성 | `REQ-NFT1155-SINGLE-APPROVAL`이 4개 evidence를 모두 참조, `REQ-NFT1155-BATCH`가 `EV-NFT1155-BATCH` 참조 확인 |

**판정: 검증 중 승격 자격 충족.**

### 3.3 FX-EVM-PROXY-001

| 조건 | 근거 |
|:---|:---|
| 공개 사례 | Aave V3 Pool proxy(`0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2`), `Upgraded` 실 event |
| 두 공급자 재현 | `primary`·`verify`의 `eth_getStorageAt` before/after가 구현체 주소 일치, admin slot 0 확인 |
| negative oracle | beacon·admin slot을 구현체로 오독, 최신 state를 과거 block으로 대체 등 6개, 2회 결정적 통과 |
| 독립 Verifier | `Upgraded` event의 `after_implementation`이 slot 재계산값과 일치, admin 두 시점 모두 0, 5개 evidence 값 재대조 |
| 참조 무결성 | `REQ-PROXY-UPGRADE-EVENT`·`REQ-PROXY-HISTORICAL-SLOT`·`REQ-PROXY-ADMIN-SEPARATION` 3개 requirement가 5개 evidence를 완전히 커버 |

**판정: 검증 중 승격 자격 충족.**

## 4. 결정

세 candidate package를 `후보(candidate)`에서 `검증 중(verifying)`으로
승격한다. `확정(confirmed)`은 §2의 잔여 Gate(6~10)를 순서대로 닫은 뒤
별도로 판단한다.

이 승격은 다음을 바꾸지 않는다.

- Analysis I/O `0.2`의 공개 계약과 기존 7개 automated 문제
- Benchmark 자동화 수(계속 7)
- Schema 검증 package 수(계속 10; fixture 상태만 변경, 신규 package 아님)
- TASK-013 Backlog `Status: ToDo`, `Context Receipt: PENDING`

## 5. 다음 Gate

1. ~~Analysis I/O 대안 결정과 전용 UI Preview 작성~~ → 대안
   B([TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) §5.1)
   확정, [UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md)·Preview 작성 완료
2. ~~사용자가 UI Preview를 확인하고 승인한다.~~ → 2026-07-29 20:19 승인 완료
3. ~~Context Receipt `PASS` 전환과 사용자 구현 승인 기록~~ → Backlog에 기록
   완료
4. **다음: NFT·Proxy analyzer 구현과 독립 Verification Receipt**
5. Benchmark automated 7 → 9 승격

## 6. Related Documents

- [TASK-013 Fixture 후보 보고서](./32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 승격 이전 candidate 근거
- [TASK-013 Negative Oracle 보고서](./33_TASK_013_NEGATIVE_ORACLE_REPORT.md) - 16개 반례·결정성
- [TASK-013 독립 Verifier 보고서](./34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md) - raw-first 재계산 증거
- [TASK-013 분석 계약 제안](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - Analysis I/O 대안·UI 영향
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - 상태 구분 정의와 fixture registry
- [Backlog TASK-013](../04_Logic_Progress/00_BACKLOG.md) - Context Receipt·승인 Gate
- [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - 후속 confirmed·Benchmark 9/9 판정
