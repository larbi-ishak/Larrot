"""Intensive tests for the admin platform: reset, journal, seed, state
forcing, near-miss diagnostics, and response identity headers."""

import pytest
from fastapi.testclient import TestClient

from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture()
def client():
    return TestClient(create_app())


def _make_server(c, name="test-vm"):
    r = c.post(f"/v1/{PID}/cloudservers", json={"server": {
        "name": name, "flavorRef": "s6.large.2",
        "imageRef": "1ce5800a-e487-4c1b-b264-3353a39e2b4b",
        "root_volume": {"volumetype": "SATA", "size": 40},
        "nics": [{"subnet_id": "70f2e74b-e660-410a-b754-0ca46744348a"}]}})
    assert r.status_code == 200
    # async create: finish the job, then find the server by name
    c.app.state.sim.jobs.complete_all()
    for s in c.get(f"/v1/{PID}/cloudservers/detail").json()["servers"]:
        if s["name"] == name:
            return {"server": s}
    raise AssertionError(f"server {name} not found after create")


class TestReset:
    def test_reset_wipes_everything(self, client):
        _make_server(client)
        client.post(f"/v1/{PID}/vpcs", json={"vpc": {"name": "r", "cidr": "10.0.0.0/16"}})
        assert client.get(f"/v1/{PID}/cloudservers/detail").json()["count"] == 1

        r = client.post("/admin/reset")
        assert r.status_code == 200
        assert r.json()["reset"] is True

        assert client.get(f"/v1/{PID}/cloudservers/detail").json()["count"] == 0
        names = [v["name"] for v in client.get(f"/v1/{PID}/vpcs").json()["vpcs"]]
        assert "r" not in names

    def test_reset_clears_seed(self, client):
        client.post("/admin/seed?a=42")
        assert client.get("/admin/seed").json()["seed"] == 42
        client.post("/admin/reset")
        assert client.get("/admin/seed").json()["seed"] is None

    def test_reset_clears_journal(self, client):
        client.get(f"/v1/{PID}/vpcs")
        assert client.get("/admin/requests").json()["total"] > 0
        client.post("/admin/reset")
        assert client.get("/admin/requests").json()["total"] == 0

    def test_reset_clears_chaos(self, client):
        client.post("/admin/chaos", json={"service": "ecs", "mode": "api",
                                         "failure_rate": 1.0, "status": 500,
                                         "error_code": "X", "error_msg": "y"})
        assert len(client.get("/admin/chaos").json()["rules"]) == 1
        client.post("/admin/reset")
        assert client.get("/admin/chaos").json()["rules"] == []

    def test_server_keeps_working_after_reset(self, client):
        client.post("/admin/reset")
        r = _make_server(client, name="post-reset-vm")
        assert r.get("server", {}).get("id") or r.get("job_id")


class TestRequestJournal:
    def test_records_every_request(self, client):
        client.post("/admin/reset")
        client.get(f"/v1/{PID}/vpcs")
        client.get(f"/v1/{PID}/subnets")
        r = client.get("/admin/requests")
        assert r.json()["total"] >= 2
        entries = r.json()["entries"]
        # newest first: the subnets call is the most recent service call
        assert entries[0]["path"].endswith("/subnets")

    def test_query_filters(self, client):
        client.post("/admin/reset")
        client.get(f"/v1/{PID}/vpcs")
        client.get(f"/v1/{PID}/subnets")
        client.get("/v1/{PID}/nonexistent-path-xyz")

        r = client.get("/admin/requests?method=GET&path=/vpcs")
        assert all("/vpcs" in e["path"] for e in r.json()["entries"])
        assert all(e["method"] == "GET" for e in r.json()["entries"])

        r = client.get("/admin/requests?status=404")
        assert all(e["status"] == 404 for e in r.json()["entries"])
        assert len(r.json()["entries"]) >= 1

        r = client.get("/admin/requests?matched=false")
        assert all(e["matched"] is False for e in r.json()["entries"])

        r = client.get("/admin/requests?limit=1")
        assert len(r.json()["entries"]) == 1

    def test_duration_and_request_id_recorded(self, client):
        client.get(f"/v1/{PID}/vpcs")
        e = client.get("/admin/requests?limit=1").json()["entries"][0]
        assert e["duration_ms"] >= 0
        assert len(e["request_id"]) == 32

    def test_clear(self, client):
        client.get(f"/v1/{PID}/vpcs")
        r = client.delete("/admin/requests")
        assert r.json()["cleared"] >= 1
        assert client.get("/admin/requests").json()["total"] == 0

    def test_ring_buffer_bounded(self, client):
        client.post("/admin/reset")
        for _ in range(50):
            client.get(f"/v1/{PID}/vpcs")
        r = client.get("/admin/requests?limit=1000")
        assert len(r.json()["entries"]) <= 1000
        assert r.json()["total"] >= 50

    def test_journal_not_persisted(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("SIM_PERSIST_DIR", str(tmp_path))
        client.get(f"/v1/{PID}/vpcs")
        client.post("/admin/save")
        client.post("/admin/reset")
        client.post("/admin/load")
        # resources come back, the journal does not: no pre-save entries
        r = client.get(f"/admin/requests?path=/vpcs")
        assert r.json()["entries"] == []


class TestSeed:
    def test_deterministic_ids(self, client):
        client.post("/admin/reset")
        client.post("/admin/seed?a=42")
        v1 = client.post(f"/v1/{PID}/vpcs",
                         json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()

        client.post("/admin/reset")
        client.post("/admin/seed?a=42")
        v2 = client.post(f"/v1/{PID}/vpcs",
                         json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()
        assert v1["vpc"]["id"] == v2["vpc"]["id"]

    def test_different_seed_different_ids(self, client):
        client.post("/admin/reset")
        client.post("/admin/seed?a=1")
        a = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()
        client.post("/admin/reset")
        client.post("/admin/seed?a=2")
        b = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()
        assert a["vpc"]["id"] != b["vpc"]["id"]

    def test_unseeded_ids_random(self, client):
        client.post("/admin/reset")
        a = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()
        b = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "s", "cidr": "10.0.0.0/16"}}).json()
        assert a["vpc"]["id"] != b["vpc"]["id"]

    def test_seed_show_and_validation(self, client):
        assert client.get("/admin/seed").json()["seed"] is None
        r = client.post("/admin/seed?a=7")
        assert r.json() == {"seeded": 7}
        assert client.get("/admin/seed").json()["seed"] == 7
        assert client.post("/admin/seed").status_code == 400
        assert client.post("/admin/seed", json={"a": 9}).json() == {"seeded": 9}

    def test_seeded_job_ids(self, client):
        from larrot.core.jobs import new_job_id
        client.post("/admin/seed?a=5")
        first = new_job_id()
        client.post("/admin/reset")
        client.post("/admin/seed?a=5")
        assert new_job_id() == first


class TestStateForcing:
    def test_force_vpc_status(self, client):
        client.post("/admin/reset")
        vid = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "f", "cidr": "10.0.0.0/16"}}).json()["vpc"]["id"]
        r = client.put(f"/admin/state/{vid}", json={"status": "PENDING"})
        assert r.status_code == 200
        assert r.json()["status"] == "PENDING"
        # visible through the real API
        assert client.get(f"/v1/{PID}/vpcs/{vid}").json()["vpc"]["status"] == "PENDING"

    def test_force_arbitrary_fields(self, client):
        client.post("/admin/reset")
        vid = client.post(f"/v1/{PID}/vpcs",
                          json={"vpc": {"name": "f", "cidr": "10.0.0.0/16"}}).json()["vpc"]["id"]
        r = client.put(f"/admin/state/{vid}",
                       json={"set": {"description": "forced by test"}})
        assert r.json()["raw"]["description"] == "forced by test"

    def test_force_unknown_resource_404(self, client):
        r = client.put("/admin/state/does-not-exist", json={"status": "X"})
        assert r.status_code == 404

    def test_force_ecs_status(self, client):
        client.post("/admin/reset")
        sid = _make_server(client)["server"]["id"]
        r = client.put(f"/admin/state/{sid}", json={"status": "ERROR"})
        assert r.json()["type"] == "ecs.server"
        assert r.json()["status"] == "ERROR"


class TestNearMiss:
    def test_typo_gets_suggestions(self, client):
        r = client.get(f"/v1/{PID}/cloudserver/detail")  # missing 's'
        assert r.status_code == 404
        assert r.json()["error_code"] == "APIGW.0101"
        hints = r.json()["near_matches"]
        assert len(hints) == 3
        assert hints[0]["path"] == "/v1/{pid}/cloudservers/detail"
        assert hints[0]["method"] == "GET"
        # ordered best-first
        assert hints[0]["distance"] <= hints[1]["distance"] <= hints[2]["distance"]

    def test_method_matters(self, client):
        # POST to a near-miss of a POST route should suggest that route
        r = client.post(f"/v1/{PID}/cloudserver")  # singular; POST /cloudservers exists
        hints = r.json()["near_matches"]
        assert any(h["method"] == "POST" and h["path"] == f"/v1/{{pid}}/cloudservers"
                   for h in hints)

    def test_wrong_method_on_real_route_is_405(self, client):
        # POST to a GET-only path is a 405 with an Allow header (correct
        # HTTP behavior - the route exists, the method does not)
        r = client.post(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 405
        assert "GET" in r.headers.get("allow", "")

    def test_ui_routes_never_suggested(self, client):
        r = client.get("/v1/some-typo/xyz")
        for h in r.json()["near_matches"]:
            assert not h["path"].startswith(("/admin", "/docs", "/console"))
            assert h["path"] != "/"

    def test_journal_captures_near_misses(self, client):
        client.get(f"/v1/{PID}/cloudserver/detail")
        r = client.get("/admin/requests?matched=false&limit=1")
        entry = r.json()["entries"][0]
        assert entry["near_misses"], "near-miss hints not journaled"
        assert entry["near_misses"][0]["path"] == "/v1/{pid}/cloudservers/detail"


class TestResponseHeaders:
    def test_x_larrot_header_everywhere(self, client):
        for path in (f"/v1/{PID}/vpcs", "/health", "/"):
            r = client.get(path)
            assert "x-larrot" in r.headers, f"x-larrot missing on {path}"

    def test_request_id_generated_when_absent(self, client):
        r = client.get(f"/v1/{PID}/vpcs")
        assert len(r.headers.get("X-Request-Id", "")) == 32

    def test_request_id_preserved_when_provided(self, client):
        r = client.get(f"/v1/{PID}/vpcs", headers={"X-Request-Id": "MY-CUSTOM-RID"})
        assert r.headers["X-Request-Id"] == "MY-CUSTOM-RID"
