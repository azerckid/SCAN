# FX-SVC-LEND-001 — Aave V3 LiquidationCall (Ethereum)

> Status: 확정(confirmed) · dual-provider raw replay · negative oracle · independent Verifier · analyzer · Benchmark automated

## 범위

- Protocol: Aave V3 Pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2`
- TX: `0x207745c3f3cbcdc4f31a5a9d89810278e2e6cef385cb1bbf0b2c4b4ccdac4a37`
- Block: `21036015` (`0x140fbef`)
- `subject_address` (liquidator): `0x1b05437f4a5f6b21692e83af3eb5607683e6dead`
- Borrower (`user`): `0xcdb238d68d8da74487711bc1f8f13f3d00667d1a`
- Debt asset (WBTC): `0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` raw `364477506`
- Collateral asset (wstETH): `0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` raw `87377757596420188410`
- PRIMARY: `https://ethereum.publicnode.com`
- VERIFY: `https://ethereum.rpc.thirdweb.com` (Merkle 429 · 1rpc identical-bytes rejected)
- Canonical hash: `6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c`
- Capture metadata: `artifacts/capture-meta.json` binds the six exact provider
  capabilities to provider ID, role, endpoint, JSON-RPC method/params, response
  SHA-256, and capture time.

## 신뢰 경계

- 2026-07-31 KST에 PRIMARY와 VERIFY를 live read-only로 재조회했고 transaction,
  receipt, block의 immutable fields가 저장 artifact와 일치했다.
- 두 endpoint는 서로 다른 공개 RPC이지만 무신뢰 합의 증명은 아니다. 운영자
  공모·동일 upstream·동시 오응답 가능성은 이 fixture가 제거할 수 없는 공개
  endpoint 신뢰 경계로 남는다.
- analyzer와 독립 Verifier는 저장 artifact의 content hash, provider provenance,
  tx/receipt/block/log binding, 양 provider selected raw log exact match를
  검증하며 network 재조회 결과를 자동으로 신뢰하지 않는다.

## Related Documents

- [69 Lending Fixture Candidate Report](../../69_TASK_016_LENDING_FIXTURE_CANDIDATE_REPORT.md)
- [70 Lending Final Promotion Receipt](../../70_TASK_016_LENDING_FINAL_PROMOTION_RECEIPT.md)
- [Lending Contract](../../../03_Technical_Specs/19_TASK_016_LENDING_CONTRACT_PROPOSAL.md)
