"""CDN: domains, origins, cache rules, purge/preheat, statistics.

Real routes: POST /v1/domains, GET /v1/domains, DELETE /v1/domains/{domain_id},
POST /v1.0/purgecache, POST /v1.0/preheating, GET /v1.0/historytasks.
CDN is account-level (no project_id in the path).
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _domain_json(d):
    return {
        "id": d["id"], "domain_name": d["name"], "business_type": d["business_type"],
        "service_area": d["service_area"], "domain_status": d["status"],
        "sources": d["sources"], "created_at": d["created_at"],
        "modified_at": d["modified_at"],
    }


@router.post("/v1/domains")
async def create_domain(request: Request):
    s = request.app.state.sim
    if not hasattr(s, "cdn_domains"):
        s.cdn_domains = {}
    body = await request.json()
    name = body.get("domain_name", "")
    if not name:
        return JSONResponse({"error_code": "CDN.0001", "error_msg": "domain_name is required"},
                            status_code=400)
    if any(d["name"] == name for d in s.cdn_domains.values()):
        return JSONResponse({"error_code": "CDN.0002", "error_msg": "domain already exists"},
                            status_code=409)
    did = new_id()
    s.cdn_domains[did] = {
        "id": did, "name": name,
        "business_type": body.get("business_type", "web"),
        "service_area": body.get("service_area", "mainland_china"),
        "status": "configuring", "sources": body.get("sources", []),
        "created_at": now_millis(), "modified_at": now_millis(),
    }
    return JSONResponse({"domain": _domain_json(s.cdn_domains[did])}, status_code=200)


@router.get("/v1/domains")
async def list_domains(request: Request):
    s = request.app.state.sim
    domains = list(getattr(s, "cdn_domains", {}).values())
    state_f = request.query_params.get("domain_status")
    if state_f:
        domains = [d for d in domains if d["status"] == state_f]
    return {"domains": [_domain_json(d) for d in domains], "total": len(domains)}


@router.get("/v1/domains/{domain_id}")
async def show_domain(request: Request, domain_id: str):
    s = request.app.state.sim
    d = getattr(s, "cdn_domains", {}).get(domain_id)
    if not d:
        return JSONResponse({"error_code": "CDN.0003", "error_msg": "domain not found"},
                            status_code=404)
    return {"domain": _domain_json(d)}


@router.put("/v1/domains/{domain_id}")
async def update_domain(request: Request, domain_id: str):
    s = request.app.state.sim
    d = getattr(s, "cdn_domains", {}).get(domain_id)
    if not d:
        return JSONResponse({"error_code": "CDN.0003", "error_msg": "domain not found"},
                            status_code=404)
    body = await request.json()
    if "sources" in body:
        d["sources"] = body["sources"]
    if "service_area" in body:
        d["service_area"] = body["service_area"]
    d["modified_at"] = now_millis()
    return {"domain": _domain_json(d)}


@router.delete("/v1/domains/{domain_id}")
async def delete_domain(request: Request, domain_id: str):
    s = request.app.state.sim
    if domain_id not in getattr(s, "cdn_domains", {}):
        return JSONResponse({"error_code": "CDN.0003", "error_msg": "domain not found"},
                            status_code=404)
    del s.cdn_domains[domain_id]
    return Response(status_code=204)


@router.post("/v1.0/purgecache")
async def purge_cache(request: Request):
    """URL purge: returns a task id (real CDN: task completes async)."""
    s = request.app.state.sim
    if not hasattr(s, "cdn_tasks"):
        s.cdn_tasks = {}
    body = await request.json()
    urls = body.get("url", [])
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        return JSONResponse({"error_code": "CDN.0004", "error_msg": "url is required"},
                            status_code=400)
    tid = new_id()
    s.cdn_tasks[tid] = {
        "id": tid, "task_type": "purge", "status": "processing",
        "urls": urls, "url_processed_count": 0, "url_total": len(urls),
        "created_at": now_millis(),
    }

    async def effect():
        t = s.cdn_tasks.get(tid)
        if t:
            t["status"] = "done"
            t["url_processed_count"] = len(urls)
        return None

    await s.jobs.submit("purgeCache", {"task_id": tid}, effect)
    return {"id": tid, "task_type": "purge", "status": "processing"}


@router.post("/v1.0/preheating")
async def preheat(request: Request):
    """URL preheat: pushes content to edge nodes."""
    s = request.app.state.sim
    if not hasattr(s, "cdn_tasks"):
        s.cdn_tasks = {}
    body = await request.json()
    urls = body.get("url", [])
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        return JSONResponse({"error_code": "CDN.0004", "error_msg": "url is required"},
                            status_code=400)
    tid = new_id()
    s.cdn_tasks[tid] = {
        "id": tid, "task_type": "preheating", "status": "processing",
        "urls": urls, "url_processed_count": 0, "url_total": len(urls),
        "created_at": now_millis(),
    }

    async def effect():
        t = s.cdn_tasks.get(tid)
        if t:
            t["status"] = "done"
            t["url_processed_count"] = len(urls)
        return None

    await s.jobs.submit("preheating", {"task_id": tid}, effect)
    return {"id": tid, "task_type": "preheating", "status": "processing"}


@router.get("/v1.0/historytasks")
async def list_history_tasks(request: Request):
    s = request.app.state.sim
    task_type = request.query_params.get("task_type")
    tasks = list(getattr(s, "cdn_tasks", {}).values())
    if task_type:
        tasks = [t for t in tasks if t["task_type"] == task_type]
    return {"total": len(tasks), "tasks": [
        {"id": t["id"], "task_type": t["task_type"], "status": t["status"],
         "url_processed_count": t["url_processed_count"], "url_total": t["url_total"],
         "created_at": t["created_at"]} for t in tasks]}


@router.get("/v1.0/statistics")
async def cdn_statistics(request: Request):
    """Domain statistics: bandwidth, traffic, requests (synthetic)."""
    s = request.app.state.sim
    domains = list(getattr(s, "cdn_domains", {}).values())
    return {
        "start_time": request.query_params.get("start_time", ""),
        "end_time": request.query_params.get("end_time", ""),
        "data": [
            {"domain_name": d["name"], "bandwidth": 1024000,
             "traffic": 8589934592, "req_num": 100000, "hit_ratio": 0.95}
            for d in domains
        ],
    }
