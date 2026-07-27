# TASK-006 DEX Vertical Slice 검증 보고서
> Created: 2026-07-28 00:58
> Last Updated: 2026-07-28 00:58
> Status: TASK-006 Scope Passed · Offline Raw Replay Only

## 1. 판정

TASK-006 DEX vertical slice는 통과했다. confirmed Uniswap V2 공개 사례의 raw
transaction·receipt log·internal native call을 독립 디코딩하고 다음 세 값을
Analysis I/O Schema `0.1` 결과로 정확히 재현한다.

| 결과 ID | 자산 | raw 값 |
|:---|:---:|---:|
| `RES-DEX-ASSET-IN` | USDC | `25000000000` |
| `RES-DEX-POOL-OUTPUT` | WETH | `14449515027026387018` |
| `RES-DEX-USER-NET-OUTPUT` | ETH native | `14449515027026387018` |

WETH pool output과 native ETH user output은 같은 수량이어도 별도 결과·증거로
유지한다. live RPC·탐색기 endpoint는 연결하지 않았고 CTFd·서명·AI 기능도
추가하지 않았다.

## 2. 구현 범위

| 영역 | 구현 |
|:---|:---|
| Raw contract | strict Pydantic transaction·receipt·log·internal call·metadata |
| Decode | ERC-20 `Transfer`, Uniswap V2 `Swap`, WETH `Withdrawal` ABI decode |
| Reconciliation | Transfer in↔Swap in, Transfer out↔Swap out↔Withdrawal↔internal ETH |
| Provenance | scoring source와 supporting metadata source·evidence 분리 |
| Result | complete·partial·failed, result→evidence→source 참조 무결성 |
| CLI | `scan analyze --request ... --evidence raw-replay.json` |
| Persistence | reviewed replay artifact·checkpoint·result·JSON·Markdown export |
| Resume | checkpoint의 immutable replay artifact로 offline 재개 |

## 3. Raw evidence와 재확인

대상 TX는 Ethereum mainnet
`0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5`,
block `16642512`다.

2026-07-28 read-only 재조회에서 다음을 다시 확인했다.

- raw transaction input·from·to·block identity
- receipt log `275` USDC Transfer in
- receipt log `276` WETH Transfer out
- receipt log `278` Uniswap V2 Swap
- receipt log `279` WETH Withdrawal
- Blockscout compatibility API internal call `17` Router→사용자 native ETH
- pinned Universal Router·Factory·Pair·token 주소

재조회 결과는
[`raw-replay.json`](./fixtures/FX-SVC-DEX-001/raw-replay.json)에 source
ID·provider ID·조회 시각·raw hex와 함께 보존했다. 분석 실행은 이 reviewed
artifact만 읽으며 네트워크를 호출하지 않는다.

## 4. 상태·오류 검증

| 조건 | 상태 | 오류 | 종료 코드 |
|:---|:---:|:---|:---:|
| 모든 raw 증거 정합 | complete | 없음 | `0` |
| internal native call 누락 | partial | `trace_unavailable` | `3` |
| Swap raw 수량 불일치 | failed | `reconciliation_failed` | `4` |
| offline·source policy 위반 | failed | `rule_restricted` | `5` |
| raw replay Schema 위반 | failed | `decode_failed` | `4` |

partial은 USDC input과 WETH pool output을 보존한다. 정합 실패도 확보한 raw
evidence·source를 버리지 않는다. malformed replay는 외부 동작 전에 차단하고
입력 원문·전체 로컬 경로를 오류에 반사하지 않는다.

## 5. 자동 검증

실행 명령:

```bash
.venv/bin/python scripts/verify.py
UV_CACHE_DIR=/private/tmp/scan-uv-cache uv pip check
UV_CACHE_DIR=/private/tmp/scan-uv-cache uv run --with pip-audit pip-audit
```

결과:

```text
All checks passed!
80 files already formatted
88 passed
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
All installed packages are compatible
No known vulnerabilities found
```

`pip-audit`는 로컬 프로젝트 자체가 PyPI 배포물이 아니어서 그 항목만 제외했고,
설치된 제3자 dependency에서는 알려진 취약점을 발견하지 않았다.

## 6. 핵심 회귀 테스트

- confirmed replay 세 result와 raw log·source·evidence exact match
- internal call 누락 시 partial과 확보 결과 보존
- Swap raw data 한 값 변경 시 구조화 failed
- WETH pool transfer를 native user output으로 오인하지 않음
- 허용하지 않은 source·live mode의 사전 차단
- malformed extra field·canary secret의 persistence·출력 금지
- CLI terminal·JSON·Markdown의 세 raw 값 일치
- 분석 중단 후 checkpoint resume complete·`resumed: true`
- invalid replay가 artifact·checkpoint로 저장되지 않음

## 7. Code Review

| 영역 | 판정 | 근거 |
|:---|:---:|:---|
| 정확성 | Pass | 네 raw 이벤트와 internal call의 양방향 수량 정합 |
| 입력 안전성 | Pass | strict replay model, tx·receipt·request identity 검증 |
| 정수 안전성 | Pass | 모든 uint256을 Python int로 decode, float 미사용 |
| 책임 분리 | Pass | domain model·slice·CLI runtime·storage 분리 |
| YAGNI | Pass | 단일 홉 fixture만, N-hop·가격·범용 DEX 미구현 |
| 오류 보존 | Pass | partial·failed에서 evidence와 source 유지 |
| Schema | Pass | 공개 Analysis I/O `0.1` 변경 없음 |
| 가독성 | Pass | event별 helper·reconciliation·result 조립 분리 |

## 8. Security Review

| 점검 | 판정 | 근거 |
|:---|:---:|:---|
| Secret·경로 노출 | Pass | canary·절대 경로 terminal 0건 |
| 입력 검증 순서 | Pass | raw replay 검증 후에만 artifact·checkpoint 저장 |
| 외부 동작 | Pass | offline artifact read-only, live endpoint 없음 |
| SQL·파일 안전 | Pass | 기존 parameter binding·content-addressed artifact 사용 |
| 민감 기능 | Pass | private key·서명·CTFd credential·자동 제출 없음 |
| Dependency | Pass | `uv pip check`, `pip-audit` 알려진 취약점 0건 |

## 9. Dependency·License

| Dependency | Lock | 용도 | License |
|:---|:---:|:---|:---:|
| `eth-abi` | `5.2.0` | strict ABI tuple·uint256 decode | MIT |
| `eth-utils` | `5.3.1` | EVM 주소 정규화 | MIT |

전이 dependency는 `uv.lock`으로 고정했다. 설치 metadata에서 eth-typing,
eth-hash, parsimonious는 MIT 표기를 확인했다. 프로젝트 코드는 MIT이지만 raw
온체인 데이터·공식 문서·제3자 API 응답의 원 권리와 이용 조건은 별도로
유지한다.

## 10. 365 글로벌 평가 기준

| 기준 | 상태 | 증거 |
|:---|:---:|:---|
| Functionality | Pass | raw decode·정합·CLI·resume와 88 tests |
| Potential Impact | Pass | 다른 EVM 사건에도 재사용 가능한 증거·오류·저장 경계 |
| Novelty | Pass | pool output과 user net output을 증거 수준에서 분리 |
| UX | Pass | exact raw 값, partial·missing·next action·resume 표시 |
| Open-source | Pass | MIT 코드·lockfile·fixture·재현 명령 공개 가능 |
| Business Plan | N/A | 대회 준비용 vertical slice로 별도 사업 계획 범위 아님 |

## 11. Originality & Ethics Check

- web3.py나 상용 포렌식 제품의 분석 코드를 복제하지 않고 공개 ABI 규격과 raw
  evidence로 작은 decoder를 직접 구현했다.
- fixture expected JSON을 결과로 복사하지 않고 raw log를 매번 디코딩한다.
- 스왑을 범죄·피싱·탈취로 해석하거나 주소 귀속을 추가하지 않는다.
- 규정 미확정 live 자동화·AI·CTFd 제출 기능을 활성화하지 않는다.

## 12. Known Issues와 다음 작업

- 단일 confirmed Uniswap V2 USDC→WETH→native ETH 경로만 지원한다.
- router command 전체 해석, N-hop, 가격 환산, 일반 DEX discovery는 범위 밖이다.
- live provider는 Rules·source plan 승인 전 비활성이다.
- AUTH·FREEZE analyzer는 각각 TASK-007·008 범위다.
- 다음 구현은 별도 승인 후 TASK-007 AUTH vertical slice다.

## 13. Related Documents

- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - DEX complete·partial·resume 동선
- **UI_Screens**: [CLI Terminal UI Design](../02_UI_Screens/01_UI_DESIGN.md) - 세 raw 결과 화면 계약
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - decoder·보안·dependency 원칙
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - raw source·provenance 경계
- **Technical_Specs**: [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md) - 결과·증거·오류 공개 계약
- **Logic_Progress**: [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-006 완료 조건과 TASK-007 경계
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed DEX 기준
- **QA_Validation**: [DEX fixture](./fixtures/FX-SVC-DEX-001/README.md) - 사례·승격·정답
- **QA_Validation**: [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md) - DEX·CLI·보안 판정
- **QA_Validation**: [TASK-005 CLI 보고서](./09_TASK_005_CLI_REPORT.md) - composition root·renderer 기준선
