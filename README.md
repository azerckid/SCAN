# SCAN

Evidence-first blockchain forensic tools and competition preparation documents for
SCAN 2026.

## Current status

The repository is documentation-complete for the approved pre-code baseline.
Application implementation has not started. Official rules for AI, automation,
prebuilt tools, external APIs, and challenge submission remain `unclear`; related
features stay disabled until an authoritative notice is recorded.

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
| Completion | [`04_DOCUMENT_COMPLETION_REPORT.md`](docs/05_QA_Validation/04_DOCUMENT_COMPLETION_REPORT.md) | document validation evidence and remaining boundaries |

## Validation

The current repository validation does not install or run application code.

```bash
python3 docs/05_QA_Validation/scripts/validate_fixture_schemas.py
python3 docs/05_QA_Validation/scripts/validate_analysis_schemas.py
git diff --check
```

The expected schema-validator outputs are:

```text
PASS 3 fixture packages validated against schema 0.1
PASS 3 analysis request/result pairs validated against schema 0.1 with reference integrity
```

The fixture validator requires `jsonschema`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r docs/05_QA_Validation/requirements-fixtures.txt
```

## Rules and safe defaults

- An absent prohibition is not treated as permission.
- `unclear` AI, agent, API, automation, and prebuilt-tool capabilities remain off.
- No private key, seed phrase, CTFd credential, or session is stored.
- No automatic answer submission or brute-force path is planned.
- Python CLI and human verification remain the fallback.

## Implementation boundary

The next implementation task is `TASK-001`, Python project initialization. It
requires separate user approval even though the document completion gate is closed.
Exact dependency versions, `uv.lock`, SQLite DDL, migrations, and backup commands
are implementation outputs, not claims made by this documentation baseline.

## License

Project-authored code and documentation are available under the
[MIT License](LICENSE). Third-party data, official documents, linked repositories,
and fixture source material retain their original licenses, terms, and attribution.
