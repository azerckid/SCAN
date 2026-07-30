# 예상문제 Offline Benchmark 0.1 검증 보고서
> Created: 2026-07-29 01:16
> Last Updated: 2026-07-30 20:20
> Status: Passed · 12 Automated / 4 Assisted / 14 Unsupported

## 1. 목적과 판정 경계

이 보고서는 예상문제 은행 Draft 2의 30문항을 현재 프로그램에 대입해
직접 답을 생성할 수 있는 범위와 기능 공백을 측정한다.

`277 passed` 같은 저장소 회귀 수치는 코드 계약의 안정성을 뜻하지만 30문항
정답 능력을 뜻하지 않는다. 이 benchmark는 다음 세 수준을 구분한다.

| 수준 | 판정 기준 |
|:---|:---|
| `automated` | 공개 Analysis type, confirmed fixture, reference answer, strict analyzer가 모두 있고 답·증거를 자동 채점 |
| `assisted` | 현재 deterministic primitive를 재사용할 수 있지만 전용 request·analyzer·reference fixture가 없어 사람이 정합 |
| `unsupported` | 문제의 핵심 기능 자체가 없어 현재 프로그램으로 답을 도출할 수 없음 |

따라서 `12/12 pass`는 automated 열두 문제의 정확도이며 30문항 전체 정확도가
아니다. Assisted와 Unsupported 문제를 성공으로 계산하지 않는다.

## 2. 실행 방법과 채점

```bash
uv run scan benchmark \
  --manifest docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json
```

각 automated 사례는 reviewed raw replay를 두 번 실행하고 다음 조건을 모두
만족해야 통과한다.

1. Analysis status가 `complete`
2. result type별 answer value가 benchmark oracle과 exact match
3. 모든 result evidence ref가 실제 evidence에 존재
4. confirmed fixture의 mandatory requirement ID가 모두 result에 연결
5. 두 실행의 Analysis I/O가 결정적으로 동일
6. 실행 중 network call 0건

CLI의 `network_mode offline`은 실행 경로의 정책 표시다. 실제 0건 증거는
integration test가 `socket.socket`을 실패하도록 바꾼 상태에서 동일 CLI를
완주하는 방식으로 검증하며 runtime 계측 counter로 오해하지 않는다.

`elapsed_ms`는 로컬 단일 실행 관찰값이며 SLA나 실대회 처리량 주장이 아니다.

## 3. 실행 결과

```text
EXPECTED PROBLEMS 30 · AUTOMATED 12 · ASSISTED 4 · UNSUPPORTED 14
PASS BASIC-EVM-001 · FX-BASIC-EVM-001
PASS BASIC-EVM-002 · FX-BASIC-EVM-002
PASS EVM-AUTH-001 · FX-EVM-AUTH-001
PASS EVM-FREEZE-001 · FX-EVM-FREEZE-001
PASS EVM-NFT-001 · FX-EVM-NFT-721-001
PASS EVM-PROXY-001 · FX-EVM-PROXY-001
PASS EVM-TOKEN-001 · FX-EVM-TOKEN-001
PASS EVM-TOKEN-002 · FX-EVM-TOKEN-002
PASS FLOW-EVM-001 · FX-FLOW-PATH-001
PASS FLOW-EVM-002 · FX-FLOW-REMERGE-001
PASS SVC-DEX-001 · FX-SVC-DEX-001
BENCHMARK 12/12 automated cases passed · network_mode offline
```

| 항목 | 결과 |
|:---|---:|
| 전체 예상문제 | 30 |
| 완전자동 | 12 |
| 도구보조 | 4 |
| 미지원 | 14 |
| 자동 실행 | 12 |
| 자동 통과 | 12 |
| 자동 범위 정확도 | 100% |
| 30문항 직접 자동화율 | 36.7% |

## 4. 30문항 Coverage Matrix

아래 `Assisted`는 현재 CLI가 답을 생성한다는 뜻이 아니다. 기존 내부 구현을
후속 전용 analyzer에서 재사용할 수 있지만 지금은 사람이 정합해야 한다는
의미다.

| 문제 ID | 수준 | 현재 재사용 기능 | 핵심 공백 |
|:---|:---:|:---|:---|
| BASIC-EVM-001 | Automated | EVM Core object summary | 없음 |
| BASIC-EVM-002 | Automated | EVM Core historical balance | 없음 |
| EVM-TOKEN-001 | Automated | EVM Core first Transfer | 없음 |
| EVM-TOKEN-002 | Automated | EVM Core native inflow | 없음 |
| EVM-NFT-001 | Automated | ERC-721/1155 subject-scoped decoder | 없음 |
| EVM-AUTH-001 | Automated | AUTH strict vertical | 없음 |
| EVM-PROXY-001 | Automated | EIP-1967 event·historical state 정합 | 없음 |
| EVM-FREEZE-001 | Automated | FREEZE strict vertical | 없음 |
| FLOW-EVM-001 | Automated | bounded PATH·증거 경로 | 서비스 귀속은 `not_assessed`, 주소 정답 채점 |
| FLOW-EVM-002 | Automated | PATH·GRAPH-RECON·exclusion | 없음 |
| FLOW-MULTI-001 | Assisted | origin contribution·dedup total | PRICE·피해자 귀속 |
| SVC-DEX-001 | Automated | DEX strict vertical | 없음 |
| SVC-BRG-001 | Unsupported | provenance·export | XCHAIN·BRIDGE |
| SVC-CEX-001 | Unsupported | provenance | CEX-CLUSTER·LABEL·HEUR |
| SVC-MIX-001 | Unsupported | provenance·export | MIXER·PATH·HEUR |
| SVC-LEND-001 | Unsupported | EVM-LOG·RECON | DEFI-LEND·EVM-TRACE |
| ACTOR-REL-001 | Unsupported | provenance | ACTOR-REL·HEUR |
| ACTOR-REL-002 | Assisted | public-hub relation·false-positive exclusion | positive multi-heuristic candidate·CLUSTER |
| CRIME-PHISH-001 | Unsupported | AUTH·provenance | PATH·LABEL·OSINT |
| CRIME-POISON-001 | Unsupported | provenance | POISON·HEUR |
| CRIME-EXP-001 | Unsupported | EVM-LOG·provenance | EVM-TRACE·EXPLOIT-DECODE·PATH |
| CRIME-RUG-001 | Unsupported | EVM-LOG·provenance | LP-RUG·PATH·LABEL |
| BTC-UTXO-001 | Unsupported | 공통 기반 | BTC-UTXO |
| BTC-UTXO-002 | Unsupported | provenance | BTC-UTXO·HEUR |
| BTC-CJ-001 | Unsupported | provenance·export | BTC-UTXO·COINJOIN·HEUR |
| OSINT-LBL-001 | Automated | intel_context collect_label_claims·confirmed LABEL fixture | 없음 |
| OSINT-SAN-001 | Assisted | official historical timeline·direct match | 1-hop indirect expansion·LABEL |
| OSINT-ENS-001 | Assisted | fixed-block ENS forward/reverse | domain·DNS·SNS·impersonation |
| MIXED-XCHAIN-001 | Unsupported | DECODE·RECON·provenance | XCHAIN·BRIDGE·PATH·LABEL |
| MIXED-CASE-001 | Unsupported | 공통 기반 | SEED-DISCOVERY·PATH·OSINT·VIZ |

## 5. 해석과 다음 구현 우선순위

현재 프로그램은 기존 세 vertical, EVM Core 네 query, NFT·Proxy와 bounded
PATH 두 문제의 결정적 증명에는 강하지만 범용 블록체인 포렌식 문제 해결기는
아니다. 30문항
coverage를 가장 크게 늘리는 순서는
아래와 같다.

1. `PRICE`·`LABEL`·`OSINT`를 확정 사실과 heuristic으로 분리해
   `FLOW-MULTI-001`과 후속 FLOW·CRIME 문제의 남은 공백을 해소한다.
2. PATH를 CRIME·MIXED에 연결하되 문제별 confirmed fixture로 범위를 제한한다.
3. `XCHAIN/BRIDGE`, `BTC-UTXO`, 전문 decoder는 실제 fixture가 확보된 순서로
   별도 vertical을 추가한다.

새 기능은 문항 수만 보고 구현하지 않는다. 공개 사례와 reference answer를
먼저 확보한 뒤 automated로 승격하고 같은 benchmark에서 회귀시킨다.

## 6. 365 글로벌 평가 기준

| 기준 | 판정 | 증거·경계 |
|:---|:---:|:---|
| Functionality | Partial | automated 12개 exact/evidence/requirement/determinism 통과, 18개 비자동 |
| Potential Impact | Partial | 공백이 큰 PATH·LABEL·OSINT 우선순위를 수치화, 실대회 효과 미측정 |
| Novelty | Pass / Offline | 답 문자열이 아니라 answer→evidence→fixture requirement를 함께 채점 |
| UX | Pass / CLI | 한 명령으로 coverage와 자동 사례 결과를 표시 |
| Open-source | Pass | JSON manifest·Python runner·fixture·재현 명령 공개 |
| Business Plan | N/A | 대회 준비용 검증이며 수익 모델 범위가 아님 |

## 7. Known Issues

- automated 사례는 Ethereum mainnet DEX·AUTH·FREEZE, EVM Core 네 query,
  NFT·Proxy, bounded FLOW path·remerge, 그리고 `OSINT-LBL-001`(intel_context
  collect_label_claims, confirmed LABEL fixture)에 한정된다. 나머지 TASK-015
  confirmed fixture(SANCTIONS·ENS·RELATION-HUB)는 문제 전체가 아니라 조사
  primitive이므로 assisted다.
- fixture oracle은 reviewed 공개 사례에 고정되어 새로운 실전 입력의 일반화
  성능을 측정하지 않는다.
- `FLOW-MULTI-001`은 raw contribution·합계만, OSINT-SAN/ENS와
  ACTOR-REL-002는 bounded intelligence fact만 도구보조다. 전체 정답 필드가
  없어 네 문제를 Assisted로 유지하며 핵심 분석기가 없는 14개는
  Unsupported다.
- Challenge Pack 10개에는 confirmed reference fixture가 없어 이번 0.1에서
  실행하지 않는다.
- 실행 시간은 단일 로컬 관찰값이며 성능 benchmark로 사용하지 않는다.

## 8. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - Draft 2 30문항과 완료·부분·실패 기준
- **Concept_Design**: [기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - 기능 빈도와 구현 단계
- **Technical_Specs**: [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md) - fixture-first·최소 구현·offline 검증 원칙
- **Technical_Specs**: [Coverage 확장 Brief](../03_Technical_Specs/09_EXPECTED_PROBLEM_EXPANSION_BRIEF.md) - 27개 비자동 문항의 엔진 묶음
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-011 구현·검증 기록
- **Logic_Progress**: [Coverage 확장 Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - TASK-012~019 실행 Wave
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed fixture 10개 기준선
- **QA_Validation**: [TASK-013 최종 승격 Receipt](./38_TASK_013_FINAL_PROMOTION_RECEIPT.md) - NFT·Proxy confirmed·9/9 근거
- **QA_Validation**: [TASK-014 최종 승격 Receipt](./44_TASK_014_FINAL_PROMOTION_RECEIPT.md) - FLOW confirmed·11/11 근거
- **QA_Validation**: [TASK-015 비격리 Fixture 승격 Receipt](./56_TASK_015_NON_QUARANTINED_PROMOTION_RECEIPT.md) - 세 confirmed fixture를 assisted로만 반영한 근거
- **QA_Validation**: [TASK-009 통합 보고서](./13_TASK_009_INTEGRATION_REPORT.md) - 기존 vertical 회귀와 보안 Gate
- **QA_Validation**: [OPS-IMPL-08 보고서](./21_OPS_IMPL_08_FINAL_INTEGRATION_REPORT.md) - 병렬 운영과 수동 제출 기준선
- **QA_Validation**: [Coverage 확장 QA](./23_EXPECTED_PROBLEM_EXPANSION_QA.md) - 새 분석기 승격·반례·통합 Gate
