# API coverage

Every operation Larrot serves, grouped by service. This page is
generated from the OpenAPI spec by `tools/gen_coverage.py` and
enforced by a test - it cannot drift from the code.

**66 services - 731 operations**

## AOM (5)

- `GET` `/v1/{pid}/aom/alarms`
- `GET` `/v1/{pid}/aom/apps`
- `POST` `/v1/{pid}/aom/apps`
- `POST` `/v1/{pid}/aom/components`
- `POST` `/v2/{pid}/aom/alarm-rules`

## APIG (27)

- `DELETE` `/v2/{pid}/apigw/apis/{api_id}`
- `DELETE` `/v2/{pid}/apigw/apps/{app_id}`
- `DELETE` `/v2/{pid}/apigw/environments/{env_id}`
- `DELETE` `/v2/{pid}/apigw/groups/{group_id}`
- `DELETE` `/v2/{pid}/apigw/throttles/{throttle_id}`
- `GET` `/v2/{pid}/apigw/apis/{api_id}`
- `GET` `/v2/{pid}/apigw/apis`
- `GET` `/v2/{pid}/apigw/app-auths`
- `GET` `/v2/{pid}/apigw/apps/{app_id}`
- `GET` `/v2/{pid}/apigw/apps`
- `GET` `/v2/{pid}/apigw/authorizers`
- `GET` `/v2/{pid}/apigw/environments/{env_id}`
- `GET` `/v2/{pid}/apigw/environments`
- `GET` `/v2/{pid}/apigw/groups/{group_id}`
- `GET` `/v2/{pid}/apigw/groups`
- `GET` `/v2/{pid}/apigw/instances/{instance_id}`
- `GET` `/v2/{pid}/apigw/instances`
- `GET` `/v2/{pid}/apigw/throttles/{throttle_id}`
- `GET` `/v2/{pid}/apigw/throttles`
- `POST` `/v2/{pid}/apigw/apis`
- `POST` `/v2/{pid}/apigw/app-auths`
- `POST` `/v2/{pid}/apigw/apps`
- `POST` `/v2/{pid}/apigw/authorizers`
- `POST` `/v2/{pid}/apigw/environments`
- `POST` `/v2/{pid}/apigw/groups`
- `POST` `/v2/{pid}/apigw/instances`
- `POST` `/v2/{pid}/apigw/throttles`

## AS (10)

- `DELETE` `/v1/{pid}/scaling_group/{group_id}`
- `DELETE` `/v1/{pid}/scaling_policy/{policy_id}`
- `GET` `/v1/{pid}/scaling_group/{group_id}/instances`
- `GET` `/v1/{pid}/scaling_group/{group_id}`
- `GET` `/v1/{pid}/scaling_group`
- `GET` `/v1/{pid}/scaling_policy/{policy_id}`
- `GET` `/v1/{pid}/scaling_policy`
- `POST` `/v1/{pid}/scaling_group`
- `POST` `/v1/{pid}/scaling_policy/{policy_id}/execute`
- `POST` `/v1/{pid}/scaling_policy`

## Anti-DDoS (4)

- `GET` `/v1/{pid}/antiddos/default`
- `GET` `/v1/{pid}/antiddos/status`
- `POST` `/v1/{pid}/antiddos/default`
- `POST` `/v1/{pid}/antiddos/enable`

## BMS (8)

- `DELETE` `/v1/{pid}/baremetalservers/{server_id}`
- `GET` `/v1/{pid}/baremetalservers/detail`
- `GET` `/v1/{pid}/baremetalservers/flavors`
- `GET` `/v1/{pid}/baremetalservers/{server_id}/nics`
- `GET` `/v1/{pid}/baremetalservers/{server_id}`
- `POST` `/v1/{pid}/baremetalservers/{server_id}/action`
- `POST` `/v1/{pid}/baremetalservers`
- `PUT` `/v1/{pid}/baremetalservers/{server_id}`

## BSS (4)

- `GET` `/v2/accounts/customer-accounts/balances`
- `GET` `/v2/orders/customer-orders/resources`
- `GET` `/v2/orders/customer-orders`
- `POST` `/v2/orders/customer-orders/pay`

## CBR (18)

- `DELETE` `/v3/{pid}/backups/{backup_id}`
- `DELETE` `/v3/{pid}/policies/{policy_id}`
- `DELETE` `/v3/{pid}/vaults/{vault_id}`
- `GET` `/v3/{pid}/backups/{backup_id}`
- `GET` `/v3/{pid}/backups`
- `GET` `/v3/{pid}/checkpoints/{checkpoint_id}`
- `GET` `/v3/{pid}/policies/{policy_id}`
- `GET` `/v3/{pid}/policies`
- `GET` `/v3/{pid}/vaults/{vault_id}`
- `GET` `/v3/{pid}/vaults`
- `POST` `/v3/{pid}/backups/{backup_id}/restore`
- `POST` `/v3/{pid}/checkpoints`
- `POST` `/v3/{pid}/policies`
- `POST` `/v3/{pid}/vaults/{vault_id}/addresources`
- `POST` `/v3/{pid}/vaults/{vault_id}/removeresources`
- `POST` `/v3/{pid}/vaults`
- `PUT` `/v3/{pid}/policies/{policy_id}`
- `PUT` `/v3/{pid}/vaults/{vault_id}`

## CCE (19)

- `DELETE` `/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}`
- `DELETE` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}`
- `DELETE` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodes/{node_id}`
- `DELETE` `/api/v3/projects/{pid}/clusters/{cluster_id}`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/addons`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodes/{node_id}`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodes`
- `GET` `/api/v3/projects/{pid}/clusters/{cluster_id}`
- `GET` `/api/v3/projects/{pid}/clusters`
- `POST` `/api/v3/projects/{pid}/clusters/{cluster_id}/addons`
- `POST` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools`
- `POST` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodes`
- `POST` `/api/v3/projects/{pid}/clusters`
- `PUT` `/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}`
- `PUT` `/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}`
- `PUT` `/api/v3/projects/{pid}/clusters/{cluster_id}`

## CCI (7)

- `DELETE` `/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}`
- `DELETE` `/v1/{pid}/cci/namespaces/{ns_id}`
- `GET` `/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}`
- `GET` `/v1/{pid}/cci/namespaces/{ns_id}/pods`
- `GET` `/v1/{pid}/cci/namespaces`
- `POST` `/v1/{pid}/cci/namespaces/{ns_id}/pods`
- `POST` `/v1/{pid}/cci/namespaces`

## CDN (9)

- `DELETE` `/v1/domains/{domain_id}`
- `GET` `/v1.0/historytasks`
- `GET` `/v1.0/statistics`
- `GET` `/v1/domains/{domain_id}`
- `GET` `/v1/domains`
- `POST` `/v1.0/preheating`
- `POST` `/v1.0/purgecache`
- `POST` `/v1/domains`
- `PUT` `/v1/domains/{domain_id}`

## CES (9)

- `DELETE` `/v1/{pid}/alarms/{alarm_id}`
- `GET` `/v1.0/{pid}/metric-data`
- `GET` `/v1/{pid}/alarms/{alarm_id}/history`
- `GET` `/v1/{pid}/alarms/{alarm_id}`
- `GET` `/v1/{pid}/alarms`
- `GET` `/v1/{pid}/metrics`
- `POST` `/v1.0/{pid}/batch-query/metric-data`
- `POST` `/v1/{pid}/alarms`
- `PUT` `/v1/{pid}/alarms/{alarm_id}`

## CFW (9)

- `DELETE` `/v1/{pid}/firewalls/{firewall_id}/rules/{rule_id}`
- `DELETE` `/v1/{pid}/firewalls/{firewall_id}`
- `GET` `/v1/{pid}/firewalls/{firewall_id}/hit-records`
- `GET` `/v1/{pid}/firewalls/{firewall_id}/rules`
- `GET` `/v1/{pid}/firewalls/{firewall_id}`
- `GET` `/v1/{pid}/firewalls`
- `POST` `/v1/{pid}/firewalls/{firewall_id}/hit-records`
- `POST` `/v1/{pid}/firewalls/{firewall_id}/rules`
- `POST` `/v1/{pid}/firewalls`

## CSE (6)

- `DELETE` `/v2/{pid}/engines/{engine_id}`
- `GET` `/v2/{pid}/engines/{engine_id}/microservices`
- `GET` `/v2/{pid}/engines/{engine_id}`
- `GET` `/v2/{pid}/engines`
- `POST` `/v2/{pid}/engines/{engine_id}/microservices`
- `POST` `/v2/{pid}/engines`

## CSS (8)

- `DELETE` `/v1.0/{pid}/css/clusters/{cluster_id}/indices/{index_name}`
- `DELETE` `/v1.0/{pid}/css/clusters/{cluster_id}`
- `GET` `/v1.0/{pid}/css/clusters/{cluster_id}/indices`
- `GET` `/v1.0/{pid}/css/clusters/{cluster_id}`
- `GET` `/v1.0/{pid}/css/clusters`
- `POST` `/v1.0/{pid}/css/clusters/{cluster_id}/indices`
- `POST` `/v1.0/{pid}/css/clusters/{cluster_id}/restart`
- `POST` `/v1.0/{pid}/css/clusters`

## CodeArts (11)

- `DELETE` `/v2/projects/repositories/{repo_id}`
- `DELETE` `/v2/{pid}/pipelines/{pipeline_id}`
- `GET` `/v2/projects/repositories/{repo_id}`
- `GET` `/v2/projects/repositories`
- `GET` `/v2/{pid}/builds`
- `GET` `/v2/{pid}/pipelines`
- `POST` `/v2/projects/repositories`
- `POST` `/v2/{pid}/builds/{build_id}/run`
- `POST` `/v2/{pid}/builds`
- `POST` `/v2/{pid}/pipelines/{pipeline_id}/run`
- `POST` `/v2/{pid}/pipelines`

## DBSS (6)

- `DELETE` `/v1/{pid}/dbss/instances/{instance_id}`
- `GET` `/v1/{pid}/dbss/instances/{instance_id}/audit-logs`
- `GET` `/v1/{pid}/dbss/instances/{instance_id}`
- `GET` `/v1/{pid}/dbss/instances`
- `POST` `/v1/{pid}/dbss/instances/{instance_id}/audit-rules`
- `POST` `/v1/{pid}/dbss/instances`

## DCS Extras (11)

- `DELETE` `/v2/{pid}/instances/{instance_id}/backups/{backup_id}`
- `GET` `/v2/{pid}/flavors`
- `GET` `/v2/{pid}/instances/{instance_id}/backups`
- `GET` `/v2/{pid}/instances/{instance_id}/big-keys`
- `GET` `/v2/{pid}/instances/{instance_id}/hot-keys`
- `GET` `/v2/{pid}/instances/{instance_id}/parameters`
- `POST` `/v2/{pid}/instances/{instance_id}/backups`
- `POST` `/v2/{pid}/instances/{instance_id}/resize`
- `POST` `/v2/{pid}/instances/{instance_id}/restart`
- `POST` `/v2/{pid}/instances/{instance_id}/restore`
- `PUT` `/v2/{pid}/instances/{instance_id}/parameters`

## DDM (7)

- `DELETE` `/v1/{pid}/instances/{instance_id}/schemas/{schema_name}`
- `DELETE` `/v1/{pid}/instances/{instance_id}`
- `GET` `/v1/{pid}/instances/{instance_id}/schemas`
- `GET` `/v1/{pid}/instances`
- `POST` `/v1/{pid}/instances/{instance_id}/schemas/{schema_name}/shard-rules`
- `POST` `/v1/{pid}/instances/{instance_id}/schemas`
- `POST` `/v1/{pid}/instances`

## DES (4)

- `DELETE` `/v1/{pid}/des/tasks/{task_id}`
- `GET` `/v1/{pid}/des/tasks/{task_id}`
- `GET` `/v1/{pid}/des/tasks`
- `POST` `/v1/{pid}/des/tasks`

## DIS (10)

- `DELETE` `/v2/{pid}/apps/{app_name}/checkpoints`
- `DELETE` `/v2/{pid}/streams/{stream_name}`
- `GET` `/v2/{pid}/apps/{app_name}/checkpoints`
- `GET` `/v2/{pid}/apps`
- `GET` `/v2/{pid}/streams/{stream_name}`
- `GET` `/v2/{pid}/streams`
- `POST` `/v2/{pid}/apps`
- `POST` `/v2/{pid}/streams`
- `PUT` `/v2/{pid}/apps/{app_name}/checkpoints`
- `PUT` `/v2/{pid}/streams/{stream_name}`

## DLI (10)

- `DELETE` `/v1.0/{pid}/databases/{database_name}`
- `DELETE` `/v1.0/{pid}/queues/{queue_id}`
- `GET` `/v1.0/{pid}/databases`
- `GET` `/v1.0/{pid}/jobs/{job_id}`
- `GET` `/v1.0/{pid}/jobs`
- `GET` `/v1.0/{pid}/queues`
- `POST` `/v1.0/{pid}/databases`
- `POST` `/v1.0/{pid}/jobs/submit`
- `POST` `/v1.0/{pid}/queues`
- `POST` `/v1.0/{pid}/tables`

## DMS (6)

- `DELETE` `/v2/{pid}/instances/{instance_id}`
- `GET` `/v2/{pid}/instances/{instance_id}/topics`
- `GET` `/v2/{pid}/instances/{instance_id}`
- `GET` `/v2/{pid}/instances`
- `POST` `/v2/{pid}/instances/{instance_id}/topics`
- `POST` `/v2/{pid}/instances`

## DNS (11)

- `DELETE` `/v2/zones/{zone_id}/recordsets/{recordset_id}`
- `DELETE` `/v2/zones/{zone_id}`
- `GET` `/v2/recordsets`
- `GET` `/v2/zones/{zone_id}/recordsets/{recordset_id}`
- `GET` `/v2/zones/{zone_id}/recordsets`
- `GET` `/v2/zones/{zone_id}`
- `GET` `/v2/zones`
- `POST` `/v2/zones/{zone_id}/recordsets`
- `POST` `/v2/zones`
- `PUT` `/v2/zones/{zone_id}/recordsets/{recordset_id}`
- `PUT` `/v2/zones/{zone_id}`

## DSC (6)

- `DELETE` `/v1/{pid}/dsc/assets/{asset_id}`
- `GET` `/v1/{pid}/dsc/assets`
- `GET` `/v1/{pid}/dsc/risks`
- `POST` `/v1/{pid}/dsc/assets`
- `POST` `/v1/{pid}/dsc/risks/{risk_id}/handle`
- `POST` `/v1/{pid}/dsc/scans`

## DWS (18)

- `DELETE` `/v1.0/{pid}/clusters/{cluster_id}`
- `DELETE` `/v1.0/{pid}/dws/clusters/{cluster_id}`
- `DELETE` `/v1.0/{pid}/dws/snapshots/{snapshot_id}`
- `DELETE` `/v1.0/{pid}/snapshots/{snapshot_id}`
- `GET` `/v1.0/{pid}/clusters/{cluster_id}`
- `GET` `/v1.0/{pid}/clusters`
- `GET` `/v1.0/{pid}/dws/clusters/{cluster_id}`
- `GET` `/v1.0/{pid}/dws/clusters`
- `GET` `/v1.0/{pid}/dws/snapshots/{snapshot_id}`
- `GET` `/v1.0/{pid}/dws/snapshots`
- `GET` `/v1.0/{pid}/snapshots/{snapshot_id}`
- `GET` `/v1.0/{pid}/snapshots`
- `POST` `/v1.0/{pid}/clusters/{cluster_id}/resize`
- `POST` `/v1.0/{pid}/clusters`
- `POST` `/v1.0/{pid}/dws/clusters/{cluster_id}/resize`
- `POST` `/v1.0/{pid}/dws/clusters`
- `POST` `/v1.0/{pid}/dws/snapshots`
- `POST` `/v1.0/{pid}/snapshots`

## DataArts (10)

- `DELETE` `/v2/{pid}/connections/{conn_id}`
- `DELETE` `/v2/{pid}/jobs/{job_id}`
- `GET` `/v2/{pid}/connections/{conn_id}`
- `GET` `/v2/{pid}/connections`
- `GET` `/v2/{pid}/jobs`
- `GET` `/v2/{pid}/scripts`
- `POST` `/v2/{pid}/connections`
- `POST` `/v2/{pid}/jobs/{job_name}/run`
- `POST` `/v2/{pid}/jobs`
- `POST` `/v2/{pid}/scripts`

## Direct Connect (10)

- `DELETE` `/v2.0/{pid}/direct-connects/{conn_id}`
- `DELETE` `/v2.0/{pid}/virtual-gateways/{vgw_id}`
- `DELETE` `/v2.0/{pid}/virtual-interfaces/{vif_id}`
- `GET` `/v2.0/{pid}/direct-connects/{conn_id}`
- `GET` `/v2.0/{pid}/direct-connects`
- `GET` `/v2.0/{pid}/virtual-gateways`
- `GET` `/v2.0/{pid}/virtual-interfaces`
- `POST` `/v2.0/{pid}/direct-connects`
- `POST` `/v2.0/{pid}/virtual-gateways`
- `POST` `/v2.0/{pid}/virtual-interfaces`

## ECS (28)

- `DELETE` `/v1/{pid}/cloudservers/{server_id}/attachvolume/{volume_id}`
- `DELETE` `/v1/{pid}/cloudservers/{server_id}/tags`
- `GET` `/v1.1/{pid}/cloudservers/detail`
- `GET` `/v1/{pid}/cloudservers/detail`
- `GET` `/v1/{pid}/cloudservers/flavors`
- `GET` `/v1/{pid}/cloudservers/{server_id}/block_device`
- `GET` `/v1/{pid}/cloudservers/{server_id}/os-resetpwd-flag`
- `GET` `/v1/{pid}/cloudservers/{server_id}/os-server-password`
- `GET` `/v1/{pid}/cloudservers/{server_id}/os-volume_attachments`
- `GET` `/v1/{pid}/cloudservers/{server_id}/tags`
- `GET` `/v1/{pid}/cloudservers/{server_id}`
- `GET` `/v1/{pid}/jobs/{job_id}`
- `GET` `/v2.1/{pid}/os-availability-zone`
- `GET` `/v2.1/{pid}/servers/detail`
- `GET` `/v2.1/{pid}/servers`
- `POST` `/v1.1/{pid}/cloudservers`
- `POST` `/v1/{pid}/cloudservers/action`
- `POST` `/v1/{pid}/cloudservers/delete`
- `POST` `/v1/{pid}/cloudservers/{server_id}/action`
- `POST` `/v1/{pid}/cloudservers/{server_id}/attachvolume`
- `POST` `/v1/{pid}/cloudservers/{server_id}/os-reset-password`
- `POST` `/v1/{pid}/cloudservers/{server_id}/tags/action`
- `POST` `/v1/{pid}/cloudservers`
- `POST` `/v2.1/{pid}/servers`
- `PUT` `/v1/{pid}/cloudservers/{server_id}/os-reset-password`
- `PUT` `/v1/{pid}/cloudservers/{server_id}/os-resetpwd-flag`
- `PUT` `/v1/{pid}/cloudservers/{server_id}/tags`
- `PUT` `/v1/{pid}/cloudservers/{server_id}`

## ECS Batch (5)

- `DELETE` `/v1/{pid}/batch/jobs/{job_id}`
- `GET` `/v1/{pid}/batch/jobs/{job_id}`
- `GET` `/v1/{pid}/batch/jobs`
- `POST` `/v1/{pid}/batch/jobs/{job_id}/cancel`
- `POST` `/v1/{pid}/batch/jobs`

## ECS Extras (16)

- `DELETE` `/v1/{pid}/cloudservers/{server_id}/metadata/{key}`
- `DELETE` `/v1/{pid}/cloudservers/{server_id}/os-interface/{port_id}`
- `GET` `/v1/{pid}/cloudservers/limits`
- `GET` `/v1/{pid}/cloudservers/{server_id}/console_log`
- `GET` `/v1/{pid}/cloudservers/{server_id}/metadata`
- `GET` `/v1/{pid}/cloudservers/{server_id}/os-interface`
- `GET` `/v1/{pid}/cloudservers/{server_id}/remote_console`
- `GET` `/v2.1/{pid}/servers/{server_id}/os-interface`
- `GET` `/v2.1/{pid}/servers/{server_id}`
- `POST` `/v1/{pid}/cloudservers/{server_id}/changeos`
- `POST` `/v1/{pid}/cloudservers/{server_id}/os-interface`
- `POST` `/v1/{pid}/cloudservers/{server_id}/remote_console`
- `POST` `/v1/{pid}/cloudservers/{server_id}/resize`
- `POST` `/v2.1/{pid}/servers/{server_id}/action`
- `PUT` `/v1/{pid}/cloudservers/{server_id}/metadata`
- `PUT` `/v2.1/{pid}/servers/{server_id}`

## ECS Keypairs (5)

- `DELETE` `/v2.1/{pid}/os-keypairs/{keypair_name}`
- `GET` `/v2.1/{pid}/os-keypairs/{keypair_name}`
- `GET` `/v2.1/{pid}/os-keypairs`
- `POST` `/v2.1/{pid}/os-keypairs/import`
- `POST` `/v2.1/{pid}/os-keypairs`

## ECS Server Groups (5)

- `DELETE` `/v2.1/{pid}/os-server-groups/{group_id}`
- `GET` `/v2.1/{pid}/os-server-groups/{group_id}`
- `GET` `/v2.1/{pid}/os-server-groups`
- `POST` `/v2.1/{pid}/os-server-groups`
- `PUT` `/v2.1/{pid}/os-server-groups/{group_id}`

## ELB (19)

- `DELETE` `/v2/{pid}/elb/healthmonitors/{healthmonitor_id}`
- `DELETE` `/v2/{pid}/elb/listeners/{listener_id}`
- `DELETE` `/v2/{pid}/elb/loadbalancers/{lb_id}`
- `DELETE` `/v2/{pid}/elb/pools/{pool_id}/members/{member_id}`
- `DELETE` `/v2/{pid}/elb/pools/{pool_id}`
- `GET` `/v2/{pid}/elb/healthmonitors/{healthmonitor_id}`
- `GET` `/v2/{pid}/elb/healthmonitors`
- `GET` `/v2/{pid}/elb/listeners/{listener_id}`
- `GET` `/v2/{pid}/elb/listeners`
- `GET` `/v2/{pid}/elb/loadbalancers/{lb_id}`
- `GET` `/v2/{pid}/elb/loadbalancers`
- `GET` `/v2/{pid}/elb/pools/{pool_id}/members/{member_id}`
- `GET` `/v2/{pid}/elb/pools/{pool_id}/members`
- `GET` `/v2/{pid}/elb/pools`
- `POST` `/v2/{pid}/elb/healthmonitors`
- `POST` `/v2/{pid}/elb/listeners`
- `POST` `/v2/{pid}/elb/loadbalancers`
- `POST` `/v2/{pid}/elb/pools/{pool_id}/members`
- `POST` `/v2/{pid}/elb/pools`

## EPS (5)

- `DELETE` `/v1.0/enterprise-projects/{eps_id}`
- `GET` `/v1.0/enterprise-projects/{eps_id}`
- `GET` `/v1.0/enterprise-projects`
- `POST` `/v1.0/enterprise-projects`
- `PUT` `/v1.0/enterprise-projects/{eps_id}`

## EVS (20)

- `DELETE` `/v2/{pid}/cloudsnapshots/{snapshot_id}`
- `DELETE` `/v2/{pid}/cloudvolumes/{volume_id}`
- `GET` `/v2.1/{pid}/cloudvolumes/detail`
- `GET` `/v2/{pid}/cloudsnapshots/detail`
- `GET` `/v2/{pid}/cloudsnapshots/{snapshot_id}`
- `GET` `/v2/{pid}/cloudsnapshots`
- `GET` `/v2/{pid}/cloudvolumes/detail`
- `GET` `/v2/{pid}/cloudvolumes/{volume_id}`
- `GET` `/v2/{pid}/cloudvolumes`
- `GET` `/v2/{pid}/os-vendor-volumes/detail`
- `GET` `/v2/{pid}/os-vendor-volumes/{volume_id}`
- `GET` `/v2/{pid}/snapshots/detail`
- `POST` `/v2.1/{pid}/cloudvolumes/{volume_id}/action`
- `POST` `/v2.1/{pid}/cloudvolumes`
- `POST` `/v2/{pid}/cloudsnapshots/{snapshot_id}/rollback`
- `POST` `/v2/{pid}/cloudsnapshots`
- `POST` `/v2/{pid}/cloudvolumes`
- `POST` `/v2/{pid}/volumes`
- `PUT` `/v2/{pid}/cloudsnapshots/{snapshot_id}`
- `PUT` `/v2/{pid}/cloudvolumes/{volume_id}`

## Enterprise Router (12)

- `DELETE` `/v3/{pid}/enterprise-router/instances/{er_id}/attachments/{attachment_id}`
- `DELETE` `/v3/{pid}/enterprise-router/instances/{er_id}`
- `GET` `/v3/{pid}/enterprise-router/instances/{er_id}/attachments`
- `GET` `/v3/{pid}/enterprise-router/instances/{er_id}/route-tables/{route_table_id}`
- `GET` `/v3/{pid}/enterprise-router/instances/{er_id}/route-tables`
- `GET` `/v3/{pid}/enterprise-router/instances/{er_id}/vpc-attachments`
- `GET` `/v3/{pid}/enterprise-router/instances/{er_id}`
- `GET` `/v3/{pid}/enterprise-router/instances`
- `POST` `/v3/{pid}/enterprise-router/instances/{er_id}/attachments`
- `POST` `/v3/{pid}/enterprise-router/instances/{er_id}/route-tables`
- `POST` `/v3/{pid}/enterprise-router/instances/{er_id}/vpc-attachments`
- `POST` `/v3/{pid}/enterprise-router/instances`

## FunctionGraph (5)

- `DELETE` `/v2/{pid}/fg/functions/{func_id}`
- `GET` `/v2/{pid}/fg/functions/{func_id}`
- `GET` `/v2/{pid}/fg/functions`
- `POST` `/v2/{pid}/fg/functions/{func_id}/invocations`
- `POST` `/v2/{pid}/fg/functions`

## GaussDB (4)

- `DELETE` `/v3/{pid}/instances/{instance_id}`
- `GET` `/v3/{pid}/instances/{instance_id}`
- `GET` `/v3/{pid}/instances`
- `POST` `/v3/{pid}/instances`

## GeminiDB (6)

- `DELETE` `/v3/{pid}/gemini/instances/{instance_id}`
- `GET` `/v3/{pid}/gemini/flavors`
- `GET` `/v3/{pid}/gemini/instances/{instance_id}`
- `GET` `/v3/{pid}/gemini/instances`
- `POST` `/v3/{pid}/gemini/instances/{instance_id}/action`
- `POST` `/v3/{pid}/gemini/instances`

## HPC (6)

- `DELETE` `/v2/{pid}/hpc/clusters/{cluster_id}`
- `GET` `/v2/{pid}/hpc/clusters/{cluster_id}/nodes`
- `GET` `/v2/{pid}/hpc/clusters/{cluster_id}`
- `GET` `/v2/{pid}/hpc/clusters`
- `POST` `/v2/{pid}/hpc/clusters/{cluster_id}/nodes`
- `POST` `/v2/{pid}/hpc/clusters`

## HSS (10)

- `GET` `/v5/{pid}/alarm-events`
- `GET` `/v5/{pid}/hosts/{host_id}`
- `GET` `/v5/{pid}/hosts`
- `GET` `/v5/{pid}/policy`
- `GET` `/v5/{pid}/quotas`
- `GET` `/v5/{pid}/vulnerabilities`
- `POST` `/v5/{pid}/alarm-events`
- `POST` `/v5/{pid}/hosts/{host_id}/protection`
- `POST` `/v5/{pid}/policy`
- `POST` `/v5/{pid}/vulnerabilities/scan`

## IAM (48)

- `DELETE` `/v3.0/OS-AGENCY/agencies/{agency_id}`
- `DELETE` `/v3.0/OS-CREDENTIAL/credentials/{access_key}`
- `DELETE` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}`
- `DELETE` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}`
- `DELETE` `/v3.0/OS-FEDERATION/mappings/{mapping_id}`
- `DELETE` `/v3/auth/tokens`
- `DELETE` `/v3/groups/{group_id}/users/{user_id}`
- `DELETE` `/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}`
- `DELETE` `/v3/projects/{project_id}/users/{user_id}/roles/{role_id}`
- `DELETE` `/v3/users/{user_id}`
- `GET` `/v3.0/OS-AGENCY/agencies/{agency_id}`
- `GET` `/v3.0/OS-AGENCY/agencies`
- `GET` `/v3.0/OS-CREDENTIAL/credentials/{access_key}`
- `GET` `/v3.0/OS-CREDENTIAL/credentials`
- `GET` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}`
- `GET` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols`
- `GET` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}`
- `GET` `/v3.0/OS-FEDERATION/identity_providers`
- `GET` `/v3.0/OS-FEDERATION/mappings/{mapping_id}`
- `GET` `/v3.0/OS-FEDERATION/mappings`
- `GET` `/v3/auth/catalog`
- `GET` `/v3/auth/projects`
- `GET` `/v3/domains`
- `GET` `/v3/groups/{group_id}/users`
- `GET` `/v3/groups`
- `GET` `/v3/projects/{project_id}/groups/{group_id}/roles`
- `GET` `/v3/projects/{project_id}/users/{user_id}/roles`
- `GET` `/v3/projects/{project_id}`
- `GET` `/v3/projects`
- `GET` `/v3/roles`
- `GET` `/v3/users/{user_id}/groups`
- `GET` `/v3/users/{user_id}`
- `GET` `/v3/users`
- `HEAD` `/v3/auth/tokens`
- `POST` `/v3.0/OS-AGENCY/agencies`
- `POST` `/v3.0/OS-CREDENTIAL/credentials`
- `POST` `/v3/auth/tokens`
- `POST` `/v3/groups`
- `POST` `/v3/users`
- `PUT` `/v3.0/OS-AGENCY/agencies/{agency_id}`
- `PUT` `/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}`
- `PUT` `/v3.0/OS-FEDERATION/identity_providers`
- `PUT` `/v3.0/OS-FEDERATION/mappings`
- `PUT` `/v3/groups/{group_id}/users/{user_id}`
- `PUT` `/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}`
- `PUT` `/v3/projects/{project_id}/users/{user_id}/roles/{role_id}`
- `PUT` `/v3/projects/{project_id}`
- `PUT` `/v3/users/{user_id}`

## IEF (8)

- `DELETE` `/v2/{pid}/edgemgr/deployments/{deployment_id}`
- `DELETE` `/v2/{pid}/edgemgr/nodes/{node_id}`
- `GET` `/v2/{pid}/edgemgr/deployments/{deployment_id}`
- `GET` `/v2/{pid}/edgemgr/deployments`
- `GET` `/v2/{pid}/edgemgr/nodes/{node_id}`
- `GET` `/v2/{pid}/edgemgr/nodes`
- `POST` `/v2/{pid}/edgemgr/deployments`
- `POST` `/v2/{pid}/edgemgr/nodes`

## IMS (13)

- `DELETE` `/v2/images/{image_id}`
- `GET` `/v1/cloudimages/job/{job_id}`
- `GET` `/v2/cloudimages`
- `GET` `/v2/images/{image_id}`
- `GET` `/v2/images`
- `PATCH` `/v2/images/{image_id}`
- `POST` `/v1/cloudimages/wholeimages/action`
- `POST` `/v1/cloudimages/{image_id}/upload`
- `POST` `/v2.1/cloudimages/action`
- `POST` `/v2/cloudimages/action`
- `POST` `/v2/cloudimages/quickimport/action`
- `POST` `/v2/images`
- `PUT` `/v2/images/{image_id}/file`

## IoTDA (10)

- `DELETE` `/v5/iot/{pid}/devices/{device_id}`
- `DELETE` `/v5/iot/{pid}/products/{product_id}`
- `GET` `/v5/iot/{pid}/devices/{device_id}`
- `GET` `/v5/iot/{pid}/devices`
- `GET` `/v5/iot/{pid}/products/{product_id}`
- `GET` `/v5/iot/{pid}/products`
- `POST` `/v5/iot/{pid}/devices/{device_id}/commands`
- `POST` `/v5/iot/{pid}/devices`
- `POST` `/v5/iot/{pid}/products`
- `PUT` `/v5/iot/{pid}/devices/{device_id}`

## KMS (15)

- `GET` `/v1/{pid}/kms/describe-key/{key_id}`
- `GET` `/v1/{pid}/kms/get-publickey/{key_id}`
- `POST` `/v1/{pid}/kms/cancel-key-deletion`
- `POST` `/v1/{pid}/kms/create-datakey`
- `POST` `/v1/{pid}/kms/create-key`
- `POST` `/v1/{pid}/kms/decrypt-data`
- `POST` `/v1/{pid}/kms/decrypt-datakey`
- `POST` `/v1/{pid}/kms/disable-key`
- `POST` `/v1/{pid}/kms/enable-key`
- `POST` `/v1/{pid}/kms/encrypt-data`
- `POST` `/v1/{pid}/kms/encrypt-datakey`
- `POST` `/v1/{pid}/kms/gen-random`
- `POST` `/v1/{pid}/kms/list-keys`
- `POST` `/v1/{pid}/kms/schedule-key-deletion`
- `POST` `/v1/{pid}/kms/update-key-alias`

## LTS (6)

- `DELETE` `/v2/{pid}/log-groups/{group_id}/log-streams/{stream_id}`
- `DELETE` `/v2/{pid}/log-groups/{group_id}`
- `GET` `/v2/{pid}/log-groups/{group_id}/log-streams`
- `GET` `/v2/{pid}/log-groups`
- `POST` `/v2/{pid}/log-groups/{group_id}/log-streams`
- `POST` `/v2/{pid}/log-groups`

## MRS (6)

- `DELETE` `/v1.1/{pid}/cluster_infos/{cluster_id}`
- `GET` `/v1.1/{pid}/cluster_infos/{cluster_id}`
- `GET` `/v1.1/{pid}/cluster_infos`
- `POST` `/v1.1/{pid}/cluster_infos/{cluster_id}/jobs`
- `POST` `/v1.1/{pid}/cluster_infos/{cluster_id}/resize`
- `POST` `/v1.1/{pid}/cluster_infos`

## ModelArts + MaaS (39)

- `DELETE` `/v1/{pid}/maas/keys/{key_id}`
- `DELETE` `/v1/{pid}/models/{model_id}`
- `DELETE` `/v1/{pid}/services/{service_id}`
- `DELETE` `/v2/{pid}/datasets/{dataset_id}/labels/{label_name}`
- `DELETE` `/v2/{pid}/datasets/{dataset_id}/versions/{version_id}`
- `DELETE` `/v2/{pid}/datasets/{dataset_id}`
- `DELETE` `/v2/{pid}/notebooks/{notebook_id}`
- `GET` `/v1/models`
- `GET` `/v1/{pid}/fine-tuning-jobs`
- `GET` `/v1/{pid}/maas/keys`
- `GET` `/v1/{pid}/models/{model_id}`
- `GET` `/v1/{pid}/models`
- `GET` `/v1/{pid}/services/{service_id}`
- `GET` `/v1/{pid}/services`
- `GET` `/v2/{pid}/datasets/{dataset_id}/export-tasks`
- `GET` `/v2/{pid}/datasets/{dataset_id}/import-tasks`
- `GET` `/v2/{pid}/datasets/{dataset_id}/labels`
- `GET` `/v2/{pid}/datasets/{dataset_id}/samples`
- `GET` `/v2/{pid}/datasets/{dataset_id}/versions`
- `GET` `/v2/{pid}/datasets/{dataset_id}`
- `GET` `/v2/{pid}/datasets`
- `GET` `/v2/{pid}/notebooks`
- `GET` `/v2/{pid}/training-jobs`
- `POST` `/v1/chat/completions`
- `POST` `/v1/embeddings`
- `POST` `/v1/{pid}/fine-tuning-jobs`
- `POST` `/v1/{pid}/maas/keys`
- `POST` `/v1/{pid}/models`
- `POST` `/v1/{pid}/services`
- `POST` `/v2/{pid}/datasets/{dataset_id}/export-tasks`
- `POST` `/v2/{pid}/datasets/{dataset_id}/import-tasks`
- `POST` `/v2/{pid}/datasets/{dataset_id}/labels`
- `POST` `/v2/{pid}/datasets/{dataset_id}/samples`
- `POST` `/v2/{pid}/datasets/{dataset_id}/versions`
- `POST` `/v2/{pid}/datasets`
- `POST` `/v2/{pid}/notebooks`
- `POST` `/v2/{pid}/training-jobs`
- `PUT` `/v2/{pid}/datasets/{dataset_id}/labels/{label_name}`
- `PUT` `/v2/{pid}/datasets/{dataset_id}`

## NAT (10)

- `DELETE` `/v2.0/{pid}/dnat_rules/{rule_id}`
- `DELETE` `/v2.0/{pid}/nat_gateways/{gateway_id}`
- `DELETE` `/v2.0/{pid}/snat_rules/{rule_id}`
- `GET` `/v2.0/{pid}/dnat_rules`
- `GET` `/v2.0/{pid}/nat_gateways/{gateway_id}`
- `GET` `/v2.0/{pid}/nat_gateways`
- `GET` `/v2.0/{pid}/snat_rules`
- `POST` `/v2.0/{pid}/dnat_rules`
- `POST` `/v2.0/{pid}/nat_gateways`
- `POST` `/v2.0/{pid}/snat_rules`

## Network ACL (9)

- `DELETE` `/v3/{pid}/vpc/acls/{acl_id}`
- `GET` `/v3/{pid}/vpc/acls/{acl_id}`
- `GET` `/v3/{pid}/vpc/acls`
- `POST` `/v3/{pid}/vpc/acls/{acl_id}/associate`
- `POST` `/v3/{pid}/vpc/acls/{acl_id}/disassociate`
- `POST` `/v3/{pid}/vpc/acls/{acl_id}/egress-rules`
- `POST` `/v3/{pid}/vpc/acls/{acl_id}/ingress-rules`
- `POST` `/v3/{pid}/vpc/acls`
- `PUT` `/v3/{pid}/vpc/acls/{acl_id}`

## OMS (5)

- `DELETE` `/v2/{pid}/tasks/{task_id}`
- `GET` `/v2/{pid}/tasks/{task_id}`
- `GET` `/v2/{pid}/tasks`
- `POST` `/v2/{pid}/tasks/{task_id}/stop`
- `POST` `/v2/{pid}/tasks`

## RDS (1)

- `GET` `/v3/{pid}/flavors`

## RDS Extras (27)

- `DELETE` `/v3/{pid}/configurations/{configuration_id}`
- `DELETE` `/v3/{pid}/instances/{instance_id}/databases/{db_name}`
- `DELETE` `/v3/{pid}/instances/{instance_id}/db-users/{user_name}`
- `DELETE` `/v3/{pid}/instances/{instance_id}/replicas/{replica_id}`
- `DELETE` `/v3/{pid}/rds/backups/{backup_id}`
- `GET` `/v3/{pid}/configurations/{configuration_id}`
- `GET` `/v3/{pid}/configurations`
- `GET` `/v3/{pid}/instances/{instance_id}/databases`
- `GET` `/v3/{pid}/instances/{instance_id}/db-users`
- `GET` `/v3/{pid}/instances/{instance_id}/error-logs`
- `GET` `/v3/{pid}/instances/{instance_id}/parameters`
- `GET` `/v3/{pid}/instances/{instance_id}/replicas`
- `GET` `/v3/{pid}/instances/{instance_id}/slow-logs`
- `GET` `/v3/{pid}/rds/backups/{backup_id}`
- `GET` `/v3/{pid}/rds/backups`
- `POST` `/v3/{pid}/configurations/{configuration_id}/apply`
- `POST` `/v3/{pid}/configurations`
- `POST` `/v3/{pid}/instances/{instance_id}/action`
- `POST` `/v3/{pid}/instances/{instance_id}/databases`
- `POST` `/v3/{pid}/instances/{instance_id}/db-users`
- `POST` `/v3/{pid}/instances/{instance_id}/failover`
- `POST` `/v3/{pid}/instances/{instance_id}/replicas`
- `POST` `/v3/{pid}/instances/{instance_id}/restore`
- `POST` `/v3/{pid}/instances/{instance_id}/switchover`
- `POST` `/v3/{pid}/rds/backups`
- `PUT` `/v3/{pid}/configurations/{configuration_id}`
- `PUT` `/v3/{pid}/instances/{instance_id}/parameters`

## SFS (5)

- `DELETE` `/v2/{pid}/shares/{share_id}`
- `GET` `/v2/{pid}/shares/{share_id}`
- `GET` `/v2/{pid}/shares`
- `POST` `/v2/{pid}/shares/{share_id}/action`
- `POST` `/v2/{pid}/shares`

## SMN (13)

- `DELETE` `/v2/{pid}/notifications/message_templates/{message_template_id}`
- `DELETE` `/v2/{pid}/notifications/topics/{topic_urn}/subscriptions/{sub_urn}`
- `DELETE` `/v2/{pid}/notifications/topics/{topic_urn}`
- `GET` `/v2/{pid}/notifications/message_templates/{message_template_id}`
- `GET` `/v2/{pid}/notifications/message_templates`
- `GET` `/v2/{pid}/notifications/topics/{topic_urn}/subscriptions`
- `GET` `/v2/{pid}/notifications/topics/{topic_urn}`
- `GET` `/v2/{pid}/notifications/topics`
- `POST` `/v2/{pid}/notifications/message_templates`
- `POST` `/v2/{pid}/notifications/topics/{topic_urn}/publish`
- `POST` `/v2/{pid}/notifications/topics/{topic_urn}/subscriptions`
- `POST` `/v2/{pid}/notifications/topics`
- `PUT` `/v2/{pid}/notifications/topics/{topic_urn}`

## SMS (10)

- `DELETE` `/v3/{pid}/sources/{source_id}`
- `DELETE` `/v3/{pid}/tasks/{task_id}`
- `GET` `/v3/{pid}/sources/{source_id}`
- `GET` `/v3/{pid}/sources`
- `GET` `/v3/{pid}/tasks/{task_id}`
- `GET` `/v3/{pid}/tasks`
- `GET` `/v3/{pid}/templates`
- `POST` `/v3/{pid}/sources`
- `POST` `/v3/{pid}/tasks`
- `POST` `/v3/{pid}/templates`

## SWR (7)

- `DELETE` `/v2/{pid}/namespaces/{namespace}/repos/{repo}`
- `GET` `/v2/{pid}/namespaces/{namespace}/repos/{repo}/tags`
- `GET` `/v2/{pid}/namespaces/{namespace}/repos/{repo}`
- `GET` `/v2/{pid}/namespaces/{namespace}/repos`
- `GET` `/v2/{pid}/namespaces`
- `POST` `/v2/{pid}/namespaces/{namespace}/repos`
- `POST` `/v2/{pid}/namespaces`

## ServiceStage (9)

- `DELETE` `/v2/{pid}/cas/applications/{app_id}`
- `DELETE` `/v2/{pid}/cas/environments/{env_id}`
- `GET` `/v2/{pid}/cas/applications/{app_id}/components`
- `GET` `/v2/{pid}/cas/applications/{app_id}`
- `GET` `/v2/{pid}/cas/applications`
- `GET` `/v2/{pid}/cas/environments`
- `POST` `/v2/{pid}/cas/applications/{app_id}/components`
- `POST` `/v2/{pid}/cas/applications`
- `POST` `/v2/{pid}/cas/environments`

## TMS (5)

- `GET` `/v1.0/project-tags/resources`
- `GET` `/v1.0/project-tags/tags`
- `POST` `/v1.0/project-tags/create-or-delete`
- `POST` `/v1.0/project-tags/resources`
- `POST` `/v2.0/project-tags/resource-tags/action`

## VOD (10)

- `DELETE` `/v1/{pid}/assets/{asset_id}`
- `DELETE` `/v1/{pid}/transcode-templates/{template_id}`
- `GET` `/v1/{pid}/assets/{asset_id}`
- `GET` `/v1/{pid}/assets`
- `GET` `/v1/{pid}/categories`
- `GET` `/v1/{pid}/transcode-templates`
- `POST` `/v1/{pid}/assets/{asset_id}/upload`
- `POST` `/v1/{pid}/assets`
- `POST` `/v1/{pid}/categories`
- `POST` `/v1/{pid}/transcode-templates`

## VPC (34)

- `DELETE` `/v1/{pid}/ports/{port_id}`
- `DELETE` `/v1/{pid}/publicips/{eip_id}`
- `DELETE` `/v1/{pid}/security-group-rules/{rule_id}`
- `DELETE` `/v1/{pid}/security-groups/{sg_id}`
- `DELETE` `/v1/{pid}/subnets/{subnet_id}`
- `DELETE` `/v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}`
- `DELETE` `/v1/{pid}/vpcs/{vpc_id}`
- `GET` `/v1/{pid}/ports/{port_id}`
- `GET` `/v1/{pid}/ports`
- `GET` `/v1/{pid}/publicips/{eip_id}`
- `GET` `/v1/{pid}/publicips`
- `GET` `/v1/{pid}/security-group-rules/{rule_id}`
- `GET` `/v1/{pid}/security-group-rules`
- `GET` `/v1/{pid}/security-groups/{sg_id}`
- `GET` `/v1/{pid}/security-groups`
- `GET` `/v1/{pid}/subnets/{subnet_id}`
- `GET` `/v1/{pid}/subnets`
- `GET` `/v1/{pid}/vpcs/{vpc_id}`
- `GET` `/v1/{pid}/vpcs`
- `GET` `/v2.0/{pid}/bandwidths/{bandwidth_id}`
- `GET` `/v2.0/{pid}/bandwidths`
- `POST` `/v1/{pid}/ports`
- `POST` `/v1/{pid}/publicips`
- `POST` `/v1/{pid}/security-group-rules`
- `POST` `/v1/{pid}/security-groups`
- `POST` `/v1/{pid}/subnets`
- `POST` `/v1/{pid}/vpcs/{vpc_id}/subnets`
- `POST` `/v1/{pid}/vpcs`
- `PUT` `/v1/{pid}/ports/{port_id}`
- `PUT` `/v1/{pid}/publicips/{eip_id}`
- `PUT` `/v1/{pid}/security-groups/{sg_id}`
- `PUT` `/v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}`
- `PUT` `/v1/{pid}/vpcs/{vpc_id}`
- `PUT` `/v2.0/{pid}/bandwidths/{bandwidth_id}`

## VPC Peering (7)

- `DELETE` `/v2.0/{pid}/vpc-peerings/{peering_id}`
- `GET` `/v2.0/{pid}/vpc-peerings/{peering_id}`
- `GET` `/v2.0/{pid}/vpc-peerings`
- `POST` `/v2.0/{pid}/vpc-peerings`
- `PUT` `/v2.0/{pid}/vpc-peerings/{peering_id}/accept`
- `PUT` `/v2.0/{pid}/vpc-peerings/{peering_id}/reject`
- `PUT` `/v2.0/{pid}/vpc-peerings/{peering_id}`

## VPC Routes (7)

- `DELETE` `/v1/{pid}/vpc/routetables/{rt_id}/routes/{route_id}`
- `DELETE` `/v1/{pid}/vpc/routetables/{rt_id}`
- `GET` `/v1/{pid}/vpc/routetables/{rt_id}`
- `GET` `/v1/{pid}/vpc/routetables`
- `POST` `/v1/{pid}/vpc/routetables/{rt_id}/routes`
- `POST` `/v1/{pid}/vpc/routetables`
- `PUT` `/v1/{pid}/vpc/routetables/{rt_id}`

## VPN (8)

- `DELETE` `/v5/{pid}/vpn-connections/{connection_id}`
- `DELETE` `/v5/{pid}/vpn-gateways/{gateway_id}`
- `GET` `/v5/{pid}/vpn-connections/{connection_id}`
- `GET` `/v5/{pid}/vpn-connections`
- `GET` `/v5/{pid}/vpn-gateways/{gateway_id}`
- `GET` `/v5/{pid}/vpn-gateways`
- `POST` `/v5/{pid}/vpn-connections`
- `POST` `/v5/{pid}/vpn-gateways`

## WAF (10)

- `DELETE` `/v1/{pid}/waf/hosts/{domain_id}`
- `GET` `/v1/{pid}/waf/hosts/{domain_id}`
- `GET` `/v1/{pid}/waf/hosts`
- `GET` `/v1/{pid}/waf/policies/{policy_id}/rules`
- `GET` `/v1/{pid}/waf/policies/{policy_id}`
- `GET` `/v1/{pid}/waf/policies`
- `POST` `/v1/{pid}/waf/hosts`
- `POST` `/v1/{pid}/waf/policies/{policy_id}/rules`
- `POST` `/v1/{pid}/waf/policies`
- `PUT` `/v1/{pid}/waf/hosts/{domain_id}`

