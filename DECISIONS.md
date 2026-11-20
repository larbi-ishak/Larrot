# Larrot 🦜: Decision Layout (D1-D31)

> The project was named `huawei-sim` during development (D3);
> renamed to **Larrot** in D31.

Every design decision made while building the simulator, why it was made, where it
lives in the code, and how confident we are in it. This is the readable companion
organized by theme.

---

## How the decision log works

- **Numbering**: `D<n>` assigned in the order decisions were made, never reused.
  Cross-referenced from code comments and the roadmap.
- **Status** of each decision is one of:
  - **settled**: safe to rely on; backed by docs or observation.
  - **reversible**: a default chosen for convenience; cheap to change (config-level).
  - **capture-verify**: a placeholder that must be diffed against real captured
    responses in the plan's replay phase; the list at the bottom collects them.
- **Precedence rule** when sources conflict: **EMPIRICAL_SPEC (observation) >
  official docs > placeholder**. Two decisions (D19, D23) explicitly invoke it.

## Quick reference

| # | Area | Decision | Status |
|---|---|---|---|
| D1 | layout | code lives in `sim/`, isolated from docs | settled |
| D2 | endpoints | single REST gateway port 8200, path routing | settled (amended by D25) |
| D3 | naming | `huawei-sim` | superseded by D31 |
| D4 | stack | Rust 2021, axum + tokio | settled |
| D5 | state | in-memory `Arc<DashMap>`, no persistence | settled |
| D6 | signing | accept-and-check: verify + log, never reject | settled |
| D7 | profiles | quirk profiles are **per-region**, not global | settled |
| D8 | pagination | default list limit: public 25, hcs 2 (observed) | capture-verify (public value) |
| D9 | seed | lab-like account, fake env-overridable AK/SK, 2 projects | settled |
| D10 | ECS create | 200 + `{job_id, serverIds}` (+`order_id` prepaid) | capture-verify |
| D11 | root volume | born `in-use` at server create | settled (simplification) |
| D12 | dry_run | 202 with empty body | capture-verify |
| D13 | state guards | ops on wrong status → 400 `Ecs.0100`; strict sets; batch rejected upfront | capture-verify (concurrent-op code) |
| D14 | quirk wiring | wire per-region quirks inline when their endpoint is built | settled |
| D15 | placeholders | attach/detach + snapshot validation use documented generic codes | capture-verify |
| D16 | EVS statuses | create/extend/delete → 202 `{job_id}`; snapshot delete → 200 | capture-verify |
| D17 | hcs anomaly | Cinder create returns `volume.id: ""` → forces name-based fallback | settled (interpretation) |
| D18 | snapshots | born `creating`, flip to `available` ~1.2s async (no job id) | settled |
| D19 | SG duplicates | 409 **`SecurityGroupRuleExists`** (observed) over docs' `VPC.0602` | settled (spec-wins) |
| D20 | VPC delete | deleting a VPC with subnets → 400 `VPC.0101` placeholder | capture-verify |
| D21 | EIP lifecycle | `PENDING_CREATE` → `DOWN` via async flip ~0.8s | settled |
| D22 | IMS errors | flat gateway-style `IMG.0001` for sync errors | capture-verify |
| D23 | whole image | STOPPED-server rule enforced on **hcs only** | settled (spec-wins + docs) |
| D24 | image scope | images are domain-scoped (IMS is a global service) | settled |
| D25 | OBS port | OBS on its own port 8201 (amends D2) | settled |
| D26 | OBS addressing | accept virtual-host AND path-style | settled |
| D27 | OBS resource | canonical resource is always `/bucket/key` | settled (bug fix) |
| D28 | rate limiter | lives in `SimState`, checked first in the middleware | settled |
| D29 | hcs flavors | flavors v1 on hcs → 404 flat `APIGW.0101` | capture-verify |
| D30 | upstream SDK | eip SDK v3 broken upstream; use its v2 client | settled (external finding) |

---

## Project & kickoff decisions

### D1: Code location: `sim/` subdirectory
All code and build artifacts live in `sim/` (cargo workspace); the docs root stays
clean. The toolchain installs to the standard `~/.cargo`. Nothing is system-wide.
*Where:* repo layout itself.

### D2: Endpoint model: single REST gateway port (8200)
The plan's kickoff question #3. One `Region("sim", "http://127.0.0.1:8200")`
override covers every REST service: the simplest possible client wiring.
Per-service ports remain possible later via config. **Amended by D25** for OBS only.
*Where:* `crates/gateway/src/main.rs` (listener setup).

### D3: Name: `huawei-sim`
Kickoff question #4. Binary name, crate workspace name, docs.
*Where:* `sim/Cargo.toml`, `[[bin]] name = "huawei-sim"`.

### D4: Stack: Rust 2021, axum + tokio
Kickoff question #2 (user-resolved). Tower middleware maps 1:1 to the gateway
design; serde models encode exact wire shapes; one static binary.
*Where:* workspace `Cargo.toml`.

## Core runtime decisions

### D5: State: in-memory only
`Arc<DashMap>` per resource family, no persistence in v1. Persistence was always
planned as a trait swap later; nothing in the validation flows needs restarts.
*Where:* `common/src/state.rs`.

### D6: Signature verification is accept-and-check
The sim **recomputes** both signature families (SDK-HMAC-SHA256 and OBS v2) and
**logs the verdict but never rejects**. Rationale: the sim's job is client
compatibility, and a mis-verification must never block a correctly-signed client.
This decision paid for itself: the logs caught three real bugs (OBS path dispatch,
canonical-resource doubling, harness Content-Type injection).
*Where:* `common/src/signing.rs`, `crates/obs/src/lib.rs` (`verify_obs`), `gateway_mw`.

### D7: Quirk profiles are per-region
`--profile` sets only the *default*; each seeded project carries its own profile
(tr-west-1 → `hcs`, ap-southeast-1 → `public`). Rationale: EMPIRICAL_SPEC §7:
"response shapes vary by REGION, not just by API version": and multi-region
scripts must replay against one instance.
*Where:* `common/src/profile.rs`, `SimState::profile_of`, `Project.profile`.

## Behavioral fidelity decisions (Phase 1)

### D8: Default list page size: public 25, hcs 2
The hcs value is **observed** (tr-west-1 returned 2). The public value (25) is a
placeholder: correct it against real captures.
*Where:* `ecs::default_limit`.

### D9: Seed data mimics the lab
Account `sim-lab`, clearly-fake credentials (`HWYSIMAK…`/`HWYSIMSK…`,
env-overridable), two projects, two images (one **without** the reset-password
agent: that flag is what makes the Ecs.0100 quirk testable), per-region flavors.
*Where:* `SimState::seed`.

### D10: ECS create responds 200 with `{job_id, serverIds}` (+`order_id` on prepaid)
The body shape is documented; the exact status code is an assumption to verify.
*Where:* `ecs::handle_create`.

### D11: Root volume is born `in-use`
At server create the root volume enters the store already attached (skipping the
`creating→available→attaching` dance). A deliberate Phase-1 simplification; the
EVS API surface (Phase 2) models full lifecycles for API-created volumes.
*Where:* `SimState::create_root_volume`.

### D12: `dry_run` returns 202 with an empty body
Docs say only "returns status code 202". Exact body to be verified.
*Where:* `ecs::handle_create`, `ecs::attach_volume`.

### D13: Lifecycle preconditions (state guards)
Ops whose status doesn't allow them → **400 `Ecs.0100`** ("The ECS status does not
meet requirements…", the documented status-mismatch code): stop/reboot require
`ACTIVE`, start requires `SHUTOFF`, any in-flight op (`task_state` set) → 400, and
a **batch is rejected upfront if any member fails**. Your exact example: "if the
ECS is stopped you can't stop it via API": is this decision.
*Where:* `ecs::batch_action` validation block; smoke §5b/§6b.

## Phase 2-4 decisions

### D14: Quirks are wired inline, not stockpiled
When an endpoint is built, its observed per-region quirks are wired immediately
(the profile mechanism already exists) instead of being saved for a consolidated
quirk phase. Avoids rework; the rate limiter and cross-cutting items stayed in
Phase 6.
*Where:* throughout `ecs`/`evs`/`ims` handlers.

### D15: Placeholder codes for unobserved validation gaps
Where the real error code was never observed: unknown-volume/bad-state on attach →
400 `Ecs.0005 "request body is illegal."`; system-disk detach → 400
`Ecs.0005 "device is illegal."`; snapshot on a non-available volume → 400
`EVS.1046 "volume status must be available when create snapshot!"`. All use
documented codes with plausible messages; all flagged for capture verification.
*Where:* `ecs::attach_volume/detach_volume`, `evs::create_snapshot`.

### D16: EVS async status codes
Create/extend/delete → **202** with `{job_id}` (create is documented 202; the
other two assumed). Snapshot delete → 200 empty.
*Where:* `evs` handlers.

### D17: The hcs Cinder-create anomaly is an empty `volume.id`
EMPIRICAL_SPEC §3.3 says the id is "sometimes NOT under `volume.id`" on HCS. The
sim's interpretation: return `id: ""`: which forces clients down the documented
name-based listing fallback, reproducing the workaround behavior end-to-end
(smoke-verified).
*Where:* `evs::create_volume_cinder`.

### D18: Snapshots mature asynchronously without a job id
Born `creating` in the 202 response, flip to `available` after ~1.2s; clients poll
the snapshot itself (the docs show no job id in the response).
*Where:* `evs::create_snapshot`.

### D19: Duplicate SG rule → 409 **`SecurityGroupRuleExists`**
The docs say `VPC.0602`; the real cloud was observed returning
`SecurityGroupRuleExists`. **Spec wins**: the sim emits the observed code with the
docs' message text.
*Where:* `vpc::create_sg_rule`.

### D20: VPC delete with subnets → 400 `VPC.0101` (placeholder)
The real code for this path is unknown; a documented VPC code is used.
*Where:* `vpc::delete_vpc`.

### D21: EIP `PENDING_CREATE` → `DOWN` via async flip (~0.8s)
The allocate response shows `PENDING_CREATE` (documented); subsequent GETs show
`DOWN`. Modeled with a short background flip so clients observe the transition.
*Where:* `vpc::create_eip`.

### D22: IMS sync errors use the flat gateway-style envelope
`{"error_msg","error_code":"IMG.0001","request_id"}`; job failures surface via the
job object (`error_code` + `fail_reason`), matching the documented job shape.
*Where:* `ims::ims_error`.

### D23: Whole-image STOPPED rule is hcs-only
EMPIRICAL_SPEC §2.9 marks the constraint "(HCS)"; the docs allow running servers
(backup-based flow). So: hcs → requires STOPPED; public → allowed. Spec wins for
hcs, docs win for public.
*Where:* `ims::whole_image`.

### D24: Images are domain-scoped
IMS is a global service (no `{pid}` in its URIs); images carry the domain id as
owner. All projects see the same image catalog.
*Where:* `ims` handlers, `Image.project_id`.

## Phase 5-6 decisions

### D25: OBS gets its own port (8201): amendment to D2
Mirrors the real cloud (OBS is a separate endpoint) and avoids route conflicts:
OBS's `/bucket/key` path space would swallow every REST path if merged.
*Where:* `gateway/src/main.rs` (second listener).

### D26: OBS accepts both addressing styles
Virtual-host (`Host: bucket.<anything>`) and path-style (`/bucket/key`). SDKs
automatically fall back to path-style for IP endpoints: which is how local
clients reach the sim without DNS tricks.
*Where:* `obs::host_bucket` + `obs_normalize`.

### D27: The OBS canonical resource is always `/bucket/key`
Regardless of addressing style, the signed resource is the full path. This was
formalized while fixing a real bug the accept-and-check verifier caught: for
path-style requests the bucket was being prepended twice.
*Where:* `obs::canonical_resource`, `obs_normalize`.

### D28: The rate limiter lives in `SimState`, checked first
The API Gateway is the outermost layer in the real cloud, so the throttle runs
before signature verification in the middleware. Per-AK sliding window
(`SIM_RATE_LIMIT`/10s, default 100), 30s cooldown, mode `0301` (401, observed) or
`0308` (429, documented) via `SIM_RATE_MODE`.
*Where:* `common/src/ratelimit.rs`, `gateway_mw`.

### D29: hcs flavors-404 body is the flat `APIGW.0101`
Interpretation: HCS regions simply don't publish the flavors v1 API, so the
gateway's "API does not exist" body is the closest documented behavior. Clients
probe flavors via createServers `dry_run` instead (the observed workaround).
*Where:* `ecs::list_flavors`.

## External findings

### D30: The official eip SDK v3 is broken upstream
`@huaweicloud/huaweicloud-sdk-eip@3.1.x` ships a v3 API that requires a
`GlobalCredentials.js` file missing from the published package. Its **v2** client
loads fine and targets the v1 `/v1/{pid}/publicips` endpoints the sim serves:
the replays use that. Recorded as an upstream finding, not our bug.

---

## The capture-verification list

Everything above marked **capture-verify**, collected in one place. When the real
backend scripts get replayed (plan Phase 7), diff these against captured responses:

| Item | Current placeholder |
|---|---|
| Public-profile default list limit | 25 |
| ECS create status code | 200 |
| `dry_run` response body | empty, 202 |
| Concurrent-op rejection code | `Ecs.0100` |
| Attach: unknown volume / bad volume state | `Ecs.0005 "request body is illegal."` |
| System-disk detach | `Ecs.0005 "device is illegal."` |
| Snapshot on non-available volume | `EVS.1046 "volume status must be available when create snapshot!"` |
| EVS extend/delete status codes | 202 |
| EVS snapshot delete status code | 200 |
| VPC delete with subnets | 400 `VPC.0101` |
| IMS sync error code | `IMG.0001` |
| hcs flavors-404 body | flat `APIGW.0101` |
| Batch job types | `startVMs` / `stopVMs` / `rebootVMs` |
| `task_state` strings | `stopping` / `starting` / `rebooting` |

Everything else in the simulator is backed by an observation (EMPIRICAL_SPEC) or
the official docs (API_DOCS_RESEARCH), and is pinned by an automated check.

### D31: Rename to **Larrot** 🦜

The project (formerly `huawei-sim`) is renamed **Larrot**: Larbi (the author) + parrot
(the mascot). The parrot *repeats the cloud perfectly*, which is the product: a local
simulator indistinguishable from the real Huawei Cloud APIs, quirks included.

- Package: `larrot` (PyPI), CLI: `larrot`, server: `larrot-server`
- Old names (`huawei-sim`, `hcli`) kept as deprecated aliases
- Internal Python package renamed `huawei_sim` → `larrot`
- Branding avoids the "Huawei" trademark in the project name (like LocalStack avoids "AWS")

### D32 — Data policy: never use live account data

Real account identifiers (account names, project/domain/user IDs, image
names) were found in the seed data, docs, git history, and every PyPI
release. All were replaced with generated values, history was rewritten,
and old releases must be yanked.

The rule going forward, enforced socially and by review: seed data is
generated, observed behavior is described without naming the account,
and the sdist ships only code + README + LICENSE so docs can never leak.
