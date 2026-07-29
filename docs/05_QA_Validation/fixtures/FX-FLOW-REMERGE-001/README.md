# Fixture: FX-FLOW-REMERGE-001
> Created: 2026-07-29 23:25
> Last Updated: 2026-07-29 23:25
> Status: Candidate 0.1 · 공개 4분기·재병합 사례 선정 · Replay/Oracle/Verifier Pending

## 1. 목적

한 seed의 동일 금액 ETH 전송 네 건이 서로 다른 branch로 나뉜 뒤 공통
주소로 다시 모이는 흐름을 재현한다. 동일 branch에 들어온 외부 dust는
seed ledger와 분리한다.

## 2. 기준 정답

| 항목 | raw |
|:---|---:|
| seed split 합계 | `30953000000000000000000` |
| merge 유입 합계 | `30951400000000000000000` |
| unresolved residual | `1600000000000000000` |
| unrelated external inflow | `1000000000000` |

branch 네 개는 `0xa1b44d...8e676`, `0xc4e04a...b208e`,
`0x46e0be...0cf55`, `0x8765a3...e38a4c`이며 merge 주소는
`0xee009f...c8c5`다.

## 3. 후보 유지 사유

- [x] 4개 split·4개 merge·1개 unrelated inflow TX 1차 재현
- [x] branch별 input/output·residual과 총합 계산
- [ ] primary provider·고정 raw artifact 재현
- [ ] selected TX 밖 연속 range의 포함·제외 규칙 결정
- [ ] residual의 balance/fee/later-output 분류
- [ ] cycle·중복·budget·asset mismatch negative oracle
- [ ] 두 번 결정성·독립 Verifier

## 4. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약](../../../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - remerge·ledger 계약
- **QA_Validation**: [TASK-014 Fixture Gate](../../39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 승격 기준
- **QA_Validation**: [TASK-014 후보 보고서](../../40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 세 후보 선정 판정
- **External**: [Euler Finance incident timeline](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) - 공개 사건 맥락
