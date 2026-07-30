# FX-SVC-CEX-001 — GARANTEX native ETH cluster

> Status: confirmed · raw provider replay·negative oracle·independent Verifier·analyzer complete

## Scope

Three OFAC SDN-listed GARANTEX deposit addresses sweep native ETH to one shared
hot wallet candidate on Ethereum mainnet within a bounded observation window.

- deposit candidates:
  - `0x8dce2aac0de82bdcaf6b4373b79f94331b8e4995`
  - `0xb338962b92cd818d6aef0a32a9ecd01212a71f33`
  - `0xf4377eda661e04b6dda78969796ed31658d602d4`
- hot wallet candidate: `0xdbaef73d20b0ca4abc72e8daf97af36626e3b973`
- observation window: blocks `18215900`–`18216000`
- outbound blocks: `18215917`, `18215920`, `18215925`
- label assertion source: US Treasury OFAC SDN public XML (`GARANTEX`)

Hot wallet ownership and criminality remain `not_assessed`. Etherscan community
tags are not used as scoring sources.

## Gates complete

- two-provider raw replay and content SHA-256 pins
- negative oracle 8 synthetic cases (2× deterministic)
- independent raw-first Verifier canonical hash match
- product analyzer hash match and CLI `--evidence` integration
- Benchmark automated registration (`SVC-CEX-001`)

## Files

- `input.json`: discovery-mode request scope
- `expected.json`: verified cluster facts and scoring requirements
- `evidence.json`: outbound, common destination, label, and pattern evidence
- `raw-replay.json`: three native transfer artifact references
- `provider-replay.json`: per-transfer capability SHA-256 pins
- `artifacts/sha256/<hash>.json`: raw JSON-RPC responses
- `artifacts/ofac-garantex-provenance.json`: gov label assertion provenance

## Canonical hash

Independent Verifier canonical fact hash:
`20fc2777b75968e905af493f97bb56a5b24ccefad755f3a12ebc62662be283bf`

## Related Documents

- [CEX Final Promotion Receipt](../../68_TASK_016_CEX_FINAL_PROMOTION_RECEIPT.md)
- [CEX Cluster contract](../../../03_Technical_Specs/22_TASK_016_CEX_CLUSTER_CONTRACT_PROPOSAL.md)
- [CEX Fixture candidate report](../../67_TASK_016_CEX_FIXTURE_CANDIDATE_REPORT.md)
- [Contest Stabilization Runbook](../../66_CONTEST_STABILIZATION_RUNBOOK.md)
