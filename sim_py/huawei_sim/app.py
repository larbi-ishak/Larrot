"""FastAPI app factory — assembles all services with middleware."""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .core.state import SimState
from .core.envelopes import apigw_error
from .persistence import save_state, load_state
from .dashboard import dashboard_html
from .middleware import gateway_middleware
from .services import (
    iam, ecs, evs, vpc, ims, cbr, obs, rds, dns, kms, elb, sfs, cce, functiongraph,
    bms, as_, smn, ces, lts, dcs, dms, dds, waf, tms, eps, apig, swr, modelarts,
    iotda, gaussdb, aom, dli, antiddos, bss,
    nat, peering, acl, routes, vpn,
    ecs_keypairs, ecs_server_groups, ecs_extras, batch, hpc,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("huawei_sim")


def create_app() -> FastAPI:
    """Create the REST app (port 8200)."""
    app = FastAPI(
        title="huawei-sim",
        description="Local Huawei Cloud API simulator — like LocalStack, but for Huawei Cloud",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    state = SimState()
    app.state.sim = state

    # Mount service routers
    app.include_router(iam.router)
    app.include_router(ecs.router)
    app.include_router(evs.router)
    app.include_router(vpc.router)
    app.include_router(ims.router)
    app.include_router(cbr.router)
    app.include_router(rds.router)
    app.include_router(dns.router)
    app.include_router(kms.router)
    app.include_router(elb.router)
    app.include_router(sfs.router)
    app.include_router(cce.router)
    app.include_router(functiongraph.router)
    app.include_router(bms.router)
    app.include_router(as_.router)
    app.include_router(smn.router)
    app.include_router(ces.router)
    app.include_router(lts.router)
    app.include_router(dcs.router)
    app.include_router(dms.router)
    app.include_router(dds.router)
    app.include_router(waf.router)
    app.include_router(tms.router)
    app.include_router(eps.router)
    app.include_router(apig.router)
    app.include_router(swr.router)
    app.include_router(modelarts.router)
    app.include_router(iotda.router)
    app.include_router(gaussdb.router)
    app.include_router(aom.router)
    app.include_router(dli.router)
    app.include_router(antiddos.router)
    app.include_router(bss.router)
    app.include_router(nat.router)
    app.include_router(peering.router)
    app.include_router(acl.router)
    app.include_router(routes.router)
    app.include_router(vpn.router)
    app.include_router(ecs_keypairs.router)
    app.include_router(ecs_server_groups.router)
    app.include_router(ecs_extras.router)
    app.include_router(batch.router)
    app.include_router(hpc.router)

    # Middleware (outermost first: rate limit → signature → logging)
    app.middleware("http")(gateway_middleware)

    # Fallback: unknown paths → APIGW.0101
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            apigw_error("APIGW.0101",
                        "The API does not exist or has not been published in the environment."),
            status_code=404,
        )

    # Web dashboard
    @app.get("/", include_in_schema=False)
    async def dashboard():
        return dashboard_html(state)

    # Health check
    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok", "version": "1.0.0",
                "services": ["iam", "ecs", "evs", "vpc", "eip", "ims", "cbr", "rds", "dns", "kms", "elb", "sfs", "cce", "functiongraph", "bms", "as", "smn", "ces", "lts", "dcs", "dms", "dds", "waf", "tms", "eps", "apig", "swr", "modelarts", "iotda", "gaussdb", "aom", "dli", "antiddos", "bss", "nat", "peering", "acl", "routes", "vpn", "ecs_keypairs", "ecs_server_groups", "ecs_extras", "batch", "hpc", "obs"]}

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
    import os
    persist_dir = os.environ.get("SIM_PERSIST_DIR", "/tmp/huawei-sim")

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

    return app


def create_obs_app() -> FastAPI:
    """Create the OBS app (port 8201) — separate endpoint, like the real cloud."""
    app = FastAPI(title="huawei-sim OBS", version="1.0.0", docs_url=None, redoc_url=None)
    state = SimState()
    app.state.sim = state

    from .middleware import obs_middleware
    app.middleware("http")(obs_middleware)
    app.include_router(obs.router)
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
<html><head><title>huawei-sim dashboard</title>
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
<h1>huawei-sim</h1>
<p class="sub">Local Huawei Cloud API simulator · <a href="/docs">API Docs</a> · OBS on :8201</p>
<div class="grid">{cards}</div>
<h2>Projects</h2>
<table><tr><th>Region</th><th>Project ID</th><th>Profile</th></tr>{projects}</table>
<p><span class="badge {'green' if running_jobs == 0 else 'yellow'}">{running_jobs} jobs running</span></p>
</body></html>"""
