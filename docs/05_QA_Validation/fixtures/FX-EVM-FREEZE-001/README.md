# Fixture: FX-EVM-FREEZE-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-24 19:19
> Status: Candidate

## 1. 목적

스테이블코인 토큰의 주소별 동결·블랙리스트 상태 또는 토큰 전체 pause
상태를 이벤트, 과거 상태와 발행사 공지로 교차검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-FREEZE-001` |
| 상태 | 후보 |
| 토큰·모드·주소·TX | 미선정 |
| 주요 소스 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM`, `DS-OSINT-WEB` |
| 승격 조건 | 확인 모드 고정, 상태·이벤트 재현, 발행사 출처 기록 |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 토큰, 확인 모드, 대상 주소, 기준 블록 |
| `expected.json` | 주소별 동결 또는 전체 pause 상태와 관련 이벤트 |
| `evidence.json` | 상태·로그 원본과 발행사 공지 provenance |

## 4. 검증 절차

1. 주소별 동결 또는 토큰 전체 pause 중 하나의 모드를 고정한다.
2. 토큰별 관련 이벤트와 상태 인터페이스를 확인한다.
3. 기준 블록에서 archive state를 조회한다.
4. 관련 이벤트 TX와 상태 변화 시점을 연결한다.
5. 발행사 공식 공지와 비교하고 충돌이 있으면 그대로 기록한다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - FREEZE 모드·허용 오차·승격 기준
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 상태·로그·OSINT 소스
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-FREEZE-001` 문제·완료 조건
