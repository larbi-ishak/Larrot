"""Unit tests for huawei-sim core modules."""
import hashlib
import hmac
import time
import pytest
from huawei_sim.core.signing import (
    sign_sdk_request, verify_sdk_hmac_sha256,
    sign_obs_request, verify_obs_v2,
    SignatureCheck, ALGORITHM, EMPTY_PAYLOAD_HASH,
)
from huawei_sim.core.jobs import JobEngine, Job, mark_sub_jobs_success, new_job_id
from huawei_sim.core.profiles import Profile
from huawei_sim.core.envelopes import ecs_error, evs_error, vpc_error, apigw_error
from huawei_sim.core.ratelimit import RateLimiter
from huawei_sim.core.state import SimState


# ---------------------------------------------------------------------------
# Signing tests
# ---------------------------------------------------------------------------

class TestSdkSigning:
    def test_roundtrip(self):
        """Sign a request, then verify it — must round-trip."""
        sk = "test-sk"
        headers = sign_sdk_request("GET", "/v1/pid/vpcs", "limit=2",
                                    "example.com", b"", "TESTAK", sk)
        assert "X-Sdk-Date" in headers
        assert headers["Authorization"].startswith(ALGORITHM)

        # Verify
        all_headers = [("content-type", "application/json"),
                        ("host", "example.com"),
                        ("x-sdk-date", headers["X-Sdk-Date"]),
                        ("authorization", headers["Authorization"])]
        check = verify_sdk_hmac_sha256("GET", "/v1/pid/vpcs", "limit=2",
                                         all_headers, b"", lambda ak: sk if ak == "TESTAK" else None)
        assert check.valid, f"reason: {check.reason}"
        assert check.ak == "TESTAK"

    def test_tampered_body_fails(self):
        sk = "test-sk"
        headers = sign_sdk_request("PUT", "/obj", None, "h", b'{"a":1}', "AK", sk)
        all_headers = [("content-type", "application/json"), ("host", "h"),
                        ("x-sdk-date", headers["X-Sdk-Date"]),
                        ("authorization", headers["Authorization"])]
        check = verify_sdk_hmac_sha256("PUT", "/obj", None, all_headers, b"tampered",
                                        lambda ak: sk)
        assert not check.valid

    def test_unknown_ak(self):
        headers = sign_sdk_request("GET", "/", None, "h", b"", "UNKNOWN", "sk")
        all_headers = [("content-type", "application/json"), ("host", "h"),
                        ("x-sdk-date", headers["X-Sdk-Date"]),
                        ("authorization", headers["Authorization"])]
        check = verify_sdk_hmac_sha256("GET", "/", None, all_headers, b"", lambda ak: None)
        assert not check.valid
        assert "unknown AK" in check.reason

    def test_no_auth_header(self):
        check = verify_sdk_hmac_sha256("GET", "/", None, [], b"", lambda ak: "sk")
        assert check.absent


class TestObsSigning:
    def test_roundtrip(self):
        sk = "test-sk"
        headers = sign_obs_request("GET", "bucket", "key", None, "h", b"", "", "AK", sk)
        assert headers["Authorization"].startswith("OBS AK:")

        all_headers = [("host", "h"), ("date", headers["Date"]),
                        ("authorization", headers["Authorization"])]
        check = verify_obs_v2("GET", "/bucket/key", None, all_headers, b"", lambda ak: sk)
        assert check.valid, f"reason: {check.reason}"

    def test_unsigned_list_params(self):
        """prefix/max-keys/marker are NOT part of the canonical resource."""
        sk = "test-sk"
        headers = sign_obs_request("GET", "bucket", "", "prefix=obj&max-keys=100",
                                    "h", b"", "", "AK", sk)
        all_headers = [("host", "h"), ("date", headers["Date"]),
                        ("authorization", headers["Authorization"])]
        check = verify_obs_v2("GET", "/bucket", "prefix=obj&max-keys=100",
                               all_headers, b"", lambda ak: sk)
        assert check.valid, f"reason: {check.reason}"


# ---------------------------------------------------------------------------
# Job engine tests
# ---------------------------------------------------------------------------

class TestJobEngine:
    async def test_job_success(self):
        engine = JobEngine(delay_range=(0.01, 0.02))
        job_id = await engine.submit("createServer", {"server_id": "s1"}, lambda: None)
        job = engine.get(job_id)
        assert job.status == "RUNNING"
        await asyncio.sleep(0.1)
        job = engine.get(job_id)
        assert job.status == "SUCCESS"
        assert job.end_time is not None

    async def test_job_fail(self):
        engine = JobEngine(delay_range=(0.01, 0.02))
        async def fail():
            return ("Ecs.0005", "device is illegal")
        job_id = await engine.submit("attachVolume", {}, fail)
        await asyncio.sleep(0.1)
        job = engine.get(job_id)
        assert job.status == "FAIL"
        assert job.error_code == "Ecs.0005"
        assert job.fail_reason == "device is illegal"

    async def test_sub_jobs_marked(self):
        engine = JobEngine(delay_range=(0.01, 0.02))
        entities = {"sub_jobs_total": 1, "sub_jobs": [{"status": "RUNNING", "end_time": None}]}
        job_id = await engine.submit("createServer", entities, lambda: None)
        # patch sub_jobs on success
        engine.patch(job_id, mark_sub_jobs_success)
        await asyncio.sleep(0.1)
        job = engine.get(job_id)
        assert job.entities["sub_jobs"][0]["status"] == "SUCCESS"


import asyncio

# ---------------------------------------------------------------------------
# Envelope tests
# ---------------------------------------------------------------------------

class TestEnvelopes:
    def test_ecs_nested(self):
        e = ecs_error("Ecs.0005", "device is illegal")
        assert e["error"]["code"] == "Ecs.0005"
        assert e["error"]["message"] == "device is illegal"

    def test_vpc_flat(self):
        e = vpc_error("VPC.0504", "Floating IP could not be found.")
        assert e["code"] == "VPC.0504"
        assert "error" not in e  # NOT nested

    def test_apigw_has_request_id(self):
        e = apigw_error("APIGW.0301", "throttled")
        assert e["error_code"] == "APIGW.0301"
        assert "request_id" in e


# ---------------------------------------------------------------------------
# Rate limiter tests
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_throttles(self):
        rl = RateLimiter(max_per_window=5, window_seconds=1.0, cooldown_seconds=0.1)
        for _ in range(5):
            assert rl.record("ak1")
        assert not rl.record("ak1")  # 6th request throttled

    def test_cooldown_clears(self):
        rl = RateLimiter(max_per_window=2, window_seconds=0.1, cooldown_seconds=0.1)
        rl.record("ak1"); rl.record("ak1")
        assert not rl.record("ak1")
        time.sleep(0.2)
        assert rl.record("ak1")  # cooldown expired

    def test_disabled(self):
        rl = RateLimiter(max_per_window=0)
        for _ in range(100):
            assert rl.record("ak1")


# ---------------------------------------------------------------------------
# State tests
# ---------------------------------------------------------------------------

class TestSimState:
    def test_seed(self):
        state = SimState()
        assert len(state.projects) == 2
        assert len(state.images) == 2
        assert len(state.vpcs) == 2
        assert len(state.subnets) == 2

    def test_profiles(self):
        state = SimState()
        pub = state.projects[0]
        hcs = state.projects[1]
        assert state.profile_of(pub["id"]) == Profile.PUBLIC
        assert state.profile_of(hcs["id"]) == Profile.HCS

    def test_create_volume(self):
        state = SimState()
        vid = state.create_volume("pid", "test", 10, "az1", "SAS", False)
        assert vid in state.volumes
        assert state.volumes[vid]["status"] == "creating"
        assert state.volumes[vid]["bootable"] == "false"

    def test_find_sk(self):
        state = SimState()
        assert state.find_sk(state.account["ak"]) == state.account["sk"]
        assert state.find_sk("wrong") is None
