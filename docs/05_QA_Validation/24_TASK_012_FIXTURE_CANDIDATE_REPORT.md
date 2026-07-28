# TASK-012 범용 EVM Fixture 후보 선정 보고서
> Created: 2026-07-29 02:08
> Last Updated: 2026-07-29 02:46
> Status: Candidate Pack 0.1 · Implementation Not Started

## 1. 목적과 판정

TASK-012의 구현 전 첫 Gate로 `BASIC-EVM-001/002`,
`EVM-TOKEN-001/002`에 사용할 공개 사례와 reference answer 후보를
선정했다. 네 패키지는 Schema `0.1`, fixture `0.1`, 상태 `candidate`다.

**판정: 후보 선정 완료, confirmed 승격과 구현 착수는 미완료다.**

## 2. 공통 기준점

confirmed `FX-SVC-DEX-001`의 Ethereum 거래를 네 후보가 재사용한다.

| 필드 | 값 |
|:---|:---|
| TX | `0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5` |
| 블록 | `16642512` / `0xfdf1d0` |
| 블록 hash | `0x0a0aaeb9...2d1644` |
| 시각 | `2023-02-16T16:34:23Z` |
| EOA | `0xa406bc6e...a7fdf` |
| Router | `0xef1c6e67...54bf6b` |
| USDC | `0xa0b86991...06eb48` |

재사용은 expected 복사를 뜻하지 않는다. 각 문제의 답은 object RPC,
historical state, token transfer range, internal call에서 별도로 계산한다.
한 기준점을 쓰면 TX→receipt→block→state→event→internal call의 상호 참조를
한 번에 검증할 수 있다.

## 3. 후보와 기준 정답

| Fixture | 문제 | 결정적 답 | 현재 상태 |
|:---|:---|:---|:---:|
| [FX-BASIC-EVM-001](./fixtures/FX-BASIC-EVM-001/README.md) | 객체 식별 | EOA·contract·TX·block hash/number·invalid, fee `8115326069137440` wei | candidate |
| [FX-BASIC-EVM-002](./fixtures/FX-BASIC-EVM-002/README.md) | 과거 잔액 | ETH `148897435437879000853` wei, USDC `26470158088` raw | candidate |
| [FX-EVM-TOKEN-001](./fixtures/FX-EVM-TOKEN-001/README.md) | 첫 ERC-20 outgoing | log `275`, pool 수신, USDC `25000000000` raw | candidate |
| [FX-EVM-TOKEN-002](./fixtures/FX-EVM-TOKEN-002/README.md) | internal ETH 유입 | outer `0`, Router→EOA `14449515027026387018` wei | candidate |

모든 raw 금액 허용 오차는 `0`이다.

## 4. 1차 재조회 결과

| 조회 | 소스 | 결과 |
|:---|:---|:---|
| TX·receipt·block | `DS-EVM-RPC-PUBLIC` / Publicnode | 일치 |
| EOA·Router historical code | `DS-EVM-RPC-ARCHIVE` / dRPC | `0x` / non-empty 일치 |
| ETH balance | dRPC | `0x8125df4a3696fff15` |
| USDC balanceOf·decimals | dRPC | `0x629be8f08` / `6` |
| 시작 블록 이후 token transfer asc | `DS-EXPLORER-EVM` / Blockscout 호환 API | 첫 결과가 기준 TX |
| 거래별 token transfers | Blockscout v2 | log `275`, from/to/value 일치 |
| internal native transfer | Blockscout 호환 API | Router→EOA, 성공, 금액 일치 |

조회 시각은 `2026-07-28T17:08:25Z`다.

## 5. 소스 실패와 후보 상태 유지 이유

- Publicnode의 historical `eth_getLogs`는 개인 token이 필요한 archive
  요청으로 거부됐다.
- dRPC의 같은 `eth_getLogs`는 free route에서 suitable provider를 찾지
  못했다.
- 따라서 `EVM-TOKEN-001`의 “첫 전송”은 현재 raw receipt event +
  Blockscout ascending range의 조합이다. 독립 raw log 범위 재현 전에는
  `confirmed`로 올리지 않는다.
- Blockscout v2 internal endpoint는 이번 재조회에서 응답이 지연돼,
  호환 API로 성공 internal call을 재확인했다. 기존 confirmed DEX replay의
  상세 call index는 후보 증거로만 재사용한다.

실패한 공급자를 성공으로 기록하지 않으며, 대체 소스 사용 사실을 provenance에
남긴다.

## 6. 문제별 partial·failed 조건

| 문제 | Partial | Failed |
|:---|:---|:---|
| BASIC-EVM-001 | lexical type은 알지만 RPC 존재·code 확인 불가 | malformed를 객체로 강제, gas limit로 fee 계산 |
| BASIC-EVM-002 | archive 또는 decimals 일부 누락 | latest 대체, block 미표시, raw 정밀도 손실 |
| EVM-TOKEN-001 | event는 있으나 첫 순서 입증 불가 | 다른 token/from, 실패 TX, pagination 무시 |
| EVM-TOKEN-002 | TX는 있으나 trace/internal data 없음 | outer value만 답, 실패 call 합산, event로 call 대체 |

## 7. 다음 Gate

1. [x] primary·independent·supporting provider 후보 topology와 smoke 계약 문서화
2. [ ] 로컬 secret 구성 후 read-only capability smoke 통과
3. [ ] 네 패키지의 독립 공급자 2차 재현
4. [ ] Readiness §7·Capability QA §5와 이 보고서의
   checksum·timestamp→block·zero-value Transfer·failed internal call 반례
   **합집합** 통과
5. [ ] Analysis I/O version 영향과 네 result type 승인
6. [ ] CLI Preview의 complete·partial·failed 표시 재검토
7. [ ] TASK-012 Context Receipt `PASS`
8. [ ] 사용자 구현 착수 승인

이 여덟 조건 전에는 `TASK-012`를 `In Progress`로 바꾸거나 코드를 작성하지
않는다.

## 8. 365 글로벌 평가 기준

| 기준 | 판정 | 증거 |
|:---|:---:|:---|
| Functionality | Partial | 공개 원자료 1차 재조회, 구현·2차 재현은 미실행 |
| Potential Impact | Planned | 네 예상문항과 후속 PATH/INTEL 공통 입력 기반 |
| Novelty | Planned | 한 블록의 object/state/event/trace 교차 fixture |
| UX | Not Executed | CLI complete·partial·failed 재검토 전 |
| Open-source | Pass | 공개 RPC·Blockscout·재현 파라미터와 raw 값 기록 |
| Business Plan | N/A | 대회 준비 QA 범위 |

## 9. Originality·Ethics

- 공개 온체인 사실만 사용하며 주소 소유자나 범죄 의도를 평가하지 않는다.
- 기존 DEX fixture를 재사용하되 문제별 reference answer를 별도 원자료에서
  계산한다.
- provider UI 라벨·현재 가격·평판은 채점에서 제외한다.
- API key, credential, private key를 저장하지 않는다.

## 10. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 네 대상 문제의 완료·부분·실패 기준
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source 역할과 장애 기록
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - WP-EVM-CORE 계약
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - 공급자 후보·secret·smoke 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 Context Lock
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 공통 생명주기
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - QA-EXP-EVM-001/002
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 smoke·독립성·반례
