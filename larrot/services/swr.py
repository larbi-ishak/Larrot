"""SWR — Software Repository for Container: namespaces, images."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/namespaces")
async def create_namespace(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "swr_namespaces"): s.swr_namespaces = {}
    body = await request.json()
    ns_name = body.get("namespace", f"ns-{new_id()[:8]}")
    s.swr_namespaces[ns_name] = {"name": ns_name, "creator": "sim",
        "created_at": now_millis(), "project_id": pid}
    return {"namespace": ns_name}

@router.get("/v2/{pid}/namespaces")
async def list_namespaces(request: Request, pid: str):
    s = request.app.state.sim
    namespaces = [n for n in getattr(s, "swr_namespaces", {}).values() if n["project_id"] == pid]
    return {"namespaces": [n["name"] for n in namespaces], "total": len(namespaces)}

@router.get("/v2/{pid}/namespaces/{namespace}/repos")
async def list_repos(request: Request, pid: str, namespace: str):
    return {"repos": [], "total": 0}

@router.post("/v2/{pid}/namespaces/{namespace}/repos")
async def create_repo(request: Request, pid: str, namespace: str):
    body = await request.json()
    return {"namespace": namespace, "repository": body.get("repository", "my-app"),
            "category": "software_app"}
