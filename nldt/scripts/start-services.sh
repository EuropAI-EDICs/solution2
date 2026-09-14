#!/usr/bin/env bash
# Start all nLDT services (Fase 1–4).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT"
export NLDT_COOKBOOK_URL="${NLDT_COOKBOOK_URL:-http://localhost:8081}"
export NLDT_PROCESS_URL="${NLDT_PROCESS_URL:-http://localhost:8082}"
export NLDT_CATALOG_URL="${NLDT_CATALOG_URL:-http://localhost:8083}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Starting services on ports 8081–8085"
python -m services.cookbook.app &
PID1=$!
python -m services.process_adapter.app &
PID2=$!
python -m services.catalog_adapter.app &
PID3=$!
python -m services.context3d.app &
PID4=$!
python -m services.a2a.app &
PID5=$!

if [[ "${NLDT_START_MCP_HTTP:-0}" == "1" ]]; then
  echo "Starting MCP servers over streamable-http (auth: NLDT_AUTH_MODE/NLDT_STATIC_TOKENS)"
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8090 python -m services.mcp_servers.catalog_server &
  PID6=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8091 python -m services.mcp_servers.process_server &
  PID7=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8092 python -m services.mcp_servers.data_server &
  PID8=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8093 python -m services.mcp_servers.poc_server &
  PID9=$!
fi

cleanup() {
  kill "$PID1" "$PID2" "$PID3" "$PID4" "$PID5" ${PID6:-} ${PID7:-} ${PID8:-} ${PID9:-} 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1
echo "Ready: cookbook :8081, processes :8082, catalog :8083, context3d :8084, a2a :8085"
[[ "${NLDT_START_MCP_HTTP:-0}" == "1" ]] && echo "MCP-http: catalog :8090, process :8091, data :8092, poc :8093 (POST /mcp)"
wait
