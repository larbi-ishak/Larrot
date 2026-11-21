"""MRS (MapReduce Service): Hadoop/Spark/Hive clusters.

Real route: POST /v1.1/{project_id}/cluster_infos. Clusters go STARTING → RUNNING
via the async job engine.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

VALID_COMPONENTS = {"hadoop", "spark", "hive", "hbase", "kafka", "flume", "oozie", "presto"}


def _cluster_json(c):
    return {
        "clusterId": c["id"], "clusterName": c["name"], "clusterState": c["status"],
        "clusterType": c["type"], "version": c["version"],
        "componentInfos": c["components"], "nodeNum": c["nodes"],
        "billingType": "package", "createAt": c["created_at"],
        "masterNodeNum": 2, "coreNodeNum": max(c["nodes"] - 2, 1),
        "safeMode": c["safe_mode"],
    }


@router.post("/v1.1/{pid}/cluster_infos")
async def create_cluster(request: Request, pid: str):
    """Create an MRS cluster: the managed Hadoop/Spark/HBase big data platform (async)."""
    s = request.app.state.sim
    if not hasattr(s, "mrs_clusters"):
        s.mrs_clusters = {}
    body = await request.json()
    name = body.get("cluster_name", "")
    if not name:
        return JSONResponse({"error_code": "MRS.0001", "error_msg": "cluster_name is required"},
                            status_code=400)
    components = body.get("component_list", ["hadoop", "spark"])
    bad = [x for x in components if x not in VALID_COMPONENTS]
    if bad:
        return JSONResponse({"error_code": "MRS.0002",
                             "error_msg": f"invalid components: {','.join(bad)}"},
                            status_code=400)
    cid = new_id()
    s.mrs_clusters[cid] = {
        "id": cid, "name": name, "status": "STARTING",
        "type": body.get("cluster_type", "ANALYSIS"),
        "version": body.get("cluster_version", "MRS 3.2.0"),
        "components": components, "nodes": body.get("node_num", 3),
        "safe_mode": body.get("safe_mode", 0),
        "created_at": now_millis(), "project_id": pid,
    }

    async def effect():
        c = s.mrs_clusters.get(cid)
        if c:
            c["status"] = "RUNNING"
        return None

    await s.jobs.submit("createMrsCluster", {"cluster_id": cid}, effect)
    return _cluster_json(s.mrs_clusters[cid])


@router.get("/v1.1/{pid}/cluster_infos")
async def list_clusters(request: Request, pid: str):
    """List MRS clusters."""
    s = request.app.state.sim
    clusters = [c for c in getattr(s, "mrs_clusters", {}).values()
                if c["project_id"] == pid]
    return {"cluster_list": [_cluster_json(c) for c in clusters],
            "total": len(clusters)}


@router.get("/v1.1/{pid}/cluster_infos/{cluster_id}")
async def show_cluster(request: Request, pid: str, cluster_id: str):
    """Show one cluster: its master nodes, components, and software version."""
    s = request.app.state.sim
    c = getattr(s, "mrs_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "MRS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    return _cluster_json(c)


@router.delete("/v1.1/{pid}/cluster_infos/{cluster_id}")
async def delete_cluster(request: Request, pid: str, cluster_id: str):
    """Delete an MRS cluster (async)."""
    s = request.app.state.sim
    c = getattr(s, "mrs_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "MRS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    del s.mrs_clusters[cluster_id]
    return Response(status_code=204)


@router.post("/v1.1/{pid}/cluster_infos/{cluster_id}/jobs")
async def submit_job(request: Request, pid: str, cluster_id: str):
    """Submit a Spark/Hive job to a RUNNING cluster."""
    s = request.app.state.sim
    c = getattr(s, "mrs_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "MRS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    if c["status"] != "RUNNING":
        return JSONResponse({"error_code": "MRS.0004",
                             "error_msg": "cluster is not RUNNING"}, status_code=400)
    body = await request.json()
    jid = new_id()
    return {"job_id": jid, "job_name": body.get("job_name", f"job-{jid[:8]}"),
            "job_state": "SUBMITTED", "job_type": body.get("job_type", "SparkSubmit")}


@router.post("/v1.1/{pid}/cluster_infos/{cluster_id}/resize")
async def scale_cluster(request: Request, pid: str, cluster_id: str):
    """Scale core nodes (grow only: shrink is a separate real API)."""
    s = request.app.state.sim
    c = getattr(s, "mrs_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_code": "MRS.0003", "error_msg": "cluster not found"},
                            status_code=404)
    body = await request.json()
    new_nodes = body.get("node_num")
    if not isinstance(new_nodes, int) or new_nodes < c["nodes"]:
        return JSONResponse({"error_code": "MRS.0005",
                             "error_msg": "node_num must be >= current"}, status_code=400)
    c["nodes"] = new_nodes
    return _cluster_json(c)
