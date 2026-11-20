"""ECS Server Groups: anti-affinity/affinity groups."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2.1/{pid}/os-server-groups")
async def create_server_group(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ecs_server_groups"): s.ecs_server_groups = {}
    body = await request.json()
    sg_name = body.get("server_group", {}).get("name", f"sg-{new_id()[:8]}")
    policies = body.get("server_group", {}).get("policies", ["anti-affinity"])
    sg_id = new_id()
    s.ecs_server_groups[sg_id] = {
        "id": sg_id, "name": sg_name, "policies": policies,
        "members": [], "created_at": now_millis(), "project_id": pid,
    }
    return {"server_group": {"id": sg_id, "name": sg_name, "policies": policies, "members": []}}


@router.get("/v2.1/{pid}/os-server-groups")
async def list_server_groups(request: Request, pid: str):
    s = request.app.state.sim
    groups = [g for g in getattr(s, "ecs_server_groups", {}).values() if g["project_id"] == pid]
    return {"server_groups": [{"id": g["id"], "name": g["name"], "policies": g["policies"],
                                "members": g["members"]} for g in groups]}


@router.get("/v2.1/{pid}/os-server-groups/{group_id}")
async def show_server_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "ecs_server_groups", {}).get(group_id)
    if not g or g["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0116", "message": "Server group not found"}}, status_code=404)
    return {"server_group": {"id": g["id"], "name": g["name"], "policies": g["policies"], "members": g["members"]}}


@router.delete("/v2.1/{pid}/os-server-groups/{group_id}")
async def delete_server_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    if group_id not in getattr(s, "ecs_server_groups", {}):
        return JSONResponse({"error": {"code": "Ecs.0116", "message": "Server group not found"}}, status_code=404)
    del s.ecs_server_groups[group_id]
    return Response(status_code=204)


@router.put("/v2.1/{pid}/os-server-groups/{group_id}")
async def update_server_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "ecs_server_groups", {}).get(group_id)
    if not g or g["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0116", "message": "Server group not found"}}, status_code=404)
    body = await request.json()
    if "name" in body.get("server_group", {}):
        g["name"] = body["server_group"]["name"]
    if "policies" in body.get("server_group", {}):
        g["policies"] = body["server_group"]["policies"]
    return {"server_group": {"id": g["id"], "name": g["name"], "policies": g["policies"], "members": g["members"]}}
