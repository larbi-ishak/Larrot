"""CSE (Cloud Service Engine) — microservice engines (ServiceComb).

Real route: POST /v2/{project_id}/engines. Engines go Creating → Available via
the async job engine.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/engines")
async def create_engine(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "cse_engines"):
        s.cse_engines = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CSE.0001", "error_msg": "name is required"},
                            status_code=400)
    flavor = body.get("flavor", "cse.s1.small.2")
    eid = new_id()
    s.cse_engines[eid] = {
        "id": eid, "name": name, "status": "Creating",
        "flavor": flavor, "version": body.get("version", "2.7.3"),
        "description": body.get("description", ""),
        "authType": body.get("authType", "RBAC"),
        "serviceLimit": body.get("serviceLimit", 1000),
        "instanceLimit": body.get("instanceLimit", 10000),
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        e = s.cse_engines.get(eid)
        if e:
            e["status"] = "Available"
        return None

    await s.jobs.submit("createCseEngine", {"engine_id": eid}, effect)
    return {"id": eid, "name": name, "status": "Creating"}


@router.get("/v2/{pid}/engines")
async def list_engines(request: Request, pid: str):
    s = request.app.state.sim
    engines = [e for e in getattr(s, "cse_engines", {}).values()
               if e["project_id"] == pid]
    return {"engines": engines, "total": len(engines)}


@router.get("/v2/{pid}/engines/{engine_id}")
async def show_engine(request: Request, pid: str, engine_id: str):
    s = request.app.state.sim
    e = getattr(s, "cse_engines", {}).get(engine_id)
    if not e or e["project_id"] != pid:
        return JSONResponse({"error_code": "CSE.0002", "error_msg": "engine not found"},
                            status_code=404)
    return e


@router.delete("/v2/{pid}/engines/{engine_id}")
async def delete_engine(request: Request, pid: str, engine_id: str):
    s = request.app.state.sim
    e = getattr(s, "cse_engines", {}).get(engine_id)
    if not e or e["project_id"] != pid:
        return JSONResponse({"error_code": "CSE.0002", "error_msg": "engine not found"},
                            status_code=404)
    del s.cse_engines[engine_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# microservices registered on an engine
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/engines/{engine_id}/microservices")
async def register_microservice(request: Request, pid: str, engine_id: str):
    s = request.app.state.sim
    e = getattr(s, "cse_engines", {}).get(engine_id)
    if not e or e["project_id"] != pid:
        return JSONResponse({"error_code": "CSE.0002", "error_msg": "engine not found"},
                            status_code=404)
    if e["status"] != "Available":
        return JSONResponse({"error_code": "CSE.0003",
                             "error_msg": "engine is not Available"}, status_code=400)
    if not hasattr(s, "cse_microservices"):
        s.cse_microservices = {}
    body = await request.json()
    name = body.get("serviceName", body.get("service_name", ""))
    if not name:
        return JSONResponse({"error_code": "CSE.0004",
                             "error_msg": "serviceName is required"}, status_code=400)
    msid = new_id()
    s.cse_microservices[msid] = {
        "serviceId": msid, "serviceName": name, "engine_id": engine_id,
        "environment": body.get("environment", "production"),
        "appId": body.get("appId", "default"),
        "version": body.get("version", "1.0.0"),
        "status": "UP", "instances": body.get("instances", 1),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"serviceId": msid, "serviceName": name}


@router.get("/v2/{pid}/engines/{engine_id}/microservices")
async def list_microservices(request: Request, pid: str, engine_id: str):
    s = request.app.state.sim
    e = getattr(s, "cse_engines", {}).get(engine_id)
    if not e or e["project_id"] != pid:
        return JSONResponse({"error_code": "CSE.0002", "error_msg": "engine not found"},
                            status_code=404)
    services = [m for m in getattr(s, "cse_microservices", {}).values()
                if m["project_id"] == pid and m["engine_id"] == engine_id]
    return {"microservices": services, "total": len(services)}
