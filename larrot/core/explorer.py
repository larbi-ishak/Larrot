"""Resource explorer: unified inventory, lookup, and dependency graph (ROADMAP 1.3)."""

# Registry: (state_attr, type, id_key, name_key, project_key, status_key)
# state_attr may not exist yet (lazy services) -> getattr(state, attr, {})
RESOURCE_TYPES = [
    ("servers", "ecs.server", "id", "name", "project_id", "status"),
    ("volumes", "evs.volume", "id", "name", "project_id", "status"),
    ("snapshots", "evs.snapshot", "id", "name", "project_id", "status"),
    ("vpcs", "vpc.vpc", "id", "name", "project_id", "status"),
    ("subnets", "vpc.subnet", "id", "name", "project_id", "status"),
    ("ports", "vpc.port", "id", "id", "project_id", None),
    ("eips", "vpc.eip", "id", "public_ip_address", "project_id", "status"),
    ("security_groups", "vpc.security_group", "id", "name", "project_id", None),
    ("images", "ims.image", "id", "name", "project_id", "status"),
    ("vaults", "cbr.vault", "id", "name", "project_id", "status"),
    ("cbr_backups", "cbr.backup", "id", "name", "project_id", "status"),
    ("obs_buckets", "obs.bucket", "name", "name", None, None),
    ("nat_gateways", "nat.gateway", "id", "name", "project_id", "status"),
    ("dws_clusters", "dws.cluster", "id", "name", "project_id", "status"),
    ("css_clusters", "css.cluster", "id", "name", "project_id", "status"),
    ("mrs_clusters", "mrs.cluster", "id", "name", "project_id", "status"),
    ("sms_sources", "sms.source", "id", "name", "project_id", "state"),
    ("sms_tasks", "sms.task", "id", "name", "project_id", "state"),
    ("dc_connections", "dc.direct_connect", "id", "name", "project_id", "status"),
    ("er_instances", "er.instance", "id", "name", "project_id", "state"),
    ("er_attachments", "er.attachment", "id", "name", "project_id", "state"),
    ("dis_streams", "dis.stream", "stream_id", "stream_name", "project_id", "status"),
    ("dataarts_connections", "dataarts.connection", "connection_id", "name", "project_id", "status"),
    ("oms_tasks", "oms.task", "id", "name", "project_id", "status"),
    ("des_tasks", "des.task", "id", "name", "project_id", "status"),
    ("codearts_repos", "codearts.repository", "repository_id", "name", None, None),
    ("codearts_pipelines", "codearts.pipeline", "pipeline_id", "name", "project_id", "status"),
    ("cas_environments", "servicestage.environment", "id", "name", "project_id", "status"),
    ("cas_applications", "servicestage.application", "id", "name", "project_id", None),
    ("cse_engines", "cse.engine", "id", "name", "project_id", "status"),
    ("cci_namespaces", "cci.namespace", "id", "name", "project_id", "status"),
    ("cci_pods", "cci.pod", "id", "name", "project_id", "status"),
    ("cfw_firewalls", "cfw.firewall", "id", "name", "project_id", "status"),
    ("dsc_assets", "dsc.asset", "asset_id", "asset_name", "project_id", None),
    ("vod_assets", "vod.asset", "id", "name", "project_id", "status"),
    ("ief_nodes", "ief.node", "id", "name", "project_id", "state"),
    ("ief_deployments", "ief.deployment", "id", "name", "project_id", "state"),
    ("ma_notebooks", "modelarts.notebook", "id", "name", "project_id", "status"),
    ("ma_models", "modelarts.model", "model_id", "model_name", "project_id", "status"),
    ("ma_services", "modelarts.service", "service_id", "service_name", "project_id", "status"),
    ("cdn_domains", "cdn.domain", "id", "name", None, "status"),
]


def _entry(state, attr, rtype, id_key, name_key, project_key, status_key, obj):
    return {
        "id": obj.get(id_key) or obj.get("id"),
        "type": rtype,
        "name": obj.get(name_key) or obj.get("id", ""),
        "project_id": obj.get(project_key) if project_key else None,
        "status": obj.get(status_key) if status_key else None,
        "created_at": obj.get("created_at") or obj.get("create_time"),
    }


def inventory(state, rid=None, rtype=None, project=None, name=None):
    """Unified inventory with optional filters."""
    out = []
    for attr, t, idk, namek, projk, statk in RESOURCE_TYPES:
        store = getattr(state, attr, None) or {}
        for obj in store.values():
            if not isinstance(obj, dict):
                continue
            e = _entry(state, attr, t, idk, namek, projk, statk, obj)
            if rid and e["id"] != rid:
                continue
            if rtype and e["type"] != rtype:
                continue
            if project and e["project_id"] != project:
                continue
            if name and name.lower() not in str(e["name"]).lower():
                continue
            out.append(e)
    return out


def find(state, rid):
    """Find a resource anywhere, by id."""
    hits = inventory(state, rid=rid)
    return hits[0] if hits else None


def _raw(state, rid):
    """Return the raw stored object for an id, plus its registry row."""
    for attr, t, idk, namek, projk, statk in RESOURCE_TYPES:
        store = getattr(state, attr, None) or {}
        for obj in store.values():
            if isinstance(obj, dict) and (obj.get(idk) == rid or obj.get("id") == rid):
                return attr, t, obj
    return None, None, None


def graph(state, rid):
    """Direct dependency edges for a resource (ROADMAP 1.3)."""
    node = find(state, rid)
    if not node:
        return None
    attr, rtype, raw = _raw(state, rid)
    edges = []

    def link(other_type, other_id, label):
        if other_id:
            edges.append({"type": other_type, "id": other_id, "relation": label})

    if rtype == "ecs.server":
        for p in state.ports.values():
            if p.get("device_id") == rid:
                link("vpc.port", p["id"], "has_nic")
        for v in state.volumes.values():
            for att in v.get("attachments", []):
                if att.get("server_id") == rid:
                    link("evs.volume", v["id"], "attached_volume")
        attached_vols = {v["id"] for v in state.volumes.values()
                         if any(att.get("server_id") == rid for att in v.get("attachments", []))}
        for s in state.snapshots.values():
            if s.get("volume_id") in attached_vols:
                link("evs.snapshot", s["id"], "snapshot_of_attached")
    elif rtype == "vpc.vpc":
        for s in state.subnets.values():
            if s.get("vpc_id") == rid:
                link("vpc.subnet", s["id"], "contains_subnet")
        for p in state.ports.values():
            if p.get("network_id") == rid:
                link("vpc.port", p["id"], "has_port")
    elif rtype == "vpc.subnet":
        for p in state.ports.values():
            if p.get("subnet_id") == rid:
                link("vpc.port", p["id"], "has_port")
    elif rtype == "vpc.port":
        link("ecs.server", raw.get("device_id"), "belongs_to")
    elif rtype == "evs.volume":
        for att in raw.get("attachments", []):
            link("ecs.server", att.get("server_id"), "attached_to")
    elif rtype == "vpc.eip":
        link("vpc.port", raw.get("port_id"), "bound_to")
    elif rtype == "er.instance":
        for a in getattr(state, "er_attachments", {}).values():
            if a.get("er_id") == rid:
                link("er.attachment", a["id"], "has_attachment")
    elif rtype == "cse.engine":
        for m in getattr(state, "cse_microservices", {}).values():
            if m.get("engine_id") == rid:
                link("cse.microservice", m.get("serviceId"), "hosts")
    elif rtype == "cci.namespace":
        for p in getattr(state, "cci_pods", {}).values():
            if p.get("namespace_id") == rid:
                link("cci.pod", p["id"], "contains_pod")

    return {"resource": node, "edges": edges}
