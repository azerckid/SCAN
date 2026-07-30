# TASK-017 Bitcoin UTXO Workbench

> Status: UI contract approved under the TASK-017 batch authorization

한 화면은 다음 순서를 유지한다.

1. Request: txid, start vout, max hops, network
2. Exact ledger: input sum − output sum = fee(sat)
3. Spend path: depth별 spent outpoint → spending transaction → frontier
4. Heuristic panel: change candidate와 CoinJoin candidate
5. Boundary: ownership/criminality/single exit `not_assessed`

`complete`도 heuristic을 confirmed fact로 보이지 않는다. `partial`은
missing prevout/frontier를, `failed`는 fee·binding 충돌을 표시한다.
loading·empty·stale은 기존 Workbench 공통 상태를 재사용한다.

## 키보드 범위

현재 정적 Preview의 상태 선택기는 native `button` 그룹이다. `Tab` /
`Shift+Tab`으로 이동하고 `Enter` / `Space`로 활성화한다. tablist나 roving
tabindex 계약이 아니므로 `ArrowLeft` / `ArrowRight` / `Home` / `End`는
이번 Preview의 필수 동작이 아니다. 향후 상태 선택기를 tablist로 바꾸면
그 키를 같은 변경에서 구현·검증한다.
