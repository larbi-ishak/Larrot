"""Web console: live resource browser, chaos panel, job stats (vanilla JS, no deps)."""

# Inline SVG favicon (red cloud + parrot silhouette)
FAVICON = """data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cpath d='M20 44a12 12 0 1 1 2.4-23.7A16 16 0 0 1 52 26a10 10 0 0 1-2 19.7H20z' fill='%23e60012'/%3E%3Cpath d='M28 32l6-4 2 5 5-2-3 6 4 2-7 2-1 5-4-4-5 3 2-6-6-1z' fill='%23fff' opacity='.15'/%3E%3C/svg%3E"""


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
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M20 44a12 12 0 1 1 2.4-23.7A16 16 0 0 1 52 26a10 10 0 0 1-2 19.7H20z"
            fill="var(--accent)"/>
      <circle cx="26" cy="30" r="3" fill="#fff" opacity=".9"/>
      <circle cx="36" cy="28" r="2.5" fill="#fff" opacity=".7"/>
      <circle cx="44" cy="32" r="2" fill="#fff" opacity=".5"/>
    </svg>
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
  Larrot &middot; repeats Huawei Cloud &middot;
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

async function addRule() {
  await fetch('/admin/chaos', { method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ service: $('c-svc').value, mode: $('c-mode').value,
      failure_rate: parseFloat($('c-rate').value), status: parseInt($('c-status').value),
      error_code: 'SIM.CHAOS', error_msg: 'injected from console' }) });
  refresh();
}
async function delRule(id) {
  await fetch(`/admin/chaos/${id}`, { method: 'DELETE' }); refresh();
}
async function resetRules() {
  await fetch('/admin/chaos/reset', { method: 'POST' }); refresh();
}

['f-name', 'f-type', 'f-project'].forEach(id =>
  $(id).addEventListener(id === 'f-name' ? 'input' : 'change', refresh));
setInterval(refresh, 3000);
refresh();
setInterval(() => $('clock').textContent =
  new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'}), 1000);
</script>
</body></html>""".replace("__FAVICON__", FAVICON)
