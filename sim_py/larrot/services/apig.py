"""APIG — API Gateway: custom APIs, groups."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/apigw/instances")
async def create_apig_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_instances"): s.apig_instances = {}
    body = await request.json()
    iid = new_id()
    s.apig_instances[iid] = {"id": iid, "name": body.get("name", f"apig-{iid[:8]}"),
        "status": "Running", "spec": body.get("spec", "BASIC"),
        "created_at": now_millis(), "project_id": pid}
    return {"id": iid, "name": s.apig_instances[iid]["name"]}

@router.get("/v2/{pid}/apigw/instances")
async def list_apig_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "apig_instances", {}).values() if i["project_id"] == pid]
    return {"total": len(instances), "instances": instances}

@router.post("/v2/{pid}/apigw/groups")
async def create_api_group(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_groups"): s.apig_groups = {}
    body = await request.json()
    gid = new_id()
    s.apig_groups[gid] = {"id": gid, "name": body.get("name", f"group-{gid[:8]}"),
        "instance_id": body.get("instance_id", ""), "apis": [],
        "created_at": now_millis(), "project_id": pid}
    return {"id": gid, "name": s.apig_groups[gid]["name"]}

@router.get("/v2/{pid}/apigw/groups")
async def list_api_groups(request: Request, pid: str):
    s = request.app.state.sim
    groups = [g for g in getattr(s, "apig_groups", {}).values() if g["project_id"] == pid]
    return {"total": len(groups), "groups": groups}

@router.post("/v2/{pid}/apigw/apis")
async def create_api(request: Request, pid: str):
    body = await request.json()
    aid = new_id()
    return {"id": aid, "name": body.get("name", f"api-{aid[:8]}"),
            "req_method": body.get("req_method", "GET"),
            "req_uri": body.get("req_uri", "/test")}
