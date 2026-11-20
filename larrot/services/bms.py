"""BMS: Bare Metal Server: instances, flavors."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.get("/v1/{pid}/baremetalservers/detail")
async def list_bms(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "bms_servers"): s.bms_servers = {}
    return {"servers": list(s.bms_servers.values()), "count": len(s.bms_servers)}

@router.post("/v1/{pid}/baremetalservers")
async def create_bms(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "bms_servers"): s.bms_servers = {}
    body = await request.json()
    bid = new_id()
    s.bms_servers[bid] = {"id": bid, "name": body.get("name", f"bms-{bid[:8]}"),
        "status": "BUILD", "flavor_ref": body.get("flavor_ref", "physical.o2.medium"),
        "image_id": body.get("image_ref", ""), "availability_zone": body.get("availability_zone", "az1"),
        "vpc_id": body.get("vpc_id", ""), "created_at": now_millis(), "project_id": pid}
    return {"server": s.bms_servers[bid], "job_id": new_id()}

@router.get("/v1/{pid}/baremetalservers/{server_id}")
async def show_bms(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    b = getattr(s, "bms_servers", {}).get(server_id)
    if not b or b["project_id"] != pid:
        return JSONResponse({"error": {"code": "BMS.0101", "message": "BMS not found"}}, status_code=404)
    return {"server": b}

@router.delete("/v1/{pid}/baremetalservers/{server_id}")
async def delete_bms(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    if server_id not in getattr(s, "bms_servers", {}):
        return JSONResponse({"error": {"code": "BMS.0101", "message": "BMS not found"}}, status_code=404)
    del s.bms_servers[server_id]
    return {"job_id": new_id()}
