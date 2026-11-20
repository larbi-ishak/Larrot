"""Tests for the tier-5 documented operations."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier5:
    def test_identity_providers(self, client):
        r = client.put("/v3.0/OS-FEDERATION/identity_providers",
                       json={"id": "keycloak", "description": "corp SSO"})
        assert r.status_code == 201
        assert any(p["id"] == "keycloak"
                   for p in client.get("/v3.0/OS-FEDERATION/identity_providers").json()["identity_providers"])
        r = client.get("/v3.0/OS-FEDERATION/identity_providers/keycloak")
        assert r.json()["identity_provider"]["id"] == "keycloak"
        assert client.put("/v3.0/OS-FEDERATION/identity_providers",
                          json={"id": "keycloak"}).status_code == 409
        assert client.delete("/v3.0/OS-FEDERATION/identity_providers/keycloak").status_code == 204
        assert client.get("/v3.0/OS-FEDERATION/identity_providers/keycloak").status_code == 404

    def test_token_validate_revoke(self, client):
        assert client.head("/v3/auth/tokens",
                           headers={"X-Subject-Token": "tok-1"}).status_code == 200
        assert client.head("/v3/auth/tokens").status_code == 401
        assert client.delete("/v3/auth/tokens",
                             headers={"X-Subject-Token": "tok-1"}).status_code == 204
        assert client.delete("/v3/auth/tokens").status_code == 401


class TestApigTier5:
    def test_throttles_apps_env(self, client):
        t = client.post(f"/v2/{PID}/apigw/throttles",
                        json={"name": "100-per-min", "api_call_num": 100}).json()
        ts = client.get(f"/v2/{PID}/apigw/throttles").json()
        assert ts["total"] == 1
        a = client.post(f"/v2/{PID}/apigw/apps", json={"name": "mobile-app"}).json()
        apps = client.get(f"/v2/{PID}/apigw/apps").json()
        assert apps["total"] == 1 and apps["apps"][0]["app_key"]
        env = client.post(f"/v2/{PID}/apigw/environments", json={"name": "t5-env"}).json()
        r = client.get(f"/v2/{PID}/apigw/environments/{env['id']}")
        assert r.json()["name"] == "t5-env"
        assert client.get(f"/v2/{PID}/apigw/environments/bad").status_code == 404


class TestModelArtsTier5:
    def test_import_tasks_and_version_delete(self, client):
        did = client.post(f"/v2/{PID}/datasets",
                          json={"dataset_name": "t5-ds"}).json()["dataset_id"]
        r = client.post(f"/v2/{PID}/datasets/{did}/import-tasks",
                        json={"import_path": "obs://bucket/in/"})
        tid = r.json()["task_id"]
        client.app.state.sim.jobs.complete_all()
        tasks = client.get(f"/v2/{PID}/datasets/{did}/import-tasks").json()
        assert tasks["total"] == 1 and tasks["import_tasks"][0]["status"] == "COMPLETED"

        v = client.post(f"/v2/{PID}/datasets/{did}/versions",
                        json={"version_name": "v1"}).json()["version_id"]
        assert client.delete(f"/v2/{PID}/datasets/{did}/versions/{v}").status_code == 204
        assert client.delete(f"/v2/{PID}/datasets/{did}/versions/{v}").status_code == 404


class TestCceTier5:
    def test_addon_show_delete(self, client):
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "t5-cce", "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        a = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/addons",
                        json={"addon_name": "metrics-server"}).json()["addon"]
        r = client.get(f"/api/v3/projects/{PID}/clusters/{cid}/addons/{a['id']}")
        assert r.json()["addon"]["id"] == a["id"]
        assert client.delete(
            f"/api/v3/projects/{PID}/clusters/{cid}/addons/{a['id']}").status_code == 204
        assert client.get(
            f"/api/v3/projects/{PID}/clusters/{cid}/addons/{a['id']}").status_code == 404


class TestVpcTier5:
    def test_create_delete_port(self, client):
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "t5-vpc", "cidr": "10.50.0.0/16"}}).json()["vpc"]
        r = client.post(f"/v1/{PID}/ports",
                        json={"port": {"network_id": vpc["id"], "name": "p1"}})
        assert r.status_code == 200
        port_id = r.json()["port"]["id"]
        assert client.delete(f"/v1/{PID}/ports/{port_id}").status_code == 204
        assert client.delete(f"/v1/{PID}/ports/{port_id}").status_code == 404
        # in-use port refuses deletion
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "t5-vm"}})
        sid = r.json()["serverIds"][0]
        used = client.get(f"/v1/{PID}/ports?device_id={sid}").json()["ports"][0]
        assert client.delete(f"/v1/{PID}/ports/{used['id']}").status_code == 409


class TestEcsRdsCesTier5:
    def test_nova_update(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "nova-upd"}})
        sid = r.json()["serverIds"][0]
        r = client.put(f"/v2.1/{PID}/servers/{sid}",
                       json={"server": {"name": "nova-renamed"}})
        assert r.json()["server"]["name"] == "nova-renamed"
        assert client.put(f"/v2.1/{PID}/servers/bad",
                          json={"server": {"name": "x"}}).status_code == 404

    def test_apply_parameter_template(self, client):
        cfg = client.post(f"/v3/{PID}/configurations",
                          json={"name": "t5-cfg"}).json()["configuration"]
        r = client.post(f"/v3/{PID}/configurations/{cfg['id']}/apply",
                        json={"instance_ids": []})
        assert r.status_code == 200 and r.json()["success"] is True
        assert client.post(f"/v3/{PID}/configurations/bad/apply",
                           json={}).status_code == 404

    def test_update_alarm(self, client):
        aid = client.post(f"/v1/{PID}/alarms",
                          json={"alarm_name": "t5-alarm"}).json()["alarm_id"]
        r = client.put(f"/v1/{PID}/alarms/{aid}",
                       json={"alarm_name": "renamed-alarm", "alarm_enabled": False})
        assert r.json()["alarm_name"] == "renamed-alarm"
        assert client.put(f"/v1/{PID}/alarms/bad", json={}).status_code == 404


class TestObsTier5:
    def test_policy_cors_lifecycle_versions_objacl(self):
        client = TestClient(create_obs_app())
        client.put("/t5-bucket")
        client.put("/t5-bucket/a.bin", content=b"data-a")
        client.put("/t5-bucket/b.bin", content=b"data-b")

        # policy (JSON in/out)
        client.put("/t5-bucket?policy", content=b'{"Statement": []}')
        r = client.get("/t5-bucket?policy")
        assert "Statement" in r.text
        # cors
        client.put("/t5-bucket?cors", content=b"<CORSRule><AllowedMethod>GET</AllowedMethod></CORSRule>")
        r = client.get("/t5-bucket?cors")
        assert "CORSConfiguration" in r.text and "CORSRule" in r.text
        # lifecycle
        client.put("/t5-bucket?lifecycle", content=b"<Rule><ID>r1</ID></Rule>")
        r = client.get("/t5-bucket?lifecycle")
        assert "LifecycleConfiguration" in r.text and "r1" in r.text
        # versions listing
        r = client.get("/t5-bucket?versions")
        assert "ListVersionsResult" in r.text
        assert "<Key>a.bin</Key>" in r.text and "<VersionId>null</VersionId>" in r.text
        # object acl
        r = client.get("/t5-bucket/a.bin?acl")
        assert "AccessControlPolicy" in r.text and "FULL_CONTROL" in r.text
        assert client.get("/t5-bucket/nope.bin?acl").status_code == 404
        # unknown bucket
        assert client.get("/no-such-bucket?policy").status_code == 404
