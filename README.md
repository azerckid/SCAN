# SCAN

Evidence-first blockchain forensic tools and competition preparation documents for
SCAN 2026.

## Current status

The repository is documentation-complete for the approved baseline. `TASK-001`
initialized the Python project and offline quality gate, and `TASK-002` implemented
the Analysis I/O 0.1 Pydantic models and semantic Schema check. `TASK-003`
implemented the rules-gated HTTP source port, retry, and fallback orchestration.
`TASK-004` implemented SQLite WAL storage, immutable cache, checkpoints,
content-addressed artifacts, backup verification, and JSON/Markdown exports.
`TASK-005` implemented the four analysis commands, terminal renderer, stable exit codes,
local `.scan/` composition root, and persisted-result display. The
`TASK-006` DEX slice now decodes raw Transfer·Swap·Withdrawal logs, reconciles
USDC/WETH/native ETH outputs, preserves supporting metadata, and supports reviewed
offline replay with checkpoint resume. `TASK-007` AUTH now reconciles Approval,
approve calldata, four historical allowance states, transferFrom trace, Transfer
event, and three reverted intermediate transactions while keeping theft or phishing
attribution `not_assessed`. `TASK-008` FREEZE reconciles blacklist and unblacklist
calls, events, four historical states, and official Circle/OFAC context while
keeping current sanctions and criminal intent `not_assessed`. `TASK-009` closes the
offline P0·V1 integration gate with deterministic replay, the 11-code error matrix,
repository traceability, and security scans; all 24 P0·V1 QA scenarios pass.
The mandatory AI Planner contract and Operations Board UI-First Gate are approved.
`OPS-IMPL-01` now implements the `TASK-010` public operations contract, generated
JSON Schema, cross-record invariants, and state-transition validator.
`OPS-IMPL-02` adds explicit SQLite v2 persistence, `OPS-IMPL-03` adds the
rules-gated AI Planner, and `OPS-IMPL-04` adds the bounded in-process scheduler,
job DAG, failure isolation, retry, idempotency dedup, and source-capability request
pool. `OPS-IMPL-05` connects approved AI plan inputs to isolated offline
DEX·AUTH·FREEZE Python evidence workers, Analysis I/O results, checkpoints, and
content-addressed artifacts. `OPS-IMPL-06` builds canonical evidence-linked
candidates, independently replays raw evidence, preserves conflicts, and allows
only the Application Gate to mark a candidate submission-ready. `OPS-IMPL-07`
adds SQLite v2 read-back, a strict OperationsSnapshot, shared JSON/terminal
rendering, and the read-only local `operations` command. Live AI and
submission-record mutation remain unimplemented.
Official rules for AI, automation, prebuilt tools, external APIs, and challenge
submission remain `unclear`, so external execution modes remain `rules_gated` until
an authoritative notice is recorded.

## What is planned

The V1 baseline is a Python core with a CLI and three verified vertical slices:

- DEX swap reconstruction with pool output and user net output separated
- token approval and delegated transfer consumption analysis
- token blacklist state transition analysis with on-chain and external context
  separated

All results follow a shared Analysis I/O contract and link each conclusion to raw
event, call, state, or official context evidence. CTFd submission remains manual.

## Documentation map

| Layer | Start here | Purpose |
|:---|:---|:---|
| Concept | [`01_SCAN_2026_PREPARATION_STRATEGY.md`](docs/01_Concept_Design/01_SCAN_2026_PREPARATION_STRATEGY.md) | preparation strategy and scope |
| Rules | [`03_SCAN_2026_RULES_REGISTER.md`](docs/01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) | authoritative facts, unknowns, notification response |
| UI | [`00_SCREEN_FLOW.md`](docs/02_UI_Screens/00_SCREEN_FLOW.md) | CLI and review flows |
| Technical | [`03_SCAN_2026_TOOL_REQUIREMENTS.md`](docs/03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) | P0 and V1 requirements |
| Database | [`01_DB_SCHEMA.md`](docs/03_Technical_Specs/01_DB_SCHEMA.md) | SQLite logical schema and mutation boundaries |
| Operations | [`07_AGENTIC_PARALLEL_SOLVE_FLOW.md`](docs/03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) | rules-gated parallel solving |
| TASK-010 brief | [`08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md`](docs/03_Technical_Specs/08_TASK_010_PRE_CODE_TECHNICAL_BRIEF.md) | operations models, SQLite v2, scheduler, AI modes, and implementation gates |
| Roadmap | [`00_ROADMAP.md`](docs/04_Logic_Progress/00_ROADMAP.md) | document and implementation gates |
| Backlog | [`00_BACKLOG.md`](docs/04_Logic_Progress/00_BACKLOG.md) | atomic implementation tasks |
| QA | [`02_QA_CHECKLIST.md`](docs/05_QA_Validation/02_QA_CHECKLIST.md) | pre-code, PR, regression, competition gates |
| TASK-001 evidence | [`05_TASK_001_BOOTSTRAP_REPORT.md`](docs/05_QA_Validation/05_TASK_001_BOOTSTRAP_REPORT.md) | Python, lock, dependency, and quality-gate evidence |
| TASK-002 evidence | [`06_TASK_002_CONTRACT_REPORT.md`](docs/05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md) | Analysis I/O models, invariants, dependencies, and Contract Gate evidence |
| TASK-003 evidence | [`07_TASK_003_SOURCE_REPORT.md`](docs/05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) | source policy, retry, fallback, dependency, and TASK-003 scope evidence |
| TASK-004 evidence | [`08_TASK_004_STORAGE_REPORT.md`](docs/05_QA_Validation/08_TASK_004_STORAGE_REPORT.md) | SQLite, cache, checkpoint, artifact, export, backup, and storage-security evidence |
| TASK-005 evidence | [`09_TASK_005_CLI_REPORT.md`](docs/05_QA_Validation/09_TASK_005_CLI_REPORT.md) | CLI commands, renderer, exit codes, UI comparison, and CLI-security evidence |
| TASK-006 evidence | [`10_TASK_006_DEX_REPORT.md`](docs/05_QA_Validation/10_TASK_006_DEX_REPORT.md) | raw DEX replay, exact reconciliation, partial/failure, resume, and DEX-security evidence |
| TASK-007 evidence | [`11_TASK_007_AUTH_REPORT.md`](docs/05_QA_Validation/11_TASK_007_AUTH_REPORT.md) | raw AUTH replay, allowance lifecycle, delegated consumption, partial/failure, resume, and AUTH-security evidence |
| TASK-008 evidence | [`12_TASK_008_FREEZE_REPORT.md`](docs/05_QA_Validation/12_TASK_008_FREEZE_REPORT.md) | raw FREEZE replay, state transitions, official context boundaries, partial/failure, resume, and security evidence |
| TASK-009 evidence | [`13_TASK_009_INTEGRATION_REPORT.md`](docs/05_QA_Validation/13_TASK_009_INTEGRATION_REPORT.md) | deterministic V1 regression, error matrix, traceability, UI comparison, and security evidence |
| OPS-IMPL-04 evidence | [`17_OPS_IMPL_04_BOUNDED_QUEUE_REPORT.md`](docs/05_QA_Validation/17_OPS_IMPL_04_BOUNDED_QUEUE_REPORT.md) | bounded scheduling, dependency, isolation, retry, dedup, and capability-limit evidence |
| OPS-IMPL-05 evidence | [`18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md`](docs/05_QA_Validation/18_OPS_IMPL_05_EVIDENCE_WORKER_REPORT.md) | approved plan projection, DEX/AUTH/FREEZE replay, workspace isolation, artifact, and checkpoint evidence |
| OPS-IMPL-06 evidence | [`19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md`](docs/05_QA_Validation/19_OPS_IMPL_06_CANDIDATE_VERIFIER_REPORT.md) | canonical candidate, fresh independent replay, conflict preservation, and promotion-gate evidence |
| OPS-IMPL-07 evidence | [`20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md`](docs/05_QA_Validation/20_OPS_IMPL_07_OPERATIONS_SNAPSHOT_REPORT.md) | SQLite read-back, strict snapshot, local terminal/JSON view, and Preview-state mapping evidence |
| Completion | [`04_DOCUMENT_COMPLETION_REPORT.md`](docs/05_QA_Validation/04_DOCUMENT_COMPLETION_REPORT.md) | document validation evidence and remaining boundaries |

## Validation

Install the exact locked environment and run the complete offline quality gate:

```bash
uv sync --locked
uv run python scripts/verify.py
```

The gate runs Ruff lint and format checks, pytest, the existing Schema validators,
the Analysis I/O and Operations generated-Schema compatibility checks, and
repository traceability and security scans.
Expected final outputs include:

```text
260 passed
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
PASS operations contract 0.1 generated Schema and runtime agree across 17 probes
PASS repository traceability: 793 links, 10 TASK IDs, 24 QA IDs, 3 fixture/example mappings
PASS repository security scan: 65 runtime/evidence files
```

The installed package exposes the approved analysis and local operations command surface:

```bash
uv run scan --help
uv run scan --version
uv run scan operations --bundle docs/05_QA_Validation/examples/operations/rules-gated-bundle.json
uv run scan operations --bundle docs/05_QA_Validation/examples/operations/rules-gated-bundle.json --output json
uv run scan validate REQUEST.json
uv run scan analyze --request REQUEST.json --evidence RAW_REPLAY.json
uv run scan resume ANALYSIS_ID
uv run scan show ANALYSIS_ID
```

TASK-006~008 accept only reviewed offline DEX, AUTH, or FREEZE replay evidence.
A supported request without `--evidence` stops explicitly with
`source_unavailable`; no hidden live request is made.

## Rules and safe defaults

- An absent prohibition is not treated as permission.
- `unclear` AI, agent, API, automation, and prebuilt-tool capabilities remain off.
- No private key, seed phrase, CTFd credential, or session is stored.
- No automatic answer submission or brute-force path is planned.
- Python CLI and human verification remain the fallback.

## Implementation boundary

`TASK-001` through `TASK-009` are complete. The offline P0·V1 baseline is closed.
`TASK-010` is a separate rules-gated operations track and requires authoritative
rules, Operations Board review, and separate implementation approval. No live
provider configuration exists; live transport also requires
`rule_status: allowed`. AI/agent execution and CTFd automation remain unimplemented.

## License

Project-authored code and documentation are available under the
[MIT License](LICENSE). Third-party data, official documents, linked repositories,
and fixture source material retain their original licenses, terms, and attribution.
