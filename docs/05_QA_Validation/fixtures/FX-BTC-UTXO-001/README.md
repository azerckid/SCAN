# FX-BTC-UTXO-001

Bitcoin block 800,000의 공개 거래를 사용한 exact-satoshi fixture다.

- deterministic fact: prevout, 두 output, fee equation, block inclusion
- `observations_complete`는 root projection 완결성을 뜻하며 unspent 증명이 아니다.
- primary: PublicNode Bitcoin Core JSON-RPC
- verify: mempool.space REST
- supporting: Blockstream REST 교차 확인
- `vout=1`은 입력 주소 재사용 신호 때문에 change **후보**일 뿐 소유 사실이 아니다.
- 이 거래는 CoinJoin 확정 사례가 아니다.

Raw provider 응답 전체는 저장하지 않는다. 대신 계산에 필요한 provider별
reviewed projection을 content-addressed artifact로 저장하고, analyzer와
독립 Verifier가 그 artifact를 직접 파싱해 replay·expected와 대조한다.
endpoint와 credential은 fixture에 포함하지 않는다.
