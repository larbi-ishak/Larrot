"""Tests for enhanced compute services: keypairs, server groups, quotas, metadata, NICs, console, resize, OS change, batch, HPC."""
import pytest
from fastapi.testclient import TestClient
from huawei_sim.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


def _create_server(client):
    r = client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "compute-test"}})
    assert r.status_code == 200
    return r.json()["serverIds"][0]


class TestEcsKeypairs:
    def test_create_and_list(self, client):
        r = client.post(f"/v2.1/{PID}/os-keypairs",
                        json={"keypair": {"name": "test-key"}})
        assert r.status_code == 200
        assert r.json()["keypair"]["name"] == "test-key"
        assert "ssh-rsa" in r.json()["keypair"]["public_key"]

        r = client.get(f"/v2.1/{PID}/os-keypairs")
        assert r.json()["keypairs"][0]["name"] == "test-key"

    def test_show_and_delete(self, client):
        client.post(f"/v2.1/{PID}/os-keypairs", json={"keypair": {"name": "show-key"}})
        r = client.get(f"/v2.1/{PID}/os-keypairs/show-key")
        assert r.status_code == 200
        assert r.json()["keypair"]["name"] == "show-key"
        r = client.delete(f"/v2.1/{PID}/os-keypairs/show-key")
        assert r.status_code == 204

    def test_import(self, client):
        r = client.post(f"/v2.1/{PID}/os-keypairs/import",
                        json={"keypair": {"name": "imported-key", "public_key": "ssh-rsa AAAA... sim@test"}})
        assert r.status_code == 200
        assert r.json()["keypair"]["name"] == "imported-key"


class TestEcsServerGroups:
    def test_create_and_list(self, client):
        r = client.post(f"/v2.1/{PID}/os-server-groups",
                        json={"server_group": {"name": "anti-affinity-1", "policies": ["anti-affinity"]}})
        assert r.status_code == 200
        gid = r.json()["server_group"]["id"]
        assert r.json()["server_group"]["policies"] == ["anti-affinity"]

        r = client.get(f"/v2.1/{PID}/os-server-groups")
        assert len(r.json()["server_groups"]) >= 1

    def test_show_update_delete(self, client):
        r = client.post(f"/v2.1/{PID}/os-server-groups",
                        json={"server_group": {"name": "update-test", "policies": ["affinity"]}})
        gid = r.json()["server_group"]["id"]

        r = client.get(f"/v2.1/{PID}/os-server-groups/{gid}")
        assert r.status_code == 200

        r = client.put(f"/v2.1/{PID}/os-server-groups/{gid}",
                       json={"server_group": {"name": "updated-name", "policies": ["anti-affinity"]}})
        assert r.json()["server_group"]["name"] == "updated-name"

        r = client.delete(f"/v2.1/{PID}/os-server-groups/{gid}")
        assert r.status_code == 204


class TestEcsQuotas:
    def test_get_limits(self, client):
        r = client.get(f"/v1/{PID}/cloudservers/limits")
        assert r.status_code == 200
        data = r.json()["absolute"]
        assert data["maxTotalInstances"] == 100
        assert "totalInstancesUsed" in data
        assert "maxTotalCores" in data
        assert "maxTotalRAMSize" in data
        assert "maxSecurityGroups" in data
        assert "maxFloatingIps" in data


class TestEcsMetadata:
    def test_metadata_crud(self, client):
        sid = _create_server(client)

        # Set metadata
        r = client.put(f"/v1/{PID}/cloudservers/{sid}/metadata",
                       json={"metadata": {"env": "test", "role": "web"}})
        assert r.status_code == 200
        assert r.json()["metadata"]["env"] == "test"

        # Get metadata
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/metadata")
        assert r.json()["metadata"]["role"] == "web"

        # Delete one key
        r = client.delete(f"/v1/{PID}/cloudservers/{sid}/metadata/env")
        assert r.status_code == 204

        # Verify it's gone
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/metadata")
        assert "env" not in r.json()["metadata"]
        assert "role" in r.json()["metadata"]


class TestEcsNics:
    def test_nic_management(self, client):
        sid = _create_server(client)

        # List NICs (should have at least 1 from server creation)
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/os-interface")
        assert r.status_code == 200
        initial_count = len(r.json()["interfaceAttachments"])
        assert initial_count >= 1

        # Add a NIC
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/os-interface",
                        json={"subnet_id": "subnet-1", "net_id": "vpc-1"})
        assert r.status_code == 200
        new_port = r.json()["interfaceAttachment"]["port_id"]

        # Verify it's in the list
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/os-interface")
        assert len(r.json()["interfaceAttachments"]) == initial_count + 1

        # Remove the NIC
        r = client.delete(f"/v1/{PID}/cloudservers/{sid}/os-interface/{new_port}")
        assert r.status_code == 204

        # Verify it's gone
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/os-interface")
        assert len(r.json()["interfaceAttachments"]) == initial_count


class TestEcsConsole:
    def test_remote_console(self, client):
        sid = _create_server(client)
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/remote_console")
        assert r.status_code == 200
        assert r.json()["remote_console"]["type"] == "novnc"
        assert "vnc" in r.json()["remote_console"]["url"]

    def test_console_log(self, client):
        sid = _create_server(client)
        r = client.get(f"/v1/{PID}/cloudservers/{sid}/console_log")
        assert r.status_code == 200
        log = r.text
        assert "Linux version" in log
        assert "cloud-init" in log
        assert "is ready" in log


class TestEcsResize:
    def test_resize(self, client):
        sid = _create_server(client)
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/resize",
                        json={"resize": {"flavorRef": FLAVOR}})
        assert r.status_code == 200
        assert r.json()["job_id"]


class TestEcsChangeOS:
    def test_change_os(self, client):
        sid = _create_server(client)
        new_image = "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21"
        r = client.post(f"/v1/{PID}/cloudservers/{sid}/changeos",
                        json={"changeOs": {"imageRef": new_image}})
        assert r.status_code == 200
        assert r.json()["job_id"]


class TestNovaServerAction:
    def test_create_image_from_server(self, client):
        sid = _create_server(client)
        r = client.post(f"/v2.1/{PID}/servers/{sid}/action",
                        json={"createImage": {"name": "snapshot-from-server"}})
        assert r.status_code == 200
        assert r.json()["image_id"]

    def test_nova_stop_start(self, client):
        sid = _create_server(client)
        r = client.post(f"/v2.1/{PID}/servers/{sid}/action", json={"os-stop": {}})
        assert r.status_code == 202
        r = client.post(f"/v2.1/{PID}/servers/{sid}/action", json={"os-start": {}})
        assert r.status_code == 202


class TestBatch:
    def test_batch_job_lifecycle(self, client):
        r = client.post(f"/v1/{PID}/batch/jobs",
                        json={"name": "test-batch", "command": "python train.py",
                              "instance_count": 2, "flavor_id": "s6.large.2"})
        assert r.status_code == 200
        jid = r.json()["job"]["id"]
        assert r.json()["job"]["status"] == "PENDING"
        assert r.json()["job"]["command"] == "python train.py"

        r = client.get(f"/v1/{PID}/batch/jobs")
        assert r.json()["total"] >= 1

        r = client.get(f"/v1/{PID}/batch/jobs/{jid}")
        assert r.status_code == 200

        r = client.post(f"/v1/{PID}/batch/jobs/{jid}/cancel")
        assert r.json()["job"]["status"] == "CANCELLED"

        r = client.delete(f"/v1/{PID}/batch/jobs/{jid}")
        assert r.status_code == 204


class TestHPC:
    def test_hpc_cluster_lifecycle(self, client):
        r = client.post(f"/v2/{PID}/hpc/clusters",
                        json={"name": "test-hpc", "scheduler": "slurm", "max_node_count": 50})
        assert r.status_code == 200
        cid = r.json()["cluster"]["id"]
        assert r.json()["cluster"]["scheduler"] == "slurm"

        r = client.get(f"/v2/{PID}/hpc/clusters")
        assert r.json()["total"] >= 1

        r = client.post(f"/v2/{PID}/hpc/clusters/{cid}/nodes",
                        json={"flavor": "hpc.large.4"})
        assert r.status_code == 200

        r = client.get(f"/v2/{PID}/hpc/clusters/{cid}")
        assert r.json()["cluster"]["node_count"] >= 1

        r = client.delete(f"/v2/{PID}/hpc/clusters/{cid}")
        assert r.status_code == 204
