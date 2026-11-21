"""MCP server: exposes Larrot's admin platform to coding agents.

Run alongside a Larrot server:

    larrot mcp                # stdio transport; LARROT_ENDPOINT overrides

Agents get tools for the whole admin platform: status, reset, seed,
presets, resources, chaos, the request journal, and state forcing -
everything needed to drive a local Huawei Cloud through a natural
test loop. Requires the optional dependency:  pip install larrot[agent]
"""


import httpx

DEFAULT_ENDPOINT = "http://127.0.0.1:8200"


class LarrotClient:
    """Thin HTTP client over the admin + public API.

    Kept separate from the MCP wiring so it can be tested (and used)
    without the mcp package installed.
    """

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT):
        self.endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(base_url=self.endpoint, timeout=15)

    # --- plumbing -----------------------------------------------------
    def _request(self, method: str, path: str, *, params=None, json_body=None):
        r = self._client.request(method, path, params=params, json=json_body)
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return {}
        return r.json()

    # --- tools ---------------------------------------------------------
    def status(self) -> dict:
        """Health, version, and resource counts of the running simulator."""
        health = self._request("GET", "/health")
        metrics = self._request("GET", "/metrics")
        return {"endpoint": self.endpoint, "health": health, "metrics": metrics}

    def reset(self) -> dict:
        """Wipe every resource and engine while the server keeps running."""
        return self._request("POST", "/admin/reset")

    def seed(self, a: int) -> dict:
        """Seed the ID generator so subsequent resource IDs are deterministic."""
        return self._request("POST", "/admin/seed", params={"a": a})

    def list_presets(self) -> dict:
        """List the deployable preset environments."""
        return self._request("GET", "/admin/preset")

    def deploy_preset(self, name: str) -> dict:
        """Deploy a preset environment (e.g. three-tier-app)."""
        return self._request("POST", f"/admin/preset/{name}")

    def list_resources(self, type: str = None, name: str = None) -> dict:
        """List simulated resources, optionally filtered by type or name."""
        params = {k: v for k, v in (("type", type), ("name", name)) if v}
        return self._request("GET", "/admin/resources", params=params or None)

    def show_resource(self, rid: str) -> dict:
        """Full detail (all properties) of one resource by id."""
        return self._request("GET", f"/admin/resources/{rid}")

    def chaos_inject(self, service: str, mode: str = "api",
                     failure_rate: float = 1.0, status: int = 500,
                     error_code: str = "SIM.CHAOS",
                     error_msg: str = "injected via MCP") -> dict:
        """Inject a chaos rule: fail calls to a service (api) or its jobs (job)."""
        return self._request("POST", "/admin/chaos", json_body={
            "service": service, "mode": mode, "failure_rate": failure_rate,
            "status": status, "error_code": error_code, "error_msg": error_msg})

    def chaos_clear(self) -> dict:
        """Remove all chaos rules."""
        return self._request("POST", "/admin/chaos/reset")

    def journal(self, method: str = None, path: str = None,
                status: int = None, limit: int = 50) -> dict:
        """Query the request journal: what the client actually sent."""
        params = {"limit": limit}
        if method:
            params["method"] = method
        if path:
            params["path"] = path
        if status is not None:
            params["status"] = status
        return self._request("GET", "/admin/requests", params=params)

    def force_state(self, rid: str, status: str) -> dict:
        """Force a resource into any state without waiting for side effects."""
        return self._request("PUT", f"/admin/state/{rid}",
                             json_body={"status": status})


INSTRUCTIONS = """Larrot is a local Huawei Cloud API simulator (LocalStack for
Huawei Cloud). Use these tools to control a running instance: deploy a preset
to get a realistic resource graph, seed for deterministic IDs, inject chaos to
test retry logic, force resource states instantly, and query the request
journal to verify what your code actually sent. Reset wipes everything."""


def create_mcp_server(endpoint: str = DEFAULT_ENDPOINT):
    """Build the MCPServer with all Larrot tools registered."""
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("larrot", instructions=INSTRUCTIONS)
    c = LarrotClient(endpoint)

    tools = [
        (c.status, "larrot_status",
         "Simulator health, version, and resource counts"),
        (c.reset, "larrot_reset",
         "Wipe every resource and engine; the server keeps running"),
        (c.seed, "larrot_seed",
         "Seed the ID generator for deterministic resource IDs"),
        (c.list_presets, "larrot_list_presets",
         "List deployable preset environments"),
        (c.deploy_preset, "larrot_deploy_preset",
         "Deploy a preset environment by name"),
        (c.list_resources, "larrot_list_resources",
         "List simulated resources, filtered by type or name"),
        (c.show_resource, "larrot_show_resource",
         "Full properties of one resource by id"),
        (c.chaos_inject, "larrot_chaos_inject",
         "Inject a chaos rule: fail API calls or async jobs of a service"),
        (c.chaos_clear, "larrot_chaos_clear",
         "Remove all chaos rules"),
        (c.journal, "larrot_journal",
         "Query the request journal: what the client actually sent"),
        (c.force_state, "larrot_force_state",
         "Force a resource into any state instantly"),
    ]
    for fn, name, description in tools:
        server.add_tool(fn, name=name, description=description)
    return server


def main(endpoint: str = None):
    """Entry point for `larrot mcp` (stdio transport)."""
    import os
    endpoint = endpoint or os.environ.get("LARROT_ENDPOINT", DEFAULT_ENDPOINT)
    server = create_mcp_server(endpoint)
    server.run()


if __name__ == "__main__":
    main()
