"""LTS — Log Tank Service: log groups, streams."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/log-groups")
async def create_log_group(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "lts_groups"): s.lts_groups = {}
    body = await request.json()
    gid = new_id()
    s.lts_groups[gid] = {"id": gid, "name": body.get("log_group_name", f"lg-{gid[:8]}"),
        "ttl_in_days": body.get("ttl_in_days", 7), "streams": [],
        "created_at": now_millis(), "project_id": pid}
    return {"log_group_id": gid}

@router.get("/v2/{pid}/log-groups")
async def list_log_groups(request: Request, pid: str):
    s = request.app.state.sim
    groups = [g for g in getattr(s, "lts_groups", {}).values() if g["project_id"] == pid]
    return {"log_groups": [{"id": g["id"], "name": g["name"], "ttl_in_days": g["ttl_in_days"]} for g in groups]}

@router.delete("/v2/{pid}/log-groups/{group_id}")
async def delete_log_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    if group_id not in getattr(s, "lts_groups", {}):
        return JSONResponse({"error_msg": "Group not found", "error_code": "LTS.0001"}, status_code=404)
    del s.lts_groups[group_id]
    return Response(status_code=204)

@router.post("/v2/{pid}/log-groups/{group_id}/log-streams")
async def create_log_stream(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "lts_groups", {}).get(group_id)
    if not g:
        return JSONResponse({"error_msg": "Group not found", "error_code": "LTS.0001"}, status_code=404)
    body = await request.json()
    sid = new_id()
    g["streams"].append({"id": sid, "name": body.get("log_stream_name", f"ls-{sid[:8]}"),
        "created_at": now_millis()})
    return {"log_stream_id": sid}

@router.get("/v2/{pid}/log-groups/{group_id}/log-streams")
async def list_log_streams(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "lts_groups", {}).get(group_id)
    if not g:
        return JSONResponse({"error_msg": "Group not found", "error_code": "LTS.0001"}, status_code=404)
    return {"log_streams": g["streams"]}
