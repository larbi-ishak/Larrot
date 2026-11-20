"""DLI: Data Lake Insight: SQL jobs, databases, tables."""
from fastapi import APIRouter, Request
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1.0/{pid}/databases")
async def create_dli_database(request: Request, pid: str):
    body = await request.json()
    return {"database_name": body.get("database_name", "my_db"), "is_success": True}

@router.get("/v1.0/{pid}/databases")
async def list_dli_databases(request: Request, pid: str):
    return {"databases": [], "total": 0}

@router.post("/v1.0/{pid}/tables")
async def create_dli_table(request: Request, pid: str):
    body = await request.json()
    return {"table_name": body.get("table_name", "my_table"), "is_success": True}

@router.post("/v1.0/{pid}/jobs/submit")
async def submit_sql_job(request: Request, pid: str):
    body = await request.json()
    jid = new_id()
    return {"job_id": jid, "sql": body.get("sql", "SELECT 1"), "status": "SUBMITTED"}

@router.get("/v1.0/{pid}/jobs/{job_id}")
async def show_dli_job(request: Request, pid: str, job_id: str):
    return {"job_id": job_id, "status": "FINISHED", "result": "OK"}
