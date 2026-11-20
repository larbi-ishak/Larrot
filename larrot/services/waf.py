"""WAF: Web Application Firewall: domains, policies, rules."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1/{pid}/waf/hosts")
async def create_waf_domain(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "waf_domains"): s.waf_domains = {}
    body = await request.json()
    did = new_id()
    s.waf_domains[did] = {"id": did, "hostname": body.get("hostname", "example.com"),
        "policy_id": body.get("policy_id", ""), "protect_status": 1,
        "access_status": 0, "created_at": now_millis(), "project_id": pid}
    return {"id": did, "hostname": s.waf_domains[did]["hostname"]}

@router.get("/v1/{pid}/waf/hosts")
async def list_waf_domains(request: Request, pid: str):
    s = request.app.state.sim
    domains = [d for d in getattr(s, "waf_domains", {}).values() if d["project_id"] == pid]
    return {"total": len(domains), "items": domains}

@router.delete("/v1/{pid}/waf/hosts/{domain_id}")
async def delete_waf_domain(request: Request, pid: str, domain_id: str):
    s = request.app.state.sim
    if domain_id not in getattr(s, "waf_domains", {}):
        return JSONResponse({"error_msg": "Domain not found", "error_code": "WAF.0001"}, status_code=404)
    del s.waf_domains[domain_id]
    return Response(status_code=204)

@router.post("/v1/{pid}/waf/policies")
async def create_waf_policy(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "waf_policies"): s.waf_policies = {}
    body = await request.json()
    pol_id = new_id()
    s.waf_policies[pol_id] = {"id": pol_id, "name": body.get("name", f"policy-{pol_id[:8]}"),
        "level": body.get("level", 1), "action": {"category": "block"},
        "created_at": now_millis(), "project_id": pid}
    return {"id": pol_id, "name": s.waf_policies[pol_id]["name"]}

@router.get("/v1/{pid}/waf/policies")
async def list_waf_policies(request: Request, pid: str):
    s = request.app.state.sim
    policies = [p for p in getattr(s, "waf_policies", {}).values() if p["project_id"] == pid]
    return {"total": len(policies), "items": policies}


# ---------------------------------------------------------------------------
# sub-APIs: host/policy details, policy binding, rules
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/waf/hosts/{domain_id}")
async def show_waf_host(request: Request, pid: str, domain_id: str):
    s = request.app.state.sim
    d = getattr(s, "waf_domains", {}).get(domain_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "WAF.0001", "error_msg": "domain not found"},
                            status_code=404)
    return d


@router.get("/v1/{pid}/waf/policies/{policy_id}")
async def show_waf_policy(request: Request, pid: str, policy_id: str):
    s = request.app.state.sim
    p = getattr(s, "waf_policies", {}).get(policy_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_code": "WAF.0002", "error_msg": "policy not found"},
                            status_code=404)
    return p


@router.put("/v1/{pid}/waf/hosts/{domain_id}")
async def bind_waf_policy(request: Request, pid: str, domain_id: str):
    s = request.app.state.sim
    d = getattr(s, "waf_domains", {}).get(domain_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "WAF.0001", "error_msg": "domain not found"},
                            status_code=404)
    body = await request.json()
    pol_id = body.get("policy_id", "")
    if pol_id and pol_id not in getattr(s, "waf_policies", {}):
        return JSONResponse({"error_code": "WAF.0002", "error_msg": "policy not found"},
                            status_code=404)
    d["policy_id"] = pol_id
    return d


@router.post("/v1/{pid}/waf/policies/{policy_id}/rules")
async def create_waf_rule(request: Request, pid: str, policy_id: str):
    s = request.app.state.sim
    p = getattr(s, "waf_policies", {}).get(policy_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_code": "WAF.0002", "error_msg": "policy not found"},
                            status_code=404)
    if not hasattr(s, "waf_rules"):
        s.waf_rules = {}
    body = await request.json()
    rid = new_id()
    s.waf_rules[rid] = {"id": rid, "policy_id": policy_id,
                          "type": body.get("type", "white_ip"),
                          "conditions": body.get("conditions", []),
                          "status": 1, "project_id": pid, "created_at": now_millis()}
    p.setdefault("rules", []).append(rid)
    return s.waf_rules[rid]


@router.get("/v1/{pid}/waf/policies/{policy_id}/rules")
async def list_waf_rules(request: Request, pid: str, policy_id: str):
    s = request.app.state.sim
    p = getattr(s, "waf_policies", {}).get(policy_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_code": "WAF.0002", "error_msg": "policy not found"},
                            status_code=404)
    rules = [r for r in getattr(s, "waf_rules", {}).values()
             if r["project_id"] == pid and r["policy_id"] == policy_id]
    return {"rules": rules, "total": len(rules)}
