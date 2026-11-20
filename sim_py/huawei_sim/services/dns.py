"""DNS — zone and recordset management."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _zone_json(z):
    return {"id": z["id"], "name": z["name"], "description": z.get("description", ""),
            "email": z.get("email", "admin@example.com"), "zone_type": z.get("zone_type", "private"),
            "status": z.get("status", "ACTIVE"), "record_num": len(z.get("recordsets", [])),
            "created_at": z["created_at"], "updated_at": z["updated_at"]}


def _recordset_json(r):
    return {"id": r["id"], "name": r["name"], "zone_id": r["zone_id"],
            "zone_name": r["zone_name"], "type": r["type"], "ttl": r.get("ttl", 300),
            "records": r.get("records", []), "status": r.get("status", "ACTIVE"),
            "created_at": r["created_at"], "updated_at": r["updated_at"]}


@router.post("/v2/zones")
async def create_zone(request: Request):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    body = await request.json()
    zone_id = new_id()
    now = now_millis()
    state.dns_zones[zone_id] = {
        "id": zone_id, "name": body["name"], "description": body.get("description", ""),
        "email": body.get("email", "admin@example.com"),
        "zone_type": body.get("zone_type", "private"),
        "status": "ACTIVE", "recordsets": [], "created_at": now, "updated_at": now,
        "project_id": state.account["domain_id"],
    }
    return {"zone": _zone_json(state.dns_zones[zone_id])}


@router.get("/v2/zones")
async def list_zones(request: Request):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    return {"zones": [_zone_json(z) for z in state.dns_zones.values()],
            "count": len(state.dns_zones)}


@router.get("/v2/zones/{zone_id}")
async def show_zone(request: Request, zone_id: str):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    z = state.dns_zones.get(zone_id)
    if not z:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    return {"zone": _zone_json(z)}


@router.delete("/v2/zones/{zone_id}")
async def delete_zone(request: Request, zone_id: str):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    if zone_id not in state.dns_zones:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    del state.dns_zones[zone_id]
    return Response(status_code=204)


@router.post("/v2/zones/{zone_id}/recordsets")
async def create_recordset(request: Request, zone_id: str):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    zone = state.dns_zones.get(zone_id)
    if not zone:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    body = await request.json()
    rs_id = new_id()
    now = now_millis()
    rs = {"id": rs_id, "name": body["name"], "zone_id": zone_id,
          "zone_name": zone["name"], "type": body.get("type", "A"),
          "ttl": body.get("ttl", 300), "records": body.get("records", []),
          "status": "ACTIVE", "created_at": now, "updated_at": now}
    zone["recordsets"].append(rs)
    return {"recordset": _recordset_json(rs)}


@router.get("/v2/zones/{zone_id}/recordsets")
async def list_recordsets(request: Request, zone_id: str):
    state = request.app.state.sim
    if not hasattr(state, "dns_zones"):
        state.dns_zones = {}
    zone = state.dns_zones.get(zone_id)
    if not zone:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    return {"recordsets": [_recordset_json(r) for r in zone["recordsets"]],
            "count": len(zone["recordsets"])}


@router.delete("/v2/zones/{zone_id}/recordsets/{recordset_id}")
async def delete_recordset(request: Request, zone_id: str, recordset_id: str):
    state = request.app.state.sim
    zone = state.dns_zones.get(zone_id)
    if not zone:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    zone["recordsets"] = [r for r in zone["recordsets"] if r["id"] != recordset_id]
    return Response(status_code=204)
