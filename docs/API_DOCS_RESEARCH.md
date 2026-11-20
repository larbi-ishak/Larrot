# Huawei Cloud API Reference Research: findings from official docs

Compiled 2026-11-19 from `support.huaweicloud.com` (intl/en-us) official API references.
Companion to `EMPIRICAL_SPEC.md`: that file is what the real cloud *actually does* (observed);
this file is what the official docs say the APIs *are* (endpoints, shapes, algorithms).
Where the two conflict, EMPIRICAL_SPEC.md wins for simulator behavior.

Sources are cited per section. All endpoints are the international site (`*.myhuaweicloud.com`):
the unified core the simulator reproduces.

---

## 1. Request signing: two universes

### 1.1 SDK-HMAC-SHA256 (all REST services except OBS)

Source: API Request Signing Guide:
https://support.huaweicloud.com/intl/en-us/devg-apisign/api-sign-algorithm-001.html
(worked example: .../api-sign-algorithm-002.html; reference implementation:
https://github.com/huaweicloud/huaweicloud-sdk-python-v3/blob/master/huaweicloud-sdk-core/huaweicloudsdkcore/signer/signer.py)

```
CanonicalRequest =
    HTTPRequestMethod + '\n' +
    CanonicalURI + '\n' +
    CanonicalQueryString + '\n' +
    CanonicalHeaders + '\n' +     // each line "name:value\n"; a final blank line follows the block
    SignedHeaders + '\n' +        // semicolon-joined lowercase header names
    HexEncode(SHA256(RequestPayload))

StringToSign =
    "SDK-HMAC-SHA256" + '\n' +
    X-Sdk-Date + '\n' +           // YYYYMMDDTHHMMSSZ, same as the X-Sdk-Date request header
    HexEncode(SHA256(CanonicalRequest))

signature = HexEncode(HMAC-SHA256(SK, StringToSign))

Authorization: SDK-HMAC-SHA256 Access=AK, SignedHeaders=content-type;host;x-sdk-date, Signature=<hex>
```

Rules that matter for a verifier:
- **CanonicalURI**: RFC 3986 URI-encoded; **must end with `/` for signing** (trailing slash added
  for signature computation even though the actual request may omit it). The worked example signs
  `/v1/{pid}/vpcs/` while sending `/v1/{pid}/vpcs`.
- **CanonicalQueryString**: params sorted by name; keys and values RFC 3986 encoded
  (unreserved `A-Za-z0-9-_.~` never encoded); empty string if no params.
- **CanonicalHeaders**: header names lowercased, values trimmed, sorted lexicographically;
  `host`, `content-type`, and `x-sdk-date` are the typical signed set. Multi-value headers are
  comma-joined.
- **Empty payload hash**: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Scoping headers on the request: `X-Sdk-Date`, `X-Project-Id` (project-scoped calls),
  `X-Domain-Id` (global services). `X-Project-Id` is NOT necessarily in SignedHeaders: the
  verifier must use whatever SignedHeaders lists.
- Auth header grammar: `algorithm` + space + `Access=AK`, then `, SignedHeaders=…, Signature=…`
  (comma-separated, no space after commas).

### 1.2 OBS v2 (HMAC-SHA1): completely different

Source: OBS API Reference → Authentication → Using an Authorization Header:
https://support.huaweicloud.com/intl/en-us/api-obs/obs_04_0010.html

```
Authorization: OBS <AK>:<Signature>
Signature = Base64( HMAC-SHA1( SK, UTF-8( StringToSign ) ) )

StringToSign =
    HTTP-Verb + "\n" +          // GET|PUT|POST|DELETE|HEAD|OPTIONS
    Content-MD5 + "\n" +        // base64 MD5 of body, empty if absent
    Content-Type + "\n" +       // empty if absent
    Date + "\n" +               // RFC 1123 GMT; EMPTY if x-obs-date header present
    CanonicalizedHeaders +      // x-obs-* headers, lowercase names, sorted, "name:value\n" each;
                                // if NO x-obs-* headers exist, this block contributes NO extra newline
    CanonicalizedResource       // "/" + bucket + "/" + object + "?" + sorted signed sub-resources
```

- **Date**: RFC 1123 GMT (`Mon, 28 Sep 1970 06:00:00 GMT`). If >15 min from server time → 403.
  ISO-8601 dates are rejected (matches EMPIRICAL_SPEC §1.4).
- **CanonicalizedResource sub-resources**: the EXACT signed list from the docs:
  `CDNNotifyConfiguration, acl, append, attname, backtosource, cors, customdomain, delete,
  deletebucket, directcoldaccess, encryption, inventory, length, lifecycle, location, logging,
  metadata, mirrorBackToSource, modify, name, notification, obscompresspolicy, partNumber,
  policy, position, quota, rename, replication, response-cache-control,
  response-content-disposition, response-content-encoding, response-content-language,
  response-content-type, response-expires, restore, storageClass, storagePolicy, storageinfo,
  tagging, torrent, truncate, uploadId, uploads, versionId, versioning, versions, website,
  x-image-process, x-image-save-bucket, x-image-save-object, x-obs-security-token, object-lock,
  retention`.
  **`prefix`, `max-keys`, `marker`, `delimiter` are NOT in the list** → list parameters are NOT
  part of the canonical resource (confirms EMPIRICAL_SPEC §1.4).
- Multiple values of the same sub-resource key: only the first is used for signing.
- Auth failure → **403** with error code `SignatureDoesNotMatch`.
- Bucket addressing: virtual-host style (`bucket.obs.<region>.myhuaweicloud.com`); with a custom
  domain the domain name replaces the bucket in CanonicalizedResource.

---

## 2. IAM

Sources:
- KeystoneListProjects: https://support.huaweicloud.com/intl/en-us/api-iam/iam_06_0001.html
- KeystoneListAuthProjects: https://support.huaweicloud.com/intl/en-us/api-iam/iam_06_0003.html
- KeystoneCreateUserTokenByPassword: https://support.huaweicloud.com/intl/en-us/api-iam/iam_30_0001.html

### 2.1 GET /v3/projects
Query params (all optional): `domain_id`, `name`, `enabled`, `is_domain`, `parent_id`,
`page` + `per_page` (1-5000).
```json
{
  "projects": [
    {
      "domain_id": "d78cbac186b744899480f25bd02...",
      "is_domain": false,
      "parent_id": "d78cbac186b744899480f25bd022...",
      "name": "ap-southeast-1",
      "description": "",
      "links": { "self": "https://iam.myhuaweicloud.com/v3/projects/06f1c..." },
      "id": "7b04940625a24928b8ab5c51552e658e",
      "enabled": true
    }
  ],
  "links": { "self": "https://iam.myhuaweicloud.com/v3/projects", "previous": null, "next": null }
}
```
- One project per region; `name` = region name (e.g. `ap-southeast-1`); `MOS` is OBS's built-in
  project. `parent_id` = account (domain) ID for built-in projects.
- Auth: `X-Auth-Token` header (Content-Type `application/json;charset=utf8`).

### 2.2 GET /v3/auth/projects
Same response shape; lists projects the token's user can access. No special permissions needed.

### 2.3 POST /v3/auth/tokens
Request (password auth, project scope):
```json
{
  "auth": {
    "identity": {
      "methods": ["password"],
      "password": { "user": { "domain": { "name": "DomainName" },
                              "name": "IAMUserName", "password": "..." } }
    },
    "scope": { "project": { "name": "ap-southeast-1" } }
  }
}
```
(`scope` may be `domain` for global services; `?nocatalog=true` omits the catalog.)
Response: **`X-Subject-Token` response header** carries the token; body has a `token` object with
`catalog` (service → endpoint URLs per region), `user`, `roles`, `project`/`domain`.
Token validity: **24 h**. Status codes: 201 (201/200 per doc examples), 400, 401, 403, 405, 413, 500, 503.

### 2.4 Endpoints
Global: `iam.myhuaweicloud.com`; per-region: `iam.<region>.myhuaweicloud.com`.
HCS-style regions resolve via the **cn-north-4** IAM endpoint with GlobalCredentials
(EMPIRICAL_SPEC §1.2: keep this behavior in the `hcs` quirk profile).

---

## 3. ECS

Sources:
- API overview: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_01_0008.html
- ListServersDetails: https://support.huaweicloud.com/intl/en-us/api-ecs/en-us_topic_0094148850.html
- ListCloudServers (v1.1): https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0107.html
- ShowServer: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0104.html
- Create (v1.1): https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0101.html
- Create (pay-per-use): https://support.huaweicloud.com/intl/en-us/api-ecs/en-us_topic_0020212668.html
- Delete: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0103.html
- Batch start/stop: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0301.html / ecs_02_0303.html
- Attach volume: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0605.html
- ShowJob: https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_02_0901.html
- Responses (Jobs): https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_07_0005.html
- ListFlavors: https://support.huaweicloud.com/intl/en-us/api-ecs/en-us_topic_0020212656.html

### 3.1 List / detail
- `GET /v1/{pid}/cloudservers/detail`: query: `offset` (page number, deprecated in favor of
  marker), `marker` (last server id), `limit`, `flavor`, `name` (fuzzy), `status`, `ip`, `tags`,
  `not-tags`, `reservation_id`. Response: `{count, servers[], servers_links[]}` (servers_links
  present only when a next page exists; `href` gives the next-page URL).
- `GET /v1.1/{pid}/cloudservers/detail`: same, plus billing/freeze info (`market_info`), and
  `power_state`, `cpu_options`.
- `GET /v1/{pid}/cloudservers/{server_id}` → `{server: {...}}`.
- Nova variants: `GET /v2.1/{pid}/servers`, `GET /v2.1/{pid}/servers/detail` (OpenStack shapes).

Server object (observed doc example: field-for-field target for serde models):
```json
{
  "fault": null,
  "id": "4f4b3dfa-eb70-47cf-a60a-998a53bd598a",
  "name": "ecs-2ecf",
  "addresses": {
    "0431c5e5-bc94-4a44-8263-15da2a642435": [
      { "version": "4", "addr": "192.168.1.99", "primary": true,
        "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:df:18:6d",
        "OS-EXT-IPS:type": "fixed",
        "OS-EXT-IPS:port_id": "23037c18-027a-44e5-b6b9-f8d8f113fe02" }
    ]
  },
  "flavor": { "disk": "0", "vcpus": "2", "ram": "1024", "id": "s3.large.1",
              "name": "s3.large.1", "gpus": [], "asic_accelerators": [] },
  "accessIPv4": "", "accessIPv6": "",
  "status": "ACTIVE",
  "image": { "id": "1ce5800a-e487-4c1b-b264-3353a39e2b4b" },
  "progress": 0,
  "hostId": "f92345b97fd291f67a29ed735a82a8983f370175d2ba3d18d66893f4",
  "OS-EXT-SRV-ATTR:reservation_id": "r-xmjj4pnm",
  "OS-EXT-SRV-ATTR:hostname": "ecs-1f30",
  "OS-EXT-STS:task_state": null,
  "OS-EXT-STS:power_state": 1,
  "OS-EXT-STS:vm_state": "active",
  "OS-EXT-SRV-ATTR:host": "az1.dc1",
  "OS-EXT-SRV-ATTR:instance_name": "instance-0013772d",
  "locked": false, "config_drive": "",
  "tenant_id": "edcb94a885a84ed3a3fdf8ea4d2741da",
  "user_id": "b44a37e1192442acaa0d578b63e38fe3",
  "key_name": "...",
  "description": "ecs-1f30",
  "created": "2019-05-22T07:48:53Z", "updated": "2019-05-22T03:30:52Z",
  "metadata": {...}, "tags": [...],
  "sys_tags": [ { "key": "_sys_enterprise_project_id", "value": "0" } ],
  "security_groups": [ { "name": "default" } ],
  "os-extended-volumes:volumes_attached": [
    { "id": "<volume-id>", "delete_on_termination": "false",
      "bootIndex": "0", "device": "/dev/sda", "size": 40 }
  ]
}
```
- Status enum: `ACTIVE, BUILD, ERROR, HARD_REBOOT, MIGRATING, REBOOT, REBUILD, RESIZE,
  REVERT_RESIZE, SHUTOFF, VERIFY_RESIZE, DELETED, SHELVED, SHELVED_OFFLOADED, UNKNOWN`.
- `addresses` is keyed by **network/VPC id** (real cloud keys it by VPC *name* in some regions:
  EMPIRICAL_SPEC §2.8; encode per profile). `OS-EXT-IPS:type` = `fixed` | `floating`.

### 3.2 Create
- `POST /v1.1/{pid}/cloudservers` (pay-per-use) and `POST /v1/{pid}/cloudservers` (adds
  yearly/monthly billing fields). Idempotency header: `X-Client-Token`.
- Request: `{server: {imageRef, flavorRef, name, user_data?, adminPass?, key_name?,
  vpcid, nicos[{subnet_id, ip_address?}], availability_zone, root_volume{volumetype, size,
  extendparam}, data_volumes[], publicip{id?, eip{...bandwidth...}}, count, ...}, dry_run?}`.
- `dry_run: true` → validate only; success returns **202** with no resources created.
- Response: `{job_id, order_id?, serverIds[]}` (`order_id` only for yearly/monthly).
  Note: serverIds may 404 on immediate detail query while the create job is RUNNING.

### 3.3 Delete
- `POST /v1/{pid}/cloudservers/delete` with `{servers: [{id}], delete_publicip?, delete_volume?}`
  → `{job_id}`. Max 1000 per batch. `delete_volume` interacts with each volume's
  `delete_on_termination` flag (either being true → disk deleted).

### 3.4 Batch lifecycle actions
- `POST /v1/{pid}/cloudservers/action` with one of:
  - `{"os-start": {"servers": [{"id": ...}]}}`
  - `{"os-stop": {"type": "SOFT"|"HARD", "servers": [...]}}`
  - `{"reboot": {"type": "SOFT"|"HARD", "servers": [...]}}`
- All → `{job_id}`. Rate: max 1000 servers processed per minute.

### 3.5 Attach / detach volume
- `POST /v1/{pid}/cloudservers/{server_id}/attachvolume` with
  `{volumeAttachment: {volumeId, device?, volume_type?, count?, "hw:passthrough"?}, dry_run?}`
  → `{job_id}`.
- **Device rules (doc)**: KVM system disk must be `/dev/vda`; data disks `/dev/vdb`, `/dev/vdc`, …
  in alphabetical order; a `/dev/sd*` request is silently converted to `/dev/vd*` on KVM
  (and vice-versa on Xen). Device name must not collide with an existing one.
- Detach: `DELETE /v1/{pid}/cloudservers/{server_id}/attachvolume/{volume_id}`
  (ecs_02_0606) → `{job_id}`.
- Batch shared-volume attach: `POST /v1/{pid}/batchaction/attachvolumes/{volume_id}`.

### 3.6 Jobs
- `GET /v1/{pid}/jobs/{job_id}` →
```json
{
  "status": "SUCCESS",            // SUCCESS | RUNNING | FAIL | INIT | PENDING_PAYMENT
  "entities": {
    "sub_jobs_total": 1,
    "sub_jobs": [ { "status": "SUCCESS", "entities": {"server_id": "..."},
                    "job_id": "...", "job_type": "createSingleServer",
                    "begin_time": "2016-04-25T20:04:47.591Z",
                    "end_time": "2016-04-25T20:08:21.328Z",
                    "error_code": null, "fail_reason": null } ]
  },
  "job_id": "...", "job_type": "createServer",
  "begin_time": "...", "end_time": "...",
  "error_code": null, "fail_reason": null
}
```
- `job_type` values: `createServer`, `createSingleServer`, `resizeServer`, `changeOS`, `reInitOs`,
  `attachVolume`, `detachVolume`, `deleteVMs`, `addNicsForServer`, …
- Terminal jobs (SUCCESS/FAIL) are garbage-collected after ~1 day (PENDING_PAYMENT after 14).
- **Async-response envelope**: normal `{job_id}`; abnormal
  `{"error": {"message": "...", "code": "...", "details": [{"code": "...", "message": "..."}]}}`.

### 3.7 Flavors
- `GET /v1/{pid}/cloudservers/flavors` (ListFlavors + extended info): **this is the endpoint that
  is NOT served in HCS regions** (EMPIRICAL_SPEC §2.2); probe via createServers `dry_run` instead.
- Nova: `GET /v2.1/{pid}/flavors/detail`.

---

## 4. EVS

Sources:
- Create (v2.1): https://support.huaweicloud.com/intl/en-us/api-evs/evs_04_2003.html
- Querying EVS Disks (deprecated, sparse): https://support.huaweicloud.com/intl/en-us/api-evs/evs_04_2012.html
- Creating an EVS Snapshot: https://support.huaweicloud.com/intl/en-us/api-evs/evs_04_2016.html
- EVS task status: https://support.huaweicloud.com/intl/en-us/api-evs/evs_04_0054.html
- Permissions table (endpoint inventory): https://support.huaweicloud.com/api-evs/evs_04_0025.html

### 4.1 Endpoint inventory (from the permissions table)
| Operation | URI |
|---|---|
| Create (v2.1, pay-per-use/prepaid) | `POST /v2.1/{pid}/cloudvolumes` |
| Create (v2 custom) | `POST /v2/{pid}/cloudvolumes` |
| Create (Cinder) | `POST /v2/{pid}/volumes` |
| List (v2 custom) | `GET /v2/{pid}/cloudvolumes` |
| List details (v2 custom) | `GET /v2/{pid}/cloudvolumes/detail` |
| List details (os-vendor) | `GET /v2/{pid}/os-vendor-volumes/detail` |
| Single detail (os-vendor) | `GET /v2/{pid}/os-vendor-volumes/{volume_id}` |
| Single detail (v2 custom) | `GET /v2/{pid}/cloudvolumes/{volume_id}` |
| Cinder list/detail | `GET /v2/{pid}/volumes`, `/v2/{pid}/volumes/detail`, `GET /v2/{pid}/volumes/{id}` |
| Update | `PUT /v2/{pid}/cloudvolumes/{id}` |
| Delete | `DELETE /v2/{pid}/cloudvolumes/{id}` |
| Extend | `POST /v2/{pid}/cloudvolumes/{id}/action` (v2/v2.1) |
| Snapshot create (custom) | `POST /v2/{pid}/cloudsnapshots` |
| Snapshot list/detail (custom) | `GET /v2/{pid}/cloudsnapshots/…` |
| Snapshot create (Cinder) | `POST /v2/{pid}/snapshots` |
| Snapshot list detail (Cinder) | `GET /v2/{pid}/snapshots/detail` |
| Task status | `GET /v1/{pid}/jobs/{job_id}` |

### 4.2 Create (v2.1)
Request: `{volume: {availability_zone, size, name, volume_type, metadata, multiattach?,
iops?, throughput?, tags?, enterprise_project_id?, snapshot_id?, imageRef?, count?},
bssParam?: {chargingMode: "postPaid"|"prePaid", isAutoPay, isAutoRenew, periodType, periodNum},
"OS-SCH-HNT:scheduler_hints"?: {dedicated_storage_id}, server_id?}`.
- `volume_type` enum: `SATA` (common I/O), `SAS` (high I/O), `GPSSD`, `SSD` (ultra I/O), `ESSD`,
  `GPSSD2`, `ESSD2`.
- Idempotency header `X-Client-Token` (36-UUID, 8 h validity).
- Response **202**: `{job_id, volume_ids[]}`.
- v2 custom variant returns just `{job_id}` (per Getting Started example).
- Cinder variant returns 202 with a full `volume` object (status `creating`, `bootable: "false"`).

### 4.3 The sparse list (HCS gold)
`GET /v2/{pid}/cloudvolumes` (deprecated DiskSummary list) returns ONLY:
```json
{ "volumes": [ { "id": "e6cf4401-…", "links": [ {"href": "https://…/v2/{pid}/volumes/{id}", "rel": "self"},
                                                {"href": "https://…/{pid}/volumes/{id}", "rel": "bookmark"} ],
                  "name": "hallo5" } ] }
```
**This is exactly the sparse shape the HCS region (tr-west-1) serves** (EMPIRICAL_SPEC §3.1):
the `public` profile should serve the full shape here, the `hcs` profile serves DiskSummary and
forces clients through the `self` link (os-vendor-volumes/{id}) for details.
Query params: `marker, name, status, limit (default 1000), availability_zone, sort_key
(id|status|size|created_at), sort_dir (desc|asc)`. Error: `{"error": {"message": "...", "code": "..."}}`.

### 4.3b Per-volume detail via the `self` link: `GET /v2/{pid}/os-vendor-volumes/{volume_id}`
(evs_04_2011; bulk variant `GET /v2/{pid}/os-vendor-volumes/detail` = evs_04_2010.)
Full Cinder-style object: the detail source in HCS regions:
```json
{ "volume": {
    "attachments": [],
    "links": [ {"href": "https://…/v2/{pid}/volumes/{id}", "rel": "self"},
               {"href": "https://…/{pid}/volumes/{id}", "rel": "bookmark"} ],
    "availability_zone": "az-dc-1",
    "os-vol-host-attr:host": "az-dc-1#SSD",
    "encrypted": false,
    "multiattach": true,
    "updated_at": "2016-02-03T02:19:29.895237",
    "replication_status": "disabled",
    "id": "591ac654-…",
    "size": 40,
    "user_id": "fd03ee73295e45478d88e15263d2ee4e",
    "os-vol-tenant-attr:tenant_id": "40acc331ac784f34842ba4f08ff2be48",
    "metadata": {},
    "tags": {"key1": "value1"},
    "status": "available",
    "description": "…",
    "name": "…",
    "bootable": "false",
    "created_at": "2016-02-03T02:19:11.723797",
    "service_type": "EVS",
    "wwn": " 688860300000d136fa16f48f05992360" } }
```
⚠️ `bootable` is a **string** (`"false"`/`"true"`), not a boolean: Cinder legacy. Attachments
entries carry `{server_id, device}` (EMPIRICAL_SPEC §3.5).

### 4.4 Snapshots
- `POST /v2/{pid}/cloudsnapshots` with `{snapshot: {volume_id, force?, metadata?, description?, name?}}`
  → **202** `{snapshot: {id, status: "creating", name, description, created_at, updated_at,
  metadata, volume_id, size, "os-extended-snapshot-attributes:project_id",
  "os-extended-snapshot-attributes:progress"}}`.
- `force: false` (default) refuses snapshots while the disk is in `attaching` status; `force: true`
  allows it. (In the real cloud, in-use SYSTEM disks still can't be snapshotted because they
  cannot detach: EMPIRICAL_SPEC §3.4.)
- Cinder list: `GET /v2/{pid}/snapshots/detail` → `{snapshots: [{status: "available",
  description, updated_at, volume_id, id, size, "os-extended-snapshot-attributes:progress": "100%",
  name, "os-extended-snapshot-attributes:project_id", created_at, metadata}]}`.
- Rollback: `POST /v2/{pid}/cloudsnapshots/{id}/rollback`.

### 4.5 EVS task status
`GET /v1/{pid}/jobs/{job_id}` → `{status: SUCCESS|RUNNING|FAIL|INIT|WAITING_EXECUTE|LISTENING,
entities: {volume_type, …}, job_id, job_type: createVolume|batchCreateVolume|deleteVolume|
extendVolume|bulkDeleteVolume|deleteSingleVolume|retypeVolume, begin_time, end_time,
error_code, fail_reason}`. (Note: EVS has two extra terminal-ish statuses vs ECS.)

### 4.6 Volume statuses
`creating → available → in-use`, `attaching`, `detaching`, `error`, `deleting`, …
Attachments on detail: `attachments: [{server_id, device, id, …}]`.

---

## 5. IMS

**Detailed appendix with full field tables and the complete doc-URL index:
`api-docs-research.md`.**

Sources:
- Registering an Image: https://support.huaweicloud.com/intl/en-us/api-ims/ims_03_0608.html
- Quick import: https://support.huaweicloud.com/intl/en-us/api-ims/ims_03_0605.html
- ISO example (create via /v2/cloudimages/action): https://support.huaweicloud.com/api-ims/ims_03_0801.html
- Permissions table (endpoint inventory): https://support.huaweicloud.com/api-ims/ims_03_appendix_05.html

### 5.1 Endpoint inventory
| Operation | URI |
|---|---|
| Create image (from OBS file / ECS / data disk) | `POST /v2/cloudimages/action` (also `/v2.1/…`) |
| Quick import (RAW/ZVHD2 ≤ 1 TB) | `POST /v2/cloudimages/quickimport/action` |
| Data disk image variant | `POST /v2.1/cloudimages/dataimages/action` |
| Register (uninitialized image) | `PUT /v1/cloudimages/{image_id}/upload` |
| Export image to OBS | `POST /v1/cloudimages/{image_id}/file` |
| Whole-ECS image | `POST /v1/cloudimages/wholeimages/action` (v2.1 variant exists) |
| List (custom) | `GET /v2/cloudimages` |
| Update | `PATCH /v2/cloudimages/{image_id}` |
| Glance: list / detail / create metadata / upload file / delete | `GET /v2/images`, `GET /v2/images/{id}`, `POST /v2/images`, `PUT /v2/images/{id}/file`, `DELETE /v2/images/{id}` |

### 5.2 Create from OBS file
`POST /v2/cloudimages/action` (also `POST /v2.1/cloudimages/action`, "safe mode" variant):
```json
{ "name": "ims_test_file",                  // 1-128 chars, required
  "description": "…",                        // ≤1024 chars
  "image_url": "ims-image:centos70.qcow2",   // "bucket:key": bucket MUST be Standard class
  "os_version": "CentOS 7.0 64bit",          // required for ISO / quick import
  "min_disk": 40,                            // required; Linux 10-1024, Windows 20-1024
  "tags": ["aaa.111"],                       // or image_tags: [{key, value}] (mutually exclusive)
  "is_quick_import": false,
  "architecture": "x86",                     // x86 (default) | arm
  "hw_firmware_type": "bios" }               // bios | uefi
```
Other scenarios on the same endpoint: from ECS (`instance_id`), from data disk (`volume_id` +
`os_version` + `type` = ECS|BMS|FusionCompute|Ironic). ISO example sends `"type": "IsoImage"`.
→ **200** `{job_id}`; poll the job API; on success `entities.image_id` is the new image id.
Image goes `queued → saving → active`.

### 5.3 Register route (files > 2 GB)
1. Create metadata via Glance `POST /v2/images` (201, status `queued`), keep the image id.
2. `PUT /v1/cloudimages/{image_id}/upload` with `{"image_url": "bucketname:Centos6.5-disk1.vmdk"}`
   → **200** `{job_id}` (job_type `imsNativeImportImageJob`); poll; image status becomes `active`.

### 5.4 Glance-style direct upload (the OBS-bypass route, EMPIRICAL_SPEC §5.2)
- `POST /v2/images` (create metadata) → **201**, status `queued`. Request: `name`, `visibility`
  (only `private`), `protected`, `container_format` (default `bare`), `disk_format`
  (`zvhd2|vhd|raw|iso|qcow2`, default zvhd2), `min_disk`, `min_ram`, `__os_version`, `tags`.
  Response (field-for-field):
```json
{ "schema": "/v2/schemas/image", "min_disk": 100,
  "created_at": "2016-06-02T07:49:48Z", "__image_source_type": "uds",
  "container_format": "bare", "__image_size": "0",
  "file": "/v2/images/4ca46bf1-5c61-48ff-b4f3-0ad4e5e3ba86/file",
  "updated_at": "2016-06-02T07:49:49Z", "protected": false,
  "id": "4ca46bf1-5c61-48ff-b4f3-0ad4e5e3ba86", "__isregistered": "true",
  "min_ram": 1024, "owner": "b912fb4a4c464b568ecfca1071b21b10",
  "__os_type": "Linux", "__imagetype": "private", "visibility": "private",
  "virtual_env_type": "FusionCompute", "tags": ["test=testvalue"],
  "__platform": "Ubuntu", "__os_bit": "64", "__os_version": "Ubuntu 14.04 server 64bit",
  "name": "test", "self": "/v2/images/4ca46bf1-…", "disk_format": "vhd", "status": "queued" }
```
- `PUT /v2/images/{image_id}/file` with the raw body (`application/octet-stream`) → **204 No
  Content** (no body). File must be **< 2 GB**; AK/SK-auth bodies limited to 12 MB (use token
  auth for big uploads). Status: `queued → saving → active` (`killed` on error).
- `GET /v2/images` (Glance list; default `limit` 25, `marker` pagination, rich filters incl.
  `__imagetype` gold/private/shared/market, `status`, `sort_key=created_at`, `sort_dir=desc`) →
  `{schema, first, next?, images: [...]}`. `next` absent on the last page.
- `GET /v2/images/{id}` → single image object.

### 5.5 IMS async job APIs (two flavors, both on the IMS endpoint)
- **`GET /v1/cloudimages/job/{job_id}`** (ShowJobProgress: current):
```json
{ "job_id": "9a175ac89d2a5e14019d2cde77f03a0f", "job_type": "imsImportImageJob",
  "begin_time": "2026-03-27T01:17:50.446Z", "end_time": "2026-03-27T01:57:11.143Z",
  "status": "SUCCESS", "error_code": null, "fail_reason": null,
  "entities": { "image_name": "name", "subJobId": "0825e1f7…",
                "image_id": "698a61e2-abde-4151-a778-f9035e214c92",
                "process_percent": 1, "current_task": "" } }
```
  `status`: SUCCESS | FAIL | RUNNING | INIT; `process_percent` = 1 when complete.
  Job types: `imsCreateImageByInstance`, `imsImportImageJob`, `imsImportOvaImageJob`,
  `imsVolumeCreateImageJob`, `imsImportDataImageJob`, `imsCreateWholeImageByInstanceJob`,
  `imsCreateWholeImageByBackupJob`, `imsNativeImportImageJob`, `imsNativeExportImageJob`, …
- **`GET /v1/{project_id}/jobs/{job_id}`** (ShowJob: deprecated but works on IMS): same shape;
  `entities` may add `results[]` (`{image_id, project_id, status}`), `addition_error_code`.

### 5.6 Whole-ECS image
`POST /v1/cloudimages/wholeimages/action`:
- From ECS: `{name (req), instance_id (req), description?, tags?/image_tags?,
  enterprise_project_id?, max_ram?, min_ram?, vault_id? (CBR vault; required if a CBR backup
  is created)}`.
- From backup: `{name (req), backup_id (req), whole_image_type: "CBR"|…}`.
→ `{job_id}` (job_type `imsCreateWholeImageByInstanceJob`/`…ByBackupJob`).
Docs do NOT require the server stopped for the ECS flow (it creates a backup first): but the
real HCS deployment requires STOPPED (EMPIRICAL_SPEC §2.9; profile-gated).

### 5.7 Image status values
`queued` (metadata created, awaiting file) → `saving` (uploading) → `active` (available);
`deleted`; `killed` (upload error).

---

## 6. VPC / EIP / Security groups / Ports

Sources:
- VPC APIs: https://support.huaweicloud.com/intl/en-us/api-vpc/vpc_api01_0003.html (list),
  vpc_api01_0002 (detail), vpc_api01_0004 (update)
- Subnets: https://support.huaweicloud.com/intl/en-us/api-vpc/vpc_subnet01_0003.html (list),
  vpc_subnet01_0002 (detail), vpc_subnet01_0004 (update)
- API overview: https://support.huaweicloud.com/intl/en-us/api-vpc/en-us_topic_0173364207.html

### 6.1 VPCs
- `GET /v1/{pid}/vpcs` (limit/marker) → `{vpcs: [{id, name, description, cidr,
  status: "CREATING"|"OK", …}]}`; recommended CIDRs 10/8-24, 172.16/12-24, 192.168/16-24.
- `GET /v1/{pid}/vpcs/{id}` → `{vpc: {...}}`; `POST /v1/{pid}/vpcs`; `PUT /v1/{pid}/vpcs/{id}`;
  `DELETE /v1/{pid}/vpcs/{id}` (subnets must be deleted first).

### 6.2 Subnets
- `GET /v1/{pid}/subnets` (limit/marker/vpc_id) → `{subnets: [{id, name, description, cidr,
  gateway_ip, ipv6_enable, cidr_v6, gateway_ip_v6, dhcp_enable, primary_dns, secondary_dns,
  dnsList, availability_zone, vpc_id, status: "ACTIVE", …}]}`.
- Create: `POST /v1/{pid}/subnets`; **update (incl. DNS):**
  `PUT /v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}` with `{subnet: {name, ipv6_enable,
  dhcp_enable, primary_dns, secondary_dns, extraDhcpOpts[{opt_name: ntp|domainname|addresstime,
  opt_value}], …}}`: note the URI nests under the VPC.
- Default `limit` is 2000 for subnets list.

### 6.3 EIP (v1): lives in the Elastic IP API reference (`api-eip`), not the VPC one
- **Create: `POST /v1/{pid}/publicips`** → **200** (not 201!). Request:
```json
{ "publicip": { "type": "5_bgp",              // REQUIRED: 5_bgp | 5_sbgp
                "ip_version": 4,              // 4 | 6
                "ip_address": "161.xx.xx.7",  // optional; assigned if omitted
                "alias": "tom",               // 1-64 chars
                "port_id": "..." },           // optional: bind immediately
  "bandwidth": { "name": "bandwidth123",      // required when share_type=PER
                 "size": 10,                  // 1-300 Mbit/s (region-dependent)
                 "id": "...",                 // shared bandwidth id when share_type=WHOLE
                 "share_type": "PER",         // REQUIRED: PER | WHOLE
                 "charge_mode": "traffic" },  // bandwidth | traffic
  "enterprise_project_id": "0" }
```
  Response is a **minimal** publicip: `PENDING_CREATE` status, `bandwidth_size: 0`, and NO
  `bandwidth_id`/`bandwidth_name`/`bandwidth_share_type`/`port_id`/`private_ip_address` yet:
```json
{ "publicip": { "id": "f588ccfa-8750-4d7c-bf5d-2ede24414706", "alias": "tom",
    "public_border_group": "center", "status": "PENDING_CREATE", "type": "5_bgp",
    "public_ip_address": "161.xx.xx.7", "tenant_id": "8b7e35ad379141fc9df3e178bd64f55c",
    "ip_version": 4, "create_time": "2015-07-16 04:10:52", "bandwidth_size": 0,
    "enterprise_project_id": "…" } }
```
- **Bind/unbind: `PUT /v1/{pid}/publicips/{id}`** with `{publicip: {port_id: "<port>"}}`
  (port_id omitted/empty = unbind) → 200 with the **full** object: `status: "ACTIVE"` when
  bound (`DOWN` unbound), plus `port_id`, `private_ip_address`, `bandwidth_id`,
  `bandwidth_name`, `bandwidth_share_type`, `bandwidth_size`, `profile: {}`.
- **Query:** `GET /v1/{pid}/publicips/{id}` and `GET /v1/{pid}/publicips` (marker/limit 0-2000,
  filters port_id/public_ip_address/private_ip_address/id) → `{publicips: [...]}`.
- **Release:** `DELETE /v1/{pid}/publicips/{id}` → **204**. 409 `VPC.0517` if still bound.
- `status` enum: `FREEZED, BIND_ERROR, BINDING, PENDING_DELETE, PENDING_CREATE, PENDING_UPDATE,
  NOTIFYING, NOTIFY_DELETE, DOWN, ACTIVE, ELB, VPN, ERROR`.
- EIP timestamps use `yyyy-MM-dd HH:mm:ss` (`create_time`): different from VPC's ISO-ish
  `yyyy-MM-ddTHH:mm:ss` (`created_at`/`updated_at`). Encode both faithfully.
- Key error codes: 400 `VPC.0301`/`VPC.0501` (bad bandwidth/params), 404 `VPC.0504` (EIP not
  found), 409 `VPC.0510`/`VPC.0511` (already bound), 409 `VPC.0512` (busy), 409 `VPC.0521`
  (floatingip quota), 409 `VPC.0522` (IP in use).

### 6.4 Security groups (v1, Neutron-style)
- **Create: `POST /v1/{pid}/security-groups`** → **201** with `{security_group: {id, name,
  description, vpc_id, enterprise_project_id, security_group_rules: [...]}}`.
  **Exactly 4 default rules are auto-created**: allow-all egress (IPv4 + IPv6) and
  self-referencing intra-group ingress (IPv4 + IPv6) via `remote_group_id` = own id, all with
  `protocol`, `port_range_min/max`, `remote_ip_prefix` = null.
- **Add rule: `POST /v1/{pid}/security-group-rules`** → **201** with `{security_group_rule:
  {direction: ingress|egress, ethertype: IPv4|IPv6, protocol: tcp|udp|icmp|0-255|<blank=all>,
  port_range_min/max, remote_ip_prefix | remote_group_id | remote_address_group_id
  (mutually exclusive), security_group_id, tenant_id, id, description}}`.
- **Duplicate rule → 409 `VPC.0602`** "Security group rule already exists." (docs code; the
  real cloud was observed returning 409 `SecurityGroupRuleExists`: EMPIRICAL_SPEC §4.5 wins
  for the sim, per profile).
- Query: `GET /v1/{pid}/security-groups` (marker/limit/vpc_id), detail, rules list/detail;
  DELETE → 204.

### 6.5 Ports (v1)
- **`GET /v1/{pid}/ports`**: filters incl. **`device_id`** (the ECS id), `network_id`,
  `fixed_ips=ip_address={ip}` / `fixed_ips=subnet_id={id}`, `status`, marker/limit →
```json
{ "ports": [ { "id": "d00f9c13-…", "name": "test", "status": "DOWN",
    "admin_state_up": true,
    "fixed_ips": [ { "subnet_id": "70f2e74e-…", "ip_address": "10.128.1.10" } ],
    "dns_name": "", "mac_address": "fa:16:3e:d7:f2:6c",
    "network_id": "5b808927-…", "tenant_id": "43f2d1cc…",
    "device_id": "", "device_owner": "", "security_groups": ["02b4e8ee-…"],
    "extra_dhcp_opts": [], "allowed_address_pairs": [],
    "binding:vnic_type": "normal", "enable_efi": false } ] }
```
  `device_owner` for an ECS NIC = `compute:{AZ}`; subnet gateway =
  `network:router_interface_distributed`.
- POST ports → 201; DELETE → 204. Errors: 400 `VPC.2500`, 404 `VPC.2502`, 409 `VPC.0701`.

---

## 7. OBS (S3-compatible, v2-signed)

Sources: OBS API Reference: list buckets obs_04_0020, create bucket obs_04_0021, list objects
obs_04_0022, HEAD bucket obs_04_0023, bucket location obs_04_0024, delete bucket obs_04_0025,
PUT object obs_04_0080, GET object obs_04_0083, HEAD object obs_04_0084, DELETE object
obs_04_0085, error overview obs_04_0115, SignatureDoesNotMatch obs_errorcode_0013,
NoSuchBucket obs_errorcode_0020, NoSuchKey obs_errorcode_0025, status codes obs_04_0114
(all under https://support.huaweicloud.com/intl/en-us/api-obs/).

### 7.1 Protocol conventions
- Virtual-host style: `bucket.obs.<region>.myhuaweicloud.com`; global endpoint
  `obs.myhuaweicloud.com`. Bucket ops hit `/`; object ops hit `/{key}` (URL-encoded).
- All XML bodies: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` + root element with
  namespace `xmlns="http://obs.<region>.myhuaweicloud.com/doc/2015-06-30/"`.
- Every response carries `Server: OBS`, `x-obs-request-id` (32 uppercase hex, e.g.
  `BF260000016435722C11379647A8A00A`), `x-obs-id-2` (opaque base64-ish, usually starts
  `32AAAQ…`). XML responses: `Content-Type: application/xml`.
- Date formats: HTTP `Date`/`Last-Modified` = RFC 1123 GMT; XML timestamps = ISO8601 UTC with
  milliseconds (`2015-07-01T00:32:16.482Z`).
- ETags = **quoted lowercase hex MD5** (`"d41d8cd98f00b204e9800998ecf8427e"`) in headers and
  list XML alike.
- Default `Content-Type` for uploaded objects: `binary/octet-stream`.
- Storage classes: `STANDARD` (default) | `WARM` | `COLD` | `DEEP_ARCHIVE`.

### 7.2 Listing buckets: `GET /` on the service endpoint
Lists buckets **across all regions** regardless of which regional endpoint is used.
Optional header `x-obs-bucket-type: OBJECT|POSIX`. Response 200:
```xml
<ListAllMyBucketsResult xmlns="http://obs.<region>.myhuaweicloud.com/doc/2015-06-30/">
  <Owner><ID>783fc6652cf246c096ea836694f71855</ID></Owner>   <!-- domain id -->
  <Buckets>
    <Bucket>
      <Name>examplebucket01</Name>
      <CreationDate>2018-06-21T09:15:01.032Z</CreationDate>
      <Location>region</Location>
      <BucketType>OBJECT</BucketType>
    </Bucket>
  </Buckets>
</ListAllMyBucketsResult>
```

### 7.3 Creating a bucket: `PUT /` on the bucket host
- Request headers: `x-obs-acl` (private|public-read|public-read-write|public-read-delivered|
  public-read-write-delivered|bucket-owner-full-control), `x-obs-storage-class`, grant headers
  (`x-obs-grant-read` etc., `id=<tenant-id>` comma-separated), `x-obs-epid`, SSE headers.
- Optional body `CreateBucketConfiguration → Location`; on a regional endpoint, Location must
  equal that endpoint's region (else 400 `InvalidLocationConstraint` /
  `IllegalLocationConstraintException`).
- Response **200, no body**, header `Location: /<bucket-name>`.
- Errors: 409 `BucketAlreadyExists` (globally unique namespace), 409 `BucketAlreadyOwnedByYou`,
  400 `InvalidBucketName`. Max **100 buckets/account** (matches EMPIRICAL_SPEC §6.3 quota);
  deleted names release after ~30 min. Same-name re-create in the same region is idempotent.
- Bucket naming: 3-63 chars, lowercase letters/digits/hyphens/periods, start with digit/letter,
  no IP-format, no leading/trailing `-`/`.`, no `..`, no `.-`/`-.` adjacency.

### 7.4 Listing objects: `GET /?prefix&marker&max-keys&delimiter` on the bucket host
- Query params: `prefix` (1-1024), `marker` (**exclusive** lexicographic start), `max-keys`
  (1-1000, clamped, default 1000), `delimiter` (rolls up into `CommonPrefixes`, which count
  toward the 1000 limit), `encoding-type=url`, versioned variant `?versions` with
  `key-marker`/`version-id-marker`.
- Response 200 (+ header `x-obs-bucket-location: <region>`):
```xml
<ListBucketResult xmlns="http://obs.<region>.myhuaweicloud.com/doc/2015-06-30/">
  <Name>examplebucket</Name>
  <Prefix>obj</Prefix>
  <Marker>obj001</Marker>
  <MaxKeys>1000</MaxKeys>
  <IsTruncated>false</IsTruncated>
  <!-- NextMarker only when IsTruncated=true: last key of this page -->
  <Contents>
    <Key>obj002</Key>
    <LastModified>2015-07-01T02:11:19.775Z</LastModified>
    <ETag>"a72e382246ac83e86bd203389849e71d"</ETag>
    <Size>9</Size>
    <Owner><ID>b4bf1b36d9ca43d984fbcb9491b6fce9</ID><DisplayName>ObjectOwnerName</DisplayName></Owner>
    <StorageClass>STANDARD</StorageClass>
  </Contents>
  <!-- CommonPrefixes → Prefix (when delimiter used) -->
</ListBucketResult>
```
- Element order: `Name, Prefix, Marker, MaxKeys, [Delimiter], IsTruncated, [NextMarker],
  Contents*, CommonPrefixes*`. `Type` (`NORMAL|APPENDABLE|SYMLINK`) only when not NORMAL.
- Pagination: loop while `IsTruncated=true`, feed `NextMarker` as `marker`. No page-number
  listing; lexicographic order only.

### 7.5 Object operations
- **PUT `/{key}`** (≤ 5 GB; overwrite unless versioned): optional `Content-MD5` (base64;
  mismatch → 400 `BadDigest`), `x-obs-meta-*` user metadata, `x-obs-storage-class`,
  `x-obs-acl`, SSE headers, `x-obs-persistent-headers` (custom response headers).
  → **200, no body**, `ETag: "<md5>"` header.
- **GET `/{key}`**: `Range` support (malformed ranges ignored; start beyond length → 416
  `InvalidRange`), conditional requests (`If-Match`/`If-None-Match`/`If-Modified-Since`/
  `If-Unmodified-Since` → 304/412 `PreconditionFailed`), `?attname=` download rename,
  `?response-content-type=` etc. overrides (anonymous + overrides → 400
  `ForbidAnonReqOverwriteRespHead`). → **200** with body; headers `Accept-Ranges: bytes`,
  `ETag`, `Last-Modified`, `Content-Type`, `Content-Length`, stored `x-obs-meta-*`.
  Missing key → **404 `NoSuchKey`**; missing bucket → 404 `NoSuchBucket`.
- **HEAD `/{key}`**: metadata only, no body.
- **DELETE `/{key}`** → **204 No Content**; deleting a non-existent object **still 204**.

### 7.6 OBS error responses (XML)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>NoSuchKey</Code>
  <Message>The resource you requested does not exist</Message>
  <RequestId>001B21A61C6C0000013402C4616D5285</RequestId>
  <HostId>RkRCRDJENDc5MzdGQkQ4OUY3MTI4NTQ3NDk2Mjg0M0FB</HostId>
  <BucketName>BucketName</BucketName>   <!-- bucket ops -->
  <Key>ObjectName</Key>                 <!-- object ops -->
</Error>
```
- `SignatureDoesNotMatch` (403) carries EXTRA elements: `AccessKeyId`, `SignatureProvided`,
  `StringToSign`, `StringToSignBytes`: invaluable for debugging client signing against the sim.
- Key codes: 403 `AccessDenied`/`SignatureDoesNotMatch`/`InvalidAccessKeyId`/
  `RequestTimeTooSkewed`; 404 `NoSuchBucket`/`NoSuchKey`/`NoSuchUpload`/`NoSuchVersion`;
  409 `BucketAlreadyExists`/`BucketAlreadyOwnedByYou`/`BucketNotEmpty`; 400 `InvalidArgument`/
  `InvalidBucketName`/`BadDigest`/`EntityTooLarge`/`IncompleteBody`; 416 `InvalidRange`;
  429 `TooManyRequests`; 500 `InternalError`; 503 `ServiceUnavailable`/`SlowDown`.
- Throttling response header: `x-obs-qos-delay-time`.

---

## 8. Error body formats: PER SERVICE (critical for fidelity)

Sources: API-signing error codes https://support.huaweicloud.com/intl/en-us/devg-apisign/api-sign-errorcode.html
and https://support.huaweicloud.com/intl/en-us/devg-apisign/api-sign-0001.html; ECS appendix
https://support.huaweicloud.com/intl/en-us/api-ecs/ecs_07_0002.html; EVS appendix
https://support.huaweicloud.com/intl/en-us/api-evs/evs_04_0038.html; VPC
https://support.huaweicloud.com/intl/en-us/api-vpc/vpc_api_0003.html; EIP
https://support.huaweicloud.com/intl/en-us/api-eip/ErrorCode.html.

| Service / layer | Error body shape | Notes |
|---|---|---|
| **API Gateway (APIGW.*)** | flat: `{"error_msg": "...", "error_code": "APIGW.XXXX", "request_id": "..."}` | shared gateway in front of all services |
| **ECS** (Ecs.*, Common.*, Pdp.*) | nested: `{"error": {"code": "...", "message": "...", "details": [{"code","message"}]?}}` | incl. all job-returning APIs |
| **EVS native v2** (EVS.*, Common.*) | nested: `{"error": {"message": "...", "code": "..."}}` | doc examples put message first |
| **EVS legacy Cinder** (`/v2/{pid}/volumes*`) | OpenStack wrapper: `{"badRequest"\|"itemNotFound": {"message": "...", "code": "..."}}` | key = error class |
| **VPC v1 + EIP v1** | flat: `{"code": "VPC.xxxx", "message": "..."}` | NOT error_code/error_msg! |
| **OBS** | XML error document | exact format in §7.6 |
| **IMS** | job failures surface in the job object (`error_code` + `fail_reason`) | |

### 8.1 API Gateway codes (the auth/throttle layer every request passes through)
| Code | HTTP | Message |
|---|---|---|
| `APIGW.0101` | 404 | The API does not exist or has not been published in the environment. |
| `APIGW.0201` | 413 | Request entity too large. (body > 12 MB) |
| **`APIGW.0301`** | **401** | **Incorrect IAM authentication information.**: suffixed with a cause: `verify aksk signature fail`, `decrypt token fail`, `Get secretKey failed,ak:******,err:ak not exist`, `AK access failed to reach the limit,forbidden.`, `current ip:xx.xx.xx.xx refused` |
| `APIGW.0302` | 403 | The IAM user is not authorized to access the API. |
| `APIGW.0305` | 401 | Incorrect authentication information. |
| `APIGW.0307` | 401 | The token must be updated. |
| **`APIGW.0308`** | **429** | **The throttling threshold has been reached.** (default ~200 calls/s per API) |

**Important interpretation for the simulator:** EMPIRICAL_SPEC §1.3 observed rapid scripted
calls → 401/403 with `APIGW.0301`. That matches this table: under rapid calling the gateway
starts failing AK lookups (`AK access failed to reach the limit,forbidden.` → 401 APIGW.0301),
and a 30 s backoff clears it. So the rate-limit emulation should emit **APIGW.0301/401** with
the `AK access failed to reach the limit,forbidden.` suffix (matching observation), while a
pure throttling response would be APIGW.0308/429. Implement both, configurable.

### 8.2 ECS codes (appendix highlights)
| Code | HTTP | Documented message |
|---|---|---|
| `Ecs.0001` | 400 | Insufficient ECS quota |
| **`Ecs.0005`** | **400** | Invalid parameter values / Invalid request body: the generic invalid-parameter code. The observed variant `"device is illegal"` (non-bootable volume at /dev/vda, EMPIRICAL_SPEC §2.6) is a real-world message under this code; docs note one code maps to many messages. |
| `Ecs.0011` | 400 | Password complexity not met |
| **`Ecs.0100`** | **400** | The ECS status does not meet requirements…: observed variant `"server does not support reset password"` (EMPIRICAL_SPEC §2.7). Documented reset-password codes: Ecs.0610/0611/0613. |
| `Ecs.0114`/`Ecs.0614` | 404 | The ECS does not exist |
| `Ecs.0605` | 400 | ECS locked |
| `Common.0002` | 400 | The request body cannot be left blank |
| `Common.0011` | 400 | Invalid job ID / failed to query system tasks |
| `Common.0013` | 401 | Invalid token |
| `Common.0024` | 202 | Flow limit exceeded |
| `Common.1503` | 429 | API flow control error because %s. |
| `Pdp.0001` | 403 | Policy does not allow %s to be performed. |

Example bodies (documented):
```json
{ "error": { "code": "Ecs.0005", "message": "request body is illegal." } }
{ "error": { "message": "privateIp [192.168.12.1] is not in this subnet […]", "code": "Ecs.0005",
             "details": [ { "code": "Ecs.0039" } ] } }
```

### 8.3 EVS codes (appendix highlights)
| Code | HTTP | Message |
|---|---|---|
| `EVS.0001` | 400 | invalid tenant id! |
| `EVS.1002` | 400 | invalid volume id! |
| `EVS.1010` | 400 | invalid volume size! |
| `EVS.1046` | 400 | volume status must be available… when delete volume! |
| `EVS.1027` | 403 | user role is not allowed for this action! |
| `EVS.5400` | 400 | Malformed request body. |
| `EVS.5401` | 401 | Authentication required. |
| `EVS.5403` | 403 | Policy check failed. |
| `EVS.5404` | 404 | Resource(Volume, Snapshot, Backup .etc) cound not be found. (sic) |
| `EVS.5413` | 413 | Insufficient volume quota. |
| `EVS.5500` | 500 | Internal server error. |
| `Common.0011` | 400 | query job fail. / No jobs found. |

EVS status codes add OpenStack flavors: 413 `overLimit`, 415 `badMediaType`.

### 8.4 Async job failures
Failed async jobs are reported by the **job query**, not the submission:
`GET /v1/{pid}/jobs/{job_id}` → `"status": "FAIL"` with `error_code` + `fail_reason`
populated (null on success); sub-jobs carry `entities.errorcode_message`. The submission call
itself only fails synchronously for validation errors (nested error body above).
Batch async APIs use `{"response": [{"id": …}]}` with per-item error entries
(ecs_07_0009.html).

**The simulator must pick the right envelope per service, not a global one.**

---

## 9. Endpoints & addressing model

- Pattern: `https://<service>.<region>.myhuaweicloud.com` (e.g.
  `ecs.ap-southeast-1.myhuaweicloud.com`, `evs.tr-west-1.myhuaweicloud.com`).
- IAM: `iam.myhuaweicloud.com` (global) + `iam.<region>.myhuaweicloud.com`.
- OBS: virtual-host style `bucket.obs.<region>.myhuaweicloud.com`; the bucket name is part of
  the Host header and the CanonicalizedResource.
- SDKs accept arbitrary endpoints via `new Region(name, url)`: the wiring mechanism for the
  simulator (EMPIRICAL_SPEC §1.5): clients pass `Region("sim", "http://127.0.0.1:<port>")`.
- Project scoping: `X-Project-Id` header on project-scoped calls; `{project_id}` path segment
  in most URIs. One project per region.
- HCS-style regions resolve via the **cn-north-4** IAM endpoint with GlobalCredentials
  (EMPIRICAL_SPEC §1.2: keep this behavior in the `hcs` quirk profile).

---

## 10. Status-code nuances worth encoding

- `POST /v1/{pid}/publicips` → **200**; but `POST /v1/{pid}/security-groups`,
  `security-group-rules`, `ports` → **201** (Neutron-native). VPC v3 pre-check → 202.
- DELETEs → **204** with no body (VPC/EIP/SG/port/EVS volume).
- Async submissions (ECS create/delete/actions, EVS v2.1 create, IMS) → **200 or 202** with
  `{job_id}`.
- EVS snapshot create → **202** with the snapshot object (status `creating`).
- Glance `POST /v2/images` → **201**; `PUT /v2/images/{id}/file` → **204**.
- Normal ECS returned values: 200/201/202/204; abnormal 300-504.

## 11. Open items / to verify against real captures

- Whether ECS `addresses` is keyed by VPC name or VPC id per profile (spec says name in tr-west-1).
- HCS sparse fields in ECS list view (flavor/az missing: EMPIRICAL_SPEC §2.8).
- EVS create-response anomaly (id not under `volume.id` in HCS: EMPIRICAL_SPEC §3.3) has no
  documented counterpart; profile-gated.
- The exact 409 code string for duplicate SG rules: docs say `VPC.0602`, observation says
  `SecurityGroupRuleExists`: encode the observed one per profile, keep both in the table.
- OBS list-params signing: docs confirm `prefix`/`max-keys`/`marker` are NOT signed
  sub-resources (§1.2): matches observation; no open question.
- IMS whole-image: docs allow running servers (backup-based), HCS observation requires STOPPED
  (EMPIRICAL_SPEC §2.9): profile-gated.
