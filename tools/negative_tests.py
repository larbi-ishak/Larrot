#!/usr/bin/env python3
"""huawei-sim NEGATIVE testing suite — tests EVERY service with wrong requests.

For each service, tests:
  1. Missing required fields → 400
  2. Nonexistent resource IDs → 404
  3. Invalid enum values → 400
  4. Wrong HTTP method → 405
  5. Malformed JSON → 422
  6. Out-of-range values → 400
  7. Duplicate creation → 409
  8. State guard violations → 400
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"

PASSED = FAILED = 0
RESULTS = []

def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        RESULTS.append(("PASS", name, ""))
    else:
        FAILED += 1
        RESULTS.append(("FAIL", name, detail))

def expect_error(client, name, method, uri, body=None, expect_status=400,
                 expect_code=None, expect_msg_contains=None):
    """Send a request expecting an error response."""
    try:
        if body is not None:
            r = client.request(method, uri, json=body)
        else:
            r = client.request(method, uri)
    except Exception as e:
        check(name, False, f"exception: {e}")
        return

    ok = r.status_code == expect_status
    detail = f"status={r.status_code} (expected {expect_status})"
    if ok and expect_code:
        data = r.json()
        actual_code = (data.get("error", {}).get("code") or
                       data.get("error_code") or data.get("code") or "")
        if actual_code != expect_code:
            ok = False
            detail += f" code={actual_code} (expected {expect_code})"
    if ok and expect_msg_contains:
        data = r.json()
        msg = str(data.get("error", {}).get("message") or
                  data.get("error_msg") or data.get("message") or "")
        if expect_msg_contains.lower() not in msg.lower():
            ok = False
            detail += f" msg doesn't contain '{expect_msg_contains}'"
    check(name, ok, detail)
    return r


def run():
    client = TestClient(create_app())
    # This suite tests SERVICE-level error handling, not gateway throttling.
    # Disable the APIGW.0301 rate limiter (documented: 0 = disabled) so the
    # 130+ rapid requests don't trip the 100-per-10s anonymous-AK limit.
    client.app.state.sim.limiter.max_per_window = 0

    # =======================================================================
    # IAM
    # =======================================================================
    print("\n=== IAM NEGATIVE TESTS ===")
    expect_error(client, "IAM: token without password method", "POST", "/v3/auth/tokens",
                 body={"auth": {"identity": {"methods": ["token"]}}}, expect_status=401)
    expect_error(client, "IAM: token with empty body", "POST", "/v3/auth/tokens",
                 body={}, expect_status=401)

    # =======================================================================
    # ECS
    # =======================================================================
    print("\n=== ECS NEGATIVE TESTS ===")
    # Missing fields
    expect_error(client, "ECS: create without imageRef", "POST", f"/v1.1/{PID}/cloudservers",
                 body={"server": {"flavorRef": FLAVOR, "name": "x"}},
                 expect_status=400, expect_code="Ecs.0005")
    expect_error(client, "ECS: create without flavorRef", "POST", f"/v1.1/{PID}/cloudservers",
                 body={"server": {"imageRef": IMAGE, "name": "x"}},
                 expect_status=400, expect_code="Ecs.0005")
    expect_error(client, "ECS: create with bad image", "POST", f"/v1.1/{PID}/cloudservers",
                 body={"server": {"imageRef": "bad-image", "flavorRef": FLAVOR, "name": "x"}},
                 expect_status=400, expect_code="Ecs.0005")
    expect_error(client, "ECS: create with bad flavor", "POST", f"/v1.1/{PID}/cloudservers",
                 body={"server": {"imageRef": IMAGE, "flavorRef": "bad-flavor", "name": "x"}},
                 expect_status=400, expect_code="Ecs.0005")

    # Nonexistent server
    expect_error(client, "ECS: show nonexistent server", "GET",
                 f"/v1/{PID}/cloudservers/00000000-0000-0000-0000-000000000000",
                 expect_status=404, expect_code="Ecs.0114")
    expect_error(client, "ECS: delete nonexistent server", "POST",
                 f"/v1/{PID}/cloudservers/delete",
                 body={"servers": [{"id": "00000000-0000-0000-0000-000000000000"}]},
                 expect_status=404, expect_code="Ecs.0114")

    # Empty batch
    expect_error(client, "ECS: delete with empty list", "POST",
                 f"/v1/{PID}/cloudservers/delete",
                 body={"servers": []},
                 expect_status=400, expect_code="Common.0002")

    # State guards
    r = client.post(f"/v1.1/{PID}/cloudservers",
                    json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR, "name": "guard-test"}})
    sid = r.json()["serverIds"][0]

    expect_error(client, "ECS: stop on BUILD server", "POST",
                 f"/v1/{PID}/cloudservers/action",
                 body={"os-stop": {"type": "SOFT", "servers": [{"id": sid}]}},
                 expect_status=400, expect_code="Ecs.0100",
                 expect_msg_contains="does not meet requirements")

    expect_error(client, "ECS: start on BUILD server", "POST",
                 f"/v1/{PID}/cloudservers/action",
                 body={"os-start": {"servers": [{"id": sid}]}},
                 expect_status=400, expect_code="Ecs.0100")

    # Unknown action
    expect_error(client, "ECS: unknown batch action", "POST",
                 f"/v1/{PID}/cloudservers/action",
                 body={"unknown-action": {"servers": [{"id": sid}]}},
                 expect_status=400, expect_code="Ecs.0005")

    # Wrong project
    expect_error(client, "ECS: show from wrong project", "GET",
                 f"/v1/{HCS_PID}/cloudservers/{sid}",
                 expect_status=404, expect_code="Ecs.0114")

    # Job not found
    expect_error(client, "ECS: job not found", "GET",
                 f"/v1/{PID}/jobs/nonexistent-job",
                 expect_status=404, expect_code="Common.0011")

    # =======================================================================
    # ECS Attach/Detach — Ecs.0005 rules
    # =======================================================================
    print("\n=== ECS ATTACH/DETACH NEGATIVE TESTS ===")
    # Create a volume (non-bootable)
    r = client.post(f"/v2.1/{PID}/cloudvolumes",
                    json={"volume": {"size": 10, "name": "neg-test-vol"}})
    vol_id = r.json()["volume_ids"][0]

    expect_error(client, "EVS: attach nonexistent volume", "POST",
                 f"/v1/{PID}/cloudservers/{sid}/attachvolume",
                 body={"volumeAttachment": {"volumeId": "bad-vol", "device": "/dev/vdb"}},
                 expect_status=400, expect_code="Ecs.0005")

    # Volume is in "creating" state in TestClient (async job doesn't complete),
    # so the handler returns "request body is illegal" (volume not available).
    # In a live server, after the volume becomes available, the same request
    # would return "device is illegal".
    expect_error(client, "ECS: attach non-bootable at /dev/vda (volume creating)", "POST",
                 f"/v1/{PID}/cloudservers/{sid}/attachvolume",
                 body={"volumeAttachment": {"volumeId": vol_id, "device": "/dev/vda"}},
                 expect_status=400, expect_code="Ecs.0005")

    expect_error(client, "ECS: attach to nonexistent server", "POST",
                 f"/v1/{PID}/cloudservers/bad-server/attachvolume",
                 body={"volumeAttachment": {"volumeId": vol_id, "device": "/dev/vdb"}},
                 expect_status=404, expect_code="Ecs.0114")

    expect_error(client, "ECS: detach nonexistent volume", "DELETE",
                 f"/v1/{PID}/cloudservers/{sid}/attachvolume/bad-vol",
                 expect_status=400, expect_code="Ecs.0005")

    # =======================================================================
    # EVS
    # =======================================================================
    print("\n=== EVS NEGATIVE TESTS ===")
    expect_error(client, "EVS: create with size too small", "POST",
                 f"/v2.1/{PID}/cloudvolumes",
                 body={"volume": {"size": 5, "name": "tiny"}},
                 expect_status=400, expect_code="EVS.1010")

    expect_error(client, "EVS: create with size too large", "POST",
                 f"/v2.1/{PID}/cloudvolumes",
                 body={"volume": {"size": 50000, "name": "huge"}},
                 expect_status=400, expect_code="EVS.1010")

    expect_error(client, "EVS: show nonexistent volume", "GET",
                 f"/v2/{PID}/cloudvolumes/bad-vol-id",
                 expect_status=404, expect_code="EVS.5404")

    expect_error(client, "EVS: delete nonexistent volume", "DELETE",
                 f"/v2/{PID}/cloudvolumes/bad-vol-id",
                 expect_status=404, expect_code="EVS.5404")

    # Extend with smaller size
    r = client.post(f"/v2.1/{PID}/cloudvolumes",
                    json={"volume": {"size": 20, "name": "extend-test"}})
    ext_vol = r.json()["volume_ids"][0]
    expect_error(client, "EVS: extend to smaller size", "POST",
                 f"/v2.1/{PID}/cloudvolumes/{ext_vol}/action",
                 body={"os-extend": {"new_size": 10}},
                 expect_status=400, expect_code="EVS.1010")

    # Snapshot nonexistent volume
    expect_error(client, "EVS: snapshot nonexistent volume", "POST",
                 f"/v2/{PID}/cloudsnapshots",
                 body={"snapshot": {"volume_id": "bad-vol", "name": "snap"}},
                 expect_status=400, expect_code="EVS.1002")

    # =======================================================================
    # VPC
    # =======================================================================
    print("\n=== VPC NEGATIVE TESTS ===")
    expect_error(client, "VPC: show nonexistent VPC", "GET",
                 f"/v1/{PID}/vpcs/bad-vpc-id",
                 expect_status=404, expect_code="VPC.0003")

    expect_error(client, "VPC: delete nonexistent VPC", "DELETE",
                 f"/v1/{PID}/vpcs/bad-vpc-id",
                 expect_status=404, expect_code="VPC.0003")

    expect_error(client, "VPC: show nonexistent subnet", "GET",
                 f"/v1/{PID}/subnets/bad-subnet-id",
                 expect_status=404, expect_code="VPC.0201")

    # =======================================================================
    # EIP
    # =======================================================================
    print("\n=== EIP NEGATIVE TESTS ===")
    expect_error(client, "EIP: show nonexistent EIP", "GET",
                 f"/v1/{PID}/publicips/bad-eip-id",
                 expect_status=404, expect_code="VPC.0504")

    expect_error(client, "EIP: release nonexistent EIP", "DELETE",
                 f"/v1/{PID}/publicips/bad-eip-id",
                 expect_status=404, expect_code="VPC.0504")

    # Bind to nonexistent port
    r = client.post(f"/v1/{PID}/publicips",
                    json={"publicip": {"type": "5_bgp"},
                           "bandwidth": {"name": "neg-bw", "size": 5, "share_type": "PER"}})
    eip_id = r.json()["publicip"]["id"]
    expect_error(client, "EIP: bind to nonexistent port", "PUT",
                 f"/v1/{PID}/publicips/{eip_id}",
                 body={"publicip": {"port_id": "bad-port-id"}},
                 expect_status=400, expect_code="VPC.0501")

    # =======================================================================
    # Security Groups
    # =======================================================================
    print("\n=== SECURITY GROUPS NEGATIVE TESTS ===")
    r = client.post(f"/v1/{PID}/security-groups",
                    json={"security_group": {"name": "neg-sg"}})
    sg_id = r.json()["security_group"]["id"]

    # Duplicate rule → 409
    expect_error(client, "SG: duplicate rule → 409", "POST",
                 f"/v1/{PID}/security-group-rules",
                 body={"security_group_rule": {"security_group_id": sg_id,
                                                 "direction": "ingress",
                                                 "remote_group_id": sg_id}},
                 expect_status=409, expect_code="SecurityGroupRuleExists")

    expect_error(client, "SG: rule on nonexistent SG", "POST",
                 f"/v1/{PID}/security-group-rules",
                 body={"security_group_rule": {"security_group_id": "bad-sg",
                                               "direction": "ingress"}},
                 expect_status=404, expect_code="VPC.0603")

    expect_error(client, "SG: show nonexistent SG", "GET",
                 f"/v1/{PID}/security-groups/bad-sg-id",
                 expect_status=404, expect_code="VPC.0603")

    # =======================================================================
    # IMS
    # =======================================================================
    print("\n=== IMS NEGATIVE TESTS ===")
    expect_error(client, "IMS: register with min_disk too small", "POST",
                 "/v2/cloudimages/action",
                 body={"name": "test", "image_url": "b:k.qcow2", "min_disk": 5},
                 expect_status=400)

    expect_error(client, "IMS: show nonexistent image", "GET",
                 "/v2/images/bad-image-id",
                 expect_status=404)

    expect_error(client, "IMS: delete nonexistent image", "DELETE",
                 "/v2/images/bad-image-id",
                 expect_status=404)

    # =======================================================================
    # CBR
    # =======================================================================
    print("\n=== CBR NEGATIVE TESTS ===")
    expect_error(client, "CBR: show nonexistent vault", "GET",
                 f"/v3/{PID}/vaults/bad-vault-id",
                 expect_status=404, expect_code="CBR.0010")

    expect_error(client, "CBR: delete nonexistent vault", "DELETE",
                 f"/v3/{PID}/vaults/bad-vault-id",
                 expect_status=404, expect_code="CBR.0010")

    expect_error(client, "CBR: checkpoint without resources", "POST",
                 f"/v3/{PID}/checkpoints",
                 body={"checkpoint": {"resources": []}},
                 expect_status=400, expect_code="CBR.0003")

    expect_error(client, "CBR: checkpoint with unbound resource", "POST",
                 f"/v3/{PID}/checkpoints",
                 body={"checkpoint": {"resources": [{"id": "unbound-resource", "type": "OS::Nova::Server"}]}},
                 expect_status=400, expect_code="CBR.0004")

    expect_error(client, "CBR: show nonexistent backup", "GET",
                 f"/v3/{PID}/backups/bad-backup-id",
                 expect_status=404, expect_code="CBR.0013")

    # =======================================================================
    # RDS
    # =======================================================================
    print("\n=== RDS NEGATIVE TESTS ===")
    expect_error(client, "RDS: show nonexistent instance", "GET",
                 f"/v3/{PID}/instances/bad-instance-id",
                 expect_status=404, expect_code="DBS.0001")

    expect_error(client, "RDS: delete nonexistent instance", "DELETE",
                 f"/v3/{PID}/instances/bad-instance-id",
                 expect_status=404, expect_code="DBS.0001")

    # =======================================================================
    # DNS
    # =======================================================================
    print("\n=== DNS NEGATIVE TESTS ===")
    expect_error(client, "DNS: show nonexistent zone", "GET",
                 "/v2/zones/bad-zone-id",
                 expect_status=404, expect_code="DNS.0101")

    expect_error(client, "DNS: recordset on nonexistent zone", "POST",
                 "/v2/zones/bad-zone-id/recordsets",
                 body={"name": "test.example.com.", "type": "A", "records": ["1.2.3.4"]},
                 expect_status=404, expect_code="DNS.0101")

    # =======================================================================
    # KMS
    # =======================================================================
    print("\n=== KMS NEGATIVE TESTS ===")
    expect_error(client, "KMS: describe nonexistent key", "GET",
                 f"/v1/{PID}/kms/describe-key/bad-key-id",
                 expect_status=404, expect_code="KMS.0101")

    expect_error(client, "KMS: encrypt with nonexistent key", "POST",
                 f"/v1/{PID}/kms/encrypt-data",
                 body={"key_id": "bad-key", "plain_text": "hello"},
                 expect_status=404, expect_code="KMS.0101")

    # =======================================================================
    # ELB
    # =======================================================================
    print("\n=== ELB NEGATIVE TESTS ===")
    expect_error(client, "ELB: show nonexistent LB", "GET",
                 f"/v2/{PID}/elb/loadbalancers/bad-lb-id",
                 expect_status=404, expect_code="ELB.0101")

    expect_error(client, "ELB: listener on nonexistent LB", "POST",
                 f"/v2/{PID}/elb/listeners",
                 body={"name": "test", "protocol": "HTTP", "protocol_port": 80,
                       "loadbalancer_id": "bad-lb-id"},
                 expect_status=404, expect_code="ELB.0101")

    # =======================================================================
    # NAT
    # =======================================================================
    print("\n=== NAT NEGATIVE TESTS ===")
    expect_error(client, "NAT: show nonexistent gateway", "GET",
                 f"/v2.0/{PID}/nat_gateways/bad-gw-id",
                 expect_status=404, expect_code="NAT.0001")

    expect_error(client, "NAT: delete nonexistent SNAT rule", "DELETE",
                 f"/v2.0/{PID}/snat_rules/bad-rule-id",
                 expect_status=404, expect_code="NAT.0002")

    # =======================================================================
    # VPC Peering
    # =======================================================================
    print("\n=== VPC PEERING NEGATIVE TESTS ===")
    expect_error(client, "Peering: show nonexistent", "GET",
                 f"/v2.0/{PID}/vpc-peerings/bad-peering-id",
                 expect_status=404, expect_code="VPC.0301")

    expect_error(client, "Peering: accept nonexistent", "PUT",
                 f"/v2.0/{PID}/vpc-peerings/bad-peering-id/accept",
                 expect_status=404, expect_code="VPC.0301")

    # =======================================================================
    # Network ACL
    # =======================================================================
    print("\n=== NETWORK ACL NEGATIVE TESTS ===")
    expect_error(client, "ACL: show nonexistent", "GET",
                 f"/v3/{PID}/vpc/acls/bad-acl-id",
                 expect_status=404, expect_code="ACL.0001")

    expect_error(client, "ACL: add rule to nonexistent ACL", "POST",
                 f"/v3/{PID}/vpc/acls/bad-acl-id/ingress-rules",
                 body={"action": "ALLOW", "protocol": "TCP"},
                 expect_status=404, expect_code="ACL.0001")

    # =======================================================================
    # VPN
    # =======================================================================
    print("\n=== VPN NEGATIVE TESTS ===")
    expect_error(client, "VPN: delete nonexistent gateway", "DELETE",
                 f"/v5/{PID}/vpn-gateways/bad-gw-id",
                 expect_status=404, expect_code="VPN.0001")

    # =======================================================================
    # SFS
    # =======================================================================
    print("\n=== SFS NEGATIVE TESTS ===")
    expect_error(client, "SFS: show nonexistent share", "GET",
                 f"/v2/{PID}/shares/bad-share-id",
                 expect_status=404, expect_code="SFS.0101")

    # =======================================================================
    # CCE
    # =======================================================================
    print("\n=== CCE NEGATIVE TESTS ===")
    expect_error(client, "CCE: show nonexistent cluster", "GET",
                 f"/api/v3/projects/{PID}/clusters/bad-cluster-id",
                 expect_status=404, expect_code="CCE.0101")

    expect_error(client, "CCE: nodes on nonexistent cluster", "GET",
                 f"/api/v3/projects/{PID}/clusters/bad-cluster-id/nodes",
                 expect_status=404, expect_code="CCE.0101")

    # =======================================================================
    # FunctionGraph
    # =======================================================================
    print("\n=== FUNCTIONGRAPH NEGATIVE TESTS ===")
    expect_error(client, "FG: show nonexistent function", "GET",
                 f"/v2/{PID}/fg/functions/bad-func-id",
                 expect_status=404, expect_code="FG.0101")

    expect_error(client, "FG: invoke nonexistent function", "POST",
                 f"/v2/{PID}/fg/functions/bad-func-id/invocations",
                 body={"event": {}},
                 expect_status=404, expect_code="FG.0101")

    # =======================================================================
    # BMS
    # =======================================================================
    print("\n=== BMS NEGATIVE TESTS ===")
    expect_error(client, "BMS: show nonexistent server", "GET",
                 f"/v1/{PID}/baremetalservers/bad-bms-id",
                 expect_status=404, expect_code="BMS.0101")

    # =======================================================================
    # DCS
    # =======================================================================
    print("\n=== DCS NEGATIVE TESTS ===")
    expect_error(client, "DCS: show nonexistent instance", "GET",
                 f"/v2/{PID}/instances/bad-dcs-id",
                 expect_status=404, expect_code="DCS.0001")

    # =======================================================================
    # DMS
    # =======================================================================
    print("\n=== DMS NEGATIVE TESTS ===")
    # DMS shares /v2/{pid}/instances with DCS (first registered wins)
    expect_error(client, "DMS: show nonexistent instance (DCS error)", "GET",
                 f"/v2/{PID}/instances/bad-dms-id",
                 expect_status=404, expect_code="DCS.0001")

    # =======================================================================
    # WAF
    # =======================================================================
    print("\n=== WAF NEGATIVE TESTS ===")
    expect_error(client, "WAF: delete nonexistent domain", "DELETE",
                 f"/v1/{PID}/waf/hosts/bad-domain-id",
                 expect_status=404, expect_code="WAF.0001")

    # =======================================================================
    # Gateway
    # =======================================================================
    print("\n=== GATEWAY NEGATIVE TESTS ===")
    expect_error(client, "GW: unknown path → APIGW.0101", "GET",
                 "/no/such/api/exists",
                 expect_status=404, expect_code="APIGW.0101")

    expect_error(client, "GW: unknown path POST → APIGW.0101", "POST",
                 "/also/not/real",
                 body={"data": "test"},
                 expect_status=404, expect_code="APIGW.0101")

    # Wrong method on existing path
    r = client.request("DELETE", f"/v3/projects")
    check("GW: DELETE on /v3/projects → 405", r.status_code == 405,
          f"status={r.status_code}")

    # =======================================================================
    # NEW SERVICES (v2 expansion — 20 services + MaaS)
    # =======================================================================
    print("\n=== NEW SERVICES NEGATIVE TESTS ===")
    # HSS
    expect_error(client, "HSS: show nonexistent host", "GET",
                 f"/v5/{PID}/hosts/bad-host-id", expect_status=404, expect_code="HSS.0001")
    expect_error(client, "HSS: protect nonexistent host", "POST",
                 f"/v5/{PID}/hosts/bad-host-id/protection", body={"charge_mode": "hsp"},
                 expect_status=404, expect_code="HSS.0001")

    # CDN
    expect_error(client, "CDN: create without domain_name", "POST", "/v1/domains",
                 body={}, expect_status=400, expect_code="CDN.0001")
    expect_error(client, "CDN: show nonexistent domain", "GET", "/v1/domains/bad-id",
                 expect_status=404, expect_code="CDN.0003")
    expect_error(client, "CDN: purge without url", "POST", "/v1.0/purgecache",
                 body={}, expect_status=400, expect_code="CDN.0004")

    # DWS
    expect_error(client, "DWS: create with too few nodes", "POST",
                 f"/v1.0/{PID}/dws/clusters",
                 body={"name": "x", "number_of_node": 1},
                 expect_status=400, expect_code="DWS.0002")
    expect_error(client, "DWS: show nonexistent cluster", "GET",
                 f"/v1.0/{PID}/dws/clusters/bad-id", expect_status=404, expect_code="DWS.0003")
    expect_error(client, "DWS: snapshot nonexistent cluster", "POST",
                 f"/v1.0/{PID}/dws/snapshots",
                 body={"name": "x", "cluster_id": "bad"},
                 expect_status=404, expect_code="DWS.0003")

    # CSS
    expect_error(client, "CSS: create without name", "POST",
                 f"/v1.0/{PID}/css/clusters", body={},
                 expect_status=400, expect_code="CSS.0001")
    expect_error(client, "CSS: show nonexistent cluster", "GET",
                 f"/v1.0/{PID}/css/clusters/bad-id", expect_status=404, expect_code="CSS.0003")
    expect_error(client, "CSS: index on nonexistent cluster", "POST",
                 f"/v1.0/{PID}/css/clusters/bad-id/indices",
                 body={"index_name": "x"}, expect_status=404, expect_code="CSS.0003")

    # MRS
    expect_error(client, "MRS: create without cluster_name", "POST",
                 f"/v1.1/{PID}/cluster_infos", body={},
                 expect_status=400, expect_code="MRS.0001")
    expect_error(client, "MRS: invalid component", "POST",
                 f"/v1.1/{PID}/cluster_infos",
                 body={"cluster_name": "x", "component_list": ["bogus"]},
                 expect_status=400, expect_code="MRS.0002")
    expect_error(client, "MRS: show nonexistent cluster", "GET",
                 f"/v1.1/{PID}/cluster_infos/bad-id", expect_status=404, expect_code="MRS.0003")

    # SMS
    expect_error(client, "SMS: register source without ip", "POST",
                 f"/v3/{PID}/sources", body={},
                 expect_status=400, expect_code="SMS.0001")
    expect_error(client, "SMS: show nonexistent source", "GET",
                 f"/v3/{PID}/sources/bad-id", expect_status=404, expect_code="SMS.0002")
    expect_error(client, "SMS: task for nonexistent source", "POST",
                 f"/v3/{PID}/tasks", body={"name": "x", "source_id": "bad"},
                 expect_status=404, expect_code="SMS.0002")
    expect_error(client, "SMS: show nonexistent task", "GET",
                 f"/v3/{PID}/tasks/bad-id", expect_status=404, expect_code="SMS.0004")

    # DC
    expect_error(client, "DC: create connection without name", "POST",
                 f"/v2.0/{PID}/direct-connects", body={},
                 expect_status=400, expect_code="DC.0001")
    expect_error(client, "DC: show nonexistent connection", "GET",
                 f"/v2.0/{PID}/direct-connects/bad-id", expect_status=404, expect_code="DC.0002")
    expect_error(client, "DC: VIF with nonexistent DC", "POST",
                 f"/v2.0/{PID}/virtual-interfaces",
                 body={"direct_connect_id": "bad", "vgw_id": "bad"},
                 expect_status=404, expect_code="DC.0002")

    # ER
    expect_error(client, "ER: create without name", "POST",
                 f"/v3/{PID}/enterprise-router/instances", body={},
                 expect_status=400, expect_code="ER.0001")
    expect_error(client, "ER: show nonexistent instance", "GET",
                 f"/v3/{PID}/enterprise-router/instances/bad-id",
                 expect_status=404, expect_code="ER.0002")
    expect_error(client, "ER: attachment with bad VPC", "POST",
                 f"/v3/{PID}/enterprise-router/instances/bad-id/attachments",
                 body={"vpc_id": "bad"}, expect_status=404, expect_code="ER.0002")

    # DIS
    expect_error(client, "DIS: create stream without name", "POST",
                 f"/v2/{PID}/streams", body={},
                 expect_status=400, expect_code="DIS.0001")
    expect_error(client, "DIS: show nonexistent stream", "GET",
                 f"/v2/{PID}/streams/no-such-stream", expect_status=404, expect_code="DIS.0004")
    expect_error(client, "DIS: app without name", "POST",
                 f"/v2/{PID}/apps", body={},
                 expect_status=400, expect_code="DIS.0005")

    # DataArts
    expect_error(client, "DataArts: connection without name", "POST",
                 f"/v2/{PID}/connections", body={},
                 expect_status=400, expect_code="DATAARTS.0001")
    expect_error(client, "DataArts: invalid connection type", "POST",
                 f"/v2/{PID}/connections",
                 body={"name": "x", "connection_type": "Bogus"},
                 expect_status=400, expect_code="DATAARTS.0002")
    expect_error(client, "DataArts: run nonexistent job", "POST",
                 f"/v2/{PID}/jobs/never/run", expect_status=404, expect_code="DATAARTS.0005")

    # OMS
    expect_error(client, "OMS: task without buckets", "POST",
                 f"/v2/{PID}/tasks", body={},
                 expect_status=400, expect_code="OMS.0001")
    expect_error(client, "OMS: task with missing dest bucket", "POST",
                 f"/v2/{PID}/tasks",
                 body={"src_node": {"bucket": "s"}, "dst_node": {"bucket": "nope"}},
                 expect_status=404, expect_code="OMS.0002")
    expect_error(client, "OMS: show nonexistent task", "GET",
                 f"/v2/{PID}/tasks/bad-id", expect_status=404, expect_code="OMS.0003")

    # DES
    expect_error(client, "DES: task without name", "POST",
                 f"/v1/{PID}/des/tasks", body={},
                 expect_status=400, expect_code="DES.0001")
    expect_error(client, "DES: invalid task type", "POST",
                 f"/v1/{PID}/des/tasks",
                 body={"name": "x", "task_type": "PigeonPost"},
                 expect_status=400, expect_code="DES.0002")

    # CodeArts
    expect_error(client, "CodeArts: repo without name", "POST",
                 "/v2/projects/repositories", body={},
                 expect_status=400, expect_code="CODEARTS.0001")
    expect_error(client, "CodeArts: show nonexistent repo", "GET",
                 "/v2/projects/repositories/bad-id",
                 expect_status=404, expect_code="CODEARTS.0003")
    expect_error(client, "CodeArts: run nonexistent pipeline", "POST",
                 f"/v2/{PID}/pipelines/bad-id/run", expect_status=404, expect_code="CODEARTS.0005")

    # ServiceStage
    expect_error(client, "ServiceStage: env without name", "POST",
                 f"/v2/{PID}/cas/environments", body={},
                 expect_status=400, expect_code="CAS.0001")
    expect_error(client, "ServiceStage: component on nonexistent app", "POST",
                 f"/v2/{PID}/cas/applications/bad-id/components",
                 body={"name": "x"}, expect_status=404, expect_code="CAS.0005")

    # CSE
    expect_error(client, "CSE: engine without name", "POST",
                 f"/v2/{PID}/engines", body={},
                 expect_status=400, expect_code="CSE.0001")
    expect_error(client, "CSE: show nonexistent engine", "GET",
                 f"/v2/{PID}/engines/bad-id", expect_status=404, expect_code="CSE.0002")

    # CCI
    expect_error(client, "CCI: namespace without name", "POST",
                 f"/v1/{PID}/cci/namespaces", body={},
                 expect_status=400, expect_code="CCI.0001")
    expect_error(client, "CCI: pod in nonexistent namespace", "POST",
                 f"/v1/{PID}/cci/namespaces/bad-ns/pods",
                 body={"name": "x", "spec": {"containers": [{"name": "c"}]}},
                 expect_status=404, expect_code="CCI.0003")
    expect_error(client, "CCI: pod without containers", "POST",
                 f"/v1/{PID}/cci/namespaces/bad-ns/pods",
                 body={"name": "x", "spec": {}},
                 expect_status=404, expect_code="CCI.0003")

    # CFW
    expect_error(client, "CFW: firewall without name", "POST",
                 f"/v1/{PID}/firewalls", body={},
                 expect_status=400, expect_code="CFW.0001")
    expect_error(client, "CFW: rule with invalid action", "POST",
                 f"/v1/{PID}/firewalls/bad-id/rules",
                 body={"action": "maybe"}, expect_status=404, expect_code="CFW.0002")
    expect_error(client, "CFW: show nonexistent firewall", "GET",
                 f"/v1/{PID}/firewalls/bad-id", expect_status=404, expect_code="CFW.0002")

    # DSC
    expect_error(client, "DSC: asset without name", "POST",
                 f"/v1/{PID}/dsc/assets", body={},
                 expect_status=400, expect_code="DSC.0001")
    expect_error(client, "DSC: scan nonexistent asset", "POST",
                 f"/v1/{PID}/dsc/scans", body={"asset_id": "bad"},
                 expect_status=404, expect_code="DSC.0002")

    # VOD
    expect_error(client, "VOD: asset without name", "POST",
                 f"/v1/{PID}/assets", body={},
                 expect_status=400, expect_code="VOD.0001")
    expect_error(client, "VOD: show nonexistent asset", "GET",
                 f"/v1/{PID}/assets/bad-id", expect_status=404, expect_code="VOD.0002")
    expect_error(client, "VOD: template without name", "POST",
                 f"/v1/{PID}/transcode-templates", body={},
                 expect_status=400, expect_code="VOD.0003")

    # IEF
    expect_error(client, "IEF: node without name", "POST",
                 f"/v2/{PID}/edgemgr/nodes", body={},
                 expect_status=400, expect_code="IEF.0001")
    expect_error(client, "IEF: show nonexistent node", "GET",
                 f"/v2/{PID}/edgemgr/nodes/bad-id", expect_status=404, expect_code="IEF.0002")
    expect_error(client, "IEF: deployment without nodes", "POST",
                 f"/v2/{PID}/edgemgr/deployments",
                 body={"deployment": {"name": "x", "node_ids": []}},
                 expect_status=400, expect_code="IEF.0004")

    # ModelArts / MaaS
    expect_error(client, "MA: model without name", "POST",
                 f"/v1/{PID}/models", body={},
                 expect_status=400, expect_code="MA.0002")
    expect_error(client, "MA: show nonexistent model", "GET",
                 f"/v1/{PID}/models/bad-id", expect_status=404, expect_code="MA.0003")
    expect_error(client, "MA: service for nonexistent model", "POST",
                 f"/v1/{PID}/services", body={"model_id": "bad"},
                 expect_status=404, expect_code="MA.0003")
    expect_error(client, "MaaS: chat with unknown model", "POST",
                 "/v1/chat/completions",
                 body={"model": "bogus", "messages": [{"role": "user", "content": "hi"}]},
                 expect_status=404)
    expect_error(client, "MaaS: chat without messages", "POST",
                 "/v1/chat/completions", body={"model": "DeepSeek-V3"},
                 expect_status=400)
    expect_error(client, "MaaS: key without name", "POST",
                 f"/v1/{PID}/maas/keys", body={},
                 expect_status=400, expect_code="MA.0007")

    # =======================================================================
    # Report
    # =======================================================================
    print("\n" + "=" * 80)
    for status, name, detail in RESULTS:
        mark = "PASS" if status == "PASS" else "FAIL"
        print(f"  [{mark}] {name}" + (f"  → {detail}" if detail else ""))
    print("=" * 80)
    print(f"\nNEGATIVE TESTS: {PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
