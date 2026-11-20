"""Tests for the tier-4 documented operations."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app, create_obs_app

PID = "79814d675f6142d9b4a8ee417b924444"
IMAGE = "1ce5800a-e487-4c1b-b264-3353a39e2b4b"
FLAVOR = "s6.large.2"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIamTier4:
    def test_agencies(self, client):
        a = client.post("/v3.0/OS-AGENCY/agencies",
                        json={"name": "cross-account"}).json()["agency"]
        assert any(x["name"] == "cross-account"
                  for x in client.get("/v3.0/OS-AGENCY/agencies").json()["agencies"])
        r = client.get(f"/v3.0/OS-AGENCY/agencies/{a['id']}")
        assert r.json()["agency"]["id"] == a["id"]
        r = client.put(f"/v3.0/OS-AGENCY/agencies/{a['id']}",
                       json={"description": "updated"})
        assert r.json()["agency"]["description"] == "updated"
        assert client.delete(f"/v3.0/OS-AGENCY/agencies/{a['id']}").status_code == 204
        assert client.get(f"/v3.0/OS-AGENCY/agencies/{a['id']}").status_code == 404
        assert client.post("/v3.0/OS-AGENCY/agencies", json={}).status_code == 400

    def test_project_show_update(self, client):
        r = client.get(f"/v3/projects/{PID}")
        assert r.json()["project"]["name"] == "ap-southeast-1"
        r = client.put(f"/v3/projects/{PID}", json={"description": "sim project"})
        assert r.status_code == 200
        assert client.get("/v3/projects/bad").status_code == 404

    def test_group_membership(self, client):
        u = client.post("/v3/users", json={"name": "carol"}).json()["user"]
        g = client.post("/v3/groups", json={"name": "team"}).json()["group"]
        assert client.put(f"/v3/groups/{g['id']}/users/{u['id']}").status_code == 204
        users = client.get(f"/v3/groups/{g['id']}/users").json()["users"]
        assert users[0]["id"] == u["id"]
        groups = client.get(f"/v3/users/{u['id']}/groups").json()["groups"]
        assert groups[0]["id"] == g["id"]
        assert client.delete(f"/v3/groups/{g['id']}/users/{u['id']}").status_code == 204
        assert client.delete(f"/v3/groups/{g['id']}/users/{u['id']}").status_code == 404
        assert client.get(f"/v3/groups/{g['id']}/users").json()["users"] == []

    def test_catalog(self, client):
        catalog = client.get("/v3/auth/catalog").json()["catalog"]
        assert any(s["type"] == "object-store" for s in catalog)


class TestApigTier4:
    def test_show_delete_flows(self, client):
        inst = client.post(f"/v2/{PID}/apigw/instances",
                           json={"name": "t4-inst"}).json()["id"]
        r = client.get(f"/v2/{PID}/apigw/instances/{inst}")
        assert r.status_code == 200
        grp = client.post(f"/v2/{PID}/apigw/groups",
                          json={"name": "t4-grp"}).json()["id"]
        assert client.get(f"/v2/{PID}/apigw/groups/{grp}").status_code == 200
        assert client.delete(f"/v2/{PID}/apigw/groups/{grp}").status_code == 204
        api = client.post(f"/v2/{PID}/apigw/apis",
                         json={"name": "t4-api"}).json()["id"]
        assert client.get(f"/v2/{PID}/apigw/apis/{api}").status_code == 200
        assert client.delete(f"/v2/{PID}/apigw/apis/{api}").status_code == 204
        env = client.post(f"/v2/{PID}/apigw/environments",
                         json={"name": "t4-env"}).json()["id"]
        assert client.delete(f"/v2/{PID}/apigw/environments/{env}").status_code == 204


class TestModelArtsTier4:
    def test_labels_and_samples(self, client):
        did = client.post(f"/v2/{PID}/datasets",
                          json={"dataset_name": "t4-ds"}).json()["dataset_id"]
        assert client.get(f"/v2/{PID}/datasets/{did}").json()["dataset_id"] == did

        r = client.post(f"/v2/{PID}/datasets/{did}/labels", json={"name": "cat"})
        assert r.status_code == 200
        assert client.post(f"/v2/{PID}/datasets/{did}/labels",
                           json={"name": "cat"}).status_code == 409
        labels = client.get(f"/v2/{PID}/datasets/{did}/labels").json()
        assert labels["total"] == 1
        r = client.put(f"/v2/{PID}/datasets/{did}/labels/cat", json={"name": "cats"})
        assert r.json()["labels"][0]["name"] == "cats"
        assert client.delete(f"/v2/{PID}/datasets/{did}/labels/cats").status_code == 204
        assert client.delete(f"/v2/{PID}/datasets/{did}/labels/cats").status_code == 404

        r = client.post(f"/v2/{PID}/datasets/{did}/samples",
                        json={"samples": [{"source": "obs://bucket/a.jpg"}]})
        assert len(r.json()["sample_ids"]) == 1
        samples = client.get(f"/v2/{PID}/datasets/{did}/samples").json()
        assert samples["total"] == 1


class TestCceTier4:
    def test_addons_cluster_nodes(self, client):
        c = client.post(f"/api/v3/projects/{PID}/clusters",
                        json={"cluster": {"name": "t4-cce", "flavor": "cce.s1.medium"}}).json()
        cid = c.get("cluster", c).get("id") or c.get("id")
        a = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/addons",
                        json={"addon_name": "core-dns"}).json()["addon"]
        addons = client.get(f"/api/v3/projects/{PID}/clusters/{cid}/addons").json()
        assert addons["count"] == 1

        r = client.put(f"/api/v3/projects/{PID}/clusters/{cid}",
                       json={"spec": {"displayName": "renamed-cce"}})
        assert r.json()["cluster"]["name"] == "renamed-cce"

        node = client.post(f"/api/v3/projects/{PID}/clusters/{cid}/nodes",
                           json={"node": {"name": "t4-node"}}).json()
        nid = node.get("node", node).get("id") or node.get("id")
        r = client.get(f"/api/v3/projects/{PID}/clusters/{cid}/nodes/{nid}")
        assert r.status_code == 200
        assert client.delete(
            f"/api/v3/projects/{PID}/clusters/{cid}/nodes/{nid}").status_code == 204
        assert client.get(
            f"/api/v3/projects/{PID}/clusters/{cid}/nodes/{nid}").status_code == 404


class TestEcsEipDnsTier4:
    def test_nova_interfaces(self, client):
        r = client.post(f"/v1.1/{PID}/cloudservers",
                        json={"server": {"imageRef": IMAGE, "flavorRef": FLAVOR,
                                          "name": "t4-vm"}})
        sid = r.json()["serverIds"][0]
        r = client.get(f"/v2.1/{PID}/servers/{sid}/os-interface")
        assert len(r.json()["interfaceAttachments"]) == 1

    def test_show_bandwidth(self, client):
        bws = client.get(f"/v2.0/{PID}/bandwidths").json()["bandwidths"]
        if bws:
            r = client.get(f"/v2.0/{PID}/bandwidths/{bws[0]['id']}")
            assert r.status_code == 200
        assert client.get(f"/v2.0/{PID}/bandwidths/bad").status_code == 404

    def test_update_zone(self, client):
        z = client.post("/v2/zones",
                        json={"name": "t4.example.com.", "email": "a@x.com"}).json()["zone"]
        r = client.put(f"/v2/zones/{z['id']}", json={"ttl": 600, "email": "b@x.com"})
        assert r.json()["zone"]["ttl"] == 600
        assert client.put("/v2/zones/bad", json={"ttl": 1}).status_code == 404


class TestSmnSwrIotDisTier4:
    def test_smn_template_and_topic(self, client):
        tid = client.post(f"/v2/{PID}/notifications/message_templates",
                          json={"message_template_name": "t4-tpl"}).json()["message_template_id"]
        r = client.get(f"/v2/{PID}/notifications/message_templates/{tid}")
        assert r.json()["name"] == "t4-tpl"
        urn = client.post(f"/v2/{PID}/notifications/topics",
                          json={"name": "t4-topic"}).json()["topic_urn"]
        r = client.put(f"/v2/{PID}/notifications/topics/{urn}",
                       json={"display_name": "renamed"})
        assert r.json()["display_name"] == "renamed"

    def test_swr_show_repo(self, client):
        client.post(f"/v2/{PID}/namespaces", json={"namespace": "t4"})
        client.post(f"/v2/{PID}/namespaces/t4/repos", json={"repository": "web"})
        r = client.get(f"/v2/{PID}/namespaces/t4/repos/web")
        assert r.status_code == 200 and r.json()["repository"] == "web"
        assert client.get(f"/v2/{PID}/namespaces/t4/repos/nope").status_code == 404

    def test_iotda_update_device(self, client):
        dev = client.post(f"/v5/iot/{PID}/devices",
                          json={"device_name": "t4-dev"}).json()["device_id"]
        r = client.put(f"/v5/iot/{PID}/devices/{dev}", json={"device_name": "renamed-dev"})
        assert r.json()["name"] == "renamed-dev"
        assert client.put(f"/v5/iot/{PID}/devices/bad", json={}).status_code == 404

    def test_dis_delete_checkpoint(self, client):
        client.post(f"/v2/{PID}/streams", json={"stream_name": "t4-stream"})
        client.post(f"/v2/{PID}/apps", json={"app_name": "t4-app"})
        client.put(f"/v2/{PID}/apps/t4-app/checkpoints",
                   json={"stream_name": "t4-stream", "checkpoint_state": "s1"})
        r = client.delete(f"/v2/{PID}/apps/t4-app/checkpoints?stream_name=t4-stream")
        assert r.status_code == 204
        assert client.delete(f"/v2/{PID}/apps/t4-app/checkpoints?stream_name=t4-stream").status_code == 404
        assert client.delete(f"/v2/{PID}/apps/t4-app/checkpoints").status_code == 400


class TestObsTier4:
    def test_multipart_copy_batchdelete_storageinfo(self, self_client=None):
        client = TestClient(create_obs_app())
        client.put("/t4-bucket")
        client.put("/t4-bucket/src.bin", content=b"payload-data")
        # copy object
        r = client.put("/t4-bucket/dst.bin", headers={"x-obs-copy-source": "/t4-bucket/src.bin"})
        assert r.status_code == 200 and "CopyObjectResult" in r.text
        assert client.get("/t4-bucket/dst.bin").content == b"payload-data"
        assert client.put("/t4-bucket/x.bin",
                          headers={"x-obs-copy-source": "/t4-bucket/nope"}).status_code == 404
        # multipart: initiate -> list uploads -> abort
        r = client.post("/t4-bucket/big.bin?uploads")
        assert "UploadId" in r.text
        import re as _re
        upload_id = _re.search(r"<UploadId>([^<]+)</UploadId>", r.text).group(1)
        r = client.get("/t4-bucket?uploads")
        assert "ListMultipartUploadsResult" in r.text and upload_id in r.text
        assert client.delete(f"/t4-bucket/big.bin?uploadId={upload_id}").status_code == 204
        # storageinfo
        r = client.get("/t4-bucket?storageinfo")
        assert "GetBucketStorageInfoResult" in r.text
        assert "<ObjectNumber>2</ObjectNumber>" in r.text
        # batch delete
        body = ('<Delete><Object><Key>src.bin</Key></Object>'
                '<Object><Key>missing.bin</Key></Object></Delete>')
        r = client.post("/t4-bucket?delete", content=body.encode())
        assert r.status_code == 200 and "src.bin" in r.text and "NoSuchKey" in r.text
        assert client.get("/t4-bucket/src.bin").status_code == 404


class TestFinalEight:
    """The last implemented-but-untested operations (full test coverage)."""

    def test_cbr_remove_vault_resources(self, client):
        v = client.post(f"/v3/{PID}/vaults",
                        json={"vault": {"name": "f8-vault", "resources": []}}).json()["vault"]
        client.post(f"/v3/{PID}/vaults/{v['id']}/addresources",
                    json={"resources": [{"id": "r1", "type": "OS::Nova::Server"}]})
        r = client.post(f"/v3/{PID}/vaults/{v['id']}/removeresources",
                        json={"remove_resource_ids": ["r1"]})
        assert r.status_code == 200

    def test_obs_upload_part(self):
        client = TestClient(create_obs_app())
        client.put("/f8-bucket")
        import re as _re
        r = client.post("/f8-bucket/big.bin?uploads")
        upload_id = _re.search(r"<UploadId>([^<]+)</UploadId>", r.text).group(1)
        r = client.put(f"/f8-bucket/big.bin?partNumber=1&uploadId={upload_id}",
                       content=b"part-one")
        assert r.status_code == 200 and "ETag" in r.headers
        r = client.get(f"/f8-bucket/big.bin?uploadId={upload_id}")
        assert "ListPartsResult" in r.text

    def test_tms_create_or_delete_tags(self, client):
        r = client.post("/v1.0/project-tags/create-or-delete",
                        json={"project_id": PID, "tags": [{"key": "env", "value": "t4"}]})
        assert r.status_code == 200

    def test_aom_create_alarm_rule(self, client):
        r = client.post(f"/v2/{PID}/aom/alarm-rules",
                        json={"alarm_rule_name": "f8-rule"})
        assert r.status_code == 200

    def test_dli_create_table(self, client):
        r = client.post(f"/v1.0/{PID}/tables",
                        json={"database_name": "f8db", "table_name": "events"})
        assert r.status_code == 200

    def test_antiddos_status(self, client):
        r = client.get(f"/v1/{PID}/antiddos/status?floating_ip_id=x")
        assert r.status_code == 200

    def test_bss_orders_and_pay(self, client):
        r = client.get("/v2/orders/customer-orders")
        assert r.status_code == 200
        r = client.post("/v2/orders/customer-orders/pay",
                        json={"order_id": "CS123"})
        assert r.status_code == 200
