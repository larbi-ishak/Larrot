"""DCS Enhancements: backup, parameters, restart, analysis, capacity."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/instances/{instance_id}/backups")
async def create_dcs_backup(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if not hasattr(s, "dcs_backups"): s.dcs_backups = {}
    bid = new_id()
    s.dcs_backups[bid] = {
        "id": bid, "instance_id": instance_id,
        "backup_type": body_type if (body_type := (await request.json()).get("backup_type", "manual")) else "manual",
        "status": "BUILDING", "size": 0,
        "created_at": now_millis(), "project_id": pid,
    }
    return {"backup_id": bid, "status": "BUILDING"}


@router.get("/v2/{pid}/instances/{instance_id}/backups")
async def list_dcs_backups(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    backups = [b for b in getattr(s, "dcs_backups", {}).values()
               if b["project_id"] == pid and b["instance_id"] == instance_id]
    return {"backups": backups, "total": len(backups)}


@router.delete("/v2/{pid}/instances/{instance_id}/backups/{backup_id}")
async def delete_dcs_backup(request: Request, pid: str, instance_id: str, backup_id: str):
    s = request.app.state.sim
    if backup_id not in getattr(s, "dcs_backups", {}):
        return JSONResponse({"error_msg": "Backup not found", "error_code": "DCS.0201"}, status_code=404)
    del s.dcs_backups[backup_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/instances/{instance_id}/restore")
async def restore_dcs_backup(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"job_id": new_id(), "backup_id": body.get("backup_id", "")}


@router.get("/v2/{pid}/instances/{instance_id}/parameters")
async def list_dcs_parameters(request: Request, pid: str, instance_id: str):
    return {"parameters": [
        {"name": "maxmemory-policy", "value": "allkeys-lru", "description": "Memory eviction policy",
         "restart_required": False},
        {"name": "timeout", "value": "0", "description": "Client timeout (seconds)",
         "restart_required": False},
        {"name": "appendonly", "value": "yes", "description": "AOF persistence enabled",
         "restart_required": True},
        {"name": "maxclients", "value": "10000", "description": "Max client connections",
         "restart_required": True},
        {"name": "notify-keyspace-events", "value": "", "description": "Keyspace notifications",
         "restart_required": False},
    ], "total_count": 5}


@router.put("/v2/{pid}/instances/{instance_id}/parameters")
async def update_dcs_parameters(request: Request, pid: str, instance_id: str):
    await request.json()
    return {"job_id": new_id(), "restart_required": False}


@router.post("/v2/{pid}/instances/{instance_id}/restart")
async def restart_dcs_instance(request: Request, pid: str, instance_id: str):
    return {"job_id": new_id(), "action": "restart"}


@router.post("/v2/{pid}/instances/{instance_id}/resize")
async def resize_dcs_instance(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"job_id": new_id(), "new_capacity": body.get("new_capacity", 4)}


@router.get("/v2/{pid}/instances/{instance_id}/big-keys")
async def analyze_big_keys(request: Request, pid: str, instance_id: str):
    return {"big_keys": [
        {"key": "session:12345", "type": "string", "size": 1048576, "shard": 1},
        {"key": "user:profile:67890", "type": "hash", "size": 524288, "shard": 2},
    ], "total": 2}


@router.get("/v2/{pid}/instances/{instance_id}/hot-keys")
async def analyze_hot_keys(request: Request, pid: str, instance_id: str):
    return {"hot_keys": [
        {"key": "counter:page_views", "qps": 5000, "shard": 1},
        {"key": "cache:user:12345", "qps": 3200, "shard": 3},
    ], "total": 2}


@router.get("/v2/{pid}/flavors")
async def list_dcs_flavors(request: Request, pid: str):
    return {"flavors": [
        {"flavor_id": "redis.ha.xlarge.2", "spec_code": "redis_cluster",
         "cache_mode": "cluster", "vcpus": 2, "memory": 4},
        {"flavor_id": "redis.ha.2xlarge.4", "spec_code": "redis_cluster",
         "cache_mode": "cluster", "vcpus": 4, "memory": 16},
        {"flavor_id": "redis.single.xlarge.1", "spec_code": "redis_single_node",
         "cache_mode": "single", "vcpus": 2, "memory": 4},
    ]}
