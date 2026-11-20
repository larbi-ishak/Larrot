# Larrot 🦜 — Architecture & Code Guide

(Formerly known as `huawei-sim`.)

How the simulator is built, how a request flows through it, and where every piece
lives in the code. Companion docs: `EMPIRICAL_SPEC.md` (what the real cloud does),
`API_DOCS_RESEARCH.md` (what the official docs say), `DECISIONS.md` (why it's built
this way), `DEVLOG.md` (the build journal).

---

## 1. What this is

A **local, API-level simulator of Huawei Cloud** — a set of HTTP services that
reproduce the REST APIs of the international site for **IAM, ECS, EVS, VPC/EIP,
IMS, OBS, and the async Jobs model**, written in Rust (axum + tokio).

The defining design property: it is **not a mock**. It is a stateful simulator —
every resource is a row plus a lifecycle state machine in one shared in-memory
store, and every API mutates or reads that same store. That is what makes the
cross-API correlations real: creating a server allocates a port/IP and a root
volume; attaching a volume flips both the volume and the server views; a job must
complete before a server leaves `BUILD`; stopping a stopped server is rejected
with the real error code.

Fidelity targets, in priority order:
1. `EMPIRICAL_SPEC.md` — observed real-cloud behavior wins everywhere.
2. `API_DOCS_RESEARCH.md` — documented shapes where we have no observation.
3. Anything unobserved and undocumented is a flagged placeholder (see `DECISIONS.md`).

## 2. The big picture

```
                real @huaweicloud SDK clients (unchanged)
                                │
        Region("sim", "http://127.0.0.1:8200")     OBS endpoint http://127.0.0.1:8201
                                │                            │
┌───────────────────────────────┴────────────┐  ┌─────────────┴──────────────┐
│  REST gateway  :8200                      │  │  OBS gateway  :8201         │
│  ──────────────────────────────────────── │  │  ────────────────────────── │
│  middleware stack (outermost first):      │  │  obs_normalize middleware: │
│   1. RateLimiter  (APIGW.0301 emulation)  │  │   • resolve bucket: Host   │
│   2. signature verify (accept-and-check)  │  │     (virtual-host) or path │
│   3. request logging                      │  │     (path-style)          │
│                                           │  │   • OBS v2 HMAC-SHA1       │
│  routers (all share one state):           │  │     verify (accept-check)  │
│   iam / ecs / evs / vpc / ims             │  │                           │
│   fallback: APIGW.0101 flat 404           │  │  bucket ops / object ops / │
│                                           │  │  multipart / XML errors    │
├───────────────────────────────────────────┤  ├────────────────────────────┤
│            Arc<SimState> (one store)       │  │        (same Arc<SimState>)│
│  DashMaps: servers, volumes, snapshots,    │  │  obs_buckets, obs_objects, │
│  ports, vpcs, subnets, eips, security_    │  │  obs_uploads              │
│  groups, images + JobEngine + RateLimiter  │  │                           │
└───────────────────────────────────────────┘  └────────────────────────────┘
```

Two listeners, one process (`crates/gateway/src/main.rs`):
- **`:8200` REST services** — everything except OBS. One port so clients need a
  single `Region` override.
- **`:8201` OBS** — a separate endpoint, exactly like the real cloud (OBS lives on
  `obs.<region>.myhuaweicloud.com`, not the service endpoints). It also avoids
  route conflicts: OBS's path space (`/bucket/key`) would swallow REST paths.

## 3. The request pipeline (REST)

Implemented in `gateway_mw` (`crates/gateway/src/main.rs`), applied as a layer over
the merged routers:

1. **Rate limit** (`common/src/ratelimit.rs`) — a per-AK sliding window. When an
   AK exceeds `SIM_RATE_LIMIT` requests / 10s it is blocked for the cooldown
   (default 30s) and every request in that window gets the flat
   `APIGW.0301` 401 body with the observed message — or `APIGW.0308`/429 in the
   alternative mode. This is the outermost layer because the API Gateway is the
   outermost layer in the real cloud.
2. **Signature verification** (`common/src/signing.rs`) — recomputes the
   SDK-HMAC-SHA256 signature from the actual request (method, canonical URI with
   the signing trailing-slash, sorted RFC-3986 query, canonical headers, payload
   hash) and compares. **Accept-and-check**: the result is logged, never enforced —
   the sim's job is client compatibility, not security. This caught three real
   bugs during development.
3. **Logging** — method/URI/verdict + `X-Project-Id`.
4. **Router dispatch** — per-service routers merged in `main.rs`; unknown paths
   hit the `APIGW.0101` fallback (`crates/gateway/src/lib.rs`).

OBS has its own pipeline (`crates/obs/src/lib.rs`, `obs_normalize`): resolve the
bucket from the Host header (virtual-host style) or the path (path-style — SDKs
fall back to this for IP endpoints), then verify the **OBS v2 signature** — a
completely different algorithm (HMAC-SHA1, `VERB\nMD5\nType\nDate\nx-obs-*\nresource`),
where `Date` goes empty when `x-obs-date` is present and list params
(`prefix`/`max-keys`/`marker`) are **not** part of the canonical resource.

## 4. The state model

`SimState` (`common/src/state.rs`) is the single source of truth, held in an
`Arc` and shared by every handler and every background job:

| Store | Key | Contents |
|---|---|---|
| `servers` | server id | `Server` — full ECS object incl. `OS-EXT-STS:*`, `os-extended-volumes:*` |
| `volumes` | volume id | `Volume` — Cinder-style (`bootable` is a **string**), sparse/detail serializers |
| `snapshots` | snapshot id | `Snapshot` — custom + Cinder shapes |
| `ports` | port id | `Port` — Neutron shape; created at server create (IP allocation) |
| `vpcs` / `subnets` | id | seeded defaults per project + API-created |
| `eips` | eip id | `Eip` — minimal (allocate) and full (GET/PUT) serializers |
| `security_groups` | sg id | `SecurityGroup` with embedded rules (4 auto-created) |
| `images` | image id | `Image` — Glance shape + lifecycle + `reset_agent` flag |
| `obs_buckets` / `obs_objects` / `obs_uploads` | name / `"{bucket}/{key}"` / upload id | OBS store |
| `jobs` | `JobEngine` | async job table |
| `limiter` | `RateLimiter` | per-AK throttle state |

Every resource carries a hidden `project_id` (skipped in serialization) — that is
what makes **project isolation** a real invariant: a server is invisible (404) from
another project's `{pid}`.

### Lifecycle state machines

| Resource | Transitions |
|---|---|
| Server | `BUILD → ACTIVE ⇄ SHUTOFF` (+ REBOOT/HARD_REBOOT/ERROR), with `task_state` set during ops; guards reject ops whose status doesn't allow them (D13) |
| Volume | `creating → available → in-use` (+ attaching/detaching in flight); delete requires `available` |
| Image | `queued → saving → active` (+ killed) |
| Job | `RUNNING → SUCCESS / FAIL` (+ INIT, PENDING_PAYMENT) |
| EIP | `PENDING_CREATE → DOWN ⇄ ACTIVE` |

## 5. The async job engine

`common/src/jobs.rs` — the mechanism behind "every mutating op returns `job_id`":

- `submit(job_type, entities, effect)` inserts a `RUNNING` job and spawns a task
  that sleeps a **jittered 1–3s**, then runs `effect(job_id)`.
- The **effect is an async closure** that mutates the shared state (servers flip to
  `ACTIVE`, volumes to `in-use`, …) and returns `Ok(())` or
  `Err((error_code, fail_reason))` — which is how failed jobs surface exactly like
  the real ShowJob `FAIL` rows.
- The effect receives its own job id so it can patch `entities` (e.g. flip
  sub-jobs to `SUCCESS` when the parent completes).
- `GET /v1/{pid}/jobs/{job_id}` (ECS) and `GET /v1/cloudimages/job/{job_id}` (IMS)
  read the same table — one engine, per-service flavors.

Because effects mutate the same `Arc<DashMap>`s the API reads, **polling clients
observe real intermediate states**: a server is `BUILD` while its job runs, a
volume is `attaching` mid-attach.

## 6. Quirk profiles

`common/src/profile.rs` — an enum `Public | Hcs`, resolved **per region**
(`SimState::profile_of(pid)`): the seed assigns tr-west-1 → `hcs` and
ap-southeast-1 → `public`; `--profile`/`SIM_PROFILE` only sets the default for
regions without an explicit assignment. This mirrors the spec's core finding:
*response shapes vary by REGION, not just by API version*.

Handlers query the profile at the point of behavior, e.g.:
- default list page size: 25 (public) vs **2** (hcs, observed)
- `GET /v2.1/{pid}/cloudvolumes/detail`: full vs **EMPTY** (observed)
- ECS list view: full vs **sparse** (flavor/az removed)
- `addresses` keyed by VPC id vs VPC **name**
- flavors v1: served vs **404**
- whole-image creation: allowed vs **requires STOPPED**

## 7. Error envelopes — per service, not global

Huawei Cloud does not use one error shape. `common/src/envelope.rs` builds each
family, and the integration tests pin them:

| Layer | Shape |
|---|---|
| ECS | nested `{"error":{"code","message","details"?}}` |
| EVS native | nested, `message` first in doc examples |
| VPC/EIP v1 | **flat** `{"code","message"}` |
| API Gateway | flat `{"error_msg","error_code","request_id"}` |
| OBS | XML `<Error><Code>…<RequestId>…` |
| IMS | flat gateway-style for sync errors; job failures via the job object |

## 8. Crate-by-crate code tour

```
sim/crates/
├── common/        the shared foundation
│   ├── signing.rs     SDK-HMAC-SHA256 verify (pure fn, unit-tested round-trip)
│   ├── ratelimit.rs   per-AK sliding window + APIGW.0301/0308 bodies
│   ├── envelope.rs    per-service error body builders
│   ├── jobs.rs        JobEngine (submit/patch/get) + Job model
│   ├── model.rs       all resource structs with serde renames matching the wire
│   │                 (OS-EXT-STS:*, os-extended-volumes:*, bootable-as-string…)
│   ├── state.rs       SimState + seed (account, projects, images, flavors, networks)
│   ├── profile.rs     Public | Hcs enum
│   └── util.rs        ids (uuid / 32-hex job ids), RFC3339, MACs
├── iam/           GET /v3/projects, GET /v3/auth/projects, POST /v3/auth/tokens
│                  (X-Subject-Token + catalog pointing at the sim itself)
├── ecs/           the largest crate:
│                  • list/detail (v1 + v1.1 + Nova v2.1) with filters, offset/marker
│                    pagination, servers_links, hcs sparse view
│                  • create (v1.1 postpaid / v1 prepaid, dry_run, count naming -0000)
│                  • delete (delete_volume × delete_on_termination interaction)
│                  • batch os-stop/os-start/reboot with STATE GUARDS (D13)
│                  • attach/detach volume — resolve_device() holds the Ecs.0005
│                    rules (vda requires bootable, sd→vd conversion, collisions,
│                    auto-assign) as a pure, unit-tested function
│                  • block_device / os-volume_attachments listings (exact doc shapes)
│                  • flavors (hcs 404), password reset (Ecs.0100), ShowJob
├── evs/           volumes: create (v2.1/v2/Cinder + hcs id-anomaly), sparse list,
│                  detail lists (v2 full / v2.1 empty-on-hcs), os-vendor detail,
│                  update, delete (EVS.1046), os-extend; snapshots with the
│                  detached-only rule (force covers ONLY `attaching`)
├── vpc/           vpcs/subnets CRUD + the DNS-update route, EIP allocate (minimal
│                  PENDING_CREATE response) → bind via port device_id lookup →
│                  release (409 VPC.0517), ports list, security groups (4 auto
│                  rules, duplicate → 409 SecurityGroupRuleExists)
├── ims/           the three image-registration routes (OBS-file action, register,
│                  direct Glance upload), whole images (hcs stopped rule), Glance
│                  list/detail/delete, custom list with page_info.next_marker,
│                  ShowJobProgress
├── obs/           its own router + middleware: addressing resolution, v2 signature
│                  verify, buckets/objects/multipart, ListBucketResult XML,
│                  XML errors
└── gateway/       the binary (main.rs: env config, two listeners, middleware
                   stack) + lib.rs (APIGW.0101 fallback) + tests/integration.rs
```

Supporting code outside the crates:
- `sim/tools/smoke.py` — the 119-check harness. It **signs requests itself**
  (both SDK-HMAC-SHA256 and OBS v2) and walks every flow, including all the
  quirk reproductions. `--rate` runs the throttle test against a low-limit server.
- `sim/replay/` — Phase-7 replays using the **official `@huaweicloud` npm SDKs**
  (inventory / lifecycle / provisioning), the closest thing to "the real scripts
  run unchanged".
- `sim/run.sh`, `sim/Dockerfile`, `docker-compose.yml` — run/package.

## 9. Testing architecture

Four layers, each catching a different class of bug (they caught real ones):

| Layer | What it covers | Examples of bugs it caught |
|---|---|---|
| Unit tests (`cargo test`) | pure logic: signing round-trip + tamper, device rules, job outcomes | test-vs-code disagreement on vda collisions |
| Integration tests (`gateway/tests/integration.rs`) | full router via tower `oneshot`, no server: per-service envelopes, hcs quirks, APIGW fallback | envelope field-order assumption (serde_json sorts keys) |
| Smoke (`tools/smoke.py`) | end-to-end over HTTP with real signing: 10 sections, 119 checks, every spec quirk | DashMap deadlock in EIP bind; OBS path-style dispatch; canonical-resource doubling; urllib Content-Type injection |
| REAL-SDK replays (`sim/replay/`) | the actual `@huaweicloud` clients: their signer, their typed response models, their error parsing | SDK raw-key response quirk; upstream eip-v3 packaging bug |

## 10. Configuration & seed

Environment variables (`SIM_PROFILE`, `SIM_PORT`/`SIM_OBS_PORT`, `SIM_AK`/`SIM_SK`,
`SIM_RATE_LIMIT`, `SIM_RATE_COOLDOWN_MS`, `SIM_RATE_MODE`) — see `sim/README.md`.
The seed mimics the lab: account `sim-lab`, two projects (ap-southeast-1/public,
tr-west-1/hcs) with default VPC/subnet, two images (one with, one without the
reset-password agent — the Ecs.0100 switch), per-region flavors.

## 11. The invariant map (what correlates with what)

| Invariant | Enforced in |
|---|---|
| Server exists only as `BUILD` until its job completes | ecs create effect + jobs |
| Port/IP allocated per server; EIP binds only to a real port | state.next_ip, vpc update_eip |
| Root volume attached at `/dev/vda`; system disk never detaches → never snapshottable | ecs build_server/detach, evs create_snapshot |
| `bootable=false` at `/dev/vda` → `Ecs.0005 "device is illegal"` | ecs resolve_device |
| Volume `in-use` can't be deleted/snapshotted | evs delete_volume/create_snapshot |
| ECS delete honors delete_volume × delete_on_termination | ecs delete_servers |
| SG always has the 4 auto rules; duplicates → 409 | vpc default_rules + same_as |
| Whole image (hcs) requires STOPPED server | ims whole_image |
| Unknown path → APIGW.0101; throttled AK → APIGW.0301 | gateway fallback + limiter |
