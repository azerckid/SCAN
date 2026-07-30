# TASK-016 Bridge Raw Replay 준비 보고서
> Created: 2026-07-30 23:30
> Last Updated: 2026-07-31 01:10
> Status: Live Replay Passed · Cross-Provider Match Code-Verified (P1 Remediated) · Candidate

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

## 9. Related Documents

- [Bridge candidate package](./fixtures/FX-SVC-BRG-001/README.md)
- [Bridge 후보 선정 보고서](./61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md)
- [Bridge 계약](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md)
- [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md)
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
