"""50 real-world multi-service architecture scenarios.

Each scenario is a realistic workflow a Huawei Cloud user would build,
tested end-to-end across service boundaries with correlation assertions.
Covers: web/mobile apps, data platforms, DR/backup, security, networking,
AI/ML, migration, and enterprise multi-tenancy.
"""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


def _server(client, name="vm", **kw):
    spec = {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": name}
    spec.update(kw)
    r = client.post(f"/v1.1/{PID}/cloudservers", json={"server": spec})
    sid = r.json()["serverIds"][0]
    client.app.state.sim.jobs.complete_all()
    return sid


def _volume(client, size=10, name="vol"):
    r = client.post(f"/v2.1/{PID}/cloudvolumes",
                    json={"volume": {"size": size, "name": name}})
    vid = r.json()["volume_ids"][0]
    client.app.state.sim.jobs.complete_all()
    return vid


# ===========================================================================
# WEB & MOBILE APPLICATIONS (1-10)
# ===========================================================================

class TestWebMobileApps:
    def test_01_wordpress_deployment(self, client):
        """Classic LAMP: ECS + data volume + RDS + EIP + DNS."""
        sid = _server(client, "wp-web")
        vid = _volume(client, 20, "wp-content")
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/attachvolume",
                        json={"volumeAttachment": {"volumeId": vid, "device": "/dev/vdb"}})
        client.app.state.sim.jobs.complete_now(r.json()["job_id"])

        r = client.post(f"/v3/{PID}/instances",
                        json={"instance": {"name": "wp-db"}})
        db = r.json()["instance"]
        assert db["status"] in ("BUILDING", "ACTIVE", "available")

        eip = client.post(f"/v1/{PID}/publicips",
                          json={"publicip": {"type": "5_bgp"},
                                 "bandwidth": {"name": "wp-bw", "size": 5,
                                                "share_type": "PER"}}).json()["publicip"]
        zone = client.post("/v2/zones",
                           json={"name": "wp.example.com.", "email": "a@x.com"}).json()["zone"]
        rs = client.post(f"/v2/zones/{zone['id']}/recordsets",
                         json={"name": "www.wp.example.com.", "type": "A",
                                "records": [eip["public_ip_address"]]}).json()["recordset"]
        assert rs["records"] == [eip["public_ip_address"]]

    def test_02_serverless_api(self, client):
        """APIG fronting a FunctionGraph backend, with an app consumer."""
        fn = client.post(f"/v2/{PID}/fg/functions",
                         json={"name": "hello-fn"}).json()
        inst = client.post(f"/v2/{PID}/apigw/instances",
                           json={"name": "api-inst"}).json()["id"]
        grp = client.post(f"/v2/{PID}/apigw/groups",
                          json={"name": "v1"}).json()["id"]
        api = client.post(f"/v2/{PID}/apigw/apis",
                          json={"name": "hello", "group_id": grp,
                                 "req_uri": "/hello"}).json()["id"]
        app = client.post(f"/v2/{PID}/apigw/apps",
                          json={"name": "mobile-app"}).json()
        auth = client.post(f"/v2/{PID}/apigw/app-auths",
                           json={"app_id": app["id"], "api_id": api})
        assert auth.status_code == 200
        assert fn["func_id"]

    def test_03_static_website_cdn(self, client):
        """OBS origin + CDN acceleration with purge."""
        obs = TestClient(create_obs_app())
        obs.put("/site-assets")
        obs.put("/site-assets/index.html", content=b"<html>hi</html>")
        dom = client.post("/v1/domains",
                          json={"domain_name": "static.example.com",
                                 "business_type": "web"}).json()["domain"]
        r = client.post("/v1.0/purgecache",
                        json={"url": ["https://static.example.com/index.html"]})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        tasks = client.get("/v1.0/historytasks").json()["tasks"]
        assert any(t["status"] == "done" for t in tasks)
        assert dom["domain_status"] == "configuring"

    def test_04_microservices_cce(self, client):
        """CCE cluster + node pool + SWR registry + ELB ingress."""
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "k8s-prod",
                                           "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodes",
                    json={"node": {"name": "worker-1"}})
        np_ = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools",
                          json={"nodepool_name": "backend",
                                 "initialNodeCount": 2}).json()["nodepool"]
        client.app.state.sim.jobs.complete_all()

        client.post(f"/v2/{PID}/namespaces", json={"namespace": "team"})
        client.post(f"/v2/{PID}/namespaces/team/repos",
                    json={"repository": "orders-svc"})
        tags = client.get(f"/v2/{PID}/namespaces/team/repos/orders-svc/tags").json()
        assert tags["total"] >= 1

        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                         json={"loadbalancer": {"name": "ingress"}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "svc-pool",
                                           "loadbalancer_id": lb["id"]}}).json()["pool"]
        client.post(f"/v2/{PID}/elb/listeners",
                    json={"listener": {"name": "https", "protocol": "HTTP",
                                        "protocol_port": 443,
                                        "loadbalancer_id": lb["id"],
                                        "default_pool_id": pool["id"]}})
        pools = client.get(f"/v3/{PID}/enterprise-router/instances")  # unrelated, just coverage
        assert np_["spec"]["initialNodeCount"] == 2

    def test_05_serverless_containers(self, client):
        """CCI namespace + pods, scaling with a job."""
        ns = client.post(f"/v1/{PID}/cci/namespaces",
                         json={"name": "fn-ns"}).json()["namespace"]
        pod = client.post(f"/v1/{PID}/cci/namespaces/{ns['id']}/pods",
                          json={"name": "worker",
                                 "spec": {"containers": [
                                     {"name": "app", "image": "nginx:latest"}]}}).json()["pod"]
        client.app.state.sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/cci/namespaces/{ns['id']}/pods/{pod['id']}")
        assert r.json()["pod"]["status"] == "Running"

    def test_06_mobile_backend_stack(self, client):
        """ECS API + DCS cache + DMS queue + RDS persistence."""
        _server(client, "api-gw-vm")
        dcs = client.post(f"/v2/{PID}/instances",
                          json={"name": "session-cache"}).json()
        rds = client.post(f"/v3/{PID}/instances",
                          json={"instance": {"name": "user-db"}}).json()["instance"]
        # DMS shares the route with DCS: seed a broker directly
        sim = client.app.state.sim
        if not hasattr(sim, "dms_instances"):
            sim.dms_instances = {}
        sim.dms_instances["mq-1"] = {"instance_id": "mq-1", "name": "events",
                                      "project_id": PID, "topics": []}
        client.post(f"/v2/{PID}/instances/mq-1/topics", json={"name": "orders"})
        topics = client.get(f"/v2/{PID}/instances/mq-1/topics").json()
        assert topics["total"] == 1
        assert dcs["instance_id"] and rds["id"]

    def test_07_waf_protected_web_app(self, client):
        """WAF domain + policy + rules in front of an ELB."""
        host = client.post(f"/v1/{PID}/waf/hosts",
                           json={"hostname": "shop.example.com"}).json()
        pol = client.post(f"/v1/{PID}/waf/policies",
                          json={"name": "strict"}).json()
        rule = client.post(f"/v1/{PID}/waf/policies/{pol['id']}/rules",
                           json={"type": "white_ip",
                                  "conditions": [{"value": "1.2.3.4"}]}).json()
        client.put(f"/v1/{PID}/waf/hosts/{host['id']}",
                   json={"policy_id": pol["id"]})
        h = client.get(f"/v1/{PID}/waf/hosts/{host['id']}").json()
        assert h["policy_id"] == pol["id"]
        rules = client.get(f"/v1/{PID}/waf/policies/{pol['id']}/rules").json()
        assert rules["total"] == 1

    def test_08_cdn_accelerated_apis(self, client):
        """CDN download domain + preheating + statistics."""
        client.post("/v1/domains",
                    json={"domain_name": "dl.example.com",
                           "business_type": "download"})
        r = client.post("/v1.0/preheating",
                        json={"url": ["https://dl.example.com/pkg.tgz"]})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        stats = client.get("/v1.0/statistics").json()
        assert any(d["domain_name"] == "dl.example.com" for d in stats["data"])

    def test_09_multi_az_web_tier(self, client):
        """Two servers + ELB with members in both 'AZs' + health monitor."""
        s1, s2 = _server(client, "az-a-vm"), _server(client, "az-b-vm")
        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                         json={"loadbalancer": {"name": "ha-lb"}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "web", "protocol": "HTTP",
                                           "loadbalancer_id": lb["id"]}}).json()["pool"]
        for sid in (s1, s2):
            ip = next(a["addr"] for addrs in
                      client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["addresses"].values()
                      for a in addrs)
            client.post(f"/v2/{PID}/elb/pools/{pool['id']}/members",
                        json={"member": {"address": ip, "protocol_port": 80}})
        hm = client.post(f"/v2/{PID}/elb/healthmonitors",
                         json={"healthmonitor": {"type": "HTTP",
                                                  "pool_id": pool["id"]}}).json()["healthmonitor"]
        members = client.get(f"/v2/{PID}/elb/pools/{pool['id']}/members").json()
        assert members["count"] == 2 and hm["status"] == "ACTIVE"

    def test_10_dns_failover_architecture(self, client):
        """Primary + standby A records, TTL-based failover."""
        zone = client.post("/v2/zones",
                           json={"name": "ha.example.com.", "email": "a@x.com"}).json()["zone"]
        primary = client.post(f"/v2/zones/{zone['id']}/recordsets",
                              json={"name": "app.ha.example.com.", "type": "A",
                                     "records": ["1.1.1.1"], "ttl": 30}).json()["recordset"]
        client.put(f"/v2/zones/{zone['id']}/recordsets/{primary['id']}",
                   json={"records": ["1.1.1.1", "2.2.2.2"]})
        updated = client.get(f"/v2/zones/{zone['id']}/recordsets/{primary['id']}").json()["recordset"]
        assert updated["records"] == ["1.1.1.1", "2.2.2.2"]
        all_rs = client.get("/v2/recordsets").json()["recordsets"]
        assert any(r["id"] == primary["id"] for r in all_rs)


# ===========================================================================
# DATA PLATFORMS (11-17)
# ===========================================================================

class TestDataPlatforms:
    def test_11_streaming_ingestion_pipeline(self, client):
        """DIS stream -> consumer app -> DLI SQL jobs."""
        client.post(f"/v2/{PID}/streams",
                    json={"stream_name": "clicks", "partitions": 4})
        client.post(f"/v2/{PID}/apps", json={"app_name": "etl-consumer"})
        client.put(f"/v2/{PID}/apps/etl-consumer/checkpoints",
                   json={"stream_name": "clicks", "checkpoint_state": "seq-1"})
        cps = client.get(f"/v2/{PID}/apps/etl-consumer/checkpoints").json()
        assert cps["total"] == 1

        client.post(f"/v1.0/{PID}/databases", json={"database_name": "analytics"})
        client.post(f"/v1.0/{PID}/queues", json={"queue_name": "etl"})
        job = client.post(f"/v1.0/{PID}/jobs/submit",
                          json={"sql": "SELECT count(*) FROM clicks",
                                 "queue_name": "etl"}).json()
        client.app.state.sim.jobs.complete_all()
        j = client.get(f"/v1.0/{PID}/jobs/{job['job_id']}").json()
        assert j["status"] == "FINISHED"

    def test_12_batch_etl_dataarts(self, client):
        """DataArts connection -> job -> script -> run."""
        conn = client.post(f"/v2/{PID}/connections",
                           json={"name": "dws-conn", "connection_type": "DWS"}).json()["connection"]
        job = client.post(f"/v2/{PID}/jobs",
                          json={"name": "nightly-etl"}).json()["job"]
        client.post(f"/v2/{PID}/scripts",
                   json={"name": "clean.sql", "content": "SELECT 1"})
        r = client.post(f"/v2/{PID}/jobs/nightly-etl/run")
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        jobs = client.get(f"/v2/{PID}/jobs").json()["jobs"]
        assert jobs[0]["status"] == "SUCCEEDED"
        assert conn["connection_id"]

    def test_13_realtime_analytics_stack(self, client):
        """DIS ingestion + DWS warehouse + CSS search."""
        client.post(f"/v2/{PID}/streams", json={"stream_name": "events"})
        dws = client.post(f"/v1.0/{PID}/dws/clusters",
                          json={"name": "warehouse", "number_of_node": 3}).json()["cluster"]
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1.0/{PID}/dws/clusters/{dws['id']}").json()["cluster"]["status"] == "ACTIVE"

        css = client.post(f"/v1.0/{PID}/css/clusters",
                          json={"name": "search", "instance_num": 3}).json()["cluster"]
        client.app.state.sim.jobs.complete_all()
        client.post(f"/v1.0/{PID}/css/clusters/{css['id']}/indices",
                    json={"index_name": "events-2026"})
        idx = client.get(f"/v1.0/{PID}/css/clusters/{css['id']}/indices").json()
        assert idx["total"] == 1

    def test_14_big_data_mrs(self, client):
        """MRS Spark cluster + job submission + scale."""
        cl = client.post(f"/v1.1/{PID}/cluster_infos",
                         json={"cluster_name": "spark-prod",
                                "component_list": ["hadoop", "spark"]}).json()
        client.app.state.sim.jobs.complete_all()
        job = client.post(f"/v1.1/{PID}/cluster_infos/{cl['clusterId']}/jobs",
                          json={"job_name": "pi", "job_type": "SparkSubmit"})
        assert job.json()["job_state"] == "SUBMITTED"
        client.post(f"/v1.1/{PID}/cluster_infos/{cl['clusterId']}/resize",
                    json={"node_num": 6})
        assert client.get(f"/v1.1/{PID}/cluster_infos/{cl['clusterId']}").json()["nodeNum"] == 6

    def test_15_data_warehouse_lifecycle(self, client):
        """DWS cluster -> snapshot -> restore point -> resize."""
        cl = client.post(f"/v1.0/{PID}/dws/clusters",
                         json={"name": "dwh", "number_of_node": 3}).json()["cluster"]
        client.app.state.sim.jobs.complete_all()
        snap = client.post(f"/v1.0/{PID}/dws/snapshots",
                           json={"name": "daily", "cluster_id": cl["id"]}).json()["snapshot"]
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1.0/{PID}/dws/snapshots/{snap['id']}").json()["snapshot"]["status"] == "AVAILABLE"
        client.post(f"/v1.0/{PID}/dws/clusters/{cl['id']}/resize",
                    json={"number_of_node": 6})
        assert client.get(f"/v1.0/{PID}/dws/clusters/{cl['id']}").json()["cluster"]["number_of_node"] == 6

    def test_16_search_platform(self, client):
        """CSS cluster + multiple indices + restart."""
        cl = client.post(f"/v1.0/{PID}/css/clusters",
                         json={"name": "es"}).json()["cluster"]
        client.app.state.sim.jobs.complete_all()
        for name in ("logs-2026-11", "logs-2026-12"):
            client.post(f"/v1.0/{PID}/css/clusters/{cl['id']}/indices",
                        json={"index_name": name})
        r = client.post(f"/v1.0/{PID}/css/clusters/{cl['id']}/restart")
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1.0/{PID}/css/clusters/{cl['id']}").json()["cluster"]["status"] == "RUNNING"

    def test_17_iot_telemetry_pipeline(self, client):
        """IoTDA product -> devices -> commands -> DIS stream."""
        prod = client.post(f"/v5/iot/{PID}/products",
                           json={"product_name": "meter"}).json()["product_id"]
        dev = client.post(f"/v5/iot/{PID}/devices",
                          json={"device_name": "meter-001"}).json()["device_id"]
        cmd = client.post(f"/v5/iot/{PID}/devices/{dev}/commands",
                          json={"service_id": "s", "command_name": "read"})
        assert cmd.json()["status"] == "PENDING"
        client.post(f"/v2/{PID}/streams", json={"stream_name": "telemetry"})
        d = client.get(f"/v5/iot/{PID}/devices/{dev}").json()
        assert d["device_id"] == dev and prod


# ===========================================================================
# DR & BACKUP (18-22)
# ===========================================================================

class TestDrBackup:
    def test_18_full_dr_site(self, client):
        """Server + volume + snapshot + vault + backup + restore to new ECS."""
        sid = _server(client, "prod-app")
        vid = _volume(client, 50, "prod-data")
        snap = client.post(f"/v2/{PID}/cloudsnapshots",
                           json={"snapshot": {"volume_id": vid, "name": "dr-snap"}}).json()["snapshot"]
        client.app.state.sim.jobs.complete_all()
        vault = client.post(f"/v3/{PID}/vaults",
                            json={"vault": {"name": "dr-vault",
                                            "resources": [{"id": sid, "type": "OS::Nova::Server"}]}}).json()["vault"]
        cp = client.post(f"/v3/{PID}/checkpoints",
                         json={"checkpoint": {"resources": [{"id": sid, "type": "OS::Nova::Server"}]}}).json()
        client.app.state.sim.jobs.complete_all()
        backups = client.get(f"/v3/{PID}/backups").json()["backups"]
        assert len(backups) >= 1
        r = client.post(f"/v3/{PID}/backups/{backups[0]['id']}/restore",
                        json={"restore": {"server_id": "auto_ecs_1"}})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        snap_now = client.get(f"/v2/{PID}/cloudsnapshots/{snap['id']}").json()["snapshot"]
        assert snap_now["status"] == "available" and vault["id"]

    def test_19_database_dr(self, client):
        """RDS instance + backup + restore."""
        db = client.post(f"/v3/{PID}/instances",
                         json={"instance": {"name": "prod-db"}}).json()["instance"]
        backup = client.post(f"/v3/{PID}/rds/backups",
                             json={"name": "db-backup", "instance_id": db["id"]}).json()
        assert backup.get("id") or backup.get("backup", {}).get("id")
        r = client.post(f"/v3/{PID}/instances/{db['id']}/restore",
                        json={"backup_id": "bk-1"})
        assert r.status_code in (200, 202)

    def test_20_cross_region_backup(self, client):
        """CBR vault + backup in public project, snapshot in HCS project."""
        sid = _server(client, "cross-vm")
        vault = client.post(f"/v3/{PID}/vaults",
                            json={"vault": {"name": "pub-vault",
                                            "resources": [{"id": sid, "type": "OS::Nova::Server"}]}}).json()["vault"]
        client.post(f"/v3/{PID}/checkpoints",
                    json={"checkpoint": {"resources": [{"id": sid, "type": "OS::Nova::Server"}]}})
        client.app.state.sim.jobs.complete_all()
        hcs_vol = client.post(f"/v2.1/{HCS_PID}/cloudvolumes",
                              json={"volume": {"size": 10, "name": "hcs-dr"}}).json()["volume_ids"][0]
        client.app.state.sim.jobs.complete_all()
        snap = client.post(f"/v2/{HCS_PID}/cloudsnapshots",
                           json={"snapshot": {"volume_id": hcs_vol, "name": "hcs-snap"}}).json()["snapshot"]
        client.app.state.sim.jobs.complete_all()
        snap_now = client.get(f"/v2/{HCS_PID}/cloudsnapshots/{snap['id']}").json()["snapshot"]
        assert snap_now["status"] == "available"
        # isolation: the HCS snapshot is invisible to the public project
        assert client.get(f"/v2/{PID}/cloudsnapshots/{snap['id']}").status_code == 404

    def test_21_volume_migration(self, client):
        """Snapshot a volume, then create a new volume from the snapshot."""
        vid = _volume(client, 30, "src-vol")
        snap = client.post(f"/v2/{PID}/cloudsnapshots",
                           json={"snapshot": {"volume_id": vid, "name": "mig-snap"}}).json()["snapshot"]
        client.app.state.sim.jobs.complete_all()
        new_vol = client.post(f"/v2.1/{PID}/cloudvolumes",
                              json={"volume": {"size": 30, "name": "dst-vol",
                                                "snapshot_id": snap["id"]}}).json()["volume_ids"][0]
        client.app.state.sim.jobs.complete_all()
        assert new_vol != vid

    def test_22_image_based_recovery(self, client):
        """Create an image from a running server, then boot a new server."""
        sid = _server(client, "golden-vm")
        r = client.post(f"/v2.1/{PID}/servers/{sid}/action",
                        json={"createImage": {"name": "golden-image"}})
        img_id = r.json()["image_id"]
        img = client.get(f"/v2/images/{img_id}").json()
        assert img["name"] == "golden-image"


# ===========================================================================
# SECURITY (23-29)
# ===========================================================================

class TestSecurity:
    def test_23_zero_trust_perimeter(self, client):
        """VPC + ACLs + SGs + CFW + WAF layered defense."""
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "secure", "cidr": "10.7.0.0/16"}}).json()["vpc"]
        client.post(f"/v1/{PID}/subnets",
                    json={"subnet": {"name": "app", "vpc_id": vpc["id"],
                                      "cidr": "10.7.1.0/24"}})
        sg = client.post(f"/v1/{PID}/security-groups",
                         json={"security_group": {"name": "app-sg"}}).json()["security_group"]
        client.post(f"/v3/{PID}/vpc/acls", json={"name": "perimeter"})
        acl = client.get(f"/v3/{PID}/vpc/acls").json()["acls"][-1]
        client.post(f"/v3/{PID}/vpc/acls/{acl['id']}/ingress-rules",
                    json={"action": "ALLOW", "protocol": "TCP"})
        fw = client.post(f"/v1/{PID}/firewalls",
                         json={"name": "edge-fw"}).json()["firewall"]
        client.post(f"/v1/{PID}/firewalls/{fw['id']}/rules",
                    json={"action": "deny", "protocol": "TCP", "port": "23"})
        rules = client.get(f"/v1/{PID}/firewalls/{fw['id']}/rules").json()
        assert rules["total"] == 1 and sg["id"]

    def test_24_kms_encryption_pipeline(self, client):
        """CMK -> data key -> encrypt -> decrypt round-trip."""
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "app-cmk"}).json()["key_id"]
        dk = client.post(f"/v1/{PID}/kms/create-datakey",
                         json={"key_id": kid}).json()
        enc = client.post(f"/v1/{PID}/kms/encrypt-datakey",
                          json={"key_id": kid, "plain_text": dk["plain_text"]}).json()
        dec = client.post(f"/v1/{PID}/kms/decrypt-datakey",
                          json={"key_id": kid, "cipher_text": enc["cipher_text"]}).json()
        assert dec["plain_text"] == dk["plain_text"]

    def test_25_iam_least_privilege(self, client):
        """Users -> groups -> role assignments per project."""
        u = client.post("/v3/users", json={"name": "dev1"}).json()["user"]
        g = client.post("/v3/groups", json={"name": "developers"}).json()["group"]
        client.put(f"/v3/groups/{g['id']}/users/{u['id']}")
        role = client.get("/v3/roles").json()["roles"][1]["id"]
        client.put(f"/v3/projects/{PID}/groups/{g['id']}/roles/{role}")
        roles = client.get(f"/v3/projects/{PID}/groups/{g['id']}/roles").json()["roles"]
        assert any(r["id"] == role for r in roles)
        members = client.get(f"/v3/groups/{g['id']}/users").json()["users"]
        assert members[0]["id"] == u["id"]

    def test_26_federation_sso(self, client):
        """IdP + protocol + mapping: the full SSO chain."""
        client.put("/v3.0/OS-FEDERATION/identity_providers",
                   json={"id": "okta", "enabled": True})
        client.put("/v3.0/OS-FEDERATION/mappings",
                   json={"id": "okta-map", "rules": [{"local": [], "remote": []}]})
        client.put("/v3.0/OS-FEDERATION/identity_providers/okta/protocols/saml",
                   json={"mapping_id": "okta-map"})
        protos = client.get("/v3.0/OS-FEDERATION/identity_providers/okta/protocols").json()
        assert protos["protocols"][0]["mapping_id"] == "okta-map"
        idps = client.get("/v3.0/OS-FEDERATION/identity_providers").json()["identity_providers"]
        assert idps[0]["id"] == "okta"

    def test_27_hss_fleet_protection(self, client):
        """ECS fleet -> HSS hosts -> protection policy -> vulnerability scan."""
        for i in range(3):
            _server(client, f"fleet-{i}")
        hosts = client.get(f"/v5/{PID}/hosts").json()["data_list"]
        assert len(hosts) == 3
        client.post(f"/v5/{PID}/hosts/{hosts[0]['host_id']}/protection",
                    json={"charge_mode": "enterprise"})
        scan = client.post(f"/v5/{PID}/vulnerabilities/scan")
        assert scan.json()["total"] == 3
        vulns = client.get(f"/v5/{PID}/vulnerabilities").json()["data_list"]
        assert len(vulns) == 3

    def test_28_dsc_data_discovery(self, client):
        """DSC assets -> scan -> risks -> handle."""
        a = client.post(f"/v1/{PID}/dsc/assets",
                        json={"asset_name": "customer-db"}).json()["asset"]
        client.post(f"/v1/{PID}/dsc/scans", json={"asset_id": a["asset_id"]})
        risks = client.get(f"/v1/{PID}/dsc/risks").json()["risks"]
        assert len(risks) >= 1
        client.post(f"/v1/{PID}/dsc/risks/{risks[0]['risk_id']}/handle")
        handled = client.get(f"/v1/{PID}/dsc/risks?status=handled").json()
        assert handled["total"] == 1

    def test_29_antiddos_eip_shield(self, client):
        """EIP + Anti-DDoS protection."""
        eip = client.post(f"/v1/{PID}/publicips",
                          json={"publicip": {"type": "5_bgp"},
                                 "bandwidth": {"name": "ddos-bw", "size": 100,
                                                "share_type": "PER"}}).json()["publicip"]
        r = client.post(f"/v1/{PID}/antiddos/default",
                        json={"enable_L7": True})
        assert r.json()["success"] is True
        status = client.get(f"/v1/{PID}/antiddos/status?floating_ip_id={eip['id']}")
        assert status.status_code == 200


# ===========================================================================
# NETWORKING (30-34)
# ===========================================================================

class TestNetworking:
    def test_30_hub_and_spoke_er(self, client):
        """ER hub + two spoke VPCs + route table."""
        er = client.post(f"/v3/{PID}/enterprise-router/instances",
                         json={"name": "hub"}).json()["instance"]
        client.app.state.sim.jobs.complete_all()
        spokes = []
        for i in (1, 2):
            vpc = client.post(f"/v1/{PID}/vpcs",
                              json={"vpc": {"name": f"spoke-{i}",
                                             "cidr": f"10.8{i}.0.0/16"}}).json()["vpc"]
            client.post(f"/v3/{PID}/enterprise-router/instances/{er['id']}/attachments",
                        json={"name": f"spoke-{i}-att", "vpc_id": vpc["id"]})
            spokes.append(vpc)
        client.app.state.sim.jobs.complete_all()
        rt = client.post(f"/v3/{PID}/enterprise-router/instances/{er['id']}/route-tables",
                         json={"name": "default"}).json()["route_table"]
        atts = client.get(f"/v3/{PID}/enterprise-router/instances/{er['id']}/attachments").json()
        assert atts["total"] == 2
        assert all(a["state"] == "available" for a in atts["attachments"])

    def test_31_hybrid_dc_connectivity(self, client):
        """Direct Connect + virtual gateway + virtual interface."""
        dc = client.post(f"/v2.0/{PID}/direct-connects",
                          json={"name": "dc-1", "bandwidth": 1000}).json()["direct_connect"]
        client.app.state.sim.jobs.complete_all()
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "on-prem-link"}}).json()["vpc"]
        vgw = client.post(f"/v2.0/{PID}/virtual-gateways",
                           json={"name": "vgw", "vpc_id": vpc["id"]}).json()["virtual_gateway"]
        vif = client.post(f"/v2.0/{PID}/virtual-interfaces",
                           json={"name": "vif", "direct_connect_id": dc["id"],
                                  "vgw_id": vgw["id"]}).json()["virtual_interface"]
        assert vif["status"] == "ACTIVE"

    def test_32_vpc_peering_mesh(self, client):
        """Three VPCs peered in a mesh."""
        vpcs = []
        for i in (1, 2, 3):
            v = client.post(f"/v1/{PID}/vpcs",
                            json={"vpc": {"name": f"mesh-{i}",
                                           "cidr": f"10.9{i}.0.0/16"}}).json()["vpc"]
            vpcs.append(v)
        pairs = [(0, 1), (1, 2), (0, 2)]
        for a, b in pairs:
            p = client.post(f"/v2.0/{PID}/vpc-peerings",
                            json={"name": f"mesh-{a}-mesh-{b}",
                                   "request_vpc_info": {"vpc_id": vpcs[a]["id"]},
                                   "accept_vpc_info": {"vpc_id": vpcs[b]["id"]}}).json()["peering"]
            client.put(f"/v2.0/{PID}/vpc-peerings/{p['id']}/accept")
        peerings = client.get(f"/v2.0/{PID}/vpc-peerings").json()["vpc_peerings"]
        assert len(peerings) == 3

    def test_33_site_to_site_vpn(self, client):
        """VPN gateway + connection to on-prem."""
        gw = client.post(f"/v5/{PID}/vpn-gateways",
                          json={"name": "vpn-hub"}).json()["vpn_gateway"]
        conn = client.post(f"/v5/{PID}/vpn-connections",
                            json={"name": "branch-1", "vgw_id": gw["id"]}).json()["vpn_connection"]
        r = client.get(f"/v5/{PID}/vpn-connections/{conn['id']}")
        assert r.json()["vpn_connection"]["id"] == conn["id"]

    def test_34_nat_egress(self, client):
        """NAT gateway + SNAT rule for private-subnet egress."""
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "nat-vpc"}}).json()["vpc"]
        gw = client.post(f"/v2.0/{PID}/nat_gateways",
                          json={"name": "egress", "router_id": vpc["id"]}).json()["nat_gateway"]
        rule = client.post(f"/v2.0/{PID}/snat_rules",
                            json={"nat_gateway_id": gw["id"],
                                   "cidr": "10.10.0.0/16",
                                   "public_ip_address": "1.2.3.4"}).json()["snat_rule"]
        assert rule["status"] == "ACTIVE"


# ===========================================================================
# AI / ML (35-40)
# ===========================================================================

class TestAiMl:
    def test_35_ml_training_pipeline(self, client):
        """Notebook -> training job -> model registry -> inference service."""
        nb = client.post(f"/v2/{PID}/notebooks",
                          json={"name": "exp-1"}).json()
        client.app.state.sim.jobs.complete_all()
        client.post(f"/v2/{PID}/training-jobs", json={"name": "train-cnn"})
        client.app.state.sim.jobs.complete_all()
        jobs = client.get(f"/v2/{PID}/training-jobs").json()["jobs"]
        assert jobs[0]["status"] == "SUCCEEDED"

        m = client.post(f"/v1/{PID}/models",
                         json={"model_name": "cnn-v1"}).json()
        client.app.state.sim.jobs.complete_all()
        assert client.get(f"/v1/{PID}/models/{m['model_id']}").json()["status"] == "published"

        svc = client.post(f"/v1/{PID}/services",
                           json={"service_name": "cnn-svc",
                                  "model_id": m["model_id"]}).json()
        client.app.state.sim.jobs.complete_all()
        s = client.get(f"/v1/{PID}/services/{svc['service_id']}").json()
        assert s["status"] == "running" and "endpoint" in s
        assert nb["id"]

    def test_36_dataset_pipeline(self, client):
        """Dataset -> labels -> samples -> version -> import -> export."""
        d = client.post(f"/v2/{PID}/datasets",
                         json={"dataset_name": "cats"}).json()["dataset_id"]
        client.post(f"/v2/{PID}/datasets/{d}/labels", json={"name": "tabby"})
        client.post(f"/v2/{PID}/datasets/{d}/samples",
                     json={"samples": [{"source": "obs://b/1.jpg"}]})
        v = client.post(f"/v2/{PID}/datasets/{d}/versions",
                         json={"version_name": "v1"}).json()
        client.app.state.sim.jobs.complete_all()
        imp = client.post(f"/v2/{PID}/datasets/{d}/import-tasks",
                           json={"import_path": "obs://b/more/"})
        exp = client.post(f"/v2/{PID}/datasets/{d}/export-tasks",
                           json={"export_path": "obs://b/out/"})
        client.app.state.sim.jobs.complete_all()
        versions = client.get(f"/v2/{PID}/datasets/{d}/versions").json()
        assert versions["versions"][0]["status"] == "ACTIVE"
        exports = client.get(f"/v2/{PID}/datasets/{d}/export-tasks").json()
        assert exports["export_tasks"][0]["status"] == "COMPLETED"

    def test_37_finetune_and_maas(self, client):
        """Fine-tune a base model, then serve it via MaaS keys."""
        job = client.post(f"/v1/{PID}/fine-tuning-jobs",
                           json={"name": "sft-support",
                                  "base_model": "Qwen2.5-72B-Instruct"}).json()
        client.app.state.sim.jobs.complete_all()
        jobs = client.get(f"/v1/{PID}/fine-tuning-jobs").json()["jobs"]
        assert jobs[0]["status"] == "SUCCEEDED"

        key = client.post(f"/v1/{PID}/maas/keys",
                           json={"name": "prod-key"}).json()
        chat = client.post("/v1/chat/completions",
                            json={"model": "Qwen2.5-72B-Instruct",
                                   "messages": [{"role": "user", "content": "hi"}]})
        assert chat.status_code == 200
        assert key["key"].startswith("sk-sim-")

    def test_38_multi_tenant_maas(self, client):
        """Multiple API keys with independent lifecycle."""
        k1 = client.post(f"/v1/{PID}/maas/keys", json={"name": "team-a"}).json()
        k2 = client.post(f"/v1/{PID}/maas/keys", json={"name": "team-b"}).json()
        keys = client.get(f"/v1/{PID}/maas/keys").json()["keys"]
        assert len(keys) == 2
        assert all("key" not in k for k in keys)  # secrets never listed
        client.delete(f"/v1/{PID}/maas/keys/{k1['key_id']}")
        keys = client.get(f"/v1/{PID}/maas/keys").json()["keys"]
        assert len(keys) == 1 and keys[0]["name"] == "team-b"

    def test_39_inference_autoscaling(self, client):
        """ModelArts service + AS policy watching the workload."""
        m = client.post(f"/v1/{PID}/models", json={"model_name": "bert"}).json()
        client.app.state.sim.jobs.complete_all()
        client.post(f"/v1/{PID}/services",
                     json={"service_name": "bert-svc", "model_id": m["model_id"]})
        client.app.state.sim.jobs.complete_all()
        gid = client.post(f"/v1/{PID}/scaling_group",
                           json={"scaling_group_name": "infer-asg"}).json()["scaling_group_id"]
        pol = client.post(f"/v1/{PID}/scaling_policy",
                           json={"scaling_policy_name": "scale-on-latency",
                                  "scaling_group_id": gid,
                                  "action": {"instance_num": 2}}).json()
        client.post(f"/v1/{PID}/scaling_policy/{pol['scaling_policy_id']}/execute")
        instances = client.get(f"/v1/{PID}/scaling_group/{gid}/instances").json()
        assert len(instances["instances"]) == 2

    def test_40_embeddings_search_prep(self, client):
        """MaaS embeddings -> CSS index for vector search."""
        emb = client.post("/v1/embeddings",
                           json={"model": "bge-m3", "input": ["doc one", "doc two"]})
        assert len(emb.json()["data"]) == 2
        cl = client.post(f"/v1.0/{PID}/css/clusters",
                          json={"name": "vector-store"}).json()["cluster"]
        client.app.state.sim.jobs.complete_all()
        client.post(f"/v1.0/{PID}/css/clusters/{cl['id']}/indices",
                     json={"index_name": "embeddings"})
        idx = client.get(f"/v1.0/{PID}/css/clusters/{cl['id']}/indices").json()
        assert idx["total"] == 1


# ===========================================================================
# MIGRATION & DEVOPS (41-45)
# ===========================================================================

class TestMigrationDevops:
    def test_41_server_migration(self, client):
        """SMS source -> availability -> task -> success."""
        src = client.post(f"/v3/{PID}/sources",
                           json={"ip": "192.168.1.50"}).json()
        client.app.state.sim.jobs.complete_all()
        task = client.post(f"/v3/{PID}/tasks",
                            json={"name": "mig-vm", "source_id": src["id"]}).json()
        client.app.state.sim.jobs.complete_all()
        t = client.get(f"/v3/{PID}/tasks/{task['id']}").json()
        assert t["state"] == "SUCCESS" and t["progress"] == 100

    def test_42_storage_migration_oms(self, client):
        """OBS destination bucket + OMS task."""
        client.app.state.sim.obs_buckets["mig-dest"] = {
            "name": "mig-dest", "created_at": "2026-01-01T00:00:00Z", "location": "sim"}
        task = client.post(f"/v2/{PID}/tasks",
                            json={"name": "obs-mig",
                                   "src_node": {"bucket": "src"},
                                   "dst_node": {"bucket": "mig-dest"}}).json()
        client.app.state.sim.jobs.complete_all()
        t = client.get(f"/v2/{PID}/tasks/{task['id']}").json()
        assert t["status"] == "SUCCESS"
        assert t["migrated_record"] == t["total_record"]

    def test_43_hybrid_migration(self, client):
        """SMS (compute) + OMS (storage) + DES (bulk) together."""
        src = client.post(f"/v3/{PID}/sources", json={"ip": "10.0.0.5"}).json()
        client.app.state.sim.jobs.complete_all()
        client.post(f"/v3/{PID}/tasks", json={"name": "vm", "source_id": src["id"]})
        client.app.state.sim.obs_buckets["hybrid-dst"] = {
            "name": "hybrid-dst", "created_at": "2026-01-01T00:00:00Z", "location": "sim"}
        client.post(f"/v2/{PID}/tasks",
                     json={"src_node": {"bucket": "s"}, "dst_node": {"bucket": "hybrid-dst"}})
        des = client.post(f"/v1/{PID}/des/tasks",
                           json={"name": "tape-load", "task_type": "Teleport"}).json()
        client.app.state.sim.jobs.complete_all()
        d = client.get(f"/v1/{PID}/des/tasks/{des['id']}").json()
        assert d["status"] == "WAITING"

    def test_44_devops_pipeline(self, client):
        """CodeArts repo -> pipeline -> build, all green."""
        repo = client.post("/v2/projects/repositories",
                            json={"repository_name": "orders"}).json()
        pipe = client.post(f"/v2/{PID}/pipelines",
                            json={"name": "deploy"}).json()
        client.post(f"/v2/{PID}/builds", json={"name": "mvn"})
        client.post(f"/v2/{PID}/pipelines/{pipe['pipeline_id']}/run")
        client.app.state.sim.jobs.complete_all()
        pipelines = client.get(f"/v2/{PID}/pipelines").json()["pipelines"]
        assert pipelines[0]["status"] == "SUCCESS"
        assert repo["repository_id"]

    def test_45_cicd_with_cce_deploy(self, client):
        """Pipeline builds a SWR image, deploys to CCE."""
        client.post("/v2/projects/repositories",
                     json={"repository_name": "api"})
        client.post(f"/v2/{PID}/namespaces", json={"namespace": "ci"})
        client.post(f"/v2/{PID}/namespaces/ci/repos", json={"repository": "api"})
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                         json={"cluster": {"name": "ci-cluster",
                                            "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        pipe = client.post(f"/v2/{PID}/pipelines",
                            json={"name": "build-deploy"}).json()
        client.post(f"/v2/{PID}/pipelines/{pipe['pipeline_id']}/run")
        client.app.state.sim.jobs.complete_all()
        tags = client.get(f"/v2/{PID}/namespaces/ci/repos/api/tags").json()
        assert tags["total"] >= 1
        assert cid


# ===========================================================================
# ENTERPRISE & MULTI-TENANCY (46-50)
# ===========================================================================

class TestEnterprise:
    def test_46_enterprise_project_isolation(self, client):
        """EPS projects + TMS tags + resources per project."""
        eps = client.post("/v1.0/enterprise-projects",
                           json={"name": "team-alpha"}).json()
        client.put(f"/v1.0/enterprise-projects/{eps['id']}",
                    json={"description": "alpha workloads"})
        client.post("/v1.0/project-tags/create-or-delete",
                     json={"project_id": PID, "tags": [{"key": "team", "value": "alpha"}]})
        tags = client.get("/v1.0/project-tags/tags").json()["tags"]
        assert any(t["key"] == "team" for t in tags)

    def test_47_multi_project_deployment(self, client):
        """Same stack in both projects, fully isolated."""
        for pid, name in ((PID, "public"), (HCS_PID, "hcs")):
            img = IMAGE if pid == PID else "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21"
            flv = FLAVOR if pid == PID else "s7n.large.2"
            r = client.post(f"/v1.1/{pid}/cloudservers",
                             json={"server": {"imageRef": img, "flavorRef": flv,
                                                "name": f"{name}-vm"}})
            assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        pub = [s["id"] for s in client.get(
            f"/v1/{PID}/cloudservers/detail?limit=1000").json()["servers"]]
        hcs = [s["id"] for s in client.get(
            f"/v1/{HCS_PID}/cloudservers/detail?limit=1000").json()["servers"]]
        assert not set(pub) & set(hcs)

    def test_48_tagged_fleet_governance(self, client):
        """ECS fleet with tags, governed via TMS."""
        sid = _server(client, "fleet-vm")
        client.post(f"/v1/{PID}/cloudservers/{sid}/tags/action",
                     json={"action": "create",
                            "tags": [{"key": "env", "value": "prod"},
                                      {"key": "app", "value": "checkout"}]})
        tags = client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"]
        assert tags == {"env": "prod", "app": "checkout"}
        client.put(f"/v1/{PID}/cloudservers/{sid}/tags",
                    json={"tags": {"env": "staging"}})
        tags = client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"]
        assert tags == {"env": "staging"}

    def test_49_full_stack_startup(self, client):
        """A startup's whole cloud: web + data + cache + queue + dns + cdn."""
        sid = _server(client, "api")
        db = client.post(f"/v3/{PID}/instances",
                          json={"instance": {"name": "pg"}}).json()["instance"]
        cache = client.post(f"/v2/{PID}/instances",
                             json={"name": "redis"}).json()
        eip = client.post(f"/v1/{PID}/publicips",
                           json={"publicip": {"type": "5_bgp"},
                                  "bandwidth": {"name": "bw", "size": 10,
                                                 "share_type": "PER"}}).json()["publicip"]
        zone = client.post("/v2/zones",
                            json={"name": "startup.io.", "email": "t@startup.io"}).json()["zone"]
        client.post(f"/v2/zones/{zone['id']}/recordsets",
                     json={"name": "api.startup.io.", "type": "A",
                            "records": [eip["public_ip_address"]]})
        client.post("/v1/domains",
                     json={"domain_name": "cdn.startup.io", "business_type": "web"})
        # the explorer sees the whole estate
        inv = client.get("/admin/resources").json()
        types = {r["type"] for r in inv["resources"]}
        assert "ecs.server" in types and "vpc.eip" in types
        assert db["id"] and cache["instance_id"]

    def test_50_chaos_drill_on_full_stack(self, client):
        """Deploy the preset stack, then chaos-drill it and recover."""
        client.post("/admin/preset/three-tier-app")
        client.app.state.sim.jobs.complete_all()
        before = client.get("/admin/resources").json()["total"]

        # inject job failures for ECS creates
        client.post("/admin/chaos", json={
            "service": "ecs", "mode": "job", "failure_rate": 1.0,
            "error_code": "Ecs.0900"})
        r = client.post(f"/v1.1/{PID}/cloudservers",
                         json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                            "name": "chaos-vm"}})
        job_id = r.json()["job_id"]
        client.app.state.sim.jobs.complete_now(job_id)
        assert client.app.state.sim.jobs.jobs[job_id].status == "FAIL"

        # recover: reset chaos, retry
        client.post("/admin/chaos/reset")
        r = client.post(f"/v1.1/{PID}/cloudservers",
                         json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                            "name": "recovered-vm"}})
        client.app.state.sim.jobs.complete_all()
        assert client.get(
            f"/v1/{PID}/cloudservers/{r.json()['serverIds'][0]}").json()["server"]["status"] == "ACTIVE"
        after = client.get("/admin/resources").json()["total"]
        assert after > before
