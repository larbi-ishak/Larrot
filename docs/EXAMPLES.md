# SDK Integration Examples

How to wire real Huawei Cloud SDKs against the simulator. The only change is the
endpoint URL: everything else stays identical to production code.

## Python SDK

```bash
pip install huaweicloudsdkecs huaweicloudsdkevs huaweicloudsdkvpc
```

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import (
    ListServersDetailsRequest,
    CreateServersRequest,
    CreateServersRequestBody,
    PostPaidServer,
    BatchStopServersRequest,
    BatchStopServersRequestBody,
    BatchStopServersOption,
    BatchStopServersOptionTypeEnum,
    ServerId,
)

# The ONLY difference from production: the endpoint URL
credentials = BasicCredentials() \
    .with_ak("HWYSIMAK00000001") \
    .with_sk("HWYSIMSK00000001") \
    .with_project_id("79814d675f6142d9b4a8ee417b924444")

client = EcsClient.newBuilder() \
    .withCredential(credentials) \
    .withEndpoint("http://127.0.0.1:8200") \
    .build()

# List servers: identical to production code
request = ListServersDetailsRequest().with_limit(10)
response = client.list_servers_details(request)
print(f"Found {response.count} servers")

# Create a server
server = PostPaidServer() \
    .with_image_ref("1ce5800a-e487-4c1b-b264-3353a39e2b4b") \
    .with_flavor_ref("s6.large.2") \
    .with_name("my-vm")

create_req = CreateServersRequest() \
    .with_body(CreateServersRequestBody().with_server(server))
create_resp = client.create_servers(create_req)
print(f"Created: {create_resp.server_ids}")

# Stop a server
stop_req = BatchStopServersRequest().with_body(
    BatchStopServersRequestBody().with_os_stop(
        BatchStopServersOption()
        .with_type(BatchStopServersOptionTypeEnum.SOFT)
        .with_servers([ServerId().with_id(create_resp.server_ids[0])])
    )
)
stop_resp = client.batch_stop_servers(stop_req)
print(f"Stopping… job: {stop_resp.job_id}")
```

## Node.js / TypeScript SDK

```bash
npm install @huaweicloud/huaweicloud-sdk-core @huaweicloud/huaweicloud-sdk-ecs
```

```typescript
import { BasicCredentials } from '@huaweicloud/huaweicloud-sdk-core';
import ecs from '@huaweicloud/huaweicloud-sdk-ecs';

const credentials = new BasicCredentials()
    .withAk('HWYSIMAK00000001')
    .withSk('HWYSIMSK00000001')
    .withProjectId('79814d675f6142d9b4a8ee417b924444');

const client = ecs.EcsClient.newBuilder()
    .withCredential(credentials)
    .withEndpoint('http://127.0.0.1:8200')
    .build();

// List servers
const response = await client.listServersDetails(
    new ecs.ListServersDetailsRequest().withLimit(10)
);
console.log(`Found ${response.count} servers`);
```

## OBS SDK (Python)

```bash
pip install esdk-obs-python
```

```python
from obs import ObsClient

# The ONLY difference: endpoint points at the simulator
obs_client = ObsClient(
    access_key_id='HWYSIMAK00000001',
    secret_access_key='HWYSIMSK00000001',
    server='http://127.0.0.1:8201',
    is_cname=False,       # path-style (required for local IP endpoints)
    signature='obs',
)

# Create a bucket
resp = obs_client.createBucket('my-bucket')
print(f"Bucket created: {resp.status}")

# Upload an object
resp = obs_client.putContent('my-bucket', 'hello.txt', 'Hello, World!')
print(f"Uploaded: {resp.status}")

# List objects
resp = obs_client.listObjects('my-bucket')
for obj in resp.body.contents:
    print(f"  {obj.key} ({obj.size} bytes)")
```

## The Ecs.0005 quirk (the /dev/vda rule)

This is the empirically-observed behavior change (~Oct-Nov 2026) that the simulator
reproduces exactly:

```python
# Create a NON-bootable data volume
volume_resp = evs_client.create_volume(CreateVolumeRequest().with_body(
    CreateVolumeRequestBody().with_volume(
        CreateVolumeOption().with_name("data").with_size(10).withVolumeType("SAS")
    )
))
volume_id = volume_resp.volume_ids[0]

# Try to attach it at /dev/vda → FAILS with Ecs.0005
try:
    ecs_client.attach_server_volume(AttachServerVolumeRequest()
        .with_server_id(server_id)
        .with_body(AttachServerVolumeRequestBody().with_volume_attachment(
            AttachServerVolumeOption()
            .with_volume_id(volume_id)
            .with_device("/dev/vda")  # ← this triggers Ecs.0005
        ))
    )
except ClientRequestException as e:
    assert e.error_code == "Ecs.0005"
    assert e.error_msg == "device is illegal"
    # This is the CORRECT behavior: the simulator matches production

# The workaround: create a BOOTABLE "carrier" volume from the gold image
carrier_resp = evs_client.create_volume(CreateVolumeRequest().with_body(
    CreateVolumeRequestBody().with_volume(
        CreateVolumeOption()
        .with_name("carrier")
        .with_size(40)
        .withVolumeType("SAS")
        .with_image_ref("d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21")  # ← bootable
    )
))
# Now the /dev/vda attach succeeds
```

## CBR: backing up a live OS disk

The spec says EVS snapshots can't capture an in-use system disk (§3.4), but CBR can:

```python
# EVS snapshot of an in-use volume → REJECTED
try:
    evs_client.create_snapshot(...)
except ClientRequestException as e:
    assert e.error_code == "EVS.1046"  # "volume status must be available"

# CBR checkpoint of the same running server → SUCCEEDS
vault_resp = cbr_client.create_vault(...)
cbr_client.add_vault_resource(vault_id, [server_id])
checkpoint = cbr_client.create_checkpoint(
    resources=[{"id": server_id, "type": "OS::Nova::Server"}]
)
# checkpoint.status: "protecting" → "available" (the live disk IS captured)
```

---

# Scenario-based testing examples

These mirror real workflows and are executable: each one is a passing test in
`tests/test_scenarios.py`. Run the whole set:

```bash
python3 -m pytest tests/test_scenarios.py -v
```

## S1: Deploy a three-tier web application

Network first, then compute, then exposure, then load balancing:

```python
vpc = vpc_client.create_vpc(CreateVpcRequest(
    body=CreateVpcRequestBody(vpc=CreateVpcOption(name="web-vpc", cidr="10.10.0.0/16")))).vpc
# subnet -> security group -> 2x ECS -> EIP bound to a port -> ELB
# (listener + pool + both servers as members)
```

Assert what a real deployment would assert: both servers ACTIVE, the EIP bound,
the pool holding two members, and `/admin/graph/{server_id}` showing the
topology (NIC + attached volumes).

## S2: Disaster recovery

```python
server -> volume -> snapshot (available) -> CBR vault (both resources)
       -> checkpoint -> backup available -> POST /backups/{id}/restore
       -> a replacement ECS is provisioned
```

The restore of a server backup provisions a new ECS with its root volume,
through the async job engine like the real service.

## S3: Tenant isolation

Create one server per project (ap-southeast-1 and tr-west-1). Assert each list
shows only its own, cross-project reads 404 in both directions, and the HCS
project keeps its sparse list view (no flavor) even with servers present.

## S4: Quota exhaustion

Fill the 100-instance quota in one batch create, assert the next create is
rejected with `405 Ecs.0015`, check `/cloudservers/limits` shows 100 used,
delete a batch, retry, and succeed. Quota enforcement lives in the ECS create
path, mirroring the limits view.

## S5: Failure recovery with chaos

```bash
curl -X POST http://127.0.0.1:8200/admin/chaos \
  -d '{"service":"ecs","mode":"job","failure_rate":1.0,"error_code":"Ecs.0900"}'
```

The create is accepted, the job FAILs with the injected code, the server stays
in BUILD. Reset the rules, retry, and the new server reaches ACTIVE. This is
how you test your client's retry and reconciliation logic against a broken
cloud.

## Try them in the console

Open `http://127.0.0.1:8200/console` while the scenario tests run: the
resource browser auto-refreshes every 3 seconds, and the chaos panel can
inject the S5 failure rule interactively.
