"""Compatibility tests against Huawei's OFFICIAL Python SDK.

These prove Larrot speaks the real wire protocol: the actual client
library that users run in production works unchanged against it.
Skipped when the SDK is not installed (pip install larrot[sdk]).
"""

import socket
import threading
import time

import pytest

pytest.importorskip("huaweicloudsdkcore", reason="official SDK not installed (pip install larrot[sdk])")

from huaweicloudsdkcore.auth.credentials import BasicCredentials  # noqa: E402
from huaweicloudsdkcore.http.http_config import HttpConfig  # noqa: E402
from huaweicloudsdkecs.v2 import EcsClient  # noqa: E402
from huaweicloudsdkecs.v2.model import (  # noqa: E402
    ListFlavorsRequest,
    ListServersDetailsRequest,
    NovaListAvailabilityZonesRequest,
)
from huaweicloudsdkeip.v2 import EipClient  # noqa: E402
from huaweicloudsdkeip.v2.model import ListPublicipsRequest  # noqa: E402
from huaweicloudsdkevs.v2 import EvsClient  # noqa: E402
from huaweicloudsdkevs.v2.model import ListVolumesRequest  # noqa: E402
from huaweicloudsdkiam.v3 import IamClient  # noqa: E402
from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest  # noqa: E402
from huaweicloudsdkims.v2 import ImsClient  # noqa: E402
from huaweicloudsdkims.v2.model import ListImagesRequest  # noqa: E402
from huaweicloudsdkvpc.v2 import VpcClient  # noqa: E402
from huaweicloudsdkvpc.v2.model import (  # noqa: E402
    CreateVpcOption,
    CreateVpcRequestBody,
    CreateVpcRequest,
    ListVpcsRequest,
)

AK = "HWYSIMAK00000001"
SK = "HWYSIMSK00000001"
PID = "79814d675f6142d9b4a8ee417b924444"
REGION = "ap-southeast-1"


@pytest.fixture(scope="module")
def endpoint():
    """A live Larrot server on a free port (the SDK makes real HTTP calls)."""
    import httpx
    import uvicorn

    from larrot.app import create_app

    app = create_app()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1",
                                           port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.3)
            break
        except Exception:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def _client(cls, endpoint, project=PID):
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = True
    cred = BasicCredentials().with_ak(AK).with_sk(SK).with_project_id(project)
    return (cls.new_builder()
            .with_credentials(cred)
            .with_endpoint(endpoint)
            .with_http_config(config)
            .build())


class TestOfficialSdk:
    """The real Huawei client libraries against Larrot, unchanged."""

    def test_iam_list_projects(self, endpoint):
        c = _client(IamClient, endpoint, project=None)
        r = c.keystone_list_projects(KeystoneListProjectsRequest(name=REGION))
        assert r.projects, "no projects returned"
        assert any(p.name == REGION for p in r.projects)

    def test_ecs_list_flavors(self, endpoint):
        c = _client(EcsClient, endpoint)
        r = c.list_flavors(ListFlavorsRequest())
        assert r.flavors, "no flavors returned"
        assert any(f.id == "s6.large.2" for f in r.flavors)

    def test_ecs_availability_zones(self, endpoint):
        c = _client(EcsClient, endpoint)
        r = c.nova_list_availability_zones(NovaListAvailabilityZonesRequest())
        assert r.availability_zone_info, "no AZs returned"
        assert all(z.zone_state.available for z in r.availability_zone_info)

    def test_ecs_list_servers(self, endpoint):
        c = _client(EcsClient, endpoint)
        r = c.list_servers_details(ListServersDetailsRequest())
        assert r.count >= 0
        assert r.servers is not None

    def test_vpc_list_and_create(self, endpoint):
        c = _client(VpcClient, endpoint)
        r = c.list_vpcs(ListVpcsRequest())
        assert r.vpcs, "no VPCs returned"

        created = c.create_vpc(CreateVpcRequest(
            body=CreateVpcRequestBody(
                vpc=CreateVpcOption(name="sdk-test-vpc", cidr="10.100.0.0/16"))))
        assert created.vpc.id
        assert created.vpc.name == "sdk-test-vpc"
        assert created.vpc.status == "OK"

    def test_evs_list_volumes(self, endpoint):
        c = _client(EvsClient, endpoint)
        r = c.list_volumes(ListVolumesRequest())
        assert r.volumes is not None

    def test_eip_list_publicips(self, endpoint):
        c = _client(EipClient, endpoint)
        r = c.list_publicips(ListPublicipsRequest())
        assert r.publicips is not None

    def test_ims_list_images(self, endpoint):
        c = _client(ImsClient, endpoint)
        r = c.list_images(ListImagesRequest())
        assert r.images, "no images returned"
        assert any("Ubuntu" in (i.name or "") for i in r.images)
