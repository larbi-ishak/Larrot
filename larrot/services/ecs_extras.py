"""ECS Quotas, Metadata, NICs, Console, Resize, OS Change."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


# ---------------------------------------------------------------------------
# Quotas
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/limits")
async def get_quotas(request: Request, pid: str):
    s = request.app.state.sim
    server_count = len([x for x in s.servers.values() if x["project_id"] == pid])
    return {
        "absolute": {
            "maxTotalInstances": 100, "totalInstancesUsed": server_count,
            "maxTotalCores": 400, "totalCoresUsed": server_count * 2,
            "maxTotalRAMSize": 819200, "totalRAMUsed": server_count * 4096,
            "maxTotalVolumeGigabytes": 32768, "totalVolumeGigabytesUsed": server_count * 40,
            "maxServerGroups": 10, "totalServerGroupsUsed": 0,
            "maxServerGroupMembers": 50, "totalServerGroupMembersUsed": 0,
            "maxSecurityGroups": 100, "totalSecurityGroupsUsed": len(s.security_groups),
            "maxSecurityGroupRules": 500, "totalSecurityGroupRulesUsed": 0,
            "maxFloatingIps": 50, "totalFloatingIpsUsed": len(s.eips),
        }
    }


# ---------------------------------------------------------------------------
# Server Metadata
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/{server_id}/metadata")
async def get_metadata(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    return {"metadata": server.get("metadata", {})}


@router.put("/v1/{pid}/cloudservers/{server_id}/metadata")
async def set_metadata(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()
    server.setdefault("metadata", {}).update(body.get("metadata", {}))
    return {"metadata": server["metadata"]}


@router.delete("/v1/{pid}/cloudservers/{server_id}/metadata/{key}")
async def delete_metadata_key(request: Request, pid: str, server_id: str, key: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    server.get("metadata", {}).pop(key, None)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# NIC Management
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/{server_id}/os-interface")
async def list_nics(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    ports = [p for p in s.ports.values() if p["device_id"] == server_id]
    nics = [{"port_id": p["id"], "net_id": p["network_id"],
             "ip_address": p["ip_address"], "mac_addr": p["mac_address"],
             "subnet_id": p["subnet_id"]} for p in ports]
    return {"interfaceAttachments": nics}


@router.post("/v1/{pid}/cloudservers/{server_id}/os-interface")
async def add_nic(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()
    port_id = new_id()
    subnet_id = body.get("subnet_id", "")
    ip = body.get("ip_address") or s.next_ip(pid)
    s.ports[port_id] = {
        "id": port_id, "network_id": body.get("net_id", ""),
        "subnet_id": subnet_id, "mac_address": f"fa:16:3e:{new_id()[:8]}",
        "ip_address": ip, "device_id": server_id, "project_id": pid,
    }
    return {"interfaceAttachment": {"port_id": port_id, "ip_address": ip}}


@router.delete("/v1/{pid}/cloudservers/{server_id}/os-interface/{port_id}")
async def remove_nic(request: Request, pid: str, server_id: str, port_id: str):
    s = request.app.state.sim
    port = s.ports.get(port_id)
    if not port or port["device_id"] != server_id:
        return JSONResponse({"error": {"code": "Ecs.0117", "message": "Interface not found"}}, status_code=404)
    del s.ports[port_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Console / Remote Access
# ---------------------------------------------------------------------------

@router.get("/v1/{pid}/cloudservers/{server_id}/remote_console")
@router.post("/v1/{pid}/cloudservers/{server_id}/remote_console")
async def get_remote_console(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    return {"remote_console": {
        "type": "novnc", "protocol": "vnc", "url": f"vnc://127.0.0.1:6080/vnc_auto.html?token={new_id()}"
    }}


@router.get("/v1/{pid}/cloudservers/{server_id}/console_log")
async def get_console_log(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    log = f"""[    0.000000] Linux version 5.10.0 (sim@larrot)
[    0.000000] Command line: BOOT_IMAGE=/vmlinuz root=/dev/vda1
[    0.100000] BIOS-provided physical RAM map
[    0.500000] Memory: {server["flavor"]["ram"]}K available
[    1.000000] vda: detected capacity: {server["os-extended-volumes:volumes_attached"][0]["size"] * 1024 * 1024} KB
[    2.000000] cloud-init[123]: Cloud-init v. 22.3 running 'init-local'
[    3.000000] cloud-init[123]: Cloud-init v. 22.3 running 'init'
[    5.000000] systemd[1]: Reached target Multi-User System.
[    5.100000] Server {server["name"]} is ready. Status: {server["status"]}
"""
    return PlainTextResponse(log)


# ---------------------------------------------------------------------------
# Resize / Change OS
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/cloudservers/{server_id}/resize")
async def resize_server(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()
    new_flavor = body.get("resize", {}).get("flavorRef", "")
    flavor = next((f for f in s.flavors if f["id"] == new_flavor), None)
    if not flavor:
        return JSONResponse({"error": {"code": "Ecs.0018", "message": "Flavor not found"}}, status_code=400)
    server["status"] = "RESIZE"
    server["OS-EXT-STS:task_state"] = "resize_confirming"

    async def effect():
        srv = s.servers.get(server_id)
        if srv:
            srv["flavor"] = {"disk": flavor["disk"], "vcpus": flavor["vcpus"],
                             "ram": flavor["ram"], "id": flavor["id"], "name": flavor["name"],
                             "gpus": [], "asic_accelerators": []}
            srv["status"] = "ACTIVE"
            srv["OS-EXT-STS:task_state"] = None
            srv["updated"] = now_millis()
        return None

    job_id = await s.jobs.submit("resizeServer", {"server_id": server_id}, effect)
    return {"job_id": job_id}


@router.post("/v1/{pid}/cloudservers/{server_id}/changeos")
async def change_os(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()
    new_image = body.get("changeOs", {}).get("imageRef", "")
    if new_image not in s.images:
        return JSONResponse({"error": {"code": "Ecs.0019", "message": "Image not found"}}, status_code=400)
    server["status"] = "REBUILD"
    server["OS-EXT-STS:task_state"] = "rebuilding"

    async def effect():
        srv = s.servers.get(server_id)
        if srv:
            srv["image"] = {"id": new_image}
            srv["status"] = "ACTIVE"
            srv["OS-EXT-STS:task_state"] = None
            srv["updated"] = now_millis()
        return None

    job_id = await s.jobs.submit("changeOS", {"server_id": server_id}, effect)
    return {"job_id": job_id}


# ---------------------------------------------------------------------------
# Nova Snapshots (create image from server)
# ---------------------------------------------------------------------------

@router.get("/v2.1/{pid}/servers/{server_id}/os-interface")
async def nova_list_interfaces(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114",
                                        "message": "The ECS does not exist"}}, status_code=404)
    ports = [p for p in s.ports.values()
             if p["device_id"] == server_id and p["project_id"] == pid]
    return {"interfaceAttachments": [{
        "port_state": "ACTIVE", "fixed_ips": [{"subnet_id": p["subnet_id"],
                                                "ip_address": p["ip_address"]}],
        "port_id": p["id"], "net_id": p["network_id"],
        "mac_addr": p["mac_address"]} for p in ports]}


@router.put("/v2.1/{pid}/servers/{server_id}")
async def nova_update_server(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114",
                                        "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()
    spec = body.get("server", {})
    if "name" in spec and spec["name"]:
        server["name"] = spec["name"]
    return {"server": server}


@router.get("/v2.1/{pid}/servers/{server_id}")
async def nova_show_server(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    return {"server": server}


@router.post("/v2.1/{pid}/servers/{server_id}/action")
async def nova_server_action(request: Request, pid: str, server_id: str):
    s = request.app.state.sim
    server = s.servers.get(server_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0114", "message": "The ECS does not exist"}}, status_code=404)
    body = await request.json()

    if "addSecurityGroup" in body:
        name = body["addSecurityGroup"].get("name", "")
        if not name:
            return JSONResponse({"error": {"code": "Ecs.0005", "message": "request body is illegal"}}, status_code=400)
        groups = [g["name"] for g in server.get("security_groups", [])]
        if name not in groups:
            server["security_groups"] = server.get("security_groups", []) + [{"name": name}]
        return Response(status_code=202)

    if "removeSecurityGroup" in body:
        name = body["removeSecurityGroup"].get("name", "")
        if not name:
            return JSONResponse({"error": {"code": "Ecs.0005", "message": "request body is illegal"}}, status_code=400)
        server["security_groups"] = [g for g in server.get("security_groups", [])
                                     if g["name"] != name]
        return Response(status_code=202)

    if "createImage" in body:
        img_name = body["createImage"].get("name", f"snapshot-{server_id[:8]}")
        img_id = new_id()
        s.images[img_id] = {
            "id": img_id, "name": img_name,
            "os_type": "Linux", "os_version": "Unknown",
            "min_disk": 40, "reset_agent": False,
            "status": "active", "disk_format": "qcow2", "visibility": "private",
            "created_at": now_millis(), "updated_at": now_millis(),
            "project_id": s.account["domain_id"],
        }
        return {"image_id": img_id}

    if "os-stop" in body:
        server["status"] = "SHUTOFF"
        server["OS-EXT-STS:power_state"] = 4
        return Response(status_code=202)

    if "os-start" in body:
        server["status"] = "ACTIVE"
        server["OS-EXT-STS:power_state"] = 1
        return Response(status_code=202)

    if "reboot" in body:
        return Response(status_code=202)

    return JSONResponse({"error": {"code": "Ecs.0005", "message": "Unknown action"}}, status_code=400)
