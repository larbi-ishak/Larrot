"""Tests for the service scaffolder: larrot new-service <name>.

The scaffolder is verified end-to-end: it generates a service, the
service registers in app.py, the routes appear in the OpenAPI spec, the
generated test file passes, and the workspace is restored afterwards.
"""

import os
import subprocess
import sys

import pytest

from larrot.scaffold import scaffold_service

ROOT = os.path.join(os.path.dirname(__file__), "..")
MOD = "zzscaffoldtest"
FILES = [
    os.path.join(ROOT, "larrot", "services", f"{MOD}.py"),
    os.path.join(ROOT, "tests", f"test_{MOD}.py"),
    os.path.join(ROOT, "larrot", "app.py"),
]


@pytest.fixture()
def clean_service():
    """Remove the scaffolded service before AND after each test."""
    _cleanup()
    with open(FILES[2]) as f:
        original_app = f.read()
    yield
    with open(FILES[2], "w") as f:
        f.write(original_app)
    _cleanup()


def _cleanup():
    for path in FILES[:2]:
        if os.path.exists(path):
            os.unlink(path)


class TestScaffold:
    def test_generates_and_registers(self, clean_service):
        report = scaffold_service(MOD, root=ROOT)
        assert report["registered"] is True
        assert os.path.exists(report["module"])
        assert os.path.exists(report["tests"])

        # verify in a fresh interpreter: the routes must be in the spec
        # (the parent process has larrot.app already imported, which would
        # not see the newly-written app.py)
        result = subprocess.run(
            [sys.executable, "-c", f"""
from fastapi.testclient import TestClient
from larrot.app import create_app
c = TestClient(create_app())
spec = c.get("/openapi.json").json()
assert "/v1/{{pid}}/{MOD}s" in spec["paths"], len(spec["paths"])
assert "/v1/{{pid}}/{MOD}s/{{rid}}" in spec["paths"]
print("OK")
"""],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
            env={**os.environ, "PYTHONPATH": ROOT})
        assert result.returncode == 0, f"routes missing:\n{result.stderr}"
        assert "OK" in result.stdout

    def test_generated_service_works(self, clean_service):
        scaffold_service(MOD, root=ROOT)
        result = subprocess.run(
            [sys.executable, "-c", f"""
from fastapi.testclient import TestClient
from larrot.app import create_app
c = TestClient(create_app())
pid = "79814d675f6142d9b4a8ee417b924444"
r = c.post(f"/v1/{{pid}}/{MOD}s", json={{"{MOD}": {{"name": "scaffolded"}}}})
assert r.status_code == 201, r.text
rid = r.json()["{MOD}"]["id"]
assert c.get(f"/v1/{{pid}}/{MOD}s/{{rid}}").json()["{MOD}"]["name"] == "scaffolded"
assert c.delete(f"/v1/{{pid}}/{MOD}s/{{rid}}").status_code == 204
assert c.get(f"/v1/{{pid}}/{MOD}s/{{rid}}").status_code == 404
print("OK")
"""],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
            env={**os.environ, "PYTHONPATH": ROOT})
        assert result.returncode == 0, f"CRUD failed:\n{result.stderr}"
        assert "OK" in result.stdout

    def test_generated_test_file_passes(self, clean_service):
        """Run the generated test file with pytest - it must pass."""
        report = scaffold_service(MOD, root=ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", report["tests"], "-q", "--tb=short"],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
            env={**os.environ, "PYTHONPATH": ROOT})
        assert result.returncode == 0, f"generated tests failed:\n{result.stdout}"

    def test_app_py_restored_after_failure(self, clean_service):
        """A bad service name must not corrupt app.py."""
        with open(FILES[2]) as f:
            before = f.read()
        with pytest.raises(ValueError):
            scaffold_service("123-bad-name", root=ROOT)
        with open(FILES[2]) as f:
            assert f.read() == before

    def test_slug_normalization(self):
        from larrot.scaffold import _slug
        assert _slug("My-Service") == "my_service"
        assert _slug("GaussDB") == "gaussdb"
        assert _slug("already_fine") == "already_fine"
