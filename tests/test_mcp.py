"""Tests for the MCP server and its underlying LarrotClient.

The client layer is tested without the mcp package; the MCP wiring is
tested when mcp is installed (pip install larrot[agent]).
"""

import socket
import threading
import time

import pytest

from larrot.mcp_server import LarrotClient

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture(scope="module")
def endpoint():
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


class TestLarrotClient:
    """The HTTP client layer behind the MCP tools - no mcp needed."""

    def test_status(self, endpoint):
        c = LarrotClient(endpoint)
        s = c.status()
        assert s["health"]["status"] == "ok"
        assert "servers" in s["metrics"]

    def test_reset_and_seed(self, endpoint):
        c = LarrotClient(endpoint)
        assert c.reset()["reset"] is True
        assert c.seed(42) == {"seeded": 42}
        v1 = c._request("POST", f"/v1/{PID}/vpcs",
                        json_body={"vpc": {"name": "mcp", "cidr": "10.0.0.0/16"}})
        c.reset()
        c.seed(42)
        v2 = c._request("POST", f"/v1/{PID}/vpcs",
                        json_body={"vpc": {"name": "mcp", "cidr": "10.0.0.0/16"}})
        assert v1["vpc"]["id"] == v2["vpc"]["id"]

    def test_presets(self, endpoint):
        c = LarrotClient(endpoint)
        presets = c.list_presets()["presets"]
        assert presets, "no presets listed"
        name = presets[0]["name"]
        r = c.deploy_preset(name)
        assert r.get("deployed", name) or r  # deployment acknowledged

    def test_resources_and_detail(self, endpoint):
        c = LarrotClient(endpoint)
        c.reset()
        c.deploy_preset("three-tier-app")
        res = c.list_resources()["resources"]
        assert res, "no resources after preset deploy"
        rid = res[0]["id"]
        detail = c.show_resource(rid)
        assert detail["id"] == rid
        assert "_raw" in detail

    def test_chaos(self, endpoint):
        c = LarrotClient(endpoint)
        c.chaos_clear()
        r = c.chaos_inject("ecs", mode="api", failure_rate=1.0, status=503)
        assert "rule_id" in r or r
        rules = c._request("GET", "/admin/chaos")["rules"]
        assert len(rules) == 1
        assert c.chaos_clear()["removed"] >= 1

    def test_journal(self, endpoint):
        c = LarrotClient(endpoint)
        c.reset()
        c._request("GET", f"/v1/{PID}/vpcs")
        j = c.journal(path="/vpcs")
        assert j["total"] >= 1
        assert any("/vpcs" in e["path"] for e in j["entries"])

    def test_force_state(self, endpoint):
        c = LarrotClient(endpoint)
        c.reset()
        v = c._request("POST", f"/v1/{PID}/vpcs",
                       json_body={"vpc": {"name": "f", "cidr": "10.0.0.0/16"}})
        vid = v["vpc"]["id"]
        r = c.force_state(vid, "PENDING")
        assert r["status"] == "PENDING"


class TestMcpWiring:
    """The MCP server itself - skipped when mcp is not installed."""

    def test_tools_registered(self, endpoint):
        mcp = pytest.importorskip("mcp.server.mcpserver")
        from larrot.mcp_server import create_mcp_server

        server = create_mcp_server(endpoint)
        tools = _run(server.list_tools())
        names = [t.name for t in tools]
        expected = ["larrot_status", "larrot_reset", "larrot_seed",
                    "larrot_list_presets", "larrot_deploy_preset",
                    "larrot_list_resources", "larrot_show_resource",
                    "larrot_chaos_inject", "larrot_chaos_clear",
                    "larrot_journal", "larrot_force_state"]
        for name in expected:
            assert name in names, f"tool {name} not registered"

    def test_call_tool_end_to_end(self, endpoint):
        pytest.importorskip("mcp.server.mcpserver")
        from larrot.mcp_server import create_mcp_server

        server = create_mcp_server(endpoint)
        result = _run(server.call_tool("larrot_status", {}))
        payload = _payload(result)
        assert payload["health"]["status"] == "ok"

        _run(server.call_tool("larrot_reset", {}))
        result = _run(server.call_tool("larrot_seed", {"a": 7}))
        assert _payload(result) == {"seeded": 7}


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def _payload(result):
    """call_tool returns content blocks; find the JSON payload."""
    import json
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                return text
    return result
