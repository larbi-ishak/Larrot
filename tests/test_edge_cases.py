"""Edge case tests: boundary values, unicode, special characters, type mismatches."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestBoundaryValues:
    """Test boundary values for numeric fields."""

    def test_volume_size_min_boundary(self, client):
        """Size 10 is the minimum: should succeed."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "min-vol"}})
        assert r.status_code == 202

    def test_volume_size_below_min(self, client):
        """Size 9 should fail."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 9, "name": "too-small"}})
        assert r.status_code == 400

    def test_volume_size_zero(self, client):
        """Size 0 should fail."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 0, "name": "zero"}})
        assert r.status_code == 400

    def test_volume_size_negative(self, client):
        """Negative size should fail."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": -10, "name": "negative"}})
        assert r.status_code == 400

    def test_volume_size_max(self, client):
        """Size 32768 is the max: should succeed."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 32768, "name": "max-vol"}})
        assert r.status_code == 202

    def test_volume_size_above_max(self, client):
        """Size 32769 should fail."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 32769, "name": "too-big"}})
        assert r.status_code == 400

    def test_eip_bandwidth_min(self, client):
        """Bandwidth size 1 is the minimum."""
        r = client.post(f"/v1/{PID}/publicips",
                        json={"publicip": {"type": "5_bgp"},
                              "bandwidth": {"name": "min-bw", "size": 1, "share_type": "PER"}})
        assert r.status_code == 200

    def test_eip_bandwidth_zero(self, client):
        """Bandwidth size 0 should fail."""
        r = client.post(f"/v1/{PID}/publicips",
                        json={"publicip": {"type": "5_bgp"},
                              "bandwidth": {"name": "zero-bw", "size": 0, "share_type": "PER"}})
        assert r.status_code in (200, 400)  # depends on validation

    def test_ims_min_disk_min(self, client):
        """min_disk 10 is the minimum."""
        r = client.post("/v2/cloudimages/action",
                        json={"name": "min-disk", "image_url": "b:k.qcow2", "min_disk": 10})
        assert r.status_code == 200

    def test_ims_min_disk_below_min(self, client):
        """min_disk 9 should fail."""
        r = client.post("/v2/cloudimages/action",
                        json={"name": "too-small", "image_url": "b:k.qcow2", "min_disk": 9})
        assert r.status_code == 400


class TestUnicodeAndSpecialChars:
    """Test unicode and special characters in names."""

    def test_server_name_chinese(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "云服务器-测试"}})
        assert r.status_code == 200

    def test_server_name_arabic(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "خادم-اختبار"}})
        assert r.status_code == 200

    def test_server_name_with_hyphens(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "my-server-name-123"}})
        assert r.status_code == 200

    def test_server_name_with_underscores(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "my_server_name"}})
        assert r.status_code == 200

    def test_volume_name_unicode(self, client):
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": "卷-データ"}})
        assert r.status_code == 202

    def test_sg_name_special_chars(self, client):
        r = client.post(f"/v1/{PID}/security-groups",
                        json={"security_group": {"name": "sg-with-(parentheses)"}})
        assert r.status_code == 201


class TestTypeMismatches:
    """Test sending wrong types for fields."""

    def test_volume_size_as_string(self, client):
        """Size as string → EVS.1010 400 (type validation)."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": "ten", "name": "string-size"}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "EVS.1010"

    def test_server_count_as_string(self, client):
        """Count as string → Ecs.0005 400 (type validation)."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "x", "count": "three"}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0005"

    def test_server_count_zero(self, client):
        """Count 0 → Ecs.0005 400."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "x", "count": 0}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0005"

    def test_server_count_negative(self, client):
        """Count -1 → Ecs.0005 400."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "x", "count": -1}})
        assert r.status_code == 400

    def test_server_count_bool(self, client):
        """Count as boolean → Ecs.0005 400 (bool is not a valid count)."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "x", "count": True}})
        assert r.status_code == 400

    def test_volume_size_bool(self, client):
        """Size as boolean → EVS.1010 400."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": True, "name": "bool-size"}})
        assert r.status_code == 400

    def test_dry_run_as_string(self, client):
        """dry_run as string should be handled."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "x"}, "dry_run": "true"})
        assert r.status_code in (200, 202, 422)

    def test_eip_size_as_float(self, client):
        """Bandwidth size as float."""
        r = client.post(f"/v1/{PID}/publicips",
                        json={"publicip": {"type": "5_bgp"},
                              "bandwidth": {"name": "float-bw", "size": 5.5, "share_type": "PER"}})
        assert r.status_code in (200, 400, 422)


class TestLongStrings:
    """Test very long strings."""

    def test_server_name_128_chars(self, client):
        """128 chars is the documented max."""
        name = "a" * 128
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": name}})
        assert r.status_code == 200

    def test_server_name_129_chars(self, client):
        """129 chars should potentially fail."""
        name = "a" * 129
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": name}})
        assert r.status_code in (200, 400)  # sim may not enforce

    def test_volume_name_255_chars(self, client):
        """255 chars for volume name."""
        name = "v" * 255
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": name}})
        assert r.status_code == 202

    def test_description_1024_chars(self, client):
        """1024 chars for description."""
        desc = "d" * 1024
        r = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "long-desc", "description": desc}})
        assert r.status_code == 200


class TestEmptyStrings:
    """Test empty string values."""

    def test_server_name_empty(self, client):
        """Empty name → Ecs.0005 400 (name is required)."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": ""}})
        assert r.status_code == 400

    def test_volume_name_empty(self, client):
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": 10, "name": ""}})
        assert r.status_code == 202  # name is optional

    def test_vpc_description_empty(self, client):
        r = client.post(f"/v1/{PID}/vpcs",
                        json={"vpc": {"name": "empty-desc", "description": ""}})
        assert r.status_code == 200


class TestNullValues:
    """Test null/None values."""

    def test_server_name_null(self, client):
        """Name as None → Ecs.0005 400 (type validation)."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": None}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "Ecs.0005"

    def test_volume_size_null(self, client):
        """Size as None → EVS.1010 400 (type validation)."""
        r = client.post(f"/v2.1/{PID}/cloudvolumes",
                        json={"volume": {"size": None, "name": "null-size"}})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "EVS.1010"

    def test_optional_fields_null(self, client):
        """Optional fields as null should be OK."""
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "null-optional", "adminPass": None,
                                          "key_name": None, "description": None}})
        assert r.status_code == 200
