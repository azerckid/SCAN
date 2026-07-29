# TASK-015 Label·OSINT·Actor Fixture·Contract Gate
> Created: 2026-07-30 02:37
> Last Updated: 2026-07-30 03:47
> Status: Preview Passed · Candidate Packages 5 · Oracle / Verifier Pending · Runtime Not Implemented

## 1. 목적

이 문서는 TASK-015의 공개 source fixture 선정, claim conflict, actor
relation 반례, UI 승인, Analysis I/O 계약, 독립 Verifier 및 Benchmark
승격에 필요한 Stop/Go 기준을 정의한다.

현재는 fixture-first 계약 단계다. 공개 사례 package 5개는 `candidate`로
작성했지만 live source runtime·제품 analyzer·Benchmark 승격을 주장하지 않는다.

## 2. 대상

| 문제 | 제안 Fixture | 현재 coverage | Gate 상태 |
|:---|:---|:---:|:---:|
| OSINT-LBL-001 | `FX-OSINT-LABEL-CONFLICT-001` | unsupported | candidate package |
| OSINT-SAN-001 | `FX-OSINT-SANCTIONS-HISTORY-001` | unsupported | candidate package |
| OSINT-ENS-001 | `FX-OSINT-ENS-CONFLICT-001` | unsupported | candidate package |
| ACTOR-REL-001 | `FX-ACTOR-COMMON-FUNDER-001` | unsupported | candidate package |
| ACTOR-REL-002 | `FX-ACTOR-RELATION-HUB-001` | unsupported | candidate package |

`FX-OSINT-LABEL-CONFLICT-001`은 Etherscan을 사용하지 않는다. OpenRAIL
research/testing sample의 `Mixer;Sanctioned` assertion과 MIT Tornado
config·onchain ENS의 `team4 vesting` 역할을 보존하는 새 subject로 교체했다.
`verifying` 승격 전 제2 ENS replay와 conflict oracle이 필요하다.

## 3. Fixture Gate

- [x] bounded 후보 주소·source·관찰 시점 조사 — 5 viable
- [x] 후보 source Terms·license·privacy·재배포 가능 범위 조사
- [x] 다섯 fixture의 subject와 bounded raw snapshot 기준선 선정
- [x] source locator·고정 commit 또는 snapshot SHA-256 기록
- [x] 다섯 candidate fixture package에 selected artifact·retrieved_at 고정
- [ ] 주소 직접 명시와 주소 비명시 claim 분리
- [ ] official/first-party/provider/public-report/heuristic role 분리
- [ ] 충돌·stale·withdrawn·정정 claim 보존
- [ ] sanctions direct와 1홉 indirect 분리
- [ ] ENS forward/reverse·설정 TX·사칭/만료 반례
- [ ] common funder와 공용 service false positive 반례
- [ ] actor relation component score와 hub exclusion
- [ ] requirement→evidence→source 참조 무결성
- [ ] 두 번 결정성 실행
- [ ] 독립 Verifier 재계산
- [ ] fixture Schema 통과

## 4. Negative Oracle

| Oracle 범주 | 입력 변형 | 기대 결과 |
|:---|:---|:---|
| address omitted | 보고서에 사건명만 있고 주소 없음 | direct claim 거부·context 보존 |
| copied misinformation | 여러 재게시물이 동일 오주소 복제 | 독립 source 수로 과대 계산 금지 |
| stale/withdrawn | 과거 지정 뒤 해제·정정 | 현재 상태로 자동 승격 금지 |
| indirect service | 1홉 상대가 CEX hot wallet | sanctioned/owner 관계 단정 금지 |
| ENS reverse mismatch | reverse와 forward 불일치 | conflict·unresolved |
| impersonation | SNS 이름만 같고 주소 서명 없음 | rejected 또는 unresolved |
| common funder service | paymaster/faucet가 여러 주소 funding | same owner 단정 금지 |
| public hub | router/common contract 공유 | actor relation score 제한 |
| source hash drift | snapshot hash 불일치 | failed·source reconciliation |
| budget/source partial | 일부 source만 허용·조회 | 확인 claim 보존 partial |

## 5. 계약 QA

| QA ID | 시나리오 | 기대 결과 | 상태 |
|:---|:---|:---|:---:|
| QA-INTEL-LABEL-001 | 일치·충돌 source claim | claim별 role·address explicit·conflict group | not_executed |
| QA-INTEL-SAN-001 | 직접 목록 match + 1홉 상대 | direct/indirect 분리·목록 버전 | not_executed |
| QA-INTEL-ENS-001 | ENS·도메인·SNS 충돌 | onchain/source claim·사칭 반례 | not_executed |
| QA-INTEL-FUNDER-001 | 공통 초기 funding | 공통 source·대상별 TX·service exclusion | not_executed |
| QA-INTEL-REL-001 | 복수 relation component | component score·hub 반례·heuristic | not_executed |
| QA-INTEL-PARTIAL-001 | source budget·Terms 제한 | claim 보존·coverage gap | not_executed |
| QA-INTEL-FAILED-001 | subject/hash/version 불일치 | failed·results 빈 배열·구조화 오류 | not_executed |
| QA-INTEL-CONFLICT-001 | official/provider/heuristic 상충 | 자동 병합·자동 truth 승격 없음 | not_executed |
| QA-INTEL-PRIVACY-001 | 직접 개인정보 포함 페이지 | 최소 수집·저장 차단 | not_executed |
| QA-INTEL-RULE-001 | Rules unclear/restricted | live adapter 0회·artifact 경로 | not_executed |
| QA-INTEL-DET-001 | 동일 snapshot 두 번 | canonical result hash 일치 | not_executed |
| QA-INTEL-BENCH-001 | 문제별 승격 | confirmed fixture가 있는 완전 범위만 반영 | not_executed |

## 6. UI Gate

- [x] query 5개와 subject/source policy 화면 정의
- [x] complete·partial·failed 정보 계층 정의
- [x] claim·conflict·timeline·direct/indirect 표현 정의
- [x] onchain observation·heuristic·rejected 표현 정의
- [x] loading·empty·stale·Rules 상태 정의
- [x] HTML Preview 작성
- [x] 정적 검사 — query 5 × 상태 3, 중복 ID 0, 외부 호출 0
- [ ] 브라우저 상호작용 검증
- [x] 사용자 Preview 확인 — 2026-07-30 02:52
- [x] 사용자 피드백 반영 — 추가 수정 요청 없이 승인

## 7. Originality·Ethics

- [x] AI Planner 출력은 source가 아닌 heuristic으로 계약
- [x] source assertion과 ownership·범죄 truth를 분리
- [x] 주소 비명시·충돌·해제·정정 기록을 숨기지 않음
- [x] 개인정보 최소 수집과 원문 전체 복제 금지
- [x] credential·session·검색 계정 token 저장 금지
- [x] 후보 source license·Terms 조사와 금지 source 제외
- [ ] 채택 source snapshot·제3자 OSS 고정 commit·license 기록

## 8. 365 글로벌 평가 기준

| 기준 | 현재 판정 | 통과 증거 |
|:---|:---:|:---|
| Functionality | Proposed | 5 query·12 QA·fixture Gate 정의 |
| Potential Impact | Planned | LABEL 의존 14문항과 CASE/SERVICE 재사용 |
| Novelty | Proposed | source claim과 실제 소유·범죄 단정 분리 |
| UX | Pass / Docs-only | 사용자 승인된 conflict·address explicit·timeline Preview |
| Open-source | Pass / Contract | provider 독립 source assertion 모델 |
| Business Plan | N/A | 대회 준비 범위 |

## 9. Stop/Go

현재 판정은 **GO for negative oracle and independent Verifier on five
candidate packages, STOP for fixture promotion and implementation**이다.

Fixture 선정 전:

1. ~~사용자 Preview 확인·피드백~~ → 2026-07-30 02:52 완료
2. source role·claim·conflict 계약 승인
3. source별 Terms·privacy 범위 조사 → 2026-07-30 후보 단계 완료.
   공식 대회 Rules와 채택 snapshot별 재배포 범위는 계속 미확정

Context Receipt `PASS` 전:

4. ~~다섯 후보 source·raw scope 기준선 확정~~ → 2026-07-30 완료
5. ~~다섯 candidate package에 selected artifact·retrieved_at 연결~~
   → 2026-07-30 완료
6. snapshot/replay·negative oracle·독립 Verifier
7. Analysis I/O `intel_context` 대안 B 정식 승인
8. 문제별 complete/partial/failed와 UI 재검토

코드 착수 전:

9. Context Receipt `PASS`
10. 사용자 analyzer 구현 명시 승인

## 10. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - OSINT·Actor 5문항 정답 기준
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - API·AI·개인정보 Rules
- **UI_Screens**: [TASK-015 Intelligence UI](../02_UI_Screens/09_TASK_015_INTELLIGENCE_UI.md) - 화면 상태·사용자 Gate
- **UI_Screens**: [Intelligence HTML Preview](../02_UI_Screens/previews/08_task_015_intelligence_preview.html) - 정적 검토 화면
- **Technical_Specs**: [TASK-015 Intelligence 계약](../03_Technical_Specs/17_TASK_015_INTELLIGENCE_CONTRACT_PROPOSAL.md) - source·claim·relation 계약
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - Label·Sanctions·ENS·OSINT source 상태
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) - Context Lock·Acceptance Criteria
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-INTEL-001 상위 Gate
- **QA_Validation**: [TASK-015 공개 Source·Fixture 후보 조사](./46_TASK_015_PUBLIC_SOURCE_CANDIDATE_REPORT.md) - 4 viable·1 source-blocked 판정
- **QA_Validation**: [Source 교체·Raw Snapshot 기준선](./47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) - 5 viable·snapshot hash 판정
- **QA_Validation**: [Candidate Fixture Package 보고서](./48_TASK_015_CANDIDATE_FIXTURE_PACKAGE_REPORT.md) - 5 package·artifact hash·잔여 Gate
