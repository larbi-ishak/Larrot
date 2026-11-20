"""CodeArts: code repositories (CodeHub), pipelines, build tasks.

Real routes: POST /v2/projects/repositories (repos), POST /v2/{project_id}/pipelines
(pipelines). Build jobs use a simplified /v2/{pid}/builds.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/projects/repositories")
async def create_repo(request: Request):
    s = request.app.state.sim
    if not hasattr(s, "codearts_repos"):
        s.codearts_repos = {}
    body = await request.json()
    name = body.get("repository_name", body.get("name", ""))
    if not name:
        return JSONResponse({"error_code": "CODEARTS.0001",
                             "error_msg": "repository_name is required"}, status_code=400)
    if any(r["name"] == name for r in s.codearts_repos.values()):
        return JSONResponse({"error_code": "CODEARTS.0002",
                             "error_msg": "repository already exists"}, status_code=409)
    rid = new_id()
    s.codearts_repos[rid] = {
        "repository_id": rid, "name": name,
        "project_uuid": body.get("project_uuid", ""),
        "visibility": body.get("visibility", "private"),
        "default_branch": body.get("default_branch", "master"),
        "https_url": f"https://codehub.myhuaweicloud.com/{name}.git",
        "ssh_url": f"git@codehub.myhuaweicloud.com:~/{name}.git",
        "created_at": now_millis(),
    }
    return {"repository_id": rid, "repository_name": name,
            "https_url": s.codearts_repos[rid]["https_url"]}


@router.get("/v2/projects/repositories")
async def list_repos(request: Request):
    s = request.app.state.sim
    repos = list(getattr(s, "codearts_repos", {}).values())
    return {"repositories": repos, "total": len(repos)}


@router.get("/v2/projects/repositories/{repo_id}")
async def show_repo(request: Request, repo_id: str):
    s = request.app.state.sim
    r = getattr(s, "codearts_repos", {}).get(repo_id)
    if not r:
        return JSONResponse({"error_code": "CODEARTS.0003",
                             "error_msg": "repository not found"}, status_code=404)
    return r


@router.delete("/v2/projects/repositories/{repo_id}")
async def delete_repo(request: Request, repo_id: str):
    s = request.app.state.sim
    if repo_id not in getattr(s, "codearts_repos", {}):
        return JSONResponse({"error_code": "CODEARTS.0003",
                             "error_msg": "repository not found"}, status_code=404)
    del s.codearts_repos[repo_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# pipelines
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/pipelines")
async def create_pipeline(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "codearts_pipelines"):
        s.codearts_pipelines = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CODEARTS.0004",
                             "error_msg": "name is required"}, status_code=400)
    plid = new_id()
    s.codearts_pipelines[plid] = {
        "pipeline_id": plid, "name": name,
        "stages": body.get("stages", ["build", "deploy"]),
        "status": "IDLE", "project_id": pid, "created_at": now_millis(),
    }
    return {"pipeline_id": plid, "name": name, "status": "IDLE"}


@router.get("/v2/{pid}/pipelines")
async def list_pipelines(request: Request, pid: str):
    s = request.app.state.sim
    pipelines = [p for p in getattr(s, "codearts_pipelines", {}).values()
                 if p["project_id"] == pid]
    return {"pipelines": pipelines, "total": len(pipelines)}


@router.post("/v2/{pid}/pipelines/{pipeline_id}/run")
async def run_pipeline(request: Request, pid: str, pipeline_id: str):
    """Run a pipeline: goes RUNNING → SUCCESS via the async job engine."""
    s = request.app.state.sim
    p = getattr(s, "codearts_pipelines", {}).get(pipeline_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_code": "CODEARTS.0005",
                             "error_msg": "pipeline not found"}, status_code=404)
    run_id = new_id()
    p["status"] = "RUNNING"
    p["last_run_id"] = run_id

    async def effect():
        pl = s.codearts_pipelines.get(pipeline_id)
        if pl:
            pl["status"] = "SUCCESS"
        return None

    await s.jobs.submit("runPipeline", {"pipeline_id": pipeline_id}, effect)
    return {"run_id": run_id, "pipeline_id": pipeline_id, "status": "RUNNING"}


@router.delete("/v2/{pid}/pipelines/{pipeline_id}")
async def delete_pipeline(request: Request, pid: str, pipeline_id: str):
    s = request.app.state.sim
    p = getattr(s, "codearts_pipelines", {}).get(pipeline_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_code": "CODEARTS.0005",
                             "error_msg": "pipeline not found"}, status_code=404)
    del s.codearts_pipelines[pipeline_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# build tasks
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/builds")
async def create_build(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "codearts_builds"):
        s.codearts_builds = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CODEARTS.0006",
                             "error_msg": "name is required"}, status_code=400)
    bid = new_id()
    s.codearts_builds[bid] = {
        "build_id": bid, "name": name, "status": "IDLE",
        "params": body.get("params", {}), "project_id": pid,
        "created_at": now_millis(),
    }
    return {"build_id": bid, "name": name}


@router.get("/v2/{pid}/builds")
async def list_builds(request: Request, pid: str):
    s = request.app.state.sim
    builds = [b for b in getattr(s, "codearts_builds", {}).values()
              if b["project_id"] == pid]
    return {"builds": builds, "total": len(builds)}


@router.post("/v2/{pid}/builds/{build_id}/run")
async def run_build(request: Request, pid: str, build_id: str):
    s = request.app.state.sim
    b = getattr(s, "codearts_builds", {}).get(build_id)
    if not b or b["project_id"] != pid:
        return JSONResponse({"error_code": "CODEARTS.0007",
                             "error_msg": "build not found"}, status_code=404)
    b["status"] = "RUNNING"
    record_id = new_id()

    async def effect():
        x = s.codearts_builds.get(build_id)
        if x:
            x["status"] = "SUCCESS"
        return None

    await s.jobs.submit("runBuild", {"build_id": build_id}, effect)
    return {"record_id": record_id, "build_id": build_id, "status": "RUNNING"}
