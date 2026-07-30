# TASK-016 Bridge Raw Replay 준비 보고서
> Created: 2026-07-30 23:30
> Last Updated: 2026-07-31 03:00
> Status: Live Replay·Negative Oracle·Independent Verifier Passed (P1 ×2 Remediated) · Candidate

## 1. 목적

`FX-SVC-BRG-001`의 두 체인·두 provider raw replay를 안전하게 실행할
bounded runner와 candidate package를 준비하고, 두 source role의 live
replay·SHA·decoded match 결과를 기록한다. negative oracle·독립 Verifier가
남아 있으므로 fixture는 candidate를 유지한다.

## 2. 구현 범위

| 산출물 | 책임 |
|:---|:---|
| `task_016_bridge_replay.py` | Base/Ethereum 고정 request set·event decode·양단 reconciliation |
| `replay_task_016_bridge.py` | `--execute`·Rules·chain별 endpoint Gate와 안전한 출력 |
| `FX-SVC-BRG-001` package | candidate input/expected/evidence와 실행된 replay manifest |
| unit tests | bounded allowlist·exact block·양단 facts·recipient mismatch 거부 |

제품 `bridge_transfer` analyzer, Analysis I/O, Benchmark dispatch는 변경하지
않았다.

## 3. Request set

각 provider role은 Base와 Ethereum에 아래 네 method를 실행한다. role당
최대 8회, 두 role 전체 최대 16회다.

1. `eth_getTransactionByHash`
2. `eth_getTransactionReceipt`
3. `eth_getBlockByNumber`
4. exact-block·SpokePool·topic0 `eth_getLogs`

send/sign/mutation, trace, address-wide scan, Explorer API는 포함하지 않는다.

## 4. Endpoint 계약

| Role | Base | Ethereum |
|:---|:---|:---|
| primary | `SCAN_BASE_PRIMARY_RPC_URL` | `SCAN_EVM_PRIMARY_RPC_URL` |
| verify | `SCAN_BASE_VERIFY_RPC_URL` | `SCAN_EVM_VERIFY_RPC_URL` |

네 값은 HTTPS 환경변수로만 읽는다. URL userinfo를 거부하며 endpoint·key를
report·fixture·로그에 저장하지 않는다.

Base managed RPC와 Base official public RPC를 각각 primary/verify로
설정했다. Ethereum은 managed RPC와 supporting explorer-backed JSON-RPC를
교차 사용했다. endpoint·credential은 로컬 `.env.local`에만 있으며
report·fixture·로그에는 저장하지 않았다.

QuickNode Ethereum은 네 capability 모두 `rate_limited`였고, PublicNode
Ethereum은 transaction·receipt·block 성공 후 exact-block `eth_getLogs`가
HTTP 403이었다. 두 실패는 성공으로 추론하지 않았으며 최종 primary
Ethereum replay는 Blockscout의 read-only JSON-RPC로 다시 실행했다.

## 5. Decode·reconciliation Gate

- transaction hash·block exact binding
- receipt transaction/block/status와 SpokePool log 존재
- block response number exact binding
- log address·topic0·transaction exact binding
- Across V3 source/destination event의 deposit ID, depositor, recipient,
  amounts, deadline, message exact comparison
- origin `8453`, destination `1`, deposit ID `2395968`
- `input_raw - output_raw = 867713010029593`

한 필드라도 다르면 `invalid_response`로 종료하고 complete를 만들지 않는다.

## 6. 현재 검증

| Role | Base | Ethereum | Pair |
|:---|:---|:---|:---|
| primary | 4/4 complete | 4/4 complete | decoded match |
| verify | 4/4 complete | 4/4 complete | decoded match |

두 role의 reconciled facts도 동일하다.

```text
live calls:       16 read-only
raw SHA-256:      16 pinned
decoded match:    primary/verify PASS
input/output:     330000000000000000 / 329132286989970407
fee difference:   867713010029593
focused unit:     6 PASS
full Gate:        552 tests, fixture 19, Schema 52, links 1862, security 213 PASS
```

## 7. Gate 상태

- [x] Base primary·verify endpoint를 로컬 secret 환경에 준비한다.
- [x] 운영자 승인에 따라 source mode를 `allowed`로 확인한다.
- [x] primary role 8개 read-only call을 실행한다.
- [x] verify role 8개 read-only call을 실행한다.
- [x] 16 capability raw SHA와 retrieved_at을 package에 pin한다.
- [x] primary/verify decoded facts가 동일함을 기계적으로 대조한다.
  PR 리뷰(P1)에서 이 대조를 실제로 수행하는 코드가 없었음이 지적됐다. §9에서
  `assert_matching_provider_facts`를 추가하고 실제 재실행으로 검증했다.
- [x] candidate 상태를 유지한 채 실제 호출 결과를 기록한다.
- [ ] Phase B negative oracle을 구현한다.
- [ ] Phase C 독립 Verifier와 verifying 판정을 수행한다.

## 8. P1 Remediation (PR #101 리뷰 반영)

리뷰에서 두 P1이 지적됐다. 둘 다 코드로 정정하고 실제 재실행으로 확인했다.

**P1 — cross-provider 대조 코드 부재.** 기존 러너는 role 하나씩만 실행하고
`bridge_pair_facts()`도 같은 role의 Base↔Ethereum만 정합했다. primary와
verify를 비교하는 코드가 없는 채로 `cross_provider_decoded_match: true`를
기록한 것은 근거 없는 주장이었다.

- `assert_matching_provider_facts()`를 추가해 두 role의 canonical facts를
  키 단위로 비교하고 불일치 시 어떤 필드가 다른지 예외로 보고한다.
- `replay_task_016_bridge.py`에 `--role both`를 추가해 한 번의 실행에서
  primary·verify 네 조합(2 chain × 2 role)을 모두 캡처하고, 두 role의
  `bridge_pair_facts()` 결과에 위 함수를 적용한 뒤에만
  `cross_provider_decoded_match`를 출력한다.
- 회귀 테스트 `test_cross_provider_matching_facts_are_accepted`,
  `test_cross_provider_fact_mismatch_is_rejected`를 추가했다.
- **실제 재실행**: `--role both --execute --rules-status allowed`를 다시
  실행해 16 read-only call·`status: complete`·`decoded_pair_match: true`·
  `cross_provider_decoded_match: true`(코드 계산)를 확인했다. 4개 provider
  중 3개(`PROVIDER-BASE-PRIMARY`·`PROVIDER-BASE-VERIFY`·
  `PROVIDER-ETHEREUM-VERIFY`)는 raw SHA-256이 기존 pin과 완전히 일치했다.
  `PROVIDER-ETHEREUM-PRIMARY`는 raw 응답 바이트가 달랐지만(현재
  `SCAN_EVM_PRIMARY_RPC_URL`이 가리키는 provider의 JSON 포맷 차이) decoded
  summary는 기존 pin과 동일했다. 따라서 기존 raw_sha256 pin은 그대로 두고
  ([provider-replay.json](./fixtures/FX-SVC-BRG-001/provider-replay.json)의
  `cross_provider_verification` 필드로 재검증 근거를 남겼다), 최종 raw SHA
  재고정은 독립 Verifier Gate에서 다시 캡처할 때 함께 처리한다.

**P1 — Across 공통 파라미터 검증 누락.** `required_equal`에
`exclusive_relayer`가 없었고 `outputToken`은 비교 없이 제외돼, 양단
`exclusiveRelayer`가 달라도, 그리고 source `outputToken=0x0`(공식 기본 매핑
사용 신호)일 때 destination이 임의 토큰이어도 통과할 수 있었다.

- `required_equal`에 `exclusive_relayer`를 추가했다.
- `output_token`이 `0x0`(zero address)이면 pinned `DEFAULT_OUTPUT_TOKEN_MAP`
  (`BASE_WETH → ETHEREUM_WETH`)과 destination의 실제 `output_token`을
  대조하고, `0x0`이 아니면 source·destination `output_token`이 정확히
  같아야 한다. 두 경우 모두 불일치 시 거부한다.
- 회귀 테스트 `test_exclusive_relayer_mismatch_is_rejected`,
  `test_zero_output_token_must_match_pinned_default_mapping`을 추가했다.

**검증.** `uv run pytest tests/unit/test_task_016_bridge_replay.py` 10 PASS
(신규 4건 포함), `scripts/verify.py` 전체 재통과, `ruff check`/`ruff format
--check` 클린.

topic0 상수(`V3FundsDeposited`/`FilledV3Relay`)는 재검토 결과 실제 ABI
signature와 일치함이 확인됐다(잔여 리스크 해소).

## 9. Negative Oracle Gate

doc 21 §6의 7개 negative oracle 범주(오매칭·domain 충돌·tolerance 남용·
evidence 누락·scope 합성·heuristic 승격·amount 공식 불일치)를 완전한
`bridge_transfer` analyzer 없이 synthetic offline case로 먼저 고정한다.
TASK-014의 `flow_path` 대비 동일한 선례를 따른다: 독립 작성된 참조
classifier(`_evaluate_bridge`)가 fixture의 결정 경계를 얼려두고, 이후
analyzer 구현이 이 경계와 일치하는지는 별도 analyzer-independent-verification
Gate에서 확인한다.

| Oracle ID | 범주(doc 21 §6) | 결과 |
|:---|:---|:---:|
| `OR-BRIDGE-SCOPE-SYNTHESIS` | 5. request에 없는 주소·체인 합성 | failed |
| `OR-BRIDGE-DOMAIN-COLLISION` | 6. domain 분리 없이 같은 key 연결 | failed |
| `OR-BRIDGE-WRONG-DEPOSIT-MATCH` | 1. 유사 금액 다른 전송 오매칭 | failed |
| `OR-BRIDGE-HEURISTIC-NOT-PROMOTED` | 2. 결정적 키 없이 confirmed 승격 시도 | partial |
| `OR-BRIDGE-DESTINATION-EVIDENCE-MISSING` | 4. 도착 evidence 미확보를 complete 처리 | partial |
| `OR-BRIDGE-TOLERANCE-WITHOUT-MAPPING` | 3. 공식 mapping 없이 임의 tolerance 승격 시도 → 승격 거부·candidate 유지 | partial |
| `OR-BRIDGE-AMOUNT-FORMULA-MISMATCH` | 7. 공식 fee/asset mapping 있어도 정수 공식 불일치(실제 모순) | failed |
| `OR-BRIDGE-COMPLETE-MATCH` | synthetic positive control(실제 raw replay를 읽지 않음, 결정 경계 회귀 방지용) | complete |

manifest: [`task-016-bridge-negative-oracles-v0.1.json`](./oracles/task-016-bridge-negative-oracles-v0.1.json).
구현: `src/scan_tool/application/task_016_bridge_negative_oracles.py`,
`scripts/verify_task_016_bridge_negative_oracles.py`(`scripts/verify.py`에
연결), `tests/unit/test_task_016_bridge_negative_oracles.py`.

**검증.** `PASS 8 TASK-016 Bridge negative oracles twice (offline
deterministic)`. 전체 게이트 553 passed·traceability·security 유지.

## 10. Independent Verifier Gate

`raw-replay.json`을 pre-decoded 요약(`event`)에서 진짜 raw ABI 로그
(`log.topics`·`log.data`, address·block·tx 바인딩 필드)로 교체했다. 기존
저장분은 이미 디코딩된 필드만 담고 있어 candidate-capture 모듈과 같은
결과를 재확인하는 것 이상을 하지 못했다. 진짜 raw bytes가 있어야 별도로
작성된 코드가 ABI를 처음부터 다시 해석해 같은 사실에 도달하는 실제
독립성이 성립한다.

- 교체한 raw log는 `.scan/live-provider-smoke/task-016-bridge-replay/`의
  실제 live 재실행 아티팩트에서 가져왔다. Base는 primary role, Ethereum은
  verify role의 raw 응답을 사용했다 — 둘 다 `provider-replay.json`에
  이미 pin된 `raw_sha256`과 바이트 단위로 일치한다.
- `task_016_bridge_independent_verifier.py`는 `task_016_bridge_replay.py`를
  **import하지 않는다.** `V3FundsDeposited`/`FilledV3Relay` word 오프셋,
  zero-output-token 매핑, 정수 fee 계산을 독립적으로 다시 구현하고,
  `expected.json`의 `bridge_transfer` projection과 정확히 일치하는지
  검증한 뒤 canonical SHA-256을 계산한다.
- evidence·requirement 연결도 raw-first로 재검증한다
  (`EV-BRIDGE-SOURCE-EVENT`/`EV-BRIDGE-DESTINATION-EVENT`의 chain/spoke
  pool/deposit ID가 재계산된 facts와 일치, `REQ-BRIDGE-SOURCE/DESTINATION/DOMAIN`
  세 requirement의 evidence_refs가 evidence.json에 실재).
- `evidence.json`의 `independent_verifier_pass`를 `true`로, `uncertainty.remaining`을
  `["candidate-to-verifying review"]`로 정정했다(negative oracle 완료 반영
  누락분도 함께 정정).

**계산된 canonical hash.** `FX-SVC-BRG-001=d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac`.

구현: `src/scan_tool/application/task_016_bridge_independent_verifier.py`,
`scripts/verify_task_016_bridge_independent_verifier.py`(`scripts/verify.py`에
연결), `tests/unit/test_task_016_bridge_independent_verifier.py`.

**검증.** `PASS TASK-016 Bridge independent Verifier: 1 fixtures, 3
requirements, 2 deterministic runs`. 이 단계는 raw-first 재계산까지이며,
아직 없는 `bridge_transfer` product analyzer와의 hash 대조
(analyzer-independent-verification)는 analyzer 구현 승인 이후 별도 Gate다.

## 11. Independent Verifier P1 Remediation (PR #103 리뷰 반영)

리뷰에서 두 P1과 P2가 지적됐다. 모두 코드로 정정하고 tamper 회귀 테스트로
확인했다.

**P1 — raw event identity와 tx/block binding 미검증.** 최초 구현은 topic
개수만 확인하고 topic0 signature·log-receipt-transaction-block 간 hash/number
binding을 확인하지 않아, source topic0·transaction hash·block hash를
각각 변조해도 통과했다.

- `_decode_chain_event()`에 전체 binding 체인을 추가했다: `topics[0]`이
  독립 선언된 `SOURCE_EVENT_TOPIC0`/`DESTINATION_EVENT_TOPIC0`와 정확히
  일치해야 하고, log의 `address`·`transactionHash`·`blockNumber`가 각각
  spoke pool·tx hash·block tag와 일치해야 한다. transaction의 `hash`·
  `blockNumber`·`to`, receipt의 `transactionHash`·`blockNumber`·`status`,
  block의 `number`·`hash`가 서로 exact binding되고, receipt의 `logs`
  배열 안에 선택된 log와 동일한 address·topic0·transactionHash·logIndex를
  가진 항목이 실제로 존재하는지도 확인한다.
- 회귀 테스트로 topic0·transaction hash·block hash 각각의 변조를 재현해
  거부됨을 확인했다(`test_wrong_topic0_is_rejected`,
  `test_wrong_transaction_hash_is_rejected`,
  `test_wrong_block_hash_is_rejected`).

**P1 — committed raw log와 provider SHA의 기계적 연결 부재.** 최초 구현은
`provider-replay.json`을 읽지 않았고, raw-replay.json에 손으로 옮겨 적은
"log" 요약과 이미 pin된 raw_sha256을 연결할 방법이 없었다.

- `raw-replay.json`을 pre-decoded 요약에서 벗어나 실제 JSON-RPC 응답
  **content-addressed 아티팩트**(`artifacts/sha256/<hash>.json`, 8개:
  Base=primary role, Ethereum=verify role)로 교체했다. 각 아티팩트는
  `.scan/live-provider-smoke/task-016-bridge-replay/`의 실제 live 재실행
  결과이며 `provider-replay.json`에 이미 pin된 `raw_sha256`과 바이트 단위로
  일치한다.
- Verifier가 각 capability의 artifact URI를 `provider-replay.json`의 같은
  `provider_id`·capability의 pinned `raw_sha256`과 대조하고, 실제 아티팩트
  파일 바이트의 SHA-256도 파일명과 재대조한 뒤에만 파싱한다.
- 회귀 테스트로 artifact URI가 pinned raw_sha256과 다르면 거부됨을 확인했다
  (`test_artifact_sha256_must_match_pinned_provider_value`).

**P2 — canonical hash가 evidence에 pin되지 않음.** 계산한 hash를 출력만
하고 기대값과 대조하지 않아 drift를 막지 못했다.

- TASK-013 선례를 따라 `evidence.json.verification_provenance.calculated_fact_sha256`에
  `d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac`를
  고정하고, `_verify_verification_provenance()`가 매 실행마다 재계산값과
  정확히 일치하는지 확인한다(불일치 시 거부).
- 회귀 테스트로 pinned 값을 임의로 바꾸면 거부됨을 확인했다
  (`test_canonical_hash_drift_from_pinned_evidence_is_rejected`).

**검증.** `tests/unit/test_task_016_bridge_independent_verifier.py` 8 PASS
(신규 5건 포함). `PASS TASK-016 Bridge independent Verifier: 1 fixtures, 3
requirements, 2 deterministic runs`(canonical hash 무변동). 전체 게이트
561 passed·traceability 1871·security 223(수치 정정 이력은 §12 참고).

## 12. Selected-log Binding P1 Remediation (PR #103 재리뷰 반영)

재리뷰에서 남은 P1 1건과 수치 정합 P2가 지적됐다. receipt log 대조가
address·topic0·tx hash·log index만 확인해, `eth_getLogs` 결과의
`blockHash`를 변조하고 SHA를 재고정해도 통과했다.

- 선택된 log 자체에 `blockHash == transaction/block hash`, `removed == false`
  확인을 추가했다.
- receipt의 매칭 log 항목과 선택된 log 사이에 `address`·`blockHash`·
  `transactionHash`·**전체 `topics` 배열**·`data`·`blockNumber`·`removed`가
  모두 일치하는지 확인하도록 확장했다(기존에는 address·topics[0]·tx hash·
  logIndex만 대조했다).
- 회귀 테스트 3건 추가: `test_selected_log_block_hash_mismatch_is_rejected`,
  `test_selected_log_removed_flag_is_rejected`,
  `test_selected_log_inconsistent_with_receipt_log_is_rejected`(eth_getLogs만
  변조하고 receipt는 그대로 두면 두 소스 불일치로 거부됨을 확인). 기존
  amount-mismatch 테스트는 두 소스를 동일하게 변조하는
  `test_destination_amount_mismatch_is_rejected`로 재구성해 ABI/정합 계층만
  독립적으로 검증한다.
- canonical hash 무변동: `d6609bb4f05ef0e75d82604a5e10e4ba16eab078494ef9ea375c0f97361800ac`.

**P2 — 검증 수치 미동기화.** 재검증 시점 실제 값은 `561 passed · traceability
1871 · security 223`이었으나 doc 62·Backlog에는 `1870`이 남아 있었다.
두 문서 모두 `1871`로 정정했다.

**검증.** `tests/unit/test_task_016_bridge_independent_verifier.py` 11 PASS
(신규 3건 포함). 전체 게이트 `564 passed`·traceability `1872`·security
`223`.

## 13. Related Documents

- [Bridge candidate package](./fixtures/FX-SVC-BRG-001/README.md)
- [Bridge 후보 선정 보고서](./61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md)
- [Bridge 계약](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md)
- [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md)
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
