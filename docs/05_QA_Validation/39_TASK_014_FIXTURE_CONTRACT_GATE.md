# TASK-014 PATH Fixture·Contract Gate
> Created: 2026-07-29 22:52
> Last Updated: 2026-07-30 00:08
> Status: Preview User Review Passed · Fixture 3 Verifying · Runtime Not Implemented

## 1. 목적

이 문서는 TASK-014가 공개 사례 선정부터 제품 analyzer·Benchmark 승격까지
통과해야 할 검증 기준을 정의한다. 세 공개 사례는 두 공급자 replay,
negative oracle 18개, 독립 Verifier를 통과해 `verifying`이다. 제품
analyzer와 최종 승격은 아직 주장하지 않는다.

## 2. 대상과 현재 상태

| 문제 | Fixture 후보 | 현재 coverage | Gate 상태 |
|:---|:---|:---:|:---:|
| FLOW-EVM-001 | [FX-FLOW-PATH-001](./fixtures/FX-FLOW-PATH-001/README.md) | unsupported | verifying |
| FLOW-EVM-002 | [FX-FLOW-REMERGE-001](./fixtures/FX-FLOW-REMERGE-001/README.md) | unsupported | verifying |
| FLOW-MULTI-001 | [FX-FLOW-MULTI-001](./fixtures/FX-FLOW-MULTI-001/README.md) | unsupported | verifying |

## 3. Fixture Gate

- [x] 공개 seed·TX·block·asset scope 선정
- [x] 두 논리 source의 decoded TX·receipt 일치
- [x] raw SHA-256·method·retrieved_at 기록
- [x] expected graph를 raw replay에서 재계산
- [x] included/excluded/unresolved edge를 분리
- [x] 단일 path·분기·재병합·multi-origin 정답 고정
- [x] cycle·unrelated fund·budget·asset mismatch 반례 18개 포함
- [x] requirement→evidence→source 참조 무결성
- [x] 두 번 결정성 실행
- [x] 독립 Verifier 재계산
- [x] fixture Schema 통과

## 4. 계약 QA

| QA ID | 시나리오 | 기대 결과 | 상태 |
|:---|:---|:---|:---:|
| QA-PATH-CONTRACT-001 | single path complete | ordered edges·terminal·asset ledger exact | not_executed |
| QA-PATH-CONTRACT-002 | remerge complete | branches·merge·unrelated exclusion·residual exact | not_executed |
| QA-PATH-CONTRACT-003 | multi-origin complete | origin별 contribution·deduplicated total exact | not_executed |
| QA-PATH-PARTIAL-001 | hop/node/edge budget 초과 | frontier·termination을 보존한 partial | not_executed |
| QA-PATH-PARTIAL-002 | 비필수 source/range 일부 누락 | 확인된 edge 보존·미확인 범위 표시 | not_executed |
| QA-PATH-FAILED-001 | scope/replay 또는 필수 source 결합 불일치 | failed·`results: []`·reconciliation error | not_executed |
| QA-PATH-NEG-001 | cycle·중복·unrelated fund | 확정 경로 오염 없이 제외·실패 | pass / offline |
| QA-PATH-SEC-001 | secret/path·Rules Gate | endpoint·credential·절대 경로 비노출 | not_executed |
| QA-PATH-DET-001 | 동일 replay 두 번 | canonical result hash 일치 | pass / fixture |
| QA-PATH-BENCH-001 | 세 FLOW 문제 승격 | automated 수와 실행 성공 수 정합 | not_executed |

## 5. UI Gate

- [x] single·remerge·multi-origin 화면 목적 정의
- [x] complete·partial·failed 정보 계층 정의
- [x] included·excluded·unresolved edge와 residual 표시 정의
- [x] loading·empty·stale·Rules 재사용 경계 정의
- [x] HTML Preview 작성
- [ ] 브라우저 상호작용 검증
- [x] 사용자 Preview 확인 — 2026-07-29 23:09
- [x] 피드백 반영 — source partial/failed·query별 failed 사유 분리

## 6. Originality·Ethics

- [ ] 공개 자료와 제3자 ABI·데이터 출처 및 license 기록
- [ ] label·AI 가설을 graph edge의 증거로 대체하지 않음
- [ ] 범죄·피해자·서비스 귀속을 `not_assessed`로 유지
- [ ] credential·개인정보·비밀키 수집 0건
- [ ] excluded edge와 residual을 숨기지 않음

## 7. 365 글로벌 평가 기준

| 기준 | 현재 판정 | 통과 증거 |
|:---|:---:|:---|
| Functionality | Partial / Verifying | 세 fixture raw replay·18 oracle·Verifier 통과, 제품 analyzer 미구현 |
| Potential Impact | Planned | PATH 18개 필수 문제의 공통 기반 |
| Novelty | Proposed | exclusion·residual을 포함한 증거 우선 graph |
| UX | Pass / Docs-only | 사용자 승인된 세 query·세 상태 HTML Preview |
| Open-source | Planned | bounded JSON 계약·fixture·재현 명령 |
| Business Plan | N/A | 대회 준비 범위 |

## 8. Stop/Go

현재 판정은 **STOP for implementation**이다. 다음을 모두 닫은 뒤에만
Context Receipt를 `PASS`로 전환한다.

1. fixture candidate 3개 작성
2. ~~replay·negative oracle·Verifier Gate~~ → 2026-07-30 완료
3. Analysis I/O 대안 정식 승인
4. ~~사용자 Preview 승인~~ → 2026-07-29 23:09 완료
5. 사용자 구현 승인

## 9. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - FLOW 문제 정답·부분·실패 기준
- **UI_Screens**: [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - 화면 상태·사용자 Gate
- **UI_Screens**: [PATH HTML Preview](../02_UI_Screens/previews/07_task_014_path_preview.html) - 정적 검토 화면
- **Technical_Specs**: [TASK-014 PATH 계약](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - graph·ledger·오류 계약
- **Logic_Progress**: [Backlog TASK-014](../04_Logic_Progress/00_BACKLOG.md) - Context Lock·Acceptance Criteria
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-PATH-001/002 상위 Gate
- **QA_Validation**: [TASK-014 후보 보고서](./40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 공개 사례·1차 정답·잔여 Gate
