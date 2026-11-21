"""ER (Enterprise Router): hub-and-spoke VPC routing.

Real routes: POST /v3/{project_id}/enterprise-router/instances, and
/v3/{project_id}/enterprise-router/instances/{er_id}/attachments (vpc attachments).
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v3/{pid}/enterprise-router/instances")
async def create_instance(request: Request, pid: str):
    """Create an Enterprise Router instance: the transit hub for VPCs (async)."""
    s = request.app.state.sim
    if not hasattr(s, "er_instances"):
        s.er_instances = {}
    if not hasattr(s, "er_attachments"):
        s.er_attachments = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "ER.0001", "error_msg": "name is required"},
                            status_code=400)
    eid = new_id()
    s.er_instances[eid] = {
        "id": eid, "name": name, "state": "pending",
        "asn": body.get("asn", 64512),
        "description": body.get("description", ""),
        "enable_default_association": body.get("enable_default_association", True),
        "enable_default_propagation": body.get("enable_default_propagation", True),
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": pid, "tags": body.get("tags", []),
    }

    async def effect():
        er = s.er_instances.get(eid)
        if er:
            er["state"] = "available"
            er["updated_at"] = now_millis()
        return None

    await s.jobs.submit("createErInstance", {"instance_id": eid}, effect)
    return {"instance": s.er_instances[eid]}


@router.get("/v3/{pid}/enterprise-router/instances")
async def list_instances(request: Request, pid: str):
    """List Enterprise Router instances."""
    s = request.app.state.sim
    state_f = request.query_params.get("state")
    instances = [i for i in getattr(s, "er_instances", {}).values()
                 if i["project_id"] == pid]
    if state_f:
        instances = [i for i in instances if i["state"] == state_f]
    return {"instances": instances, "total": len(instances)}


@router.get("/v3/{pid}/enterprise-router/instances/{er_id}")
async def show_instance(request: Request, pid: str, er_id: str):
    """Show one instance: its ASN, status, and default route table."""
    s = request.app.state.sim
    er = getattr(s, "er_instances", {}).get(er_id)
    if not er or er["project_id"] != pid:
        return JSONResponse({"error_code": "ER.0002", "error_msg": "instance not found"},
                            status_code=404)
    return {"instance": er}


@router.delete("/v3/{pid}/enterprise-router/instances/{er_id}")
async def delete_instance(request: Request, pid: str, er_id: str):
    """Delete an Enterprise Router instance."""
    s = request.app.state.sim
    er = getattr(s, "er_instances", {}).get(er_id)
    if not er or er["project_id"] != pid:
        return JSONResponse({"error_code": "ER.0002", "error_msg": "instance not found"},
                            status_code=404)
    if any(a["er_id"] == er_id for a in getattr(s, "er_attachments", {}).values()):
        return JSONResponse({"error_code": "ER.0003",
                             "error_msg": "instance has attachments"}, status_code=409)
    del s.er_instances[er_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# attachments (VPC spokes)
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/enterprise-router/instances/{er_id}/attachments")
@router.post("/v3/{pid}/enterprise-router/instances/{er_id}/vpc-attachments")
async def create_attachment(request: Request, pid: str, er_id: str):
    """Attach a VPC or another router to the Enterprise Router."""
    s = request.app.state.sim
    er = getattr(s, "er_instances", {}).get(er_id)
    if not er or er["project_id"] != pid:
        return JSONResponse({"error_code": "ER.0002", "error_msg": "instance not found"},
                            status_code=404)
    body = await request.json()
    vpc_id = body.get("vpc_id", "")
    if not vpc_id:
        return JSONResponse({"error_code": "ER.0004", "error_msg": "vpc_id is required"},
                            status_code=400)
    if not s.vpcs.get(vpc_id) or s.vpcs[vpc_id].get("project_id") != pid:
        return JSONResponse({"error_code": "ER.0005", "error_msg": "vpc not found"},
                            status_code=404)
    aid = new_id()
    s.er_attachments[aid] = {
        "id": aid, "name": body.get("name", f"att-{aid[:8]}"),
        "er_id": er_id, "vpc_id": vpc_id,
        "resource_type": "vpc", "state": "pending",
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": pid,
    }

    async def effect():
        att = s.er_attachments.get(aid)
        if att:
            att["state"] = "available"
            att["updated_at"] = now_millis()
        return None

    await s.jobs.submit("createErAttachment", {"attachment_id": aid}, effect)
    return {"attachment": s.er_attachments[aid]}


@router.get("/v3/{pid}/enterprise-router/instances/{er_id}/attachments")
@router.get("/v3/{pid}/enterprise-router/instances/{er_id}/vpc-attachments")
async def list_attachments(request: Request, pid: str, er_id: str):
    """List the attachments of an instance."""
    s = request.app.state.sim
    atts = [a for a in getattr(s, "er_attachments", {}).values()
            if a["project_id"] == pid and a["er_id"] == er_id]
    return {"attachments": atts, "total": len(atts),
            "request_id": new_id().replace("-", "")}


@router.delete("/v3/{pid}/enterprise-router/instances/{er_id}/attachments/{attachment_id}")
async def delete_attachment(request: Request, pid: str, er_id: str, attachment_id: str):
    """Remove an attachment."""
    s = request.app.state.sim
    att = getattr(s, "er_attachments", {}).get(attachment_id)
    if not att or att["project_id"] != pid or att["er_id"] != er_id:
        return JSONResponse({"error_code": "ER.0006", "error_msg": "attachment not found"},
                            status_code=404)
    del s.er_attachments[attachment_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# route tables
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/enterprise-router/instances/{er_id}/route-tables")
async def create_route_table(request: Request, pid: str, er_id: str):
    """Create a route table on the instance: the routing policy container."""
    s = request.app.state.sim
    er = getattr(s, "er_instances", {}).get(er_id)
    if not er or er["project_id"] != pid:
        return JSONResponse({"error_code": "ER.0002", "error_msg": "instance not found"},
                            status_code=404)
    if not hasattr(s, "er_route_tables"):
        s.er_route_tables = {}
    body = await request.json()
    tid = new_id()
    s.er_route_tables[tid] = {
        "id": tid, "name": body.get("name", f"rt-{tid[:8]}"),
        "er_id": er_id, "is_default_association": False,
        "is_default_propagation": False, "state": "available",
        "created_at": now_millis(), "project_id": pid,
    }
    return {"route_table": s.er_route_tables[tid]}


@router.get("/v3/{pid}/enterprise-router/instances/{er_id}/route-tables/{route_table_id}")
async def show_route_table(request: Request, pid: str, er_id: str, route_table_id: str):
    """Show one route table: its associations and propagations."""
    s = request.app.state.sim
    t = getattr(s, "er_route_tables", {}).get(route_table_id)
    if not t or t["project_id"] != pid or t["er_id"] != er_id:
        return JSONResponse({"error_code": "ER.0007", "error_msg": "route table not found"},
                            status_code=404)
    return {"route_table": t}


@router.get("/v3/{pid}/enterprise-router/instances/{er_id}/route-tables")
async def list_route_tables(request: Request, pid: str, er_id: str):
    """List the route tables of an instance."""
    s = request.app.state.sim
    tables = [t for t in getattr(s, "er_route_tables", {}).values()
              if t["project_id"] == pid and t["er_id"] == er_id]
    return {"route_tables": tables, "total": len(tables)}
