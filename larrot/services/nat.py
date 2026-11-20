"""NAT Gateway: gateways, SNAT rules, DNAT rules."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _gw_json(g):
    return {
        "id": g["id"], "name": g["name"], "description": g.get("description", ""),
        "router_id": g.get("router_id", ""), "internal_network_id": g.get("internal_network_id", ""),
        "status": g.get("status", "ACTIVE"), "admin_state_up": True,
        "spec": g.get("spec", "1"), "created_at": g["created_at"],
        "enterprise_project_id": "0",
    }


@router.post("/v2.0/{pid}/nat_gateways")
async def create_nat_gateway(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "nat_gateways"): s.nat_gateways = {}
    if not hasattr(s, "nat_snat_rules"): s.nat_snat_rules = {}
    if not hasattr(s, "nat_dnat_rules"): s.nat_dnat_rules = {}
    body = await request.json()
    gid = new_id()
    s.nat_gateways[gid] = {
        "id": gid, "name": body.get("name", f"nat-{gid[:8]}"),
        "description": body.get("description", ""),
        "router_id": body.get("router_id", ""), "spec": body.get("spec", "1"),
        "internal_network_id": body.get("internal_network_id", ""),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"nat_gateway": _gw_json(s.nat_gateways[gid])}


@router.get("/v2.0/{pid}/nat_gateways")
async def list_nat_gateways(request: Request, pid: str):
    s = request.app.state.sim
    gateways = [g for g in getattr(s, "nat_gateways", {}).values() if g["project_id"] == pid]
    return {"nat_gateways": [_gw_json(g) for g in gateways], "total": len(gateways)}


@router.get("/v2.0/{pid}/nat_gateways/{gateway_id}")
async def show_nat_gateway(request: Request, pid: str, gateway_id: str):
    s = request.app.state.sim
    g = getattr(s, "nat_gateways", {}).get(gateway_id)
    if not g or g["project_id"] != pid:
        return JSONResponse({"error_msg": "NAT gateway not found", "error_code": "NAT.0001"}, status_code=404)
    return {"nat_gateway": _gw_json(g)}


@router.delete("/v2.0/{pid}/nat_gateways/{gateway_id}")
async def delete_nat_gateway(request: Request, pid: str, gateway_id: str):
    s = request.app.state.sim
    if gateway_id not in getattr(s, "nat_gateways", {}):
        return JSONResponse({"error_msg": "NAT gateway not found", "error_code": "NAT.0001"}, status_code=404)
    del s.nat_gateways[gateway_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# SNAT rules (outbound: private → public)
# ---------------------------------------------------------------------------

@router.post("/v2.0/{pid}/snat_rules")
async def create_snat_rule(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "nat_snat_rules"): s.nat_snat_rules = {}
    body = await request.json()
    rid = new_id()
    s.nat_snat_rules[rid] = {
        "id": rid, "nat_gateway_id": body.get("nat_gateway_id", ""),
        "cidr": body.get("cidr", ""), "source_type": body.get("source_type", 0),
        "floating_ip_id": body.get("floating_ip_id", ""),
        "public_ip_address": body.get("floating_ip_address", ""),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"snat_rule": s.nat_snat_rules[rid]}


@router.get("/v2.0/{pid}/snat_rules")
async def list_snat_rules(request: Request, pid: str):
    s = request.app.state.sim
    rules = [r for r in getattr(s, "nat_snat_rules", {}).values() if r["project_id"] == pid]
    return {"snat_rules": rules, "total": len(rules)}


@router.delete("/v2.0/{pid}/snat_rules/{rule_id}")
async def delete_snat_rule(request: Request, pid: str, rule_id: str):
    s = request.app.state.sim
    if rule_id not in getattr(s, "nat_snat_rules", {}):
        return JSONResponse({"error_msg": "SNAT rule not found", "error_code": "NAT.0002"}, status_code=404)
    del s.nat_snat_rules[rule_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# DNAT rules (inbound: public port → private IP:port)
# ---------------------------------------------------------------------------

@router.post("/v2.0/{pid}/dnat_rules")
async def create_dnat_rule(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "nat_dnat_rules"): s.nat_dnat_rules = {}
    body = await request.json()
    rid = new_id()
    s.nat_dnat_rules[rid] = {
        "id": rid, "nat_gateway_id": body.get("nat_gateway_id", ""),
        "port_id": body.get("port_id", ""),
        "private_ip": body.get("private_ip", ""),
        "internal_service_port": body.get("internal_service_port", 80),
        "protocol": body.get("protocol", "tcp"),
        "floating_ip_id": body.get("floating_ip_id", ""),
        "public_ip_address": body.get("floating_ip_address", ""),
        "external_service_port": body.get("external_service_port", 8080),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"dnat_rule": s.nat_dnat_rules[rid]}


@router.get("/v2.0/{pid}/dnat_rules")
async def list_dnat_rules(request: Request, pid: str):
    s = request.app.state.sim
    rules = [r for r in getattr(s, "nat_dnat_rules", {}).values() if r["project_id"] == pid]
    return {"dnat_rules": rules, "total": len(rules)}


@router.delete("/v2.0/{pid}/dnat_rules/{rule_id}")
async def delete_dnat_rule(request: Request, pid: str, rule_id: str):
    s = request.app.state.sim
    if rule_id not in getattr(s, "nat_dnat_rules", {}):
        return JSONResponse({"error_msg": "DNAT rule not found", "error_code": "NAT.0003"}, status_code=404)
    del s.nat_dnat_rules[rule_id]
    return Response(status_code=204)
