"""Optional MITM proxy mode: `larrot proxy`.

Clients keep Huawei Cloud's real endpoints (*.myhuaweicloud.com) and set
HTTPS_PROXY to Larrot; the proxy rewrites emulated domains to the local
simulator, so KooCLI, the official SDKs, and the Terraform provider work
with zero client configuration. Non-Huawei hosts are relayed unchanged.

Requires the optional dependency:  pip install larrot[proxy]

The proxy binds 127.0.0.1 by default. mitmproxy generates its CA on first
run (~/.mitmproxy/mitmproxy-ca-cert.pem); HTTPS clients must trust it.
"""

import logging

logger = logging.getLogger("larrot")

HUAWEI_DOMAIN = "myhuaweicloud.com"
DEFAULT_LISTEN_PORT = 8780


def upstream_for(host: str, rest_port: int = 8200, obs_port: int = 8201):
    """Which local upstream serves this host? None = not a Huawei domain.

    OBS buckets use bucket.obs.<region>.myhuaweicloud.com and the OBS
    service itself obs.<region>.myhuaweicloud.com - both go to the OBS
    port. Everything else under myhuaweicloud.com goes to the REST port.
    """
    h = (host or "").lower().rstrip(".")
    if h != HUAWEI_DOMAIN and not h.endswith("." + HUAWEI_DOMAIN):
        return None
    parts = h.split(".")
    if "obs" in parts:
        return ("127.0.0.1", obs_port)
    return ("127.0.0.1", rest_port)


class LarrotAddon:
    """mitmproxy addon: rewrite Huawei Cloud domains to the local simulator."""

    def __init__(self, rest_port: int = 8200, obs_port: int = 8201):
        self.rest_port = rest_port
        self.obs_port = obs_port
        self.intercepted = 0
        self.relayed = 0

    def request(self, flow):
        target = upstream_for(flow.request.host, self.rest_port, self.obs_port)
        if target is None:
            self.relayed += 1
            return  # not a Huawei Cloud domain: mitmproxy relays as usual
        self.intercepted += 1
        flow.request.scheme = "http"
        flow.request.host = target[0]
        flow.request.port = target[1]


def run_proxy(listen_port: int = DEFAULT_LISTEN_PORT, rest_port: int = 8200,
              obs_port: int = 8201, listen_host: str = "127.0.0.1"):
    """Run the proxy until interrupted. Raises if mitmproxy is missing."""
    try:
        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster
    except ImportError as e:
        raise SystemExit(
            "larrot proxy needs the optional dependency mitmproxy.\n"
            "Install it with:  pip install larrot[proxy]") from e

    import asyncio

    async def _run():
        opts = options.Options(listen_host=listen_host, listen_port=listen_port)
        master = DumpMaster(opts)
        master.addons.add(LarrotAddon(rest_port, obs_port))
        logger.info("larrot proxy on http://%s:%d -> REST :%d, OBS :%d",
                    listen_host, listen_port, rest_port, obs_port)
        await master.run()

    asyncio.run(_run())
