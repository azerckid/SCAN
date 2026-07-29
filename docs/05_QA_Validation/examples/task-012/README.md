# TASK-012 Analysis Contract Examples
> Created: 2026-07-29 04:46
> Last Updated: 2026-07-29 12:40
> Status: Approved 0.2 · 12 Contract Cases · Runtime Applied

## 1. 범위

`TASK-012-ANALYSIS-CONTRACT-PROPOSAL.json`은 네 confirmed fixture를
`analysis_type: evm_core`의 네 query로 변환한 계약 예제다.

| Fixture | Query | 사례 |
|:---|:---|:---|
| FX-BASIC-EVM-001 | `object_summary` | complete·partial·failed |
| FX-BASIC-EVM-002 | `historical_balance` | complete·partial·failed |
| FX-EVM-TOKEN-001 | `first_token_transfer` | complete·partial·failed |
| FX-EVM-TOKEN-002 | `native_inflow` | complete·partial·failed |

이 예제는 Analysis I/O 0.2 계약 검증용 matrix다. 실제 CLI runtime은
각 fixture의 `analysis-request.json`과 `raw-replay.json`을 입력으로 받고,
0.1 DEX·AUTH·FREEZE 계약은 그대로 호환한다.

## 2. 검증

```bash
uv run python scripts/check_task_012_analysis_contract_proposal.py
```

검증기는 Schema·12 case·14 probe·fixture exact 값·source
policy·request/result 일치를 확인한다. failed null/error, ERC-20
token address, fee 요청, range/trace completeness도 강제하며 Analysis
I/O 0.2 채택과 0.1 하위 호환을 검사한다.

## 3. Related Documents

- **Technical_Specs**: [TASK-012 계약 제안](../../../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - 설계·버전·UI 영향
- **Technical_Specs**: [Analysis I/O 0.2](../../../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 현재 승인 계약과 0.1 호환
- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - 원본 fixture
- **QA_Validation**: [Negative Oracle 보고서](../../27_TASK_012_NEGATIVE_ORACLE_REPORT.md) - partial·failed 경계
