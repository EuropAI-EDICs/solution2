#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/../deep-agents:${ROOT}/../nldt:${ROOT}"
export A2A_SIM_MODE="${A2A_SIM_MODE:-simulate}"
export A2A_SIM_AUTH="${A2A_SIM_AUTH:-static}"
export NLDT_STATIC_TOKENS="${NLDT_STATIC_TOKENS:-sim-toolbox-token}"

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

PYTHON="${NLDT_PYTHON:-}"
if [[ -z "$PYTHON" && -x "${ROOT}/../nldt/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/../nldt/.venv/bin/python"
fi
PYTHON="${PYTHON:-python3}"

AGENTS=(breda utrecht rijnland eindhoven crosstrack minigim)
for id in "${AGENTS[@]}"; do
  A2A_POC_AGENT_ID="$id" "$PYTHON" -m agents.app &
  PIDS+=("$!")
done

echo "A2A PoC mesh (${A2A_SIM_MODE}) — agents: ${AGENTS[*]}"
echo "A2A 1.x + auth=${A2A_SIM_AUTH} mode=${A2A_SIM_MODE} token=${NLDT_STATIC_TOKENS%%,*}"
echo "export A2A_SIM_AUTH=static NLDT_STATIC_TOKENS=sim-toolbox-token  # for federator CLI too"
echo "Try: python -m federator.client send breda 'Plan breda-five-value-scan'"
echo "Press Ctrl+C to stop."

wait
