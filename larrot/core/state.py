"""Shared simulator state + seed data (the 'lab account')."""

import os

from .jobs import JobEngine, new_id, now_millis
from .profiles import Profile
from .ratelimit import RateLimiter


class SimState:
    """Single source of truth: every service reads and mutates this."""

    def __init__(self):
        self.profile_default = Profile.parse(os.environ.get("SIM_PROFILE", "public"))
        self.jobs = JobEngine()
        self.limiter = RateLimiter()
        # accept: log signature mismatches, never reject (default).
        # enforce: reject with Huawei's APIGW auth errors (SIM_IAM=enforce).
        self.iam_mode = os.environ.get("SIM_IAM", "accept").lower()
        # Request journal: bounded, in-memory, queryable via /admin/requests
        from .journal import RequestJournal
        self.journal = RequestJournal(
            int(os.environ.get("SIM_JOURNAL_SIZE", "1000")))

        # Account
        self.account = {
            "domain_id": "7b04940625a24928b8ab5c51552e658e",
            "name": "sim-lab",
            "ak": os.environ.get("SIM_AK", "HWYSIMAK00000001"),
            "sk": os.environ.get("SIM_SK", "HWYSIMSK00000001"),
        }

        # Projects (one per region, each with its own quirk profile)
        self.projects = [
            {
                "id": "79814d675f6142d9b4a8ee417b924444",
                "name": "ap-southeast-1",
                "domain_id": self.account["domain_id"],
                "profile": Profile.PUBLIC,
                "vpc_id": "3ec3b33f-ac1c-4630-ad1c-7dba1ed79d85",
                "vpc_name": "vpc-ap-southeast-1",
                "subnet_id": "70f2e74b-e660-410a-b754-0ca46744348a",
                "subnet_cidr": "192.168.0.0/24",
                "gateway_ip": "192.168.0.1",
            },
            {
                "id": "93c9dfbe6c9e45409fac947d042e6676",
                "name": "tr-west-1",
                "domain_id": self.account["domain_id"],
                "profile": Profile.HCS,
                "vpc_id": "164489f6-cbf7-45b4-b6d0-d407c48cf7fc",
                "vpc_name": "vpc-tr-west-1",
                "subnet_id": "8a3e74bb-1234-410a-b754-0ca46744348b",
                "subnet_cidr": "192.168.0.0/24",
                "gateway_ip": "192.168.0.1",
            },
        ]

        # Images
        self.images: dict[str, dict] = {}
        for img in [
            {"id": "1ce5800a-e487-4c1b-b264-3353a39e2b4b", "name": "Ubuntu 22.04 server 64bit",
             "os_type": "Linux", "os_version": "Ubuntu 22.04 server 64bit",
             "min_disk": 40, "reset_agent": True, "status": "active",
             "disk_format": "qcow2", "visibility": "private"},
            {"id": "d4b8e2b1-7c5a-4f31-9e2d-8b1f6a9c0d21", "name": "replica-gold",
             "os_type": "Linux", "os_version": "CentOS 7.9 64bit",
             "min_disk": 40, "reset_agent": False, "status": "active",
             "disk_format": "qcow2", "visibility": "private"},
        ]:
            img["created_at"] = now_millis()
            img["updated_at"] = now_millis()
            img["project_id"] = self.account["domain_id"]
            self.images[img["id"]] = img

        # Flavors
        self.flavors = [
            {"id": "s6.large.2", "name": "s6.large.2", "vcpus": "2", "ram": "4096", "disk": "0",
             "regions": ["ap-southeast-1"]},
            {"id": "s7n.large.2", "name": "s7n.large.2", "vcpus": "2", "ram": "4096", "disk": "0",
             "regions": ["tr-west-1"]},
        ]

        # Resource stores (id -> dict)
        self.servers: dict[str, dict] = {}
        self.volumes: dict[str, dict] = {}
        self.snapshots: dict[str, dict] = {}
        self.ports: dict[str, dict] = {}
        self.vpcs: dict[str, dict] = {}
        self.subnets: dict[str, dict] = {}
        self.eips: dict[str, dict] = {}
        self.security_groups: dict[str, dict] = {}
        self.obs_buckets: dict[str, dict] = {}
        self.obs_objects: dict[str, dict] = {}  # key: "{bucket}/{key}"
        self.obs_uploads: dict[str, dict] = {}
        self.vaults: dict[str, dict] = {}
        self.cbr_policies: dict[str, dict] = {}
        self.cbr_backups: dict[str, dict] = {}
        self.checkpoints: dict[str, dict] = {}

        # Seed default VPC + subnet per project
        for p in self.projects:
            now = now_millis()
            self.vpcs[p["vpc_id"]] = {
                "id": p["vpc_id"], "name": p["vpc_name"], "description": "",
                "cidr": p["subnet_cidr"], "status": "OK",
                "created_at": now, "updated_at": now, "project_id": p["id"],
            }
            self.subnets[p["subnet_id"]] = {
                "id": p["subnet_id"], "name": f"{p['vpc_name']}-subnet", "description": "",
                "cidr": p["subnet_cidr"], "gateway_ip": p["gateway_ip"],
                "dhcp_enable": True, "primary_dns": "100.125.0.41", "secondary_dns": "100.125.1.41",
                "availability_zone": "", "vpc_id": p["vpc_id"], "status": "ACTIVE",
                "created_at": now, "updated_at": now, "project_id": p["id"],
            }

    # -----------------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------------

    def project(self, pid: str) -> dict | None:
        return next((p for p in self.projects if p["id"] == pid), None)

    def profile_of(self, pid: str) -> Profile:
        p = self.project(pid)
        return p["profile"] if p else self.profile_default

    def find_sk(self, ak: str) -> str | None:
        return self.account["sk"] if ak == self.account["ak"] else None

    def next_ip(self, pid: str) -> str:
        used = sum(1 for p in self.ports.values() if p["project_id"] == pid)
        return f"192.168.0.{10 + used}"

    def create_volume(self, pid, name, size, az, vtype, bootable, source=None):
        vid = new_id()
        now = now_millis()
        vol = {
            "id": vid, "name": name, "size": size, "status": "creating",
            "bootable": "true" if bootable else "false",
            "availability_zone": az, "volume_type": vtype,
            "attachments": [], "description": "",
            "created_at": now, "updated_at": now,
            "metadata": {}, "encrypted": False, "multiattach": False,
            "user_id": "b44a37e1192442acaa0d578b63e38fe3",
            "tags": {}, "wwn": f" {new_id()}", "project_id": pid,
        }
        if source:
            kind, src = source
            vol["metadata"]["__system__root"] = kind
            vol["metadata"][f"__{kind.replace('Ref', '')}__"] = src
        self.volumes[vid] = vol
        return vid
