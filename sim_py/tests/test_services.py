"""Integration tests — full app via httpx ASGI transport (no live server needed)."""
import pytest
from fastapi.testclient import TestClient
from huawei_sim.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestIAM:
    def test_list_projects(self, client):
        r = client.get("/v3/projects")
        assert r.status_code == 200
        data = r.json()
        assert len(data["projects"]) >= 2
        assert data["projects"][0]["id"]
        assert data["projects"][0]["name"] in ("ap-southeast-1", "tr-west-1")

    def test_auth_projects(self, client):
        r = client.get("/v3/auth/projects")
        assert r.status_code == 200
        assert len(r.json()["projects"]) >= 2

    def test_create_token(self, client):
        r = client.post("/v3/auth/tokens", json={
            "auth": {"identity": {"methods": ["password"],
                                   "password": {"user": {"domain": {"name": "sim-lab"},
                                                          "name": "simuser", "password": "x"}}},
                      "scope": {"project": {"name": "ap-southeast-1"}}}
        })
        assert r.status_code == 201
        assert "X-Subject-Token" in r.headers
        assert "token" in r.json()
        assert "catalog" in r.json()["token"]


class TestGateway:
    def test_unknown_path_apigw_404(self, client):
        r = client.get("/no/such/api")
        assert r.status_code == 404
        assert r.json()["error_code"] == "APIGW.0101"

    def test_ecs_error_envelope(self, client):
        r = client.get("/v1/fakepid/jobs/nonexistent")
        assert r.status_code == 404
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "Common.0011"

    def test_vpc_error_envelope_flat(self, client):
        r = client.get("/v1/fakepid/publicips/none")
        assert r.status_code == 404
        body = r.json()
        assert body["code"] == "VPC.0504"
        assert "error" not in body


class TestECS:
    PID = "79814d675f6142d9b4a8ee417b924444"
    IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
    FLAVOR = "s6.large.2"

    def test_create_and_lifecycle(self, client):
        # create
        r = client.post(f"/v1.1/{self.PID}/cloudservers", json={
            "server": {"imageRef": self.IMAGE, "flavorRef": self.FLAVOR, "name": "test-vm"}
        })
        assert r.status_code == 200
        data = r.json()
        assert data["job_id"]
        assert len(data["serverIds"]) == 1
        sid = data["serverIds"][0]

        # show (BUILD initially)
        r = client.get(f"/v1/{self.PID}/cloudservers/{sid}")
        assert r.status_code == 200
        assert r.json()["server"]["id"] == sid

        # list
        r = client.get(f"/v1/{self.PID}/cloudservers/detail?limit=10")
        assert r.status_code == 200
        assert r.json()["count"] >= 1

        # delete
        r = client.post(f"/v1/{self.PID}/cloudservers/delete",
                        json={"servers": [{"id": sid}], "delete_volume": True})
        assert r.status_code == 200
        assert r.json()["job_id"]

    def test_dry_run(self, client):
        r = client.post(f"/v1.1/{self.PID}/cloudservers", json={
            "server": {"imageRef": self.IMAGE, "flavorRef": self.FLAVOR, "name": "x"},
            "dry_run": True
        })
        assert r.status_code == 202

    def test_hcs_flavors_404(self, client):
        hcs_pid = "93c9dfbe6c9e45409fac947d042e6676"
        r = client.get(f"/v1/{hcs_pid}/cloudservers/flavors")
        assert r.status_code == 404
        assert r.json()["error_code"] == "APIGW.0101"


class TestEVS:
    PID = "79814d675f6142d9b4a8ee417b924444"

    def test_volume_lifecycle(self, client):
        r = client.post(f"/v2.1/{self.PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "test-vol"}})
        assert r.status_code == 202
        data = r.json()
        assert data["job_id"]
        assert len(data["volume_ids"]) == 1

    def test_sparse_list(self, client):
        r = client.get(f"/v2/{self.PID}/cloudvolumes")
        assert r.status_code == 200
        vols = r.json()["volumes"]
        if vols:
            assert set(vols[0].keys()) == {"id", "links", "name"}


class TestVPC:
    PID = "79814d675f6142d9b4a8ee417b924444"

    def test_vpcs(self, client):
        r = client.get(f"/v1/{self.PID}/vpcs")
        assert r.status_code == 200
        assert len(r.json()["vpcs"]) >= 1

    def test_subnets(self, client):
        r = client.get(f"/v1/{self.PID}/subnets")
        assert r.status_code == 200
        assert len(r.json()["subnets"]) >= 1


class TestCBR:
    PID = "79814d675f6142d9b4a8ee417b924444"

    def test_vault_crud(self, client):
        r = client.post(f"/v3/{self.PID}/vaults",
                        json={"vault": {"name": "test-vault", "resources": []}})
        assert r.status_code == 200
        vid = r.json()["vault"]["id"]

        r = client.get(f"/v3/{self.PID}/vaults")
        assert r.status_code == 200
        assert r.json()["count"] >= 1

        r = client.delete(f"/v3/{self.PID}/vaults/{vid}")
        assert r.status_code == 204


class TestRDS:
    PID = "79814d675f6142d9b4a8ee417b924444"

    def test_flavors(self, client):
        r = client.get(f"/v3/{self.PID}/flavors")
        assert r.status_code == 200
        assert len(r.json()["flavors"]) >= 4
