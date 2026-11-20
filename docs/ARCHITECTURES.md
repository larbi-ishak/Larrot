# Real-world architectures

The 50 scenarios in `tests/test_scenarios_50.py` are executable versions of the
architectures below. Each maps to a test method and spans 3-8 services with
cross-service correlation assertions.

## Web & mobile applications

| # | Architecture | Services | Test |
|---|---|---|---|
| 1 | WordPress deployment: web VM + data volume + managed DB + public IP + DNS | ECS, EVS, RDS, EIP, DNS | `test_01_wordpress_deployment` |
| 2 | Serverless API: gateway fronting functions, with app consumers and auth bindings | APIG, FunctionGraph | `test_02_serverless_api` |
| 3 | Static website: object storage origin + CDN acceleration with cache purge | OBS, CDN | `test_03_static_website_cdn` |
| 4 | Microservices on Kubernetes: cluster + node pools + image registry + ingress | CCE, SWR, ELB | `test_04_microservices_cce` |
| 5 | Serverless containers: namespace + pods with async startup | CCI | `test_05_serverless_containers` |
| 6 | Mobile backend: API VM + Redis cache + Kafka queue + managed DB | ECS, DCS, DMS, RDS | `test_06_mobile_backend_stack` |
| 7 | WAF-protected web app: domain + policy + rules in front of the tier | WAF, ELB | `test_07_waf_protected_web_app` |
| 8 | CDN-accelerated downloads: preheating + statistics | CDN | `test_08_cdn_accelerated_apis` |
| 9 | Multi-AZ web tier: two servers behind an ELB with health monitors | ECS, ELB | `test_09_multi_az_web_tier` |
| 10 | DNS failover: primary + standby A records with TTL control | DNS | `test_10_dns_failover_architecture` |

## Data platforms

| # | Architecture | Services | Test |
|---|---|---|---|
| 11 | Streaming ingestion: stream -> consumer app with checkpoints -> SQL jobs | DIS, DLI | `test_11_streaming_ingestion_pipeline` |
| 12 | Batch ETL: connection -> job -> script -> scheduled run | DataArts | `test_12_batch_etl_dataarts` |
| 13 | Realtime analytics: stream + warehouse + search cluster | DIS, DWS, CSS | `test_13_realtime_analytics_stack` |
| 14 | Big data: Spark cluster + job submission + scale-out | MRS | `test_14_big_data_mrs` |
| 15 | Data warehouse lifecycle: cluster -> snapshot -> resize | DWS | `test_15_data_warehouse_lifecycle` |
| 16 | Search platform: cluster + time-partitioned indices + restart | CSS | `test_16_search_platform` |
| 17 | IoT telemetry: product -> devices -> commands -> stream | IoTDA, DIS | `test_17_iot_telemetry_pipeline` |

## DR & backup

| # | Architecture | Services | Test |
|---|---|---|---|
| 18 | Full DR site: server + volume + snapshot + vault + backup + restore to a new ECS | ECS, EVS, CBR | `test_18_full_dr_site` |
| 19 | Database DR: instance + backup + restore | RDS | `test_19_database_dr` |
| 20 | Cross-region backup: vault in one project, snapshot in the other, isolation proof | CBR, EVS (both projects) | `test_20_cross_region_backup` |
| 21 | Volume migration: snapshot -> new volume from snapshot | EVS | `test_21_volume_migration` |
| 22 | Image-based recovery: create image from a running server | ECS, IMS | `test_22_image_based_recovery` |

## Security

| # | Architecture | Services | Test |
|---|---|---|---|
| 23 | Zero-trust perimeter: VPC + ACL + SG + cloud firewall + WAF | VPC, ACL, CFW, WAF | `test_23_zero_trust_perimeter` |
| 24 | KMS encryption pipeline: CMK -> data key -> encrypt -> decrypt round-trip | KMS | `test_24_kms_encryption_pipeline` |
| 25 | IAM least-privilege: users -> groups -> per-project role assignments | IAM | `test_25_iam_least_privilege` |
| 26 | Federation SSO: IdP + protocol + mapping chain | IAM | `test_26_federation_sso` |
| 27 | HSS fleet protection: ECS fleet -> hosts -> policy -> vulnerability scan | ECS, HSS | `test_27_hss_fleet_protection` |
| 28 | Data discovery: assets -> scan -> risks -> handling | DSC | `test_28_dsc_data_discovery` |
| 29 | Anti-DDoS: EIP + protection task | EIP, Anti-DDoS | `test_29_antiddos_eip_shield` |

## Networking

| # | Architecture | Services | Test |
|---|---|---|---|
| 30 | Hub-and-spoke: ER hub + two spoke VPCs + route table | ER, VPC | `test_30_hub_and_spoke_er` |
| 31 | Hybrid connectivity: Direct Connect + virtual gateway + interface | DC, VPC | `test_31_hybrid_dc_connectivity` |
| 32 | VPC peering mesh: three VPCs, all pairs peered | VPC (peering) | `test_32_vpc_peering_mesh` |
| 33 | Site-to-site VPN: gateway + connection | VPN | `test_33_site_to_site_vpn` |
| 34 | NAT egress: gateway + SNAT rule for a private subnet | NAT, VPC | `test_34_nat_egress` |

## AI / ML

| # | Architecture | Services | Test |
|---|---|---|---|
| 35 | ML training pipeline: notebook -> training job -> model registry -> inference service | ModelArts | `test_35_ml_training_pipeline` |
| 36 | Dataset pipeline: labels -> samples -> version -> import -> export | ModelArts | `test_36_dataset_pipeline` |
| 37 | Fine-tune + serve: fine-tuning job -> MaaS API key -> chat completions | ModelArts, MaaS | `test_37_finetune_and_maas` |
| 38 | Multi-tenant MaaS: multiple API keys with independent lifecycle | MaaS | `test_38_multi_tenant_maas` |
| 39 | Inference autoscaling: service + scaling group + policy execution | ModelArts, AS | `test_39_inference_autoscaling` |
| 40 | Embeddings search prep: MaaS embeddings -> search cluster index | MaaS, CSS | `test_40_embeddings_search_prep` |

## Migration & DevOps

| # | Architecture | Services | Test |
|---|---|---|---|
| 41 | Server migration: source -> availability gate -> task -> success | SMS | `test_41_server_migration` |
| 42 | Storage migration: OBS destination + migration task | OMS, OBS | `test_42_storage_migration_oms` |
| 43 | Hybrid migration: compute + storage + bulk transfer together | SMS, OMS, DES | `test_43_hybrid_migration` |
| 44 | DevOps pipeline: repo -> pipeline -> build, all green | CodeArts | `test_44_devops_pipeline` |
| 45 | CI/CD with Kubernetes deploy: pipeline -> image -> cluster | CodeArts, SWR, CCE | `test_45_cicd_with_cce_deploy` |

## Enterprise & multi-tenancy

| # | Architecture | Services | Test |
|---|---|---|---|
| 46 | Enterprise project governance: EPS + TMS tags | EPS, TMS | `test_46_enterprise_project_isolation` |
| 47 | Multi-project deployment: same stack in both projects, fully isolated | ECS (both projects) | `test_47_multi_project_deployment` |
| 48 | Tagged fleet governance: ECS tags + TMS | ECS, TMS | `test_48_tagged_fleet_governance` |
| 49 | Full-stack startup: web + data + cache + DNS + CDN, visible in the explorer | ECS, RDS, DCS, EIP, DNS, CDN | `test_49_full_stack_startup` |
| 50 | Chaos drill on a live stack: inject job failures -> verify FAIL -> recover | presets, chaos, ECS | `test_50_chaos_drill_on_full_stack` |

## Running them

```bash
python3 -m pytest tests/test_scenarios_50.py -v
```

All 50 pass against a fresh simulator instance. Each scenario is self-contained:
no ordering dependencies, no shared state.
