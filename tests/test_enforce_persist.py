"""IAM enforce mode (SIM_IAM=enforce) and state persistence."""

import json
import os
import tempfile

import pytest


@pytest.fixture()
def enforce_client(monkeypatch):
    monkeypatch.setenv("SIM_IAM", "enforce")
    from fastapi.testclient import TestClient
    from larrot.app import create_app
    return TestClient(create_app())


@pytest.fixture()
def accept_client():
    from fastapi.testclient import TestClient
    from larrot.app import create_app
    return TestClient(create_app())


PID = "79814d675f6142d9b4a8ee417b924444"


def _sign(client, method, path, body=b"", host="testserver"):
    from larrot.core.signing import sign_sdk_request
    state = client.app.state.sim
    return sign_sdk_request(method, path, None, host, body,
                             state.account["ak"], state.account["sk"])


class TestEnforceMode:
    """SIM_IAM=enforce rejects unsigned/invalid requests with APIGW errors."""

    def test_unsigned_rejected(self, enforce_client):
        r = enforce_client.get(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 401
        assert r.json()["error_code"] == "APIGW.0305"

    def test_bad_signature_rejected(self, enforce_client):
        from larrot.core.signing import sign_sdk_request
        state = enforce_client.app.state.sim
        h = sign_sdk_request("GET", f"/v1/{PID}/cloudservers/detail", None,
                            "testserver", b"", state.account["ak"], "wrong" * 8)
        r = enforce_client.get(f"/v1/{PID}/cloudservers/detail", headers=h)
        assert r.status_code == 401
        assert r.json()["error_code"] == "APIGW.0301"
        assert "verify aksk signature fail" in r.json()["error_msg"]

    def test_unknown_ak_rejected(self, enforce_client):
        from larrot.core.signing import sign_sdk_request
        state = enforce_client.app.state.sim
        h = sign_sdk_request("GET", f"/v1/{PID}/cloudservers/detail", None,
                            "testserver", b"", "UNKNOWNAK", state.account["sk"])
        r = enforce_client.get(f"/v1/{PID}/cloudservers/detail", headers=h)
        assert r.status_code == 401
        assert "ak not exist" in r.json()["error_msg"]

    def test_valid_signature_accepted(self, enforce_client):
        h = _sign(enforce_client, "GET", f"/v1/{PID}/cloudservers/detail")
        r = enforce_client.get(f"/v1/{PID}/cloudservers/detail", headers=h)
        assert r.status_code == 200

    def test_signed_post_accepted(self, enforce_client):
        body = json.dumps({"server": {
            "name": "enforce-test", "flavorRef": "s6.large.2",
            "imageRef": "1ce5800a-e487-4c1b-b264-3353a39e2b4b",
            "root_volume": {"volumetype": "SATA", "size": 40},
            "nics": [{"subnet_id": "70f2e74b-e660-410a-b754-0ca46744348a"}],
        }}).encode()
        h = _sign(enforce_client, "POST", f"/v1/{PID}/cloudservers", body)
        r = enforce_client.post(f"/v1/{PID}/cloudservers", content=body,
                               headers={**h, "Content-Type": "application/json"})
        assert r.status_code == 200

    def test_exempt_paths_stay_open(self, enforce_client):
        for path in ("/", "/health", "/metrics", "/admin/resources",
                     "/console", "/docs", "/openapi.json", "/v3/auth/tokens"):
            r = enforce_client.get(path)
            assert r.status_code in (200, 405), f"{path} -> {r.status_code}"

    def test_accept_mode_still_default(self, accept_client):
        """Default mode never rejects: frictionless local development."""
        r = accept_client.get(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 200


class TestPersistence:
    """State survives save/load round-trips, including bytes and enums."""

    def test_round_trip(self):
        from larrot.core.state import SimState
        from larrot.persistence import load_state, save_state

        s = SimState()
        s.servers["abc"] = {"id": "abc", "name": "persisted", "status": "ACTIVE"}
        s.obs_objects["b/k"] = {"bucket": "b", "key": "k",
                               "data": b"\x00\x01bin", "size": 4}
        path = tempfile.mktemp(suffix=".json")
        try:
            saved = save_state(s, path)
            assert saved >= 15

            s2 = SimState()
            loaded = load_state(s2, path)
            assert loaded == saved
            assert s2.servers["abc"]["name"] == "persisted"
            assert s2.obs_objects["b/k"]["data"] == b"\x00\x01bin"
            # Profile enum restored, not left as a string
            from larrot.core.profiles import Profile
            assert s2.projects[0]["profile"] is Profile.PUBLIC
        finally:
            os.unlink(path)

    def test_versioned_format(self):
        from larrot.core.state import SimState
        from larrot.persistence import load_state, save_state

        s = SimState()
        path = tempfile.mktemp(suffix=".json")
        try:
            save_state(s, path)
            with open(path) as f:
                doc = json.load(f)
            assert doc["version"] == 1
            assert "saved_at" in doc
            assert "stores" in doc
            # engines are never persisted
            assert "jobs" not in doc["stores"]
            assert "limiter" not in doc["stores"]
        finally:
            os.unlink(path)

    def test_load_missing_file_is_noop(self):
        from larrot.core.state import SimState
        from larrot.persistence import load_state
        s = SimState()
        assert load_state(s, "/nonexistent/state.json") == 0
        assert s.servers == {}

    def test_admin_save_load_endpoints(self, accept_client, monkeypatch):
        monkeypatch.setenv("SIM_PERSIST_DIR", tempfile.mkdtemp())
        c = accept_client
        c.post(f"/v1/{PID}/cloudservers", json={"server": {
            "name": "persist-me", "flavorRef": "s6.large.2",
            "imageRef": "1ce5800a-e487-4c1b-b264-3353a39e2b4b",
            "root_volume": {"volumetype": "SATA", "size": 40},
            "nics": [{"subnet_id": "70f2e74b-e660-410a-b754-0ca46744348a"}]}})
        r = c.post("/admin/save")
        assert r.status_code == 200
        # wipe and reload
        c.app.state.sim.servers.clear()
        assert c.get(f"/v1/{PID}/cloudservers/detail").json()["count"] == 0
        r = c.post("/admin/load")
        assert r.status_code == 200
        assert c.get(f"/v1/{PID}/cloudservers/detail").json()["count"] >= 1
