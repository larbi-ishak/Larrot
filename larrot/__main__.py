"""Entry point: starts both REST (8200) and OBS (8201) servers.

SIM_HOST controls the bind address: 127.0.0.1 (default, local-only) or
0.0.0.0 (all interfaces - required inside Docker, use with care)."""

import os

import uvicorn


def main():
    """Run larrot: REST on :8200, OBS on :8201."""
    port = int(os.environ.get("SIM_PORT", "8200"))
    obs_port = int(os.environ.get("SIM_OBS_PORT", "8201"))
    host = os.environ.get("SIM_HOST", "127.0.0.1")

    print("Larrot - repeats Huawei Cloud")
    print(f"  REST: http://{host}:{port}  (59 services)")
    print(f"  OBS:  http://{host}:{obs_port}  (object storage)")
    print(f"  Dashboard: http://{host}:{port}/")
    print(f"  API Docs: http://{host}:{port}/docs")
    print(f"  AK: {os.environ.get('SIM_AK', 'HWYSIMAK00000001')}")
    print()

    # Run both servers concurrently
    import threading

    def run_obs():
        from .app import create_obs_app
        obs_app = create_obs_app()
        uvicorn.run(obs_app, host=host, port=obs_port, log_level="warning")

    obs_thread = threading.Thread(target=run_obs, daemon=True)
    obs_thread.start()

    from .app import create_app
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
