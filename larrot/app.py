"""FastAPI app factory: assembles all services with middleware."""

import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .core.envelopes import apigw_error
from .core.state import SimState
from .dashboard import dashboard_html
from .middleware import gateway_middleware
from .persistence import load_state, save_state
from .services import (
    acl,
    antiddos,
    aom,
    apig,
    as_,
    batch,
    bms,
    bss,
    cbr,
    cce,
    cci,
    cdn,
    ces,
    cfw,
    codearts,
    cse,
    css,
    dataarts,
    dbss,
    dc,
    dcs,
    dcs_extras,
    ddm,
    dds,
    des,
    dis,
    dli,
    dms,
    dns,
    dsc,
    dws,
    ecs,
    ecs_extras,
    ecs_keypairs,
    ecs_server_groups,
    elb,
    eps,
    er,
    evs,
    functiongraph,
    gaussdb,
    geminidb,
    hpc,
    hss,
    iam,
    ief,
    ims,
    iotda,
    kms,
    lts,
    modelarts,
    mrs,
    nat,
    obs,
    oms,
    peering,
    rds,
    rds_extras,
    routes,
    servicestage,
    sfs,
    smn,
    sms,
    swr,
    tms,
    vod,
    vpc,
    vpc_v3,
    vpn,
    waf,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("larrot")


def create_app() -> FastAPI:
    """Create the REST app (port 8200)."""
    from . import __version__
    app = FastAPI(
        title="Larrot",
        description="Larrot repeats Huawei Cloud. A local Huawei Cloud API simulator: LocalStack, but for Huawei Cloud",
        version=__version__,
        # Custom branded docs: /docs wraps /docs/swagger with the shared navbar
        docs_url=None,
        redoc_url="/redoc",
    )
    state = SimState()
    app.state.sim = state

    # State persistence (SIM_PERSIST=1): restore on start, save on shutdown
    if os.environ.get("SIM_PERSIST", "").lower() in ("1", "true", "yes"):
        from .persistence import state_path as _state_path
        _path = _state_path()
        _restored = load_state(state, _path)
        if _restored:
            logger.info("persist: restored %d stores from %s", _restored, _path)

        @app.on_event("shutdown")
        async def _persist_on_shutdown():
            saved = save_state(state, _path)
            logger.info("persist: saved %d stores to %s", saved, _path)

    # Chaos engine (ROADMAP 1.2) + job engine hook
    from .core.chaos import ChaosEngine
    state.chaos = ChaosEngine()
    state.jobs.chaos = state.chaos

    # A missing or malformed JSON body is a client error, never a 500
    import json as _json

    @app.exception_handler(_json.JSONDecodeError)
    async def malformed_json_handler(request, exc):
        return JSONResponse(
            {"error_msg": "Invalid request body: expected JSON.",
             "error_code": "Common.0001", "request_id": ""},
            status_code=400)

    # Mount service routers
    app.include_router(iam.router, tags=["IAM"])
    app.include_router(ecs.router, tags=["ECS"])
    app.include_router(evs.router, tags=["EVS"])
    app.include_router(vpc.router, tags=["VPC"])
    app.include_router(vpc_v3.router, tags=["VPC"])
    app.include_router(ims.router, tags=["IMS"])
    app.include_router(cbr.router, tags=["CBR"])
    app.include_router(rds.router, tags=["RDS"])
    app.include_router(dns.router, tags=["DNS"])
    app.include_router(kms.router, tags=["KMS"])
    app.include_router(elb.router, tags=["ELB"])
    app.include_router(sfs.router, tags=["SFS"])
    app.include_router(cce.router, tags=["CCE"])
    app.include_router(functiongraph.router, tags=["FunctionGraph"])
    app.include_router(bms.router, tags=["BMS"])
    app.include_router(as_.router, tags=["AS"])
    app.include_router(smn.router, tags=["SMN"])
    app.include_router(ces.router, tags=["CES"])
    app.include_router(lts.router, tags=["LTS"])
    app.include_router(dcs.router, tags=["DCS"])
    app.include_router(dms.router, tags=["DMS"])
    app.include_router(dds.router, tags=["DDS"])
    app.include_router(waf.router, tags=["WAF"])
    app.include_router(tms.router, tags=["TMS"])
    app.include_router(eps.router, tags=["EPS"])
    app.include_router(apig.router, tags=["APIG"])
    app.include_router(swr.router, tags=["SWR"])
    app.include_router(modelarts.router, tags=["ModelArts + MaaS"])
    app.include_router(iotda.router, tags=["IoTDA"])
    app.include_router(gaussdb.router, tags=["GaussDB"])
    app.include_router(aom.router, tags=["AOM"])
    app.include_router(dli.router, tags=["DLI"])
    app.include_router(antiddos.router, tags=["Anti-DDoS"])
    app.include_router(bss.router, tags=["BSS"])
    app.include_router(nat.router, tags=["NAT"])
    app.include_router(peering.router, tags=["VPC Peering"])
    app.include_router(acl.router, tags=["Network ACL"])
    app.include_router(routes.router, tags=["VPC Routes"])
    app.include_router(vpn.router, tags=["VPN"])
    app.include_router(ecs_keypairs.router, tags=["ECS Keypairs"])
    app.include_router(ecs_server_groups.router, tags=["ECS Server Groups"])
    app.include_router(ecs_extras.router, tags=["ECS Extras"])
    app.include_router(batch.router, tags=["ECS Batch"])
    app.include_router(hpc.router, tags=["HPC"])
    app.include_router(rds_extras.router, tags=["RDS Extras"])
    app.include_router(geminidb.router, tags=["GeminiDB"])
    app.include_router(ddm.router, tags=["DDM"])
    app.include_router(dbss.router, tags=["DBSS"])
    app.include_router(dcs_extras.router, tags=["DCS Extras"])
    app.include_router(hss.router, tags=["HSS"])
    app.include_router(cdn.router, tags=["CDN"])
    app.include_router(dws.router, tags=["DWS"])
    app.include_router(css.router, tags=["CSS"])
    app.include_router(mrs.router, tags=["MRS"])
    app.include_router(sms.router, tags=["SMS"])
    app.include_router(dc.router, tags=["Direct Connect"])
    app.include_router(er.router, tags=["Enterprise Router"])
    app.include_router(dis.router, tags=["DIS"])
    app.include_router(dataarts.router, tags=["DataArts"])
    app.include_router(oms.router, tags=["OMS"])
    app.include_router(des.router, tags=["DES"])
    app.include_router(codearts.router, tags=["CodeArts"])
    app.include_router(servicestage.router, tags=["ServiceStage"])
    app.include_router(cse.router, tags=["CSE"])
    app.include_router(cci.router, tags=["CCI"])
    app.include_router(cfw.router, tags=["CFW"])
    app.include_router(dsc.router, tags=["DSC"])
    app.include_router(vod.router, tags=["VOD"])
    app.include_router(ief.router, tags=["IEF"])

    # Middleware (outermost first: rate limit → signature → logging)
    app.middleware("http")(gateway_middleware)

    # Fallback: unknown paths → APIGW.0101 + near-miss route hints
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        from .core.nearmiss import near_misses
        hints = near_misses(app, request.method, request.url.path)
        request.state.near_misses = hints
        body = apigw_error(
            "APIGW.0101",
            "The API does not exist or has not been published in the environment.")
        body["near_matches"] = hints
        return JSONResponse(body, status_code=404)

    # Web dashboard + console
    from fastapi.responses import FileResponse, HTMLResponse

    from .console import console_html

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        import os
        logo = os.path.join(os.path.dirname(__file__), "static", "logo-64.png")
        return FileResponse(logo, media_type="image/png")

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(dashboard_html(state))

    @app.get("/console", include_in_schema=False, response_class=HTMLResponse)
    async def console():
        return HTMLResponse(console_html(state))

    # Branded API docs: navbar wrapper + raw Swagger UI (served separately
    # so the wrapper page can embed it in an iframe)
    from .ui import api_docs_html

    @app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    async def api_docs():
        return HTMLResponse(api_docs_html())

    @app.get("/docs/swagger", include_in_schema=False)
    async def docs_swagger():
        from fastapi.openapi.docs import get_swagger_ui_html
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " API",
            # 445+ paths: collapse the 66 service tags by default
            swagger_ui_parameters={"docExpansion": "none"},
        )

    # Health check
    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok", "version": "1.0.0",
                "services": ["iam", "ecs", "evs", "vpc", "eip", "ims", "cbr", "rds", "dns", "kms", "elb", "sfs", "cce", "functiongraph", "bms", "as", "smn", "ces", "lts", "dcs", "dms", "dds", "waf", "tms", "eps", "apig", "swr", "modelarts", "iotda", "gaussdb", "aom", "dli", "antiddos", "bss", "nat", "peering", "acl", "routes", "vpn", "ecs_keypairs", "ecs_server_groups", "ecs_extras", "batch", "hpc", "rds_extras", "geminidb", "ddm", "dbss", "dcs_extras", "obs",
                             "hss", "cdn", "dws", "css", "mrs", "sms", "dc", "er", "dis", "dataarts", "oms", "des", "codearts", "servicestage", "cse", "cci", "cfw", "dsc", "vod", "ief", "maas"]}

    # Metrics
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return {
            "servers": len(state.servers),
            "volumes": len(state.volumes),
            "snapshots": len(state.snapshots),
            "vpcs": len(state.vpcs),
            "subnets": len(state.subnets),
            "eips": len(state.eips),
            "security_groups": len(state.security_groups),
            "images": len(state.images),
            "vaults": len(state.vaults),
            "backups": len(state.cbr_backups),
            "obs_buckets": len(state.obs_buckets),
            "obs_objects": len(state.obs_objects),
            "jobs_total": len(state.jobs.jobs),
            "jobs_running": sum(1 for j in state.jobs.jobs.values() if j.status == "RUNNING"),
        }

    # Persistence
    persist_dir = os.environ.get("SIM_PERSIST_DIR", "/tmp/larrot")

    @app.post("/admin/save", include_in_schema=False)
    async def save():
        path = os.path.join(persist_dir, "state.json")
        save_state(state, path)
        return {"saved": path}

    @app.post("/admin/load", include_in_schema=False)
    async def load():
        path = os.path.join(persist_dir, "state.json")
        if not os.path.exists(path):
            return JSONResponse({"error": "no saved state"}, status_code=404)
        load_state(state, path)
        return {"loaded": path}

    # ------------------------------------------------------------------
    # Admin platform: reset, request journal, determinism, state forcing
    # ------------------------------------------------------------------
    @app.post("/admin/reset", include_in_schema=False)
    async def admin_reset():
        """Wipe every store and engine while the server keeps running."""
        from .core import determinism
        from .core.chaos import ChaosEngine
        fresh = SimState()
        fresh.chaos = ChaosEngine()
        fresh.jobs.chaos = fresh.chaos
        old_journal = state.journal
        fresh.journal = old_journal
        for key, val in vars(fresh).items():
            setattr(state, key, val)
        determinism.unseed()
        old_journal.clear()
        return {"reset": True, "stores": len(vars(fresh))}

    @app.get("/admin/requests", include_in_schema=False)
    async def admin_requests(request: Request):
        """Query the request journal (newest first)."""
        p = request.query_params
        status = int(p["status"]) if p.get("status") else None
        matched = None
        if p.get("matched") is not None:
            matched = p.get("matched").lower() == "true"
        return {
            "total": state.journal.total,
            "entries": state.journal.query(
                method=p.get("method"), path=p.get("path"), status=status,
                limit=int(p.get("limit", 100)), matched=matched),
        }

    @app.delete("/admin/requests", include_in_schema=False)
    async def admin_requests_clear():
        return {"cleared": state.journal.clear()}

    @app.post("/admin/seed", include_in_schema=False)
    async def admin_seed(request: Request):
        """Seed the ID generator: POST /admin/seed?a=42 -> deterministic IDs."""
        from .core import determinism
        raw = request.query_params.get("a")
        if raw is None:
            try:
                body = await request.json()
                raw = body.get("a")
            except Exception:
                raw = None
        if raw is None:
            return JSONResponse(
                {"error": "missing seed: use ?a=<int>"},
                status_code=400)
        determinism.seed(int(raw))
        return {"seeded": int(raw)}

    @app.get("/admin/seed", include_in_schema=False)
    async def admin_seed_show():
        from .core import determinism
        return {"seed": determinism.current_seed()}

    @app.put("/admin/state/{rid}", include_in_schema=False)
    async def admin_force_state(rid: str, request: Request):
        """Force a resource into any state without waiting for side effects."""
        from .core import explorer
        hit = explorer.find(state, rid)
        if not hit:
            return JSONResponse({"error": "resource not found"}, status_code=404)
        attr, rtype, raw = explorer._raw(state, rid)
        status_key = "status"
        for row_attr, _t, _idk, _nk, _pk, statk in explorer.RESOURCE_TYPES:
            if row_attr == attr and statk:
                status_key = statk
                break
        body = await request.json()
        if "status" in body:
            raw[status_key] = body["status"]
        for k, v in (body.get("set") or {}).items():
            raw[k] = v
        return {"id": rid, "type": rtype, "status": raw.get(status_key),
                "raw": raw}

    # ------------------------------------------------------------------
    # Chaos fault injection (ROADMAP 1.2)
    # ------------------------------------------------------------------
    @app.post("/admin/chaos", include_in_schema=False)
    async def chaos_add(request: Request):
        try:
            spec = await request.json()
            rule = state.chaos.add(spec)
            return {"rule": rule}
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.get("/admin/chaos", include_in_schema=False)
    async def chaos_list():
        return {"rules": state.chaos.list()}

    @app.delete("/admin/chaos/{rule_id}", include_in_schema=False)
    async def chaos_delete(rule_id: str):
        if not state.chaos.remove(rule_id):
            return JSONResponse({"error": "rule not found"}, status_code=404)
        return Response(status_code=204)

    @app.post("/admin/chaos/reset", include_in_schema=False)
    async def chaos_reset():
        return {"removed": state.chaos.reset()}

    # ------------------------------------------------------------------
    # Resource explorer (ROADMAP 1.3)
    # ------------------------------------------------------------------
    @app.get("/admin/resources", include_in_schema=False)
    async def resources(request: Request):
        from .core import explorer
        params = request.query_params
        items = explorer.inventory(
            state,
            rid=params.get("id"),
            rtype=params.get("type"),
            project=params.get("project"),
            name=params.get("name"),
        )
        return {"total": len(items), "resources": items}

    @app.get("/admin/resources/{rid}", include_in_schema=False)
    async def resource_show(rid: str):
        from .core import explorer
        hit = explorer.find(state, rid)
        if not hit:
            return JSONResponse({"error": "resource not found"}, status_code=404)
        # Also return the raw object for the detail view
        _, _, raw = explorer._raw(state, rid)
        hit["_raw"] = raw
        return hit

    @app.get("/admin/graph/{rid}", include_in_schema=False)
    async def resource_graph(rid: str):
        from .core import explorer
        g = explorer.graph(state, rid)
        if not g:
            return JSONResponse({"error": "resource not found"}, status_code=404)
        return g

    # ------------------------------------------------------------------
    # Preset environments (ROADMAP 2.2)
    # ------------------------------------------------------------------
    @app.get("/admin/preset", include_in_schema=False)
    async def preset_list():
        from .core.presets import PRESETS
        return {"presets": [{"name": k, "description": v["description"]}
                            for k, v in PRESETS.items()]}

    @app.post("/admin/preset/{name}", include_in_schema=False)
    async def preset_deploy(name: str):
        from .core.presets import PRESETS, deploy
        if name not in PRESETS:
            return JSONResponse({"error": f"unknown preset '{name}'",
                                 "available": sorted(PRESETS)}, status_code=404)
        result = deploy(state, name)
        return {"deployed": name, **result}

    return app


def create_obs_app() -> FastAPI:
    """Create the OBS app (port 8201): separate endpoint, like the real cloud."""
    app = FastAPI(title="Larrot OBS", version="1.0.0", docs_url=None, redoc_url=None)
    state = SimState()
    app.state.sim = state

    from .middleware import obs_middleware
    app.middleware("http")(obs_middleware)
    app.include_router(obs.router, tags=["Obs"])
    return app


def _dashboard_html(state) -> str:
    """Simple HTML dashboard showing resource counts."""
    counts = {
        "Servers": len(state.servers),
        "Volumes": len(state.volumes),
        "Snapshots": len(state.snapshots),
        "VPCs": len(state.vpcs),
        "Subnets": len(state.subnets),
        "EIPs": len(state.eips),
        "Security Groups": len(state.security_groups),
        "Images": len(state.images),
        "Vaults": len(state.vaults),
        "Backups": len(state.cbr_backups),
        "OBS Buckets": len(state.obs_buckets),
        "OBS Objects": len(state.obs_objects),
        "Jobs (total)": len(state.jobs.jobs),
    }
    running_jobs = sum(1 for j in state.jobs.jobs.values() if j.status == "RUNNING")

    cards = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="label">{k}</div></div>'
        for k, v in counts.items()
    )
    projects = "".join(
        f'<tr><td>{p["name"]}</td><td>{p["id"]}</td><td>{p["profile"].value}</td></tr>'
        for p in state.projects
    )
    return f"""<!DOCTYPE html>
<html><head><title>larrot dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:2rem}}
h1{{color:#58a6ff;margin-bottom:0.5rem}}
.sub{{color:#8b949e;margin-bottom:2rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:1rem;margin-bottom:2rem}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:1.2rem;text-align:center}}
.num{{font-size:2rem;font-weight:700;color:#58a6ff}}
.label{{color:#8b949e;font-size:0.85rem;margin-top:0.3rem}}
table{{width:100%;border-collapse:collapse;margin-bottom:2rem}}
th,td{{padding:0.6rem 1rem;text-align:left;border-bottom:1px solid #21262d}}
th{{color:#58a6ff;font-weight:600}}
.badge{{display:inline-block;padding:0.2rem 0.6rem;border-radius:12px;font-size:0.75rem;font-weight:600}}
.green{{background:#1a3a2a;color:#3fb950}}
.yellow{{background:#3a311a;color:#d29922}}
a{{color:#58a6ff;text-decoration:none}}
</style></head><body>
<h1>larrot</h1>
<p class="sub">Local Huawei Cloud API simulator · <a href="/docs">API Docs</a> · OBS on :8201</p>
<div class="grid">{cards}</div>
<h2>Projects</h2>
<table><tr><th>Region</th><th>Project ID</th><th>Profile</th></tr>{projects}</table>
<p><span class="badge {'green' if running_jobs == 0 else 'yellow'}">{running_jobs} jobs running</span></p>
</body></html>"""
