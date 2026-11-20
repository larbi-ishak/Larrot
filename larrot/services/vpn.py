"""VPN: IPsec and SSL VPN gateways, connections."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()


@router.post("/v5/{pid}/vpn-gateways")
async def create_vpn_gateway(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vpn_gateways"): s.vpn_gateways = {}
    body = await request.json()
    gid = new_id()
    s.vpn_gateways[gid] = {
        "id": gid, "name": body.get("name", f"vpn-{gid[:8]}"),
        "vpc_id": body.get("vpc_id", ""), "flavor": body.get("flavor", "Basic"),
        "availability_zone": body.get("availability_zone", "az1"),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
        "public_ip": {"id": new_id(), "ip_address": f"100.64.0.{10 + len(s.vpn_gateways)}"},
        "local_subnets": body.get("local_subnets", []),
    }
    return {"vpn_gateway": s.vpn_gateways[gid]}


@router.get("/v5/{pid}/vpn-gateways")
async def list_vpn_gateways(request: Request, pid: str):
    s = request.app.state.sim
    gateways = [g for g in getattr(s, "vpn_gateways", {}).values() if g["project_id"] == pid]
    return {"vpn_gateways": gateways, "total": len(gateways)}


@router.delete("/v5/{pid}/vpn-gateways/{gateway_id}")
async def delete_vpn_gateway(request: Request, pid: str, gateway_id: str):
    s = request.app.state.sim
    if gateway_id not in getattr(s, "vpn_gateways", {}):
        return JSONResponse({"error_msg": "VPN gateway not found", "error_code": "VPN.0001"}, status_code=404)
    del s.vpn_gateways[gateway_id]
    return Response(status_code=204)


@router.post("/v5/{pid}/vpn-connections")
async def create_vpn_connection(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vpn_connections"): s.vpn_connections = {}
    body = await request.json()
    cid = new_id()
    s.vpn_connections[cid] = {
        "id": cid, "name": body.get("name", f"conn-{cid[:8]}"),
        "vgw_id": body.get("vgw_id", ""), "peer_subnets": body.get("peer_subnets", []),
        "psk": body.get("psk", "changeme"),
        "ike_policy": body.get("ike_policy", {"encryption_algorithm": "aes-256", "dh_group": 14}),
        "ipsec_policy": body.get("ipsec_policy", {"encryption_algorithm": "aes-256"}),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"vpn_connection": s.vpn_connections[cid]}


@router.get("/v5/{pid}/vpn-connections")
async def list_vpn_connections(request: Request, pid: str):
    s = request.app.state.sim
    conns = [c for c in getattr(s, "vpn_connections", {}).values() if c["project_id"] == pid]
    return {"vpn_connections": conns, "total": len(conns)}


@router.get("/v5/{pid}/vpn-gateways/{gateway_id}")
async def show_vpn_gateway(request: Request, pid: str, gateway_id: str):
    s = request.app.state.sim
    g = getattr(s, "vpn_gateways", {}).get(gateway_id)
    if not g or g.get("project_id") != pid:
        return JSONResponse({"error_msg": "VPN gateway not found",
                             "error_code": "VPN.0001"}, status_code=404)
    return {"vpn_gateway": g}


@router.delete("/v5/{pid}/vpn-connections/{connection_id}")
async def delete_vpn_connection(request: Request, pid: str, connection_id: str):
    s = request.app.state.sim
    c = getattr(s, "vpn_connections", {}).get(connection_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error_msg": "VPN connection not found",
                             "error_code": "VPN.0002"}, status_code=404)
    del s.vpn_connections[connection_id]
    return Response(status_code=204)
