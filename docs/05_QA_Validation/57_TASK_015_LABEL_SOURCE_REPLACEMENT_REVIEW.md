# TASK-015 LABEL Source Replacement Review
> Created: 2026-07-30 15:37
> Last Updated: 2026-07-30 15:37
> Status: Proposed · Replacement Route Selected · Fixture Migration Not Executed

## 1. 목적과 판정

`FX-OSINT-LABEL-CONFLICT-001`의 OpenRAIL selected row를 제거할 수 있는
대체 source를 조사한다. 대체 source는 다음 조건을 동시에 만족해야 한다.

- 같은 주소에 대한 source-scoped assertion을 고정할 수 있다.
- 원문 locator·pin·사용 경계를 재현할 수 있다.
- Etherscan label 원문이나 불명확한 dataset license를 우회 복제하지 않는다.
- category·role·onchain binding을 하나의 ownership·criminality truth로
  자동 병합하지 않는다.

**판정: 기존 subject를 유지한 제3자 mixer list 교체는 채택하지 않는다.**
대신 이미 confirmed인 공식 OFAC action fact와 MIT community config를
재사용하는 subject 교체안을 선택한다.

선택 subject는
`0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc`다.

- 공식 OFAC 2022 action은 해당 주소를 당시 `TORNADO CASH` entity의
  digital currency address로 열거한다.
- pinned MIT community config는 `eth-01.tornadocash.eth` name과 `0.1 ETH`
  instance address를 각각 포함한다. 둘의 결합은 새 ENS replay로 검증한다.
- 새 fixed-block ENS replay는 name → address binding만 확인해야 한다.

이는 역사적 제재 assertion과 protocol instance role을 분리하는
`category_role_conflict`다. 현재 제재 상태·소유권·범죄성은 계속
`not_assessed`다.

## 2. 후보 대조

| 후보 | 명시 license | 원천 provenance | 판정 | 이유 |
|:---|:---|:---|:---:|:---|
| Codatta selected row | `openrail` family만 표시 | publisher dataset | BLOCK | exact text·version·notice 부재 |
| Haas Labs `mixers.list` | Apache-2.0 repository | file 자체의 upstream 미기재 | HOLD | 대상 주소는 있으나 source assertion의 원천을 독립적으로 설명할 수 없음 |
| GraphSense Etherscan wordcloud tagpack | MIT repository | `source: etherscan.io/accounts/label/mixing_service` 명시 | REJECT | Etherscan label 복제를 대체 source로 우회할 수 없음 |
| brianleect Etherscan labels | MIT repository | Etherscan-derived path·dataset | REJECT | repository license가 upstream Terms 경계를 제거하지 않음 |
| OFAC action + MIT config + fixed-block ENS | official locator + MIT config + onchain raw | source별 독립 locator | SELECT | 재배포 범위를 bounded fact·hash·locator로 제한할 수 있음 |

명시적 repository license가 있어도 upstream data provenance가 불명확하거나
Etherscan 파생임이 명시된 경우 채택하지 않는다. 이는 license laundering을
피하기 위한 보수적 판단이다.

## 3. 선택 source와 고정 기준

### 3.1 Official historical action

| 필드 | 값 |
|:---|:---|
| Source ID | `DS-SANCTIONS-PUBLIC` |
| Locator | `https://ofac.treasury.gov/recent-actions/20220808` |
| Subject | `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc` |
| 허용 assertion | 2022-08-08 action에 열거된 historical designation address |
| 금지 assertion | 현재 제재 상태·소유권·범죄성 |
| 저장 방식 | confirmed SANCTIONS fixture의 bounded fact·locator·hash 재사용 |

OFAC 원문이나 full SLS CSV를 LABEL package에 다시 복제하지 않는다.
[confirmed SANCTIONS fixture](./fixtures/FX-OSINT-SANCTIONS-HISTORY-001/README.md)의
content-addressed provenance를 참조한다.

### 3.2 Pinned community config

| 필드 | 값 |
|:---|:---|
| Source ID | `DS-OSINT-WEB` |
| Repository | `tornadocash-community/torn-token` |
| Commit | `4dea68f71633dab37e3cb4c8b4d8dca3479891c6` |
| License | MIT |
| Config fact | rate table의 `eth-01.tornadocash.eth`; ETH `0.1` instance address |
| Address | `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc` |

현재 pinned `config.js` artifact는 이미 content hash와 MIT provenance를
검증했다. replacement migration에서는 subject-scoped projection과
Verifier fact만 새 주소에 맞춰 재계산한다.

### 3.3 Fixed-block ENS

새 ENS replay는 아직 실행하지 않았다. migration Gate에서 다음을 고정한다.

- name: `eth-01.tornadocash.eth`
- fixed block: replay 실행 전 명시
- provider 2개 또는 provider + 저장 artifact 독립 재현
- decoded address:
  `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc`
- 실패·429·timeout은 일치로 추론하지 않음

## 4. Fixture migration 범위

이번 Review에서는 fixture JSON·artifact·analyzer·Verifier를 변경하지 않는다.
후속 migration은 다음 원자 단위로 수행한다.

1. [ ] 새 subject와 세 source assertion을 `input.json`·`expected.json`에 반영한다.
2. [ ] OpenRAIL selected row artifact와 scoring reference를 새 package에서 제거한다.
3. [ ] confirmed SANCTIONS fixture provenance를 hash로 연결한다.
4. [ ] pinned MIT config에서 instance name·address를 raw-first로 재계산한다.
5. [ ] fixed-block ENS를 독립 재현하고 raw SHA-256을 고정한다.
6. [ ] negative oracle의 subject·historical/current·role conflict 경계를 갱신한다.
7. [ ] 독립 Verifier와 analyzer canonical hash를 다시 계산한다.
8. [ ] fixture를 `verifying`으로 유지한 채 Promotion Review를 요청한다.
9. [ ] 기존 OpenRAIL artifact 삭제는 별도 승인과 history 보존 정책에 따른다.

## 5. 승격·실패 조건

### 승격 검토 진입

- 새 subject의 OFAC action fact가 official locator와 일치한다.
- config address·instance role과 fixed-block ENS decoded address가 일치한다.
- OpenRAIL selected row가 scoring·provenance dependency에서 제거된다.
- analyzer·독립 Verifier canonical hash가 두 번 결정적으로 일치한다.
- current sanctions status는 이 query에서 평가하지 않고 ownership·criminality는
  `not_assessed`를 유지한다.

### 실패·중단

| 조건 | 처리 |
|:---|:---|
| ENS name이 선택 block에서 다른 주소로 resolve | `reconciliation_failed` |
| historical designation을 current status로 승격 | `evidence_incomplete` |
| official action과 community role을 하나의 ownership fact로 병합 | `evidence_incomplete` |
| upstream 불명 Etherscan 파생 list를 대체 source로 채택 | source 교체 중단 |
| artifact·analyzer·Verifier hash 불일치 | `verifying` 유지 |

## 6. 현재 변경 경계

- 제품 analyzer·공개 Schema·Benchmark 변경: 0
- live RPC/API 호출: 0
- fixture status 변경: 0 (`LABEL verifying` 유지)
- OpenRAIL artifact 삭제: 0
- TASK-016 착수: 0
- `scripts/verify.py`: 537 tests, fixture 18, Analysis I/O 52 probes,
  traceability 1,728 links, security 205 files PASS

## 7. 365 글로벌 평가 기준

| 기준 | 상태 | 근거 |
|:---|:---:|:---|
| Functionality | Partial | replacement route를 선택했지만 fixture migration은 미실행 |
| Potential Impact | Pass | 불명확 label license와 false attribution 위험을 함께 제거 |
| Novelty | Pass | repository license와 upstream data provenance를 별도 Gate로 판정 |
| UX | Pass / Existing | source별 assertion·conflict·`not_assessed` 표시 계약 유지 |
| Open-source | Pass / Planned | official locator·MIT config·onchain raw로 재현 가능한 경로 선택 |
| Business Plan | N/A | 대회 준비용 source·fixture QA |

## 8. Originality & Ethics Check

- repository license로 upstream data 권한을 세탁하지 않는다.
- 역사적 제재 주소라는 사실을 현재 범죄성·소유권으로 확대하지 않는다.
- community role과 official action은 source별 assertion으로 보존한다.
- 대체가 완료되기 전 기존 fixture를 `confirmed`로 표시하지 않는다.

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT-LBL-001 완료·부분·실패 경계
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - source conflict·not_assessed 표현
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - label·sanctions·ENS source 정책
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) · [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md)
- **QA_Validation**: [OpenRAIL Resolution](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md) · [Promotion Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) · [비격리 Promotion Receipt](./56_TASK_015_NON_QUARANTINED_PROMOTION_RECEIPT.md)
- **Fixture**: [LABEL conflict fixture](./fixtures/FX-OSINT-LABEL-CONFLICT-001/README.md) · [confirmed SANCTIONS fixture](./fixtures/FX-OSINT-SANCTIONS-HISTORY-001/README.md)
- **External**: [OFAC 2022 action](https://ofac.treasury.gov/recent-actions/20220808) · [Haas Labs Apache-2.0 candidate file](https://github.com/haas-labs/ext-sentinel-py-sdk/blob/2a68b314fec45d234c6157c92c9f539af546a331/examples/block_tx/data/mixers.list) · [GraphSense Etherscan-derived tagpack](https://github.com/graphsense/graphsense-tagpacks/blob/921ae2ba98fe9f4050f46c80583cd4b98ced1042/packs/etherscan-wordcloud-mixing_service.yaml)
