# FX-SVC-BRG-001 — Across V3 Base→Ethereum 후보

> Status: candidate · raw provider replay·negative oracle complete

## 범위

Across V3의 공개 Base→Ethereum 전송 한 건을 `SVC-BRG-001`의 fixture
후보로 고정한다.

- source: Base `8453`, TX
  `0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b`
- destination: Ethereum `1`, TX
  `0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0`
- Across deposit ID: `2395968`
- recipient: `0xdd8591007149631190f1013ac1067305f191cd0a`
- amount: `330000000000000000` → `329132286989970407`

현재 값은 Across 공식 문서와 BaseScan/Etherscan supporting 화면에서
선정한 뒤 Base·Ethereum 각 두 source role에서 재현했다. 16개 read-only
관찰의 SHA-256과 decoded match는 고정됐고, `assert_matching_provider_facts`가
primary·verify 두 role의 canonical facts(deposit ID·자산·금액·deadline·
exclusive relayer·message)가 실제로 동일함을 코드로 재확인했다. `exclusive_relayer`
비교와 zero-output-token → 공식 Base WETH↔Ethereum WETH 매핑 검증도
`bridge_pair_facts`에 포함됐다. doc 21 §6의 7개 negative oracle 범주(오매칭·
domain 충돌·tolerance 남용·evidence 누락·scope 합성·heuristic 승격·amount
공식 불일치)를 8개 synthetic case로 고정해 2회 결정성으로 통과했다. 독립
Verifier가 남아 있으므로 아직 `verifying` 상태가 아니다.

## 파일

- `input.json`: 발견 모드 request와 양단 고정 scope
- `expected.json`: 후보 정답·composite match·정수 금액 계약
- `evidence.json`: 공식 문서와 Explorer supporting evidence
- `raw-replay.json`: 양단 normalized replay와 reconciled facts
- `provider-replay.json`: 네 chain/provider 역할의 capability별 SHA-256

## 다음 Gate

1. ~~negative oracle과 2회 결정성 Gate~~ — 완료
   ([manifest](../../oracles/task-016-bridge-negative-oracles-v0.1.json)).
2. 독립 Verifier의 raw-first 재계산
3. candidate → verifying 별도 판정

endpoint·credential·Explorer 본문은 이 package에 저장하지 않는다.
QuickNode의 bounded 호출은 429, PublicNode의 exact-block log는 403이었고
성공으로 추론하지 않았다. 최종 decoded 교차검증은 Base managed/official
public RPC와 Ethereum managed/supporting explorer-backed RPC로 완료했다.

## Related Documents

- [Bridge 후보 보고서](../../61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md)
- [Bridge 계약](../../../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md)
- [Reference Fixtures](../../01_REFERENCE_FIXTURES.md)
