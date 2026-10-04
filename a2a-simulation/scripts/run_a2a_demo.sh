#!/usr/bin/env bash
# Live A2A dashboard (default http://127.0.0.1:9190)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${NLDT_PYTHON:-$ROOT/../deep-agents/.venv/bin/python}"
export PYTHONPATH="${ROOT}:${ROOT}/simulation:${ROOT}/../deep-agents:${ROOT}/../nldt"
export A2A_SIM_AUTH="${A2A_SIM_AUTH:-static}"
export NLDT_STATIC_TOKENS="${NLDT_STATIC_TOKENS:-sim-toolbox-token}"
exec "$PY" "$ROOT/simulation/demo_server.py"
