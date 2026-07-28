# TASK-012 Analysis Contract Proposal Examples
> Created: 2026-07-29 04:46
> Last Updated: 2026-07-29 04:46
> Status: Proposed · 8 Cases · Runtime Not Implemented

## 1. 범위

`TASK-012-ANALYSIS-CONTRACT-PROPOSAL.json`은 네 verifying fixture를
`analysis_type: evm_core`의 네 query로 변환한 제안 예제다.

| Fixture | Query | 사례 |
|:---|:---|:---|
| FX-BASIC-EVM-001 | `object_summary` | complete·partial |
| FX-BASIC-EVM-002 | `historical_balance` | complete·partial |
| FX-EVM-TOKEN-001 | `first_token_transfer` | complete·partial |
| FX-EVM-TOKEN-002 | `native_inflow` | complete·partial |

이 예제는 승인된 Analysis I/O 0.1 예제가 아니며 runtime 출력도 아니다.
정식 0.2 승인 전에는 `AnalysisRequest`·CLI·Operations가 이를 입력으로
받지 않는다.

## 2. 검증

```bash
uv run python scripts/check_task_012_analysis_contract_proposal.py
```

검증기는 Schema·8 case·5 probe·fixture exact 값·source policy·request/result
일치를 확인하고, 기존 Analysis I/O 0.1과 runtime enum이 변경되지 않았는지
검사한다.

## 3. Related Documents

- **Technical_Specs**: [TASK-012 계약 제안](../../../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - 설계·버전·UI 영향
- **Technical_Specs**: [Analysis I/O 0.1](../../../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 현재 승인 계약
- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - 원본 fixture
- **QA_Validation**: [Negative Oracle 보고서](../../27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - partial·failed 경계
