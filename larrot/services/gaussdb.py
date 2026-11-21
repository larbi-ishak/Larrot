"""GaussDB: for MySQL/NoSQL: database instances."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

@router.post("/v3/{pid}/instances")
async def create_gaussdb_instance(request: Request, pid: str):
    """Create a GaussDB instance: the distributed MySQL-compatible database (async)."""
    s = request.app.state.sim
    if not hasattr(s, "gaussdb_instances"): s.gaussdb_instances = {}
    body = await request.json()
    iid = new_id()
    s.gaussdb_instances[iid] = {"id": iid, "name": body.get("name", f"gauss-{iid[:8]}"),
        "engine": body.get("datastore", {}).get("type", "gaussdb-mysql"),
        "engine_version": body.get("datastore", {}).get("version", "8.0"),
        "status": "BUILDING", "mode": body.get("mode", "Single"),
        "flavor_ref": body.get("flavor_ref", "gaussdb.mysql.x8.large.2"),
        "volume": body.get("volume", {"type": "ESSD", "size": 40}),
        "vpc_id": body.get("vpc_id", ""), "subnet_id": body.get("subnet_id", ""),
        "created_at": now_millis(), "project_id": pid}
    return {"id": iid, "name": s.gaussdb_instances[iid]["name"], "status": "BUILDING"}

@router.get("/v3/{pid}/instances")
async def list_gaussdb_instances(request: Request, pid: str):
    """List GaussDB instances."""
    s = request.app.state.sim
    instances = [i for i in getattr(s, "gaussdb_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total_count": len(instances)}

@router.get("/v3/{pid}/instances/{instance_id}")
async def show_gaussdb_instance(request: Request, pid: str, instance_id: str):
    """Show one instance: its nodes, flavor, storage, and endpoints."""
    s = request.app.state.sim
    i = getattr(s, "gaussdb_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "GDB.0001"}, status_code=404)
    return i

@router.delete("/v3/{pid}/instances/{instance_id}")
async def delete_gaussdb_instance(request: Request, pid: str, instance_id: str):
    """Delete a GaussDB instance (async)."""
    s = request.app.state.sim
    if instance_id not in getattr(s, "gaussdb_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "GDB.0001"}, status_code=404)
    del s.gaussdb_instances[instance_id]
    return {"job_id": new_id()}
