#!/usr/bin/env bash
# Start de toolbox-sim (9191–9195; --eubd voegt 9196 toe).
set -euo pipefail
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
elif [ -x "../nldt/.venv/bin/python" ]; then PY="../nldt/.venv/bin/python"
else PY="python3"; fi
exec "$PY" -m app.server "$@"
