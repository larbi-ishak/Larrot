<div align="center">

<p>
  <img src="https://raw.githubusercontent.com/larbi-ishak/Larrot/main/docs/larrot-logo-red.png" alt="Larrot" width="160">
</p>

# Larrot 🦜

**Larrot repeats Huawei Cloud.**

*A local Huawei Cloud API simulator: LocalStack, but for Huawei Cloud.*

[![CI](https://github.com/larbi-ishak/Larrot/actions/workflows/ci.yml/badge.svg)](../../actions)

</div>

---

> Larrot is an independent, community-developed open-source project.
> It is not affiliated with, endorsed by, or sponsored by Huawei Technologies.

Larrot is a parrot. It listens to Huawei Cloud and repeats the parts it
implements: endpoints, per-service error envelopes, async jobs, and the
production quirks we observed and documented in
[docs/EMPIRICAL_SPEC.md](docs/EMPIRICAL_SPEC.md)
(*yes, including `Ecs.0005 "device is illegal"`*).

How faithful is it? Measured, not claimed: **72/72 conformance checks green
across 15 core services**, 339 unit/integration tests, 130 negative tests,
and the example below runs unmodified against the official
`huaweicloudsdk*` Python SDKs. Full numbers:
**[CONFORMANCE_REPORT.md](CONFORMANCE_REPORT.md)**,
**[COVERAGE.md](COVERAGE.md)** (operation-level: 642/642 documented
operations across all 59 services), and
**[ROADMAP.md](ROADMAP.md)**.

It runs the REST APIs of Huawei Cloud's international site
(`*.myhuaweicloud.com`) on your machine: **59 services** on ports
8200/8201. See [CATALOG.md](CATALOG.md) for the full list grouped by
category, and [Known limitations](#known-limitations) for what is shallow
or missing.

## Quick start

```bash
# Install
pip install larrot

# Run
larrot-server
# → REST on http://127.0.0.1:8200, OBS on http://127.0.0.1:8201

# Or with Docker
docker compose up

# Or from source
pip install -e .
python -m larrot
```

## CLI

```bash
larrot projects
larrot ecs list
larrot --wait ecs create --image <id> --flavor s6.large.2 --name myvm
larrot --wait ecs stop <server-id>
larrot evs list
larrot cbr vaults
larrot obs buckets
larrot --json ecs list
```

## End-to-end with the official SDKs

This example runs **unmodified** against Larrot using the official
`huaweicloudsdk*` packages (validated output below):

```python
import time
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import (VpcClient, CreateVpcRequest,
                                  CreateVpcRequestBody, CreateVpcOption)
from huaweicloudsdkevs.v2 import (EvsClient, CreateVolumeRequest,
                                  CreateVolumeRequestBody, CreateVolumeOption,
                                  ShowVolumeRequest)
from huaweicloudsdkecs.v2 import (EcsClient, CreatePostPaidServersRequest,
                                  CreatePostPaidServersRequestBody, PostPaidServer,
                                  ShowJobRequest, ShowServerRequest)

ENDPOINT = "http://127.0.0.1:8200"
credentials = BasicCredentials().with_ak("HWYSIMAK00000001") \
    .with_sk("HWYSIMSK00000001") \
    .with_project_id("79814d675f6142d9b4a8ee417b924444")
vpc_client = VpcClient.new_builder().with_credentials(credentials).with_endpoint(ENDPOINT).build()
evs_client = EvsClient.new_builder().with_credentials(credentials).with_endpoint(ENDPOINT).build()
ecs_client = EcsClient.new_builder().with_credentials(credentials).with_endpoint(ENDPOINT).build()

# 1. Create a VPC
vpc = vpc_client.create_vpc(CreateVpcRequest(
    body=CreateVpcRequestBody(vpc=CreateVpcOption(name="demo-vpc", cidr="192.168.0.0/16"))
)).vpc
print(f"1. VPC created:   {vpc.id}  ({vpc.name}, {vpc.cidr})")

# 2. Create a volume (async: returns job_id + volume_ids)
vol_resp = evs_client.create_volume(CreateVolumeRequest(
    body=CreateVolumeRequestBody(volume=CreateVolumeOption(size=10, name="demo-vol"))
))
while ecs_client.show_job(ShowJobRequest(job_id=vol_resp.job_id)).status != "SUCCESS":
    time.sleep(0.5)
vol = evs_client.show_volume(ShowVolumeRequest(volume_id=vol_resp.volume_ids[0])).volume
print(f"2. Volume ready:  {vol.name}, {vol.size} GB, status={vol.status}")

# 3. Create an ECS instance (async: returns a job)
resp = ecs_client.create_post_paid_servers(CreatePostPaidServersRequest(
    body=CreatePostPaidServersRequestBody(server=PostPaidServer(
        image_ref="1ce5800a-e487-4c1b-b264-3353a39e2b4b",
        flavor_ref="s6.large.2", name="demo-vm"))))
while ecs_client.show_job(ShowJobRequest(job_id=resp.job_id)).status != "SUCCESS":
    time.sleep(0.5)

# 4. Show the server
server = ecs_client.show_server(ShowServerRequest(server_id=resp.server_ids[0])).server
print(f"3. Server ready:  {server.name}  status={server.status}  flavor={server.flavor.id}")
```

Actual output against a running Larrot:

```
1. VPC created:   a5447b0b-a64a-48b7-af4f-b05b86ed8834  (demo-vpc, 192.168.0.0/16)
2. Volume ready:  demo-vol, 10 GB, status=available
3. Server ready:  demo-vm  status=ACTIVE  flavor=s6.large.2
```

Your existing SDK scripts run unchanged: point the endpoint at Larrot and go.

## Services

**59 distinct Huawei Cloud services** across 71 router modules.
Full catalog grouped by category: **[CATALOG.md](CATALOG.md)**

| Service | Port | What it covers |
|---|---|---|
| IAM | 8200 | Projects, tokens |
| ECS | 8200 | Servers: lifecycle, attach/detach, state guards, batch ops, flavors |
| EVS | 8200 | Volumes: CRUD, snapshots (detached-only), os-vendor detail, extend |
| VPC | 8200 | VPCs, subnets, ports, peering, network ACLs, route tables |
| EIP | 8200 | Allocate/bind/unbind/release, bandwidths (v2.0) |
| IMS | 8200 | Images: 3 registration routes, Glance v2, whole images |
| CBR | 8200 | Vaults, policies, checkpoints (on-demand backup), backups, restore |
| RDS | 8200 | Database instances, flavors, backups, params, replicas, users, logs |
| OBS | 8201 | Buckets, objects, multipart upload, ListObjects XML |
| ELB / NAT / VPN / DNS | 8200 | Load balancers, NAT gateways, VPN gateways, zones + recordsets |
| CCE / CCI / SWR | 8200 | Kubernetes clusters, serverless pods, container registry |
| DWS / CSS / MRS | 8200 | Data warehouse, Elasticsearch clusters, Hadoop/Spark clusters |
| RDS-family | 8200 | DDS, GaussDB, GeminiDB, DDM, DBSS |
| DCS / DMS / DIS | 8200 | Redis, Kafka/RocketMQ, streaming ingestion |
| ModelArts + MaaS | 8200 | Notebooks, training, model registry, inference services, fine-tuning, OpenAI-compatible chat/embeddings |
| HSS / CFW / DSC / WAF / Anti-DDoS / KMS | 8200 | Host security, cloud firewall, data security, WAF, DDoS, keys |
| CDN | 8200 | Domains, origins, purge/preheat, statistics |
| SMS / OMS / DES | 8200 | Server migration, OBS migration, physical data transfer |
| DC / ER | 8200 | Direct Connect, Enterprise Router (attachments, route tables) |
| CodeArts / ServiceStage / CSE | 8200 | Repos, pipelines, builds; environments/apps/components; microservice engines |
| VOD / IEF | 8200 | Media assets + transcode, edge nodes + deployments |
| DataArts / DLI / AOM / CES / LTS / SMN | 8200 | Data governance, SQL jobs, ops, monitoring, logs, notifications |
| BMS / AS / SFS / TMS / EPS / APIG / IoTDA / BSS | 8200 | Bare metal, auto scaling, file shares, tags, enterprise projects, API gateway, IoT, billing |

## What makes it different from a mock

- **State machines with preconditions**: can't stop a stopped server, can't snapshot an
  in-use volume, can't detach a system disk
- **Async job model**: every mutation returns `job_id`, completes after 1-3s, clients poll
- **Per-region quirk profiles**: tr-west-1 (HCS) behaves differently from ap-southeast-1
- **Exact error codes**: `Ecs.0005 "device is illegal"`, `APIGW.0301`, `SecurityGroupRuleExists`
- **Rate limiting**: rapid calls → 401 `APIGW.0301`, 30s backoff clears it
- **Signature verification**: recomputes SDK-HMAC-SHA256 and OBS v2 signatures (accept-and-check)

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `SIM_PORT` | 8200 | REST port |
| `SIM_OBS_PORT` | 8201 | OBS port |
| `SIM_PROFILE` | public | Default quirk profile |
| `SIM_AK` / `SIM_SK` | HWYSIMAK… / HWYSIMSK… | Credentials |
| `SIM_RATE_LIMIT` | 100 | Per-AK requests / 10s (0 = disabled) |
| `SIM_RATE_COOLDOWN_MS` | 30000 | Throttle backoff |

## Dashboard

Open `http://127.0.0.1:8200/` for a live dashboard showing resource counts.
Open `http://127.0.0.1:8200/docs` for auto-generated API documentation.

## Testing

```bash
python3 tools/smoke.py        # 23-check smoke suite
python3 -m pytest tests/      # unit tests
```

## Known limitations

Honest scope statement: Larrot emulates **API behavior**, not infrastructure.
No virtual machines run, no packets flow, no disks exist.

**Depth varies by service.** The conformance suite covers 15 core services
(IAM, ECS, EVS, VPC, EIP, IMS, CBR, RDS, DNS, KMS, ELB, SFS, CCE, FG, GW)
at 100%. Beyond those:

- **Deep** (state machines, guards, async jobs, cross-service validation):
  OBS, HSS, CDN, DWS, CSS, MRS, SMS, DC, ER, DIS, DataArts, OMS, DES,
  CodeArts, ServiceStage, CSE, CCI, CFW, DSC, VOD, IEF, ModelArts + MaaS
- **Shallow** (basic CRUD, minimal lifecycle): BMS, AS, SMN, CES, LTS,
  DCS, DMS, DDS, GaussDB, WAF, TMS, EPS, APIG, SWR, IoTDA, AOM, DLI,
  Anti-DDoS, BSS, NAT, VPN, SFS, peering, ACL, routes

**Other limitations:**

- Signature verification is accept-and-check: mismatches are logged, never
  rejected (a deliberate choice for local development; the real cloud
  rejects them)
- Single port: services that share a path on the real cloud (RDS/DDS/
  GaussDB on `/v3/{pid}/instances`, DCS/DMS on `/v2/{pid}/instances`) are
  separated by namespaced routes; first-registered wins on the bare path
- Some error codes are modeled on documented behavior, not empirically
  observed (e.g., the newer 409 in-use guards)
- Jobs always complete in 1-3s; no real region latency, quotas are static
- Terraform provider compatibility is not yet validated
  (see [examples/terraform](examples/terraform/README.md))

## License

Apache 2.0: see [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
