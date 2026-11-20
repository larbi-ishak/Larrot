"""SWR: Software Repository for Container: namespaces, images."""
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
    s = request.app.state.sim
    repos = [r for r in getattr(s, "swr_repos", {}).values()
             if r["project_id"] == pid and r["namespace"] == namespace]
    return {"repos": repos, "total": len(repos)}

@router.post("/v2/{pid}/namespaces/{namespace}/repos")
async def create_repo(request: Request, pid: str, namespace: str):
    s = request.app.state.sim
    if not hasattr(s, "swr_repos"):
        s.swr_repos = {}
    body = await request.json()
    repo_name = body.get("repository", "")
    if not repo_name:
        return JSONResponse({"error_msg": "repository is required",
                             "error_code": "SWR.0001"}, status_code=400)
    rid = new_id()
    s.swr_repos[rid] = {
        "id": rid, "namespace": namespace, "repository": repo_name,
        "category": body.get("category", "software_app"),
        "description": body.get("description", ""),
        "tags": [{"Tag": "latest", "digest": "sha256:sim" + rid[:12],
                   "size": 1024, "created_at": now_millis()}],
        "project_id": pid, "created_at": now_millis(),
    }
    return {"namespace": namespace, "repository": repo_name,
            "category": s.swr_repos[rid]["category"]}


@router.get("/v2/{pid}/namespaces/{namespace}/repos/{repo}/tags")
async def list_image_tags(request: Request, pid: str, namespace: str, repo: str):
    s = request.app.state.sim
    repo_obj = next((r for r in getattr(s, "swr_repos", {}).values()
                     if r["project_id"] == pid and r["namespace"] == namespace
                     and r["repository"] == repo), None)
    if not repo_obj:
        return JSONResponse({"error_msg": "repository not found", "error_code": "SWR.0001"}, status_code=404)
    return {"tags": repo_obj.get("tags", []), "total": len(repo_obj.get("tags", []))}
