"""Tests for the tier-3 documented operations."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier3:
    def test_role_assignments(self, client):
        u = client.post("/v3/users", json={"name": "bob"}).json()["user"]
        g = client.post("/v3/groups", json={"name": "ops"}).json()["group"]
        role = client.get("/v3/roles").json()["roles"][0]["id"]

        assert client.put(f"/v3/projects/{PID}/users/{u['id']}/roles/{role}").status_code == 204
        assert client.put(f"/v3/projects/{PID}/groups/{g['id']}/roles/{role}").status_code == 204

        roles = client.get(f"/v3/projects/{PID}/users/{u['id']}/roles").json()["roles"]
        assert any(r["id"] == role for r in roles)
        roles = client.get(f"/v3/projects/{PID}/groups/{g['id']}/roles").json()["roles"]
        assert any(r["id"] == role for r in roles)

        assert client.delete(f"/v3/projects/{PID}/users/{u['id']}/roles/{role}").status_code == 204
        assert client.delete(f"/v3/projects/{PID}/users/{u['id']}/roles/{role}").status_code == 404
        assert client.get(f"/v3/projects/{PID}/users/{u['id']}/roles").json()["roles"] == []

    def test_list_domains(self, client):
        domains = client.get("/v3/domains").json()["domains"]
        assert len(domains) == 1 and domains[0]["name"] == "sim-lab"


class TestEcsTier3:
    def test_tags_overwrite_and_clear(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "t3-vm"}})
        sid = r.json()["serverIds"][0]
        client.post(f"/v1/{PID}/cloudservers/{sid}/tags/action",
                    json={"action": "create", "tags": [{"key": "a", "value": "1"}]})
        # PUT overwrites everything
        r = client.put(f"/v1/{PID}/cloudservers/{sid}/tags",
                       json={"tags": {"x": "9", "y": "8"}})
        assert r.json()["tags"] == {"x": "9", "y": "8"}
        # DELETE clears
        assert client.delete(f"/v1/{PID}/cloudservers/{sid}/tags").status_code == 204
        assert client.get(f"/v1/{PID}/cloudservers/{sid}/tags").json()["tags"] == {}


class TestBmsTier3:
    def test_update_bms(self, client):
        sid = client.post(f"/v1/{PID}/baremetalservers",
                          json={"name": "bms-t3"}).json()["server"]["id"]
        r = client.put(f"/v1/{PID}/baremetalservers/{sid}", json={"name": "renamed-bms"})
        assert r.json()["name"] == "renamed-bms"
        assert client.put(f"/v1/{PID}/baremetalservers/bad", json={"name": "x"}).status_code == 404


class TestAsTier3:
    def test_show_delete_policy(self, client):
        gid = client.post(f"/v1/{PID}/scaling_group",
                          json={"scaling_group_name": "t3-asg"}).json()["scaling_group_id"]
        pol = client.post(f"/v1/{PID}/scaling_policy",
                          json={"scaling_policy_name": "t3-pol",
                                "scaling_group_id": gid}).json()["scaling_policy_id"]
        r = client.get(f"/v1/{PID}/scaling_policy/{pol}")
        assert r.status_code == 200 and r.json()["id"] == pol
        assert client.delete(f"/v1/{PID}/scaling_policy/{pol}").status_code == 204
        assert client.get(f"/v1/{PID}/scaling_policy/{pol}").status_code == 404


class TestRdsTier3:
    def test_parameter_templates(self, client):
        r = client.post(f"/v3/{PID}/configurations",
                        json={"name": "tpl-1", "values": {"max_connections": "100"}})
        cid = r.json()["configuration"]["id"]
        assert client.get(f"/v3/{PID}/configurations").json()["total"] == 1
        r = client.get(f"/v3/{PID}/configurations/{cid}")
        assert r.json()["configuration"]["name"] == "tpl-1"
        r = client.put(f"/v3/{PID}/configurations/{cid}", json={"name": "tpl-2"})
        assert r.json()["configuration"]["name"] == "tpl-2"
        assert client.delete(f"/v3/{PID}/configurations/{cid}").status_code == 204
        assert client.delete(f"/v3/{PID}/configurations/{cid}").status_code == 404
        assert client.post(f"/v3/{PID}/configurations", json={}).status_code == 400


class TestElbTier3:
    def test_healthmonitor_and_member_lifecycle(self, client):
        lb = client.post(f"/v2/{PID}/elb/loadbalancers",
                        json={"loadbalancer": {"name": "t3-lb"}}).json()["loadbalancer"]
        pool = client.post(f"/v2/{PID}/elb/pools",
                           json={"pool": {"name": "t3-pool",
                                           "loadbalancer_id": lb["id"]}}).json()["pool"]
        hm = client.post(f"/v2/{PID}/elb/healthmonitors",
                         json={"healthmonitor": {"type": "TCP", "pool_id": pool["id"]}}).json()["healthmonitor"]
        r = client.get(f"/v2/{PID}/elb/healthmonitors/{hm['id']}")
        assert r.status_code == 200 and r.json()["healthmonitor"]["id"] == hm["id"]
        assert client.delete(f"/v2/{PID}/elb/healthmonitors/{hm['id']}").status_code == 204
        assert client.get(f"/v2/{PID}/elb/healthmonitors/{hm['id']}").status_code == 404

        m = client.post(f"/v2/{PID}/elb/pools/{pool['id']}/members",
                        json={"member": {"address": "10.1.1.1",
                                          "protocol_port": 80}}).json()["member"]
        assert client.delete(f"/v2/{PID}/elb/pools/{pool['id']}/members/{m['id']}").status_code == 204
        assert client.delete(f"/v2/{PID}/elb/pools/{pool['id']}/members/{m['id']}").status_code == 404


class TestCceTier3:
    def test_node_pool_show_delete(self, client):
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "t3-cce", "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        np_ = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools",
                          json={"nodepool_name": "t3-pool"}).json()["nodepool"]
        r = client.get(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools/{np_['id']}")
        assert r.status_code == 200 and r.json()["nodepool"]["id"] == np_["id"]
        assert client.delete(
            f"/api/v3/projects/{PID}/clusters/{cid}/nodepools/{np_['id']}").status_code == 204
        assert client.get(
            f"/api/v3/projects/{PID}/clusters/{cid}/nodepools/{np_['id']}").status_code == 404


class TestSmnTier3:
    def test_delete_template(self, client):
        tid = client.post(f"/v2/{PID}/notifications/message_templates",
                          json={"message_template_name": "del-tpl"}).json()["message_template_id"]
        assert client.delete(
            f"/v2/{PID}/notifications/message_templates/{tid}").status_code == 204
        assert client.delete(
            f"/v2/{PID}/notifications/message_templates/{tid}").status_code == 404


class TestLtsTier3:
    def test_delete_log_stream(self, client):
        gid = client.post(f"/v2/{PID}/log-groups",
                          json={"log_group_name": "t3-group"}).json()["log_group_id"]
        sid = client.post(f"/v2/{PID}/log-groups/{gid}/log-streams",
                          json={"log_stream_name": "t3-stream"}).json()["log_stream_id"]
        assert client.delete(f"/v2/{PID}/log-groups/{gid}/log-streams/{sid}").status_code == 204
        assert client.delete(f"/v2/{PID}/log-groups/{gid}/log-streams/{sid}").status_code == 404


class TestEpsTier3:
    def test_update_eps(self, client):
        eid = client.post("/v1.0/enterprise-projects",
                          json={"name": "t3-eps"}).json()["id"]
        r = client.put(f"/v1.0/enterprise-projects/{eid}",
                       json={"name": "renamed-eps", "description": "updated"})
        assert r.json()["name"] == "renamed-eps"
        assert client.put("/v1.0/enterprise-projects/bad", json={}).status_code == 404


class TestSwrTier3:
    def test_delete_repo(self, client):
        client.post(f"/v2/{PID}/namespaces", json={"namespace": "t3"})
        client.post(f"/v2/{PID}/namespaces/t3/repos", json={"repository": "svc"})
        assert client.delete(f"/v2/{PID}/namespaces/t3/repos/svc").status_code == 204
        assert client.delete(f"/v2/{PID}/namespaces/t3/repos/svc").status_code == 404


class TestIotdaTier3:
    def test_show_delete_product(self, client):
        pid_ = client.post(f"/v5/iot/{PID}/products",
                           json={"product_name": "t3-prod"}).json()["product_id"]
        r = client.get(f"/v5/iot/{PID}/products/{pid_}")
        assert r.status_code == 200 and r.json()["product_id"] == pid_
        assert client.delete(f"/v5/iot/{PID}/products/{pid_}").status_code == 204
        assert client.get(f"/v5/iot/{PID}/products/{pid_}").status_code == 404


class TestDliTier3:
    def test_databases_stateful_and_delete(self, client):
        client.post(f"/v1.0/{PID}/databases", json={"database_name": "analytics"})
        dbs = client.get(f"/v1.0/{PID}/databases").json()
        assert dbs["total"] == 1 and dbs["databases"][0]["database_name"] == "analytics"
        assert client.delete(f"/v1.0/{PID}/databases/analytics").json()["is_success"] is True
        assert client.get(f"/v1.0/{PID}/databases").json()["total"] == 0
        assert client.delete(f"/v1.0/{PID}/databases/nope").status_code == 404


class TestDwsTier3:
    def test_delete_snapshot(self, client):
        cid = client.post(f"/v1.0/{PID}/dws/clusters",
                          json={"name": "t3-dws", "number_of_node": 3}).json()["cluster"]["id"]
        snap = client.post(f"/v1.0/{PID}/dws/snapshots",
                           json={"name": "t3-snap", "cluster_id": cid}).json()["snapshot"]
        assert client.delete(f"/v1.0/{PID}/dws/snapshots/{snap['id']}").status_code == 204
        assert client.delete(f"/v1.0/{PID}/dws/snapshots/{snap['id']}").status_code == 404


class TestIefTier3:
    def test_show_deployment(self, client):
        nid = client.post(f"/v2/{PID}/edgemgr/nodes",
                          json={"name": "t3-node"}).json()["node"]["id"]
        d = client.post(f"/v2/{PID}/edgemgr/deployments",
                       json={"deployment": {"name": "t3-dep", "node_ids": [nid]}}).json()["deployment"]
        r = client.get(f"/v2/{PID}/edgemgr/deployments/{d['id']}")
        assert r.status_code == 200 and r.json()["deployment"]["id"] == d["id"]
        assert client.get(f"/v2/{PID}/edgemgr/deployments/bad").status_code == 404


class TestPeeringTier3:
    def test_update_peering(self, client):
        p = client.post(f"/v2.0/{PID}/vpc-peerings",
                        json={"name": "t3-peer"}).json()["peering"]
        r = client.put(f"/v2.0/{PID}/vpc-peerings/{p['id']}", json={"name": "renamed-peer"})
        assert r.json()["peering"]["name"] == "renamed-peer"
        assert client.put(f"/v2.0/{PID}/vpc-peerings/bad", json={"name": "x"}).status_code == 404


class TestAclTier3:
    def test_update_acl(self, client):
        a = client.post(f"/v3/{PID}/vpc/acls", json={"name": "t3-acl"}).json()["acl"]
        r = client.put(f"/v3/{PID}/vpc/acls/{a['id']}", json={"name": "renamed-acl"})
        assert r.json()["acl"]["name"] == "renamed-acl"


class TestRoutesTier3:
    def test_update_route_table(self, client):
        rt = client.post(f"/v1/{PID}/vpc/routetables",
                         json={"name": "t3-rt"}).json()["routetable"]
        r = client.put(f"/v1/{PID}/vpc/routetables/{rt['id']}", json={"name": "renamed-rt"})
        assert r.json()["routetable"]["name"] == "renamed-rt"
        assert client.put(f"/v1/{PID}/vpc/routetables/bad", json={"name": "x"}).status_code == 404


class TestDnsTier3:
    def test_list_all_recordsets(self, client):
        zone = client.post("/v2/zones",
                           json={"name": "t3.example.com.", "email": "a@x.com"}).json()["zone"]
        client.post(f"/v2/zones/{zone['id']}/recordsets",
                    json={"name": "all.t3.example.com.", "type": "A", "records": ["1.1.1.1"]})
        r = client.get("/v2/recordsets")
        assert any(rs["name"] == "all.t3.example.com."
                   for rs in r.json()["recordsets"])


class TestKmsTier3:
    def test_update_key_alias(self, client):
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "orig"}).json()["key_id"]
        r = client.post(f"/v1/{PID}/kms/update-key-alias",
                        json={"key_id": kid, "key_alias": "renamed"})
        assert r.json()["key_alias"] == "renamed"
        assert client.post(f"/v1/{PID}/kms/update-key-alias",
                           json={"key_id": kid}).status_code == 400
        assert client.post(f"/v1/{PID}/kms/update-key-alias",
                           json={"key_id": "bad", "key_alias": "x"}).status_code == 404
