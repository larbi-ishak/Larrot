"""EPS: Enterprise Project Service."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

@router.post("/v1.0/enterprise-projects")
async def create_eps(request: Request):
    """Create an enterprise project: the container for organizing and isolating cloud resources."""
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
    """List enterprise projects."""
    s = request.app.state.sim
    projects = list(getattr(s, "eps_projects", {}).values())
    return {"enterprise_projects": projects, "total_count": len(projects)}

@router.get("/v1.0/enterprise-projects/{eps_id}")
async def show_eps(request: Request, eps_id: str):
    """Show one enterprise project: its status and description."""
    s = request.app.state.sim
    p = getattr(s, "eps_projects", {}).get(eps_id)
    if not p:
        return JSONResponse({"error_msg": "EPS not found", "error_code": "EPS.0001"}, status_code=404)
    return p

@router.put("/v1.0/enterprise-projects/{eps_id}")
async def update_enterprise_project(request: Request, eps_id: str):
    """Update an enterprise project's name or description."""
    s = request.app.state.sim
    e = getattr(s, "eps_projects", {}).get(eps_id)
    if not e:
        return JSONResponse({"error_code": "EPS.0001", "error_msg": "not found"}, status_code=404)
    body = await request.json()
    for field in ("name", "description"):
        if field in body:
            e[field] = body[field]
    return e


@router.delete("/v1.0/enterprise-projects/{eps_id}")
async def delete_eps(request: Request, eps_id: str):
    """Delete an enterprise project (must be empty of resources)."""
    s = request.app.state.sim
    if eps_id not in getattr(s, "eps_projects", {}):
        return JSONResponse({"error_msg": "EPS not found", "error_code": "EPS.0001"}, status_code=404)
    del s.eps_projects[eps_id]
    return Response(status_code=204)
