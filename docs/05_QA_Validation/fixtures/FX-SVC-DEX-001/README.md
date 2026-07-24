# Fixture: FX-SVC-DEX-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-24 19:19
> Status: Candidate

## 1. 목적

실제 EVM DEX 스왑 한 건을 기준으로 로그 수집, 이벤트 디코딩, 입력·출력
자산 정합, DEX 메타데이터 연결과 증거 출력을 검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `SVC-DEX-001` |
| 상태 | 후보 |
| 체인·TX | 미선정 |
| 주요 소스 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-DEX-META` |
| 승격 조건 | 공개 TX 선정, 수동 재현 1회 성공, 기준 정답·출처 고정 |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 체인 ID와 스왑 TX 등 도구 입력 |
| `expected.json` | 입력·출력 자산, 수량, DEX·라우터·풀 기준 정답 |
| `evidence.json` | 원본 로그, 출처, 조회 시각과 provenance |

## 4. 검증 절차

1. 공개 검증에 적합한 단일 또는 멀티홉 스왑 TX를 선정한다.
2. receipt와 전체 로그를 수집한다.
3. 토큰 decimals를 확인하고 입력·출력 raw 수량을 계산한다.
4. DEX·라우터·풀 메타데이터를 출처와 함께 연결한다.
5. `expected.json`과 `evidence.json`을 채운 뒤 동일 입력으로 재현한다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - fixture 필드·허용 오차·승격 기준
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 등록 소스 ID와 제약
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `SVC-DEX-001` 문제·완료 조건
