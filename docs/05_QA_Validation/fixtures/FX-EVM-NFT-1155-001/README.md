# Fixture: FX-EVM-NFT-1155-001
> Created: 2026-07-29 14:38
> Last Updated: 2026-07-29 14:38
> Status: Candidate 0.1 · Two-Provider Receipt Match

## 1. 목적

Rarible ERC-1155 계약의 Single·Batch·ApprovalForAll을 raw ABI 순서로
복원하는 공개 후보다.

## 2. 공개 사례

| 항목 | 값 |
|:---|:---|
| Contract | `0xb66a603f...6518b8` |
| Single + approval | TX `0x49f0ce14...fe2f0`, block `24609794`, logs `1033`~`1038` |
| Multi-item Batch | TX `0x94fcb633...a230e`, block `23762140`, log `646` |
| Batch 길이 | ids 2 · amounts 2 |
| Batch amounts | `[1, 1]` |
| 상태 | candidate — 두 RPC receipt decoded match |

## 3. 승격 잔여

- [ ] raw replay SHA-256과 filtered range completeness
- [ ] Batch 길이 불일치·다른 contract·누락 log negative oracle
- [ ] Analysis I/O·UI Preview 승인
- [ ] 독립 Verifier와 결정성

## 4. Related Documents

- **Technical_Specs**: [TASK-013 계약](../../../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - ERC-1155 해석 경계
- **QA_Validation**: [TASK-013 후보 보고서](../../32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 선정·승격 Gate
- **External**: [ERC-1155](https://eips.ethereum.org/EIPS/eip-1155) - 공식 event 정의
