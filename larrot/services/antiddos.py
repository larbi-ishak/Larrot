"""Anti-DDoS: protection policies and status, backed by the real EIP store.

Protection records are kept per EIP (state.antiddos_protections) and the
default policy per project (state.antiddos_defaults); /status enumerates
the project's actual EIPs, so enabling protection changes what status
reports - the backend is stateful, not canned.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

DEFAULT_POLICY = {
    "enable_l7": True,
    "traffic_pos_limit": 100,
    "http_request_pos_limit": 100,
    "cleaning_access_pos_limit": 100,
    "app_type": 0,
}


def _protections(s):
    """Per-EIP protection records: {eip_id: {...}} (lazily created)."""
    store = getattr(s, "antiddos_protections", None)
    if store is None:
        store = {}
        setattr(s, "antiddos_protections", store)
    return store


def _defaults(s):
    """Per-project default policies: {pid: policy} (lazily created)."""
    store = getattr(s, "antiddos_defaults", None)
    if store is None:
        store = {}
        setattr(s, "antiddos_defaults", store)
    return store


def _find_eip(s, pid, ip_or_id):
    """Find an EIP of the project by id or by public address."""
    for e in s.eips.values():
        if e.get("project_id") != pid:
            continue
        if e["id"] == ip_or_id or e.get("public_ip_address") == ip_or_id:
            return e
    return None


def _eip_not_found(ip_or_id):
    return JSONResponse(
        {"error_msg": f"EIP {ip_or_id} could not be found.",
         "error_code": "Common.0004", "request_id": ""},
        status_code=404)


@router.post("/v1/{pid}/antiddos/default")
async def set_default_config(request: Request, pid: str):
    """Set the default Anti-DDoS defense policy applied to newly purchased EIPs."""
    s = request.app.state.sim
    body = await request.json()
    policy = {**DEFAULT_POLICY, **body}
    _defaults(s)[pid] = policy
    return {"task_id": new_id(), "success": True}


@router.get("/v1/{pid}/antiddos/default")
async def get_default_config(request: Request, pid: str):
    """Query the default Anti-DDoS defense policy."""
    s = request.app.state.sim
    return _defaults(s).get(pid, dict(DEFAULT_POLICY))


@router.get("/v1/{pid}/antiddos/status")
async def list_antiddos_status(request: Request, pid: str,
                               floating_ip_id: str = None):
    """List the Anti-DDoS protection status of each EIP: configured policy, traffic, and defense events."""
    s = request.app.state.sim
    protections = _protections(s)
    items = []
    for e in s.eips.values():
        if e.get("project_id") != pid:
            continue
        if floating_ip_id and e["id"] != floating_ip_id:
            continue
        rec = protections.get(e["id"])
        items.append({
            "floating_ip_id": e["id"],
            "floating_ip_address": e.get("public_ip_address", ""),
            "network_type": "EIP",
            "status": "normal" if rec else "notConfig",
            "protection_type": rec["protection_type"] if rec else "default",
            "blackhole_endtime": 0,
            **({"policy": rec["policy"]} if rec else {}),
        })
    return {"total": len(items), "items": items}


@router.post("/v1/{pid}/antiddos/enable")
async def enable_antiddos(request: Request, pid: str):
    """Enable Anti-DDoS protection for an EIP (async: returns a task id)."""
    s = request.app.state.sim
    body = await request.json()
    ip = body.get("ip", "")
    eip = _find_eip(s, pid, ip)
    if not eip:
        return _eip_not_found(ip or "(none)")
    _protections(s)[eip["id"]] = {
        "eip_id": eip["id"],
        "ip": eip.get("public_ip_address", ""),
        "protection_type": body.get("protection_type", "default"),
        "policy": _defaults(s).get(pid, dict(DEFAULT_POLICY)),
        "enabled_at": now_millis(),
    }
    return {"task_id": new_id(), "ip": eip.get("public_ip_address", ""),
            "success": True}


# Per-EIP routes are registered AFTER the static segments (default,
# status, enable) so the static paths match first.
@router.get("/v1/{pid}/antiddos/{floating_ip_id}")
async def show_antiddos(request: Request, pid: str, floating_ip_id: str):
    """Show one EIP's Anti-DDoS protection: its status and applied policy."""
    s = request.app.state.sim
    eip = _find_eip(s, pid, floating_ip_id)
    if not eip:
        return _eip_not_found(floating_ip_id)
    rec = _protections(s).get(eip["id"])
    return {
        "floating_ip_id": eip["id"],
        "floating_ip_address": eip.get("public_ip_address", ""),
        "status": "normal" if rec else "notConfig",
        "policy": rec["policy"] if rec else _defaults(s).get(pid, dict(DEFAULT_POLICY)),
        "enabled_at": rec["enabled_at"] if rec else None,
    }


@router.post("/v1/{pid}/antiddos/{floating_ip_id}")
async def update_antiddos_policy(request: Request, pid: str, floating_ip_id: str):
    """Update the protection policy applied to one EIP (async: returns a task id)."""
    s = request.app.state.sim
    eip = _find_eip(s, pid, floating_ip_id)
    if not eip:
        return _eip_not_found(floating_ip_id)
    body = await request.json()
    rec = _protections(s).get(eip["id"])
    if not rec:
        return JSONResponse(
            {"error_msg": "Anti-DDoS protection is not enabled on this EIP.",
             "error_code": "Common.0004", "request_id": ""},
            status_code=404)
    rec["policy"] = {**rec["policy"], **body}
    rec["protection_type"] = "custom"
    return {"task_id": new_id(), "success": True}


@router.delete("/v1/{pid}/antiddos/{floating_ip_id}")
async def disable_antiddos(request: Request, pid: str, floating_ip_id: str):
    """Cancel Anti-DDoS protection for an EIP (async: returns a task id)."""
    s = request.app.state.sim
    eip = _find_eip(s, pid, floating_ip_id)
    if not eip:
        return _eip_not_found(floating_ip_id)
    if eip["id"] not in _protections(s):
        return JSONResponse(
            {"error_msg": "Anti-DDoS protection is not enabled on this EIP.",
             "error_code": "Common.0004", "request_id": ""},
            status_code=404)
    del _protections(s)[eip["id"]]
    return {"task_id": new_id(), "success": True}
