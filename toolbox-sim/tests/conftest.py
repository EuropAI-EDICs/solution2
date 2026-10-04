import sys
from pathlib import Path

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

import subprocess
import time

import httpx
import pytest


@pytest.fixture(scope="session")
def live_sim():
    proc = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=SIM_ROOT)
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:9191/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise AssertionError("sim kwam niet op binnen 20 s")
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)
