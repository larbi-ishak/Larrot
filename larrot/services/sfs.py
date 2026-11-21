"""SFS: Scalable File System (shares, access rules)."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _share_json(s):
    return {
        "id": s["id"], "name": s["name"], "description": s.get("description", ""),
        "size": s["size"], "share_proto": s.get("share_proto", "NFS"),
        "status": s.get("status", "available"),
        "availability_zone": s.get("availability_zone", "az1"),
        "export_location": s.get("export_location", ""),
        "export_locations": s.get("export_locations", []),
        "volume_type": s.get("volume_type", "default"),
        "share_type": s.get("share_type", "default"),
        "project_id": s.get("project_id", ""),
        "created_at": s["created_at"], "updated_at": s["updated_at"],
    }


@router.post("/v2/{pid}/shares")
async def create_share(request: Request, pid: str):
    """Create an SFS Turbo file share: the shared POSIX filesystem (async)."""
    state = request.app.state.sim
    if not hasattr(state, "sfs_shares"):
        state.sfs_shares = {}
    body = await request.json()
    spec = body.get("share", body)
    share_id = new_id()
    now = now_millis()
    export = f"192.168.0.{50 + len(state.sfs_shares)}:/shares/{share_id}"
    state.sfs_shares[share_id] = {
        "id": share_id, "name": spec.get("name", f"share-{share_id[:8]}"),
        "description": spec.get("description", ""),
        "size": spec.get("size", 100),
        "share_proto": spec.get("share_proto", "NFS"),
        "status": "creating",
        "availability_zone": spec.get("availability_zone", "az1"),
        "export_location": export, "export_locations": [{"path": export}],
        "created_at": now, "updated_at": now, "project_id": pid,
    }

    import asyncio
    async def _flip():
        await asyncio.sleep(1.5)
        s = getattr(state, "sfs_shares", {}).get(share_id)
        if s:
            s["status"] = "available"
            s["updated_at"] = now_millis()
    asyncio.get_event_loop().create_task(_flip())

    return {"share": _share_json(state.sfs_shares[share_id])}


@router.get("/v2/{pid}/shares")
async def list_shares(request: Request, pid: str):
    """List file shares with their sizes and export locations."""
    state = request.app.state.sim
    if not hasattr(state, "sfs_shares"):
        state.sfs_shares = {}
    shares = [s for s in state.sfs_shares.values() if s["project_id"] == pid]
    return {"shares": [_share_json(s) for s in shares], "count": len(shares)}


@router.get("/v2/{pid}/shares/{share_id}")
async def show_share(request: Request, pid: str, share_id: str):
    """Show one share: its capacity, protocol, and mount target."""
    state = request.app.state.sim
    s = getattr(state, "sfs_shares", {}).get(share_id)
    if not s or s["project_id"] != pid:
        return JSONResponse({"error_msg": "Share not found", "error_code": "SFS.0101"}, status_code=404)
    return {"share": _share_json(s)}


@router.delete("/v2/{pid}/shares/{share_id}")
async def delete_share(request: Request, pid: str, share_id: str):
    """Delete a file share (async)."""
    state = request.app.state.sim
    s = getattr(state, "sfs_shares", {}).get(share_id)
    if not s or s["project_id"] != pid:
        return JSONResponse({"error_msg": "Share not found", "error_code": "SFS.0101"}, status_code=404)
    del state.sfs_shares[share_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/shares/{share_id}/action")
async def share_action(request: Request, pid: str, share_id: str):
    """Share action: expand capacity or change the performance mode (async)."""
    state = request.app.state.sim
    s = getattr(state, "sfs_shares", {}).get(share_id)
    if not s or s["project_id"] != pid:
        return JSONResponse({"error_msg": "Share not found", "error_code": "SFS.0101"}, status_code=404)
    body = await request.json()
    if "os-extend" in body:
        new_size = body["os-extend"]["new_size"]
        s["size"] = new_size
        s["updated_at"] = now_millis()
        return {"share": _share_json(s)}
    if "allow_access" in body:
        rule = body["allow_access"]
        s.setdefault("access_rules", []).append({
            "id": new_id(), "access_type": rule.get("access_type", "ip"),
            "access_to": rule.get("access_to", "0.0.0.0/0"),
            "access_level": rule.get("access_level", "rw"),
        })
        return {"access": s["access_rules"][-1]}
    return JSONResponse({"error_msg": "Unknown action", "error_code": "SFS.0102"}, status_code=400)
