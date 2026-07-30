# TASK-016 CEX Cluster 최종 승격·Benchmark Receipt

> Created: 2026-07-31 05:40
> Last Updated: 2026-07-31 06:20
> Status: Passed · Fixture Confirmed · Benchmark 14/14 · MIXED-XCHAIN Unsupported

## 1. 목적과 판정

사용자 batch approval(2026-07-31)로 CEX Feature Freeze를 thaw한 뒤
`FX-SVC-CEX-001`의 confirmed 승격과 `SVC-CEX-001` Benchmark automated
등록을 판정한다.

**판정: PRIMARY(`https://ethereum-rpc.publicnode.com`) 9건과 VERIFY
(`https://eth.merkle.io`) 9건의 immutable decoded facts가 transfers 0–2에서
코드로 일치하고, negative oracle 8개·독립 Verifier·제품 analyzer·canonical
hash `20fc2777b75968e905af493f97bb56a5b24ccefad755f3a12ebc62662be283bf`가
모두 통과했으므로 fixture를 `확정(confirmed)`으로 승격하고 Benchmark
automated로 등록한다. 이전 incomplete 1RPC VERIFY 주장은 폐기했다.
`MIXED-XCHAIN-001`은 COMPOSITION 미구현으로 unsupported를 유지한다.**

## 2. Fixture 상태 전이

| Fixture | 이전 | 현재 | 확정 범위 |
|:---|:---:|:---:|:---|
| `FX-SVC-CEX-001` | verifying 0.1 | **confirmed 0.1** | OFAC-listed D 3주소 → 공통 H native ETH 집금, blocks 18215917–18215925; PRIMARY+VERIFY complete |

경계:

- 라벨은 evidence-backed assertion(US Treasury SDN public domain)
- 핫월렛 H는 pattern candidate이며 SDN 미등재 → ownership `not_assessed`
- criminality `not_assessed`
- 단일 공통 상대만으로 confirmed 금지(negative oracle)
- `cluster_judgment=confirmed`는 PRIMARY/VERIFY 두 독립 endpoint의 전 transfer
  immutable fact equality 이후에만 허용

## 3. Benchmark 판정

| 문제 | 이전 | 현재 |
|:---|:---:|:---:|
| `SVC-CEX-001` | unsupported | **automated** |
| `MIXED-XCHAIN-001` | unsupported | **unsupported** (COMPOSITION) |

| 항목 | 결과 |
|:---|---:|
| Automated | 14 |
| Assisted | 4 |
| Unsupported | 12 |
| 실행·통과 | 14 / 14 |
| 30문항 직접 자동화율 | 46.7% |

## 4. Commands and Results

| Command | Result |
|:---|:---|
| CEX independent verifier / analyzer hash / negative oracles | PASS |
| focused CEX unit+CLI pytest | PASS |
| Benchmark integration/CLI | PASS — 14/14 |
| `scripts/verify.py` | PASS — 584 tests, 2016 links, security 259, schema 62 probes |

## 5. Residual / Non-goals

- Mixer·Lending adapter
- `MIXED-XCHAIN-001` composition Gate
- live Rules / Evidence Worker CEX stage
- TASK-017 Bitcoin (별도 worktree)

## 6. Related Documents

- [CEX 계약](../03_Technical_Specs/22_TASK_016_CEX_CLUSTER_CONTRACT_PROPOSAL.md)
- [CEX UI](../02_UI_Screens/12_TASK_016_CEX_UI.md)
- [CEX 후보 보고서](./67_TASK_016_CEX_FIXTURE_CANDIDATE_REPORT.md)
- [Contest Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
- [Backlog TASK-016](../04_Logic_Progress/00_BACKLOG.md)
