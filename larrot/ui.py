"""Shared UI components: navbar, theme constants, used by dashboard, console, and API docs wrapper."""

import base64
import os

_logo_path = os.path.join(os.path.dirname(__file__), "static", "logo-64.png")
_logo = base64.b64encode(open(_logo_path, "rb").read()).decode()
LOGO = f"data:image/png;base64,{_logo}"

# Service tree for the sidebar
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


def navbar(active: str = "") -> str:
    """Shared top navbar. active = 'dashboard' | 'console' | 'docs'"""
    links = [
        ("dashboard", "/", "Dashboard"),
        ("console", "/console", "Console"),
        ("docs", "/docs", "API Docs"),
        ("", "https://larbi-ishak.github.io/Larrot/", "Docs Site"),
        ("", "https://github.com/larbi-ishak/Larrot", "GitHub"),
    ]
    nav_html = ""
    for key, href, label in links:
        cls = ' class="active"' if key == active else ""
        tgt = ' target="_blank"' if href.startswith("http") else ""
        nav_html += f'<a href="{href}"{cls}{tgt}>{label}</a>'
    return f"""
<header class="topbar">
  <div class="logo">
    <img src="{LOGO}" alt="Larrot">
    <span class="name">Larrot</span>
  </div>
  <span class="spacer"></span>
  <span class="region">ap-southeast-1</span>
  <nav>{nav_html}</nav>
</header>"""


def api_docs_html() -> str:
    """API docs page: shared navbar on top, Swagger UI in a frame below."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Larrot API Docs</title>
<link rel="icon" href="{LOGO}">
<style>
{SHARED_CSS}
  html, body {{ height: 100%; overflow: hidden; }}
  .docs-frame {{ position: fixed; top: 48px; left: 0; right: 0; bottom: 0;
                  width: 100%; height: calc(100vh - 48px); border: none; }}
</style>
</head>
<body>
{navbar("docs")}
<iframe class="docs-frame" src="/docs/swagger" title="Swagger UI"></iframe>
</body>
</html>"""


def sidebar(active_svc: str = "") -> str:
    """Shared sidebar with service tree."""
    tree = f'<a class="nav-item{" active" if not active_svc else ""}" href="/console">'
    tree += '<span class="nav-dot"></span>Overview</a>'
    for cat, svcs in SERVICES.items():
        items = "".join(
            f'<a class="nav-item{" active" if s == active_svc else ""}" '
            f'href="/console?q={s}"><span class="nav-dot"></span>{s}</a>'
            for s in svcs)
        tree += f'<div class="nav-group"><div class="nav-cat">{cat}</div>{items}</div>'
    return f"""
<aside class="sidebar">
  <div class="sidebar-header">
    <img src="{LOGO}" alt="Larrot">
    <div>
      <div class="name">Larrot</div>
      <div class="sub">local Huawei Cloud</div>
    </div>
  </div>
  <nav class="sidebar-nav">{tree}</nav>
  <div class="sidebar-footer">
    <a href="/">Dashboard</a> &middot;
    <a href="/docs">API</a> &middot;
    <a href="https://github.com/larbi-ishak/Larrot">GitHub</a>
  </div>
</aside>"""


SHARED_CSS = """
  :root {
    --bg: #f5f6f8; --sidebar-bg: #1a1d27; --sidebar-hover: #252a38;
    --sidebar-active: #e60012; --sidebar-text: #8b949e; --sidebar-text-hi: #fff;
    --card-bg: #fff; --card-border: #e3e6ea; --card-shadow: 0 1px 3px rgba(0,0,0,.06);
    --text: #26282c; --text-dim: #6b7280; --text-faint: #9ca3af;
    --accent: #e60012; --accent-bg: #fef0f0;
    --ok: #16a34a; --ok-bg: #f0fdf4;
    --warn: #d97706; --warn-bg: #fffbeb;
    --err: #dc2626; --err-bg: #fef2f2;
    --blue: #2563eb; --blue-bg: #eff6ff;
  }
  * { margin: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", sans-serif; background: var(--bg); color: var(--text);
          font-size: 14px; }

  /* ===== topbar ===== */
  .topbar { background: #fff; border-bottom: 1px solid var(--card-border);
            padding: 0 24px; height: 48px; display: flex; align-items: center;
            gap: 12px; position: sticky; top: 0; z-index: 50; }
  .topbar .logo { display: flex; align-items: center; gap: 8px; }
  .topbar .logo img { width: 28px; height: 28px; }
  .topbar .logo .name { font-size: 16px; font-weight: 700;
                          background: linear-gradient(135deg, #ff4757, #e60012);
                          -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .topbar .spacer { flex: 1; }
  .topbar .region { background: var(--accent-bg); color: var(--accent);
                    padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .topbar nav { display: flex; gap: 2px; }
  .topbar nav a { color: var(--text-dim); text-decoration: none; font-size: 12px;
                  padding: 5px 10px; border-radius: 4px; }
  .topbar nav a:hover { background: var(--bg); color: var(--text); }
  .topbar nav a.active { color: var(--accent); background: var(--accent-bg); }

  /* ===== sidebar ===== */
  .sidebar { width: 230px; background: var(--sidebar-bg); color: var(--sidebar-text);
              display: flex; flex-direction: column; position: fixed; top: 48px; bottom: 0;
              left: 0; overflow-y: auto; z-index: 100; }
  .sidebar-header { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,.08);
                     display: flex; align-items: center; gap: 10px; }
  .sidebar-header img { width: 30px; height: 30px; }
  .sidebar-header .name { color: #fff; font-size: 16px; font-weight: 700; }
  .sidebar-header .sub { font-size: 10px; color: var(--sidebar-text); }
  .sidebar-nav { padding: 6px 0; flex: 1; }
  .nav-group { margin-bottom: 2px; }
  .nav-cat { padding: 10px 16px 3px; font-size: 10px; text-transform: uppercase;
              letter-spacing: 1px; color: var(--text-faint); font-weight: 600; }
  .nav-item { display: flex; align-items: center; gap: 8px; padding: 6px 16px;
              color: var(--sidebar-text); text-decoration: none; font-size: 12.5px;
              transition: all .1s; border-left: 3px solid transparent; }
  .nav-item:hover { background: var(--sidebar-hover); color: var(--sidebar-text-hi); }
  .nav-item.active { background: var(--sidebar-hover); color: #fff;
                      border-left-color: var(--sidebar-active); }
  .nav-dot { width: 5px; height: 5px; border-radius: 50%; background: #3a3f4f; flex-shrink: 0; }
  .nav-item:hover .nav-dot, .nav-item.active .nav-dot { background: var(--sidebar-active); }
  .sidebar-footer { padding: 10px 16px; border-top: 1px solid rgba(255,255,255,.08);
                    font-size: 11px; }
  .sidebar-footer a { color: var(--sidebar-text); text-decoration: none; }
  .sidebar-footer a:hover { color: #fff; }

  /* ===== main content area (with sidebar offset) ===== */
  .main-with-sidebar { margin-left: 230px; padding-top: 48px; }
  .main-no-sidebar { padding-top: 48px; }

  /* ===== panels ===== */
  .panel { background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 8px; margin-bottom: 16px; box-shadow: var(--card-shadow);
            overflow: hidden; }
  .panel-header { padding: 12px 18px; border-bottom: 1px solid var(--card-border);
                   display: flex; align-items: center; gap: 10px; }
  .panel-header h2 { font-size: 14px; font-weight: 600; }
  .panel-header .badge { background: var(--accent-bg); color: var(--accent);
                          padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }

  /* ===== status badges ===== */
  .st { display: inline-flex; align-items: center; gap: 5px;
          padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .st::before { content: ''; width: 6px; height: 6px; border-radius: 50%; }
  .st-ok { background: var(--ok-bg); color: var(--ok); } .st-ok::before { background: var(--ok); }
  .st-warn { background: var(--warn-bg); color: var(--warn); } .st-warn::before { background: var(--warn); }
  .st-err { background: var(--err-bg); color: var(--err); } .st-err::before { background: var(--err); }
  .st-mut { background: var(--bg); color: var(--text-faint); } .st-mut::before { background: var(--text-faint); }

  /* ===== buttons ===== */
  .btn { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px;
          border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer;
          border: 1px solid var(--card-border); background: #fff; color: var(--text); }
  .btn:hover { border-color: var(--text-dim); }
  .btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
  .btn-primary:hover { background: #c50010; }
  .btn-danger { color: var(--err); border-color: var(--err); }
  .btn-danger:hover { background: var(--err-bg); }
  .btn-sm { padding: 3px 10px; font-size: 11px; }

  /* ===== table ===== */
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 8px 18px; color: var(--text-dim); font-weight: 500;
       font-size: 11px; border-bottom: 1px solid var(--card-border);
       text-transform: uppercase; letter-spacing: .3px; }
  td { padding: 8px 18px; border-bottom: 1px solid var(--card-border); font-size: 13px; }
  tr:hover td { background: #fafbfc; }
  td code { color: var(--blue); font-family: ui-monospace, Menlo, monospace; font-size: 12px; }

  /* ===== responsive ===== */
  @media (max-width: 1024px) {
    .sidebar { display: none; }
    .main-with-sidebar { margin-left: 0; }
    .topbar nav { display: none; }
  }
"""
