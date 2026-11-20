"""DNS: zone and recordset management."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import apigw_error
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _zone_json(z):
    return {"id": z["id"], "name": z["name"], "description": z.get("description", ""),
            "email": z.get("email", "admin@example.com"), "zone_type": z.get("zone_type", "private"),
            "ttl": z.get("ttl", 300),
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


@router.put("/v2/zones/{zone_id}")
async def update_zone(request: Request, zone_id: str):
    state = request.app.state.sim
    z = state.dns_zones.get(zone_id)
    if not z:
        return JSONResponse(apigw_error("DNS.0101", "Zone does not exist."), status_code=404)
    body = await request.json()
    if "email" in body:
        z["email"] = body["email"]
    if "ttl" in body:
        z["ttl"] = body["ttl"]
    if "description" in body:
        z["description"] = body["description"]
    z["updated_at"] = now_millis()
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


@router.get("/v2/zones/{zone_id}/recordsets/{recordset_id}")
async def show_recordset(request: Request, zone_id: str, recordset_id: str):
    state = request.app.state.sim
    z = state.dns_zones.get(zone_id)
    if not z:
        return JSONResponse(apigw_error("DNS.0101", "Zone does not exist."), status_code=404)
    r = next((x for x in z.get("recordsets", []) if x["id"] == recordset_id), None)
    if not r:
        return JSONResponse(apigw_error("DNS.0102", "Record set does not exist."), status_code=404)
    return {"recordset": _recordset_json(r)}


@router.put("/v2/zones/{zone_id}/recordsets/{recordset_id}")
async def update_recordset(request: Request, zone_id: str, recordset_id: str):
    state = request.app.state.sim
    z = state.dns_zones.get(zone_id)
    if not z:
        return JSONResponse(apigw_error("DNS.0101", "Zone does not exist."), status_code=404)
    r = next((x for x in z.get("recordsets", []) if x["id"] == recordset_id), None)
    if not r:
        return JSONResponse(apigw_error("DNS.0102", "Record set does not exist."), status_code=404)
    body = await request.json()
    if "name" in body:
        r["name"] = body["name"]
    if "records" in body:
        r["records"] = body["records"]
    if "ttl" in body:
        r["ttl"] = body["ttl"]
    r["updated_at"] = now_millis()
    return {"recordset": _recordset_json(r)}


@router.delete("/v2/zones/{zone_id}/recordsets/{recordset_id}")
async def delete_recordset(request: Request, zone_id: str, recordset_id: str):
    state = request.app.state.sim
    zone = state.dns_zones.get(zone_id)
    if not zone:
        return JSONResponse({"error_msg": "Zone not found", "error_code": "DNS.0101"}, status_code=404)
    zone["recordsets"] = [r for r in zone["recordsets"] if r["id"] != recordset_id]
    return Response(status_code=204)


@router.get("/v2/recordsets")
async def list_all_recordsets(request: Request):
    state = request.app.state.sim
    out = []
    for z in state.dns_zones.values():
        out.extend(_recordset_json(r) for r in z.get("recordsets", []))
    return {"recordsets": out, "metadata": {"total_count": len(out)}}
