"""CCI (Cloud Container Instance): serverless containers: namespaces, pods.

The real CCI API is Kubernetes-style (/apis/...); this sim exposes a simplified
REST surface under /v1/{pid}/cci/. Pods go Pending → Running via the async
job engine, mirroring k8s pod startup.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/cci/namespaces")
async def create_namespace(request: Request, pid: str):
    """Create a CCI namespace: the Kubernetes-style isolation unit for serverless containers."""
    s = request.app.state.sim
    if not hasattr(s, "cci_namespaces"):
        s.cci_namespaces = {}
    body = await request.json()
    name = body.get("name", body.get("metadata", {}).get("name", ""))
    if not name:
        return JSONResponse({"error_code": "CCI.0001", "error_msg": "name is required"},
                            status_code=400)
    if any(n["name"] == name for n in s.cci_namespaces.values()):
        return JSONResponse({"error_code": "CCI.0002", "error_msg": "namespace exists"},
                            status_code=409)
    nid = new_id()
    s.cci_namespaces[nid] = {
        "id": nid, "name": name, "status": "Active",
        "labels": body.get("metadata", {}).get("labels", {}),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"namespace": s.cci_namespaces[nid]}


@router.get("/v1/{pid}/cci/namespaces")
async def list_namespaces(request: Request, pid: str):
    """List CCI namespaces."""
    s = request.app.state.sim
    ns = [n for n in getattr(s, "cci_namespaces", {}).values()
          if n["project_id"] == pid]
    return {"namespaces": ns, "total": len(ns)}


@router.delete("/v1/{pid}/cci/namespaces/{ns_id}")
async def delete_namespace(request: Request, pid: str, ns_id: str):
    """Delete a namespace and everything in it."""
    s = request.app.state.sim
    if ns_id not in getattr(s, "cci_namespaces", {}):
        return JSONResponse({"error_code": "CCI.0003", "error_msg": "namespace not found"},
                            status_code=404)
    if any(p["namespace_id"] == ns_id for p in getattr(s, "cci_pods", {}).values()):
        return JSONResponse({"error_code": "CCI.0004",
                             "error_msg": "namespace is not empty"}, status_code=409)
    del s.cci_namespaces[ns_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# pods
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/cci/namespaces/{ns_id}/pods")
async def create_pod(request: Request, pid: str, ns_id: str):
    """Create a pod in a namespace: serverless container instances with their workloads."""
    s = request.app.state.sim
    if ns_id not in getattr(s, "cci_namespaces", {}):
        return JSONResponse({"error_code": "CCI.0003", "error_msg": "namespace not found"},
                            status_code=404)
    if not hasattr(s, "cci_pods"):
        s.cci_pods = {}
    body = await request.json()
    spec = body.get("spec", {})
    name = body.get("name", body.get("metadata", {}).get("name", ""))
    if not name:
        return JSONResponse({"error_code": "CCI.0005", "error_msg": "name is required"},
                            status_code=400)
    containers = spec.get("containers", body.get("containers", []))
    if not containers:
        return JSONResponse({"error_code": "CCI.0006",
                             "error_msg": "at least one container is required"}, status_code=400)
    pod_id = new_id()
    s.cci_pods[pod_id] = {
        "id": pod_id, "name": name, "namespace_id": ns_id,
        "status": "Pending", "restart_policy": spec.get("restartPolicy", "Always"),
        "containers": [{"name": c.get("name", "app"),
                        "image": c.get("image", "nginx:latest"),
                        "resources": c.get("resources", {})} for c in containers],
        "pod_ip": f"10.0.{len(s.cci_pods) % 255}.{(len(s.cci_pods) * 7) % 255 + 1}",
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        p = s.cci_pods.get(pod_id)
        if p:
            p["status"] = "Running"
        return None

    await s.jobs.submit("createCciPod", {"pod_id": pod_id}, effect)
    return {"pod": s.cci_pods[pod_id]}


@router.get("/v1/{pid}/cci/namespaces/{ns_id}/pods")
async def list_pods(request: Request, pid: str, ns_id: str):
    """List the pods of a namespace."""
    s = request.app.state.sim
    if ns_id not in getattr(s, "cci_namespaces", {}):
        return JSONResponse({"error_code": "CCI.0003", "error_msg": "namespace not found"},
                            status_code=404)
    pods = [p for p in getattr(s, "cci_pods", {}).values()
            if p["project_id"] == pid and p["namespace_id"] == ns_id]
    return {"pods": pods, "total": len(pods)}


@router.get("/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}")
async def show_pod(request: Request, pid: str, ns_id: str, pod_id: str):
    """Show one pod: container statuses, restarts, and events."""
    s = request.app.state.sim
    p = getattr(s, "cci_pods", {}).get(pod_id)
    if not p or p["project_id"] != pid or p["namespace_id"] != ns_id:
        return JSONResponse({"error_code": "CCI.0007", "error_msg": "pod not found"},
                            status_code=404)
    return {"pod": p}


@router.delete("/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}")
async def delete_pod(request: Request, pid: str, ns_id: str, pod_id: str):
    """Delete a pod."""
    s = request.app.state.sim
    p = getattr(s, "cci_pods", {}).get(pod_id)
    if not p or p["project_id"] != pid or p["namespace_id"] != ns_id:
        return JSONResponse({"error_code": "CCI.0007", "error_msg": "pod not found"},
                            status_code=404)
    del s.cci_pods[pod_id]
    return Response(status_code=204)
