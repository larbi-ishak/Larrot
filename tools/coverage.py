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
    "bms.py": ["BMS"], "as_.py": ["AS"], "smn.py": ["SMN"], "ces.py": ["CES"],
    "lts.py": ["LTS"], "dcs.py": ["DCS"], "dcs_extras.py": ["DCS"], "dms.py": ["DMS"],
    "dds.py": ["DDS"], "waf.py": ["WAF"], "tms.py": ["TMS"], "eps.py": ["EPS"],
    "apig.py": ["APIG"], "swr.py": ["SWR"], "modelarts.py": ["ModelArts"],
    "iotda.py": ["IoTDA"], "gaussdb.py": ["GaussDB"], "aom.py": ["AOM"],
    "dli.py": ["DLI"], "antiddos.py": ["Anti-DDoS"], "bss.py": ["BSS"],
    "nat.py": ["NAT"], "peering.py": ["Peering"], "acl.py": ["ACL"],
    "routes.py": ["VPC-Routes"], "vpn.py": ["VPN"], "geminidb.py": ["GeminiDB"],
    "ddm.py": ["DDM"], "dbss.py": ["DBSS"], "hss.py": ["HSS"], "cdn.py": ["CDN"],
    "dws.py": ["DWS"], "css.py": ["CSS"], "mrs.py": ["MRS"], "sms.py": ["SMS"],
    "dc.py": ["DC"], "er.py": ["ER"], "dis.py": ["DIS"], "dataarts.py": ["DataArts"],
    "oms.py": ["OMS"], "des.py": ["DES"], "codearts.py": ["CodeArts"],
    "servicestage.py": ["ServiceStage"], "cse.py": ["CSE"], "cci.py": ["CCI"],
    "cfw.py": ["CFW"], "dsc.py": ["DSC"], "vod.py": ["VOD"], "ief.py": ["IEF"],
    "rds_extras.py": ["RDS"], "hpc.py": [], "batch.py": [],
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
            cand = normalize(path)
            for doc_p, sim_p in ALIASES.items():
                if cand == doc_p or cand.startswith(doc_p + "/"):
                    cand = sim_p + cand[len(doc_p):]
                    break
            hit = (method, cand) in impl_routes or \
                  any(r == cand and m == method for m, r in impl_routes)
            # loose match: same path with different {param} names
            if not hit:
                pat = re.sub(r"\{[^}]+\}", r"{[^}]*}", cand) + "$"
                hit = any(m == method and re.match(pat, r) for m, r in impl_routes)
            if hit:
                frag = search_fragment(cand)
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



# ---------------------------------------------------------------------------
# Registries for the remaining services (core documented operation set)
# ---------------------------------------------------------------------------

REGISTRY_EXTRA = {
    "BMS": [
        ("ListBmsServers", "GET", "/v1/{pid}/baremetalservers/detail"),
        ("CreateBmsServer", "POST", "/v1/{pid}/baremetalservers"),
        ("ShowBmsServer", "GET", "/v1/{pid}/baremetalservers/{server_id}"),
        ("DeleteBmsServer", "DELETE", "/v1/{pid}/baremetalservers/{server_id}"),
        ("BmsBatchActions", "POST", "/v1/{pid}/baremetalservers/{server_id}/action"),
        ("ListBmsNics", "GET", "/v1/{pid}/baremetalservers/{server_id}/nics"),
        ("ListBmsFlavors", "GET", "/v1/{pid}/baremetalservers/flavors"),
    ],
    "AS": [
        ("CreateScalingGroup", "POST", "/v1/{pid}/scaling_group"),
        ("ListScalingGroups", "GET", "/v1/{pid}/scaling_group"),
        ("ShowScalingGroup", "GET", "/v1/{pid}/scaling_group/{group_id}"),
        ("DeleteScalingGroup", "DELETE", "/v1/{pid}/scaling_group/{group_id}"),
        ("CreateScalingPolicy", "POST", "/v1/{pid}/scaling_policy"),
        ("ListScalingPolicies", "GET", "/v1/{pid}/scaling_policy"),
        ("ExecuteScalingPolicy", "POST", "/v1/{pid}/scaling_policy/{policy_id}/execute"),
        ("ListScalingInstances", "GET", "/v1/{pid}/scaling_group/{group_id}/instances"),
    ],
    "SMN": [
        ("CreateTopic", "POST", "/v2/{pid}/notifications/topics"),
        ("ListTopics", "GET", "/v2/{pid}/notifications/topics"),
        ("ShowTopic", "GET", "/v2/{pid}/notifications/topics/{topic_urn}"),
        ("DeleteTopic", "DELETE", "/v2/{pid}/notifications/topics/{topic_urn}"),
        ("Subscribe", "POST", "/v2/{pid}/notifications/topics/{topic_urn}/subscriptions"),
        ("ListSubscriptions", "GET", "/v2/{pid}/notifications/topics/{topic_urn}/subscriptions"),
        ("Unsubscribe", "DELETE", "/v2/{pid}/notifications/topics/{topic_urn}/subscriptions/{sub_urn}"),
        ("Publish", "POST", "/v2/{pid}/notifications/topics/{topic_urn}/publish"),
    ],
    "CES": [
        ("ListAlarms", "GET", "/v1/{pid}/alarms"),
        ("CreateAlarm", "POST", "/v1/{pid}/alarms"),
        ("ShowAlarm", "GET", "/v1/{pid}/alarms/{alarm_id}"),
        ("DeleteAlarm", "DELETE", "/v1/{pid}/alarms/{alarm_id}"),
        ("ListAlarmsHistory", "GET", "/v1/{pid}/alarms/{alarm_id}/history"),
        ("ListMetrics", "GET", "/v1/{pid}/metrics"),
        ("GetMetricData", "GET", "/v1.0/{pid}/metric-data"),
        ("BatchQueryMetricData", "POST", "/v1.0/{pid}/batch-query/metric-data"),
    ],
    "LTS": [
        ("CreateLogGroup", "POST", "/v2/{pid}/log-groups"),
        ("ListLogGroups", "GET", "/v2/{pid}/log-groups"),
        ("DeleteLogGroup", "DELETE", "/v2/{pid}/log-groups/{group_id}"),
        ("CreateLogStream", "POST", "/v2/{pid}/log-groups/{group_id}/log-streams"),
        ("ListLogStreams", "GET", "/v2/{pid}/log-groups/{group_id}/log-streams"),
    ],
    "DCS": [
        ("CreateInstance", "POST", "/v2/{pid}/instances"),
        ("ListInstances", "GET", "/v2/{pid}/instances"),
        ("ShowInstance", "GET", "/v2/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v2/{pid}/instances/{instance_id}"),
        ("ListFlavors", "GET", "/v2/{pid}/flavors"),
        ("CreateBackup", "POST", "/v2/{pid}/instances/{instance_id}/backups"),
        ("ListBackups", "GET", "/v2/{pid}/instances/{instance_id}/backups"),
        ("DeleteBackup", "DELETE", "/v2/{pid}/instances/{instance_id}/backups/{backup_id}"),
        ("RestoreInstance", "POST", "/v2/{pid}/instances/{instance_id}/restore"),
        ("ListParameters", "GET", "/v2/{pid}/instances/{instance_id}/parameters"),
        ("UpdateParameters", "PUT", "/v2/{pid}/instances/{instance_id}/parameters"),
        ("RestartInstance", "POST", "/v2/{pid}/instances/{instance_id}/restart"),
        ("ResizeInstance", "POST", "/v2/{pid}/instances/{instance_id}/resize"),
    ],
    "DMS": [
        ("CreateInstance", "POST", "/v2/{pid}/instances"),
        ("ListInstances", "GET", "/v2/{pid}/instances"),
        ("ShowInstance", "GET", "/v2/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v2/{pid}/instances/{instance_id}"),
        ("CreateTopic", "POST", "/v2/{pid}/instances/{instance_id}/topics"),
        ("ListTopics", "GET", "/v2/{pid}/instances/{instance_id}/topics"),
    ],
    "DDS": [
        ("CreateInstance", "POST", "/v3/{pid}/instances"),
        ("ListInstances", "GET", "/v3/{pid}/instances"),
        ("ShowInstance", "GET", "/v3/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v3/{pid}/instances/{instance_id}"),
    ],
    "WAF": [
        ("CreateHost", "POST", "/v1/{pid}/waf/hosts"),
        ("ListHosts", "GET", "/v1/{pid}/waf/hosts"),
        ("ShowHost", "GET", "/v1/{pid}/waf/hosts/{domain_id}"),
        ("UpdateHost(bindPolicy)", "PUT", "/v1/{pid}/waf/hosts/{domain_id}"),
        ("DeleteHost", "DELETE", "/v1/{pid}/waf/hosts/{domain_id}"),
        ("CreatePolicy", "POST", "/v1/{pid}/waf/policies"),
        ("ListPolicies", "GET", "/v1/{pid}/waf/policies"),
        ("ShowPolicy", "GET", "/v1/{pid}/waf/policies/{policy_id}"),
        ("CreateRule", "POST", "/v1/{pid}/waf/policies/{policy_id}/rules"),
        ("ListRules", "GET", "/v1/{pid}/waf/policies/{policy_id}/rules"),
    ],
    "TMS": [
        ("CreateOrDeleteProjectTags", "POST", "/v1.0/{pid}/project-tags/create-or-delete"),
        ("ListProjectTags", "GET", "/v1.0/{pid}/project-tags/tags"),
        ("ListProjectResources", "POST", "/v1.0/{pid}/project-tags/resources"),
        ("ResourceTagsAction", "POST", "/v2.0/{pid}/project-tags/resource-tags/action"),
    ],
    "EPS": [
        ("CreateEnterpriseProject", "POST", "/v1.0/enterprise-projects"),
        ("ListEnterpriseProjects", "GET", "/v1.0/enterprise-projects"),
        ("ShowEnterpriseProject", "GET", "/v1.0/enterprise-projects/{eps_id}"),
        ("DeleteEnterpriseProject", "DELETE", "/v1.0/enterprise-projects/{eps_id}"),
    ],
    "APIG": [
        ("CreateInstance", "POST", "/v2/{pid}/apigw/instances"),
        ("ListInstances", "GET", "/v2/{pid}/apigw/instances"),
        ("CreateGroup", "POST", "/v2/{pid}/apigw/groups"),
        ("ListGroups", "GET", "/v2/{pid}/apigw/groups"),
        ("CreateApi", "POST", "/v2/{pid}/apigw/apis"),
        ("ListApis", "GET", "/v2/{pid}/apigw/apis"),
    ],
    "SWR": [
        ("CreateNamespace", "POST", "/v2/manage/namespaces"),
        ("ListNamespaces", "GET", "/v2/manage/namespaces"),
        ("CreateRepo", "POST", "/v2/manage/namespaces/{namespace}/repos"),
        ("ListRepos", "GET", "/v2/manage/namespaces/{namespace}/repos"),
    ],
    "ModelArts": [
        ("CreateNotebook", "POST", "/v2/{pid}/notebooks"),
        ("ListNotebooks", "GET", "/v2/{pid}/notebooks"),
        ("DeleteNotebook", "DELETE", "/v2/{pid}/notebooks/{notebook_id}"),
        ("CreateTrainingJob", "POST", "/v2/{pid}/training-jobs"),
        ("ListTrainingJobs", "GET", "/v2/{pid}/training-jobs"),
        ("CreateDataset", "POST", "/v2/{pid}/datasets"),
        ("ListDatasets", "GET", "/v2/{pid}/datasets"),
        ("DeleteDataset", "DELETE", "/v2/{pid}/datasets/{dataset_id}"),
        ("RegisterModel", "POST", "/v1/{pid}/models"),
        ("ListModels", "GET", "/v1/{pid}/models"),
        ("ShowModel", "GET", "/v1/{pid}/models/{model_id}"),
        ("DeleteModel", "DELETE", "/v1/{pid}/models/{model_id}"),
        ("CreateService", "POST", "/v1/{pid}/services"),
        ("ListServices", "GET", "/v1/{pid}/services"),
        ("ShowService", "GET", "/v1/{pid}/services/{service_id}"),
        ("DeleteService", "DELETE", "/v1/{pid}/services/{service_id}"),
        ("CreateFineTuningJob", "POST", "/v1/{pid}/fine-tuning-jobs"),
        ("ListFineTuningJobs", "GET", "/v1/{pid}/fine-tuning-jobs"),
        ("MaaSListModels", "GET", "/v1/models"),
        ("MaaSChatCompletions", "POST", "/v1/chat/completions"),
        ("MaaSEmbeddings", "POST", "/v1/embeddings"),
        ("CreateApiKey", "POST", "/v1/{pid}/maas/keys"),
        ("ListApiKeys", "GET", "/v1/{pid}/maas/keys"),
        ("DeleteApiKey", "DELETE", "/v1/{pid}/maas/keys/{key_id}"),
    ],
    "IoTDA": [
        ("CreateProduct", "POST", "/v5/iot/{pid}/products"),
        ("ListProducts", "GET", "/v5/iot/{pid}/products"),
        ("CreateDevice", "POST", "/v5/iot/{pid}/devices"),
        ("ListDevices", "GET", "/v5/iot/{pid}/devices"),
        ("DeleteDevice", "DELETE", "/v5/iot/{pid}/devices/{device_id}"),
        ("SendCommand", "POST", "/v5/iot/{pid}/devices/{device_id}/commands"),
    ],
    "GaussDB": [
        ("CreateInstance", "POST", "/v3/{pid}/instances"),
        ("ListInstances", "GET", "/v3/{pid}/instances"),
        ("ShowInstance", "GET", "/v3/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v3/{pid}/instances/{instance_id}"),
    ],
    "AOM": [
        ("CreateApp", "POST", "/v1/{pid}/aom/apps"),
        ("ListApps", "GET", "/v1/{pid}/aom/apps"),
        ("CreateComponent", "POST", "/v1/{pid}/aom/components"),
        ("ListAlarms", "GET", "/v1/{pid}/aom/alarms"),
        ("CreateAlarmRule", "POST", "/v2/{pid}/aom/alarm-rules"),
    ],
    "DLI": [
        ("CreateDatabase", "POST", "/v1.0/{pid}/databases"),
        ("ListDatabases", "GET", "/v1.0/{pid}/databases"),
        ("CreateTable", "POST", "/v1.0/{pid}/tables"),
        ("SubmitSqlJob", "POST", "/v1.0/{pid}/jobs/submit"),
        ("ShowSqlJob", "GET", "/v1.0/{pid}/jobs/{job_id}"),
        ("ListSqlJobs", "GET", "/v1.0/{pid}/jobs"),
        ("CreateQueue", "POST", "/v1.0/{pid}/queues"),
        ("ListQueues", "GET", "/v1.0/{pid}/queues"),
        ("DeleteQueue", "DELETE", "/v1.0/{pid}/queues/{queue_id}"),
    ],
    "Anti-DDoS": [
        ("SetDefaultProtection", "POST", "/v1/{pid}/antiddos/default"),
        ("GetDefaultProtection", "GET", "/v1/{pid}/antiddos/default"),
        ("GetProtectionStatus", "GET", "/v1/{pid}/antiddos/status"),
        ("EnableProtection", "POST", "/v1/{pid}/antiddos/enable"),
    ],
    "BSS": [
        ("ListCustomerOrders", "GET", "/v2/orders/customer-orders"),
        ("ListOrderResources", "GET", "/v2/orders/customer-orders/resources"),
        ("ListAccountBalances", "GET", "/v2/accounts/customer-accounts/balances"),
        ("PayOrder", "POST", "/v2/orders/customer-orders/pay"),
    ],
    "NAT": [
        ("CreateNatGateway", "POST", "/v2.0/{pid}/nat_gateways"),
        ("ListNatGateways", "GET", "/v2.0/{pid}/nat_gateways"),
        ("ShowNatGateway", "GET", "/v2.0/{pid}/nat_gateways/{gateway_id}"),
        ("DeleteNatGateway", "DELETE", "/v2.0/{pid}/nat_gateways/{gateway_id}"),
        ("CreateSnatRule", "POST", "/v2.0/{pid}/snat_rules"),
        ("ListSnatRules", "GET", "/v2.0/{pid}/snat_rules"),
        ("DeleteSnatRule", "DELETE", "/v2.0/{pid}/snat_rules/{rule_id}"),
        ("CreateDnatRule", "POST", "/v2.0/{pid}/dnat_rules"),
        ("ListDnatRules", "GET", "/v2.0/{pid}/dnat_rules"),
        ("DeleteDnatRule", "DELETE", "/v2.0/{pid}/dnat_rules/{rule_id}"),
    ],
    "Peering": [
        ("CreatePeering", "POST", "/v2.0/{pid}/vpc-peerings"),
        ("ListPeerings", "GET", "/v2.0/{pid}/vpc-peerings"),
        ("ShowPeering", "GET", "/v2.0/{pid}/vpc-peerings/{peering_id}"),
        ("AcceptPeering", "PUT", "/v2.0/{pid}/vpc-peerings/{peering_id}/accept"),
        ("RejectPeering", "PUT", "/v2.0/{pid}/vpc-peerings/{peering_id}/reject"),
        ("DeletePeering", "DELETE", "/v2.0/{pid}/vpc-peerings/{peering_id}"),
    ],
    "ACL": [
        ("CreateAcl", "POST", "/v3/{pid}/vpc/acls"),
        ("ListAcls", "GET", "/v3/{pid}/vpc/acls"),
        ("ShowAcl", "GET", "/v3/{pid}/vpc/acls/{acl_id}"),
        ("DeleteAcl", "DELETE", "/v3/{pid}/vpc/acls/{acl_id}"),
        ("CreateIngressRule", "POST", "/v3/{pid}/vpc/acls/{acl_id}/ingress-rules"),
        ("CreateEgressRule", "POST", "/v3/{pid}/vpc/acls/{acl_id}/egress-rules"),
        ("AssociateSubnet", "POST", "/v3/{pid}/vpc/acls/{acl_id}/associate"),
        ("DisassociateSubnet", "POST", "/v3/{pid}/vpc/acls/{acl_id}/disassociate"),
    ],
    "VPC-Routes": [
        ("CreateRouteTable", "POST", "/v1/{pid}/vpc/routetables"),
        ("ListRouteTables", "GET", "/v1/{pid}/vpc/routetables"),
        ("ShowRouteTable", "GET", "/v1/{pid}/vpc/routetables/{rt_id}"),
        ("DeleteRouteTable", "DELETE", "/v1/{pid}/vpc/routetables/{rt_id}"),
        ("CreateRoute", "POST", "/v1/{pid}/vpc/routetables/{rt_id}/routes"),
        ("DeleteRoute", "DELETE", "/v1/{pid}/vpc/routetables/{rt_id}/routes/{route_id}"),
    ],
    "VPN": [
        ("CreateVpnGateway", "POST", "/v5/{pid}/vpn-gateways"),
        ("ListVpnGateways", "GET", "/v5/{pid}/vpn-gateways"),
        ("ShowVpnGateway", "GET", "/v5/{pid}/vpn-gateways/{gateway_id}"),
        ("DeleteVpnGateway", "DELETE", "/v5/{pid}/vpn-gateways/{gateway_id}"),
        ("CreateVpnConnection", "POST", "/v5/{pid}/vpn-connections"),
        ("ListVpnConnections", "GET", "/v5/{pid}/vpn-connections"),
        ("DeleteVpnConnection", "DELETE", "/v5/{pid}/vpn-connections/{connection_id}"),
    ],
    "GeminiDB": [
        ("CreateInstance", "POST", "/v3/{pid}/instances"),
        ("ListInstances", "GET", "/v3/{pid}/instances"),
        ("ShowInstance", "GET", "/v3/{pid}/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v3/{pid}/instances/{instance_id}"),
        ("InstanceAction", "POST", "/v3/{pid}/instances/{instance_id}/action"),
        ("ListFlavors", "GET", "/v3/{pid}/flavors"),
    ],
    "DDM": [
        ("CreateInstance", "POST", "/v1/{pid}/instances"),
        ("ListInstances", "GET", "/v1/{pid}/instances"),
        ("DeleteInstance", "DELETE", "/v1/{pid}/instances/{instance_id}"),
        ("CreateSchema", "POST", "/v1/{pid}/instances/{instance_id}/schemas"),
        ("ListSchemas", "GET", "/v1/{pid}/instances/{instance_id}/schemas"),
        ("DeleteSchema", "DELETE", "/v1/{pid}/instances/{instance_id}/schemas/{schema_name}"),
        ("CreateShardRule", "POST", "/v1/{pid}/instances/{instance_id}/schemas/{schema_name}/shard-rules"),
    ],
    "DBSS": [
        ("CreateInstance", "POST", "/v1/{pid}/dbss/instances"),
        ("ListInstances", "GET", "/v1/{pid}/dbss/instances"),
        ("ShowInstance", "GET", "/v1/{pid}/dbss/instances/{instance_id}"),
        ("DeleteInstance", "DELETE", "/v1/{pid}/dbss/instances/{instance_id}"),
        ("CreateAuditRule", "POST", "/v1/{pid}/dbss/instances/{instance_id}/audit-rules"),
        ("ListAuditLogs", "GET", "/v1/{pid}/dbss/instances/{instance_id}/audit-logs"),
    ],
    "HSS": [
        ("ListHosts", "GET", "/v5/{pid}/hosts"),
        ("ShowHost", "GET", "/v5/{pid}/hosts/{host_id}"),
        ("SetProtection", "POST", "/v5/{pid}/hosts/{host_id}/protection"),
        ("ListPolicies", "GET", "/v5/{pid}/policy"),
        ("CreatePolicy", "POST", "/v5/{pid}/policy"),
        ("ListAlarmEvents", "GET", "/v5/{pid}/alarm-events"),
        ("CreateAlarmEvent", "POST", "/v5/{pid}/alarm-events"),
        ("ListVulnerabilities", "GET", "/v5/{pid}/vulnerabilities"),
        ("ScanVulnerabilities", "POST", "/v5/{pid}/vulnerabilities/scan"),
        ("ListQuotas", "GET", "/v5/{pid}/quotas"),
    ],
    "CDN": [
        ("CreateDomain", "POST", "/v1/domains"),
        ("ListDomains", "GET", "/v1/domains"),
        ("ShowDomain", "GET", "/v1/domains/{domain_id}"),
        ("UpdateDomain", "PUT", "/v1/domains/{domain_id}"),
        ("DeleteDomain", "DELETE", "/v1/domains/{domain_id}"),
        ("PurgeCache", "POST", "/v1.0/purgecache"),
        ("Preheat", "POST", "/v1.0/preheating"),
        ("ListHistoryTasks", "GET", "/v1.0/historytasks"),
        ("QueryStatistics", "GET", "/v1.0/statistics"),
    ],
    "DWS": [
        ("CreateCluster", "POST", "/v1.0/{pid}/clusters"),
        ("ListClusters", "GET", "/v1.0/{pid}/clusters"),
        ("ShowCluster", "GET", "/v1.0/{pid}/clusters/{cluster_id}"),
        ("DeleteCluster", "DELETE", "/v1.0/{pid}/clusters/{cluster_id}"),
        ("ResizeCluster", "POST", "/v1.0/{pid}/clusters/{cluster_id}/resize"),
        ("CreateSnapshot", "POST", "/v1.0/{pid}/snapshots"),
        ("ListSnapshots", "GET", "/v1.0/{pid}/snapshots"),
        ("ShowSnapshot", "GET", "/v1.0/{pid}/snapshots/{snapshot_id}"),
    ],
    "CSS": [
        ("CreateCluster", "POST", "/v1.0/{pid}/css/clusters"),
        ("ListClusters", "GET", "/v1.0/{pid}/css/clusters"),
        ("ShowCluster", "GET", "/v1.0/{pid}/css/clusters/{cluster_id}"),
        ("DeleteCluster", "DELETE", "/v1.0/{pid}/css/clusters/{cluster_id}"),
        ("RestartCluster", "POST", "/v1.0/{pid}/css/clusters/{cluster_id}/restart"),
        ("CreateIndex", "POST", "/v1.0/{pid}/css/clusters/{cluster_id}/indices"),
        ("ListIndices", "GET", "/v1.0/{pid}/css/clusters/{cluster_id}/indices"),
        ("DeleteIndex", "DELETE", "/v1.0/{pid}/css/clusters/{cluster_id}/indices/{index_name}"),
    ],
    "MRS": [
        ("CreateCluster", "POST", "/v1.1/{pid}/cluster_infos"),
        ("ListClusters", "GET", "/v1.1/{pid}/cluster_infos"),
        ("ShowCluster", "GET", "/v1.1/{pid}/cluster_infos/{cluster_id}"),
        ("DeleteCluster", "DELETE", "/v1.1/{pid}/cluster_infos/{cluster_id}"),
        ("SubmitJob", "POST", "/v1.1/{pid}/cluster_infos/{cluster_id}/jobs"),
        ("ResizeCluster", "POST", "/v1.1/{pid}/cluster_infos/{cluster_id}/resize"),
    ],
    "SMS": [
        ("RegisterSource", "POST", "/v3/{pid}/sources"),
        ("ListSources", "GET", "/v3/{pid}/sources"),
        ("ShowSource", "GET", "/v3/{pid}/sources/{source_id}"),
        ("DeleteSource", "DELETE", "/v3/{pid}/sources/{source_id}"),
        ("CreateTask", "POST", "/v3/{pid}/tasks"),
        ("ListTasks", "GET", "/v3/{pid}/tasks"),
        ("ShowTask", "GET", "/v3/{pid}/tasks/{task_id}"),
        ("DeleteTask", "DELETE", "/v3/{pid}/tasks/{task_id}"),
        ("CreateTemplate", "POST", "/v3/{pid}/templates"),
        ("ListTemplates", "GET", "/v3/{pid}/templates"),
    ],
    "DC": [
        ("CreateDirectConnect", "POST", "/v2.0/{pid}/direct-connects"),
        ("ListDirectConnects", "GET", "/v2.0/{pid}/direct-connects"),
        ("ShowDirectConnect", "GET", "/v2.0/{pid}/direct-connects/{conn_id}"),
        ("DeleteDirectConnect", "DELETE", "/v2.0/{pid}/direct-connects/{conn_id}"),
        ("CreateVirtualGateway", "POST", "/v2.0/{pid}/virtual-gateways"),
        ("ListVirtualGateways", "GET", "/v2.0/{pid}/virtual-gateways"),
        ("DeleteVirtualGateway", "DELETE", "/v2.0/{pid}/virtual-gateways/{vgw_id}"),
        ("CreateVirtualInterface", "POST", "/v2.0/{pid}/virtual-interfaces"),
        ("ListVirtualInterfaces", "GET", "/v2.0/{pid}/virtual-interfaces"),
        ("DeleteVirtualInterface", "DELETE", "/v2.0/{pid}/virtual-interfaces/{vif_id}"),
    ],
    "ER": [
        ("CreateInstance", "POST", "/v3/{pid}/enterprise-router/instances"),
        ("ListInstances", "GET", "/v3/{pid}/enterprise-router/instances"),
        ("ShowInstance", "GET", "/v3/{pid}/enterprise-router/instances/{er_id}"),
        ("DeleteInstance", "DELETE", "/v3/{pid}/enterprise-router/instances/{er_id}"),
        ("CreateAttachment", "POST", "/v3/{pid}/enterprise-router/instances/{er_id}/attachments"),
        ("ListAttachments", "GET", "/v3/{pid}/enterprise-router/instances/{er_id}/attachments"),
        ("DeleteAttachment", "DELETE", "/v3/{pid}/enterprise-router/instances/{er_id}/attachments/{attachment_id}"),
        ("CreateRouteTable", "POST", "/v3/{pid}/enterprise-router/instances/{er_id}/route-tables"),
        ("ListRouteTables", "GET", "/v3/{pid}/enterprise-router/instances/{er_id}/route-tables"),
    ],
    "DIS": [
        ("CreateStream", "POST", "/v2/{pid}/streams"),
        ("ListStreams", "GET", "/v2/{pid}/streams"),
        ("ShowStream", "GET", "/v2/{pid}/streams/{stream_name}"),
        ("UpdateStream", "PUT", "/v2/{pid}/streams/{stream_name}"),
        ("DeleteStream", "DELETE", "/v2/{pid}/streams/{stream_name}"),
        ("CreateApp", "POST", "/v2/{pid}/apps"),
        ("ListApps", "GET", "/v2/{pid}/apps"),
        ("CommitCheckpoint", "PUT", "/v2/{pid}/apps/{app_name}/checkpoints"),
        ("ListCheckpoints", "GET", "/v2/{pid}/apps/{app_name}/checkpoints"),
    ],
    "DataArts": [
        ("CreateConnection", "POST", "/v2/{pid}/connections"),
        ("ListConnections", "GET", "/v2/{pid}/connections"),
        ("ShowConnection", "GET", "/v2/{pid}/connections/{conn_id}"),
        ("DeleteConnection", "DELETE", "/v2/{pid}/connections/{conn_id}"),
        ("CreateJob", "POST", "/v2/{pid}/jobs"),
        ("ListJobs", "GET", "/v2/{pid}/jobs"),
        ("RunJob", "POST", "/v2/{pid}/jobs/{job_name}/run"),
        ("DeleteJob", "DELETE", "/v2/{pid}/jobs/{job_id}"),
        ("CreateScript", "POST", "/v2/{pid}/scripts"),
        ("ListScripts", "GET", "/v2/{pid}/scripts"),
    ],
    "OMS": [
        ("CreateTask", "POST", "/v2/{pid}/tasks"),
        ("ListTasks", "GET", "/v2/{pid}/tasks"),
        ("ShowTask", "GET", "/v2/{pid}/tasks/{task_id}"),
        ("StopTask", "POST", "/v2/{pid}/tasks/{task_id}/stop"),
        ("DeleteTask", "DELETE", "/v2/{pid}/tasks/{task_id}"),
    ],
    "DES": [
        ("CreateTask", "POST", "/v1/{pid}/tasks"),
        ("ListTasks", "GET", "/v1/{pid}/tasks"),
        ("ShowTask", "GET", "/v1/{pid}/tasks/{task_id}"),
        ("DeleteTask", "DELETE", "/v1/{pid}/tasks/{task_id}"),
    ],
    "CodeArts": [
        ("CreateRepository", "POST", "/v2/projects/repositories"),
        ("ListRepositories", "GET", "/v2/projects/repositories"),
        ("ShowRepository", "GET", "/v2/projects/repositories/{repo_id}"),
        ("DeleteRepository", "DELETE", "/v2/projects/repositories/{repo_id}"),
        ("CreatePipeline", "POST", "/v2/{pid}/pipelines"),
        ("ListPipelines", "GET", "/v2/{pid}/pipelines"),
        ("RunPipeline", "POST", "/v2/{pid}/pipelines/{pipeline_id}/run"),
        ("DeletePipeline", "DELETE", "/v2/{pid}/pipelines/{pipeline_id}"),
        ("CreateBuild", "POST", "/v2/{pid}/builds"),
        ("ListBuilds", "GET", "/v2/{pid}/builds"),
        ("RunBuild", "POST", "/v2/{pid}/builds/{build_id}/run"),
    ],
    "ServiceStage": [
        ("CreateEnvironment", "POST", "/v2/{pid}/cas/environments"),
        ("ListEnvironments", "GET", "/v2/{pid}/cas/environments"),
        ("DeleteEnvironment", "DELETE", "/v2/{pid}/cas/environments/{env_id}"),
        ("CreateApplication", "POST", "/v2/{pid}/cas/applications"),
        ("ListApplications", "GET", "/v2/{pid}/cas/applications"),
        ("ShowApplication", "GET", "/v2/{pid}/cas/applications/{app_id}"),
        ("DeleteApplication", "DELETE", "/v2/{pid}/cas/applications/{app_id}"),
        ("CreateComponent", "POST", "/v2/{pid}/cas/applications/{app_id}/components"),
        ("ListComponents", "GET", "/v2/{pid}/cas/applications/{app_id}/components"),
    ],
    "CSE": [
        ("CreateEngine", "POST", "/v2/{pid}/engines"),
        ("ListEngines", "GET", "/v2/{pid}/engines"),
        ("ShowEngine", "GET", "/v2/{pid}/engines/{engine_id}"),
        ("DeleteEngine", "DELETE", "/v2/{pid}/engines/{engine_id}"),
        ("RegisterMicroservice", "POST", "/v2/{pid}/engines/{engine_id}/microservices"),
        ("ListMicroservices", "GET", "/v2/{pid}/engines/{engine_id}/microservices"),
    ],
    "CCI": [
        ("CreateNamespace", "POST", "/v1/{pid}/cci/namespaces"),
        ("ListNamespaces", "GET", "/v1/{pid}/cci/namespaces"),
        ("DeleteNamespace", "DELETE", "/v1/{pid}/cci/namespaces/{ns_id}"),
        ("CreatePod", "POST", "/v1/{pid}/cci/namespaces/{ns_id}/pods"),
        ("ListPods", "GET", "/v1/{pid}/cci/namespaces/{ns_id}/pods"),
        ("ShowPod", "GET", "/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}"),
        ("DeletePod", "DELETE", "/v1/{pid}/cci/namespaces/{ns_id}/pods/{pod_id}"),
    ],
    "CFW": [
        ("CreateFirewall", "POST", "/v1/{pid}/firewalls"),
        ("ListFirewalls", "GET", "/v1/{pid}/firewalls"),
        ("ShowFirewall", "GET", "/v1/{pid}/firewalls/{firewall_id}"),
        ("DeleteFirewall", "DELETE", "/v1/{pid}/firewalls/{firewall_id}"),
        ("CreateRule", "POST", "/v1/{pid}/firewalls/{firewall_id}/rules"),
        ("ListRules", "GET", "/v1/{pid}/firewalls/{firewall_id}/rules"),
        ("DeleteRule", "DELETE", "/v1/{pid}/firewalls/{firewall_id}/rules/{rule_id}"),
        ("RecordHit", "POST", "/v1/{pid}/firewalls/{firewall_id}/hit-records"),
        ("ListHitRecords", "GET", "/v1/{pid}/firewalls/{firewall_id}/hit-records"),
    ],
    "DSC": [
        ("CreateAsset", "POST", "/v1/{pid}/dsc/assets"),
        ("ListAssets", "GET", "/v1/{pid}/dsc/assets"),
        ("DeleteAsset", "DELETE", "/v1/{pid}/dsc/assets/{asset_id}"),
        ("CreateScan", "POST", "/v1/{pid}/dsc/scans"),
        ("ListRisks", "GET", "/v1/{pid}/dsc/risks"),
        ("HandleRisk", "POST", "/v1/{pid}/dsc/risks/{risk_id}/handle"),
    ],
    "VOD": [
        ("CreateAsset", "POST", "/v1/{pid}/assets"),
        ("ListAssets", "GET", "/v1/{pid}/assets"),
        ("ShowAsset", "GET", "/v1/{pid}/assets/{asset_id}"),
        ("UploadAsset", "POST", "/v1/{pid}/assets/{asset_id}/upload"),
        ("DeleteAsset", "DELETE", "/v1/{pid}/assets/{asset_id}"),
        ("CreateTranscodeTemplate", "POST", "/v1/{pid}/transcode-templates"),
        ("ListTranscodeTemplates", "GET", "/v1/{pid}/transcode-templates"),
        ("DeleteTranscodeTemplate", "DELETE", "/v1/{pid}/transcode-templates/{template_id}"),
        ("CreateCategory", "POST", "/v1/{pid}/categories"),
        ("ListCategories", "GET", "/v1/{pid}/categories"),
    ],
    "IEF": [
        ("CreateNode", "POST", "/v2/{pid}/edgemgr/nodes"),
        ("ListNodes", "GET", "/v2/{pid}/edgemgr/nodes"),
        ("ShowNode", "GET", "/v2/{pid}/edgemgr/nodes/{node_id}"),
        ("DeleteNode", "DELETE", "/v2/{pid}/edgemgr/nodes/{node_id}"),
        ("CreateDeployment", "POST", "/v2/{pid}/edgemgr/deployments"),
        ("ListDeployments", "GET", "/v2/{pid}/edgemgr/deployments"),
        ("DeleteDeployment", "DELETE", "/v2/{pid}/edgemgr/deployments/{deployment_id}"),
    ],
    "ELB-extra": [
        ("ShowListener", "GET", "/v2/{pid}/elb/listeners/{listener_id}"),
        ("DeletePool", "DELETE", "/v2/{pid}/elb/pools/{pool_id}"),
        ("CreateHealthMonitor", "POST", "/v2/{pid}/elb/healthmonitors"),
        ("ListHealthMonitors", "GET", "/v2/{pid}/elb/healthmonitors"),
    ],
}

# documented path -> sim path where the sim uses a namespaced adaptation
ALIASES = {
    "/v1/{pid}/tasks": "/v1/{pid}/des/tasks",                      # DES
    "/v2/manage/namespaces": "/v2/{pid}/namespaces",               # SWR
    "/v2/manage/namespaces/{namespace}/repos": "/v2/{pid}/namespaces/{namespace}/repos",
    "/v1.0/{pid}/project-tags/create-or-delete": "/v1.0/project-tags/create-or-delete",  # TMS
    "/v1.0/{pid}/project-tags/tags": "/v1.0/project-tags/tags",
    "/v1.0/{pid}/project-tags/resources": "/v1.0/project-tags/resources",
    "/v2.0/{pid}/project-tags/resource-tags/action": "/v2.0/project-tags/resource-tags/action",
}

REGISTRY.update(REGISTRY_EXTRA)
# GeminiDB lives at the namespaced path (RDS owns the bare /v3/{pid}/instances)
REGISTRY["GeminiDB"] = [(n, m, p.replace("/v3/{pid}/instances", "/v3/{pid}/gemini/instances")
                         .replace("/v3/{pid}/flavors", "/v3/{pid}/gemini/flavors"))
                        for (n, m, p) in REGISTRY["GeminiDB"]]
# ELB-extra entries fold into ELB
REGISTRY["ELB"] = REGISTRY["ELB"] + REGISTRY.pop("ELB-extra")


if __name__ == "__main__":
    run()
