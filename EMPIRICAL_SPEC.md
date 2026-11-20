# EMPIRICAL SPEC — Real Huawei Cloud Behaviors (source material for the simulator)

Every item below was **observed first-hand** during the cloud-explorer / HyperDR / EVS-experiments
tr-west-1, ap-southeast-1). This file is the simulator's
source of truth for "how the real thing actually behaves" — including where it CONTRADICTS the
official docs. Append-only: new findings get added, never silently edited.

Scope note (2026-11-19): v1 targets the **unified international-site core only**
(`*.myhuaweicloud.com`). Sovereign-plane / alternate-domain findings are out of scope for v1
and will be revisited in a future phase.


---

## 1. Identity, signing, endpoints

| # | Behavior | Detail |
|---|---|---|
| 1.1 | REST signing | SDK-HMAC-A256 (HMAC-SHA256), `Authorization: SDK-HMAC-A256 ak:signature`; BasicCredentials carries projectId; `X-Project-Id` header required on project-scoped calls |
| 1.2 | Project model | one project per region; `GET iam.myhuaweicloud.com/v3/projects` lists them; HCS-style regions resolve via **cn-north-4** IAM endpoint with GlobalCredentials |
| 1.3 | Rate limit | rapid scripted calls → HTTP 401/403 with body `{"error_code":"APIGW.0301", ...}`; 30s backoff clears it; appears per-AK |
| 1.4 | OBS is a different signing universe | OBS v2: `Authorization: OBS ak:base64(hmac-SHA1(sk, StringToSign))`; StringToSign = `VERB\nMD5\nType\nDate\nCanonicalizedAmzHeaders+Resource`; **virtual-host style required**; **list params (prefix/max-keys/marker) are NOT part of the canonical resource** (S3 v2-like); Date header must be RFC1123 (`Mon, 28 Sep 1970 06:00:00 GMT`) — ISO8601 → 400 InvalidArgument; using the standard API signer against OBS → 400 "one and only one ' ' (space) required" |
| 1.5 | Custom endpoints work | the SDKs accept arbitrary endpoint URLs via `new Region(name, url)` — this is how the sim wiring is done |

## 2. ECS

| # | Behavior | Detail |
|---|---|---|
| 2.1 | Pagination | `GET /v1/{pid}/cloudservers/detail?limit=N&offset=M`; default limit small (2 observed in tr-west-1!) — always paginate |
| 2.2 | Flavors per region differ | tr-west-1: `s7n.large.2`; ap-southeast-1: `s6.large.2`; **flavors v1 API not served in HCS regions** → probe via createServers dry_run instead |
| 2.3 | Create | `POST /v1/{pid}/cloudservers` (prepaid) with `dry_run` validation; response `serverIds[]` + `jobId`; postpaid variant exists (`createPostPaidServers`) |
| 2.4 | Lifecycle | `os-stop` (SOFT/HARD) → SHUTOFF; `os-start` → ACTIVE; `task_state` (`OS-EXT-STS:task_state`) transitions visible during ops; poll until status==target && task in (null,"-") |
| 2.5 | Async jobs | attach/detach/stop/start return `job_id`; `GET /v1/{pid}/jobs/{id}` → status RUNNING/SUCCESS/FAIL |
| 2.6 | **/dev/vda attach rule (CHANGED ~Oct-Nov 2026)** | attaching a volume with `bootable=false` at `/dev/vda` now fails: `Ecs.0005 "device is illegal"`. Volumes created from images are `bootable=true` and pass. Nova v2.1 direct boot-from-volume is closed. **Workaround (the updated HyperBDR recipe):** create a bootable "carrier" volume from the gold image, dd the replica content into it, then the /dev/vda swap passes |
| 2.7 | Password reset | `Ecs.0100 "server does not support reset password"` on images lacking the reset agent (e.g. imported/HyperBDR images) |
| 2.8 | Response shapes | `addresses` is a dict keyed by VPC name; IP entries carry `OS-EXT-IPS:type` = fixed/floating; flavor info under `flavor.id` (HCS list view returns sparse fields — flavor/az missing) |
| 2.9 | Whole-image creation (HCS) | `POST /v1/cloudimages/wholeimages/action` requires the server STOPPED |

## 3. EVS

| # | Behavior | Detail |
|---|---|---|
| 3.1 | **HCS list view is sparse** | `GET /v2/{pid}/cloudvolumes` (tr-west-1) returns only `{id, links, name}` — size/status/attachments must be fetched per-volume via the `self` link (`os-vendor-volumes`) |
| 3.2 | v2.1 detail endpoint | `GET /v2.1/{pid}/cloudvolumes/detail` returns EMPTY on tr-west-1 (HCS) — use v2 + per-volume detail |
| 3.3 | Create response anomaly | volume id sometimes NOT under `volume.id` (HCS) → resolve by name-based listing fallback |
| 3.4 | **Snapshots require detached volumes** | system disks cannot detach → cannot snapshot; point-in-time capture of a live OS disk needs CBR (v2 path) or agent-side freeze |
| 3.5 | Statuses | `creating → available → in-use`, `error`; attachments: `{server_id, device}`; delete with server takes `delete_volume` flag |

## 4. VPC / EIP

| # | Behavior | Detail |
|---|---|---|
| 4.1 | EIP create | `POST /v1/{pid}/publicips` with embedded `bandwidth {share_type: PER, size, charge_mode: traffic|bandwidth, name}`; response includes `publicip.id`, `public_ip_address` |
| 4.2 | Bind/unbind | `PUT /v1/{pid}/publicips/{id}` with `{publicip:{port_id}}`; port looked up via `GET /v1/{pid}/ports?device_id=<vm>` |
| 4.3 | Traffic-mode billing | bandwidth size is only a CAP; cost is per-GB → resizing 5→300 Mbit costs nothing extra with no traffic |
| 4.4 | Subnet DNS update | `PUT /v1/{pid}/subnets/{id}` with `dnsList/primaryDns/secondaryDns`; VM must renew DHCP (SOFT reboot) to pick it up |
| 4.5 | SG auto-rule quirk | SG creation AUTO-CREATES the intra-SG allow rule; re-adding it → `409 SecurityGroupRuleExists` (treat as OK) |

## 5. IMS

| # | Behavior | Detail |
|---|---|---|
| 5.1 | Register from OBS | `POST /v2/cloudimages` with `image_url: "bucket:key"` (qcow2 in OBS) → `job_id` → poll → `entities.image_id`; image goes queued→active |
| 5.2 | Direct metadata+upload route | create image metadata (status `queued`), then `PUT /v2/images/{id}/file` with the qcow2 body (Glance-style) → `active`; used to bypass OBS entirely |
| 5.3 | Image list | `GET /v2/images` (Glance list, not the public-cloud images API) |

## 6. OBS (beyond signing, §1.4)

| # | Behavior | Detail |
|---|---|---|
| 6.1 | List | `GET /?prefix&max-keys&marker` on the bucket virtual host; `IsTruncated` + `NextMarker` pagination; Owner ID = domain id |
| 6.2 | Errors | `NoSuchKey` on missing chunk; `SignatureDoesNotMatch` on bad sig; XML error bodies with RequestId/HostId |
| 6.3 | Bucket quota | account-level bucket quota (100) can block creating new buckets → reuse user bucket with dedicated prefix |

## 7. Cross-cutting lessons for the simulator

- **Never trust "it copied"** — every real flow ends with a hash/verify step; the sim must make verify-style reads available (e.g. serve written chunk data back correctly).
- **Response shapes vary by REGION, not just by API version** — hence quirk profiles.
- **Async job model is universal** — every mutating op in ECS/EVS/VPC/IMS returns job_id; synchronous-looking responses are the exception.
- **Error bodies carry `error_code`** (e.g. `Ecs.0005`, `APIGW.0301`, `Evs.xxxx`) — clients branch on these, so the sim must emit the exact codes.
