# FX-SVC-MIX-001 · Tornado Cash 0.1 ETH mixer flow

> Status: confirmed 0.1 · offline dual-provider replay
> Captured: 2026-07-31T04:47:24Z

## Case

- Chain: Ethereum mainnet (`chain_id` 1)
- Subject (depositor): `0xe1fe63b019ddac3a448f97a3c0c21df9c3613893`
- Pool (OFAC-designated Tornado Cash 0.1 ETH): `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc`
- Deposit TX: `0xc716eec2c710b22840d0cd877a61a83e9aacf628c79843a9505d53fa2e33f483` (block 25304911)
- Withdraw event facts (pool confirmed): 2 TXs in blocks 25305908–25305914
- Linkage: **heuristic/candidate only** — never confirmed ownership
- Attribution: ownership/criminality = `not_assessed`
- Label: OFAC press release assertion for the pool contract only

## Providers

| Role | Provider | Endpoint |
|:---|:---|:---|
| PRIMARY | PROVIDER-ETHEREUM-PUBLICNODE | https://ethereum-rpc.publicnode.com |
| VERIFY | PROVIDER-ETHEREUM-MERKLE | https://eth.merkle.io |

Artifact bytes for PRIMARY and VERIFY are distinct. Role/endpoint relabel and identical primary/verify hashes are rejected.

## Canonical fact hash

`4c8c4eb8041642ea514e4c7357d474bb4038b9f6eeea55a816aa2dae41484939`

## Boundaries

- Pool deposit/withdraw events and amounts are confirmed facts.
- Deposit↔withdraw linkage is candidate/불가; single-exit promotion is forbidden.
- Unlabeled mixer claims fail.
- `MIXED-XCHAIN-001` and Lending are out of scope for this fixture.
