# Toolbox-sim — runnable simulatie van de PoC-relevante EU LDT Toolbox-oplossingen

Eén lokaal FastAPI-proces dat instaat voor de zes oplossingen met hard bewijs
van PoC-gebruik (zie `catalogue.json` voor alle 20 catalogusoplossingen met
status en reden) en exact de HTTP-contracten spreekt die de nldt-adapters
al aanroepen. Ontwerp: `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md`.

| Poort | Oplossing |
|---|---|
| 9191 | Identity Management (OIDC, realm LDT) |
| 9192 | Data Platform — NGSI-LD-broker + UCS-proxy + Trino-stub |
| 9193 | Play & Visualise |
| 9194 | Use Cases & Scenarios |
| 9195 | Marketplace Agent |
| 9196 | EU Building Database-feed (alleen met `--eubd`) |

```bash
# fixtures (deterministisch, gecommit) hergenereren:
../nldt/.venv/bin/python build_fixtures.py
# sim starten (IM+DP+P&V+UCS+Marketplace):
./run_sim.sh
# inclusief EUBD-feed (vereist lokale PostGIS `exposure`):
TOOLBOX_SIM_EUBD_DSN="postgresql://marc@localhost:5432/exposure" \
  ../nldt/.venv/bin/python build_fixtures.py --eubd "$TOOLBOX_SIM_EUBD_DSN"
./run_sim.sh --eubd
# tests:
../nldt/.venv/bin/python -m pytest tests -q
```

Auth: sim-IM mint HS256-JWTs; het statische mesh-token `sim-toolbox-token`
(a2a-simulation) wordt ook geaccepteerd. Elke response draagt
`X-Sim-Provenance`. Geen verzonnen waarden: alles herleidbaar naar canonieke
run-artefacten of echte PostGIS-rijen.
