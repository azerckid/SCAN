# TASK-017 Bitcoin UTXO 구현·검증 보고서

> Status: Partial completion · UTXO automated · heuristics assisted

## 결과

- `FX-BTC-UTXO-001`: confirmed, two-source exact replay + supporting source
- BTC-UTXO-001: bounded 1-hop path와 frontier를 자동 채점
- BTC-UTXO-002: change 후보는 assisted
- BTC-CJ-001: 별도 `FX-BTC-CJ-001` candidate, assisted

## Gate

- fee/outpoint/path를 stored provider artifact-first 방식으로 독립 Verifier가
  두 번 재계산하고 normalized replay·expected를 별도로 대조한다.
- negative oracle 7종은 fee conflict, prevout 누락, duplicate outpoint,
  change/CoinJoin 과대 주장과 positive control을 고정한다.
- product analyzer와 독립 Verifier는 서로 import하지 않는다.
- provider stored artifact SHA와 source exact set을 검사하고, mempool.space와
  Blockstream projection의 root·hop decoded equality를 직접 검증한다.
- PublicNode projection의 txid·vin outpoint·vout·block hash/time을 REST
  projection과 독립 대조한다.
- request start_vout 존재와 `1..n` depth 연속성, 각 hop의 직전 created
  outpoint/value 연결을 replay validator와 artifact-derived Verifier 양쪽에서
  강제한다.
- 빈 spend path는 unspent 증명으로 해석하지 않고 `partial`로 내린다.

## 보안

공개 read-only endpoint만 사용했다. endpoint credential, wallet, signing,
send/broadcast는 없다. fixture에는 논리 provider ID와 content hash만 남긴다.

## 저장 호환성

Bitcoin mainnet은 `chain_id=0`으로 저장한다. TASK-017 이후 새 SQLite
v1 DB는 `CHECK(chain_id IN (0, 1))`을 사용한다. 이전에 생성된
`CHECK(chain_id = 1)` DB는 open만으로 변형하지 않고 Bitcoin run 생성 전에
명확히 거부한다. 기존 사용자 DB는 별도 승인된 backup·migration Gate
없이는 변경하지 않는 경계를 회귀 테스트로 고정한다.

## 최종 검증

- pytest: 598 passed
- fixture Schema: 21 packages
- Analysis I/O compatibility: 62 probes
- traceability: 1951 links
- security: 245 runtime/evidence files
- Benchmark: 14 automated / 6 assisted / 10 unsupported, automated 14/14 PASS

## 잔여

CoinJoin candidate의 full raw package·방법론 provenance·독립 Verifier가
남아 있다. 따라서 change/CoinJoin은 confirmed fact 또는 automated로
승격하지 않는다.
