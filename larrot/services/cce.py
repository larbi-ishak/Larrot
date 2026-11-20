"""CCE: Cloud Container Engine: clusters, nodes."""

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


@router.post("/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools")
async def create_node_pool(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    if not hasattr(state, "cce_node_pools"):
        state.cce_node_pools = {}
    body = await request.json()
    npid = new_id()
    state.cce_node_pools[npid] = {
        "metadata": {"name": body.get("nodepool_name", f"nodepool-{npid[:8]}")},
        "status": {"phase": "Creating", "currentNode": 0},
        "spec": {"initialNodeCount": body.get("initialNodeCount", 1),
                  "flavor": body.get("flavor", "s6.large.2")},
        "cluster_id": cluster_id, "project_id": pid, "id": npid,
    }

    async def effect():
        np_ = state.cce_node_pools.get(npid)
        if np_:
            np_["status"] = {"phase": "Active", "currentNode": np_["spec"]["initialNodeCount"]}
        return None

    await state.jobs.submit("createNodePool", {"nodepool_id": npid}, effect)
    return {"nodepool": state.cce_node_pools[npid]}


@router.put("/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}")
async def update_node_pool(request: Request, pid: str, cluster_id: str, nodepool_id: str):
    state = request.app.state.sim
    np_ = getattr(state, "cce_node_pools", {}).get(nodepool_id)
    if not np_ or np_["project_id"] != pid or np_["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0102",
                                        "message": "node pool not found"}}, status_code=404)
    body = await request.json()
    spec = body.get("spec", {})
    if "initialNodeCount" in spec:
        np_["spec"]["initialNodeCount"] = spec["initialNodeCount"]
    return {"nodepool": np_}


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}")
async def show_node_pool(request: Request, pid: str, cluster_id: str, nodepool_id: str):
    state = request.app.state.sim
    np_ = getattr(state, "cce_node_pools", {}).get(nodepool_id)
    if not np_ or np_["project_id"] != pid or np_["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0102",
                                        "message": "node pool not found"}}, status_code=404)
    return {"nodepool": np_}


@router.delete("/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools/{nodepool_id}")
async def delete_node_pool(request: Request, pid: str, cluster_id: str, nodepool_id: str):
    state = request.app.state.sim
    np_ = getattr(state, "cce_node_pools", {}).get(nodepool_id)
    if not np_ or np_["project_id"] != pid or np_["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0102",
                                        "message": "node pool not found"}}, status_code=404)
    del state.cce_node_pools[nodepool_id]
    return Response(status_code=204)


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/nodepools")
async def list_node_pools(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    pools = [np_ for np_ in getattr(state, "cce_node_pools", {}).values()
             if np_["project_id"] == pid and np_["cluster_id"] == cluster_id]
    return {"nodepools": pools, "count": len(pools)}


@router.post("/api/v3/projects/{pid}/clusters/{cluster_id}/addons")
async def create_addon(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    if not hasattr(state, "cce_addons"):
        state.cce_addons = {}
    body = await request.json()
    aid = new_id()
    addon = {"metadata": {"id": aid,
                            "name": body.get("addon_name", body.get("itemName", "core-dns"))},
             "spec": {"version": body.get("version", "1.0.0"),
                       "clusterID": cluster_id},
             "status": {"state": "running"},
             "cluster_id": cluster_id, "project_id": pid, "id": aid}
    state.cce_addons[aid] = addon
    return {"addon": addon}


@router.put("/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}")
async def update_addon(request: Request, pid: str, cluster_id: str, addon_id: str):
    state = request.app.state.sim
    a = getattr(state, "cce_addons", {}).get(addon_id)
    if not a or a["project_id"] != pid or a["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0104",
                                        "message": "addon not found"}}, status_code=404)
    body = await request.json()
    spec = body.get("spec", {})
    if "version" in spec:
        a["spec"]["version"] = spec["version"]
    a["status"] = {"state": "running"}
    return {"addon": a}


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}")
async def show_addon(request: Request, pid: str, cluster_id: str, addon_id: str):
    state = request.app.state.sim
    a = getattr(state, "cce_addons", {}).get(addon_id)
    if not a or a["project_id"] != pid or a["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0104",
                                        "message": "addon not found"}}, status_code=404)
    return {"addon": a}


@router.delete("/api/v3/projects/{pid}/clusters/{cluster_id}/addons/{addon_id}")
async def delete_addon(request: Request, pid: str, cluster_id: str, addon_id: str):
    state = request.app.state.sim
    a = getattr(state, "cce_addons", {}).get(addon_id)
    if not a or a["project_id"] != pid or a["cluster_id"] != cluster_id:
        return JSONResponse({"error": {"code": "CCE.0104",
                                        "message": "addon not found"}}, status_code=404)
    del state.cce_addons[addon_id]
    return Response(status_code=204)


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/addons")
async def list_addons(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    addons = [a for a in getattr(state, "cce_addons", {}).values()
              if a["project_id"] == pid and a["cluster_id"] == cluster_id]
    return {"addons": addons, "count": len(addons)}


@router.put("/api/v3/projects/{pid}/clusters/{cluster_id}")
async def update_cluster(request: Request, pid: str, cluster_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    body = await request.json()
    spec = body.get("spec", {})
    if "description" in spec:
        c["description"] = spec["description"]
    if "displayName" in spec:
        c["name"] = spec["displayName"]
    return {"cluster": _cluster_json(c)}


@router.get("/api/v3/projects/{pid}/clusters/{cluster_id}/nodes/{node_id}")
async def show_node(request: Request, pid: str, cluster_id: str, node_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    n = next((x for x in c.get("nodes", []) if x["id"] == node_id), None)
    if not n:
        return JSONResponse({"error": {"code": "CCE.0103",
                                        "message": "node not found"}}, status_code=404)
    return {"node": n}


@router.delete("/api/v3/projects/{pid}/clusters/{cluster_id}/nodes/{node_id}")
async def delete_node(request: Request, pid: str, cluster_id: str, node_id: str):
    state = request.app.state.sim
    c = getattr(state, "cce_clusters", {}).get(cluster_id)
    if not c or c.get("project_id") != pid:
        return JSONResponse({"error": {"code": "CCE.0101",
                                        "message": "cluster not found"}}, status_code=404)
    before = len(c.get("nodes", []))
    c["nodes"] = [x for x in c.get("nodes", []) if x["id"] != node_id]
    if len(c["nodes"]) == before:
        return JSONResponse({"error": {"code": "CCE.0103",
                                        "message": "node not found"}}, status_code=404)
    return Response(status_code=204)
