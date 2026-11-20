"""OMS (Object Storage Migration) — bulk migration tasks into OBS.

Real route: POST /v2/{project_id}/tasks. Tasks go MIGRATING → SUCCESS via the
async job engine, with a migrated-record count.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/tasks")
async def create_task(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "oms_tasks"):
        s.oms_tasks = {}
    body = await request.json()
    src = body.get("src_node", {})
    dst = body.get("dst_node", {})
    if not src.get("bucket") or not dst.get("bucket"):
        return JSONResponse({"error_code": "OMS.0001",
                             "error_msg": "src_node.bucket and dst_node.bucket are required"},
                            status_code=400)
    if dst["bucket"] not in getattr(s, "obs_buckets", {}):
        return JSONResponse({"error_code": "OMS.0002",
                             "error_msg": "destination bucket does not exist"}, status_code=404)
    tid = new_id()
    s.oms_tasks[tid] = {
        "id": tid, "name": body.get("name", f"oms-{tid[:8]}"),
        "status": "MIGRATING",
        "src_node": src, "dst_node": dst,
        "migrated_record": 0, "total_record": body.get("total_record", 1000),
        "failure_record": 0, "skipped_record": 0,
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        t = s.oms_tasks.get(tid)
        if t:
            t["status"] = "SUCCESS"
            t["migrated_record"] = t["total_record"]
        return None

    await s.jobs.submit("runOmsTask", {"task_id": tid}, effect)
    return s.oms_tasks[tid]


@router.get("/v2/{pid}/tasks")
async def list_tasks(request: Request, pid: str):
    s = request.app.state.sim
    status_f = request.query_params.get("status")
    tasks = [t for t in getattr(s, "oms_tasks", {}).values() if t["project_id"] == pid]
    if status_f:
        tasks = [t for t in tasks if t["status"] == status_f]
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/v2/{pid}/tasks/{task_id}")
async def show_task(request: Request, pid: str, task_id: str):
    s = request.app.state.sim
    t = getattr(s, "oms_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "OMS.0003", "error_msg": "task not found"},
                            status_code=404)
    return t


@router.post("/v2/{pid}/tasks/{task_id}/stop")
async def stop_task(request: Request, pid: str, task_id: str):
    s = request.app.state.sim
    t = getattr(s, "oms_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "OMS.0003", "error_msg": "task not found"},
                            status_code=404)
    if t["status"] != "MIGRATING":
        return JSONResponse({"error_code": "OMS.0004",
                             "error_msg": "task is not MIGRATING"}, status_code=400)
    t["status"] = "STOPPING"
    return {"id": task_id, "status": "STOPPING"}


@router.delete("/v2/{pid}/tasks/{task_id}")
async def delete_task(request: Request, pid: str, task_id: str):
    s = request.app.state.sim
    t = getattr(s, "oms_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "OMS.0003", "error_msg": "task not found"},
                            status_code=404)
    del s.oms_tasks[task_id]
    return Response(status_code=204)
