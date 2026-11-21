"""HPC: High Performance Computing clusters and nodes."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/hpc/clusters")
async def create_hpc_cluster(request: Request, pid: str):
    """Create an HPC cluster: bare-metal based high performance computing (async)."""
    s = request.app.state.sim
    if not hasattr(s, "hpc_clusters"): s.hpc_clusters = {}
    body = await request.json()
    cid = new_id()
    s.hpc_clusters[cid] = {
        "id": cid, "name": body.get("name", f"hpc-{cid[:8]}"),
        "status": "CREATING", "scheduler": body.get("scheduler", "slurm"),
        "node_count": 0, "max_node_count": body.get("max_node_count", 100),
        "network_id": body.get("network_id", ""),
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"cluster": s.hpc_clusters[cid]}


@router.get("/v2/{pid}/hpc/clusters")
async def list_hpc_clusters(request: Request, pid: str):
    """List HPC clusters."""
    s = request.app.state.sim
    clusters = [c for c in getattr(s, "hpc_clusters", {}).values() if c["project_id"] == pid]
    return {"clusters": clusters, "total": len(clusters)}


@router.get("/v2/{pid}/hpc/clusters/{cluster_id}")
async def show_hpc_cluster(request: Request, pid: str, cluster_id: str):
    """Show one cluster: its scheduler, network, and nodes."""
    s = request.app.state.sim
    c = getattr(s, "hpc_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_msg": "HPC cluster not found", "error_code": "HPC.0001"}, status_code=404)
    return {"cluster": c}


@router.delete("/v2/{pid}/hpc/clusters/{cluster_id}")
async def delete_hpc_cluster(request: Request, pid: str, cluster_id: str):
    """Delete an HPC cluster (async)."""
    s = request.app.state.sim
    if cluster_id not in getattr(s, "hpc_clusters", {}):
        return JSONResponse({"error_msg": "HPC cluster not found", "error_code": "HPC.0001"}, status_code=404)
    del s.hpc_clusters[cluster_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/hpc/clusters/{cluster_id}/nodes")
async def add_hpc_node(request: Request, pid: str, cluster_id: str):
    """Add a compute node to an HPC cluster (async)."""
    s = request.app.state.sim
    c = getattr(s, "hpc_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_msg": "HPC cluster not found", "error_code": "HPC.0001"}, status_code=404)
    body = await request.json()
    node_id = new_id()
    c["node_count"] += 1
    return {"node": {"id": node_id, "flavor": body.get("flavor", "hpc.large.4"),
                     "status": "ACTIVE", "cluster_id": cluster_id}}


@router.get("/v2/{pid}/hpc/clusters/{cluster_id}/nodes")
async def list_hpc_nodes(request: Request, pid: str, cluster_id: str):
    """List the compute nodes of an HPC cluster."""
    s = request.app.state.sim
    c = getattr(s, "hpc_clusters", {}).get(cluster_id)
    if not c or c["project_id"] != pid:
        return JSONResponse({"error_msg": "HPC cluster not found", "error_code": "HPC.0001"}, status_code=404)
    return {"nodes": [], "total": c["node_count"]}
