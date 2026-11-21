"""VPC v3 API (/v3/{project_id}/vpc/vpcs).

The Terraform provider's huaweicloud_vpc resource creates via v1 but
reads back through v3 (it needs extend_cidrs), so the v3 read paths are
required for real-client compatibility. Shapes follow the VPC v3 API:
responses wrap in {"vpc": ...}; status uses v3 values (available).
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _v3_view(v: dict) -> dict:
    """A v1 store object -> the v3 response shape."""
    return {
        "id": v["id"],
        "name": v.get("name", ""),
        "cidr": v.get("cidr", ""),
        "description": v.get("description", ""),
        "status": "available" if v.get("status", "OK") == "OK" else "pending",
        "project_id": v.get("project_id", ""),
        "created_at": v.get("created_at", ""),
        "updated_at": v.get("updated_at", ""),
        "extend_cidrs": v.get("extend_cidrs", []),
        "tags": v.get("tags", []),
        "enterprise_project_id": v.get("enterprise_project_id", "0"),
    }


def _find(state, pid: str, vpc_id: str):
    v = state.vpcs.get(vpc_id)
    if not v or v.get("project_id") != pid:
        return None
    return v


@router.get("/v3/{pid}/vpc/vpcs")
async def v3_list_vpcs(request: Request, pid: str, limit: int = None, marker: str = None):
    state = request.app.state.sim
    items = [_v3_view(v) for v in state.vpcs.values() if v.get("project_id") == pid]
    items.sort(key=lambda v: v["id"])
    if marker:
        items = [v for v in items if v["id"] > marker]
    if limit:
        items = items[:limit]
    return {"vpcs": items, "page_info": {
        "previous_marker": marker or "", "next_marker": items[-1]["id"] if len(items) == (limit or 0) else ""}}


@router.post("/v3/{pid}/vpc/vpcs")
async def v3_create_vpc(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    inner = body.get("vpc", body)  # accept wrapped or flat
    name = inner.get("name") or f"vpc-{new_id()[:8]}"
    cidr = inner.get("cidr", "192.168.0.0/16")
    v = {
        "id": new_id(), "name": name, "cidr": cidr,
        "description": inner.get("description", ""),
        "status": "OK", "project_id": pid,
        "created_at": now_millis(), "updated_at": now_millis(),
        "extend_cidrs": inner.get("extend_cidrs", []),
        "tags": inner.get("tags", []),
        "enterprise_project_id": inner.get("enterprise_project_id", "0"),
    }
    state.vpcs[v["id"]] = v
    return JSONResponse({"vpc": _v3_view(v)}, status_code=201)


@router.get("/v3/{pid}/vpc/vpcs/{vpc_id}")
async def v3_show_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = _find(state, pid, vpc_id)
    if not v:
        return JSONResponse(
            {"error_msg": f"Vpc {vpc_id} could not be found.",
             "error_code": "VPC.9904", "request_id": ""},
            status_code=404)
    return {"vpc": _v3_view(v)}


@router.put("/v3/{pid}/vpc/vpcs/{vpc_id}")
async def v3_update_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = _find(state, pid, vpc_id)
    if not v:
        return JSONResponse(
            {"error_msg": f"Vpc {vpc_id} could not be found.",
             "error_code": "VPC.9904", "request_id": ""},
            status_code=404)
    body = await request.json()
    inner = body.get("vpc", body)
    for key in ("name", "description", "cidr"):
        if key in inner:
            v[key] = inner[key]
    v["updated_at"] = now_millis()
    return {"vpc": _v3_view(v)}


@router.delete("/v3/{pid}/vpc/vpcs/{vpc_id}")
async def v3_delete_vpc(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = _find(state, pid, vpc_id)
    if not v:
        return JSONResponse(
            {"error_msg": f"Vpc {vpc_id} could not be found.",
             "error_code": "VPC.9904", "request_id": ""},
            status_code=404)
    del state.vpcs[vpc_id]
    return Response(status_code=204)


@router.put("/v3/{pid}/vpc/vpcs/{vpc_id}/add-extend-cidr")
async def v3_add_extend_cidr(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = _find(state, pid, vpc_id)
    if not v:
        return JSONResponse(
            {"error_msg": f"Vpc {vpc_id} could not be found.",
             "error_code": "VPC.9904", "request_id": ""},
            status_code=404)
    body = await request.json()
    inner = body.get("vpc", body)
    cidr = inner.get("extend_cidr")
    if not cidr:
        return JSONResponse(
            {"error_msg": "Invalid CIDR block format.",
             "error_code": "VPC.9911", "request_id": ""},
            status_code=400)
    v.setdefault("extend_cidrs", [])
    if cidr not in v["extend_cidrs"]:
        v["extend_cidrs"].append(cidr)
    v["updated_at"] = now_millis()
    return {"vpc": _v3_view(v)}


@router.put("/v3/{pid}/vpc/vpcs/{vpc_id}/remove-extend-cidr")
async def v3_remove_extend_cidr(request: Request, pid: str, vpc_id: str):
    state = request.app.state.sim
    v = _find(state, pid, vpc_id)
    if not v:
        return JSONResponse(
            {"error_msg": f"Vpc {vpc_id} could not be found.",
             "error_code": "VPC.9904", "request_id": ""},
            status_code=404)
    body = await request.json()
    inner = body.get("vpc", body)
    cidr = inner.get("extend_cidr")
    exts = v.setdefault("extend_cidrs", [])
    if cidr not in exts:
        return JSONResponse(
            {"error_msg": "The secondary CIDR block to be removed not found.",
             "error_code": "VPC.9915", "request_id": ""},
            status_code=404)
    exts.remove(cidr)
    v["updated_at"] = now_millis()
    return {"vpc": _v3_view(v)}
