# SCAN 2026 Reference Fixtures
> Created: 2026-07-24 15:49
> Last Updated: 2026-07-24 21:30
> Status: Draft

## 1. 문서 목적

이 문서는 예상문제 은행 Draft 2의 대표 문제에 대해, 도구 정확성을 검증할 수 있는 reference fixture를 관리한다. 현재 단계는 **후보 8개 골격**을 고정하고, 공개 데이터 확보 후 `검증 중` → `확정`으로 승격한다.

입력 문서:

- [SCAN 2026 예상문제 은행 Draft 2](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md)

## 2. Rubric 정렬

| Rubric | 이 문서에서의 적용 |
|:---|:---|
| Functionality | fixture로 수집·디코딩·추적·환산 결과가 재현 가능한지 검증 |
| Potential Impact | 대회 문제 유형을 대표하는 최소 세트로 준비 효율을 높임 |
| Novelty | 확정/추정 분리, 불확실 연결, AUTH/PROXY/FREEZE 등 공백 기능을 포함 |
| UX | 증거 표·출처·허용 오차가 사람이 검수하기 쉽게 기록됨 |
| Open-source | 공개 사건·공개 온체인 데이터·자체 소규모 테스트 데이터를 우선 |
| Business Plan | 해당 없음 (대회 준비 QA). N/A |

## 3. 정보 구분 원칙

| 구분 | 적용 |
|:---|:---|
| 확정 사실 | 온체인에서 재조회 가능한 TX·로그·상태 |
| 과거 근거 | 공개 사건 보고서·사후분석 |
| 예상 | 아직 주소/TX를 고르지 않은 후보 구성 |
| 결정 | fixture 필드, 상태 코드, 허용 오차 정의 원칙 |
| 미결정 | 실제 주소·TX·기준 정답 값 |

## 4. Fixture 필드 표준

각 fixture는 아래 필드를 채운다.

| 필드 | 설명 |
|:---|:---|
| Fixture ID | `FX-...` |
| 연결 문제 ID | 예상문제 은행 ID |
| 상태 | 후보 / 검증 중 / 확정 / 폐기 |
| 데이터 형태 | 공개 사건 / 공개 온체인 / 자체 테스트 / JSON fixture |
| 체인 | 대상 체인 |
| 주소·TX | 시드 주소, TX 해시, 블록 |
| 기준 정답 | reference answer 요약 |
| 허용 오차 | raw 단위, 수수료, 가격 정밀도 규칙 |
| 확정 사실 | 재조회로 고정되는 사실. 필요 시 `확정 사실(이벤트)`와 `확정 사실(호출·상태)`처럼 증거 유형을 분행 |
| 휴리스틱 | 추정으로만 둘 항목. 문제 유형이 둘 이상이면 분기별로 나눔 |
| 필요 데이터 소스 | 등록부 소스 ID만 사용 (`DS-...`). 설명문·데이터 종류 나열 금지 |
| 재현 절차 | 단계 목록 |
| 저작권·출처 | URL, 라이선스/인용 주의 |
| 마지막 확인 | YYYY-MM-DD HH:mm |

### 4.1 허용 오차 정의 원칙

예상문제 은행 3.4와 동일하게, 금액·가격·수수료 오차는 fixture마다 명시한다.

| 유형 | 기본 원칙 |
|:---|:---|
| 네이티브/토큰 수량 | 가능하면 raw 정수 일치(오차 0). 사람이 읽는 단위는 decimals와 함께 병기 |
| 수수료 포함 경로 | 수수료를 제외한 자산 이동과 수수료를 분리 기록 |
| 스왑·브리지 | 수수료·슬리피지·브리지 비용을 명시한 뒤 net 금액 허용 범위를 적음 |
| 가격 환산 | 가격 출처, 시각, 통화, 소수점 자릿수를 고정. 허용 오차는 fixture에 수치로 기재 |
| 불확실 연결 | 정답 자체가 후보 집합인 경우 집합 포함 여부로 채점하고 단일 주소 단정은 실패 |

## 5. 대표 Fixture 목록

| Fixture ID | 문제 ID | Draft | 상태 | 핵심 검증 기능 |
|:---|:---|:---:|:---|:---|
| FX-FLOW-EVM-001 | FLOW-EVM-001 | 1 | 후보 | 수집, PATH, LABEL, 증거 |
| FX-SVC-DEX-001 | SVC-DEX-001 | 1 | 검증 중 | EVM-LOG, DECODE, RECON |
| FX-SVC-BRG-001 | SVC-BRG-001 | 1 | 후보 | XCHAIN, BRIDGE, RECON |
| FX-EVM-AUTH-001 | EVM-AUTH-001 | 2 | 검증 중 | AUTH-DECODE, allowance 연결 |
| FX-EVM-PROXY-001 | EVM-PROXY-001 | 2 | 후보 | PROXY, archive state |
| FX-EVM-FREEZE-001 | EVM-FREEZE-001 | 2 | 후보 | FREEZE, state/logs |
| FX-FLOW-MULTI-001 | FLOW-MULTI-001 | 2 | 후보 | RECON, PRICE, 다주소 집계 |
| FX-UNCERTAIN-001 | SVC-MIX-001 또는 BTC-CJ-001 | 2 | 후보 | MIXER 또는 HEUR(CoinJoin), 불확실성 태그 |

## 6. Fixture 상세

`후보` fixture의 `TBD`는 공개 사례 확정 후 채운다. `검증 중` fixture는 패키지의 JSON을 기준 정답과 provenance 원본으로 사용한다.

---

### FX-FLOW-EVM-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | FLOW-EVM-001 |
| 상태 | 후보 |
| 데이터 형태 | 공개 사건 + 공개 온체인 |
| 체인 | TBD (EVM) |
| 주소·TX | 피해 주소 A=TBD, 피해 시각 창=TBD, 근거 TX 목록=TBD |
| 기준 정답 | 최종 도착 서비스/주소, 이동 금액, 홉별 TX |
| 허용 오차 | 토큰/ETH raw 오차 0. 수수료는 별도 표기. 환전이 있으면 net 허용 범위를 fixture 확정 시 수치화 |
| 확정 사실 | 각 홉의 TX·from/to·value |
| 휴리스틱 | 미라벨 입금주소의 거래소 귀속 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-LABEL-PUBLIC` |
| 재현 절차 | 1) A 출금 수집 2) 시간·금액 필터 3) N홉 추적 4) 라벨 교차검증 5) 증거 표 출력 |
| 저작권·출처 | 공개 사건 보고서 URL=TBD. 본문 복제 없이 사실 요약만 |
| 마지막 확인 | 2026-07-24 15:49 |

---

### FX-SVC-DEX-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | SVC-DEX-001 |
| 상태 | 검증 중 |
| 패키지 | [FX-SVC-DEX-001](./fixtures/FX-SVC-DEX-001/README.md) |
| 데이터 형태 | 공개 온체인 / JSON fixture |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | TX `0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5`, 라우터 `0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b`, 풀 `0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc` |
| 기준 정답 | USDC in `25000000000` raw; pool_output WETH `14449515027026387018`; user_net_output ETH 동일 raw |
| 허용 오차 | raw 오차 0 |
| 확정 사실 | Transfer·Swap·Withdrawal 로그 + Router→user internal ETH 전송 |
| 휴리스틱 | 해당 없음 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-DEX-META` |
| 재현 절차 | RPC 로그로 pool_output 계산 → Blockscout API로 user_net_output 확인 → Factory.getPair로 풀 provenance |
| 저작권·출처 | publicnode RPC, Blockscout API, Uniswap deploy JSON/V2 Deployments/Pair Addresses, Etherscan UI(교차만). 본문 복제 없음 |
| 마지막 확인 | 2026-07-24 19:48 |

---

### FX-SVC-BRG-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | SVC-BRG-001 |
| 상태 | 후보 |
| 데이터 형태 | 공개 온체인 |
| 체인 | 출발 TBD, 도착 TBD |
| 주소·TX | 출발 TX=TBD, 도착 TX=TBD, 브리지=TBD |
| 기준 정답 | 출발·도착 TX 쌍, 도착 주소, 매칭 키 |
| 허용 오차 | 브리지 수수료로 인한 금액 차이를 fixture에 명시. raw 기준 허용 범위 TBD |
| 확정 사실 | 양단 이벤트/전송 |
| 휴리스틱 | 유사 금액 후보 중 최종 선택 근거 |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`, `DS-BRIDGE-META` |
| 재현 절차 | 1) 출발 이벤트 2) destination 힌트 3) 도착 매칭 4) 교차검증 |
| 저작권·출처 | 브리지 탐색기/문서 URL=TBD |
| 마지막 확인 | 2026-07-24 15:49 |

---

### FX-EVM-AUTH-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-AUTH-001 |
| 상태 | 검증 중 |
| 패키지 | [FX-EVM-AUTH-001](./fixtures/FX-EVM-AUTH-001/README.md) |
| 데이터 형태 | 공개 온체인 |
| 체인 | Ethereum (`chain_id` 1) |
| 주소·TX | V `0x193070...af59`, USDC, 승인 TX `0x3f7037...dabd`, 소비 TX `0x7b888f...af51` |
| 기준 정답 | `approve` calldata·Approval 로그 + Router의 `transferFrom` trace + USDC `4500000` raw 전송 + allowance 4지점 |
| 허용 오차 | allowance·전송량 raw 오차 0 |
| 확정 사실(이벤트) | `Approval` 로그. 소비 구간에 `Transfer` 등 전송 이벤트가 있으면 별도 행으로 기록. 호출 calldata와 한 줄로 합치지 않음 |
| 확정 사실(호출·상태) | `approve`/`permit` 호출 TX·calldata·nonce, allowance 전후 상태(archive), `TransferFrom`(또는 동등) 소비 호출 TX. 이벤트 로그와 한 줄로 합치지 않음 |
| 휴리스틱 | 피싱·탈취·피해자 여부는 판정하지 않음. fixture는 권한 소비 연결만 검증 |
| 필수 데이터 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM` |
| 보조 provenance | `DS-DEX-META` — `SwapRouter02` 공식 주소 확인용이며 권한 소비 채점의 필수 소스는 아님 |
| 재현 절차 | Approval·approve calldata → archive allowance 전후 → 실패 TX 제외 → 성공 TX trace의 transferFrom → Transfer 로그·감소량 대조 |
| 저작권·출처 | publicnode RPC, dRPC archive/trace, Blockscout API, Uniswap Deployments. 본문 복제 없음 |
| 마지막 확인 | 2026-07-24 21:30 |

---

### FX-EVM-PROXY-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-PROXY-001 |
| 상태 | 후보 |
| 데이터 형태 | 공개 온체인 |
| 체인 | TBD (EVM) |
| 주소·TX | 프록시 P=TBD, upgrade TX 목록=TBD |
| 기준 정답 | 구현체 이력, admin/권한 변경, 근거 TX·슬롯 값 |
| 허용 오차 | 해당 없음(주소·슬롯 exact match) |
| 확정 사실 | implementation slot, Upgraded/AdminChanged 이벤트 |
| 휴리스틱 | 비표준 프록시 패턴 해석 |
| 필요 데이터 소스 | `DS-EVM-RPC-ARCHIVE` |
| 재현 절차 | 1) 현재 구현체 조회 2) 이벤트 이력 3) 슬롯 historical 조회 4) 타임라인 |
| 저작권·출처 | TBD |
| 마지막 확인 | 2026-07-24 16:03 |

---

### FX-EVM-FREEZE-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | EVM-FREEZE-001 |
| 상태 | 후보 |
| 데이터 형태 | 공개 온체인 + 발행사 공지 |
| 체인 | TBD (EVM) |
| 주소·TX | 토큰 T=TBD, 확인 모드=주소별 또는 pause, 대상 A=TBD(해당 시), 이벤트 TX=TBD |
| 기준 정답 | 모드별 동결/pause 여부, 이벤트·상태 근거 |
| 허용 오차 | 해당 없음(boolean/상태 exact) |
| 확정 사실 | 블랙리스트/pause 이벤트 및 상태 값 |
| 휴리스틱 | 공지와 온체인 불일치 시 충돌로 기록 |
| 필요 데이터 소스 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM`, `DS-OSINT-WEB` |
| 재현 절차 | 1) 모드 선택 2) 이벤트 검색 3) 상태 조회 4) 공지 교차검증 |
| 저작권·출처 | 발행사 공지 URL=TBD |
| 마지막 확인 | 2026-07-24 16:03 |

---

### FX-FLOW-MULTI-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | FLOW-MULTI-001 |
| 상태 | 후보 |
| 데이터 형태 | 공개 사건 또는 합성 집계 세트 |
| 체인 | TBD |
| 주소·TX | 출구/시드=TBD, 피해자 목록=TBD, 가격 기준 시각=TBD |
| 기준 정답 | 피해자별 유입, 합계, 환산 피해액, 가격 출처 |
| 허용 오차 | 유입 raw 오차 0. 환산액은 가격 소수점 N자리와 허용 절대/상대 오차를 fixture 확정 시 수치화 |
| 확정 사실 | 피해자별 TX와 수량 |
| 휴리스틱 | 사건 귀속 범위(포함/제외 피해자) |
| 필요 데이터 소스 | `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`, `DS-PRICE` |
| 재현 절차 | 1) 유입 수집 2) 정규화 3) 가격 조회 4) 합계·환산 5) 출구 연결 |
| 저작권·출처 | 사건 보고서·가격 API 출처=TBD |
| 마지막 확인 | 2026-07-24 16:03 |

---

### FX-UNCERTAIN-001

| 필드 | 내용 |
|:---|:---|
| 연결 문제 ID | `SVC-MIX-001` 또는 `BTC-CJ-001` (fixture 확정 시 하나로 고정. 둘을 한 카드의 동일 확정 사실로 쓰지 않음) |
| 상태 | 후보 |
| 데이터 형태 | 공개 사례 |
| 체인 | `SVC-MIX-001`이면 EVM, `BTC-CJ-001`이면 Bitcoin |
| 주소·TX | 유입 TX=TBD, 유출/후속 후보=TBD |
| 기준 정답 | 유입 확정 + 유출 후보 집합 + 항목별 태그(확정/후보/불가). 채점 기준은 아래 분기 확정 사실만 사용 |
| 허용 오차 | 집합 채점. 단일 출구 단정은 실패 |
| 확정 사실 (`SVC-MIX-001`) | 믹서 유입 TX, 믹서 컨트랙트 주소, 라벨·출처 URL. 유출 주소는 확정 사실에 넣지 않음 |
| 확정 사실 (`BTC-CJ-001`) | 해당 TXID의 입출력 주소·금액·vout 등 재조회 가능 필드만. CoinJoin 여부 자체는 확정 사실이 아님 |
| 휴리스틱 (`SVC-MIX-001`) | 유출 후보 집합과 연결 강도 |
| 휴리스틱 (`BTC-CJ-001`) | CoinJoin(또는 유사 혼합) 가능성 점수, 이후 추적 후보 집합 |
| 필요 데이터 소스 | `DS-LABEL-PUBLIC`; EVM이면 `DS-EVM-RPC-PUBLIC` 또는 `DS-EXPLORER-EVM`; Bitcoin이면 `DS-BTC-API` |
| 재현 절차 | 1) 문제 ID 분기 확정 2) 분기별 확정 사실만 기록 3) 휴리스틱 후보 생성 4) 태그 부여 5) 단정 금지 확인 |
| 저작권·출처 | TBD |
| 마지막 확인 | 2026-07-24 19:14 |

## 7. 승격 기준

| 상태 | 조건 |
|:---|:---|
| 후보 | 필드 골격만 존재, 주소/TX TBD |
| 검증 중 | 공개 데이터 확보, 수동 재현 1회 성공, 필요 소스 등록부에 연결 |
| 확정 | 기준 정답·허용 오차 수치 고정, 동일 입력 재현 성공, 출처·저작권 기록 완료 |
| 폐기 | 데이터 삭제·비공개 전환·중복·규정 위반 위험 |

## 8. 미결정 사항

- 8개 후보의 실제 공개 사건/TX 선정
- `FX-UNCERTAIN-001`을 믹서와 CoinJoin 중 무엇으로 고정할지
- `fixture_version: 0.1` JSON 필드의 공통 스키마 확정 여부
- 가격 아카이브 공급자 확정
- 저작권상 보고서를 어느 수준까지 인용할지

## 9. 다음 단계

1. 데이터 소스 등록부와 함께 각 fixture의 공개 데이터 확보 가능성을 점검한다.
2. `FX-SVC-DEX-001`, `FX-EVM-AUTH-001`은 검증 중으로 승격됨. 다음은 [FX-EVM-FREEZE-001](./fixtures/FX-EVM-FREEZE-001/README.md) 공개 사례를 선정한다.
3. 각 디렉터리의 `input.json`, `expected.json`, `evidence.json`을 채우고 수동 재현에 성공하면 `검증 중`으로 올린다.
4. 기능 우선순위 문서에 확정 fixture를 검증 입력으로 연결한다.

## 10. Related Documents

- **Concept_Design**: [SCAN 2026 예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 문제·완료조건·대표 사례 후보의 기준
- **Concept_Design**: [SCAN 2026 참가·분석 도구 준비 전략](../01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) - 준비 전략
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - fixture별 필요 소스와 제약
- **QA_Validation**: [FX-SVC-DEX-001](./fixtures/FX-SVC-DEX-001/README.md), [FX-EVM-AUTH-001](./fixtures/FX-EVM-AUTH-001/README.md), [FX-EVM-FREEZE-001](./fixtures/FX-EVM-FREEZE-001/README.md) - 우선 구축 fixture 패키지
- 후속 문서 후보: `../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md`, `../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md`
