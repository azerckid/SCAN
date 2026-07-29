# TASK-013 NFT·Proxy 최종 승격 Receipt
> Created: 2026-07-29 22:13
> Last Updated: 2026-07-29 22:13
> Status: Passed · Fixture 3 Confirmed · Benchmark 9/9 · TASK-013 Done

## 1. 목적과 판정

PR #66 merge commit `45afa7b`에 포함된 TASK-013 analyzer remediation을
독립 재검토한 뒤, ERC-721·ERC-1155·EIP-1967 fixture를 `verifying`에서
`confirmed`로 승격하고 예상문제 Benchmark의 실제 자동화 범위를 갱신한다.

**판정: 세 fixture는 raw replay·두 공급자 provenance·negative oracle·독립
Verifier·제품 analyzer·변형 회귀 테스트를 모두 통과했다. EVM-NFT-001과
EVM-PROXY-001은 confirmed fixture와 strict analyzer를 가지므로 automated로
승격하며, Benchmark는 9/9다.**

## 2. 승격 입력

| 입력 | 확인 |
|:---|:---|
| 공개 replay | receipt·filtered log·historical storage·capability별 SHA-256 |
| 공급자 | `PROVIDER-EVM-PRIMARY`, `PROVIDER-EVM-VERIFY` decoded match |
| 반례 | TASK-013 negative oracle 16개 × 2회 |
| 독립 검증 | 3 fixture · 7 requirements · 13 evidence values × 2회 |
| 제품 검증 | 3 fixture · 4 subject-scoped requests · canonical hash 일치 × 2회 |
| remediation | subject/proxy/token 결합, receipt/block 정합, Schema family binding, 범용 결과 형태, Beacon 미지원 경계, 복수 provider provenance |
| 재검토 | PR #66 `Approve with P2`, 병합 차단 문제 없음 |
| 병합 기준선 | `main` merge commit `45afa7b` |

## 3. Fixture 상태 전이

| Fixture | 이전 | 현재 | 확정 범위 |
|:---|:---:|:---:|:---|
| `FX-EVM-NFT-721-001` | verifying 0.1 | **confirmed 0.1** | 선정 두 TX·각 exact block window의 subject-bound ERC-721 이동·승인 |
| `FX-EVM-NFT-1155-001` | verifying 0.1 | **confirmed 0.1** | 서로 다른 subject의 Single/Approval·Batch를 두 요청으로 분리한 선정 TX 범위 |
| `FX-EVM-PROXY-001` | verifying 0.1 | **confirmed 0.1** | 선정 upgrade TX와 직전/해당 block의 EIP-1967 implementation/admin state |

`confirmed`는 위의 bounded scope만 확정한다. NFT block 사이의 연속 전체
구간, Proxy의 전체 upgrade history, NFT 가치·소유권 분쟁·거래 의도,
Proxy upgrade의 악성 여부는 판정하지 않는다.

## 4. Benchmark 승격

| 문제 | 이전 | 현재 | 실행 fixture |
|:---|:---:|:---:|:---|
| `EVM-NFT-001` | assisted | **automated** | `FX-EVM-NFT-721-001` |
| `EVM-PROXY-001` | assisted | **automated** | `FX-EVM-PROXY-001` |

EVM-NFT-001은 예상문제 한 문항이므로 Benchmark executable case도 하나다.
ERC-721 confirmed fixture를 대표 exact oracle로 실행하고, ERC-1155 confirmed
fixture는 동일 analyzer의 별도 회귀 Gate로 유지한다. 따라서 fixture 수를
문제 수로 중복 계산하지 않는다.

갱신된 집계:

| 항목 | 결과 |
|:---|---:|
| 전체 예상문제 | 30 |
| Automated | 9 |
| Assisted | 0 |
| Unsupported | 21 |
| 실행·통과 | 9 / 9 |
| Automated 범위 정확도 | 100% |
| 30문항 직접 자동화율 | 30.0% |

## 5. 재현 명령과 결과

```bash
uv run scan benchmark \
  --manifest docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json
uv run python scripts/check_task_013_replay_gate.py
uv run python scripts/verify_task_013_independent_verifier.py
uv run python scripts/verify_task_013_analyzer_independent_verification.py
uv run python scripts/verify.py
```

확인된 핵심 출력:

- `EXPECTED PROBLEMS 30 · AUTOMATED 9 · ASSISTED 0 · UNSUPPORTED 21`
- `BENCHMARK 9/9 automated cases passed · network_mode offline`
- `PASS TASK-013 replay Gate: 3 fixtures (confirmed)`
- `PASS TASK-013 independent Verifier: 3 fixtures (confirmed)`
- `PASS TASK-013 analyzer independent verification: 3 fixtures, 4 subject-scoped requests`

## 6. 변경 경계

- Analysis I/O Schema `0.2`와 `0.1` 호환 계약은 변경하지 않는다.
- 새 analysis type·query kind·dependency·network call을 추가하지 않는다.
- Benchmark runner에는 이미 승인된 `EvmSpecialAnalysisRequest` 디스패치만
  연결한다.
- live RPC·AI provider·CTFd 제출은 실행하지 않는다.
- TASK-014 PATH 구현은 이 Receipt의 범위가 아니며 별도 fixture·Context
  Receipt·사용자 승인을 요구한다.

## 7. 365 글로벌 평가 기준

| 기준 | 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Pass / Bounded | 9개 automated exact·evidence·requirement·determinism |
| Potential Impact | Partial | NFT·Proxy 자동화 추가, PATH·BTC·cross-chain은 미지원 |
| Novelty | Pass | subject-scoped raw proof와 independent Verifier 결과를 함께 승격 조건으로 사용 |
| UX | Pass / CLI | 기존 `benchmark` 한 명령으로 30문항 coverage와 9개 결과 표시 |
| Open-source | Pass | 공개 replay·manifest·검증 명령·증거 연결 공개 |
| Business Plan | N/A | 대회 문제 해결 준비용 검증 |

## 8. 다음 작업

TASK-013을 `Done`으로 닫는다. 다음 구현 트랙은 TASK-014 PATH Graph·금액
정합 엔진이며, 단일 경로와 분기·재병합 fixture·Analysis I/O·UI 영향을
먼저 docs-only로 승인한다.

## 9. Related Documents

- **Technical_Specs**: [TASK-013 분석 계약](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - evm_special 경계
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-013 Done과 TASK-014 잠금
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 3 상태
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - confirmed registry
- **QA_Validation**: [Offline Benchmark](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md) - 9/9 coverage
- **QA_Validation**: [Analyzer P1 정정 Receipt](./37_TASK_013_ANALYZER_REMEDIATION_RECEIPT.md) - 재검토 전 수정 근거
