# TASK-015 Source 교체·Raw Snapshot 기준선 보고서
> Created: 2026-07-30 03:27
> Last Updated: 2026-07-30 03:37
> Status: Source Blocker Resolved · 5 Viable Candidates · Snapshot Basis Recorded · No Fixture Packages · Runtime Not Implemented

## 1. 목적과 경계

이 문서는 `FX-OSINT-LABEL-CONFLICT-001`의 금지 source를 교체하고,
TASK-015 다섯 후보의 bounded raw snapshot locator·고정 버전·SHA-256
기준선을 기록한다.

이번 단계에서 한 일:

- Etherscan label을 전혀 사용하지 않는 replacement 사례 선정
- remote source의 pinned commit 또는 조회 snapshot hash 기록
- 기존 confirmed fixture를 재사용하는 Actor 후보의 local artifact hash 기록
- ENS 두 후보를 고정 block에서 raw `eth_call`로 재현

이번 단계에서 하지 않은 일:

- fixture package 생성·`candidate` 또는 `verifying` 승격
- negative oracle·독립 Verifier
- `intel_context` Analysis I/O 확정·Context Receipt 전환
- 제품 analyzer·Benchmark 승격

## 2. Label conflict 교체 판정

### 2.1 교체 전

기존 주소 `0xd96f...4307`은 공식 OFAC timeline은 있었지만, 충돌 label을
Etherscan Terms 때문에 fixture/AI dataset source로 사용할 수 없었다.
따라서 해당 조합은 폐기한다. Etherscan snapshot·label·derived expected
값은 저장하지 않는다.

### 2.2 교체 후

새 subject:

`0xc3877028655ebe90b9447dd33de391c955ead267`

| Source assertion | 역할 | 판정 |
|:---|:---|:---|
| Humanbased-AI/Codatta 10K sample row: entity `Tornado.Cash`, category `Mixer;Sanctioned`, source `external` | public dataset assertion | assertion only |
| Tornado community `torn-token` MIT config: `team4.vesting.contract.tornadocash.eth` | first-party-style pinned config | role assertion |
| Ethereum ENS at block 25,640,270: 위 name → subject address | onchain binding | confirmed observation |

이 fixture의 정답은 어느 label이 “진짜 소유자·범죄 사실”이라고 고르는 것이
아니다. source별 assertion·역할·시점·provenance를 보존하고
`Mixer;Sanctioned`와 `team4 vesting`의 category conflict를 자동 병합하지
않는 것이다.

OpenRAIL sample은 dataset card가 허용한 research/testing 범위에서만 사용한다.
상업·전체 dataset 사용 권한으로 확대 해석하지 않는다. fixture에는 전체 CSV가
아니라 pinned locator·전체 file hash·선택 row·row hash만 둘 계획이다.

## 3. Raw snapshot 기준선

### 3.1 Label conflict

| Artifact | Locator / version | SHA-256 |
|:---|:---|:---|
| 10K CSV | `Humanbased-AI/Crypto-Address-Annotation-10K`, commit `865b4b7ca276ffa50255f5fa751227b3c666dbf1`, `Crypto-Address-Annotation-10K.csv` | `7732e18f0534dd8825f17f7408f8fe3c0538787d7a6fe9abb0448bbb80f772c2` |
| 선택 CSV row | 위 CSV의 subject address 단일 row | `15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475` |
| dataset card | 위 commit `README.md` | `426c2409b607ca540627f2ef10f65c268026287117f7fa0d7b6c5966f919f0fe` |
| Tornado config | `tornadocash-community/torn-token`, commit `4dea68f71633dab37e3cb4c8b4d8dca3479891c6`, `config.js` | `84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32` |
| Tornado LICENSE | 위 commit `LICENSE` · MIT | `d74f0c66499a60013b9ab537c6a30479f47783187a9a785a56caea4f5593868f` |
| ENS raw probe | Ethereum block `25,640,270`, Alchemy logical provider, resolver+addr raw results | `762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b` |

ENS probe는 같은 고정 block에서 두 번 같은 hash를 냈다. QuickNode는 HTTP
429로 이 단계의 독립 재현에 사용하지 못했으므로 package 승격 전 제2 provider
또는 저장 artifact 재현이 남아 있다.

### 3.2 Sanctions history

Subject:

`0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc`

| Artifact | Locator | SHA-256 / match |
|:---|:---|:---|
| 2022 designation HTML | `https://ofac.treasury.gov/recent-actions/20220808` | `a6160e2d63d9c13ac8ca60778b48c778e94dc84e10b6ef4cacadd337f34df74c`, address 1 match |
| 2025 removal HTML | `https://ofac.treasury.gov/recent-actions/20250321` | `630ff0e4efa827bb95fd4d00e2ecd0072daff56e966f9fa3536dcd07b4ead465`, address 1 match |

두 action은 역사적 timeline이다. 2022 match를 현재 제재 상태로 자동
승격하지 않는다. package 전 OFAC SLS 목록 version과 direct/indirect 반례를
추가한다.

### 3.3 ENS forward/reverse

| 항목 | 값 |
|:---|:---|
| name | `nick.eth` |
| address | `0xb8c2c29ee19d8307cb7255e1cd9cbde883a267d5` |
| block | `25,640,270` (`0x1873d4e`) |
| forward node | `0x05a67c0ee82964c4f7394cdd47fee7f4d9503a23c09c38341779ea012afe6e00` |
| forward resolver | `0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41` |
| reverse node | `0xe78fb51f6a12a1a1675dd4dc3cbae52b360fd1b58a4725fd03abff93586071d1` |
| reverse resolver | `0xa2c122be93b0074270ebee7f6b7292c7deb45047` |
| decoded result | forward address와 reverse name 모두 일치 |
| raw probe SHA-256 | `a1ed2bfc3bb65b0717afeb979fc92b68658f2ee9391f458a67ad2c5ef246ce2c` |

같은 고정 block에서 두 번 같은 hash를 확인했다. QuickNode HTTP 429 때문에
현재는 Alchemy logical provider 단일 snapshot이다. mismatch·expired
negative oracle과 제2 provider replay가 남아 있다.

### 3.4 Common funder

기존 confirmed `FX-FLOW-REMERGE-001`을 raw source로 재사용한다.

| Local artifact | SHA-256 |
|:---|:---|
| `fixtures/FX-FLOW-REMERGE-001/raw-replay.json` | `16ff54e8a12245d3d23a6c8954604db6c1ce371558a47645c8f58307be526ab5` |
| `fixtures/FX-FLOW-REMERGE-001/expected.json` | `627c47ffb39dcb8c5179883a8c84c1ac92fca14ef08cf23dd5cfbfd804437cad` |

이 snapshot은 seed의 네 branch 출력을 입증하지만, 각 branch 주소의
bounded history에서 “초기 유입”이었는지는 아직 입증하지 않는다. common
funder package 전 선행 inbound·faucet·paymaster 반례가 필요하다.

### 3.5 Public relation hub

기존 confirmed DEX·AUTH replay에서 두 subject가 공용 USDC contract와
관계를 가진 사실을 재계산한다.

| Local artifact | SHA-256 |
|:---|:---|
| `fixtures/FX-SVC-DEX-001/raw-replay.json` | `ff0924acb52db56c2a907d709f83c13b2ecdd5d5a17cae09da70e0aab422733c` |
| `fixtures/FX-SVC-DEX-001/expected.json` | `495b5fddafbf41f627f4d01a7e249304cf2303fcfd7f52fcbd33c251dd9d7dc9` |
| `fixtures/FX-EVM-AUTH-001/raw-replay.json` | `75f07f30863d958146f85052642be07b6d6478194672408f9b473b21ff554dd6` |
| `fixtures/FX-EVM-AUTH-001/expected.json` | `9e8966209171a0c9590eb69d8e1499c59d403253a58c8de7f2bfaaedfb08c716` |

공용 token contract 공유는 owner relation이 아니다. 이 candidate의 핵심은
hub exclusion 후 ownership을 `not_assessed`로 유지하는 것이다.

## 4. 후보 상태

| Fixture ID | 현재 판정 | Snapshot 상태 | 남은 하드 Gate |
|:---|:---:|:---:|:---|
| `FX-OSINT-LABEL-CONFLICT-001` | viable replacement | pinned dataset/config + single-provider ENS | selected row artifact·제2 ENS replay·conflict oracle |
| `FX-OSINT-SANCTIONS-HISTORY-001` | viable | official HTML hashes | SLS version·direct/indirect oracle |
| `FX-OSINT-ENS-CONFLICT-001` | viable | single-provider fixed-block raw | 제2 provider·mismatch/expired oracle |
| `FX-ACTOR-COMMON-FUNDER-001` | viable | confirmed FLOW artifacts | initial-inflow completeness·service exclusion |
| `FX-ACTOR-RELATION-HUB-001` | viable | confirmed DEX/AUTH artifacts | component scoring·hub false-positive oracle |

다섯 후보는 모두 viable이지만 fixture package는 아직 0개다. 이 보고서의
`Snapshot 상태`는 source 입력 기준선이지 Schema 검증·독립 Verifier 통과를
뜻하지 않는다.

## 5. Source 보안·privacy

- endpoint·credential은 기록하지 않고 logical provider ID만 사용했다.
- 공개 주소·ENS name·공식 action처럼 문제 풀이에 필요한 식별자만 기록했다.
- 전체 Codatta CSV·OFAC HTML은 repository에 복제하지 않는다.
- 개인 연락처·social profile·session·검색 계정 정보는 수집하지 않았다.
- Etherscan label은 교체안에도 포함하지 않았다.
- OpenRAIL sample은 research/testing 범위를 벗어나 사용하지 않는다.

## 6. 다음 Gate

1. 다섯 fixture candidate package의 `input/expected/evidence` 골격을 만든다.
2. remote raw는 content-addressed local artifact 또는 selected row로 고정한다.
3. ENS 두 사례를 제2 provider 또는 재현 가능한 저장 artifact로 대조한다.
4. Sanctions direct/indirect·ENS mismatch·common funder service·public hub
   negative oracle을 작성한다.
5. 두 번 결정성·독립 Verifier 후에만 `verifying` 승격을 검토한다.
6. 그 이후 `intel_context` 계약·Context Receipt·구현 승인으로 이동한다.

## 7. Verification Receipt

2026-07-30 03:37 KST 기준 `scripts/verify.py` 전체 Gate:

- 468 tests PASS
- fixture Schema 0.1: 13 packages PASS
- Analysis I/O 0.2: 48 semantic probes PASS, 0.1 compatible
- repository traceability: 1,569 links PASS
- repository security scan: 162 runtime/evidence files PASS
- TASK-012~014 oracle·독립 Verifier·analyzer verification PASS

이번 검증은 문서 정합성과 기존 회귀 Gate를 확인한다. TASK-015 package,
negative oracle, 독립 Verifier 또는 runtime을 실행했다는 뜻은 아니다.

## 8. 365 글로벌 평가 기준

| 기준 | 현재 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Snapshot Basis | 다섯 후보의 재현 입력·hash 기준, analyzer 없음 |
| Potential Impact | Planned | LABEL·SAN·ENS·Actor 5문제와 CASE 재사용 |
| Novelty | Pass / Contract | 상충 label을 자동 truth로 병합하지 않음 |
| UX | Pass / Docs-only | conflict·timeline·hub exclusion Preview 승인 |
| Open-source | Partial | MIT·OpenRAIL research source와 onchain 재현, package 미작성 |
| Business Plan | N/A | 대회 준비 범위 |

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT·Actor 정답 범위
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - conflict·timeline·relation 표현
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source role·Terms 상태
- **Technical_Specs**: [TASK-015 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md) - source assertion 계약
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock
- **QA_Validation**: [공개 Source 후보 조사](./46_TASK_015_PUBLIC_SOURCE_CANDIDATE_REPORT.md) - 교체 전 4 viable·1 blocked 기준선
- **QA_Validation**: [TASK-015 Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md) - 다음 승격 Gate

## 10. External Provenance

- **Dataset**: [Humanbased-AI/Crypto-Address-Annotation-10K](https://huggingface.co/datasets/Humanbased-AI/Crypto-Address-Annotation-10K) - pinned research/testing sample
- **Community config**: [tornadocash-community/torn-token](https://github.com/tornadocash-community/torn-token) - pinned MIT repository
- **OFAC**: [2022 designation](https://ofac.treasury.gov/recent-actions/20220808) · [2025 removal](https://ofac.treasury.gov/recent-actions/20250321) - official historical actions
- **ENS**: [Primary-name reverse resolution](https://docs.ens.domains/web/reverse/) - forward/reverse interpretation reference
