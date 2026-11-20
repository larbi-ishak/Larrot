"""ServiceStage: environments, applications, components (app hosting).

Real routes: POST /v2/{project_id}/cas/environments, /v2/{project_id}/cas/applications,
/v2/{project_id}/cas/applications/{app_id}/components.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/cas/environments")
async def create_environment(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "cas_environments"):
        s.cas_environments = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CAS.0001", "error_msg": "name is required"},
                            status_code=400)
    vpc_id = body.get("vpc_id", "")
    if vpc_id and (not s.vpcs.get(vpc_id) or s.vpcs[vpc_id].get("project_id") != pid):
        return JSONResponse({"error_code": "CAS.0002", "error_msg": "vpc not found"},
                            status_code=404)
    eid = new_id()
    s.cas_environments[eid] = {
        "id": eid, "name": name, "vpc_id": vpc_id or s.project(pid)["vpc_id"],
        "description": body.get("description", ""),
        "status": "CREATING", "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        e = s.cas_environments.get(eid)
        if e:
            e["status"] = "READY"
        return None

    await s.jobs.submit("createCasEnvironment", {"environment_id": eid}, effect)
    return {"environment": s.cas_environments[eid]}


@router.get("/v2/{pid}/cas/environments")
async def list_environments(request: Request, pid: str):
    s = request.app.state.sim
    envs = [e for e in getattr(s, "cas_environments", {}).values()
            if e["project_id"] == pid]
    return {"environments": envs, "total": len(envs)}


@router.delete("/v2/{pid}/cas/environments/{env_id}")
async def delete_environment(request: Request, pid: str, env_id: str):
    s = request.app.state.sim
    e = getattr(s, "cas_environments", {}).get(env_id)
    if not e or e["project_id"] != pid:
        return JSONResponse({"error_code": "CAS.0003", "error_msg": "environment not found"},
                            status_code=404)
    del s.cas_environments[env_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# applications
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/cas/applications")
async def create_application(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "cas_applications"):
        s.cas_applications = {}
    if not hasattr(s, "cas_components"):
        s.cas_components = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CAS.0004", "error_msg": "name is required"},
                            status_code=400)
    aid = new_id()
    s.cas_applications[aid] = {
        "id": aid, "name": name, "component_num": 0,
        "description": body.get("description", ""),
        "project_id": pid, "created_at": now_millis(),
    }
    s.cas_components[aid] = []
    return {"application": s.cas_applications[aid]}


@router.get("/v2/{pid}/cas/applications")
async def list_applications(request: Request, pid: str):
    s = request.app.state.sim
    apps = [a for a in getattr(s, "cas_applications", {}).values()
            if a["project_id"] == pid]
    return {"applications": apps, "total": len(apps)}


@router.get("/v2/{pid}/cas/applications/{app_id}")
async def show_application(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    a = getattr(s, "cas_applications", {}).get(app_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "CAS.0005", "error_msg": "application not found"},
                            status_code=404)
    return {"application": a}


@router.delete("/v2/{pid}/cas/applications/{app_id}")
async def delete_application(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    a = getattr(s, "cas_applications", {}).get(app_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "CAS.0005", "error_msg": "application not found"},
                            status_code=404)
    del s.cas_applications[app_id]
    s.cas_components.pop(app_id, None)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# components (deployable units within an application)
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/cas/applications/{app_id}/components")
async def create_component(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    app = getattr(s, "cas_applications", {}).get(app_id)
    if not app or app["project_id"] != pid:
        return JSONResponse({"error_code": "CAS.0005", "error_msg": "application not found"},
                            status_code=404)
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CAS.0006", "error_msg": "name is required"},
                            status_code=400)
    env_id = body.get("environment_id", "")
    if env_id not in getattr(s, "cas_environments", {}):
        return JSONResponse({"error_code": "CAS.0003", "error_msg": "environment not found"},
                            status_code=404)
    cid = new_id()
    component = {
        "component_id": cid, "name": name, "application_id": app_id,
        "environment_id": env_id, "runtime": body.get("runtime", "Docker"),
        "replica_count": body.get("replica_count", 1),
        "status": "CREATING", "created_at": now_millis(), "project_id": pid,
    }
    s.cas_components[app_id].append(component)
    app["component_num"] += 1

    async def effect():
        c = next((x for x in s.cas_components.get(app_id, [])
                  if x["component_id"] == cid), None)
        if c:
            c["status"] = "RUNNING"
        return None

    await s.jobs.submit("createCasComponent", {"component_id": cid}, effect)
    return {"component": component}


@router.get("/v2/{pid}/cas/applications/{app_id}/components")
async def list_components(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    app = getattr(s, "cas_applications", {}).get(app_id)
    if not app or app["project_id"] != pid:
        return JSONResponse({"error_code": "CAS.0005", "error_msg": "application not found"},
                            status_code=404)
    components = s.cas_components.get(app_id, [])
    return {"components": components, "total": len(components)}
