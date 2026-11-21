"""DCS: Distributed Cache Service: Redis/Memcached instances."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

@router.post("/v2/{pid}/instances")
async def create_dcs_instance(request: Request, pid: str):
    """Create a DCS Redis instance (async: takes minutes)."""
    s = request.app.state.sim
    if not hasattr(s, "dcs_instances"): s.dcs_instances = {}
    body = await request.json()
    iid = new_id()
    s.dcs_instances[iid] = {"instance_id": iid, "name": body.get("name", f"dcs-{iid[:8]}"),
        "engine": body.get("engine", "Redis"), "engine_version": body.get("engine_version", "5.0"),
        "capacity": body.get("capacity", 1), "status": "CREATING",
        "spec_code": body.get("spec_code", "redis.single.node"),
        "network_id": body.get("network_id", ""), "subnet_id": body.get("subnet_id", ""),
        "security_group_id": body.get("security_group_id", ""),
        "port": body.get("port", 6379),
        "ip": f"192.168.0.{200 + len(s.dcs_instances)}",
        "created_at": now_millis(), "project_id": pid}
    return {"instance_id": iid, "name": s.dcs_instances[iid]["name"]}

@router.get("/v2/{pid}/instances")
async def list_dcs_instances(request: Request, pid: str):
    """List DCS instances."""
    s = request.app.state.sim
    instances = [i for i in getattr(s, "dcs_instances", {}).values() if i["project_id"] == pid]
    return {"instance_num": len(instances), "instances": instances}

@router.get("/v2/{pid}/instances/{instance_id}")
async def show_dcs_instance(request: Request, pid: str, instance_id: str):
    """Show one instance: capacity, engine version, endpoints, and status."""
    s = request.app.state.sim
    i = getattr(s, "dcs_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DCS.0001"}, status_code=404)
    return i

@router.delete("/v2/{pid}/instances/{instance_id}")
async def delete_dcs_instance(request: Request, pid: str, instance_id: str):
    """Delete a DCS instance (async)."""
    s = request.app.state.sim
    if instance_id not in getattr(s, "dcs_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DCS.0001"}, status_code=404)
    del s.dcs_instances[instance_id]
    return Response(status_code=204)
