"""IEF (Intelligent EdgeFabric) — edge nodes, deployments, batches.

Real routes: GET/POST /v2/{project_id}/edgemgr/nodes,
POST /v2/{project_id}/edgemgr/deployments.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/edgemgr/nodes")
async def create_node(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ief_nodes"):
        s.ief_nodes = {}
    body = await request.json()
    name = body.get("node", {}).get("name", body.get("name", ""))
    if not name:
        return JSONResponse({"error_code": "IEF.0001", "error_msg": "name is required"},
                            status_code=400)
    nid = new_id()
    s.ief_nodes[nid] = {
        "id": nid, "name": name, "state": "unknown",
        "cpu": body.get("cpu", 4), "memory": body.get("memory", 8192),
        "os_name": body.get("os_name", "Ubuntu 22.04"),
        "architecture": body.get("architecture", "x86_64"),
        "device_num": 0, "gpu_num": 0,
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        n = s.ief_nodes.get(nid)
        if n:
            n["state"] = "running"  # edge agent connected
        return None

    await s.jobs.submit("createIefNode", {"node_id": nid}, effect)
    return {"node": s.ief_nodes[nid]}


@router.get("/v2/{pid}/edgemgr/nodes")
async def list_nodes(request: Request, pid: str):
    s = request.app.state.sim
    state_f = request.query_params.get("state")
    nodes = [n for n in getattr(s, "ief_nodes", {}).values()
             if n["project_id"] == pid]
    if state_f:
        nodes = [n for n in nodes if n["state"] == state_f]
    return {"nodes": nodes, "total": len(nodes)}


@router.get("/v2/{pid}/edgemgr/nodes/{node_id}")
async def show_node(request: Request, pid: str, node_id: str):
    s = request.app.state.sim
    n = getattr(s, "ief_nodes", {}).get(node_id)
    if not n or n["project_id"] != pid:
        return JSONResponse({"error_code": "IEF.0002", "error_msg": "node not found"},
                            status_code=404)
    return {"node": n}


@router.delete("/v2/{pid}/edgemgr/nodes/{node_id}")
async def delete_node(request: Request, pid: str, node_id: str):
    s = request.app.state.sim
    n = getattr(s, "ief_nodes", {}).get(node_id)
    if not n or n["project_id"] != pid:
        return JSONResponse({"error_code": "IEF.0002", "error_msg": "node not found"},
                            status_code=404)
    del s.ief_nodes[node_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# edge deployments (apps pushed to nodes)
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/edgemgr/deployments")
async def create_deployment(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ief_deployments"):
        s.ief_deployments = {}
    body = await request.json()
    dep = body.get("deployment", body)
    name = dep.get("name", "")
    node_ids = dep.get("node_ids", [])
    if not name:
        return JSONResponse({"error_code": "IEF.0003", "error_msg": "name is required"},
                            status_code=400)
    if not node_ids:
        return JSONResponse({"error_code": "IEF.0004",
                             "error_msg": "node_ids is required"}, status_code=400)
    for nid in node_ids:
        if nid not in getattr(s, "ief_nodes", {}):
            return JSONResponse({"error_code": "IEF.0002",
                                 "error_msg": f"node {nid} not found"}, status_code=404)
    did = new_id()
    s.ief_deployments[did] = {
        "id": did, "name": name, "node_ids": node_ids,
        "replicas": dep.get("replicas", 1),
        "containers": dep.get("containers", [{"name": "app", "image": "nginx:latest"}]),
        "state": "pending", "desired": dep.get("replicas", 1) * len(node_ids),
        "ready": 0, "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        d = s.ief_deployments.get(did)
        if d:
            d["state"] = "running"
            d["ready"] = d["desired"]
        return None

    await s.jobs.submit("createIefDeployment", {"deployment_id": did}, effect)
    return {"deployment": s.ief_deployments[did]}


@router.get("/v2/{pid}/edgemgr/deployments")
async def list_deployments(request: Request, pid: str):
    s = request.app.state.sim
    deployments = [d for d in getattr(s, "ief_deployments", {}).values()
                   if d["project_id"] == pid]
    return {"deployments": deployments, "total": len(deployments)}


@router.delete("/v2/{pid}/edgemgr/deployments/{deployment_id}")
async def delete_deployment(request: Request, pid: str, deployment_id: str):
    s = request.app.state.sim
    d = getattr(s, "ief_deployments", {}).get(deployment_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "IEF.0005",
                             "error_msg": "deployment not found"}, status_code=404)
    del s.ief_deployments[deployment_id]
    return Response(status_code=204)
