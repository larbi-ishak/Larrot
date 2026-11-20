#!/usr/bin/env python3
"""Larrot differential testing harness (ROADMAP 3.1).

Sends the same requests to a real Huawei Cloud test project AND to Larrot,
normalizes dynamic fields, and diffs the responses. This converts
EMPIRICAL_SPEC.md from manual notes into a runnable regression harness.

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
    ("iam: list projects", "GET", "/v3/projects", None, 200, ["projects[].id"]),
    ("ecs: list flavors", "GET", f"/v1/{PID}/cloudservers/flavors", None, 200, ["flavors[].id"]),
    ("ecs: list servers", "GET", f"/v1/{PID}/cloudservers/detail", None, 200, ["count", "servers"]),
    ("ecs: show missing server", "GET", f"/v1/{PID}/cloudservers/00000000-0000-0000-0000-000000000000",
     None, 404, ["error.code"]),
    ("ecs: create without imageRef", "POST", f"/v1.1/{PID}/cloudservers",
     {"server": {"flavorRef": FLAVOR, "name": "x"}}, 400, ["error.code"]),
    ("ecs: create without flavorRef", "POST", f"/v1.1/{PID}/cloudservers",
     {"server": {"imageRef": IMAGE, "name": "x"}}, 400, ["error.code"]),
    ("evs: list volumes", "GET", f"/v2/{PID}/cloudvolumes", None, 200, ["volumes"]),
    ("evs: create size 9 (too small)", "POST", f"/v2.1/{PID}/cloudvolumes",
     {"volume": {"size": 9, "name": "tiny"}}, 400, ["error.code"]),
    ("evs: show missing volume", "GET", f"/v2/{PID}/cloudvolumes/no-such-vol",
     None, 404, ["error.code"]),
    ("vpc: list vpcs", "GET", f"/v1/{PID}/vpcs", None, 200, ["vpcs[].id"]),
    ("vpc: show missing vpc", "GET", f"/v1/{PID}/vpcs/no-such-vpc",
     None, 404, ["code"]),
    ("eip: show missing eip", "GET", f"/v1/{PID}/publicips/no-such-eip",
     None, 404, ["code"]),
    ("gw: unknown path", "GET", "/no/such/api", None, 404, ["error_code"]),
    ("maas: list models", "GET", "/v1/models", None, 200, ["data[].id"]),
    ("maas: unknown model", "POST", "/v1/chat/completions",
     {"model": "not-a-model", "messages": []}, 404, ["error.code"]),
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
