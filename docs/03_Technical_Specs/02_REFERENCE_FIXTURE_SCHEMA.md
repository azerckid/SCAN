# SCAN 2026 Reference Fixture Schema
> Created: 2026-07-25 02:49
> Last Updated: 2026-07-25 03:04
> Status: Confirmed 0.1

## 1. 목적

이 문서는 SCAN 2026 분석 도구의 기준 입력·정답·증거 패키지가 같은 방식으로
해석되고 자동 검증되도록 공통 JSON 계약을 정의한다. 공통 계약은
`FX-SVC-DEX-001`, `FX-EVM-AUTH-001`, `FX-EVM-FREEZE-001`의 실제 데이터를
기준으로 작성했으며, fixture별 정답 필드는 확장 필드로 허용한다.

## 2. 버전 결정

| 필드 | 의미 | 변경 기준 |
|:---|:---|:---|
| `schema_version` | 공통 JSON 구조와 검증 규칙의 호환 버전 | 필수 필드·자료형·의미가 바뀔 때 변경 |
| `fixture_version` | 개별 fixture 데이터의 개정 버전 | TX·정답·증거·허용 오차가 바뀔 때 변경 |

현재 두 값은 모두 `0.1`이다. 두 버전은 우연히 같을 수 있지만 독립적으로
관리한다. 공통 구조만 바뀌면 `schema_version`만, 사례 데이터만 바뀌면
`fixture_version`만 올린다.

## 3. 패키지 구조

```text
fixtures/FX-.../
├── README.md
├── input.json
├── expected.json
└── evidence.json
```

| 파일 | 공통 책임 | fixture별 확장 예시 |
|:---|:---|:---|
| `input.json` | 문제 ID, 상태, 체인, 분석 시작점 | DEX TX, AUTH 승인·소비 TX, FREEZE 상태 블록 |
| `expected.json` | 허용 오차, 채점 요구사항, 기준 정답 | 자산 출력, allowance, 블랙리스트 전이 |
| `evidence.json` | 이벤트·호출·상태·맥락 증거와 provenance | Swap 로그, transferFrom trace, OFAC 원문 |

세 JSON은 `$schema`, `schema_version`, `fixture_version`, `fixture_id`,
`status`를 공통으로 가진다. `fixture_id`와 세 파일의 버전·상태는 패키지 안에서
모두 같아야 한다.

## 4. 증거 분리 원칙

| 배열 | 허용 내용 | 금지 내용 |
|:---|:---|:---|
| `event_evidence` | receipt 로그, topic, log index, 디코딩 값 | calldata·trace·정책 문서 |
| `call_evidence` | 외부 호출, 내부 trace, calldata, selector, 반환값 | 이벤트를 호출 사실로 대체 |
| `state_evidence` | 특정 블록의 상태 조회 결과와 디코딩 값 | 최신 상태를 과거 상태로 간주 |
| `context_evidence` | 발행사·규제기관·OSINT 원문과 해석 범위 | 온체인 사실이나 범죄 판단으로 승격 |

각 증거는 `evidence_id`, `evidence_type`, `source_id`를 가져야 한다.
`expected.json`의 채점 요구사항은 `evidence_refs`로 증거 ID를 참조한다.
맥락 증거는 `role: context`로 분류하며, 온체인 상태의 대체 증거로 사용하지 않는다.

## 5. 소스 역할

`evidence.json.source_requirements`는 소스의 목적과 필수 여부를 구조화한다.

| `role` | 의미 | 예시 |
|:---|:---|:---|
| `scoring` | 기준 정답을 직접 재현하거나 채점하는 소스 | receipt, trace, archive state |
| `context` | 사건·발행사·규제 맥락을 설명하는 소스 | OFAC 고시, Circle 정책 |
| `supporting` | 주소·ABI·UI 교차확인 등 보조 provenance | 공식 배포 주소, 탐색기 UI |

`required`는 역할과 별개다. 예를 들어 공식 맥락을 반드시 분리해야 하는 문제는
`role: context`, `required: true`가 될 수 있다. 반대로 교차확인 전용 출처는
`role: supporting`, `required: false`로 둔다.

## 6. 채점 요구사항

`expected.json.scoring.requirements`의 각 항목은 다음 필드를 가진다.

| 필드 | 설명 |
|:---|:---|
| `requirement_id` | fixture 안에서 유일한 채점 조건 ID |
| `description` | 사람이 이해할 수 있는 성공 조건 |
| `mandatory` | 전체 통과에 필수인지 여부 |
| `evidence_refs` | 조건을 입증하는 `evidence_id` 목록 |

fixture별 기존 `requires_...` 불리언은 사람이 빠르게 읽을 수 있는 요약으로
유지할 수 있다. 자동 검증과 증거 추적의 기준은 `requirements` 배열이다.

## 7. 확장과 호환성

1. 공통 스키마는 `additionalProperties: true`로 fixture별 분석 필드를 허용한다.
2. 공통 필드의 의미를 바꾸는 확장은 금지한다.
3. 선택 필드가 없으면 `null`을 남발하지 않고, 의미상 필요한 경우에만 명시한다.
4. raw 금액은 정밀도 손실을 피하기 위해 10진 문자열로 저장한다.
5. EVM 주소·TX 해시는 소문자 `0x` 형식을 기본으로 한다.
6. 확정 사실과 해석·휴리스틱은 같은 필드에 합치지 않는다.

## 8. JSON Schema와 검증

| 산출물 | 경로 |
|:---|:---|
| Input schema | `../05_QA_Validation/schemas/fixture-input.schema.json` |
| Expected schema | `../05_QA_Validation/schemas/fixture-expected.schema.json` |
| Evidence schema | `../05_QA_Validation/schemas/fixture-evidence.schema.json` |
| 검증 스크립트 | `../05_QA_Validation/scripts/validate_fixture_schemas.py` |
| Python 의존성 | `../05_QA_Validation/requirements-fixtures.txt` |

검증 환경은 Python 3.9 이상을 사용한다. 최초 1회 의존성을 설치한 뒤
검증기를 실행한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r docs/05_QA_Validation/requirements-fixtures.txt
python3 docs/05_QA_Validation/scripts/validate_fixture_schemas.py
```

`jsonschema`는 검증에 사용한 `4.26` 계열과 다음 메이저 버전 사이의
호환 범위로 고정한다. 시스템 Python에 직접 설치하지 않고 프로젝트
가상환경을 사용한다.

검증기는 JSON Schema 검사와 함께 다음 패키지 불변조건을 확인한다.

- 세 JSON의 fixture ID·schema version·fixture version·상태 일치
- 채점 요구사항 ID와 증거 ID의 유일성
- 모든 `evidence_refs`가 실제 증거를 가리키는지 확인
- 모든 source requirement가 provenance의 `source_id`와 연결되는지 확인

## 9. 0.1 적용 결정

| 결정 | 결과 |
|:---|:---|
| DEX 이벤트의 `type` 혼용 | `evidence_type`으로 통일 |
| FREEZE 이벤트 안의 calldata | `call_evidence`로 분리 |
| FREEZE 발행사·규제 자료 | `context_evidence`로 통합 |
| 필수·보조 소스의 문장 표기 | `source_requirements`로 구조화 |
| 채점 불리언만 존재 | `requirements`와 `evidence_refs` 추가 |
| fixture 버전의 구조 버전 겸용 | `schema_version`을 별도 도입 |

세 검증 중 fixture가 공통 스키마와 패키지 불변조건을 모두 통과하면
공통 스키마 `0.1`을 적용한 것으로 본다. 이는 개별 fixture의 `확정` 승격을
의미하지 않는다.

## 10. 0.2 후보

| 우선순위 | 후보 | 수용 조건 |
|:---:|:---|:---|
| Medium | 증거 배열별 자동 분리 검사 | `event_evidence`에서 calldata·selector·trace 필드를 거부하고, 올바른 `call_evidence` 이동을 오류 메시지로 안내 |
| Low | 맥락 증거 연결 구조 | 채점용 `evidence_refs`와 별도로 `context_requirements`를 정의해 미참조 provenance의 의도를 명시 |
| Low | 복수 공급자 식별 | 같은 `source_id`에 여러 공급자가 있을 때 `source_record_id`로 provenance 레코드를 구분 |

위 항목은 `0.1`의 확정이나 개별 fixture 검증을 막지 않는다. 공통 필수 필드나
증거 의미를 바꾸는 경우에만 `schema_version`을 `0.2`로 올린다.

## 11. Related Documents

- **Concept_Design**: [SCAN 2026 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제별 완료·부분·실패 조건
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - `DS-...` 소스 ID와 제약
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - fixture 목록과 승격 기준
- **QA_Validation**: [DEX](../05_QA_Validation/fixtures/FX-SVC-DEX-001/README.md), [AUTH](../05_QA_Validation/fixtures/FX-EVM-AUTH-001/README.md), [FREEZE](../05_QA_Validation/fixtures/FX-EVM-FREEZE-001/README.md) - 0.1 적용 대상
