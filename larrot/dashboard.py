"""Dashboard: overview page with resource stats and recent jobs."""

from .ui import LOGO, SHARED_CSS, navbar


def dashboard_html(state) -> str:
    """Overview dashboard with stats cards and recent jobs."""
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
    for attr, name in [("rds_instances", "RDS"), ("dns_zones", "DNS"),
                       ("kms_keys", "KMS"), ("elb_loadbalancers", "ELB"),
                       ("sfs_shares", "SFS"), ("cce_clusters", "CCE"),
                       ("fg_functions", "Functions")]:
        resources[name] = len(getattr(state, attr, {}))

    running = sum(1 for j in state.jobs.jobs.values() if j.status == "RUNNING")
    total_jobs = len(state.jobs.jobs)
    recent = sorted(state.jobs.jobs.values(), key=lambda j: j.begin_time, reverse=True)[:10]

    jobs_html = ""
    for j in recent:
        cls = "st-ok" if j.status == "SUCCESS" else ("st-warn" if j.status == "RUNNING" else "st-err")
        jobs_html += (
            f'<tr><td><code>{j.job_id[:12]}…</code></td>'
            f'<td>{j.job_type}</td>'
            f'<td><span class="st {cls}">{j.status}</span></td>'
            f'<td>{j.begin_time}</td></tr>')

    cards = ""
    for k, v in sorted(resources.items(), key=lambda x: -x[1]):
        cards += f'<div class="stat-card"><div class="num">{v}</div><div class="label">{k}</div></div>'

    empty_jobs = '<tr><td colspan="4" class="empty">No jobs yet</td></tr>' if not jobs_html else jobs_html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Larrot Dashboard</title>
<link rel="icon" href="{LOGO}">
<style>
{SHARED_CSS}
  .hero {{ text-align: center; padding: 24px 0 16px; }}
  .hero h1 {{ font-size: 24px; font-weight: 700; }}
  .hero p {{ color: var(--text-dim); margin-top: 4px; font-size: 14px; }}
  .hero .accent {{ color: var(--accent); }}
  .stats-row {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
                gap: 12px; margin-bottom: 20px; }}
  .stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border);
               border-radius: 8px; padding: 12px 16px; box-shadow: var(--card-shadow); }}
  .stat-card .num {{ font-size: 24px; font-weight: 700; }}
  .stat-card .label {{ color: var(--text-dim); font-size: 11px; margin-top: 1px;
                       text-transform: uppercase; letter-spacing: .3px; }}
  .content {{ padding: 20px 24px; max-width: 1280px; margin: 0 auto; }}
  .jobs-bar {{ display: flex; gap: 12px; padding: 12px 18px;
               border-bottom: 1px solid var(--card-border); }}
  .jobs-bar .item {{ color: var(--text-dim); font-size: 13px; }}
  .jobs-bar .item b {{ color: var(--text); font-size: 16px; margin-right: 4px; }}
  .jobs-bar .item.alert b {{ color: var(--warn); }}
</style>
</head>
<body>
{navbar("dashboard")}
<div class="main-no-sidebar">
  <div class="content">
    <div class="hero">
      <h1>Larrot 🦜 <span class="accent">repeats</span> Huawei Cloud</h1>
      <p>59 services &middot; 720 documented operations &middot; running locally</p>
    </div>
    <div class="stats-row">{cards}</div>
    <div class="panel">
      <div class="panel-header"><h2>Recent Jobs</h2>
        <span class="badge">{total_jobs} total</span></div>
      <div class="jobs-bar">
        <span class="item"><b>{total_jobs}</b>total</span>
        <span class="item alert"><b>{running}</b>running</span>
      </div>
      <table>
        <thead><tr><th>Job ID</th><th>Type</th><th>Status</th><th>Started</th></tr></thead>
        <tbody>{empty_jobs}</tbody>
      </table>
    </div>
  </div>
</div>
</body></html>"""
