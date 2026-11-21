"""Testcontainers module: Larrot as a Docker container for test suites.

The LocalStack distribution pattern: one class that starts the
simulator, waits for it, and hands you a ready endpoint with
credentials. Requires Docker and `pip install larrot[testcontainers]`;
build the image first with `docker build -t larrot .` (or pass image=).

    from larrot.testcontainers import LarrotContainer

    with LarrotContainer() as larrot:
        endpoint = larrot.get_endpoint()      # http://172.17.0.2:8200
        ak, sk = larrot.access_key, larrot.secret_key
"""

DEFAULT_IMAGE = "larrot:latest"

AK = "HWYSIMAK00000001"
SK = "HWYSIMSK00000001"
PROJECT_ID = "79814d675f6142d9b4a8ee417b924444"
REGION = "ap-southeast-1"


class LarrotContainer:
    """Larrot in Docker: start, wait for health, stop."""

    def __init__(self, image: str = DEFAULT_IMAGE, rest_port: int = 8200,
                 obs_port: int = 8201, env: dict = None):
        try:
            from testcontainers.core.container import DockerContainer
        except ImportError as e:
            raise SystemExit(
                "LarrotContainer needs testcontainers: "
                "pip install larrot[testcontainers]") from e
        self._c = DockerContainer(image)
        self._rest_port = rest_port
        self._obs_port = obs_port
        self._c.with_exposed_ports(rest_port, obs_port)
        # 0.0.0.0 is required inside a container for port mapping to work
        self._c.with_env("SIM_HOST", "0.0.0.0")
        for k, v in (env or {}).items():
            self._c.with_env(k, v)
        self.access_key = AK
        self.secret_key = SK
        self.project_id = PROJECT_ID
        self.region = REGION

    # --- lifecycle ------------------------------------------------------
    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def start(self) -> "LarrotContainer":
        self._c.start()
        import time

        import httpx
        for _ in range(60):
            try:
                httpx.get(f"{self.get_endpoint()}/health", timeout=1)
                return self
            except Exception:
                time.sleep(0.5)
        raise TimeoutError("larrot container did not become healthy")

    def stop(self):
        self._c.stop()

    # --- endpoints ------------------------------------------------------
    def get_endpoint(self) -> str:
        return (f"http://{self._c.get_container_host_ip()}:"
                f"{self._c.get_exposed_port(self._rest_port)}")

    def get_obs_endpoint(self) -> str:
        return (f"http://{self._c.get_container_host_ip()}:"
                f"{self._c.get_exposed_port(self._obs_port)}")
