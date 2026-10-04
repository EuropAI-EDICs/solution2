#!/usr/bin/env bash
# PoC A2A mesh proxy → nLDT :8085. Start eerst start_nldt_stack.sh in andere terminal.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NLDT="$(cd "$ROOT/../nldt" && pwd)"
cd "$ROOT"
# PoC-server package heet ook `agents` — mesh draaien vanuit a2a-simulation/
export PYTHONPATH="${ROOT}:${NLDT}"
export A2A_SIM_MODE=nldt
export A2A_SIM_AUTH="${A2A_SIM_AUTH:-static}"
export NLDT_STATIC_TOKENS="${NLDT_STATIC_TOKENS:-sim-toolbox-token}"
export NLDT_AUTH_MODE="${NLDT_AUTH_MODE:-static}"
export NLDT_A2A_URL="${NLDT_A2A_URL:-http://127.0.0.1:8085}"
export NLDT_A2A_AUTO_HITL="${NLDT_A2A_AUTO_HITL:-1}"
export NLDT_OFFLINE="${NLDT_OFFLINE:-1}"

PY="${NLDT}/.venv/bin/python"
AGENTS=(breda utrecht rijnland eindhoven crosstrack minigim)
PIDS=()
cleanup() { for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

for id in "${AGENTS[@]}"; do
  A2A_POC_AGENT_ID="$id" "$PY" -m agents.app &
  PIDS+=("$!")
done
echo "PoC mesh A2A_SIM_MODE=nldt → $NLDT_A2A_URL (nLDT PYTHONPATH first)"
echo "Federator: export A2A_SIM_AUTH=static NLDT_STATIC_TOKENS=$NLDT_STATIC_TOKENS"
echo "  python -m federator.client send rijnland 'recipe rijnland-peil-conflict'"
wait
