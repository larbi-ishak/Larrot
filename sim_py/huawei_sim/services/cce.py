"""CCE — Cloud Container Engine: clusters, nodes."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _cluster_json(c):
    return {
        "id": c["id"], "name": c["name"], "description": c.get("description", ""),
        "status": c.get("status", "Available"),
        "flavor": c.get("flavor", "cce.s1.small"),
        "version": c.get("version", "v1.29"),
        "network": c.get("network", {"vpcId": "", "subnetId": "", "cidr": "172.16.0.0/16"}),
        "node_count": len(c.get("nodes", [])),
        "created_at": c["created_at"], "updated_at": c["updated_at"],
        "enterprise_project_id": "0",
    }


def _node_json(n):
    return {
        "id": n["id"], "name": n["name"], "status": n.get("status", "Active"),
        "flavor": n.get("flavor", "s6.large.2"),
        "os": n.get("os", "EulerOS 2.9"),
        "role": n.get("role", "worker"),
        "cluster_id": n["cluster_id"],
        "private_ip": n.get("private_ip", ""),
        "public_ip": n.get("public_ip", ""),
        "created_at": n["created_at"], "updated_at": n["updated_at"],
    }


@router.post("/api/v3/projects/{pid}/clusters")
async def create_cluster(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "cce_clusters"):
        state.cce_clusters = {}
    body = await request.json()
    spec = body.get("cluster", body)
    cluster_id = new_id()
    now = now_millis()
    state.cce_clusters[cluster_id] = {
        "id": cluster_id, "name": spec.get("name", f"cluster-{cluster_id[:8]}"),
        "description": spec.get("description", ""),
        "flavor": spec.get("flavor", "cce.s1.small"),
        "version": spec.get("version", "v1.29"),
        "network": spec.get("network", {"vpcId": "", "subnetId": "", "cidr": "172.16.0.0/16"}),
        "status": "Creating", "nodes": [],
        "created_at": now, "updated_at": now, "project_id": pid,
    }

    import asyncio
    async def _flip():
        await asyncio.sleep(2.0)
        c = getattr(state, "cce_clusters", {}).get(cluster_id)
        if c:
            c["status"] = "Available"
            c["updated_at"] = now_millis()
    asyncio.get_event_loop().create_task(_flip())

    return JSONResponse({"cluster": _cluster_json(state.cce_clusters[cluster_id])}, status_code=201)


@router.get("/api/v3/projects/{pid}/clusters")
async def list_clusters(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "cce_clusters"):
        state.cce_clusters = {}
    clusters = [c for c in state.cce_clusters.values() if c["project_id"] == pid]
    return {"clusters": [_cluster_json(c) for c in clusters], "count": len(clusters)}


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}")
async def show_cluster(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_msg": "Cluster not found", "error_code": "CCE.0101"}, status_code=404)
    return {"cluster": _cluster_json(c)}


@router.delete("/api/v3/projects/{pid}/clusters/{cluster_id}")
async def delete_cluster(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_msg": "Cluster not found", "error_code": "CCE.0101"}, status_code=404)
    del state.cce_clusters[cluster_id]
    return Response(status_code=204)


@router.post("/api/v3/projects/{pid}/clusters/{cluster_id}/nodes")
async def create_node(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    cluster = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not cluster or cluster["project_id"] != pid:
        return JSONResponse({"error_msg": "Cluster not found", "error_code": "CCE.0101"}, status_code=404)
    body = await request.json()
    spec = body.get("node", body)
    node_id = new_id()
    now = now_millis()
    node = {
        "id": node_id, "name": spec.get("name", f"node-{node_id[:8]}"),
        "flavor": spec.get("flavor", "s6.large.2"),
        "os": spec.get("os", "EulerOS 2.9"),
        "role": spec.get("role", "worker"),
        "cluster_id": cluster_id,
        "private_ip": f"172.16.0.{10 + len(cluster['nodes'])}",
        "status": "Creating",
        "created_at": now, "updated_at": now,
    }
    cluster["nodes"].append(node)

    import asyncio
    async def _flip():
        await asyncio.sleep(2.0)
        n = cluster["nodes"][-1] if cluster["nodes"] else None
        if n and n["id"] == node_id:
            n["status"] = "Active"
            n["updated_at"] = now_millis()
    asyncio.get_event_loop().create_task(_flip())

    return JSONResponse({"node": _node_json(node)}, status_code=201)


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/nodes")
async def list_nodes(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    cluster = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not cluster or cluster["project_id"] != pid:
        return JSONResponse({"error_msg": "Cluster not found", "error_code": "CCE.0101"}, status_code=404)
    return {"nodes": [_node_json(n) for n in cluster["nodes"]], "count": len(cluster["nodes"])}
