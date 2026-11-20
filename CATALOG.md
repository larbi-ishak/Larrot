# Larrot service catalog

All **59 Huawei Cloud services** simulated by Larrot, grouped by category.
`{pid}` is the project id; OBS runs on its own port (8201); IAM, CDN, and MaaS are
account-level (no project id in the path).

Total: 59 services across 71 router modules. Every mutating call returns a
`job_id` and completes asynchronously (1-3s), like the real cloud.

## Compute (7)

| Service | API base | What's simulated |
|---|---|---|
| **ECS** Elastic Cloud Server | `/v1/{pid}/cloudservers`, `/v1.1/...`, `/v2.1/...` | Server lifecycle, attach/detach volumes, state guards, batch actions, flavors, jobs, keypairs, server groups, metadata, NICs, resize, OS change, HPC |
| **BMS** Bare Metal Server | `/v1/{pid}/baremetalservers` | Bare metal lifecycle and jobs |
| **AS** Auto Scaling | `/v1/{pid}/scaling_group`, `.../scaling_policy` | Scaling groups, policies, instances |
| **CCE** Cloud Container Engine | `/api/v3/projects/{pid}/clusters` | Kubernetes clusters, nodes, node pools |
| **CCI** Cloud Container Instance | `/v1/{pid}/cci/...` | Serverless namespaces and pods (Pending -> Running) |
| **FunctionGraph** | `/v2/{pid}/fg/...` | Functions and invocations |
| **IMS** Image Management Service | `/v2/cloudimages`, `/v2/images` | 3 registration routes, Glance v2, whole images |

## Storage (4)

| Service | API base | What's simulated |
|---|---|---|
| **OBS** Object Storage Service | port **8201**, S3-style | Buckets, objects, multipart upload, ListObjects XML, virtual-host and path addressing |
| **EVS** Elastic Volume Service | `/v2/{pid}/cloudvolumes`, `/v2.1/...` | Volume CRUD, snapshots (detached-only), os-vendor detail, extend |
| **SFS** Scalable File Service | `/v2/{pid}/shares` | File shares and access rules |
| **CBR** Cloud Backup and Recovery | `/v3/{pid}/vaults`, `.../checkpoints` | Vaults, policies, on-demand backup, restore |

## Database (8)

| Service | API base | What's simulated |
|---|---|---|
| **RDS** Relational Database Service | `/v3/{pid}/instances` | Instances, flavors, backups, params, replicas, users, databases, logs, failover |
| **GaussDB** | `/v3/{pid}/instances` | Primary/enterprise instances |
| **GeminiDB** | `/v3/{pid}/gemini/...` | NoSQL instances (Redis/Cassandra/MongoDB flavors) |
| **DDS** Document Database Service | `/v3/{pid}/instances` | MongoDB-compatible instances |
| **DCS** Distributed Cache Service | `/v2/{pid}/instances` | Redis instances, backup/restore, parameters |
| **DMS** Distributed Message Service | `/v2/{pid}/instances` | Kafka/RocketMQ instances |
| **DDM** Distributed Database Middleware | `/v1/{pid}/instances` | Logical DBs, read replicas, users |
| **DBSS** Database Security Service | `/v1/{pid}/dbss/...` | Audit instances and rules |

## Network (9)

| Service | API base | What's simulated |
|---|---|---|
| **VPC** Virtual Private Cloud | `/v1/{pid}/vpcs` | VPCs, subnets, ports, security groups, **EIPs** (`/v1/{pid}/publicips`), VPC peering, network ACLs, route tables |
| **EIP** Elastic IP | `/v1/{pid}/publicips` | Allocate/bind/unbind/release, bandwidths (listed under VPC) |
| **ELB** Elastic Load Balance | `/v2/{pid}/elb/...` | Load balancers, listeners, pools |
| **NAT** NAT Gateway | `/v2.0/{pid}/nat_gateways` | Gateways, SNAT rules, DNAT rules |
| **VPN** | `/v5/{pid}/vpn-gateways` | IPsec/SSL VPN gateways and connections |
| **DNS** | `/v2/zones` | Public/private zones, recordsets |
| **DC** Direct Connect | `/v2.0/{pid}/direct-connects` | Connections, virtual gateways, virtual interfaces |
| **ER** Enterprise Router | `/v3/{pid}/enterprise-router/...` | Routers, VPC attachments, route tables |
| **CDN** | `/v1/domains` (account-level) | Domains, origins, purge/preheat tasks, statistics |

## Security (7)

| Service | API base | What's simulated |
|---|---|---|
| **IAM** Identity Access Management | `/v3/auth/tokens` (account-level) | Tokens, projects, agencies |
| **KMS** Key Management Service | `/v1/{pid}/kms/...` | CMKs, enable/disable, encrypt/decrypt |
| **WAF** Web Application Firewall | `/v1/{pid}/waf/...` | Domains, policies, rules |
| **Anti-DDoS** | `/v1/{pid}/antiddos/...` | Protection tasks and statuses |
| **HSS** Host Security Service | `/v5/{pid}/hosts` | Hosts (derived from ECS servers), protection policies, alarms, vulnerability scans |
| **CFW** Cloud Firewall | `/v1/{pid}/firewalls` | Firewalls, rules, hit records |
| **DSC** Data Security Center | `/v1/{pid}/dsc/...` | Assets, sensitive-data scans, risk handling |

## Management and Operations (7)

| Service | API base | What's simulated |
|---|---|---|
| **CES** Cloud Eye Service | `/v1/{pid}/metrics`, `.../alarms` | Metrics and alarm rules |
| **LTS** Log Tank Service | `/v2/{pid}/log-groups` | Log groups, streams, queries |
| **AOM** Application Operations Management | `/v1/{pid}/aom/...` | Components, monitoring data |
| **SMN** Simple Message Notification | `/v2/{pid}/notifications` | Topics, subscriptions, publishing |
| **TMS** Tag Management Service | `/v1.0/{pid}/project-tags` | Project and resource tags |
| **EPS** Enterprise Project Service | `/v1.0/{pid}/enterprise-projects` | Enterprise projects |
| **BSS** Billing and Subscription | `/v2/{pid}/orders` | Orders, account balances |

## Big Data and Analytics (6)

| Service | API base | What's simulated |
|---|---|---|
| **DWS** GaussDB DWS | `/v1.0/{pid}/clusters` | Data warehouse clusters, snapshots, resize |
| **CSS** Cloud Search Service | `/v1.0/{pid}/css/clusters` | Elasticsearch clusters, restart, indices |
| **MRS** MapReduce Service | `/v1.1/{pid}/cluster_infos` | Hadoop/Spark/Hive clusters, jobs, scaling |
| **DLI** Data Lake Insight | `/v1.0/{pid}/databases` | SQL databases, tables, jobs |
| **DIS** Data Ingestion Service | `/v2/{pid}/streams` | Streams, partitions, apps, checkpoints |
| **DataArts** Studio | `/v2/{pid}/connections` | Connections, ETL jobs, scripts |

## Application Services (4)

| Service | API base | What's simulated |
|---|---|---|
| **APIG** API Gateway | `/v2/{pid}/apigw/...` | Gateways, groups, APIs |
| **ServiceStage** | `/v2/{pid}/cas/...` | Environments, applications, components |
| **CSE** Cloud Service Engine | `/v2/{pid}/engines` | Microservice engines, service registration |
| **SWR** SoftWare Repository | `/v2/{pid}/namespaces` | Container namespaces, images |

## Development and DevOps (1)

| Service | API base | What's simulated |
|---|---|---|
| **CodeArts** | `/v2/projects/repositories`, `/v2/{pid}/pipelines` | Code repos, pipelines, build tasks |

## AI (1)

| Service | API base | What's simulated |
|---|---|---|
| **ModelArts** + **MaaS** | `/v2/{pid}/notebooks`, `/v1/{pid}/models`, `/v1/chat/completions` | Notebooks, training jobs, model registry, inference services, fine-tuning, and OpenAI-compatible MaaS (`/v1/models`, `/v1/chat/completions`, `/v1/embeddings`, API keys) |

## Migration (3)

| Service | API base | What's simulated |
|---|---|---|
| **SMS** Server Migration Service | `/v3/{pid}/sources` | Source servers (availability gate), migration tasks, templates |
| **OMS** Object Storage Migration | `/v2/{pid}/tasks` | Bucket-to-bucket tasks (validates the OBS destination) |
| **DES** Data Express | `/v1/{pid}/des/tasks` | Teleport/disk transfer tasks |

## IoT and Edge (2)

| Service | API base | What's simulated |
|---|---|---|
| **IoTDA** IoT Device Access | `/v5/{pid}/iot/...` | Products, devices, messages |
| **IEF** Intelligent EdgeFabric | `/v2/{pid}/edgemgr/...` | Edge nodes, app deployments |

## Media (1)

| Service | API base | What's simulated |
|---|---|---|
| **VOD** Video on Demand | `/v1/{pid}/assets` | Media assets (EMPTY -> PUBLISHED), transcode templates, categories |

---

## Notes

- **Shared routes**: RDS, DDS, and GaussDB all serve `/v3/{pid}/instances` on the
  real cloud via separate endpoint hostnames. Larrot is single-port, so the
  first-registered service (RDS) answers the bare path; the others use their
  namespaced routes. Same for DCS/DMS on `/v2/{pid}/instances`.
- **Async jobs**: every create/mutate call returns a `job_id`; poll
  `GET /v1/{pid}/jobs/{job_id}` until `SUCCESS` (1-3s, jittered).
- **Quirk profiles**: the `hcs` profile (tr-west-1) reproduces observed
  production quirks: sparse list views, flavors 404, empty v2.1 volume lists.
  See `docs/EMPIRICAL_SPEC.md`.
