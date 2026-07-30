# TASK-015 intel_context Analyzer 독립 Verification Receipt

> Created: 2026-07-30
> Last Updated: 2026-07-30
> Status: Passed · Analyzer 구현·독립 검증 완료 · Fixture 4 Verifying / 1 Candidate 유지 · Benchmark 11 유지

## 1. 목적과 판정

사용자 계약 정식 승인·Context Receipt `PASS`·구현 승인(2026-07-30) 이후
구현한 `intel_context` 제품 analyzer(`scan_tool.slices.intel_context`)가
독립 Verifier(`task_015_independent_verifier.py`)와 별도 코드 경로로 같은
source-first 결론에 도달하는지 검증한다. 두 코드는 서로 import하지 않는다.

**판정: 네 `검증 중` fixture 모두 analyzer가 `complete`를 산출했고, 그
결과 `results[0].value`의 canonical SHA-256이 독립 Verifier가 evidence.json에
고정한 `calculated_fact_sha256`과 정확히 일치했다. common-funder는 completeness
미증명으로 `partial`을 유지했고, 두 번의 결정적 실행도 통과했다.**

승인 범위는 doc 18 §10 계약 확장·CLI 연결·독립 Verifier hash 대조·offline
테스트다. **live source adapter와 fixture 최종 승격(`확정`)은 별도 Gate로
유지하며 이 문서로 승격하지 않는다.**

## 2. 독립성 경계

- `slices/intel_context.py`(Pydantic 타입 모델)는
  `application/task_015_independent_verifier.py`(순수 stdlib·raw 파일 파싱)를
  import하지 않는다. analyzer는 per-fixture `source-replay.json` 번들을,
  verifier는 fixture 패키지의 CSV/config/provider-replay/snapshot/linked
  fixture를 각각 재해석한다.
- `domain/intel_context.py`의 reviewed source replay 모델은 raw source 필드를
  받고, verifier처럼 최종 facts를 계산 입력으로 쓰지 않는다.
- `scripts/verify_task_015_analyzer_independent_verification.py`는 analyzer
  결과의 canonical hash를 evidence.json 고정 값과 비교하며 verifier 모듈을
  import하지 않는다. `scripts/verify.py`에 연결했다.

## 3. 검증 결과

| Fixture | query | 상태 | canonical hash 일치 |
|:---|:---|:---:|:---:|
| `FX-OSINT-LABEL-CONFLICT-001` | collect_label_claims | complete | pass |
| `FX-OSINT-SANCTIONS-HISTORY-001` | check_sanctions_exposure | complete | pass |
| `FX-OSINT-ENS-CONFLICT-001` | resolve_identity_clues | complete | pass |
| `FX-ACTOR-RELATION-HUB-001` | score_actor_relations | complete | pass |
| `FX-ACTOR-COMMON-FUNDER-001` | find_common_funder | **partial** | candidate 유지 |

추가 확인:

- 네 complete value가 `results[0].value` 단위로 §5 계약·verifier fact와 일치.
- ownership·criminality·coordination은 모든 결과에서 `not_assessed`, label
  category와 first-party role은 `auto_merge:false`로 분리(자동 병합 금지).
- `scan analyze --request … --evidence source-replay.json` CLI로 네 fixture
  `COMPLETE`·`schema_version 0.2`·checkpoint 1개 저장, `scan show` 재현.
- common-funder는 CLI `PARTIAL`·exit 3·`evidence_incomplete`(initial inflow /
  service exclusion 미증명), KeyboardInterrupt 후 `scan resume`이 저장 replay로
  `resumed yes` 완료.

## 4. 계약 확장 경계 (doc 18 §10)

- `AnalysisType.INTEL_CONTEXT`(0.2), `IntelContextQueryKind` 5종, query별 strict
  inputs·result variant, `IntelContextAnalysisRequest`(discriminated) 추가.
  `evm_core`·`evm_special`·`flow_path`·기존 `0.1`은 변경하지 않았다.
- **새 공개 `ErrorCode`를 추가하지 않았다.** `rule_restricted`·
  `reconciliation_failed`·`evidence_incomplete`·`decode_failed` 기존 enum만
  재사용하고 query별 사유는 `stage`로 전달(doc 18 §7).
- `FixtureRequirementId` 패턴과 정적 `analysis-result.schema.json`에 `INTEL`
  접두 추가. `analysis-request.schema.json`에 `intel_context` type·query_kind
  family binding, `check_analysis_schema.py`에 교차 조합 probe 4개(48→52),
  `operations-contract.schema.json` enum 동기화.
- §5가 이미 Verifier fact와 일치하므로 pinned hash 재계산은 없었다.

## 5. 산출물

- `src/scan_tool/domain/intel_context.py` — reviewed source replay 모델
- `src/scan_tool/domain/analysis_request.py` — `IntelContextQueryKind`·5 inputs·`IntelContextAnalysisRequest`
- `src/scan_tool/domain/analysis_result.py` — `IntelContextComplete/Partial/FailedAnalysisResult`
- `src/scan_tool/slices/intel_context.py` — `analyze_intel_context_replay`
- `src/scan_tool/application/cli_runtime.py` — dispatch·`INTEL_CONTEXT_REPLAY_STAGE`
- `docs/05_QA_Validation/fixtures/FX-{OSINT,ACTOR}-*/analysis-request.json`·`source-replay.json`(신규)
- schema 3종·`check_analysis_schema.py`·`check_task_012_analysis_contract_proposal.py` — 갱신
- `tests/unit/test_intel_context_slice.py`(26)·`tests/integration/test_intel_context_cli.py`(6)
- `scripts/verify_task_015_analyzer_independent_verification.py` — verify.py 연결

## 5.1 재검토(Request changes) P1 4건·P2 3건 정정

PR #86 재검토에서 fixture 정상값에 가려진 request↔replay 결합 구멍(변조
replay 7종이 잘못 complete)이 발견돼 같은 브랜치에서 수정하고 회귀 테스트를
추가했다. 네 verifying fixture의 `results[].value`와 canonical hash는 불변이다.

| # | 결함 | 정정 후 |
|:---:|:---|:---|
| P1-1 | query별 scope 필드가 replay와 결합되지 않음 | ENS block/address·label observation_block·actor subject/fixture·sanctions 요청 action 전건·label artifact ref를 replay와 대조, 불일치 시 `reconciliation_failed` |
| P1-2 | boolean 두 개로 common-funder completion 위조 | `find_common_funder`를 **partial-only**로 고정. claimed boolean은 증명이 아니며 항상 `initial/service_exclusion_complete: false` |
| P1-3 | evidence provenance가 allowlist에서 합성됨 | reviewed replay의 실제 source record(`source_id`·`artifact_ref`·`content_sha256`)에서 provenance를 취하고, 모든 source가 request allowlist 안인지 대조(아니면 `rule_restricted`) |
| P1-4 | candidate 평가가 `confirmed_fact`로 출력 | 확정 relations(`confirmed_fact`)와 candidate assessment(`heuristic`)를 별도 result item으로 분할 |
| P2 | 날짜·빈 문자열·중복 relation 검증 약함 | `IsoDate` 패턴·`NonEmptyString`·relation subject·source record uniqueness 모델 검증 추가 |
| P2 | 모든 오류 `retryable: true` | 결합/정합 실패는 `retryable: false`, coverage(`evidence_incomplete`)만 `true` |
| P2 | doc 18 §11 승인 체크박스 미갱신 | §11·§5.4(partial-only·분할) 갱신 |

변조 7종을 회귀 테스트로 고정했다(ENS 무관 주소/블록·actor 무관 subject/fixture·
sanctions action 누락·label observation block·common-funder subject 축소+boolean·
allowlist 임의 교체·binding 오류 non-retryable).

## 5.2 재재검토 결합 경계 8건 추가

첫 정정이 "대표 변조"만 막고 query별 **전체 scope**는 결합하지 못한 점이
재검토에서 확인돼(변형 8종이 여전히 complete), 각 query의 남은 scope 필드를
모두 request↔replay로 결합했다.

| # | 결합 추가 | 정정 후 |
|:---:|:---|:---|
| 1 | ENS `reverse.address` | forward.address와 일치 강제, 불일치 `reconciliation_failed` |
| 2 | ENS `provider_replay_ref` | replay source artifact_ref와 대조 |
| 3 | Actor subject 집합 | subset → **정확 일치**(relation 제거·추가 모두 거부) |
| 4 | Actor `component_weights` | 각 relation type이 요청 weight 안인지 대조 |
| 5 | Label `max_sources` | replay source 수가 budget 초과면 거부 |
| 6 | Sanctions `current_list_snapshot_ref` | replay SLS source artifact_ref와 대조 |
| 7 | Common-funder `block_range` | request block_range와 정확 일치(번들에 block_range 추가) |
| 8 | artifact URI ↔ content SHA | `IntelSourceRecord`가 `artifact://sha256/<h>`의 h == `content_sha256` 강제(불일치 `decode_failed`) |

8종을 모두 회귀 테스트로 고정했다(unit 34). 네 verifying fixture의
`results[].value`·canonical hash는 여전히 불변이다.

## 5.3 인접 변형 6건·strict 모델 정정

재재검토에서 일대일 대응·strict 모델의 인접 변형 6건이 여전히 complete로
확인돼 마저 닫았다.

| # | 결함 | 정정 후 |
|:---:|:---|:---|
| 1 | sanctions 요청 action이 일대일 대응이 아님(removal→designation 복제) | 요청 ref를 `(date, action)`로 parse해 replay action multiset과 **정확 일치** |
| 2 | label source record 1개 제거가 complete | `_require_artifact_binding`을 subset → **정확 집합 일치**로 강화 |
| 3 | actor component 중복(한 weight 미커버) | relation type multiset == `component_weights` 정확 일치 |
| 4·5 | label role·actor hub role 빈 문자열 | 사실 판정 문자열(dataset/ens/community_config/hub)을 모두 `NonEmptyString`으로 |
| 6 | `2022-99-99` 등 비달력 날짜 허용 | `CalendarDate`가 정규식 + `date.fromisoformat` 실제 달력 검증 |
| P2 | `source_role` 임의 문자열 허용 | 계약 6개 값 `Literal`(official_record/first_party/provider_label/public_report/onchain_registry/heuristic) |

6종을 회귀 테스트로 고정했다(unit 40). 네 verifying fixture의 canonical
hash는 여전히 불변이다.

## 6. 상태 경계와 다음 Gate

- Fixture: 4개 `검증 중` / common-funder `candidate` 유지(확정 승격 없음).
- Benchmark: 11 유지(자동화 승격 없음).
- 전체 게이트: 514 tests PASS, fixture 18, schema 52 probes, traceability 1656 links, security 204 files, TASK-015 negative oracle 30×2·독립 Verifier
  4×2·analyzer 독립 검증 4 fixtures PASS.
- **다음(별도 Gate): live source adapter·Terms 확정, common-funder bounded
  prehistory·service exclusion, fixture `확정`·Benchmark 자동화 승격.**

## 7. Related Documents

- **Technical_Specs**: [intel_context I/O 계약](../03_Technical_Specs/18_TASK_015_INTEL_CONTEXT_IO_CONTRACT.md)
- **QA_Validation**: [독립 Verifier 보고서](./51_TASK_015_INDEPENDENT_VERIFIER_REPORT.md) · [Provenance Hardening Receipt](./52_TASK_015_PROVENANCE_HARDENING_RECEIPT.md)
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) · [Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md)
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md)
