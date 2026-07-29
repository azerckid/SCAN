# TASK-014 PATH 독립 Verifier 보고서
> Created: 2026-07-30 00:08
> Last Updated: 2026-07-30
> Status: Passed · Historical Verifying Gate · Final Promotion Completed

## 1. 목적

provider replay builder를 import하지 않는 별도 코드 경로에서 세
`raw-replay.json`을 읽고 graph·ledger를 재계산한다. expected는 계산 후
대조하며, evidence 값과 requirement 참조도 별도로 확인한다.

## 2. 결과

| Fixture | 재계산 범위 | Fact SHA-256 |
|:---|:---|:---|
| `FX-FLOW-PATH-001` | internal+top-level 3 edge, ordered path | `4035497ab47987952c12732ea45806b1ec4830df7e5b7b4c9e46cf41391367fe` |
| `FX-FLOW-REMERGE-001` | split 4, merge 4, residual, dust exclusion | `39198d15b878ddd07a227fd6df1e0047a2c3cf2b2d8f8b414bfa33e14ffab381` |
| `FX-FLOW-MULTI-001` | origin 4, exit 1, deduplicated total | `8e80cb1a34bcdf1308073b56ca15fd05bc0c04826abf83ae986cfcf2078a2f79` |

두 번의 실행 결과와 canonical hash가 동일했다. 총 6개 mandatory
requirement의 evidence 참조가 존재하며, PATH edge raw 값, REMERGE ledger,
MULTI total이 evidence와 일치했다.

## 3. 거부 조건

- transaction·receipt hash/block/index 불일치
- 실패 receipt
- path endpoint 불연속
- branch 누락·음수 residual
- 중복 transaction·다른 exit
- evidence raw 값 불일치
- requirement가 존재하지 않는 evidence를 참조

## 4. 독립성

Verifier는 네트워크를 호출하지 않으며 `task_014_artifacts`의 builder나
provider decoded summary를 import하지 않는다. raw replay의 transaction,
receipt, internal edge만으로 계산한 뒤 expected·evidence를 대조한다.

## 5. 판정

독립 Verifier Gate는 **Pass**다. 이는 fixture를 `verifying`으로 올릴
근거이며 제품 analyzer의 구현·Analysis result hash·Benchmark 성공을
대체하지 않는다.

이후 별도 코드 경로의 제품 analyzer와 canonical hash를 대조하고 PATH
internal edge를 Blockscout API로 교차검증했다. 최종 `confirmed` 판정과
Benchmark 11/11 근거는
[최종 승격 Receipt](./44_TASK_014_FINAL_PROMOTION_RECEIPT.md)에 기록한다.

## 6. Related Documents

- **QA_Validation**: [Replay·Oracle 보고서](./41_TASK_014_REPLAY_NEGATIVE_ORACLE_REPORT.md) - 입력 artifact와 반례
- **QA_Validation**: [Fixture Gate](./39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 남은 계약·구현 Gate
- **QA_Validation**: [최종 승격 Receipt](./44_TASK_014_FINAL_PROMOTION_RECEIPT.md) - 후속 confirmed 판정
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - Context Receipt 잠금
