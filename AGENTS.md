# AGENTS.md — working on Larrot with coding agents

Larrot is a local Huawei Cloud API simulator (LocalStack, but for Huawei
Cloud). Python 3.11+, FastAPI, Apache-2.0. This file is the guide for
AI coding agents contributing to this repository.

## Ground rules

- **Never use real account data.** No real AK/SK keys, project IDs,
  account names, or IPs — generated values only. This is non-negotiable.
- Keep every change tested: `PYTHONPATH=. python3 -m pytest tests/ -q`
  must stay green (550+ tests).
- Lint before committing: `ruff check larrot/` (CI enforces it).
- Docs are code: `docs/coverage.md` is generated
  (`python3 tools/gen_coverage.py`) and enforced by a test. If you add
  or change operations, regenerate it.

## Architecture (one paragraph)

`larrot/app.py` builds two FastAPI apps: REST (port 8200) and OBS
(port 8201). Every service lives in `larrot/services/<name>.py` as an
`APIRouter` and is registered in `app.py`. All state is one object:
`SimState` (`larrot/core/state.py`) — plain dicts/lists per resource
type, reachable as `request.app.state.sim`. Mutating operations return
jobs (`larrot/core/jobs.py`, async with jittered delays; tests call
`state.jobs.complete_all()`). Cross-cutting behavior is middleware
(`larrot/middleware.py`): rate limiting, chaos injection, signature
verification (accept-and-check by default; `SIM_IAM=enforce` to reject),
and the request journal. Error envelopes differ per service
(`larrot/core/envelopes.py`) — match the service you are editing.
Region quirks: `larrot/core/profiles.py` (public vs HCS).

## Common tasks

**Run the simulator:** `PYTHONPATH=. python3 -m larrot` (REST :8200,
OBS :8201). Health: `GET /health`. Console UI: `http://127.0.0.1:8200/console`.

**Run tests:** `PYTHONPATH=. python3 -m pytest tests/ -q --tb=short`.
Fast feedback on one area:
`pytest tests/test_core.py tests/test_compute.py -q`.

**Add an operation:** find the service module, add the route with the
exact real Huawei path/shape, then add tests. The official SDK
compatibility suite (`tests/test_official_sdk.py`, needs
`pip install larrot[sdk]`) and the conformance suite
(`python3 tools/conformance.py`) both validate shapes — run them.

**Add a service:** `python3 -m larrot.cli new-service <name>` scaffolds
the module and tests; register the router in `app.py` (import + one
`include_router` line), regenerate `docs/coverage.md`.

**Debug a 404:** the API returns `near_matches` — the closest real
routes. The request journal (`GET /admin/requests`) shows everything
the client sent.

## Testing culture

Conformance (`tools/conformance.py`), negative tests, fuzzing
(`tools/fuzz.py`), property-based tests, 50 real-world scenarios, the
official-SDK suite, and a Terraform apply/destroy scenario are all part
of CI. When you fix a bug, add the test that would have caught it.

## Admin platform (useful for agent-driven testing)

`POST /admin/reset` wipes state; `POST /admin/seed?a=42` makes IDs
deterministic; `PUT /admin/state/{rid}` forces any resource state;
`GET /admin/requests` is the request journal; `POST /admin/chaos`
injects failures; `POST /admin/preset/{name}` deploys environments.
`larrot mcp` exposes all of this as MCP tools.
