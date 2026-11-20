"""AS: Auto Scaling: groups, configurations, policies."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1/{pid}/scaling_group")
async def create_as_group(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "as_groups"): s.as_groups = {}
    body = await request.json()
    gid = new_id()
    s.as_groups[gid] = {"id": gid, "name": body.get("scaling_group_name", f"as-{gid[:8]}"),
        "status": "INSERVICE", "desire_instance_number": body.get("desire_instance_number", 0),
        "min_instance_number": body.get("min_instance_number", 0),
        "max_instance_number": body.get("max_instance_number", 10),
        "vpc_id": body.get("vpc_id", ""), "created_at": now_millis(), "project_id": pid}
    return {"scaling_group_id": gid}

@router.get("/v1/{pid}/scaling_group")
async def list_as_groups(request: Request, pid: str):
    s = request.app.state.sim
    groups = [g for g in getattr(s, "as_groups", {}).values() if g["project_id"] == pid]
    return {"total_number": len(groups), "scaling_groups": groups}

@router.get("/v1/{pid}/scaling_group/{group_id}")
async def show_as_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "as_groups", {}).get(group_id)
    if not g or g["project_id"] != pid:
        return JSONResponse({"error_msg": "Group not found", "error_code": "AS.0001"}, status_code=404)
    return {"scaling_group": g}

@router.delete("/v1/{pid}/scaling_group/{group_id}")
async def delete_as_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    if group_id not in getattr(s, "as_groups", {}):
        return JSONResponse({"error_msg": "Group not found", "error_code": "AS.0001"}, status_code=404)
    del s.as_groups[group_id]
    return Response(status_code=204)

@router.post("/v1/{pid}/scaling_policy")
async def create_as_policy(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "as_policies"): s.as_policies = {}
    body = await request.json()
    p_id = new_id()
    s.as_policies[p_id] = {"id": p_id, "name": body.get("scaling_policy_name", f"policy-{p_id[:8]}"),
        "type": body.get("scaling_policy_type", "ALARM"),
        "scaling_group_id": body.get("scaling_group_id", ""),
        "created_at": now_millis(), "project_id": pid}
    return {"scaling_policy_id": p_id}

@router.get("/v1/{pid}/scaling_policy")
async def list_as_policies(request: Request, pid: str):
    s = request.app.state.sim
    policies = [p for p in getattr(s, "as_policies", {}).values() if p["project_id"] == pid]
    return {"total_number": len(policies), "scaling_policies": policies}
