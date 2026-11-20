"""DWS (GaussDB DWS): data warehouse clusters, snapshots, resize.

Real route: POST /v1.0/{project_id}/clusters on the DWS endpoint. Registered
under BOTH /v1.0/{pid}/clusters and /v1.0/{pid}/dws/clusters (the real cloud
separates DWS/CSS by endpoint hostname; this sim is single-port, so DWS keeps
the real path and CSS uses the /css/ namespace).
Clusters go CREATING → ACTIVE via the async job engine.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _cluster_json(c):
    return {
        "id": c["id"], "name": c["name"], "status": c["status"],
        "version": c["version"], "flavor": c["flavor"],
        "number_of_node": c["nodes"], "subnet_id": c["subnet_id"],
        "security_group_id": c["security_group_id"],
        "created_at": c["created_at"], "updated_at": c["updated_at"],
        "public_ip": None, "enterprise_project_id": "0",
    }


def _dws_error(code, msg):
    return JSONResponse({"error_code": code, "error_msg": msg}, status_code=404)


@router.post("/v1.0/{pid}/clusters")
@router.post("/v1.0/{pid}/dws/clusters")
async def create_cluster(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dws_clusters"):
        s.dws_clusters = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "DWS.0001", "error_msg": "name is required"},
                            status_code=400)
    nodes = body.get("number_of_node", body.get("number_of_cn", 3))
    if not isinstance(nodes, int) or nodes < 3:
        return JSONResponse({"error_code": "DWS.0002",
                             "error_msg": "number_of_node must be >= 3"}, status_code=400)
    cid = new_id()
    s.dws_clusters[cid] = {
        "id": cid, "name": name, "status": "CREATING",
        "version": body.get("version", "8.2.0"),
        "flavor": body.get("flavor", "dws.m3.xlarge"),
        "nodes": nodes, "subnet_id": body.get("subnet_id", ""),
        "security_group_id": body.get("security_group_id", ""),
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": pid,
    }

    async def effect():
        c = s.dws_clusters.get(cid)
        if c:
            c["status"] = "ACTIVE"
            c["updated_at"] = now_millis()
        return None

    await s.jobs.submit("createDwsCluster", {"cluster_id": cid}, effect)
    return {"cluster": _cluster_json(s.dws_clusters[cid])}


@router.get("/v1.0/{pid}/clusters")
@router.get("/v1.0/{pid}/dws/clusters")
async def list_clusters(request: Request, pid: str):
    s = request.app.state.sim
    clusters = [c for c in getattr(s, "dws_clusters", {}).values()
                if c["project_id"] == pid]
    return {"clusters": [_cluster_json(c) for c in clusters], "count": len(clusters)}


@router.get("/v1.0/{pid}/clusters/{cluster_id}")
@router.get("/v1.0/{pid}/dws/clusters/{cluster_id}")
async def show_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "dws_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return _dws_error("DWS.0003", "cluster not found")
    return {"cluster": _cluster_json(c)}


@router.delete("/v1.0/{pid}/clusters/{cluster_id}")
@router.delete("/v1.0/{pid}/dws/clusters/{cluster_id}")
async def delete_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "dws_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return _dws_error("DWS.0003", "cluster not found")
    del s.dws_clusters[cluster_id]
    return Response(status_code=204)


@router.post("/v1.0/{pid}/clusters/{cluster_id}/resize")
@router.post("/v1.0/{pid}/dws/clusters/{cluster_id}/resize")
async def resize_cluster(request: Request, pid: str, cluster_id: str):
    s = request.app.state.sim
    c = getattr(s, "dws_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return _dws_error("DWS.0003", "cluster not found")
    body = await request.json()
    new_size = body.get("number_of_node")
    if not isinstance(new_size, int) or new_size < 3:
        return JSONResponse({"error_code": "DWS.0002",
                             "error_msg": "number_of_node must be >= 3"}, status_code=400)
    old = c["nodes"]
    c["nodes"] = new_size
    c["updated_at"] = now_millis()
    return {"cluster": _cluster_json(c), "old_number_of_node": old}


@router.post("/v1.0/{pid}/snapshots")
@router.post("/v1.0/{pid}/dws/snapshots")
async def create_snapshot(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dws_snapshots"):
        s.dws_snapshots = {}
    body = await request.json()
    cid = body.get("cluster_id", "")
    c = getattr(s, "dws_clusters", {}).get(cid)
    if not c or c["project_id"] != pid:
        return _dws_error("DWS.0003", "cluster not found")
    snap_id = new_id()
    s.dws_snapshots[snap_id] = {
        "id": snap_id, "name": body.get("name", f"snap-{snap_id[:8]}"),
        "cluster_id": cid, "status": "CREATING",
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        snap = s.dws_snapshots.get(snap_id)
        if snap:
            snap["status"] = "AVAILABLE"
        return None

    await s.jobs.submit("createDwsSnapshot", {"snapshot_id": snap_id}, effect)
    return {"snapshot": s.dws_snapshots[snap_id]}


@router.get("/v1.0/{pid}/snapshots")
@router.get("/v1.0/{pid}/dws/snapshots")
async def list_snapshots(request: Request, pid: str):
    s = request.app.state.sim
    snaps = [x for x in getattr(s, "dws_snapshots", {}).values()
             if x["project_id"] == pid]
    return {"snapshots": snaps, "count": len(snaps)}


@router.delete("/v1.0/{pid}/snapshots/{snapshot_id}")
@router.delete("/v1.0/{pid}/dws/snapshots/{snapshot_id}")
async def delete_dws_snapshot(request: Request, pid: str, snapshot_id: str):
    s = request.app.state.sim
    snap = getattr(s, "dws_snapshots", {}).get(snapshot_id)
    if not snap or snap.get("project_id") != pid:
        return JSONResponse({"error_code": "DWS.0005",
                             "error_msg": "snapshot not found"}, status_code=404)
    del s.dws_snapshots[snapshot_id]
    return Response(status_code=204)


@router.get("/v1.0/{pid}/snapshots/{snapshot_id}")
@router.get("/v1.0/{pid}/dws/snapshots/{snapshot_id}")
async def show_dws_snapshot(request: Request, pid: str, snapshot_id: str):
    s = request.app.state.sim
    snap = getattr(s, "dws_snapshots", {}).get(snapshot_id)
    if not snap or snap.get("project_id") != pid:
        return JSONResponse({"error_code": "DWS.0005",
                             "error_msg": "snapshot not found"}, status_code=404)
    return {"snapshot": snap}
