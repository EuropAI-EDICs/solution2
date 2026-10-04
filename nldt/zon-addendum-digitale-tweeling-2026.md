# Addendum 2026 — Programma Zicht op Nederland · Digitale Tweeling

| | |
|---|---|
| **Status** | Concept voor bespreking · 4 oktober 2026 |
| **Voor wie** | Programmaraden ZoN / GI-beraad / Digitaal Tweeling-spoor |
| **Bij** | [Meerjarenvisie Zicht op Nederland](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424) (Beraad voor Geo-informatie, april 2024) |
| **Doel** | De 2024-visie niet herschrijven, maar bijwerken waar de nLDT-referentie-implementatie (Testbed 2026) ambities concreet heeft gemaakt |
| **Technische grounding** | [24-zichtopnl-alignment.md](24-zichtopnl-alignment.md) · [bestuurlijke-samenvatting.md](bestuurlijke-samenvatting.md) |

---

## 1. Waarom dit addendum

De meerjarenvisie blijft de stip op de horizon. De doctrinezin over het stelsel Digitale Tweeling Fysieke Leefomgeving (DTFL) — *niet één systeem, maar een geheel van afspraken* waarmee regionale en thematische tweelingen vergelijkbaar en optelbaar zijn, leveranciersonafhankelijk — staat. Wat sinds 2024 is veranderd: er is een werkende referentie-implementatie die die afspraken in open standaarden en aantoonbare runs vertaalt.

Dit addendum stelt voor om de **werkagenda** en de taal van programma **ZoN Digitale Tweeling** (spoor *Doorontwikkeling NGII*) daarop aan te laten sluiten. Datafundament, financiering, wetgeving en ondergrond blijven buiten dit addendum — dat is respectievelijk bronhouderswerk, nationaal programmawerk, of nog geen first-class domein in de referentie-implementatie.

---

## 2. Zes bijstellingen

### 2.1 Programma Digitale Tweeling: van abstracte afspraken naar bouwstenen

**Visie 2024.** DTFL = afspraken + standaarden voor visualisatie, analyse en reken-/simulatiemodellen (pas-toe-of-leg-uit).

**Voorstel 2026 — expliciet benoemen als bewezen bouwstenen:**

| Bouwsteen | Betekenis voor de werkagenda |
|---|---|
| **Recepten (recipes)** | Gestandaardiseerde, versieerbare rekenmodellen met schema-contract |
| **ValidationReport + PROV** | Gestandaardiseerde publicatie van uitkomsten; bit-identiek herhaalbaar |
| **OGC API Records / Processes** | Open federatie-interface i.p.v. één nationaal platform |
| **Agentlaag met harde grens** | *LLMs stellen voor, engines beslissen over cijfers* — cite-or-abstain, human-in-the-loop |

**Indicator werkagenda:** “Aantal gevalideerde recepten met PROV-annex dat in ≥1 andere organisatie of gebied hergebruikt is.”

### 2.2 Analyseren en AI: van experiment naar gestuurde inzet

**Visie 2024.** AI voor analyses en voorspellingen “experimenteel of op beperkte schaal”; zwakke schakel = gebrek aan standaardisatie van (reken)modellen en publicatie van uitkomsten.

**Voorstel 2026.** Gestuurde AI is onderdeel van de datawaardeketen *mits* kwantitatieve uitkomsten altijd uit deterministische engines komen. De standaardisatie van modellen én uitkomsten is geen open wens meer, maar een aantoonbaar patroon (recepten + validatie V0–V4).

**Niet doen:** AI als vervanging van wettelijke of fysische rekenmodellen presenteren.

### 2.3 Georganiseerd vertrouwen: van goodwill naar bewijs

**Visie 2024.** Vertrouwen via governance, bereidheid tot delen en “georganiseerd vertrouwen”.

**Voorstel 2026.** Aanvullen: vertrouwen als **bewijsbaar artefact** — receipt trail per job (gates, weigeringen, herleidbare claims, PROV). Bestuurlijke afspraken blijven nodig; technische aantoonbaarheid maakt ze uitvoerbaar.

### 2.4 Gebruiken: één rekenkern, meerdere toegangen

**Visie 2024.** Zelfde informatie “begrijpelijk met én zonder digitale kennis”; visualisaties ook voor bestuurders, beleidsadviseurs en burgers.

**Voorstel 2026.** Concretiseren als: **één deterministische rekenkern, meerdere toegangen** (planoloog / beleidsambtenaar / burger) — geen apart “burgermodel”. Ambtelijke voordeur (beleidskompas) eerst; publieke lens daarna, met DPIA vóór pilot.

**Integrale gebiedsafweging (piloot).** Plane D op Breda: ruimtelijke claim (woningverdichting / dak-PV) tegen de vijf waarden → trade-offrapport zonder geautomatiseerde winnaar. Recipe `breda-gebiedsafweging`; design in `docs/superpowers/specs/2026-10-04-breda-gebiedsafweging-plane-d-design.md`.

### 2.5 Europese kaders: DTAS / Toolbox / EDIC toevoegen

**Visie 2024.** Dataspaces, INSPIRE, Federatief Datastelsel, AI Act, algoritmeregister.

**Voorstel 2026.** In spoor *Kaderstelling* en programma Digitale Tweeling ook benoemen:

- Nederlandse **DTAS**-lijn (modules / “bouw eens, hergebruik vaak”)
- **EU LDT Toolbox Marketplace** als publicatiekanaal
- **LDT CitiVERSE EDIC** als Europees thuis voor ruimtelijke digitale-tweeling-assets

Zo blijft FDS/dataspace het nationale delen-van-data; DTAS/Toolbox wordt het delen-van-*functionaliteit*.

### 2.6 Optelbaarheid en algoritmeregister: van streefbeeld naar meetbaar

| Ambitie visie | Meetbaar doel 2026 |
|---|---|
| Optelbaarheid tot nationaal beeld | Zelfde indicator-recept,zelfde definities, in **≥2 gebieden** aantoonbaar (eerste test) |
| Transparantie algoritmen (algoritmeregister / AI Act) | Export per seam/recept uit bestaande PROV + seam catalogue, klaar voor registratie |

Beide staan al als ZN-1 / ZN-2 in de technische alignment ([24](24-zichtopnl-alignment.md)); dit addendum tilt ze naar de werkagenda.

---

## 3. Wat níet wijzigt in de 2024-visie

- De DTFL-doctrinezin (afsprakenstelsel, optellen, leveranciersonafhankelijk).
- Governance via GI-beraad en programmaraden.
- Urgentie van robuuste financiering (§6) — blijft nationaal.
- Ondergrond als streefbeeld — blijft relevant; nog geen first-class domein in de referentie-implementatie.
- Versterking datafundament / basisregistraties — blijft bij bronhouders en programma Datafundament.

---

## 4. Voorstel formulering voor de werkagenda (kort)

> *In het programma ZoN Digitale Tweeling werken we aan een DTFL als afsprakenstelsel. De nLDT-referentie-implementatie (Testbed 2026) toont dat gestandaardiseerde recepten, open procesinterfaces (OGC), bewijsbare uitkomsten (PROV/validatie) en een begrensde agentlaag samen de zwakke schakels “analyseren / visualiseren / gebruiken” versterken. We nemen twee meetbare verplichtingen over: (1) optelbaarheid via hetzelfde indicator-recept in minstens twee gebieden; (2) algoritmeregister-klare transparantie-export. Europese schaal loopt via DTAS, de EU LDT Toolbox Marketplace en LDT CitiVERSE EDIC. Ondergrond, financiering en wetgeving blijven buiten deze referentie; daar blijft de 2024-visie leidend.*

---

## 5. Bestuurlijke vraag

1. **Ken dit addendum toe** als bijlage bij spoor *Doorontwikkeling NGII* / programma Digitale Tweeling.
2. **Neem ZN-1 en ZN-2 op** in de meetbare indicatoren van de werkagenda.
3. **Mandateer Europese publicatie** van 2–3 gevalideerde modules (DTAS/Toolbox) als bewijs dat “pas-toe-of-leg-uit” voor rekenmodellen uitvoerbaar is.

---

## 6. Bronnen

- Meerjarenvisie ZoN (april 2024): [handlerdownloadfiles.ashx?idnv=2781424](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424)
- Technische mapping: [24-zichtopnl-alignment.md](24-zichtopnl-alignment.md)
- Bestuurlijke kern: [bestuurlijke-samenvatting.md](bestuurlijke-samenvatting.md)
- Europees arm: [23-dtas-alignment.md](23-dtas-alignment.md)
- Doelgroepen: [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md)
