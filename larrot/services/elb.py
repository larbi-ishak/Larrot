"""ELB: Elastic Load Balance: listeners, pools, members, health monitors."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _lb_json(lb):
    return {
        "id": lb["id"], "name": lb["name"], "description": lb.get("description", ""),
        "operating_status": lb.get("operating_status", "ONLINE"),
        "provisioning_status": lb.get("provisioning_status", "ACTIVE"),
        "vip_subnet_id": lb.get("vip_subnet_id", ""),
        "vpc_id": lb.get("vpc_id", ""),
        "listeners": [{"id": l["id"]} for l in lb.get("listeners", [])],
        "pools": [{"id": p["id"]} for p in lb.get("pools", [])],
        "ip_address": lb.get("ip_address", ""),
        "created_at": lb["created_at"], "updated_at": lb["updated_at"],
        "enterprise_project_id": "0",
    }


def _listener_json(l):
    return {
        "id": l["id"], "name": l["name"], "description": l.get("description", ""),
        "protocol": l["protocol"], "protocol_port": l["protocol_port"],
        "loadbalancer_id": l["loadbalancer_id"],
        "operating_status": "ONLINE", "provisioning_status": "ACTIVE",
        "default_pool_id": l.get("default_pool_id"),
        "connection_limit": l.get("connection_limit", -1),
        "created_at": l["created_at"], "updated_at": l["updated_at"],
    }


def _pool_json(p):
    return {
        "id": p["id"], "name": p["name"], "description": p.get("description", ""),
        "protocol": p["protocol"], "loadbalancer_id": p["loadbalancer_id"],
        "listener_id": p.get("listener_id"),
        "members": [{"id": m["id"]} for m in p.get("members", [])],
        "health_monitor_id": p.get("health_monitor_id"),
        "session_persistence": p.get("session_persistence"),
        "operating_status": "ONLINE", "provisioning_status": "ACTIVE",
        "created_at": p["created_at"], "updated_at": p["updated_at"],
    }


def _member_json(m):
    return {
        "id": m["id"], "address": m["address"], "protocol_port": m["protocol_port"],
        "pool_id": m["pool_id"], "weight": m.get("weight", 1),
        "operating_status": m.get("operating_status", "ONLINE"),
        "provisioning_status": "ACTIVE",
        "subnet_id": m.get("subnet_id", ""),
        "created_at": m["created_at"], "updated_at": m["updated_at"],
    }


# ---------------------------------------------------------------------------
# Load balancers
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/elb/loadbalancers")
async def create_loadbalancer(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_loadbalancers"):
        state.elb_loadbalancers = {}
    body = await request.json()
    spec = body.get("loadbalancer", body)
    lb_id = new_id()
    now = now_millis()
    state.elb_loadbalancers[lb_id] = {
        "id": lb_id, "name": spec.get("name", f"elb-{lb_id[:8]}"),
        "description": spec.get("description", ""),
        "vip_subnet_id": spec.get("vip_subnet_id", ""),
        "vpc_id": spec.get("vpc_id", ""),
        "ip_address": spec.get("vip_address", f"192.168.0.{100 + len(state.elb_loadbalancers)}"),
        "listeners": [], "pools": [],
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    return {"loadbalancer": _lb_json(state.elb_loadbalancers[lb_id])}


@router.get("/v2/{pid}/elb/loadbalancers")
async def list_loadbalancers(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_loadbalancers"):
        state.elb_loadbalancers = {}
    lbs = [lb for lb in state.elb_loadbalancers.values() if lb["project_id"] == pid]
    return {"loadbalancers": [_lb_json(lb) for lb in lbs], "count": len(lbs)}


@router.get("/v2/{pid}/elb/loadbalancers/{lb_id}")
async def show_loadbalancer(request: Request, pid: str, lb_id: str):
    state = request.app.state.sim
    lb = getattr(state, "elb_loadbalancers", {}).get(lb_id)
    if not lb or lb["project_id"] != pid:
        return JSONResponse({"error_msg": "Load balancer not found", "error_code": "ELB.0101"}, status_code=404)
    return {"loadbalancer": _lb_json(lb)}


@router.delete("/v2/{pid}/elb/loadbalancers/{lb_id}")
async def delete_loadbalancer(request: Request, pid: str, lb_id: str):
    state = request.app.state.sim
    lb = getattr(state, "elb_loadbalancers", {}).get(lb_id)
    if not lb or lb["project_id"] != pid:
        return JSONResponse({"error_msg": "Load balancer not found", "error_code": "ELB.0101"}, status_code=404)
    del state.elb_loadbalancers[lb_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Listeners
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/elb/listeners")
async def create_listener(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_listeners"):
        state.elb_listeners = {}
    body = await request.json()
    spec = body.get("listener", body)
    lb = getattr(state, "elb_loadbalancers", {}).get(spec.get("loadbalancer_id", ""))
    if not lb:
        return JSONResponse({"error_msg": "Load balancer not found", "error_code": "ELB.0101"}, status_code=404)
    lis_id = new_id()
    now = now_millis()
    listener = {
        "id": lis_id, "name": spec.get("name", f"listener-{lis_id[:8]}"),
        "description": spec.get("description", ""),
        "protocol": spec.get("protocol", "HTTP"),
        "protocol_port": spec.get("protocol_port", 80),
        "loadbalancer_id": spec["loadbalancer_id"],
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    state.elb_listeners[lis_id] = listener
    lb["listeners"].append(listener)
    return {"listener": _listener_json(listener)}


@router.get("/v2/{pid}/elb/listeners")
async def list_listeners(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_listeners"):
        state.elb_listeners = {}
    listeners = [l for l in state.elb_listeners.values() if l["project_id"] == pid]
    return {"listeners": [_listener_json(l) for l in listeners], "count": len(listeners)}


@router.delete("/v2/{pid}/elb/listeners/{listener_id}")
async def delete_listener(request: Request, pid: str, listener_id: str):
    state = request.app.state.sim
    if listener_id not in state.elb_listeners:
        return JSONResponse({"error_msg": "Listener not found", "error_code": "ELB.0102"}, status_code=404)
    listener = state.elb_listeners.pop(listener_id)
    lb = getattr(state, "elb_loadbalancers", {}).get(listener["loadbalancer_id"])
    if lb:
        lb["listeners"] = [l for l in lb["listeners"] if l["id"] != listener_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Pools + members
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/elb/pools")
async def create_pool(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_pools"):
        state.elb_pools = {}
    body = await request.json()
    spec = body.get("pool", body)
    pool_id = new_id()
    now = now_millis()
    pool = {
        "id": pool_id, "name": spec.get("name", f"pool-{pool_id[:8]}"),
        "description": spec.get("description", ""),
        "protocol": spec.get("protocol", "HTTP"),
        "loadbalancer_id": spec.get("loadbalancer_id", ""),
        "listener_id": spec.get("listener_id"),
        "members": [], "created_at": now, "updated_at": now, "project_id": pid,
    }
    state.elb_pools[pool_id] = pool
    return {"pool": _pool_json(pool)}


@router.get("/v2/{pid}/elb/pools")
async def list_pools(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_pools"):
        state.elb_pools = {}
    pools = [p for p in state.elb_pools.values() if p["project_id"] == pid]
    return {"pools": [_pool_json(p) for p in pools], "count": len(pools)}


@router.post("/v2/{pid}/elb/pools/{pool_id}/members")
async def create_member(request: Request, pid: str, pool_id: str):
    state = request.app.state.sim
    pool = state.elb_pools.get(pool_id)
    if not pool:
        return JSONResponse({"error_msg": "Pool not found", "error_code": "ELB.0103"}, status_code=404)
    body = await request.json()
    spec = body.get("member", body)
    member_id = new_id()
    now = now_millis()
    member = {
        "id": member_id, "address": spec["address"],
        "protocol_port": spec.get("protocol_port", 80),
        "pool_id": pool_id, "weight": spec.get("weight", 1),
        "subnet_id": spec.get("subnet_id", ""),
        "created_at": now, "updated_at": now,
    }
    pool["members"].append(member)
    return {"member": _member_json(member)}


@router.get("/v2/{pid}/elb/pools/{pool_id}/members")
async def list_members(request: Request, pid: str, pool_id: str):
    state = request.app.state.sim
    pool = state.elb_pools.get(pool_id)
    if not pool:
        return JSONResponse({"error_msg": "Pool not found", "error_code": "ELB.0103"}, status_code=404)
    return {"members": [_member_json(m) for m in pool["members"]], "count": len(pool["members"])}


@router.get("/v2/{pid}/elb/listeners/{listener_id}")
async def show_listener(request: Request, pid: str, listener_id: str):
    state = request.app.state.sim
    l = getattr(state, "elb_listeners", {}).get(listener_id)
    if not l or l.get("project_id") != pid:
        return JSONResponse({"error_msg": "Listener not found", "error_code": "ELB.0102"}, status_code=404)
    return {"listener": _listener_json(l)}


@router.delete("/v2/{pid}/elb/pools/{pool_id}")
async def delete_pool(request: Request, pid: str, pool_id: str):
    state = request.app.state.sim
    p = getattr(state, "elb_pools", {}).get(pool_id)
    if not p or p.get("project_id") != pid:
        return JSONResponse({"error_msg": "Pool not found", "error_code": "ELB.0103"}, status_code=404)
    del state.elb_pools[pool_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/elb/healthmonitors")
async def create_health_monitor(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "elb_healthmonitors"):
        state.elb_healthmonitors = {}
    body = await request.json()
    spec = body.get("healthmonitor", body)
    hm_id = new_id()
    now = now_millis()
    state.elb_healthmonitors[hm_id] = {
        "id": hm_id, "pool_id": spec.get("pool_id", ""),
        "type": spec.get("type", "TCP"), "delay": spec.get("delay", 5),
        "timeout": spec.get("timeout", 10), "max_retries": spec.get("max_retries", 3),
        "admin_state_up": True, "status": "ACTIVE",
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    return {"healthmonitor": state.elb_healthmonitors[hm_id]}


@router.get("/v2/{pid}/elb/healthmonitors")
async def list_health_monitors(request: Request, pid: str):
    state = request.app.state.sim
    hms = [h for h in getattr(state, "elb_healthmonitors", {}).values()
           if h["project_id"] == pid]
    return {"healthmonitors": hms, "total": len(hms)}
