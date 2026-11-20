"""State persistence: save/load the full simulator state to/from JSON."""

import json
import os
from .core.state import SimState


def save_state(state: SimState, path: str) -> None:
    """Save all resource stores to a JSON file."""
    data = {
        "account": state.account,
        "projects": [{**p, "profile": p["profile"].value} for p in state.projects],
        "images": state.images,
        "flavors": state.flavors,
        "servers": state.servers,
        "volumes": state.volumes,
        "snapshots": state.snapshots,
        "ports": state.ports,
        "vpcs": state.vpcs,
        "subnets": state.subnets,
        "eips": state.eips,
        "security_groups": state.security_groups,
        "obs_buckets": state.obs_buckets,
        "obs_objects": {k: {**v, "data": v["data"].hex()} for k, v in state.obs_objects.items()},
        "obs_uploads": state.obs_uploads,
        "vaults": state.vaults,
        "cbr_policies": state.cbr_policies,
        "cbr_backups": state.cbr_backups,
        "checkpoints": state.checkpoints,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_state(state: SimState, path: str) -> None:
    """Load resource stores from a JSON file (replaces current state)."""
    with open(path) as f:
        data = json.load(f)

    from .core.profiles import Profile

    state.account = data.get("account", state.account)
    state.projects = [{**p, "profile": Profile.parse(p.get("profile", "public"))}
                       for p in data.get("projects", [])]
    state.images = data.get("images", {})
    state.flavors = data.get("flavors", [])
    state.servers = data.get("servers", {})
    state.volumes = data.get("volumes", {})
    state.snapshots = data.get("snapshots", {})
    state.ports = data.get("ports", {})
    state.vpcs = data.get("vpcs", {})
    state.subnets = data.get("subnets", {})
    state.eips = data.get("eips", {})
    state.security_groups = data.get("security_groups", {})
    state.obs_buckets = data.get("obs_buckets", {})
    state.obs_objects = {k: {**v, "data": bytes.fromhex(v["data"])}
                          for k, v in data.get("obs_objects", {}).items()}
    state.obs_uploads = data.get("obs_uploads", {})
    state.vaults = data.get("vaults", {})
    state.cbr_policies = data.get("cbr_policies", {})
    state.cbr_backups = data.get("cbr_backups", {})
    state.checkpoints = data.get("checkpoints", {})
