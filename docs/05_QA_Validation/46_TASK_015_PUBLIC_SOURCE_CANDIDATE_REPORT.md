# TASK-015 공개 Source·Fixture 후보 조사 보고서
> Created: 2026-07-30 03:07
> Last Updated: 2026-07-30 03:07
> Status: Candidate Research Complete · 4 Viable · 1 Source-Blocked · No Fixture Packages · Runtime Not Implemented

## 1. 목적과 경계

이 문서는 TASK-015의 다섯 proposed fixture에 사용할 공개 사례와 source의
이용조건·privacy·재배포 경계를 조사한다. 이번 단계는 **후보 선정**이며
fixture package, raw snapshot, negative oracle, 독립 Verifier, Analysis I/O
승인 또는 analyzer 구현을 포함하지 않는다.

공개 페이지에 주소가 보인다는 사실만으로 자동 수집·재배포·AI dataset
사용이 허용되는 것은 아니다. 이용조건이 허용하지 않는 source는 관찰
가능하더라도 fixture source에서 제외한다.

## 2. Source 이용조건·privacy 판정

| Source | 사용할 수 있는 범위 | 저장 최소 필드 | 판정 |
|:---|:---|:---|:---:|
| OFAC Sanctions List Service·공식 고시 | 공식 지정·해제 시점, 주소 직접 명시 여부, 목록 snapshot | locator, retrieved_at, raw SHA-256, action date, address, list version | viable |
| ENS onchain registry/resolver | 고정 block의 forward·reverse·resolver 상태와 설정 TX | chain, block, namehash/address, raw call/log, SHA-256 | viable |
| ENS 문서·ensjs | forward/reverse 검증 알고리즘과 pinned MIT 구현 provenance | 문서 locator, commit, license, hash | supporting |
| ENS 웹사이트 profile/content | Terms상 interface content 재배포·자동 이용에 제한 가능 | fixture에 원문·profile 저장 금지 | rejected for fixture content |
| Etherscan public labels | 화면 관찰은 가능하나 Terms가 public label/name tag 복제와 AI/ML·dataset 이용을 제한 | label 원문·snapshot·derived dataset 저장 금지 | rejected |
| MyEtherWallet `ethereum-lists` | MIT repository의 고정 commit·파일 hash·address entry | commit, license, file hash, matched entry | viable source candidate |
| Blockscout API | read-only onchain transaction·internal transaction 교차확인 | request scope, retrieved_at, raw SHA-256, decoded fields | supporting |
| 기존 confirmed SCAN fixture | 이미 고정된 raw replay에서 공통 funding·hub 관계 재계산 | fixture ID, evidence refs, calculated fact hash | viable |

공통 privacy 경계:

- 개인 이메일·전화번호·결제정보·session token을 수집하지 않는다.
- 주소·도메인·공식 고시처럼 문제 풀이에 필요한 공개 식별자만 보존한다.
- 웹 문서 전체를 복제하지 않고 locator·시각·hash·짧은 derived assertion만
  남긴다.
- social profile과 동일 이름은 소유권 증거로 사용하지 않는다.
- source assertion은 소유자·범죄성의 확정 사실이 아니다.

## 3. 후보 판정

| 문제 | Fixture ID | 공개 후보 | 현재 판정 | 다음 Gate |
|:---|:---|:---|:---:|:---|
| OSINT-LBL-001 | `FX-OSINT-LABEL-CONFLICT-001` | Tornado Cash 주소의 공식 OFAC 2022 지정·2025 해제와 현재 제3자 label 충돌 관찰 | source-blocked | 재사용 가능한 open-license 제2 label source 선정 |
| OSINT-SAN-001 | `FX-OSINT-SANCTIONS-HISTORY-001` | `0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc`의 OFAC 지정·해제 이력 | viable candidate | SLS snapshot·1홉 반례·현재 상태 분리 |
| OSINT-ENS-001 | `FX-OSINT-ENS-CONFLICT-001` | `nick.eth` ↔ `0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5` | viable candidate | 고정 block forward/reverse replay·불일치 반례 |
| ACTOR-REL-001 | `FX-ACTOR-COMMON-FUNDER-001` | Euler seed와 네 branch의 confirmed FLOW 관계 | viable candidate | 각 대상의 initial-inflow 범위 완전성·service exclusion |
| ACTOR-REL-002 | `FX-ACTOR-RELATION-HUB-001` | DEX·AUTH subject가 공유하는 공개 USDC token contract | viable candidate | 공용 hub false-positive·ownership `not_assessed` 고정 |

`viable candidate`는 fixture 확정이 아니다. raw snapshot·두 번 결정성·negative
oracle·독립 Verifier가 없으므로 package 생성과 `verifying` 승격은 금지한다.

## 4. 후보별 사실과 잔여

### 4.1 Label conflict — source-blocked

- 후보 주소:
  `0xd96f2B1c14Db8458374d9Aca76E26c3D18364307`
- 공식 OFAC source는 2022 지정과 2025 해제의 역사적 사실을 제공한다.
- Etherscan UI에서 stale 또는 상충 label을 관찰할 수 있으나 Etherscan
  Terms는 public label/name tag 복제와 AI/ML·dataset 이용을 제한한다.
- 따라서 Etherscan label은 fixture의 source assertion·snapshot·derived
  expected 값으로 저장하지 않는다.
- MyEtherWallet `ethereum-lists`는 MIT지만 현재 후보 주소가 light/dark
  list에 없어 conflict의 제2 assertion을 제공하지 못한다.
- 공개 재사용 가능한 제2 label source가 확보될 때까지 `source-blocked`다.

### 4.2 Sanctions history — viable

- 후보 주소:
  `0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc`
- OFAC 2022 공식 action의 주소 직접 명시와 2025 공식 removal을 서로 다른
  timeline event로 보존한다.
- 2022 designation을 현재 제재 상태로 자동 승격하지 않는다.
- 다음 단계에서 공식 SLS snapshot version·hash와 direct match를 고정하고,
  단순 1홉 상대·공용 service를 `indirect` 또는 `not_assessed`로 남기는
  반례를 추가한다.

### 4.3 ENS conflict — viable

- positive 기준 후보:
  `nick.eth` ↔ `0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5`
- ENS 공식 문서 원칙에 따라 reverse name은 forward resolution이 동일
  address로 돌아오는 경우에만 confirmed pair 후보가 된다.
- fixture 사실은 고정 block의 onchain RPC로 재계산한다. ENS 웹 profile이나
  social text는 복제하지 않는다.
- mismatch·expired·resolver 변경은 historical replay 또는 synthetic
  negative oracle로 별도 구성한다.

### 4.4 Common funder — viable

- confirmed FLOW seed:
  `0xb66cd966670d962c227b3eaba30a872dbfb995db`
- branch 대상:
  `0xa1b44d4b5b4c361f51e029b81bf2db9cf4d8e676`,
  `0xc4e04ac48639ff077ebb36e7cfe0c4993b7b208e`,
  `0x46e0be2df97dac791fc8e30cf2b2e4f58c50cf55`,
  `0x8765a35394c98e81b9d56d44248e1199d8e38a4c`
- 기존 confirmed FLOW replay는 seed의 네 출력과 금액 정합을 제공한다.
- 이것만으로 동일 소유자를 뜻하지 않는다. fixture package 전 각 대상의
  bounded history에서 initial-inflow 조건과 선행 유입 부재를 검증해야 한다.
- faucet·paymaster·service funder 반례를 negative oracle에 포함한다.

### 4.5 Relation hub — viable

- DEX subject:
  `0xa406bc6e319cbe7ab2822cc55fa8376e9c3a7fdf`
- AUTH subject:
  `0x193070aea3df0e8e0436f6ed810fd8bbe687af59`
- shared public hub:
  USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48`
- 기존 confirmed DEX·AUTH replay로 두 subject가 같은 public token contract와
  관계를 가진다는 사실을 재계산할 수 있다.
- 공용 token/router와의 공유 관계는 ownership·coordination 증거가 아니다.
  hub exclusion을 적용하고 owner relation은 `false`가 아니라
  `not_assessed`로 유지한다.

## 5. 공식 locator

| 용도 | Locator |
|:---|:---|
| OFAC 2022 action | `https://ofac.treasury.gov/recent-actions/20220808` |
| Treasury 2022 release | `https://home.treasury.gov/news/press-releases/jy0916` |
| OFAC 2025 removal | `https://ofac.treasury.gov/recent-actions/20250321` |
| Treasury 2025 release | `https://home.treasury.gov/news/press-releases/sb0057` |
| OFAC Sanctions List Service | `https://ofac.treasury.gov/sanctions-list-service` |
| Treasury privacy/site policy | `https://home.treasury.gov/subfooter/site-policies-and-notices` |
| ENS reverse verification | `https://docs.ens.domains/web/reverse/` |
| ENS resolution | `https://docs.ens.domains/resolution/` |
| ENS Terms | `https://ens.domains/legal/terms-of-use` |
| ENS privacy | `https://ens.domains/legal/privacy-policy` |
| ensjs MIT repository | `https://github.com/ensdomains/ensjs` |
| MyEtherWallet ethereum-lists MIT | `https://github.com/MyEtherWallet/ethereum-lists` |
| Etherscan rejected-source Terms | `https://etherscan.io/terms/` |
| Etherscan API Terms | `https://etherscan.io/apiterms` |
| Blockscout API | `https://docs.blockscout.com/devs/apis` |

## 6. 다음 Gate

1. label conflict용 open-license 제2 source를 찾거나 후보 ID를 교체한다.
2. viable 후보 4개에 bounded scope·raw snapshot·locator·retrieved_at·SHA-256을
   고정한다.
3. OFAC SLS version과 ENS pinned block을 고정한다.
4. common funder initial-inflow와 public-hub exclusion을 raw-first로 재계산한다.
5. negative oracle·두 번 결정성·독립 Verifier를 통과한다.
6. 다섯 package가 준비된 뒤에만 `intel_context` 계약과 Context Receipt
   승인을 요청한다.

## 7. 검증 Receipt

| 항목 | 결과 |
|:---|:---|
| 전체 test | 468 passed |
| Fixture Schema | 13 packages PASS · TASK-015 package 0 |
| Analysis Schema | 48 probes PASS · 변경 없음 |
| Traceability | 1554 links PASS |
| Security scan | 162 runtime/evidence files PASS |
| 코드·runtime | 변경 없음 |
| Benchmark | 11/11 유지 · TASK-015 전부 unsupported |

## 8. 365 글로벌 평가 기준

| 기준 | 현재 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Candidate Research | 실행 가능한 fixture·analyzer는 아직 없음 |
| Potential Impact | Planned | Label·Sanctions·ENS·Actor 5문제와 후속 CASE 재사용 |
| Novelty | Pass / Contract | source assertion과 소유·범죄 truth를 분리 |
| UX | Pass / Docs-only | conflict·timeline·hub exclusion Preview 사용자 승인 |
| Open-source | Partial | ENS/onchain·MIT source는 가능, Etherscan label은 제외 |
| Business Plan | N/A | 대회 준비 범위 |

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT·Actor 문제 범위
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 대회 API·개인정보 상태
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - source·conflict·relation 표현
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source capability·Terms 상태
- **Technical_Specs**: [TASK-015 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md) - assertion·timeline·relation 계약
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock
- **QA_Validation**: [TASK-015 Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md) - 승격 Stop/Go
