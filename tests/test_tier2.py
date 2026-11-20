"""Tests for the tier-2 documented operations (the deeper coverage increment)."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier2:
    def test_user_lifecycle(self, client):
        u = client.post("/v3/users", json={"name": "alice"}).json()["user"]
        assert client.get("/v3/users").json()["users"][0]["name"] == "alice"
        assert client.get(f"/v3/users/{u['id']}").json()["user"]["id"] == u["id"]
        r = client.put(f"/v3/users/{u['id']}", json={"email": "a@x.com"})
        assert r.json()["user"]["email"] == "a@x.com"
        assert client.delete(f"/v3/users/{u['id']}").status_code == 204
        assert client.get(f"/v3/users/{u['id']}").status_code == 404
        assert client.post("/v3/users", json={}).status_code == 400

    def test_groups_and_roles(self, client):
        g = client.post("/v3/groups", json={"name": "devs"}).json()["group"]
        assert any(x["name"] == "devs" for x in client.get("/v3/groups").json()["groups"])
        roles = client.get("/v3/roles").json()["roles"]
        assert len(roles) == 2


class TestEcsTier2:
    def test_get_server_password(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "pwd-vm"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/os-server-password")
        assert r.status_code == 200 and "password" in r.json()


class TestVpcTier2:
    def test_sg_update_and_rule_show_delete(self, client):
        sg = client.post(f"/v1/{PID}/security-groups",
                        json={"security_group": {"name": "upd-sg"}}).json()["security_group"]
        r = client.put(f"/v1/{PID}/security-groups/{sg['id']}",
                       json={"security_group": {"name": "renamed-sg"}})
        assert r.json()["security_group"]["name"] == "renamed-sg"

        rule = client.post(f"/v1/{PID}/security-group-rules",
                           json={"security_group_rule": {"security_group_id": sg["id"],
                                                          "direction": "ingress",
                                                          "protocol": "TCP",
                                                          "port_range_min": 8080,
                                                          "port_range_max": 8080,
                                                          "remote_ip_prefix": "10.0.0.0/8"}}).json()["security_group_rule"]
        r = client.get(f"/v1/{PID}/security-group-rules/{rule['id']}")
        assert r.status_code == 200 and r.json()["security_group_rule"]["id"] == rule["id"]
        assert client.delete(f"/v1/{PID}/security-group-rules/{rule['id']}").status_code == 204
        assert client.get(f"/v1/{PID}/security-group-rules/{rule['id']}").status_code == 404

    def test_update_port(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "port-upd"}})
        sid = r.json()["serverIds"][0]
        port = client.get(f"/v1/{PID}/ports?device_id={sid}").json()["ports"][0]
        r = client.put(f"/v1/{PID}/ports/{port['id']}", json={"port": {"name": "renamed"}})
        assert r.status_code == 200
        assert client.put(f"/v1/{PID}/ports/bad", json={"port": {}}).status_code == 404


class TestDnsTier2:
    def test_recordset_show_update(self, client):
        zone = client.post("/v2/zones", json={"name": "tier2.example.com.", "email": "a@x.com"}).json()["zone"]
        rs = client.post(f"/v2/zones/{zone['id']}/recordsets",
                         json={"name": "a.tier2.example.com.", "type": "A",
                               "records": ["1.2.3.4"]}).json()["recordset"]
        r = client.get(f"/v2/zones/{zone['id']}/recordsets/{rs['id']}")
        assert r.status_code == 200 and r.json()["recordset"]["id"] == rs["id"]
        r = client.put(f"/v2/zones/{zone['id']}/recordsets/{rs['id']}",
                       json={"records": ["5.6.7.8"], "ttl": 600})
        assert r.json()["recordset"]["records"] == ["5.6.7.8"]
        assert r.json()["recordset"]["ttl"] == 600
        assert client.get(f"/v2/zones/{zone['id']}/recordsets/bad").status_code == 404


class TestKmsTier2:
    def test_gen_random_and_publickey(self, client):
        r = client.post(f"/v1/{PID}/kms/gen-random", json={"random_data_length": 32})
        assert r.status_code == 200 and len(r.json()["random_data"]) > 0
        assert client.post(f"/v1/{PID}/kms/gen-random",
                           json={"random_data_length": 5}).status_code == 400
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "pk-key"}).json()["key_id"]
        r = client.get(f"/v1/{PID}/kms/get-publickey/{kid}")
        assert r.status_code == 200 and "PUBLIC KEY" in r.json()["public_key"]
        assert client.get(f"/v1/{PID}/kms/get-publickey/bad").status_code == 404


class TestCbrTier2:
    def test_update_policy(self, client):
        p = client.post(f"/v3/{PID}/policies", json={"policy": {"name": "pol-1"}}).json()["policy"]
        r = client.put(f"/v3/{PID}/policies/{p['id']}", json={"name": "pol-2", "enabled": True})
        assert r.json()["policy"]["name"] == "pol-2"
        assert client.put(f"/v3/{PID}/policies/bad", json={}).status_code == 404


class TestElbTier2:
    def test_show_member(self, client):
        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                        json={"loadbalancer": {"name": "m-lb"}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "m-pool", "loadbalancer_id": lb["id"]}}).json()["pool"]
        m = client.post(f"/v2/{PID}/elb/pools/{pool['id']}/members",
                        json={"member": {"address": "10.0.0.5", "protocol_port": 80}}).json()["member"]
        r = client.get(f"/v2/{PID}/elb/pools/{pool['id']}/members/{m['id']}")
        assert r.status_code == 200 and r.json()["member"]["id"] == m["id"]
        assert client.get(f"/v2/{PID}/elb/pools/{pool['id']}/members/bad").status_code == 404


class TestCceTier2:
    def test_node_pools(self, client):
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "np-cluster", "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        r = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools",
                        json={"nodepool_name": "pool-1", "initialNodeCount": 2})
        assert r.status_code == 200
        np_id = r.json()["nodepool"]["id"]
        client.app.state.sim.jobs.complete_all()
        pools = client.get(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools").json()
        assert pools["count"] == 1
        assert pools["nodepools"][0]["status"]["phase"] == "Active"
        assert client.post(f"/api/v3/projects/{PID}/clusters/bad/nodepools",
                           json={}).status_code == 404


class TestSmnTier2:
    def test_message_templates(self, client):
        r = client.post(f"/v2/{PID}/notifications/message_templates",
                        json={"message_template_name": "alert-tpl", "protocol": "email"})
        assert r.status_code == 200
        tpls = client.get(f"/v2/{PID}/notifications/message_templates").json()
        assert tpls["count"] == 1
        assert client.post(f"/v2/{PID}/notifications/message_templates",
                           json={}).status_code == 400


class TestApigTier2:
    def test_environments(self, client):
        r = client.post(f"/v2/{PID}/apigw/environments", json={"name": "prod"})
        assert r.status_code == 200
        envs = client.get(f"/v2/{PID}/apigw/environments").json()
        assert envs["total"] == 1 and envs["environments"][0]["name"] == "prod"
        assert client.post(f"/v2/{PID}/apigw/environments", json={}).status_code == 400


class TestSwrTier2:
    def test_repos_stateful_and_tags(self, client):
        client.post(f"/v2/{PID}/namespaces", json={"namespace": "team-a"})
        client.post(f"/v2/{PID}/namespaces/team-a/repos", json={"repository": "api"})
        repos = client.get(f"/v2/{PID}/namespaces/team-a/repos").json()
        assert repos["total"] == 1 and repos["repos"][0]["repository"] == "api"
        tags = client.get(f"/v2/{PID}/namespaces/team-a/repos/api/tags").json()
        assert tags["total"] >= 1 and tags["tags"][0]["Tag"] == "latest"
        assert client.get(f"/v2/{PID}/namespaces/team-a/repos/nope/tags").status_code == 404


class TestIotdaTier2:
    def test_show_device(self, client):
        dev = client.post(f"/v5/iot/{PID}/devices",
                          json={"device_name": "show-dev"}).json()["device_id"]
        r = client.get(f"/v5/iot/{PID}/devices/{dev}")
        assert r.status_code == 200 and r.json()["device_id"] == dev
        assert client.get(f"/v5/iot/{PID}/devices/bad").status_code == 404


class TestModelArtsTier2:
    def test_dataset_versions(self, client):
        did = client.post(f"/v2/{PID}/datasets",
                          json={"dataset_name": "imgs"}).json()["dataset_id"]
        r = client.post(f"/v2/{PID}/datasets/{did}/versions", json={"version_name": "v1"})
        assert r.status_code == 200
        client.app.state.sim.jobs.complete_all()
        vs = client.get(f"/v2/{PID}/datasets/{did}/versions").json()
        assert vs["total"] == 1 and vs["versions"][0]["status"] == "ACTIVE"
        assert client.post(f"/v2/{PID}/datasets/bad/versions",
                           json={}).status_code == 404


class TestVpnTier2:
    def test_show_connection(self, client):
        g = client.post(f"/v5/{PID}/vpn-gateways",
                        json={"name": "c-gw"}).json()["vpn_gateway"]
        c = client.post(f"/v5/{PID}/vpn-connections",
                        json={"name": "c1", "vgw_id": g["id"]}).json()
        cid = c.get("vpn_connection", c).get("id") or c.get("id")
        r = client.get(f"/v5/{PID}/vpn-connections/{cid}")
        assert r.status_code == 200
        assert client.get(f"/v5/{PID}/vpn-connections/bad").status_code == 404


class TestErTier2:
    def test_show_route_table(self, client):
        eid = client.post(f"/v3/{PID}/enterprise-router/instances",
                          json={"name": "rt-er"}).json()["instance"]["id"]
        t = client.post(f"/v3/{PID}/enterprise-router/instances/{eid}/route-tables",
                        json={"name": "rt-1"}).json()["route_table"]
        r = client.get(f"/v3/{PID}/enterprise-router/instances/{eid}/route-tables/{t['id']}")
        assert r.status_code == 200 and r.json()["route_table"]["id"] == t["id"]
        assert client.get(f"/v3/{PID}/enterprise-router/instances/{eid}/route-tables/bad").status_code == 404


class TestObsTier2:
    def test_versioning_acl_tagging(self):
        client = TestClient(create_obs_app())
        client.put("/tier2-bucket")
        # versioning: disabled by default -> enable -> read back
        r = client.get("/tier2-bucket?versioning")
        assert "Disabled" in r.text
        client.put("/tier2-bucket?versioning", content=b"<VersioningConfiguration><Status>Enabled</Status></VersioningConfiguration>")
        r = client.get("/tier2-bucket?versioning")
        assert "Enabled" in r.text
        # acl
        client.put("/tier2-bucket?acl", content=b"<AccessControlPolicy/>")
        r = client.get("/tier2-bucket?acl")
        assert "FULL_CONTROL" in r.text
        # tagging
        client.put("/tier2-bucket?tagging",
                   content=b"<Tagging><TagSet><Tag><Key>env</Key><Value>prod</Value></Tag></TagSet></Tagging>")
        r = client.get("/tier2-bucket?tagging")
        assert "env" in r.text and "prod" in r.text
        # unknown bucket
        assert client.get("/no-such-bucket?versioning").status_code == 404
