#!/usr/bin/env bash
# nLDT services voor A2A_SIM_MODE=nldt. PYTHONPATH = alleen nldt/ (geen a2a-simulation/agents!).
set -euo pipefail
NLDT="$(cd "$(dirname "$0")/../../nldt" && pwd)"
cd "$NLDT"
PY="${NLDT}/.venv/bin/python"
# Geen a2a-simulation op PYTHONPATH — anders shadowed nldt/agents.orchestrator
run_svc() {
  env PYTHONPATH="${NLDT}" \
    NLDT_AUTH_MODE="${NLDT_AUTH_MODE:-static}" \
    NLDT_STATIC_TOKENS="${NLDT_STATIC_TOKENS:-sim-toolbox-token}" \
    NLDT_OFFLINE="${NLDT_OFFLINE:-1}" \
    "$PY" -m "$1" &
}
echo "nLDT stack (PYTHONPATH=$NLDT only) — ports 8081–8085"
run_svc services.cookbook.app
run_svc services.process_adapter.app
run_svc services.catalog_adapter.app
run_svc services.a2a.app
sleep 2
echo "Ready. Test: curl -H 'Authorization: Bearer ${NLDT_STATIC_TOKENS%%,*}' http://127.0.0.1:8085/agent-card"
wait
