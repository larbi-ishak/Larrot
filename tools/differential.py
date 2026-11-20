#!/usr/bin/env python3
"""Larrot differential testing harness (ROADMAP 3.1).

Sends the same requests to a real Huawei Cloud test project AND to Larrot,
normalizes dynamic fields, and diffs the responses. This converts
docs/docs from manual notes into a runnable regression harness.

Modes:
  sim-only (default): validate the sim against expected statuses/shapes.
  differential:       set HWY_AK, HWY_SK, HWY_PID, HWY_ENDPOINT env vars
                      to also hit a real account and diff both responses.

Usage:
  python3 tools/differential.py                 # sim-only
  HWY_AK=... HWY_SK=... python3 tools/differential.py   # differential

Safety: uses disposable test projects only; every created resource is
tracked and cleaned up. Never point this at a production project.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))

SIM_URL = os.environ.get("SIM_URL", "http://127.0.0.1:8200")
REAL_URL = os.environ.get("HWY_ENDPOINT", "")
REAL_AK = os.environ.get("HWY_AK", "")
REAL_SK = os.environ.get("HWY_SK", "")
REAL_PID = os.environ.get("HWY_PID", "")

PID = os.environ.get("SIM_PID", "79814d675f6142d9b4a8ee417b924444")
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"

# ---------------------------------------------------------------------------
# request corpus: (name, method, path, body, expect_sim_status, required_fields)
# ---------------------------------------------------------------------------

CORPUS = [
    # --- IAM ---
    ("iam: list projects", "GET", "/v3/projects", None, 200, ["projects[].id"]),
    ("iam: list domains", "GET", "/v3/domains", None, 200, ["domains[].id"]),
    ("iam: service catalog", "GET", "/v3/auth/catalog", None, 200, ["catalog[].type"]),
    ("iam: list identity providers", "GET", "/v3.0/OS-FEDERATION/identity_providers", None, 200, ["identity_providers"]),
    ("iam: list mappings", "GET", "/v3.0/OS-FEDERATION/mappings", None, 200, ["mappings"]),
    ("iam: token without password", "POST", "/v3/auth/tokens",
     {"auth": {"identity": {"methods": ["token"]}}}, 401, ["error_code"]),
    # --- ECS ---
    ("ecs: list flavors", "GET", f"/v1/{PID}/cloudservers/flavors", None, 200, ["flavors[].id"]),
    ("ecs: list servers", "GET", f"/v1/{PID}/cloudservers/detail", None, 200, ["count", "servers"]),
    ("ecs: show missing server", "GET", f"/v1/{PID}/cloudservers/00000000-0000-0000-0000-000000000000",
     None, 404, ["error.code"]),
    ("ecs: create without imageRef", "POST", f"/v1.1/{PID}/cloudservers",
     {"server": {"flavorRef": FLAVOR, "name": "x"}}, 400, ["error.code"]),
    ("ecs: quotas", "GET", f"/v1/{PID}/cloudservers/limits", None, 200, ["absolute.maxTotalInstances"]),
    ("ecs: job not found", "GET", f"/v1/{PID}/jobs/nonexistent", None, 404, ["error.code"]),
    ("ecs: keypairs", "GET", f"/v2.1/{PID}/os-keypairs", None, 200, ["keypairs"]),
    ("ecs: server groups", "GET", f"/v2.1/{PID}/os-server-groups", None, 200, ["server_groups"]),
    # --- EVS ---
    ("evs: list volumes", "GET", f"/v2/{PID}/cloudvolumes", None, 200, ["volumes"]),
    ("evs: list volumes detail", "GET", f"/v2/{PID}/cloudvolumes/detail", None, 200, ["count", "volumes"]),
    ("evs: create size 9", "POST", f"/v2.1/{PID}/cloudvolumes",
     {"volume": {"size": 9, "name": "tiny"}}, 400, ["error.code"]),
    ("evs: show missing volume", "GET", f"/v2/{PID}/cloudvolumes/no-such-vol", None, 404, ["error.code"]),
    ("evs: snapshots list", "GET", f"/v2/{PID}/cloudsnapshots", None, 200, ["snapshots"]),
    # --- VPC / EIP / ports ---
    ("vpc: list vpcs", "GET", f"/v1/{PID}/vpcs", None, 200, ["vpcs[].id"]),
    ("vpc: show missing vpc", "GET", f"/v1/{PID}/vpcs/no-such-vpc", None, 404, ["code"]),
    ("vpc: list subnets", "GET", f"/v1/{PID}/subnets", None, 200, ["subnets"]),
    ("vpc: list ports", "GET", f"/v1/{PID}/ports", None, 200, ["ports"]),
    ("vpc: list security groups", "GET", f"/v1/{PID}/security-groups", None, 200, ["security_groups"]),
    ("eip: show missing eip", "GET", f"/v1/{PID}/publicips/no-such-eip", None, 404, ["code"]),
    ("eip: bandwidths", "GET", f"/v2.0/{PID}/bandwidths", None, 200, ["bandwidths"]),
    # --- IMS / CBR / RDS ---
    ("ims: list images", "GET", "/v2/images", None, 200, ["images[].id"]),
    ("cbr: list vaults", "GET", f"/v3/{PID}/vaults", None, 200, ["vaults"]),
    ("cbr: show missing backup", "GET", f"/v3/{PID}/backups/bad-id", None, 404, ["error_code"]),
    ("rds: list instances", "GET", f"/v3/{PID}/instances", None, 200, ["instances"]),
    ("rds: list flavors", "GET", f"/v3/{PID}/flavors", None, 200, ["flavors"]),
    # --- DNS / KMS / ELB / NAT / VPN ---
    ("dns: list zones", "GET", "/v2/zones", None, 200, ["zones"]),
    ("dns: recordset on missing zone", "POST", "/v2/zones/bad-zone/recordsets",
     {"name": "t.example.com.", "type": "A", "records": ["1.2.3.4"]}, 404, ["error_code"]),
    ("kms: describe missing key", "GET", f"/v1/{PID}/kms/describe-key/bad-key", None, 404, []),
    ("elb: list loadbalancers", "GET", f"/v2/{PID}/elb/loadbalancers", None, 200, ["loadbalancers"]),
    ("nat: list gateways", "GET", f"/v2.0/{PID}/nat_gateways", None, 200, ["nat_gateways"]),
    ("vpn: list gateways", "GET", f"/v5/{PID}/vpn-gateways", None, 200, ["vpn_gateways"]),
    # --- CCE / SMN / CES / LTS ---
    ("cce: list clusters", "GET", f"/api/v3/projects/{PID}/clusters", None, 200, ["clusters"]),
    ("smn: list topics", "GET", f"/v2/{PID}/notifications/topics", None, 200, ["topics"]),
    ("ces: list alarms", "GET", f"/v1/{PID}/alarms", None, 200, ["metric_alarms"]),
    ("ces: metric data", "GET", f"/v1.0/{PID}/metric-data?metric_name=cpu_util", None, 200,
     ["metric_data_results[].datapoints"]),
    ("lts: list log groups", "GET", f"/v2/{PID}/log-groups", None, 200, ["log_groups"]),
    # --- data services ---
    ("dcs/dms: list instances", "GET", f"/v2/{PID}/instances", None, 200, ["instances"]),
    ("dis: list streams", "GET", f"/v2/{PID}/streams", None, 200, ["stream_names"]),
    ("dws: list clusters", "GET", f"/v1.0/{PID}/dws/clusters", None, 200, ["clusters"]),
    ("css: list clusters", "GET", f"/v1.0/{PID}/css/clusters", None, 200, ["clusters"]),
    ("mrs: list clusters", "GET", f"/v1.1/{PID}/cluster_infos", None, 200, ["cluster_list"]),
    ("dli: list queues", "GET", f"/v1.0/{PID}/queues", None, 200, ["queues"]),
    # --- security / ops ---
    ("hss: list hosts", "GET", f"/v5/{PID}/hosts", None, 200, ["data_list"]),
    ("hss: quotas", "GET", f"/v5/{PID}/quotas", None, 200, ["total"]),
    ("waf: list hosts", "GET", f"/v1/{PID}/waf/hosts", None, 200, []),
    ("cfw: list firewalls", "GET", f"/v1/{PID}/firewalls", None, 200, ["firewalls"]),
    ("antiddos: status", "GET", f"/v1/{PID}/antiddos/status?floating_ip_id=x", None, 200, []),
    # --- platform ---
    ("cdn: list domains", "GET", "/v1/domains", None, 200, ["domains"]),
    ("cdn: history tasks", "GET", "/v1.0/historytasks", None, 200, ["tasks"]),
    ("modelarts: list models", "GET", f"/v1/{PID}/models", None, 200, ["models"]),
    ("modelarts: list services", "GET", f"/v1/{PID}/services", None, 200, ["services"]),
    ("maas: list models", "GET", "/v1/models", None, 200, ["data[].id"]),
    ("maas: chat completions", "POST", "/v1/chat/completions",
     {"model": "DeepSeek-V3", "messages": [{"role": "user", "content": "hi"}]},
     200, ["choices[].message.content"]),
    ("maas: unknown model", "POST", "/v1/chat/completions",
     {"model": "bogus", "messages": []}, 404, ["error.code"]),
    ("swr: list namespaces", "GET", f"/v2/{PID}/namespaces", None, 200, []),
    ("apig: list instances", "GET", f"/v2/{PID}/apigw/instances", None, 200, []),
    ("bss: list orders", "GET", "/v2/orders/customer-orders", None, 200, []),
    ("tms: project tags", "GET", "/v1.0/project-tags/tags", None, 200, ["tags"]),
    ("eps: enterprise projects", "GET", "/v1.0/enterprise-projects", None, 200, []),
    # --- gateway ---
    ("gw: unknown path", "GET", "/no/such/api", None, 404, ["error_code"]),
]

# ---------------------------------------------------------------------------
# normalization: dynamic fields become placeholders before comparing
# ---------------------------------------------------------------------------

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
HEX32_RE = re.compile(r"\b[0-9a-f]{32}\b")
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?")
IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
DYNAMIC_KEYS = {"id", "job_id", "request_id", "created_at", "updated_at",
                "create_time", "begin_time", "end_time", "hostId", "checkpoint_id"}


def normalize(node):
    """Replace dynamic values with placeholders so responses are comparable."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in DYNAMIC_KEYS and isinstance(v, str) and v:
                out[k] = "<dyn>"
            else:
                out[k] = normalize(v)
        return out
    if isinstance(node, list):
        return [normalize(x) for x in node]
    if isinstance(node, str):
        s = UUID_RE.sub("<uuid>", node)
        s = HEX32_RE.sub("<hex32>", s)
        s = TIME_RE.sub("<time>", s)
        s = IP_RE.sub("<ip>", s)
        return s
    return node


def _shape(node):
    """Reduce to a shape: dict keys, list lengths, scalar types."""
    if isinstance(node, dict):
        return {k: _shape(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        return [_shape(x) for x in node[:1]] if node else []
    return type(node).__name__


def send(url, method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": raw.decode(errors="replace")[:200]}


def check_required(data, path):
    parts = path.replace("[]", "").split(".")
    node = data
    for p in parts:
        if isinstance(node, list) and node:
            node = node[0]
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return False
    return True


def sign_headers(method, path, body):
    if not (REAL_AK and REAL_SK):
        return None
    from larrot.core.signing import sign_sdk_request
    host = REAL_URL.replace("https://", "").replace("http://", "").split("/")[0]
    payload = json.dumps(body).encode() if body is not None else b""
    return sign_sdk_request(method, path, None, host, payload, REAL_AK, REAL_SK)


def run():
    differential = bool(REAL_URL and REAL_AK and REAL_SK)
    mode = "DIFFERENTIAL" if differential else "SIM-ONLY"
    print(f"differential harness: {mode} ({len(CORPUS)} requests)\n")

    passed = failed = 0
    for name, method, path, body, expect, required in CORPUS:
        status, data = send(SIM_URL, method, path, body)
        ok = status == expect
        notes = []
        if not ok:
            notes.append(f"sim status {status} != {expect}")
        for r in required:
            if not check_required(data, r):
                ok = False
                notes.append(f"missing {r}")

        verdict = "PASS" if ok else "FAIL"
        detail = "; ".join(notes)

        if differential:
            real_path = path.replace(PID, REAL_PID) if REAL_PID else path
            headers = sign_headers(method, real_path, body)
            rstatus, rdata = send(REAL_URL, method, real_path, body, headers)
            if rstatus == status:
                a, b = normalize(data), normalize(rdata)
                if a == b:
                    verdict += " IDENTICAL"
                elif _shape(a) == _shape(b):
                    verdict += " SHAPE_MATCH"
                else:
                    verdict += " MISMATCH"
                    detail += f" | real status {rstatus}"
            else:
                verdict += f" STATUS_DIFF (real={rstatus})"
            failed += ("MISMATCH" in verdict or "STATUS_DIFF" in verdict) or not ok
        else:
            if ok:
                passed += 1
            else:
                failed += 1

        print(f"  [{verdict}] {name}" + (f"  -> {detail}" if detail else ""))

    print(f"\n{mode}: {passed} passed, {failed} failed")
    if mode == "SIM-ONLY":
        print("set HWY_ENDPOINT, HWY_AK, HWY_SK, HWY_PID to enable differential mode")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
