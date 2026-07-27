# TASK-002 Analysis I/O Contract 검증 보고서
> Created: 2026-07-27 21:22
> Last Updated: 2026-07-27 21:22
> Status: Passed · QA-SCHEMA-001~002

## 1. 판정

`TASK-002`의 Analysis I/O Pydantic model, runtime 불변조건과 승인 JSON
Schema `0.1` 의미 호환성 Gate는 통과했다. source adapter·SQLite·CLI 분석
명령·DEX/AUTH/FREEZE 실행 엔진은 구현하지 않았으며 live API·AI·agent·CTFd
자동 제출도 활성화하지 않았다.

| 항목 | 결과 |
|:---|:---|
| 기준 code commit | `48c1442` |
| branch | `codex/task-002-analysis-contract-models` |
| Python | `3.13.7` |
| Pydantic | `2.13.4` |
| Schema | Analysis I/O `0.1` 유지 |
| QA | `QA-SCHEMA-001`, `QA-SCHEMA-002` pass |

## 2. 구현된 계약

| 영역 | 구현 |
|:---|:---|
| Request | DEX·AUTH·FREEZE discriminated union, source policy, 분석별 input |
| Result | complete·partial·failed discriminated union, result·evidence·source·run |
| Error | 승인된 11개 오류 코드, retry·source·attempt·evidence 참조 |
| Strictness | 알 수 없는 field 금지, 주소·hash·ID·block·datetime 형식 검증 |
| Raw value | ASCII uint256 십진 문자열, `uint256.max` 포함 무손실 처리 |
| References | result·warning·error→evidence→source 존재성과 일치 검사 |
| Status | complete/partial/failed별 result·warning·error 조합 검사 |
| Envelope | request/result의 `analysis_id`, `analysis_type`, 허용 source 일치 |

구현 위치:

- `src/scan_tool/domain/analysis_request.py`
- `src/scan_tool/domain/analysis_result.py`
- `src/scan_tool/domain/analysis_error.py`
- `src/scan_tool/domain/validation.py`
- `scripts/check_analysis_schema.py`

## 3. Schema 의미 호환성

Pydantic이 생성한 JSON Schema와 승인 Schema는 표현 구조가 완전히 같지 않다.
예를 들어 Pydantic discriminated union은 `oneOf`를 사용하고 승인 Schema는
일부 조건을 `if/then`으로 표현한다. 따라서 텍스트나 AST 동일성을 호환성으로
오인하지 않고, 승인된 세 request/result 예제와 35개 양성·음성 probe를 두
Schema에 각각 적용해 accept/reject 결과가 같은지 검사한다.

| 검증 | 결과 |
|:---|:---|
| 승인 Schema validator | `PASS 3` |
| 생성 Schema 의미 호환성 | `PASS 3`, 35 probes |
| request/result round-trip | DEX·AUTH·FREEZE 3쌍 pass |
| 승인 Schema version | `0.1`, 변경 없음 |

재현 명령:

```bash
uv sync --locked
uv run python scripts/verify.py
uv run python scripts/check_analysis_schema.py
```

## 4. Runtime 불변조건

JSON Schema만으로 안정적으로 표현하기 어려운 참조·집합·순서 조건은
Pydantic runtime validation으로 분리했다.

- `source_order`는 허용 source의 부분집합이며 중복이 없다.
- datetime은 timezone을 가져야 하고 실행 종료는 시작보다 빠를 수 없다.
- result·evidence·source ID는 각 범위에서 유일하다.
- 모든 `evidence_refs`는 존재하고 evidence의 `source_record_id`도 존재한다.
- 참조되지 않는 evidence와 source record는 허용하지 않는다.
- fallback source·attempt 참조는 실제 provenance와 연결된다.
- result envelope는 원 request의 ID·type·허용 source와 일치한다.
- complete·partial·failed 상태는 결과·warning·error 조합과 일치한다.

이 분리는 공개 Schema 계약을 느슨하게 만들기 위한 것이 아니라, cross-record
불변조건을 실행 시점에 결정적으로 거부하기 위한 것이다.

## 5. 오류 분류와 비노출

| 분류 | 대표 입력 | 결과 |
|:---|:---|:---|
| `invalid_input` | 잘못된 주소·TX hash·block·analysis type | failed, exit code 2용 오류 |
| `schema_invalid` | extra field·float raw·naive datetime·중복/누락 참조·상태 충돌 | failed, exit code 2용 오류 |

Validation issue에는 원본 입력을 포함하지 않는다. provider credential이나
Authorization header를 입력 계약으로 받지 않으며, 오류 문자열에 검사 대상
원문을 재출력하지 않는다.

## 6. Dependency Gate

| package | version | 역할 | license |
|:---|:---:|:---|:---|
| `pydantic` | `2.13.4` | runtime model·validation·Schema 생성 | MIT |
| `pydantic-core` | `2.46.4` | Pydantic validation core | MIT |
| `annotated-types` | `0.8.0` | annotation constraint 보조 | MIT |
| `typing-inspection` | `0.4.2` | typing inspection 보조 | MIT |

잠금 dependency를 `pip-audit`로 확인한 결과는
`No known vulnerabilities found`였다. `pip-audit`은 임시 검증 도구이며
project dependency에는 추가하지 않았다.

## 7. 실행 증거

| 검증 | 결과 |
|:---|:---|
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass |
| `uv run pytest` | `31 passed` |
| fixture Schema validator | `PASS 3` |
| analysis Schema validator | `PASS 3` |
| generated Schema compatibility | `PASS 3`, 35 probes |
| 외부 네트워크 | test·validator 실행 중 0회 |
| DB·cache·artifact write | 없음 |

## 8. 보안·부작용 경계

- 테스트와 검증기는 저장 example·Schema·fixture만 읽는다.
- 사용자 홈 credential과 실제 `.scan/`을 읽거나 변경하지 않는다.
- private key·seed phrase·API key·CTFd credential 입력은 없다.
- 오류 변환은 원본 validation input을 포함하지 않는다.
- 분석·서명·거래 전송·자동 제출·외부 AI 호출은 없다.

## 9. 365 글로벌 평가 기준

| 기준 | TASK-002 반영 |
|:---|:---|
| Functionality | 31 test, 3쌍 round-trip, 35개 Schema probe, 참조 불변조건 |
| Potential Impact | 모든 후속 분석 기능이 공유하는 typed request/result/error 경계 |
| Novelty | evidence-first 참조 무결성과 complete/partial/failed 계약 결합 |
| UX | `invalid_input`과 `schema_invalid`를 분리해 다음 행동의 기반 제공 |
| Open-source | MIT dependency, lockfile, 재현 명령, 취약점 점검 |
| Business Plan | runtime 계약 구현 범위가 아니므로 N/A |

## 10. Originality & Ethics Check

- 승인된 자체 Schema와 공개 fixture의 provenance를 유지했다.
- fixture 정답이나 제3자에 대한 탈취·범죄·현재 제재 판단을 변경하지 않았다.
- 외부 코드의 도메인 모델을 복제하지 않고 Pydantic 공개 API로 계약을 직접
  구현했다.
- 의존성 license와 잠금 버전, 취약점 점검 결과를 기록했다.
- 비공개 문제·답안·개인정보·credential을 외부 서비스에 전송하지 않았다.

## 11. 남은 경계

- `TASK-003` source port·policy·retry·fallback: 별도 승인 필요
- `TASK-004` SQLite cache·checkpoint·artifact: 미구현
- `TASK-005` CLI validate/analyze/show/export: 미구현
- DEX·AUTH·FREEZE 실행 엔진: `TASK-006`~`TASK-008`
- live API·AI·agent·CTFd 자동 제출: Rules 확인과 별도 승인 전 비활성

## 12. Related Documents

- [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md)
- [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md)
- [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md)
- [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)
- [P0·V1 QA Checklist](./02_QA_CHECKLIST.md)
- [분석 I/O 예제](./examples/analysis/README.md)
