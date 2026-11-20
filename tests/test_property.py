"""Property-based tests: randomized request generation + invariants (ROADMAP 2.1).

Uses a seeded RNG (no external dependencies) so every failure is reproducible:
the seed is printed with the failure. Invariants:

  P1  A failed create leaves no partial resource
  P2  A deleted resource never appears in list results
  P3  Resource IDs are unique across bulk creation
  P4  Cross-project access always 404s
  P5  Repeated deletes follow real semantics (204 then 404)
  P6  Fuzzed inputs never crash the API (only 4xx, never 5xx)
"""
import random

import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"
SEED = 2026


@pytest.fixture
def client():
    return TestClient(create_app())


def _count(client, path, key):
    r = client.get(path)
    return len(r.json().get(key, []))


class TestP1NoPartialResources:
    def test_failed_creates_leave_nothing(self, client):
        """P1: 40 randomized invalid creates -> resource counts never move."""
        rng = random.Random(SEED)
        before = {
            "servers": _count(client, f"/v1/{PID}/cloudservers/detail", "servers"),
            "volumes": _count(client, f"/v2/{PID}/cloudvolumes", "volumes"),
            "vpcs": _count(client, f"/v1/{PID}/vpcs", "vpcs"),
        }
        bad_flavors = ["", "nope", "s6.large.2x", 42, None]
        bad_sizes = [0, -1, 9, 32769, "ten", None, 1.5]
        bad_names = [None, "", 123]

        for _ in range(40):
            op = rng.choice(["ecs", "evs", "vpc"])
            if op == "ecs":
                body = {"server": {
                    "imageRef": rng.choice([IMAGE, "bad", "", None]),
                    "flavorRef": rng.choice(bad_flavors),
                    "name": rng.choice(bad_names),
                }}
                client.post(f"/v1.1/{PID}/cloudservers", json=body)
            elif op == "evs":
                body = {"volume": {
                    "size": rng.choice(bad_sizes),
                    "name": rng.choice(bad_names),
                }}
                client.post(f"/v2.1/{PID}/cloudvolumes", json=body)
            else:
                body = {"vpc": {
                    "name": rng.choice(bad_names),
                    "cidr": rng.choice(["10.0.0.0/8", "not-a-cidr", "", None]),
                }}
                client.post(f"/v1/{PID}/vpcs", json=body)

        after = {
            "servers": _count(client, f"/v1/{PID}/cloudservers/detail", "servers"),
            "volumes": _count(client, f"/v2/{PID}/cloudvolumes", "volumes"),
            "vpcs": _count(client, f"/v1/{PID}/vpcs", "vpcs"),
        }
        assert before == after, f"P1 violated: {before} -> {after} (seed {SEED})"


class TestP2DeletedAbsent:
    def test_deleted_resources_never_listed(self, client):
        """P2: create + delete across 3 services -> gone from every list."""
        sim = client.app.state.sim

        # ECS (async delete: completes via the job engine)
        sid = client.post(f"/v1.1/{PID}/cloudservers", json={
            "server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "p2-vm"}
        }).json()["serverIds"][0]
        r = client.post(f"/v1/{PID}/cloudservers/delete",
                        json={"servers": [{"id": sid}]})
        sim.jobs.complete_now(r.json()["job_id"])
        ids = [s["id"] for s in client.get(
            f"/v1/{PID}/cloudservers/detail?limit=1000").json()["servers"]]
        assert sid not in ids

        # EVS (async delete: creation AND deletion complete via the job engine)
        vid = client.post(f"/v2.1/{PID}/cloudvolumes", json={
            "volume": {"size": 10, "name": "p2-vol"}}).json()["volume_ids"][0]
        sim.jobs.complete_all()  # volume becomes available
        r = client.delete(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.status_code == 202
        sim.jobs.complete_now(r.json()["job_id"])  # deletion completes
        vids = [v["id"] for v in client.get(f"/v2/{PID}/cloudvolumes").json()["volumes"]]
        assert vid not in vids

        # VPC (own subnet-free VPC)
        vpc_id = client.post(f"/v1/{PID}/vpcs", json={
            "vpc": {"name": "p2-vpc", "cidr": "10.77.0.0/16"}}).json()["vpc"]["id"]
        client.delete(f"/v1/{PID}/vpcs/{vpc_id}")
        vpc_ids = [v["id"] for v in client.get(f"/v1/{PID}/vpcs").json()["vpcs"]]
        assert vpc_id not in vpc_ids


class TestP3UniqueId:
    def test_bulk_ids_unique(self, client):
        """P3: 30 randomized creates -> 30 unique ids, no collisions."""
        rng = random.Random(SEED)
        ids = []
        for i in range(30):
            if rng.random() < 0.5:
                r = client.post(f"/v1.1/{PID}/cloudservers", json={
                    "server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                "name": f"p3-{i}"}})
                ids.extend(r.json().get("serverIds", []))
            else:
                r = client.post(f"/v2.1/{PID}/cloudvolumes", json={
                    "volume": {"size": rng.choice([10, 20, 50]),
                                "name": f"p3-vol-{i}"}})
                ids.extend(r.json().get("volume_ids", []))
        assert len(ids) == 30
        assert len(set(ids)) == 30, f"P3 violated (seed {SEED})"


class TestP4CrossProject:
    def test_cross_project_always_404(self, client):
        """P4: resources created in PID are invisible from HCS_PID."""
        rng = random.Random(SEED)
        sid = client.post(f"/v1.1/{PID}/cloudservers", json={
            "server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "p4-vm"}
        }).json()["serverIds"][0]
        vid = client.post(f"/v2.1/{PID}/cloudvolumes", json={
            "volume": {"size": 10, "name": "p4-vol"}}).json()["volume_ids"][0]

        for _ in range(10):
            rid = rng.choice([sid, vid])
            r = client.get(f"/v1/{HCS_PID}/cloudservers/{rid}")
            assert r.status_code == 404
            r = client.get(f"/v2/{HCS_PID}/cloudvolumes/{rid}")
            assert r.status_code == 404


class TestP5RepeatedDelete:
    def test_delete_twice_204_then_404(self, client):
        """P5: first delete 204, second delete 404 (real semantics)."""
        sim = client.app.state.sim
        vpc_id = client.post(f"/v1/{PID}/vpcs", json={
            "vpc": {"name": "p5-vpc", "cidr": "10.76.0.0/16"}}).json()["vpc"]["id"]
        assert client.delete(f"/v1/{PID}/vpcs/{vpc_id}").status_code == 204
        assert client.delete(f"/v1/{PID}/vpcs/{vpc_id}").status_code == 404

        vid = client.post(f"/v2.1/{PID}/cloudvolumes", json={
            "volume": {"size": 10, "name": "p5-vol"}}).json()["volume_ids"][0]
        sim.jobs.complete_all()  # volume must be available before delete
        # EVS delete is async: 202 + job, then gone; repeat -> 404
        assert client.delete(f"/v2/{PID}/cloudvolumes/{vid}").status_code == 202
        sim.jobs.complete_all()
        assert client.get(f"/v2/{PID}/cloudvolumes/{vid}").status_code == 404
        assert client.delete(f"/v2/{PID}/cloudvolumes/{vid}").status_code == 404


class TestP6NoCrash:
    def test_fuzz_never_500(self, client):
        """P6: 100 fuzzed requests -> only 2xx/4xx, never a 5xx crash."""
        rng = random.Random(SEED)
        endpoints = [
            ("POST", f"/v1.1/{PID}/cloudservers",
             lambda: {"server": {"imageRef": rng.choice([IMAGE, "", None, 42]),
                                  "flavorRef": rng.choice([FLAVOR, "", None]),
                                  "name": rng.choice(["x", "", None, 42]),
                                  "count": rng.choice([1, 0, -1, "3", None])}}),
            ("POST", f"/v2.1/{PID}/cloudvolumes",
             lambda: {"volume": {"size": rng.choice([10, 0, -5, "big", None]),
                                  "name": rng.choice(["v", "", None])}}),
            ("POST", f"/v1/{PID}/vpcs",
             lambda: {"vpc": {"name": rng.choice(["v", "", None]),
                              "cidr": rng.choice(["10.0.0.0/16", "banana", None])}}),
            ("POST", f"/v1/{PID}/publicips",
             lambda: {"publicip": {"type": rng.choice(["5_bgp", "bogus", None])},
                      "bandwidth": {"name": "b", "size": rng.choice([5, 0, -1, "x"]),
                                     "share_type": "PER"}}),
            ("POST", "/v3/auth/tokens",
             lambda: {"auth": rng.choice([{}, None, {"identity": None}])}),
        ]
        for i in range(100):
            method, path, gen = endpoints[i % len(endpoints)]
            r = client.request(method, path, json=gen())
            assert r.status_code < 500, (
                f"P6 violated at request {i}: {method} {path} -> "
                f"{r.status_code} (seed {SEED})")
