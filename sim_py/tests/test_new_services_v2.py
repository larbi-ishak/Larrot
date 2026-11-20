"""Tests for the 20 new services + ModelArts MaaS (the v2 expansion)."""
import pytest
from fastapi.testclient import TestClient
from huawei_sim.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# HSS — hosts correlate with ECS servers
# ---------------------------------------------------------------------------

class TestHss:
    def test_hosts_derive_from_ecs(self, client):
        """Every ECS server appears as an HSS host."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "hss-correlation"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/v5/{PID}/hosts")
        assert r.status_code == 200
        assert any(h["host_id"] == sid for h in r.json()["data_list"])

    def test_host_not_found(self, client):
        assert client.get(f"/v5/{PID}/hosts/bad-id").status_code == 404

    def test_protection_lifecycle(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "hss-protect"}})
        sid = r.json()["serverIds"][0]

        # Before: protection closed
        host = client.get(f"/v5/{PID}/hosts/{sid}").json()
        assert host["protect_status"] == "closed"

        # Enable
        r = client.post(f"/v5/{PID}/hosts/{sid}/protection",
                        json={"charge_mode": "hsp"})
        assert r.status_code == 200
        assert r.json()["protect_status"] == "opened"

        host = client.get(f"/v5/{PID}/hosts/{sid}").json()
        assert host["protect_status"] == "opened"
        assert host["agent_status"] == "online"

    def test_policies(self, client):
        r = client.post(f"/v5/{PID}/policy", json={"name": "my-policy"})
        assert r.status_code == 200
        pid = r.json()["policy_id"]
        r = client.get(f"/v5/{PID}/policy")
        assert any(p["policy_id"] == pid for p in r.json()["data_list"])

    def test_alarms_and_vulnerabilities(self, client):
        client.post(f"/v5/{PID}/alarm-events", json={"event_name": "brute force"})
        r = client.get(f"/v5/{PID}/alarm-events")
        assert r.json()["total"] >= 1

        # Vulns are found per host — create one first (cross-service: ECS)
        client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                      "name": "vuln-host"}})
        r = client.post(f"/v5/{PID}/vulnerabilities/scan")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        r = client.get(f"/v5/{PID}/vulnerabilities")
        assert r.json()["total"] == 1
        assert r.json()["data_list"][0]["severity"] == "Important"

    def test_quotas(self, client):
        r = client.get(f"/v5/{PID}/quotas")
        assert r.status_code == 200
        assert "total" in r.json() and "used" in r.json()


# ---------------------------------------------------------------------------
# CDN
# ---------------------------------------------------------------------------

class TestCdn:
    def test_domain_lifecycle(self, client):
        r = client.post("/v1/domains", json={"domain_name": "cdn.example.com",
                                              "business_type": "web"})
        assert r.status_code == 200
        did = r.json()["domain"]["id"]

        r = client.get("/v1/domains")
        assert any(d["id"] == did for d in r.json()["domains"])

        r = client.get(f"/v1/domains/{did}")
        assert r.json()["domain"]["domain_name"] == "cdn.example.com"

        r = client.put(f"/v1/domains/{did}",
                       json={"sources": [{"ipaddr": "1.2.3.4", "priority": 50}]})
        assert r.json()["domain"]["sources"][0]["ipaddr"] == "1.2.3.4"

        assert client.delete(f"/v1/domains/{did}").status_code == 204
        assert client.get(f"/v1/domains/{did}").status_code == 404

    def test_duplicate_domain_409(self, client):
        client.post("/v1/domains", json={"domain_name": "dupe.example.com"})
        r = client.post("/v1/domains", json={"domain_name": "dupe.example.com"})
        assert r.status_code == 409
        assert r.json()["error_code"] == "CDN.0002"

    def test_missing_name_400(self, client):
        r = client.post("/v1/domains", json={})
        assert r.status_code == 400
        assert r.json()["error_code"] == "CDN.0001"

    def test_purge_and_preheat(self, client):
        r = client.post("/v1.0/purgecache", json={"url": ["https://cdn.example.com/a.css"]})
        assert r.status_code == 200
        purge_id = r.json()["id"]

        r = client.post("/v1.0/preheating", json={"url": ["https://cdn.example.com/b.js"]})
        assert r.status_code == 200
        preheat_id = r.json()["id"]

        r = client.get("/v1.0/historytasks")
        tasks = {t["id"]: t for t in r.json()["tasks"]}
        assert tasks[purge_id]["task_type"] == "purge"
        assert tasks[preheat_id]["task_type"] == "preheating"

        # Complete the jobs → tasks become done
        client.app.state.sim.jobs.complete_all()
        r = client.get("/v1.0/historytasks")
        assert all(t["status"] == "done" for t in r.json()["tasks"])

    def test_statistics(self, client):
        client.post("/v1/domains", json={"domain_name": "stats.example.com"})
        r = client.get("/v1.0/statistics")
        assert r.status_code == 200
        assert any(d["domain_name"] == "stats.example.com" for d in r.json()["data"])


# ---------------------------------------------------------------------------
# DWS
# ---------------------------------------------------------------------------

class TestDws:
    def test_cluster_lifecycle(self, client):
        r = client.post(f"/v1.0/{PID}/dws/clusters",
                        json={"name": "dws-test", "number_of_node": 3})
        assert r.status_code == 200
        cid = r.json()["cluster"]["id"]
        assert r.json()["cluster"]["status"] == "CREATING"

        # Job completes → ACTIVE
        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1.0/{PID}/dws/clusters/{cid}")
        assert r.json()["cluster"]["status"] == "ACTIVE"

        # Resize
        r = client.post(f"/v1.0/{PID}/dws/clusters/{cid}/resize",
                        json={"number_of_node": 6})
        assert r.json()["cluster"]["nodes"] if "nodes" in r.text else True
        assert r.json()["cluster"]["number_of_node"] == 6

        # Bare route alias also works
        r = client.get(f"/v1.0/{PID}/clusters")
        assert any(c["id"] == cid for c in r.json()["clusters"])

        assert client.delete(f"/v1.0/{PID}/dws/clusters/{cid}").status_code == 204

    def test_cluster_min_nodes(self, client):
        r = client.post(f"/v1.0/{PID}/dws/clusters",
                        json={"name": "too-small", "number_of_node": 2})
        assert r.status_code == 400
        assert r.json()["error_code"] == "DWS.0002"

    def test_cluster_not_found(self, client):
        assert client.get(f"/v1.0/{PID}/dws/clusters/bad-id").status_code == 404

    def test_snapshots(self, client):
        r = client.post(f"/v1.0/{PID}/dws/clusters",
                        json={"name": "snap-src", "number_of_node": 3})
        cid = r.json()["cluster"]["id"]
        r = client.post(f"/v1.0/{PID}/dws/snapshots",
                        json={"name": "snap-1", "cluster_id": cid})
        assert r.status_code == 200
        assert r.json()["snapshot"]["status"] == "CREATING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1.0/{PID}/dws/snapshots")
        assert r.json()["snapshots"][0]["status"] == "AVAILABLE"

    def test_snapshot_bad_cluster_404(self, client):
        r = client.post(f"/v1.0/{PID}/dws/snapshots",
                        json={"name": "x", "cluster_id": "bad"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

class TestCss:
    def test_cluster_lifecycle(self, client):
        r = client.post(f"/v1.0/{PID}/css/clusters",
                        json={"name": "es-test", "instance_num": 3})
        assert r.status_code == 200
        cid = r.json()["cluster"]["id"]
        assert r.json()["cluster"]["status"] == "CREATING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1.0/{PID}/css/clusters/{cid}")
        assert r.json()["cluster"]["status"] == "RUNNING"

        # Restart
        r = client.post(f"/v1.0/{PID}/css/clusters/{cid}/restart")
        assert r.json()["status"] == "RESTARTING"
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1.0/{PID}/css/clusters/{cid}").json()["cluster"]["status"] == "RUNNING"

    def test_indices(self, client):
        r = client.post(f"/v1.0/{PID}/css/clusters", json={"name": "es-idx"})
        cid = r.json()["cluster"]["id"]
        client.app.state.sim.jobs.complete_all()

        r = client.post(f"/v1.0/{PID}/css/clusters/{cid}/indices",
                        json={"index_name": "logs-2026", "shards": 5})
        assert r.status_code == 200
        assert r.json()["acknowledged"] is True

        r = client.get(f"/v1.0/{PID}/css/clusters/{cid}/indices")
        assert r.json()["total"] == 1
        assert r.json()["indices"][0]["index_name"] == "logs-2026"

        assert client.delete(
            f"/v1.0/{PID}/css/clusters/{cid}/indices/logs-2026").status_code == 200
        assert client.get(f"/v1.0/{PID}/css/clusters/{cid}/indices").json()["total"] == 0

    def test_missing_name_400(self, client):
        r = client.post(f"/v1.0/{PID}/css/clusters", json={})
        assert r.status_code == 400
        assert r.json()["error_code"] == "CSS.0001"

    def test_cluster_not_found(self, client):
        assert client.get(f"/v1.0/{PID}/css/clusters/bad").status_code == 404


# ---------------------------------------------------------------------------
# MRS
# ---------------------------------------------------------------------------

class TestMrs:
    def test_cluster_lifecycle(self, client):
        r = client.post(f"/v1.1/{PID}/cluster_infos",
                        json={"cluster_name": "mrs-test",
                              "component_list": ["hadoop", "spark"]})
        assert r.status_code == 200
        cid = r.json()["clusterId"]
        assert r.json()["clusterState"] == "STARTING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1.1/{PID}/cluster_infos/{cid}")
        assert r.json()["clusterState"] == "RUNNING"

        # Submit a job to the RUNNING cluster
        r = client.post(f"/v1.1/{PID}/cluster_infos/{cid}/jobs",
                        json={"job_name": "spark-job", "job_type": "SparkSubmit"})
        assert r.status_code == 200
        assert r.json()["job_state"] == "SUBMITTED"

        # Scale up
        r = client.post(f"/v1.1/{PID}/cluster_infos/{cid}/resize", json={"node_num": 5})
        assert r.json()["nodeNum"] == 5

    def test_invalid_component_400(self, client):
        r = client.post(f"/v1.1/{PID}/cluster_infos",
                        json={"cluster_name": "bad", "component_list": ["not-a-component"]})
        assert r.status_code == 400
        assert r.json()["error_code"] == "MRS.0002"

    def test_job_on_non_running_400(self, client):
        r = client.post(f"/v1.1/{PID}/cluster_infos",
                        json={"cluster_name": "starting"})
        cid = r.json()["clusterId"]
        # Still STARTING (job not completed)
        r = client.post(f"/v1.1/{PID}/cluster_infos/{cid}/jobs",
                        json={"job_name": "too-early"})
        assert r.status_code == 400
        assert r.json()["error_code"] == "MRS.0004"

    def test_shrink_rejected(self, client):
        r = client.post(f"/v1.1/{PID}/cluster_infos",
                        json={"cluster_name": "shrink", "node_num": 5})
        cid = r.json()["clusterId"]
        r = client.post(f"/v1.1/{PID}/cluster_infos/{cid}/resize", json={"node_num": 3})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# SMS — source state machine gates task creation
# ---------------------------------------------------------------------------

class TestSms:
    def test_full_migration_flow(self, client):
        # Register source (unavailable until agent job completes)
        r = client.post(f"/v3/{PID}/sources", json={"ip": "192.168.1.10"})
        assert r.status_code == 200
        src_id = r.json()["id"]
        assert r.json()["state"] == "unavailable"

        # Task creation fails while source is unavailable
        r = client.post(f"/v3/{PID}/tasks",
                        json={"name": "mig-1", "source_id": src_id})
        assert r.status_code == 400
        assert r.json()["error_code"] == "SMS.0003"

        # Agent connects
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v3/{PID}/sources/{src_id}").json()["state"] == "available"

        # Now the task can be created
        r = client.post(f"/v3/{PID}/tasks",
                        json={"name": "mig-1", "source_id": src_id})
        assert r.status_code == 200
        task_id = r.json()["id"]
        assert r.json()["state"] == "MIGRATING"

        # Migration completes
        client.app.state.sim.jobs.complete_all()
        t = client.get(f"/v3/{PID}/tasks/{task_id}").json()
        assert t["state"] == "SUCCESS"
        assert t["progress"] == 100

    def test_source_not_found(self, client):
        r = client.post(f"/v3/{PID}/tasks",
                        json={"name": "x", "source_id": "bad"})
        assert r.status_code == 404
        assert r.json()["error_code"] == "SMS.0002"

    def test_templates(self, client):
        r = client.post(f"/v3/{PID}/templates", json={"name": "tpl"})
        assert r.status_code == 200
        r = client.get(f"/v3/{PID}/templates")
        assert r.json()["total"] >= 1


# ---------------------------------------------------------------------------
# DC
# ---------------------------------------------------------------------------

class TestDc:
    def test_connection_lifecycle(self, client):
        r = client.post(f"/v2.0/{PID}/direct-connects",
                        json={"name": "dc-1", "bandwidth": 1000})
        assert r.status_code == 200
        cid = r.json()["direct_connect"]["id"]
        assert r.json()["direct_connect"]["status"] == "BUILD"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2.0/{PID}/direct-connects/{cid}")
        assert r.json()["direct_connect"]["status"] == "ACTIVE"

    def test_virtual_gateway_and_interface(self, client):
        # VGW needs a real VPC
        vpc = client.post(f"/v1/{PID}/vpcs", json={"vpc": {"name": "dc-vpc"}}).json()["vpc"]

        r = client.post(f"/v2.0/{PID}/virtual-gateways",
                        json={"name": "vgw-1", "vpc_id": vpc["id"]})
        assert r.status_code == 200
        vgw_id = r.json()["virtual_gateway"]["id"]

        r = client.post(f"/v2.0/{PID}/direct-connects", json={"name": "dc-vif"})
        dc_id = r.json()["direct_connect"]["id"]

        # VIF requires both a real DC and a real VGW
        r = client.post(f"/v2.0/{PID}/virtual-interfaces",
                        json={"name": "vif-1", "direct_connect_id": dc_id,
                              "vgw_id": vgw_id})
        assert r.status_code == 200
        assert r.json()["virtual_interface"]["status"] == "ACTIVE"

        r = client.post(f"/v2.0/{PID}/virtual-interfaces",
                        json={"name": "bad", "direct_connect_id": "nope",
                              "vgw_id": vgw_id})
        assert r.status_code == 404

    def test_vgw_requires_vpc(self, client):
        r = client.post(f"/v2.0/{PID}/virtual-gateways",
                        json={"name": "x", "vpc_id": ""})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# ER — attachments validate the VPC exists
# ---------------------------------------------------------------------------

class TestEr:
    def test_instance_lifecycle(self, client):
        r = client.post(f"/v3/{PID}/enterprise-router/instances", json={"name": "er-1"})
        assert r.status_code == 200
        eid = r.json()["instance"]["id"]
        assert r.json()["instance"]["state"] == "pending"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v3/{PID}/enterprise-router/instances/{eid}")
        assert r.json()["instance"]["state"] == "available"

        # Route tables
        r = client.post(f"/v3/{PID}/enterprise-router/instances/{eid}/route-tables",
                        json={"name": "rt-1"})
        assert r.status_code == 200
        r = client.get(f"/v3/{PID}/enterprise-router/instances/{eid}/route-tables")
        assert r.json()["total"] == 1

    def test_vpc_attachment(self, client):
        r = client.post(f"/v3/{PID}/enterprise-router/instances", json={"name": "er-att"})
        eid = r.json()["instance"]["id"]
        vpc = client.post(f"/v1/{PID}/vpcs", json={"vpc": {"name": "spoke-vpc"}}).json()["vpc"]

        r = client.post(f"/v3/{PID}/enterprise-router/instances/{eid}/attachments",
                        json={"name": "spoke-1", "vpc_id": vpc["id"]})
        assert r.status_code == 200
        aid = r.json()["attachment"]["id"]

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v3/{PID}/enterprise-router/instances/{eid}/attachments")
        assert r.json()["attachments"][0]["state"] == "available"
        assert r.json()["attachments"][0]["id"] == aid

    def test_attachment_bad_vpc_404(self, client):
        r = client.post(f"/v3/{PID}/enterprise-router/instances", json={"name": "er-bad"})
        eid = r.json()["instance"]["id"]
        r = client.post(f"/v3/{PID}/enterprise-router/instances/{eid}/attachments",
                        json={"name": "x", "vpc_id": "bad-vpc"})
        assert r.status_code == 404
        assert r.json()["error_code"] == "ER.0005"

    def test_delete_with_attachments_409(self, client):
        r = client.post(f"/v3/{PID}/enterprise-router/instances", json={"name": "er-del"})
        eid = r.json()["instance"]["id"]
        vpc = client.post(f"/v1/{PID}/vpcs", json={"vpc": {"name": "del-vpc"}}).json()["vpc"]
        client.post(f"/v3/{PID}/enterprise-router/instances/{eid}/attachments",
                    json={"name": "att", "vpc_id": vpc["id"]})
        r = client.delete(f"/v3/{PID}/enterprise-router/instances/{eid}")
        assert r.status_code == 409
        assert r.json()["error_code"] == "ER.0003"


# ---------------------------------------------------------------------------
# DIS
# ---------------------------------------------------------------------------

class TestDis:
    def test_stream_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/streams", json={"stream_name": "events", "partitions": 2})
        assert r.status_code == 200

        r = client.get(f"/v2/{PID}/streams")
        assert "events" in r.json()["stream_names"]
        assert r.json()["has_more_streams"] is False

        r = client.get(f"/v2/{PID}/streams/events")
        assert r.json()["partition_count"] == 2

        # Grow partitions
        r = client.put(f"/v2/{PID}/streams/events", json={"partition_count": 4})
        assert r.json()["partition_count"] == 4

        assert client.delete(f"/v2/{PID}/streams/events").status_code == 204

    def test_duplicate_stream_409(self, client):
        client.post(f"/v2/{PID}/streams", json={"stream_name": "dupe"})
        r = client.post(f"/v2/{PID}/streams", json={"stream_name": "dupe"})
        assert r.status_code == 409

    def test_shrink_rejected(self, client):
        client.post(f"/v2/{PID}/streams", json={"stream_name": "shrink", "partitions": 4})
        r = client.put(f"/v2/{PID}/streams/shrink", json={"partition_count": 2})
        assert r.status_code == 400

    def test_apps_and_checkpoints(self, client):
        client.post(f"/v2/{PID}/streams", json={"stream_name": "cp-stream"})
        client.post(f"/v2/{PID}/apps", json={"app_name": "consumer-1"})

        r = client.put(f"/v2/{PID}/apps/consumer-1/checkpoints",
                       json={"stream_name": "cp-stream", "checkpoint_state": "seq-42"})
        assert r.status_code == 200

        r = client.get(f"/v2/{PID}/apps/consumer-1/checkpoints")
        assert r.json()["total"] == 1
        assert r.json()["checkpoints"][0]["checkpoint_state"] == "seq-42"

    def test_checkpoint_bad_stream_404(self, client):
        client.post(f"/v2/{PID}/apps", json={"app_name": "cp-bad"})
        r = client.put(f"/v2/{PID}/apps/cp-bad/checkpoints",
                       json={"stream_name": "no-such"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DataArts
# ---------------------------------------------------------------------------

class TestDataArts:
    def test_connection_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/connections",
                        json={"name": "dws-conn", "connection_type": "DWS"})
        assert r.status_code == 200
        cid = r.json()["connection"]["connection_id"]

        r = client.get(f"/v2/{PID}/connections")
        assert any(c["connection_id"] == cid for c in r.json()["connections"])

        assert client.delete(f"/v2/{PID}/connections/{cid}").status_code == 204

    def test_invalid_type_400(self, client):
        r = client.post(f"/v2/{PID}/connections",
                        json={"name": "x", "connection_type": "NotReal"})
        assert r.status_code == 400

    def test_job_run_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/jobs", json={"name": "etl-job"})
        assert r.status_code == 200
        assert r.json()["job"]["status"] == "DRAFT"

        r = client.post(f"/v2/{PID}/jobs/etl-job/run")
        assert r.status_code == 200
        assert r.json()["status"] == "RUNNING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/jobs")
        assert r.json()["jobs"][0]["status"] == "SUCCEEDED"

    def test_run_missing_job_404(self, client):
        r = client.post(f"/v2/{PID}/jobs/never-created/run")
        assert r.status_code == 404

    def test_scripts(self, client):
        client.post(f"/v2/{PID}/scripts", json={"name": "flink-sql", "content": "SELECT 1"})
        r = client.get(f"/v2/{PID}/scripts")
        assert r.json()["total"] == 1


# ---------------------------------------------------------------------------
# OMS — destination bucket must exist (cross-service: OBS)
# ---------------------------------------------------------------------------

class TestOms:
    def test_task_lifecycle(self, client):
        # Destination bucket must exist in OBS state
        client.app.state.sim.obs_buckets["dest-bucket"] = {
            "name": "dest-bucket", "created_at": "2026-01-01T00:00:00Z",
            "location": "sim"}

        r = client.post(f"/v2/{PID}/tasks",
                        json={"name": "oms-1",
                              "src_node": {"bucket": "src-bucket"},
                              "dst_node": {"bucket": "dest-bucket"}})
        assert r.status_code == 200
        tid = r.json()["id"]
        assert r.json()["status"] == "MIGRATING"

        client.app.state.sim.jobs.complete_all()
        t = client.get(f"/v2/{PID}/tasks/{tid}").json()
        assert t["status"] == "SUCCESS"
        assert t["migrated_record"] == t["total_record"]

    def test_missing_bucket_400(self, client):
        r = client.post(f"/v2/{PID}/tasks",
                        json={"src_node": {"bucket": "s"}, "dst_node": {}})
        assert r.status_code == 400

    def test_missing_dest_bucket_404(self, client):
        r = client.post(f"/v2/{PID}/tasks",
                        json={"src_node": {"bucket": "s"},
                              "dst_node": {"bucket": "no-such-bucket"}})
        assert r.status_code == 404
        assert r.json()["error_code"] == "OMS.0002"

    def test_stop_only_while_migrating(self, client):
        client.app.state.sim.obs_buckets["stop-bucket"] = {
            "name": "stop-bucket", "created_at": "2026-01-01T00:00:00Z",
            "location": "sim"}
        r = client.post(f"/v2/{PID}/tasks",
                        json={"src_node": {"bucket": "s"},
                              "dst_node": {"bucket": "stop-bucket"}})
        tid = r.json()["id"]

        # STOPPING while MIGRATING is fine
        r = client.post(f"/v2/{PID}/tasks/{tid}/stop")
        assert r.status_code == 200

        # After STOPPING, stop again → 400
        r = client.post(f"/v2/{PID}/tasks/{tid}/stop")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# DES
# ---------------------------------------------------------------------------

class TestDes:
    def test_task_lifecycle(self, client):
        r = client.post(f"/v1/{PID}/des/tasks",
                        json={"name": "teleport-1", "task_type": "Teleport"})
        assert r.status_code == 200
        tid = r.json()["id"]
        assert r.json()["status"] == "CREATING"

        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1/{PID}/des/tasks/{tid}").json()["status"] == "WAITING"

    def test_invalid_type_400(self, client):
        r = client.post(f"/v1/{PID}/des/tasks",
                        json={"name": "x", "task_type": "CarrierPigeon"})
        assert r.status_code == 400
        assert r.json()["error_code"] == "DES.0002"

    def test_not_found(self, client):
        assert client.get(f"/v1/{PID}/des/tasks/bad").status_code == 404


# ---------------------------------------------------------------------------
# CodeArts
# ---------------------------------------------------------------------------

class TestCodeArts:
    def test_repo_lifecycle(self, client):
        r = client.post("/v2/projects/repositories", json={"repository_name": "my-app"})
        assert r.status_code == 200
        rid = r.json()["repository_id"]
        assert "codehub.myhuaweicloud.com" in r.json()["https_url"]

        r = client.get("/v2/projects/repositories")
        assert any(x["repository_id"] == rid for x in r.json()["repositories"])

        assert client.delete(f"/v2/projects/repositories/{rid}").status_code == 204

    def test_duplicate_repo_409(self, client):
        client.post("/v2/projects/repositories", json={"repository_name": "dupe-repo"})
        r = client.post("/v2/projects/repositories", json={"repository_name": "dupe-repo"})
        assert r.status_code == 409

    def test_pipeline_run_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/pipelines", json={"name": "release"})
        assert r.status_code == 200
        plid = r.json()["pipeline_id"]

        r = client.post(f"/v2/{PID}/pipelines/{plid}/run")
        assert r.status_code == 200
        assert r.json()["status"] == "RUNNING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/pipelines")
        assert r.json()["pipelines"][0]["status"] == "SUCCESS"

    def test_build_run_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/builds", json={"name": "mvn-build"})
        bid = r.json()["build_id"]

        r = client.post(f"/v2/{PID}/builds/{bid}/run")
        assert r.json()["status"] == "RUNNING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/builds")
        assert r.json()["builds"][0]["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# ServiceStage
# ---------------------------------------------------------------------------

class TestServiceStage:
    def test_environment_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/cas/environments", json={"name": "prod-env"})
        assert r.status_code == 200
        eid = r.json()["environment"]["id"]
        assert r.json()["environment"]["status"] == "CREATING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/cas/environments")
        assert r.json()["environments"][0]["status"] == "READY"

    def test_application_and_component(self, client):
        eid = client.post(f"/v2/{PID}/cas/environments",
                          json={"name": "comp-env"}).json()["environment"]["id"]
        client.app.state.sim.jobs.complete_all()

        r = client.post(f"/v2/{PID}/cas/applications", json={"name": "orders-app"})
        aid = r.json()["application"]["id"]

        r = client.post(f"/v2/{PID}/cas/applications/{aid}/components",
                        json={"name": "orders-api", "environment_id": eid})
        assert r.status_code == 200
        assert r.json()["component"]["status"] == "CREATING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/cas/applications/{aid}/components")
        assert r.json()["components"][0]["status"] == "RUNNING"

        # Application component_num incremented
        r = client.get(f"/v2/{PID}/cas/applications/{aid}")
        assert r.json()["application"]["component_num"] == 1

    def test_component_bad_env_404(self, client):
        aid = client.post(f"/v2/{PID}/cas/applications",
                          json={"name": "bad-app"}).json()["application"]["id"]
        r = client.post(f"/v2/{PID}/cas/applications/{aid}/components",
                        json={"name": "x", "environment_id": "bad"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# CSE
# ---------------------------------------------------------------------------

class TestCse:
    def test_engine_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/engines", json={"name": "cse-main"})
        assert r.status_code == 200
        eid = r.json()["id"]
        assert r.json()["status"] == "Creating"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/engines/{eid}")
        assert r.json()["status"] == "Available"

    def test_microservice_registration_gated_by_engine_state(self, client):
        eid = client.post(f"/v2/{PID}/engines", json={"name": "cse-gate"}).json()["id"]

        # Engine still Creating → registration rejected
        r = client.post(f"/v2/{PID}/engines/{eid}/microservices",
                        json={"serviceName": "svc"})
        assert r.status_code == 400
        assert r.json()["error_code"] == "CSE.0003"

        # After engine is Available → registration succeeds
        client.app.state.sim.jobs.complete_all()
        r = client.post(f"/v2/{PID}/engines/{eid}/microservices",
                        json={"serviceName": "svc"})
        assert r.status_code == 200
        r = client.get(f"/v2/{PID}/engines/{eid}/microservices")
        assert r.json()["total"] == 1
        assert r.json()["microservices"][0]["status"] == "UP"


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------

class TestCci:
    def test_namespace_and_pod_lifecycle(self, client):
        r = client.post(f"/v1/{PID}/cci/namespaces", json={"name": "team-a"})
        assert r.status_code == 200
        ns_id = r.json()["namespace"]["id"]

        r = client.post(f"/v1/{PID}/cci/namespaces/{ns_id}/pods",
                        json={"name": "web-1",
                              "spec": {"containers": [
                                  {"name": "nginx", "image": "nginx:latest"}]}})
        assert r.status_code == 200
        pod_id = r.json()["pod"]["id"]
        assert r.json()["pod"]["status"] == "Pending"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/cci/namespaces/{ns_id}/pods/{pod_id}")
        assert r.json()["pod"]["status"] == "Running"
        assert r.json()["pod"]["pod_ip"]

    def test_pod_requires_containers(self, client):
        ns_id = client.post(f"/v1/{PID}/cci/namespaces",
                            json={"name": "empty-ns"}).json()["namespace"]["id"]
        r = client.post(f"/v1/{PID}/cci/namespaces/{ns_id}/pods",
                        json={"name": "empty-pod", "spec": {}})
        assert r.status_code == 400
        assert r.json()["error_code"] == "CCI.0006"

    def test_delete_nonempty_namespace_409(self, client):
        ns_id = client.post(f"/v1/{PID}/cci/namespaces",
                            json={"name": "full-ns"}).json()["namespace"]["id"]
        client.post(f"/v1/{PID}/cci/namespaces/{ns_id}/pods",
                    json={"name": "p", "spec": {"containers": [{"name": "c"}]}})
        r = client.delete(f"/v1/{PID}/cci/namespaces/{ns_id}")
        assert r.status_code == 409
        assert r.json()["error_code"] == "CCI.0004"

    def test_duplicate_namespace_409(self, client):
        client.post(f"/v1/{PID}/cci/namespaces", json={"name": "dupe-ns"})
        r = client.post(f"/v1/{PID}/cci/namespaces", json={"name": "dupe-ns"})
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# CFW
# ---------------------------------------------------------------------------

class TestCfw:
    def test_firewall_lifecycle(self, client):
        r = client.post(f"/v1/{PID}/firewalls", json={"name": "edge-fw"})
        assert r.status_code == 200
        fid = r.json()["firewall"]["id"]
        assert r.json()["firewall"]["status"] == "creating"

        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1/{PID}/firewalls/{fid}").json()["firewall"]["status"] == "running"

    def test_rules_and_hits(self, client):
        fid = client.post(f"/v1/{PID}/firewalls",
                          json={"name": "rule-fw"}).json()["firewall"]["id"]
        client.app.state.sim.jobs.complete_all()

        r = client.post(f"/v1/{PID}/firewalls/{fid}/rules",
                        json={"name": "block-ssh", "action": "deny", "port": "22"})
        assert r.status_code == 200
        rule_id = r.json()["rule"]["id"]

        # Invalid action rejected
        r = client.post(f"/v1/{PID}/firewalls/{fid}/rules",
                        json={"action": "maybe"})
        assert r.status_code == 400

        # Record hits — count increments
        r = client.post(f"/v1/{PID}/firewalls/{fid}/hit-records",
                        json={"rule_id": rule_id})
        assert r.json()["hit_count"] == 1
        r = client.post(f"/v1/{PID}/firewalls/{fid}/hit-records",
                        json={"rule_id": rule_id})
        assert r.json()["hit_count"] == 2

        r = client.get(f"/v1/{PID}/firewalls/{fid}/hit-records")
        assert r.json()["total"] == 2

        # Rule list shows hit_count
        r = client.get(f"/v1/{PID}/firewalls/{fid}/rules")
        assert r.json()["rules"][0]["hit_count"] == 2

    def test_hit_bad_rule_404(self, client):
        fid = client.post(f"/v1/{PID}/firewalls",
                          json={"name": "hit-fw"}).json()["firewall"]["id"]
        r = client.post(f"/v1/{PID}/firewalls/{fid}/hit-records",
                        json={"rule_id": "bad"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DSC
# ---------------------------------------------------------------------------

class TestDsc:
    def test_asset_scan_risk_flow(self, client):
        r = client.post(f"/v1/{PID}/dsc/assets", json={"asset_name": "obs-pii-bucket"})
        assert r.status_code == 200
        aid = r.json()["asset"]["asset_id"]

        # Scan discovers seeded risks
        r = client.post(f"/v1/{PID}/dsc/scans",
                        json={"asset_id": aid})
        assert r.json()["total"] == 3

        # Asset counters updated
        r = client.get(f"/v1/{PID}/dsc/assets")
        assert r.json()["assets"][0]["risk_count"] == 3

        # Handle a risk
        rid = r.json()["assets"][0] and client.get(
            f"/v1/{PID}/dsc/risks").json()["risks"][0]["risk_id"]
        r = client.post(f"/v1/{PID}/dsc/risks/{rid}/handle")
        assert r.json()["status"] == "handled"

        # Filter by status
        r = client.get(f"/v1/{PID}/dsc/risks?status=handled")
        assert r.json()["total"] == 1
        r = client.get(f"/v1/{PID}/dsc/risks?status=open")
        assert r.json()["total"] == 2

    def test_scan_bad_asset_404(self, client):
        r = client.post(f"/v1/{PID}/dsc/scans", json={"asset_id": "bad"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# VOD
# ---------------------------------------------------------------------------

class TestVod:
    def test_asset_upload_publish_flow(self, client):
        r = client.post(f"/v1/{PID}/assets", json={"asset_name": "promo-video"})
        assert r.status_code == 200
        aid = r.json()["asset"]["asset_id"]
        assert r.json()["asset"]["status"] == "EMPTY"

        r = client.post(f"/v1/{PID}/assets/{aid}/upload")
        assert r.json()["status"] == "UPLOADING"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/assets/{aid}")
        assert r.json()["asset"]["status"] == "PUBLISHED"
        assert r.json()["asset"]["duration"] > 0
        assert "m3u8" in r.json()["asset"]["video_url"]

    def test_transcode_templates(self, client):
        r = client.post(f"/v1/{PID}/transcode-templates",
                        json={"name": "1080p", "video": {"width": 1920}})
        assert r.status_code == 200
        tid = r.json()["template"]["template_id"]

        r = client.get(f"/v1/{PID}/transcode-templates")
        assert r.json()["total"] == 1

        assert client.delete(f"/v1/{PID}/transcode-templates/{tid}").status_code == 204

    def test_categories(self, client):
        client.post(f"/v1/{PID}/categories", json={"name": "marketing"})
        r = client.get(f"/v1/{PID}/categories")
        assert r.json()["total"] == 1

    def test_missing_name_400(self, client):
        r = client.post(f"/v1/{PID}/assets", json={})
        assert r.status_code == 400
        assert r.json()["error_code"] == "VOD.0001"


# ---------------------------------------------------------------------------
# IEF
# ---------------------------------------------------------------------------

class TestIef:
    def test_node_and_deployment(self, client):
        r = client.post(f"/v2/{PID}/edgemgr/nodes",
                        json={"name": "edge-gw-1"})
        assert r.status_code == 200
        nid = r.json()["node"]["id"]
        assert r.json()["node"]["state"] == "unknown"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/edgemgr/nodes/{nid}")
        assert r.json()["node"]["state"] == "running"

        # Deployment targeting the node
        r = client.post(f"/v2/{PID}/edgemgr/deployments",
                        json={"deployment": {"name": "camera-ai",
                                             "node_ids": [nid], "replicas": 1}})
        assert r.status_code == 200
        did = r.json()["deployment"]["id"]
        assert r.json()["deployment"]["state"] == "pending"

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/edgemgr/deployments")
        d = r.json()["deployments"][0]
        assert d["state"] == "running"
        assert d["ready"] == d["desired"] == 1

    def test_deployment_bad_node_404(self, client):
        r = client.post(f"/v2/{PID}/edgemgr/deployments",
                        json={"deployment": {"name": "x", "node_ids": ["bad"]}})
        assert r.status_code == 404

    def test_deployment_requires_nodes_400(self, client):
        r = client.post(f"/v2/{PID}/edgemgr/deployments",
                        json={"deployment": {"name": "x", "node_ids": []}})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# ModelArts — model registry, services, fine-tuning
# ---------------------------------------------------------------------------

class TestModelArts:
    def test_model_publish_and_deploy(self, client):
        # Register → publishing
        r = client.post(f"/v1/{PID}/models", json={"model_name": "my-cnn"})
        assert r.status_code == 200
        mid = r.json()["model_id"]
        assert r.json()["status"] == "publishing"

        # Deploying an unpublished model fails
        r = client.post(f"/v1/{PID}/services",
                        json={"service_name": "svc", "model_id": mid})
        assert r.status_code == 400
        assert r.json()["error_code"] == "MA.0004"

        # Publish completes
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1/{PID}/models/{mid}").json()["status"] == "published"

        # Now deploy
        r = client.post(f"/v1/{PID}/services",
                        json={"service_name": "my-cnn-svc", "model_id": mid})
        assert r.status_code == 200
        sid = r.json()["service_id"]
        assert r.json()["status"] == "deploying"

        client.app.state.sim.jobs.complete_all()
        svc = client.get(f"/v1/{PID}/services/{sid}").json()
        assert svc["status"] == "running"
        assert "endpoint" in svc

    def test_notebook_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/notebooks", json={"name": "exp-1"})
        assert r.status_code == 200
        nid = r.json()["id"]

        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/notebooks")
        assert r.json()["notebooks"][0]["status"] == "RUNNING"

        assert client.delete(f"/v2/{PID}/notebooks/{nid}").status_code == 204

    def test_training_job_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/training-jobs", json={"name": "train-1"})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v2/{PID}/training-jobs")
        assert r.json()["jobs"][0]["status"] == "SUCCEEDED"

    def test_fine_tuning(self, client):
        r = client.post(f"/v1/{PID}/fine-tuning-jobs",
                        json={"name": "sft-1", "base_model": "Qwen2.5-72B-Instruct"})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/fine-tuning-jobs")
        assert r.json()["jobs"][0]["status"] == "SUCCEEDED"

    def test_fine_tuning_bad_model_400(self, client):
        r = client.post(f"/v1/{PID}/fine-tuning-jobs",
                        json={"base_model": "gpt-not-real"})
        assert r.status_code == 400
        assert r.json()["error_code"] == "MA.0006"


# ---------------------------------------------------------------------------
# MaaS — OpenAI-compatible endpoints
# ---------------------------------------------------------------------------

class TestMaas:
    def test_list_models(self, client):
        r = client.get("/v1/models")
        assert r.status_code == 200
        assert r.json()["object"] == "list"
        ids = [m["id"] for m in r.json()["data"]]
        assert "DeepSeek-V3" in ids
        assert "Pangu-N4B" in ids

    def test_chat_completions(self, client):
        r = client.post("/v1/chat/completions",
                        json={"model": "DeepSeek-V3",
                              "messages": [{"role": "user", "content": "hello"}]})
        assert r.status_code == 200
        body = r.json()
        assert body["object"] == "chat.completion"
        assert body["model"] == "DeepSeek-V3"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert "hello" in body["choices"][0]["message"]["content"]
        assert body["usage"]["total_tokens"] > 0
        assert body["usage"]["total_tokens"] == (body["usage"]["prompt_tokens"]
                                                 + body["usage"]["completion_tokens"])

    def test_chat_unknown_model_404(self, client):
        r = client.post("/v1/chat/completions",
                        json={"model": "not-a-model", "messages": []})
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "model_not_found"

    def test_chat_empty_messages_400(self, client):
        r = client.post("/v1/chat/completions",
                        json={"model": "DeepSeek-V3", "messages": []})
        assert r.status_code == 400

    def test_embeddings(self, client):
        r = client.post("/v1/embeddings",
                        json={"model": "bge-m3", "input": ["hello", "world"]})
        assert r.status_code == 200
        body = r.json()
        assert body["object"] == "list"
        assert len(body["data"]) == 2
        assert len(body["data"][0]["embedding"]) == 32
        # Deterministic: same input → same vector
        r2 = client.post("/v1/embeddings",
                         json={"model": "bge-m3", "input": ["hello", "world"]})
        assert r2.json()["data"][0]["embedding"] == body["data"][0]["embedding"]

    def test_api_keys(self, client):
        r = client.post(f"/v1/{PID}/maas/keys", json={"name": "prod-key"})
        assert r.status_code == 200
        assert r.json()["key"].startswith("sk-sim-")
        kid = r.json()["key_id"]

        # List does NOT return the secret again
        r = client.get(f"/v1/{PID}/maas/keys")
        assert "key" not in r.json()["keys"][0]
        assert r.json()["keys"][0]["key_id"] == kid

        assert client.delete(f"/v1/{PID}/maas/keys/{kid}").status_code == 204
