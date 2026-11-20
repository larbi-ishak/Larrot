"""RDS Enhancements: backups, parameters, read replicas, accounts, databases, logs, failover."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/rds/backups")
async def create_backup(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "rds_backups"): s.rds_backups = {}
    body = await request.json()
    bid = new_id()
    s.rds_backups[bid] = {
        "id": bid, "name": body.get("name", f"backup-{bid[:8]}"),
        "instance_id": body.get("instance_id", ""),
        "backup_type": body.get("backup_type", "auto"),
        "size": body.get("size", 0), "status": "BUILDING",
        "databases": body.get("databases", []),
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"backup": s.rds_backups[bid]}


@router.get("/v3/{pid}/rds/backups")
async def list_backups(request: Request, pid: str):
    s = request.app.state.sim
    instance_id = request.query_params.get("instance_id")
    backups = [b for b in getattr(s, "rds_backups", {}).values() if b["project_id"] == pid]
    if instance_id:
        backups = [b for b in backups if b["instance_id"] == instance_id]
    return {"backups": backups, "total": len(backups)}


@router.get("/v3/{pid}/rds/backups/{backup_id}")
async def show_backup(request: Request, pid: str, backup_id: str):
    s = request.app.state.sim
    b = getattr(s, "rds_backups", {}).get(backup_id)
    if not b or b["project_id"] != pid:
        return JSONResponse({"error_msg": "Backup not found", "error_code": "DBS.0201"}, status_code=404)
    return {"backup": b}


@router.delete("/v3/{pid}/rds/backups/{backup_id}")
async def delete_backup(request: Request, pid: str, backup_id: str):
    s = request.app.state.sim
    if backup_id not in getattr(s, "rds_backups", {}):
        return JSONResponse({"error_msg": "Backup not found", "error_code": "DBS.0201"}, status_code=404)
    del s.rds_backups[backup_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/instances/{instance_id}/restore")
async def restore_backup(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"job_id": new_id(), "restore_target": body.get("target_instance_id", instance_id)}


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@router.get("/v3/{pid}/instances/{instance_id}/parameters")
async def list_parameters(request: Request, pid: str, instance_id: str):
    return {"parameters": [
        {"name": "max_connections", "value": "1000", "description": "Maximum connections",
         "restart_required": False, "readonly": False},
        {"name": "innodb_buffer_pool_size", "value": "1073741824", "description": "InnoDB buffer pool size",
         "restart_required": True, "readonly": False},
        {"name": "character_set_server", "value": "utf8mb4", "description": "Server character set",
         "restart_required": False, "readonly": False},
        {"name": "slow_query_log", "value": "ON", "description": "Slow query log enabled",
         "restart_required": False, "readonly": False},
        {"name": "long_query_time", "value": "1", "description": "Slow query threshold (seconds)",
         "restart_required": False, "readonly": False},
        {"name": "max_allowed_packet", "value": "1073741824", "description": "Max packet size",
         "restart_required": False, "readonly": False},
        {"name": "read_only", "value": "OFF", "description": "Read-only mode",
         "restart_required": False, "readonly": False},
        {"name": "binlog_format", "value": "ROW", "description": "Binary log format",
         "restart_required": True, "readonly": False},
    ], "total_count": 8}


@router.put("/v3/{pid}/instances/{instance_id}/parameters")
async def update_parameters(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"job_id": new_id(), "restart_required": False}


# ---------------------------------------------------------------------------
# Read Replicas
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/instances/{instance_id}/replicas")
async def create_read_replica(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if not hasattr(s, "rds_replicas"): s.rds_replicas = {}
    body = await request.json()
    replica_id = new_id()
    s.rds_replicas[replica_id] = {
        "id": replica_id, "name": body.get("name", f"replica-{replica_id[:8]}"),
        "master_id": instance_id, "status": "BUILDING",
        "flavor_ref": body.get("flavor_ref", "rds.mysql.c2.large"),
        "volume": body.get("volume", {"type": "CLOUDSSD", "size": 40}),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"replica": s.rds_replicas[replica_id]}


@router.get("/v3/{pid}/instances/{instance_id}/replicas")
async def list_read_replicas(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    replicas = [r for r in getattr(s, "rds_replicas", {}).values()
                if r["project_id"] == pid and r["master_id"] == instance_id]
    return {"replicas": replicas, "total": len(replicas)}


@router.delete("/v3/{pid}/instances/{instance_id}/replicas/{replica_id}")
async def delete_read_replica(request: Request, pid: str, instance_id: str, replica_id: str):
    s = request.app.state.sim
    if replica_id not in getattr(s, "rds_replicas", {}):
        return JSONResponse({"error_msg": "Replica not found", "error_code": "DBS.0301"}, status_code=404)
    del s.rds_replicas[replica_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Database Accounts (users)
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/instances/{instance_id}/db-users")
async def create_db_user(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if not hasattr(s, "rds_db_users"): s.rds_db_users = {}
    body = await request.json()
    user_name = body.get("name", f"user-{new_id()[:8]}")
    s.rds_db_users[user_name] = {
        "name": user_name, "host": body.get("host", "%"),
        "databases": body.get("databases", []),
        "privileges": body.get("privileges", ["SELECT"]),
        "created_at": now_millis(), "instance_id": instance_id, "project_id": pid,
    }
    return {"user": {"name": user_name, "host": s.rds_db_users[user_name]["host"]}}


@router.get("/v3/{pid}/instances/{instance_id}/db-users")
async def list_db_users(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    users = [u for u in getattr(s, "rds_db_users", {}).values()
             if u["project_id"] == pid and u["instance_id"] == instance_id]
    return {"users": [{"name": u["name"], "host": u["host"], "databases": u["databases"]} for u in users]}


@router.delete("/v3/{pid}/instances/{instance_id}/db-users/{user_name}")
async def delete_db_user(request: Request, pid: str, instance_id: str, user_name: str):
    s = request.app.state.sim
    if user_name not in getattr(s, "rds_db_users", {}):
        return JSONResponse({"error_msg": "User not found", "error_code": "DBS.0401"}, status_code=404)
    del s.rds_db_users[user_name]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Databases within instance
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/instances/{instance_id}/databases")
async def create_database(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if not hasattr(s, "rds_databases"): s.rds_databases = {}
    body = await request.json()
    db_name = body.get("name", f"db_{new_id()[:8]}")
    s.rds_databases[db_name] = {
        "name": db_name, "character_set": body.get("character_set", "utf8mb4"),
        "instance_id": instance_id, "project_id": pid,
    }
    return {"database": {"name": db_name, "character_set": "utf8mb4"}}


@router.get("/v3/{pid}/instances/{instance_id}/databases")
async def list_databases(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    databases = [d for d in getattr(s, "rds_databases", {}).values()
                 if d["project_id"] == pid and d["instance_id"] == instance_id]
    return {"databases": [{"name": d["name"], "character_set": d["character_set"]} for d in databases]}


@router.delete("/v3/{pid}/instances/{instance_id}/databases/{db_name}")
async def delete_database(request: Request, pid: str, instance_id: str, db_name: str):
    s = request.app.state.sim
    if db_name not in getattr(s, "rds_databases", {}):
        return JSONResponse({"error_msg": "Database not found", "error_code": "DBS.0501"}, status_code=404)
    del s.rds_databases[db_name]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Logs (slow query, error)
# ---------------------------------------------------------------------------

@router.get("/v3/{pid}/instances/{instance_id}/slow-logs")
async def list_slow_logs(request: Request, pid: str, instance_id: str):
    return {"slow_logs": [
        {"execute_time": "2026-11-20T10:00:00Z", "query_time": "2.5s",
         "lock_time": "0.01s", "rows_examined": 1000000, "rows_sent": 10,
         "sql": "SELECT * FROM large_table WHERE col LIKE '%search%'", "user": "app_user"},
        {"execute_time": "2026-11-20T10:05:00Z", "query_time": "1.8s",
         "lock_time": "0.00s", "rows_examined": 500000, "rows_sent": 5,
         "sql": "SELECT COUNT(*) FROM orders WHERE status = 'pending'", "user": "app_user"},
    ], "total": 2}


@router.get("/v3/{pid}/instances/{instance_id}/error-logs")
async def list_error_logs(request: Request, pid: str, instance_id: str):
    return {"error_logs": [
        {"time": "2026-11-20T09:00:00Z", "level": "ERROR",
         "content": "InnoDB: Buffer pool is full, consider increasing innodb_buffer_pool_size"},
    ], "total": 1}


# ---------------------------------------------------------------------------
# Failover / Switchover
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/instances/{instance_id}/failover")
async def failover(request: Request, pid: str, instance_id: str):
    return {"job_id": new_id(), "failover_mode": "auto"}


@router.post("/v3/{pid}/instances/{instance_id}/switchover")
async def switchover(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"job_id": new_id(), "target": body.get("target_instance_id", "")}


# ---------------------------------------------------------------------------
# Storage / Flavor / Public IP
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/instances/{instance_id}/action")
async def instance_action(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    body = await request.json()
    if "resize" in body:
        return {"job_id": new_id(), "action": "resize_flavor"}
    if "extend" in body:
        return {"job_id": new_id(), "action": "extend_volume",
                "new_size": body["extend"].get("size", 100)}
    if "public_ip" in body:
        return {"job_id": new_id(), "action": "bind_public_ip"}
    return JSONResponse({"error_msg": "Unknown action", "error_code": "DBS.0601"}, status_code=400)


# ---------------------------------------------------------------------------
# parameter templates (tier-3 documented operations)
# ---------------------------------------------------------------------------

@router.get("/v3/{pid}/configurations")
async def list_rds_configurations(request: Request, pid: str):
    s = request.app.state.sim
    cfgs = [c for c in getattr(s, "rds_configurations", {}).values()
            if c["project_id"] == pid]
    return {"configurations": cfgs, "total": len(cfgs)}


@router.post("/v3/{pid}/configurations")
async def create_rds_configuration(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "rds_configurations"):
        s.rds_configurations = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "DBS.0201", "error_msg": "name is required"},
                            status_code=400)
    cid = new_id()
    s.rds_configurations[cid] = {
        "id": cid, "name": name,
        "description": body.get("description", ""),
        "datastore": body.get("datastore", {"type": "MySQL", "version": "8.0"}),
        "parameters": body.get("values", {}),
        "project_id": pid, "created_at": now_millis(), "updated_at": now_millis(),
    }
    return {"configuration": s.rds_configurations[cid]}


@router.get("/v3/{pid}/configurations/{configuration_id}")
async def show_rds_configuration(request: Request, pid: str, configuration_id: str):
    s = request.app.state.sim
    c = getattr(s, "rds_configurations", {}).get(configuration_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DBS.0202",
                             "error_msg": "configuration not found"}, status_code=404)
    return {"configuration": c}


@router.put("/v3/{pid}/configurations/{configuration_id}")
async def update_rds_configuration(request: Request, pid: str, configuration_id: str):
    s = request.app.state.sim
    c = getattr(s, "rds_configurations", {}).get(configuration_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DBS.0202",
                             "error_msg": "configuration not found"}, status_code=404)
    body = await request.json()
    for field in ("name", "description", "parameters"):
        if field in body:
            c[field] = body[field]
    c["updated_at"] = now_millis()
    return {"configuration": c}


@router.delete("/v3/{pid}/configurations/{configuration_id}")
async def delete_rds_configuration(request: Request, pid: str, configuration_id: str):
    s = request.app.state.sim
    c = getattr(s, "rds_configurations", {}).get(configuration_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DBS.0202",
                             "error_msg": "configuration not found"}, status_code=404)
    del s.rds_configurations[configuration_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/configurations/{configuration_id}/apply")
async def apply_rds_configuration(request: Request, pid: str, configuration_id: str):
    s = request.app.state.sim
    c = getattr(s, "rds_configurations", {}).get(configuration_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DBS.0202",
                             "error_msg": "configuration not found"}, status_code=404)
    body = await request.json()
    instance_ids = body.get("instance_ids", [])
    applied = []
    for iid in instance_ids:
        inst = getattr(s, "rds_instances", {}).get(iid)
        if inst:
            inst.setdefault("applied_configurations", []).append(configuration_id)
            applied.append(iid)
    return {"configuration_id": configuration_id,
            "instance_ids": applied, "success": True}
