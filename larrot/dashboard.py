"""Enhanced web dashboard with real-time updates and resource browsing."""

FAVICON = """data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cpath d='M20 44a12 12 0 1 1 2.4-23.7A16 16 0 0 1 52 26a10 10 0 0 1-2 19.7H20z' fill='%23e60012'/%3E%3C/svg%3E"""


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
        f'<tr><td><code>{j.job_id[:12]}…</code></td><td>{j.job_type}</td>'
        f'<td><span class="pill {"ok" if j.status == "SUCCESS" else "warn" if j.status == "RUNNING" else "err"}">{j.status}</span></td>'
        f'<td>{j.begin_time}</td></tr>'
        for j in recent_jobs
    )

    # Resource cards
    cards = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="label">{k}</div></div>'
        for k, v in sorted(resources.items(), key=lambda x: -x[1])
    )

    total = len(state.servers)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="5">
<title>Larrot dashboard</title>
<link rel="icon" href="{FAVICON}">
<style>
  :root {{
    color-scheme: dark;
    --bg: #0a0e14; --surface: #111721; --surface2: #1a2230;
    --border: #1e2a3a; --text: #c8d3e0; --text-dim: #6b7a8d; --text-faint: #3a4a5f;
    --accent: #e60012; --blue: #58a6ff;
    --ok: #3fb950; --warn: #d29922; --err: #f85149;
  }}
  * {{ margin: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: var(--bg); color: var(--text); font-size: 14px; }}

  header {{ background: linear-gradient(180deg, var(--surface), var(--bg));
            border-bottom: 1px solid var(--border); padding: 0 24px; height: 56px;
            display: flex; align-items: center; gap: 16px; }}
  .logo {{ display: flex; align-items: center; gap: 10px; }}
  .logo svg {{ width: 28px; height: 28px; }}
  .logo .name {{ font-size: 18px; font-weight: 700;
                 background: linear-gradient(135deg, #ff4757, #e60012);
                 -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .logo .tag {{ font-size: 11px; color: var(--text-dim); margin-left: -6px; }}
  header .spacer {{ flex: 1; }}
  header nav {{ display: flex; gap: 4px; }}
  header nav a {{ color: var(--text-dim); text-decoration: none; padding: 6px 12px;
                  border-radius: 6px; font-size: 13px; }}
  header nav a:hover {{ color: var(--text); background: var(--surface2); }}
  header nav a.active {{ color: var(--accent); background: rgba(230,0,18,.1); }}

  .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}

  .hero {{ text-align: center; padding: 32px 0 24px; }}
  .hero h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -1px; }}
  .hero p {{ color: var(--text-dim); margin-top: 6px; font-size: 15px; }}
  .hero .accent {{ color: var(--accent); }}

  .stats {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 12px; margin-bottom: 24px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border);
           border-radius: 10px; padding: 14px 16px; position: relative; overflow: hidden; }}
  .card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
                   background: linear-gradient(90deg, var(--accent), transparent); opacity: .5; }}
  .card .num {{ font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .card .label {{ color: var(--text-dim); font-size: 11px; text-transform: uppercase;
                   letter-spacing: .5px; margin-top: 2px; }}

  .panel {{ background: var(--surface); border: 1px solid var(--border);
            border-radius: 10px; margin-bottom: 20px; overflow: hidden; }}
  .panel h2 {{ padding: 12px 18px; font-size: 13px; font-weight: 600; color: var(--text-dim);
               border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: .5px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 8px 18px; color: var(--text-dim); font-weight: 500;
       font-size: 11px; text-transform: uppercase; letter-spacing: .5px;
       border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px 18px; border-bottom: 1px solid var(--border); font-size: 13px; }}
  td code {{ color: var(--blue); font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
  .pill {{ padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
  .ok {{ background: #12261a; color: var(--ok); }}
  .warn {{ background: #2a2208; color: var(--warn); }}
  .err {{ background: #2a0f0f; color: var(--err); }}

  .jobs-bar {{ display: flex; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--border); }}
  .jobs-bar .item {{ color: var(--text-dim); font-size: 13px; }}
  .jobs-bar .item b {{ color: var(--text); font-size: 16px; margin-right: 4px; }}
  .jobs-bar .item.alert b {{ color: var(--warn); }}

  footer {{ text-align: center; padding: 20px; color: var(--text-faint); font-size: 12px;
            border-top: 1px solid var(--border); margin-top: 20px; }}
  footer a {{ color: var(--text-dim); text-decoration: none; }}
  footer a:hover {{ color: var(--accent); }}

  @media (max-width: 768px) {{
    .wrap {{ padding: 12px; }}
    header {{ padding: 0 12px; }}
    header nav {{ display: none; }}
    .hero h1 {{ font-size: 22px; }}
  }}
</style>
</head>
<body>
<header>
  <div class="logo">
    <img src="data:image/png;base64,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" alt="Larrot" style="width:32px;height:32px;filter:drop-shadow(0 0 6px rgba(230,0,18,.3))">
    <span class="name">Larrot</span>
    <span class="tag">dashboard</span>
  </div>
  <span class="spacer"></span>
  <nav>
    <a href="/" class="active">dashboard</a>
    <a href="/console">console</a>
    <a href="/docs">API docs</a>
    <a href="https://larbi-ishak.github.io/Larrot/" target="_blank">docs site</a>
    <a href="https://github.com/larbi-ishak/Larrot" target="_blank">GitHub</a>
  </nav>
</header>

<div class="wrap">
  <div class="hero">
    <h1>Larrot <span class="accent">repeats</span> Huawei Cloud</h1>
    <p>59 services &middot; 720 documented operations &middot; running locally</p>
  </div>

  <div class="stats">{cards}</div>

  <div class="panel">
    <h2>recent jobs</h2>
    <div class="jobs-bar">
      <span class="item"><b>{total_jobs}</b>total</span>
      <span class="item alert"><b>{running_jobs}</b>running</span>
    </div>
    <table>
      <thead><tr><th>job id</th><th>type</th><th>status</th><th>started</th></tr></thead>
      <tbody>{jobs_html if jobs_html else '<tr><td colspan="4" style="text-align:center;color:var(--text-faint);padding:24px">no jobs yet</td></tr>'}</tbody>
    </table>
  </div>
</div>

<footer>
  Larrot &middot; local Huawei Cloud API simulator &middot;
  <a href="/console">console</a> &middot;
  <a href="https://github.com/larbi-ishak/Larrot">GitHub</a> &middot; Apache 2.0 &middot;
  not affiliated with Huawei Technologies
</footer>
</body></html>"""
