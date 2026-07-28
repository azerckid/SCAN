# OPS-IMPL-06 Candidate·Independent Verifier 검증 보고서
> Created: 2026-07-28 15:29
> Last Updated: 2026-07-28 15:29
> Status: Passed · QA-OPS-VERIFY-001 / QA-OPS-CONFLICT-001 Passed

## 1. 목적과 범위

이 보고서는 `OPS-IMPL-06`에서 AI plan을 실행한 Python evidence 결과가
제출 후보로 구성되고, 별도 verifier job이 raw replay를 다시 실행한 뒤에만
`submission_ready`로 승격되는지 기록한다.

포함 범위:

- scoped Analysis result에서 candidate result/evidence 참조 파생
- 선택 result의 ID·type·value를 canonical JSON answer로 결정적 생성
- candidate를 검증 전 `draft`로 유지
- verifier 전용 adapter workspace에서 DEX·AUTH·FREEZE raw replay 재실행
- 기존 결과 재사용(`reused=true`)을 독립 검증으로 인정하지 않음
- answer format/value·chain·result·evidence와 조건부 address·TX·raw amount·
  decimals 검사
- reporter·evidence job과 verifier job의 problem·plan·role 독립성
- conflict·missing evidence·adapter 실패의 보존
- Application Gate만 `submission_ready` 승격
- partial·uncertainty·not_assessed·필수 check 누락의 `review_required` 유지
- 생성 결과의 Operations contract `0.1` round-trip

제외 범위:

- OperationsSnapshot·command result·local CLI view (`OPS-IMPL-07`)
- submission record·전체 운영 보안 Gate (`OPS-IMPL-08`)
- live AI·RPC·CTFd 호출
- distributed verifier·process 간 worker isolation

## 2. 구현

| 위치 | 책임 |
|:---|:---|
| `src/scan_tool/application/candidate_verifier.py` | Candidate Builder·fresh replay Verifier·Promotion Gate |
| `tests/integration/test_candidate_verifier.py` | 세 vertical·독립성·격리·충돌·불완전·우회 차단 19 tests |

Operations Schema `0.1`, Analysis I/O `0.1`, SQLite schema v2와 dependency는
변경하지 않았다. verifier는 기존 `EvidenceWorkerPort`와
`InProcessEvidenceWorker`를 재사용하되 evidence workspace와 다른 root를
주입하며, adapter가 기존 결과를 반환하면 검증을 `incomplete`로 처리한다.

## 3. 검증 결과

| 검증 | 결과 |
|:---|:---:|
| OPS-IMPL-06 integration | 19 passed |
| 전체 pytest | 244 passed |
| Ruff lint·format | pass |
| fixture Schema | PASS 3 |
| Analysis request/result | PASS 3 |
| generated Analysis Schema | PASS 3 · 35 probes |
| Operations contract | PASS · 17 probes |
| 저장소 추적성 | PASS · 763 links |
| 저장소 보안 검사 | PASS · 63 runtime/evidence files |

주요 결과:

1. DEX·AUTH·FREEZE raw replay를 verifier 전용 workspace에서 다시 실행해
   원본 Analysis result/evidence와 일치시켰다.
2. 검증 전 candidate는 `draft`이며 verification ref가 없다.
3. canonical answer를 임의 문자열로 바꾸면 `answer_value` conflict가 발생했다.
4. required check를 `answer_format` 하나로 축소한 pass record는 승격되지 않았다.
5. replay result·evidence가 다르면 conflict·missing evidence를 보존하고
   candidate는 `review_required`가 됐다.
6. reporter와 verifier가 같은 job이면 adapter 호출 0건으로 차단됐다.
7. `reused=true` 결과, adapter 실패는 독립 검증이 아닌 `incomplete`로 남았다.
8. partial evidence, uncertainty, `not_assessed` result는 replay가 일치해도
   `submission_ready`가 되지 않았다.
9. pass Verification·Candidate·event를 포함한 Operations contract `0.1`
   bundle이 cross-record validator를 통과했다.
10. 다른 problem의 evidence run과 범위 밖 result ref는 candidate 생성·승격
    Gate에서 구조화 오류로 거부되며 예외로 runtime을 중단하지 않았다.

## 4. QA 판정

| QA | 판정 | 증거·남은 조건 |
|:---|:---:|:---|
| `QA-OPS-VERIFY-001` | pass | draft→fresh replay pass→Application Gate 승격, self-check·재사용·필수 check 축소 차단 |
| `QA-OPS-CONFLICT-001` | pass | result/evidence 충돌·누락을 보존하고 `review_required` 유지 |
| `QA-OPS-PAR-001` | partial | candidate problem scope는 통과, 실제 OperationsSnapshot 격리는 OPS-IMPL-07 |
| `QA-OPS-INTRA-001` | partial | evidence→candidate→verifier dependency는 연결, 한 문제의 복수 leaf reconciliation 통합은 OPS-IMPL-07 |
| `QA-OPS-RULE-001` | partial | offline fresh replay 통과, 공식 허용 live adapter 미실행 |

## 5. 승격 불변조건

다음 조건을 모두 만족해야 `submission_ready`다.

1. verification status가 `pass`다.
2. reporter·모든 candidate evidence job이 `independent_from_job_ids`에 있다.
3. 모든 candidate result/evidence ref가 통과 check에 포함된다.
4. data에 존재하는 필수 check를 Application Gate가 재계산해 모두 확인한다.
5. candidate answer가 선택 result에서 만든 canonical answer와 같다.
6. 모든 근거 job과 Analysis result가 `complete`다.
7. 선택 result classification이 모두 `confirmed_fact`다.
8. candidate uncertainty가 없다.

confidence는 이 조건을 대체하지 않는다.

## 6. 안전·범위 경계

- external network·live AI·live RPC·CTFd 호출을 추가하지 않았다.
- verifier adapter 예외 원문·secret·로컬 경로를 event/error에 반사하지 않는다.
- AI 자연어 결론과 confidence를 result/evidence ref로 사용하지 않는다.
- 제출 자동화와 credential·session·Authorization 필드를 추가하지 않았다.
- 새 dependency·Schema·migration·UI를 추가하지 않았다.

## 7. Known Issues와 다음 단계

- verifier 독립성은 별도 job ID, 역할, fresh adapter result와 주입된 별도
  workspace root로 보장한다. process·host 수준 격리는 범위 밖이다.
- 현재 canonical answer는 선택 result의 ID·type·value JSON이다. 실제 대회
  answer format별 표시·복사 UI는 OPS-IMPL-07에서 이 값을 읽는다.
- 한 문제의 복수 evidence run을 입력할 수 있으나 전체 Queue dependency와
  OperationsSnapshot 통합은 아직 실행하지 않았다.
- candidate·verification 중앙 SQLite v2 저장 연결은 OPS-IMPL-07 composition
  root 범위다.

다음 구현 단위는 별도 승인 후 `OPS-IMPL-07`
OperationsSnapshot·command result·local CLI view다.

## 8. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Pass | candidate·fresh replay·격리·conflict·promotion 19 integration tests |
| Potential Impact | Partial | 잘못된 후보 자동 승격 차단, 실제 대회 처리시간 미측정 |
| Novelty | Pass | AI 방법 가설과 결정적 Python 증거 사이에 fresh independent replay Gate |
| UX | N/A | OperationsSnapshot·CLI/Board 표시는 OPS-IMPL-07 |
| Open-source | Pass | 기존 port·Analysis I/O·표준 라이브러리 재사용, 새 dependency 없음 |
| Business Plan | N/A | 대회 운영 검증 계층이며 수익 모델 검증 범위가 아님 |

## 9. Related Documents

- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - `REQ-OPS-VERIFY-*`
- **Technical_Specs**: [TASK-010 Pre-Code Technical Brief](../03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) - Candidate·Verifier Gate
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - OPS-IMPL 상태
- **QA_Validation**: [Agentic Parallel Solve QA](./03_AGENTIC_PARALLEL_SOLVE_QA.md) - VERIFY·CONFLICT 시나리오
- **QA_Validation**: [OPS-IMPL-05 Evidence Worker 보고서](./18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md) - raw evidence worker 기준선
