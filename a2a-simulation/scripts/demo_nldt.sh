#!/usr/bin/env bash
# PoC-mesh in nldt-modus: A2A → legacy nLDT orchestrator (:8085) → recipes/processes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NLDT="$(cd "$ROOT/../nldt" && pwd)"
PY="${NLDT}/.venv/bin/python"
DEEP="${ROOT}/../deep-agents/.venv/bin/python"
TOKEN="${NLDT_STATIC_TOKENS:-sim-toolbox-token}"

export A2A_SIM_MODE=nldt
export A2A_SIM_AUTH="${A2A_SIM_AUTH:-static}"
export NLDT_STATIC_TOKENS="$TOKEN"
export NLDT_AUTH_MODE="${NLDT_AUTH_MODE:-static}"
export NLDT_A2A_URL="${NLDT_A2A_URL:-http://127.0.0.1:8085}"
export NLDT_A2A_AUTO_HITL="${NLDT_A2A_AUTO_HITL:-1}"
export NLDT_OFFLINE="${NLDT_OFFLINE:-1}"

echo "=== nLDT stack (8081–8085) — PYTHONPATH alleen nldt/ ==="
if ! curl -sf "${NLDT_A2A_URL}/agent-card" -H "Authorization: Bearer ${TOKEN%%,*}" >/dev/null 2>&1; then
  echo "Start in andere terminal: ./scripts/start_nldt_stack.sh"
  echo "Of: cd ../nldt && PYTHONPATH=. NLDT_AUTH_MODE=static NLDT_STATIC_TOKENS=$TOKEN ./scripts/start-services.sh"
  exit 1
fi

echo "=== PoC proxy rijnland :9183 ==="
export PYTHONPATH="${ROOT}:${NLDT}"
A2A_POC_AGENT_ID=rijnland "$PY" -m agents.app &
PID_MESH=$!
sleep 2

echo "=== A2A 1.x → nLDT orchestrator ==="
export PYTHONPATH="${ROOT}:${NLDT}"
"$PY" -m federator.client send rijnland \
  "Execute recipe rijnland-peil-conflict offline demo"

kill "$PID_MESH" 2>/dev/null || true
echo ""
echo "LLM + nldt: export A2A_SIM_MODE=nldt && $DEEP -m orchestrator.demo_scenarios --start-mesh --mode nldt"
