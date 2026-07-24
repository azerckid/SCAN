# Fixture: FX-EVM-AUTH-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-24 19:19
> Status: Candidate

## 1. 목적

`approve` 또는 `permit`으로 부여된 토큰 권한과 이후 소비 호출을 연결하고,
이벤트·호출·과거 allowance 상태를 서로 분리해 검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-AUTH-001` |
| 상태 | 후보 |
| 피해자·토큰·TX | 미선정 |
| 주요 소스 | `DS-EXPLORER-EVM` 또는 `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE` |
| 승격 조건 | 승인 유형 확정, allowance 전후 조회, 소비 TX 연결, 수동 재현 성공 |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 피해자·토큰·승인·소비 TX와 조회 블록 |
| `expected.json` | 승인 유형별 증거, allowance 전후와 실제 전송 기준 정답 |
| `evidence.json` | 이벤트·calldata·상태 조회 원본과 provenance |

## 4. 검증 절차

1. 승인 유형을 `approve` 또는 `permit`으로 확정한다.
2. `Approval`·`Transfer` 이벤트 증거를 별도 수집한다.
3. 승인·소비 호출의 calldata와 nonce 근거를 기록한다.
4. archive state로 allowance 전후 값을 조회한다.
5. 소비 호출과 실제 전송을 연결해 두 증거 표를 분리 출력한다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - AUTH 증거 유형과 승격 기준
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - archive state 필수 소스
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-AUTH-001` 문제·완료 조건
