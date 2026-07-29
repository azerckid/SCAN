# Fixture: FX-EVM-PROXY-001
> Created: 2026-07-29 14:38
> Last Updated: 2026-07-29 14:38
> Status: Candidate 0.1 · Two-Provider Archive Match

## 1. 목적

Aave V3 Pool proxy의 EIP-1967 implementation 변경을 event와 historical
storage로 함께 입증하는 공개 후보다.

## 2. 공개 사례

| 항목 | 값 |
|:---|:---|
| Proxy | `0x87870bca...b4fa4e2` |
| Upgrade TX | `0xe9949c36...bc2b35` |
| Block | `25199939` |
| Before implementation | `0x8147b99d...0f119bd` at `25199938` |
| After implementation | `0x728a138a...6fe03cf` at `25199939` |
| Upgraded log | `1041`, after implementation과 일치 |
| Admin slot | before/after 모두 zero |
| 상태 | candidate — 두 archive RPC decoded match |

## 3. 승격 잔여

- [ ] raw replay SHA-256과 더 넓은 upgrade history 범위
- [ ] latest-state 오용·admin/beacon 혼동·event/state conflict negative oracle
- [ ] Analysis I/O·UI Preview 승인
- [ ] 독립 Verifier와 결정성

## 4. Related Documents

- **Technical_Specs**: [TASK-013 계약](../../../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - EIP-1967 해석 경계
- **QA_Validation**: [TASK-013 후보 보고서](../../32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 선정·승격 Gate
- **External**: [ERC-1967](https://eips.ethereum.org/EIPS/eip-1967) - 공식 slot·event 정의
