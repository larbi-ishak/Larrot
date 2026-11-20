"""VPC: vpcs, subnets, EIPs, ports, security groups."""

import time
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import vpc_error
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _vpc_json(v):
    return {"id": v["id"], "name": v["name"], "description": v["description"],
            "cidr": v["cidr"], "status": v["status"],
            "tenant_id": v["project_id"], "enterprise_project_id": "0",
            "created_at": v["created_at"], "updated_at": v["updated_at"]}


def _subnet_json(s):
    dns = [s["primary_dns"]]
    if s["secondary_dns"]:
        dns.append(s["secondary_dns"])
    return {"id": s["id"], "name": s["name"], "description": s["description"],
            "cidr": s["cidr"], "gateway_ip": s["gateway_ip"],
            "ipv6_enable": False, "dhcp_enable": s["dhcp_enable"],
            "primary_dns": s["primary_dns"], "secondary_dns": s["secondary_dns"],
            "dnsList": dns, "availability_zone": s["availability_zone"],
            "vpc_id": s["vpc_id"], "status": s["status"],
            "tenant_id": s["project_id"], "enterprise_project_id": "0",
            "neutron_network_id": s["id"], "neutron_subnet_id": s["id"],
            "available_ip_address_count": 253, "extra_dhcp_opts": [],
            "created_at": s["created_at"], "updated_at": s["updated_at"]}


def _eip_create_json(e):
    return {"id": e["id"], "alias": e["alias"], "public_border_group": "center",
            "status": e["status"], "type": e["ip_type"],
            "public_ip_address": e["public_ip_address"], "tenant_id": e["tenant_id"],
            "ip_version": e["ip_version"], "create_time": e["create_time"],
            "bandwidth_size": 0, "enterprise_project_id": e["enterprise_project_id"]}


def _eip_json(e):
    v = {"id": e["id"], "alias": e["alias"], "status": e["status"],
         "profile": {}, "type": e["ip_type"],
         "public_ip_address": e["public_ip_address"],
         "public_border_group": "center",
         "tenant_id": e["tenant_id"], "create_time": e["create_time"],
         "bandwidth_size": e["bandwidth_size"], "bandwidth_id": e["bandwidth_id"],
         "bandwidth_name": e["bandwidth_name"],
         "bandwidth_share_type": e["bandwidth_share_type"],
         "ip_version": e["ip_version"],
         "enterprise_project_id": e["enterprise_project_id"], "tags": []}
    if e.get("port_id"):
        v["port_id"] = e["port_id"]
    if e.get("private_ip_address"):
        v["private_ip_address"] = e["private_ip_address"]
    return v


def _sg_json(g):
    return {"id": g["id"], "name": g["name"], "description": g["description"],
            "vpc_id": g["vpc_id"], "enterprise_project_id": "0",
            "security_group_rules": [_rule_json(r) for r in g["rules"]]}


def _rule_json(r):
    return {"id": r["id"], "security_group_id": r["security_group_id"],
            "direction": r["direction"], "ethertype": r["ethertype"],
            "protocol": r["protocol"], "port_range_min": r["port_range_min"],
            "port_range_max": r["port_range_max"],
            "remote_ip_prefix": r["remote_ip_prefix"],
            "remote_group_id": r["remote_group_id"],
            "remote_address_group_id": r["remote_address_group_id"],
            "description": r["description"], "tenant_id": r["tenant_id"]}


# ---------------------------------------------------------------------------
# VPCs
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/vpcs")
async def list_vpcs(request: Request, pid: str):
    state = request.app.state.sim
    return {"vpcs": [_vpc_json(v) for v in state.vpcs.values() if v["project_id"] == pid]}


@router.get("/v1/{pid}/vpcs/{vpc_id}")
async def show_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = state.vpcs.get(vpc_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0003", "VPC does not exist."), status_code=404)
    return {"vpc": _vpc_json(v)}


@router.post("/v1/{pid}/vpcs")
async def create_vpc(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    now = now_millis()
    vpc = {"id": new_id(), "name": body["vpc"]["name"],
           "description": body["vpc"].get("description", ""),
           "cidr": body["vpc"].get("cidr", "192.168.0.0/16"),
           "status": "OK", "created_at": now, "updated_at": now, "project_id": pid}
    state.vpcs[vpc["id"]] = vpc
    return {"vpc": _vpc_json(vpc)}


@router.put("/v1/{pid}/vpcs/{vpc_id}")
async def update_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = state.vpcs.get(vpc_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0003", "VPC does not exist."), status_code=404)
    body = await request.json()
    for k in ("name", "description", "cidr"):
        if k in body["vpc"]:
            v[k] = body["vpc"][k]
    v["updated_at"] = now_millis()
    return {"vpc": _vpc_json(v)}


@router.delete("/v1/{pid}/vpcs/{vpc_id}")
async def delete_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = state.vpcs.get(vpc_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0003", "VPC does not exist."), status_code=404)
    if any(s["vpc_id"] == vpc_id for s in state.subnets.values()):
        return JSONResponse(vpc_error("VPC.0101", "Invalid VPC parameter values."), status_code=400)
    del state.vpcs[vpc_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Subnets
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/subnets")
async def list_subnets(request: Request, pid: str):
    state = request.app.state.sim
    return {"subnets": [_subnet_json(s) for s in state.subnets.values() if s["project_id"] == pid]}


@router.get("/v1/{pid}/subnets/{subnet_id}")
async def show_subnet(request: Request, pid: str, subnet_id: str):
    state = request.app.state.sim
    s = state.subnets.get(subnet_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0201", "Subnet is not exist."), status_code=404)
    return {"subnet": _subnet_json(s)}


@router.post("/v1/{pid}/subnets")
async def create_subnet(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["subnet"]
    vpc = state.vpcs.get(spec.get("vpc_id", ""))
    if not vpc or vpc["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0003", "VPC does not exist."), status_code=404)
    now = now_millis()
    subnet = {"id": new_id(), "name": spec["name"],
              "description": spec.get("description", ""),
              "cidr": spec.get("cidr", "192.168.1.0/24"),
              "gateway_ip": spec.get("gateway_ip", "192.168.1.1"),
              "dhcp_enable": spec.get("dhcp_enable", True),
              "primary_dns": spec.get("primary_dns", "100.125.0.41"),
              "secondary_dns": spec.get("secondary_dns", ""),
              "availability_zone": spec.get("availability_zone", ""),
              "vpc_id": spec["vpc_id"], "status": "ACTIVE",
              "created_at": now, "updated_at": now, "project_id": pid}
    state.subnets[subnet["id"]] = subnet
    return {"subnet": _subnet_json(subnet)}


@router.put("/v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}")
async def update_subnet(request: Request, pid: str, vpc_id: str, subnet_id: str):
    state = request.app.state.sim
    s = state.subnets.get(subnet_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0201", "Subnet is not exist."), status_code=404)
    body = await request.json()
    spec = body["subnet"]
    for k in ("name", "primary_dns", "secondary_dns"):
        if k in spec:
            s[k] = spec[k]
    if "dhcp_enable" in spec:
        s["dhcp_enable"] = spec["dhcp_enable"]
    s["updated_at"] = now_millis()
    return {"subnet": _subnet_json(s)}


@router.delete("/v1/{pid}/subnets/{subnet_id}")
@router.delete("/v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}")
async def delete_subnet(request: Request, pid: str, subnet_id: str, vpc_id: str = ""):
    state = request.app.state.sim
    s = state.subnets.get(subnet_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0201", "Subnet is not exist."), status_code=404)
    del state.subnets[subnet_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# EIPs
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/publicips")
async def create_eip(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    n = len(state.eips)
    eip = {
        "id": new_id(), "alias": body["publicip"].get("alias", ""),
        "status": "PENDING_CREATE",
        "ip_type": body["publicip"].get("type", "5_bgp"),
        "public_ip_address": body["publicip"].get("ip_address") or f"119.3.{n // 255}.{10 + n % 240}",
        "ip_version": body["publicip"].get("ip_version", 4),
        "tenant_id": pid,
        "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "bandwidth_id": new_id(),
        "bandwidth_name": body["bandwidth"].get("name", ""),
        "bandwidth_size": body["bandwidth"].get("size", 5),
        "bandwidth_share_type": body["bandwidth"].get("share_type", "PER"),
        "charge_mode": body["bandwidth"].get("charge_mode", "traffic"),
        "port_id": None, "private_ip_address": None,
        "enterprise_project_id": "0", "project_id": pid,
    }
    state.eips[eip["id"]] = eip

    async def _flip():
        e = state.eips.get(eip["id"])
        if e and e["status"] == "PENDING_CREATE":
            e["status"] = "DOWN"

    import asyncio
    asyncio.get_event_loop().create_task(_delay_flip(_flip, 0.8))
    return {"publicip": _eip_create_json(eip)}


async def _delay_flip(fn, delay):
    import asyncio
    await asyncio.sleep(delay)
    await fn()


@router.get("/v1/{pid}/publicips")
async def list_eips(request: Request, pid: str):
    state = request.app.state.sim
    return {"publicips": [_eip_json(e) for e in state.eips.values() if e["project_id"] == pid]}


@router.get("/v1/{pid}/publicips/{eip_id}")
async def show_eip(request: Request, pid: str, eip_id: str):
    state = request.app.state.sim
    e = state.eips.get(eip_id)
    if not e or e["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0504", "Floating IP could not be found."), status_code=404)
    return {"publicip": _eip_json(e)}


@router.put("/v1/{pid}/publicips/{eip_id}")
async def update_eip(request: Request, pid: str, eip_id: str):
    state = request.app.state.sim
    e = state.eips.get(eip_id)
    if not e or e["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0504", "Floating IP could not be found."), status_code=404)
    body = await request.json()
    port_id = body["publicip"].get("port_id")

    if port_id:
        port = state.ports.get(port_id)
        if not port or port["project_id"] != pid:
            return JSONResponse(vpc_error("VPC.0501", "Port id is invalid."), status_code=400)
        if any(other["port_id"] == port_id for other in state.eips.values() if other["id"] != eip_id):
            return JSONResponse(vpc_error("VPC.0511", "The port has already been bound with an EIP."), status_code=409)
        e["port_id"] = port_id
        e["private_ip_address"] = port["ip_address"]
        e["status"] = "ACTIVE"
    else:
        e["port_id"] = None
        e["private_ip_address"] = None
        e["status"] = "DOWN"

    if "alias" in body["publicip"]:
        e["alias"] = body["publicip"]["alias"]
    return {"publicip": _eip_json(e)}


@router.delete("/v1/{pid}/publicips/{eip_id}")
async def delete_eip(request: Request, pid: str, eip_id: str):
    state = request.app.state.sim
    e = state.eips.get(eip_id)
    if not e or e["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0504", "Floating IP could not be found."), status_code=404)
    if e["port_id"]:
        return JSONResponse(vpc_error("VPC.0517", "EIP is bound to a port. Unbind it first."), status_code=409)
    del state.eips[eip_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/ports")
async def list_ports(request: Request, pid: str):
    state = request.app.state.sim
    device_id = request.query_params.get("device_id")
    ports = [p for p in state.ports.values() if p["project_id"] == pid]
    if device_id:
        ports = [p for p in ports if p["device_id"] == device_id]
    return {"ports": [{
        "id": p["id"], "name": "",
        "status": "ACTIVE" if p["device_id"] else "DOWN",
        "admin_state_up": True,
        "fixed_ips": [{"subnet_id": p["subnet_id"], "ip_address": p["ip_address"]}],
        "dns_name": "", "mac_address": p["mac_address"],
        "network_id": p["network_id"], "tenant_id": p["project_id"],
        "device_id": p["device_id"],
        "device_owner": "compute:None" if p["device_id"] else "",
        "security_groups": [], "extra_dhcp_opts": [],
        "allowed_address_pairs": [], "binding:vnic_type": "normal",
        "enable_efi": False,
    } for p in ports]}


# ---------------------------------------------------------------------------
# Security groups
# ---------------------------------------------------------------------------

def _default_rules(sg_id, tenant):
    return [
        {"id": new_id(), "security_group_id": sg_id, "direction": "ingress",
         "ethertype": "IPv4", "protocol": None, "port_range_min": None,
         "port_range_max": None, "remote_ip_prefix": None,
         "remote_group_id": sg_id, "remote_address_group_id": None,
         "description": "", "tenant_id": tenant},
        {"id": new_id(), "security_group_id": sg_id, "direction": "ingress",
         "ethertype": "IPv6", "protocol": None, "port_range_min": None,
         "port_range_max": None, "remote_ip_prefix": None,
         "remote_group_id": sg_id, "remote_address_group_id": None,
         "description": "", "tenant_id": tenant},
        {"id": new_id(), "security_group_id": sg_id, "direction": "egress",
         "ethertype": "IPv4", "protocol": None, "port_range_min": None,
         "port_range_max": None, "remote_ip_prefix": None,
         "remote_group_id": None, "remote_address_group_id": None,
         "description": "", "tenant_id": tenant},
        {"id": new_id(), "security_group_id": sg_id, "direction": "egress",
         "ethertype": "IPv6", "protocol": None, "port_range_min": None,
         "port_range_max": None, "remote_ip_prefix": None,
         "remote_group_id": None, "remote_address_group_id": None,
         "description": "", "tenant_id": tenant},
    ]


@router.post("/v1/{pid}/security-groups")
async def create_sg(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    sg_id = new_id()
    sg = {"id": sg_id, "name": body["security_group"]["name"],
          "description": body["security_group"].get("description", ""),
          "vpc_id": body["security_group"].get("vpc_id", ""),
          "rules": _default_rules(sg_id, pid), "project_id": pid}
    state.security_groups[sg_id] = sg
    return JSONResponse({"security_group": _sg_json(sg)}, status_code=201)


@router.get("/v1/{pid}/security-groups")
async def list_sgs(request: Request, pid: str):
    state = request.app.state.sim
    return {"security_groups": [_sg_json(g) for g in state.security_groups.values()
                                 if g["project_id"] == pid]}


@router.get("/v1/{pid}/security-groups/{sg_id}")
async def show_sg(request: Request, pid: str, sg_id: str):
    state = request.app.state.sim
    g = state.security_groups.get(sg_id)
    if not g or g["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0603", "Security group does not exist."), status_code=404)
    return {"security_group": _sg_json(g)}


@router.delete("/v1/{pid}/security-groups/{sg_id}")
async def delete_sg(request: Request, pid: str, sg_id: str):
    state = request.app.state.sim
    g = state.security_groups.get(sg_id)
    if not g or g["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0603", "Security group does not exist."), status_code=404)
    del state.security_groups[sg_id]
    return Response(status_code=204)


@router.post("/v1/{pid}/security-group-rules")
async def create_sg_rule(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["security_group_rule"]
    sg = state.security_groups.get(spec["security_group_id"])
    if not sg or sg["project_id"] != pid:
        return JSONResponse(vpc_error("VPC.0603", "Security group does not exist."), status_code=404)

    candidate = {"id": new_id(), "security_group_id": sg["id"],
                 "direction": spec["direction"],
                 "ethertype": spec.get("ethertype", "IPv4"),
                 "protocol": spec.get("protocol"),
                 "port_range_min": spec.get("port_range_min"),
                 "port_range_max": spec.get("port_range_max"),
                 "remote_ip_prefix": spec.get("remote_ip_prefix"),
                 "remote_group_id": spec.get("remote_group_id"),
                 "remote_address_group_id": spec.get("remote_address_group_id"),
                 "description": spec.get("description", ""), "tenant_id": pid}

    def same(r):
        return (r["security_group_id"] == candidate["security_group_id"]
                and r["direction"] == candidate["direction"]
                and r["ethertype"] == candidate["ethertype"]
                and r["protocol"] == candidate["protocol"]
                and r["port_range_min"] == candidate["port_range_min"]
                and r["port_range_max"] == candidate["port_range_max"]
                and r["remote_ip_prefix"] == candidate["remote_ip_prefix"]
                and r["remote_group_id"] == candidate["remote_group_id"])

    if any(same(r) for r in sg["rules"]):
        return JSONResponse(vpc_error("SecurityGroupRuleExists",
            "Security group rule already exists."), status_code=409)

    sg["rules"].append(candidate)
    return JSONResponse({"security_group_rule": _rule_json(candidate)}, status_code=201)


@router.get("/v1/{pid}/security-group-rules")
async def list_sg_rules(request: Request, pid: str):
    state = request.app.state.sim
    rules = []
    for g in state.security_groups.values():
        if g["project_id"] == pid:
            rules.extend(g["rules"])
    return {"security_group_rules": [_rule_json(r) for r in rules]}


# ---------------------------------------------------------------------------
# Bandwidths (v2.0)
# ---------------------------------------------------------------------------

@router.get("/v2.0/{pid}/bandwidths")
async def list_bandwidths(request: Request, pid: str):
    state = request.app.state.sim
    items = []
    for e in state.eips.values():
        if e["project_id"] != pid:
            continue
        items.append({
            "id": e["bandwidth_id"], "name": e["bandwidth_name"],
            "size": e["bandwidth_size"], "share_type": e["bandwidth_share_type"],
            "charge_mode": e["charge_mode"], "status": "NORMAL",
            "public_border_group": "center", "bandwidth_type": "bgp",
            "enable_bandwidth_rules": False, "rule_quota": 0,
            "bandwidth_rules": [],
            "publicip_info": [{"publicip_id": e["id"],
                              "publicip_address": e["public_ip_address"],
                              "ip_version": e["ip_version"],
                              "publicip_type": e["ip_type"]}],
            "tenant_id": pid, "enterprise_project_id": "0",
            "created_at": e["create_time"], "updated_at": e["create_time"],
            "billing_info": None,
        })
    return {"bandwidths": items, "count": len(items)}


@router.put("/v2.0/{pid}/bandwidths/{bandwidth_id}")
async def resize_bandwidth(request: Request, pid: str, bandwidth_id: str):
    state = request.app.state.sim
    e = next((e for e in state.eips.values()
              if e["bandwidth_id"] == bandwidth_id and e["project_id"] == pid), None)
    if not e:
        return JSONResponse(vpc_error("VPC.0504", "Bandwidth not found."), status_code=404)
    body = await request.json()
    size = body["bandwidth"].get("size")
    if size and not (1 <= size <= 2000):
        return JSONResponse(vpc_error("VPC.0501", "Bandwidth size is invalid."), status_code=400)
    if size:
        e["bandwidth_size"] = size
    if "name" in body["bandwidth"]:
        e["bandwidth_name"] = body["bandwidth"]["name"]
    return {"bandwidth": {"id": e["bandwidth_id"], "name": e["bandwidth_name"],
                          "size": e["bandwidth_size"], "status": "NORMAL"}}
