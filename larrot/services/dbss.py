"""DBSS: Database Security Service (audit)."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/dbss/instances")
async def create_dbss_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dbss_instances"): s.dbss_instances = {}
    body = await request.json()
    iid = new_id()
    s.dbss_instances[iid] = {
        "id": iid, "name": body.get("name", f"dbss-{iid[:8]}"),
        "status": "ACTIVE", "flavor": body.get("flavor", "dbss.standard.2"),
        "version": "3.2", "audit_types": body.get("audit_types", ["MySQL"]),
        "protected_databases": [], "audit_log_size": 0,
        "created_at": now_millis(), "project_id": pid,
    }
    return {"instance": s.dbss_instances[iid]}


@router.get("/v1/{pid}/dbss/instances")
async def list_dbss_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "dbss_instances", {}).values() if i["project_id"] == pid]
    return {"instances": instances, "total": len(instances)}


@router.get("/v1/{pid}/dbss/instances/{instance_id}")
async def show_dbss_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    i = getattr(s, "dbss_instances", {}).get(instance_id)
    if not i or i["project_id"] != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DBSS.0001"}, status_code=404)
    return {"instance": i}


@router.delete("/v1/{pid}/dbss/instances/{instance_id}")
async def delete_dbss_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    if instance_id not in getattr(s, "dbss_instances", {}):
        return JSONResponse({"error_msg": "Instance not found", "error_code": "DBSS.0001"}, status_code=404)
    del s.dbss_instances[instance_id]
    return Response(status_code=204)


@router.post("/v1/{pid}/dbss/instances/{instance_id}/audit-rules")
async def create_audit_rule(request: Request, pid: str, instance_id: str):
    body = await request.json()
    return {"rule_id": new_id(), "rule_name": body.get("name", "audit-rule"),
            "risk_level": body.get("risk_level", "HIGH"),
            "action": body.get("action", "ALARM")}


@router.get("/v1/{pid}/dbss/instances/{instance_id}/audit-logs")
async def list_audit_logs(request: Request, pid: str, instance_id: str):
    return {"audit_logs": [
        {"time": "2026-11-20T10:00:00Z", "user": "admin", "database": "mydb",
         "sql": "DROP TABLE users", "risk_level": "HIGH", "action": "ALARM"},
        {"time": "2026-11-20T10:05:00Z", "user": "app", "database": "mydb",
         "sql": "SELECT * FROM users WHERE id = 1", "risk_level": "LOW", "action": "LOG"},
    ], "total": 2}
