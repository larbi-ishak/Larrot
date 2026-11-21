"""HSS (Host Security Service): hosts, protection policies, alarms, vulnerabilities.

Real routes: GET /v5/{project_id}/hosts, /v5/{project_id}/policy, /v5/{project_id}/alarm-events.
Hosts are discovered from ECS servers (cross-service correlation: every ECS in the
project appears as an HSS host with its agent status).
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _host_json(s, server, pid):
    host = getattr(s, "hss_hosts", {}).get(server["id"], {})
    return {
        "host_id": server["id"],
        "host_name": server["name"],
        "agent_status": host.get("agent_status", "not_installed"),
        "protect_status": host.get("protect_status", "closed"),
        "protect_version": host.get("charge_mode", ""),
        "os_type": "Linux",
        "os_name": "Ubuntu 22.04",
        "host_status": "ACTIVE" if server["status"] == "ACTIVE" else "BUILD",
        "private_ip": next((a["addr"] for addrs in server["addresses"].values()
                            for a in addrs), ""),
        "asset_value": host.get("asset_value", "important"),
        "decoy_host": False,
        "project_id": pid,
    }


@router.get("/v5/{pid}/hosts")
async def list_hosts(request: Request, pid: str):
    """List HSS hosts: every ECS appears with its agent and protection status."""
    s = request.app.state.sim
    servers = [x for x in s.servers.values() if x["project_id"] == pid]
    hosts = [_host_json(s, x, pid) for x in servers]
    return {"total": len(hosts), "data_list": hosts}


@router.get("/v5/{pid}/hosts/{host_id}")
async def show_host(request: Request, pid: str, host_id: str):
    """Show one host: agent status, protection version, and asset value."""
    s = request.app.state.sim
    server = s.servers.get(host_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error_code": "HSS.0001", "error_msg": "Host not found"},
                            status_code=404)
    return _host_json(s, server, pid)


@router.post("/v5/{pid}/hosts/{host_id}/protection")
async def set_protection(request: Request, pid: str, host_id: str):
    """Enable/change protection (charge_mode: basic/hsp/pro/enterprise)."""
    s = request.app.state.sim
    if not hasattr(s, "hss_hosts"):
        s.hss_hosts = {}
    server = s.servers.get(host_id)
    if not server or server["project_id"] != pid:
        return JSONResponse({"error_code": "HSS.0001", "error_msg": "Host not found"},
                            status_code=404)
    body = await request.json()
    mode = body.get("charge_mode", "hsp")
    s.hss_hosts[host_id] = {
        "agent_status": "online", "protect_status": "opened",
        "charge_mode": mode, "version": now_millis(),
    }
    return {"host_id": host_id, "protect_status": "opened", "charge_mode": mode}


@router.get("/v5/{pid}/policy")
async def list_policies(request: Request, pid: str):
    """List protection policies: ransomware and baseline check configurations."""
    s = request.app.state.sim
    policies = [p for p in getattr(s, "hss_policies", {}).values()
                if p["project_id"] == pid]
    return {"total": len(policies), "data_list": policies}


@router.post("/v5/{pid}/policy")
async def create_policy(request: Request, pid: str):
    """Create a protection policy: which hosts get which protection."""
    s = request.app.state.sim
    if not hasattr(s, "hss_policies"):
        s.hss_policies = {}
    body = await request.json()
    policy_id = new_id()
    s.hss_policies[policy_id] = {
        "policy_id": policy_id, "name": body.get("name", f"policy-{policy_id[:8]}"),
        "protection_type": body.get("protection_type", "container"),
        "detect_type": body.get("detect_type", "all"),
        "protection_mode": body.get("protection_mode", "alarm"),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"policy_id": policy_id, "name": s.hss_policies[policy_id]["name"]}


@router.get("/v5/{pid}/alarm-events")
async def list_alarms(request: Request, pid: str):
    """List HSS alarm events: intrusion and anomaly detections."""
    s = request.app.state.sim
    alarms = [a for a in getattr(s, "hss_alarms", {}).values()
              if a["project_id"] == pid]
    return {"total": len(alarms), "data_list": alarms}


@router.post("/v5/{pid}/alarm-events")
async def create_alarm_event(request: Request, pid: str):
    """Test hook: inject an alarm event (real HSS generates these from detection)."""
    s = request.app.state.sim
    if not hasattr(s, "hss_alarms"):
        s.hss_alarms = {}
    body = await request.json()
    aid = new_id()
    s.hss_alarms[aid] = {
        "event_id": aid, "event_type": body.get("event_type", 3001),
        "event_name": body.get("event_name", "Abnormal login"),
        "severity": body.get("severity", "Medium"),
        "host_name": body.get("host_name", ""), "host_id": body.get("host_id", ""),
        "occur_time": now_millis(), "handle_status": "unhandled",
        "project_id": pid,
    }
    return {"event_id": aid}


@router.get("/v5/{pid}/vulnerabilities")
async def list_vulnerabilities(request: Request, pid: str):
    """List the vulnerabilities found on hosts with severities."""
    s = request.app.state.sim
    vulns = [v for v in getattr(s, "hss_vulns", {}).values() if v["project_id"] == pid]
    return {"total": len(vulns), "data_list": vulns}


@router.post("/v5/{pid}/vulnerabilities/scan")
async def scan_vulnerabilities(request: Request, pid: str):
    """Trigger a scan: creates a scan task that finds seeded vulns."""
    s = request.app.state.sim
    if not hasattr(s, "hss_vulns"):
        s.hss_vulns = {}
    found = []
    for server in [x for x in s.servers.values() if x["project_id"] == pid]:
        vid = new_id()
        s.hss_vulns[vid] = {
            "vuln_id": vid, "vuln_name": "CVE-2024-1234 test vulnerability",
            "severity": "Important", "host_id": server["id"],
            "host_name": server["name"], "status": "open",
            "scan_time": now_millis(), "project_id": pid,
        }
        found.append(vid)
    return {"total": len(found), "scan_task_id": new_id()}


@router.get("/v5/{pid}/quotas")
async def hss_quotas(request: Request, pid: str):
    """Show HSS quotas: how many hosts can be protected."""
    s = request.app.state.sim
    hosts = len([x for x in s.servers.values() if x["project_id"] == pid])
    return {"total": 1000, "used": hosts, "version": "hsp"}
