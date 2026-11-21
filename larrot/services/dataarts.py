"""DataArts Studio: connections, jobs, scripts (data governance + ETL).

Real routes: /v2/{project_id}/connections (factory connections), jobs, scripts.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

VALID_CONN_TYPES = {"DWS", "DLI", "RDS", "OBS", "Kafka", "DIS", "MySQL", "Oracle", "Hive"}


@router.post("/v2/{pid}/connections")
async def create_connection(request: Request, pid: str):
    """Create a DataArts data connection: a link to a database or message queue."""
    s = request.app.state.sim
    if not hasattr(s, "dataarts_connections"):
        s.dataarts_connections = {}
    body = await request.json()
    name = body.get("name", "")
    ctype = body.get("connection_type", "DWS")
    if not name:
        return JSONResponse({"error_code": "DATAARTS.0001", "error_msg": "name is required"},
                            status_code=400)
    if ctype not in VALID_CONN_TYPES:
        return JSONResponse({"error_code": "DATAARTS.0002",
                             "error_msg": f"invalid connection_type: {ctype}"},
                            status_code=400)
    cid = new_id()
    s.dataarts_connections[cid] = {
        "connection_id": cid, "name": name, "connection_type": ctype,
        "config": body.get("config", {}), "status": "ACTIVE",
        "created_at": now_millis(), "project_id": pid,
    }
    return {"connection": s.dataarts_connections[cid]}


@router.get("/v2/{pid}/connections")
async def list_connections(request: Request, pid: str):
    """List data connections."""
    s = request.app.state.sim
    conns = [c for c in getattr(s, "dataarts_connections", {}).values()
             if c["project_id"] == pid]
    return {"connections": conns, "total": len(conns)}


@router.get("/v2/{pid}/connections/{conn_id}")
async def show_connection(request: Request, pid: str, conn_id: str):
    """Show one data connection: type, endpoint, and credentials reference."""
    s = request.app.state.sim
    c = getattr(s, "dataarts_connections", {}).get(conn_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DATAARTS.0003",
                             "error_msg": "connection not found"}, status_code=404)
    return {"connection": c}


@router.delete("/v2/{pid}/connections/{conn_id}")
async def delete_connection(request: Request, pid: str, conn_id: str):
    """Delete a data connection."""
    s = request.app.state.sim
    c = getattr(s, "dataarts_connections", {}).get(conn_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "DATAARTS.0003",
                             "error_msg": "connection not found"}, status_code=404)
    del s.dataarts_connections[conn_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# jobs (factory ETL pipelines)
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/jobs")
async def create_job(request: Request, pid: str):
    """Create a data integration job: where data comes from and where it goes."""
    s = request.app.state.sim
    if not hasattr(s, "dataarts_jobs"):
        s.dataarts_jobs = {}
    body = await request.json()
    name = body.get("name", body.get("job_name", ""))
    if not name:
        return JSONResponse({"error_code": "DATAARTS.0004", "error_msg": "name is required"},
                            status_code=400)
    jid = new_id()
    s.dataarts_jobs[jid] = {
        "job_id": jid, "name": name, "job_type": body.get("job_type", "BatchJob"),
        "nodes": body.get("nodes", []), "status": "DRAFT",
        "created_at": now_millis(), "project_id": pid,
    }
    return {"job": s.dataarts_jobs[jid]}


@router.get("/v2/{pid}/jobs")
async def list_jobs(request: Request, pid: str):
    """List data jobs."""
    s = request.app.state.sim
    jobs = [j for j in getattr(s, "dataarts_jobs", {}).values()
            if j["project_id"] == pid]
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/v2/{pid}/jobs/{job_name}/run")
async def run_job(request: Request, pid: str, job_name: str):
    """Start a job: goes RUNNING → SUCCEEDED via the async job engine."""
    s = request.app.state.sim
    job = next((j for j in getattr(s, "dataarts_jobs", {}).values()
                if j["name"] == job_name and j["project_id"] == pid), None)
    if not job:
        return JSONResponse({"error_code": "DATAARTS.0005", "error_msg": "job not found"},
                            status_code=404)
    job["status"] = "RUNNING"

    async def effect():
        j = next((x for x in s.dataarts_jobs.values() if x["job_id"] == job["job_id"]), None)
        if j:
            j["status"] = "SUCCEEDED"
        return None

    await s.jobs.submit("runDataArtsJob", {"job_name": job_name}, effect)
    return {"job_name": job_name, "status": "RUNNING"}


@router.delete("/v2/{pid}/jobs/{job_id}")
async def delete_job(request: Request, pid: str, job_id: str):
    """Delete a data job."""
    s = request.app.state.sim
    job = getattr(s, "dataarts_jobs", {}).get(job_id)
    if not job or job["project_id"] != pid:
        return JSONResponse({"error_code": "DATAARTS.0005", "error_msg": "job not found"},
                            status_code=404)
    del s.dataarts_jobs[job_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# scripts
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/scripts")
async def create_script(request: Request, pid: str):
    """Create a SQL script saved in DataArts."""
    s = request.app.state.sim
    if not hasattr(s, "dataarts_scripts"):
        s.dataarts_scripts = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "DATAARTS.0006", "error_msg": "name is required"},
                            status_code=400)
    scid = new_id()
    s.dataarts_scripts[scid] = {
        "script_id": scid, "name": name,
        "script_type": body.get("script_type", "FlinkSQL"),
        "content": body.get("content", ""), "project_id": pid,
        "created_at": now_millis(),
    }
    return {"script": s.dataarts_scripts[scid]}


@router.get("/v2/{pid}/scripts")
async def list_scripts(request: Request, pid: str):
    """List saved scripts."""
    s = request.app.state.sim
    scripts = [x for x in getattr(s, "dataarts_scripts", {}).values()
               if x["project_id"] == pid]
    return {"scripts": scripts, "total": len(scripts)}
