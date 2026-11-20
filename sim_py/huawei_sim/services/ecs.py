"""ECS — cloud server lifecycle, attach/detach, state guards, jobs."""

import asyncio
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import ecs_error, apigw_error
from ..core.jobs import new_id, new_job_id, now_millis, mark_sub_jobs_success
from ..core.profiles import Profile

router = APIRouter()

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _default_limit(state, pid):
    return 2 if state.profile_of(pid) == Profile.HCS else 25


def _status_matches(filter, status):
    if filter == "ACTIVE":
        return status in ("ACTIVE", "REBOOT", "HARD_REBOOT", "REBUILD", "MIGRATING", "RESIZE")
    if filter == "SHUTOFF":
        return status in ("SHUTOFF", "RESIZE", "REBUILD")
    return status == filter


def _server_list_json(state, pid, server):
    """Serialize for LIST views — hcs profile removes flavor + AZ (sparse)."""
    import json
    v = dict(server)
    if state.profile_of(pid) == Profile.HCS:
        v.pop("flavor", None)
        v.pop("OS-EXT-AZ:availability_zone", None)
    return v


def _build_server(state, pid, spec, suffix=None):
    project = state.project(pid)
    flavor = next(f for f in state.flavors if f["id"] == spec["flavorRef"])
    image = state.images[spec["imageRef"]]

    name = spec["name"] if suffix is None else f"{spec['name']}-{suffix:04d}"
    az = spec.get("availability_zone") or (
        "az-dc-1" if state.profile_of(pid) == Profile.HCS else f"{project['name']}a"
    )

    server_id = new_id()
    ip = state.next_ip(pid)
    port_id = new_id()
    state.ports[port_id] = {
        "id": port_id, "network_id": project["vpc_id"],
        "subnet_id": project["subnet_id"], "mac_address": f"fa:16:3e:{new_id()[:8]}",
        "ip_address": ip, "device_id": server_id, "project_id": pid,
    }

    root_size = spec.get("root_volume", {}).get("size", image["min_disk"])
    vol_id = state.create_volume(pid, f"root-{name}", root_size, az, "SAS", True)
    vol = state.volumes[vol_id]
    vol["status"] = "in-use"
    vol["attachments"] = [{"server_id": server_id, "device": "/dev/vda"}]

    addr_key = project["vpc_name"] if state.profile_of(pid) == Profile.HCS else project["vpc_id"]
    return {
        "id": server_id,
        "name": name,
        "status": "BUILD",
        "OS-EXT-STS:task_state": None,
        "OS-EXT-STS:power_state": 0,
        "OS-EXT-STS:vm_state": "building",
        "addresses": {addr_key: [{
            "version": "4", "addr": ip, "primary": True,
            "OS-EXT-IPS-MAC:mac_addr": state.ports[port_id]["mac_address"],
            "OS-EXT-IPS:type": "fixed",
            "OS-EXT-IPS:port_id": port_id,
        }]},
        "flavor": {"disk": flavor["disk"], "vcpus": flavor["vcpus"],
                    "ram": flavor["ram"], "id": flavor["id"], "name": flavor["name"],
                    "gpus": [], "asic_accelerators": []},
        "image": {"id": image["id"]},
        "tenant_id": pid,
        "user_id": "b44a37e1192442acaa0d578b63e38fe3",
        "accessIPv4": "", "accessIPv6": "",
        "progress": 0,
        "hostId": new_job_id() + new_job_id(),
        "OS-EXT-SRV-ATTR:host": az,
        "OS-EXT-SRV-ATTR:instance_name": f"instance-{new_job_id()[:8]}",
        "OS-EXT-SRV-ATTR:reservation_id": f"r-{new_job_id()[:8]}",
        "OS-EXT-SRV-ATTR:hostname": name.replace("_", "-"),
        "locked": False,
        "config_drive": "",
        "description": "",
        "key_name": spec.get("key_name"),
        "created": now_millis(),
        "updated": now_millis(),
        "OS-EXT-AZ:availability_zone": az,
        "metadata": {},
        "tags": [],
        "security_groups": [{"name": "default"}],
        "os-extended-volumes:volumes_attached": [{
            "id": vol_id, "delete_on_termination": "false",
            "bootIndex": "0", "device": "/dev/vda", "size": root_size,
        }],
        "fault": None,
        "project_id": pid,
        "image_agent": image["reset_agent"],
    }


def resolve_device(server, volume_bootable, requested):
    """The Ecs.0005 rules — pure function (EMPIRICAL_SPEC §2.6)."""
    used = [v["device"] for v in server["os-extended-volumes:volumes_attached"]]
    if requested:
        if requested.startswith("/dev/sd"):
            requested = "/dev/vd" + requested[7:]  # KVM: sd* → vd*
        device = requested
    else:
        candidate = ord("b")
        while True:
            d = f"/dev/vd{chr(candidate)}"
            if d not in used:
                device = d
                break
            candidate += 1
            if candidate > ord("z"):
                return None
    if device == "/dev/vda" and volume_bootable != "true":
        return None
    if device in used:
        return None
    return device


# ---------------------------------------------------------------------------
# list / show
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/detail")
async def list_servers_detail(request: Request, pid: str):
    state = request.app.state.sim
    params = request.query_params
    servers = [s for s in state.servers.values() if s["project_id"] == pid]

    if "flavor" in params:
        servers = [s for s in servers if s["flavor"]["id"] == params["flavor"]]
    if "name" in params:
        servers = [s for s in servers if params["name"] in s["name"]]
    if "status" in params:
        servers = [s for s in servers if _status_matches(params["status"], s["status"])]
    if "ip" in params:
        servers = [s for s in servers if any(
            params["ip"] in a["addr"] for addrs in s["addresses"].values() for a in addrs)]

    servers.sort(key=lambda s: (s["created"], s["id"]))
    total = len(servers)
    limit = min(int(params.get("limit", _default_limit(state, pid))), 1000)

    if "marker" in params:
        start = next((i for i, s in enumerate(servers) if s["id"] == params["marker"]), -1) + 1
    else:
        offset = max(int(params.get("offset", 1)), 1)
        start = (offset - 1) * limit

    page = servers[start:start + limit]
    next_marker = page[-1]["id"] if page and start + len(page) < total else None

    body = {"count": total, "servers": [_server_list_json(state, pid, s) for s in page]}
    if next_marker:
        body["servers_links"] = [{"rel": "next",
            "href": f"http://{request.headers.get('host', '127.0.0.1:8200')}/v1/{pid}/cloudservers/detail?marker={next_marker}&limit={limit}"}]
    return body


@router.get("/v1.1/{pid}/cloudservers/detail")
async def list_servers_v11(request: Request, pid: str):
    state = request.app.state.sim
    servers = [s for s in state.servers.values() if s["project_id"] == pid]
    return {"servers": [_server_list_json(state, pid, s) for s in servers],
            "request_id": new_job_id()}


@router.get("/v1/{pid}/cloudservers/flavors")
async def list_flavors(request: Request, pid: str):
    state = request.app.state.sim
    if state.profile_of(pid) == Profile.HCS:
        return JSONResponse(
            apigw_error("APIGW.0101", "The API does not exist or has not been published in the environment."),
            status_code=404)
    region = state.project(pid)["name"] if state.project(pid) else ""
    flavors = [{"id": f["id"], "name": f["name"], "vcpus": f["vcpus"],
                "ram": f["ram"], "disk": f["disk"],
                "os_flavor_access": {"is_public": True}}
               for f in state.flavors if region in f["regions"]]
    return {"flavors": flavors}


@router.get("/v1/{pid}/cloudservers/{server_id}")
async def show_server(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    return {"server": s}


@router.put("/v1/{pid}/cloudservers/{server_id}")
async def update_server(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    body = await request.json()
    spec = body.get("server", {})
    if "name" in spec:
        s["name"] = spec["name"]
    if "description" in spec:
        s["description"] = spec["description"]
    s["updated"] = now_millis()
    return {"server": s}


# ---------------------------------------------------------------------------
# create / delete / batch actions
# ---------------------------------------------------------------------------

@router.post("/v1.1/{pid}/cloudservers")
@router.post("/v1/{pid}/cloudservers")
async def create_servers(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["server"]
    prepaid = "/v1/" in request.url.path

    if not state.project(pid):
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)
    if spec["imageRef"] not in state.images:
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)
    region = state.project(pid)["name"]
    if not any(f["id"] == spec["flavorRef"] and region in f["regions"] for f in state.flavors):
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)
    if body.get("dry_run") is True:
        return Response(status_code=202)

    count = min(spec.get("count", 1), 100)
    server_ids, sub_jobs = [], []
    for i in range(count):
        suffix = i if count > 1 else None
        server = _build_server(state, pid, spec, suffix)
        state.servers[server["id"]] = server
        server_ids.append(server["id"])
        sub_jobs.append({
            "status": "RUNNING", "entities": {"server_id": server["id"]},
            "job_id": new_job_id(), "job_type": "createSingleServer",
            "begin_time": now_millis(), "end_time": None,
            "error_code": None, "fail_reason": None,
        })

    async def effect():
        for sid in server_ids:
            s = state.servers.get(sid)
            if s:
                s["status"] = "ACTIVE"
                s["vm_state"] = "active"
                s["OS-EXT-STS:power_state"] = 1
                s["OS-EXT-STS:task_state"] = None
                s["updated"] = now_millis()
        state.jobs.patch(job_id, mark_sub_jobs_success)
        return None

    entities = {"sub_jobs_total": count, "sub_jobs": sub_jobs}
    job_id = await state.jobs.submit("createServer", entities, effect)

    resp = {"job_id": job_id, "serverIds": server_ids}
    if prepaid:
        resp["order_id"] = f"CS{new_job_id()[:16].upper()}"
    return resp


@router.post("/v1/{pid}/cloudservers/delete")
async def delete_servers(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    ids = [s["id"] for s in body.get("servers", [])]
    delete_volume = body.get("delete_volume", False)

    for sid in ids:
        s = state.servers.get(sid)
        if not s or s["project_id"] != pid:
            return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)

    vol_flags = []
    for sid in ids:
        s = state.servers.get(sid)
        for va in s["os-extended-volumes:volumes_attached"]:
            vol_flags.append((va["id"], va["delete_on_termination"]))

    async def effect():
        for sid in ids:
            state.servers.pop(sid, None)
        for vid, dot in vol_flags:
            if delete_volume or dot == "true":
                state.volumes.pop(vid, None)
            elif vid in state.volumes:
                v = state.volumes[vid]
                v["status"] = "available"
                v["attachments"] = []
                v["updated_at"] = now_millis()
        state.jobs.patch(job_id, mark_sub_jobs_success)
        return None

    sub_jobs = [{"status": "RUNNING", "entities": {"server_id": sid},
                 "job_id": new_job_id(), "job_type": "deleteSingleServer",
                 "begin_time": now_millis(), "end_time": None,
                 "error_code": None, "fail_reason": None} for sid in ids]
    job_id = await state.jobs.submit("deleteVMs",
        {"sub_jobs_total": len(ids), "sub_jobs": sub_jobs}, effect)
    return {"job_id": job_id}


@router.post("/v1/{pid}/cloudservers/action")
async def batch_action(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()

    if "os-stop" in body:
        action, job_type, final_status, final_power, final_vm = "os-stop", "stopVMs", "SHUTOFF", 4, "stopped"
        task_state = "stopping"
    elif "os-start" in body:
        action, job_type, final_status, final_power, final_vm = "os-start", "startVMs", "ACTIVE", 1, "active"
        task_state = "starting"
    elif "reboot" in body:
        action, job_type, final_status, final_power, final_vm = "reboot", "rebootVMs", "ACTIVE", 1, "active"
        task_state = "rebooting"
    else:
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)

    ids = [s["id"] for s in body[action].get("servers", [])]
    if not ids:
        return JSONResponse(ecs_error("Common.0002", "The request body cannot be left blank."), status_code=400)

    # State guards (D13)
    for sid in ids:
        s = state.servers.get(sid)
        if not s or s["project_id"] != pid:
            return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
        if s["OS-EXT-STS:task_state"]:
            return JSONResponse(ecs_error("Ecs.0100",
                "The ECS status does not meet requirements. Make the ECS in the required status and try again."),
                status_code=400)
        allowed = (s["status"] == "ACTIVE") if action in ("os-stop", "reboot") else (s["status"] == "SHUTOFF")
        if not allowed:
            return JSONResponse(ecs_error("Ecs.0100",
                "The ECS status does not meet requirements. Make the ECS in the required status and try again."),
                status_code=400)

    for sid in ids:
        s = state.servers[sid]
        s["OS-EXT-STS:task_state"] = task_state
        s["updated"] = now_millis()

    async def effect():
        for sid in ids:
            s = state.servers.get(sid)
            if s:
                s["status"] = final_status
                s["OS-EXT-STS:vm_state"] = final_vm
                s["OS-EXT-STS:power_state"] = final_power
                s["OS-EXT-STS:task_state"] = None
                s["updated"] = now_millis()
        state.jobs.patch(job_id, mark_sub_jobs_success)
        return None

    sub_jobs = [{"status": "RUNNING", "entities": {"server_id": sid},
                 "job_id": new_job_id(), "job_type": f"{job_type}Single",
                 "begin_time": now_millis(), "end_time": None,
                 "error_code": None, "fail_reason": None} for sid in ids]
    job_id = await state.jobs.submit(job_type,
        {"sub_jobs_total": len(ids), "sub_jobs": sub_jobs}, effect)
    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# flavors / jobs / Nova compat / password
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/jobs/{job_id}")
async def show_job(request: Request, pid: str, job_id: str):
    state = request.app.state.sim
    job = state.jobs.get(job_id)
    if not job:
        return JSONResponse(ecs_error("Common.0011", "Invalid job ID."), status_code=404)
    return job.to_json()


@router.get("/v2.1/{pid}/servers")
async def nova_list_brief(request: Request, pid: str):
    state = request.app.state.sim
    servers = [{"id": s["id"], "name": s["name"],
                "links": [{"rel": "self", "href": f"/v2.1/{pid}/servers/{s['id']}"},
                          {"rel": "bookmark", "href": f"/{pid}/servers/{s['id']}"}]}
               for s in state.servers.values() if s["project_id"] == pid]
    return {"servers": servers}


@router.get("/v2.1/{pid}/servers/detail")
async def nova_list_detail(request: Request, pid: str):
    state = request.app.state.sim
    servers = [_server_list_json(state, pid, s)
               for s in state.servers.values() if s["project_id"] == pid]
    return {"servers": servers}


# ---------------------------------------------------------------------------
# attach / detach volume — the Ecs.0005 rules
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/cloudservers/{server_id}/attachvolume")
async def attach_volume(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    body = await request.json()
    va = body["volumeAttachment"]

    server = state.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)

    vol = state.volumes.get(va["volumeId"])
    if not vol or vol["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)
    if vol["status"] != "available":
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)

    device = resolve_device(server, vol["bootable"], va.get("device"))
    if device is None:
        return JSONResponse(ecs_error("Ecs.0005", "device is illegal"), status_code=400)

    if body.get("dry_run") is True:
        return Response(status_code=202)

    vol["status"] = "attaching"
    vol["updated_at"] = now_millis()

    async def effect():
        v = state.volumes.get(vol["id"])
        if v:
            v["status"] = "in-use"
            v["updated_at"] = now_millis()
            v["attachments"] = [{"server_id": server_id, "device": device}]
        s = state.servers.get(server_id)
        if s:
            s["os-extended-volumes:volumes_attached"].append({
                "id": vol["id"], "delete_on_termination": "false",
                "bootIndex": "0" if device == "/dev/vda" else "",
                "device": device, "size": vol["size"],
            })
            s["updated"] = now_millis()
        return None

    job_id = await state.jobs.submit("attachVolume",
        {"server_id": server_id, "volume_id": vol["id"]}, effect)
    return {"job_id": job_id}


@router.delete("/v1/{pid}/cloudservers/{server_id}/attachvolume/{volume_id}")
async def detach_volume(request: Request, pid: str, server_id: str, volume_id: str):
    state = request.app.state.sim
    server = state.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)

    attachment = next((a for a in server["os-extended-volumes:volumes_attached"]
                       if a["id"] == volume_id), None)
    if not attachment:
        return JSONResponse(ecs_error("Ecs.0005", "request body is illegal."), status_code=400)
    if attachment["device"] == "/dev/vda":
        return JSONResponse(ecs_error("Ecs.0005", "device is illegal"), status_code=400)

    vol = state.volumes.get(volume_id)
    if vol:
        vol["status"] = "detaching"
        vol["updated_at"] = now_millis()

    async def effect():
        v = state.volumes.get(volume_id)
        if v:
            v["status"] = "available"
            v["attachments"] = []
            v["updated_at"] = now_millis()
        s = state.servers.get(server_id)
        if s:
            s["os-extended-volumes:volumes_attached"] = [
                a for a in s["os-extended-volumes:volumes_attached"] if a["id"] != volume_id]
            s["updated"] = now_millis()
        return None

    job_id = await state.jobs.submit("detachVolume",
        {"server_id": server_id, "volume_id": volume_id}, effect)
    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# block devices / password reset
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/{server_id}/block_device")
async def list_block_devices(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    items = [{"pciAddress": f"0000:02:{i+1:02}.0", "volumeId": a["id"],
              "device": a["device"], "serverId": server_id, "id": a["id"],
              "size": a["size"], "bootIndex": i, "bus": "virtio"}
             for i, a in enumerate(s["os-extended-volumes:volumes_attached"])]
    free = max(24 - len(items), 0)
    return {"attachableQuantity": {"free_scsi": free, "free_blk": free, "free_disk": free},
            "volumeAttachments": items}


@router.get("/v1/{pid}/cloudservers/{server_id}/os-volume_attachments")
async def list_volume_attachments(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    return {"volumeAttachments": [
        {"device": a["device"], "id": a["id"], "serverId": server_id, "volumeId": a["id"]}
        for a in s["os-extended-volumes:volumes_attached"]]}


@router.get("/v1/{pid}/cloudservers/{server_id}/os-resetpwd-flag")
async def resetpwd_flag(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    return {"resetpwd_flag": s["image_agent"]}


@router.put("/v1/{pid}/cloudservers/{server_id}/os-reset-password")
async def reset_password(request: Request, pid: str, server_id: str):
    state = request.app.state.sim
    s = state.servers.get(server_id)
    if not s or s["project_id"] != pid:
        return JSONResponse(ecs_error("Ecs.0114", "The ECS does not exist."), status_code=404)
    if not s["image_agent"]:
        return JSONResponse(ecs_error("Ecs.0100", "server does not support reset password"), status_code=400)
    job_id = await state.jobs.submit("resetPassword", {"server_id": server_id}, lambda: asyncio.sleep(0))
    return {"job_id": job_id}
