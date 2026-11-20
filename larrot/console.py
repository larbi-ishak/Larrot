"""Web console: live resource browser, chaos panel, job stats (vanilla JS, no deps)."""

# Favicon (red cloud)
FAVICON = """"data:image/png;base64,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"""


def console_html(state) -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Larrot console</title>
<link rel="icon" href="__FAVICON__">
<style>
  :root {
    color-scheme: dark;
    --bg: #0a0e14; --surface: #111721; --surface2: #1a2230;
    --border: #1e2a3a; --border2: #2a3a4f;
    --text: #c8d3e0; --text-dim: #6b7a8d; --text-faint: #3a4a5f;
    --accent: #e60012; --accent-dim: #a0000e;
    --ok: #3fb950; --ok-bg: #12261a;
    --warn: #d29922; --warn-bg: #2a2208;
    --err: #f85149; --err-bg: #2a0f0f;
    --blue: #58a6ff;
  }
  * { box-sizing: border-box; margin: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.5; }

  /* ===== header ===== */
  header { background: linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%);
           border-bottom: 1px solid var(--border); padding: 0 24px; height: 56px;
           display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 10; }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo svg { width: 28px; height: 28px; }
  .logo .name { font-size: 18px; font-weight: 700; letter-spacing: -0.5px;
                background: linear-gradient(135deg, #ff4757, #e60012);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .logo .tag { font-size: 11px; color: var(--text-dim); margin-left: -6px; }
  header .spacer { flex: 1; }
  header nav { display: flex; gap: 4px; }
  header nav a { color: var(--text-dim); text-decoration: none; padding: 6px 12px;
                 border-radius: 6px; font-size: 13px; transition: all .15s; }
  header nav a:hover { color: var(--text); background: var(--surface2); }
  header nav a.active { color: var(--accent); background: rgba(230,0,18,.1); }

  /* ===== layout ===== */
  .wrap { max-width: 1280px; margin: 0 auto; padding: 24px; }

  /* ===== stats bar ===== */
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
           gap: 12px; margin-bottom: 24px; }
  .stat { background: var(--surface); border: 1px solid var(--border);
          border-radius: 10px; padding: 14px 16px; position: relative; overflow: hidden; }
  .stat::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
                   background: linear-gradient(90deg, var(--accent), transparent); opacity: .5; }
  .stat b { display: block; font-size: 26px; font-weight: 700; color: var(--text);
            font-variant-numeric: tabular-nums; }
  .stat span { color: var(--text-dim); font-size: 11px; text-transform: uppercase;
               letter-spacing: .5px; }
  .stat.alert b { color: var(--warn); }

  /* ===== panels ===== */
  .panel { background: var(--surface); border: 1px solid var(--border);
           border-radius: 10px; margin-bottom: 20px; overflow: hidden; }
  .panel > h2 { padding: 12px 18px; font-size: 13px; font-weight: 600;
                color: var(--text-dim); border-bottom: 1px solid var(--border);
                display: flex; align-items: center; gap: 10px;
                text-transform: uppercase; letter-spacing: .5px; }
  .panel > h2 .count { color: var(--accent); font-size: 12px;
                        background: rgba(230,0,18,.15); padding: 2px 8px; border-radius: 10px; }

  /* ===== toolbar ===== */
  .toolbar { padding: 12px 18px; display: flex; gap: 8px; flex-wrap: wrap;
             border-bottom: 1px solid var(--border); align-items: center; }
  .toolbar input[type="text"] { background: var(--bg); border: 1px solid var(--border2);
           color: var(--text); border-radius: 8px; padding: 8px 12px; font: inherit;
           width: 240px; transition: border-color .15s; }
  .toolbar input:focus { outline: none; border-color: var(--accent); }
  .toolbar select { background: var(--bg); border: 1px solid var(--border2);
           color: var(--text); border-radius: 8px; padding: 8px 12px; font: inherit; }
  .toolbar .search-icon { color: var(--text-faint); margin-right: -6px; }

  /* ===== table ===== */
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 8px 18px; color: var(--text-dim); font-weight: 500;
       font-size: 11px; text-transform: uppercase; letter-spacing: .5px;
       border-bottom: 1px solid var(--border); }
  td { padding: 8px 18px; border-bottom: 1px solid var(--border); font-size: 13px; }
  tr:hover td { background: rgba(26,34,48,.5); }
  td code { color: var(--blue); font-family: ui-monospace, "SF Mono", Menlo, monospace;
            font-size: 12px; }

  /* ===== pills ===== */
  .pill { padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
          display: inline-block; }
  .ok { background: var(--ok-bg); color: var(--ok); }
  .warn { background: var(--warn-bg); color: var(--warn); }
  .err { background: var(--err-bg); color: var(--err); }
  .mut { background: var(--surface2); color: var(--text-dim); }

  /* ===== buttons ===== */
  button { background: var(--surface2); color: var(--text); border: 1px solid var(--border2);
           border-radius: 8px; padding: 8px 14px; font: inherit; font-size: 13px;
           cursor: pointer; transition: all .15s; }
  button:hover { background: var(--border2); border-color: var(--text-faint); }
  button.primary { background: var(--accent); color: #fff; border-color: var(--accent);
                   font-weight: 600; }
  button.primary:hover { background: var(--accent-dim); }
  button.danger { color: var(--err); border-color: var(--err); }
  button.danger:hover { background: var(--err-bg); }

  /* ===== chaos form ===== */
  .chaos-form { display: flex; gap: 8px; flex-wrap: wrap; padding: 14px 18px;
                border-bottom: 1px solid var(--border); align-items: center; }
  .chaos-form label { color: var(--text-dim); font-size: 11px; text-transform: uppercase;
                      letter-spacing: .5px; }
  .chaos-form input, .chaos-form select { background: var(--bg);
           border: 1px solid var(--border2); color: var(--text);
           border-radius: 6px; padding: 6px 10px; font: inherit; font-size: 13px; }
  .chaos-form input { width: 80px; }

  /* ===== empty state ===== */
  .empty { text-align: center; color: var(--text-faint); padding: 40px 20px; font-size: 14px; }
  .empty .icon { font-size: 32px; display: block; margin-bottom: 8px; opacity: .5; }


  /* ===== catalog grid ===== */
  .catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                   gap: 8px; padding: 14px 18px; }
  .catalog-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px;
                   background: var(--surface2); border: 1px solid var(--border);
                   border-radius: 8px; font-size: 13px; transition: border-color .15s; }
  .catalog-item:hover { border-color: var(--accent); }
  .catalog-item .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .catalog-item .dot.up { background: var(--ok); box-shadow: 0 0 4px var(--ok); }
  .catalog-item .dot.down { background: var(--text-faint); }
  .catalog-item .name { color: var(--text); font-weight: 500; }
  .catalog-item .cat { color: var(--text-dim); font-size: 11px; margin-left: auto; }

  /* ===== footer ===== */
  footer { text-align: center; padding: 20px; color: var(--text-faint); font-size: 12px;
           border-top: 1px solid var(--border); margin-top: 20px; }
  footer a { color: var(--text-dim); text-decoration: none; }
  footer a:hover { color: var(--accent); }

  /* ===== clock ===== */
  #clock { color: var(--text-faint); font-size: 12px; font-variant-numeric: tabular-nums; }

  /* ===== responsive ===== */
  @media (max-width: 768px) {
    .wrap { padding: 12px; }
    .toolbar input[type="text"] { width: 100%; }
    header { padding: 0 12px; }
    header nav { display: none; }
  }
</style>
</head>
<body>
<header>
  <div class="logo">
    <img src="data:image/png;base64,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" alt="Larrot" style="width:32px;height:32px;filter:drop-shadow(0 0 6px rgba(230,0,18,.3))">
    <span class="name">Larrot</span>
    <span class="tag">console</span>
  </div>
  <span class="spacer"></span>
  <span id="clock"></span>
  <nav>
    <a href="/">dashboard</a>
    <a href="/console" class="active">console</a>
    <a href="/docs">API docs</a>
    <a href="https://larbi-ishak.github.io/Larrot/" target="_blank">docs site</a>
    <a href="https://github.com/larbi-ishak/Larrot" target="_blank">GitHub</a>
  </nav>
</header>

<div class="wrap">
  <div class="stats" id="stats"></div>

  <div class="panel">
    <h2>resources <span class="count" id="res-count"></span></h2>
    <div class="toolbar">
      <span class="search-icon">&#128269;</span>
      <input id="f-name" type="text" placeholder="filter by name or id">
      <select id="f-type"><option value="">all types</option></select>
      <select id="f-project"><option value="">all projects</option></select>
      <button onclick="refresh()">refresh</button>
    </div>
    <table>
      <thead><tr><th>type</th><th>name</th><th>id</th><th>project</th><th>status</th></tr></thead>
      <tbody id="res-body"></tbody>
    </table>
  </div>

  <div class="panel">
    <h2>service catalog <span class="count" id="catalog-count"></span></h2>
    <div class="catalog-grid" id="catalog-grid"></div>
  </div>

  <div class="panel">
    <h2>chaos rules <span class="count" id="chaos-count"></span></h2>
    <div class="chaos-form">
      <label>service</label>
      <input id="c-svc" placeholder="ecs">
      <label>mode</label>
      <select id="c-mode"><option>api</option><option>job</option></select>
      <label>rate</label>
      <input id="c-rate" value="1.0">
      <label>status</label>
      <input id="c-status" value="500">
      <button class="primary" onclick="addRule()">inject</button>
      <button class="danger" onclick="resetRules()">reset all</button>
    </div>
    <table>
      <thead><tr><th>rule</th><th>target</th><th>mode</th><th>rate</th><th>error</th><th></th></tr></thead>
      <tbody id="chaos-body"></tbody>
    </table>
  </div>
</div>

<footer>
  Larrot &middot; local Huawei Cloud API simulator &middot;
  <a href="https://github.com/larbi-ishak/Larrot">GitHub</a> &middot;
  Apache 2.0 &middot; not affiliated with Huawei Technologies
</footer>

<script>
const $ = (id) => document.getElementById(id);
const pill = (s) => {
  if (!s) return '<span class="pill mut">-</span>';
  const cls = /^(ACTIVE|available|SUCCESS|RUNNING|OK|ready|INSERVICE|running|Ready)$/i.test(s) ? 'ok'
    : /^(BUILD|CREATING|creating|RUNNING|attaching|pending|processing|STARTING|deploying)$/i.test(s) ? 'warn'
    : /^(FAIL|ERROR|SHUTOFF|deleted|STOPPING)$/i.test(s) ? 'err' : 'mut';
  return `<span class="pill ${cls}">${s}</span>`;
};

async function refresh() {
  try {
    const [res, chaos, metrics] = await Promise.all([
      fetch(`/admin/resources?type=${$('f-type').value}&project=${$('f-project').value}&name=${$('f-name').value}`),
      fetch('/admin/chaos'),
      fetch('/metrics'),
    ].map(p => p.then(r => r.json())));
    renderStats(metrics);
    renderResources(res);
    renderChaos(chaos);
  } catch (e) { console.error(e); }
}

function renderStats(m) {
  const items = [
    ['servers', m.servers], ['volumes', m.volumes], ['vpcs', m.vpcs],
    ['eips', m.eips], ['obs buckets', m.obs_buckets],
    ['jobs running', m.jobs_running], ['jobs total', m.jobs_total],
  ];
  $('stats').innerHTML = items.map(([k, v]) =>
    `<div class="stat${k === 'jobs running' && v > 0 ? ' alert' : ''}">
       <b>${v ?? 0}</b><span>${k}</span></div>`).join('');
}

function renderResources(res) {
  $('res-count').textContent = `${res.total} total`;
  const rows = (res.resources || []).slice(0, 500).map(r => `<tr>
    <td>${r.type}</td><td>${r.name || '-'}</td>
    <td><a href="/admin/resources/${r.id}" style="color:var(--blue);text-decoration:none"><code>${(r.id||'').slice(0,18)}</code></a></td>
    <td><code>${(r.project_id || '-').slice(0, 8)}</code></td>
    <td>${pill(r.status)}</td></tr>`).join('');
  $('res-body').innerHTML = rows ||
    '<tr><td colspan="5" class="empty"><span class="icon">&#9729;</span>no resources match</td></tr>';
  const sel = $('f-type');
  if (sel.options.length === 1) {
    [...new Set((res.resources || []).map(r => r.type))].sort().forEach(t => {
      sel.add(new Option(t, t));
    });
  }
}

function renderChaos(chaos) {
  const rules = chaos.rules || [];
  $('chaos-count').textContent = `${rules.length} active`;
  $('chaos-body').innerHTML = rules.map(r => `<tr>
    <td><code>${r.rule_id.slice(0, 8)}</code></td>
    <td>${r.service}</td><td>${r.mode}</td><td>${r.failure_rate}</td>
    <td>${r.error_code} / ${r.status}</td>
    <td><button class="danger" onclick="delRule('${r.rule_id}')">remove</button></td>
  </tr>`).join('') ||
  '<tr><td colspan="6" class="empty"><span class="icon">&#9889;</span>no rules: the cloud is behaving</td></tr>';
}


const CATALOG = [
  {n:"IAM",c:"Identity"},{n:"ECS",c:"Compute"},{n:"EVS",c:"Storage"},{n:"VPC",c:"Network"},
  {n:"EIP",c:"Network"},{n:"IMS",c:"Compute"},{n:"CBR",c:"Storage"},{n:"RDS",c:"Database"},
  {n:"DNS",c:"Network"},{n:"KMS",c:"Security"},{n:"ELB",c:"Network"},{n:"SFS",c:"Storage"},
  {n:"CCE",c:"Containers"},{n:"FunctionGraph",c:"Serverless"},{n:"BMS",c:"Compute"},
  {n:"AS",c:"Compute"},{n:"SMN",c:"Messaging"},{n:"CES",c:"Monitoring"},
  {n:"LTS",c:"Monitoring"},{n:"DCS",c:"Database"},{n:"DMS",c:"Messaging"},
  {n:"DDS",c:"Database"},{n:"WAF",c:"Security"},{n:"TMS",c:"Management"},
  {n:"EPS",c:"Management"},{n:"APIG",c:"API"},{n:"SWR",c:"Containers"},
  {n:"ModelArts",c:"AI/ML"},{n:"IoTDA",c:"IoT"},{n:"GaussDB",c:"Database"},
  {n:"AOM",c:"Monitoring"},{n:"DLI",c:"Big Data"},{n:"Anti-DDoS",c:"Security"},
  {n:"BSS",c:"Billing"},{n:"NAT",c:"Network"},{n:"Peering",c:"Network"},
  {n:"ACL",c:"Network"},{n:"VPC Routes",c:"Network"},{n:"VPN",c:"Network"},
  {n:"HSS",c:"Security"},{n:"CDN",c:"Edge"},{n:"DWS",c:"Big Data"},
  {n:"CSS",c:"Big Data"},{n:"MRS",c:"Big Data"},{n:"SMS",c:"Migration"},
  {n:"DC",c:"Network"},{n:"ER",c:"Network"},{n:"DIS",c:"Streaming"},
  {n:"DataArts",c:"Big Data"},{n:"OMS",c:"Migration"},{n:"DES",c:"Migration"},
  {n:"CodeArts",c:"DevOps"},{n:"ServiceStage",c:"DevOps"},{n:"CSE",c:"DevOps"},
  {n:"CCI",c:"Containers"},{n:"CFW",c:"Security"},{n:"DSC",c:"Security"},
  {n:"VOD",c:"Media"},{n:"IEF",c:"Edge"},{n:"OBS",c:"Storage"},
];

function renderCatalog() {
  $('catalog-count').textContent = CATALOG.length + ' services';
  $('catalog-grid').innerHTML = CATALOG.map(s =>
    `<div class="catalog-item" title="${s.n} - ${s.c}">
       <span class="dot up"></span>
       <span class="name">${s.n}</span>
       <span class="cat">${s.c}</span>
     </div>`).join('');
}

async function addRule() {
  await fetch('/admin/chaos', { method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ service: $('c-svc').value, mode: $('c-mode').value,
      failure_rate: parseFloat($('c-rate').value), status: parseInt($('c-status').value),
      error_code: 'SIM.CHAOS', error_msg: 'injected from console' }) });
  refresh();
renderCatalog();
}
async function delRule(id) {
  await fetch(`/admin/chaos/${id}`, { method: 'DELETE' }); refresh();
renderCatalog();
}
async function resetRules() {
  await fetch('/admin/chaos/reset', { method: 'POST' }); refresh();
renderCatalog();
}

['f-name', 'f-type', 'f-project'].forEach(id =>
  $(id).addEventListener(id === 'f-name' ? 'input' : 'change', refresh));
setInterval(refresh, 3000);
refresh();
renderCatalog();
setInterval(() => $('clock').textContent =
  new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'}), 1000);
</script>
</body></html>""".replace("__FAVICON__", FAVICON)
