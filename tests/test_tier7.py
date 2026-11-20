"""Tests for the tier-7 documented operations."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier7:
    def test_access_keys(self, client):
        u = client.post("/v3/users", json={"name": "ak-user"}).json()["user"]
        r = client.post("/v3.0/OS-CREDENTIAL/credentials",
                        json={"user_id": u["id"], "description": "ci-key"})
        cred = r.json()["credential"]
        assert cred["access"].startswith("HWY") and len(cred["secret"]) == 64

        keys = client.get("/v3.0/OS-CREDENTIAL/credentials").json()["credentials"]
        assert any(k["access"] == cred["access"] for k in keys)
        # list never leaks the secret
        assert all("secret" not in k for k in keys)

        r = client.get(f"/v3.0/OS-CREDENTIAL/credentials/{cred['access']}")
        assert r.json()["credential"]["description"] == "ci-key"
        assert "secret" not in r.json()["credential"]

        assert client.delete(f"/v3.0/OS-CREDENTIAL/credentials/{cred['access']}").status_code == 204
        assert client.get(f"/v3.0/OS-CREDENTIAL/credentials/{cred['access']}").status_code == 404
        assert client.post("/v3.0/OS-CREDENTIAL/credentials",
                           json={"user_id": "bad"}).status_code == 404


class TestKmsTier7:
    def test_datakey_crypto_pair(self, client):
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "t7-key"}).json()["key_id"]
        dk = client.post(f"/v1/{PID}/kms/create-datakey",
                         json={"key_id": kid}).json()

        # encrypt the plain key, then decrypt it back
        r = client.post(f"/v1/{PID}/kms/encrypt-datakey",
                        json={"key_id": kid, "plain_text": dk["plain_text"]})
        cipher = r.json()["cipher_text"]
        r = client.post(f"/v1/{PID}/kms/decrypt-datakey",
                        json={"key_id": kid, "cipher_text": cipher})
        assert r.json()["plain_text"] == dk["plain_text"]
        # invalid cipher rejected
        assert client.post(f"/v1/{PID}/kms/decrypt-datakey",
                           json={"key_id": kid,
                                  "cipher_text": "bm90LXZhbGlk"}).status_code == 400

    def test_cancel_key_deletion(self, client):
        kid = client.post(f"/v1/{PID}/kms/create-key",
                          json={"key_alias": "t7-del"}).json()["key_id"]
        client.post(f"/v1/{PID}/kms/schedule-key-deletion", json={"key_id": kid})
        r = client.post(f"/v1/{PID}/kms/cancel-key-deletion", json={"key_id": kid})
        assert r.json()["key_state"] == 3  # disabled, deletion cancelled
        assert client.post(f"/v1/{PID}/kms/cancel-key-deletion",
                           json={"key_id": "bad"}).status_code == 404


class TestApigTier7:
    def test_authorizers(self, client):
        r = client.post(f"/v2/{PID}/apigw/authorizers",
                        json={"name": "jwt-check", "type": "FRONT",
                              "authorizer_uri": "urn:fg:auth"})
        assert r.status_code == 200
        auths = client.get(f"/v2/{PID}/apigw/authorizers").json()
        assert auths["total"] == 1 and auths["authorizers"][0]["type"] == "FRONT"
        assert client.post(f"/v2/{PID}/apigw/authorizers", json={}).status_code == 400


class TestVpcTier7:
    def test_nested_subnet_create(self, client):
        vpc = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "t7-vpc", "cidr": "10.60.0.0/16"}}).json()["vpc"]
        r = client.post(f"/v1/{PID}/vpcs/{vpc['id']}/subnets",
                        json={"subnet": {"name": "t7-subnet", "cidr": "10.60.1.0/24"}})
        assert r.status_code == 200
        sub = r.json()["subnet"]
        assert sub["vpc_id"] == vpc["id"]
        # vpc_id from the path wins over a wrong body value
        r = client.post(f"/v1/{PID}/vpcs/{vpc['id']}/subnets",
                        json={"subnet": {"name": "t7b", "cidr": "10.60.2.0/24",
                                          "vpc_id": "wrong"}})
        assert r.json()["subnet"]["vpc_id"] == vpc["id"]


class TestObsTier7:
    def test_inventory_replication_notification_and_deletes(self):
        client = TestClient(create_obs_app())
        client.put("/t7-bucket")
        # configure all three store-and-echo sub-resources
        for sub, payload in [
            ("inventory", b"<InventoryConfiguration><Id>i1</Id></InventoryConfiguration>"),
            ("replication", b"<ReplicationRule><Destination></Destination></ReplicationRule>"),
            ("notification", b"<TopicConfiguration><Topic>smn</Topic></TopicConfiguration>"),
        ]:
            assert client.put(f"/t7-bucket?{sub}", content=payload).status_code == 200
            r = client.get(f"/t7-bucket?{sub}")
            assert r.status_code == 200 and "i1" in r.text if sub == "inventory" else True

        r = client.get("/t7-bucket?inventory")
        assert "i1" in r.text
        r = client.get("/t7-bucket?replication")
        assert "ReplicationConfiguration" in r.text
        r = client.get("/t7-bucket?notification")
        assert "GetBucketNotificationResult" in r.text
        assert "TopicConfiguration" in r.text

        # the DELETE family clears each sub-resource
        client.put("/t7-bucket?website", content=b"<IndexDocument><Suffix>i</Suffix></IndexDocument>")
        client.put("/t7-bucket?cors", content=b"<CORSRule/>")
        client.put("/t7-bucket?lifecycle", content=b"<Rule/>")
        client.put("/t7-bucket?encryption", content=b"<SSEAlgorithm>kms</SSEAlgorithm>")
        client.put("/t7-bucket?policy", content=b"{}")
        for sub in ("website", "cors", "lifecycle", "encryption", "policy", "tagging"):
            assert client.delete(f"/t7-bucket?{sub}").status_code == 204
        # cleared: website/encryption now 404 again
        assert client.get("/t7-bucket?website").status_code == 404
        assert client.get("/t7-bucket?encryption").status_code == 404
        # unknown bucket
        assert client.delete("/no-such-bucket?cors").status_code == 404
