"""Tests for all new services: DNS, KMS, ELB, SFS, CCE, RDS."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestDNS:
    def test_zone_lifecycle(self, client):
        r = client.post("/v2/zones", json={"name": "test.example.com.", "zone_type": "private"})
        assert r.status_code == 200
        zid = r.json()["zone"]["id"]
        assert r.json()["zone"]["name"] == "test.example.com."

        r = client.get("/v2/zones")
        assert r.status_code == 200
        assert r.json()["count"] >= 1

        r = client.get(f"/v2/zones/{zid}")
        assert r.status_code == 200

        r = client.delete(f"/v2/zones/{zid}")
        assert r.status_code == 204

    def test_recordsets(self, client):
        r = client.post("/v2/zones", json={"name": "rs.example.com."})
        zid = r.json()["zone"]["id"]

        r = client.post(f"/v2/zones/{zid}/recordsets",
                        json={"name": "www.rs.example.com.", "type": "A", "records": ["1.2.3.4"]})
        assert r.status_code == 200
        assert r.json()["recordset"]["records"] == ["1.2.3.4"]

        r = client.get(f"/v2/zones/{zid}/recordsets")
        assert r.json()["count"] >= 1

        r = client.delete(f"/v2/zones/{zid}/recordsets/{r.json()['recordsets'][0]['id']}")
        assert r.status_code == 204


class TestKMS:
    def test_key_lifecycle(self, client):
        r = client.post(f"/v1/{PID}/kms/create-key", json={"key_alias": "test-key"})
        assert r.status_code == 200
        kid = r.json()["key_id"]

        r = client.get(f"/v1/{PID}/kms/describe-key/{kid}")
        assert r.status_code == 200
        assert r.json()["key_info"]["key_alias"] == "test-key"

        r = client.post(f"/v1/{PID}/kms/list-keys", json={})
        assert r.json()["total"] >= 1

    def test_encrypt_decrypt(self, client):
        r = client.post(f"/v1/{PID}/kms/create-key", json={"key_alias": "enc-key"})
        kid = r.json()["key_id"]

        r = client.post(f"/v1/{PID}/kms/encrypt-data",
                        json={"key_id": kid, "plain_text": "hello world"})
        assert r.status_code == 200
        cipher = r.json()["cipher_text"]

        r = client.post(f"/v1/{PID}/kms/decrypt-data",
                        json={"key_id": kid, "cipher_text": cipher})
        assert r.json()["plain_text"] == "hello world"


class TestELB:
    def test_loadbalancer_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/elb/loadbalancers", json={"name": "test-lb"})
        assert r.status_code == 200
        lb_id = r.json()["loadbalancer"]["id"]

        r = client.get(f"/v2/{PID}/elb/loadbalancers")
        assert r.json()["count"] >= 1

        r = client.get(f"/v2/{PID}/elb/loadbalancers/{lb_id}")
        assert r.status_code == 200

        r = client.delete(f"/v2/{PID}/elb/loadbalancers/{lb_id}")
        assert r.status_code == 204

    def test_listener_and_pool(self, client):
        r = client.post(f"/v2/{PID}/elb/loadbalancers", json={"name": "lb2"})
        lb_id = r.json()["loadbalancer"]["id"]

        r = client.post(f"/v2/{PID}/elb/listeners",
                        json={"name": "http-listener", "protocol": "HTTP",
                              "protocol_port": 80, "loadbalancer_id": lb_id})
        assert r.status_code == 200
        lis_id = r.json()["listener"]["id"]

        r = client.post(f"/v2/{PID}/elb/pools",
                        json={"name": "backend-pool", "protocol": "HTTP",
                              "loadbalancer_id": lb_id})
        pool_id = r.json()["pool"]["id"]

        r = client.post(f"/v2/{PID}/elb/pools/{pool_id}/members",
                        json={"address": "192.168.0.10", "protocol_port": 8080})
        assert r.status_code == 200
        assert r.json()["member"]["address"] == "192.168.0.10"

        r = client.get(f"/v2/{PID}/elb/pools/{pool_id}/members")
        assert r.json()["count"] >= 1


class TestSFS:
    def test_share_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/shares", json={"name": "test-share", "size": 100})
        assert r.status_code == 200
        share_id = r.json()["share"]["id"]
        assert r.json()["share"]["status"] == "creating"

        r = client.get(f"/v2/{PID}/shares")
        assert r.json()["count"] >= 1

        r = client.get(f"/v2/{PID}/shares/{share_id}")
        assert r.status_code == 200

        r = client.post(f"/v2/{PID}/shares/{share_id}/action",
                        json={"os-extend": {"new_size": 200}})
        assert r.json()["share"]["size"] == 200

        r = client.delete(f"/v2/{PID}/shares/{share_id}")
        assert r.status_code == 204


class TestCCE:
    def test_cluster_lifecycle(self, client):
        r = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"name": "test-cluster", "flavor": "cce.s1.small"})
        assert r.status_code == 201
        cluster_id = r.json()["cluster"]["id"]
        assert r.json()["cluster"]["status"] == "Creating"

        r = client.get(f"/api/v3/projects/{PID}/clusters")
        assert r.json()["count"] >= 1

        r = client.get(f"/api/v3/projects/{PID}/clusters/{cluster_id}")
        assert r.status_code == 200

        r = client.delete(f"/api/v3/projects/{PID}/clusters/{cluster_id}")
        assert r.status_code == 204

    def test_nodes(self, client):
        r = client.post(f"/api/v3/projects/{PID}/clusters", json={"name": "node-test"})
        cluster_id = r.json()["cluster"]["id"]

        r = client.post(f"/api/v3/projects/{PID}/clusters/{cluster_id}/nodes",
                        json={"name": "worker-1", "flavor": "s6.large.2"})
        assert r.status_code == 201
        assert r.json()["node"]["status"] == "Creating"

        r = client.get(f"/api/v3/projects/{PID}/clusters/{cluster_id}/nodes")
        assert r.json()["count"] >= 1


class TestRDS:
    def test_instance_lifecycle(self, client):
        r = client.post(f"/v3/{PID}/instances",
                        json={"instance": {"name": "test-db", "datastore": {"type": "MySQL", "version": "8.0"}}})
        assert r.status_code == 200
        db_id = r.json()["instance"]["id"]

        r = client.get(f"/v3/{PID}/instances")
        assert r.json()["total_count"] >= 1

        r = client.get(f"/v3/{PID}/instances/{db_id}")
        assert r.status_code == 200

        r = client.delete(f"/v3/{PID}/instances/{db_id}")
        assert r.status_code == 200

    def test_flavors(self, client):
        r = client.get(f"/v3/{PID}/flavors")
        assert r.status_code == 200
        assert len(r.json()["flavors"]) >= 4


class TestFunctionGraph:
    def test_function_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/fg/functions",
                        json={"func_name": "hello", "runtime": "Python3.9",
                              "code": "def handler(event): return 'Hello!'"} )
        assert r.status_code == 200
        fid = r.json()["func_id"]

        r = client.get(f"/v2/{PID}/fg/functions")
        assert r.json()["count"] >= 1

        r = client.get(f"/v2/{PID}/fg/functions/{fid}")
        assert r.status_code == 200

        r = client.post(f"/v2/{PID}/fg/functions/{fid}/invocations",
                        json={"event": {"name": "world"}})
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        assert "Hello" in str(r.json()["result"].get("result", ""))

        r = client.delete(f"/v2/{PID}/fg/functions/{fid}")
        assert r.status_code == 204
