"""Web console: live resource browser, chaos panel, job stats (vanilla JS, no deps)."""



def console_html(state) -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Larrot console</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         background: #0d1117; color: #c9d1d9; font-size: 13px; }
  header { padding: 14px 20px; border-bottom: 1px solid #21262d;
           display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  header h1 { margin: 0; font-size: 16px; color: #58a6ff; }
  header .parrot { font-size: 20px; }
  header .spacer { flex: 1; }
  header a { color: #8b949e; text-decoration: none; }
  header a:hover { color: #58a6ff; }
  .wrap { padding: 16px 20px; max-width: 1200px; margin: 0 auto; }
  .stats { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
  .stat { background: #161b22; border: 1px solid #21262d; border-radius: 6px;
          padding: 8px 14px; min-width: 90px; }
  .stat b { display: block; font-size: 18px; color: #58a6ff; }
  .stat span { color: #8b949e; font-size: 11px; }
  .panel { background: #161b22; border: 1px solid #21262d; border-radius: 6px;
           margin-bottom: 16px; }
  .panel h2 { margin: 0; padding: 10px 14px; font-size: 13px; color: #8b949e;
              border-bottom: 1px solid #21262d; display: flex; align-items: center; gap: 8px; }
  .panel h2 .count { color: #58a6ff; }
  .toolbar { padding: 10px 14px; display: flex; gap: 8px; flex-wrap: wrap;
             border-bottom: 1px solid #21262d; }
  .toolbar input, .toolbar select { background: #0d1117; border: 1px solid #30363d;
           color: #c9d1d9; border-radius: 4px; padding: 5px 8px; font: inherit; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 6px 14px; border-bottom: 1px solid #21262d; }
  th { color: #8b949e; font-weight: normal; font-size: 11px; text-transform: uppercase; }
  tr:hover td { background: #161b2288; }
  .pill { padding: 1px 8px; border-radius: 10px; font-size: 11px; }
  .ok { background: #1b4721; color: #3fb950; } .warn { background: #4a3800; color: #d29922; }
  .err { background: #5a1d1d; color: #f85149; } .mut { background: #21262d; color: #8b949e; }
  .empty { text-align: center; color: #484f58; padding: 18px; }
  button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
           border-radius: 4px; padding: 5px 10px; font: inherit; cursor: pointer; }
  button:hover { background: #30363d; }
  button.danger { color: #f85149; }
  .chaos-form { display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 14px;
                border-bottom: 1px solid #21262d; align-items: center; }
  .chaos-form label { color: #8b949e; font-size: 11px; }
  code { color: #79c0ff; }
</style>
</head>
<body>
<header>
  <span class="parrot">&#129436;</span>
  <h1>Larrot console</h1>
  <span id="clock"></span>
  <span class="spacer"></span>
  <a href="/">dashboard</a>
  <a href="/docs">API docs</a>
  <a href="https://github.com/larbi-ishak/Larrot">GitHub</a>
</header>
<div class="wrap">
  <div class="stats" id="stats"></div>

  <div class="panel">
    <h2>resources <span class="count" id="res-count"></span></h2>
    <div class="toolbar">
      <input id="f-name" placeholder="filter by name or id" size="24">
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
      <input id="c-svc" placeholder="ecs" size="8">
      <label>mode</label>
      <select id="c-mode"><option>api</option><option>job</option></select>
      <label>rate</label>
      <input id="c-rate" value="1.0" size="4">
      <label>status</label>
      <input id="c-status" value="500" size="4">
      <button onclick="addRule()">inject</button>
      <button onclick="resetRules()" class="danger">reset all</button>
    </div>
    <table>
      <thead><tr><th>rule</th><th>target</th><th>mode</th><th>rate</th><th>error</th><th></th></tr></thead>
      <tbody id="chaos-body"></tbody>
    </table>
  </div>
</div>
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
    `<div class="stat"><b>${v ?? 0}</b><span>${k}</span></div>`).join('');
}

function renderResources(res) {
  $('res-count').textContent = `${res.total} total`;
  const rows = (res.resources || []).slice(0, 500).map(r => `<tr>
    <td>${r.type}</td><td>${r.name || '-'}</td>
    <td><a href="/admin/resources/${r.id}" style="color:#79c0ff">${(r.id||'').slice(0,18)}</a></td>
    <td>${(r.project_id || '-').slice(0, 8)}</td>
    <td>${pill(r.status)}</td></tr>`).join('');
  $('res-body').innerHTML = rows || '<tr><td colspan="5" class="empty">no resources match</td></tr>';
  // populate the type filter once
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
  </tr>`).join('') || '<tr><td colspan="6" class="empty">no rules: the cloud is behaving</td></tr>';
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
setInterval(() => $('clock').textContent = new Date().toLocaleTimeString(), 1000);
</script>
</body></html>"""
