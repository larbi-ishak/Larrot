"""ModelArts — ML development: notebooks, training jobs, models."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/notebooks")
async def create_notebook(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_notebooks"): s.ma_notebooks = {}
    body = await request.json()
    nid = new_id()
    s.ma_notebooks[nid] = {"id": nid, "name": body.get("name", f"nb-{nid[:8]}"),
        "flavor": body.get("flavor", "modelarts.kat1.xlarge"),
        "status": "CREATING", "image_id": body.get("image_id", ""),
        "created_at": now_millis(), "project_id": pid}
    return {"id": nid, "name": s.ma_notebooks[nid]["name"], "status": "CREATING"}

@router.get("/v2/{pid}/notebooks")
async def list_notebooks(request: Request, pid: str):
    s = request.app.state.sim
    notebooks = [n for n in getattr(s, "ma_notebooks", {}).values() if n["project_id"] == pid]
    return {"notebooks": notebooks, "total": len(notebooks)}

@router.delete("/v2/{pid}/notebooks/{notebook_id}")
async def delete_notebook(request: Request, pid: str, notebook_id: str):
    s = request.app.state.sim
    if notebook_id not in getattr(s, "ma_notebooks", {}):
        return JSONResponse({"error_msg": "Notebook not found", "error_code": "MA.0001"}, status_code=404)
    del s.ma_notebooks[notebook_id]
    return Response(status_code=204)

@router.post("/v2/{pid}/training-jobs")
async def create_training_job(request: Request, pid: str):
    body = await request.json()
    jid = new_id()
    return {"id": jid, "name": body.get("name", f"job-{jid[:8]}"), "status": "SUBMITTED"}

@router.get("/v2/{pid}/training-jobs")
async def list_training_jobs(request: Request, pid: str):
    return {"jobs": [], "total": 0}

@router.post("/v2/{pid}/models")
async def create_model(request: Request, pid: str):
    body = await request.json()
    mid = new_id()
    return {"model_id": mid, "model_name": body.get("model_name", "my-model")}
