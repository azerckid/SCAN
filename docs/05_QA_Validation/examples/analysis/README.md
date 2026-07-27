# SCAN Analysis I/O Schema 0.1 Examples
> Created: 2026-07-26 12:26
> Last Updated: 2026-07-28 00:58

## 1. 목적

이 디렉터리는 confirmed fixture 3개를 공통 분석 요청·결과 Schema `0.1`로
변환한 계약 예제다. 실제 도구 실행 결과가 아니므로 `run.execution_mode`는
`fixture_example`, raw artifact는 `fixture://...` 참조를 사용한다.

## 2. 파일

| 분석 | 요청 | 결과 |
|:---|:---|:---|
| DEX | `dex-request.json` | `dex-result.json` |
| AUTH | `auth-request.json` | `auth-result.json` |
| FREEZE | `freeze-request.json` | `freeze-result.json` |

예제는 fixture의 모든 원본 증거를 복제하지 않는다. Schema의 공통 필드,
유형 분리, exact-match 핵심 결과와 참조 무결성을 보여주는 최소 예다.

TASK-006 실제 DEX analyzer는 이 예제의 세 result ID·raw 값을 유지하면서
`EV-DEX-METADATA` supporting provenance를 추가한다. 예제와 runtime의 증거
개수가 달라도 공개 Schema와 채점 결과의 의미는 바뀌지 않는다.

## 3. 검증

```bash
uv run python docs/05_QA_Validation/scripts/validate_analysis_schemas.py
uv run python scripts/check_analysis_schema.py
```

검증기는 세 요청·결과 쌍의 JSON Schema, ID 유일성, 결과→증거→소스 참조,
요청 source policy와 실제 사용 소스의 일관성을 검사한다. Pydantic 모델은
세 쌍을 의미 변경 없이 round-trip하며 두 번째 명령은 생성 Schema와 승인
Schema의 35개 probe 수락 결과를 비교한다.

## 4. 글로벌 평가 기준

| Criterion | Status | Evidence |
|:---|:---:|:---|
| Functionality | Pass | Schema 3종과 요청·결과 3쌍 자동 검증 |
| Potential Impact | Pass | 새 분석 유형·공급자에 재사용 가능한 공통 봉투 |
| Novelty | Pass | 확정 사실·맥락·휴리스틱·미평가와 증거 유형 분리 |
| UX | Pass | 부분 성공·오류·실행 상태의 일관된 CLI 표시 기반 |
| Open-source | Pass | 공개 JSON Schema와 독립 검증 예제 |
| Business Plan | N/A | 대회 준비용 기술 계약으로 현재 평가 범위가 아님 |

## 5. Related Documents

- **Technical_Specs**: [공통 분석 I/O Schema](../../../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 예제의 규범적 계약과 fixture 매핑
- **Technical_Specs**: [P0·V1 도구 요구사항](../../../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - exact-match 완료 조건
- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - 예제 원본 fixture 목록
- **QA_Validation**: [DEX](../../fixtures/FX-SVC-DEX-001/README.md), [AUTH](../../fixtures/FX-EVM-AUTH-001/README.md), [FREEZE](../../fixtures/FX-EVM-FREEZE-001/README.md) - 기준 패키지
- **QA_Validation**: [TASK-006 DEX 보고서](../../10_TASK_006_DEX_REPORT.md) - 예제와 실제 raw replay 결과 대조
