# TASK-015 Common-funder Completeness 계약·Blocker 기록
> Created: 2026-07-30 20:45
> Last Updated: 2026-07-30 20:45
> Status: docs-only Contract · Blocked on live/archive Source Gate · Common-funder Candidate 유지

## 1. 목적과 경계

이 문서는 `FX-ACTOR-COMMON-FUNDER-001`의 `find_common_funder` 결과를
`candidate`에서 승격하려면 무엇을 증명해야 하는지를 docs-only로 고정한다.
코드·fixture·replay·플래그를 변경하지 않으며, 승격 판정도 하지 않는다.
현재 데이터로는 승격이 불가하다는 **blocker**를 명시하고, common-funder를
`candidate`/문제 coverage `assisted`로 유지하는 근거를 남긴다.

이 계약은 새 사실을 만들지 않는다. bounded prehistory·service exclusion은
**reviewed archive 데이터가 확보된 뒤에만** `true`로 전환할 수 있고, 그
전까지 어떤 플래그도 근거 없이 참으로 바꾸지 않는다(anti-P1 원칙:
AI 가설을 confirmed fact로 승격 금지).

## 2. 현재 fixture 상태(불변)

| 항목 | 값 |
|:---|:---|
| Fixture | `FX-ACTOR-COMMON-FUNDER-001` (`candidate` 0.1) |
| seed | `0xb66cd966670d962c227b3eaba30a872dbfb995db` |
| subjects | 4개 (`0xa1b44d…`, `0xc4e04a…`, `0x46e0be…`, `0x8765a3…`) |
| relation | 각 subject에 `direct_seed_output`, `amount_raw` `7738250000000000000000` |
| source | `SRC-INTEL-FUNDER-REMERGE` · `DS-EVM-RPC-ARCHIVE` · `onchain_registry` |
| source_fixture_ref | confirmed `FX-FLOW-REMERGE-001` |
| block_range | `16905356`–`16920507` |
| coverage_gaps | `bounded_prehistory_unavailable`, `service_exclusion_unavailable` |
| `initial_inflow_complete` | `false` |
| `service_exclusion_complete` | `false` |
| `common_funder_assessment` | `candidate` |
| `ownership_assessment` / `coordination_assessment` | `not_assessed` |

analyzer는 이미 completeness 미증명을 `partial`로 보존하고, 독립 Verifier와
`verifying` 승격 검토는 미착수(pending)다.

## 3. Bounded prehistory 조회 범위와 완결성 기준

**조회 범위(bounded window).** 각 subject 주소별로 시작 경계와 종료 경계를
명시적으로 고정한 연속 inbound 구간이다.

- 종료 경계: 해당 subject가 seed로부터 `direct_seed_output`을 받은 block.
- 시작 경계는 아래 두 주장 강도에 따라 달라진다.

**두 주장 강도를 분리한다.** 고정 lookback은 "최초·유일 funder"를 증명하지
못한다. `prehistory_lookback_blocks` **이전**의 입금이 미확인 상태로 남으므로,
그 앞에 다른 funder가 있었을 가능성을 배제할 수 없다. 따라서 두 주장을 별도
플래그로 구분한다.

| 시작 경계 | 허용 주장 | 플래그 | 최초·유일 주장 |
|:---|:---|:---|:---:|
| 검증된 first-seen block | 최초·유일 funder | `initial_inflow_complete: true` 가능 | 허용 |
| 고정 `prehistory_lookback_blocks` | window 내 연속성만 | `bounded_prehistory_complete`만 | **금지** |

**연속성 요건.** window 안에서 subject로 들어온 모든 value 이동을 gap 없이
스캔해야 한다. replay는 `continuous_gap_scanned: true`이어야 하며,
`selected_transactions`(선택 TX만) scope는 완결성 증거로 사용할 수 없다.

**최초·유일 funder 판정(`initial_inflow_complete: true`) 조건 — 네 subject 전부 충족.**

1. 시작 경계가 **검증된 first-seen block**이다. subject의 first-seen 이전
   inbound가 존재하지 않음을 replay가 입증한다(고정 lookback은 이 조건을
   충족하지 못한다). 실제 archive 캡처 시 first-seen의 시작점은 **chain
   genesis** 또는 **검증 가능한 주소 생성 시점**(EOA는 genesis 기준 연속
   스캔, 컨트랙트는 생성 TX block)으로 명시한다.
2. first-seen부터 seed 입금까지 연속 inbound 스캔이 gap 없이 완료됐다
   (`continuous_gap_scanned: true`).
3. 그 구간에서 seed 이전에 subject를 funding한 **비-seed inbound value 이동이
   0건**이다(= seed가 최초·유일 funder).
4. 위 사실이 replay 자체의 source record에서 재계산 가능하다(request
   allowlist에서 합성 금지).

**bounded prehistory 판정(`bounded_prehistory_complete: true`) — 약한 주장.**
first-seen을 검증하지 못하고 고정 lookback window만 확보한 경우, window 내
연속성과 비-seed inbound 0건까지만 주장할 수 있고 **최초·유일 funder는 주장할
수 없다.** 이때 `initial_inflow_complete: false`를 유지하며
`common_funder_assessment`는 `candidate`를 넘지 못한다.

어느 조건이든 미충족이면 해당 플래그를 `false`로 유지한다.

## 4. Service / faucet / paymaster 제외 기준

**목적.** seed가 공용 서비스(거래소 hot wallet·faucet·paymaster·batch
disperser)라면 여러 주소로의 direct funding은 공모·공통 소유의 증거가 아니다.
따라서 seed의 비서비스 여부를 별도 reviewed source로 분류해야 한다.

**제외 신호(하나라도 해당 시 relations를 common-funder 증거에서 제외).**

- reviewed service registry / label source에서 seed가 service·faucet·
  paymaster·mixer로 식별됨.
- bounded window에서 seed의 outbound fan-out이 사전 고정한 임계값을 초과하는
  분산 지급 패턴(단순 heuristic이며 확정 사실이 아님 → `assessment`로만 표기).

**판정(`service_exclusion_complete: true`) 조건.**

1. reviewed source가 seed의 service 여부를 명시적으로 판정했다(license/Terms
   clearance 포함).
2. service로 판정되면 relations를 제외하고 `common_funder_assessment: failed`
   또는 `not_applicable`로 남긴다.
3. non-service로 판정돼야 direct edges를 common-funder 후보로 유지한다.

source가 없거나 불명확하면 `service_exclusion_complete: false`를 유지하고
`assessment`를 확정 사실로 올리지 않는다.

## 5. 필요한 archive 데이터와 source 역할

`source_role`은 기존 허용 어휘(`official_record` · `first_party` ·
`provider_label` · `public_report` · `onchain_registry` · `heuristic`)만
사용하며 새 값을 도입하지 않는다.

| 데이터 | 목적 | source_role | 현재 확보 |
|:---|:---|:---|:---:|
| subject별 bounded window 연속 inbound 스캔 | 최초·유일 funder 증명 | `onchain_registry` (archive RPC, 연속 scope) | ✗ |
| seed service 분류 판정 | faucet/paymaster/service 제외 | `official_record`·`provider_label`(reviewed registry), heuristic 신호는 `heuristic` | ✗ |
| 위 데이터의 content-addressed artifact·SHA-256 | 무결성·독립 재계산 | 각 source record | ✗ |

**inbound 자산 범위.** 연속 inbound 스캔은 subject로 들어오는 funding을
누락 없이 포착해야 하므로 아래 세 경로를 **모두 포함**한다.

- native ETH 이동(외부 TX의 `value`),
- internal call로 전달된 ETH(trace의 value-bearing internal transfer),
- ERC-20 `Transfer`(subject가 `to`인 토큰 입금).

셋 중 하나라도 스캔에서 빠지면 "비-seed inbound 0건"을 주장할 수 없으므로
완결성 플래그를 `false`로 유지한다.

두 데이터 모두 새 **continuous-scope reviewed/archive 캡처**가 필요하며,
confirmed `FX-FLOW-REMERGE-001` replay(선택 TX scope)에는 존재하지 않는다.

## 6. partial · failed · negative oracle 조건

**partial(현재 상태 유지).** direct seed edges는 confirmed지만
`initial_inflow_complete` 또는 `service_exclusion_complete`가 `false`이면
`common_funder_assessment: candidate`, ownership·coordination는
`not_assessed`, `partial_conditions`에 미확보 사유를 남긴다.

**failed.**

- 비-seed inbound를 seed funding으로 계산.
- direct funding을 공통 소유·공모로 승격.
- 공개 정보상 service인 seed를 제외하지 않음.
- gap 있는(불연속) 스캔을 완결로 처리.
- source 없는 prehistory를 confirmed fact로 사용.

**negative oracle.** 기존 6개(scope·금액·truth-promotion, 2회 결정성)에 더해
완결성 Gate 진입 시 아래를 추가 고정한다.

1. window 내 seed 이전 비-seed inbound 1건 → completeness `false`·승격 차단.
2. 불연속(`continuous_gap_scanned:false`) 스캔 → 완결 처리 거부.
3. service로 분류된 seed → relations 제외.
4. source 없는 합성 prehistory → 거부.

모든 오류 경로는 고정 `ErrorCode`를 재사용한다: 완결성 미증명은
`evidence_incomplete`(retryable), request↔replay binding 불일치는
`reconciliation_failed`(non-retryable). 새 public error code를 추가하지 않는다.

## 7. 제품 계약·Verifier Migration Gate

현재 `intel_context` analyzer와 독립 Verifier는 common-funder를 **의도적으로
`partial`로 고정**하고, `initial_inflow_complete`·`service_exclusion_complete`
같은 완결성 신호를 hardcoded `false`로 취급한다. 따라서 §5 데이터를 확보하는
것만으로는 승격할 수 없으며, 아래 migration Gate를 **순서대로** 통과해야 한다.
어느 단계도 건너뛰지 않는다.

1. **replay evidence 구조 추가.** source-replay/evidence에 subject별 연속
   inbound 스캔·seed 분류 evidence 구조(§3·§4)를 실제로 추가하고 content-
   addressed artifact로 고정한다.
2. **계약·Schema 갱신.** `intel_context` I/O 계약(doc 18)과 `find_common_funder`
   result·replay Schema를 완결성 필드까지 확장하고, family/cross-family probe를
   갱신한다. `common_funder_assessment`에 `failed`·`not_applicable` 같은 새
   enum 값을 도입한다면 이 Schema migration 대상에 포함한다. 새 public
   `ErrorCode`는 도입하지 않는다.
3. **analyzer hardcoded false 제거.** analyzer가 완결성을 replay evidence에서
   raw-first로 유도하도록 바꾸되, 미증명 시 `partial`을 유지하는 경로는
   보존한다(§6 partial/failed).
4. **독립 Verifier ready set 편입.** common-funder를 Verifier ready set에 넣어
   edges·완결성 플래그를 두 번째 독립 코드 경로에서 raw-first로 재계산한다.
5. **canonical hash·Verification Receipt 재고정.** analyzer hash ↔ 독립
   Verifier hash 일치와 2회 결정성을 새 Verification Receipt로 고정한다.
6. **이후에만 승격 검토.** 위 5단계를 통과한 뒤에야 `candidate → verifying →
   confirmed` 및 Benchmark 자동화 승격을 **별도 Gate**에서 판정한다(이 문서는
   그 판정을 하지 않는다).

## 8. Blocker: 현재 승격 불가

- confirmed `FX-FLOW-REMERGE-001` raw replay의 scope는
  `selected_transactions_and_exact_blocks` · `continuous_gap_scanned: false`
  이므로 네 subject의 연속 inbound 이력과 seed service 분류가 **없다.**
- 따라서 §3·§4의 완결성 조건을 현재 confirmed 오프라인 소스만으로는
  증명할 수 없다.
- 완결에 필요한 continuous-scope archive 캡처와 seed 분류 source는
  **live/archive source Gate**에 해당하며, 이는 공식 대회 Rules·원문 Terms가
  허용될 때까지 후순위로 유지된다([Promotion Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) §2 Retrieval permission).

**결론.** common-funder는 `candidate`(fixture)·`assisted`/`unsupported`(문제
coverage)로 유지한다. Benchmark automated 집계는 변동 없다
(12 automated / 4 assisted / 14 unsupported). Rules·Terms 확정 후 별도 Gate로
§5 데이터를 캡처하고 §7 migration Gate를 통과한 뒤에만 §3·§4·§6 기준으로
재진입한다.

## 9. Related Documents

- **QA_Validation**: [Common-funder Fixture](./fixtures/FX-ACTOR-COMMON-FUNDER-001/README.md) - candidate 근거와 남은 Gate
- **QA_Validation**: [Source FLOW fixture](./fixtures/FX-FLOW-REMERGE-001/README.md) - 선택 TX scope raw replay
- **QA_Validation**: [Live Source·Terms 승격 Readiness](./54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md) - permission·retrieval·fact Gate 분리
- **QA_Validation**: [비격리 Fixture 승격 Receipt](./56_TASK_015_NON_QUARANTINED_PROMOTION_RECEIPT.md) - 세 confirmed fixture 근거
- **QA_Validation**: [예상문제 Benchmark 보고서](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 12·4·14 coverage
- **Technical_Specs**: [intel_context I/O Contract](../03_Technical_Specs/18_TASK_015_INTEL_CONTEXT_IO_CONTRACT.md) - `find_common_funder` 결과 계약
- **Logic_Progress**: [Coverage 확장 Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - `TASK-015` Wave 4
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - `TASK-015` 진행·검증 기록
