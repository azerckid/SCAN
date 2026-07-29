# TASK-015 Candidate Fixture Package 보고서
> Created: 2026-07-30 03:47
> Last Updated: 2026-07-30 04:00
> Status: Candidate Packages 5 · Schema / Oracle PASS · Verifier Pending · Runtime Not Implemented

## 1. 목적과 경계

이 문서는 TASK-015 다섯 문제의 `input.json`, `expected.json`,
`evidence.json`, `README.md` package를 `candidate` 상태로 고정하고,
selected artifact·source hash·잔여 승격 Gate를 기록한다.

이번 단계에서 한 일:

- 5개 package × 공통 4파일 작성
- label 선택 CSV 행과 ENS fixed-block raw replay를 content-addressed artifact로 저장
- OFAC 원문 전체를 복제하지 않고 공식 URL·whole-file hash·주소 match만 보존
- Actor 두 후보는 기존 confirmed fixture raw/expected SHA-256을 참조
- fixture validator가 `artifacts/sha256/<digest>.*` 파일명을 실제 bytes와 대조

이번 단계에서 하지 않은 일:

- TASK-015 독립 Verifier
- `candidate` → `verifying` 또는 `confirmed` 승격
- `intel_context` Analysis I/O 승인·Context Receipt 전환
- 제품 analyzer·Benchmark 자동화 승격

## 2. Package 판정

| Fixture ID | 문제 | 상태 | 현재 고정 근거 | 잔여 핵심 Gate |
|:---|:---|:---:|:---|:---|
| `FX-OSINT-LABEL-CONFLICT-001` | OSINT-LBL-001 | candidate | selected row·MIT config·ENS raw·oracle | ENS 제2 replay·Verifier |
| `FX-OSINT-SANCTIONS-HISTORY-001` | OSINT-SAN-001 | candidate | OFAC 2022/2025 URL·HTML SHA·주소 match·oracle | SLS version·Verifier |
| `FX-OSINT-ENS-CONFLICT-001` | OSINT-ENS-001 | candidate | fixed-block forward/reverse raw·oracle | 제2 provider·Verifier |
| `FX-ACTOR-COMMON-FUNDER-001` | ACTOR-REL-001 | candidate | confirmed FLOW raw/expected SHA | prehistory·service exclusion |
| `FX-ACTOR-RELATION-HUB-001` | ACTOR-REL-002 | candidate | confirmed DEX/AUTH raw/expected SHA·oracle | 독립 Verifier |

다섯 package의 expected 값은 정답 계약 초안이다. negative oracle은
통과했지만 독립 Verifier가 source/raw facts를 재계산하기 전에는 검증된
정답 또는 자동화 coverage로 세지 않는다.

## 3. Content-addressed Artifact

| Package | Artifact | SHA-256 판정 |
|:---|:---|:---:|
| Label conflict | 선택 CSV row | filename = actual bytes PASS |
| Label conflict | team4 ENS raw replay | filename = actual bytes PASS |
| ENS conflict | `nick.eth` forward/reverse raw replay | filename = actual bytes PASS |

OpenRAIL sample은 research/testing 범위에서 선택 행 하나만 저장한다. 전체
dataset은 repository에 넣지 않는다. ENS artifact에는 endpoint·credential이
없고 logical provider ID와 fixed-block raw result만 있다.

OFAC HTML은 약관·재배포 최소화 때문에 repository에 복제하지 않는다. 두
공식 URL, whole-file SHA-256, 주소 match count가 evidence에 남아 있으며
SLS version을 다음 Gate에서 고정한다.

## 4. Source Assertion·윤리 경계

- dataset category는 source assertion일 뿐 소유·범죄 사실이 아니다.
- ENS forward/reverse 일치는 fixed-block binding이며 법적 소유권 증거가 아니다.
- 2022 designation과 2025 removal은 역사적 timeline이며 현재 상태는
  `not_assessed`다.
- direct seed funding은 ownership·coordination 증거가 아니다.
- 공개 USDC hub 공유는 actor 연결이 아니라 false-positive control이다.
- AI Planner의 label·relation 가설은 evidence 없는 confirmed fact가 아니다.

## 5. Verification Receipt

2026-07-30 03:47 KST 기준:

- `scripts/verify.py`: 470 tests PASS
- fixture Schema 0.1: 18 packages PASS
- Analysis I/O 0.2: 48 semantic probes PASS, 0.1 compatible
- repository traceability: 1,594 links PASS
- repository security scan: 185 runtime/evidence files PASS
- content-addressed artifact digest: 3 files PASS
- 기존 TASK-012~014 oracle·Verifier·analyzer Gate PASS

fixture validator 기대값은 13에서 18로 갱신했다. 이는 다섯 candidate
package가 Schema와 참조 무결성을 통과했다는 뜻이며, TASK-015 의미 검증이
끝났다는 뜻은 아니다.

## 6. 다음 Gate

1. ~~TASK-015 negative oracle ID·입력·expected outcome을 고정한다.~~
   → 30개·두 번 결정성 완료
2. ENS 두 package의 제2 provider 또는 독립 저장 replay를 확보한다.
3. Sanctions direct/indirect·current-state, Actor service/public-hub 반례를
   두 번 결정적으로 실행한다.
4. 독립 Verifier가 raw/source artifact에서 필수 사실을 재계산한다.
5. 조건을 충족한 fixture만 `verifying` 승격을 검토한다.
6. 그 뒤 `intel_context` 계약·Context Receipt·구현 승인을 진행한다.

## 7. Related Documents

- **Technical_Specs**: [TASK-015 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md) - source assertion 계약
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - 13 confirmed·5 candidate package·2 deferred
- **QA_Validation**: [Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md) - Stop/Go
- **QA_Validation**: [Source-resolution report](./47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) - package 전 snapshot 기준선
- **QA_Validation**: [TASK-015 Negative Oracle 보고서](./49_TASK_015_NEGATIVE_ORACLE_REPORT.md) - 30개 반례·두 번 결정성
