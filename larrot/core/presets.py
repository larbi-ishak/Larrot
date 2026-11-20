"""Preset environments: one-call deployment of realistic seeded setups (ROADMAP 2.2).

Presets build resources directly on the state in their final ("ready") states,
skipping the async job machinery: a preset is seed data, not a workflow.
"""

from ..core.jobs import new_id, now_millis


def _ensure(state, attr):
    if not hasattr(state, attr):
        setattr(state, attr, {})
    return getattr(state, attr)


def _make_server(state, pid, name, sg_name=None):
    """Build an ACTIVE server (port + root volume included) via the ECS helper."""
    from ..services.ecs import _build_server
    image = next(iter(state.images))
    flavor = next(f for f in state.flavors
                  if state.project(pid)["name"] in f["regions"])
    server = _build_server(state, pid, {
        "imageRef": image, "flavorRef": flavor["id"], "name": name,
    })
    server["status"] = "ACTIVE"
    server["OS-EXT-STS:vm_state"] = "active"
    server["OS-EXT-STS:power_state"] = 1
    if sg_name:
        server["security_groups"] = [{"name": sg_name}]
    state.servers[server["id"]] = server
    return server


def _three_tier_app(state, pid):
    """Web tier: SG + 2 ACTIVE servers + ELB (listener, pool, members) + EIP."""
    project = state.project(pid)
    sg_id = new_id()
    state.security_groups[sg_id] = {
        "id": sg_id, "name": "three-tier-sg", "project_id": pid,
        "description": "preset: three-tier-app", "security_group_rules": [],
    }

    servers = [_make_server(state, pid, f"web-{i}", "three-tier-sg") for i in (1, 2)]

    lbs = _ensure(state, "elb_loadbalancers")
    listeners = _ensure(state, "elb_listeners")
    pools = _ensure(state, "elb_pools")
    now = now_millis()
    lb_id = new_id()
    lbs[lb_id] = {
        "id": lb_id, "name": "three-tier-elb", "description": "preset",
        "vip_subnet_id": project["subnet_id"], "vpc_id": project["vpc_id"],
        "ip_address": f"192.168.0.{100 + len(lbs)}",
        "listeners": [], "pools": [],
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    pool_id = new_id()
    now = now_millis()
    pools[pool_id] = {
        "id": pool_id, "name": "web-pool", "protocol": "HTTP",
        "loadbalancer_id": lb_id, "members": [
            {"id": new_id(), "address": next(
                a["addr"] for addrs in s["addresses"].values() for a in addrs),
             "protocol_port": 80, "pool_id": pool_id, "weight": 1,
             "subnet_id": project["subnet_id"],
             "created_at": now, "updated_at": now}
            for s in servers],
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    lis_id = new_id()
    listeners[lis_id] = {
        "id": lis_id, "name": "web-http", "protocol": "HTTP", "protocol_port": 80,
        "loadbalancer_id": lb_id, "default_pool_id": pool_id,
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    lbs[lb_id]["listeners"] = [{"id": lis_id}]
    lbs[lb_id]["pools"] = [{"id": pool_id}]

    n = len(state.eips)
    eip_id = new_id()
    state.eips[eip_id] = {
        "id": eip_id, "alias": "three-tier-eip", "status": "DOWN",
        "ip_type": "5_bgp", "public_ip_address": f"119.3.{n // 255}.{10 + n % 240}",
        "ip_version": 4, "tenant_id": pid, "create_time": now,
        "bandwidth_id": new_id(), "bandwidth_name": "three-tier-bw",
        "bandwidth_size": 5, "bandwidth_share_type": "PER", "charge_mode": "traffic",
        "enterprise_project_id": "0", "project_id": pid,
    }
    return {"servers": [s["id"] for s in servers], "security_group": sg_id,
            "loadbalancer": lb_id, "listener": lis_id, "pool": pool_id, "eip": eip_id}


def _dr(state, pid):
    """Disaster recovery: server + data volume + snapshot + CBR vault + backup."""
    server = _make_server(state, pid, "dr-app")

    vol_id = state.create_volume(pid, "dr-data", 50, "az-dc-1", "SAS", False)
    state.volumes[vol_id]["status"] = "available"

    now = now_millis()
    snap_id = new_id()
    state.snapshots[snap_id] = {
        "id": snap_id, "status": "available", "name": "dr-data-snap",
        "description": "preset: dr", "volume_id": vol_id, "size": 50,
        "created_at": now, "updated_at": now, "metadata": {}, "project_id": pid,
    }

    vault_id = new_id()
    state.vaults[vault_id] = {
        "id": vault_id, "name": "dr-vault", "description": "preset: dr",
        "resources": [
            {"id": server["id"], "name": server["name"], "type": "OS::Nova::Server",
             "protect_status": "available", "size": 40, "backup_size": 0,
             "backup_count": 0, "extra_info": {}},
            {"id": vol_id, "name": "dr-data", "type": "OS::Cinder::Volume",
             "protect_status": "available", "size": 50, "backup_size": 0,
             "backup_count": 0, "extra_info": {}},
        ],
        "auto_bind": False, "auto_expand": False, "availability_zone": "az-dc-1",
        "billing": {"consistent_level": "crash_consistent", "object_type": "server",
                     "protect_type": "backup", "size": 100},
        "project_id": pid, "user_id": "b44a37e1192442acaa0d578b63e38fe3",
        "provider_id": "0c99f9b3", "created_at": now,
    }

    backup_id = new_id()
    state.cbr_backups[backup_id] = {
        "id": backup_id, "checkpoint_id": new_id(), "name": "dr-backup",
        "description": "preset: dr", "resource_id": server["id"],
        "resource_name": server["name"], "resource_type": "OS::Nova::Server",
        "resource_size": 40, "status": "available", "vault_id": vault_id,
        "created_at": now, "updated_at": now, "expired_at": now, "protected_at": now,
        "incremental": False, "image_type": "backup", "version": "0.12.0",
        "extend_info": {"auto_trigger": False, "bootable": True,
                         "contain_system_disk": True, "encrypted": False,
                         "is_multi_az": False, "snapshot_id": None,
                         "support_lld": False, "supported_restore_mode": "backup",
                         "system_disk": True, "os_images_data": []},
        "project_id": pid,
    }
    return {"server": server["id"], "volume": vol_id, "snapshot": snap_id,
            "vault": vault_id, "backup": backup_id}


def _multi_tenant(state, pid):
    """Resources in both projects: public (ap-southeast-1) + HCS (tr-west-1)."""
    created = {}
    for project in state.projects:
        p = project["id"]
        server = _make_server(state, p, f"tenant-{project['name']}")
        vol_id = state.create_volume(p, f"vol-{project['name']}", 20, "az-dc-1", "SAS", False)
        state.volumes[vol_id]["status"] = "available"
        created[project["name"]] = {"server": server["id"], "volume": vol_id}
    return {"tenants": created}


PRESETS = {
    "three-tier-app": {
        "description": "SG + 2 web servers + ELB (listener/pool/members) + EIP",
        "build": _three_tier_app,
    },
    "dr": {
        "description": "Server + data volume + snapshot + CBR vault + backup",
        "build": _dr,
    },
    "multi-tenant": {
        "description": "A server + volume in every project (public + HCS)",
        "build": _multi_tenant,
    },
}


def deploy(state, name: str) -> dict:
    return PRESETS[name]["build"](state, state.projects[0]["id"])
