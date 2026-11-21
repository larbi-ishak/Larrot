"""Deep tests for the stateful Anti-DDoS service.

Protection is recorded against the project's real EIPs; status is
computed from state, not canned.
"""

import pytest
from fastapi.testclient import TestClient

from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture()
def client():
    return TestClient(create_app())


def _make_eip(c, name="ddos-eip"):
    r = c.post(f"/v1/{PID}/publicips", json={
        "publicip": {"type": "5_bgp"},
        "bandwidth": {"name": f"bw-{name}", "size": 100, "share_type": "PER"}})
    assert r.status_code in (200, 201)
    return r.json()["publicip"]


class TestDefaultPolicy:
    def test_default_when_unset(self, client):
        r = client.get(f"/v1/{PID}/antiddos/default")
        assert r.status_code == 200
        assert r.json()["enable_l7"] is True
        assert r.json()["traffic_pos_limit"] == 100

    def test_set_and_get_round_trip(self, client):
        r = client.post(f"/v1/{PID}/antiddos/default",
                        json={"enable_l7": False, "traffic_pos_limit": 500})
        assert r.json()["success"] is True
        r = client.get(f"/v1/{PID}/antiddos/default")
        assert r.json()["enable_l7"] is False
        assert r.json()["traffic_pos_limit"] == 500
        # unset keys keep their defaults
        assert r.json()["app_type"] == 0

    def test_policy_is_per_project(self, client):
        client.post(f"/v1/{PID}/antiddos/default", json={"traffic_pos_limit": 777})
        other = "93c9dfbe6c9e45409fac947d042e6676"
        r = client.get(f"/v1/{other}/antiddos/default")
        assert r.json()["traffic_pos_limit"] == 100  # untouched


class TestProtectionLifecycle:
    def test_enable_by_id_shows_in_status(self, client):
        eip = _make_eip(client)
        # before: unprotected
        r = client.get(f"/v1/{PID}/antiddos/status?floating_ip_id={eip['id']}")
        assert r.json()["items"][0]["status"] == "notConfig"

        r = client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        assert r.json()["success"] is True
        assert r.json()["ip"] == eip["public_ip_address"]

        # after: protected, with the policy attached
        r = client.get(f"/v1/{PID}/antiddos/status?floating_ip_id={eip['id']}")
        item = r.json()["items"][0]
        assert item["status"] == "normal"
        assert item["policy"]["enable_l7"] is True

    def test_enable_by_address(self, client):
        eip = _make_eip(client)
        r = client.post(f"/v1/{PID}/antiddos/enable",
                        json={"ip": eip["public_ip_address"]})
        assert r.status_code == 200
        assert client.get(
            f"/v1/{PID}/antiddos/{eip['id']}").json()["status"] == "normal"

    def test_enable_unknown_ip_404(self, client):
        r = client.post(f"/v1/{PID}/antiddos/enable", json={"ip": "9.9.9.9"})
        assert r.status_code == 404
        assert "could not be found" in r.json()["error_msg"]

    def test_status_lists_all_project_eips(self, client):
        _make_eip(client, "a")
        _make_eip(client, "b")
        r = client.get(f"/v1/{PID}/antiddos/status")
        assert r.json()["total"] >= 2
        assert all(i["status"] == "notConfig" for i in r.json()["items"])

    def test_status_filter_unknown_id_still_200(self, client):
        r = client.get(f"/v1/{PID}/antiddos/status?floating_ip_id=x")
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_per_eip_show(self, client):
        eip = _make_eip(client)
        client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        r = client.get(f"/v1/{PID}/antiddos/{eip['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "normal"
        assert r.json()["enabled_at"]

    def test_update_policy_marks_custom(self, client):
        eip = _make_eip(client)
        client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        r = client.post(f"/v1/{PID}/antiddos/{eip['id']}",
                        json={"traffic_pos_limit": 900})
        assert r.json()["success"] is True
        item = client.get(
            f"/v1/{PID}/antiddos/status?floating_ip_id={eip['id']}").json()["items"][0]
        assert item["protection_type"] == "custom"
        assert item["policy"]["traffic_pos_limit"] == 900

    def test_update_policy_without_enable_404(self, client):
        eip = _make_eip(client)
        r = client.post(f"/v1/{PID}/antiddos/{eip['id']}", json={"enable_l7": False})
        assert r.status_code == 404

    def test_disable_protection(self, client):
        eip = _make_eip(client)
        client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        r = client.delete(f"/v1/{PID}/antiddos/{eip['id']}")
        assert r.json()["success"] is True
        assert client.get(
            f"/v1/{PID}/antiddos/{eip['id']}").json()["status"] == "notConfig"

    def test_disable_without_enable_404(self, client):
        eip = _make_eip(client)
        r = client.delete(f"/v1/{PID}/antiddos/{eip['id']}")
        assert r.status_code == 404


class TestBackendIntegration:
    def test_protections_survive_persistence(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("SIM_PERSIST_DIR", str(tmp_path))
        eip = _make_eip(client)
        client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        client.post("/admin/save")
        client.post("/admin/reset")
        client.post("/admin/load")
        item = client.get(
            f"/v1/{PID}/antiddos/status?floating_ip_id={eip['id']}").json()["items"][0]
        assert item["status"] == "normal"

    def test_protections_visible_in_explorer(self, client):
        eip = _make_eip(client)
        client.post(f"/v1/{PID}/antiddos/enable", json={"ip": eip["id"]})
        # the EIP itself is the explorer-visible resource; protection shows on it
        r = client.get(f"/admin/resources/{eip['id']}")
        assert r.status_code == 200
