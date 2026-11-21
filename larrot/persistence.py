"""State persistence: save/load the full simulator state to/from JSON.

Generic: every JSON-serializable attribute on SimState is a store, so
services that create stores lazily (rds_instances, dns_zones, ...) are
picked up automatically. Binary values (OBS object data) are hex-coded,
enums (region quirk profiles) serialize to their value. The file carries
a version field so future format changes can migrate old state.
"""

import enum
import json
import logging
import os
import time

logger = logging.getLogger("larrot")

STATE_VERSION = 1

# Engine objects are rebuilt on start; only resource stores survive.
SKIP_ATTRS = {"jobs", "limiter", "chaos", "profile_default"}

DEFAULT_PATH = os.path.join("~", ".larrot", "state.json")


def state_path() -> str:
    """Where the state file lives (honors SIM_STATE_FILE)."""
    return os.environ.get("SIM_STATE_FILE") or os.path.expanduser(DEFAULT_PATH)


def _encode(o):
    """JSON fallback encoder: enums -> value, bytes -> hex wrapper."""
    if isinstance(o, enum.Enum):
        return o.value
    if isinstance(o, (bytes, bytearray)):
        return {"__hex__": o.hex()}
    raise TypeError(f"not serializable: {type(o)}")


def _decode(o):
    """JSON object hook: hex wrapper -> bytes."""
    if isinstance(o, dict) and "__hex__" in o:
        return bytes.fromhex(o["__hex__"])
    return o


def save_state(state, path: str) -> int:
    """Write every store to disk atomically. Returns the store count."""
    stores = {}
    for key, val in vars(state).items():
        if key in SKIP_ATTRS:
            continue
        try:
            json.dumps(val, default=_encode)
        except TypeError:
            continue  # engine objects and other non-store attributes
        stores[key] = val
    doc = {
        "version": STATE_VERSION,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stores": stores,
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, default=_encode)
    os.replace(tmp, path)
    return len(stores)


def load_state(state, path: str) -> int:
    """Restore stores from disk into state. Returns the store count."""
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        doc = json.load(f, object_hook=_decode)
    version = doc.get("version", 1)
    if version > STATE_VERSION:
        logger.warning("persist: state file version %s > supported %s; "
                       "loading anyway", version, STATE_VERSION)
    stores = doc.get("stores", {})
    for key, val in stores.items():
        if key in SKIP_ATTRS:
            continue
        setattr(state, key, val)
    # Projects carry the region quirk profile as an enum; it was saved as
    # a string, so parse it back.
    from .core.profiles import Profile
    for p in getattr(state, "projects", []):
        if isinstance(p.get("profile"), str):
            p["profile"] = Profile.parse(p["profile"])
    return len(stores)
