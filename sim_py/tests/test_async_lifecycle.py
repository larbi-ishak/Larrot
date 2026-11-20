"""Async lifecycle tests — verify job completion drives state transitions.

Uses the JobEngine test hooks (complete_now / complete_all) to simulate the
async job engine completing, as it would on a live server after 1-3s delay.
"""
import pytest
from fastapi.testclient import TestClient
from huawei_sim.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestJobLifecycle:
    """Job status transitions."""

    def test_job_running_then_success(self, client):
        """A freshly created job is RUNNING; after completion it is SUCCESS."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "job-status"}})
        job_id = r.json()["job_id"]

        # While pending, job is RUNNING
        r = client.get(f"/v1/{PID}/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "RUNNING"

        # Force completion
        assert client.app.state.sim.jobs.complete_now(job_id) is True

        r = client.get(f"/v1/{PID}/jobs/{job_id}")
        assert r.json()["status"] == "SUCCESS"
        assert r.json()["end_time"] is not None

    def test_complete_now_is_idempotent(self, client):
        """Completing an already-completed job is a no-op."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "idempotent"}})
        job_id = r.json()["job_id"]
        sim = client.app.state.sim

        assert sim.jobs.complete_now(job_id) is True
        end_time = sim.jobs.jobs[job_id].end_time
        assert sim.jobs.complete_now(job_id) is False  # already done
        assert sim.jobs.jobs[job_id].end_time == end_time  # unchanged

    def test_complete_now_unknown_job(self, client):
        """Completing a nonexistent job returns False, no crash."""
        assert client.app.state.sim.jobs.complete_now("no-such-job") is False

    def test_complete_all(self, client):
        """complete_all drains every RUNNING job."""
        for i in range(3):
            client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": f"drain-{i}"}})
        sim = client.app.state.sim
        running = [j for j in sim.jobs.jobs.values() if j.status == "RUNNING"]
        assert len(running) >= 3
        n = sim.jobs.complete_all()
        assert n >= 3
        assert all(j.status == "SUCCESS" for j in sim.jobs.jobs.values())


class TestServerLifecycle:
    """Server state machine driven by job completion."""

    def test_server_build_then_active(self, client):
        """Server goes BUILD → ACTIVE when the create job completes."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "lifecycle-vm"}})
        sid = r.json()["serverIds"][0]

        # Before job completion: BUILD
        r = client.get(f"/v1/{PID}/cloudservers/{sid}")
        assert r.json()["server"]["status"] == "BUILD"
        assert r.json()["server"]["OS-EXT-STS:vm_state"] == "building"

        # Complete the job
        client.app.state.sim.jobs.complete_all()

        # After: ACTIVE
        r = client.get(f"/v1/{PID}/cloudservers/{sid}")
        server = r.json()["server"]
        assert server["status"] == "ACTIVE"
        assert server["OS-EXT-STS:vm_state"] == "active"
        assert server["OS-EXT-STS:power_state"] == 1
        assert server["OS-EXT-STS:task_state"] is None

    def test_batch_create_subjobs_flip_to_success(self, client):
        """Creating N servers spawns N sub-jobs; all flip to SUCCESS."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "batch", "count": 3}})
        job_id = r.json()["job_id"]
        assert len(r.json()["serverIds"]) == 3

        # Sub-jobs are RUNNING before completion
        r = client.get(f"/v1/{PID}/jobs/{job_id}")
        subs = r.json()["entities"]["sub_jobs"]
        assert len(subs) == 3
        assert all(s["status"] == "RUNNING" for s in subs)

        client.app.state.sim.jobs.complete_now(job_id)

        r = client.get(f"/v1/{PID}/jobs/{job_id}")
        assert r.json()["status"] == "SUCCESS"
        subs = r.json()["entities"]["sub_jobs"]
        assert all(s["status"] == "SUCCESS" for s in subs)
        assert all(s["end_time"] is not None for s in subs)

    def test_stop_start_after_active(self, client):
        """Full lifecycle: create → ACTIVE → stop → SHUTOFF → start → ACTIVE."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "stop-start"}})
        sid = r.json()["serverIds"][0]
        sim = client.app.state.sim
        sim.jobs.complete_all()

        # Stop
        r = client.post(f"/v1/{PID}/cloudservers/action",
                        json={"os-stop": {"type": "SOFT", "servers": [{"id": sid}]}})
        assert r.status_code in (200, 202)
        sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/cloudservers/{sid}")
        assert r.json()["server"]["status"] == "SHUTOFF"

        # Start
        r = client.post(f"/v1/{PID}/cloudservers/action",
                        json={"os-start": {"servers": [{"id": sid}]}})
        assert r.status_code in (200, 202)
        sim.jobs.complete_all()
        r = client.get(f"/v1/{PID}/cloudservers/{sid}")
        assert r.json()["server"]["status"] == "ACTIVE"

    def test_delete_removes_server_after_job(self, client):
        """Server is gone once the delete job completes."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "doomed"}})
        sid = r.json()["serverIds"][0]
        client.app.state.sim.jobs.complete_all()

        r = client.post(f"/v1/{PID}/cloudservers/delete",
                        json={"servers": [{"id": sid}]})
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # Before completion the server still exists
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").status_code == 200

        client.app.state.sim.jobs.complete_now(job_id)
        assert client.get(f"/v1/{PID}/cloudservers/{sid}").status_code == 404


class TestVolumeLifecycle:
    """Volume state machine driven by job completion."""

    def test_volume_creating_then_available(self, client):
        """Volume goes creating → available when the job completes."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "vol-lifecycle"}})
        vid = r.json()["volume_ids"][0]

        r = client.get(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["status"] == "creating"

        client.app.state.sim.jobs.complete_all()

        r = client.get(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["status"] == "available"

    def test_attach_detach_full_cycle(self, client):
        """Full cycle: create vol + server → attach → in-use → detach → available."""
        sim = client.app.state.sim

        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "cycle-vm"}})
        sid = r.json()["serverIds"][0]
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "cycle-vol"}})
        vid = r.json()["volume_ids"][0]
        sim.jobs.complete_all()  # server ACTIVE, volume available

        # Attach
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/attachvolume",
                        json={"volumeAttachment": {"volumeId": vid, "device": "/dev/vdb"}})
        assert r.status_code == 200
        sim.jobs.complete_now(r.json()["job_id"])

        r = client.get(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["status"] == "in-use"

        # Detach
        r = client.delete(f"/v1/{PID}/cloudservers/{sid}/attachvolume/{vid}")
        assert r.status_code == 200
        sim.jobs.complete_now(r.json()["job_id"])

        r = client.get(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["status"] == "available"

        # Server no longer lists the volume
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/block_device")
        assert not any(d["volumeId"] == vid for d in r.json()["volumeAttachments"])

    def test_extend_updates_size(self, client):
        """os-extend grows the volume after the job completes."""
        sim = client.app.state.sim
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "grow-me"}})
        vid = r.json()["volume_ids"][0]
        sim.jobs.complete_all()

        r = client.post(f"/v2.1/{PID}/cloudvolumes/{vid}/action",
                        json={"os-extend": {"new_size": 50}})
        assert r.status_code == 202
        sim.jobs.complete_all()

        r = client.get(f"/v2/{PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["size"] == 50

    def test_snapshot_of_available_volume(self, client):
        """Snapshot succeeds once the volume is available (not creating)."""
        sim = client.app.state.sim
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "snap-source"}})
        vid = r.json()["volume_ids"][0]
        sim.jobs.complete_all()

        r = client.post(f"/v2/{PID}/cloudsnapshots",
                        json={"snapshot": {"volume_id": vid, "name": "my-snap"}})
        assert r.status_code in (200, 202)
        snap_id = (r.json().get("snapshot", {}).get("id")
                   or r.json().get("snapshot_id")
                   or r.json().get("id"))
        assert snap_id

        r = client.get(f"/v2/{PID}/cloudsnapshots/{snap_id}")
        assert r.status_code == 200
        assert r.json()["snapshot"]["volume_id"] == vid


class TestQuirkProfileLifecycle:
    """HCS profile behaviors across the full lifecycle."""

    def test_hcs_server_active_after_job(self, client):
        """HCS servers also reach ACTIVE, and stay sparse in list view."""
        sim = client.app.state.sim
        r = client.post(f"/v1.1/{HCS_PID}/cloudservers",
                        json={"server": {"imageRef": "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21",
                                          "flavorRef": "s7n.large.2", "name": "hcs-life"}})
        sid = r.json()["serverIds"][0]
        sim.jobs.complete_all()

        # Detail view: ACTIVE
        r = client.get(f"/v1/{HCS_PID}/cloudservers/{sid}")
        assert r.json()["server"]["status"] == "ACTIVE"

        # List view: still sparse (no flavor) even when ACTIVE
        r = client.get(f"/v1/{HCS_PID}/cloudservers/detail")
        matches = [s for s in r.json()["servers"] if s["id"] == sid]
        assert matches
        assert "flavor" not in matches[0]

    def test_hcs_volume_available_but_v21_list_still_empty(self, client):
        """HCS quirk persists after jobs complete: v2.1 detail always empty."""
        sim = client.app.state.sim
        r = client.post(f"/v2.1/{HCS_PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "hcs-vol"}})
        vid = r.json()["volume_ids"][0]
        sim.jobs.complete_all()

        # Show works
        r = client.get(f"/v2/{HCS_PID}/cloudvolumes/{vid}")
        assert r.json()["volume"]["status"] == "available"

        # v2.1 list is still empty (quirk), v2 list shows it
        assert client.get(f"/v2.1/{HCS_PID}/cloudvolumes/detail").json()["volumes"] == []
        r = client.get(f"/v2/{HCS_PID}/cloudvolumes")
        assert any(v["id"] == vid for v in r.json()["volumes"])
