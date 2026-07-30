# TASK-015 비격리 Fixture 최종 승격 Receipt

> Created: 2026-07-30 15:01
> Last Updated: 2026-07-30 15:01
> Status: Passed · Fixture 3 Confirmed · LABEL Quarantined · Common-funder Candidate · Benchmark 11 Automated / 4 Assisted / 15 Unsupported

## 1. 목적과 판정

OpenRAIL exact license가 없어 격리된 `FX-OSINT-LABEL-CONFLICT-001`과
완전성 증거가 없는 `FX-ACTOR-COMMON-FUNDER-001`을 제외하고, 다음 세
fixture의 source permission·raw fact·claim boundary·제품 analyzer를
독립적으로 재검토한다.

- `FX-OSINT-SANCTIONS-HISTORY-001`
- `FX-OSINT-ENS-CONFLICT-001`
- `FX-ACTOR-RELATION-HUB-001`

**판정: 세 fixture는 bounded fact 범위에서 `confirmed`로 승격한다.**
다만 예상문제 원문 전체를 자동 해결하지는 못하므로 세 문제는
`automated`가 아니라 `assisted`로만 올린다.

## 2. 최종 Hard Gate

| Fixture | Source·artifact | Fact·Verifier | Claim boundary | 판정 |
|:---|:---|:---|:---|:---:|
| SANCTIONS | OFAC action URL·whole-file hash, SLS locator/hash/metadata-only | designation→removal timeline, analyzer/Verifier canonical hash 일치 | current status·criminality `not_assessed` | confirmed |
| ENS | fixed block `25,640,270`, 두 provider decoded match, content-addressed replay | forward/reverse·resolver exact, analyzer/Verifier hash 일치 | current ownership `not_assessed` | confirmed |
| RELATION-HUB | confirmed DEX/AUTH raw·expected hash | subject별 relation·USDC hub exclusion exact | ownership·coordination `not_assessed` | confirmed |

### 2.1 SANCTIONS snapshot 결합 보완

승격 재검토 중 `sls-snapshot.json`의 조회 주소가 fixture 주체와 다르다는
provenance 결합 오류를 발견했다. 공식 SLS `SDN.CSV`를 repository 밖의
임시 파일로 다시 받아 다음을 확인한 뒤 즉시 삭제했다.

| 항목 | 값 |
|:---|:---|
| byte length | `5,624,423` |
| line count | `19,175` |
| SHA-256 | `464a917d662b9de3a26588499a8f1a4cfea341a70f3ace64038a5f8cb2b85b65` |
| fixture subject match | `0` |

snapshot query와 reviewed replay에 fixture 주체 주소를 명시하고, 제품
analyzer와 독립 Verifier가 이 주소 결합을 각각 거부 테스트로 검사하도록
보강했다. 전체 CSV는 repository에 저장하지 않는다. `0건`은 최신 상태의
보조 context이며 역사적 지정·해제를 지우거나 현재 제재 상태를 확정하지
않는다.

## 3. Fixture 상태 전이

| Fixture | 이전 | 현재 | 확정 범위 |
|:---|:---:|:---:|:---|
| `FX-OSINT-SANCTIONS-HISTORY-001` | verifying 0.1 | **confirmed 0.1** | 주소를 직접 명시한 2022 지정·2025 해제 timeline |
| `FX-OSINT-ENS-CONFLICT-001` | verifying 0.1 | **confirmed 0.1** | 고정 block의 ENS forward/reverse·resolver |
| `FX-ACTOR-RELATION-HUB-001` | verifying 0.1 | **confirmed 0.1** | DEX/AUTH 두 주체의 별도 USDC interaction과 public-hub exclusion |

`confirmed`는 source가 주장한 bounded fact의 재현 가능성을 뜻한다.
법적 소유, 범죄성, 제재의 현재 효력, 동일 주체·공모를 확정하지 않는다.

## 4. Benchmark 판정

세 confirmed fixture가 생겼다는 이유만으로 문제 원문 전체를 자동화하지
않는다.

| 문제 | 이전 | 현재 | 남은 전체 문제 공백 |
|:---|:---:|:---:|:---|
| `OSINT-SAN-001` | unsupported | **assisted** | 1홉 상대방 확장·직접/간접 일괄 대조 |
| `OSINT-ENS-001` | unsupported | **assisted** | 도메인·DNS·SNS·사칭/만료 확인 |
| `ACTOR-REL-002` | unsupported | **assisted** | 복수 positive heuristic의 후보 생성·점수·오탐 제거 |

갱신 집계:

| 항목 | 결과 |
|:---|---:|
| 전체 예상문제 | 30 |
| Automated | 11 |
| Assisted | 4 |
| Unsupported | 15 |
| 자동 실행·통과 | 11 / 11 |
| Automated 범위 정확도 | 100% |
| 30문항 직접 자동화율 | 36.7% |

## 5. 검증과 변경 영향

- Analysis I/O 0.2와 공개 오류 코드에는 변화가 없다.
- SANCTIONS source replay에 snapshot 주체 주소를 추가하고 두 독립 경로에서
  request/fixture와 결합한다.
- Benchmark automated 집합과 실행 dispatcher는 바꾸지 않는다.
- LABEL은 `verifying`·quarantined, common-funder는 `candidate`·`partial`로
  유지한다.
- live AI·CTFd·자동 제출은 호출하거나 구현하지 않았다.

최종 `scripts/verify.py`는 **537 tests**, fixture **18**, Analysis Schema
**52 probes**, traceability **1,710 links**, security **205 files**를 통과했다.
TASK-015 negative oracle 30×2, 독립 Verifier 4×2, analyzer 독립 검증 4개와
common-funder partial도 모두 통과했다.

## 6. 365 글로벌 평가 기준

| 기준 | 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Pass / Bounded | 세 source fact를 analyzer·Verifier·반례로 재현 |
| Potential Impact | Partial | OSINT·Actor 조사 primitive 3개 확보, 전체 문제는 assisted |
| Novelty | Pass | source permission·fact correctness·claim boundary를 별도 Gate로 판정 |
| UX | Pass / Existing | 승인된 Intelligence UI의 `not_assessed`·conflict 표현 유지 |
| Open-source | Pass / Bounded | 공개 locator·hash·고정 block·local confirmed fixture 사용 |
| Business Plan | N/A | 대회 준비용 QA·승격 판단 |

## 7. 독창성·윤리 경계

- source assertion은 법적 소유·범죄·공모 사실이 아니다.
- AI·heuristic candidate는 evidence 없는 `confirmed_fact`가 될 수 없다.
- current list 부재를 역사적 기록 삭제나 무혐의 판정으로 사용하지 않는다.
- 공개 hub 상호작용만으로 주소를 동일 주체로 합치지 않는다.
- full OFAC CSV와 격리된 OpenRAIL selected row를 재배포하지 않는다.

## 8. 다음 작업

1. LABEL은 exact terms 확보 또는 명확한 license source 교체 후 별도
   Promotion Review에 다시 진입한다.
2. common-funder는 bounded prehistory·service exclusion을 닫기 전까지
   `candidate`·`partial`을 유지한다.
3. TASK-016은 별도 docs-only Gate와 fixture 승인 후 착수한다.

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT/Actor 전체 문제 완료 조건
- **Technical_Specs**: [intel_context I/O 계약](../03_Technical_Specs/18_TASK_015_INTEL_CONTEXT_IO_CONTRACT.md) - bounded request/result·claim 경계
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-015 상태·잔여
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 4 승격 순서
- **QA_Validation**: [Promotion Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) - permission·live 선택·Hard Gate
- **QA_Validation**: [OpenRAIL Resolution](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md) - LABEL quarantine 근거
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 상태 등록부
- **QA_Validation**: [Offline Benchmark](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 30문항 coverage 집계
- **External**: [OFAC Sanctions List Service](https://ofac.treasury.gov/other-ofac-sanctions-lists) - 공식 list data 제공
- **External**: [ENS Primary Names](https://docs.ens.domains/web/reverse/) - reverse 결과의 forward 재검증 원칙
