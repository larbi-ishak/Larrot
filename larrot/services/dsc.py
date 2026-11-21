"""DSC (Data Security Center): assets, scan tasks, risk items.

Real route is GET /v1/{project_id}/assets on the DSC endpoint; namespaced here
under /v1/{pid}/dsc/assets to avoid colliding with VOD's asset routes.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v1/{pid}/dsc/assets")
async def create_asset(request: Request, pid: str):
    """Register a data asset with DSC: the database or bucket to scan for sensitive data."""
    s = request.app.state.sim
    if not hasattr(s, "dsc_assets"):
        s.dsc_assets = {}
    body = await request.json()
    name = body.get("asset_name", "")
    if not name:
        return JSONResponse({"error_code": "DSC.0001", "error_msg": "asset_name is required"},
                            status_code=400)
    aid = new_id()
    s.dsc_assets[aid] = {
        "asset_id": aid, "asset_name": name,
        "asset_type": body.get("asset_type", "OBS"),
        "risk_count": 0, "sensitive_count": 0,
        "location": body.get("location", "ap-southeast-1"),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"asset": s.dsc_assets[aid]}


@router.get("/v1/{pid}/dsc/assets")
async def list_assets(request: Request, pid: str):
    """List registered data assets."""
    s = request.app.state.sim
    assets = [a for a in getattr(s, "dsc_assets", {}).values()
              if a["project_id"] == pid]
    return {"assets": assets, "total": len(assets)}


@router.delete("/v1/{pid}/dsc/assets/{asset_id}")
async def delete_asset(request: Request, pid: str, asset_id: str):
    """Remove a data asset."""
    s = request.app.state.sim
    if asset_id not in getattr(s, "dsc_assets", {}):
        return JSONResponse({"error_code": "DSC.0002", "error_msg": "asset not found"},
                            status_code=404)
    del s.dsc_assets[asset_id]
    return Response(status_code=204)


@router.post("/v1/{pid}/dsc/scans")
async def create_scan(request: Request, pid: str):
    """Scan an asset for sensitive data: discovers seeded risk items."""
    s = request.app.state.sim
    if not hasattr(s, "dsc_risks"):
        s.dsc_risks = {}
    body = await request.json()
    asset_id = body.get("asset_id", "")
    asset = getattr(s, "dsc_assets", {}).get(asset_id)
    if not asset or asset["project_id"] != pid:
        return JSONResponse({"error_code": "DSC.0002", "error_msg": "asset not found"},
                            status_code=404)
    scan_id = new_id()
    risks = []
    for i, risk_type in enumerate(body.get("risk_types",
                                           ["PII", "API_KEY", "CREDIT_CARD"])):
        rid = new_id()
        s.dsc_risks[rid] = {
            "risk_id": rid, "asset_id": asset_id, "risk_type": risk_type,
            "risk_level": "high" if i == 0 else "medium",
            "status": "open", "occurrence_time": now_millis(),
            "project_id": pid,
        }
        risks.append(rid)
    asset["risk_count"] += len(risks)
    asset["sensitive_count"] += len(risks)
    return {"scan_id": scan_id, "risk_ids": risks, "total": len(risks)}


@router.get("/v1/{pid}/dsc/risks")
async def list_risks(request: Request, pid: str):
    """List sensitive-data risks found by scans."""
    s = request.app.state.sim
    status_f = request.query_params.get("status")
    risks = [r for r in getattr(s, "dsc_risks", {}).values()
             if r["project_id"] == pid]
    if status_f:
        risks = [r for r in risks if r["status"] == status_f]
    return {"risks": risks, "total": len(risks)}


@router.post("/v1/{pid}/dsc/risks/{risk_id}/handle")
async def handle_risk(request: Request, pid: str, risk_id: str):
    """Mark a risk as handled (real DSC: ignore / report as false positive)."""
    s = request.app.state.sim
    risk = getattr(s, "dsc_risks", {}).get(risk_id)
    if not risk or risk["project_id"] != pid:
        return JSONResponse({"error_code": "DSC.0003", "error_msg": "risk not found"},
                            status_code=404)
    risk["status"] = "handled"
    return {"risk_id": risk_id, "status": "handled"}
