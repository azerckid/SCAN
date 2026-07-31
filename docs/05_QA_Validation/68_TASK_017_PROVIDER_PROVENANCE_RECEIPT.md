# TASK-017 Bitcoin Provider Provenance Receipt

> Status: PASS · independent PublicNode/mempool replay · 2026-07-31 06:25 KST
> Scope: public read-only root transaction and one-hop spend

## 1. 목적

`FX-BTC-UTXO-001`의 독립성은 provider 이름 수가 아니라 서로 다른 응답
경로와 원문 body hash로 판정한다. 같은 bounded projection을 내는
mempool.space와 Blockstream을 두 독립 공급자로 세지 않는다.

전체 endpoint와 credential은 저장하지 않는다. 아래에는 공개 host, method,
조회 시각, 응답 body SHA-256만 남긴다.

## 2. 실제 호출 provenance

| 범위 | provider | 독립성 | method | endpoint host | retrieved_at | response body SHA-256 |
|---|---|---|---|---|---|---|
| root | PublicNode | independent primary | `getrawtransaction(txid,true)` | `bitcoin-rpc.publicnode.com` | 2026-07-31 06:24 KST | `757cbc01f955185761fad056b239e427a9a7b8595ee37308a5c338b2f100fe13` |
| hop 1 | PublicNode | independent primary | `getrawtransaction(txid,true)` | `bitcoin-rpc.publicnode.com` | 2026-07-31 06:25 KST | `59d353ad36038abee2c976a5c6083b48bfd428aeb1fdd914e245791af97a757e` |
| root | mempool.space | independent verify | `GET /api/tx/:txid` | `mempool.space` | 2026-07-31 01:00:01 KST | `a646813ef9c8dcd3b362957b6b1cdaa85b212930b2b1e035a930994646884534` |
| hop 1 | mempool.space | independent verify | `GET /api/tx/:txid` | `mempool.space` | 2026-07-31 01:01:00 KST | `36b7bfc3f761d57407bd9112555e68f3ab2683a1f94449c19755ba1855b52b29` |
| root | Blockstream | supporting-only | `GET /api/tx/:txid` | `blockstream.info` | 2026-07-31 01:00:02 KST | `8ada4be5a9ae943e83906584f4d1d1d3961ac746b97a01b1e60eb560b43df64e` |
| hop 1 | Blockstream | supporting-only | `GET /api/tx/:txid` | `blockstream.info` | 2026-07-31 01:01:01 KST | `e1430c13216bcbc0679718aa77819ac2bce8a38ead8e7e32ef483a07d7421fa4` |

PublicNode와 mempool.space의 네 body는 각각 다음 artifact에 변형 없이
저장되어 표의 hash와 일치한다.

- `artifacts/publicnode-root-raw.json`
- `artifacts/publicnode-hop1-raw.json`
- `artifacts/mempool-root-raw.json`
- `artifacts/mempool-hop1-raw.json`

Blockstream은 계산 필드만 담은 supporting-only reviewed projection이다.
그 projection의 저장 hash는 root
`08f42db51b88efa4bde6ff9541288a02db715d90d3e47c49ecbea74d0151f816`,
hop `8017b3791d1b66f9606a31c0e435fe30f2630fb71ad002f36e4776d7450ec1f5`다.

## 3. 독립성 판정

- root: PublicNode 원문에서 txid·vin outpoint·vout·block hash/time을
  재계산하고 mempool 원문에서 산출한 projection과 대조한다.
- hop: PublicNode 원문에서 spent outpoint·spending vin·created outputs를
  재계산한다. spent value는 PublicNode root의 해당 output에 결합하고,
  `spent value - sum(outputs)`로 fee를 독립 재계산해 mempool 원문 결과와
  대조한다.
- Blockstream projection은 추가 일치 확인에는 사용하지만 independent
  quorum에는 포함하지 않는다.
- `independence_role=independent`인 두 artifact hash가 같으면 replay model과
  독립 Verifier가 모두 거부한다.

## 4. 보안·경계

- 공개 read-only 조회만 사용했다.
- wallet, signing, send/broadcast, API key는 사용하지 않았다.
- 전체 endpoint URL, query credential, header는 문서·fixture·로그에 없다.
- 이 Receipt는 exact bounded UTXO 사실만 다룬다. change·ownership·범죄성·
  CoinJoin은 heuristic 또는 `not_assessed`다.
