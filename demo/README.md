# Demo-portaal — één website, alle demo's

Eén lokale website die alle LDT-toolbox-demo's aanroept: de agent–fase–tool
matrix, het transport-bewijs uit het modelregister, het golden-bewijs
van de M2-migratie en de test-suites. Offline, deterministisch, geen
API-sleutels — stdlib `http.server`.

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
| 1 · matrix | M1: de agent–fase–tool matrix uit fase-manifesten |
| 2 · transports verifiëren | M4: modelregister — processes-replay (met verdict-gate) + catalog-sha256 |
| 3 · golden-reproductie | M2: de pre-refactor golden artefacten worden canonisch identiek gereproduceerd |
| 4 · test-suites | fundament (contracten + V-tool) |

## Ontwerpnoot

De server zelf importeert **geen** native libs (shapely/GEOS): de
matrix-render draait als subprocess. Reden: native libs in het
ouderproces + `fork` laten child-processen op macOS segvallen (rc −11,
gevonden bij het bouwen van dit portaal). Alle overige endpoints waren
al subprocessen.

Het artefact-endpoint staat alleen whitelisted-bestandsnamen toe en valideert
het run-id-formaat.
