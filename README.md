# SCAN

Evidence-first blockchain forensic tools and competition preparation documents for
SCAN 2026.

## Current status

The repository is documentation-complete for the approved baseline. `TASK-001`
initialized the Python project and offline quality gate, and `TASK-002` implemented
the Analysis I/O 0.1 Pydantic models and semantic Schema check. `TASK-003`
implemented the rules-gated HTTP source port, retry, and fallback orchestration.
Storage and DEX/AUTH/FREEZE analyzers are not implemented yet.
Official rules for AI, automation, prebuilt tools, external APIs, and challenge
submission remain `unclear`; related features stay disabled until an authoritative
notice is recorded.

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
| Roadmap | [`00_ROADMAP.md`](docs/04_Logic_Progress/00_ROADMAP.md) | document and implementation gates |
| Backlog | [`00_BACKLOG.md`](docs/04_Logic_Progress/00_BACKLOG.md) | atomic implementation tasks |
| QA | [`02_QA_CHECKLIST.md`](docs/05_QA_Validation/02_QA_CHECKLIST.md) | pre-code, PR, regression, competition gates |
| TASK-001 evidence | [`05_TASK_001_BOOTSTRAP_REPORT.md`](docs/05_QA_Validation/05_TASK_001_BOOTSTRAP_REPORT.md) | Python, lock, dependency, and quality-gate evidence |
| TASK-002 evidence | [`06_TASK_002_CONTRACT_REPORT.md`](docs/05_QA_Validation/06_TASK_002_CONTRACT_REPORT.md) | Analysis I/O models, invariants, dependencies, and Contract Gate evidence |
| TASK-003 evidence | [`07_TASK_003_SOURCE_REPORT.md`](docs/05_QA_Validation/07_TASK_003_SOURCE_REPORT.md) | source policy, retry, fallback, dependency, and TASK-003 scope evidence |
| Completion | [`04_DOCUMENT_COMPLETION_REPORT.md`](docs/05_QA_Validation/04_DOCUMENT_COMPLETION_REPORT.md) | document validation evidence and remaining boundaries |

## Validation

Install the exact locked environment and run the complete offline quality gate:

```bash
uv sync --locked
uv run python scripts/verify.py
```

The gate runs Ruff lint and format checks, pytest, and both existing Schema
validators, followed by the generated-Pydantic-Schema compatibility check.
Expected final outputs include:

```text
47 passed
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
PASS 3 generated schemas are semantically compatible with Analysis I/O 0.1 across 35 probes
```

The installed package currently exposes only the approved bootstrap surface:

```bash
uv run scan --help
uv run scan --version
```

## Rules and safe defaults

- An absent prohibition is not treated as permission.
- `unclear` AI, agent, API, automation, and prebuilt-tool capabilities remain off.
- No private key, seed phrase, CTFd credential, or session is stored.
- No automatic answer submission or brute-force path is planned.
- Python CLI and human verification remain the fallback.

## Implementation boundary

`TASK-001` through `TASK-003` are complete. The next eligible task is `TASK-004`
(SQLite cache, checkpoint, artifact, and export) and still requires separate
implementation approval. No live provider configuration exists; live transport
also requires `rule_status: allowed`. AI/agent execution and CTFd automation remain
unimplemented.

## License

Project-authored code and documentation are available under the
[MIT License](LICENSE). Third-party data, official documents, linked repositories,
and fixture source material retain their original licenses, terms, and attribution.
