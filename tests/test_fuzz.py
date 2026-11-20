"""Request-level fuzzing across every documented operation (720 ops).

The invariant: the API must NEVER answer 5xx. Every request either
succeeds (2xx) or is rejected with a proper client error (4xx). A 500
means a handler crashed on malformed input - which is a fidelity bug,
because the real cloud returns a 4xx error envelope, never a crash.

For each operation in the coverage registry, four adversarial variants:
  A. valid-looking path, empty body
  B. valid-looking path, wrong-typed body
  C. garbage path parameters
  D. unicode + oversized path parameters

Deterministic (no RNG): every failure is reproducible.
"""
import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from coverage import REGISTRY, ALIASES  # noqa: E402

from larrot.app import create_app, create_obs_app  # noqa: E402

PID = "79814d675f6142d9b4a8ee417b924444"
HCS_PID = "93c9dfbe6c9e45409fac947d042e6676"

# ---------------------------------------------------------------------------
# fixture: one app for the whole fuzz session, with real resources to hit
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    c = TestClient(create_app(), raise_server_exceptions=False)
    # seed real resources so "valid" paths reach deep handler code
    c.post("/admin/preset/three-tier-app")
    c.post("/admin/preset/dr")
    c.app.state.sim.jobs.complete_all()
    # a few extras the presets don't cover
    c.post(f"/v2.1/{PID}/cloudvolumes", json={"volume": {"size": 10, "name": "fuzz-vol"}})
    c.app.state.sim.jobs.complete_all()
    c.post("/v2/zones", json={"name": "fuzz.example.com.", "email": "f@z.com"})
    c.post(f"/v1/{PID}/kms/create-key", json={"key_alias": "fuzz-key"})
    c.post("/v3/users", json={"name": "fuzz-user"})
    c.post("/v3/groups", json={"name": "fuzz-group"})
    c.put("/v3.0/OS-FEDERATION/identity_providers", json={"id": "fuzz-idp"})
    c.put("/v3.0/OS-FEDERATION/mappings", json={"id": "fuzz-map"})
    c.put("/v3.0/OS-FEDERATION/identity_providers/fuzz-idp/protocols/saml",
          json={"mapping_id": "fuzz-map"})
    c.post("/v3.0/OS-CREDENTIAL/credentials", json={"description": "fuzz"})
    c.post(f"/v2/{PID}/datasets", json={"dataset_name": "fuzz-ds"})
    c.post(f"/v2/{PID}/notifications/topics", json={"name": "fuzz-topic"})
    c.post(f"/v2/{PID}/notifications/message_templates",
           json={"message_template_name": "fuzz-tpl"})
    c.post(f"/v2/{PID}/streams", json={"stream_name": "fuzz-stream"})
    c.post(f"/v2/{PID}/apps", json={"app_name": "fuzz-app"})
    c.post(f"/v1.0/{PID}/queues", json={"queue_name": "fuzz-queue"})
    c.post(f"/v1.0/{PID}/databases", json={"database_name": "fuzzdb"})
    c.post(f"/v2/{PID}/log-groups", json={"log_group_name": "fuzz-group"})
    gid = c.get(f"/v2/{PID}/log-groups").json()["log_groups"][-1]["id"]
    c.post(f"/v2/{PID}/log-groups/{gid}/log-streams", json={"log_stream_name": "fs"})
    c.post(f"/v2/{PID}/elb/loadbalancers", json={"loadbalancer": {"name": "fuzz-lb"}})
    c.post(f"/v2/{PID}/elb/healthmonitors", json={"healthmonitor": {"type": "TCP"}})
    c.post(f"/v2/{PID}/apigw/instances", json={"name": "fuzz-inst"})
    c.post(f"/v2/{PID}/apigw/groups", json={"name": "fuzz-grp"})
    c.post(f"/v2/{PID}/apigw/apis", json={"name": "fuzz-api"})
    c.post(f"/v2/{PID}/apigw/apps", json={"name": "fuzz-app"})
    c.post(f"/v2/{PID}/apigw/environments", json={"name": "fuzz-env"})
    c.post(f"/v2/{PID}/apigw/throttles", json={"name": "fuzz-th"})
    c.post(f"/v2/{PID}/apigw/authorizers", json={"name": "fuzz-auth"})
    c.post(f"/v1/{PID}/alarms", json={"alarm_name": "fuzz-alarm"})
    c.post(f"/v1/{PID}/scaling_group", json={"scaling_group_name": "fuzz-asg"})
    c.post(f"/v1/{PID}/scaling_policy", json={"scaling_policy_name": "fuzz-pol"})
    c.post(f"/v1/{PID}/baremetalservers", json={"name": "fuzz-bms"})
    c.post(f"/v3/{PID}/vaults", json={"vault": {"name": "fuzz-vault", "resources": []}})
    c.post(f"/v3/{PID}/policies", json={"policy": {"name": "fuzz-pol"}})
    c.post(f"/v3/{PID}/configurations", json={"name": "fuzz-cfg"})
    c.post(f"/v5/iot/{PID}/products", json={"product_name": "fuzz-prod"})
    c.post(f"/v5/iot/{PID}/devices", json={"device_name": "fuzz-dev"})
    c.post(f"/v2/{PID}/namespaces", json={"namespace": "fuzz-ns"})
    c.post(f"/v2/{PID}/namespaces/fuzz-ns/repos", json={"repository": "fuzz-repo"})
    c.post(f"/v1/{PID}/waf/hosts", json={"hostname": "fuzz.example.com"})
    c.post(f"/v1/{PID}/vpc/acls", json={"name": "fuzz-acl"})
    c.post(f"/v1/{PID}/vpc/routetables", json={"name": "fuzz-rt"})
    c.post(f"/v2.0/{PID}/vpc-peerings", json={"name": "fuzz-peer"})
    c.post(f"/v2.0/{PID}/nat_gateways", json={"name": "fuzz-nat"})
    c.post(f"/v5/{PID}/vpn-gateways", json={"name": "fuzz-vpn"})
    c.post(f"/v2/{PID}/shares", json={"name": "fuzz-share"})
    c.post(f"/v2/{PID}/cas/environments", json={"name": "fuzz-env"})
    c.post(f"/v2/{PID}/cas/applications", json={"name": "fuzz-app"})
    c.post(f"/v2/{PID}/engines", json={"name": "fuzz-engine"})
    c.post(f"/v1/{PID}/cci/namespaces", json={"name": "fuzz-ns"})
    c.post(f"/v1/{PID}/firewalls", json={"name": "fuzz-fw"})
    c.post(f"/v1/{PID}/dsc/assets", json={"asset_name": "fuzz-asset"})
    c.post(f"/v1/{PID}/assets", json={"asset_name": "fuzz-vod"})
    c.post(f"/v2/{PID}/edgemgr/nodes", json={"name": "fuzz-node"})
    c.post(f"/v2/{PID}/hpc/clusters", json={"name": "fuzz-hpc"})
    c.post(f"/v1.1/{PID}/cluster_infos", json={"cluster_name": "fuzz-mrs"})
    c.post(f"/v1.0/{PID}/css/clusters", json={"name": "fuzz-css"})
    c.post(f"/v1.0/{PID}/dws/clusters", json={"name": "fuzz-dws", "number_of_node": 3})
    c.post(f"/v3/{PID}/sources", json={"ip": "10.9.9.9"})
    c.post(f"/v2.0/{PID}/direct-connects", json={"name": "fuzz-dc"})
    c.post(f"/v3/{PID}/enterprise-router/instances", json={"name": "fuzz-er"})
    c.post(f"/v2/{PID}/connections", json={"name": "fuzz-da"})
    c.post(f"/v2/{PID}/jobs", json={"name": "fuzz-job"})
    c.post(f"/v2/{PID}/scripts", json={"name": "fuzz-script"})
    c.post(f"/v2/{PID}/fg/functions", json={"name": "fuzz-fn"})
    c.post("/v2/projects/repositories", json={"repository_name": "fuzz-repo"})
    c.post(f"/v2/{PID}/pipelines", json={"name": "fuzz-pipe"})
    c.post(f"/v2/{PID}/builds", json={"name": "fuzz-build"})
    c.post("/v1/domains", json={"domain_name": "fuzz.cdn.example.com"})
    c.post(f"/v1/{PID}/dbss/instances", json={"name": "fuzz-dbss"})
    c.post(f"/v1/{PID}/instances", json={"name": "fuzz-ddm"})
    c.post(f"/v3/{PID}/gemini/instances", json={"name": "fuzz-gemini"})
    c.post(f"/v1/{PID}/antiddos/default", json={"enable_L7": True})
    c.app.state.sim.jobs.complete_all()
    return c


@pytest.fixture(scope="module")
def obs():
    c = TestClient(create_obs_app(), raise_server_exceptions=False)
    c.put("/fuzz-bucket")
    c.put("/fuzz-bucket/fuzz-key.bin", content=b"fuzz")
    return c


# ---------------------------------------------------------------------------
# valid-value harvesting: map path params to real resource ids
# ---------------------------------------------------------------------------

def _harvest(client):
    """Real ids from the seeded state, keyed by heuristic param names."""
    sim = client.app.state.sim
    ids = {
        "pid": PID, "project_id": PID,
        "server_id": next(iter(sim.servers), "x"),
        "volume_id": next(iter(sim.volumes), "x"),
        "snapshot_id": next(iter(sim.snapshots), "x"),
        "vpc_id": next(iter(sim.vpcs), "x"),
        "subnet_id": next(iter(sim.subnets), "x"),
        "port_id": next(iter(sim.ports), "x"),
        "publicip_id": next(iter(sim.eips), "x"),
        "eip_id": next(iter(sim.eips), "x"),
        "sg_id": next(iter(sim.security_groups), "x"),
        "security_group_id": next(iter(sim.security_groups), "x"),
        "rule_id": "x",
        "image_id": next(iter(sim.images), "x"),
        "vault_id": next(iter(sim.vaults), "x"),
        "backup_id": next(iter(sim.cbr_backups), "x"),
        "policy_id": next(iter(getattr(sim, "cbr_policies", {})), "x"),
        "checkpoint_id": next(iter(sim.checkpoints), "x"),
        "job_id": next(iter(sim.jobs.jobs), "x"),
        "keypair_name": "fuzz-key",
        "group_id": next(iter(getattr(sim, "iam_groups", {})), "x"),
        "user_id": next(iter(getattr(sim, "iam_users", {})), "x"),
        "role_id": "r_00000000000000000000000000000000",
        "agency_id": next(iter(getattr(sim, "iam_agencies", {})), "x"),
        "provider_id": next(iter(getattr(sim, "iam_idps", {})), "x"),
        "mapping_id": next(iter(getattr(sim, "iam_mappings", {})), "x"),
        "protocol_id": "saml",
        "access_key": next(iter(getattr(sim, "iam_credentials", {})), "x"),
        "domain_id": sim.account["domain_id"],
        "cluster_id": next(iter(getattr(sim, "cce_clusters", {})), "x"),
        "node_id": "x",
        "nodepool_id": next(iter(getattr(sim, "cce_node_pools", {})), "x"),
        "addon_id": next(iter(getattr(sim, "cce_addons", {})), "x"),
        "zone_id": next(iter(sim.dns_zones), "x"),
        "recordset_id": "x",
        "key_id": next(iter(getattr(sim, "kms_keys", {})), "x"),
        "topic_urn": next(iter(getattr(sim, "smn_topics", {})), "x"),
        "message_template_id": next(iter(getattr(sim, "smn_templates", {})), "x"),
        "alarm_id": next(iter(getattr(sim, "ces_alarms", {})), "x"),
        "gateway_id": next(iter(getattr(sim, "nat_gateways", {})), "x"),
        "connection_id": next(iter(getattr(sim, "vpn_connections", {})), "x"),
        "vgw_id": next(iter(getattr(sim, "dc_virtual_gateways", {})), "x"),
        "vif_id": next(iter(getattr(sim, "dc_virtual_interfaces", {})), "x"),
        "conn_id": next(iter(getattr(sim, "dc_connections", {})), "x"),
        "peering_id": next(iter(getattr(sim, "vpc_peerings", {})), "x"),
        "acl_id": next(iter(getattr(sim, "network_acls", {})), "x"),
        "rt_id": next(iter(getattr(sim, "vpc_route_tables", {})), "x"),
        "route_table_id": next(iter(getattr(sim, "er_route_tables", {})), "x"),
        "instance_id": next(iter(sim.volumes), "x"),
        "er_id": next(iter(getattr(sim, "er_instances", {})), "x"),
        "attachment_id": next(iter(getattr(sim, "er_attachments", {})), "x"),
        "stream_name": "fuzz-stream",
        "app_name": "fuzz-app",
        "queue_id": next(iter(getattr(sim, "dli_queues", {})), "x"),
        "database_name": "fuzzdb",
        "group_id_lts": "x",
        "dataset_id": next(iter(getattr(sim, "ma_datasets", {})), "x"),
        "version_id": "x",
        "label_name": "x",
        "task_id": next(iter(getattr(sim, "sms_tasks", {})), "x"),
        "source_id": next(iter(getattr(sim, "sms_sources", {})), "x"),
        "template_id": "x",
        "deployment_id": next(iter(getattr(sim, "ief_deployments", {})), "x"),
        "node_id_ief": "x",
        "asset_id": next(iter(getattr(sim, "dsc_assets", {})), "x"),
        "risk_id": next(iter(getattr(sim, "dsc_risks", {})), "x"),
        "firewall_id": next(iter(getattr(sim, "cfw_firewalls", {})), "x"),
        "ns_id": next(iter(getattr(sim, "cci_namespaces", {})), "x"),
        "pod_id": next(iter(getattr(sim, "cci_pods", {})), "x"),
        "engine_id": next(iter(getattr(sim, "cse_engines", {})), "x"),
        "env_id": next(iter(getattr(sim, "cas_environments", {})), "x"),
        "app_id": next(iter(getattr(sim, "cas_applications", {})), "x"),
        "domain_id_cdn": "x",
        "domain_id_vod": "x",
        "host_id": next(iter(sim.servers), "x"),
        "loadbalancer_id": next(iter(getattr(sim, "elb_loadbalancers", {})), "x"),
        "lb_id": next(iter(getattr(sim, "elb_loadbalancers", {})), "x"),
        "listener_id": next(iter(getattr(sim, "elb_listeners", {})), "x"),
        "pool_id": next(iter(getattr(sim, "elb_pools", {})), "x"),
        "member_id": "x",
        "healthmonitor_id": next(iter(getattr(sim, "elb_healthmonitors", {})), "x"),
        "instance_id_apig": next(iter(getattr(sim, "apig_instances", {})), "x"),
        "api_id": next(iter(getattr(sim, "apig_apis", {})), "x"),
        "app_id_apig": next(iter(getattr(sim, "apig_apps", {})), "x"),
        "group_id_apig": next(iter(getattr(sim, "apig_groups", {})), "x"),
        "throttle_id": next(iter(getattr(sim, "apig_throttles", {})), "x"),
        "env_id_apig": next(iter(getattr(sim, "apig_environments", {})), "x"),
        "auth_id": next(iter(getattr(sim, "apig_app_auths", {})), "x"),
        "share_id": next(iter(getattr(sim, "sfs_shares", {})), "x"),
        "job_name": "fuzz-job",
        "conn_id_da": next(iter(getattr(sim, "dataarts_connections", {})), "x"),
        "product_id": next(iter(getattr(sim, "iot_products", {})), "x"),
        "device_id": next(iter(getattr(sim, "iot_devices", {})), "x"),
        "namespace": "fuzz-ns",
        "repo": "fuzz-repo",
        "bucket": "fuzz-bucket",
        "key": "fuzz-key.bin",
        "index_name": "x",
        "configuration_id": next(iter(getattr(sim, "rds_configurations", {})), "x"),
        "schema_name": "x",
        "keypair": "fuzz-key",
        "order_id": "CS123",
        "floating_ip_id": "x",
        "user_name": "x",
        "db_name": "x",
        "replica_id": "x",
        "backup_id_rds": "x",
    }
    # fill anything missing with a generic id from the state
    generic = next(iter(sim.servers), "x")
    return ids, generic


BAD_BODIES = [
    {},
    {"name": 12345, "size": "ten", "enabled": "yes"},
    {"name": None, "id": ["not", "a", "string"], "tags": "not-a-dict"},
    {"x" * 60: "y" * 3000},
]

GARBAGE_PARAMS = {
    "pid": "bad-project",
    "project_id": "bad-project",
}
UNICODE_LONG = "😀" * 40


def _fill(path, values):
    def sub(m):
        name = m.group(1)
        return str(values.get(name, values.get("_generic", "x")))
    return re.sub(r"\{(\w+)\}", sub, path)


def _aliased(path):
    cand = path
    for doc_p, sim_p in ALIASES.items():
        if cand == doc_p or cand.startswith(doc_p + "/"):
            return sim_p + cand[len(doc_p):]
    return cand


def _fuzz_cases():
    """(service, op, method, path, body) tuples for every registry op."""
    for svc, ops in REGISTRY.items():
        for (name, method, path) in ops:
            yield svc, name, method, path


def test_fuzz_never_500(client, obs):
    ids, generic = _harvest(client)
    ids["_generic"] = generic
    crashes = []
    total = 0

    for svc, op, method, path in _fuzz_cases():
        base = _aliased(path)
        is_obs = path.startswith("/{bucket") or path == "/"
        target = obs if is_obs else client

        variants = []
        # A: valid path, empty body
        variants.append((_fill(base, ids), None))
        # B: valid path, junk bodies (body methods only)
        if method in ("POST", "PUT", "PATCH"):
            for bb in BAD_BODIES:
                variants.append((_fill(base, ids), bb))
        # C: garbage path params
        gp = dict(ids)
        gp.update(GARBAGE_PARAMS)
        gp["_generic"] = "bad-id"
        variants.append((_fill(base, gp), None))
        # D: unicode/oversized path params
        up = dict(ids)
        up["_generic"] = UNICODE_LONG
        variants.append((_fill(base, up), None))

        for req_path, body in variants:
            total += 1
            try:
                if body is not None:
                    r = target.request(method, req_path, json=body)
                else:
                    r = target.request(method, req_path)
            except Exception as e:  # TestClient transport-level crash
                crashes.append(f"{svc}.{op} {method} {req_path} -> EXC {type(e).__name__}")
                continue
            if r.status_code >= 500:
                crashes.append(f"{svc}.{op} {method} {req_path} -> {r.status_code}")

    assert not crashes, (
        f"{len(crashes)}/{total} fuzz requests crashed (5xx/exception):\n  "
        + "\n  ".join(crashes[:40])
        + (f"\n  ... and {len(crashes) - 40} more" if len(crashes) > 40 else ""))
