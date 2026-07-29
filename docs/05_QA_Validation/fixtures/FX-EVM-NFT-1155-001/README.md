# Fixture: FX-EVM-NFT-1155-001
> Created: 2026-07-29 14:38
> Last Updated: 2026-07-29 15:38
> Status: Candidate 0.1 · Replay, Negative Oracle, and Verifier Gates Passed

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
| 상태 | candidate — 두 RPC receipt·filtered logs·raw SHA match Gate 통과 |

범위 완전성은 선정된 두 TX와 각각의 정확한 block window에만 적용한다.
두 block 사이의 연속 구간 전체를 스캔했다는 뜻이 아니다.

## 3. 승격 잔여

- [x] 선정 TX receipt·정확한 block window filtered logs·raw replay SHA-256
- [x] Batch 길이 불일치·다른 contract·누락 log negative oracle
- [ ] Analysis I/O·UI Preview 승인
- [x] 독립 Verifier와 두 번의 결정성

## 4. Related Documents

- **Technical_Specs**: [TASK-013 계약](../../../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - ERC-1155 해석 경계
- **QA_Validation**: [TASK-013 후보 보고서](../../32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - 선정·승격 Gate
- **QA_Validation**: [TASK-013 Negative Oracle](../../33_TASK_013_NEGATIVE_ORACLE_REPORT.md) - ABI·범위 반례
- **QA_Validation**: [TASK-013 독립 Verifier](../../34_TASK_013_INDEPENDENT_VERIFIER_REPORT.md) - raw-first 재계산
- **QA_Validation**: [Raw replay](./raw-replay.json) · [Provider replay](./provider-replay.json) - raw evidence와 공급자별 SHA
- **External**: [ERC-1155](https://eips.ethereum.org/EIPS/eip-1155) - 공식 event 정의
