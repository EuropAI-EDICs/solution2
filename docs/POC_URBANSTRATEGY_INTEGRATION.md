# Urban Strategy-integratie voor PoC-1 Utrecht (stiltegebied-geluid)

Integratie van de LDT-toolbox met
[**Urban Strategy**](https://doc.urbanstrategy.nl/) (Scenexus): hoe de
stiltegebied-abstention van [PoC-1 Utrecht](POC_RULE_GRAPH.md) (FR-W-11 /
NC-W-11, art. 9.26) wordt aangevuld met een decision-support
noise-screening via de Urban Strategy RestAPI. Design:
[`superpowers/specs/2026-09-29-urbanstrategy-stiltegebied-design.md`](superpowers/specs/2026-09-29-urbanstrategy-stiltegebied-design.md).

## Wat is Urban Strategy

Urban Strategy is een digital-twinplatform voor interactieve beleidsanalyse
(verkeer, lucht, geluid, …) op het Inter Model Broker (IMB)-framework. Voor
deze PoC is vooral relevant:

- **RestAPI** (OpenAPI 3.0, docs v0.6.4): `GET /login`,
  `GET /data/bin/{Bin}/get`, model-control onder `/data/models/…`
  — zie [Rest API references](https://doc.urbanstrategy.nl/develop/rest-api/);
- **Noise-model** (SRM-2): per receptor o.a. `L_AEQ`, `I_LDEN`
  — zie [Noise levels](https://doc.urbanstrategy.nl/analytics/noise/).

## Waarom PoC-1 en Urban Strategy elkaar aanvullen

| | PoC-1 Utrecht (wind) | Urban Strategy |
|---|---|---|
| vraagvorm | "waar mag een omgevingsplan X toestaan?" | "welk geluidniveau bereken ik op receptor Y?" |
| art. 9.26 | dB-drempels bekend, maar FR-W-11 abstaineert (geen akoestisch model) | levert `L_AEQ` per receptor |
| geometrie | stiltegebied-GIO (stille kern + bufferzone) | receptorpunten + bronnen in de DT-store |
| rol | juridische zone-waarheid | decision-support annex |

De natuurlijke koppeling: **de PoC levert stiltegebied-geometrie en
juridische drempels; Urban Strategy levert het noiseveld**. Slice 1 toetst
een SRM-2 traffic/industry-veld binnen stiltegebied; turbine-bronmodellering
is follow-up.

## Conceptmapping

| PoC-concept | Urban Strategy |
|---|---|
| NC-W-11 / art. 9.26 LAeq ≤ 40/45 dB | receptor `L_AEQ` vs thresholds |
| stiltegebied-GIO | zone-polygonen voor point-in-polygon |
| FR-W-11 (ambiguous) | blijft ambiguous; annex in `urbanstrategy-stiltegebied.json` |
| Critic / PROV | US-stap is PROV-entity; falen = degradation |

## Architectuur (slice 1)

Zelfde patroon als H3: één implementatie in `nldt/`, PoC via cache-first brug.

| Component | Pad |
|---|---|
| RestAPI-client | [`nldt/services/common/urbanstrategy_client.py`](../nldt/services/common/urbanstrategy_client.py) |
| Evaluatiekernel | [`nldt/services/common/us_stiltegebied.py`](../nldt/services/common/us_stiltegebied.py) |
| OGC-processen | `us-fetch-noise-receptors`, `us-stiltegebied-noise-eval` in `handlers.py` |
| Schema | [`nldt/schemas/us-stiltegebied-eval.schema.json`](../nldt/schemas/us-stiltegebied-eval.schema.json) (mirrored in `poc/schemas/`) |
| PoC-brug | [`poc/pipeline/usstep.py`](../poc/pipeline/usstep.py) |
| Wind-wiring | `poc/run.py` (na cartographer; `--skip-us` / `--refresh-us`) |

Offline default: fixtures onder `nldt/fixtures/urbanstrategy/` + cache
`poc/data/cache/us/`. Live pad: `US_LIVE=1` + `US_BASE_URL` /
`US_TOKEN` of `US_EMAIL`+`US_PASSWORD` + `US_BIN`.

## Fasering

**Slice 1 (deze oplevering)** — receptor exceedance screening, offline
fixtures, wind-run artifact, schema + tests.

**Slice 2 (follow-up)** — live model-start (`/data/models/...`), industry
noise met turbine-bronparameters, aparte stille-kern/bufferzone-GIO's wanneer
beschikbaar, Leaflet-laag in het wind-rapport.

## Verificatie

```bash
# nldt unit + process tests
cd nldt && .venv/bin/python -m pytest \
  tests/test_urbanstrategy_client.py \
  tests/test_us_stiltegebied.py \
  tests/test_urbanstrategy_processes.py -q

# poc offline bridge tests (fixtures committed)
cd poc && POC_US_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_usstep -q

# regenerate cache fixtures
cd poc && POC_US_OFFLINE= ../nldt/.venv/bin/python tests/make_us_fixtures.py
```

## Juridische grens

Urban Strategy is decision-support. Zone-algebra en pipeline-verdict blijven
ongewijzigd. FR-W-11 wordt niet automatisch geformaliseerd. Caveats in het
artifact vermelden expliciet: SRM-2 traffic/industry-veld, geen
turbine-bronmodellering in slice 1.
