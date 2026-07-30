# TASK-017 Bitcoin UTXO Analysis I/O 계약

> Status: Approved for offline implementation · 2026-07-31
> Analysis type: `bitcoin_utxo` · Schema `0.2` · Bitcoin mainnet `chain_id: 0`

## 1. 범위

`summarize_transaction`은 `transaction_id`, `start_vout`, `max_hops`를
받아 prevout·output·fee와 선택 outpoint의 bounded 소비 경로를 satoshi
정수로 재계산한다. `assess_heuristics`는 같은 확정 사실 위에 change와
CoinJoin 후보를 별도 `heuristic` 결과로 추가한다.

## 2. 불변식

- `sum(prevout) - sum(output) == fee_sat`
- outpoint는 `(txid, vout)`이며 중복 소비를 허용하지 않는다.
- request의 network·txid·start_vout·max_hops는 replay와 결합한다.
- `start_vout`은 root transaction output에 반드시 존재한다.
- spend path depth는 `1..n`으로 연속하고, 각 hop의 spent outpoint/value는
  바로 이전 transaction이 만든 output 중 하나와 exact match해야 한다.
- root와 각 hop은 정확히 하나의 primary와 verify, 최대 하나의 supporting을
  허용하며 provider ID는 중복될 수 없다.
- primary와 verify는 별도 capture여야 하며 실제 response body artifact
  SHA-256이 반드시 달라야 한다.
- stored artifact는 repository package 내부 경로와 SHA-256으로 검증한다.
- PublicNode primary와 mempool.space verify의 실제 root·hop response
  body를 변형 없이 저장하고 직접 파싱한다. root는 txid·vin outpoint·vout·
  block hash/time, hop은 spent outpoint·spending vin·created outputs를
  각 경로에서 재유도한다. PublicNode hop fee는 root output value에서
  created outputs 합을 빼서 독립 계산한다. block height는 mempool 원문에서
  재유도해 replay와 exact compare한다.
- 같은 wire format의 동일 byte copy는 독립 검증으로 계산하지 않는다.
  Blockstream projection은 존재할 경우 `supporting_only` fact agreement
  확인에만 사용한다.
- normalized replay·expected는 계산 원천이 아니라 위 artifact-derived
  사실과 exact compare하는 계약·채점 문서다.
- replay source set과 request allowlist는 exact set이다.

## 3. 사실과 휴리스틱

| 값 | classification |
|---|---|
| prevout, output, fee, block, spend path | `confirmed_fact` |
| 입력 주소 재사용 change 신호 | `heuristic` |
| 동일 금액 다중 output CoinJoin 신호 | `heuristic` |
| 공동 소유·범죄성·단일 출구 | `not_assessed` |

CoinJoin 후보가 있어도 특정 출구나 주소 소유를 확정하지 않는다.

## 4. 상태

- `complete`: 선택 범위의 prevout과 하나 이상의 bounded spend path가 모두 있다.
- `partial`: prevout 또는 spend evidence가 없어 범위를 완결하지 못한다. 현재
  v1에서 빈 spend path는 미사용 UTXO 증명이 아니라 evidence 부재이므로
  `observations_complete: true`여도 complete/empty frontier로 승격하지 않는다.
- `failed`: fee·outpoint·provider artifact·request binding이 모순이다.

`observations_complete`는 root transaction의 reviewed projection이 완전하다는
뜻이며 해당 output이 미사용이라는 뜻이 아니다. 향후 unspent 증명을 추가하면
그 증거로 start outpoint 자체를 frontier로 반환하는 별도 계약이 필요하다.

기존 ErrorCode만 재사용하며 새 공개 오류 코드는 만들지 않는다.

## 5. 입력 모드

`external_rpc`, `contest_rpc`, `provided_artifact`는 정규화 후 같은 replay
계약을 소비한다. 현재 제품 analyzer는 reviewed offline artifact만
실행한다. live Bitcoin endpoint는 필수가 아니다.

## 6. 승인·Context Receipt

- Source: PublicNode primary, mempool.space verify, Blockstream supporting
- 공개 read-only 조회만 사용하며 credential을 저장하지 않는다.
- UI는 exact satoshi와 heuristic candidate를 시각적으로 분리한다.
- Context Receipt: PASS
- 사용자 구현 승인: 2026-07-31
  “17을 병렬 처리를 브랜치를 따로 만들어서 진행 … 작업이 마무리 되면
  일괄 승인 하고 검증·커밋·Draft PR 생성까지 완료” 요청.
  이 승인은 `codex/task-017-bitcoin`의 TASK-017 구현·검증·커밋·Draft PR
  생성에만 적용하며 TASK-016 CEX 또는 다른 adapter 구현 승인이 아니다.
