"""DES (Data Express): physical bulk data transfer (Teleport/disk).

Real route: POST /v1/{project_id}/tasks on the DES endpoint; namespaced here
under /v1/{pid}/des/tasks to avoid a collision with future bare /v1/{pid}/tasks.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

VALID_TYPES = {"Teleport", "Disk"}


@router.post("/v1/{pid}/des/tasks")
async def create_task(request: Request, pid: str):
    """Create a Data Express task: ship storage to the cloud by disk or teleport (async)."""
    s = request.app.state.sim
    if not hasattr(s, "des_tasks"):
        s.des_tasks = {}
    body = await request.json()
    name = body.get("name", "")
    ttype = body.get("task_type", "Teleport")
    if not name:
        return JSONResponse({"error_code": "DES.0001", "error_msg": "name is required"},
                            status_code=400)
    if ttype not in VALID_TYPES:
        return JSONResponse({"error_code": "DES.0002",
                             "error_msg": f"task_type must be one of {sorted(VALID_TYPES)}"},
                            status_code=400)
    tid = new_id()
    s.des_tasks[tid] = {
        "id": tid, "name": name, "task_type": ttype,
        "status": "CREATING", "region": body.get("region", "ap-southeast-1"),
        "description": body.get("description", ""),
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        t = s.des_tasks.get(tid)
        if t:
            t["status"] = "WAITING"  # waiting for the device to arrive
        return None

    await s.jobs.submit("createDesTask", {"task_id": tid}, effect)
    return s.des_tasks[tid]


@router.get("/v1/{pid}/des/tasks")
async def list_tasks(request: Request, pid: str):
    """List DES tasks."""
    s = request.app.state.sim
    tasks = [t for t in getattr(s, "des_tasks", {}).values() if t["project_id"] == pid]
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/v1/{pid}/des/tasks/{task_id}")
async def show_task(request: Request, pid: str, task_id: str):
    """Show one task: its region, package type, and progress."""
    s = request.app.state.sim
    t = getattr(s, "des_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "DES.0003", "error_msg": "task not found"},
                            status_code=404)
    return t


@router.delete("/v1/{pid}/des/tasks/{task_id}")
async def delete_task(request: Request, pid: str, task_id: str):
    """Delete a DES task."""
    s = request.app.state.sim
    t = getattr(s, "des_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "DES.0003", "error_msg": "task not found"},
                            status_code=404)
    del s.des_tasks[task_id]
    return Response(status_code=204)
