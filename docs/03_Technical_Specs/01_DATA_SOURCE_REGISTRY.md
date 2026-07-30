# SCAN 2026 데이터 소스 등록부
> Created: 2026-07-24 15:49
> Last Updated: 2026-07-30 14:19
> Status: Draft · TASK-009 Offline Integration Passed · Rules Unclear

## 1. 문서 목적

이 문서는 SCAN 2026 예상문제 풀이와 분석 도구가 의존할 수 있는 데이터 소스의 능력·제약·대체 경로를 등록한다. 현재 단계는 공급자 확정이 아니라 **비교 가능한 등록부**를 만드는 것이다.

입력 문서:

- [SCAN 2026 예상문제 은행 Draft 2](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md)

병행 문서:

- [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md)
- [Reference Fixture Schema](./02_REFERENCE_FIXTURE_SCHEMA.md)
- [P0·V1 분석 도구 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md)
- [P0·V1 기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md)

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
| 상태 | 검증 중 | 검증 중 |
| 마지막 확인 | 2026-07-25 15:25 | 2026-07-25 15:25 |
| 비고 | 기존 confirmed 3개와 TASK-013 NFT 후보 2개의 receipt/log를 확인. endpoint·credential은 fixture에 저장하지 않음 | 기존 confirmed 3개와 TASK-013 Proxy 후보의 historical implementation/admin slot을 확인. 공급자 역할과 decoded match만 candidate evidence에 기록 |

#### 5.1.1 Phase 2 live provider 후보

| 논리 역할 | 후보 | 문서상 capability | 미확정 사항 | 상태 |
|:---|:---|:---|:---|:---:|
| `PROVIDER-EVM-PRIMARY` | QuickNode Ethereum | archive·Debug·Trace·Ethereum JSON-RPC | smoke 7/7·fixture replay 10/10; credential 회전·rate/timeout 반례 | verifying |
| `PROVIDER-EVM-VERIFY` | Alchemy Ethereum | 기본 RPC·historical archive·filtered logs | smoke 6/6·fixture replay 9/9; debug·parity trace 모두 HTTP 400 | verifying / trace rejected |
| `PROVIDER-EVM-EXPLORER` | Blockscout | transaction·log·internal transaction 교차확인 | 원본 RPC·독립 trace 대체 불가 | supporting |
| `PROVIDER-EVM-TRACE-VERIFY` | 비차단 후속 | 엄격한 fixture 승격용 독립 trace | Alchemy HTTP 400·Chainstack Developer HTTP 403 | deferred |

이 topology는 채택 기록이 아니다. pre-event read-only smoke 이후 TASK-012
fixture 공통 9개 조회도 두 공급자에서 독립 실행해 decoded summary가 모두
일치했고 primary trace도 성공했다. Alchemy의 debug·parity trace는
각각 HTTP 400으로 실패했으므로 독립 trace·rate behavior는 미완료다.
Chainstack Developer/Full endpoint도 Ethereum Mainnet chain ID는 반환했지만
두 trace dialect가 HTTP 403으로 거부되어 독립 Trace 역할에서 제외했다.
실전 분석은 QuickNode raw Trace를 사용할 수 있고, 독립 Trace는 엄격한
fixture 승격을 위한 비차단 후속으로 관리한다.
설정 중 대화에 노출된 credential은 대회 사용과 후속 지속 호출 전 회전해야 한다. 회전한
endpoint·API key는 로컬 secret 환경에만 두고 source record에는 논리
provider ID, method, block tag, 조회 시각, 안전한 오류 코드, raw SHA-256만
남긴다. 상세 Gate와 공식 근거는
[Live Provider Readiness](./10_LIVE_PROVIDER_READINESS.md)를 따른다.

#### 5.1.2 대회 제공 입력과 artifact

| 논리 source | 입력 모드 | 제공 데이터 | 현재 상태 |
|:---|:---|:---|:---:|
| `DS-CONTEST-RPC` | `contest_rpc` | 주최 read-only RPC의 TX·receipt·block·state·logs·trace | core adapter 구현, CLI wiring 미구현 |
| `DS-CONTEST-ARTIFACT` | `provided_artifact` | 문제 첨부 JSON/JSONL/CSV/raw TX·receipt·logs·trace | JSON·JSONL·CSV bounded importer 구현, 임의 mapping·CLI 미구현 |
| `DS-SELF-NODE` | `external_rpc` 또는 local source | 검증된 client가 제공하는 chain 원자료 | 운영·규정·비용 미결정 |

외부 API가 금지되면 탐색기 API를 자동 대체재로 간주하지 않는다. RPC와
Explorer가 모두 외부 서비스로 제한될 수 있으므로 공식 Rules와 문제 제공
형식에 따라 `DS-CONTEST-RPC` 또는 `DS-CONTEST-ARTIFACT`를 선택한다.
세 입력 경로는 정규화 이후 동일 evidence 계약을 사용해야 한다.

자체 노드는 가능한 source 후보지만 EVM 실행/Trace 엔진을 SCAN에서
재구현한다는 뜻이 아니다. 검증된 client의 read-only 결과를 adapter로
가져온다. 상세 계약은
[다중 입력 모드와 체인 범위](./12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md)를
따른다.

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
| 상태 | 검증 중 |
| 마지막 확인 | 2026-07-25 15:25 |
| 관련 fixture | FLOW-EVM-001, SVC-DEX-001, EVM-AUTH-001, EVM-FREEZE-001 |
| 비고 | `FX-SVC-DEX-001`의 internal ETH, `FX-EVM-AUTH-001`의 거래·token transfer·internal trace, `FX-EVM-FREEZE-001`의 blacklist 설정·해제 성공 호출과 대상을 **Blockscout API**로 검증. DEX 확정 재현에서는 V2 endpoint timeout 후 호환 API가 동일 내부 전송을 반환. Etherscan TX 페이지는 UI 교차확인만이며 API 검증으로 치지 않음 |

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
| 관련 fixture | BTC-CJ-001 | BTC-UTXO-001 추가 세트 |

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
| 상태 | 후보 | 검증 중 |
| 마지막 확인 | 2026-07-30 03:07 | 2026-07-30 03:07 |
| 관련 fixture | FLOW-EVM-001 등 | EVM-FREEZE-001 (`FX-EVM-FREEZE-001`) |
| 비고 | Etherscan public label/name tag는 Terms 때문에 fixture source에서 제외. replacement는 pinned OpenRAIL research/testing sample row와 MIT Tornado config·onchain ENS의 category conflict이며 상업·전체 dataset 권한으로 확대하지 않음 | OFAC SLS의 공개 download/API와 2022 지정·2025 해제 원문에서 주소·timeline 후보를 확인. 고시 시점의 역사적 맥락이며 현재 제재 상태로 자동 간주하지 않음 |

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
| 상태 | 후보 | 검증 중 |
| 마지막 확인 | 2026-07-30 03:07 | 2026-07-30 03:07 |
| 관련 fixture | OSINT-ENS-001 | EVM-FREEZE-001 (`FX-EVM-FREEZE-001`) |
| 비고 | ENS forward/reverse는 고정 block의 onchain RPC로 재계산하고 공식 문서의 양방향 검증 원칙을 적용. `ensjs` MIT provenance는 supporting. ENS 웹 profile/content는 Terms 경계 때문에 fixture에 복제하지 않음 | Circle 공식 블로그·USDC Terms·컨트랙트 주소 문서와 거래 이전 공식 커밋 `b42cf04...59d9`의 `Blacklistable.sol`·MIT 라이선스·파일 해시를 확인. 주소별 공지와 정책·대응 맥락을 구분 |

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
| 상태 | 후보 | 검증 중 | 후보 |
| 마지막 확인 | 2026-07-24 15:49 | 2026-07-25 15:13 | 2026-07-24 15:49 |
| 관련 fixture | SVC-BRG-001 | SVC-DEX-001 (`FX-SVC-DEX-001`), EVM-AUTH-001 (`FX-EVM-AUTH-001`) | FLOW-MULTI-001 |
| 비고 |  | DEX Universal Router: 거래 이전 공식 커밋 `d2575ff...f9f`의 `mainnet.json` `UniversalRouter` 주소·파일 해시·GPL-3.0 라이선스 고정. Factory: V2 Deployments. Pool: Pair Addresses 가이드 + 거래 시점 `eth_call getPair` 기록. AUTH `SwapRouter02`: 공식 `sdk-core` 커밋 `baff6d3c...d28a`의 `SWAP_ROUTER_02_ADDRESSES(1)`과 MIT 라이선스 고정 |  |

## 6. fixture별 최소 소스 요구

| Fixture / 문제 ID | 최소 필요 소스 | 없으면 영향 |
|:---|:---|:---|
| BASIC-EVM-001 | `DS-EVM-RPC-PUBLIC`, historical code 사용 시 `DS-EVM-RPC-ARCHIVE` | 객체 존재·TX fee·EOA/contract 구분 불가 |
| BASIC-EVM-002 | `DS-EVM-RPC-ARCHIVE`, `DS-EVM-RPC-PUBLIC` | 기준 블록 잔액·timestamp 고정 불가 |
| EVM-TOKEN-001 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM` 또는 범위 logs 지원 archive | 이벤트 또는 첫 전송 순서 입증 불가 |
| EVM-TOKEN-002 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM` 또는 trace 지원 RPC | top-level과 internal native 유입 분리 불가 |
| FLOW-EVM-001 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-LABEL-PUBLIC` | 경로·라벨 검증 불가 |
| SVC-DEX-001 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-DEX-META` | in/out 복원 불가 |
| SVC-BRG-001 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-BRIDGE-META` | 양단 매칭 실패 |
| EVM-AUTH-001 | `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM` | 승인·allowance·권한 소비 연결 불가 |
| EVM-NFT-001 | `DS-EVM-RPC-PUBLIC`, 범위 완전성 확인 시 logs 지원 RPC | 표준 event·tokenId·amount·승인 순서 입증 불가 |
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

## 8.1 TASK-003 구현 기준선

- `DS-...`는 정책·provenance의 논리 source ID이고 `provider_id`는 실제
  공급자 식별자다.
- JSON-RPC와 REST adapter는 주입된 HTTPX client로 한 번의 read만 수행한다.
- retry·backoff·fallback은 adapter가 아니라 application orchestration이
  관리한다.
- timeout·429·HTTP 500·502·503·504만 자동 재시도한다. 400·501·malformed
  JSON은 재시도하지 않는다.
- 최초 1회와 retry 2회, base 0.5초 지수 backoff·jitter,
  `Retry-After` 우선을 구현 기준선으로 둔다.
- 규정이 `restricted`이거나 live 실행이 `unconfirmed`이면 호출 전에
  `rule_restricted`로 차단한다. offline mode도 transport 호출을 0건으로
  유지한다.
- 실제 endpoint·API key·provider별 rate limit은 코드에 내장하지 않았으며
  공식 규정·계정·plan 확인 전 live provider 구성을 만들지 않는다.

## 8.2 TASK-004 저장 기준선

- source request fingerprint에 chain ID를 결합한 SHA-256을 cache key로 쓴다.
- 고정 block tag 응답만 immutable cache로 자동 저장한다. `latest`와
  `pending`은 자동 cache하지 않는다.
- cache row는 source·provider·capability·block tag·artifact hash·safe
  endpoint host/path·retrieved time·fallback source를 보존한다.
- source attempt는 provider별 번호를 append하며 outcome·failure kind·
  wait seconds·raw hash·artifact hash를 보존한다.
- raw body는 SQLite가 아니라 content-addressed artifact에 저장한다.
- 같은 cache key에 다른 artifact·source provenance가 들어오면 덮어쓰지 않고
  conflict로 거부한다.
- 실제 사용자 `.scan/` composition root는 TASK-005에서 만들었다. TASK-006
  DEX analyzer는 confirmed fixture에서 검토한 raw transaction·receipt·internal
  call·metadata artifact만 읽는다. live provider 구성은 여전히 만들지 않았다.

## 8.3 TASK-006 DEX source 기준선

- `DS-EVM-RPC-PUBLIC`은 raw transaction·receipt의 scoring source,
  `DS-EXPLORER-EVM`은 internal native call의 scoring source다.
- `DS-EVM-RPC-ARCHIVE`의 `getPair` 결과와 `DS-DEX-META`의 pinned 주소는
  pair·router provenance를 확인하는 supporting source다.
- reviewed `raw-replay.json`은 각 source ID·provider ID·조회 시각과 raw hex를
  보존하며 분석기는 이 파일 밖의 endpoint를 호출하지 않는다.
- 2026-07-28 재조회에서 TX·receipt log·internal call이 confirmed 기준값과
  일치했다. 이는 live 자동화 허용을 뜻하지 않는다.
- internal call이 없으면 `partial/trace_unavailable`, Transfer·Swap·Withdrawal
  정합이 깨지면 `failed/reconciliation_failed`로 증거를 보존한다.

## 8.4 TASK-007 AUTH source 기준선

- `DS-EVM-RPC-PUBLIC`은 Approval·Transfer raw transaction·receipt와 nonce
  327~329의 reverted transaction identity를 제공하는 scoring source다.
- `DS-EVM-RPC-ARCHIVE`는 allowance 네 지점과 성공 `transferFrom` trace를
  제공하는 scoring source다.
- `DS-EXPLORER-EVM`은 승인·소비 transaction과 Transfer log의 독립
  cross-check source이며 `DS-DEX-META`는 pinned SwapRouter02 provenance다.
- reviewed `raw-replay.json`은 source ID, 조회 시각, raw calldata·log·state·
  trace를 보존하며 analyzer는 endpoint나 API key를 갖지 않는다.
- state 또는 trace 누락은 `partial`, raw 정합 위반은 `failed`로 처리하고,
  source가 제공하지 않는 theft/phishing 귀속은 `not_assessed`로 유지한다.

## 8.5 TASK-008 FREEZE source 기준선

- `DS-EVM-RPC-ARCHIVE`는 blacklist·unblacklist event와 네 historical
  `isBlacklisted` state를 제공하는 scoring source다.
- `DS-EXPLORER-EVM`은 두 transaction의 method·대상 주소를 확인하는
  cross-check source다.
- `DS-OSINT-WEB`은 Circle의 주소 비특정 정책·대응 맥락,
  `DS-SANCTIONS-PUBLIC`은 OFAC의 주소 특정 지정·해제 맥락을 보존한다.
  어느 쪽도 현재 제재나 범죄 의도의 자동 판정 source가 아니다.
- `DS-EVM-RPC-PUBLIC`은 transaction·receipt 재확인에 사용하는 supporting
  source이며 archive state를 대체하지 않는다.
- reviewed `raw-replay.json`은 source·provider·조회 시각·raw hex·고정
  인터페이스 provenance를 보존한다. analyzer는 live endpoint를 호출하지 않는다.
- historical state나 한 전이가 없으면 `partial`, call·event·state가
  충돌하면 `failed`다. global pause는 해당 fixture에서 `applicable=false`다.

## 9. 다음 단계

1. confirmed fixture 3개의 source 기준선을 유지한다.
2. 공식 규정은 `미확인`으로 유지하고 Notification Intake 결과가 있을 때 갱신한다.
3. live provider 구성 전 공식 plan·rate limit·fallback을 재확인한다.
4. TASK-004 cache·attempt 저장 기준선을 TASK-005 CLI composition root에 주입했다.
5. live source가 제한되면 offline fixture·cache·human fallback을 사용한다.
6. TASK-006~008 세 offline replay source 기준선을 유지한다.
7. TASK-009에서 세 source 경계와 failure matrix를 통합 회귀했다.
8. TASK-010과 live source는 공식 Rules·명시적 opt-in·별도 승인 전까지
   비활성 상태를 유지한다.
9. TASK-012 fixture 4개는 QuickNode·Alchemy로 TX·receipt·block·historical
   code/balance/call·범위 지정 `eth_getLogs`를 독립 재현해 공통 9개 decoded
   값이 일치했다. 이 fixture들은 offline provenance 정책에 따라
   `confirmed 0.2`로 승격했으며 provider별 raw SHA와 조회 시각은 로컬
   artifact, 재현 요약은 fixture `provider-replay.json`에 보존한다.
10. primary trace는 성공했지만 Alchemy 독립 trace는 HTTP 400으로 실패했다.
    독립 trace는 비차단 후속이며 provider `adopted` 판정과 live
    rate/timeout Gate는 계속 별도로 유지한다.
11. 기본 network 0건인 opt-in smoke runner를 준비했다. Rules `allowed`와
    역할별 HTTPS endpoint가 없으면 실제 adapter 호출 전에 중단한다.

### 9.1 TASK-015 공개 source 후보 기준선

- OFAC 공식 action과 Sanctions List Service는 주소 직접 명시·목록 시점·
  해제 이력을 보존하는 `DS-SANCTIONS-PUBLIC` 후보로 사용한다.
- ENS 사실은 고정 block onchain forward/reverse로 재계산한다. 문서와
  `ensjs` MIT 구현은 알고리즘·provenance supporting source이며 웹 profile
  원문은 fixture에 복제하지 않는다.
- Etherscan public label은 Terms가 label/name tag 복제와 AI/ML·dataset
  사용을 제한하므로 `DS-LABEL-PUBLIC` fixture source로 채택하지 않는다.
- MyEtherWallet `ethereum-lists`는 MIT source 후보지만 선택 주소가 실제
  목록에 있을 때만 assertion을 만든다.
- Actor 후보는 기존 confirmed FLOW·DEX·AUTH replay에서 재계산한다.
  공통 funder·공용 contract는 ownership 또는 coordination 확정이 아니다.
- Etherscan을 쓰지 않는 replacement subject를 선정해 현재 다섯 후보가 모두
  viable이다. pinned dataset/config, official HTML, fixed-block ENS,
  confirmed local replay의 SHA-256 기준선을 기록했다.
- snapshot 기준선은 fixture package가 아니다. selected artifact·negative
  oracle·독립 Verifier 전에는 `verifying`으로 승격하지 않는다.

### 9.2 TASK-015 analyzer 이후 source·승격 경계

- `intel_context` analyzer와 독립 hash 대조는 통과했지만 source permission과
  fact correctness를 같은 Gate로 취급하지 않는다.
- Codatta 선택 행은 dataset card의 OpenRAIL·research/testing 범위만 확인됐다.
  exact license text·notice·재배포 의무를 pin하기 전 label fixture는
  `verifying`을 유지한다.
- OFAC action은 공식 locator·whole-file hash·bounded match를 사용하고, 현재
  SLS 전체 CSV는 repository에 재배포하지 않는다.
- ENS는 웹 Interface 내용을 복제하지 않고 fixed-block onchain artifact를
  사용한다. 새 RPC/Explorer 호출은 승격 필수 조건이 아니며 Rules 허용 시에만
  read-only로 실행한다.
- relation-hub는 confirmed DEX/AUTH local fixture만으로 승격 검토할 수 있다.
  common-funder는 bounded prehistory·service exclusion 전까지 candidate다.
- 상세 판정은 [TASK-015 Live Source·Terms·Promotion Readiness](../05_QA_Validation/54_TASK_015_LIVE_SOURCE_TERMS_PROMOTION_READINESS.md)를 따른다.

## 10. Related Documents

- **Concept_Design**: [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 준비 전략과 위험·제약
- **Concept_Design**: [SCAN 2026 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - Draft 2 기능·fixture 요구의 기준
- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 소스 의존성·fallback을 반영한 기능 순서
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - source별 대회 허용 상태와 Notification Intake
- **Technical_Specs**: [SQLite 논리 DB Schema](./01_DB_SCHEMA.md) - source attempt·cache·artifact 보존 구조
- **Technical_Specs**: [P0·V1 분석 도구 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md) - source policy·cache·fallback·오류 계약
- **Technical_Specs**: [P0·V1 기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md) - HTTP transport·source adapter·저장 경계
- **Technical_Specs**: [Live Provider Readiness](./10_LIVE_PROVIDER_READINESS.md) - Phase 2 후보 topology·secret·capability Gate
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - 소스 검증용 대표 사례
- **QA_Validation**: [TASK-003 Source 보고서](../05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) - source transport·policy·retry·fallback 검증
- **QA_Validation**: [TASK-004 Storage 보고서](../05_QA_Validation/08_TASK_004_STORAGE_REPORT.md) - source attempt·cache·artifact 저장 검증
- **QA_Validation**: [TASK-005 CLI 보고서](../05_QA_Validation/09_TASK_005_CLI_REPORT.md) - source policy 차단·CLI 오류·exit code 검증
- **QA_Validation**: [TASK-006 DEX 보고서](../05_QA_Validation/10_TASK_006_DEX_REPORT.md) - reviewed raw source·재조회·정합 검증
- **QA_Validation**: [TASK-007 AUTH 보고서](../05_QA_Validation/11_TASK_007_AUTH_REPORT.md) - public/archive/trace/explorer raw source·재조회·정합 검증
- **QA_Validation**: [TASK-008 FREEZE 보고서](../05_QA_Validation/12_TASK_008_FREEZE_REPORT.md) - public/archive/explorer/issuer/OFAC source·재조회·정합 검증
- **QA_Validation**: [TASK-009 통합 보고서](../05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) - source 실패·offline 불변·보안 통합 회귀
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](../05_QA_Validation/24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - EVM Core 1차 재조회와 source 장애
- **QA_Validation**: [Live Provider Capability QA](../05_QA_Validation/25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 계정 smoke·독립성·반례
- **QA_Validation**: [Smoke Runner 준비 보고서](../05_QA_Validation/26_LIVE_PROVIDER_SMOKE_PREPARATION_REPORT.md) - dry-run·보안·미실행 경계
- **QA_Validation**: [TASK-015 공개 Source·Fixture 후보 조사](../05_QA_Validation/46_TASK_015_PUBLIC_SOURCE_CANDIDATE_REPORT.md) - Terms·privacy·후보 채택 가능성
- **QA_Validation**: [TASK-015 Source 교체·Raw Snapshot 기준선](../05_QA_Validation/47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md) - replacement와 artifact hash
