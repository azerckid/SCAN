# TASK-015 Label·OSINT·Actor Intelligence 계약 제안
> Created: 2026-07-30 02:37
> Last Updated: 2026-07-30 03:47
> Status: Proposed 0.1 · Candidate Packages 5 · Runtime Not Implemented

## 1. 목적

이 문서는 `OSINT-LBL-001`, `OSINT-SAN-001`, `OSINT-ENS-001`,
`ACTOR-REL-001`, `ACTOR-REL-002`를 지원하기 위한 source assertion,
충돌, 시점, actor relation 계약을 구현 전에 고정한다.

TASK-015의 목표는 주소 소유자나 범죄성을 자동 단정하는 것이 아니다.
확정하는 대상은 다음 두 종류뿐이다.

1. 공개 출처가 특정 시점에 특정 주소를 명시하며 어떤 주장을 했다는 사실
2. 온체인 transaction·log·state에서 직접 관찰되는 관계 사실

동일 주체, 서비스 귀속, 제재의 실질적 의미, SNS 운영자 동일성은 별도의
휴리스틱 또는 사람 검토 대상으로 남긴다.

## 2. 현재 기준선과 범위

| 항목 | 현재 상태 | TASK-015 결정 |
|:---|:---|:---|
| Benchmark | automated 11 · assisted 1 · unsupported 18 | 대상 5문항은 아직 unsupported |
| PATH | TASK-014 complete | 1홉·공통 펀딩 evidence 재사용 가능 |
| Label source | DS-LABEL-PUBLIC 후보 | source별 Terms·버전·주소 명시 여부 필요 |
| Sanctions | DS-SANCTIONS-PUBLIC 검증 중 | 역사적 고시와 현재 상태를 분리 |
| ENS·Web | DS-ENS 후보, DS-OSINT-WEB 검증 중 | 자동 조회·스크래핑은 Rules·Terms Gate |
| Runtime | 전용 analyzer 없음 | Context Receipt·사용자 구현 승인 전 코드 금지 |

일반 웹 검색, 검색엔진, SNS, WHOIS, 제3자 라벨 API의 live 호출은 공식
Rules와 각 서비스 Terms가 허용된 경우에만 활성화한다. 허용되지 않으면
주최 제공 artifact 또는 사용자가 제공한 bounded JSON/CSV를 같은 source
assertion 계약으로 정규화한다.

## 3. 제안 Analysis I/O

### 3.1 Analysis type

Analysis I/O `0.2`에 `analysis_type: "intel_context"`를 추가하는 대안 B를
제안한다. 이 문서는 제안만 하며 enum·Pydantic·JSON Schema를 변경하지 않는다.

| query_kind | 대상 | 출력 |
|:---|:---|:---|
| `collect_label_claims` | OSINT-LBL-001 | 주소 명시 source claim, 충돌, disposition |
| `check_sanctions_exposure` | OSINT-SAN-001 | 직접 match, 1홉 indirect, 목록·버전 |
| `resolve_identity_clues` | OSINT-ENS-001 | ENS·도메인·SNS 단서와 온체인 연결 |
| `find_common_funder` | ACTOR-REL-001 | 공통 funding address, 대상별 TX, service exclusion |
| `score_actor_relations` | ACTOR-REL-002 | 후보별 근거 유형·반례·heuristic score |

### 3.2 공통 request

```json
{
  "schema_version": "0.2",
  "analysis_type": "intel_context",
  "query_kind": "collect_label_claims",
  "chain_scope": "evm",
  "subject_addresses": [
    "0x1111111111111111111111111111111111111111"
  ],
  "observation_window": {
    "from": "2026-07-01T00:00:00Z",
    "to": "2026-07-30T00:00:00Z"
  },
  "source_policy": {
    "allowed_roles": [
      "official_record",
      "first_party",
      "provider_label",
      "public_report",
      "heuristic"
    ],
    "max_sources": 20,
    "rules_status": "unclear",
    "network_mode": "offline"
  }
}
```

필수 제약:

- address는 checksum 표현과 별개로 normalized address를 비교한다.
- `observation_window` 밖 자료는 삭제하지 않고 `stale` 후보로 분리한다.
- source budget 초과는 확인된 claim을 보존한 `partial`이다.
- `rules_status != allowed`이면 live source adapter는 호출하지 않는다.
- 제공 artifact는 content SHA-256과 논리 locator를 기록한다.

## 4. Source assertion 계약

### 4.1 Source role

| source_role | 의미 | truth 승격 |
|:---|:---|:---|
| `official_record` | 정부·규제기관·공식 registry 원문 | 원문이 해당 주장을 했음만 확정 |
| `first_party` | 프로젝트·서비스 운영 주체의 공식 공지 | 자기 주장임을 확정, 소유 진실과 분리 |
| `provider_label` | 탐색기·라벨 공급자의 표시 | provider claim, 독립 사실 아님 |
| `public_report` | 보안 보고서·연구·언론 | 주소 명시·인용 범위를 보존 |
| `heuristic` | AI·규칙·클러스터링이 생성한 후보 | confirmed fact 승격 금지 |

`official_record`는 source role 우선순위가 높지만, 자동으로 현재 제재 상태나
범죄 사실을 의미하지 않는다. 지정·정정·해제·만료의 시점을 함께 본다.

### 4.2 Source 최소 필드

| 필드 | 필수 | 설명 |
|:---|:---:|:---|
| `source_id` | O | package 내 고유 ID |
| `source_role` | O | 위 5개 role |
| `locator` | O | URL 또는 artifact 논리 URI |
| `publisher` | O | 발행 주체 |
| `retrieved_at` | O | 수집 시각 |
| `published_at` | 선택 | 발행 시각 |
| `content_sha256` | O | 저장 snapshot hash |
| `address_explicit` | O | 원문에 normalized 주소 문자열이 직접 있는지 |
| `terms_mode` | O | allowed / artifact_only / restricted / unclear |
| `quote_summary` | O | 짧은 요약; 원문 전체 복제 금지 |

### 4.3 Claim 최소 필드

```json
{
  "claim_id": "CLM-001",
  "subject_address": "0x1111111111111111111111111111111111111111",
  "claim_type": "service_label",
  "claim_value": "Example Service",
  "assertion_class": "source_assertion",
  "source_refs": ["SRC-001"],
  "evidence_refs": [],
  "valid_from": null,
  "valid_to": null,
  "conflict_group_id": "CG-001",
  "disposition": "unresolved"
}
```

`assertion_class`:

- `source_assertion`: 출처가 실제로 한 주장
- `onchain_observation`: TX·log·state로 직접 관찰
- `heuristic_candidate`: 규칙·AI·통계 후보
- `rejected`: 반례로 기각
- `not_assessed`: 범위 밖 판단

`disposition`:

- `accepted_as_source_claim`: source가 그렇게 말했다는 사실만 채택
- `unresolved`: 충돌 또는 근거 부족
- `rejected`: 오주소·사칭·무관 허브 등 반례로 기각
- `stale`: 관찰 시점 밖 또는 이후 정정 가능
- `withdrawn`: 공식 해제·철회·정정 기록

## 5. Query별 계약

### 5.1 collect_label_claims

- source별 claim을 병합하지 않고 배열로 보존한다.
- 같은 주소·claim_type의 다른 값은 `conflict_group_id`로 묶는다.
- 주소가 원문에 없으면 `address_explicit: false`이며 direct label로 쓰지 않는다.
- 재게시물은 원출처를 찾지 못하면 supporting context로만 남긴다.

### 5.2 check_sanctions_exposure

- `direct_matches`: subject 주소가 목록 원문에 직접 명시된 경우
- `indirect_matches`: 확인된 1홉 TX 상대방이 목록에 직접 명시된 경우
- direct와 indirect를 하나의 `sanctioned` boolean으로 합치지 않는다.
- 목록 이름·고시일·버전·해제/철회 기록을 필수로 보존한다.
- 1홉 공용 서비스 경유는 `heuristic_candidate` 또는 `rejected`다.

### 5.3 resolve_identity_clues

- ENS forward·reverse 결과와 설정 TX를 분리한다.
- ENS 이름, DNS/WHOIS, SNS profile의 claim은 서로 다른 source assertion이다.
- reverse mismatch, 만료, 사칭, 주소 비명시 계정을 반례로 보존한다.
- 운영 주체 동일성은 독립 근거 없이는 `unresolved`다.

### 5.4 find_common_funder

- 각 대상 주소의 bounded initial inflow를 onchain evidence로 계산한다.
- 공통 from 주소와 대상별 TX를 deterministic하게 집계한다.
- CEX hot wallet, paymaster, faucet, bridge, 공용 contract 후보는 label
  assertion과 transaction 패턴을 근거로 exclusion 후보가 된다.
- 공통 funder는 관계 사실이며 동일 소유 사실이 아니다.

### 5.5 score_actor_relations

- 근거 유형을 `common_source`, `common_destination`, `shared_contract_call`,
  `temporal_pattern`, `amount_pattern`으로 분리한다.
- score는 설명 가능한 component별 raw 값과 weight를 보존한다.
- 공용 허브·라우터·서비스 반례가 있으면 score와 함께 표시한다.
- threshold 초과도 `heuristic_candidate`이며 `confirmed owner`가 아니다.

## 6. Complete·Partial·Failed

### 6.1 Complete

- 승인된 bounded source·address·time 범위를 모두 조회했다.
- 모든 claim에 source 또는 onchain evidence 참조가 있다.
- 충돌·stale·withdrawn·주소 비명시 항목이 숨겨지지 않는다.
- heuristic은 source assertion/onchain observation과 분리돼 있다.

### 6.2 Partial

- Rules/Terms가 허용한 source subset만 조회했다.
- source budget·rate limit·artifact 누락으로 일부 범위가 미확인이다.
- 확인된 claim과 evidence는 보존하고 `coverage_gaps`를 반환한다.
- partial 결과를 “라벨 없음” 또는 “관계 없음”으로 해석하지 않는다.

### 6.3 Failed

- request subject와 source/replay subject가 결합되지 않는다.
- content hash·목록 버전·TX evidence가 불일치한다.
- 필수 address normalization 또는 source provenance가 손상됐다.
- failed는 `results: []`와 구조화 오류를 반환한다.

## 7. 제안 fixture

| Fixture ID | 문제 | 필수 사실 | 상태 |
|:---|:---|:---|:---:|
| `FX-OSINT-LABEL-CONFLICT-001` | OSINT-LBL-001 | 동일 주소에 대한 source assertion·role conflict | verifying |
| `FX-OSINT-SANCTIONS-HISTORY-001` | OSINT-SAN-001 | 직접 match·고시/해제 시점·현재 상태 분리 | verifying |
| `FX-OSINT-ENS-CONFLICT-001` | OSINT-ENS-001 | 고정 block forward/reverse·소유권 분리 | verifying |
| `FX-ACTOR-COMMON-FUNDER-001` | ACTOR-REL-001 | direct funding·initial-inflow·service exclusion | candidate |
| `FX-ACTOR-RELATION-HUB-001` | ACTOR-REL-002 | 근거 component·공용 hub false-positive | verifying |

공개 사례·주소·source locator를 선정해 다섯 Schema 0.1 package를
`candidate`로 작성했다. 이는 정식 계약 승인이나 `verifying` 승격이 아니다.
negative oracle·독립 Verifier와 source별 잔여 Gate를 먼저 닫는다.

## 8. AI Planner·Python·Verifier 경계

AI Planner는 모든 문제에서 검색어, source 후보, 관계 계산 방법과 반례를
제안한다. AI 출력 자체는 source가 아니며 `heuristic_candidate`다.

Python worker는 다음을 수행한다.

- 승인 source/artifact 수집과 content hash
- 주소·시점·목록 버전 정규화
- claim conflict·direct/indirect 분리
- bounded onchain relation 계산
- deterministic result·evidence·source 참조 생성

독립 Verifier는 source snapshot과 onchain replay에서 claim의 주소 명시,
시점, 직접/간접 연결, component score를 다시 계산한다. evidence 없는 AI
출력은 `review_required`를 벗어나지 못한다.

## 9. 보안·윤리·Open-source

- 개인 이메일·전화번호·결제정보 등 직접 개인정보를 artifact에 저장하지 않는다.
- 공개 SNS라도 필요한 주소 연결 문장과 시점만 최소 수집한다.
- 원문 전체를 복제하지 않고 hash·locator·짧은 요약을 저장한다.
- credential, session cookie, 검색 계정 token을 fixture·SQLite·로그에 넣지 않는다.
- 라이선스·Terms가 재배포를 막으면 raw artifact는 로컬 보존하고 fixture에는
  hash·derived fact만 둔다.
- 휴리스틱·라벨은 증거가 아니라 검토 대상 assertion이다.

## 10. 365 글로벌 평가 기준

| 기준 | 현재 판정 | 계약 근거 |
|:---|:---:|:---|
| Functionality | Proposed | 5 query·source/claim/conflict 계약 |
| Potential Impact | Planned | LABEL이 필요한 14개 문제와 후속 CASE/SERVICE 재사용 |
| Novelty | Proposed | source가 말한 사실과 실제 소유·범죄 사실을 분리 |
| UX | Pass / Docs-only | conflict·stale·direct/indirect Preview 사용자 승인 |
| Open-source | Pass / Contract | provider 종속 없는 JSON assertion 모델 |
| Business Plan | N/A | 대회 준비 범위 |

## 11. 구현 전 Gate

- [ ] source role·claim·conflict 계약 사용자 승인
- [x] TASK-015 UI Preview 사용자 검토·피드백 — 2026-07-30 02:52 승인
- [x] 공개 fixture 5개 후보 bounded 조사·source blocker 교체 — 5 viable
- [x] 다섯 후보의 pinned locator·raw snapshot SHA 기준선 기록
- [x] selected raw artifact를 포함한 다섯 candidate fixture package 작성
- [ ] source별 Rules·Terms·privacy·license 확인
- [ ] raw/source snapshot·negative oracle·독립 Verifier
- [ ] Analysis I/O 대안 B 정식 승인
- [ ] Context Receipt `PASS`
- [ ] 사용자 analyzer 구현 명시 승인

## 12. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 대상 5문항 정답·부분·실패 기준
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - 외부 API·AI·개인정보 Gate
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - claim·conflict·relation 화면
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - Label·Sanctions·ENS·OSINT source 상태
- **Technical_Specs**: [Coverage 확장 Brief](./09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-INTEL 상위 계약
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock·구현 승인
- **QA_Validation**: [TASK-015 Fixture·Contract Gate](../05_QA_Validation/45_TASK_015_FIXTURE_CONTRACT_GATE.md) - Stop/Go 기준
- **QA_Validation**: [TASK-015 공개 Source·Fixture 후보 조사](../05_QA_Validation/46_TASK_015_PUBLIC_SOURCE_CANDIDATE_REPORT.md) - Terms·privacy·후보 판정
- **QA_Validation**: [Source 교체·Raw Snapshot 기준선](../05_QA_Validation/47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) - replacement·snapshot hash
- **QA_Validation**: [Candidate Fixture Package 보고서](../05_QA_Validation/48_TASK_015_CANDIDATE_FIXTURE_PACKAGE_REPORT.md) - 5 candidate packages·artifact hash
