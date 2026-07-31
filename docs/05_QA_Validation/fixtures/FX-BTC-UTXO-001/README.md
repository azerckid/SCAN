# FX-BTC-UTXO-001

Bitcoin block 800,000의 공개 거래를 사용한 exact-satoshi fixture다.

- deterministic fact: prevout, 두 output, fee equation, block inclusion
- `observations_complete`는 root projection 완결성을 뜻하며 unspent 증명이 아니다.
- independent primary: PublicNode Bitcoin Core JSON-RPC root·hop 원문
- independent verify: mempool.space REST root·hop 원문
- supporting-only: Blockstream REST reviewed projection
- `vout=1`은 입력 주소 재사용 신호 때문에 change **후보**일 뿐 소유 사실이 아니다.
- 이 거래는 CoinJoin 확정 사례가 아니다.

PublicNode와 mempool.space의 root·hop 실제 응답 body를 content-addressed
artifact로 저장한다. analyzer와 독립 Verifier는 그 원문을 직접 파싱해
replay·expected와 대조한다. endpoint와 credential은 포함하지 않는다.

Root와 hop 모두 PublicNode primary와 mempool.space verify의 실제 raw
capture를 유지하며 두 SHA-256은 달라야 한다. hop의 PublicNode 원문에서
spent outpoint, spending tx/vin, created output과 fee를 독립 재계산해
mempool 원문 projection과 비교한다. block height는 mempool 원문을
replay 원천으로 사용한다.

Blockstream hop artifact는 mempool.space와 같은 Esplora projection byte를
가질 수 있다. 이 경우 fact agreement를 보조하지만 독립 capture나
independence gate로 계산하지 않는다.
