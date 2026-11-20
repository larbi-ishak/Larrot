"""CSS (Cloud Search Service): Elasticsearch clusters and indices.

Real route is POST /v1.0/{project_id}/clusters on the CSS endpoint; this sim
uses /v1.0/{pid}/css/clusters because single-port DWS owns the bare path.
Clusters go CREATING → RUNNING via the async job engine.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _cluster_json(c):
    return {
        "id": c["id"], "name": c["name"], "status": c["status"],
        "version": c["version"], "engine": "elasticsearch",
        "flavor": c["flavor"], "instance_num": c["nodes"],
        "datastore": {"type": "elasticsearch", "version": c["version"]},
        "https_enabled": c["https_enabled"], "disk_type": c["disk_type"],
        "created_at": c["created_at"], "endpoint": c["endpoint"],
        "enterprise_project_id": "0",
    }


@router.post("/v1.0/{pid}/css/clusters")
async def create_cluster(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "css_clusters"):
        s.css_clusters = {}
    if not hasattr(s, "css_indices"):
        s.css_indices = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CSS.0001", "error_msg": "name is required"},
                            status_code=400)
    nodes = body.get("instance_num", body.get("instance", 3))
    if not isinstance(nodes, int) or nodes < 1:
        return JSONResponse({"error_code": "CSS.0002",
                             "error_msg": "instance_num must be >= 1"}, status_code=400)
    cid = new_id()
    s.css_clusters[cid] = {
        "id": cid, "name": name, "status": "CREATING",
        "version": body.get("datastore", {}).get("version", "7.10.2"),
        "flavor": body.get("flavor", "ess.spec-4u16g"),
        "nodes": nodes, "https_enabled": body.get("https_enabled", True),
        "disk_type": body.get("disk_type", "high"),
        "endpoint": f"ff808082-{cid[:8]}.css.myhuaweicloud.com:9200",
        "created_at": now_millis(), "project_id": pid,
    }
    s.css_indices[cid] = {}

    async def effect():
        c = s.css_clusters.get(cid)
        if c:
            c["status"] = "RUNNING"
        return None

    await s.jobs.submit("createCssCluster", {"cluster_id": cid}, effect)
    return {"cluster": _cluster_json(s.css_clusters[cid])}


@router.get("/v1.0/{pid}/css/clusters")
async def list_clusters(request: Request, pid: str):
    s = request.app.state.sim
    clusters = [c for c in getattr(s, "css_clusters", {}).values()
                if c["project_id"] == pid]
    return {"clusters": [_cluster_json(c) for c in clusters]}


@router.get("/v1.0/{pid}/css/clusters/{cluster_id}")
async def show_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    return {"cluster": _cluster_json(c)}


@router.delete("/v1.0/{pid}/css/clusters/{cluster_id}")
async def delete_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    del s.css_clusters[cluster_id]
    s.css_indices.pop(cluster_id, None)
    return Response(status_code=204)


@router.post("/v1.0/{pid}/css/clusters/{cluster_id}/restart")
async def restart_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    c["status"] = "RESTARTING"

    async def effect():
        x = s.css_clusters.get(cluster_id)
        if x:
            x["status"] = "RUNNING"
        return None

    job_id = await s.jobs.submit("restartCssCluster", {"cluster_id": cluster_id}, effect)
    return {"job_id": job_id, "status": "RESTARTING"}


# ---------------------------------------------------------------------------
# index management (real CSS proxies these through the ES API)
# ---------------------------------------------------------------------------

@router.post("/v1.0/{pid}/css/clusters/{cluster_id}/indices")
async def create_index(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    body = await request.json()
    index_name = body.get("index_name", "")
    if not index_name:
        return JSONResponse({"error_code": "CSS.0004",
                             "error_msg": "index_name is required"}, status_code=400)
    s.css_indices[cluster_id][index_name] = {
        "index_name": index_name, "doc_count": 0,
        "shards": body.get("shards", 3), "replicas": body.get("replicas", 1),
        "created_at": now_millis(),
    }
    return {"index": s.css_indices[cluster_id][index_name], "acknowledged": True}


@router.get("/v1.0/{pid}/css/clusters/{cluster_id}/indices")
async def list_indices(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    indices = list(s.css_indices.get(cluster_id, {}).values())
    return {"indices": indices, "total": len(indices)}


@router.delete("/v1.0/{pid}/css/clusters/{cluster_id}/indices/{index_name}")
async def delete_index(request: Request, pid: str, cluster_id: str, index_name: str):
    s = request.app.state.sim
    c = getattr(s, "css_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "CSS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    if index_name not in s.css_indices.get(cluster_id, {}):
        return JSONResponse({"error_code": "CSS.0005", "error_msg": "index not found"},
                            status_code=404)
    del s.css_indices[cluster_id][index_name]
    return {"acknowledged": True}
