"""APIG: API Gateway: custom APIs, groups."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/apigw/instances")
async def create_apig_instance(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_instances"): s.apig_instances = {}
    body = await request.json()
    iid = new_id()
    s.apig_instances[iid] = {"id": iid, "name": body.get("name", f"apig-{iid[:8]}"),
        "status": "Running", "spec": body.get("spec", "BASIC"),
        "created_at": now_millis(), "project_id": pid}
    return {"id": iid, "name": s.apig_instances[iid]["name"]}

@router.get("/v2/{pid}/apigw/instances")
async def list_apig_instances(request: Request, pid: str):
    s = request.app.state.sim
    instances = [i for i in getattr(s, "apig_instances", {}).values() if i["project_id"] == pid]
    return {"total": len(instances), "instances": instances}

@router.post("/v2/{pid}/apigw/groups")
async def create_api_group(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_groups"): s.apig_groups = {}
    body = await request.json()
    gid = new_id()
    s.apig_groups[gid] = {"id": gid, "name": body.get("name", f"group-{gid[:8]}"),
        "instance_id": body.get("instance_id", ""), "apis": [],
        "created_at": now_millis(), "project_id": pid}
    return {"id": gid, "name": s.apig_groups[gid]["name"]}

@router.get("/v2/{pid}/apigw/groups")
async def list_api_groups(request: Request, pid: str):
    s = request.app.state.sim
    groups = [g for g in getattr(s, "apig_groups", {}).values() if g["project_id"] == pid]
    return {"total": len(groups), "groups": groups}

@router.post("/v2/{pid}/apigw/apis")
async def create_api(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_apis"):
        s.apig_apis = {}
    body = await request.json()
    aid = new_id()
    s.apig_apis[aid] = {
        "id": aid, "name": body.get("name", f"api-{aid[:8]}"),
        "req_method": body.get("req_method", "GET"),
        "req_uri": body.get("req_uri", "/test"),
        "group_id": body.get("group_id", ""),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"id": aid, "name": s.apig_apis[aid]["name"],
            "req_method": s.apig_apis[aid]["req_method"],
            "req_uri": s.apig_apis[aid]["req_uri"]}


@router.get("/v2/{pid}/apigw/apis")
async def list_apig_apis(request: Request, pid: str):
    s = request.app.state.sim
    apis = [a for a in getattr(s, "apig_apis", {}).values() if a.get("project_id") == pid]
    return {"apis": apis, "total": len(apis)}


@router.post("/v2/{pid}/apigw/environments")
async def create_environment(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_environments"):
        s.apig_environments = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_msg": "name is required", "error_code": "APIG.0001"}, status_code=400)
    eid = new_id()
    s.apig_environments[eid] = {
        "id": eid, "name": name,
        "description": body.get("description", ""),
        "instance_id": body.get("instance_id", ""),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"id": eid, "name": name}


@router.get("/v2/{pid}/apigw/environments")
async def list_environments(request: Request, pid: str):
    s = request.app.state.sim
    envs = [e for e in getattr(s, "apig_environments", {}).values() if e["project_id"] == pid]
    return {"environments": envs, "total": len(envs)}


@router.get("/v2/{pid}/apigw/apis/{api_id}")
async def show_api(request: Request, pid: str, api_id: str):
    s = request.app.state.sim
    a = getattr(s, "apig_apis", {}).get(api_id)
    if not a or a.get("project_id") != pid:
        return JSONResponse({"error_msg": "API not found", "error_code": "APIG.0002"}, status_code=404)
    return a


@router.delete("/v2/{pid}/apigw/apis/{api_id}")
async def delete_api(request: Request, pid: str, api_id: str):
    s = request.app.state.sim
    a = getattr(s, "apig_apis", {}).get(api_id)
    if not a or a.get("project_id") != pid:
        return JSONResponse({"error_msg": "API not found", "error_code": "APIG.0002"}, status_code=404)
    del s.apig_apis[api_id]
    return Response(status_code=204)


@router.get("/v2/{pid}/apigw/instances/{instance_id}")
async def show_apig_instance(request: Request, pid: str, instance_id: str):
    s = request.app.state.sim
    i = getattr(s, "apig_instances", {}).get(instance_id)
    if not i or i.get("project_id") != pid:
        return JSONResponse({"error_msg": "Instance not found", "error_code": "APIG.0003"}, status_code=404)
    return i


@router.get("/v2/{pid}/apigw/groups/{group_id}")
async def show_apig_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "apig_groups", {}).get(group_id)
    if not g or g.get("project_id") != pid:
        return JSONResponse({"error_msg": "Group not found", "error_code": "APIG.0004"}, status_code=404)
    return g


@router.delete("/v2/{pid}/apigw/groups/{group_id}")
async def delete_apig_group(request: Request, pid: str, group_id: str):
    s = request.app.state.sim
    g = getattr(s, "apig_groups", {}).get(group_id)
    if not g or g.get("project_id") != pid:
        return JSONResponse({"error_msg": "Group not found", "error_code": "APIG.0004"}, status_code=404)
    del s.apig_groups[group_id]
    return Response(status_code=204)


@router.delete("/v2/{pid}/apigw/environments/{env_id}")
async def delete_apig_environment(request: Request, pid: str, env_id: str):
    s = request.app.state.sim
    e = getattr(s, "apig_environments", {}).get(env_id)
    if not e or e.get("project_id") != pid:
        return JSONResponse({"error_msg": "Environment not found", "error_code": "APIG.0005"}, status_code=404)
    del s.apig_environments[env_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/apigw/throttles")
async def create_throttle(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_throttles"):
        s.apig_throttles = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_msg": "name is required", "error_code": "APIG.0001"}, status_code=400)
    tid = new_id()
    s.apig_throttles[tid] = {
        "id": tid, "name": name,
        "time_interval": body.get("time_interval", 60000),
        "time_unit": body.get("time_unit", "MINUTE"),
        "api_call_num": body.get("api_call_num", 100),
        "app_call_limit": body.get("app_call_limit", 100),
        "description": body.get("description", ""),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"id": tid, "name": name}


@router.get("/v2/{pid}/apigw/throttles")
async def list_throttles(request: Request, pid: str):
    s = request.app.state.sim
    ts = [t for t in getattr(s, "apig_throttles", {}).values() if t["project_id"] == pid]
    return {"throttles": ts, "total": len(ts)}


@router.post("/v2/{pid}/apigw/apps")
async def create_app(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_apps"):
        s.apig_apps = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_msg": "name is required", "error_code": "APIG.0001"}, status_code=400)
    aid = new_id()
    s.apig_apps[aid] = {
        "id": aid, "name": name, "description": body.get("description", ""),
        "app_key": new_id()[:16], "app_secret": new_id()[:32],
        "project_id": pid, "created_at": now_millis(),
    }
    return {"id": aid, "name": name}


@router.get("/v2/{pid}/apigw/apps")
async def list_apps(request: Request, pid: str):
    s = request.app.state.sim
    apps = [a for a in getattr(s, "apig_apps", {}).values() if a["project_id"] == pid]
    return {"apps": apps, "total": len(apps)}


@router.get("/v2/{pid}/apigw/environments/{env_id}")
async def show_apig_environment(request: Request, pid: str, env_id: str):
    s = request.app.state.sim
    e = getattr(s, "apig_environments", {}).get(env_id)
    if not e or e.get("project_id") != pid:
        return JSONResponse({"error_msg": "Environment not found", "error_code": "APIG.0005"}, status_code=404)
    return e


@router.post("/v2/{pid}/apigw/app-auths")
async def create_app_auth(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "apig_app_auths"):
        s.apig_app_auths = {}
    body = await request.json()
    app_id = body.get("app_id", "")
    api_id = body.get("api_id", "")
    if not app_id or not api_id:
        return JSONResponse({"error_msg": "app_id and api_id are required",
                             "error_code": "APIG.0001"}, status_code=400)
    if app_id not in getattr(s, "apig_apps", {}):
        return JSONResponse({"error_msg": "App not found", "error_code": "APIG.0006"}, status_code=404)
    if api_id not in getattr(s, "apig_apis", {}):
        return JSONResponse({"error_msg": "API not found", "error_code": "APIG.0002"}, status_code=404)
    aid = new_id()
    s.apig_app_auths[aid] = {
        "id": aid, "app_id": app_id, "api_id": api_id,
        "env_id": body.get("env_id", ""),
        "auth_type": body.get("auth_type", "APP"),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"id": aid, "app_id": app_id, "api_id": api_id}


@router.get("/v2/{pid}/apigw/app-auths")
async def list_app_auths(request: Request, pid: str):
    s = request.app.state.sim
    auths = [a for a in getattr(s, "apig_app_auths", {}).values()
             if a["project_id"] == pid]
    return {"app_auths": auths, "total": len(auths)}


@router.get("/v2/{pid}/apigw/throttles/{throttle_id}")
async def show_throttle(request: Request, pid: str, throttle_id: str):
    s = request.app.state.sim
    t = getattr(s, "apig_throttles", {}).get(throttle_id)
    if not t or t.get("project_id") != pid:
        return JSONResponse({"error_msg": "Throttle not found", "error_code": "APIG.0007"}, status_code=404)
    return t


@router.delete("/v2/{pid}/apigw/throttles/{throttle_id}")
async def delete_throttle(request: Request, pid: str, throttle_id: str):
    s = request.app.state.sim
    t = getattr(s, "apig_throttles", {}).get(throttle_id)
    if not t or t.get("project_id") != pid:
        return JSONResponse({"error_msg": "Throttle not found", "error_code": "APIG.0007"}, status_code=404)
    del s.apig_throttles[throttle_id]
    return Response(status_code=204)


@router.get("/v2/{pid}/apigw/apps/{app_id}")
async def show_app(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    a = getattr(s, "apig_apps", {}).get(app_id)
    if not a or a.get("project_id") != pid:
        return JSONResponse({"error_msg": "App not found", "error_code": "APIG.0006"}, status_code=404)
    return a


@router.delete("/v2/{pid}/apigw/apps/{app_id}")
async def delete_app(request: Request, pid: str, app_id: str):
    s = request.app.state.sim
    a = getattr(s, "apig_apps", {}).get(app_id)
    if not a or a.get("project_id") != pid:
        return JSONResponse({"error_msg": "App not found", "error_code": "APIG.0006"}, status_code=404)
    del s.apig_apps[app_id]
    return Response(status_code=204)
