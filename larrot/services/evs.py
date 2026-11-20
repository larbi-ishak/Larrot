"""EVS: cloud volumes, snapshots, os-vendor detail."""

import asyncio
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import evs_error
from ..core.jobs import new_id, now_millis
from ..core.profiles import Profile

router = APIRouter()


def _detail(v, pid):
    return {
        "attachments": [{"server_id": a["server_id"], "device": a["device"], "id": v["id"]}
                        for a in v["attachments"]],
        "links": [{"href": f"http://sim/v2/{pid}/volumes/{v['id']}", "rel": "self"},
                  {"href": f"http://sim/{pid}/volumes/{v['id']}", "rel": "bookmark"}],
        "availability_zone": v["availability_zone"],
        "os-vol-host-attr:host": f"{v['availability_zone']}#{v['volume_type']}",
        "encrypted": v["encrypted"],
        "multiattach": v["multiattach"],
        "shareable": False,
        "updated_at": v["updated_at"],
        "replication_status": "disabled",
        "os-volume-replication:extended_status": "disabled",
        "id": v["id"], "size": v["size"], "user_id": v["user_id"],
        "os-vol-tenant-attr:tenant_id": v["project_id"],
        "metadata": v["metadata"], "tags": v["tags"],
        "status": v["status"], "description": v["description"],
        "name": v["name"], "bootable": v["bootable"],
        "created_at": v["created_at"], "service_type": "EVS",
        "wwn": v["wwn"], "volume_type": v["volume_type"],
        "snapshot_id": None, "source_volid": None,
        "volume_image_metadata": None,
    }


def _summary(v, pid):
    return {
        "id": v["id"],
        "links": [{"href": f"http://sim/v2/{pid}/volumes/{v['id']}", "rel": "self"},
                  {"href": f"http://sim/{pid}/volumes/{v['id']}", "rel": "bookmark"}],
        "name": v["name"],
    }


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@router.post("/v2.1/{pid}/cloudvolumes")
async def create_volume_v21(request: Request, pid: str):
    return await _create_volume(request, pid, include_ids=True)


@router.post("/v2/{pid}/cloudvolumes")
async def create_volume_v2(request: Request, pid: str):
    return await _create_volume(request, pid, include_ids=False)


async def _create_volume(request, pid, include_ids):
    state = request.app.state.sim
    body = await request.json()
    spec = body["volume"]

    size = spec.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not (10 <= size <= 32768):
        return JSONResponse(evs_error("EVS.1010", "invalid volume size!"), status_code=400)

    bootable = bool(spec.get("imageRef") or spec.get("snapshot_id"))
    source = None
    if spec.get("imageRef"):
        source = ("imageRef", spec["imageRef"])
    elif spec.get("snapshot_id"):
        source = ("snapshot_id", spec["snapshot_id"])

    az = spec.get("availability_zone") or (
        "az-dc-1" if state.profile_of(pid) == Profile.HCS
        else f"{state.project(pid)['name']}a" if state.project(pid) else "")
    vtype = spec.get("volume_type", "SAS")
    count = min(spec.get("count", 1), 100)
    name = spec.get("name", f"evs-{new_id()[:8]}")

    ids = []
    for i in range(count):
        n = name if count == 1 else f"{name}-{i:04d}"
        vid = state.create_volume(pid, n, size, az, vtype, bootable, source)
        ids.append(vid)

    async def effect():
        for vid in ids:
            v = state.volumes.get(vid)
            if v:
                v["status"] = "available"
                v["updated_at"] = now_millis()
        return None

    job_type = "batchCreateVolume" if count > 1 else "createVolume"
    job_id = await state.jobs.submit(job_type, {"volume_ids": ids}, effect)

    if include_ids:
        return JSONResponse({"job_id": job_id, "volume_ids": ids}, status_code=202)
    return JSONResponse({"job_id": job_id}, status_code=202)


@router.post("/v2/{pid}/volumes")
async def create_volume_cinder(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["volume"]
    size = spec.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not (10 <= size <= 32768):
        return JSONResponse(evs_error("EVS.1010", "invalid volume size!"), status_code=400)
    bootable = bool(spec.get("imageRef") or spec.get("snapshot_id"))
    source = ("imageRef", spec["imageRef"]) if spec.get("imageRef") else None
    az = spec.get("availability_zone", "az-dc-1")
    vid = state.create_volume(pid, spec.get("name", ""), size, az,
                              spec.get("volume_type", "SAS"), bootable, source)

    async def effect():
        v = state.volumes.get(vid)
        if v:
            v["status"] = "available"
            v["updated_at"] = now_millis()
        return None

    await state.jobs.submit("createVolume", {"volume_ids": [vid]}, effect)
    v = state.volumes[vid]
    detail = _detail(v, pid)
    if state.profile_of(pid) == Profile.HCS:
        detail["id"] = ""  # hcs anomaly (§3.3)
    return JSONResponse({"volume": detail}, status_code=202)


# ---------------------------------------------------------------------------
# list / show / update / delete
# ---------------------------------------------------------------------------

@router.get("/v2/{pid}/cloudvolumes")
async def list_volumes_sparse(request: Request, pid: str):
    state = request.app.state.sim
    name = request.query_params.get("name")
    status_f = request.query_params.get("status")
    vols = [v for v in state.volumes.values() if v["project_id"] == pid]
    if name:
        vols = [v for v in vols if name in v["name"]]
    if status_f:
        vols = [v for v in vols if v["status"] == status_f]
    return {"volumes": [_summary(v, pid) for v in vols]}


@router.get("/v2/{pid}/cloudvolumes/detail")
async def list_volumes_detail(request: Request, pid: str):
    state = request.app.state.sim
    vols = [v for v in state.volumes.values() if v["project_id"] == pid]
    return {"count": len(vols), "volumes": [_detail(v, pid) for v in vols]}


@router.get("/v2.1/{pid}/cloudvolumes/detail")
async def list_volumes_detail_v21(request: Request, pid: str):
    state = request.app.state.sim
    if state.profile_of(pid) == Profile.HCS:
        return {"volumes": []}
    vols = [v for v in state.volumes.values() if v["project_id"] == pid]
    return {"count": len(vols), "volumes": [_detail(v, pid) for v in vols]}


@router.get("/v2/{pid}/cloudvolumes/{volume_id}")
@router.get("/v2/{pid}/os-vendor-volumes/{volume_id}")
async def show_volume(request: Request, pid: str, volume_id: str):
    state = request.app.state.sim
    v = state.volumes.get(volume_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    return {"volume": _detail(v, pid)}


@router.get("/v2/{pid}/os-vendor-volumes/detail")
async def os_vendor_list(request: Request, pid: str):
    state = request.app.state.sim
    vols = [v for v in state.volumes.values() if v["project_id"] == pid]
    return {"volumes": [_detail(v, pid) for v in vols]}


@router.put("/v2/{pid}/cloudvolumes/{volume_id}")
async def update_volume(request: Request, pid: str, volume_id: str):
    state = request.app.state.sim
    v = state.volumes.get(volume_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    body = await request.json()
    spec = body.get("volume", {})
    if "name" in spec:
        v["name"] = spec["name"]
    if "description" in spec:
        v["description"] = spec["description"]
    v["updated_at"] = now_millis()
    return {"volume": _detail(v, pid)}


@router.delete("/v2/{pid}/cloudvolumes/{volume_id}")
async def delete_volume(request: Request, pid: str, volume_id: str):
    state = request.app.state.sim
    v = state.volumes.get(volume_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    if v["status"] != "available":
        return JSONResponse(evs_error("EVS.1046",
            "volume status must be available, extending, uploading, restoring, error_extending, error_restoring, rollbacking... when delete volume!"),
            status_code=400)

    async def effect():
        state.volumes.pop(volume_id, None)
        return None

    job_id = await state.jobs.submit("deleteVolume", {"volume_id": volume_id}, effect)
    return JSONResponse({"job_id": job_id}, status_code=202)


@router.post("/v2.1/{pid}/cloudvolumes/{volume_id}/action")
async def volume_action(request: Request, pid: str, volume_id: str):
    state = request.app.state.sim
    body = await request.json()
    if "os-extend" not in body:
        return JSONResponse(evs_error("EVS.5400", "Malformed request body."), status_code=400)
    v = state.volumes.get(volume_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    new_size = body["os-extend"]["new_size"]
    if new_size <= v["size"] or not (10 <= new_size <= 32768):
        return JSONResponse(evs_error("EVS.1010", "invalid volume size!"), status_code=400)

    async def effect():
        vol = state.volumes.get(volume_id)
        if vol:
            vol["size"] = new_size
            vol["updated_at"] = now_millis()
        return None

    job_id = await state.jobs.submit("extendVolume", {"volume_id": volume_id}, effect)
    return JSONResponse({"job_id": job_id}, status_code=202)


# ---------------------------------------------------------------------------
# snapshots: the detached-only rule (§3.4)
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/cloudsnapshots")
async def create_snapshot(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["snapshot"]
    vol = state.volumes.get(spec["volume_id"])
    if not vol or vol["project_id"] != pid:
        return JSONResponse(evs_error("EVS.1002", "invalid volume id!"), status_code=400)

    force = spec.get("force", False)
    if vol["status"] == "in-use":
        return JSONResponse(evs_error("EVS.1046",
            "volume status must be available when create snapshot!"), status_code=400)
    if vol["status"] == "attaching" and not force:
        return JSONResponse(evs_error("EVS.1046",
            "volume status must be available when create snapshot!"), status_code=400)

    snap_id = new_id()
    now = now_millis()
    state.snapshots[snap_id] = {
        "id": snap_id, "status": "creating",
        "name": spec.get("name", f"snap-{snap_id[:8]}"),
        "description": spec.get("description", ""),
        "volume_id": vol["id"], "size": vol["size"],
        "created_at": now, "updated_at": now,
        "metadata": {}, "project_id": pid,
    }

    async def _flip():
        s = state.snapshots.get(snap_id)
        if s:
            s["status"] = "available"
            s["updated_at"] = now_millis()

    # Through the job engine so tests can force completion (complete_now)
    await state.jobs.submit("createSnapshot", {"snapshot_id": snap_id}, _flip)

    s = state.snapshots[snap_id]
    return JSONResponse({"snapshot": _snap_json(s)}, status_code=202)


def _snap_json(s):
    return {
        "id": s["id"], "status": s["status"], "name": s["name"],
        "description": s["description"], "created_at": s["created_at"],
        "updated_at": s["updated_at"], "metadata": s["metadata"],
        "volume_id": s["volume_id"], "size": s["size"],
        "os-extended-snapshot-attributes:project_id": s["project_id"],
        "os-extended-snapshot-attributes:progress": "100%",
    }


@router.get("/v2/{pid}/snapshots/detail")
async def list_snapshots(request: Request, pid: str):
    state = request.app.state.sim
    snaps = [s for s in state.snapshots.values() if s["project_id"] == pid]
    return {"snapshots": [_snap_json(s) for s in snaps]}


@router.get("/v2/{pid}/cloudsnapshots/{snapshot_id}")
async def show_snapshot(request: Request, pid: str, snapshot_id: str):
    state = request.app.state.sim
    s = state.snapshots.get(snapshot_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    return {"snapshot": _snap_json(s)}


@router.delete("/v2/{pid}/cloudsnapshots/{snapshot_id}")
async def delete_snapshot(request: Request, pid: str, snapshot_id: str):
    state = request.app.state.sim
    s = state.snapshots.get(snapshot_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    del state.snapshots[snapshot_id]
    return Response(status_code=200)


@router.post("/v2/{pid}/cloudsnapshots/{snapshot_id}/rollback")
async def rollback_snapshot(request: Request, pid: str, snapshot_id: str):
    state = request.app.state.sim
    s = state.snapshots.get(snapshot_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(evs_error("EVS.5404",
            "Resource(Volume, Snapshot, Backup .etc) cound not be found."), status_code=404)
    vol = state.volumes.get(s["volume_id"])
    if not vol or vol["status"] != "available":
        return JSONResponse(evs_error("EVS.1046",
            "volume status must be available when rollback snapshot!"), status_code=400)

    async def effect():
        v = state.volumes.get(s["volume_id"])
        if v:
            v["updated_at"] = now_millis()
        return None

    job_id = await state.jobs.submit("rollbackSnapshot", {"volume_id": s["volume_id"]}, effect)
    return JSONResponse({"job_id": job_id}, status_code=202)
