"""hcli — the huawei-sim CLI. Table output by default, --json for raw, --wait for async."""

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.request
import urllib.error
from .core.signing import sign_sdk_request, sign_obs_request

DEFAULT_ENDPOINT = "http://127.0.0.1:8200"
DEFAULT_OBS = "http://127.0.0.1:8201"
DEFAULT_AK = "HWYSIMAK00000001"
DEFAULT_SK = "HWYSIMSK00000001"
DEFAULT_PROJECT = "ap-southeast-1"


class Client:
    def __init__(self, endpoint, obs_endpoint, ak, sk, project):
        self.endpoint = endpoint.rstrip("/")
        self.obs_endpoint = obs_endpoint.rstrip("/")
        self.ak, self.sk = ak, sk
        self.project_name = project
        self._pid = None

    def pid(self):
        if self._pid:
            return self._pid
        body = self.get("/v3/projects")
        for p in body["projects"]:
            if p["name"] == self.project_name:
                self._pid = p["id"]
                return self._pid
        raise RuntimeError(f"project '{self.project_name}' not found")

    def _host(self):
        return self.endpoint.split("//")[1]

    def _request(self, method, path, body=None):
        url = self.endpoint + path
        data = json.dumps(body).encode() if body else b""
        p, _, q = path.partition("?")
        headers = sign_sdk_request(method, p, q or None, self._host(), data, self.ak, self.sk)
        req = urllib.request.Request(url, data=data if body else None, headers={
            "Content-Type": "application/json", **headers}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            text = e.read().decode()
            try:
                v = json.loads(text)
                code = v.get("error", {}).get("code") or v.get("error_code") or v.get("code") or "?"
                msg = v.get("error", {}).get("message") or v.get("error_msg") or v.get("message") or text
                raise RuntimeError(f"[{code}] {msg}")
            except json.JSONDecodeError:
                raise RuntimeError(f"HTTP {e.code}: {text[:200]}")

    def get(self, path): return self._request("GET", path)
    def post(self, path, body): return self._request("POST", path, body)
    def put(self, path, body): return self._request("PUT", path, body)
    def delete(self, path): return self._request("DELETE", path)

    def wait_job(self, job_id, timeout=30):
        for _ in range(timeout * 2):
            time.sleep(0.5)
            job = self.get(f"/v1/{self.pid()}/jobs/{job_id}")
            if job["status"] in ("SUCCESS", "FAIL"):
                if job["status"] == "FAIL":
                    raise RuntimeError(f"Job FAILED: {job.get('error_code')} — {job.get('fail_reason')}")
                return job
        raise RuntimeError(f"Job {job_id} timed out")

    # OBS
    def obs_request(self, method, bucket, key="", query="", data=b""):
        path = f"/{bucket}/{key}" if key else f"/{bucket}" if bucket else "/"
        url = self.obs_endpoint + path + (f"?{query}" if query else "")
        host = self.obs_endpoint.split("//")[1]
        headers = sign_obs_request(method, bucket, key, query or None, host, data,
                                    "application/octet-stream", self.ak, self.sk)
        req = urllib.request.Request(url, data=data if method in ("PUT", "POST") else None,
                                     headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    def obs_get_text(self, bucket, query=""):
        return self.obs_request("GET", bucket, query=query).decode()

    def obs_get_raw(self, bucket, key):
        return self.obs_request("GET", bucket, key)

    def obs_put(self, bucket, key, data):
        self.obs_request("PUT", bucket, key, data=data)

    def obs_delete(self, bucket, key):
        self.obs_request("DELETE", bucket, key)


# ---------------------------------------------------------------------------
# table formatting
# ---------------------------------------------------------------------------

def table(headers, rows, title=""):
    if title:
        print(title)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "─" * (sum(widths) + len(widths) * 2 + 1)
    print(sep)
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for row in rows:
        print("  " + "  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
    print(sep)
    print(f"  {len(rows)} item(s)\n")


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(prog="hcli", description="Huawei Cloud simulator CLI")
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p.add_argument("--obs-endpoint", default=DEFAULT_OBS)
    p.add_argument("--ak", default=DEFAULT_AK)
    p.add_argument("--sk", default=DEFAULT_SK)
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--json", action="store_true", help="raw JSON output")
    p.add_argument("--wait", action="store_true", help="wait for async jobs")
    sub = p.add_subparsers(dest="cmd", required=True)

    # projects
    sub.add_parser("projects")

    # ecs
    ecs_p = sub.add_parser("ecs")
    ecs_sub = ecs_p.add_subparsers(dest="action", required=True)
    ecs_sub.add_parser("list")
    ecs_show = ecs_sub.add_parser("show"); ecs_show.add_argument("id")
    ecs_create = ecs_sub.add_parser("create")
    ecs_create.add_argument("--image", required=True)
    ecs_create.add_argument("--flavor", required=True)
    ecs_create.add_argument("--name", required=True)
    ecs_create.add_argument("--count", type=int, default=1)
    ecs_stop = ecs_sub.add_parser("stop"); ecs_stop.add_argument("id"); ecs_stop.add_argument("--hard", action="store_true")
    ecs_start = ecs_sub.add_parser("start"); ecs_start.add_argument("id")
    ecs_del = ecs_sub.add_parser("delete"); ecs_del.add_argument("id"); ecs_del.add_argument("--delete-volume", action="store_true")
    ecs_att = ecs_sub.add_parser("attach"); ecs_att.add_argument("id")
    ecs_att.add_argument("--volume", required=True); ecs_att.add_argument("--device", default="/dev/vdb")
    ecs_det = ecs_sub.add_parser("detach"); ecs_det.add_argument("id"); ecs_det.add_argument("--volume", required=True)
    ecs_sub.add_parser("flavors")
    ecs_blk = ecs_sub.add_parser("blocks"); ecs_blk.add_argument("id")

    # evs
    evs_p = sub.add_parser("evs")
    evs_sub = evs_p.add_subparsers(dest="action", required=True)
    evs_sub.add_parser("list")
    evs_show = evs_sub.add_parser("show"); evs_show.add_argument("id")
    evs_create = evs_sub.add_parser("create")
    evs_create.add_argument("--size", type=int, required=True)
    evs_create.add_argument("--name", required=True)
    evs_create.add_argument("--from-image")
    evs_del = evs_sub.add_parser("delete"); evs_del.add_argument("id")
    evs_ext = evs_sub.add_parser("extend"); evs_ext.add_argument("id"); evs_ext.add_argument("--new-size", type=int, required=True)
    evs_snap = evs_sub.add_parser("snapshot"); evs_snap.add_argument("id"); evs_snap.add_argument("--name", required=True)
    evs_sub.add_parser("snapshots")

    # vpc / eip / sg
    vpc_p = sub.add_parser("vpc"); vpc_sub = vpc_p.add_subparsers(dest="action", required=True)
    vpc_sub.add_parser("vpcs"); vpc_sub.add_parser("subnets")
    eip_p = sub.add_parser("eip"); eip_sub = eip_p.add_subparsers(dest="action", required=True)
    eip_sub.add_parser("list")
    eip_alloc = eip_sub.add_parser("allocate"); eip_alloc.add_argument("--size", type=int, default=5)
    eip_bind = eip_sub.add_parser("bind"); eip_bind.add_argument("id"); eip_bind.add_argument("--server", required=True)
    eip_unb = eip_sub.add_parser("unbind"); eip_unb.add_argument("id")
    eip_rel = eip_sub.add_parser("release"); eip_rel.add_argument("id")
    sg_p = sub.add_parser("sg"); sg_sub = sg_p.add_subparsers(dest="action", required=True)
    sg_sub.add_parser("list")
    sg_cr = sg_sub.add_parser("create"); sg_cr.add_argument("--name", required=True)

    # ims / cbr / obs / jobs
    ims_p = sub.add_parser("ims"); ims_sub = ims_p.add_subparsers(dest="action", required=True)
    ims_sub.add_parser("list")
    ims_reg = ims_sub.add_parser("register")
    ims_reg.add_argument("--bucket", required=True); ims_reg.add_argument("--key", required=True)
    ims_reg.add_argument("--name", required=True)
    cbr_p = sub.add_parser("cbr"); cbr_sub = cbr_p.add_subparsers(dest="action", required=True)
    cbr_sub.add_parser("vaults")
    cbr_cv = cbr_sub.add_parser("create-vault"); cbr_cv.add_argument("--name", required=True)
    cbr_bind = cbr_sub.add_parser("bind"); cbr_bind.add_argument("--vault", required=True); cbr_bind.add_argument("--server", required=True)
    cbr_bk = cbr_sub.add_parser("backup"); cbr_bk.add_argument("--server", required=True); cbr_bk.add_argument("--vault", required=True)
    cbr_bks = cbr_sub.add_parser("backups"); cbr_bks.add_argument("--server")
    cbr_res = cbr_sub.add_parser("restore"); cbr_res.add_argument("id")
    obs_p = sub.add_parser("obs"); obs_sub = obs_p.add_subparsers(dest="action", required=True)
    obs_sub.add_parser("buckets")
    obs_ls = obs_sub.add_parser("ls"); obs_ls.add_argument("--bucket", default="obs-sim"); obs_ls.add_argument("--prefix")
    obs_put = obs_sub.add_parser("put"); obs_put.add_argument("--bucket", required=True)
    obs_put.add_argument("--key", required=True); obs_put.add_argument("file")
    obs_get = obs_sub.add_parser("get"); obs_get.add_argument("--bucket", required=True)
    obs_get.add_argument("--key", required=True); obs_get.add_argument("--output", default="-")
    obs_rm = obs_sub.add_parser("rm"); obs_rm.add_argument("--bucket", required=True); obs_rm.add_argument("--key", required=True)
    jobs_p = sub.add_parser("jobs"); jobs_sub = jobs_p.add_subparsers(dest="action", required=True)
    jobs_get = jobs_sub.add_parser("get"); jobs_get.add_argument("id")

    args = p.parse_args()
    c = Client(args.endpoint, args.obs_endpoint, args.ak, args.sk, args.project)
    _dispatch(c, args)


def _dispatch(c, args):
    j = args.json
    w = args.wait

    if args.cmd == "projects":
        r = c.get("/v3/projects")
        if j: print(json.dumps(r, indent=2)); return
        table(["ID", "NAME", "DOMAIN_ID"],
              [(p["id"], p["name"], p["domain_id"]) for p in r["projects"]], "PROJECTS")

    elif args.cmd == "ecs":
        pid = c.pid()
        if args.action == "list":
            r = c.get(f"/v1/{pid}/cloudservers/detail?limit=100")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "STATUS", "FLAVOR", "TASK"],
                  [(s["id"][:12], s["name"], s["status"],
                    s.get("flavor", {}).get("id", "-"),
                    s.get("OS-EXT-STS:task_state") or "-")
                   for s in r["servers"]], f"SERVERS ({args.project})")
        elif args.action == "show":
            print(json.dumps(c.get(f"/v1/{pid}/cloudservers/{args.id}"), indent=2))
        elif args.action == "create":
            body = {"server": {"imageRef": args.image, "flavorRef": args.flavor,
                                "name": args.name, "count": args.count}}
            r = c.post(f"/v1.1/{pid}/cloudservers", body)
            print(f"Created: {', '.join(r['serverIds'])}")
            if w: c.wait_job(r["job_id"]); print("Job SUCCESS")
            else: print(f"Job: {r['job_id']}")
        elif args.action == "stop":
            body = {"os-stop": {"type": "HARD" if args.hard else "SOFT", "servers": [{"id": args.id}]}}
            r = c.post(f"/v1/{pid}/cloudservers/action", body)
            print(f"Stopping {args.id}… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Server stopped.")
        elif args.action == "start":
            r = c.post(f"/v1/{pid}/cloudservers/action", {"os-start": {"servers": [{"id": args.id}]}})
            print(f"Starting {args.id}… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Server started.")
        elif args.action == "delete":
            body = {"servers": [{"id": args.id}], "delete_volume": args.delete_volume}
            r = c.post(f"/v1/{pid}/cloudservers/delete", body)
            print(f"Deleting {args.id}… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Server deleted.")
        elif args.action == "attach":
            body = {"volumeAttachment": {"volumeId": args.volume, "device": args.device}}
            r = c.post(f"/v1/{pid}/cloudservers/{args.id}/attachvolume", body)
            print(f"Attaching… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Attached.")
        elif args.action == "detach":
            r = c.delete(f"/v1/{pid}/cloudservers/{args.id}/attachvolume/{args.volume}")
            print(f"Detaching… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Detached.")
        elif args.action == "flavors":
            r = c.get(f"/v1/{pid}/cloudservers/flavors")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "vCPU", "RAM"],
                  [(f["id"], f["vcpus"], f["ram"]) for f in r["flavors"]], "FLAVORS")
        elif args.action == "blocks":
            r = c.get(f"/v1/{pid}/cloudservers/{args.id}/block_device")
            if j: print(json.dumps(r, indent=2)); return
            table(["VOLUME", "DEVICE", "SIZE", "BOOT"],
                  [(b["volumeId"][:12], b["device"], b["size"], b["bootIndex"])
                   for b in r["volumeAttachments"]], "BLOCK DEVICES")

    elif args.cmd == "evs":
        pid = c.pid()
        if args.action == "list":
            r = c.get(f"/v2/{pid}/cloudvolumes/detail")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "STATUS", "SIZE", "BOOTABLE", "TYPE"],
                  [(v["id"][:12], v["name"], v["status"], v["size"],
                    v["bootable"], v["volume_type"]) for v in r["volumes"]], "VOLUMES")
        elif args.action == "show":
            print(json.dumps(c.get(f"/v2/{pid}/cloudvolumes/{args.id}"), indent=2))
        elif args.action == "create":
            vol = {"size": args.size, "name": args.name, "volume_type": "SAS"}
            if args.from_image:
                vol["imageRef"] = args.from_image
            r = c.post(f"/v2.1/{pid}/cloudvolumes", {"volume": vol})
            print(f"Created: {', '.join(r['volume_ids'])}")
            if w: c.wait_job(r["job_id"]); print("Volume available.")
        elif args.action == "delete":
            r = c.delete(f"/v2/{pid}/cloudvolumes/{args.id}")
            print(f"Deleting… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Volume deleted.")
        elif args.action == "extend":
            r = c.post(f"/v2.1/{pid}/cloudvolumes/{args.id}/action",
                       {"os-extend": {"new_size": args.new_size}})
            print(f"Extending to {args.new_size}G… job: {r['job_id']}")
            if w: c.wait_job(r["job_id"]); print("Volume extended.")
        elif args.action == "snapshot":
            r = c.post(f"/v2/{pid}/cloudsnapshots",
                       {"snapshot": {"volume_id": args.id, "name": args.name}})
            print(json.dumps(r, indent=2))
        elif args.action == "snapshots":
            r = c.get(f"/v2/{pid}/snapshots/detail")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "STATUS", "VOLUME", "SIZE"],
                  [(s["id"][:12], s["name"], s["status"], s["volume_id"][:12], s["size"])
                   for s in r["snapshots"]], "SNAPSHOTS")

    elif args.cmd == "vpc":
        pid = c.pid()
        if args.action == "vpcs":
            r = c.get(f"/v1/{pid}/vpcs")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "CIDR", "STATUS"],
                  [(v["id"][:12], v["name"], v["cidr"], v["status"]) for v in r["vpcs"]], "VPCs")
        elif args.action == "subnets":
            r = c.get(f"/v1/{pid}/subnets")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "CIDR", "GATEWAY"],
                  [(s["id"][:12], s["name"], s["cidr"], s["gateway_ip"]) for s in r["subnets"]], "SUBNETS")

    elif args.cmd == "eip":
        pid = c.pid()
        if args.action == "list":
            r = c.get(f"/v1/{pid}/publicips")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "IP", "STATUS", "BANDWIDTH", "PORT"],
                  [(e["id"][:12], e["public_ip_address"], e["status"],
                    e["bandwidth_size"], e.get("port_id", "-") or "-")
                   for e in r["publicips"]], "EIPs")
        elif args.action == "allocate":
            body = {"publicip": {"type": "5_bgp"},
                    "bandwidth": {"name": "hcli-bw", "size": args.size, "share_type": "PER",
                                  "charge_mode": "traffic"}}
            r = c.post(f"/v1/{pid}/publicips", body)
            print(f"Allocated: {r['publicip']['public_ip_address']}")
        elif args.action == "bind":
            ports = c.get(f"/v1/{pid}/ports?device_id={args.server}")
            port_id = ports["ports"][0]["id"]
            r = c.put(f"/v1/{pid}/publicips/{args.id}", {"publicip": {"port_id": port_id}})
            print(f"Bound {args.id} → {args.server}")
        elif args.action == "unbind":
            r = c.put(f"/v1/{pid}/publicips/{args.id}", {"publicip": {"port_id": ""}})
            print(f"Unbound {args.id}")
        elif args.action == "release":
            c.delete(f"/v1/{pid}/publicips/{args.id}")
            print(f"Released {args.id}")

    elif args.cmd == "sg":
        pid = c.pid()
        if args.action == "list":
            r = c.get(f"/v1/{pid}/security-groups")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "RULES"],
                  [(g["id"][:12], g["name"], len(g["security_group_rules"]))
                   for g in r["security_groups"]], "SECURITY GROUPS")
        elif args.action == "create":
            r = c.post(f"/v1/{pid}/security-groups", {"security_group": {"name": args.name}})
            print(f"Created: {args.name} ({r['security_group']['id']})")

    elif args.cmd == "ims":
        if args.action == "list":
            r = c.get("/v2/images")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "STATUS", "FORMAT"],
                  [(i["id"][:12], i["name"], i["status"], i["disk_format"])
                   for i in r["images"]], "IMAGES")
        elif args.action == "register":
            body = {"name": args.name, "image_url": f"{args.bucket}:{args.key}", "min_disk": 40}
            r = c.post("/v2/cloudimages/action", body)
            print(f"Registering… job: {r['job_id']}")

    elif args.cmd == "cbr":
        pid = c.pid()
        if args.action == "vaults":
            r = c.get(f"/v3/{pid}/vaults")
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "RESOURCES"],
                  [(v["id"][:12], v["name"], len(v["resources"])) for v in r["vaults"]], "VAULTS")
        elif args.action == "create-vault":
            r = c.post(f"/v3/{pid}/vaults", {"vault": {"name": args.name, "resources": []}})
            print(f"Vault created: {r['vault']['id']}")
        elif args.action == "bind":
            body = {"resources": [{"id": args.server, "type": "OS::Nova::Server"}]}
            c.post(f"/v3/{pid}/vaults/{args.vault}/addresources", body)
            print(f"Bound {args.server} to vault {args.vault}")
        elif args.action == "backup":
            body = {"checkpoint": {"resources": [{"id": args.server, "type": "OS::Nova::Server"}],
                                    "name": "hcli-backup"}}
            r = c.post(f"/v3/{pid}/checkpoints", body)
            print(f"Checkpoint: {r['checkpoint']['id']} ({r['checkpoint']['status']})")
        elif args.action == "backups":
            path = f"/v3/{pid}/backups" + (f"?resource_id={args.server}" if args.server else "")
            r = c.get(path)
            if j: print(json.dumps(r, indent=2)); return
            table(["ID", "NAME", "STATUS", "RESOURCE"],
                  [(b["id"][:12], b["name"], b["status"], b["resource_id"][:12])
                   for b in r["backups"]], "BACKUPS")
        elif args.action == "restore":
            r = c.post(f"/v3/{pid}/backups/{args.id}/restore", {"restore": {"power_on": False}})
            print(f"Restored → new volume: {r['restore']['volume_id']}")

    elif args.cmd == "obs":
        if args.action == "buckets":
            xml = c.obs_get_text("")
            import re
            names = re.findall(r"<Name>([^<]+)</Name>", xml)
            if j: print(json.dumps({"buckets": names}, indent=2)); return
            table(["NAME"], [(n,) for n in names], "BUCKETS")
        elif args.action == "ls":
            q = f"prefix={args.prefix}" if args.prefix else ""
            xml = c.obs_get_text(args.bucket, q)
            import re
            keys = re.findall(r"<Key>([^<]+)</Key>", xml)
            sizes = re.findall(r"<Size>(\d+)</Size>", xml)
            if j: print(json.dumps({"keys": keys}, indent=2)); return
            table(["KEY", "SIZE"], list(zip(keys, sizes)), f"s3://{args.bucket}")
        elif args.action == "put":
            data = open(args.file, "rb").read()
            c.obs_put(args.bucket, args.key, data)
            print(f"Uploaded {args.file} → s3://{args.bucket}/{args.key} ({len(data)} bytes)")
        elif args.action == "get":
            data = c.obs_get_raw(args.bucket, args.key)
            if args.output == "-":
                sys.stdout.buffer.write(data)
            else:
                open(args.output, "wb").write(data)
                print(f"Downloaded → {args.output} ({len(data)} bytes)")
        elif args.action == "rm":
            c.obs_delete(args.bucket, args.key)
            print(f"Deleted s3://{args.bucket}/{args.key}")

    elif args.cmd == "jobs":
        pid = c.pid()
        if w:
            c.wait_job(args.id)
        r = c.get(f"/v1/{pid}/jobs/{args.id}")
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
