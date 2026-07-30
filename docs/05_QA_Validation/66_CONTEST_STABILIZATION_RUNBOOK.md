# Contest Stabilization Runbook · Feature Freeze

> Created: 2026-07-31 04:55
> Last Updated: 2026-07-31 04:55
> Status: Active · Bridge Confirmed · Benchmark 13/13 · Feature Freeze until contest start

## 1. 목적

대회(2026-08-02 09:00 KST) 직전 프로그램의 **사용 가능한 안정 범위**와
실행·복구 절차를 고정한다. 신규 adapter(BTC·CEX·Mixer·Lending·TASK-018)
구현은 freeze한다. 대회 중 실제 출제가 확인된 경우에만 최소 범위로
재개한다.

## 2. 확정 Coverage

| 수준 | 수 | 문제 |
|:---|---:|:---|
| Automated | 13 | BASIC×2, TOKEN×2, NFT, AUTH, PROXY, FREEZE, FLOW×2, DEX, LABEL, **BRG** |
| Assisted | 4 | FLOW-MULTI, ENS, SANCTIONS, ACTOR-REL-002 |
| Unsupported | 13 | BTC×3, CEX, MIX, LEND, CRIME×4, MIXED-XCHAIN, MIXED-CASE, ACTOR-REL-001 등 |

Fixture registry: **18 Confirmed · 0 Verifying · 1 Candidate · 1 Deferred**.

## 3. 설치·실행

```bash
uv sync
uv run python scripts/verify.py
uv run scan benchmark --manifest docs/05_QA_Validation/benchmarks/expected-problem-v0.1.json
```

Bridge 단일 사례(파일 경로 필수). CLI는 cwd의 `.scan/`에 analysis_id를
저장하므로, 동일 ID 재실행 전에는 빈 작업 디렉터리에서 실행한다.

```bash
WORKDIR=$(mktemp -d) && cd "$WORKDIR"
uv run --project /path/to/SCAN scan analyze \
  --request /path/to/SCAN/docs/05_QA_Validation/fixtures/FX-SVC-BRG-001/analysis-request.json \
  --evidence /path/to/SCAN/docs/05_QA_Validation/fixtures/FX-SVC-BRG-001/raw-replay.json
```

결과·checkpoint는 CLI 기본 출력과 기존 Operations 경로를 따른다.
`BRIDGE_TRANSFER`는 Evidence Worker stage map에 없다(FLOW/INTEL과 동일).
byte-only replay body만 전달하면 `AnalysisUnavailable`로 거부된다.

## 4. 실전 점검 결과 (2026-07-31)

| 점검 | 결과 |
|:---|:---|
| `scripts/verify.py` | PASS — 570 tests, 1951 links, security 226, schema 57 probes |
| Benchmark CLI | PASS — 13/13 automated · ASSISTED 4 · UNSUPPORTED 13 |
| Bridge hash / oracle / verifier gates | PASS — hash `d6609bb4…00ac` |
| Bridge CLI `--evidence` (fresh cwd) | PASS — `COMPLETE AN-FX-SVC-BRG-001` |
| Bridge byte-only path | PASS — rejects with `requires --evidence` |
| Existing DEX/AUTH/PATH/LABEL regression | covered by full verify.py |

## 5. Feature Freeze 규칙

- Freeze 대상: TASK-017 Bitcoin, TASK-016 CEX/Mixer/Lending, TASK-018/019,
  MIXED-XCHAIN 조합, live Rules adapter
- 허용: 문서 정합, 치명적 회귀 버그 수정, 대회 중 실제 출제 대응의
  최소 hotfix(별도 승인)
- 금지: Benchmark unsupported를 숨기거나 fixture를 가짜 confirmed로 올리기

## 6. 실패 시 복구

| 증상 | 조치 |
|:---|:---|
| Benchmark 1건 실패 | 해당 fixture hash gate·oracle부터 재실행. 네트워크 호출 금지 |
| Bridge AnalysisUnavailable | `--evidence`가 package 내 `raw-replay.json` 경로인지 확인 |
| Schema probe 실패 | `REQ-*` pattern·공개 Schema 동기화 확인 |
| 전체 verify 실패 | 신규 코드 롤백 후 freeze 범위로 복귀 |

## 7. Related Documents

- [Bridge Final Promotion Receipt](./65_TASK_016_BRIDGE_FINAL_PROMOTION_RECEIPT.md)
- [Benchmark Report](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md)
- [Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md)
