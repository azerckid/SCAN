# Fixture: FX-EVM-NFT-721-001
> Created: 2026-07-29 14:38
> Last Updated: 2026-07-29 14:38
> Status: Candidate 0.1 · Two-Provider Receipt Match

## 1. 목적

동일 BAYC 소유자의 운영자 승인과 token 9110 이동을 ERC-721 raw event로
복원하는 공개 후보다.

## 2. 공개 사례

| 항목 | 값 |
|:---|:---|
| Contract | BAYC `0xbc4ca0ed...a936f13d` |
| Subject | `0x28dda46b...729367a0` |
| ApprovalForAll | TX `0x4501b47b...af9379`, block `25008826`, log `971` |
| Approval reset + Transfer | TX `0x07ae8c28...a727d7`, block `25023516`, logs `417`·`418` |
| Token ID | `9110` |
| 상태 | candidate — 두 RPC receipt decoded match |

## 3. 승격 잔여

- [ ] 범위 filtered logs와 raw replay SHA-256
- [ ] ERC-20/721 혼동·다른 contract·range 누락 negative oracle
- [ ] Analysis I/O·UI Preview 승인
- [ ] 독립 Verifier와 결정성

## 4. Related Documents

- **Technical_Specs**: [TASK-013 계약](../../../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - ERC-721 해석 경계
- **QA_Validation**: [TASK-013 후보 보고서](../../32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 선정·승격 Gate
- **External**: [ERC-721](https://eips.ethereum.org/EIPS/eip-721) - 공식 event 정의
