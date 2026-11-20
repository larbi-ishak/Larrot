# SDK Integration Examples

How to wire real Huawei Cloud SDKs against the simulator. The only change is the
endpoint URL — everything else stays identical to production code.

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

# List servers — identical to production code
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
    # This is the CORRECT behavior — the simulator matches production

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
