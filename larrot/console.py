"""Cloud console: resource browser, detail views, dependency graph, chaos panel."""

from .ui import LOGO, SERVICES, SHARED_CSS, navbar, sidebar


def console_html(state) -> str:
    total_svcs = sum(len(v) for v in SERVICES.values())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Larrot Console</title>
<link rel="icon" href="{LOGO}">
<style>
{SHARED_CSS}
  .content {{ padding: 20px 24px; }}
  .stats-row {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat-card {{ background: var(--card-bg); border: 1px solid var(--card-border);
               border-radius: 8px; padding: 12px 16px; min-width: 120px;
               box-shadow: var(--card-shadow); }}
  .stat-card .num {{ font-size: 24px; font-weight: 700; }}
  .stat-card .label {{ color: var(--text-dim); font-size: 11px; margin-top: 1px; }}
  .stat-card.alert .num {{ color: var(--warn); }}
  .panel-header input, .panel-header select {{
      border: 1px solid var(--card-border); border-radius: 6px; padding: 6px 10px;
      font: inherit; font-size: 12px; background: var(--bg); }}
  .panel-header input:focus {{ outline: none; border-color: var(--accent); }}
  .panel-header .spacer {{ flex: 1; }}
  .res-link {{ color: var(--blue); cursor: pointer; text-decoration: none; }}
  .res-link:hover {{ text-decoration: underline; }}
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
  .dep-list {{ display: flex; flex-direction: column; gap: 6px; padding: 14px 18px; }}
  .dep-item {{ display: flex; align-items: center; gap: 10px; padding: 8px 12px;
               background: var(--bg); border: 1px solid var(--card-border);
               border-radius: 6px; }}
  .dep-item .rel {{ color: var(--text-dim); font-size: 11px; min-width: 140px; }}
  .chaos-bar {{ display: flex; gap: 6px; padding: 10px 18px; flex-wrap: wrap;
               align-items: center; border-bottom: 1px solid var(--card-border); }}
  .chaos-bar label {{ font-size: 11px; color: var(--text-dim); font-weight: 500; }}
  .chaos-bar input, .chaos-bar select {{ border: 1px solid var(--card-border);
      border-radius: 6px; padding: 5px 8px; font: inherit; font-size: 12px; }}
  .chaos-bar input {{ width: 70px; }}
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
  .toast {{ position: fixed; bottom: 24px; right: 24px; background: #26282c; color: #fff;
            padding: 12px 20px; border-radius: 8px; font-size: 13px; z-index: 200;
            display: none; box-shadow: 0 4px 12px rgba(0,0,0,.2); }}
  .toast.show {{ display: block; animation: fadeIn .2s; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; }} }}
</style>
</head>
<body>
{navbar("console")}
{sidebar()}
<div class="main-with-sidebar">
  <div class="content">

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
        <div class="panel-header"><h2>Service Catalog</h2>
          <span class="badge">{total_svcs} services</span></div>
        <div class="catalog-grid" id="catalog-grid"></div>
      </div>
      <div class="panel">
        <div class="panel-header"><h2>Chaos Rules</h2>
          <span class="badge" id="chaos-count"></span></div>
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

    <div id="view-detail" class="detail">
      <div class="detail-header">
        <div class="icon" id="d-icon">&#9729;</div>
        <div><h2 id="d-name">-</h2><div class="sub" id="d-sub">-</div></div>
        <span class="spacer"></span>
        <button class="btn" onclick="showOverview()">&#8592; Back</button>
      </div>
      <div class="panel">
        <div class="panel-header"><h2>Properties</h2></div>
        <div class="kv-grid" id="d-props"></div>
      </div>
      <div class="panel" id="d-deps-panel">
        <div class="panel-header"><h2>Dependencies</h2>
          <span class="badge" id="d-dep-count"></span></div>
        <div class="dep-list" id="d-deps"></div>
      </div>
    </div>

  </div>
</div>
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
  const t = $('toast'); t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}
function showOverview() {{
  $('view-overview').style.display = 'block';
  $('view-detail').classList.remove('visible');
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
    $('view-overview').style.display = 'none';
    $('view-detail').classList.add('visible');
    $('d-icon').innerHTML = TYPE_ICONS[type] || '&#9729;';
    $('d-name').textContent = name;
    $('d-sub').textContent = `${{type}} · ${{rid}}`;
    let html = '';
    for (const [k, v] of Object.entries(raw)) {{
      let val;
      if (v === null || v === undefined) val = '<span style="color:var(--text-faint)">-</span>';
      else if (typeof v === 'object') val = `<code>${{JSON.stringify(v).slice(0, 120)}}</code>`;
      else val = `<code>${{String(v).slice(0, 200)}}</code>`;
      html += `<div class="kv"><div class="k">${{k}}</div><div class="v">${{val}}</div></div>`;
    }}
    $('d-props').innerHTML = html || '<div class="empty">No properties</div>';
    const edges = graphRes.edges || [];
    $('d-dep-count').textContent = `${{edges.length}} linked`;
    if (edges.length > 0) {{
      $('d-deps').innerHTML = edges.map(e =>
        `<div class="dep-item"><span class="rel">${{e.relation}}</span>
         <a class="res-link" onclick="showDetail('${{e.id}}')">${{e.type}}: ${{e.id.slice(0, 12)}}…</a></div>`).join('');
      $('d-deps-panel').style.display = 'block';
    }} else {{ $('d-deps-panel').style.display = 'none'; }}
  }} catch (e) {{ toast('Failed to load resource'); }}
}}
async function refresh() {{
  try {{
    const [res, chaos, metrics] = await Promise.all([
      fetch(`/admin/resources?type=${{$('f-type').value}}&name=${{$('f-name').value}}`),
      fetch('/admin/chaos'), fetch('/metrics'),
    ].map(p => p.then(r => r.json())));
    const items = [
      ['Servers', metrics.servers], ['Volumes', metrics.volumes], ['VPCs', metrics.vpcs],
      ['EIPs', metrics.eips], ['OBS Buckets', metrics.obs_buckets],
      ['Jobs Running', metrics.jobs_running],
    ];
    $('stats').innerHTML = items.map(([k, v]) =>
      `<div class="stat-card${{k === 'Jobs Running' && v > 0 ? ' alert' : ''}}">
         <div class="num">${{v ?? 0}}</div><div class="label">${{k}}</div></div>`).join('');
    $('res-count').textContent = `${{res.total}} total`;
    const rows = (res.resources || []).slice(0, 500).map(r => {{
      const icon = TYPE_ICONS[r.type] || '&#9729;';
      return `<tr><td>${{icon}} ${{r.type}}</td>
        <td><a class="res-link" onclick="showDetail('${{r.id}}')">${{r.name || r.id.slice(0, 12)}}</a></td>
        <td><code>${{(r.id||'').slice(0, 18)}}</code></td>
        <td>${{statusPill(r.status)}}</td>
        <td><button class="btn btn-sm" onclick="showDetail('${{r.id}}')">Details</button></td></tr>`;
    }}).join('');
    $('res-body').innerHTML = rows ||
      '<tr><td colspan="5" class="empty"><span class="icon">&#9729;</span>No resources</td></tr>';
    const sel = $('f-type');
    if (sel.options.length === 1) {{
      [...new Set((res.resources || []).map(r => r.type))].sort().forEach(t => sel.add(new Option(t, t)));
    }}
    const rules = chaos.rules || [];
    $('chaos-count').textContent = `${{rules.length}} active`;
    $('chaos-body').innerHTML = rules.map(r => `<tr>
      <td><code>${{r.rule_id.slice(0, 8)}}</code></td>
      <td>${{r.service}}</td><td>${{r.mode}}</td><td>${{r.failure_rate}}</td>
      <td>${{r.error_code}} / ${{r.status}}</td>
      <td><button class="btn btn-danger btn-sm" onclick="delRule('${{r.rule_id}}')">Remove</button></td>
    </tr>`).join('') ||
    '<tr><td colspan="6" class="empty"><span class="icon">&#9889;</span>No rules active</td></tr>';
  }} catch (e) {{ console.error(e); }}
}}
function renderCatalog() {{
  const items = {SERVICES};
  let html = '';
  for (const [cat, svcs] of Object.entries(items)) {{
    for (const s of svcs) {{
      html += `<div class="catalog-item" onclick="$('f-name').value='${{s}}';refresh()">
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
  toast('Chaos rule injected'); refresh();
}}
async function delRule(id) {{
  await fetch(`/admin/chaos/${{id}}`, {{ method: 'DELETE' }}); toast('Rule removed'); refresh();
}}
async function resetRules() {{
  await fetch('/admin/chaos/reset', {{ method: 'POST' }}); toast('All rules reset'); refresh();
}}
// Read ?q= from URL for sidebar deep links
const params = new URLSearchParams(window.location.search);
const q = params.get('q');
if (q) {{ $('f-name').value = q; }}
refresh();
renderCatalog();
setInterval(refresh, 5000);
</script>
</body></html>"""
