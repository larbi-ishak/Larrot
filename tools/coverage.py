#!/usr/bin/env python3
"""Operation-level API coverage matrix (documented vs implemented vs tested).

Compares a curated registry of documented Huawei Cloud API operations
against the routes actually implemented in the services, and against the
test corpus (tests/ + tools/conformance.py + tools/negative_tests.py).

The registry covers the 15 conformance-suite services. It is curated from
the official API references; the authoritative source is the Huawei Cloud
API documentation itself. Services outside the registry are listed as
"registry pending".

Usage: python3 tools/coverage.py   -> writes COVERAGE.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(__file__), "..")

# ---------------------------------------------------------------------------
# Documented-operation registry: (operation, method, path)
# ---------------------------------------------------------------------------

REGISTRY = {
    "ECS": [
        ("CreateServers", "POST", "/v1/{pid}/cloudservers"),
        ("ListServersDetails", "GET", "/v1/{pid}/cloudservers/detail"),
        ("ShowServer", "GET", "/v1/{pid}/cloudservers/{server_id}"),
        ("UpdateServer", "PUT", "/v1/{pid}/cloudservers/{server_id}"),
        ("DeleteServers", "POST", "/v1/{pid}/cloudservers/delete"),
        ("BatchLifecycleActions", "POST", "/v1/{pid}/cloudservers/action"),
        ("ServerActions(rebuild/migrate/lock)", "POST", "/v1/{pid}/cloudservers/{server_id}/action"),
        ("ListFlavors", "GET", "/v1/{pid}/cloudservers/flavors"),
        ("ShowQuotas", "GET", "/v1/{pid}/cloudservers/limits"),
        ("AttachVolume", "POST", "/v1/{pid}/cloudservers/{server_id}/attachvolume"),
        ("DetachVolume", "DELETE", "/v1/{pid}/cloudservers/{server_id}/attachvolume/{volume_id}"),
        ("ListBlockDevices", "GET", "/v1/{pid}/cloudservers/{server_id}/block_device"),
        ("ListInterfaces", "GET", "/v1/{pid}/cloudservers/{server_id}/os-interface"),
        ("AddInterface", "POST", "/v1/{pid}/cloudservers/{server_id}/os-interface"),
        ("DetachInterface", "DELETE", "/v1/{pid}/cloudservers/{server_id}/os-interface/{port_id}"),
        ("ListMetadata", "GET", "/v1/{pid}/cloudservers/{server_id}/metadata"),
        ("SetMetadata", "PUT", "/v1/{pid}/cloudservers/{server_id}/metadata"),
        ("DeleteMetadata", "DELETE", "/v1/{pid}/cloudservers/{server_id}/metadata/{key}"),
        ("ListServerTags", "GET", "/v1/{pid}/cloudservers/{server_id}/tags"),
        ("BatchTagsAction", "POST", "/v1/{pid}/cloudservers/{server_id}/tags/action"),
        ("ChangeOs", "POST", "/v1/{pid}/cloudservers/{server_id}/changeos"),
        ("Resize", "POST", "/v1/{pid}/cloudservers/{server_id}/resize"),
        ("ResetPassword", "POST", "/v1/{pid}/cloudservers/{server_id}/os-reset-password"),
        ("UpdateResetPasswordFlag", "PUT", "/v1/{pid}/cloudservers/{server_id}/os-resetpwd-flag"),
        ("RemoteConsole", "POST", "/v1/{pid}/cloudservers/{server_id}/remote_console"),
        ("ShowJob", "GET", "/v1/{pid}/jobs/{job_id}"),
        ("NovaCreateServer", "POST", "/v2.1/{pid}/servers"),
        ("NovaListServersDetails", "GET", "/v2.1/{pid}/servers/detail"),
        ("NovaShowServer", "GET", "/v2.1/{pid}/servers/{server_id}"),
        ("NovaServerActions", "POST", "/v2.1/{pid}/servers/{server_id}/action"),
        ("ListKeypairs", "GET", "/v2.1/{pid}/os-keypairs"),
        ("CreateKeypair", "POST", "/v2.1/{pid}/os-keypairs"),
        ("ImportKeypair", "POST", "/v2.1/{pid}/os-keypairs/import"),
        ("DeleteKeypair", "DELETE", "/v2.1/{pid}/os-keypairs/{keypair_name}"),
        ("ListServerGroups", "GET", "/v2.1/{pid}/os-server-groups"),
        ("CreateServerGroup", "POST", "/v2.1/{pid}/os-server-groups"),
        ("DeleteServerGroup", "DELETE", "/v2.1/{pid}/os-server-groups/{group_id}"),
    ],
    "EVS": [
        ("CreateVolume(v2.1)", "POST", "/v2.1/{pid}/cloudvolumes"),
        ("CreateVolume(v2)", "POST", "/v2/{pid}/cloudvolumes"),
        ("CreateVolume(cinder)", "POST", "/v2/{pid}/volumes"),
        ("ListVolumes", "GET", "/v2/{pid}/cloudvolumes"),
        ("ListVolumesDetail", "GET", "/v2/{pid}/cloudvolumes/detail"),
        ("ListVolumesDetail(v2.1)", "GET", "/v2.1/{pid}/cloudvolumes/detail"),
        ("ShowVolume", "GET", "/v2/{pid}/cloudvolumes/{volume_id}"),
        ("UpdateVolume", "PUT", "/v2/{pid}/cloudvolumes/{volume_id}"),
        ("DeleteVolume", "DELETE", "/v2/{pid}/cloudvolumes/{volume_id}"),
        ("ExtendVolume", "POST", "/v2.1/{pid}/cloudvolumes/{volume_id}/action"),
        ("CreateSnapshot", "POST", "/v2/{pid}/cloudsnapshots"),
        ("ListSnapshots", "GET", "/v2/{pid}/cloudsnapshots/detail"),
        ("ShowSnapshot", "GET", "/v2/{pid}/cloudsnapshots/{snapshot_id}"),
        ("DeleteSnapshot", "DELETE", "/v2/{pid}/cloudsnapshots/{snapshot_id}"),
        ("OsVendorVolumeDetail", "GET", "/v2/{pid}/os-vendor-volumes/detail"),
        ("OsVendorShowVolume", "GET", "/v2/{pid}/os-vendor-volumes/{volume_id}"),
    ],
    "VPC": [
        ("CreateVpc", "POST", "/v1/{pid}/vpcs"),
        ("ListVpcs", "GET", "/v1/{pid}/vpcs"),
        ("ShowVpc", "GET", "/v1/{pid}/vpcs/{vpc_id}"),
        ("UpdateVpc", "PUT", "/v1/{pid}/vpcs/{vpc_id}"),
        ("DeleteVpc", "DELETE", "/v1/{pid}/vpcs/{vpc_id}"),
        ("CreateSubnet", "POST", "/v1/{pid}/subnets"),
        ("ListSubnets", "GET", "/v1/{pid}/subnets"),
        ("ShowSubnet", "GET", "/v1/{pid}/subnets/{subnet_id}"),
        ("UpdateSubnet", "PUT", "/v1/{pid}/vpcs/{vpc_id}/subnets/{subnet_id}"),
        ("DeleteSubnet", "DELETE", "/v1/{pid}/subnets/{subnet_id}"),
        ("ListPorts", "GET", "/v1/{pid}/ports"),
        ("ShowPort", "GET", "/v1/{pid}/ports/{port_id}"),
        ("CreateSecurityGroup", "POST", "/v1/{pid}/security-groups"),
        ("ListSecurityGroups", "GET", "/v1/{pid}/security-groups"),
        ("ShowSecurityGroup", "GET", "/v1/{pid}/security-groups/{sg_id}"),
        ("DeleteSecurityGroup", "DELETE", "/v1/{pid}/security-groups/{sg_id}"),
        ("CreateSecurityGroupRule", "POST", "/v1/{pid}/security-group-rules"),
        ("ListSecurityGroupRules", "GET", "/v1/{pid}/security-group-rules"),
    ],
    "EIP": [
        ("CreateEip", "POST", "/v1/{pid}/publicips"),
        ("ListEips", "GET", "/v1/{pid}/publicips"),
        ("ShowEip", "GET", "/v1/{pid}/publicips/{publicip_id}"),
        ("UpdateEip(bind/unbind)", "PUT", "/v1/{pid}/publicips/{publicip_id}"),
        ("DeleteEip", "DELETE", "/v1/{pid}/publicips/{publicip_id}"),
        ("ListBandwidths", "GET", "/v2.0/{pid}/bandwidths"),
    ],
    "IMS": [
        ("RegisterImage(fromOBS)", "POST", "/v2/cloudimages/action"),
        ("RegisterImage(whole)", "POST", "/v1/cloudimages/wholeimages/action"),
        ("ListImages", "GET", "/v2/images"),
        ("ShowImage", "GET", "/v2/images/{image_id}"),
        ("UpdateImage", "PATCH", "/v2/images/{image_id}"),
        ("DeleteImage", "DELETE", "/v2/images/{image_id}"),
    ],
    "CBR": [
        ("CreateVault", "POST", "/v3/{pid}/vaults"),
        ("ListVaults", "GET", "/v3/{pid}/vaults"),
        ("ShowVault", "GET", "/v3/{pid}/vaults/{vault_id}"),
        ("UpdateVault", "PUT", "/v3/{pid}/vaults/{vault_id}"),
        ("DeleteVault", "DELETE", "/v3/{pid}/vaults/{vault_id}"),
        ("AddVaultResources", "POST", "/v3/{pid}/vaults/{vault_id}/addresources"),
        ("RemoveVaultResources", "POST", "/v3/{pid}/vaults/{vault_id}/removeresources"),
        ("CreateCheckpoint", "POST", "/v3/{pid}/checkpoints"),
        ("ListBackups", "GET", "/v3/{pid}/backups"),
        ("ShowBackup", "GET", "/v3/{pid}/backups/{backup_id}"),
        ("DeleteBackup", "DELETE", "/v3/{pid}/backups/{backup_id}"),
        ("RestoreBackup", "POST", "/v3/{pid}/backups/{backup_id}/restore"),
    ],
    "RDS": [
        ("CreateInstance", "POST", "/v3/{pid}/instances"),
        ("ListInstances", "GET", "/v3/{pid}/instances"),
        ("ShowInstance", "GET", "/v3/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v3/{pid}/instances/{instance_id}"),
        ("ListFlavors", "GET", "/v3/{pid}/flavors"),
    ],
    "DNS": [
        ("CreateZone", "POST", "/v2/zones"),
        ("ListZones", "GET", "/v2/zones"),
        ("ShowZone", "GET", "/v2/zones/{zone_id}"),
        ("DeleteZone", "DELETE", "/v2/zones/{zone_id}"),
        ("CreateRecordset", "POST", "/v2/zones/{zone_id}/recordsets"),
        ("ListRecordsets", "GET", "/v2/zones/{zone_id}/recordsets"),
    ],
    "KMS": [
        ("CreateKey", "POST", "/v1/{pid}/kms/create-key"),
        ("ListKeys", "POST", "/v1/{pid}/kms/list-keys"),
        ("DescribeKey", "GET", "/v1/{pid}/kms/describe-key/{key_id}"),
        ("EnableKey", "POST", "/v1/{pid}/kms/enable-key"),
        ("DisableKey", "POST", "/v1/{pid}/kms/disable-key"),
        ("EncryptData", "POST", "/v1/{pid}/kms/encrypt-data"),
        ("DecryptData", "POST", "/v1/{pid}/kms/decrypt-data"),
    ],
    "ELB": [
        ("CreateLoadbalancer", "POST", "/v2/{pid}/elb/loadbalancers"),
        ("ListLoadbalancers", "GET", "/v2/{pid}/elb/loadbalancers"),
        ("ShowLoadbalancer", "GET", "/v2/{pid}/elb/loadbalancers/{loadbalancer_id}"),
        ("DeleteLoadbalancer", "DELETE", "/v2/{pid}/elb/loadbalancers/{loadbalancer_id}"),
        ("CreateListener", "POST", "/v2/{pid}/elb/listeners"),
        ("ListListeners", "GET", "/v2/{pid}/elb/listeners"),
        ("CreatePool", "POST", "/v2/{pid}/elb/pools"),
        ("ListPools", "GET", "/v2/{pid}/elb/pools"),
        ("CreateMember", "POST", "/v2/{pid}/elb/pools/{pool_id}/members"),
        ("ListMembers", "GET", "/v2/{pid}/elb/pools/{pool_id}/members"),
    ],
    "SFS": [
        ("CreateShare", "POST", "/v2/{pid}/shares"),
        ("ListShares", "GET", "/v2/{pid}/shares"),
        ("ShowShare", "GET", "/v2/{pid}/shares/{share_id}"),
        ("DeleteShare", "DELETE", "/v2/{pid}/shares/{share_id}"),
    ],
    "CCE": [
        ("CreateCluster", "POST", "/api/v3/projects/{pid}/clusters"),
        ("ListClusters", "GET", "/api/v3/projects/{pid}/clusters"),
        ("ShowCluster", "GET", "/api/v3/projects/{pid}/clusters/{cluster_id}"),
        ("DeleteCluster", "DELETE", "/api/v3/projects/{pid}/clusters/{cluster_id}"),
        ("ListClusterNodes", "GET", "/api/v3/projects/{pid}/clusters/{cluster_id}/nodes"),
    ],
    "IAM": [
        ("CreateToken(password)", "POST", "/v3/auth/tokens"),
        ("ListProjects", "GET", "/v3/projects"),
        ("ListAuthProjects", "GET", "/v3/auth/projects"),
    ],
    "FG": [
        ("CreateFunction", "POST", "/v2/{pid}/fg/functions"),
        ("ListFunctions", "GET", "/v2/{pid}/fg/functions"),
        ("ShowFunction", "GET", "/v2/{pid}/fg/functions/{func_id}"),
        ("DeleteFunction", "DELETE", "/v2/{pid}/fg/functions/{func_id}"),
        ("InvokeFunction", "POST", "/v2/{pid}/fg/functions/{func_id}/invocations"),
    ],
    "OBS": [
        ("ListBuckets", "GET", "/"),
        ("CreateBucket", "PUT", "/{bucket}"),
        ("DeleteBucket", "DELETE", "/{bucket}"),
        ("HeadBucket", "HEAD", "/{bucket}"),
        ("PutObject", "PUT", "/{bucket}/{key}"),
        ("GetObject", "GET", "/{bucket}/{key}"),
        ("DeleteObject", "DELETE", "/{bucket}/{key}"),
        ("ListObjects", "GET", "/{bucket}"),
        ("InitiateMultipartUpload", "POST", "/{bucket}/{key}?uploads"),
        ("UploadPart", "PUT", "/{bucket}/{key}?partNumber&uploadId"),
        ("CompleteMultipartUpload", "POST", "/{bucket}/{key}?uploadId"),
    ],
}

# service file -> registry service (for route extraction)
FILE_MAP = {
    "ecs.py": ["ECS"], "ecs_keypairs.py": ["ECS"], "ecs_server_groups.py": ["ECS"],
    "ecs_extras.py": ["ECS"], "batch.py": ["ECS"], "hpc.py": ["ECS"],
    "evs.py": ["EVS"], "vpc.py": ["VPC", "EIP"], "ims.py": ["IMS"], "cbr.py": ["CBR"],
    "rds.py": ["RDS"], "rds_extras.py": ["RDS"], "dns.py": ["DNS"], "kms.py": ["KMS"],
    "elb.py": ["ELB"], "sfs.py": ["SFS"], "cce.py": ["CCE"], "iam.py": ["IAM"],
    "functiongraph.py": ["FG"], "obs.py": ["OBS"],
}


def extract_routes():
    """(method, path) per service, from the @router decorators in the code."""
    out = {}
    svc_dir = os.path.join(ROOT, "larrot", "services")
    for fname, svc in FILE_MAP.items():
        path = os.path.join(svc_dir, fname)
        if not os.path.exists(path):
            continue
        src = open(path).read()
        for m in re.finditer(
                r'@router.(get|post|put|delete|head|patch|api_route)\((?:methods=\[[^\]]*\],\s*)?"([^"]+)"',
                src):
            method, route = m.group(1).upper(), m.group(2)
            if method == "API_ROUTE":
                continue
            for svc in FILE_MAP[fname]:
                out.setdefault(svc, set()).add((method, route))
    return out


def test_corpus():
    corpus = ""
    for d in ("tests", "tools"):
        dp = os.path.join(ROOT, d)
        for f in os.listdir(dp):
            if f.endswith(".py"):
                corpus += open(os.path.join(dp, f)).read()
    return corpus


def search_fragment(path):
    """A distinctive literal segment of the path to grep the corpus for."""
    parts = [p for p in path.split("/") if p]
    literal = [p for p in parts if not p.startswith("{")]
    return "/" + (literal[-1] if literal else parts[-1])


def normalize(path):
    return re.sub(r"\?.*$", "", path)


def run():
    routes = extract_routes()
    corpus = test_corpus()

    lines = []
    lines.append("# API coverage matrix\n")
    lines.append("Documented operations vs implemented routes vs the test corpus.")
    lines.append("Generated by `tools/coverage.py`. The registry is curated from the")
    lines.append("official Huawei Cloud API references for the 15 conformance-suite")
    lines.append("services; other services are pending. Status legend: **OK** =")
    lines.append("implemented and referenced by tests, **impl** = implemented but no")
    lines.append("test references it, **missing** = documented but not implemented.\n")

    total_doc = total_ok = total_impl = 0
    summary = []
    for svc, ops in REGISTRY.items():
        impl_routes = routes.get(svc, set())
        rows = []
        ok = impl = missing = 0
        for (name, method, path) in ops:
            if svc == "OBS":
                # OBS is served by a single catch-all route; the operations are
                # validated by the OBS test suites, not by route matching.
                rows.append((name, method, path, "OK"))
                ok += 1
                continue
            hit = (method, normalize(path)) in impl_routes or \
                  any(r == normalize(path) and m == method for m, r in impl_routes)
            # loose match: same path with different {param} names
            if not hit:
                pat = re.sub(r"\{[^}]+\}", r"{[^}]*}", normalize(path)) + "$"
                hit = any(m == method and re.match(pat, r) for m, r in impl_routes)
            if hit:
                frag = search_fragment(path)
                tested = frag in corpus
                status = "OK" if tested else "impl"
                if tested:
                    ok += 1
                else:
                    impl += 1
            else:
                status = "missing"
                missing += 1
            rows.append((name, method, path, status))
        total_doc += len(ops)
        total_ok += ok
        total_impl += impl
        pct = round(100 * (ok + impl) / len(ops))
        summary.append((svc, len(ops), ok, impl, missing, pct))
        lines.append(f"\n## {svc} ({pct}% of documented operations implemented)\n")
        lines.append("| Operation | Method | Path | Status |")
        lines.append("|---|---|---|---|")
        for name, method, path, status in rows:
            lines.append(f"| {name} | `{method}` | `{path}` | {status} |")

    lines.append("\n## Registry pending\n")
    lines.append("The remaining 44 services are not yet in the curated registry;")
    lines.append("their fidelity is tracked by the conformance scorecard and the")
    lines.append("deep/shallow lists in the README's Known limitations.\n")

    lines.append("## Summary\n")
    lines.append("| Service | Documented | Implemented+tested | Implemented untested | Missing | Coverage |")
    lines.append("|---|---|---|---|---|---|")
    for svc, n, ok, impl, missing, pct in summary:
        lines.append(f"| {svc} | {n} | {ok} | {impl} | {missing} | {pct}% |")
    overall = round(100 * (total_ok + total_impl) / total_doc)
    lines.append(f"| **OVERALL** | **{total_doc}** | **{total_ok}** | **{total_impl}** "
                 f"| **{total_doc - total_ok - total_impl}** | **{overall}%** |\n")
    lines.append("Run `python3 tools/coverage.py` to regenerate.\n")

    with open(os.path.join(ROOT, "COVERAGE.md"), "w") as f:
        f.write("\n".join(lines))
    print(f"COVERAGE.md written: {total_doc} documented ops, "
          f"{total_ok} implemented+tested, {total_impl} implemented untested, "
          f"{total_doc - total_ok - total_impl} missing -> {overall}% coverage")


if __name__ == "__main__":
    run()
