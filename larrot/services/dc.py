"""DC (Direct Connect): connections, virtual gateways, virtual interfaces.

Real routes: /v2.0/{project_id}/direct-connects, /v2.0/{project_id}/virtual-gateways,
/v2.0/{project_id}/virtual-interfaces.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _conn_json(c):
    return {
        "id": c["id"], "name": c["name"], "status": c["status"],
        "port_type": c["port_type"], "bandwidth": c["bandwidth"],
        "location": c["location"], "provider": " Huawei",
        "type": "standard", "description": c.get("description", ""),
        "apply_time": c["created_at"], "create_time": c["created_at"],
        "enterprise_project_id": "0",
    }


@router.post("/v2.0/{pid}/direct-connects")
async def create_connection(request: Request, pid: str):
    """Create a direct connect: the physical line into Huawei's network (async)."""
    s = request.app.state.sim
    if not hasattr(s, "dc_connections"):
        s.dc_connections = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "DC.0001", "error_msg": "name is required"},
                            status_code=400)
    cid = new_id()
    s.dc_connections[cid] = {
        "id": cid, "name": name, "status": "BUILD",
        "port_type": body.get("port_type", "1G"),
        "bandwidth": body.get("bandwidth", 1000),
        "location": body.get("location", "DC-01"),
        "description": body.get("description", ""),
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        c = s.dc_connections.get(cid)
        if c:
            c["status"] = "ACTIVE"
        return None

    await s.jobs.submit("createDirectConnect", {"connection_id": cid}, effect)
    return {"direct_connect": _conn_json(s.dc_connections[cid])}


@router.get("/v2.0/{pid}/direct-connects")
async def list_connections(request: Request, pid: str):
    """List direct connects."""
    s = request.app.state.sim
    conns = [c for c in getattr(s, "dc_connections", {}).values()
             if c["project_id"] == pid]
    return {"direct_connects": [_conn_json(c) for c in conns], "total": len(conns)}


@router.get("/v2.0/{pid}/direct-connects/{conn_id}")
async def show_connection(request: Request, pid: str, conn_id: str):
    """Show one direct connect: bandwidth, port type, and status."""
    s = request.app.state.sim
    c = getattr(s, "dc_connections", {}).get(conn_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DC.0002", "error_msg": "direct connect not found"},
                            status_code=404)
    return {"direct_connect": _conn_json(c)}


@router.delete("/v2.0/{pid}/direct-connects/{conn_id}")
async def delete_connection(request: Request, pid: str, conn_id: str):
    """Delete a direct connect."""
    s = request.app.state.sim
    c = getattr(s, "dc_connections", {}).get(conn_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DC.0002", "error_msg": "direct connect not found"},
                            status_code=404)
    del s.dc_connections[conn_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# virtual gateways (VPC side of the connection)
# ---------------------------------------------------------------------------

@router.post("/v2.0/{pid}/virtual-gateways")
async def create_vgw(request: Request, pid: str):
    """Create a virtual gateway: the VPC-side endpoint of a direct connect."""
    s = request.app.state.sim
    if not hasattr(s, "dc_virtual_gateways"):
        s.dc_virtual_gateways = {}
    body = await request.json()
    vpc_id = body.get("vpc_id", "")
    if not vpc_id:
        return JSONResponse({"error_code": "DC.0003", "error_msg": "vpc_id is required"},
                            status_code=400)
    gid = new_id()
    s.dc_virtual_gateways[gid] = {
        "id": gid, "name": body.get("name", f"vgw-{gid[:8]}"),
        "vpc_id": vpc_id, "local_ep_group": body.get("local_ep_group", []),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"virtual_gateway": s.dc_virtual_gateways[gid]}


@router.get("/v2.0/{pid}/virtual-gateways")
async def list_vgws(request: Request, pid: str):
    """List virtual gateways."""
    s = request.app.state.sim
    vgws = [g for g in getattr(s, "dc_virtual_gateways", {}).values()
            if g["project_id"] == pid]
    return {"virtual_gateways": vgws, "total": len(vgws)}


@router.delete("/v2.0/{pid}/virtual-gateways/{vgw_id}")
async def delete_vgw(request: Request, pid: str, vgw_id: str):
    """Delete a virtual gateway."""
    s = request.app.state.sim
    if vgw_id not in getattr(s, "dc_virtual_gateways", {}):
        return JSONResponse({"error_code": "DC.0004", "error_msg": "virtual gateway not found"},
                            status_code=404)
    del s.dc_virtual_gateways[vgw_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# virtual interfaces (the BGP peering between DC and VGW)
# ---------------------------------------------------------------------------

@router.post("/v2.0/{pid}/virtual-interfaces")
async def create_vif(request: Request, pid: str):
    """Create a virtual interface: the logical connection over a direct connect."""
    s = request.app.state.sim
    if not hasattr(s, "dc_virtual_interfaces"):
        s.dc_virtual_interfaces = {}
    body = await request.json()
    direct_connect_id = body.get("direct_connect_id", "")
    vgw_id = body.get("vgw_id", body.get("virtual_gateway_id", ""))
    if direct_connect_id not in getattr(s, "dc_connections", {}):
        return JSONResponse({"error_code": "DC.0002",
                             "error_msg": "direct connect not found"}, status_code=404)
    if vgw_id not in getattr(s, "dc_virtual_gateways", {}):
        return JSONResponse({"error_code": "DC.0004",
                             "error_msg": "virtual gateway not found"}, status_code=404)
    vid = new_id()
    s.dc_virtual_interfaces[vid] = {
        "id": vid, "name": body.get("name", f"vif-{vid[:8]}"),
        "direct_connect_id": direct_connect_id, "vgw_id": vgw_id,
        "type": body.get("type", "private"),
        "service_ep_group": body.get("service_ep_group", []),
        "status": "ACTIVE", "created_at": now_millis(), "project_id": pid,
    }
    return {"virtual_interface": s.dc_virtual_interfaces[vid]}


@router.get("/v2.0/{pid}/virtual-interfaces")
async def list_vifs(request: Request, pid: str):
    """List virtual interfaces."""
    s = request.app.state.sim
    vifs = [v for v in getattr(s, "dc_virtual_interfaces", {}).values()
            if v["project_id"] == pid]
    return {"virtual_interfaces": vifs, "total": len(vifs)}


@router.delete("/v2.0/{pid}/virtual-interfaces/{vif_id}")
async def delete_vif(request: Request, pid: str, vif_id: str):
    """Delete a virtual interface."""
    s = request.app.state.sim
    if vif_id not in getattr(s, "dc_virtual_interfaces", {}):
        return JSONResponse({"error_code": "DC.0005",
                             "error_msg": "virtual interface not found"}, status_code=404)
    del s.dc_virtual_interfaces[vif_id]
    return Response(status_code=204)
