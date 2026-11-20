"""DDS — Document Database Service: MongoDB instances."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v3/{pid}/instances")
async def create_dds_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dds_instances"): s.dds_instances = {}
    body = await request.json()
    iid = new_id()
    s.dds_instances[iid] = {"id": iid, "name": body.get("name", f"dds-{iid[:8]}"),
        "datastore": body.get("datastore", {"type": "DDS-Community", "version": "4.0"}),
        "status": "BUILDING", "mode": body.get("mode", "ReplicaSet"),
        "flavor_ref": body.get("flavor_ref", "dds.mongodb.s3.medium.4.replica"),
        "volume": body.get("volume", {"size": 20}),
        "vpc_id": body.get("vpc_id", ""), "subnet_id": body.get("subnet_id", ""),
        "security_group_id": body.get("security_group_id", ""),
        "created_at": now_millis(), "project_id": pid}
    return {"id": iid, "name": s.dds_instances[iid]["name"], "status": "BUILDING"}

@router.get("/v3/{pid}/instances")
async def list_dds_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "dds_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total_count": len(instances)}

@router.get("/v3/{pid}/instances/{instance_id}")
async def show_dds_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    i = getattr(s, "dds_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DDS.0001"}, status_code=404)
    return i

@router.delete("/v3/{pid}/instances/{instance_id}")
async def delete_dds_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if instance_id not in getattr(s, "dds_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DDS.0001"}, status_code=404)
    del s.dds_instances[instance_id]
    return {"job_id": new_id()}
