# SCAN 2026 분석 도구 기능 우선순위
> Created: 2026-07-25 15:49
> Last Updated: 2026-07-25 15:49
> Status: Draft 1

## 1. 문서 목적

이 문서는 30개 예상문제의 기능 적용 빈도와 confirmed reference fixture를
결합해 어떤 분석 기능을 먼저 요구사항으로 전환할지 결정한다.

현재 단계의 목적은 기술 스택이나 구현 언어를 확정하는 것이 아니다. 반복
문제 해결에 기여하는 공통 기능, 실제 사례로 검증 가능한 기능, 이후로
미뤄야 할 전문 기능을 구분하는 것이 목적이다.

## 2. 우선순위 입력

| 입력 | 현재 상태 | 이 문서에서의 사용 |
|:---|:---|:---|
| 예상문제 은행 | Draft 2, 30문항 | 필수·조건부 기능 적용 범위 |
| 데이터 소스 등록부 | Draft, EVM 핵심 소스 검증 중 | 외부 의존성과 재시도 위험 |
| 공통 fixture 스키마 | Confirmed 0.1 | 검증 입력·정답·증거 연결 계약 |
| `FX-SVC-DEX-001` | confirmed / 0.2 | 로그·DEX 해석·정합 검증 |
| `FX-EVM-AUTH-001` | confirmed / 0.2 | 권한 승인·소비·과거 상태 검증 |
| `FX-EVM-FREEZE-001` | confirmed / 0.2 | 동결 이벤트·상태·공식 맥락 검증 |
| SCAN 2026 세부 규정 | 미확인 | 규정 위험 점수는 임시값 |

confirmed fixture가 있다는 것은 도구 기능이 이미 구현됐다는 뜻이 아니다.
동일 입력·기준 정답·증거가 고정되어 그 기능을 구현 후 회귀 검증할 수 있다는
뜻이다.

## 3. 점수 산정 방법

### 3.1 계산식

```text
적용점수 C = 필수 문항 수 + (조건부 문항 수 × 0.5)

초기 우선순위 점수 =
  C
  + (시간 절감 T × 4)
  + (정확도 개선 A × 4)
  + (confirmed fixture 준비도 F × 5)
  - 구현 부담 E
  - 외부 의존 D
  - 오판 위험 R
  - 규정 위험 G
```

| 기호 | 범위 | 판단 기준 |
|:---:|:---:|:---|
| C | 0~30 | 문제은행 원자적 행렬의 필수·조건부 빈도 |
| T | 0~5 | 수작업 반복 시간을 줄이는 정도 |
| A | 0~5 | 누락·계산·증거 연결 오류를 줄이는 정도 |
| F | 0~3 | 해당 기능을 검증할 수 있는 confirmed fixture 수 |
| E | 0~5 | 구현·유지보수 복잡도 |
| D | 0~4 | 외부 API·archive·유료 데이터 의존도 |
| R | 0~4 | 자동 결과가 잘못된 결론을 만들 위험 |
| G | 0~2 | 공식 규정에 따라 사용이 제한될 가능성 |

T·A·E·D·R·G는 현재 문서와 세 fixture를 바탕으로 한 가안이다. 공식 규정,
팀 역량, 실제 구현 시간 측정값이 생기면 재평가한다.

### 3.2 단계 제한 규칙

- 전 문항 공통 기반은 개별 분석 기능보다 먼저 계약을 고정한다.
- 점수가 높아도 confirmed fixture가 없는 단일 문제용 전문 기능은 P3보다
  앞당기지 않는다.
- confirmed fixture가 있는 `AUTH-DECODE`, `FREEZE`는 전체 플랫폼
  우선순위와 별도로 최소 vertical slice를 먼저 만든다.
- 휴리스틱·라벨·OSINT 결과는 확정 사실과 분리하는 출력 계약이 없으면
  구현을 시작하지 않는다.
- 공식 규정에서 자동화·API 사용이 제한되면 G를 다시 평가하고 구현 범위를
  축소한다.

## 4. confirmed fixture와 기능 연결

| Fixture | 확정 입력·정답 | 직접 검증할 기능 | 공통 기반 |
|:---|:---|:---|:---|
| `FX-SVC-DEX-001` | USDC 입력, pool WETH 출력, user native ETH 출력 | `EVM-TX`, `EVM-LOG`, `RECON`, `LABEL`, `DECODE` | `BASE-CACHE`, `BASE-PROVENANCE`, `BASE-EXPORT` |
| `FX-EVM-AUTH-001` | 승인·소비 TX, allowance 4지점, `transferFrom` | `EVM-TX`, `EVM-STATE`, `EVM-LOG`, `EVM-TRACE`, `RECON`, `AUTH-DECODE` | 동일 |
| `FX-EVM-FREEZE-001` | 설정·해제 TX, 이벤트 2건, 상태 4지점 | `EVM-TX`, `EVM-STATE`, `EVM-LOG`, `RECON`, `OSINT`, `FREEZE` | 동일 |

세 fixture는 모두 raw 수량 또는 boolean exact match를 사용한다. 도구의 첫
회귀 검증은 이 세 사례에서 시작한다.

## 5. 원자적 기능 초기 점수

`F`는 fixture가 기능 검증 입력으로 사용 가능한 개수다. 점수는 구현 완료율이
아니며 Draft 1의 작업 순서 결정을 위한 비교값이다.

| 기능 | 필수 | 조건부 | C | T | A | F | E | D | R | G | 점수 |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE-EXPORT | 30 | 0 | 30 | 4 | 5 | 3 | 2 | 0 | 1 | 0 | 78 |
| BASE-PROVENANCE | 30 | 0 | 30 | 4 | 5 | 3 | 2 | 1 | 1 | 1 | 76 |
| BASE-CACHE | 30 | 0 | 30 | 5 | 4 | 3 | 3 | 2 | 1 | 1 | 74 |
| RECON | 24 | 0 | 24 | 5 | 5 | 3 | 3 | 1 | 1 | 0 | 74 |
| EVM-TX | 20 | 3 | 21.5 | 5 | 5 | 3 | 2 | 2 | 1 | 1 | 70.5 |
| EVM-LOG | 12 | 6 | 15 | 5 | 5 | 3 | 2 | 2 | 1 | 1 | 64 |
| PATH | 18 | 2 | 19 | 5 | 5 | 0 | 4 | 1 | 3 | 1 | 50 |
| DECODE | 7 | 5 | 9.5 | 5 | 5 | 1 | 4 | 2 | 2 | 1 | 45.5 |
| LABEL | 14 | 6 | 17 | 4 | 4 | 1 | 3 | 4 | 4 | 1 | 42 |
| EVM-STATE | 3 | 1 | 3.5 | 4 | 5 | 2 | 3 | 3 | 1 | 1 | 41.5 |
| EVM-TRACE | 2 | 5 | 4.5 | 5 | 5 | 1 | 4 | 3 | 2 | 1 | 39.5 |
| VIZ | 16 | 3 | 17.5 | 4 | 3 | 0 | 4 | 1 | 2 | 0 | 38.5 |
| AUTH-DECODE | 1 | 0 | 1 | 4 | 5 | 1 | 3 | 2 | 1 | 1 | 35 |
| FREEZE | 1 | 0 | 1 | 4 | 5 | 1 | 3 | 3 | 1 | 1 | 34 |
| BTC-UTXO | 3 | 1 | 3.5 | 4 | 5 | 0 | 3 | 2 | 2 | 1 | 31.5 |
| XCHAIN | 2 | 4 | 4 | 5 | 4 | 0 | 5 | 4 | 2 | 1 | 28 |
| LP-RUG | 1 | 0 | 1 | 4 | 5 | 0 | 4 | 2 | 2 | 1 | 28 |
| BRIDGE | 2 | 5 | 4.5 | 5 | 4 | 0 | 5 | 4 | 3 | 1 | 27.5 |
| OSINT | 6 | 9 | 10.5 | 3 | 3 | 1 | 3 | 4 | 4 | 1 | 27.5 |
| PROXY | 1 | 0 | 1 | 4 | 5 | 0 | 4 | 3 | 2 | 1 | 27 |
| HEUR | 7 | 2 | 8 | 4 | 3 | 0 | 4 | 1 | 4 | 1 | 26 |
| DEFI-LEND | 1 | 0 | 1 | 4 | 5 | 0 | 5 | 3 | 2 | 1 | 26 |
| PRICE | 1 | 0 | 1 | 4 | 4 | 0 | 3 | 4 | 2 | 1 | 23 |
| NFT-DECODE | 1 | 0 | 1 | 3 | 4 | 0 | 3 | 2 | 1 | 1 | 22 |
| MIXER | 1 | 0 | 1 | 3 | 2 | 0 | 5 | 3 | 4 | 1 | 8 |

## 6. 구현 우선순위 결정

### 6.1 P0 — 공통 기반과 결정적 EVM 입력

| 기능 | 우선 이유 |
|:---|:---|
| BASE-PROVENANCE | 모든 결론을 원본·출처·조회 시각·블록에 연결 |
| BASE-EXPORT | 모든 문제의 제출·검토 가능한 증거 산출 |
| BASE-CACHE | API 제한·장애·중단 후 재개 대응 |
| EVM-TX | 20개 필수, 3개 조건부 문제의 기본 입력 |
| EVM-LOG | 토큰·DEX·AUTH·FREEZE의 결정적 이벤트 입력 |
| RECON | 24문항의 시간·금액·자산·블록 정합 |

P0 완료 전에는 전문 분석 기능을 독립 도구로 확장하지 않는다.

### 6.2 V1 — confirmed fixture vertical slice

P0 계약 위에서 아래 세 경로를 end-to-end로 통과시킨다.

1. DEX: `EVM-LOG → DECODE → RECON → pool_output/user_net_output`
2. AUTH: `EVM-LOG/EVM-STATE/EVM-TRACE → AUTH-DECODE → 권한 소비`
3. FREEZE: `EVM-LOG/EVM-STATE → FREEZE → 온체인/공식 맥락 분리`

V1은 별도 제품 세 개를 만드는 단계가 아니다. 공통 입력·증거·출력 계약이
서로 다른 문제에서도 유지되는지 검증하는 최소 구현 경로다.

### 6.3 P1 — 핵심 분석 워크벤치

| 기능 | 우선 이유 |
|:---|:---|
| PATH | 18개 필수 문제의 N홉·관계 경로 탐색 |
| DECODE | 일반 토큰·DEX·프로토콜 의미 복원 |
| LABEL | 14개 필수 문제의 서비스·위험 주소 식별 |
| EVM-STATE | AUTH·FREEZE·PROXY 등 과거 상태 검증 |
| EVM-TRACE | 내부 ETH·권한 소비·익스플로잇 호출 검증 |
| VIZ | 16개 필수 문제의 그래프·타임라인 검토 |

LABEL과 VIZ는 증거가 아니라 판단 지원 화면이다. 원본 TX·출처로 되돌아갈
수 없는 라벨이나 그래프는 완료로 보지 않는다.

### 6.4 P2 — 체인·판단 범위 확장

| 기능 | 승격 조건 |
|:---|:---|
| BTC-UTXO | BTC 공개 fixture 1개 이상 확보 |
| XCHAIN, BRIDGE | 브리지 양단 fixture를 confirmed로 승격 |
| OSINT | 출처 보존·주소 명시 여부·인용 범위 계약 확정 |
| HEUR | 후보·신뢰도·반례·단정 금지 출력 형식 확정 |

### 6.5 P3 — 전문 어댑터

`NFT-DECODE`, `PROXY`, `MIXER`, `DEFI-LEND`, `PRICE`, `LP-RUG`는 각
문제의 적용 범위가 1개이고 confirmed fixture가 없다. 해당 fixture를
확보하거나 공식 출제 범위에서 중요도가 확인된 뒤 구현한다.

`LP-RUG`처럼 초기 점수가 P2 기능과 비슷해도 단계 제한 규칙을 우선한다.

## 7. 권장 구현 순서

1. provenance·export JSON 계약과 오류·불확실성 필드를 고정한다.
2. 캐시·재시도·rate limit·중단 후 재개 규칙을 명세한다.
3. EVM TX·receipt·log·과거 state의 공통 정규화 형식을 정의한다.
4. RECON의 raw 단위·소수점·시간·블록 정합 규칙을 정의한다.
5. DEX·AUTH·FREEZE vertical slice 요구사항을 작성한다.
6. 세 confirmed fixture를 자동 회귀 검증 입력으로 연결한다.
7. PATH·LABEL·VIZ·TRACE 요구사항을 문제별 완료 조건과 연결한다.
8. P2 fixture 확보 후 BTC·브리지·휴리스틱 범위를 확장한다.

## 8. P0·V1 완료 기준

- 동일 fixture를 반복 실행해 expected의 결정적 값이 exact match한다.
- 모든 출력 값에 source ID와 evidence ID가 연결된다.
- API 오류·timeout 후 재시도와 캐시 사용 여부가 기록된다.
- 원본 raw 값과 사람이 읽는 단위 변환값을 함께 제공한다.
- DEX의 pool output과 user net output을 구분한다.
- AUTH의 승인·소비와 탈취 판정을 구분한다.
- FREEZE의 온체인 상태와 발행사·규제기관 맥락을 구분한다.
- JSON·CSV·Markdown 중 최소 JSON과 사람이 읽는 증거 표를 출력한다.
- 실패·부분 성공이 fixture의 완료·부분·실패 조건과 연결된다.

## 9. 미결정 사항

- 2026년 공식 규정에 따른 G 점수 재평가
- 팀 구성과 담당 기능별 실제 구현 시간
- P0·V1의 CLI·노트북·웹 UI 경계
- Python·TypeScript·DuckDB 등 기술 조합
- 성능 목표와 로컬 캐시 용량
- 라벨 데이터의 무료·유료 소스 범위

## 10. 다음 단계

1. P0·V1을 `도구 요구사항` 문서로 전환한다.
2. 입력·출력·오류·캐시·provenance 인터페이스를 명세한다.
3. 기술 후보를 요구사항별로 비교하고 선택 기록을 작성한다.
4. 2026-07-27 등록 시작 후 규정 변경 기록을 작성하고 점수를 보정한다.
5. P2 승격에 필요한 BRIDGE·BTC fixture 공개 사례를 선정한다.

## 11. Related Documents

- **Concept_Design**: [참가·분석 도구 준비 전략](./01_SCAN_2026_PREPARATION_STRATEGY.md) - 문제 우선 접근과 기술 선택 원칙
- **Concept_Design**: [예상문제 은행](./02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항과 원자적 기능 빈도
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 공급자 능력·제약·최소 소스
- **Technical_Specs**: [Reference Fixture Schema](../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) - fixture JSON·증거 연결 계약
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - confirmed fixture와 승격 기준
- **QA_Validation**: [DEX fixture](../05_QA_Validation/fixtures/FX-SVC-DEX-001/README.md) - DEX vertical slice
- **QA_Validation**: [AUTH fixture](../05_QA_Validation/fixtures/FX-EVM-AUTH-001/README.md) - AUTH vertical slice
- **QA_Validation**: [FREEZE fixture](../05_QA_Validation/fixtures/FX-EVM-FREEZE-001/README.md) - FREEZE vertical slice
