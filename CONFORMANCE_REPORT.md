# API conformance report

**120/120 checks conformant.** Every implemented endpoint tested with real signed requests; shapes validated against the documented examples and the official SDK model wire keys.

## How "matching the real API" was verified

Each endpoint was exercised with a real signed request (SDK-HMAC-SHA256 for REST,
OBS v2 for the object service) and validated on three levels:

1. **Status code** - against the documented expectation (200/201/202/204/400/404/409).
2. **Documented shape** - required/forbidden response fields per the official doc
   examples captured in `API_DOCS_RESEARCH.md`.
3. **SDK wire-key cross-validation** - the `@huaweicloud` SDK model classes are
   generated from Huawei's official API definitions, so their field names ARE the
   real wire contract. The suite extracts every wire key from the SDK model sources
   (`ServerDetail`, `ShowJobResponse`, `VolumeDetailForTag`, `PublicipShowResp`,
   `Vpc`, `Subnet`, `SecurityGroup`, `SecurityGroupRule`,
   `GlanceCreateImageMetadataResponse`, `JobProgressEntities`) and checks the
   simulator's objects against them.

## Real-API mismatches the suite found (and were fixed)

The first run scored **66/99**. Eight genuine wire-format mismatches were fixed:

| # | Endpoint | Mismatch vs real API | Fix |
|---|---|---|---|
| 1 | ECS server object | field emitted as `availability_zone`; the real wire name is **`OS-EXT-AZ:availability_zone`** | serde rename in `common/src/model.rs` |
| 2 | IAM `POST /v3/auth/tokens` | body lacked the wrapping **`token`** object | wrapped in `iam/src/lib.rs` |
| 3 | EVS volume detail | missing **`volume_type`** and **`shareable`** (SDK `VolumeDetailForTag`) | added to `Volume::to_detail` |
| 4 | VPC `vpcs` | missing **`tenant_id`** (SDK `Vpc`) | added (+ `enterprise_project_id`) |
| 5 | VPC `subnets` | missing **`tenant_id`** (SDK `Subnet`) | added (+ `available_ip_address_count`, `extra_dhcp_opts`, neutron ids) |
| 6 | IMS Glance image | missing **`checksum`**, **`size`**, **`virtual_size`** | added (+ `properties`, `__root_origin`) |
| 7 | EIP full object | missing `public_border_group` and `tags` | added to `Eip::to_json` |
| 8 | EVS `GET /v2/{pid}/cloudvolumes/detail` | missing **`count`** (SDK `ListVolumesResponse`) | added |

The remaining first-run failures were suite bugs (array-path validation, swapped
dry_run expectations, a missing delimiter fixture) - corrected in the suite, no
simulator change.

Note: the suite runs against a server with `SIM_RATE_LIMIT=1000`; its request
bursts legitimately trip the default 100/10s throttle (observed behavior, covered
by the dedicated `--rate` test).

## Coverage per service (this run)

## IAM: 3/3

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `GET` | `KeystoneListProjects` | 200 | 200 |  |
| ✅ | `GET` | `KeystoneListAuthProjects` | 200 | 200 |  |
| ✅ | `POST` | `KeystoneCreateUserTokenByPassword` | 201 + X-Subject-Token + catalog | 201 + hdr=yes |  |

## ECS: 26/26

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `GET` | `ListServersDetails (v1)` | 200 | 200 |  |
| ✅ | `GET` | `ListCloudServers (v1.1)` | 200 | 200 |  |
| ✅ | `GET` | `ShowServer` | 200 | 200 |  |
| ✅ | `SHAPE` | `ServerDetail vs SDK` | must-have present | ok | SDK wire-key coverage: 30/53 |
| ✅ | `PUT` | `UpdateServer (rename)` | 200 | 200 |  |
| ✅ | `POST` | `CreateServers (v1.1)` | 200 | 200 |  |
| ✅ | `POST` | `CreateServers (v1 prepaid)` | 200 | 200 |  |
| ✅ | `POST` | `CreateServers dry_run` | 202 | 202 |  |
| ✅ | `POST` | `DeleteServers` | 404 | 404 |  |
| ✅ | `POST` | `BatchStopServers` | 200 | 200 |  |
| ✅ | `GET` | `ListFlavors (public)` | 200 | 200 |  |
| ✅ | `GET` | `ListFlavors (hcs -> 404)` | 404 | 404 |  |
| ✅ | `GET` | `ShowJob` | 200 | 200 |  |
| ✅ | `SHAPE` | `ShowJobResponse vs SDK` | must-have present | ok | SDK wire-key coverage: 8/10 |
| ✅ | `GET` | `NovaListServers (brief)` | 200 | 200 |  |
| ✅ | `GET` | `NovaListServersDetails` | 200 | 200 |  |
| ✅ | `DELETE` | `DetachServerVolume` | 200 | 200 |  |
| ✅ | `POST` | `AttachServerVolume` | 200 | 200 |  |
| ✅ | `POST` | `AttachServerVolume dry_run (in-use volume -> 400)` | 400 | 400 |  |
| ✅ | `POST` | `AttachServerVolume dry_run (available volume -> 202)` | 202 | 202 |  |
| ✅ | `GET` | `ListServerBlockDevices` | 200 | 200 |  |
| ✅ | `GET` | `ShowServerBlockDevice` | 200 | 200 |  |
| ✅ | `GET` | `ListServerVolumeAttachments` | 200 | 200 |  |
| ✅ | `DELETE` | `DetachServerVolume` | 200 | 200 |  |
| ✅ | `GET` | `ShowServerResetPwdFlag` | 200 | 200 |  |
| ✅ | `PUT` | `ResetServerPassword` | 200 | 200 |  |

## EVS: 18/18

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `POST` | `CreateVolume (v2.1)` | 202 | 202 |  |
| ✅ | `POST` | `CreateVolume (v2)` | 202 | 202 |  |
| ✅ | `POST` | `CreateVolume (Cinder)` | 202 | 202 |  |
| ✅ | `GET` | `ListVolumes (sparse)` | 200 | 200 |  |
| ✅ | `GET` | `ListVolumesDetail (v2)` | 200 | 200 |  |
| ✅ | `GET` | `ListVolumesDetail (v2.1, public)` | 200 | 200 |  |
| ✅ | `GET` | `ListVolumesDetail (v2.1, hcs -> EMPTY)` | 200 | 200 |  |
| ✅ | `GET` | `ShowVolume` | 200 | 200 |  |
| ✅ | `SHAPE` | `VolumeDetail vs SDK` | must-have present | ok | SDK wire-key coverage: 27/33 |
| ✅ | `GET` | `os-vendor ListVolumesDetail` | 200 | 200 |  |
| ✅ | `GET` | `os-vendor ShowVolume` | 200 | 200 |  |
| ✅ | `PUT` | `UpdateVolume` | 200 | 200 |  |
| ✅ | `DELETE` | `DeleteVolume (in-use -> EVS.1046)` | 400 | 400 |  |
| ✅ | `POST` | `ExtendVolume` | 202 | 202 |  |
| ✅ | `POST` | `CreateSnapshot (in-use -> 400)` | 400 | 400 |  |
| ✅ | `GET` | `ListSnapshotsDetail` | 200 | 200 |  |
| ✅ | `GET` | `ShowSnapshot (404)` | 404 | 404 |  |
| ✅ | `POST` | `RollbackSnapshot (404)` | 404 | 404 |  |

## VPC: 21/21

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `GET` | `ListVpcs` | 200 | 200 |  |
| ✅ | `SHAPE` | `Vpc vs SDK` | must-have present | ok | SDK wire-key coverage: 9/12 |
| ✅ | `GET` | `ShowVpc` | 200 | 200 |  |
| ✅ | `POST` | `CreateVpc` | 200 | 200 |  |
| ✅ | `GET` | `ListSubnets` | 200 | 200 |  |
| ✅ | `SHAPE` | `Subnet vs SDK` | must-have present | ok | SDK wire-key coverage: 20/25 |
| ✅ | `GET` | `ShowSubnet` | 200 | 200 |  |
| ✅ | `POST` | `CreateSubnet` | 200 | 200 |  |
| ✅ | `PUT` | `UpdateSubnet (DNS route)` | 200 | 200 |  |
| ✅ | `GET` | `ListPublicips` | 200 | 200 |  |
| ✅ | `SHAPE` | `Publicip vs SDK` | must-have present | ok | SDK wire-key coverage: 16/20 |
| ✅ | `GET` | `ShowPublicip` | 200 | 200 |  |
| ✅ | `PUT` | `UpdatePublicip (unbind)` | 200 | 200 |  |
| ✅ | `GET` | `ListPorts (device_id filter)` | 200 | 200 |  |
| ✅ | `GET` | `ListSecurityGroups` | 200 | 200 |  |
| ✅ | `SHAPE` | `SecurityGroup vs SDK` | must-have present | ok | SDK wire-key coverage: 6/6 |
| ✅ | `GET` | `ShowSecurityGroup` | 200 | 200 |  |
| ✅ | `POST` | `CreateSecurityGroupRule (duplicate -> 409)` | 409 | 409 |  |
| ✅ | `GET` | `ListSecurityGroupRules` | 200 | 200 |  |
| ✅ | `SHAPE` | `SecurityGroupRule vs SDK` | must-have present | ok | SDK wire-key coverage: 12/12 |
| ✅ | `GET` | `ShowSecurityGroupRule` | 200 | 200 |  |

## IMS: 14/14

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `POST` | `CreateImage (OBS-file)` | 200 | 200 |  |
| ✅ | `POST` | `CreateImage (v2.1)` | 200 | 200 |  |
| ✅ | `POST` | `QuickImport` | 200 | 200 |  |
| ✅ | `POST` | `CreateWholeImage (running on hcs -> 400)` | 400 | 400 |  |
| ✅ | `POST` | `RegisterImage` | 400 | 400 |  |
| ✅ | `POST` | `GlanceCreateImageMetadata` | 201 | 201 |  |
| ✅ | `SHAPE` | `Glance image vs SDK` | must-have present | ok | SDK wire-key coverage: 30/30 |
| ✅ | `PUT` | `GlanceUploadImageFile` | 204 | 204 |  |
| ✅ | `GET` | `GlanceListImages` | 200 | 200 |  |
| ✅ | `GET` | `GlanceShowImage` | 200 | 200 |  |
| ✅ | `DELETE` | `GlanceDeleteImage` | 204 | 204 |  |
| ✅ | `GET` | `ListImages (custom)` | 200 | 200 |  |
| ✅ | `GET` | `ShowJobProgress` | 200 | 200 |  |
| ✅ | `SHAPE` | `JobProgressEntities vs SDK` | must-have present | ok | SDK wire-key coverage: 4/7 |

## OBS: 17/17

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `GET` | `ListBuckets` | 200 | 200 |  |
| ✅ | `PUT` | `CreateBucket (exists -> 409)` | 409 | 409 |  |
| ✅ | `HEAD` | `HeadBucket` | 200 | 200 |  |
| ✅ | `GET` | `GetBucketLocation` | 200 | 200 |  |
| ✅ | `GET` | `ListObjects (prefix)` | 200 | 200 |  |
| ✅ | `GET` | `ListObjects (delimiter rollup)` | 200 | 200 |  |
| ✅ | `GET` | `GetObject` | 200 | 200 |  |
| ✅ | `GET` | `GetObject byte-identical + ETag` | 200 + quoted md5 | 200 etag="5d41402abc4b2a76b9719d911017c592" |  |
| ✅ | `HEAD` | `HeadObject` | 200 | 200 |  |
| ✅ | `GET` | `GetObject (missing -> NoSuchKey XML)` | 404 | 404 |  |
| ✅ | `DELETE` | `DeleteObject (missing -> 204)` | 204 | 204 |  |
| ✅ | `DELETE` | `DeleteBucket (non-empty -> 409)` | 409 | 409 |  |
| ✅ | `POST` | `InitiateMultipartUpload` | 200 | 200 |  |
| ✅ | `PUT` | `UploadPart` | 200 | 200 |  |
| ✅ | `GET` | `ListParts` | 200 | 200 |  |
| ✅ | `POST` | `CompleteMultipartUpload` | 200 | 200 |  |
| ✅ | `DELETE` | `DeleteObject mp` | 204 | 204 |  |

## CBR: 21/21

| Result | Method | Endpoint / model | Expected | Got | Notes |
|---|---|---|---|---|---|
| ✅ | `POST` | `CreateVault` | 200 | 200 |  |
| ✅ | `SHAPE` | `Vault vs SDK` | must-have present | ok | SDK wire-key coverage: 18/19 |
| ✅ | `GET` | `ListVaults` | 200 | 200 |  |
| ✅ | `GET` | `ShowVault` | 200 | 200 |  |
| ✅ | `PUT` | `UpdateVault` | 200 | 200 |  |
| ✅ | `POST` | `AddVaultResource` | 200 | 200 |  |
| ✅ | `POST` | `CreatePolicy` | 200 | 200 |  |
| ✅ | `GET` | `ListPolicies` | 200 | 200 |  |
| ✅ | `GET` | `ShowPolicy` | 200 | 200 |  |
| ✅ | `DELETE` | `DeletePolicy` | 204 | 204 |  |
| ✅ | `POST` | `CreateCheckpoint` | 200 | 200 |  |
| ✅ | `GET` | `ShowCheckpoint` | 200 | 200 |  |
| ✅ | `GET` | `ListBackups` | 200 | 200 |  |
| ✅ | `SHAPE` | `BackupResp vs SDK` | must-have present | ok | SDK wire-key coverage: 26/26 |
| ✅ | `GET` | `ShowBackup` | 200 | 200 |  |
| ✅ | `POST` | `AddVaultResource (volume)` | 200 | 200 |  |
| ✅ | `POST` | `CreateCheckpoint (volume)` | 200 | 200 |  |
| ✅ | `GET` | `ListBackups (volume)` | 200 | 200 |  |
| ✅ | `POST` | `RestoreBackup` | 200 | 200 |  |
| ✅ | `DELETE` | `DeleteBackup` | 204 | 204 |  |
| ✅ | `DELETE` | `DeleteVault` | 204 | 204 |  |
