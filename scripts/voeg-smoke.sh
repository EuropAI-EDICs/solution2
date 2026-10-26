#!/bin/sh
# voeg-smoke — éen offline S2-call via replay + éen decide tegen de fake
# sidecar. Draait zonder netwerk en zonder MLX.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VOEG="${VOEG_BIN:-$ROOT/../rustharness/target/debug/voeg}"
test -x "$VOEG" || { echo "bouw eerst: cargo build -p voeg"; exit 1; }
# Controller-goedgekeurde override (zelfde patroon als VOEG_BIN): het
# fake-sidecar-pad is via env te overschrijven zolang de voeg-branch nog
# niet gemerged is (binary/script leven nu in de worktree).
VOEG_LAYA_SCRIPT="${VOEG_LAYA_SCRIPT:-$ROOT/../rustharness/voeg/tests/python/fake_sidecar.py}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# questions-fixture
cat > "$TMP/q.json" <<'JSON'
{"routing": ["primary_poc"],
 "questions": {"primary_poc": {"type": "choice",
   "criteria": {"utrecht": "", "breda": ""}, "escalation": "arbiter"}}}
JSON

# 1) decide tegen de fake sidecar (hoge band → accept, geen LLM; env
# hoort vóór de opdracht, niet als argument)
out="$(VOEG_LAYA_PYTHON=python3 \
  VOEG_LAYA_SCRIPT="$VOEG_LAYA_SCRIPT" \
  VOEG_LAYA_CKPT=/ckpt \
  "$VOEG" decide --questions "$TMP/q.json" --request 'gewone vraag' \
  --runs-dir "$TMP/runs")"
echo "decide: $out"
echo "$out" | grep -q '"band":"high"'

# 2) ledger over die runs: leeg-goed (exit 0)
"$VOEG" ledger --runs-dir "$TMP/runs" > /dev/null
echo "smoke OK"
