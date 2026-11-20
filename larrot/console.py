"""Web console: cloud-console-style UI with sidebar, service tree, resource panels."""

import base64

# Compact logo as base64 data URI
_logo = base64.b64encode(open(
    __file__.replace("console.py", "static/logo-64.png"), "rb").read()).decode()
LOGO = f"data:image/png;base64,{_logo}"

# Service tree data: category -> services
SERVICES = {
    "Compute": ["ECS", "BMS", "AS", "IMS", "CCE", "CCI", "FunctionGraph", "HPC"],
    "Storage": ["EVS", "OBS", "SFS", "CBR"],
    "Network": ["VPC", "EIP", "ELB", "NAT", "DNS", "VPN", "DC", "ER", "Peering", "ACL", "Routes"],
    "Database": ["RDS", "GaussDB", "GeminiDB", "DDS", "DCS", "DMS", "DDM", "DBSS"],
    "Security": ["IAM", "KMS", "WAF", "Anti-DDoS", "HSS", "CFW", "DSC"],
    "Management": ["CES", "LTS", "AOM", "TMS", "EPS", "BSS", "SMN"],
    "Big Data": ["DWS", "CSS", "MRS", "DLI", "DIS", "DataArts"],
    "AI & ML": ["ModelArts", "MaaS"],
    "App Services": ["APIG", "SWR", "ServiceStage", "CSE", "CodeArts"],
    "Edge & Media": ["CDN", "IEF", "VOD", "IoTDA"],
    "Migration": ["SMS", "OMS", "DES"],
}


def console_html(state) -> str:
    # Build sidebar tree HTML
    tree_html = ""
    for cat, svcs in SERVICES.items():
        items = "".join(
            f'<a class="nav-item" data-svc="{s.lower().replace(" ", "")}" '
            f'onclick="filterService(\'{s}\')">'
            f'<span class="nav-dot"></span>{s}</a>'
            for s in svcs)
        tree_html += f'<div class="nav-group"><div class="nav-cat">{cat}</div>{items}</div>'

    total_svcs = sum(len(v) for v in SERVICES.values())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Larrot Console</title>
<link rel="icon" href="{LOGO}">
<style>
  :root {{
    --bg: #f5f6f8; --sidebar-bg: #1a1d27; --sidebar-hover: #252a38;
    --sidebar-active: #e60012; --sidebar-text: #8b949e; --sidebar-text-hi: #fff;
    --card-bg: #fff; --card-border: #e3e6ea; --card-shadow: 0 1px 3px rgba(0,0,0,.06);
    --text: #26282c; --text-dim: #6b7280; --text-faint: #9ca3af;
    --accent: #e60012; --accent-bg: #fef0f0;
    --ok: #16a34a; --ok-bg: #f0fdf4;
    --warn: #d97706; --warn-bg: #fffbeb;
    --err: #dc2626; --err-bg: #fef2f2;
    --blue: #2563eb;
  }}
  * {{ margin: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", sans-serif; background: var(--bg); color: var(--text);
          font-size: 14px; display: flex; min-height: 100vh; }}

  /* ===== sidebar ===== */
  .sidebar {{ width: 240px; background: var(--sidebar-bg); color: var(--sidebar-text);
              display: flex; flex-direction: column; position: fixed; top: 0; bottom: 0;
              left: 0; overflow-y: auto; z-index: 100; }}
  .sidebar-header {{ padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,.08);
                     display: flex; align-items: center; gap: 10px; }}
  .sidebar-header img {{ width: 32px; height: 32px; }}
  .sidebar-header .name {{ color: #fff; font-size: 17px; font-weight: 700; }}
  .sidebar-header .sub {{ font-size: 10px; color: var(--sidebar-text); }}
  .sidebar-nav {{ padding: 8px 0; flex: 1; }}
  .nav-cat {{ padding: 12px 20px 4px; font-size: 10px; text-transform: uppercase;
              letter-spacing: 1px; color: var(--text-faint); font-weight: 600; }}
  .nav-item {{ display: flex; align-items: center; gap: 8px; padding: 7px 20px;
              color: var(--sidebar-text); text-decoration: none; font-size: 13px;
              cursor: pointer; transition: all .12s; border-left: 3px solid transparent; }}
  .nav-item:hover {{ background: var(--sidebar-hover); color: var(--sidebar-text-hi); }}
  .nav-item.active {{ background: var(--sidebar-hover); color: #fff;
                      border-left-color: var(--sidebar-active); }}
  .nav-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #3a3f4f; flex-shrink: 0; }}
  .nav-item:hover .nav-dot {{ background: var(--sidebar-active); }}
  .sidebar-footer {{ padding: 12px 20px; border-top: 1px solid rgba(255,255,255,.08);
                    font-size: 11px; }}
  .sidebar-footer a {{ color: var(--sidebar-text); text-decoration: none; }}
  .sidebar-footer a:hover {{ color: #fff; }}

  /* ===== main ===== */
  .main {{ flex: 1; margin-left: 240px; display: flex; flex-direction: column; }}
  .topbar {{ background: #fff; border-bottom: 1px solid var(--card-border);
             padding: 0 32px; height: 52px; display: flex; align-items: center;
             gap: 16px; position: sticky; top: 0; z-index: 50; }}
  .topbar h1 {{ font-size: 16px; font-weight: 600; }}
  .topbar .breadcrumb {{ color: var(--text-dim); font-size: 13px; }}
  .topbar .spacer {{ flex: 1; }}
  .topbar .region {{ background: var(--accent-bg); color: var(--accent);
                     padding: 4px 12px; border-radius: 4px; font-size: 12px;
                     font-weight: 600; }}
  .topbar a {{ color: var(--text-dim); text-decoration: none; font-size: 13px;
               padding: 6px 10px; border-radius: 4px; }}
  .topbar a:hover {{ background: var(--bg); color: var(--text); }}
  .topbar a.active {{ color: var(--accent); background: var(--accent-bg); }}

  .content {{ padding: 24px 32px; flex: 1; }}

  /* ===== stats row ===== */
  .stats-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border);
               border-radius: 8px; padding: 16px 20px; min-width: 140px;
               box-shadow: var(--card-shadow); }}
  .stat-card .num {{ font-size: 28px; font-weight: 700; color: var(--text); }}
  .stat-card .label {{ color: var(--text-dim); font-size: 12px; margin-top: 2px; }}
  .stat-card.alert .num {{ color: var(--warn); }}

  /* ===== panels ===== */
  .panel {{ background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 8px; margin-bottom: 20px; box-shadow: var(--card-shadow);
            overflow: hidden; }}
  .panel-header {{ padding: 14px 20px; border-bottom: 1px solid var(--card-border);
                   display: flex; align-items: center; gap: 12px; }}
  .panel-header h2 {{ font-size: 15px; font-weight: 600; }}
  .panel-header .badge {{ background: var(--accent-bg); color: var(--accent);
                          padding: 2px 10px; border-radius: 12px; font-size: 11px;
                          font-weight: 600; }}
  .panel-header .spacer {{ flex: 1; }}
  .panel-header input, .panel-header select {{
      border: 1px solid var(--card-border); border-radius: 6px; padding: 7px 12px;
      font: inherit; font-size: 13px; background: var(--bg); }}
  .panel-header input:focus {{ outline: none; border-color: var(--accent); }}

  /* ===== table ===== */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 10px 20px; color: var(--text-dim); font-weight: 500;
       font-size: 12px; border-bottom: 1px solid var(--card-border);
       text-transform: uppercase; letter-spacing: .3px; }}
  td {{ padding: 10px 20px; border-bottom: 1px solid var(--card-border); font-size: 13px; }}
  tr:hover td {{ background: #fafbfc; }}
  td code {{ color: var(--blue); font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}

  /* ===== status badges ===== */
  .badge-status {{ display: inline-flex; align-items: center; gap: 5px;
                   padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
  .badge-status::before {{ content: ''; width: 6px; height: 6px; border-radius: 50%; }}
  .st-ok {{ background: var(--ok-bg); color: var(--ok); }}
  .st-ok::before {{ background: var(--ok); }}
  .st-warn {{ background: var(--warn-bg); color: var(--warn); }}
  .st-warn::before {{ background: var(--warn); }}
  .st-err {{ background: var(--err-bg); color: var(--err); }}
  .st-err::before {{ background: var(--err); }}
  .st-mut {{ background: var(--bg); color: var(--text-faint); }}
  .st-mut::before {{ background: var(--text-faint); }}

  /* ===== buttons ===== */
  .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px;
          border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;
          border: 1px solid var(--card-border); background: #fff; color: var(--text);
          transition: all .12s; }}
  .btn:hover {{ border-color: var(--text-dim); }}
  .btn-primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .btn-primary:hover {{ background: #c50010; }}
  .btn-danger {{ color: var(--err); border-color: var(--err); }}
  .btn-danger:hover {{ background: var(--err-bg); }}

  /* ===== chaos form ===== */
  .chaos-bar {{ display: flex; gap: 8px; padding: 12px 20px; flex-wrap: wrap;
               align-items: center; border-bottom: 1px solid var(--card-border); }}
  .chaos-bar label {{ font-size: 12px; color: var(--text-dim); font-weight: 500; }}
  .chaos-bar input, .chaos-bar select {{ border: 1px solid var(--card-border);
      border-radius: 6px; padding: 6px 10px; font: inherit; font-size: 13px; }}
  .chaos-bar input {{ width: 80px; }}

  /* ===== empty ===== */
  .empty {{ text-align: center; padding: 40px; color: var(--text-faint); }}
  .empty .icon {{ font-size: 28px; display: block; margin-bottom: 6px; }}

  /* ===== catalog grid ===== */
  .catalog-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                   gap: 10px; padding: 16px 20px; }}
  .catalog-item {{ display: flex; align-items: center; gap: 8px; padding: 10px 14px;
                   background: var(--bg); border: 1px solid var(--card-border);
                   border-radius: 6px; font-size: 13px; cursor: pointer;
                   transition: all .12s; }}
  .catalog-item:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
  .catalog-item .dot {{ width: 7px; height: 7px; border-radius: 50%;
                        background: var(--ok); flex-shrink: 0; }}
  .catalog-item .cat {{ color: var(--text-faint); font-size: 11px; margin-left: auto; }}

  /* ===== responsive ===== */
  @media (max-width: 1024px) {{
    .sidebar {{ display: none; }}
    .main {{ margin-left: 0; }}
    .content {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-header">
    <img src="{LOGO}" alt="Larrot">
    <div>
      <div class="name">Larrot</div>
      <div class="sub">local Huawei Cloud</div>
    </div>
  </div>
  <nav class="sidebar-nav">
    <a class="nav-item active" onclick="showAll()">
      <span class="nav-dot"></span>Overview</a>
    {tree_html}
  </nav>
  <div class="sidebar-footer">
    <a href="/">Dashboard</a> &middot;
    <a href="/docs">API</a> &middot;
    <a href="https://github.com/larbi-ishak/Larrot">GitHub</a>
  </div>
</aside>

<main class="main">
  <div class="topbar">
    <h1>Console</h1>
    <span class="breadcrumb" id="crumb">all resources</span>
    <span class="spacer"></span>
    <span class="region">ap-southeast-1</span>
    <a href="/">Dashboard</a>
    <a href="/console" class="active">Console</a>
    <a href="/docs">API Docs</a>
    <a href="https://larbi-ishak.github.io/Larrot/" target="_blank">Docs</a>
  </div>

  <div class="content">
    <div class="stats-row" id="stats"></div>

    <div class="panel">
      <div class="panel-header">
        <h2>Resources</h2>
        <span class="badge" id="res-count"></span>
        <span class="spacer"></span>
        <input id="f-name" placeholder="Search..." oninput="refresh()">
        <select id="f-type" onchange="refresh()"><option value="">All types</option></select>
        <select id="f-project" onchange="refresh()"><option value="">All projects</option></select>
      </div>
      <table>
        <thead><tr><th>Type</th><th>Name</th><th>ID</th><th>Project</th><th>Status</th></tr></thead>
        <tbody id="res-body"></tbody>
      </table>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2>Service Catalog</h2>
        <span class="badge">{total_svcs} services</span>
      </div>
      <div class="catalog-grid" id="catalog-grid"></div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2>Chaos Rules</h2>
        <span class="badge" id="chaos-count"></span>
      </div>
      <div class="chaos-bar">
        <label>Service</label><input id="c-svc" placeholder="ecs">
        <label>Mode</label><select id="c-mode"><option>api</option><option>job</option></select>
        <label>Rate</label><input id="c-rate" value="1.0">
        <label>Status</label><input id="c-status" value="500">
        <button class="btn btn-primary" onclick="addRule()">Inject</button>
        <button class="btn btn-danger" onclick="resetRules()">Reset All</button>
      </div>
      <table>
        <thead><tr><th>Rule</th><th>Target</th><th>Mode</th><th>Rate</th><th>Error</th><th></th></tr></thead>
        <tbody id="chaos-body"></tbody>
      </table>
    </div>
  </div>
</main>

<script>
const $ = (id) => document.getElementById(id);

const statusPill = (s) => {{
  if (!s) return '<span class="badge-status st-mut">-</span>';
  const cls = /^(ACTIVE|available|SUCCESS|RUNNING|OK|ready|INSERVICE|running|Ready)$/i.test(s) ? 'st-ok'
    : /^(BUILD|CREATING|creating|RUNNING|attaching|pending|processing|STARTING|deploying)$/i.test(s) ? 'st-warn'
    : /^(FAIL|ERROR|SHUTOFF|deleted|STOPPING)$/i.test(s) ? 'st-err' : 'st-mut';
  return `<span class="badge-status ${{cls}}">${{s}}</span>`;
}};

async function refresh() {{
  try {{
    const [res, chaos, metrics] = await Promise.all([
      fetch(`/admin/resources?type=${{$('f-type').value}}&project=${{$('f-project').value}}&name=${{$('f-name').value}}`),
      fetch('/admin/chaos'),
      fetch('/metrics'),
    ].map(p => p.then(r => r.json())));
    renderStats(metrics);
    renderResources(res);
    renderChaos(chaos);
  }} catch (e) {{ console.error(e); }}
}}

function renderStats(m) {{
  const items = [
    ['Servers', m.servers], ['Volumes', m.volumes], ['VPCs', m.vpcs],
    ['EIPs', m.eips], ['OBS Buckets', m.obs_buckets],
    ['Jobs Running', m.jobs_running], ['Jobs Total', m.jobs_total],
  ];
  $('stats').innerHTML = items.map(([k, v]) =>
    `<div class="stat-card${{k === 'Jobs Running' && v > 0 ? ' alert' : ''}}">
       <div class="num">${{v ?? 0}}</div><div class="label">${{k}}</div></div>`).join('');
}}

function renderResources(res) {{
  $('res-count').textContent = `${{res.total}} total`;
  const rows = (res.resources || []).slice(0, 500).map(r => `<tr>
    <td>${{r.type}}</td><td>${{r.name || '-'}}</td>
    <td><code>${{(r.id||'').slice(0,18)}}</code></td>
    <td><code>${{(r.project_id || '-').slice(0, 8)}}</code></td>
    <td>${{statusPill(r.status)}}</td></tr>`).join('');
  $('res-body').innerHTML = rows ||
    '<tr><td colspan="5" class="empty"><span class="icon">&#9729;</span>No resources</td></tr>';
  const sel = $('f-type');
  if (sel.options.length === 1) {{
    [...new Set((res.resources || []).map(r => r.type))].sort().forEach(t => {{
      sel.add(new Option(t, t));
    }});
  }}
}}

function renderChaos(chaos) {{
  const rules = chaos.rules || [];
  $('chaos-count').textContent = `${{rules.length}} active`;
  $('chaos-body').innerHTML = rules.map(r => `<tr>
    <td><code>${{r.rule_id.slice(0, 8)}}</code></td>
    <td>${{r.service}}</td><td>${{r.mode}}</td><td>${{r.failure_rate}}</td>
    <td>${{r.error_code}} / ${{r.status}}</td>
    <td><button class="btn btn-danger" onclick="delRule('${{r.rule_id}}')">Remove</button></td>
  </tr>`).join('') ||
  '<tr><td colspan="6" class="empty"><span class="icon">&#9889;</span>No rules active</td></tr>';
}}

function renderCatalog() {{
  const items = {SERVICES};
  let html = '';
  for (const [cat, svcs] of Object.entries(items)) {{
    for (const s of svcs) {{
      html += `<div class="catalog-item" onclick="filterService('${{s}}')">
        <span class="dot"></span><span>${{s}}</span><span class="cat">${{cat}}</span></div>`;
    }}
  }}
  $('catalog-grid').innerHTML = html;
}}

function filterService(svc) {{
  $('f-name').value = svc;
  $('crumb').textContent = svc;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  refresh();
}}

function showAll() {{
  $('f-name').value = '';
  $('crumb').textContent = 'all resources';
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector('.nav-item').classList.add('active');
  refresh();
}}

async function addRule() {{
  await fetch('/admin/chaos', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ service: $('c-svc').value, mode: $('c-mode').value,
      failure_rate: parseFloat($('c-rate').value), status: parseInt($('c-status').value),
      error_code: 'SIM.CHAOS', error_msg: 'injected from console' }}) }});
  refresh();
}}
async function delRule(id) {{
  await fetch(`/admin/chaos/${{id}}`, {{ method: 'DELETE' }}); refresh();
}}
async function resetRules() {{
  await fetch('/admin/chaos/reset', {{ method: 'POST' }}); refresh();
}}

refresh();
renderCatalog();
setInterval(refresh, 5000);
</script>
</body></html>"""
