# TASK-016 Bridge Fixture 승격 검토 보고서
> Created: 2026-07-31 03:20
> Last Updated: 2026-07-31 04:00
> Status: Promoted to 검증 중 (Verifying) · Analysis I/O 대안 B 확정 · Analyzer 구현 대기

## 1. 목적

이 문서는 `FX-SVC-BRG-001`이 `후보(candidate)`에서 `검증 중(verifying)`으로
승격할 자격을 갖췄는지만 판단한다. `확정(confirmed)` 승격, Analysis I/O
대안 확정, `bridge_transfer` analyzer 구현 승인은 이 문서의 범위가 아니다.

## 2. 승격 기준 근거

[TASK-013 승격 검토](./35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) §2가 정한
최소 조건을 그대로 따른다.

`검증 중`으로 인정하는 최소 조건:

1. 공개 주소·TX·block이 실제 mainnet 자료에서 선정됨
2. 두 개의 독립 논리 공급자(primary·verify)가 같은 decoded 값을 재현
3. negative oracle이 표준별 실패·경계 조건을 반례로 검증
4. 결과가 두 번 실행에서 결정적으로 동일
5. requirement→evidence→source 참조 무결성이 파손 없이 성립

`확정`으로 올리려면 위에 더해 다음이 필요하며, 이 문서는 이 항목들을
승격 조건이 아니라 **잔여 Gate**로 명시한다.

6. Analysis I/O 대안 A/B 정식 결정과 Schema 반영
7. 사용자가 확인한 UI Preview 승인 (이미 완료 — [Bridge/XChain UI](../02_UI_Screens/11_TASK_016_BRIDGE_XCHAIN_UI.md))
8. Context Receipt `PASS`
9. 사용자 구현 승인 기록
10. `bridge_transfer` analyzer 구현과 독립 Verification Receipt

## 3. FX-SVC-BRG-001 검토

| 조건 | 근거 |
|:---|:---|
| 공개 사례 | Across V3 Base→Ethereum 실 전송(deposit ID `2395968`, Base TX `0x957143...05a1b`, Ethereum TX `0x816ebc...8f8a0`) |
| 두 공급자 재현 | Base primary/verify, Ethereum primary/verify 16 read-only call. `assert_matching_provider_facts`가 두 role의 canonical facts(deposit ID·자산·금액·deadline·exclusive relayer·message)가 코드로 실제 동일함을 확인(`cross_provider_decoded_match: true`) |
| negative oracle | doc 21 §6의 7개 범주(오매칭·domain 충돌·tolerance 남용·evidence 누락·scope 합성·heuristic 승격·amount 공식 불일치)를 8개 synthetic case로 고정, 2회 결정성 통과 |
| 독립 Verifier | content-addressed raw JSON-RPC 아티팩트(`artifacts/sha256/`)가 provider-replay.json의 pinned raw_sha256과 바이트 단위 일치, topic0 signature·log↔receipt↔transaction↔block exact binding(blockHash·전체 topics·data·blockNumber·removed 포함)까지 재검증한 뒤 ABI를 처음부터 재디코딩. `expected.json`의 `bridge_transfer`와 정확히 일치, canonical hash `d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac`를 `evidence.json.verification_provenance`에 pin하고 drift 시 거부 |
| 참조 무결성 | `REQ-BRIDGE-SOURCE`→`EV-BRIDGE-SOURCE-EVENT`, `REQ-BRIDGE-DESTINATION`→`EV-BRIDGE-DESTINATION-EVENT`, `REQ-BRIDGE-DOMAIN`→`EV-BRIDGE-OFFICIAL-CONTRACTS`+`EV-BRIDGE-MATCHING-RULE` 모두 존재 확인 |

**판정: 검증 중 승격 자격 충족.**

## 4. 결정

`FX-SVC-BRG-001`을 `후보(candidate)`에서 `검증 중(verifying)`으로 승격한다.
`확정(confirmed)`은 §2의 잔여 Gate(6~10)를 순서대로 닫은 뒤 별도로 판단한다.

이 승격은 다음을 바꾸지 않는다.

- Benchmark 자동화 수(계속 12 automated·4 assisted·14 unsupported)
- Analysis I/O 공개 Schema·코드(대안 B는 확정됐으나 Pydantic 모델·Schema
  반영은 별도 구현 승인 후)
- TASK-016 Backlog `Status: ToDo`, `Context Receipt: PENDING`
- `MIXED-XCHAIN-001` 조합 Gate(별도, DEX+Bridge+CEX leg 결합)

## 5. 다음 Gate

1. ~~Analysis I/O 대안 A/B 정식 결정~~ — 완료. 대안 B(`bridge_transfer`
   전용 leaf) 확정(doc 21 §5, PR #105).
2. Context Receipt `PASS`·사용자 구현 승인 기록
3. `bridge_transfer` analyzer 구현과 독립 Verification Receipt(analyzer
   canonical hash ↔ 독립 Verifier hash 대조)
4. Benchmark automated 승격 여부를 별도 판정

## 6. Related Documents

- [Bridge 후보 선정 보고서](./61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md) - 승격 이전 candidate 근거
- [Bridge Raw Replay 보고서](./62_TASK_016_BRIDGE_RAW_REPLAY_REPORT.md) - 16 call·negative oracle 8개·독립 Verifier·P1 remediation 전체 기록
- [Bridge/XChain 계약 제안](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md) - 정답·evidence·오라클 계약
- [Bridge/XChain UI](../02_UI_Screens/11_TASK_016_BRIDGE_XCHAIN_UI.md) - 사용자 승인된 Preview
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 상태 목록
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md) - adapter 범위·Context Receipt
