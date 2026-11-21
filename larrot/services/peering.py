"""VPC Peering: peering connections between VPCs, accept/reject."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _peering_json(p):
    return {
        "id": p["id"], "name": p["name"], "status": p["status"],
        "requester_vpc_info": p.get("requester_vpc_info", {"vpc_id": ""}),
        "accepter_vpc_info": p.get("accepter_vpc_info", {"vpc_id": ""}),
        "created_at": p["created_at"], "updated_at": p.get("updated_at", p["created_at"]),
    }


@router.post("/v2.0/{pid}/vpc-peerings")
async def create_peering(request: Request, pid: str):
    """Create a VPC peering connection: link two VPCs' networks."""
    s = request.app.state.sim
    if not hasattr(s, "vpc_peerings"): s.vpc_peerings = {}
    body = await request.json()
    peering_id = new_id()
    s.vpc_peerings[peering_id] = {
        "id": peering_id, "name": body.get("name", f"peering-{peering_id[:8]}"),
        "status": "PENDING_ACCEPTANCE",
        "requester_vpc_info": {"vpc_id": body.get("requester_vpc_id", "")},
        "accepter_vpc_info": {"vpc_id": body.get("accepter_vpc_id", "")},
        "created_at": now_millis(), "updated_at": now_millis(), "project_id": pid,
    }
    return {"peering": _peering_json(s.vpc_peerings[peering_id])}


@router.get("/v2.0/{pid}/vpc-peerings")
async def list_peerings(request: Request, pid: str):
    """List peering connections."""
    s = request.app.state.sim
    peerings = [p for p in getattr(s, "vpc_peerings", {}).values() if p["project_id"] == pid]
    return {"vpc_peerings": [_peering_json(p) for p in peerings], "count": len(peerings)}


@router.get("/v2.0/{pid}/vpc-peerings/{peering_id}")
async def show_peering(request: Request, pid: str, peering_id: str):
    """Show one peering: its two VPCs and acceptance status."""
    s = request.app.state.sim
    p = getattr(s, "vpc_peerings", {}).get(peering_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_msg": "Peering not found", "error_code": "VPC.0301"}, status_code=404)
    return {"peering": _peering_json(p)}


@router.put("/v2.0/{pid}/vpc-peerings/{peering_id}/accept")
async def accept_peering(request: Request, pid: str, peering_id: str):
    """Accept a peering request from another account."""
    s = request.app.state.sim
    p = getattr(s, "vpc_peerings", {}).get(peering_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_msg": "Peering not found", "error_code": "VPC.0301"}, status_code=404)
    p["status"] = "ACTIVE"
    p["updated_at"] = now_millis()
    return {"peering": _peering_json(p)}


@router.put("/v2.0/{pid}/vpc-peerings/{peering_id}/reject")
async def reject_peering(request: Request, pid: str, peering_id: str):
    """Reject a peering request from another account."""
    s = request.app.state.sim
    p = getattr(s, "vpc_peerings", {}).get(peering_id)
    if not p or p["project_id"] != pid:
        return JSONResponse({"error_msg": "Peering not found", "error_code": "VPC.0301"}, status_code=404)
    p["status"] = "REJECTED"
    p["updated_at"] = now_millis()
    return {"peering": _peering_json(p)}


@router.put("/v2.0/{pid}/vpc-peerings/{peering_id}")
async def update_peering(request: Request, pid: str, peering_id: str):
    """Update a peering connection's name or description."""
    s = request.app.state.sim
    p = getattr(s, "vpc_peerings", {}).get(peering_id)
    if not p or p.get("project_id") != pid:
        return JSONResponse({"error_msg": "Peering not found",
                             "error_code": "VPC.0301"}, status_code=404)
    body = await request.json()
    if "name" in body and body["name"]:
        p["name"] = body["name"]
    return {"peering": _peering_json(p)}


@router.delete("/v2.0/{pid}/vpc-peerings/{peering_id}")
async def delete_peering(request: Request, pid: str, peering_id: str):
    """Delete a peering connection."""
    s = request.app.state.sim
    if peering_id not in getattr(s, "vpc_peerings", {}):
        return JSONResponse({"error_msg": "Peering not found", "error_code": "VPC.0301"}, status_code=404)
    del s.vpc_peerings[peering_id]
    return Response(status_code=204)
