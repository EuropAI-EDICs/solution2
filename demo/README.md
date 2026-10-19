# Demo-portaal — één website, alle demo's

Eén lokale website die alle LDT-toolbox-demo's aanroept: de agent–fase–tool
matrix van beide pilots, de MiniGIM-gebiedscheck (met rapport en per-run
fase-matrix), het transport-bewijs uit het modelregister, het golden-bewijs
van de M2-migratie en de vier test-suites. Offline, deterministisch, geen
API-sleutels — stdlib `http.server` (zelfde patroon als
`deep-agents/live_server.py`).

## Start

```bash
cd /Users/marc/Projecten/ldttoolbox
nldt/.venv/bin/python demo/server.py
# → http://127.0.0.1:8766/
```

Gebruik de venv-interpreter (`nldt/.venv/bin/python`): systeem-python heeft
geen shapely. Alle demo-URL's zijn GET en dus deelbaar
(`/api/matrix?poc=nspd`, `/api/suite?name=deepagents`, …).

## Wat het portaal laat zien

| sectie | bewijs uit |
|---|---|
| 1 · matrix minigim + nspd | M1: de agent–fase–tool matrix uit beide fase-manifesten |
| 2 · gebiedscheck draaien | M2: echte run op het fundament — report.html, fase-matrix.md per run, V0–V3, verdict pass |
| 3 · transports verifiëren | M4: modelregister — processes-replay (met verdict-gate) + a2a Agent Card-check + catalog-sha256 |
| 4 · golden-reproductie | M2: de pre-refactor golden artefacten worden canonisch identiek gereproduceerd |
| 5 · vier test-suites | fundament (contracten + V-tool) · minigim · nspd (tweede pilot) · deep-agents (slotgates) |
| 6 · externe demo's | deep-agents-dashboard (:8765, Ollama vereist) en NSPD-Leia-viewer (:8000) — status-pills bovenaan |

## Ontwerpnoot

De server zelf importeert **geen** native libs (shapely/GEOS): de
matrix-render draait als subprocess. Reden: native libs in het
ouderproces + `fork` laten child-processen op macOS segvallen (rc −11,
gevonden bij het bouwen van dit portaal). Alle overige endpoints waren
al subprocessen.

De run-artefacten komen uit `poc-minigim/runs/` (git-ignored); het
artefact-endpoint staat alleen whitelisted-bestandsnamen toe en valideert
het run-id-formaat.
