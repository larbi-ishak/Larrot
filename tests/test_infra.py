"""Infrastructure tests — OBS, persistence, signed requests, concurrency, admin."""
import logging
import threading

import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app
from larrot.core.signing import sign_sdk_request

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"
AK = "HWYSIMAK00000001"
SK = "HWYSIMSK00000001"


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def obs():
    return TestClient(create_obs_app())


# ---------------------------------------------------------------------------
# OBS — S3-compatible API (separate app, like the real cloud's port 8201)
# ---------------------------------------------------------------------------

class TestObsBuckets:
    def test_create_and_list_buckets(self, obs):
        assert obs.put("/bucket-a").status_code == 200
        assert obs.put("/bucket-b").status_code == 200

        r = obs.get("/")
        assert r.status_code == 200
        assert "application/xml" in r.headers["content-type"]
        assert "bucket-a" in r.text
        assert "bucket-b" in r.text
        assert "ListAllMyBucketsResult" in r.text

    def test_duplicate_bucket_409(self, obs):
        assert obs.put("/dupe").status_code == 200
        r = obs.put("/dupe")
        assert r.status_code == 409
        assert "BucketAlreadyOwnedByYou" in r.text

    def test_head_bucket(self, obs):
        obs.put("/head-bucket")
        assert obs.head("/head-bucket").status_code == 200
        assert obs.head("/never-created").status_code == 404

    def test_get_nonexistent_bucket(self, obs):
        r = obs.get("/no-such-bucket")
        assert r.status_code == 404
        assert "NoSuchBucket" in r.text
        assert "no-such-bucket" in r.text  # BucketName echoed

    def test_bucket_location(self, obs):
        obs.put("/loc-bucket")
        r = obs.get("/loc-bucket?location")
        assert r.status_code == 200
        assert "LocationConstraint" in r.text

    def test_delete_empty_bucket(self, obs):
        obs.put("/gone-bucket")
        assert obs.delete("/gone-bucket").status_code == 204
        assert obs.head("/gone-bucket").status_code == 404

    def test_delete_nonempty_bucket_409(self, obs):
        obs.put("/full-bucket")
        obs.put("/full-bucket/data.txt", content=b"hello")
        r = obs.delete("/full-bucket")
        assert r.status_code == 409
        assert "BucketNotEmpty" in r.text


class TestObsObjects:
    def test_put_get_roundtrip(self, obs):
        obs.put("/rt-bucket")
        assert obs.put("/rt-bucket/hello.txt", content=b"hello world").status_code == 200
        r = obs.get("/rt-bucket/hello.txt")
        assert r.status_code == 200
        assert r.content == b"hello world"

    def test_get_nonexistent_object_404(self, obs):
        obs.put("/obj-bucket")
        r = obs.get("/obj-bucket/nope.txt")
        assert r.status_code == 404
        assert "NoSuchKey" in r.text

    def test_delete_object(self, obs):
        obs.put("/del-bucket")
        obs.put("/del-bucket/x.txt", content=b"x")
        assert obs.delete("/del-bucket/x.txt").status_code == 204
        assert obs.get("/del-bucket/x.txt").status_code == 404

    def test_list_objects(self, obs):
        obs.put("/list-bucket")
        for name in ("a.txt", "b.txt", "c/d.txt"):
            obs.put(f"/list-bucket/{name}", content=b"data")

        r = obs.get("/list-bucket")
        assert "ListBucketResult" in r.text
        for name in ("a.txt", "b.txt", "c/d.txt"):
            assert f"<Key>{name}</Key>" in r.text

    def test_list_prefix_filter(self, obs):
        obs.put("/prefix-bucket")
        for name in ("logs/a.log", "logs/b.log", "data/c.csv"):
            obs.put(f"/prefix-bucket/{name}", content=b"d")

        r = obs.get("/prefix-bucket?prefix=logs/")
        assert "a.log" in r.text
        assert "b.log" in r.text
        assert "c.csv" not in r.text

    def test_list_delimiter_common_prefixes(self, obs):
        obs.put("/delim-bucket")
        for name in ("2024/01/a", "2024/02/b", "root.txt"):
            obs.put(f"/delim-bucket/{name}", content=b"d")

        r = obs.get("/delim-bucket?delimiter=/")
        assert "<CommonPrefixes><Prefix>2024/</Prefix></CommonPrefixes>" in r.text
        assert "root.txt" in r.text
        assert "<Key>2024/01/a</Key>" not in r.text  # rolled into the prefix

    def test_list_max_keys_truncation(self, obs):
        obs.put("/trunc-bucket")
        for i in range(5):
            obs.put(f"/trunc-bucket/f{i}.txt", content=b"d")

        r = obs.get("/trunc-bucket?max-keys=2")
        assert "<MaxKeys>2</MaxKeys>" in r.text
        assert "<IsTruncated>true</IsTruncated>" in r.text
        assert "<NextMarker>" in r.text

    def test_marker_pagination(self, obs):
        obs.put("/marker-bucket")
        for i in range(5):
            obs.put(f"/marker-bucket/f{i}.txt", content=b"d")

        page1 = obs.get("/marker-bucket?max-keys=2").text
        assert "f0.txt" in page1 and "f1.txt" in page1
        page2 = obs.get("/marker-bucket?max-keys=2&marker=f1.txt").text
        assert "f2.txt" in page2 and "f0.txt" not in page2

    def test_overwrite_object(self, obs):
        obs.put("/ow-bucket")
        obs.put("/ow-bucket/doc.txt", content=b"v1")
        obs.put("/ow-bucket/doc.txt", content=b"v2-longer")
        assert obs.get("/ow-bucket/doc.txt").content == b"v2-longer"

    def test_unicode_object_key(self, obs):
        obs.put("/uni-bucket")
        key = "文件夹/文件.txt"
        assert obs.put(f"/uni-bucket/{key}", content=b"unicode").status_code == 200
        assert obs.get(f"/uni-bucket/{key}").content == b"unicode"


# ---------------------------------------------------------------------------
# Admin / infra endpoints
# ---------------------------------------------------------------------------

class TestInfraEndpoints:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "ecs" in r.json()["services"]
        assert "obs" in r.json()["services"]

    def test_metrics_counts(self, client):
        before = client.get("/metrics").json()
        client.post(f"/v2.1/{PID}/cloudvolumes",
                    json={"volume": {"size": 10, "name": "metrics-vol"}})
        after = client.get("/metrics").json()
        assert after["volumes"] == before["volumes"] + 1
        assert after["jobs_total"] >= before["jobs_total"] + 1

    def test_dashboard_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_openapi_docs(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
        r = client.get("/openapi.json")
        assert r.status_code == 200
        assert len(r.json()["paths"]) > 50  # 50 services wired


class TestPersistence:
    def test_save_load_roundtrip(self, monkeypatch):
        monkeypatch.setenv("SIM_PERSIST_DIR", "/tmp/opencode/sim-persist-test")
        c1 = TestClient(create_app())
        r = c1.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                      "name": "persist-me"}})
        sid = r.json()["serverIds"][0]
        n_volumes = len(c1.get("/metrics").json()["volumes"] * [0]) or None

        assert c1.post("/admin/save").status_code == 200

        # Fresh app instance — state is empty until loaded
        c2 = TestClient(create_app())
        assert c2.get(f"/v1/{PID}/cloudservers/{sid}").status_code == 404

        assert c2.post("/admin/load").status_code == 200
        r = c2.get(f"/v1/{PID}/cloudservers/{sid}")
        assert r.status_code == 200
        assert r.json()["server"]["name"] == "persist-me"

    def test_load_without_save_404(self, monkeypatch):
        monkeypatch.setenv("SIM_PERSIST_DIR", "/tmp/opencode/sim-persist-empty")
        c = TestClient(create_app())
        assert c.post("/admin/load").status_code == 404


# ---------------------------------------------------------------------------
# Live signed requests through the gateway middleware
# ---------------------------------------------------------------------------

class TestSignedRequests:
    def test_valid_signature_accepted(self, client, caplog):
        path = f"/v1/{PID}/cloudservers/detail"
        headers = sign_sdk_request("GET", path, None, "testserver", b"", AK, SK)
        headers["Content-Type"] = "application/json"  # SDK always signs content-type
        with caplog.at_level(logging.INFO, logger="larrot"):
            r = client.get(path, headers=headers)
        assert r.status_code == 200
        assert any("signature OK" in rec.message for rec in caplog.records)

    def test_valid_signature_with_body(self, client, caplog):
        import json as _json
        body = _json.dumps({"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                        "name": "signed-create"}}).encode()
        path = f"/v1.1/{PID}/cloudservers"
        headers = sign_sdk_request("POST", path, None, "testserver", body, AK, SK)
        headers["Content-Type"] = "application/json"
        with caplog.at_level(logging.INFO, logger="larrot"):
            r = client.post(path, content=body, headers=headers)
        assert r.status_code == 200
        assert any("signature OK" in rec.message for rec in caplog.records)

    def test_tampered_signature_still_accepted(self, client, caplog):
        """Accept-and-check policy: bad signatures are logged, never rejected."""
        path = f"/v1/{PID}/cloudservers/detail"
        headers = sign_sdk_request("GET", path, None, "testserver", b"", AK, SK)
        headers["Authorization"] = headers["Authorization"][:-4] + "beef"
        with caplog.at_level(logging.INFO, logger="larrot"):
            r = client.get(path, headers=headers)
        assert r.status_code == 200  # accepted anyway
        assert any("SIGNATURE INVALID" in rec.message for rec in caplog.records)

    def test_unknown_ak_still_accepted(self, client, caplog):
        path = f"/v1/{PID}/cloudservers/detail"
        headers = sign_sdk_request("GET", path, None, "testserver", b"",
                                   "UNKNOWNAK", "whatever")
        with caplog.at_level(logging.INFO, logger="larrot"):
            r = client.get(path, headers=headers)
        assert r.status_code == 200
        assert any("SIGNATURE INVALID" in rec.message for rec in caplog.records)

    def test_unsigned_request_accepted(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="larrot"):
            r = client.get(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 200
        assert any("no signature" in rec.message for rec in caplog.records)

    def test_request_id_passthrough(self, client):
        rid = "ff80808288d41e1b018990260955686a"
        r = client.get(f"/v1/{PID}/cloudservers/detail", headers={"X-Request-Id": rid})
        assert r.headers.get("x-request-id") == rid


# ---------------------------------------------------------------------------
# Concurrency / ID uniqueness
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_batch_create_unique_ids(self, client):
        """Batch create of 100 servers yields 100 unique IDs."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "unique", "count": 100}})
        ids = r.json()["serverIds"]
        assert len(ids) == 100
        assert len(set(ids)) == 100  # all unique

    def test_parallel_creates_unique_ids(self, client):
        """Parallel requests from threads never collide on IDs."""
        results = []
        lock = threading.Lock()

        def create(i):
            r = client.post(f"/v1.1/{PID}/cloudservers",
                            json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                              "name": f"thread-{i}"}})
            with lock:
                results.append(r.json()["serverIds"][0])

        threads = [threading.Thread(target=create, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 16
        assert len(set(results)) == 16  # no collisions

    def test_parallel_volume_creates(self, client):
        results = []
        lock = threading.Lock()

        def create(i):
            r = client.post(f"/v2.1/{PID}/cloudvolumes",
                            json={"volume": {"size": 10, "name": f"vol-{i}"}})
            with lock:
                results.append(r.json()["volume_ids"][0])

        threads = [threading.Thread(target=create, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 12
        assert len(set(results)) == 12
