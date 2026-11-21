"""Testcontainers module: LarrotContainer starts the simulator in Docker.

Skipped when Docker is not reachable; CI builds the image and runs it.
"""

import subprocess

import pytest

pytest.importorskip("testcontainers",
                     reason="testcontainers not installed (pip install larrot[testcontainers])")


def _docker_ok() -> bool:
    try:
        return subprocess.run(["docker", "info"],
                              capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


pytestmark = pytest.mark.skipif(not _docker_ok(), reason="Docker not reachable")


@pytest.fixture(scope="module")
def container():
    from larrot.testcontainers import LarrotContainer
    with LarrotContainer() as c:
        yield c


class TestLarrotContainer:
    def test_healthy_and_serves(self, container):
        import httpx
        r = httpx.get(f"{container.get_endpoint()}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_real_api_call(self, container):
        import httpx
        r = httpx.get(
            f"{container.get_endpoint()}/v1/{container.project_id}/cloudservers/detail",
            timeout=10)
        assert r.status_code == 200
        assert "servers" in r.json()

    def test_obs_endpoint(self, container):
        import httpx
        r = httpx.get(f"{container.get_obs_endpoint()}/", timeout=10)
        assert r.status_code == 200
