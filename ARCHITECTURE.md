# Larrot architecture

How the simulator is built. For what it simulates see
[CATALOG.md](CATALOG.md); for tested real-world usage see
[docs/ARCHITECTURES.md](docs/ARCHITECTURES.md).

## The one design rule

Larrot emulates **API behavior**, not infrastructure. No VMs run, no
packets flow. The fidelity target is what an SDK client sees: routes,
request validation, response shapes, error envelopes, async job
semantics, and the production quirks in
[docs/EMPIRICAL_SPEC.md](docs/EMPIRICAL_SPEC.md).

## Layers

```
request -> gateway middleware -> service router -> shared core -> response
```

1. **Gateway middleware** (`larrot/middleware.py`) - applied to every
   request: rate limiting (APIGW.0301 emulation), chaos injection
   (configurable 5xx/latency/job failures), and signature verification
   (SDK-HMAC-SHA256 recomputed, accept-and-check).
2. **Service routers** (`larrot/services/*.py`) - one file per service,
   thin FastAPI routers. 59 services, 71 modules, 720 documented
   operations. Handlers parse requests, validate, mutate state, and
   submit async effects.
3. **Shared core** (`larrot/core/`):
   - `state.py` - SimState: all resource stores, seed data (generated
     values only - see the data policy in CONTRIBUTING.md)
   - `jobs.py` - async job engine: every mutation returns a `job_id`,
     effects run after a jittered 1-3s delay, `complete_now`/
     `complete_all` test hooks
   - `signing.py` - SDK-HMAC-SHA256 + OBS v2 verify/sign
   - `profiles.py` - per-region quirk dialects (public vs hcs)
   - `envelopes.py` - per-service error body shapes (ECS nested, VPC
     flat, APIGW with request_id, OBS XML)
   - `ratelimit.py` - per-AK sliding window throttle
   - `chaos.py` - fault injection rules
   - `explorer.py` - unified inventory + dependency graph
   - `presets.py` - one-call environment seeding

## Deliberate asymmetries (fidelity features)

- **Per-service error envelopes**: Huawei's real APIs are inconsistent
  by design; a uniform error shape would be less faithful.
- **Quirk profiles**: the `hcs` project (tr-west-1) serves sparse list
  views, 404s the flavors endpoint, and returns empty v2.1 volume lists
  - observed production behavior.
- **Shared routes**: RDS/DDS/GaussDB share `/v3/{pid}/instances` on
  the real cloud via separate hostnames; single-port Larrot separates
  them by namespaced routes (first-registered answers the bare path).
- **OBS on its own port** (8201) with S3-style XML, like the real
  cloud's separate OBS endpoint.

## Admin surface (not Huawei-compatible)

`/admin/*` endpoints (chaos, resources, graph, presets, save/load) and
`/console` are Larrot-specific and kept outside the Huawei API surface
so they never collide with compatibility.

## Testing posture

| Dimension | Tool | Scale |
|---|---|---|
| Operation coverage | `tools/coverage.py` -> COVERAGE.md | 720/720 documented ops |
| Request robustness | `tests/test_fuzz.py` | 3,288 adversarial requests, zero 5xx |
| Conformance | `tools/conformance.py` | 72 checks + scorecard |
| Negative | `tools/negative_tests.py` | 130 checks |
| Scenarios | `tests/test_scenarios_50.py` | 50 multi-service architectures |
| Differential | `tools/differential.py` | 66-request corpus, real-account mode via env |

## Data policy

Never use real account data. Seed values are generated. See the
non-negotiable policy in [CONTRIBUTING.md](CONTRIBUTING.md).
