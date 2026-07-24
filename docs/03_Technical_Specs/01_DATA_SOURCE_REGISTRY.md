# SCAN 2026 데이터 소스 등록부
> Created: 2026-07-24 15:49
> Last Updated: 2026-07-24 16:03
> Status: Draft

## 1. 문서 목적

이 문서는 SCAN 2026 예상문제 풀이와 분석 도구가 의존할 수 있는 데이터 소스의 능력·제약·대체 경로를 등록한다. 현재 단계는 공급자 확정이 아니라 **비교 가능한 등록부**를 만드는 것이다.

입력 문서:

- [SCAN 2026 예상문제 은행 Draft 2](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md)

병행 문서:

- [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md)

## 2. 정보 구분 원칙

| 구분 | 적용 |
|:---|:---|
| 확정 사실 | 공개 문서·요금표·엔드포인트로 확인한 내용 |
| 과거 근거 | 일반적인 온체인 분석에서 널리 쓰이는 소스 유형 |
| 예상 | 대회 중 필요 가능성 |
| 결정 | 등록 필드, 상태 코드, fixture와 병행 선정 원칙 |
| 미결정 | 최종 공급자, 유료 구독, 대회 규정상 허용 여부 |

## 3. 등록 필드 표준

각 소스는 아래 필드를 채운다. 값이 아직 없으면 `미확인`으로 두고 확인일을 남긴다.

| 필드 | 설명 |
|:---|:---|
| 소스 ID | `DS-...` 형식 |
| 유형 | RPC / 탐색기 API / BTC / 라벨 / 제재 / OSINT / 브리지 / DEX / 가격 / 기타 |
| 제공 데이터 | TX, receipt, logs, trace, historical state, UTXO 등 |
| 지원 체인 | 명시된 체인 목록 |
| API 키 | 필요 / 선택 / 불필요 |
| 호출 제한 | rate limit, 일일 쿼리, 페이지 크기 |
| 과거 데이터 | archive / pruned / 제한적 / 미확인 |
| 비용 | 무료 / 프리티어 / 유료 |
| 신뢰도 | 원본 노드에 가까울수록 높음. 라벨은 출처 의존 |
| 캐시·재시도 | 권장 캐시 키, 재시도, 중단 후 재개 |
| 원본 보존 | 저장할 필드(응답, 시각, 엔드포인트, 블록) |
| 대체 소스 | 장애·제한 시 후보 |
| 이용약관 주의 | 재배포·상업 이용·스크래핑 제한 |
| 대회 규정 | 허용 / 금지 / 미확인 |
| 상태 | 후보 / 검증 중 / 채택 / 제외 |
| 마지막 확인 | YYYY-MM-DD HH:mm |

## 4. 소스 선정과 fixture 병행 원칙

1. fixture에 필요한 데이터가 없는 소스는 대표 검증용으로 채택하지 않는다.
2. archive historical state, logs, trace, 가격 시점 데이터가 필요한 fixture를 먼저 고른다.
3. 동일 기능에 대해 최소 1개의 무료/공개 대체 경로를 확보한다.
4. 라벨·OSINT는 항상 출처 URL과 수집 시각을 보존한다.
5. 대회 규정이 공개되기 전에는 모든 소스의 `대회 규정`을 `미확인`으로 둔다.

## 5. 소스 등록부 (Draft)

아래 항목의 구체 한도·가격은 공급자 정책 변경이 잦으므로, 채택 전에 공식 문서로 재확인한다.

### 5.1 EVM RPC

| 필드 | DS-EVM-RPC-PUBLIC | DS-EVM-RPC-ARCHIVE |
|:---|:---|:---|
| 유형 | RPC | RPC (archive) |
| 제공 데이터 | TX, receipt, 일부 logs, 최신 state | TX, receipt, logs, historical state, (공급자별) trace |
| 지원 체인 | Ethereum 등 EVM (공급자별) | 동일, archive 플랜 의존 |
| API 키 | 경우에 따라 | 경우에 따라 |
| 호출 제한 | 공급자별 | 공급자별, 보통 더 엄격 |
| 과거 데이터 | pruned 가능 | archive 필요 기능에 필수 |
| 비용 | 무료~유료 | 대개 유료 또는 제한적 프리티어 |
| 신뢰도 | 높음(원본에 근접) | 높음 |
| 캐시·재시도 | 블록·TX 해시 키, 지수 백오프 | 동일 + historical 호출 우선순위 큐 |
| 원본 보존 | raw JSON-RPC 응답, endpoint, 시각 | 동일 |
| 대체 소스 | 다른 RPC, 탐색기 API | 다른 archive 공급자, 탐색기 historical API |
| 이용약관 주의 | 공급자 ToS | 동일 |
| 대회 규정 | 미확인 | 미확인 |
| 상태 | 후보 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-24 15:49 |
| 비고 | `BASIC`, `FLOW` 기본 조회 | `EVM-PROXY`, `BASIC-EVM-002`, `EVM-FREEZE`에 중요 |

### 5.2 탐색기 API

| 필드 | DS-EXPLORER-EVM |
|:---|:---|
| 유형 | 탐색기 API |
| 제공 데이터 | 주소 거래 목록, 토큰 전송, 내부 tx(지원 시), 일부 라벨 |
| 지원 체인 | 탐색기별 멀티체인 |
| API 키 | 경우에 따라 |
| 호출 제한 | 있음 (키/플랜별) |
| 과거 데이터 | 지원 범위 확인 필요 |
| 비용 | 무료~유료 |
| 신뢰도 | 중~고 (인덱스 지연·누락 가능) |
| 캐시·재시도 | 주소+페이지 키, 페이지네이션 커서 보존 |
| 원본 보존 | API 응답, 페이지 파라미터, 시각 |
| 대체 소스 | RPC + self-index, 다른 탐색기 |
| 이용약관 주의 | 스크래핑·재배포 제한 가능 |
| 대회 규정 | 미확인 |
| 상태 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 |
| 관련 fixture | FLOW-EVM-001, SVC-DEX-001, EVM-AUTH-001 |

### 5.3 Bitcoin UTXO

| 필드 | DS-BTC-API | DS-BTC-NODE |
|:---|:---|:---|
| 유형 | BTC API | 로컬/원격 Bitcoin 노드 |
| 제공 데이터 | TX, 입출력, 소비 관계, 주소 이력(API별) | TX, UTXO set, raw block |
| 지원 체인 | Bitcoin | Bitcoin |
| API 키 | 공급자별 | 불필요(자체) |
| 호출 제한 | 있음 | 로컬 자원 한계 |
| 과거 데이터 | 대부분 지원 | full node 기준 전체 |
| 비용 | 혼합 | 운영 비용 |
| 신뢰도 | 중~고 | 높음 |
| 캐시·재시도 | TXID 키 | 로컬 캐시 |
| 원본 보존 | API 응답 또는 raw TX | raw TX/block |
| 대체 소스 | 다른 BTC API, 로컬 노드 | 다른 노드, BTC API |
| 이용약관 주의 | API ToS | 해당 시 호스팅 약관 |
| 대회 규정 | 미확인 | 미확인 |
| 상태 | 후보 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-24 15:49 |
| 관련 fixture | BTC-CJ-001 (또는 BTC-UTXO-001 추가 세트) |

### 5.4 주소 라벨·제재 목록

| 필드 | DS-LABEL-PUBLIC | DS-SANCTIONS-PUBLIC |
|:---|:---|:---|
| 유형 | 라벨 | 제재·위험 목록 |
| 제공 데이터 | 거래소·서비스·사건 라벨 | 제재·고위험 주소 |
| 지원 체인 | 목록별 | 목록별 |
| API 키 | 없거나 선택 | 없음~선택 |
| 호출 제한 | 낮음~중간 | 낮음 |
| 과거 데이터 | 버전 관리 필요 | 버전·고시일 관리 필요 |
| 비용 | 무료~혼합 | 무료(공개 고시) |
| 신뢰도 | 중 (충돌·전파 오류 가능) | 고(공식 고시) / 중(2차 정리본) |
| 캐시·재시도 | 주소 키 + 목록 버전 | 목록 버전 + 배포일 |
| 원본 보존 | 라벨, 출처 URL, 버전, 수집 시각 | 고시문·URL·버전 |
| 대체 소스 | 다른 라벨 DB, 탐색기 라벨 | 공식 원문, 다른 정리본 |
| 이용약관 주의 | 재배포 제한 가능 | 공적 자료라도 2차 라이선스 확인 |
| 대회 규정 | 미확인 | 미확인 |
| 상태 | 후보 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-24 15:49 |

### 5.5 ENS·OSINT

| 필드 | DS-ENS | DS-OSINT-WEB |
|:---|:---|:---|
| 유형 | OSINT / 이름서비스 | OSINT |
| 제공 데이터 | ENS resolve/reverse, 관련 TX | 검색결과, 보고서, SNS·도메인 단서 |
| 지원 체인 | Ethereum 중심 | 체인 무관 |
| API 키 | 경우에 따라 | 검색엔진·플랫폼별 |
| 호출 제한 | 공급자별 | 플랫폼별 |
| 과거 데이터 | 온체인 이력 + 인덱서 | 페이지 보존 필요 |
| 비용 | 무료~혼합 | 무료~혼합 |
| 신뢰도 | 온체인 설정은 고, 소셜은 저~중 | 출처 의존 |
| 캐시·재시도 | 이름·주소 키 | URL 스냅샷 |
| 원본 보존 | resolve 결과, TX, URL | URL, 인용, 수집 시각 |
| 대체 소스 | 다른 ENS 인덱서, 탐색기 | 다른 검색·아카이브 |
| 이용약관 주의 | API ToS, SNS ToS | 스크래핑·자동화 제한 |
| 대회 규정 | 미확인 | 미확인 |
| 상태 | 후보 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-24 15:49 |

### 5.6 브리지·DEX·가격

| 필드 | DS-BRIDGE-META | DS-DEX-META | DS-PRICE |
|:---|:---|:---|:---|
| 유형 | 브리지 | DEX | 가격 |
| 제공 데이터 | 출발·도착 매칭 힌트, 체인 ID, 메시지/탐색기 | 라우터·페어·풀 메타, 이벤트 ABI | 시점 가격, OHLC, 심볼 매핑 |
| 지원 체인 | 브리지별 | DEX·체인별 | 자산·거래소별 |
| API 키 | 경우에 따라 | 경우에 따라 | 경우에 따라 |
| 호출 제한 | 있음 | 있음 | 있음 |
| 과거 데이터 | 탐색기·자체 인덱스 | 이벤트 로그 기반 | 아카이브 지원 여부 핵심 |
| 비용 | 혼합 | 혼합 | 무료~유료 |
| 신뢰도 | 중~고 | 이벤트 원본은 고 | 피드 품질 의존 |
| 캐시·재시도 | 메시지/TX 쌍 키 | 페어+블록 키 | 심볼+시각 키 |
| 원본 보존 | 매칭 키, 양단 TX | 이벤트 raw | 가격, 출처, 시각, 통화 |
| 대체 소스 | 양단 RPC 수동 매칭 | 로그 직접 디코딩 | 다른 가격 API, DEX TWAP |
| 이용약관 주의 | 각 서비스 ToS | 동일 | 재배포·지연 데이터 제한 |
| 대회 규정 | 미확인 | 미확인 | 미확인 |
| 상태 | 후보 | 후보 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-24 15:49 | 2026-07-24 15:49 |
| 관련 fixture | SVC-BRG-001 | SVC-DEX-001 | FLOW-MULTI-001 |

## 6. fixture별 최소 소스 요구

| Fixture / 문제 ID | 최소 필요 소스 | 없으면 영향 |
|:---|:---|:---|
| FLOW-EVM-001 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-LABEL-PUBLIC` | 경로·라벨 검증 불가 |
| SVC-DEX-001 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-DEX-META` | in/out 복원 불가 |
| SVC-BRG-001 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-BRIDGE-META` | 양단 매칭 실패 |
| EVM-AUTH-001 | `DS-EXPLORER-EVM` 또는 `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE` | 승인·allowance·탈취 연결 불가 |
| EVM-PROXY-001 | `DS-EVM-RPC-ARCHIVE` | 구현체 이력 검증 불가 |
| EVM-FREEZE-001 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM`, `DS-OSINT-WEB` | 동결 여부 확정 불가 |
| FLOW-MULTI-001 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-PRICE` | 환산 피해액 실패 |
| SVC-MIX-001 / BTC-CJ-001 | `DS-LABEL-PUBLIC` + (`DS-EVM-RPC-PUBLIC`/`DS-EXPLORER-EVM` 또는 `DS-BTC-API`) | 불확실성 사례 구성 불가 |

## 7. 캐시·재시도·원본 보존 공통 규칙

예상문제 은행의 `BASE-CACHE`, `BASE-PROVENANCE`, `BASE-EXPORT`와 맞춘다.

| 규칙 | 내용 |
|:---|:---|
| 캐시 키 | 체인 + 메서드 + 파라미터 정규화 문자열 |
| 재시도 | 429/5xx에 지수 백오프, idempotent 조회만 자동 재시도 |
| 페이지네이션 | 커서·페이지 번호를 메타와 함께 저장해 중단 후 재개 |
| 원본 보존 | raw 응답, 출처, 조회 시각, 사용 블록/높이 |
| 라벨 보존 | 라벨 값과 출처를 분리 저장, 충돌 시 둘 다 유지 |
| 가격 보존 | 심볼, 시각, 통화, 출처, 사용한 소수점 |

## 8. 미결정 사항

- 최종 RPC·탐색기·가격 공급자 선정
- 유료 archive / trace 플랜 필요 여부
- 로컬 Bitcoin 노드 운영 여부
- 상용 라벨·포렌식 서비스 사용 가능 여부 (대회 규정 대기)
- API 키 보관 방식과 팀 공유 범위
- 각 소스의 정확한 rate limit 수치 (공식 문서 재확인 필요)

## 9. 다음 단계

1. [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) 후보 8개의 공개 데이터 확보 가능성을 소스별로 점검한다.
2. 확보 가능한 fixture를 `검증 중`으로 올리고 필요 소스를 `검증 중`으로 승격한다.
3. 2026-07-27 이후 공식 규정에 따라 `대회 규정` 필드를 갱신한다.
4. 채택 소스 목록을 기능 우선순위 문서 입력으로 넘긴다.

## 10. Related Documents

- **Concept_Design**: [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 준비 전략과 위험·제약
- **Concept_Design**: [SCAN 2026 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - Draft 2 기능·fixture 요구의 기준
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - 소스 검증용 대표 사례
- 후속 문서 후보: `../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md`, `../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md`
