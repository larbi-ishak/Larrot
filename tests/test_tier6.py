"""Tests for the tier-6 documented operations."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier6:
    def test_mappings(self, client):
        r = client.put("/v3.0/OS-FEDERATION/mappings",
                       json={"id": "m1", "rules": [{"local": [], "remote": []}]})
        assert r.status_code == 201
        assert any(m["id"] == "m1"
                   for m in client.get("/v3.0/OS-FEDERATION/mappings").json()["mappings"])
        r = client.get("/v3.0/OS-FEDERATION/mappings/m1")
        assert r.json()["mapping"]["id"] == "m1"
        assert client.put("/v3.0/OS-FEDERATION/mappings",
                          json={"id": "m1"}).status_code == 409
        assert client.delete("/v3.0/OS-FEDERATION/mappings/m1").status_code == 204
        assert client.get("/v3.0/OS-FEDERATION/mappings/m1").status_code == 404

    def test_protocols(self, client):
        client.put("/v3.0/OS-FEDERATION/identity_providers",
                   json={"id": "t6-idp"})
        r = client.put("/v3.0/OS-FEDERATION/identity_providers/t6-idp/protocols/saml",
                       json={"mapping_id": "m1"})
        assert r.status_code == 201
        protos = client.get("/v3.0/OS-FEDERATION/identity_providers/t6-idp/protocols").json()
        assert protos["protocols"][0]["id"] == "saml"
        r = client.get("/v3.0/OS-FEDERATION/identity_providers/t6-idp/protocols/saml")
        assert r.json()["protocol"]["mapping_id"] == "m1"
        assert client.delete(
            "/v3.0/OS-FEDERATION/identity_providers/t6-idp/protocols/saml").status_code == 204
        assert client.get(
            "/v3.0/OS-FEDERATION/identity_providers/t6-idp/protocols/saml").status_code == 404
        # unknown provider 404s
        assert client.put("/v3.0/OS-FEDERATION/identity_providers/nope/protocols/saml",
                          json={}).status_code == 404


class TestApigTier6:
    def test_app_auths_throttle_app_flows(self, client):
        app = client.post(f"/v2/{PID}/apigw/apps", json={"name": "t6-app"}).json()
        api = client.post(f"/v2/{PID}/apigw/apis", json={"name": "t6-api"}).json()
        r = client.post(f"/v2/{PID}/apigw/app-auths",
                        json={"app_id": app["id"], "api_id": api["id"]})
        assert r.status_code == 200
        auths = client.get(f"/v2/{PID}/apigw/app-auths").json()
        assert auths["total"] == 1
        # validation: unknown app/api 404
        assert client.post(f"/v2/{PID}/apigw/app-auths",
                           json={"app_id": "bad", "api_id": api["id"]}).status_code == 404

        t = client.post(f"/v2/{PID}/apigw/throttles", json={"name": "t6-th"}).json()
        assert client.get(f"/v2/{PID}/apigw/throttles/{t['id']}").status_code == 200
        assert client.delete(f"/v2/{PID}/apigw/throttles/{t['id']}").status_code == 204
        assert client.get(f"/v2/{PID}/apigw/throttles/{t['id']}").status_code == 404

        assert client.get(f"/v2/{PID}/apigw/apps/{app['id']}").status_code == 200
        assert client.delete(f"/v2/{PID}/apigw/apps/{app['id']}").status_code == 204
        assert client.get(f"/v2/{PID}/apigw/apps/{app['id']}").status_code == 404


class TestModelArtsTier6:
    def test_export_tasks_and_update_dataset(self, client):
        did = client.post(f"/v2/{PID}/datasets",
                          json={"dataset_name": "t6-ds"}).json()["dataset_id"]
        r = client.post(f"/v2/{PID}/datasets/{did}/export-tasks",
                        json={"export_path": "obs://bucket/out/"})
        tid = r.json()["task_id"]
        client.app.state.sim.jobs.complete_all()
        tasks = client.get(f"/v2/{PID}/datasets/{did}/export-tasks").json()
        assert tasks["export_tasks"][0]["status"] == "COMPLETED"

        r = client.put(f"/v2/{PID}/datasets/{did}",
                       json={"dataset_name": "renamed-ds"})
        assert r.json()["dataset_name"] == "renamed-ds"


class TestCceTier6:
    def test_update_addon_and_nodepool(self, client):
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "t6-cce", "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        a = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/addons",
                        json={"addon_name": "dns", "version": "1.0.0"}).json()["addon"]
        r = client.put(f"/api/v3/projects/{PID}/clusters/{cid}/addons/{a['id']}",
                       json={"spec": {"version": "1.1.0"}})
        assert r.json()["addon"]["spec"]["version"] == "1.1.0"

        np_ = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools",
                          json={"nodepool_name": "t6-pool", "initialNodeCount": 1}).json()["nodepool"]
        r = client.put(f"/api/v3/projects/{PID}/clusters/{cid}/nodepools/{np_['id']}",
                       json={"spec": {"initialNodeCount": 5}})
        assert r.json()["nodepool"]["spec"]["initialNodeCount"] == 5


class TestKmsTier6:
    def test_create_datakey(self, client):
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "t6-key"}).json()["key_id"]
        r = client.post(f"/v1/{PID}/kms/create-datakey", json={"key_id": kid})
        assert r.status_code == 200
        body = r.json()
        assert body["plain_text"] != body["cipher_text"]
        # disabled key refuses datakey creation
        client.post(f"/v1/{PID}/kms/disable-key", json={"key_id": kid})
        assert client.post(f"/v1/{PID}/kms/create-datakey",
                           json={"key_id": kid}).status_code == 400
        assert client.post(f"/v1/{PID}/kms/create-datakey",
                           json={"key_id": "bad"}).status_code == 404


class TestObsTier6:
    def test_website_encryption_tagging_objacl_restore(self):
        client = TestClient(create_obs_app())
        client.put("/t6-bucket")
        client.put("/t6-bucket/archived.bin", content=b"cold-data")

        # website: 404 before set, set, read back
        assert client.get("/t6-bucket?website").status_code == 404
        client.put("/t6-bucket?website",
                   content=b"<IndexDocument><Suffix>index.html</Suffix></IndexDocument>")
        r = client.get("/t6-bucket?website")
        assert "WebsiteConfiguration" in r.text and "index.html" in r.text

        # encryption: 404 before set, set, read back
        assert client.get("/t6-bucket?encryption").status_code == 404
        client.put("/t6-bucket?encryption",
                   content=b"<ApplyServerSideEncryptionByDefault><SSEAlgorithm>kms</SSEAlgorithm></ApplyServerSideEncryptionByDefault>")
        r = client.get("/t6-bucket?encryption")
        assert "kms" in r.text

        # delete bucket tagging
        client.put("/t6-bucket?tagging",
                   content=b"<Tagging><TagSet><Tag><Key>k</Key><Value>v</Value></Tag></TagSet></Tagging>")
        assert client.delete("/t6-bucket?tagging").status_code == 204
        r = client.get("/t6-bucket?tagging")
        assert "<TagSet></TagSet>" in r.text

        # set + get object acl (custom ACL round-trips)
        assert client.put("/t6-bucket/archived.bin?acl",
                          content=b"<AccessControlPolicy><Owner><ID>me</ID></Owner></AccessControlPolicy>").status_code == 200
        r = client.get("/t6-bucket/archived.bin?acl")
        assert "me" in r.text
        assert client.put("/t6-bucket/nope.bin?acl", content=b"x").status_code == 404

        # restore object (202)
        assert client.post("/t6-bucket/archived.bin?restore").status_code == 202
        assert client.post("/t6-bucket/nope.bin?restore").status_code == 404
