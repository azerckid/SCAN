# Fixture: FX-FLOW-PATH-001
> Created: 2026-07-29 23:25
> Last Updated: 2026-07-29 23:25
> Status: Candidate 0.1 · 공개 3홉 사례 선정 · Replay/Oracle/Verifier Pending

## 1. 목적

Ethereum native ETH 이동을 internal call 1건과 top-level transfer 2건으로
이어, 선택된 seed에서 terminal까지 3홉 경로를 복원하는 공개 후보이다.

## 2. 공개 사례

| 홉 | TX · block | from → to | amount raw |
|:---:|:---|:---|---:|
| 1 | `0x298bde3f...05db55` · `16818102` | `0x036cec...25f1c` → `0xb66cd9...995db` | `88752697459828535340019` |
| 2 | `0x79c10cf5...baeda` · `16905356` | `0xb66cd9...995db` → `0xa1b44d...8e676` | `7738250000000000000000` |
| 3 | `0xe3f67f8e...3fd0d` · `16920430` | `0xa1b44d...8e676` → `0xee009f...c8c5` | `7738050000000000000000` |

세 TX의 exact block만 선정했다. block 사이 전체를 연속 스캔했거나 seed의
다른 출력까지 완전하게 재구성했다는 뜻은 아니다.

## 3. 후보 유지 사유

- [x] 공개 TX·block·from/to·raw value·성공 receipt 1차 재현
- [x] 공식 사건 연표와 온체인 이동의 시점·주소 맥락 대조
- [ ] 첫 internal edge 독립 trace replay
- [ ] 두 공급자 raw artifact·SHA-256 고정
- [ ] selected path와 seed 전체 ledger의 범위 결정
- [ ] negative oracle·두 번 결정성·독립 Verifier

## 4. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약](../../../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - bounded path·ledger 계약
- **QA_Validation**: [TASK-014 Fixture Gate](../../39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 승격 기준
- **QA_Validation**: [TASK-014 후보 보고서](../../40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 세 후보 선정 판정
- **External**: [Euler Finance incident timeline](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) - 공개 사건 맥락
