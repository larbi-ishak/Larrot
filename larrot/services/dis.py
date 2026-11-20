"""DIS (Data Ingestion Service): streams, partitions, apps, checkpoints.

Real route: POST /v2/{project_id}/streams.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


@router.post("/v2/{pid}/streams")
async def create_stream(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dis_streams"):
        s.dis_streams = {}
    body = await request.json()
    name = body.get("stream_name", "")
    if not name:
        return JSONResponse({"error_code": "DIS.0001", "error_msg": "stream_name is required"},
                            status_code=400)
    if any(x["stream_name"] == name for x in s.dis_streams.values()):
        return JSONResponse({"error_code": "DIS.0002", "error_msg": "stream already exists"},
                            status_code=409)
    partitions = body.get("partitions", 1)
    if not isinstance(partitions, int) or partitions < 1:
        return JSONResponse({"error_code": "DIS.0003",
                             "error_msg": "partitions must be >= 1"}, status_code=400)
    sid = new_id()
    s.dis_streams[sid] = {
        "stream_id": sid, "stream_name": name,
        "partition_count": partitions,
        "stream_type": body.get("stream_type", "COMMON"),
        "data_type": body.get("data_type", "BLOB"),
        "data_duration": body.get("data_duration", 24),
        "status": "RUNNING", "created_at": now_millis(),
        "project_id": pid, "retention_period": body.get("retention_period", 24),
    }
    return {"stream_id": sid, "stream_name": name}


@router.get("/v2/{pid}/streams")
async def list_streams(request: Request, pid: str):
    s = request.app.state.sim
    limit = int(request.query_params.get("limit", 10))
    start = request.query_params.get("start_name", "")
    streams = sorted([x for x in getattr(s, "dis_streams", {}).values()
                      if x["project_id"] == pid], key=lambda x: x["stream_name"])
    if start:
        streams = [x for x in streams if x["stream_name"] > start]
    page = streams[:limit]
    return {"stream_names": [x["stream_name"] for x in page],
            "has_more_streams": len(streams) > len(page)}


@router.get("/v2/{pid}/streams/{stream_name}")
async def show_stream(request: Request, pid: str, stream_name: str):
    s = request.app.state.sim
    stream = next((x for x in getattr(s, "dis_streams", {}).values()
                   if x["stream_name"] == stream_name and x["project_id"] == pid), None)
    if not stream:
        return JSONResponse({"error_code": "DIS.0004", "error_msg": "stream not found"},
                            status_code=404)
    return stream


@router.put("/v2/{pid}/streams/{stream_name}")
async def update_stream(request: Request, pid: str, stream_name: str):
    """Scale partitions up (grow only, like the real service)."""
    s = request.app.state.sim
    stream = next((x for x in getattr(s, "dis_streams", {}).values()
                   if x["stream_name"] == stream_name and x["project_id"] == pid), None)
    if not stream:
        return JSONResponse({"error_code": "DIS.0004", "error_msg": "stream not found"},
                            status_code=404)
    body = await request.json()
    new_count = body.get("partition_count")
    if not isinstance(new_count, int) or new_count < stream["partition_count"]:
        return JSONResponse({"error_code": "DIS.0003",
                             "error_msg": "partition_count can only grow"}, status_code=400)
    stream["partition_count"] = new_count
    return stream


@router.delete("/v2/{pid}/streams/{stream_name}")
async def delete_stream(request: Request, pid: str, stream_name: str):
    s = request.app.state.sim
    sid = next((k for k, x in getattr(s, "dis_streams", {}).items()
                if x["stream_name"] == stream_name and x["project_id"] == pid), None)
    if not sid:
        return JSONResponse({"error_code": "DIS.0004", "error_msg": "stream not found"},
                            status_code=404)
    del s.dis_streams[sid]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# consumer apps + checkpoints
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/apps")
async def create_app(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "dis_apps"):
        s.dis_apps = {}
    body = await request.json()
    name = body.get("app_name", "")
    if not name:
        return JSONResponse({"error_code": "DIS.0005", "error_msg": "app_name is required"},
                            status_code=400)
    aid = new_id()
    s.dis_apps[aid] = {
        "app_id": aid, "app_name": name, "project_id": pid,
        "created_at": now_millis(),
    }
    return {"app_name": name}


@router.get("/v2/{pid}/apps")
async def list_apps(request: Request, pid: str):
    s = request.app.state.sim
    apps = [a for a in getattr(s, "dis_apps", {}).values() if a["project_id"] == pid]
    return {"apps": apps, "total": len(apps)}


@router.put("/v2/{pid}/apps/{app_name}/checkpoints")
async def commit_checkpoint(request: Request, pid: str, app_name: str):
    """Commit a consumer checkpoint for a stream."""
    s = request.app.state.sim
    if not hasattr(s, "dis_checkpoints"):
        s.dis_checkpoints = {}
    body = await request.json()
    stream_name = body.get("stream_name", "")
    if not any(x["stream_name"] == stream_name for x in
               getattr(s, "dis_streams", {}).values()):
        return JSONResponse({"error_code": "DIS.0004", "error_msg": "stream not found"},
                            status_code=404)
    key = f"{app_name}/{stream_name}"
    s.dis_checkpoints[key] = {
        "app_name": app_name, "stream_name": stream_name,
        "checkpoint_type": body.get("checkpoint_type", "LAST_READ"),
        "checkpoint_state": body.get("checkpoint_state", ""),
        "commit_timestamp": now_millis(), "project_id": pid,
    }
    return {"checkpoint": s.dis_checkpoints[key]}


@router.get("/v2/{pid}/apps/{app_name}/checkpoints")
async def list_checkpoints(request: Request, pid: str, app_name: str):
    s = request.app.state.sim
    cps = [c for c in getattr(s, "dis_checkpoints", {}).values()
           if c["project_id"] == pid and c["app_name"] == app_name]
    return {"checkpoints": cps, "total": len(cps)}
