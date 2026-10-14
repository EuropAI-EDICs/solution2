# Toolbox-sim — runnable simulatie van alle twintig catalogus-oplossingen

Eén lokaal FastAPI-proces dat alle twintig catalogusoplossingen van de EU LDT
Toolbox simuleert (zie `catalogue.json` voor status, evidence en grounding per
oplossing) en exact de HTTP-contracten spreekt die de nldt-adapters
al aanroepen. Ontwerp: `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md`
en `docs/superpowers/specs/2026-10-14-toolbox-sim-full-catalogue-design.md`.

| Poort | Oplossing |
|---|---|
| 9191 | Identity Management (OIDC, realm LDT) |
| 9192 | Data Platform — NGSI-LD-broker + UCS-proxy + Trino-stub |
| 9193 | Play & Visualise (incl. kaartweergave op `/ui/map`) |
| 9194 | Use Cases & Scenarios |
| 9195 | Marketplace Agent |
| 9196 | EU Building Database-feed (alleen met `--eubd`) |
| 9197 | Data Space Ready — EDC-stub (alleen met `--full`) |
| 9198 | Algoritmmodellen — alle 7 achter één endpoint (alleen met `--full`) |
| 9199 | Participate (alleen met `--full`) |
| 9200 | Federated Learning (alleen met `--full`) |
| 9201 | AI Notebook (alleen met `--full`) |
| 9202 | Data Modeller (alleen met `--full`) |
| 9203 | Integrated Environment (alleen met `--full`) |
| 9204 | City Innovation Planner (alleen met `--full`) |

Zonder vlaggen start de sim 9191–9195 (bestaand gedrag). Met `--eubd` komt de
EUBD-feed op 9196 erbij; met `--full` de acht catalogus-apps op 9197–9204
(Data Space Ready, algoritmmodellen, Participate, Federated Learning,
AI Notebook, Data Modeller, Integrated Environment, City Innovation Planner).

```bash
# fixtures (deterministisch, gecommit) hergenereren:
../nldt/.venv/bin/python build_fixtures.py
# sim starten (IM+DP+P&V+UCS+Marketplace):
./run_sim.sh
# inclusief EUBD-feed (vereist lokale PostGIS `exposure`):
TOOLBOX_SIM_EUBD_DSN="postgresql://marc@localhost:5432/exposure" \
  ../nldt/.venv/bin/python build_fixtures.py --eubd "$TOOLBOX_SIM_EUBD_DSN"
./run_sim.sh --eubd
# volledige catalogus: 9191–9204 (9196 vereist --eubd, 9197–9204 vereisen --full):
./run_sim.sh --full --eubd
# tests:
../nldt/.venv/bin/python -m pytest tests -q
```

## NLDT_FULL_SIM-adaptertests

De full-catalogus-adapters worden écht against de sim getest in
`nldt/tests/test_full_catalogue_adapters.py` (EDC-negotiate/transfer via
`dataspace_connector`, model-runs via `UCSAdapter`). Start de sim met `--full`
en draai daarna met `NLDT_FULL_SIM=1` — zonder die env skippen de live-tests
netjes (de offline UCSAdapter merge/strip-tests draaien altijd):

```bash
cd toolbox-sim && ../nldt/.venv/bin/python -m app.server --full
# tweede terminal:
cd nldt && NLDT_FULL_SIM=1 .venv/bin/python -m pytest tests/test_full_catalogue_adapters.py -q
```

`NLDT_EDC_MANAGEMENT_URL` (standaard `http://127.0.0.1:9197`) en
`NLDT_EDC_MANAGEMENT_TOKEN` (standaard `sim-toolbox-token`) worden door de
testmodule automatisch gezet; eigen waarden winnen via `os.environ.setdefault`.

Auth: sim-IM mint HS256-JWTs; het statische mesh-token `sim-toolbox-token`
(a2a-simulation) wordt ook geaccepteerd. Elke response draagt
`X-Sim-Provenance`. Geen verzonnen waarden: alles herleidbaar naar canonieke
run-artefacten of echte PostGIS-rijen; modellen zonder lokale grondslag zijn
expliciet `syntheticSeed`-gemarkeerd (zie `grounding` in `catalogue.json`).
