"""DMS: Distributed Message Service: Kafka queues, RabbitMQ."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/instances")
async def create_dms_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dms_instances"): s.dms_instances = {}
    body = await request.json()
    iid = new_id()
    s.dms_instances[iid] = {"instance_id": iid, "name": body.get("name", f"dms-{iid[:8]}"),
        "engine": body.get("engine", "kafka"), "engine_version": body.get("engine_version", "2.7"),
        "status": "CREATING", "broker_num": body.get("broker_num", 3),
        "storage_space": body.get("storage_space", 300),
        "access_ip": f"192.168.0.{150 + len(s.dms_instances)}",
        "created_at": now_millis(), "project_id": pid}
    return {"instance_id": iid}

@router.get("/v2/{pid}/instances")
async def list_dms_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "dms_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total": len(instances)}

@router.get("/v2/{pid}/instances/{instance_id}")
async def show_dms_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    i = getattr(s, "dms_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DMS.0001"}, status_code=404)
    return i

@router.delete("/v2/{pid}/instances/{instance_id}")
async def delete_dms_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if instance_id not in getattr(s, "dms_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DMS.0001"}, status_code=404)
    del s.dms_instances[instance_id]
    return Response(status_code=204)

@router.post("/v2/{pid}/instances/{instance_id}/topics")
async def create_topic(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"topic": body.get("name", "test-topic"), "partition": body.get("partition", 3)}
