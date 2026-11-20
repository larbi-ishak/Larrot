# Larrot roadmap

This roadmap turns Larrot from "59 simulated services" into a credible Huawei
Cloud API emulation platform. It prioritizes **fidelity over breadth**: the
services exist; what remains is dependency correctness, fault behavior,
evidence-based compatibility, and ecosystem integration.

Guiding principle: keep the shared core (SimState, JobEngine, signing
middleware, per-service envelopes, quirk profiles) and add cross-cutting
engines beside it. Do NOT unify response shapes: Huawei's real APIs are
deliberately inconsistent (nested ECS errors, flat VPC errors, APIGW
request_id bodies, OBS XML), and reproducing that inconsistency is the
product.

## Phase 1: Dependency guards + platform features (P0) — IMPLEMENTED

### 1.1 Deletion dependency guards

Resources must refuse deletion while other resources depend on them,
matching real cloud semantics:

| Delete | Guard | Error |
|---|---|---|
| Subnet | ports exist in the subnet | 409 |
| Security group | ports reference it | 409 |
| VPC | subnets exist (already implemented) | 400 |
| EIP | bound to a port (already implemented) | 409 |
| OBS bucket | contains objects (already implemented) | 409 |
| ER instance | has attachments (already implemented) | 409 |
| CCI namespace | contains pods (already implemented) | 409 |

Note: the 409 codes for subnet/SG in-use are modeled on real behavior, not
empirically observed (no production capture available for these paths).

### 1.2 Chaos and fault injection

A management API to deliberately break things, so users can test how their
applications handle Huawei Cloud failures:

- `POST /admin/chaos` creates a rule: match by service prefix, failure rate
  (0.0-1.0), injected status + error body, optional extra latency.
- Rule type `job`: matched create operations succeed at the API level, but
  their async jobs FAIL (tests polling/retry logic).
- `GET /admin/chaos` lists rules; `DELETE /admin/chaos/{id}` removes one;
  `POST /admin/chaos/reset` clears all.

### 1.3 Resource explorer

One API to discover every resource in the simulator:

- `GET /admin/resources` unified inventory (filter by id, type, project, name).
- `GET /admin/resources/{id}` find a resource anywhere.
- `GET /admin/graph/{id}` direct dependencies (server -> ports/volumes,
  VPC -> subnets/ports, volume -> attachments).

### 1.4 Compatibility scorecard

Extend the conformance suite into a per-service percentage matrix:
API coverage, request validation, response fidelity, error fidelity,
lifecycle, dependencies. Published as CONFORMANCE_REPORT.md so the roadmap
is evidence-based.

## Phase 2: Testing depth + developer experience (P1) — IMPLEMENTED

### 2.1 Property-based testing

Generate hundreds of randomized request combinations and assert invariants:

- A failed operation must not leave partially created resources.
- A deleted resource must not appear in list results.
- Resource IDs must remain unique.
- Cross-project access must 404.
- Repeated deletes follow real semantics (404 after success).

Implemented with a seeded RNG generator (no new dependencies), so failures
are reproducible.

### 2.2 Preset environments

One-call deployment of realistic seeded environments:

- `POST /admin/preset/three-tier-app` VPC + subnet + SG + 2 ECS + ELB + EIP
- `POST /admin/preset/dr` ECS + EVS + snapshot + CBR vault + backup
- `POST /admin/preset/multi-tenant` resources across both projects
- `GET /admin/preset` list available presets

## Phase 3: Ecosystem compatibility (P1/P2) — harness shipped (sim-only mode); real-account differential and Terraform validation pending credentials

### 3.1 Differential testing harness — tools/differential.py shipped

The killer feature: send the same request to a real Huawei Cloud test
project and to Larrot, normalize dynamic fields (ids, timestamps,
request_ids), and diff. Converts EMPIRICAL_SPEC.md from manual notes into
a CI-runnable regression harness.

- `tools/differential.py` runner with a request corpus.
- Targets configured by env vars (real account AK/SK/endpoints).
- Sim-only mode validates response schemas without a real account.
- Reports: identical / shape-match / mismatch, per service.

### 3.2 Terraform provider validation — examples/terraform/ shipped, unvalidated

If the community `huaweicloud` Terraform provider works against Larrot via
endpoint overrides, unmodified, that is a headline capability. Ship
`examples/terraform/` with a working config and document the result.

## Phase 4: Advanced simulation (P3)

| Feature | Value |
|---|---|
| Time machine | Advance simulated time: trigger retention, expiry, scheduled jobs |
| Record and replay | Capture real interactions, replay as fixtures |
| Network reachability analyzer | Explain why ECS-A can/cannot reach ECS-B (SG + ACL + routes) |
| Realistic metric generators | CES datapoints driven by resource state |
| Pricing simulation | BSS cost breakdowns per service |

## KPIs

- Operation coverage: implemented / documented operations per service.
- Compatibility rate: differential tests passing.
- Lifecycle correctness: state transition tests passing.
- Dependency correctness: cross-service guard tests passing.
- Determinism: same scenario, same outcome (seeded).

## Deliberately not planned

- A rigid unified ResourceEngine class hierarchy (would fight per-service
  fidelity).
- Real compute/network virtualization (Larrot is an API emulator).
- More service breadth before depth: the top 15 services by usage come first.

## Implementation log

- Phase 1: dependency guards (subnet/SG in-use -> 409), chaos engine
  (/admin/chaos, api + job modes), resource explorer (/admin/resources,
  /admin/graph), compatibility scorecard (tools/conformance.py ->
  CONFORMANCE_REPORT.md). Property tests caught and fixed 2 real bugs:
  VPC create accepted empty names and invalid CIDRs; IAM token crashed
  with a 500 on {"auth": null}.
- Phase 2: property-based tests (tests/test_property.py, seeded RNG,
  6 invariants), preset environments (/admin/preset: three-tier-app,
  dr, multi-tenant).
- Phase 3: differential harness (tools/differential.py, 15-request corpus,
  sim-only mode green) and Terraform example (examples/terraform/).
