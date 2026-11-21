"""Service scaffolder: `larrot new-service <name>`.

Generates a working service module (list/create/show/delete against a
lazy SimState store), a test file, and registers the router in app.py.
If auto-registration cannot be verified, the files are still written and
the exact manual steps are returned.

The Moto scaffolder pattern: adding a service should be one command,
so contributors (human or agent) never start from a blank file.
"""

import re

MODULE_TEMPLATE = '''"""{TAG}: {NAME} resources (scaffolded - replace paths/shapes
with the real API once you have them)."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()

STORE = "{STORE}"  # lazy dict on SimState: getattr(s, STORE, {{}})


def _json(r, pid):
    return {{
        "id": r["id"], "name": r["name"], "status": r["status"],
        "description": r.get("description", ""),
        "project_id": pid,
        "created_at": r.get("created_at", ""),
    }}


@router.get("/v1/{{pid}}/{PATH}s")
async def list_{FN}(request: Request, pid: str, limit: int = None, offset: int = 0):
    s = request.app.state.sim
    items = [_json(r, pid) for r in getattr(s, STORE, {{}}).values()
             if r.get("project_id") == pid]
    items.sort(key=lambda r: r["id"])
    if offset:
        items = items[offset:]
    if limit:
        items = items[:limit]
    return {{"{PATH}s": items, "total_count": len(items)}}


@router.post("/v1/{{pid}}/{PATH}s")
async def create_{FN}(request: Request, pid: str):
    s = request.app.state.sim
    body = await request.json()
    inner = body.get("{PATH}", body)
    r = {{
        "id": new_id(),
        "name": inner.get("name") or f"{PATH}-{{{{new_id()[:8]}}}}",
        "status": "ACTIVE",
        "description": inner.get("description", ""),
        "project_id": pid,
        "created_at": now_millis(),
    }}
    store = getattr(s, STORE, None)
    if store is None:
        store = {{}}
        setattr(s, STORE, store)
    store[r["id"]] = r
    return JSONResponse({{"{PATH}": _json(r, pid)}}, status_code=201)


@router.get("/v1/{{pid}}/{PATH}s/{{rid}}")
async def show_{FN}(request: Request, pid: str, rid: str):
    s = request.app.state.sim
    r = getattr(s, STORE, {{}}).get(rid)
    if not r or r.get("project_id") != pid:
        return JSONResponse(
            {{"error_msg": "{PATH} not found", "error_code": "Common.0004",
              "request_id": ""}},
            status_code=404)
    return {{"{PATH}": _json(r, pid)}}


@router.delete("/v1/{{pid}}/{PATH}s/{{rid}}")
async def delete_{FN}(request: Request, pid: str, rid: str):
    s = request.app.state.sim
    r = getattr(s, STORE, {{}}).get(rid)
    if not r or r.get("project_id") != pid:
        return JSONResponse(
            {{"error_msg": "{PATH} not found", "error_code": "Common.0004",
              "request_id": ""}},
            status_code=404)
    del getattr(s, STORE)[rid]
    return Response(status_code=204)
'''

TEST_TEMPLATE = '''"""Tests for the scaffolded {TAG} service."""

from fastapi.testclient import TestClient

from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


def test_{FN}_crud():
    c = TestClient(create_app())
    # create
    r = c.post(f"/v1/{{PID}}/{PATH}s", json={{"{PATH}": {{"name": "t1"}}}})
    assert r.status_code == 201
    rid = r.json()["{PATH}"]["id"]
    # list
    r = c.get(f"/v1/{{PID}}/{PATH}s")
    assert any(x["id"] == rid for x in r.json()["{PATH}s"])
    # show
    assert c.get(f"/v1/{{PID}}/{PATH}s/{{rid}}").json()["{PATH}"]["name"] == "t1"
    # delete
    assert c.delete(f"/v1/{{PID}}/{PATH}s/{{rid}}").status_code == 204
    assert c.get(f"/v1/{{PID}}/{PATH}s/{{rid}}").status_code == 404


def test_{FN}_unknown_404():
    c = TestClient(create_app())
    assert c.get(f"/v1/{{PID}}/{PATH}s/nope").status_code == 404
'''


def _slug(name: str) -> str:
    """Service name -> python module name (lowercase, underscores)."""
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")


def scaffold_service(name: str, root: str = ".") -> dict:
    """Generate + register a new service. Returns a report dict."""
    mod = _slug(name)
    if not mod or mod[0].isdigit():
        raise ValueError(f"invalid service name: {name!r}")
    tag = mod.upper()
    fn = mod.replace("_", "")
    path = mod.replace("_", "-")
    store = f"{fn}s"

    subs = {"TAG": tag, "NAME": tag, "FN": fn, "PATH": path, "STORE": store}
    module_src = MODULE_TEMPLATE.format(**subs)
    test_src = TEST_TEMPLATE.format(**subs)

    import os
    module_path = os.path.join(root, "larrot", "services", f"{mod}.py")
    test_path = os.path.join(root, "tests", f"test_{mod}.py")
    app_path = os.path.join(root, "larrot", "app.py")

    with open(module_path, "w") as f:
        f.write(module_src)
    with open(test_path, "w") as f:
        f.write(test_src)

    report = {"service": mod, "module": module_path, "tests": test_path,
              "registered": False, "instructions": []}

    # --- auto-register in app.py --------------------------------------
    with open(app_path) as f:
        original = f.read()
    src = original
    # 1. import: alphabetical slot in the services import block
    src = re.sub(
        rf"(from \.services import \(\n)((?:    \w+,\n)*?)(    {re.escape(mod)},?\n)?",
        lambda m: m.group(1) + _insert_sorted(m.group(2), mod),
        src, count=1)
    # 2. include_router after the last one in the REST app factory
    #    (create_obs_app has its own include_router calls - never touch those)
    main_app_src = src.split("def create_obs_app")[0]
    matches = list(re.finditer(r"[ \t]*app\.include_router\([^\n]*\n", main_app_src))
    if matches:
        last = matches[-1]
        line = f'    app.include_router({mod}.router, tags=["{tag}"])\n'
        src = src[:last.end()] + line + src[last.end():]
    try:
        compile(src, "app.py", "exec")
        if f"    {mod},\n" not in src or f"include_router({mod}.router" not in src:
            raise ValueError("registration incomplete")
        with open(app_path, "w") as f:
            f.write(src)
        report["registered"] = True
    except (SyntaxError, ValueError):
        with open(app_path, "w") as f:
            f.write(original)  # roll back
        report["instructions"] = [
            f'Add `{mod},` to the `from .services import (...)` block in larrot/app.py',
            f'Add `app.include_router({mod}.router, tags=["{tag}"])` next to the others',
        ]
    return report


def _insert_sorted(block: str, mod: str) -> str:
    """Insert '    mod,\\n' into the import block, alphabetically."""
    lines = [ln for ln in block.splitlines() if ln.strip()]
    lines.append(f"    {mod},")
    lines = sorted(set(lines), key=lambda ln: ln.strip().rstrip(","))
    return "\n".join(lines) + "\n"
