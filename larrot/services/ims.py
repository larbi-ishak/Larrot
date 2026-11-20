"""IMS: image management (3 registration routes, Glance v2)."""

import asyncio

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.envelopes import ims_error
from ..core.jobs import new_id, now_millis
from ..core.profiles import Profile

router = APIRouter()


def _glance_json(img):
    return {
        "schema": "/v2/schemas/image", "min_disk": img["min_disk"],
        "created_at": img["created_at"],
        "__image_source_type": "uds", "container_format": "bare",
        "__image_size": "0",
        "file": f"/v2/images/{img['id']}/file",
        "updated_at": img["updated_at"], "protected": False,
        "id": img["id"], "__isregistered": "true", "min_ram": 0,
        "owner": img["project_id"], "__os_type": img["os_type"],
        "__imagetype": "private", "visibility": img["visibility"],
        "virtual_env_type": "FusionCompute", "tags": [],
        "__platform": img["os_version"], "__os_bit": "64",
        "__os_version": img["os_version"], "__root_origin": "file",
        "checksum": None, "size": None, "virtual_size": None,
        "properties": {}, "name": img["name"],
        "self": f"/v2/images/{img['id']}",
        "disk_format": img["disk_format"], "status": img["status"],
    }


@router.post("/v2/cloudimages/action")
@router.post("/v2.1/cloudimages/action")
@router.post("/v2/cloudimages/quickimport/action")
async def create_image_action(request: Request):
    state = request.app.state.sim
    body = await request.json()
    min_disk = body.get("min_disk", 40)
    if min_disk < 10:
        return JSONResponse(ims_error("Invalid min_disk."), status_code=400)

    img_id = new_id()
    state.images[img_id] = {
        "id": img_id, "name": body["name"],
        "os_type": body.get("os_type", "Linux"),
        "os_version": body.get("os_version", "Other 64bit"),
        "min_disk": min_disk, "reset_agent": False,
        "status": "queued", "disk_format": "qcow2",
        "visibility": "private",
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": state.account["domain_id"],
    }

    async def effect():
        img = state.images.get(img_id)
        if img:
            img["status"] = "active"
            img["updated_at"] = now_millis()
        state.jobs.patch(job_id, lambda j: j.entities.update({"process_percent": 1}))
        return None

    job_id = await state.jobs.submit("imsImportImageJob",
        {"image_id": img_id, "image_name": body["name"],
         "process_percent": 0, "current_task": ""}, effect)
    return {"job_id": job_id}


@router.post("/v1/cloudimages/wholeimages/action")
async def create_whole_image(request: Request):
    state = request.app.state.sim
    body = await request.json()
    instance_id = body.get("instance_id")
    if not instance_id:
        return JSONResponse(ims_error("instance_id is required."), status_code=400)
    server = state.servers.get(instance_id)
    if not server:
        return JSONResponse(ims_error("The ECS does not exist."), status_code=400)
    if state.profile_of(server["project_id"]) == Profile.HCS and server["status"] != "SHUTOFF":
        return JSONResponse(ims_error(
            "The ECS status does not meet requirements. Make the ECS in the required status and try again."),
            status_code=400)

    img_id = new_id()
    state.images[img_id] = {
        "id": img_id, "name": body["name"],
        "os_type": "Linux", "os_version": "Other 64bit",
        "min_disk": 40, "reset_agent": False,
        "status": "queued", "disk_format": "qcow2", "visibility": "private",
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": state.account["domain_id"],
    }

    async def effect():
        img = state.images.get(img_id)
        if img:
            img["status"] = "active"
            img["updated_at"] = now_millis()
        return None

    job_id = await state.jobs.submit("imsCreateWholeImageByInstanceJob",
        {"image_id": img_id, "image_name": body["name"],
         "process_percent": 0, "current_task": ""}, effect)
    return {"job_id": job_id}


@router.post("/v1/cloudimages/{image_id}/upload")
async def register_image(request: Request, image_id: str):
    state = request.app.state.sim
    img = state.images.get(image_id)
    if not img:
        return JSONResponse(ims_error("The image does not exist."), status_code=404)
    if img["status"] != "queued":
        return JSONResponse(ims_error("The image is not in the queued state."), status_code=400)

    async def effect():
        i = state.images.get(image_id)
        if i:
            i["status"] = "active"
            i["updated_at"] = now_millis()
        return None

    job_id = await state.jobs.submit("imsNativeImportImageJob",
        {"image_id": image_id, "process_percent": 0}, effect)
    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# Glance native
# ---------------------------------------------------------------------------

@router.post("/v2/images")
async def create_image_metadata(request: Request):
    state = request.app.state.sim
    body = await request.json()
    img_id = new_id()
    state.images[img_id] = {
        "id": img_id, "name": body["name"],
        "os_type": "Linux",
        "os_version": body.get("__os_version", "Other 64bit"),
        "min_disk": body.get("min_disk", 40), "reset_agent": False,
        "status": "queued",
        "disk_format": body.get("disk_format", "zvhd2"),
        "visibility": body.get("visibility", "private"),
        "created_at": now_millis(), "updated_at": now_millis(),
        "project_id": state.account["domain_id"],
    }
    return JSONResponse(_glance_json(state.images[img_id]), status_code=201)


@router.put("/v2/images/{image_id}/file")
async def upload_image_file(request: Request, image_id: str):
    state = request.app.state.sim
    img = state.images.get(image_id)
    if not img:
        return JSONResponse(ims_error("The image does not exist."), status_code=404)
    if img["status"] != "queued":
        return JSONResponse(ims_error("The image is not in the queued state."), status_code=409)
    img["status"] = "saving"
    img["updated_at"] = now_millis()

    async def _flip():
        await asyncio.sleep(1.5)
        i = state.images.get(image_id)
        if i:
            i["status"] = "active"
            i["updated_at"] = now_millis()

    asyncio.get_event_loop().create_task(_flip())
    return Response(status_code=204)


@router.get("/v2/images")
async def list_images_glance(request: Request):
    state = request.app.state.sim
    name = request.query_params.get("name")
    images = list(state.images.values())
    if name:
        images = [i for i in images if i["name"] == name]
    return {"schema": "/v2/schemas/images", "images": [_glance_json(i) for i in images]}


@router.get("/v2/cloudimages")
async def list_images_custom(request: Request):
    state = request.app.state.sim
    name = request.query_params.get("name")
    limit = min(int(request.query_params.get("limit", 1000)), 1000)
    images = list(state.images.values())
    if name:
        images = [i for i in images if i["name"] == name]
    page = images[:limit]
    body = {"images": [_glance_json(i) for i in page]}
    if len(images) > limit:
        body["page_info"] = {"next_marker": page[-1]["id"]}
    return body


@router.patch("/v2/images/{image_id}")
async def update_image(request: Request, image_id: str):
    s = request.app.state.sim
    img = s.images.get(image_id)
    if not img:
        return JSONResponse(ims_error("image not found"), status_code=404)
    body = await request.json()
    for field in ("name", "min_disk", "min_ram", "visibility", "description"):
        if field in body:
            img[field] = body[field]
    img["updated_at"] = now_millis()
    return {"image": img}


@router.get("/v2/images/{image_id}")
async def show_image(request: Request, image_id: str):
    state = request.app.state.sim
    img = state.images.get(image_id)
    if not img:
        return JSONResponse(ims_error("The image does not exist."), status_code=404)
    return _glance_json(img)


@router.delete("/v2/images/{image_id}")
async def delete_image(request: Request, image_id: str):
    state = request.app.state.sim
    if image_id not in state.images:
        return JSONResponse(ims_error("The image does not exist."), status_code=404)
    del state.images[image_id]
    return Response(status_code=204)


@router.get("/v1/cloudimages/job/{job_id}")
async def show_job_progress(request: Request, job_id: str):
    state = request.app.state.sim
    job = state.jobs.get(job_id)
    if not job:
        return JSONResponse(ims_error("Invalid job ID."), status_code=404)
    return job.to_json()
