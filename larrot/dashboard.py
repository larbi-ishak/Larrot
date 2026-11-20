"""Enhanced web dashboard with real-time updates and resource browsing."""

from fastapi import Request
from fastapi.responses import HTMLResponse
import json


def dashboard_html(state) -> str:
    """Rich HTML dashboard with auto-refresh, resource browsing, and job history."""
    # Gather resource data
    resources = {}
    for name, store in [
        ("Servers", state.servers), ("Volumes", state.volumes),
        ("Snapshots", state.snapshots), ("VPCs", state.vpcs),
        ("Subnets", state.subnets), ("EIPs", state.eips),
        ("Security Groups", state.security_groups), ("Images", state.images),
        ("Vaults", state.vaults), ("Backups", state.cbr_backups),
        ("OBS Buckets", state.obs_buckets), ("OBS Objects", state.obs_objects),
    ]:
        resources[name] = len(store)

    # Additional services
    for attr, name in [("rds_instances", "RDS Instances"), ("dns_zones", "DNS Zones"),
                       ("kms_keys", "KMS Keys"), ("elb_loadbalancers", "Load Balancers"),
                       ("sfs_shares", "File Shares"), ("cce_clusters", "CCE Clusters"),
                       ("fg_functions", "Functions")]:
        resources[name] = len(getattr(state, attr, {}))

    running_jobs = sum(1 for j in state.jobs.jobs.values() if j.status == "RUNNING")
    total_jobs = len(state.jobs.jobs)

    # Recent jobs (last 10)
    recent_jobs = sorted(state.jobs.jobs.values(), key=lambda j: j.begin_time, reverse=True)[:10]
    jobs_html = "".join(
        f'<tr><td>{j.job_id[:12]}…</td><td>{j.job_type}</td>'
        f'<td><span class="badge {"green" if j.status == "SUCCESS" else "yellow" if j.status == "RUNNING" else "red"}">{j.status}</span></td>'
        f'<td>{j.begin_time}</td></tr>'
        for j in recent_jobs
    )

    # Resource cards
    cards = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="label">{k}</div></div>'
        for k, v in resources.items()
    )

    # Projects table
    projects_html = "".join(
        f'<tr><td>{p["name"]}</td><td>{p["id"]}</td>'
        f'<td><span class="badge {"blue" if p["profile"].value == "public" else "orange"}">{p["profile"].value}</span></td></tr>'
        for p in state.projects
    )

    # Server list
    servers_html = "".join(
        f'<tr><td>{s["id"][:12]}…</td><td>{s["name"]}</td>'
        f'<td><span class="badge {"green" if s["status"] == "ACTIVE" else "red" if s["status"] == "ERROR" else "yellow"}">{s["status"]}</span></td>'
        f'<td>{s.get("flavor", {}).get("id", "-")}</td>'
        f'<td>{s.get("OS-EXT-AZ:availability_zone", "-")}</td></tr>'
        for s in list(state.servers.values())[:20]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="5">
<title>larrot dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     background:#0d1117;color:#c9d1d9;padding:1.5rem;line-height:1.5}}
h1{{color:#58a6ff;font-size:1.5rem;margin-bottom:0.3rem}}
h2{{color:#58a6ff;font-size:1.1rem;margin:1.5rem 0 0.5rem}}
.sub{{color:#8b949e;font-size:0.85rem;margin-bottom:1.5rem}}
a{{color:#58a6ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0.8rem;margin-bottom:1rem}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.8rem;text-align:center;transition:transform 0.15s}}
.card:hover{{transform:scale(1.05);border-color:#58a6ff}}
.num{{font-size:1.6rem;font-weight:700;color:#58a6ff}}
.label{{color:#8b949e;font-size:0.75rem;margin-top:0.2rem}}
table{{width:100%;border-collapse:collapse;margin-bottom:1rem;background:#161b22;border-radius:8px;overflow:hidden}}
th{{background:#21262d;color:#58a6ff;padding:0.5rem 0.8rem;text-align:left;font-size:0.8rem;text-transform:uppercase}}
td{{padding:0.5rem 0.8rem;border-bottom:1px solid #21262d;font-size:0.85rem}}
.badge{{display:inline-block;padding:0.15rem 0.5rem;border-radius:10px;font-size:0.7rem;font-weight:600}}
.green{{background:#1a3a2a;color:#3fb950}}
.yellow{{background:#3a311a;color:#d29922}}
.red{{background:#3a1a1a;color:#f85149}}
.blue{{background:#1a2a3a;color:#58a6ff}}
.orange{{background:#3a2a1a;color:#f0883e}}
.empty{{color:#484f58;text-align:center;padding:1.5rem;font-style:italic}}
.footer{{margin-top:2rem;padding-top:1rem;border-top:1px solid #21262d;color:#484f58;font-size:0.75rem}}
</style>
</head><body>
<h1>⚡ larrot</h1>
<p class="sub">Local Huawei Cloud API simulator ·
<a href="/docs">API Docs</a> ·
<a href="/health">Health</a> ·
<a href="/metrics">Metrics</a> ·
OBS on <a href="http://127.0.0.1:8201/">:8201</a> ·
auto-refreshes every 5s</p>

<div class="grid">{cards}</div>

<h2>Projects</h2>
<table><tr><th>Region</th><th>Project ID</th><th>Profile</th></tr>{projects_html}</table>

<h2>Recent Jobs</h2>
<table>
<tr><th>Job ID</th><th>Type</th><th>Status</th><th>Started</th></tr>
{jobs_html if jobs_html else '<tr><td colspan="4" class="empty">No jobs yet</td></tr>'}
</table>

<h2>Servers</h2>
<table>
<tr><th>ID</th><th>Name</th><th>Status</th><th>Flavor</th><th>Zone</th></tr>
{servers_html if servers_html else '<tr><td colspan="5" class="empty">No servers running</td></tr>'}
</table>

<div class="footer">
<p>Larrot · {total_jobs} total jobs · {running_jobs} running ·
<a href="/console">console</a> · <a href="https://github.com/larbi-ishak/Larrot">GitHub</a> · Apache 2.0</p>
</div>
</body></html>"""
