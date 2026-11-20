"""Scenario-based integration tests (ROADMAP: scenario testing).

Each test is a realistic end-to-end workflow, not a single API call:
  S1  Deploy a web application: VPC -> Subnet -> SG -> ECS x2 -> EIP -> ELB
  S2  Disaster recovery: ECS -> EVS -> snapshot -> CBR vault -> backup -> restore
  S3  Tenant isolation: resources in both projects never leak across
  S4  Quota exhaustion: fill the quota -> rejected -> free -> retry succeeds
  S5  Failure recovery: chaos-injected job failure -> inspect -> retry -> healthy
"""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
HCS_IMAGE = "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21"
FLAVOR = "s6.large.2"
HCS_FLAVOR = "s7n.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestS1DeployWebApp:
    def test_full_deployment(self, client):
        """VPC -> subnet -> SG -> 2 ECS -> EIP bound -> ELB with backend members."""
        sim = client.app.state.sim

        # 1. Network: VPC + subnet
        vpc = client.post(f"/v1/{PID}/vpcs",
                         json={"vpc": {"name": "web-vpc", "cidr": "10.10.0.0/16"}}).json()["vpc"]
        subnet = client.post(f"/v1/{PID}/subnets",
                            json={"subnet": {"name": "web-subnet", "vpc_id": vpc["id"],
                                               "cidr": "10.10.1.0/24"}}).json()["subnet"]

        # 2. Security group for HTTP
        sg = client.post(f"/v1/{PID}/security-groups",
                        json={"security_group": {"name": "web-sg"}}).json()["security_group"]

        # 3. Two app servers (ACTIVE after jobs)
        server_ids = []
        for i in (1, 2):
            r = client.post(f"/v1.1/{PID}/cloudservers",
                            json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                              "name": f"web-{i}",
                                              "security_groups": [{"name": "web-sg"}]}})
            server_ids.append(r.json()["serverIds"][0])
        sim.jobs.complete_all()
        for sid in server_ids:
            assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["status"] == "ACTIVE"

        # 4. EIP bound to the first server's port
        eip = client.post(f"/v1/{PID}/publicips",
                         json={"publicip": {"type": "5_bgp"},
                                "bandwidth": {"name": "web-bw", "size": 5,
                                                "share_type": "PER"}}).json()["publicip"]
        port = client.get(f"/v1/{PID}/ports?device_id={server_ids[0]}").json()["ports"][0]
        r = client.put(f"/v1/{PID}/publicips/{eip['id']}",
                       json={"publicip": {"port_id": port["id"]}})
        assert r.json()["publicip"]["status"] == "ACTIVE"

        # 5. ELB with listener + pool + both servers as members
        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                         json={"loadbalancer": {"name": "web-elb",
                                                 "vpc_id": vpc["id"],
                                                 "vip_subnet_id": subnet["id"]}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "web-pool", "protocol": "HTTP",
                                           "loadbalancer_id": lb["id"]}}).json()["pool"]
        for sid in server_ids:
            ip = next(a["addr"] for addrs in
                      client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["addresses"].values()
                      for a in addrs)
            r = client.post(f"/v2/{PID}/elb/pools/{pool['id']}/members",
                            json={"member": {"address": ip, "protocol_port": 80}})
            assert r.status_code == 200
        listener = client.post(f"/v2/{PID}/elb/listeners",
                              json={"listener": {"name": "web-http", "protocol": "HTTP",
                                                   "protocol_port": 80,
                                                   "loadbalancer_id": lb["id"],
                                                   "default_pool_id": pool["id"]}}).json()["listener"]
        members = client.get(f"/v2/{PID}/elb/pools/{pool['id']}/members").json()
        assert members["count"] == 2

        # 6. The explorer sees the whole topology
        graph = client.get(f"/admin/graph/{server_ids[0]}").json()
        relations = {e["relation"] for e in graph["edges"]}
        assert "has_nic" in relations and "attached_volume" in relations


class TestS2DisasterRecovery:
    def test_backup_and_restore(self, client):
        """Server -> volume -> snapshot -> vault -> checkpoint -> restore -> new volume."""
        sim = client.app.state.sim

        server = client.post(f"/v1.1/{PID}/cloudservers",
                            json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                              "name": "dr-app"}}).json()["serverIds"][0]
        sim.jobs.complete_all()

        vol_id = client.post(f"/v2.1/{PID}/cloudvolumes",
                             json={"volume": {"size": 20, "name": "dr-data"}}).json()["volume_ids"][0]
        sim.jobs.complete_all()

        # Snapshot the data volume
        snap = client.post(f"/v2/{PID}/cloudsnapshots",
                           json={"snapshot": {"volume_id": vol_id, "name": "dr-snap"}}).json()["snapshot"]
        sim.jobs.complete_all()
        assert client.get(f"/v2/{PID}/cloudsnapshots/{snap['id']}").json()["snapshot"]["status"] == "available"

        # Vault protecting both resources
        vault = client.post(f"/v3/{PID}/vaults",
                            json={"vault": {"name": "dr-vault",
                                             "resources": [{"id": server, "type": "OS::Nova::Server"},
                                                            {"id": vol_id, "type": "OS::Cinder::Volume"}]}}).json()["vault"]

        # On-demand checkpoint -> backup
        cp = client.post(f"/v3/{PID}/checkpoints",
                         json={"checkpoint": {"resources": [{"id": server, "type": "OS::Nova::Server"}]}}).json()["checkpoint"]
        sim.jobs.complete_all()
        backups = client.get(f"/v3/{PID}/backups").json()["backups"]
        assert len(backups) >= 1

        # Restore the backup -> a new volume appears
        backup_id = backups[0]["id"]
        r = client.post(f"/v3/{PID}/backups/{backup_id}/restore",
                        json={"restore": {"server_id": "auto_ecs_1",
                                           "volume_ids": "auto_boot;auto_data_1"}})
        assert r.status_code in (200, 202)
        restored = r.json().get("restore", {}).get("volume_ids", "")
        assert "auto_data_1" in restored


class TestS3TenantIsolation:
    def test_projects_do_not_leak(self, client):
        """Resources created in each project are invisible to the other."""
        sim = client.app.state.sim
        pub = client.post(f"/v1.1/{PID}/cloudservers",
                          json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                            "name": "pub-vm"}}).json()["serverIds"][0]
        hcs = client.post(f"/v1.1/{HCS_PID}/cloudservers",
                          json={"server": {"imageRef": HCS_IMAGE, "flavorRef": HCS_FLAVOR,
                                            "name": "hcs-vm"}}).json()["serverIds"][0]
        sim.jobs.complete_all()

        # Each project sees only its own
        pub_list = {s["id"] for s in client.get(
            f"/v1/{PID}/cloudservers/detail?limit=1000").json()["servers"]}
        hcs_list = {s["id"] for s in client.get(
            f"/v1/{HCS_PID}/cloudservers/detail?limit=1000").json()["servers"]}
        assert pub in pub_list and hcs not in pub_list
        assert hcs in hcs_list and pub not in hcs_list

        # Direct cross-project reads 404 both ways
        assert client.get(f"/v1/{PID}/cloudservers/{hcs}").status_code == 404
        assert client.get(f"/v1/{HCS_PID}/cloudservers/{pub}").status_code == 404

        # The HCS project keeps its sparse-list quirk even with servers present
        hcs_view = client.get(f"/v1/{HCS_PID}/cloudservers/detail").json()["servers"]
        assert all("flavor" not in s for s in hcs_view)


class TestS4QuotaExhaustion:
    def test_fill_reject_free_retry(self, client):
        """Fill the 100-instance quota -> create rejected -> delete -> retry works."""
        sim = client.app.state.sim

        # Fill the quota in one batch
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "fill", "count": 100}})
        assert r.status_code == 200
        fill_ids = r.json()["serverIds"]
        assert len(fill_ids) == 100

        # Quota reached: next create is rejected with Ecs.0015
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "over"}})
        assert r.status_code == 405
        assert r.json()["error"]["code"] == "Ecs.0015"
        assert "maximum number" in r.json()["error"]["message"].lower()

        # The limits endpoint reflects the usage
        limits = client.get(f"/v1/{PID}/cloudservers/limits").json()["absolute"]
        assert limits["totalInstancesUsed"] == 100

        # Free space: delete a batch
        r = client.post(f"/v1/{PID}/cloudservers/delete",
                        json={"servers": [{"id": sid} for sid in fill_ids[:10]]})
        sim.jobs.complete_now(r.json()["job_id"])

        # Retry succeeds now
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "after-free", "count": 5}})
        assert r.status_code == 200
        assert len(r.json()["serverIds"]) == 5


class TestS5FailureRecovery:
    def test_chaos_job_failure_then_retry(self, client):
        """A chaos-injected ECS job failure leaves the server in BUILD; retry works."""
        sim = client.app.state.sim

        # Inject a 100% job-failure rule for ECS creates
        client.post("/admin/chaos", json={
            "service": "ecs", "failure_rate": 1.0, "mode": "job",
            "error_code": "Ecs.0900", "error_msg": "injected failure"})

        # Create: API accepts, but the job FAILs
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "doomed"}})
        sid = r.json()["serverIds"][0]
        job_id = r.json()["job_id"]
        assert r.status_code == 200
        sim.jobs.complete_now(job_id)
        job = sim.jobs.jobs[job_id]
        assert job.status == "FAIL"
        assert job.error_code == "Ecs.0900"

        # Inspect: the server never became ACTIVE
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["status"] == "BUILD"

        # Recover: remove the chaos rule and retry with a fresh server
        client.post("/admin/chaos/reset")
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "recovered"}})
        sid2 = r.json()["serverIds"][0]
        sim.jobs.complete_all()
        assert client.get(f"/v1/{PID}/cloudservers/{sid2}").json()["server"]["status"] == "ACTIVE"

        # Cleanup the failed server
        r = client.post(f"/v1/{PID}/cloudservers/delete",
                        json={"servers": [{"id": sid}]})
        sim.jobs.complete_now(r.json()["job_id"])
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").status_code == 404
