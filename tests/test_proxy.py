"""Tests for the optional MITM proxy mode (larrot proxy)."""

import pytest

from larrot.proxy import upstream_for


class TestUpstreamRouting:
    """Pure routing logic - no mitmproxy needed."""

    def test_rest_domains(self):
        assert upstream_for("ecs.ap-southeast-1.myhuaweicloud.com") == ("127.0.0.1", 8200)
        assert upstream_for("vpc.ap-southeast-1.myhuaweicloud.com") == ("127.0.0.1", 8200)
        assert upstream_for("iam.ap-southeast-1.myhuaweicloud.com") == ("127.0.0.1", 8200)
        assert upstream_for("myhuaweicloud.com") == ("127.0.0.1", 8200)

    def test_obs_domains(self):
        assert upstream_for("obs.ap-southeast-1.myhuaweicloud.com") == ("127.0.0.1", 8201)
        assert upstream_for("my-bucket.obs.ap-southeast-1.myhuaweicloud.com") == ("127.0.0.1", 8201)

    def test_custom_ports(self):
        assert upstream_for("ecs.ap-southeast-1.myhuaweicloud.com",
                            rest_port=9000, obs_port=9001) == ("127.0.0.1", 9000)
        assert upstream_for("obs.ap-southeast-1.myhuaweicloud.com",
                            rest_port=9000, obs_port=9001) == ("127.0.0.1", 9001)

    def test_non_huawei_relayed(self):
        assert upstream_for("example.com") is None
        assert upstream_for("ecs.amazonaws.com") is None
        assert upstream_for("fakemyhuaweicloud.com") is None  # suffix must match exactly
        assert upstream_for("") is None

    def test_case_and_trailing_dot(self):
        assert upstream_for("ECS.AP-SOUTHEAST-1.MYHUaweicloud.COM.") == ("127.0.0.1", 8200)


class TestAddonRewrite:
    """The mitmproxy addon rewrites emulated domains (needs mitmproxy)."""

    def test_rewrite(self):
        mitmproxy = pytest.importorskip("mitmproxy")

        from larrot.proxy import LarrotAddon

        class FakeRequest:
            def __init__(self, host):
                self.host = host
                self.scheme = "https"
                self.port = 443

        class FakeFlow:
            def __init__(self, host):
                self.request = FakeRequest(host)

        addon = LarrotAddon()
        flow = FakeFlow("ecs.ap-southeast-1.myhuaweicloud.com")
        addon.request(flow)
        assert flow.request.scheme == "http"
        assert flow.request.host == "127.0.0.1"
        assert flow.request.port == 8200
        assert addon.intercepted == 1

        # Non-Huawei: untouched, counted as relayed
        flow2 = FakeFlow("registry.terraform.io")
        addon.request(flow2)
        assert flow2.request.host == "registry.terraform.io"
        assert flow2.request.scheme == "https"
        assert addon.relayed == 1
        assert mitmproxy.__name__ == "mitmproxy"
