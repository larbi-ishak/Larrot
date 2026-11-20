"""Network ACL: subnet-level firewall rules (different from security groups)."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()


def _acl_json(a):
    return {
        "id": a["id"], "name": a["name"], "description": a.get("description", ""),
        "status": a.get("status", "ACTIVE"),
        "ingress_rules": a.get("ingress_rules", []),
        "egress_rules": a.get("egress_rules", []),
        "subnets": a.get("subnets", []),
        "created_at": a["created_at"], "updated_at": a.get("updated_at", a["created_at"]),
        "enterprise_project_id": "0",
    }


def _rule_json(r):
    return {
        "id": r["id"], "action": r.get("action", "ALLOW"),
        "protocol": r.get("protocol", "ALL"),
        "source_ip_address": r.get("source_ip_address", "0.0.0.0/0"),
        "destination_ip_address": r.get("destination_ip_address", "0.0.0.0/0"),
        "source_port": r.get("source_port", ""), "destination_port": r.get("destination_port", ""),
        "priority": r.get("priority", 1),
        "enabled": r.get("enabled", True),
    }


@router.post("/v3/{pid}/vpc/acls")
async def create_acl(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "network_acls"): s.network_acls = {}
    body = await request.json()
    acl_id = new_id()
    s.network_acls[acl_id] = {
        "id": acl_id, "name": body.get("name", f"acl-{acl_id[:8]}"),
        "description": body.get("description", ""),
        "status": "ACTIVE", "ingress_rules": [], "egress_rules": [], "subnets": [],
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"acl": _acl_json(s.network_acls[acl_id])}


@router.get("/v3/{pid}/vpc/acls")
async def list_acls(request: Request, pid: str):
    s = request.app.state.sim
    acls = [a for a in getattr(s, "network_acls", {}).values() if a["project_id"] == pid]
    return {"acls": [_acl_json(a) for a in acls], "count": len(acls)}


@router.get("/v3/{pid}/vpc/acls/{acl_id}")
async def show_acl(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    return {"acl": _acl_json(a)}


@router.put("/v3/{pid}/vpc/acls/{acl_id}")
async def update_acl(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a.get("project_id") != pid:
        return JSONResponse({"error_code": "ACL.0001", "error_msg": "ACL not found"},
                            status_code=404)
    body = await request.json()
    if "name" in body and body["name"]:
        a["name"] = body["name"]
    return {"acl": _acl_json(a)}


@router.delete("/v3/{pid}/vpc/acls/{acl_id}")
async def delete_acl(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    if acl_id not in getattr(s, "network_acls", {}):
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    del s.network_acls[acl_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# ACL rules (ingress/egress)
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/vpc/acls/{acl_id}/ingress-rules")
async def add_ingress_rule(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    body = await request.json()
    rule = {"id": new_id(), "action": body.get("action", "ALLOW"),
            "protocol": body.get("protocol", "ALL"),
            "source_ip_address": body.get("source_ip_address", "0.0.0.0/0"),
            "destination_ip_address": body.get("destination_ip_address", "0.0.0.0/0"),
            "source_port": body.get("source_port", ""),
            "destination_port": body.get("destination_port", ""),
            "priority": body.get("priority", len(a["ingress_rules"]) + 1),
            "enabled": body.get("enabled", True)}
    a["ingress_rules"].append(rule)
    a["updated_at"] = now_millis()
    return {"rule": _rule_json(rule)}


@router.post("/v3/{pid}/vpc/acls/{acl_id}/egress-rules")
async def add_egress_rule(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    body = await request.json()
    rule = {"id": new_id(), "action": body.get("action", "ALLOW"),
            "protocol": body.get("protocol", "ALL"),
            "source_ip_address": body.get("source_ip_address", "0.0.0.0/0"),
            "destination_ip_address": body.get("destination_ip_address", "0.0.0.0/0"),
            "source_port": body.get("source_port", ""),
            "destination_port": body.get("destination_port", ""),
            "priority": body.get("priority", len(a["egress_rules"]) + 1),
            "enabled": body.get("enabled", True)}
    a["egress_rules"].append(rule)
    a["updated_at"] = now_millis()
    return {"rule": _rule_json(rule)}


# ---------------------------------------------------------------------------
# Associate/disassociate ACL with subnet
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/vpc/acls/{acl_id}/associate")
async def associate_acl(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    body = await request.json()
    subnet_id = body.get("subnet_id", "")
    if subnet_id not in a["subnets"]:
        a["subnets"].append(subnet_id)
    a["updated_at"] = now_millis()
    return {"acl": _acl_json(a)}


@router.post("/v3/{pid}/vpc/acls/{acl_id}/disassociate")
async def disassociate_acl(request: Request, pid: str, acl_id: str):
    s = request.app.state.sim
    a = getattr(s, "network_acls", {}).get(acl_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_msg": "ACL not found", "error_code": "ACL.0001"}, status_code=404)
    body = await request.json()
    subnet_id = body.get("subnet_id", "")
    a["subnets"] = [sid for sid in a["subnets"] if sid != subnet_id]
    a["updated_at"] = now_millis()
    return {"acl": _acl_json(a)}
