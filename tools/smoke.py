#!/usr/bin/env python3
"""huawei-sim smoke suite: tests every service with signed requests."""
import hashlib
import hmac
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

AK = "HWYSIMAK00000001"
SK = "HWYSIMSK00000001"
ALGORITHM = "SDK-HMAC-SHA256"
EMPTY_HASH = hashlib.sha256(b"").hexdigest()
BASE = "http://127.0.0.1:8200"
OBS = "http://127.0.0.1:8201"

PASSED = FAILED = 0


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def sign(method, url, body=b""):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.netloc
    path = parsed.path or "/"
    canonical_uri = path if path.endswith("/") else path + "/"
    pairs = sorted((k, v) for k, _, v in
                    (p.partition("=") for p in (parsed.query.split("&") if parsed.query else [])))
    canonical_query = "&".join(f"{k}={v}" if v else k for k, v in pairs)
    date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_HASH
    canonical_headers = f"content-type:application/json\nhost:{host}\nx-sdk-date:{date}\n"
    signed = "content-type;host;x-sdk-date"
    cr = "\n".join([method.upper(), canonical_uri, canonical_query, canonical_headers, signed, payload_hash])
    sts = "\n".join([ALGORITHM, date, hashlib.sha256(cr.encode()).hexdigest()])
    sig = hmac.new(SK.encode(), sts.encode(), hashlib.sha256).hexdigest()
    return {"Host": host, "X-Sdk-Date": date, "Content-Type": "application/json",
            "Authorization": f"{ALGORITHM} Access={AK}, SignedHeaders={signed}, Signature={sig}"}


def call(method, url, body=b""):
    headers = sign(method, url, body)
    req = urllib.request.Request(url, data=body if method in ("POST", "PUT") else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}


def obs_call(method, bucket, key="", query="", body=b"", content_type=""):
    if body and not content_type:
        content_type = "application/octet-stream"
    path = f"/{bucket}/{key}" if key else f"/{bucket}" if bucket else "/"
    url = OBS + path + (f"?{query}" if query else "")
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    resource = f"/{bucket}/{key}" if key else f"/{bucket}"
    sts = f"{method}\n\n{content_type}\n{date}\n{resource}"
    sig = __import__("base64").b64encode(hmac.new(SK.encode(), sts.encode(), hashlib.sha1).digest()).decode()
    headers = {"Date": date, "Authorization": f"OBS {AK}:{sig}"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body if method in ("POST", "PUT") and body else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def get_pid(name):
    _, body = call("GET", f"{BASE}/v3/projects")
    return next(p["id"] for p in body["projects"] if p["name"] == name)


def poll_job(pid, job_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, job = call("GET", f"{BASE}/v1/{pid}/jobs/{job_id}")
        if job.get("status") in ("SUCCESS", "FAIL"):
            return job
        time.sleep(0.3)
    return {"status": "TIMEOUT"}


def jbytes(obj):
    return json.dumps(obj).encode()


def main():
    global PASSED, FAILED

    print("== 1. IAM ==")
    st, body = call("GET", f"{BASE}/v3/projects")
    check("projects listed", st == 200 and len(body.get("projects", [])) >= 2)
    pid_pub = get_pid("ap-southeast-1")
    pid_hcs = get_pid("tr-west-1")

    print("== 2. ECS create ==")
    create = jbytes({"server": {"imageRef": "1ce5800a-e487-4c1b-b264-3353a39e2b4b",
                                 "flavorRef": "s6.large.2", "name": "smoke-vm", "count": 1}})
    st, body = call("POST", f"{BASE}/v1.1/{pid_pub}/cloudservers", create)
    check("create returns job+ids", st == 200 and body.get("job_id") and len(body.get("serverIds", [])) == 1)
    sid = body["serverIds"][0]
    job = poll_job(pid_pub, body["job_id"])
    check("job SUCCESS", job["status"] == "SUCCESS")

    print("== 3. ECS list + state ==")
    st, body = call("GET", f"{BASE}/v1/{pid_pub}/cloudservers/detail?limit=10")
    check("list shows ACTIVE", any(s["status"] == "ACTIVE" for s in body["servers"]))

    print("== 4. stop / start / guards ==")
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/cloudservers/action",
                    jbytes({"os-stop": {"type": "SOFT", "servers": [{"id": sid}]}}))
    poll_job(pid_pub, body["job_id"])
    st, body = call("GET", f"{BASE}/v1/{pid_pub}/cloudservers/{sid}")
    check("server SHUTOFF", body["server"]["status"] == "SHUTOFF")
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/cloudservers/action",
                    jbytes({"os-stop": {"type": "SOFT", "servers": [{"id": sid}]}}))
    check("stop on SHUTOFF → 400 Ecs.0100", st == 400 and body["error"]["code"] == "Ecs.0100")
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/cloudservers/action",
                    jbytes({"os-start": {"servers": [{"id": sid}]}}))
    poll_job(pid_pub, body["job_id"])
    st, body = call("GET", f"{BASE}/v1/{pid_pub}/cloudservers/{sid}")
    check("server ACTIVE again", body["server"]["status"] == "ACTIVE")

    print("== 5. EVS create + attach ==")
    st, body = call("POST", f"{BASE}/v2.1/{pid_pub}/cloudvolumes",
                    jbytes({"volume": {"size": 10, "name": "data-vol", "volume_type": "SAS"}}))
    check("volume create 202", st == 202 and body.get("job_id"))
    vol_id = body["volume_ids"][0]
    poll_job(pid_pub, body["job_id"])
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/cloudservers/{sid}/attachvolume",
                    jbytes({"volumeAttachment": {"volumeId": vol_id, "device": "/dev/vdb"}}))
    check("attach OK", st == 200 and body.get("job_id"))
    poll_job(pid_pub, body["job_id"])

    print("== 6. Ecs.0005 gold ==")
    st, body = call("POST", f"{BASE}/v2.1/{pid_pub}/cloudvolumes",
                    jbytes({"volume": {"size": 10, "name": "plain"}}))
    plain = body["volume_ids"][0]
    poll_job(pid_pub, body["job_id"])
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/cloudservers/{sid}/attachvolume",
                    jbytes({"volumeAttachment": {"volumeId": plain, "device": "/dev/vda"}}))
    check("non-bootable at vda → 400 Ecs.0005", st == 400 and body["error"]["code"] == "Ecs.0005"
          and body["error"]["message"] == "device is illegal")

    print("== 7. hcs quirks ==")
    for i in range(3):
        call("POST", f"{BASE}/v1.1/{pid_hcs}/cloudservers",
             jbytes({"server": {"imageRef": "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21",
                                 "flavorRef": "s7n.large.2", "name": "hcs-vm"}}))
    st, body = call("GET", f"{BASE}/v1/{pid_hcs}/cloudservers/detail")
    check("hcs default page size == 2", len(body["servers"]) == 2)
    st, body = call("GET", f"{BASE}/v1/{pid_hcs}/cloudservers/flavors")
    check("hcs flavors → 404", st == 404)

    print("== 8. VPC + EIP + SG ==")
    st, body = call("GET", f"{BASE}/v1/{pid_pub}/vpcs")
    check("vpcs listed", st == 200 and len(body["vpcs"]) >= 1)
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/publicips",
                    jbytes({"publicip": {"type": "5_bgp"},
                            "bandwidth": {"name": "bw", "size": 5, "share_type": "PER",
                                          "charge_mode": "traffic"}}))
    check("EIP allocated", st == 200 and body["publicip"]["status"] == "PENDING_CREATE")
    eip_id = body["publicip"]["id"]
    time.sleep(1.2)
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/security-groups",
                    jbytes({"security_group": {"name": "smoke-sg"}}))
    check("SG created with 4 rules", st == 201 and len(body["security_group"]["security_group_rules"]) == 4)
    sg_id = body["security_group"]["id"]
    st, body = call("POST", f"{BASE}/v1/{pid_pub}/security-group-rules",
                    jbytes({"security_group_rule": {"security_group_id": sg_id,
                                                     "direction": "ingress",
                                                     "remote_group_id": sg_id}}))
    check("duplicate rule → 409 SecurityGroupRuleExists", st == 409 and body["code"] == "SecurityGroupRuleExists")

    print("== 9. IMS ==")
    st, body = call("POST", f"{BASE}/v2/cloudimages/action",
                    jbytes({"name": "smoke-img", "image_url": "b:k.qcow2", "min_disk": 40}))
    check("image registered", st == 200 and body.get("job_id"))
    st, body = call("POST", f"{BASE}/v2/images",
                    jbytes({"name": "glance-img", "disk_format": "qcow2", "min_disk": 40}))
    check("Glance metadata created", st == 201 and body["status"] == "queued")
    st, _, _ = obs_call("PUT", "smoke-bucket")
    st, _, raw = obs_call("PUT", "smoke-bucket", "test-obj", body=b"hello world")
    check("OBS object uploaded", st == 200)
    st, _, raw = obs_call("GET", "smoke-bucket", "test-obj")
    check("OBS object read back", raw == b"hello world")

    print("== 10. CBR ==")
    st, body = call("POST", f"{BASE}/v3/{pid_pub}/vaults",
                    jbytes({"vault": {"name": "smoke-vault", "resources": []}}))
    check("vault created", st == 200 and body["vault"]["id"])
    vault_id = body["vault"]["id"]
    call("POST", f"{BASE}/v3/{pid_pub}/vaults/{vault_id}/addresources",
          jbytes({"resources": [{"id": sid, "type": "OS::Nova::Server"}]}))
    st, body = call("POST", f"{BASE}/v3/{pid_pub}/checkpoints",
                    jbytes({"checkpoint": {"resources": [{"id": sid, "type": "OS::Nova::Server"}]}}))
    check("checkpoint created (protecting)", st == 200 and body["checkpoint"]["status"] == "protecting")
    time.sleep(2)
    st, body = call("GET", f"{BASE}/v3/{pid_pub}/backups?resource_id={sid}")
    check("backup available", st == 200 and len(body["backups"]) >= 1
          and body["backups"][0]["status"] == "available")

    # cleanup
    call("DELETE", f"{BASE}/v1/{pid_pub}/publicips/{eip_id}")
    call("DELETE", f"{BASE}/v1/{pid_pub}/security-groups/{sg_id}")
    call("DELETE", f"{BASE}/v1/{pid_pub}/cloudservers/{sid}")
    obs_call("DELETE", "smoke-bucket", "test-obj")
    obs_call("DELETE", "smoke-bucket")

    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
