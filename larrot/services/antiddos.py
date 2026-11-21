"""Anti-DDoS: protection policies and status."""
from fastapi import APIRouter, Request

from ..core.jobs import new_id

router = APIRouter()

@router.post("/v1/{pid}/antiddos/default")
async def set_default_config(request: Request, pid: str):
    """Set the default Anti-DDoS defense policy applied to newly purchased EIPs."""
    await request.json()
    return {"task_id": new_id(), "success": True}

@router.get("/v1/{pid}/antiddos/default")
async def get_default_config(request: Request, pid: str):
    """Query the default Anti-DDoS defense policy."""
    return {"enable_l7": True, "traffic_pos_limit": 100, "http_request_pos_limit": 100,
            "cleaning_access_pos_limit": 100, "app_type": 0}

@router.get("/v1/{pid}/antiddos/status")
async def list_antiddos_status(request: Request, pid: str):
    """List the Anti-DDoS protection status of each EIP: configured policy, traffic, and defense events."""
    return {"total": 0, "items": []}

@router.post("/v1/{pid}/antiddos/enable")
async def enable_antiddos(request: Request, pid: str):
    """Enable Anti-DDoS protection for an EIP (async: returns a task id)."""
    body = await request.json()
    return {"task_id": new_id(), "ip": body.get("ip", "0.0.0.0"), "success": True}
