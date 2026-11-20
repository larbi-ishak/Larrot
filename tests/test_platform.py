"""Platform feature tests: dependency guards, chaos, explorer, presets (ROADMAP phase 1-2)."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# 1.1 Deletion dependency guards
# ---------------------------------------------------------------------------

class TestDependencyGuards:
    def test_subnet_with_ports_409(self, client):
        """A subnet with live ports refuses deletion (creating a server makes a port)."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "guard-subnet"}})
        sid = r.json()["serverIds"][0]

        # The server's port sits on the project's seeded subnet
        r = client.get(f"/v1/{PID}/ports?device_id={sid}")
        subnet_id = r.json()["ports"][0]["fixed_ips"][0]["subnet_id"]

        r = client.delete(f"/v1/{PID}/subnets/{subnet_id}")
        assert r.status_code == 409
        assert r.json()["code"] == "VPC.0203"
        assert "ports" in r.json()["message"]

        # Subnet still exists
        assert client.get(f"/v1/{PID}/subnets/{subnet_id}").status_code == 200

    def test_subnet_without_ports_deletes(self, client):
        """A fresh subnet with no ports deletes cleanly."""
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "guard-vpc", "cidr": "10.99.0.0/16"}}).json()["vpc"]
        r = client.post(f"/v1/{PID}/subnets",
                        json={"subnet": {"name": "guard-subnet", "vpc_id": vpc["id"],
                                          "cidr": "10.99.1.0/24"}})
        subnet_id = r.json()["subnet"]["id"]
        assert client.delete(f"/v1/{PID}/subnets/{subnet_id}").status_code == 204

    def test_security_group_in_use_409(self, client):
        """A security group referenced by a server refuses deletion."""
        r = client.post(f"/v1/{PID}/security-groups",
                        json={"security_group": {"name": "web-sg"}})
        sg_id = r.json()["security_group"]["id"]

        # Server referencing the SG by name
        client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                      "name": "sg-guard",
                                      "security_groups": [{"name": "web-sg"}]}})

        r = client.delete(f"/v1/{PID}/security-groups/{sg_id}")
        assert r.status_code == 409
        assert r.json()["code"] == "VPC.0604"

    def test_security_group_unused_deletes(self, client):
        r = client.post(f"/v1/{PID}/security-groups",
                        json={"security_group": {"name": "free-sg"}})
        sg_id = r.json()["security_group"]["id"]
        assert client.delete(f"/v1/{PID}/security-groups/{sg_id}").status_code == 204

    def test_vpc_with_subnets_400(self, client):
        """VPC with subnets refuses deletion (pre-existing guard)."""
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "vpc-guard", "cidr": "10.98.0.0/16"}}).json()["vpc"]
        client.post(f"/v1/{PID}/subnets",
                    json={"subnet": {"name": "vpc-guard-sub", "vpc_id": vpc["id"],
                                      "cidr": "10.98.1.0/24"}})
        r = client.delete(f"/v1/{PID}/vpcs/{vpc['id']}")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 1.2 Chaos fault injection
# ---------------------------------------------------------------------------

class TestChaos:
    def test_api_mode_injects_error(self, client):
        """failure_rate=1.0 api rule: every matched ECS request gets the error."""
        r = client.post("/admin/chaos", json={
            "service": "ecs", "failure_rate": 1.0, "mode": "api",
            "status": 500, "error_code": "Ecs.9999", "error_msg": "chaos!",
        })
        assert r.status_code == 200
        rule_id = r.json()["rule"]["rule_id"]

        r = client.get(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 500
        assert r.json()["error_code"] == "Ecs.9999"
        assert r.json()["chaos_rule_id"] == rule_id

        # Other services unaffected
        assert client.get(f"/v1/{PID}/vpcs").status_code == 200

        # Remove the rule -> back to normal
        assert client.delete(f"/admin/chaos/{rule_id}").status_code == 204
        assert client.get(f"/v1/{PID}/cloudservers/detail").status_code == 200

    def test_api_mode_with_latency(self, client):
        import time
        client.post("/admin/chaos", json={
            "service": "vpc", "failure_rate": 1.0, "mode": "api",
            "status": 429, "error_code": "APIGW.0308", "latency_ms": 500,
        })
        t0 = time.monotonic()
        r = client.get(f"/v1/{PID}/vpcs")
        elapsed = time.monotonic() - t0
        assert r.status_code == 429
        assert elapsed >= 0.4  # latency was injected
        client.post("/admin/chaos/reset")

    def test_job_mode_fails_async_jobs(self, client):
        """API succeeds, but the async job FAILs with the injected error."""
        client.post("/admin/chaos", json={
            "service": "evs", "failure_rate": 1.0, "mode": "job",
            "error_code": "EVS.8888", "error_msg": "chaos job failure",
        })
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "chaos-vol"}})
        assert r.status_code == 202  # API level: accepted
        job_id = r.json()["job_id"]

        sim = client.app.state.sim
        assert sim.jobs.complete_now(job_id) is True
        job = sim.jobs.jobs[job_id]
        assert job.status == "FAIL"
        assert job.error_code == "EVS.8888"

        # The volume never became available (effect skipped)
        vid = r.json()["volume_ids"][0]
        assert sim.volumes[vid]["status"] == "creating"

        client.post("/admin/chaos/reset")

    def test_job_mode_spares_unmatched(self, client):
        client.post("/admin/chaos", json={
            "service": "dws", "failure_rate": 1.0, "mode": "job"})
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "spared-vol"}})
        job_id = r.json()["job_id"]
        sim = client.app.state.sim
        sim.jobs.complete_now(job_id)
        assert sim.jobs.jobs[job_id].status == "SUCCESS"
        client.post("/admin/chaos/reset")

    def test_rule_validation(self, client):
        """Invalid rules are rejected with 400."""
        r = client.post("/admin/chaos", json={"failure_rate": 1.0})
        assert r.status_code == 400  # no service/path_contains
        r = client.post("/admin/chaos", json={"service": "not-a-service"})
        assert r.status_code == 400
        r = client.post("/admin/chaos", json={"service": "ecs", "failure_rate": 5})
        assert r.status_code == 400
        r = client.post("/admin/chaos", json={"service": "ecs", "mode": "bogus"})
        assert r.status_code == 400

    def test_list_and_reset(self, client):
        client.post("/admin/chaos", json={"service": "ecs", "failure_rate": 0.5})
        client.post("/admin/chaos", json={"service": "vpc", "failure_rate": 0.5})
        r = client.get("/admin/chaos")
        assert len(r.json()["rules"]) == 2
        r = client.post("/admin/chaos/reset")
        assert r.json()["removed"] == 2
        assert client.get("/admin/chaos").json()["rules"] == []

    def test_path_contains_matching(self, client):
        """Raw path substring matching (for services not in the keyword map)."""
        client.post("/admin/chaos", json={
            "path_contains": "chat/completions", "failure_rate": 1.0,
            "status": 503, "error_code": "MAAS.CHAOS"})
        r = client.post("/v1/chat/completions",
                        json={"model": "DeepSeek-V3", "messages": []})
        assert r.status_code == 503
        client.post("/admin/chaos/reset")


# ---------------------------------------------------------------------------
# 1.3 Resource explorer
# ---------------------------------------------------------------------------

class TestExplorer:
    def test_inventory_and_filters(self, client):
        client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                      "name": "explorer-vm"}})
        r = client.get("/admin/resources")
        assert r.status_code == 200
        items = r.json()["resources"]
        assert any(x["type"] == "ecs.server" and x["name"] == "explorer-vm"
                   for x in items)

        # type filter
        r = client.get("/admin/resources?type=ecs.server")
        assert all(x["type"] == "ecs.server" for x in r.json()["resources"])

        # project filter: HCS project has no servers from this test
        r = client.get(f"/admin/resources?type=ecs.server&project={HCS_PID}")
        assert all(x["project_id"] == HCS_PID for x in r.json()["resources"])

    def test_find_by_id(self, client):
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "find-me"}})
        vid = r.json()["volume_ids"][0]
        r = client.get(f"/admin/resources/{vid}")
        assert r.status_code == 200
        assert r.json()["type"] == "evs.volume"
        assert client.get("/admin/resources/no-such-id").status_code == 404

    def test_graph_server(self, client):
        """Server graph shows its NIC port and root volume."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "graph-vm"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/admin/graph/{sid}")
        assert r.status_code == 200
        edges = r.json()["edges"]
        rels = {(e["type"], e["relation"]) for e in edges}
        assert ("vpc.port", "has_nic") in rels
        assert ("evs.volume", "attached_volume") in rels

    def test_graph_vpc(self, client):
        """A server in the VPC gives it both subnets and ports."""
        client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                      "name": "graph-vpc-vm"}})
        project_vpc = client.app.state.sim.project(PID)["vpc_id"]
        r = client.get(f"/admin/graph/{project_vpc}")
        edges = r.json()["edges"]
        assert any(e["relation"] == "contains_subnet" for e in edges)
        assert any(e["relation"] == "has_port" for e in edges)

    def test_graph_unknown_404(self, client):
        assert client.get("/admin/graph/no-such-id").status_code == 404


# ---------------------------------------------------------------------------
# 2.2 Preset environments
# ---------------------------------------------------------------------------

class TestPresets:
    def test_list_presets(self, client):
        r = client.get("/admin/preset")
        assert r.status_code == 200
        names = {p["name"] for p in r.json()["presets"]}
        assert {"three-tier-app", "dr", "multi-tenant"} <= names

    def test_unknown_preset_404(self, client):
        r = client.post("/admin/preset/not-a-preset")
        assert r.status_code == 404
        assert "available" in r.json()

    def test_three_tier_app(self, client):
        r = client.post("/admin/preset/three-tier-app")
        assert r.status_code == 200
        ids = r.json()

        # Servers are ACTIVE and visible through the normal API
        for sid in ids["servers"]:
            srv = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]
            assert srv["status"] == "ACTIVE"
            assert srv["security_groups"] == [{"name": "three-tier-sg"}]

        # ELB with listener + pool + members
        lb = client.get(f"/v2/{PID}/elb/loadbalancers/{ids['loadbalancer']}").json()["loadbalancer"]
        assert lb["listeners"] and lb["pools"]
        members = client.get(f"/v2/{PID}/elb/pools/{ids['pool']}/members").json()
        assert len(members.get("members", [])) == 2

        # EIP exists and is DOWN (not bound)
        eip = client.get(f"/v1/{PID}/publicips/{ids['eip']}").json()["publicip"]
        assert eip["status"] == "DOWN"

        # The preset SG is now in use -> deletion guard applies
        r = client.delete(f"/v1/{PID}/security-groups/{ids['security_group']}")
        assert r.status_code == 409

    def test_dr_preset(self, client):
        r = client.post("/admin/preset/dr")
        ids = r.json()

        vol = client.get(f"/v2/{PID}/cloudvolumes/{ids['volume']}").json()["volume"]
        assert vol["status"] == "available"
        assert vol["size"] == 50

        snap = client.get(f"/v2/{PID}/cloudsnapshots/{ids['snapshot']}").json()["snapshot"]
        assert snap["status"] == "available"

        vault = client.get(f"/v3/{PID}/vaults/{ids['vault']}").json()["vault"]
        assert len(vault["resources"]) == 2

        backup = client.get(f"/v3/{PID}/backups/{ids['backup']}").json()["backup"]
        assert backup["status"] == "available"
        assert backup["extend_info"]["contain_system_disk"] is True

    def test_multi_tenant_preset(self, client):
        r = client.post("/admin/preset/multi-tenant")
        tenants = r.json()["tenants"]
        assert set(tenants) == {"ap-southeast-1", "tr-west-1"}

        # Each project sees its own server, not the other's
        for region, ids in tenants.items():
            pid = PID if region == "ap-southeast-1" else HCS_PID
            assert client.get(f"/v1/{pid}/cloudservers/{ids['server']}").status_code == 200
            other = HCS_PID if pid == PID else PID
            assert client.get(f"/v1/{other}/cloudservers/{ids['server']}").status_code == 404
