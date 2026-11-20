"""Sub-API tests for the six services that gained endpoints (BMS, AS, SMN, CES, WAF, DLI)."""
import pytest
from fastapi.testclient import TestClient
from larrot.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


class TestBmsSubApis:
    def test_action_lifecycle(self, client):
        sid = client.post(f"/v1/{PID}/baremetalservers",
                          json={"name": "bms-1"}).json()["server"]["id"]
        assert client.post(f"/v1/{PID}/baremetalservers/{sid}/action",
                           json={"os-stop": {}}).json()["status"] == "SHUTOFF"
        assert client.post(f"/v1/{PID}/baremetalservers/{sid}/action",
                           json={"os-start": {}}).json()["status"] == "ACTIVE"
        r = client.post(f"/v1/{PID}/baremetalservers/{sid}/action", json={"nope": {}})
        assert r.status_code == 400 and r.json()["error_code"] == "BMS.0102"
        assert client.post(f"/v1/{PID}/baremetalservers/bad/action",
                           json={"os-stop": {}}).status_code == 404

    def test_nics_and_flavors(self, client):
        sid = client.post(f"/v1/{PID}/baremetalservers",
                          json={"name": "bms-2"}).json()["server"]["id"]
        r = client.get(f"/v1/{PID}/baremetalservers/{sid}/nics")
        assert len(r.json()["nics"]) == 1
        assert client.get(f"/v1/{PID}/baremetalservers/bad/nics").status_code == 404
        r = client.get(f"/v1/{PID}/baremetalservers/flavors")
        assert len(r.json()["flavors"]) == 2


class TestAsSubApis:
    def test_execute_policy_scales_group(self, client):
        gid = client.post(f"/v1/{PID}/scaling_group",
                          json={"scaling_group_name": "asg-1"}).json()["scaling_group_id"]
        pol = client.post(f"/v1/{PID}/scaling_policy",
                          json={"scaling_policy_name": "pol-1", "scaling_group_id": gid,
                                 "action": {"instance_num": 2}}).json()
        r = client.post(f"/v1/{PID}/scaling_policy/{pol['scaling_policy_id']}/execute")
        assert r.json()["executed"] is True

        r = client.get(f"/v1/{PID}/scaling_group/{gid}/instances")
        assert len(r.json()["instances"]) == 2
        assert all(i["status"] == "INSERVICE" for i in r.json()["instances"])

        assert client.post(f"/v1/{PID}/scaling_policy/bad/execute").status_code == 404
        assert client.get(f"/v1/{PID}/scaling_group/bad/instances").status_code == 404


class TestSmnSubApis:
    def test_subscription_lifecycle(self, client):
        urn = client.post(f"/v2/{PID}/notifications/topics",
                          json={"name": "t1"}).json()["topic_urn"]
        sub = client.post(f"/v2/{PID}/notifications/topics/{urn}/subscriptions",
                          json={"protocol": "https",
                                 "endpoint": "https://example.com/hook"}).json()
        sub_urn = sub["subscription_urn"]

        r = client.get(f"/v2/{PID}/notifications/topics/{urn}/subscriptions")
        assert len(r.json()["subscriptions"]) == 1

        assert client.delete(
            f"/v2/{PID}/notifications/topics/{urn}/subscriptions/{sub_urn}").status_code == 204
        assert client.get(
            f"/v2/{PID}/notifications/topics/{urn}/subscriptions").json()["subscriptions"] == []
        assert client.delete(
            f"/v2/{PID}/notifications/topics/{urn}/subscriptions/{sub_urn}").status_code == 404

    def test_show_topic(self, client):
        urn = client.post(f"/v2/{PID}/notifications/topics",
                          json={"name": "t2"}).json()["topic_urn"]
        assert client.get(f"/v2/{PID}/notifications/topics/{urn}").json()["name"] == "t2"
        assert client.get(f"/v2/{PID}/notifications/topics/bad").status_code == 404


class TestCesSubApis:
    def test_alarm_history(self, client):
        aid = client.post(f"/v1/{PID}/alarms",
                          json={"alarm_name": "cpu-high"}).json()["alarm_id"]
        r = client.get(f"/v1/{PID}/alarms/{aid}/history")
        assert r.json()["history"][0]["status"] == "alarm"
        assert client.get(f"/v1/{PID}/alarms/bad/history").status_code == 404

    def test_batch_metric_data(self, client):
        r = client.post(f"/v1.0/{PID}/batch-query/metric-data",
                        json={"metrics": [{"metric_name": "cpu_util", "dim_0": "i-123"}]})
        assert len(r.json()["metric_data_results"]) == 1
        assert r.json()["metric_data_results"][0]["data_points"][0]["value"] == 42.0


class TestWafSubApis:
    def test_host_policy_binding_and_rules(self, client):
        did = client.post(f"/v1/{PID}/waf/hosts",
                          json={"hostname": "app.example.com"}).json()["id"]
        pid_ = client.post(f"/v1/{PID}/waf/policies",
                           json={"name": "strict"}).json()["id"]

        # Bind policy to host
        r = client.put(f"/v1/{PID}/waf/hosts/{did}", json={"policy_id": pid_})
        assert r.json()["policy_id"] == pid_
        assert client.put(f"/v1/{PID}/waf/hosts/{did}",
                          json={"policy_id": "bad"}).status_code == 404

        # Rules under the policy
        rule = client.post(f"/v1/{PID}/waf/policies/{pid_}/rules",
                           json={"type": "white_ip",
                                  "conditions": [{"value": "1.2.3.4"}]}).json()
        r = client.get(f"/v1/{PID}/waf/policies/{pid_}/rules")
        assert r.json()["total"] == 1
        assert r.json()["rules"][0]["id"] == rule["id"]

        # Details
        assert client.get(f"/v1/{PID}/waf/hosts/{did}").json()["id"] == did
        assert client.get(f"/v1/{PID}/waf/policies/{pid_}").json()["name"] == "strict"
        assert client.get(f"/v1/{PID}/waf/hosts/bad").status_code == 404
        assert client.get(f"/v1/{PID}/waf/policies/bad").status_code == 404
        assert client.post(f"/v1/{PID}/waf/policies/bad/rules",
                           json={}).status_code == 404


class TestDliSubApis:
    def test_queue_lifecycle(self, client):
        q = client.post(f"/v1.0/{PID}/queues",
                        json={"queue_name": "etl", "cu_count": 32}).json()
        assert client.get(f"/v1.0/{PID}/queues").json()["total"] == 1
        assert client.post(f"/v1.0/{PID}/queues", json={}).status_code == 400
        assert client.delete(f"/v1.0/{PID}/queues/{q['queue_id']}").json()["is_success"] is True
        assert client.delete(f"/v1.0/{PID}/queues/{q['queue_id']}").status_code == 404

    def test_sql_job_lifecycle(self, client):
        r = client.post(f"/v1.0/{PID}/jobs/submit",
                        json={"sql": "SELECT count(*) FROM t", "queue_name": "default"})
        jid = r.json()["job_id"]
        assert r.json()["status"] == "RUNNING"

        client.app.state.sim.jobs.complete_all()
        job = client.get(f"/v1.0/{PID}/jobs/{jid}").json()
        assert job["status"] == "FINISHED"
        assert job["rows"] == 42

        r = client.get(f"/v1.0/{PID}/jobs")
        assert any(j["job_id"] == jid for j in r.json()["jobs"])
        assert client.get(f"/v1.0/{PID}/jobs/bad").status_code == 404
