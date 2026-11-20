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
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M20 44a12 12 0 1 1 2.4-23.7A16 16 0 0 1 52 26a10 10 0 0 1-2 19.7H20z" fill="var(--accent)"/>
      <circle cx="26" cy="30" r="3" fill="#fff" opacity=".9"/>
      <circle cx="36" cy="28" r="2.5" fill="#fff" opacity=".7"/>
      <circle cx="44" cy="32" r="2" fill="#fff" opacity=".5"/>
    </svg>
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
  Larrot &middot; repeats Huawei Cloud &middot;
  <a href="/console">console</a> &middot;
  <a href="https://github.com/larbi-ishak/Larrot">GitHub</a> &middot; Apache 2.0 &middot;
  not affiliated with Huawei Technologies
</footer>
</body></html>"""
