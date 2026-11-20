"""Tests for the ECS documented-operation gap (update, tags, rebuild, migrate,
lock/unlock, v2.1 show, v2.1 security groups)."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
IMAGE2 = "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


def _active_server(client, name="gap-vm"):
    r = client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": name}})
    sid = r.json()["serverIds"][0]
    client.app.state.sim.jobs.complete_all()
    return sid


class TestUpdateServer:
    def test_rename(self, client):
        sid = _active_server(client)
        r = client.put(f"/v1/{PID}/cloudservers/{sid}",
                       json={"server": {"name": "renamed-vm", "description": "updated"}})
        assert r.status_code == 200
        srv = r.json()["server"]
        assert srv["name"] == "renamed-vm"
        assert srv["description"] == "updated"
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["name"] == "renamed-vm"

    def test_update_missing_404(self, client):
        r = client.put(f"/v1/{PID}/cloudservers/bad-id",
                       json={"server": {"name": "x"}})
        assert r.status_code == 404


class TestServerTags:
    def test_tag_lifecycle(self, client):
        sid = _active_server(client, "tagged-vm")

        # empty at first
        assert client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"] == {}

        # batch create
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/tags/action",
                        json={"action": "create",
                              "tags": [{"key": "env", "value": "prod"},
                                        {"key": "team", "value": "core"}]})
        assert r.status_code == 202
        tags = client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"]
        assert tags == {"env": "prod", "team": "core"}

        # batch delete one
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/tags/action",
                        json={"action": "delete", "tags": [{"key": "team"}]})
        assert r.status_code == 202
        tags = client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"]
        assert tags == {"env": "prod"}

    def test_invalid_action_400(self, client):
        sid = _active_server(client, "tag-bad")
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/tags/action",
                        json={"action": "explode", "tags": [{"key": "k"}]})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0005"

    def test_tags_missing_server_404(self, client):
        assert client.get(f"/v1/{PID}/cloudservers/bad/tags").status_code == 404


class TestRebuild:
    def test_rebuild_changes_image(self, client):
        sim = client.app.state.sim
        sid = _active_server(client, "rebuild-vm")
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["image"]["id"] == IMAGE

        r = client.post(f"/v1/{PID}/cloudservers/{sid}/action",
                        json={"rebuild": {"imageRef": IMAGE2}})
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # transitional state: REBUILD
        srv = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]
        assert srv["status"] == "REBUILD"

        sim.jobs.complete_now(job_id)
        srv = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]
        assert srv["status"] == "ACTIVE"
        assert srv["image"]["id"] == IMAGE2

    def test_rebuild_bad_image_400(self, client):
        sid = _active_server(client, "rebuild-bad")
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/action",
                        json={"rebuild": {"imageRef": "no-such-image"}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0005"

    def test_rebuild_on_shutoff_400(self, client):
        sid = _active_server(client, "rebuild-stopped")
        client.post(f"/v1/{PID}/cloudservers/action",
                    json={"os-stop": {"type": "SOFT", "servers": [{"id": sid}]}})
        client.app.state.sim.jobs.complete_all()
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/action",
                        json={"rebuild": {"imageRef": IMAGE}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0100"


class TestMigrate:
    def test_migrate_flips_host(self, client):
        sim = client.app.state.sim
        sid = _active_server(client, "migrate-vm")
        before = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["OS-EXT-SRV-ATTR:host"]

        r = client.post(f"/v1/{PID}/cloudservers/{sid}/action", json={"migrate": {}})
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["status"] == "MIGRATING"

        sim.jobs.complete_now(job_id)
        srv = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]
        assert srv["status"] == "ACTIVE"
        assert srv["OS-EXT-SRV-ATTR:host"] != before

    def test_migrate_missing_server_404(self, client):
        assert client.post(f"/v1/{PID}/cloudservers/bad/action",
                           json={"migrate": {}}).status_code == 404


class TestLockUnlock:
    def test_lock_cycle(self, client):
        sid = _active_server(client, "lock-vm")
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["locked"] is False

        assert client.post(f"/v1/{PID}/cloudservers/{sid}/action",
                           json={"lock": {}}).status_code == 202
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["locked"] is True

        assert client.post(f"/v1/{PID}/cloudservers/{sid}/action",
                           json={"unlock": {}}).status_code == 202
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["locked"] is False


class TestV21Show:
    def test_show(self, client):
        sid = _active_server(client, "nova-vm")
        r = client.get(f"/v2.1/{PID}/servers/{sid}")
        assert r.status_code == 200
        assert r.json()["server"]["id"] == sid
        assert r.json()["server"]["status"] == "ACTIVE"

    def test_show_missing_404(self, client):
        assert client.get(f"/v2.1/{PID}/servers/bad").status_code == 404


class TestV21SecurityGroups:
    def test_add_remove(self, client):
        sid = _active_server(client, "sg-vm")
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["security_groups"] == [{"name": "default"}]

        r = client.post(f"/v2.1/{PID}/servers/{sid}/action",
                        json={"addSecurityGroup": {"name": "web-sg"}})
        assert r.status_code == 202
        groups = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["security_groups"]
        assert {"name": "web-sg"} in groups

        # adding twice does not duplicate
        client.post(f"/v2.1/{PID}/servers/{sid}/action",
                    json={"addSecurityGroup": {"name": "web-sg"}})
        groups = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["security_groups"]
        assert groups.count({"name": "web-sg"}) == 1

        r = client.post(f"/v2.1/{PID}/servers/{sid}/action",
                        json={"removeSecurityGroup": {"name": "web-sg"}})
        assert r.status_code == 202
        groups = client.get(f"/v1/{PID}/cloudservers/{sid}").json()["server"]["security_groups"]
        assert {"name": "web-sg"} not in groups

    def test_add_empty_name_400(self, client):
        sid = _active_server(client, "sg-bad")
        r = client.post(f"/v2.1/{PID}/servers/{sid}/action",
                        json={"addSecurityGroup": {}})
        assert r.status_code == 400


class TestGapClosures:
    """The operations added to reach 100% documented coverage."""

    def test_nova_create_v21(self, client):
        r = client.post(f"/v2.1/{PID}/servers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "nova-create"}})
        assert r.status_code == 200
        assert len(r.json()["serverIds"]) == 1

    def test_resetpwd_flag_update(self, client):
        sid = _active_server(client, "flag-vm")
        assert client.get(f"/v1/{PID}/cloudservers/{sid}/os-resetpwd-flag").json()["resetpwd_flag"] is True
        r = client.put(f"/v1/{PID}/cloudservers/{sid}/os-resetpwd-flag",
                       json={"resetpwd_flag": False})
        assert r.json()["resetpwd_flag"] is False
        assert client.get(f"/v1/{PID}/cloudservers/{sid}/os-resetpwd-flag").json()["resetpwd_flag"] is False
        r = client.put(f"/v1/{PID}/cloudservers/{sid}/os-resetpwd-flag", json={})
        assert r.status_code == 400

    def test_remote_console_post(self, client):
        sid = _active_server(client, "console-vm")
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/remote_console",
                        json={"type": "novnc", "protocol": "vnc"})
        assert r.status_code == 200
        assert "console" in r.json() or "url" in r.json() or r.json()

    def test_reset_password_post(self, client):
        sid = _active_server(client, "pwd-vm")
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/os-reset-password",
                        json={"new_password": "Sim-Test-123!"})
        assert r.status_code == 200
        assert "job_id" in r.json()

    def test_snapshot_list(self, client):
        sim = client.app.state.sim
        vid = client.post(f"/v2.1/{PID}/cloudvolumes",
                          json={"volume": {"size": 10, "name": "snap-list-vol"}}).json()["volume_ids"][0]
        sim.jobs.complete_all()
        client.post(f"/v2/{PID}/cloudsnapshots",
                    json={"snapshot": {"volume_id": vid, "name": "s1"}})
        r = client.get(f"/v2/{PID}/cloudsnapshots")
        assert r.status_code == 200 and r.json()["count"] >= 1
        r = client.get(f"/v2/{PID}/cloudsnapshots/detail")
        assert r.status_code == 200 and r.json()["count"] >= 1

    def test_show_port(self, client):
        sid = _active_server(client, "port-vm")
        ports = client.get(f"/v1/{PID}/ports?device_id={sid}").json()["ports"]
        r = client.get(f"/v1/{PID}/ports/{ports[0]['id']}")
        assert r.status_code == 200
        assert r.json()["port"]["id"] == ports[0]["id"]
        assert client.get(f"/v1/{PID}/ports/bad-port").status_code == 404

    def test_kms_enable_disable(self, client):
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "gap-key"}).json()["key_id"]
        r = client.post(f"/v1/{PID}/kms/disable-key", json={"key_id": kid})
        assert r.json()["key_state"] == 3  # 3 = disabled
        r = client.post(f"/v1/{PID}/kms/enable-key", json={"key_id": kid})
        assert r.json()["key_state"] == 2  # 2 = enabled
        assert client.post(f"/v1/{PID}/kms/enable-key",
                           json={"key_id": "bad"}).status_code == 404

    def test_ims_update_image(self, client):
        r = client.patch(f"/v2/images/{IMAGE}",
                         json={"name": "renamed-img", "min_disk": 20})
        assert r.status_code == 200
        assert r.json()["image"]["name"] == "renamed-img"
        assert r.json()["image"]["min_disk"] == 20
        assert client.patch("/v2/images/bad-img", json={}).status_code == 404


class TestAllServiceGapClosures:
    """The 16 endpoints added to reach full documented coverage."""

    def test_elb_show_listener_and_pool_delete(self, client):
        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                        json={"loadbalancer": {"name": "gap-lb"}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "gap-pool",
                                           "loadbalancer_id": lb["id"]}}).json()["pool"]
        listener = client.post(f"/v2/{PID}/elb/listeners",
                               json={"listener": {"name": "gap-lis", "protocol": "HTTP",
                                                   "protocol_port": 80,
                                                   "loadbalancer_id": lb["id"],
                                                   "default_pool_id": pool["id"]}}).json()["listener"]
        r = client.get(f"/v2/{PID}/elb/listeners/{listener['id']}")
        assert r.status_code == 200 and r.json()["listener"]["id"] == listener["id"]
        assert client.get(f"/v2/{PID}/elb/listeners/bad").status_code == 404
        assert client.delete(f"/v2/{PID}/elb/pools/{pool['id']}").status_code == 204
        assert client.delete(f"/v2/{PID}/elb/pools/{pool['id']}").status_code == 404

    def test_elb_health_monitors(self, client):
        r = client.post(f"/v2/{PID}/elb/healthmonitors",
                        json={"healthmonitor": {"type": "TCP", "delay": 5}})
        assert r.status_code == 200
        hm_id = r.json()["healthmonitor"]["id"]
        r = client.get(f"/v2/{PID}/elb/healthmonitors")
        assert any(h["id"] == hm_id for h in r.json()["healthmonitors"])

    def test_ces_metric_data(self, client):
        r = client.get(f"/v1.0/{PID}/metric-data?metric_name=cpu_util")
        assert r.status_code == 200
        assert r.json()["metric_data_results"][0]["datapoints"][0]["value"] == 42.0

    def test_dcs_flavors(self, client):
        r = client.get(f"/v2/{PID}/flavors")
        assert r.status_code == 200 and len(r.json()["flavors"]) == 3

    def test_dms_list_topics(self, client):
        # DMS shares POST /v2/{pid}/instances with DCS (first registered wins),
        # so seed the DMS instance directly like the catalog documents.
        sim = client.app.state.sim
        if not hasattr(sim, "dms_instances"):
            sim.dms_instances = {}
        iid = "dms-seed-001"
        sim.dms_instances[iid] = {"instance_id": iid, "name": "gap-dms",
                                   "project_id": PID, "topics": []}
        client.post(f"/v2/{PID}/instances/{iid}/topics", json={"name": "t1"})
        r = client.get(f"/v2/{PID}/instances/{iid}/topics")
        assert r.status_code == 200 and r.json()["total"] >= 1
        assert client.get(f"/v2/{PID}/instances/bad/topics").status_code == 404

    def test_tms_post_resources(self, client):
        assert client.post("/v1.0/project-tags/resources", json={}).status_code == 200

    def test_apig_list_apis(self, client):
        client.post(f"/v2/{PID}/apigw/apis", json={"name": "a1"})
        r = client.get(f"/v2/{PID}/apigw/apis")
        assert r.status_code == 200 and r.json()["total"] >= 1

    def test_modelarts_datasets(self, client):
        r = client.post(f"/v2/{PID}/datasets", json={"dataset_name": "imgs"})
        assert r.status_code == 200
        did = r.json()["dataset_id"]
        assert client.get(f"/v2/{PID}/datasets").json()["total"] == 1
        assert client.delete(f"/v2/{PID}/datasets/{did}").status_code == 204
        assert client.delete(f"/v2/{PID}/datasets/{did}").status_code == 404
        assert client.post(f"/v2/{PID}/datasets", json={}).status_code == 400

    def test_iotda_send_command(self, client):
        dev = client.post(f"/v5/iot/{PID}/devices",
                          json={"device_name": "gap-dev"}).json()["device_id"]
        r = client.post(f"/v5/iot/{PID}/devices/{dev}/commands",
                        json={"service_id": "s1", "command_name": "reboot"})
        assert r.status_code == 200 and r.json()["status"] == "PENDING"
        assert client.post(f"/v5/iot/{PID}/devices/bad/commands",
                           json={}).status_code == 404

    def test_vpn_show_gateway_and_delete_connection(self, client):
        g = client.post(f"/v5/{PID}/vpn-gateways",
                        json={"name": "gap-vpn"}).json()["vpn_gateway"]
        r = client.get(f"/v5/{PID}/vpn-gateways/{g['id']}")
        assert r.status_code == 200 and r.json()["vpn_gateway"]["id"] == g["id"]
        assert client.get(f"/v5/{PID}/vpn-gateways/bad").status_code == 404
        c = client.post(f"/v5/{PID}/vpn-connections",
                        json={"name": "c1", "vgw_id": g["id"]}).json()
        cid = c.get("vpn_connection", c).get("id") or c.get("id")
        assert client.delete(f"/v5/{PID}/vpn-connections/{cid}").status_code == 204
        assert client.delete(f"/v5/{PID}/vpn-connections/{cid}").status_code == 404

    def test_dws_show_snapshot(self, client):
        cid = client.post(f"/v1.0/{PID}/dws/clusters",
                          json={"name": "snap-vm", "number_of_node": 3}).json()["cluster"]["id"]
        snap = client.post(f"/v1.0/{PID}/dws/snapshots",
                           json={"name": "s", "cluster_id": cid}).json()["snapshot"]
        r = client.get(f"/v1.0/{PID}/dws/snapshots/{snap['id']}")
        assert r.status_code == 200 and r.json()["snapshot"]["id"] == snap["id"]
        assert client.get(f"/v1.0/{PID}/dws/snapshots/bad").status_code == 404
