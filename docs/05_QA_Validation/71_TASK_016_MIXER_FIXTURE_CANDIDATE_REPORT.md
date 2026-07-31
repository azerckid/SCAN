# TASK-016 Mixer Flow 공개 Fixture 후보 선정 보고서
> Created: 2026-07-31 08:00
> Last Updated: 2026-07-31 08:30
> Status: Selected · FX-SVC-MIX-001 confirmed

## 1. 선택 결과

| 필드 | 값 |
|:---|:---|
| Fixture | `FX-SVC-MIX-001` |
| 문제 | `SVC-MIX-001` |
| Chain | Ethereum mainnet (`chain_id` 1) |
| `subject_address` | `0xe1fe63b019ddac3a448f97a3c0c21df9c3613893` |
| `pool_address` | `0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc` (Tornado Cash 0.1 ETH) |
| Deposit TX | `0xc716eec2c710b22840d0cd877a61a83e9aacf628c79843a9505d53fa2e33f483` (block 25304911) |
| Withdraw TX | `0x2258d635…ef984` (block 25305908), `0x8232b56f…9a5d` (block 25305914) |
| `observation_window` | blocks `25304911`–`25305914` |
| Label source | US Treasury OFAC press release — entity `Tornado Cash` |
| Canonical fact SHA | `4c8c4eb8041642ea514e4c7357d474bb4038b9f6eeea55a816aa2dae41484939` |

withdraw linkage는 `heuristic_candidate`만 허용. ownership·criminality `not_assessed`.

## 2. Provider diversity

| Role | Provider | Endpoint |
|:---|:---|:---|
| PRIMARY | publicnode | `https://ethereum-rpc.publicnode.com` |
| VERIFY | merkle | `https://eth.merkle.io` |

PRIMARY/VERIFY artifact SHA-256 sets are distinct per event index.

## 3. Related Documents

- [Mixer 계약](../03_Technical_Specs/23_TASK_016_MIXER_CONTRACT_PROPOSAL.md)
- [Final Promotion Receipt](./72_TASK_016_MIXER_FINAL_PROMOTION_RECEIPT.md)
