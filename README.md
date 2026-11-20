# huawei-sim

**A local Huawei Cloud API simulator — like LocalStack, but for Huawei Cloud.**

Runs the REST APIs of Huawei Cloud's international site (`*.myhuaweicloud.com`) on your
machine: IAM, ECS, EVS, VPC, EIP, IMS, CBR, RDS, and OBS — including the undocumented
quirks we observed in production.

## Quick start

```bash
# Install
pip install huawei-sim

# Run
huawei-sim
# → REST on http://127.0.0.1:8200, OBS on http://127.0.0.1:8201

# Or with Docker
docker compose up

# Or from source
cd sim_py
pip install -e .
python -m huawei_sim
```

## CLI

```bash
hcli projects
hcli ecs list
hcli --wait ecs create --image <id> --flavor s6.large.2 --name myvm
hcli --wait ecs stop <server-id>
hcli evs list
hcli cbr vaults
hcli obs buckets
hcli --json ecs list
```

## Wire real SDKs

Point any `@huaweicloud` SDK at the simulator with a custom endpoint:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient, CreateServersRequest

credentials = BasicCredentials() \
    .with_ak("HWYSIMAK00000001") \
    .with_sk("HWYSIMSK00000001") \
    .with_project_id("79814d675f6142d9b4a8ee417b924444")

client = EcsClient.newBuilder() \
    .withCredential(credentials) \
    .withEndpoint("http://127.0.0.1:8200") \
    .build()
```

Your existing scripts run **unchanged** — just change the endpoint.

## Services

| Service | Port | What it covers |
|---|---|---|
| IAM | 8200 | Projects, tokens |
| ECS | 8200 | Servers: lifecycle, attach/detach, state guards, batch ops, flavors |
| EVS | 8200 | Volumes: CRUD, snapshots (detached-only), os-vendor detail, extend |
| VPC | 8200 | VPCs, subnets, ports |
| EIP | 8200 | Allocate/bind/unbind/release, bandwidths (v2.0) |
| IMS | 8200 | Images: 3 registration routes, Glance v2, whole images |
| CBR | 8200 | Vaults, policies, checkpoints (on-demand backup), backups, restore |
| RDS | 8200 | Database instances, flavors |
| OBS | 8201 | Buckets, objects, multipart upload, ListObjects XML |

## What makes it different from a mock

- **State machines with preconditions** — can't stop a stopped server, can't snapshot an
  in-use volume, can't detach a system disk
- **Async job model** — every mutation returns `job_id`, completes after 1–3s, clients poll
- **Per-region quirk profiles** — tr-west-1 (HCS) behaves differently from ap-southeast-1
- **Exact error codes** — `Ecs.0005 "device is illegal"`, `APIGW.0301`, `SecurityGroupRuleExists`
- **Rate limiting** — rapid calls → 401 `APIGW.0301`, 30s backoff clears it
- **Signature verification** — recomputes SDK-HMAC-SHA256 and OBS v2 signatures (accept-and-check)

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
cd sim_py
python3 tools/smoke.py        # 23-check smoke suite
python3 -m pytest tests/      # unit tests
```

## License

Apache 2.0 — see [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
