"""DLI: Data Lake Insight: SQL jobs, databases, tables."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1.0/{pid}/databases")
async def create_dli_database(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dli_databases"):
        s.dli_databases = {}
    body = await request.json()
    name = body.get("database_name", "")
    if not name:
        return JSONResponse({"error_code": "DLI.0001",
                             "error_msg": "database_name is required"}, status_code=400)
    s.dli_databases[name] = {"database_name": name, "description": body.get("description", ""),
                              "project_id": pid, "created_at": now_millis()}
    return {"database_name": name, "is_success": True}

@router.get("/v1.0/{pid}/databases")
async def list_dli_databases(request: Request, pid: str):
    s = request.app.state.sim
    dbs = [d for d in getattr(s, "dli_databases", {}).values() if d["project_id"] == pid]
    return {"databases": dbs, "total": len(dbs)}

@router.delete("/v1.0/{pid}/databases/{database_name}")
async def delete_dli_database(request: Request, pid: str, database_name: str):
    s = request.app.state.sim
    d = getattr(s, "dli_databases", {}).get(database_name)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "DLI.0002", "error_msg": "database not found"},
                            status_code=404)
    del s.dli_databases[database_name]
    return {"is_success": True}

@router.post("/v1.0/{pid}/tables")
async def create_dli_table(request: Request, pid: str):
    body = await request.json()
    return {"table_name": body.get("table_name", "my_table"), "is_success": True}

@router.post("/v1.0/{pid}/jobs/submit")
async def submit_sql_job(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dli_jobs"):
        s.dli_jobs = {}
    body = await request.json()
    jid = new_id()
    s.dli_jobs[jid] = {"job_id": jid, "sql": body.get("sql", "SELECT 1"),
                         "queue_name": body.get("queue_name", "default"),
                         "status": "RUNNING", "rows": 0,
                         "project_id": pid, "created_at": now_millis()}

    async def _finish():
        j = s.dli_jobs.get(jid)
        if j:
            j["status"] = "FINISHED"
            j["rows"] = 42
        return None

    await s.jobs.submit("runDliSql", {"job_id": jid}, _finish)
    return {"job_id": jid, "sql": body.get("sql", "SELECT 1"), "status": "RUNNING"}

@router.get("/v1.0/{pid}/jobs/{job_id}")
async def show_dli_job(request: Request, pid: str, job_id: str):
    s = request.app.state.sim
    j = getattr(s, "dli_jobs", {}).get(job_id)
    if not j or j["project_id"] != pid:
        return JSONResponse({"error_code": "DLI.0003", "error_msg": "job not found"},
                            status_code=404)
    return j


# ---------------------------------------------------------------------------
# sub-APIs: queues, table/database listing, job listing
# ---------------------------------------------------------------------------

@router.post("/v1.0/{pid}/queues")
async def create_dli_queue(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dli_queues"):
        s.dli_queues = {}
    body = await request.json()
    name = body.get("queue_name", "")
    if not name:
        return JSONResponse({"error_code": "DLI.0001",
                             "error_msg": "queue_name is required"}, status_code=400)
    qid = new_id()
    s.dli_queues[qid] = {"queue_id": qid, "queue_name": name,
                           "cu_count": body.get("cu_count", 16),
                           "status": "RUNNING", "project_id": pid,
                           "created_at": now_millis()}
    return {"queue_id": qid, "queue_name": name}


@router.get("/v1.0/{pid}/queues")
async def list_dli_queues(request: Request, pid: str):
    s = request.app.state.sim
    queues = [q for q in getattr(s, "dli_queues", {}).values()
              if q["project_id"] == pid]
    return {"queues": queues, "total": len(queues)}


@router.delete("/v1.0/{pid}/queues/{queue_id}")
async def delete_dli_queue(request: Request, pid: str, queue_id: str):
    s = request.app.state.sim
    if queue_id not in getattr(s, "dli_queues", {}):
        return JSONResponse({"error_code": "DLI.0002", "error_msg": "queue not found"},
                            status_code=404)
    del s.dli_queues[queue_id]
    return {"is_success": True}


@router.get("/v1.0/{pid}/jobs")
async def list_dli_jobs(request: Request, pid: str):
    s = request.app.state.sim
    jobs = [j for j in getattr(s, "dli_jobs", {}).values() if j["project_id"] == pid]
    return {"jobs": jobs, "total": len(jobs)}
