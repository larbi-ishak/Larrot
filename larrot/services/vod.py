"""VOD (Video on Demand): media assets, transcode templates, categories.

Real routes: POST /v1/{project_id}/assets (media assets),
POST /v1/{project_id}/transcode-templates, POST /v1/{project_id}/categories.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _asset_json(a):
    return {
        "asset_id": a["id"], "asset_name": a["name"], "asset_type": a["type"],
        "status": a["status"], "category_id": a["category_id"],
        "duration": a["duration"], "media_type": a["media_type"],
        "video_url": f"https://vod.myhuaweicloud.com/{a['id']}/index.m3u8",
        "created_at": a["created_at"],
    }


@router.post("/v1/{pid}/assets")
async def create_asset(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vod_assets"):
        s.vod_assets = {}
    body = await request.json()
    name = body.get("asset_name", body.get("name", ""))
    if not name:
        return JSONResponse({"error_code": "VOD.0001", "error_msg": "asset_name is required"},
                            status_code=400)
    aid = new_id()
    s.vod_assets[aid] = {
        "id": aid, "name": name, "type": body.get("asset_type", "video"),
        "status": "EMPTY",  # EMPTY → PUBLISHED after upload
        "category_id": body.get("category_id", -1),
        "duration": body.get("duration", 0),
        "media_type": body.get("media_type", "MP4"),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"asset": _asset_json(s.vod_assets[aid])}


@router.get("/v1/{pid}/assets")
async def list_assets(request: Request, pid: str):
    s = request.app.state.sim
    status_f = request.query_params.get("status")
    assets = [a for a in getattr(s, "vod_assets", {}).values()
              if a["project_id"] == pid]
    if status_f:
        assets = [a for a in assets if a["status"] == status_f]
    return {"assets": [_asset_json(a) for a in assets], "total": len(assets)}


@router.get("/v1/{pid}/assets/{asset_id}")
async def show_asset(request: Request, pid: str, asset_id: str):
    s = request.app.state.sim
    a = getattr(s, "vod_assets", {}).get(asset_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "VOD.0002", "error_msg": "asset not found"},
                            status_code=404)
    return {"asset": _asset_json(a)}


@router.post("/v1/{pid}/assets/{asset_id}/upload")
async def upload_asset(request: Request, pid: str, asset_id: str):
    """Simulate uploading media: asset goes EMPTY → PUBLISHED via a job."""
    s = request.app.state.sim
    a = getattr(s, "vod_assets", {}).get(asset_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "VOD.0002", "error_msg": "asset not found"},
                            status_code=404)
    a["status"] = "UPLOADING"

    async def effect():
        x = s.vod_assets.get(asset_id)
        if x:
            x["status"] = "PUBLISHED"
            x["duration"] = 120  # seconds, after "processing"
        return None

    await s.jobs.submit("uploadVodAsset", {"asset_id": asset_id}, effect)
    return {"asset_id": asset_id, "status": "UPLOADING"}


@router.delete("/v1/{pid}/assets/{asset_id}")
async def delete_asset(request: Request, pid: str, asset_id: str):
    s = request.app.state.sim
    a = getattr(s, "vod_assets", {}).get(asset_id)
    if not a or a["project_id"] != pid:
        return JSONResponse({"error_code": "VOD.0002", "error_msg": "asset not found"},
                            status_code=404)
    del s.vod_assets[asset_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# transcode templates
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/transcode-templates")
async def create_transcode_template(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vod_templates"):
        s.vod_templates = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "VOD.0003", "error_msg": "name is required"},
                            status_code=400)
    tid = new_id()
    s.vod_templates[tid] = {
        "template_id": tid, "name": name,
        "video": body.get("video", {"width": 1920, "height": 1080,
                                    "bitrate": 2000, "codec": "H.264"}),
        "audio": body.get("audio", {"bitrate": 128, "codec": "AAC"}),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"template": s.vod_templates[tid]}


@router.get("/v1/{pid}/transcode-templates")
async def list_transcode_templates(request: Request, pid: str):
    s = request.app.state.sim
    templates = [t for t in getattr(s, "vod_templates", {}).values()
                 if t["project_id"] == pid]
    return {"templates": templates, "total": len(templates)}


@router.delete("/v1/{pid}/transcode-templates/{template_id}")
async def delete_transcode_template(request: Request, pid: str, template_id: str):
    s = request.app.state.sim
    if template_id not in getattr(s, "vod_templates", {}):
        return JSONResponse({"error_code": "VOD.0004", "error_msg": "template not found"},
                            status_code=404)
    del s.vod_templates[template_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# categories
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/categories")
async def create_category(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "vod_categories"):
        s.vod_categories = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "VOD.0005", "error_msg": "name is required"},
                            status_code=400)
    cid = new_id()
    s.vod_categories[cid] = {
        "category_id": cid, "name": name,
        "parent_id": body.get("parent_id", -1),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"category": s.vod_categories[cid]}


@router.get("/v1/{pid}/categories")
async def list_categories(request: Request, pid: str):
    s = request.app.state.sim
    categories = [c for c in getattr(s, "vod_categories", {}).values()
                  if c["project_id"] == pid]
    return {"categories": categories, "total": len(categories)}
