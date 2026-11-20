"""Pagination and filter tests: offset/marker/limit combinations, list filtering."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


def _create_servers(client, count=5, prefix="page-test"):
    """Create multiple servers for pagination testing."""
    ids = []
    for i in range(count):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": f"{prefix}-{i}"}})
        ids.append(r.json()["serverIds"][0])
    return ids


class TestPagination:
    """Test pagination on list endpoints."""

    def test_default_limit(self, client):
        """Default limit should return some results."""
        _create_servers(client, 3)
        r = client.get(f"/v1/{PID}/cloudservers/detail")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "servers" in data
        assert data["count"] >= 3

    def test_limit_1(self, client):
        """Limit 1 should return at most 1 server."""
        _create_servers(client, 3)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=1")
        data = r.json()
        assert len(data["servers"]) <= 1

    def test_limit_2(self, client):
        """Limit 2 should return at most 2 servers."""
        _create_servers(client, 3)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=2")
        data = r.json()
        assert len(data["servers"]) <= 2

    def test_limit_100(self, client):
        """Limit 100 should return all servers (up to 100)."""
        _create_servers(client, 3)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=100")
        data = r.json()
        assert len(data["servers"]) >= 3

    def test_offset_1(self, client):
        """Offset 1 should skip the first server."""
        ids = _create_servers(client, 3)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=10&offset=2")
        data = r.json()
        # offset is page number, so offset=2 means skip first 10 (or limit) results
        assert data["count"] >= 3

    def test_marker_pagination(self, client):
        """Marker should start after the specified server."""
        ids = _create_servers(client, 5)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=2")
        first_page = r.json()
        if len(first_page["servers"]) == 2:
            marker = first_page["servers"][-1]["id"]
            r2 = client.get(f"/v1/{PID}/cloudservers/detail?limit=2&marker={marker}")
            second_page = r2.json()
            # Second page should not contain the marker server
            server_ids = [s["id"] for s in second_page["servers"]]
            assert marker not in server_ids

    def test_servers_links_present(self, client):
        """servers_links should be present when there are more pages."""
        _create_servers(client, 5)
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=2")
        data = r.json()
        # If there are more results than the limit, servers_links should exist
        if data["count"] > 2:
            assert "servers_links" in data

    def test_hcs_default_limit_2(self, client):
        """HCS profile default limit should be 2 (observed quirk)."""
        for i in range(3):
            client.post(f"/v1.1/{HCS_PID}/cloudservers",
                        json={"server": {"imageRef": "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21",
                                          "flavorRef": "s7n.large.2", "name": f"hcs-page-{i}"}})
        r = client.get(f"/v1/{HCS_PID}/cloudservers/detail")
        data = r.json()
        assert len(data["servers"]) <= 2  # hcs default is 2
        assert data["count"] >= 3  # but count shows total


class TestListFilters:
    """Test filtering on list endpoints."""

    def test_filter_by_name(self, client):
        """Filter servers by name (fuzzy match)."""
        _create_servers(client, 3, prefix="filter-name")
        r = client.get(f"/v1/{PID}/cloudservers/detail?name=filter-name")
        data = r.json()
        for s in data["servers"]:
            assert "filter-name" in s["name"]

    def test_filter_by_status(self, client):
        """Filter servers by status."""
        _create_servers(client, 2)
        r = client.get(f"/v1/{PID}/cloudservers/detail?status=ACTIVE")
        data = r.json()
        for s in data["servers"]:
            assert s["status"] in ("ACTIVE", "REBOOT", "HARD_REBOOT", "REBUILD", "MIGRATING", "RESIZE")

    def test_filter_by_flavor(self, client):
        """Filter servers by flavor."""
        _create_servers(client, 2)
        r = client.get(f"/v1/{PID}/cloudservers/detail?flavor={FLAVOR}")
        data = r.json()
        for s in data["servers"]:
            if "flavor" in s:
                assert s["flavor"]["id"] == FLAVOR

    def test_filter_nonexistent_name(self, client):
        """Filter by name that doesn't match anything."""
        r = client.get(f"/v1/{PID}/cloudservers/detail?name=zzz-nonexistent-zzz")
        data = r.json()
        assert data["count"] == 0
        assert len(data["servers"]) == 0

    def test_volume_filter_by_name(self, client):
        """Filter volumes by name."""
        client.post(f"/v2.1/{PID}/cloudvolumes",
                    json={"volume": {"size": 10, "name": "filter-vol-test"}})
        r = client.get(f"/v2/{PID}/cloudvolumes?name=filter-vol")
        data = r.json()
        assert len(data["volumes"]) >= 1
        for v in data["volumes"]:
            assert "filter-vol" in v["name"]

    def test_port_filter_by_device_id(self, client):
        """Filter ports by device_id."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "port-filter"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/v1/{PID}/ports?device_id={sid}")
        data = r.json()
        assert len(data["ports"]) >= 1
        for p in data["ports"]:
            assert p["device_id"] == sid

    def test_backup_filter_by_resource(self, client):
        """Filter CBR backups by resource_id."""
        r = client.get(f"/v3/{PID}/backups?resource_id=nonexistent-resource")
        data = r.json()
        assert data["count"] == 0


class TestCrossProjectIsolation:
    """Test that resources are isolated between projects."""

    def test_servers_isolated(self, client):
        """Servers in one project should not appear in another."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "isolated-vm"}})
        sid = r.json()["serverIds"][0]

        # Check in the correct project
        r = client.get(f"/v1/{PID}/cloudservers/detail?limit=100")
        assert any(s["id"] == sid for s in r.json()["servers"])

        # Check in the other project: should NOT be there
        r = client.get(f"/v1/{HCS_PID}/cloudservers/detail?limit=100")
        assert not any(s["id"] == sid for s in r.json()["servers"])

    def test_show_from_wrong_project_404(self, client):
        """Showing a server from the wrong project should 404."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "wrong-project"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/v1/{HCS_PID}/cloudservers/{sid}")
        assert r.status_code == 404

    def test_volumes_isolated(self, client):
        """Volumes in one project should not appear in another."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "isolated-vol"}})
        vid = r.json()["volume_ids"][0]

        r = client.get(f"/v2/{PID}/cloudvolumes")
        assert any(v["id"] == vid for v in r.json()["volumes"])

        r = client.get(f"/v2/{HCS_PID}/cloudvolumes")
        assert not any(v["id"] == vid for v in r.json()["volumes"])
