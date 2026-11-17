# Runbook — Nota Ruimte / groeiregio Eindhoven (annotatie → toets → scenario)

| | |
|---|---|
| **Beleidshaak** | Ontwerp-Nota Ruimte: thema **wonen, werken, bereikbaarheid**; VISTA-strategie **Accommoderen** (sterke groei o.a. Eindhoven) — [kamerbericht 26-09-2025](https://www.rijksoverheid.nl/actueel/nieuws/2025/09/26/kabinet-stelt-nationale-omgevingsvisie-op-en-maakt-keuzes-ontwerp-nota-ruimte-naar-tweede-kamer) |
| **NOVEX-link** | Gemeentelijke uitvoering die provinciale arrangementen en nationale woningbouwkeuzes moet kunnen dragen |
| **Plan** | [PLAN_NOVEX_NOTA_RUIMTE.md](PLAN_NOVEX_NOTA_RUIMTE.md) §A7 tracé A |
| **Leitmotif** | AI verkent · rekenlaag toetst · mens beslist |

---

## Praatplaat

1. **Annotatie (DSO)** — welke regels horen bij deze plek?  
2. **Toets (RegelRecht, formalized subset)** — mag dit voorstel, gegeven feiten X?  
3. **Verkenning** — AI mag varianten voorstellen; scorecard filtert.  
4. **Mens** — jurist/college beslist (geen “gekoppeld door AI”).

Gemeten (fixture Woensel-proxy): **457 / 811** artikelen in DSO-hit uitvoerbaar (**≈56%**). Rest = onthouding. Bron: [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md).

---

## Commando’s (offline eerst)

```bash
cd /pad/naar/ldttoolbox

# 1. Overlap DSO ↔ formalisering (cache default = dso_overlap/out)
nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.compare \
  --instruments eindhoven --offline

# 2. TPOD-index + toets op geo-feiten
nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod \
  --instruments eindhoven --toets

# 3. UI
# nldt/simulation/regelrecht-demo.html
# nldt/simulation/poc-eindhoven.html  of  ?poc=eindhoven
```

Live Presenteren alleen met `DSO_API_KEY` (nooit committen).

bp2op-conversie: zie `poc-bp2op/README.md` — status “gekoppeld door AI” bestaat niet.

EDIC: `recipe:eindhoven-bp2op` → `novex_rol: gemeentelijke_uitvoering`, `nota_thema: wonen`.

---

## Succescriteria

- [x] Offline pad geverifieerd (25-10-2026): coverage ≈56%.  
- [ ] Sessie met gemeente / regio gehouden.  
- [ ] Nota-haak (Accommoderen / woningbouw) expliciet in slides.  
- [ ] Geen claim dat AI beslist.
