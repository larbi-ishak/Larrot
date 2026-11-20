"""CES: Cloud Eye Service: metrics, alarms."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
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


# ---------------------------------------------------------------------------
# sub-APIs: alarm history + metric datapoints
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/alarms/{alarm_id}/history")
async def alarm_history(request: Request, pid: str, alarm_id: str):
    s = request.app.state.sim
    a = getattr(s, "ces_alarms", {}).get(alarm_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "CES.0001", "error_msg": "alarm not found"},
                            status_code=404)
    return {"history": [{"alarm_id": alarm_id, "status": "alarm",
                          "timestamp": now_millis(), "level": 2}]}


@router.post("/v1.0/{pid}/batch-query/metric-data")
async def batch_metric_data(request: Request, pid: str):
    body = await request.json()
    out = []
    for m in body.get("metrics", []):
        dims = m.get("dim_0", "")
        out.append({"metric": m.get("metric_name", ""),
                     "data_points": [{"timestamp": now_millis(), "value": 42.0}],
                     "dim_0": dims})
    return {"metric_data_results": out}


@router.get("/v1.0/{pid}/metric-data")
async def get_metric_data(request: Request, pid: str):
    """Query metric datapoints (documented: GET /v1.0/{project_id}/metric-data)."""
    return {"metric_data_results": [{
        "metric_name": request.query_params.get("metric_name", "cpu_util"),
        "dim.0": request.query_params.get("dim.0", ""),
        "datapoints": [{"timestamp": now_millis(), "value": 42.0}],
    }]}
