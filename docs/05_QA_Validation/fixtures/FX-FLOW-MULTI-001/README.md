# Fixture: FX-FLOW-MULTI-001
> Created: 2026-07-29 23:25
> Last Updated: 2026-07-30
> Status: Confirmed 0.1 · Raw Contribution Analyzer/Verifier Passed

## 1. 목적

네 origin의 성공한 native ETH 전송이 동일 exit로 들어오는 양을 origin별로
계산하고, transaction hash 중복 없이 raw 합계를 재계산하는 공개 후보이다.

## 2. 기준 정답

| origin | contribution raw |
|:---|---:|
| `0x46e0be...0cf55` | `7737250000000000000000` |
| `0xa1b44d...8e676` | `7738050000000000000000` |
| `0x8765a3...e38a4c` | `7738050000000000000000` |
| `0xc4e04a...b208e` | `7738050000000000000000` |
| **합계** | **`30951400000000000000000`** |

exit는 `0xee009f...c8c5`다. 가격 환산과 네 주소의 동일 소유자 여부는 채점하지
않는다.

## 3. 검증 상태

- [x] origin 네 개·exit 하나·성공 TX 네 건 1차 재현
- [x] transaction hash dedup 후 raw 총액 계산
- [x] 가격·라벨·귀속을 `not_assessed`로 분리
- [x] 두 공급자 raw replay·SHA-256
- [x] 명시 origin set와 transaction hash 중복 제거 결정성
- [x] 중복·누락·다른 exit·price 누락 negative oracle
- [x] 두 번 결정성·독립 Verifier contribution·total 재계산
- [x] 제품 analyzer·canonical hash 독립 검증
- [x] raw contribution 범위로 최종 fixture 승격
- [ ] 가격·피해자 귀속은 TASK-015 이후 별도 문제 자동화 Gate

## 4. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약](../../../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - multi-origin·dedup 계약
- **QA_Validation**: [TASK-014 Fixture Gate](../../39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 승격 기준
- **QA_Validation**: [TASK-014 후보 보고서](../../40_TASK_014_FIXTURE_CANDIDATE_REPORT.md) - 세 후보 선정 판정
- **QA_Validation**: [Replay·Oracle 보고서](../../41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) - 공급자 재현과 반례
- **QA_Validation**: [독립 Verifier 보고서](../../42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) - raw-first total 재계산
- **External**: [Euler Finance incident timeline](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) - 공개 사건 맥락
