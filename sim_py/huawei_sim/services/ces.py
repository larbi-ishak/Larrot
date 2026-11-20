"""CES — Cloud Eye Service: metrics, alarms."""
from fastapi import APIRouter, Request, Response
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.get("/v1/{pid}/alarms")
async def list_alarms(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ces_alarms"): s.ces_alarms = {}
    return {"metric_alarms": list(getattr(s, "ces_alarms", {}).values())}

@router.post("/v1/{pid}/alarms")
async def create_alarm(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ces_alarms"): s.ces_alarms = {}
    body = await request.json()
    aid = new_id()
    s.ces_alarms[aid] = {"alarm_id": aid, "alarm_name": body.get("alarm_name", f"alarm-{aid[:8]}"),
        "alarm_description": body.get("alarm_description", ""),
        "alarm_status": "ok", "alarm_level": body.get("alarm_level", 2),
        "metric": body.get("metric", {"namespace": "SYS.ECS", "metric_name": "cpu_util"}),
        "condition": body.get("condition", {}), "alarm_action_enabled": True,
        "created_at": now_millis(), "project_id": pid}
    return {"alarm_id": aid}

@router.get("/v1/{pid}/alarms/{alarm_id}")
async def show_alarm(request: Request, pid: str, alarm_id: str):
    s = request.app.state.sim
    a = getattr(s, "ces_alarms", {}).get(alarm_id)
    if not a:
        return JSONResponse({"error_msg": "Alarm not found", "error_code": "CES.0001"}, status_code=404)
    return {"metric_alarms": [a]}

@router.delete("/v1/{pid}/alarms/{alarm_id}")
async def delete_alarm(request: Request, pid: str, alarm_id: str):
    s = request.app.state.sim
    if alarm_id not in getattr(s, "ces_alarms", {}):
        return JSONResponse({"error_msg": "Alarm not found", "error_code": "CES.0001"}, status_code=404)
    del s.ces_alarms[alarm_id]
    return Response(status_code=204)

@router.get("/v1/{pid}/metrics")
async def list_metrics(request: Request, pid: str):
    return {"metrics": [
        {"namespace": "SYS.ECS", "metric_name": "cpu_util", "unit": "%"},
        {"namespace": "SYS.ECS", "metric_name": "mem_util", "unit": "%"},
        {"namespace": "SYS.EVS", "metric_name": "disk_util", "unit": "%"},
        {"namespace": "SYS.RDS", "metric_name": "rds_cpu_util", "unit": "%"},
    ]}
