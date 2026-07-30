# TASK-016 CEX Cluster 공개 Fixture 후보 선정 보고서
> Created: 2026-07-31 05:14
> Last Updated: 2026-07-31 06:20
> Status: Selected · FX-SVC-CEX-001 confirmed

## 1. 목적

사용자 batch approval(2026-07-31)에 따라 `SVC-CEX-001`용 `FX-SVC-CEX-001`의
공개 후보를 선정한다. 이 단계는 first-party/gov 라벨 출처와 공개 온체인
이동에서 한 건의 다주소 집금 패턴을 식별하고, 후속 raw replay가 검증할 값을
고정하는 docs-only Gate다.

이 보고서는 다음을 주장하지 않는다.

- 거래소 소유·본인성·불법성 판정
- Etherscan community tag를 label truth 또는 scoring source로 사용

후속 Gate에서 fixture package·PRIMARY/VERIFY raw replay·negative oracle·독립
Verifier·제품 analyzer·Benchmark automated 승격은
[68 Final Promotion Receipt](./68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md)에서
판정했다.

## 2. 선택 결과

| 필드 | 값 |
|:---|:---|
| Fixture | `FX-SVC-CEX-001` |
| 문제 | `SVC-CEX-001` |
| Chain | Ethereum mainnet (`chain_id` 1) |
| `deposit_candidates[]` | `0x8dce2aac0de82bdcaf6b4373b79f94331b8e4995`, `0xb338962b92cd818d6aef0a32a9ecd01212a71f33`, `0xf4377eda661e04b6dda78969796ed31658d602d4` |
| `observation_window` | blocks `18215900`–`18216000` |
| Common destination (hot wallet candidate) | `0xdbaef73d20b0ca4abc72e8daf97af36626e3b973` |
| Outbound TX (native ETH sweeps) | `0x4448b91c3473144d93c90d83c3499ed047fceb4b81349f2a4b0f5e162e8ee2ea` (block 18215917), `0x60afb23f8e0bcd2374e3c489df92f6725394b0cd1674ce3d99e614193c67306e` (block 18215920), `0xeeee1c9b6df17404ac03575b4cba55535c765ed1870c343e189b6098faaa4d5a` (block 18215925) |
| Label assertion source | US Treasury OFAC SDN public XML — entity `GARANTEX` |
| 상태 | **selected** → `confirmed 0.1` ([68 Receipt](./68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md)) |

핫월렛 후보 `0xdbaef73d…`는 pattern-derived candidate이며 SDN 미등재.
ownership·criminality는 `not_assessed`다.

## 3. 후보 선정 기준

### 3.1 온체인 (confirmed fact)

- `deposit_candidates[]` 내 **2개 이상** 주소가 bounded window 안에서 **동일
  destination**으로 outbound Transfer를 수행할 것.
- Transfer는 ERC-20 또는 native value leg로 재현 가능할 것.
- 단일 공통 counterparty만 존재하고 반복·다주소 패턴이 없는 사례는 **제외**
  (negative oracle 2번과 충돌).
- 공용 router·multicall·known shared hub만 destination인 사례는 우선 **제외**
  또는 `false_positive_exclusion` 문서화 대상.

### 3.2 라벨 (evidence-backed assertion)

- 거래소·서비스 식별 claim의 출처는 **first-party disclosure**(공식 고객센터·
  입금 안내·공식 GitHub/문서) 또는 **government public domain**(규제 공시·
  수사 공개 자료 등)만 허용.
- **Etherscan community tag·익명 3rd-party label DB는 scoring source 금지.**
  탐색기 화면은 supporting reference(후보 발견)로만 쓰고 assertion truth로
  승격하지 않는다.
- assertion에는 출처 URL·조회 시점·원본 조회 키(주소·문서 ID)를 pin할 것.

### 3.3 패턴·오탐 배제

- 입금주소 재사용·집금 주기·창 내 반복 횟수를 pattern_evidence로 기록할 것.
- 무관 허브·공용 서비스 오탐 배제 사유를 `false_positive_exclusions[]`에
  대응할 수 있을 것.
- `cluster_judgment=confirmed`에 필요한 label + destination + 패턴 교차검증이
  가능할 것.

### 3.4 재현·Rules

- 두 독립 RPC provider(`PRIMARY`/`VERIFY`, distinct endpoints)에서 outbound
  TX·receipt·block replay가 일치할 것. transfer index별 label은 provider가
  아니다. `cross_provider_decoded_match` boolean 선언만으로 confirmed를
  허용하지 않으며, 각 transfer의 immutable decoded facts를 비교해야 한다.
- Explorer Terms·대회 Rules 확정 전 자동 수집·재배포·live adapter 채택을
  주장하지 않는다.

## 4. 제외 기준

| 제외 사유 | 설명 |
|:---|:---|
| Etherscan tag only | community tag만으로 거래소 단정 불가 |
| Single counterparty | D→H 1회성 공통 destination만 존재 |
| Shared hub | 다 tenant 공용 contract/router destination |
| Label source unknown | first-party/gov 출처 미확인 |
| Window ambiguity | observation_window 경계 불명확 |
| Cross-chain mix | 단일 체인 fixture 범위 위반 |

## 5. Source 역할과 이용 경계

| Source | 역할 | 현재 사용 |
|:---|:---|:---|
| US Treasury OFAC SDN XML | gov label assertion | GARANTEX entity·deposit address pin |
| Etherscan TX page | supporting explorer | outbound TX 후보 발견 |
| Etherscan "Name Tag" (community) | **금지** | scoring·assertion source 아님 |
| Anonymous label DB | **금지** | scoring·assertion source 아님 |

공식 문서 URL과 탐색기 URL만 기록한다. 페이지 본문을 fixture에 복제하지
않는다.

## 6. 다음 Gate

1. ~~위 기준으로 1~3건 공개 후보를 좁히고 first-party/gov label 출처를 pin한다.~~ **완료**
2. ~~`deposit_candidates[]`·window·common destination TX 목록을 docs-only로 고정한다.~~ **완료**
3. ~~두 RPC raw replay·SHA·negative oracle 10개·독립 Verifier Gate를 수행한다.~~ **완료** — PRIMARY publicnode 9건·VERIFY merkle 9건·negative oracle 8개·기계적 dual-provider guards.
4. ~~`candidate → verifying → confirmed`와 Benchmark automated 승격을 별도 판정한다.~~ **완료** — [68 Receipt](./68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md)

## 7. Blocker

- ~~구체 공개 사례·주소·TX 미확정(TBD).~~ **해소**
- ~~first-party/gov 라벨 출처 pin 미완.~~ **해소** — OFAC SDN public domain
- ~~VERIFY second-provider replay incomplete~~ **해소** — `https://eth.merkle.io` 9건 완료·immutable fact match. 1RPC incomplete·Cloudflare historical-block 실패는 capture-meta에만 요약.
- live Rules·Explorer Terms 미확정 — live adapter blocker로 유지
- Etherscan tag를 label source로 쓸 수 없음 — 정책 유지

## 8. Related Documents

- **Technical_Specs**: [CEX Cluster 계약](../03_Technical_Specs/22_TASK_016_CEX_CLUSTER_CONTRACT_PROPOSAL.md) - 정답·판정 경계
- **Concept_Design**: [예상문제 은행 SVC-CEX-001](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제 정의
- **Technical_Specs**: [WP-SERVICE 공통 계약](../03_Technical_Specs/20_TASK_016_SERVICE_COMMON_CONTRACT.md) - CEX label=assertion
- **QA_Validation**: [CEX Final Promotion Receipt](./68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md) - confirmed·Benchmark 14/14
- **QA_Validation**: [Bridge 후보 보고서](./61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md) - docs-only 후보 Gate 선례
- **QA_Validation**: [Contest Stabilization Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md) - freeze·CEX confirmed
- **Logic_Progress**: [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
