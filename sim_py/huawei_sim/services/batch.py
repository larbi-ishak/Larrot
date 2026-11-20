"""Batch Computing — batch job instances for HPC workloads."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()


@router.post("/v1/{pid}/batch/jobs")
async def create_batch_job(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "batch_jobs"): s.batch_jobs = {}
    body = await request.json()
    jid = new_id()
    s.batch_jobs[jid] = {
        "id": jid, "name": body.get("name", f"batch-{jid[:8]}"),
        "status": "PENDING", "image_id": body.get("image_id", ""),
        "flavor_id": body.get("flavor_id", "s6.large.2"),
        "instance_count": body.get("instance_count", 1),
        "command": body.get("command", "echo hello"),
        "environment": body.get("environment", {}),
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"job": s.batch_jobs[jid]}


@router.get("/v1/{pid}/batch/jobs")
async def list_batch_jobs(request: Request, pid: str):
    s = request.app.state.sim
    jobs = [j for j in getattr(s, "batch_jobs", {}).values() if j["project_id"] == pid]
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/v1/{pid}/batch/jobs/{job_id}")
async def show_batch_job(request: Request, pid: str, job_id: str):
    s = request.app.state.sim
    j = getattr(s, "batch_jobs", {}).get(job_id)
    if not j or j["project_id"] != pid:
        return JSONResponse({"error_msg": "Batch job not found", "error_code": "BATCH.0001"}, status_code=404)
    return {"job": j}


@router.delete("/v1/{pid}/batch/jobs/{job_id}")
async def delete_batch_job(request: Request, pid: str, job_id: str):
    s = request.app.state.sim
    if job_id not in getattr(s, "batch_jobs", {}):
        return JSONResponse({"error_msg": "Batch job not found", "error_code": "BATCH.0001"}, status_code=404)
    del s.batch_jobs[job_id]
    return Response(status_code=204)


@router.post("/v1/{pid}/batch/jobs/{job_id}/cancel")
async def cancel_batch_job(request: Request, pid: str, job_id: str):
    s = request.app.state.sim
    j = getattr(s, "batch_jobs", {}).get(job_id)
    if not j or j["project_id"] != pid:
        return JSONResponse({"error_msg": "Batch job not found", "error_code": "BATCH.0001"}, status_code=404)
    j["status"] = "CANCELLED"
    j["updated_at"] = now_millis()
    return {"job": j}
