# FX-SVC-BRG-001 — Across V3 Base→Ethereum 후보

> Status: candidate · raw provider replay complete

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
관찰의 SHA-256과 decoded match는 고정됐지만 negative oracle·독립 Verifier가
남아 있으므로 아직 `verifying` 상태가 아니다.

## 파일

- `input.json`: 발견 모드 request와 양단 고정 scope
- `expected.json`: 후보 정답·composite match·정수 금액 계약
- `evidence.json`: 공식 문서와 Explorer supporting evidence
- `raw-replay.json`: 양단 normalized replay와 reconciled facts
- `provider-replay.json`: 네 chain/provider 역할의 capability별 SHA-256

## 다음 Gate

1. negative oracle과 2회 결정성 Gate
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
