"""EPS: Enterprise Project Service."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1.0/enterprise-projects")
async def create_eps(request: Request):
    s = request.app.state.sim
    if not hasattr(s, "eps_projects"): s.eps_projects = {}
    body = await request.json()
    eid = new_id()
    s.eps_projects[eid] = {"id": eid, "name": body.get("name", f"eps-{eid[:8]}"),
        "description": body.get("description", ""), "status": "1",
        "created_at": now_millis()}
    return {"id": eid, "name": s.eps_projects[eid]["name"]}

@router.get("/v1.0/enterprise-projects")
async def list_eps(request: Request):
    s = request.app.state.sim
    projects = list(getattr(s, "eps_projects", {}).values())
    return {"enterprise_projects": projects, "total_count": len(projects)}

@router.get("/v1.0/enterprise-projects/{eps_id}")
async def show_eps(request: Request, eps_id: str):
    s = request.app.state.sim
    p = getattr(s, "eps_projects", {}).get(eps_id)
    if not p:
        return JSONResponse({"error_msg": "EPS not found", "error_code": "EPS.0001"}, status_code=404)
    return p

@router.delete("/v1.0/enterprise-projects/{eps_id}")
async def delete_eps(request: Request, eps_id: str):
    s = request.app.state.sim
    if eps_id not in getattr(s, "eps_projects", {}):
        return JSONResponse({"error_msg": "EPS not found", "error_code": "EPS.0001"}, status_code=404)
    del s.eps_projects[eps_id]
    return Response(status_code=204)
