# TASK-015 OpenRAIL License Resolution Receipt
> Created: 2026-07-30 14:38
> Last Updated: 2026-07-30 15:37
> Status: Blocked · Exact License Text Absent · Label Fixture Verifying / Quarantined

## 1. 목적과 판정

`FX-OSINT-LABEL-CONFLICT-001`의 selected dataset row가 참조하는 pinned
repository에서 exact OpenRAIL license text·notice·재배포 의무를 확인한다.

**판정: exact license text를 pin할 수 없다.** pinned commit에는 `LICENSE`
계열 파일이 없고 README metadata와 본문이 일반 `openrail` / `OpenRAIL`
family만 표시한다. Hugging Face 공식 license registry도 `openrail`을 특정
단일 계약문이 아니라 **OpenRAIL license family** 식별자로 설명한다.

따라서 임의의 OpenRAIL 변형을 선택하지 않는다. label fixture는
`verifying`·HOLD를 유지하고 selected-row artifact는 README가 명시한
research/testing regression에만 한정한다. promotion·export에는 사용하지 않는
quarantine 상태로 둔다.

후속 [LABEL Source Replacement Review](./57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md)는
publisher license를 추정하지 않고 official OFAC historical action + MIT
community config + fixed-block ENS로 subject를 교체하는 경로를 선택했다.
fixture migration·재검증은 아직 실행하지 않았으므로 본 차단 기록은 기존
OpenRAIL artifact에 계속 적용된다.

## 2. Pinned Source

| 필드 | 값 |
|:---|:---|
| Repository | `Humanbased-AI/Crypto-Address-Annotation-10K` |
| Commit | `865b4b7ca276ffa50255f5fa751227b3c666dbf1` |
| Commit last modified | `2025-12-08T04:10:22Z` |
| README SHA-256 | `426c2409b607ca540627f2ef10f65c268026287117f7fa0d7b6c5966f919f0fe` |
| README license metadata | `openrail` |
| README human-readable claim | `OpenRAIL` |
| Dataset CSV SHA-256 | `7732e18f0534dd8825f17f7408f8fe3c0538787d7a6fe9abb0448bbb80f772c2` |
| Selected-row artifact SHA-256 | `15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475` |
| Retrieved at | `2026-07-30T14:38:00+09:00` |

공식 원문:

- [Pinned dataset card](https://huggingface.co/datasets/Humanbased-AI/Crypto-Address-Annotation-10K/blob/865b4b7ca276ffa50255f5fa751227b3c666dbf1/README.md)
- [Pinned repository tree API](https://huggingface.co/api/datasets/Humanbased-AI/Crypto-Address-Annotation-10K/tree/865b4b7ca276ffa50255f5fa751227b3c666dbf1?recursive=true&expand=false)
- [Hugging Face license registry](https://huggingface.co/docs/hub/repositories-licenses)

## 3. Absence Proof

Pinned repository tree의 전체 파일은 다음 세 개다.

| Path | Git object ID | Size |
|:---|:---|---:|
| `.gitattributes` | `1ef325f1b111266a6b26e0196871bd78baa8c2f3` | 2,461 |
| `Crypto-Address-Annotation-10K.csv` | `2c15e5d9304990833b1bfd5b68b797ac6cbc8e66` | 865,124 |
| `README.md` | `483226bdf0479cfa093bbf62cab055b0ee9b4cc3` | 4,101 |

같은 commit의 `LICENSE`, `LICENSE.md`, `LICENSE.txt` raw URL은 모두 HTTP
`404`였다. README에는 license URL·version·full text·notice file이 없다.

이 증거는 “license가 없다”가 아니라 **어떤 OpenRAIL 변형과 의무가
적용되는지 repository 자료만으로 특정할 수 없다**는 뜻이다.

## 4. Usage·Redistribution Decision

| 행위 | 상태 | 근거 |
|:---|:---:|:---|
| repository locator·commit·hash 인용 | ALLOW | 출처 식별·무결성 기록 |
| license metadata `openrail` 사실 기록 | ALLOW | pinned README에서 직접 확인 |
| 기존 selected row를 offline analyzer regression에 사용 | BOUNDED | README가 명시한 research/testing 범위, 신규 배포·확장 없음 |
| selected row를 confirmed fixture 근거로 승격 | BLOCK | 재배포·notice 의무 불명 |
| selected row를 export/package에 포함 | BLOCK | exact permission 불명 |
| 임의 OpenRAIL-D/M/++ 문구를 대신 적용 | BLOCK | publisher가 선택한 변형이라는 근거 없음 |
| 게시자 확인 또는 명확한 license source로 교체 | GO | 다음 resolution 경로 |

기존 selected-row 파일은 이미 repository에 존재하고 현재 offline regression이
그 값을 사용한다. 이 Receipt는 삭제나 새로운 재배포를 승인하지 않는다.
제거·history 처리·대체 source 채택은 별도 사용자 승인과 새 fixture
provenance 검증을 필요로 한다.

## 5. 다음 Hard Gate

아래 둘 중 하나가 충족돼야 label fixture 승격 검토를 재개한다.

1. dataset publisher가 pinned dataset에 적용되는 exact license text·version·
   notice·selected-row 재배포 조건을 공식 locator로 제공한다.
2. 같은 conflict를 재현할 수 있고 exact license text가 pin된 대체 source를
   선정해 artifact·expected·evidence·Verifier hash를 다시 검증한다.

그 전까지:

- fixture JSON status는 `verifying`을 유지한다.
- Benchmark는 11을 유지한다.
- label source assertion은 `confirmed_fact`가 아니다.
- 다른 SANCTIONS·ENS·RELATION-HUB promotion 검토를 함께 막지는 않는다.

## 6. Verification Receipt

- pinned README SHA-256 재계산: PASS
- repository tree 3 files 고정: PASS
- `LICENSE*` 세 경로 HTTP 404: PASS
- Hugging Face registry의 `openrail = OpenRAIL license family` 확인: PASS
- product source·fixture JSON·Benchmark 변경: 0
- live analyzer/provider 호출: 0
- repository Gate: **535 tests**, fixture **18**, Analysis I/O **52 probes**,
  traceability **1,691 links**, security **205 files** PASS

## 7. 365 글로벌 평가 기준

| 기준 | 상태 | 근거 |
|:---|:---:|:---|
| Functionality | Pass | license resolution을 machine-readable evidence와 Hard Gate로 고정 |
| Potential Impact | Pass | 불명확한 제3자 label의 오승격·오배포 위험 차단 |
| Novelty | Pass | fact correctness와 redistribution permission을 독립 검증 |
| UX | Pass | HOLD/BLOCK/GO와 다음 행동을 표로 표시 |
| Open-source | Partial | source는 공개지만 exact license text가 없어 재사용·재배포 보류 |
| Business Plan | N/A | 대회 준비 QA·compliance 기록 |

## 8. Originality & Ethics Check

- 제3자 license text를 추정·합성·대체하지 않았다.
- dataset row를 소유·범죄 사실로 자동 승격하지 않는다.
- license 불명확성을 숨기고 `confirmed`로 표시하지 않는다.
- 기존 artifact 삭제는 별도 승인 없이 수행하지 않는다.

## 9. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 대회 source 허용 상태
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - source claim·conflict·상태 표시
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - label source·Terms 경계
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) · [Coverage Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md)
- **QA_Validation**: [Promotion Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) · [Source Resolution](./47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) · [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- **QA_Validation**: [LABEL Source Replacement Review](./57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md) - exact text 추정 없이 선택한 대체 경로
- **Fixture**: [FX-OSINT-LABEL-CONFLICT-001](./fixtures/FX-OSINT-LABEL-CONFLICT-001/README.md)
