# TASK-016 Lending 최종 승격·Benchmark Receipt

> Created: 2026-07-31 07:31
> Last Updated: 2026-07-31 07:35
> Status: Passed · Fixture Confirmed · Benchmark 15/15 · MIXED-XCHAIN Unsupported

## 1. 목적과 판정

사용자 batch approval(2026-07-31)로 Lending Feature Freeze를 thaw한 뒤
`FX-SVC-LEND-001`의 confirmed 승격과 `SVC-LEND-001` Benchmark automated
등록을 판정한다.

**판정: PRIMARY(`https://ethereum.publicnode.com`)와 VERIFY
(`https://ethereum.rpc.thirdweb.com`)의 immutable decoded LiquidationCall·
Transfer facts가 코드로 일치하고, negative oracle 8개·독립 Verifier·제품
analyzer·canonical hash `6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c`가 모두 통과했으므로 fixture를
`확정(confirmed)`으로 승격하고 Benchmark automated로 등록한다.
`MIXED-XCHAIN-001`은 COMPOSITION 미구현으로 unsupported를 유지한다.**

최종 결함 보완에서는 canonical ABI shape, tx/receipt/block 및 selected log
exact binding, `removed=false`, collateral receipt 이후 `logIndex` 순서,
승인 provider provenance를 제품 analyzer와 독립 Verifier 양쪽에서 재검증했다.

## 2. Fixture 상태 전이

| Fixture | 이전 | 현재 | 확정 범위 |
|:---|:---:|:---:|:---|
| `FX-SVC-LEND-001` | candidate | **confirmed 0.1** | Aave V3 LiquidationCall `0x207745c3f3cbcdc4f31a5a9d89810278e2e6cef385cb1bbf0b2c4b4ccdac4a37` · liquidator subject · event-only Transfer-matched ledger · PRIMARY+VERIFY complete |

## 3. Benchmark 판정

| 문제 | 이전 | 현재 |
|:---|:---:|:---:|
| `SVC-LEND-001` | unsupported | **automated** |
| `MIXED-XCHAIN-001` | unsupported | **unsupported** |

| 항목 | 결과 |
|:---|---:|
| Automated | 15 |
| Assisted | 4 |
| Unsupported | 11 |

## 4. Commands and Results

| Command | Result |
|:---|:---|
| Lending independent verifier / analyzer hash / negative oracles | PASS — hash `6c51b2ebfaef49ca…` |
| focused Lending unit+CLI pytest | PASS — 21 tests |
| focused Bridge+CEX regression pytest | PASS — 31 tests |
| Benchmark integration/CLI | PASS — 15/15 |
| `scripts/check_task_012_analysis_contract_proposal.py` | PASS — 12 cases, 14 probes |
| `scripts/verify.py` | PASS — 605 tests, fixture 21, schema 67 probes, traceability 2037 links, security 277 files |

## 5. Provenance hashes and trust boundary

- Capture metadata SHA-256:
  `b48eade06fb835337bf2d2ed3605aa369baea4460b8065006e6ebdec9bbf4182`
- PUBLICNODE PRIMARY: transaction
  `6b7ec7aeaa67e61d1e22c03c52751298346423b77e1a60f1b6adbcce674cbc1b`,
  receipt `5b8c66e6043fd185227340291552525a5db8de85c132a928816170ecf5591598`,
  block `0f17bad5c5886e0e5a3a036e69406d20a5f1028291f8269e881564f9288b3ebf`
- THIRDWEB VERIFY: transaction
  `9fd62d8c66094d7261eccfc7a52c8f38a518e1866d6c6d077315bf45377bfe38`,
  receipt `493b01d0f2daa938cea66bfd8751bace55b84a52266321e42995a11d47badc23`,
  block `9dfb1298a0c3354036dedfbec4645b847ac621f062ba5d81473c12b9a7f60fc3`
- Canonical fact SHA-256:
  `6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c`
- 2026-07-31 KST live read-only 재검증에서 immutable fields가 일치했다.
  서로 다른 공개 endpoint도 동일 upstream·운영자 공모·동시 오응답 가능성을
  암호학적으로 배제하지는 못하며 이 경계는 잔여 신뢰 위험이다.

## 6. Residual / Non-goals

- Mixer adapter
- `MIXED-XCHAIN-001` composition Gate
- live Rules / Evidence Worker lending stage
- TASK-017 Bitcoin (별도 worktree `/private/tmp/scan-task-017` 미접촉)

## 7. Related Documents

- [69 Lending Fixture Candidate Report](./69_TASK_016_LENDING_FIXTURE_CANDIDATE_REPORT.md)
- [Lending 계약](../03_Technical_Specs/19_TASK_016_LENDING_CONTRACT_PROPOSAL.md)
- [Contest Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
