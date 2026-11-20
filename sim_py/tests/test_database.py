"""Tests for enhanced database services: RDS extras, GeminiDB, DDM, DBSS, DCS extras."""
import pytest
from fastapi.testclient import TestClient
from huawei_sim.app import create_app

PID = "79814d675f6142d9b4a8ee417b924444"


@pytest.fixture
def client():
    return TestClient(create_app())


def _create_rds_instance(client):
    r = client.post(f"/v3/{PID}/instances",
                    json={"instance": {"name": "test-db", "datastore": {"type": "MySQL", "version": "8.0"}}})
    return r.json()["instance"]["id"]


class TestRdsBackups:
    def test_backup_lifecycle(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/rds/backups",
                        json={"name": "test-backup", "instance_id": iid, "backup_type": "manual"})
        assert r.status_code == 200
        bid = r.json()["backup"]["id"]
        assert r.json()["backup"]["status"] == "BUILDING"

        r = client.get(f"/v3/{PID}/rds/backups?instance_id={iid}")
        assert r.json()["total"] >= 1

        r = client.get(f"/v3/{PID}/rds/backups/{bid}")
        assert r.status_code == 200

        r = client.delete(f"/v3/{PID}/rds/backups/{bid}")
        assert r.status_code == 204

    def test_restore(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/restore",
                        json={"backup_id": "some-backup"})
        assert r.status_code == 200
        assert r.json()["job_id"]


class TestRdsParameters:
    def test_list_and_update(self, client):
        iid = _create_rds_instance(client)
        r = client.get(f"/v3/{PID}/instances/{iid}/parameters")
        assert r.status_code == 200
        params = r.json()["parameters"]
        assert len(params) >= 8
        assert any(p["name"] == "max_connections" for p in params)
        assert any(p["name"] == "slow_query_log" for p in params)

        r = client.put(f"/v3/{PID}/instances/{iid}/parameters",
                        json={"parameters": [{"name": "max_connections", "value": "2000"}]})
        assert r.status_code == 200


class TestRdsReadReplicas:
    def test_replica_lifecycle(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/replicas",
                        json={"name": "read-replica-1", "flavor_ref": "rds.mysql.c2.large"})
        assert r.status_code == 200
        rid = r.json()["replica"]["id"]
        assert r.json()["replica"]["master_id"] == iid

        r = client.get(f"/v3/{PID}/instances/{iid}/replicas")
        assert r.json()["total"] >= 1

        r = client.delete(f"/v3/{PID}/instances/{iid}/replicas/{rid}")
        assert r.status_code == 204


class TestRdsDbUsers:
    def test_user_lifecycle(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/db-users",
                        json={"name": "app_user", "host": "192.168.%.%", "privileges": ["SELECT", "INSERT"]})
        assert r.status_code == 200
        assert r.json()["user"]["name"] == "app_user"

        r = client.get(f"/v3/{PID}/instances/{iid}/db-users")
        assert len(r.json()["users"]) >= 1

        r = client.delete(f"/v3/{PID}/instances/{iid}/db-users/app_user")
        assert r.status_code == 204


class TestRdsDatabases:
    def test_database_lifecycle(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/databases",
                        json={"name": "mydb", "character_set": "utf8mb4"})
        assert r.status_code == 200
        assert r.json()["database"]["name"] == "mydb"

        r = client.get(f"/v3/{PID}/instances/{iid}/databases")
        assert len(r.json()["databases"]) >= 1

        r = client.delete(f"/v3/{PID}/instances/{iid}/databases/mydb")
        assert r.status_code == 204


class TestRdsLogs:
    def test_slow_logs(self, client):
        iid = _create_rds_instance(client)
        r = client.get(f"/v3/{PID}/instances/{iid}/slow-logs")
        assert r.status_code == 200
        logs = r.json()["slow_logs"]
        assert len(logs) >= 2
        assert "sql" in logs[0]
        assert "query_time" in logs[0]

    def test_error_logs(self, client):
        iid = _create_rds_instance(client)
        r = client.get(f"/v3/{PID}/instances/{iid}/error-logs")
        assert r.status_code == 200
        assert len(r.json()["error_logs"]) >= 1
        assert r.json()["error_logs"][0]["level"] == "ERROR"


class TestRdsFailover:
    def test_failover(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/failover")
        assert r.status_code == 200
        assert r.json()["failover_mode"] == "auto"

    def test_switchover(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/switchover",
                        json={"target_instance_id": "other-id"})
        assert r.status_code == 200


class TestRdsActions:
    def test_resize_flavor(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/action",
                        json={"resize": {"flavor_ref": "rds.mysql.c2.xlarge"}})
        assert r.status_code == 200
        assert r.json()["action"] == "resize_flavor"

    def test_extend_volume(self, client):
        iid = _create_rds_instance(client)
        r = client.post(f"/v3/{PID}/instances/{iid}/action",
                        json={"extend": {"size": 200}})
        assert r.status_code == 200
        assert r.json()["action"] == "extend_volume"
        assert r.json()["new_size"] == 200


class TestGeminiDB:
    def test_cassandra_instance(self, client):
        r = client.post(f"/v3/{PID}/gemini/instances",
                        json={"name": "test-cassandra", "engine": "cassandra", "nodes": 3})
        assert r.status_code == 200
        iid = r.json()["instance"]["id"]
        assert r.json()["instance"]["engine"] == "cassandra"
        assert r.json()["instance"]["nodes"] == 3

        r = client.get(f"/v3/{PID}/gemini/instances")
        assert r.json()["total"] >= 1

        r = client.get(f"/v3/{PID}/gemini/instances/{iid}")
        assert r.status_code == 200

        r = client.delete(f"/v3/{PID}/gemini/instances/{iid}")
        assert r.status_code == 204

    def test_flavors(self, client):
        r = client.get(f"/v3/{PID}/gemini/flavors")
        assert r.status_code == 200
        assert len(r.json()["flavors"]) >= 4
        assert any(f["engine"] == "cassandra" for f in r.json()["flavors"])
        assert any(f["engine"] == "influxdb" for f in r.json()["flavors"])


class TestDDM:
    def test_ddm_instance_and_schema(self, client):
        # Create DDM instance
        r = client.post(f"/v1/{PID}/instances",
                        json={"name": "test-ddm", "node_num": 4})
        assert r.status_code == 200
        iid = r.json()["instance"]["id"]

        # Create schema with sharding
        r = client.post(f"/v1/{PID}/instances/{iid}/schemas",
                        json={"name": "my_schema", "shard_num": 16, "shard_mode": "hash"})
        assert r.status_code == 200
        assert r.json()["schema"]["shard_num"] == 16

        # List schemas
        r = client.get(f"/v1/{PID}/instances/{iid}/schemas")
        assert len(r.json()["schemas"]) >= 1

        # Create shard rule
        r = client.post(f"/v1/{PID}/instances/{iid}/schemas/my_schema/shard-rules",
                        json={"table_name": "orders", "shard_column": "order_id", "shard_num": 16})
        assert r.status_code == 200
        assert r.json()["shard_rule"]["shard_column"] == "order_id"

        # Delete schema
        r = client.delete(f"/v1/{PID}/instances/{iid}/schemas/my_schema")
        assert r.status_code == 204


class TestDBSS:
    def test_audit_instance(self, client):
        r = client.post(f"/v1/{PID}/dbss/instances",
                        json={"name": "test-audit", "audit_types": ["MySQL", "PostgreSQL"]})
        assert r.status_code == 200
        iid = r.json()["instance"]["id"]
        assert "MySQL" in r.json()["instance"]["audit_types"]

        r = client.get(f"/v1/{PID}/dbss/instances")
        assert r.json()["total"] >= 1

    def test_audit_rules_and_logs(self, client):
        r = client.post(f"/v1/{PID}/dbss/instances",
                        json={"name": "audit-test"})
        iid = r.json()["instance"]["id"]

        r = client.post(f"/v1/{PID}/dbss/instances/{iid}/audit-rules",
                        json={"name": "high-risk", "risk_level": "HIGH", "action": "ALARM"})
        assert r.status_code == 200
        assert r.json()["risk_level"] == "HIGH"

        r = client.get(f"/v1/{PID}/dbss/instances/{iid}/audit-logs")
        assert len(r.json()["audit_logs"]) >= 2
        assert any(log["risk_level"] == "HIGH" for log in r.json()["audit_logs"])


class TestDCSExtras:
    def test_backup_and_restore(self, client):
        # Create DCS instance
        r = client.post(f"/v2/{PID}/instances", json={"name": "test-redis", "engine": "Redis"})
        iid = r.json()["instance_id"]

        # Create backup
        r = client.post(f"/v2/{PID}/instances/{iid}/backups", json={"backup_type": "manual"})
        assert r.status_code == 200
        bid = r.json()["backup_id"]

        # List backups
        r = client.get(f"/v2/{PID}/instances/{iid}/backups")
        assert r.json()["total"] >= 1

        # Restore
        r = client.post(f"/v2/{PID}/instances/{iid}/restore", json={"backup_id": bid})
        assert r.status_code == 200

        # Delete backup
        r = client.delete(f"/v2/{PID}/instances/{iid}/backups/{bid}")
        assert r.status_code == 204

    def test_parameters(self, client):
        r = client.post(f"/v2/{PID}/instances", json={"name": "param-redis"})
        iid = r.json()["instance_id"]
        r = client.get(f"/v2/{PID}/instances/{iid}/parameters")
        assert r.status_code == 200
        assert len(r.json()["parameters"]) >= 5
        assert any(p["name"] == "maxmemory-policy" for p in r.json()["parameters"])

    def test_restart_and_resize(self, client):
        r = client.post(f"/v2/{PID}/instances", json={"name": "restart-redis"})
        iid = r.json()["instance_id"]
        r = client.post(f"/v2/{PID}/instances/{iid}/restart")
        assert r.status_code == 200
        r = client.post(f"/v2/{PID}/instances/{iid}/resize", json={"new_capacity": 8})
        assert r.status_code == 200
        assert r.json()["new_capacity"] == 8

    def test_big_keys_and_hot_keys(self, client):
        r = client.post(f"/v2/{PID}/instances", json={"name": "analysis-redis"})
        iid = r.json()["instance_id"]
        r = client.get(f"/v2/{PID}/instances/{iid}/big-keys")
        assert r.status_code == 200
        assert len(r.json()["big_keys"]) >= 2
        r = client.get(f"/v2/{PID}/instances/{iid}/hot-keys")
        assert r.status_code == 200
        assert len(r.json()["hot_keys"]) >= 2
        assert r.json()["hot_keys"][0]["qps"] > 0
