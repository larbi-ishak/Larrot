"""Terraform scenario: the huaweicloud provider applies against Larrot.

The provider is the #1 real-world Huawei Cloud client. This proves a
`terraform apply` works unchanged against the simulator (endpoint
overrides, no proxy needed). Skipped when terraform is not installed;
CI runs it with hashicorp/setup-terraform.
"""

import shutil
import socket
import subprocess
import threading
import time

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("terraform") is None, reason="terraform not installed")

AK = "HWYSIMAK00000001"
SK = "HWYSIMSK00000001"
PID = "79814d675f6142d9b4a8ee417b924444"

TF_CONFIG = """terraform {{
  required_providers {{
    huaweicloud = {{
      source = "huaweicloud/huaweicloud"
    }}
  }}
}}

provider "huaweicloud" {{
  region     = "ap-southeast-1"
  access_key = "{ak}"
  secret_key = "{sk}"
  project_id = "{pid}"
  endpoints = {{
    vpc = "{endpoint}"
    ecs = "{endpoint}"
    evs = "{endpoint}"
  }}
}}

resource "huaweicloud_vpc" "tf_test" {{
  name = "tf-test-vpc"
  cidr = "10.200.0.0/16"
}}
"""


@pytest.fixture(scope="module")
def endpoint():
    import httpx
    import uvicorn

    from larrot.app import create_app

    app = create_app()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1",
                                           port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.3)
            break
        except Exception:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def _tf(workdir, *args):
    return subprocess.run(
        ["terraform", *args], cwd=workdir, capture_output=True, text=True,
        timeout=300)


class TestTerraformScenario:
    def test_apply_and_destroy(self, endpoint, tmp_path_factory):
        workdir = tmp_path_factory.mktemp("tf")
        (workdir / "main.tf").write_text(TF_CONFIG.format(
            ak=AK, sk=SK, pid=PID, endpoint=endpoint))

        init = _tf(workdir, "init", "-input=false")
        assert init.returncode == 0, f"terraform init failed:\n{init.stderr}"

        plan = _tf(workdir, "plan", "-input=false", "-no-color", "-out=tfplan")
        assert plan.returncode == 0, f"terraform plan failed:\n{plan.stderr}"
        assert "1 to add" in plan.stdout

        apply = _tf(workdir, "apply", "-input=false", "-auto-approve",
                    "-no-color", "tfplan")
        assert apply.returncode == 0, f"terraform apply failed:\n{apply.stderr}"

        # The VPC must exist in the simulator
        import httpx
        r = httpx.get(f"{endpoint}/v1/{PID}/vpcs", timeout=10)
        names = [v["name"] for v in r.json()["vpcs"]]
        assert "tf-test-vpc" in names

        destroy = _tf(workdir, "destroy", "-input=false", "-auto-approve",
                      "-no-color")
        assert destroy.returncode == 0, f"terraform destroy failed:\n{destroy.stderr}"

        r = httpx.get(f"{endpoint}/v1/{PID}/vpcs", timeout=10)
        names = [v["name"] for v in r.json()["vpcs"]]
        assert "tf-test-vpc" not in names
