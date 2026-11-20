# Contributing to Larrot 🦜

Thank you for your interest in contributing! This document covers the basics.

## Getting started

```bash
git clone https://github.com/larbi-ishak/Larrot.git
cd larrot/sim_py
pip install -e ".[dev]"
python -m larrot  # starts on :8200 (REST) and :8201 (OBS)
```

## Project structure

```
sim_py/
├── larrot/
│   ├── core/           # signing, state, jobs, profiles, envelopes, ratelimit
│   ├── services/       # one file per service (iam, ecs, evs, vpc, ims, cbr, obs, rds)
│   ├── app.py          # FastAPI app factory + dashboard
│   ├── middleware.py   # rate limit + signature verification
│   └── cli.py          # larrot CLI
├── tools/
│   ├── smoke.py        # end-to-end smoke suite
│   └── start.sh        # dev server launcher
└── tests/
```

## Adding a new service

1. Create `larrot/services/<name>.py` with an `APIRouter`
2. Register it in `app.py`:
   ```python
   from .services import <name>
   app.include_router(<name>.router)
   ```
3. Add endpoints — use the existing services as patterns
4. Add tests to `tools/smoke.py`
5. Run the smoke suite: `python3 tools/smoke.py`

## Adding a new endpoint to an existing service

1. Add the route handler in the service file
2. Follow the error envelope conventions (see `core/envelopes.py`)
3. Add a smoke test
4. Verify the response shape matches the real API (check the SDK models)

## Error envelopes

Each service family has its own error body shape — this is intentional:

| Service | Shape |
|---|---|
| ECS | `{"error": {"code", "message"}}` |
| EVS | `{"error": {"message", "code"}}` |
| VPC/EIP | `{"code", "message"}` (flat) |
| APIGW | `{"error_msg", "error_code", "request_id"}` (flat) |
| OBS | XML `<Error><Code>…` |

Use the helpers in `core/envelopes.py` — never hand-roll an error body.

## Testing

```bash
# Smoke suite (needs a running server)
python3 tools/smoke.py

# Unit tests
python3 -m pytest tests/ -v
```

## Code style

- Python 3.11+
- Type hints where practical
- `ruff check` for linting
- Docstrings on public functions

## Commit messages

Follow conventional commits:
```
feat: add RDS instance resize endpoint
fix: OBS bucket creation was blocked by existence check
docs: update README with CLI examples
test: add conformance check for volume detail shape
```

## Pull requests

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run the smoke suite
5. Submit a PR with a clear description

## Questions?

Open an issue on GitHub.
