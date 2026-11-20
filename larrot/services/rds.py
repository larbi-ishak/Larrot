"""RDS: relational database service (instances, flavors)."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import apigw_error
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _instance_json(db):
    return {
        "id": db["id"], "name": db["name"], "status": db["status"],
        "datastore": db["datastore"],
        "engine": db["engine"], "engine_version": db["engine_version"],
        "flavor_ref": db["flavor_ref"],
        "vpc_id": db["vpc_id"], "subnet_id": db["subnet_id"],
        "security_group_id": db["security_group_id"],
        "availability_zone": db["availability_zone"],
        "port": db["port"],
        "volume": {"type": db["volume_type"], "size": db["volume_size"]},
        "public_ips": db["public_ips"],
        "private_ips": db["private_ips"],
        "created": db["created"], "updated": db["updated"],
        "charge_info": {"charge_mode": db["charge_mode"]},
        "enterprise_project_id": "0",
        "backup_strategy": db.get("backup_strategy"),
        "tags": db.get("tags", []),
        "disk_encryption_id": None,
        "ssl_option": db.get("ssl", 1),
        "master_instance_id": None,
        "read_replicas": [],
    }


@router.get("/v3/{pid}/instances")
async def list_instances(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "rds_instances"):
        state.rds_instances = {}
    instances = [db for db in state.rds_instances.values() if db["project_id"] == pid]
    return {"instances": [_instance_json(db) for db in instances],
            "total_count": len(instances)}


@router.get("/v3/{pid}/instances/{instance_id}")
async def show_instance(request: Request, pid: str, instance_id: str):
    state = request.app.state.sim
    if not hasattr(state, "rds_instances"):
        state.rds_instances = {}
    db = state.rds_instances.get(instance_id)
    if not db or db["project_id"] != pid:
        return JSONResponse(apigw_error("DBS.0001", "Instance not found."), status_code=404)
    return {"instance": _instance_json(db)}


@router.post("/v3/{pid}/instances")
async def create_instance(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "rds_instances"):
        state.rds_instances = {}
    body = await request.json()
    instance = body.get("instance") or {}
    if not instance.get("name"):
        return JSONResponse({"error_code": "DBS.0201",
                             "error_msg": "instance.name is required"}, status_code=400)

    db_id = new_id()
    now = now_millis()
    db = {
        "id": db_id, "name": instance["name"], "status": "BUILDING",
        "datastore": instance.get("datastore", {"type": "MySQL", "version": "8.0"}),
        "engine": instance.get("datastore", {}).get("type", "MySQL"),
        "engine_version": instance.get("datastore", {}).get("version", "8.0"),
        "flavor_ref": instance.get("flavor_ref", "rds.mysql.c2.large"),
        "vpc_id": instance.get("vpc_id", ""),
        "subnet_id": instance.get("subnet_id", ""),
        "security_group_id": instance.get("security_group_id", ""),
        "availability_zone": instance.get("availability_zone", "az1"),
        "port": instance.get("port", 3306),
        "volume_type": instance.get("volume", {}).get("type", "CLOUDSSD"),
        "volume_size": instance.get("volume", {}).get("size", 40),
        "public_ips": [],
        "private_ips": [f"192.168.0.{20 + len(state.rds_instances)}"],
        "created": now, "updated": now,
        "charge_mode": instance.get("charge_info", {}).get("charge_mode", "postPaid"),
        "project_id": pid,
    }
    state.rds_instances[db_id] = db

    async def effect():
        d = state.rds_instances.get(db_id)
        if d:
            d["status"] = "ACTIVE"
            d["updated"] = now_millis()

    import asyncio
    asyncio.get_event_loop().create_task(_delay_flip(effect, 2.0))

    return {"instance": _instance_json(db)}


async def _delay_flip(fn, delay):
    import asyncio
    await asyncio.sleep(delay)
    await fn()


@router.delete("/v3/{pid}/instances/{instance_id}")
async def delete_instance(request: Request, pid: str, instance_id: str):
    state = request.app.state.sim
    if not hasattr(state, "rds_instances"):
        state.rds_instances = {}
    db = state.rds_instances.get(instance_id)
    if not db or db["project_id"] != pid:
        return JSONResponse(apigw_error("DBS.0001", "Instance not found."), status_code=404)
    del state.rds_instances[instance_id]
    return {"job_id": new_id()}


@router.get("/v3/{pid}/flavors")
async def list_flavors(request: Request, pid: str):
    return {"flavors": [
        {"id": "rds.mysql.c2.large", "name": "2 vCPUs | 4 GB", "vcpus": "2", "ram": "4"},
        {"id": "rds.mysql.c2.xlarge", "name": "4 vCPUs | 8 GB", "vcpus": "4", "ram": "8"},
        {"id": "rds.mysql.c4.large", "name": "2 vCPUs | 8 GB", "vcpus": "2", "ram": "8"},
        {"id": "rds.pg.c2.large", "name": "2 vCPUs | 4 GB", "vcpus": "2", "ram": "4"},
    ]}
