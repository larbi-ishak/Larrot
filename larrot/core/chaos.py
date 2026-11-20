"""Chaos engine: configurable fault injection (ROADMAP section 1.2).

Two modes:
- api: matched requests get the injected error response (with optional latency)
- job: matched create requests succeed at the API level, but the async job
  they submit FAILs (tests client polling/retry logic)

Rules match by service keyword (convenience) or raw path substring.
"""

import random
import time
from dataclasses import dataclass, field

from .jobs import new_id

# Best-effort service keyword map: a rule with service=X matches any request
# whose path contains one of the keywords.
SERVICE_KEYWORDS = {
    "ecs": ["cloudservers", "os-keypairs", "os-server-groups", "cloudservers/limits"],
    "evs": ["cloudvolumes", "cloudsnapshots", "os-vendor-volumes"],
    "vpc": ["/vpcs", "/subnets", "/ports", "security-groups"],
    "eip": ["publicips"],
    "ims": ["cloudimages", "/images"],
    "cbr": ["/vaults", "/checkpoints", "/backups"],
    "rds": ["/instances"],
    "dns": ["/zones"],
    "kms": ["/kms"],
    "elb": ["/elb"],
    "sfs": ["/shares"],
    "cce": ["/clusters"],
    "functiongraph": ["/fg/"],
    "bms": ["baremetalservers"],
    "as": ["scaling_group", "scaling_policy"],
    "smn": ["/notifications"],
    "ces": ["/alarms", "/metrics"],
    "lts": ["log-groups"],
    "dcs": ["/instances"],
    "dms": ["/instances"],
    "dds": ["/instances"],
    "waf": ["/waf"],
    "apig": ["apigw"],
    "swr": ["/namespaces"],
    "modelarts": ["notebooks", "training-jobs", "/models", "/services", "fine-tuning"],
    "maas": ["chat/completions", "/embeddings"],
    "iotda": ["/iot"],
    "gaussdb": ["/instances"],
    "aom": ["/aom"],
    "dli": ["/databases", "/tables"],
    "antiddos": ["antiddos"],
    "bss": ["/orders", "/accounts"],
    "nat": ["nat_gateways", "snat_rules", "dnat_rules"],
    "peering": ["vpc-peerings"],
    "acl": ["/acls"],
    "routes": ["/routes"],
    "vpn": ["vpn-gateways", "vpn-connections"],
    "hss": ["/hosts", "/policy", "/alarm-events", "/vulnerabilities"],
    "cdn": ["/domains", "purgecache", "preheating"],
    "dws": ["dws/clusters", "/clusters"],
    "css": ["css/clusters"],
    "mrs": ["cluster_infos"],
    "sms": ["/sources", "/tasks", "/templates"],
    "dc": ["direct-connects", "virtual-gateways", "virtual-interfaces"],
    "er": ["enterprise-router"],
    "dis": ["/streams", "/apps"],
    "dataarts": ["/connections", "/jobs", "/scripts"],
    "oms": ["/tasks"],
    "des": ["des/tasks"],
    "codearts": ["repositories", "/pipelines", "/builds"],
    "servicestage": ["/cas/"],
    "cse": ["/engines"],
    "cci": ["/cci/"],
    "cfw": ["/firewalls"],
    "dsc": ["/dsc/"],
    "vod": ["/assets", "transcode-templates"],
    "ief": ["edgemgr"],
}


@dataclass
class ChaosRule:
    rule_id: str
    failure_rate: float
    mode: str                      # "api" | "job"
    service: str = ""
    path_contains: str = ""
    method: str = ""               # optional: only this HTTP method
    status: int = 500
    error_code: str = "SIM.CHAOS"
    error_msg: str = "Injected by chaos rule"
    latency_ms: int = 0
    created_at: float = field(default_factory=time.time)

    def matches(self, method: str, path: str) -> bool:
        if self.method and method.upper() != self.method.upper():
            return False
        if self.path_contains:
            return self.path_contains in path
        for kw in SERVICE_KEYWORDS.get(self.service, []):
            if kw in path:
                return True
        return False

    def to_json(self) -> dict:
        return {
            "rule_id": self.rule_id, "service": self.service or self.path_contains,
            "mode": self.mode, "failure_rate": self.failure_rate,
            "method": self.method or "ANY", "status": self.status,
            "error_code": self.error_code, "error_msg": self.error_msg,
            "latency_ms": self.latency_ms,
        }


class ChaosEngine:
    """Holds chaos rules; consulted by the gateway middleware and job engine."""

    def __init__(self):
        self.rules: dict[str, ChaosRule] = {}
        self._pending_job_failure: ChaosRule | None = None

    def add(self, spec: dict) -> dict:
        service = spec.get("service", "")
        path_contains = spec.get("path_contains", "")
        if not service and not path_contains:
            raise ValueError("service or path_contains is required")
        if service and service not in SERVICE_KEYWORDS:
            raise ValueError(f"unknown service '{service}'")
        rate = spec.get("failure_rate", 1.0)
        if not isinstance(rate, (int, float)) or not (0.0 <= rate <= 1.0):
            raise ValueError("failure_rate must be between 0.0 and 1.0")
        mode = spec.get("mode", "api")
        if mode not in ("api", "job"):
            raise ValueError("mode must be 'api' or 'job'")
        rule = ChaosRule(
            rule_id=new_id(), failure_rate=float(rate), mode=mode,
            service=service, path_contains=path_contains,
            method=spec.get("method", ""),
            status=spec.get("status", 500),
            error_code=spec.get("error_code", "SIM.CHAOS"),
            error_msg=spec.get("error_msg", "Injected by chaos rule"),
            latency_ms=spec.get("latency_ms", 0),
        )
        self.rules[rule.rule_id] = rule
        return rule.to_json()

    def remove(self, rule_id: str) -> bool:
        return self.rules.pop(rule_id, None) is not None

    def reset(self) -> int:
        n = len(self.rules)
        self.rules.clear()
        self._pending_job_failure = None
        return n

    def list(self) -> list[dict]:
        return [r.to_json() for r in self.rules.values()]

    def maybe_inject(self, method: str, path: str):
        """Return (status, body, latency_ms) if a rule fires, else None."""
        for rule in self.rules.values():
            if rule.mode != "api" or not rule.matches(method, path):
                continue
            if random.random() < rule.failure_rate:
                body = {"error_code": rule.error_code,
                        "error_msg": rule.error_msg,
                        "chaos_rule_id": rule.rule_id}
                return rule.status, body, rule.latency_ms
        return None

    def maybe_mark_job_failure(self, method: str, path: str) -> bool:
        """Mark the next submitted job to FAIL if a job-mode rule fires."""
        for rule in self.rules.values():
            if rule.mode != "job" or not rule.matches(method, path):
                continue
            if random.random() < rule.failure_rate:
                self._pending_job_failure = rule
                return True
        return False

    def consume_job_failure(self):
        """Called by the job engine: return the rule that should fail this job."""
        rule = self._pending_job_failure
        self._pending_job_failure = None
        return rule
