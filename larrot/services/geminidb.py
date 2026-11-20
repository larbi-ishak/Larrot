"""GeminiDB: Cassandra, InfluxDB, and Redis-compatible instances."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v3/{pid}/gemini/instances")
async def create_gemini_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "gemini_instances"): s.gemini_instances = {}
    body = await request.json()
    iid = new_id()
    engine = body.get("engine", "cassandra")
    s.gemini_instances[iid] = {
        "id": iid, "name": body.get("name", f"gemini-{engine}-{iid[:8]}"),
        "engine": engine, "engine_version": body.get("engine_version", "3.11"),
        "status": "CREATING", "mode": body.get("mode", "Cluster"),
        "flavor": body.get("flavor", "gemini.cassandra.large.2"),
        "volume": body.get("volume", {"type": "SSD", "size": 100}),
        "nodes": body.get("nodes", 3),
        "vpc_id": body.get("vpc_id", ""), "subnet_id": body.get("subnet_id", ""),
        "security_group_id": body.get("security_group_id", ""),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"instance": s.gemini_instances[iid]}


@router.get("/v3/{pid}/gemini/instances")
async def list_gemini_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "gemini_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total": len(instances)}


@router.get("/v3/{pid}/gemini/instances/{instance_id}")
async def show_gemini_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    i = getattr(s, "gemini_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "GDB.0101"}, status_code=404)
    return {"instance": i}


@router.delete("/v3/{pid}/gemini/instances/{instance_id}")
async def delete_gemini_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if instance_id not in getattr(s, "gemini_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "GDB.0101"}, status_code=404)
    del s.gemini_instances[instance_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/gemini/instances/{instance_id}/action")
async def gemini_instance_action(request: Request, pid: str, instance_id: str):
    body = await request.json()
    if "resize" in body:
        return {"job_id": new_id(), "action": "resize"}
    if "extend" in body:
        return {"job_id": new_id(), "action": "extend"}
    return JSONResponse({"error_msg": "Unknown action", "error_code": "GDB.0102"}, status_code=400)


@router.get("/v3/{pid}/gemini/flavors")
async def list_gemini_flavors(request: Request, pid: str):
    return {"flavors": [
        {"id": "gemini.cassandra.large.2", "name": "2 vCPUs | 8 GB", "engine": "cassandra"},
        {"id": "gemini.cassandra.xlarge.4", "name": "4 vCPUs | 16 GB", "engine": "cassandra"},
        {"id": "gemini.influx.large.2", "name": "2 vCPUs | 8 GB", "engine": "influxdb"},
        {"id": "gemini.redis.large.2", "name": "2 vCPUs | 8 GB", "engine": "redis"},
    ]}
