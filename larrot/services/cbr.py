"""CBR — vaults, policies, checkpoints (on-demand backup), backups, restore."""

import asyncio
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import cbr_error
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _vault_json(v):
    return {
        "id": v["id"], "name": v["name"], "description": v["description"],
        "resources": [{"id": r["id"], "name": r["name"], "type": r["type"],
                       "protect_status": r["protect_status"], "size": r["size"],
                       "backup_size": r["backup_size"], "backup_count": r["backup_count"],
                       "extra_info": r["extra_info"]} for r in v["resources"]],
        "auto_bind": v["auto_bind"], "auto_expand": v["auto_expand"],
        "availability_zone": v["availability_zone"],
        "enterprise_project_id": "0", "billing": v["billing"],
        "project_id": v["project_id"], "user_id": v["user_id"],
        "provider_id": v["provider_id"], "created_at": v["created_at"],
        "tags": [], "locked": False, "smn_notify": False,
        "sys_lock_source_service": "", "threshold": 80,
    }


def _backup_json(b):
    return {
        "id": b["id"], "checkpoint_id": b["checkpoint_id"],
        "name": b["name"], "description": b["description"],
        "resource_id": b["resource_id"], "resource_name": b["resource_name"],
        "resource_type": b["resource_type"], "resource_size": b["resource_size"],
        "status": b["status"], "vault_id": b["vault_id"],
        "created_at": b["created_at"], "updated_at": b["updated_at"],
        "expired_at": b["expired_at"], "protected_at": b["protected_at"],
        "incremental": b["incremental"], "image_type": b["image_type"],
        "version": b["version"], "extend_info": b["extend_info"],
        "project_id": b["project_id"], "provider_id": "c733a7c7",
        "children": [], "replication_records": [],
        "parent_id": None, "scheduled_operation_id": None,
        "resource_az": "", "enterprise_project_id": "0",
    }


def _checkpoint_json(c):
    return {
        "id": c["id"], "status": c["status"],
        "created_at": c["created_at"], "project_id": c["project_id"],
        "vault": {"id": c["vault_id"], "name": ""},
        "extra_info": c["extra_info"],
    }


# ---------------------------------------------------------------------------
# vaults
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/vaults")
async def create_vault(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["vault"]
    resources = [{"id": r["id"], "name": r.get("name", ""),
                  "type": r.get("type", "OS::Nova::Server"),
                  "protect_status": "available", "size": 40,
                  "backup_size": 0, "backup_count": 0, "extra_info": {}}
                 for r in spec.get("resources", [])]
    vault = {
        "id": new_id(), "name": spec["name"],
        "description": spec.get("description", ""),
        "resources": resources,
        "auto_bind": spec.get("auto_bind", False),
        "auto_expand": spec.get("auto_expand", False),
        "availability_zone": spec.get("availability_zone", ""),
        "billing": spec.get("billing", {"consistent_level": "crash_consistent",
                                         "object_type": "server", "protect_type": "backup",
                                         "size": 100}),
        "project_id": pid, "user_id": "b44a37e1192442acaa0d578b63e38fe3",
        "provider_id": "0c99f9b3", "created_at": now_millis(),
    }
    state.vaults[vault["id"]] = vault
    return {"vault": _vault_json(vault)}


@router.get("/v3/{pid}/vaults")
async def list_vaults(request: Request, pid: str):
    state = request.app.state.sim
    vaults = [v for v in state.vaults.values() if v["project_id"] == pid]
    return {"vaults": [_vault_json(v) for v in vaults],
            "count": len(vaults), "limit": 100, "offset": 0}


@router.get("/v3/{pid}/vaults/{vault_id}")
async def show_vault(request: Request, pid: str, vault_id: str):
    state = request.app.state.sim
    v = state.vaults.get(vault_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0010", "The vault does not exist."), status_code=404)
    return {"vault": _vault_json(v)}


@router.put("/v3/{pid}/vaults/{vault_id}")
async def update_vault(request: Request, pid: str, vault_id: str):
    state = request.app.state.sim
    v = state.vaults.get(vault_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0010", "The vault does not exist."), status_code=404)
    body = await request.json()
    for k in ("name", "description"):
        if k in body["vault"]:
            v[k] = body["vault"][k]
    return {"vault": _vault_json(v)}


@router.delete("/v3/{pid}/vaults/{vault_id}")
async def delete_vault(request: Request, pid: str, vault_id: str):
    state = request.app.state.sim
    v = state.vaults.get(vault_id)
    if not v or v["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0010", "The vault does not exist."), status_code=404)
    del state.vaults[vault_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/vaults/{vault_id}/addresources")
async def add_resources(request: Request, pid: str, vault_id: str):
    state = request.app.state.sim
    vault = state.vaults.get(vault_id)
    if not vault or vault["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0010", "The vault does not exist."), status_code=404)
    body = await request.json()
    results = []
    for r in body.get("resources", []):
        if r["id"] in state.servers:
            s = state.servers[r["id"]]
            name, rtype, size = s["name"], "OS::Nova::Server", 40
        elif r["id"] in state.volumes:
            vol = state.volumes[r["id"]]
            name, rtype, size = vol["name"], "OS::Cinder::Volume", vol["size"]
        else:
            return JSONResponse(cbr_error("CBR.0002", "The resource does not exist."), status_code=400)
        vault["resources"].append({
            "id": r["id"], "name": name, "type": rtype,
            "protect_status": "available", "size": size,
            "backup_size": 0, "backup_count": 0, "extra_info": {},
        })
        results.append({"id": r["id"], "status": "available"})
    return {"add_resource_results": results}


@router.post("/v3/{pid}/vaults/{vault_id}/removeresources")
async def remove_resources(request: Request, pid: str, vault_id: str):
    state = request.app.state.sim
    vault = state.vaults.get(vault_id)
    if not vault or vault["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0010", "The vault does not exist."), status_code=404)
    body = await request.json()
    results = []
    for rid in body.get("resource_ids", []):
        vault["resources"] = [r for r in vault["resources"] if r["id"] != rid]
        results.append({"id": rid, "status": "removed"})
    return {"remove_resource_results": results}


# ---------------------------------------------------------------------------
# policies
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/policies")
async def create_policy(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    spec = body["policy"]
    policy = {
        "id": new_id(), "name": spec["name"],
        "enabled": spec.get("enabled", True),
        "operation_type": spec.get("operation_type", "backup"),
        "operation_definition": spec.get("operation_definition", {
            "day_backups": 1, "max_backups": 10, "month_backups": 0,
            "retention_duration_days": 30, "timezone": "UTC+00:00",
            "week_backups": 0, "year_backups": 0,
        }),
        "trigger": spec.get("trigger", {"properties": {"pattern": ["FREQ=DAILY;INTERVAL=1"]}}),
        "associated_vaults": [], "project_id": pid,
    }
    state.cbr_policies[policy["id"]] = policy
    return {"policy": {**policy, "policy_type": "disk"}}


@router.get("/v3/{pid}/policies")
async def list_policies(request: Request, pid: str):
    state = request.app.state.sim
    policies = [p for p in state.cbr_policies.values() if p["project_id"] == pid]
    return {"policies": [{**p, "policy_type": "disk"} for p in policies],
            "count": len(policies)}


@router.get("/v3/{pid}/policies/{policy_id}")
async def show_policy(request: Request, pid: str, policy_id: str):
    state = request.app.state.sim
    p = state.cbr_policies.get(policy_id)
    if not p or p["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0011", "The policy does not exist."), status_code=404)
    return {"policy": {**p, "policy_type": "disk"}}


@router.delete("/v3/{pid}/policies/{policy_id}")
async def delete_policy(request: Request, pid: str, policy_id: str):
    state = request.app.state.sim
    p = state.cbr_policies.get(policy_id)
    if not p or p["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0011", "The policy does not exist."), status_code=404)
    del state.cbr_policies[policy_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# checkpoints (on-demand backup) — the §3.4 CBR path
# ---------------------------------------------------------------------------

@router.post("/v3/{pid}/checkpoints")
async def create_checkpoint(request: Request, pid: str):
    state = request.app.state.sim
    body = await request.json()
    resources = body["checkpoint"]["resources"]
    if not resources:
        return JSONResponse(cbr_error("CBR.0003", "Resources must be specified."), status_code=400)

    for r in resources:
        bound = any(v["project_id"] == pid and any(vr["id"] == r["id"] for vr in v["resources"])
                    for v in state.vaults.values())
        if not bound:
            return JSONResponse(cbr_error("CBR.0004", "The resource is not bound to any vault."), status_code=400)

    vault = next((v for v in state.vaults.values() if v["project_id"] == pid), None)
    vault_id = vault["id"] if vault else ""

    cp_id = new_id()
    state.checkpoints[cp_id] = {
        "id": cp_id, "status": "protecting",
        "created_at": now_millis(), "project_id": pid,
        "vault_id": vault_id, "extra_info": {},
    }

    backup_ids = []
    for r in resources:
        if r["id"] in state.servers:
            s = state.servers[r["id"]]
            rname, rtype, rsize, bootable = s["name"], "OS::Nova::Server", 40, True
        else:
            vol = state.volumes[r["id"]]
            rname, rtype, rsize, bootable = vol["name"], "OS::Cinder::Volume", vol["size"], vol["bootable"] == "true"

        backup_id = new_id()
        state.cbr_backups[backup_id] = {
            "id": backup_id, "checkpoint_id": cp_id,
            "name": body["checkpoint"].get("name", f"backup-{r['id'][:8]}"),
            "description": body["checkpoint"].get("description", ""),
            "resource_id": r["id"], "resource_name": rname,
            "resource_type": rtype, "resource_size": rsize,
            "status": "protecting", "vault_id": vault_id,
            "created_at": now_millis(), "updated_at": now_millis(),
            "expired_at": now_millis(), "protected_at": now_millis(),
            "incremental": False, "image_type": "backup", "version": "0.12.0",
            "extend_info": {"auto_trigger": False, "bootable": bootable,
                            "contain_system_disk": True, "encrypted": False,
                            "is_multi_az": False, "snapshot_id": None,
                            "support_lld": False, "supported_restore_mode": "backup",
                            "system_disk": True, "os_images_data": []},
            "project_id": pid,
        }
        backup_ids.append(backup_id)

    async def _flip():
        await asyncio.sleep(1.5)
        for bid in backup_ids:
            b = state.cbr_backups.get(bid)
            if b:
                b["status"] = "available"
                b["updated_at"] = now_millis()
        c = state.checkpoints.get(cp_id)
        if c:
            c["status"] = "available"

    asyncio.get_event_loop().create_task(_flip())
    return {"checkpoint": _checkpoint_json(state.checkpoints[cp_id])}


@router.get("/v3/{pid}/checkpoints/{checkpoint_id}")
async def show_checkpoint(request: Request, pid: str, checkpoint_id: str):
    state = request.app.state.sim
    c = state.checkpoints.get(checkpoint_id)
    if not c or c["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0012", "The checkpoint does not exist."), status_code=404)
    return {"checkpoint": _checkpoint_json(c)}


# ---------------------------------------------------------------------------
# backups
# ---------------------------------------------------------------------------

@router.get("/v3/{pid}/backups")
async def list_backups(request: Request, pid: str):
    state = request.app.state.sim
    rid = request.query_params.get("resource_id")
    backups = [b for b in state.cbr_backups.values() if b["project_id"] == pid]
    if rid:
        backups = [b for b in backups if b["resource_id"] == rid]
    return {"backups": [_backup_json(b) for b in backups],
            "count": len(backups), "limit": 100, "offset": 0}


@router.get("/v3/{pid}/backups/{backup_id}")
async def show_backup(request: Request, pid: str, backup_id: str):
    state = request.app.state.sim
    b = state.cbr_backups.get(backup_id)
    if not b or b["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0013", "The backup does not exist."), status_code=404)
    return {"backup": _backup_json(b)}


@router.delete("/v3/{pid}/backups/{backup_id}")
async def delete_backup(request: Request, pid: str, backup_id: str):
    state = request.app.state.sim
    b = state.cbr_backups.get(backup_id)
    if not b or b["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0013", "The backup does not exist."), status_code=404)
    del state.cbr_backups[backup_id]
    return Response(status_code=204)


@router.post("/v3/{pid}/backups/{backup_id}/restore")
async def restore_backup(request: Request, pid: str, backup_id: str):
    state = request.app.state.sim
    b = state.cbr_backups.get(backup_id)
    if not b or b["project_id"] != pid:
        return JSONResponse(cbr_error("CBR.0013", "The backup does not exist."), status_code=404)
    if b["status"] != "available":
        return JSONResponse(cbr_error("CBR.0005", "The backup is not available yet."), status_code=400)
    if b["resource_type"] != "OS::Cinder::Volume":
        return JSONResponse(cbr_error("CBR.0006",
            "Only volume backups can be restored to volumes in the sim."), status_code=400)

    new_vol_id = state.create_volume(pid, f"restore-{b['resource_name']}",
                                      b["resource_size"], "az-dc-1", "SAS", True)

    async def _flip():
        await asyncio.sleep(1.5)
        v = state.volumes.get(new_vol_id)
        if v:
            v["status"] = "available"
            v["updated_at"] = now_millis()

    asyncio.get_event_loop().create_task(_flip())
    body = await request.json()
    return {"restore": {"resource_id": b["resource_id"], "volume_id": new_vol_id,
                        "power_on": body.get("restore", {}).get("power_on", False),
                        "mappings": [], "details": None}}
