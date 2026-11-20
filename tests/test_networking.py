"""Tests for networking services: NAT, VPC Peering, Network ACL, Routes, VPN."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestNAT:
    def test_gateway_lifecycle(self, client):
        r = client.post(f"/v2.0/{PID}/nat_gateways", json={"name": "test-nat", "spec": "2"})
        assert r.status_code == 200
        gid = r.json()["nat_gateway"]["id"]
        assert r.json()["nat_gateway"]["status"] == "ACTIVE"
        r = client.get(f"/v2.0/{PID}/nat_gateways")
        assert r.json()["total"] >= 1
        r = client.get(f"/v2.0/{PID}/nat_gateways/{gid}")
        assert r.status_code == 200
        r = client.delete(f"/v2.0/{PID}/nat_gateways/{gid}")
        assert r.status_code == 204

    def test_snat_rules(self, client):
        r = client.post(f"/v2.0/{PID}/nat_gateways", json={"name": "snat-gw"})
        gid = r.json()["nat_gateway"]["id"]
        r = client.post(f"/v2.0/{PID}/snat_rules",
                        json={"nat_gateway_id": gid, "cidr": "192.168.0.0/24",
                              "floating_ip_address": "1.2.3.4"})
        assert r.status_code == 200
        rid = r.json()["snat_rule"]["id"]
        assert r.json()["snat_rule"]["cidr"] == "192.168.0.0/24"
        r = client.get(f"/v2.0/{PID}/snat_rules")
        assert r.json()["total"] >= 1
        r = client.delete(f"/v2.0/{PID}/snat_rules/{rid}")
        assert r.status_code == 204

    def test_dnat_rules(self, client):
        r = client.post(f"/v2.0/{PID}/nat_gateways", json={"name": "dnat-gw"})
        gid = r.json()["nat_gateway"]["id"]
        r = client.post(f"/v2.0/{PID}/dnat_rules",
                        json={"nat_gateway_id": gid, "private_ip": "192.168.0.10",
                              "internal_service_port": 80, "protocol": "tcp",
                              "external_service_port": 8080})
        assert r.status_code == 200
        rid = r.json()["dnat_rule"]["id"]
        assert r.json()["dnat_rule"]["internal_service_port"] == 80
        r = client.get(f"/v2.0/{PID}/dnat_rules")
        assert r.json()["total"] >= 1
        r = client.delete(f"/v2.0/{PID}/dnat_rules/{rid}")
        assert r.status_code == 204


class TestVPCPeering:
    def test_peering_lifecycle(self, client):
        # Create peering
        r = client.post(f"/v2.0/{PID}/vpc-peerings",
                        json={"name": "test-peering", "requester_vpc_id": "vpc-1", "accepter_vpc_id": "vpc-2"})
        assert r.status_code == 200
        pid = r.json()["peering"]["id"]
        assert r.json()["peering"]["status"] == "PENDING_ACCEPTANCE"

        # Accept
        r = client.put(f"/v2.0/{PID}/vpc-peerings/{pid}/accept")
        assert r.status_code == 200
        assert r.json()["peering"]["status"] == "ACTIVE"

        # List
        r = client.get(f"/v2.0/{PID}/vpc-peerings")
        assert r.json()["count"] >= 1

        # Delete
        r = client.delete(f"/v2.0/{PID}/vpc-peerings/{pid}")
        assert r.status_code == 204

    def test_reject_peering(self, client):
        r = client.post(f"/v2.0/{PID}/vpc-peerings", json={"name": "reject-test"})
        pid = r.json()["peering"]["id"]
        r = client.put(f"/v2.0/{PID}/vpc-peerings/{pid}/reject")
        assert r.json()["peering"]["status"] == "REJECTED"


class TestNetworkACL:
    def test_acl_lifecycle(self, client):
        # Create ACL
        r = client.post(f"/v3/{PID}/vpc/acls", json={"name": "test-acl"})
        assert r.status_code == 200
        acl_id = r.json()["acl"]["id"]

        # Add ingress rule
        r = client.post(f"/v3/{PID}/vpc/acls/{acl_id}/ingress-rules",
                        json={"action": "ALLOW", "protocol": "TCP", "destination_port": "443"})
        assert r.status_code == 200
        assert r.json()["rule"]["protocol"] == "TCP"

        # Add egress rule
        r = client.post(f"/v3/{PID}/vpc/acls/{acl_id}/egress-rules",
                        json={"action": "DENY", "protocol": "ALL"})
        assert r.status_code == 200
        assert r.json()["rule"]["action"] == "DENY"

        # Associate with subnet
        r = client.post(f"/v3/{PID}/vpc/acls/{acl_id}/associate", json={"subnet_id": "subnet-1"})
        assert r.status_code == 200
        assert "subnet-1" in r.json()["acl"]["subnets"]

        # Disassociate
        r = client.post(f"/v3/{PID}/vpc/acls/{acl_id}/disassociate", json={"subnet_id": "subnet-1"})
        assert r.status_code == 200
        assert "subnet-1" not in r.json()["acl"]["subnets"]

        # List + show + delete
        r = client.get(f"/v3/{PID}/vpc/acls")
        assert r.json()["count"] >= 1
        r = client.get(f"/v3/{PID}/vpc/acls/{acl_id}")
        assert r.status_code == 200
        r = client.delete(f"/v3/{PID}/vpc/acls/{acl_id}")
        assert r.status_code == 204


class TestVPCRoutes:
    def test_route_table(self, client):
        # Create route table
        r = client.post(f"/v1/{PID}/vpc/routetables", json={"name": "test-rt", "vpc_id": "vpc-1"})
        assert r.status_code == 200
        rt_id = r.json()["routetable"]["id"]

        # Add route
        r = client.post(f"/v1/{PID}/vpc/routetables/{rt_id}/routes",
                        json={"destination": "10.0.0.0/8", "nexthop": "peering-1", "type": "peering"})
        assert r.status_code == 200
        route_id = r.json()["route"]["id"]
        assert r.json()["route"]["destination"] == "10.0.0.0/8"

        # List route tables
        r = client.get(f"/v1/{PID}/vpc/routetables")
        assert r.json()["count"] >= 1

        # Show
        r = client.get(f"/v1/{PID}/vpc/routetables/{rt_id}")
        assert r.status_code == 200
        assert len(r.json()["routetable"]["routes"]) >= 1

        # Delete route
        r = client.delete(f"/v1/{PID}/vpc/routetables/{rt_id}/routes/{route_id}")
        assert r.status_code == 204

        # Delete route table
        r = client.delete(f"/v1/{PID}/vpc/routetables/{rt_id}")
        assert r.status_code == 204


class TestVPN:
    def test_vpn_gateway_and_connection(self, client):
        # Create gateway
        r = client.post(f"/v5/{PID}/vpn-gateways", json={"name": "test-vpn", "vpc_id": "vpc-1"})
        assert r.status_code == 200
        gid = r.json()["vpn_gateway"]["id"]
        assert r.json()["vpn_gateway"]["status"] == "ACTIVE"

        # Create connection
        r = client.post(f"/v5/{PID}/vpn-connections",
                        json={"name": "test-conn", "vgw_id": gid, "peer_subnets": ["10.1.0.0/16"]})
        assert r.status_code == 200
        cid = r.json()["vpn_connection"]["id"]
        assert r.json()["vpn_connection"]["status"] == "ACTIVE"

        # List
        r = client.get(f"/v5/{PID}/vpn-gateways")
        assert r.json()["total"] >= 1
        r = client.get(f"/v5/{PID}/vpn-connections")
        assert r.json()["total"] >= 1

        # Delete
        r = client.delete(f"/v5/{PID}/vpn-gateways/{gid}")
        assert r.status_code == 204
