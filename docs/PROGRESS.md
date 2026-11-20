# Progress

Current status of the Larrot simulator. No dates, no timelines - the
numbers below are the status.

## Service coverage

| Metric | Value |
|---|---|
| Distinct Huawei Cloud services | 59 |
| Router modules | 71 |
| Documented operations in the registry | 720 |
| Implemented + tested | 720/720 |
| Operation-level report | [COVERAGE.md](../COVERAGE.md) |

## Test suites

| Suite | Checks | Status |
|---|---|---|
| Unit + integration (pytest) | 523 | all green |
| Real-world scenarios | 50 | all green |
| Request fuzzing (720 ops x 4 variants) | 3,288 requests | zero 5xx |
| Conformance | 72 | all green |
| Negative | 130 | all green |
| Differential (sim-only) | 66 | all green |

## Platform features

- Async job engine with test hooks (`complete_now` / `complete_all`)
- Chaos fault injection (`/admin/chaos`, api + job modes)
- Resource explorer (`/admin/resources`, `/admin/graph`)
- Preset environments (`/admin/preset`: three-tier-app, dr, multi-tenant)
- Compatibility scorecard (`tools/conformance.py` -> CONFORMANCE_REPORT.md)
- Operation coverage matrix (`tools/coverage.py` -> COVERAGE.md)
- Request fuzzing (`tests/test_fuzz.py`)
- Differential harness (`tools/differential.py`, real-account mode via env vars)
- Web console (`/console`) and dashboard (`/`)
- Persistence (`/admin/save`, `/admin/load`)

## Packaging

- PyPI: `larrot` (REST + OBS + CLI)
- CLI: `larrot` (40+ subcommands), server: `larrot-server`
- Docker + docker-compose (binds 0.0.0.0 inside; bare Python defaults to 127.0.0.1)
- CI: Python 3.11/3.12 matrix, lint, full test suite, Docker build

## Known gaps

See the README's "Known limitations" section for what is not simulated,
and [ARCHITECTURES.md](ARCHITECTURES.md) for the tested real-world scenarios.
