"""Cloud-console-style UI: sidebar, service tree, resource list, detail views, dependency graph."""

import base64
import json as _json

_logo = base64.b64encode(open(
    __file__.replace("console.py", "static/logo-64.png"), "rb").read()).decode()
LOGO = f"data:image/png;base64,{_logo}"

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
    tree_html = ""
    for cat, svcs in SERVICES.items():
        items = "".join(
            f'<a class="nav-item" data-svc="{s}" onclick="filterService(\'{s}\')">'
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
    --blue: #2563eb; --blue-bg: #eff6ff;
  }}
  * {{ margin: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", sans-serif; background: var(--bg); color: var(--text);
          font-size: 14px; display: flex; min-height: 100vh; }}

  /* ===== sidebar ===== */
  .sidebar {{ width: 230px; background: var(--sidebar-bg); color: var(--sidebar-text);
              display: flex; flex-direction: column; position: fixed; top: 0; bottom: 0;
              left: 0; overflow-y: auto; z-index: 100; }}
  .sidebar-header {{ padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,.08);
                     display: flex; align-items: center; gap: 10px; }}
  .sidebar-header img {{ width: 30px; height: 30px; }}
  .sidebar-header .name {{ color: #fff; font-size: 16px; font-weight: 700; }}
  .sidebar-header .sub {{ font-size: 10px; color: var(--sidebar-text); }}
  .sidebar-nav {{ padding: 6px 0; flex: 1; }}
  .nav-group {{ margin-bottom: 2px; }}
  .nav-cat {{ padding: 10px 16px 3px; font-size: 10px; text-transform: uppercase;
              letter-spacing: 1px; color: var(--text-faint); font-weight: 600; }}
  .nav-item {{ display: flex; align-items: center; gap: 8px; padding: 6px 16px;
              color: var(--sidebar-text); text-decoration: none; font-size: 12.5px;
              cursor: pointer; transition: all .1s; border-left: 3px solid transparent; }}
  .nav-item:hover {{ background: var(--sidebar-hover); color: var(--sidebar-text-hi); }}
  .nav-item.active {{ background: var(--sidebar-hover); color: #fff;
                      border-left-color: var(--sidebar-active); }}
  .nav-dot {{ width: 5px; height: 5px; border-radius: 50%; background: #3a3f4f; flex-shrink: 0; }}
  .nav-item:hover .nav-dot, .nav-item.active .nav-dot {{ background: var(--sidebar-active); }}
  .sidebar-footer {{ padding: 10px 16px; border-top: 1px solid rgba(255,255,255,.08);
                    font-size: 11px; }}
  .sidebar-footer a {{ color: var(--sidebar-text); text-decoration: none; }}
  .sidebar-footer a:hover {{ color: #fff; }}

  /* ===== main ===== */
  .main {{ flex: 1; margin-left: 230px; display: flex; flex-direction: column; }}
  .topbar {{ background: #fff; border-bottom: 1px solid var(--card-border);
             padding: 0 24px; height: 48px; display: flex; align-items: center;
             gap: 12px; position: sticky; top: 0; z-index: 50; }}
  .topbar .crumb {{ display: flex; align-items: center; gap: 6px; font-size: 13px; }}
  .topbar .crumb a {{ color: var(--blue); text-decoration: none; cursor: pointer; }}
  .topbar .crumb a:hover {{ text-decoration: underline; }}
  .topbar .crumb .sep {{ color: var(--text-faint); }}
  .topbar .crumb .current {{ color: var(--text); font-weight: 500; }}
  .topbar .spacer {{ flex: 1; }}
  .topbar .region {{ background: var(--accent-bg); color: var(--accent);
                     padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .topbar a {{ color: var(--text-dim); text-decoration: none; font-size: 12px;
               padding: 5px 8px; border-radius: 4px; }}
  .topbar a:hover {{ background: var(--bg); color: var(--text); }}
  .topbar a.active {{ color: var(--accent); background: var(--accent-bg); }}

  .content {{ padding: 20px 24px; flex: 1; }}

  /* ===== stats ===== */
  .stats-row {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border);
               border-radius: 8px; padding: 12px 16px; min-width: 120px;
               box-shadow: var(--card-shadow); }}
  .stat-card .num {{ font-size: 24px; font-weight: 700; }}
  .stat-card .label {{ color: var(--text-dim); font-size: 11px; margin-top: 1px; }}
  .stat-card.alert .num {{ color: var(--warn); }}

  /* ===== panels ===== */
  .panel {{ background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 8px; margin-bottom: 16px; box-shadow: var(--card-shadow);
            overflow: hidden; }}
  .panel-header {{ padding: 12px 18px; border-bottom: 1px solid var(--card-border);
                   display: flex; align-items: center; gap: 10px; }}
  .panel-header h2 {{ font-size: 14px; font-weight: 600; }}
  .panel-header .badge {{ background: var(--accent-bg); color: var(--accent);
                          padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
  .panel-header .spacer {{ flex: 1; }}
  .panel-header input, .panel-header select {{
      border: 1px solid var(--card-border); border-radius: 6px; padding: 6px 10px;
      font: inherit; font-size: 12px; background: var(--bg); }}
  .panel-header input:focus {{ outline: none; border-color: var(--accent); }}

  /* ===== table ===== */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 8px 18px; color: var(--text-dim); font-weight: 500;
       font-size: 11px; border-bottom: 1px solid var(--card-border);
       text-transform: uppercase; letter-spacing: .3px; }}
  td {{ padding: 8px 18px; border-bottom: 1px solid var(--card-border); font-size: 13px; }}
  tr:hover td {{ background: #fafbfc; }}
  td code {{ color: var(--blue); font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
  .res-link {{ color: var(--blue); cursor: pointer; text-decoration: none; }}
  .res-link:hover {{ text-decoration: underline; }}

  /* ===== status badges ===== */
  .st {{ display: inline-flex; align-items: center; gap: 5px;
          padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
  .st::before {{ content: ''; width: 6px; height: 6px; border-radius: 50%; }}
  .st-ok {{ background: var(--ok-bg); color: var(--ok); }} .st-ok::before {{ background: var(--ok); }}
  .st-warn {{ background: var(--warn-bg); color: var(--warn); }} .st-warn::before {{ background: var(--warn); }}
  .st-err {{ background: var(--err-bg); color: var(--err); }} .st-err::before {{ background: var(--err); }}
  .st-mut {{ background: var(--bg); color: var(--text-faint); }} .st-mut::before {{ background: var(--text-faint); }}

  /* ===== buttons ===== */
  .btn {{ display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px;
          border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer;
          border: 1px solid var(--card-border); background: #fff; color: var(--text); }}
  .btn:hover {{ border-color: var(--text-dim); }}
  .btn-primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .btn-primary:hover {{ background: #c50010; }}
  .btn-danger {{ color: var(--err); border-color: var(--err); }}
  .btn-danger:hover {{ background: var(--err-bg); }}
  .btn-sm {{ padding: 3px 10px; font-size: 11px; }}

  /* ===== detail view ===== */
  .detail {{ display: none; }}
  .detail.visible {{ display: block; }}
  .detail-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
  .detail-header .icon {{ width: 40px; height: 40px; border-radius: 8px;
                           display: flex; align-items: center; justify-content: center;
                           font-size: 18px; background: var(--blue-bg); color: var(--blue); }}
  .detail-header h2 {{ font-size: 18px; font-weight: 600; }}
  .detail-header .sub {{ color: var(--text-dim); font-size: 13px; }}
  .detail-header .spacer {{ flex: 1; }}
  .kv-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
               gap: 1px; background: var(--card-border); border-radius: 8px; overflow: hidden;
               margin-bottom: 16px; }}
  .kv {{ background: var(--card-bg); padding: 12px 16px; }}
  .kv .k {{ color: var(--text-dim); font-size: 11px; text-transform: uppercase;
             letter-spacing: .3px; margin-bottom: 3px; }}
  .kv .v {{ font-size: 13px; word-break: break-all; }}
  .kv .v code {{ color: var(--blue); font-family: ui-monospace, Menlo, monospace; }}

  /* ===== dependency graph ===== */
  .dep-list {{ display: flex; flex-direction: column; gap: 6px; padding: 14px 18px; }}
  .dep-item {{ display: flex; align-items: center; gap: 10px; padding: 8px 12px;
               background: var(--bg); border: 1px solid var(--card-border);
               border-radius: 6px; }}
  .dep-item .rel {{ color: var(--text-dim); font-size: 11px; min-width: 140px; }}
  .dep-item .res-link {{ font-size: 13px; }}

  /* ===== chaos ===== */
  .chaos-bar {{ display: flex; gap: 6px; padding: 10px 18px; flex-wrap: wrap;
               align-items: center; border-bottom: 1px solid var(--card-border); }}
  .chaos-bar label {{ font-size: 11px; color: var(--text-dim); font-weight: 500; }}
  .chaos-bar input, .chaos-bar select {{ border: 1px solid var(--card-border);
      border-radius: 6px; padding: 5px 8px; font: inherit; font-size: 12px; }}
  .chaos-bar input {{ width: 70px; }}

  /* ===== catalog ===== */
  .catalog-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                   gap: 8px; padding: 12px 18px; }}
  .catalog-item {{ display: flex; align-items: center; gap: 6px; padding: 8px 12px;
                   background: var(--bg); border: 1px solid var(--card-border);
                   border-radius: 6px; font-size: 12px; cursor: pointer; }}
  .catalog-item:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
  .catalog-item .dot {{ width: 6px; height: 6px; border-radius: 50%;
                        background: var(--ok); flex-shrink: 0; }}
  .catalog-item .cat {{ color: var(--text-faint); font-size: 10px; margin-left: auto; }}

  .empty {{ text-align: center; padding: 32px; color: var(--text-faint); }}
  .empty .icon {{ font-size: 24px; display: block; margin-bottom: 4px; }}

  /* ===== toast ===== */
  .toast {{ position: fixed; bottom: 24px; right: 24px; background: #26282c; color: #fff;
            padding: 12px 20px; border-radius: 8px; font-size: 13px; z-index: 200;
            display: none; box-shadow: 0 4px 12px rgba(0,0,0,.2); }}
  .toast.show {{ display: block; animation: fadeIn .2s; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; }} }}

  @media (max-width: 1024px) {{ .sidebar {{ display: none; }} .main {{ margin-left: 0; }} }}
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
    <a class="nav-item active" onclick="showOverview()">
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
    <div class="crumb" id="crumb">
      <a onclick="showOverview()">Console</a>
      <span class="sep">/</span>
      <span class="current">Overview</span>
    </div>
    <span class="spacer"></span>
    <span class="region">ap-southeast-1</span>
    <a href="/">Dashboard</a>
    <a href="/console" class="active">Console</a>
    <a href="/docs">API</a>
    <a href="https://larbi-ishak.github.io/Larrot/" target="_blank">Docs</a>
  </div>

  <div class="content">

    <!-- ===== OVERVIEW VIEW ===== -->
    <div id="view-overview">
      <div class="stats-row" id="stats"></div>

      <div class="panel">
        <div class="panel-header">
          <h2>Resources</h2>
          <span class="badge" id="res-count"></span>
          <span class="spacer"></span>
          <input id="f-name" placeholder="Search..." oninput="refresh()">
          <select id="f-type" onchange="refresh()"><option value="">All types</option></select>
        </div>
        <table>
          <thead><tr><th>Type</th><th>Name</th><th>ID</th><th>Status</th><th></th></tr></thead>
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

    <!-- ===== DETAIL VIEW ===== -->
    <div id="view-detail" class="detail">
      <div class="detail-header">
        <div class="icon" id="d-icon">&#9729;</div>
        <div>
          <h2 id="d-name">-</h2>
          <div class="sub" id="d-sub">-</div>
        </div>
        <span class="spacer"></span>
        <button class="btn" onclick="showOverview()">&#8592; Back to list</button>
      </div>

      <div class="panel">
        <div class="panel-header"><h2>Properties</h2></div>
        <div class="kv-grid" id="d-props"></div>
      </div>

      <div class="panel" id="d-deps-panel">
        <div class="panel-header"><h2>Dependencies</h2><span class="badge" id="d-dep-count"></span></div>
        <div class="dep-list" id="d-deps"></div>
      </div>
    </div>

  </div>
</main>

<div class="toast" id="toast"></div>

<script>
const $ = (id) => document.getElementById(id);
const TYPE_ICONS = {{
  'ecs.server': '&#128421;', 'evs.volume': '&#128190;', 'vpc.vpc': '&#127760;',
  'vpc.subnet': '&#127760;', 'vpc.eip': '&#127760;', 'vpc.port': '&#128268;',
  'evs.snapshot': '&#128247;', 'ims.image': '&#128444;', 'cbr.vault': '&#128230;',
  'obs.bucket': '&#129513;', 'rds.instance': '&#128451;', 'cce.cluster': '&#9879;',
}};

const statusPill = (s) => {{
  if (!s) return '<span class="st st-mut">-</span>';
  const cls = /^(ACTIVE|available|SUCCESS|RUNNING|OK|ready|INSERVICE|running|Ready)$/i.test(s) ? 'st-ok'
    : /^(BUILD|CREATING|creating|RUNNING|attaching|pending|processing|STARTING|deploying)$/i.test(s) ? 'st-warn'
    : /^(FAIL|ERROR|SHUTOFF|deleted|STOPPING)$/i.test(s) ? 'st-err' : 'st-mut';
  return `<span class="st ${{cls}}">${{s}}</span>`;
}};

function toast(msg) {{
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}

// ===== navigation =====
function showOverview() {{
  $('view-overview').style.display = 'block';
  $('view-detail').classList.remove('visible');
  $('crumb').innerHTML = '<a onclick="showOverview()">Console</a><span class="sep">/</span><span class="current">Overview</span>';
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector('.nav-item').classList.add('active');
  refresh();
}}

function filterService(svc) {{
  $('f-name').value = svc;
  showOverview();
  $('crumb').innerHTML = `<a onclick="showOverview()">Console</a><span class="sep">/</span><span class="current">${{svc}}</span>`;
  document.querySelectorAll('.nav-item').forEach(n => {{
    n.classList.toggle('active', n.dataset.svc === svc);
  }});
  refresh();
}}

async function showDetail(rid) {{
  try {{
    const [detailRes, graphRes] = await Promise.all([
      fetch(`/admin/resources/${{rid}}`).then(r => r.json()),
      fetch(`/admin/graph/${{rid}}`).then(r => r.json()),
    ]);
    if (detailRes.error) {{ toast('Resource not found'); return; }}

    const raw = detailRes._raw || {{}};
    const name = detailRes.name || raw.name || rid;
    const type = detailRes.type || 'unknown';

    // Show detail view
    $('view-overview').style.display = 'none';
    $('view-detail').classList.add('visible');

    // Header
    $('d-icon').innerHTML = TYPE_ICONS[type] || '&#9729;';
    $('d-name').textContent = name;
    $('d-sub').textContent = `${{type}} · ${{rid}}`;

    // Breadcrumb
    $('crumb').innerHTML = `<a onclick="showOverview()">Console</a><span class="sep">/</span><span class="current">${{name}}</span>`;

    // Properties: show all keys from the raw object
    const skip = new Set(['_raw']);
    let html = '';
    const entries = Object.entries(raw).filter(([k]) => !skip.has(k));
    for (const [k, v] of entries) {{
      let val;
      if (v === null || v === undefined) val = '<span style="color:var(--text-faint)">-</span>';
      else if (typeof v === 'object') val = `<code>${{JSON.stringify(v).slice(0, 120)}}</code>`;
      else val = `<code>${{String(v).slice(0, 200)}}</code>`;
      html += `<div class="kv"><div class="k">${{k}}</div><div class="v">${{val}}</div></div>`;
    }}
    $('d-props').innerHTML = html || '<div class="empty">No properties</div>';

    // Dependencies
    const edges = graphRes.edges || [];
    $('d-dep-count').textContent = `${{edges.length}} linked`;
    if (edges.length > 0) {{
      $('d-deps').innerHTML = edges.map(e =>
        `<div class="dep-item">
           <span class="rel">${{e.relation}}</span>
           <a class="res-link" onclick="showDetail('${{e.id}}')">${{e.type}}: ${{e.id.slice(0, 12)}}…</a>
         </div>`).join('');
      $('d-deps-panel').style.display = 'block';
    }} else {{
      $('d-deps-panel').style.display = 'none';
    }}

    toast(`Opened ${{type}}: ${{name}}`);
  }} catch (e) {{
    console.error(e);
    toast('Failed to load resource');
  }}
}}

// ===== data loading =====
async function refresh() {{
  try {{
    const [res, chaos, metrics] = await Promise.all([
      fetch(`/admin/resources?type=${{$('f-type').value}}&name=${{$('f-name').value}}`),
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
    ['Jobs Running', m.jobs_running],
  ];
  $('stats').innerHTML = items.map(([k, v]) =>
    `<div class="stat-card${{k === 'Jobs Running' && v > 0 ? ' alert' : ''}}">
       <div class="num">${{v ?? 0}}</div><div class="label">${{k}}</div></div>`).join('');
}}

function renderResources(res) {{
  $('res-count').textContent = `${{res.total}} total`;
  const rows = (res.resources || []).slice(0, 500).map(r => {{
    const icon = TYPE_ICONS[r.type] || '&#9729;';
    return `<tr>
      <td>${{icon}} ${{r.type}}</td>
      <td><a class="res-link" onclick="showDetail('${{r.id}}')">${{r.name || r.id.slice(0, 12)}}</a></td>
      <td><code>${{(r.id||'').slice(0, 18)}}</code></td>
      <td>${{statusPill(r.status)}}</td>
      <td><button class="btn btn-sm" onclick="showDetail('${{r.id}}')">Details</button></td>
    </tr>`;
  }}).join('');
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
    <td><button class="btn btn-danger btn-sm" onclick="delRule('${{r.rule_id}}')">Remove</button></td>
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

async function addRule() {{
  await fetch('/admin/chaos', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ service: $('c-svc').value, mode: $('c-mode').value,
      failure_rate: parseFloat($('c-rate').value), status: parseInt($('c-status').value),
      error_code: 'SIM.CHAOS', error_msg: 'injected from console' }}) }});
  toast('Chaos rule injected');
  refresh();
}}
async function delRule(id) {{
  await fetch(`/admin/chaos/${{id}}`, {{ method: 'DELETE' }});
  toast('Rule removed');
  refresh();
}}
async function resetRules() {{
  await fetch('/admin/chaos/reset', {{ method: 'POST' }});
  toast('All chaos rules reset');
  refresh();
}}

refresh();
renderCatalog();
setInterval(refresh, 5000);
</script>
</body></html>"""
