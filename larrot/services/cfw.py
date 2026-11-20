"""CFW (Cloud Firewall): VPC-boundary firewalls, rules, hit records.

Real route: POST /v1/{project_id}/firewalls on the CFW endpoint.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/firewalls")
async def create_firewall(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "cfw_firewalls"):
        s.cfw_firewalls = {}
    if not hasattr(s, "cfw_rules"):
        s.cfw_rules = {}
    if not hasattr(s, "cfw_hits"):
        s.cfw_hits = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "CFW.0001", "error_msg": "name is required"},
                            status_code=400)
    fid = new_id()
    s.cfw_firewalls[fid] = {
        "id": fid, "name": name, "status": "creating",
        "flavor": body.get("flavor", "standard"),
        "protect_objects": body.get("protect_objects", []),
        "project_id": pid, "created_at": now_millis(),
    }
    s.cfw_rules[fid] = []

    async def effect():
        f = s.cfw_firewalls.get(fid)
        if f:
            f["status"] = "running"
        return None

    await s.jobs.submit("createCfwFirewall", {"firewall_id": fid}, effect)
    return {"firewall": s.cfw_firewalls[fid]}


@router.get("/v1/{pid}/firewalls")
async def list_firewalls(request: Request, pid: str):
    s = request.app.state.sim
    firewalls = [f for f in getattr(s, "cfw_firewalls", {}).values()
                 if f["project_id"] == pid]
    return {"firewalls": firewalls, "total": len(firewalls)}


@router.get("/v1/{pid}/firewalls/{firewall_id}")
async def show_firewall(request: Request, pid: str, firewall_id: str):
    s = request.app.state.sim
    f = getattr(s, "cfw_firewalls", {}).get(firewall_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    return {"firewall": f}


@router.delete("/v1/{pid}/firewalls/{firewall_id}")
async def delete_firewall(request: Request, pid: str, firewall_id: str):
    s = request.app.state.sim
    if firewall_id not in getattr(s, "cfw_firewalls", {}):
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    del s.cfw_firewalls[firewall_id]
    s.cfw_rules.pop(firewall_id, None)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/firewalls/{firewall_id}/rules")
async def create_rule(request: Request, pid: str, firewall_id: str):
    s = request.app.state.sim
    f = getattr(s, "cfw_firewalls", {}).get(firewall_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    body = await request.json()
    action = body.get("action", "allow")
    if action not in ("allow", "deny"):
        return JSONResponse({"error_code": "CFW.0003",
                             "error_msg": "action must be allow or deny"}, status_code=400)
    rid = new_id()
    rule = {
        "id": rid, "name": body.get("name", f"rule-{rid[:8]}"),
        "direction": body.get("direction", "in"),
        "action": action, "protocol": body.get("protocol", "TCP"),
        "source": body.get("source", "0.0.0.0/0"),
        "destination": body.get("destination", "0.0.0.0/0"),
        "port": body.get("port", "443"), "status": "enabled",
        "hit_count": 0, "created_at": now_millis(),
    }
    s.cfw_rules[firewall_id].append(rule)
    return {"rule": rule}


@router.get("/v1/{pid}/firewalls/{firewall_id}/rules")
async def list_rules(request: Request, pid: str, firewall_id: str):
    s = request.app.state.sim
    f = getattr(s, "cfw_firewalls", {}).get(firewall_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    rules = s.cfw_rules.get(firewall_id, [])
    return {"rules": rules, "total": len(rules)}


@router.delete("/v1/{pid}/firewalls/{firewall_id}/rules/{rule_id}")
async def delete_rule(request: Request, pid: str, firewall_id: str, rule_id: str):
    s = request.app.state.sim
    rules = s.cfw_rules.get(firewall_id, [])
    if not any(r["id"] == rule_id for r in rules):
        return JSONResponse({"error_code": "CFW.0004", "error_msg": "rule not found"},
                            status_code=404)
    s.cfw_rules[firewall_id] = [r for r in rules if r["id"] != rule_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# hit records (traffic that matched a rule)
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/firewalls/{firewall_id}/hit-records")
async def record_hit(request: Request, pid: str, firewall_id: str):
    """Test hook: record a rule hit (real CFW generates these from traffic)."""
    s = request.app.state.sim
    f = getattr(s, "cfw_firewalls", {}).get(firewall_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    body = await request.json()
    rule_id = body.get("rule_id", "")
    rule = next((r for r in s.cfw_rules.get(firewall_id, []) if r["id"] == rule_id), None)
    if not rule:
        return JSONResponse({"error_code": "CFW.0004", "error_msg": "rule not found"},
                            status_code=404)
    rule["hit_count"] += 1
    hid = new_id()
    s.cfw_hits[hid] = {
        "id": hid, "rule_id": rule_id, "firewall_id": firewall_id,
        "action": rule["action"], "source": rule["source"],
        "destination": rule["destination"],
        "log_time": now_millis(), "project_id": pid,
    }
    return {"hit_id": hid, "hit_count": rule["hit_count"]}


@router.get("/v1/{pid}/firewalls/{firewall_id}/hit-records")
async def list_hits(request: Request, pid: str, firewall_id: str):
    s = request.app.state.sim
    f = getattr(s, "cfw_firewalls", {}).get(firewall_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_code": "CFW.0002", "error_msg": "firewall not found"},
                            status_code=404)
    hits = [h for h in getattr(s, "cfw_hits", {}).values()
            if h["project_id"] == pid and h["firewall_id"] == firewall_id]
    return {"records": hits, "total": len(hits)}
