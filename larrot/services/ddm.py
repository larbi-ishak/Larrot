"""DDM: Distributed Database Middleware (sharding)."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/instances")
async def create_ddm_instance(request: Request, pid: str):
    """Create a DDM distributed database instance: the sharding middleware (async)."""
    s = request.app.state.sim
    if not hasattr(s, "ddm_instances"): s.ddm_instances = {}
    body = await request.json()
    iid = new_id()
    s.ddm_instances[iid] = {
        "id": iid, "name": body.get("name", f"ddm-{iid[:8]}"),
        "status": "CREATING", "flavor": body.get("flavor", "ddm.c6.large.2"),
        "node_num": body.get("node_num", 2),
        "vpc_id": body.get("vpc_id", ""), "subnet_id": body.get("subnet_id", ""),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"instance": s.ddm_instances[iid]}


@router.get("/v1/{pid}/instances")
async def list_ddm_instances(request: Request, pid: str):
    """List DDM instances."""
    s = request.app.state.sim
    instances = [i for i in getattr(s, "ddm_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total": len(instances)}


@router.delete("/v1/{pid}/instances/{instance_id}")
async def delete_ddm_instance(request: Request, pid: str, instance_id: str):
    """Delete a DDM instance."""
    s = request.app.state.sim
    if instance_id not in getattr(s, "ddm_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DDM.0001"}, status_code=404)
    del s.ddm_instances[instance_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Schemas (logical databases with sharding)
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/instances/{instance_id}/schemas")
async def create_schema(request: Request, pid: str, instance_id: str):
    """Create a logical schema on a DDM instance: the sharded table space."""
    s = request.app.state.sim
    if not hasattr(s, "ddm_schemas"): s.ddm_schemas = {}
    body = await request.json()
    schema_name = body.get("name", f"schema_{new_id()[:8]}")
    s.ddm_schemas[schema_name] = {
        "name": schema_name, "instance_id": instance_id,
        "sharded": body.get("sharded", True),
        "shard_mode": body.get("shard_mode", "hash"),
        "shard_num": body.get("shard_num", 8),
        "data_nodes": body.get("data_nodes", []),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"schema": {"name": schema_name, "shard_num": s.ddm_schemas[schema_name]["shard_num"]}}


@router.get("/v1/{pid}/instances/{instance_id}/schemas")
async def list_schemas(request: Request, pid: str, instance_id: str):
    """List a DDM instance's logical schemas."""
    s = request.app.state.sim
    schemas = [sc for sc in getattr(s, "ddm_schemas", {}).values()
               if sc["project_id"] == pid and sc["instance_id"] == instance_id]
    return {"schemas": [{"name": sc["name"], "shard_num": sc["shard_num"],
                          "shard_mode": sc["shard_mode"]} for sc in schemas]}


@router.delete("/v1/{pid}/instances/{instance_id}/schemas/{schema_name}")
async def delete_schema(request: Request, pid: str, instance_id: str, schema_name: str):
    """Delete a logical schema."""
    s = request.app.state.sim
    if schema_name not in getattr(s, "ddm_schemas", {}):
        return JSONResponse({"error_msg": "Schema not found", "error_code": "DDM.0002"}, status_code=404)
    del s.ddm_schemas[schema_name]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Sharding rules
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/instances/{instance_id}/schemas/{schema_name}/shard-rules")
async def create_shard_rule(request: Request, pid: str, instance_id: str, schema_name: str):
    """Create a shard rule: how a table's rows split across backend RDS shards."""
    body = await request.json()
    return {"shard_rule": {
        "name": body.get("name", "shard_rule"),
        "table_name": body.get("table_name", ""),
        "shard_column": body.get("shard_column", "id"),
        "shard_algorithm": body.get("shard_algorithm", "hash"),
        "shard_num": body.get("shard_num", 8),
    }}
