# TASK-013 NFT·Proxy Analyzer 독립 Verification Receipt
> Created: 2026-07-29 20:55
> Last Updated: 2026-07-29 21:40
> Status: canonical hash 일치는 유효 · **`확정` 승격은 철회**, 사유는
> [P1 정정 Receipt](./37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md) 참고

> **정정 안내(2026-07-29 21:40):** 이 문서가 근거로 삼은 canonical hash
> 일치는 여전히 유효하지만, hash 일치만으로는 subject/proxy 결합 누락과
> receipt·block 정합 누락 같은 P1 결함을 드러내지 못한다는 점이 이후
> 리뷰에서 확인됐다. §6·§7의 `확정` 승격 판정은 철회하고 fixture는
> `검증 중`으로 되돌렸으며 Benchmark automated는 7로 유지한다. 자세한
> 내용은 [P1 정정 Receipt](./37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)를
> 참고한다.

## 1. 목적과 판정

TASK-013 사용자 구현 승인(2026-07-29 20:19) 이후 구현한 NFT·Proxy 제품
analyzer(`scan_tool.slices.evm_special`)가 `task_013_independent_verifier.py`와
독립적으로 동일한 raw-first 결론에 도달하는지 검증한다. 두 코드는 서로
import하지 않으며, 이 문서는 두 결과가 canonical hash 단위로 정확히
일치함을 기록한다. ERC-1155는 서로 다른 대상 주소의 Single/Approval과
Batch를 두 subject-scoped 요청으로 각각 실행한 뒤, 검증 Gate에서만 두
결과를 결합해 fixture 전체 hash와 비교한다.

**판정: 세 `검증 중` fixture 모두 analyzer가 `complete`를 산출했고, 그
결과의 canonical SHA-256이 독립 Verifier가 이미 evidence.json에 고정한
`calculated_fact_sha256`과 정확히 일치했다. 두 번의 결정적 실행도
통과했다.**

## 2. 독립성 경계

- `slices/evm_special.py`는 `task_013_independent_verifier.py`를
  import하지 않는다. 두 모듈은 서로 다른 파싱 방식(raw dict vs
  Pydantic 타입 모델)으로 같은 raw-replay.json을 각자 재해석한다.
- `domain/evm_special.py`의 reviewed replay 모델은 raw JSON 구조를 그대로
  받고, verifier처럼 expected.json을 계산 입력으로 사용하지 않는다.
- ERC-1155 Batch는 verifier와 마찬가지로 설치된 `eth-abi` decoder를
  사용하지만, 호출 지점과 전후 검증 로직은 analyzer에서 새로 작성했다.
- `scripts/verify_task_013_analyzer_independent_verification.py`는
  analyzer 실행 결과의 canonical hash를 evidence.json에 이미 고정된
  `calculated_fact_sha256`과 비교하며, verifier 모듈을 import하지 않는다.

## 3. 검증 결과

| Fixture | analyzer 상태 | canonical hash | 고정된 verifier hash | 일치 |
|:---|:---:|:---|:---|:---:|
| `FX-EVM-NFT-721-001` | complete | `a2b879fb7aa9f157168b349875decff86d3a1d685792332c9eff1af8ca0e5e74` | 동일 | pass |
| `FX-EVM-NFT-1155-001` | complete × 2 subject-scoped requests | `0caf8a09994abbff71cb4afddf9bb6e11fa5411ef0870c27d1a92ea324aade91` | 동일 | pass |
| `FX-EVM-PROXY-001` | complete | `f0683ef2167e2e7799891a66e0b065300842fd46de5d63b84ebe440ee2f58d93` | 동일 | pass |

추가로 확인한 조건:

- 세 fixture 모두 analyzer 결과가 `expected.json`의 채점 필드와
  Python dict 동등성으로 정확히 일치한다(`standard`/`movements`/
  `approvals`, `single_case`/`batch_case`, `pattern`/`change`/`admin`/
  `beacon`). ERC-1155는 두 요청 결과를 검증기에서 결합한 뒤 대조한다.
- 두 번 실행한 `AnalysisResult.to_contract_dict()`가 완전히 동일해
  결정적이다.
- `scan analyze --request ... --evidence ...` CLI로 세 fixture 모두
  `COMPLETE`·`schema_version 0.2`·checkpoint 1개로 저장되고 `scan show`가
  같은 결과를 재현한다(`tests/integration/test_evm_special_cli.py`).
- Proxy의 `implementation_before` 스냅샷을 제거하면 CLI가 `PARTIAL`·
  exit 3·`archive_required`를 반환하고 확보한 사실을 보존한다.
- `scan analyze`를 KeyboardInterrupt로 중단한 뒤 `scan resume`이 저장된
  replay artifact에서 `resumed yes`로 완료한다(네트워크 재호출 없음).

## 4. 계약 확장 경계

- Analysis I/O `schema_version`은 계속 `{"0.1", "0.2"}`이며, `0.2`는
  기존 `evm_core`에 신규 `evm_special`(`analysis_type`, discriminated
  request/result variant)을 더한 것으로 `evm_core` 자체는 변경하지 않았다.
- 새 공개 오류 코드는 추가하지 않았다. `decode_failed`·
  `reconciliation_failed`·`source_unavailable`·`archive_required`·
  `rule_restricted` 기존 `ErrorCode` enum만 재사용하고, 표준별 세부
  사유는 `message`/`stage` 텍스트로 전달한다.
- `FixtureRequirementId` 패턴과 정적 `analysis-result.schema.json`의
  `fixture_requirement_ids` 정규식에 `NFT721`·`NFT1155`·`PROXY` 접두를
  추가했다(기존 `DEX|AUTH|FREEZE|BASIC|TOKEN`은 그대로).
- 공유 `raw_values_are_uint256` 검증기가 `ids_raw`/`amounts_raw`처럼
  `_raw`로 끝나는 키의 **배열** 값도 각 원소를 canonical uint256
  decimal string으로 검사하도록 확장했다(이전에는 스칼라만 지원해
  Batch 배열에서 오탐이 발생했다).
- `docs/05_QA_Validation/schemas/operations-contract.schema.json`의
  `AnalysisType` enum에도 `evm_special`을 추가해 Operations 계약과
  runtime을 동기화했다.
- `check_task_012_analysis_contract_proposal.py`의 승인된 analysis_type
  집합을 TASK-012 4종에서 TASK-013 승인을 반영한 5종으로 갱신했다.

## 5. 산출물

- `src/scan_tool/domain/evm_special.py` — reviewed replay 모델
  (`NftActivityReplay`, `ProxyHistoryReplay`, callable discriminator)
- `src/scan_tool/domain/analysis_request.py` — `EvmSpecialQueryKind`,
  `NftActivityInputs`, `ProxyHistoryInputs`, `EvmSpecialAnalysisRequest`
- `src/scan_tool/domain/analysis_result.py` — `EvmSpecialComplete/Partial/FailedAnalysisResult`
- `src/scan_tool/slices/evm_special.py` — `analyze_evm_special_replay`
  (nft_activity: ERC-721/ERC-1155, proxy_history: EIP-1967)
- `src/scan_tool/application/cli_runtime.py` — `EvmSpecialAnalysisRequest`
  디스패치와 `EVM_SPECIAL_REPLAY_STAGE` checkpoint
- `src/scan_tool/application/expected_problem_benchmark.py` —
  `EVM-NFT-001`·`EVM-PROXY-001`을 automated로 승격
- `docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json` —
  두 문제의 executable fixture 등록
- `docs/05_QA_Validation/fixtures/FX-EVM-{NFT-721,NFT-1155,PROXY}-001/analysis-request.json`
  및 ERC-1155 `analysis-request-batch.json` — subject-scoped 요청
- `docs/05_QA_Validation/schemas/analysis-request.schema.json`,
  `analysis-result.schema.json`, `operations-contract.schema.json` — 갱신
- `tests/unit/test_evm_special_slice.py` — complete·partial·failed 18개
- `tests/integration/test_evm_special_cli.py` — persist·partial·resume 5개
- `scripts/verify_task_013_analyzer_independent_verification.py` —
  analyzer canonical hash와 고정 verifier hash 비교, `scripts/verify.py`에 연결

## 6. 확정(Confirmed) 승격 판정

[TASK-013 Fixture 승격 검토](./35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) §2가
정의한 `확정` 잔여 Gate(6~10) 다섯 항목을 모두 다시 확인한다.

| # | 잔여 Gate | 근거 |
|:---:|:---|:---|
| 6 | Analysis I/O 계약 정식 결정과 Schema 반영 | 대안 B(`evm_special`) 확정, `analysis-request/result.schema.json` 갱신·검증 통과 |
| 7 | 사용자가 확인한 UI Preview 승인 | 2026-07-29 20:19 "TASK-013 UI Preview를 승인합니다" 명시 승인 |
| 8 | Context Receipt `PASS` | Backlog TASK-013 Context Receipt 기록 완료 |
| 9 | 사용자 구현 승인 기록 | "TASK-013 analyzer 구현을 진행해 주세요" 명시 승인 |
| 10 | Python decoder 구현과 독립 Verification Receipt | `slices/evm_special.py` 구현, 본 문서의 canonical hash 일치로 독립 검증 완료 |

다섯 항목이 모두 닫혔다고 판단해 당시 세 fixture를 `검증 중`에서
`확정`으로 승격했었다. **이 판정은 이후 리뷰에서 철회됐다** — canonical
hash 일치는 analyzer가 fixture 3개에 대해 결정적으로 같은 값을 낸다는
것만 보장하며, 요청 대상(subject/proxy_address)이 실제로 결합됐는지나
log/snapshot이 receipt·block과 정합하는지는 별도로 검증하지 않았기
때문이다. 자세한 결함 목록과 수정 내역은
[P1 정정 Receipt](./37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)를 참고한다.

## 7. 상태 경계와 다음 Gate (철회됨 — §37 참고)

- ~~Fixture 3개: `검증 중` → `확정`으로 승격.~~ → 철회, `검증 중` 유지.
- Analysis I/O: `0.2`에 `evm_special` 추가, `evm_core`·기존 `0.1` 분석기
  결과는 변경하지 않았다. (변경 없음, 유효)
- ~~Benchmark 자동화: 7 → 9문항.~~ → 철회, 7 유지.
- 전체 게이트: 이 문서 작성 시점 기준 419 tests PASS, fixture 10 PASS.
  P1 수정 이후 최신 결과는 [P1 정정 Receipt](./37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md)를
  참고한다.

## 8. 365 글로벌 평가 기준

| 기준 | 판정 |
|:---|:---|
| Functionality | 세 fixture의 raw-first 결과가 독립 Verifier의 고정 hash와 정확히 일치, CLI complete/partial/resume 재현 |
| Potential Impact | NFT·Proxy 자동화가 목표(대회 자동화 범위 7→9문항)이나, 자동 승격은 P1 정정·재검토 완료 후로 보류 |
| Novelty | 승인된 expected.json 값을 복사하지 않고 raw에서 두 번째로 재계산 |
| UX | 기존 CLI 명령·종료 코드·checkpoint 경계 재사용, 신규 플래그 없음 |
| Open-source | 신규 dependency 없음, 기존 `eth-abi`/`eth-utils`만 재사용 |
| Business Plan | N/A — 대회 준비 analyzer 구현 |

공개 온체인 raw replay만 사용했으며 제3자 구현 코드를 복제하지 않았다.
NFT 자산 가치·소유권 분쟁·거래 의도·upgrade 악성 여부는 `not_assessed`로
유지한다.

## 9. Related Documents

- **Technical_Specs**: [TASK-013 분석 계약](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - `evm_special` 대안 B 계약
- **UI_Screens**: [TASK-013 NFT·Proxy UI](../02_UI_Screens/07_TASK_013_NFT_PROXY_UI.md) - 사용자 승인된 Preview
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-013 진행 상태
- **QA_Validation**: [TASK-013 Fixture 승격 검토](./35_TASK_013_FIXTURE_PROMOTION_REVIEW.md) - `검증 중` 승격 판정
- **QA_Validation**: [TASK-013 독립 Verifier 보고서](./34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md) - 고정된 fact hash의 최초 근거
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 상태 registry
