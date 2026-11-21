"""SMS (Server Migration Service): source servers, migration tasks, templates.

Real routes: POST /v3/{project_id}/sources, POST /v3/{project_id}/tasks.
Migration tasks go MIGRATING → SUCCESS via the async job engine, with a
progress percentage that advances with the job.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v3/{pid}/sources")
async def register_source(request: Request, pid: str):
    """Register a source server for migration: its specs and disks."""
    s = request.app.state.sim
    if not hasattr(s, "sms_sources"):
        s.sms_sources = {}
    body = await request.json()
    ip = body.get("ip", "")
    if not ip:
        return JSONResponse({"error_code": "SMS.0001", "error_msg": "ip is required"},
                            status_code=400)
    sid = new_id()
    s.sms_sources[sid] = {
        "id": sid, "ip": ip, "name": body.get("name", f"source-{sid[:8]}"),
        "os_type": body.get("os_type", "LINUX"),
        "os_version": body.get("os_version", "CentOS 7.9"),
        "state": "unavailable",  # unavailable → available once agent connects
        "cpu_quantity": body.get("cpu_quantity", 4),
        "memory": body.get("memory", 8192),
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        src = s.sms_sources.get(sid)
        if src:
            src["state"] = "available"
        return None

    await s.jobs.submit("registerSource", {"source_id": sid}, effect)
    return s.sms_sources[sid]


@router.get("/v3/{pid}/sources")
async def list_sources(request: Request, pid: str):
    """List registered source servers with their migration states."""
    s = request.app.state.sim
    state_f = request.query_params.get("state")
    sources = [x for x in getattr(s, "sms_sources", {}).values()
               if x["project_id"] == pid]
    if state_f:
        sources = [x for x in sources if x["state"] == state_f]
    return {"total": len(sources), "sources": sources}


@router.get("/v3/{pid}/sources/{source_id}")
async def show_source(request: Request, pid: str, source_id: str):
    """Show one source server: its disks, CPU, and memory."""
    s = request.app.state.sim
    src = getattr(s, "sms_sources", {}).get(source_id)
    if not src or src["project_id"] != pid:
        return JSONResponse({"error_code": "SMS.0002", "error_msg": "source not found"},
                            status_code=404)
    return src


@router.delete("/v3/{pid}/sources/{source_id}")
async def delete_source(request: Request, pid: str, source_id: str):
    """Remove a source server registration."""
    s = request.app.state.sim
    src = getattr(s, "sms_sources", {}).get(source_id)
    if not src or src["project_id"] != pid:
        return JSONResponse({"error_code": "SMS.0002", "error_msg": "source not found"},
                            status_code=404)
    del s.sms_sources[source_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/tasks")
async def create_task(request: Request, pid: str):
    """Create a migration task (source server → target ECS)."""
    s = request.app.state.sim
    if not hasattr(s, "sms_tasks"):
        s.sms_tasks = {}
    body = await request.json()
    source_id = body.get("source_id", "")
    src = getattr(s, "sms_sources", {}).get(source_id)
    if not src or src["project_id"] != pid:
        return JSONResponse({"error_code": "SMS.0002", "error_msg": "source not found"},
                            status_code=404)
    if src["state"] != "available":
        return JSONResponse({"error_code": "SMS.0003",
                             "error_msg": "source is not available"}, status_code=400)
    tid = new_id()
    s.sms_tasks[tid] = {
        "id": tid, "name": body.get("name", f"task-{tid[:8]}"),
        "type": body.get("type", "MIGRATE_FILE"),
        "state": "MIGRATING", "progress": 0,
        "source_id": source_id, "target_server_id": body.get("target_server_id", ""),
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        t = s.sms_tasks.get(tid)
        if t:
            t["state"] = "SUCCESS"
            t["progress"] = 100
        return None

    await s.jobs.submit("migrateServer", {"task_id": tid}, effect)
    return s.sms_tasks[tid]


@router.get("/v3/{pid}/tasks")
async def list_tasks(request: Request, pid: str):
    """List migration tasks with their progress."""
    s = request.app.state.sim
    state_f = request.query_params.get("state")
    tasks = [t for t in getattr(s, "sms_tasks", {}).values() if t["project_id"] == pid]
    if state_f:
        tasks = [t for t in tasks if t["state"] == state_f]
    return {"total": len(tasks), "tasks": tasks}


@router.get("/v3/{pid}/tasks/{task_id}")
async def show_task(request: Request, pid: str, task_id: str):
    """Show one task: its state, speed, and target server."""
    s = request.app.state.sim
    t = getattr(s, "sms_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "SMS.0004", "error_msg": "task not found"},
                            status_code=404)
    return t


@router.delete("/v3/{pid}/tasks/{task_id}")
async def delete_task(request: Request, pid: str, task_id: str):
    """Delete a migration task."""
    s = request.app.state.sim
    t = getattr(s, "sms_tasks", {}).get(task_id)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "SMS.0004", "error_msg": "task not found"},
                            status_code=404)
    del s.sms_tasks[task_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/templates")
async def create_template(request: Request, pid: str):
    """Create a migration template: the target specs and disk mappings."""
    s = request.app.state.sim
    if not hasattr(s, "sms_templates"):
        s.sms_templates = {}
    body = await request.json()
    tpl_id = new_id()
    s.sms_templates[tpl_id] = {
        "id": tpl_id, "name": body.get("name", f"tpl-{tpl_id[:8]}"),
        "region": body.get("region", "ap-southeast-1"),
        "project_id": pid, "created_at": now_millis(),
    }
    return s.sms_templates[tpl_id]


@router.get("/v3/{pid}/templates")
async def list_templates(request: Request, pid: str):
    """List migration templates."""
    s = request.app.state.sim
    templates = [t for t in getattr(s, "sms_templates", {}).values()
                 if t["project_id"] == pid]
    return {"total": len(templates), "templates": templates}
