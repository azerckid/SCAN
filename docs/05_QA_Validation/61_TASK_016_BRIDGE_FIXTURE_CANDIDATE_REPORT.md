# TASK-016 Bridge/XChain 공개 Fixture 후보 선정 보고서
> Created: 2026-07-30 22:51
> Last Updated: 2026-07-30 22:51
> Status: Candidate Selected · Raw Replay Not Executed · Fixture Package Not Created

## 1. 목적

사용자 승인에 따라 `SVC-BRG-001`용 `FX-SVC-BRG-001`의 공개 후보를
선정한다. 이 단계는 공식 프로토콜 문서와 공개 탐색기 화면에서 한 건의
양단 거래를 식별하고, 후속 raw replay가 검증할 값을 고정하는 docs-only
Gate다.

이 보고서는 다음을 주장하지 않는다.

- fixture package 생성 또는 `verifying`/`confirmed` 승격
- 두 RPC provider raw replay·content SHA-256 완료
- negative oracle·독립 Verifier·제품 analyzer 완료
- Across API 호출, live source 채택 또는 대회 Rules 허용
- recipient 소유·본인성·불법성 판정

## 2. 선택 결과

| 필드 | 후보 값 |
|:---|:---|
| Fixture | `FX-SVC-BRG-001` |
| 문제 | `SVC-BRG-001` |
| 프로토콜 | Across V3 |
| 경로 | Base `8453` → Ethereum `1` |
| 출발 SpokePool | `0x09aea4b2242abc8bb4bb78d537a67a245a7bec64` |
| 도착 SpokePool | `0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5` |
| 출발 TX | `0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b` |
| 출발 block / 시각 | `21912139` / `2024-11-03 06:00:25 UTC` |
| 도착 TX | `0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0` |
| 도착 block / 시각 | `21105182` / `2024-11-03 06:00:35 UTC` |
| domain key | Across V3 + origin `8453` + destination `1` + source SpokePool + `depositId=2395968` |
| 상태 | `candidate` — package·raw replay 없음 |

Across 공식 배포 문서는 Base와 Ethereum의 chain ID·SpokePool 주소를
제시한다. 공식 V3 문서는 출발 `V3FundsDeposited`, 도착 `FilledV3Relay`,
`originChainId + depositId` 추적과 공통 파라미터 일치를 정의한다. 공개
BaseScan/Etherscan 화면은 위 주소와 이벤트를 표시하지만, 탐색기 해석은
후보 발견·교차확인 역할일 뿐 raw scoring source가 아니다.

## 3. 양단에서 관찰한 후보 사실

### 3.1 출발 — `V3FundsDeposited`

| 필드 | 값 |
|:---|:---|
| event topic0 | `0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f` |
| input token | Base WETH `0x4200000000000000000000000000000000000006` |
| output token | zero address — 공식 규칙의 destination equivalent token |
| input amount | `330000000000000000` |
| output amount | `329132286989970407` |
| destination chain | `1` |
| deposit ID | `2395968` |
| depositor | `0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae` |
| recipient | `0xdd8591007149631190f1013ac1067305f191cd0a` |
| quote timestamp | `1730613371` (`2024-11-03 05:56:11 UTC`) |
| fill deadline | `4294967295` |
| message | empty |

### 3.2 도착 — `FilledV3Relay`

| 필드 | 값 |
|:---|:---|
| event topic0 | `0x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7` |
| origin chain | `8453` |
| destination token | Ethereum WETH `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` |
| deposit ID | `2395968` |
| input amount | `330000000000000000` |
| output / observed amount | `329132286989970407` |
| depositor / recipient | 출발 이벤트와 동일 |
| observed destination leg | WETH transfer → unwrap → recipient ETH transfer |

도착 시각은 출발보다 10초 뒤다. 이는 이 한 사례의 관찰값일 뿐 일반적인
Across 도착 시간이나 허용 window로 사용하지 않는다.

## 4. 정수 정합과 매칭 경계

이 후보의 두 자산은 모두 18 decimals다. 공식 V3 규칙에서 출발
`outputToken=0x0`은 도착 체인의 equivalent token을 뜻하며, 도착 이벤트는
Ethereum WETH를 사용한다.

```text
source_raw                 = 330000000000000000
observed_destination_raw   = 329132286989970407
protocol_fee_raw candidate =   867713010029593

330000000000000000 - 867713010029593
  = 329132286989970407
```

`max_abs_delta_raw` 후보는 `0`이다. `protocol_fee_raw`는 두 event amount의
차이로 재계산한 값이며, 세부 fee component나 경제적 귀속은 판정하지 않는다.

`depositId=2395968`만으로 연결하지 않는다. raw replay에서는 protocol,
양 chain ID, source SpokePool, deposit ID, depositor, recipient, input/output
amount, deadline, message 등 Across V3의 공통 파라미터를 함께 대조해야 한다.
금액·10초 시간차만으로 같은 전송이라고 판정하는 것도 금지한다.

## 5. Source 역할과 이용 경계

| Source | 역할 | 현재 사용 |
|:---|:---|:---|
| Across Chains & Contracts | official contract registry | chain ID·SpokePool 주소 후보 pin |
| Across Tracking Deposits / V2→V3 migration | official protocol contract | event schema·tracking/matching 규칙 |
| BaseScan source TX page | supporting explorer | 출발 TX·event 후보 발견 |
| Etherscan destination TX page | supporting explorer | 도착 TX·event·value leg 후보 발견 |
| Across status API | 사용 안 함 | production key 필요; fixture truth로 사용하지 않음 |

공식 문서 URL과 탐색기 URL만 기록한다. 페이지 본문·Across API 응답을
fixture에 복제하지 않는다. Explorer Terms와 대회 Rules가 확정되기 전에는
자동 수집·재배포·live adapter 채택을 주장하지 않는다.

## 6. 다음 raw replay Gate

1. Base와 Ethereum을 지원하는 두 독립 RPC 역할에서 각 TX·receipt·block을
   읽기 전용으로 재현한다.
2. 각 SpokePool 주소와 exact-block filtered logs를 조회하고 raw response
   SHA-256·retrieved_at·논리 provider ID를 보존한다.
3. 출발 `V3FundsDeposited`와 도착 `FilledV3Relay`를 ABI로 독립 decode하고
   §4의 composite domain·공통 파라미터·정수 amount를 대조한다.
4. WETH Transfer·Withdrawal·recipient ETH leg를 정합하고, missing trace/log는
   `partial`, 확보 근거 충돌은 `reconciliation_failed`로 분리한다.
5. 다른 chain/SpokePool의 동일 deposit ID, 유사 금액, 다른 recipient,
   destination window 밖 도착, 임의 tolerance 등 negative oracle을 작성한다.
6. 위 Gate 이후에만 package 생성과 `candidate → verifying`을 별도 심사한다.

현재는 endpoint·credential·raw response를 저장하지 않았고 network call
count도 fixture 실행 수치로 기록하지 않는다.

## 7. Gate 판정

| 항목 | 결과 |
|:---|:---:|
| 공식 chain/contract/event 규칙 확인 | PASS / docs |
| 공개 양단 TX·recipient·amount 후보 확인 | PASS / explorer supporting |
| composite domain 후보와 정수 fee 계산 | PASS / candidate |
| 두 RPC raw replay·SHA | NOT EXECUTED |
| negative oracle·독립 Verifier | NOT EXECUTED |
| fixture package·Schema | NOT CREATED |
| Context Receipt·구현 승인 | PENDING |
| Benchmark | `12 / 4 / 14` 유지 |

**판정: `FX-SVC-BRG-001` 공개 후보 선정 완료, fixture 승격·구현은 계속
차단한다.**

## 8. Related Documents

- [Bridge/XChain 계약 제안](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md)
- [Bridge/XChain UI 계약](../02_UI_Screens/11_TASK_016_BRIDGE_XCHAIN_UI.md)
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md)
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
- [Execution Plan Wave 5](../04_Logic_Progress/01_EXECUTION_PLAN.md)
- [Across Chains & Contracts](https://docs.across.to/chains-and-contracts)
- [Across Tracking Deposits](https://docs.across.to/introduction/tracking-deposits)
- [Across V2→V3 migration](https://docs.across.to/guides/migration/v2-to-v3)
- [Base source transaction](https://basescan.org/tx/0x95714346d20bfaa328b75e4e6cf980d9620c4c4331af935032f848a118f05a1b)
- [Ethereum destination transaction](https://etherscan.io/tx/0x816ebca944c8cf40309c8c2ec4bd0f6e25f78d782cf7732f93ca771e55b8f8a0)
