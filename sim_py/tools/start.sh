#!/usr/bin/env bash
# Start the huawei-sim Python server
cd "$(dirname "$0")/.."
export PYTHONPATH=.
exec python3 -c "
import threading, uvicorn, time
from huawei_sim.app import create_app, create_obs_app
app = create_app()
obs_app = create_obs_app()
threading.Thread(target=lambda: uvicorn.run(app, host='127.0.0.1', port=8200, log_level='error'), daemon=True).start()
threading.Thread(target=lambda: uvicorn.run(obs_app, host='127.0.0.1', port=8201, log_level='error'), daemon=True).start()
print('READY')
time.sleep(3600)
"
