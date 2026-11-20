"""VPC Routes: route tables and routes."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/vpc/routetables")
async def create_route_table(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vpc_route_tables"): s.vpc_route_tables = {}
    body = await request.json()
    rt_id = new_id()
    s.vpc_route_tables[rt_id] = {
        "id": rt_id, "name": body.get("name", f"rt-{rt_id[:8]}"),
        "vpc_id": body.get("vpc_id", ""), "routes": [],
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"routetable": s.vpc_route_tables[rt_id]}


@router.get("/v1/{pid}/vpc/routetables")
async def list_route_tables(request: Request, pid: str):
    s = request.app.state.sim
    tables = [rt for rt in getattr(s, "vpc_route_tables", {}).values() if rt["project_id"] == pid]
    return {"routetables": tables, "count": len(tables)}


@router.get("/v1/{pid}/vpc/routetables/{rt_id}")
async def show_route_table(request: Request, pid: str, rt_id: str):
    s = request.app.state.sim
    rt = getattr(s, "vpc_route_tables", {}).get(rt_id)
    if not rt or rt["project_id"] != pid:
        return JSONResponse({"error_msg": "Route table not found", "error_code": "VPC.0401"}, status_code=404)
    return {"routetable": rt}


@router.put("/v1/{pid}/vpc/routetables/{rt_id}")
async def update_route_table(request: Request, pid: str, rt_id: str):
    s = request.app.state.sim
    rt = getattr(s, "vpc_route_tables", {}).get(rt_id)
    if not rt or rt.get("project_id") != pid:
        return JSONResponse({"error_msg": "Route table not found",
                             "error_code": "VPC.0401"}, status_code=404)
    body = await request.json()
    if "name" in body and body["name"]:
        rt["name"] = body["name"]
    return {"routetable": rt}


@router.delete("/v1/{pid}/vpc/routetables/{rt_id}")
async def delete_route_table(request: Request, pid: str, rt_id: str):
    s = request.app.state.sim
    if rt_id not in getattr(s, "vpc_route_tables", {}):
        return JSONResponse({"error_msg": "Route table not found", "error_code": "VPC.0401"}, status_code=404)
    del s.vpc_route_tables[rt_id]
    return Response(status_code=204)


@router.post("/v1/{pid}/vpc/routetables/{rt_id}/routes")
async def add_route(request: Request, pid: str, rt_id: str):
    s = request.app.state.sim
    rt = getattr(s, "vpc_route_tables", {}).get(rt_id)
    if not rt or rt["project_id"] != pid:
        return JSONResponse({"error_msg": "Route table not found", "error_code": "VPC.0401"}, status_code=404)
    body = await request.json()
    route = {
        "id": new_id(),
        "destination": body.get("destination", ""),
        "nexthop": body.get("nexthop", ""),
        "type": body.get("type", "peering"),
    }
    rt["routes"].append(route)
    rt["updated_at"] = now_millis()
    return {"route": route}


@router.delete("/v1/{pid}/vpc/routetables/{rt_id}/routes/{route_id}")
async def delete_route(request: Request, pid: str, rt_id: str, route_id: str):
    s = request.app.state.sim
    rt = getattr(s, "vpc_route_tables", {}).get(rt_id)
    if not rt or rt["project_id"] != pid:
        return JSONResponse({"error_msg": "Route table not found", "error_code": "VPC.0401"}, status_code=404)
    rt["routes"] = [r for r in rt["routes"] if r["id"] != route_id]
    return Response(status_code=204)
