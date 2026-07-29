# Fixture: FX-FLOW-REMERGE-001
> Created: 2026-07-29 23:25
> Last Updated: 2026-07-30
> Status: Confirmed 0.1 · Analyzer/Verifier Passed

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

## 3. 검증 상태

- [x] 4개 split·4개 merge·1개 unrelated inflow TX 1차 재현
- [x] branch별 input/output·residual과 총합 계산
- [x] 두 공급자 selected TX·receipt decoded match와 raw SHA-256
- [x] selected-transaction·exact block scope로 고정
- [x] residual은 근거 없이 fee로 승격하지 않고 unresolved로 보존
- [x] cycle·중복·budget·외부 inflow negative oracle
- [x] 두 번 결정성·독립 Verifier
- [x] 제품 analyzer·canonical hash 독립 검증
- [x] bounded selected-transaction scope로 최종 fixture 승격

## 4. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약](../../../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - remerge·ledger 계약
- **QA_Validation**: [TASK-014 Fixture Gate](../../39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 승격 기준
- **QA_Validation**: [TASK-014 후보 보고서](../../40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 세 후보 선정 판정
- **QA_Validation**: [Replay·Oracle 보고서](../../41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) - 공급자 재현과 반례
- **QA_Validation**: [독립 Verifier 보고서](../../42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) - raw-first ledger 재계산
- **External**: [Euler Finance incident timeline](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) - 공개 사건 맥락
