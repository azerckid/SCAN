# TASK-016 Bridge Raw Replay 준비 보고서
> Created: 2026-07-30 23:30
> Last Updated: 2026-07-31 00:35
> Status: Live Replay Passed · Candidate

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
full Gate:        548 tests, fixture 19, Schema 52, links 1859, security 213 PASS
```

## 7. Gate 상태

- [x] Base primary·verify endpoint를 로컬 secret 환경에 준비한다.
- [x] 운영자 승인에 따라 source mode를 `allowed`로 확인한다.
- [x] primary role 8개 read-only call을 실행한다.
- [x] verify role 8개 read-only call을 실행한다.
- [x] 16 capability raw SHA와 retrieved_at을 package에 pin한다.
- [x] primary/verify decoded facts가 동일함을 기계적으로 대조한다.
- [x] candidate 상태를 유지한 채 실제 호출 결과를 기록한다.
- [ ] Phase B negative oracle을 구현한다.
- [ ] Phase C 독립 Verifier와 verifying 판정을 수행한다.

## 8. Related Documents

- [Bridge candidate package](./fixtures/FX-SVC-BRG-001/README.md)
- [Bridge 후보 선정 보고서](./61_TASK_016_BRIDGE_FIXTURE_CANDIDATE_REPORT.md)
- [Bridge 계약](../03_Technical_Specs/21_TASK_016_BRIDGE_XCHAIN_CONTRACT_PROPOSAL.md)
- [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md)
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
