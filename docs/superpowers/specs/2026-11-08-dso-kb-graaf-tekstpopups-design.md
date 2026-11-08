# Ontwerp — Tekst- en RegelRecht-popups in de DSO-kennisgraaf

| | |
|---|---|
| **Datum** | 2026-11-08 |
| **Status** | uitwerking volgt direct (gebaseerd op het expliciete gebruikersverzoek: "niet de coderingen maar de echte tekst en hoe die mogelijk is omgezet naar regelrecht") |
| **Scope** | rijke tooltips voor de kennisgraaf in Tab 7: echte wettekst + leesbare RegelRecht-omzetting, build-time gerenderd |
| **Aansluiting** | [Kennisgraaf-spec](2026-11-08-dso-kb-kennisgraaf-design.md) (+ errata) · [Tab 7-spec](2026-11-08-dso-kb-simulatie-tab-design.md) |
| **Doctrine** | ongewijzigd — geen LLM, geen runtime-diensten; alle tekst komt uit de kennisbank-artefacten |

---

## 1. Doel en niet-doelen

**Doel.** De graaf-knopen tonen in hun popup de inhoud in plaats van de techniek: artikel-popups krijgen de artikeltekst en de leesbare RegelRecht-executie (of de eerlijke onthouding), regeltekst-popups de echte lidtekst.

**Niet-doelen.** Geen tekstweergave ín de knopen (alleen tooltips); geen tekstanalyse; geen andere knopen gewijzigd (jr/act/loc/gio blijven semantisch); geen fulltekst-weergave (alleen excerpten met caps); geen wijziging aan de vier bestaande stappen.

## 2. Gegevensbronnen (gemeten 08-11)

| Bron | Inhoud | Koppeling |
|---|---|---|
| `documentstructuur.json` | per bladcomponent (LID) `kop` (lidnummer, STOP-XML) en `inhoud` (tekst, STOP-XML `<Al>`-paragrafen) | `identificatie` ↔ regeltekst-`wId` — **1407/1407** match (Eindhoven) |
| instrument-YAML (`full_export/out/<instrument>.yaml`) | per artikel `number`, `text` (p50 332 / p90 1150 / max ~999K tekens), en voor 567/1074 (Eindhoven) `machine_readable.execution` met `produces/parameters/input/output/actions` | `number` ↔ artikelnummer |
| `overlap.json` | `rrStatus` + reden per artikel | al in de kg-payload |

## 3. Componenten

### 3.1 `simulation/build_simulation.py` — tekstextractie + executie-render

- **Lidtekst-map** per instrument: `documentstructuur` → `{wId: {"lid": "<kop-Nummer>", "tekst": "<Al>-tekst samengevoegd, cap 350 tekens + '…'"}}` (regex-extractie uit `inhoud`-XML, `_esc` bij render).
- **Artikelgegevens** uit het YAML: `tekst` cap 500 tekens; `machine_readable` → **voorgemaakt tooltip-HTML** via een render-functie:
  - geformaliseerd: kopje "Omgezet naar RegelRecht (v0.8.11)" + karakter (produces), regels "input: naam — beschrijving" (cap 2 inputs + "…"), "output: naam — beschrijving" en de actions recursief uitgevouwen in leesbare vorm (`output ← waarde` / `output ← AND(a, b)` / `IF … dan …`, operaties en operands ge-`_esc`d; cap 4 action-regels);
  - niet-geformaliseerd: "niet geformaliseerd — status: <rrStatus>" (geen gefantaseerde omzetting).
- **Payload-uitbreiding** (kg-contract): `artikelen[nr]` krijgt `"tekst": str` en `"rr": str` (voorgemaakt HTML); nieuw topveld `"lids": {wId: {"lid": str, "tekst": str}}` (alléén wIds die in de payload-`rts` voorkomen, cap 350). Overzicht- en subgraph-artikel/regeltekst-tooltips worden build-time opgebouwd uit deze velden.

### 3.2 `simulation/template.html`

- Regeltekst-node popup (overzicht en subgraph): `lid X. — <tekst>` uit `lids[wId]` (valt terug op huidige wId-regel als ontbrekend).
- Artikel-node popup (overzicht en subgraph): status + `artikelen[nr].tekst`-excerpt + `artikelen[nr].rr`-HTML-blok.
- Subgraph-tooltips schakelen van template-`esc()`-strings naar de vooraf gerenderde HTML-blokken (kg1-patroon: `tipShow` krijgt HTML).

### 3.3 `simulation/verify_static.mjs`

- `kgE.artikelen["1.8"].tekst` bevat een gouden tekstfragment van art. 1.8 (uit het YAML, letterlijk gekozen in het plan) én `"rr"` bevat `toegestaan_art_1_8` en een inputnaam (`limiet_m` of `in_werkingsgebied`).
- Eén regeltekst-gouden: het eerste wId van art. 1.8 heeft `lids[wId].tekst` met ≥ 40 tekens dat geen substring van de wId is.
- Bestaande asserts ongewijzigd; hub-herbouw in de slot-taak.

### 3.4 `simulation/README.md`

Graaf-alinea uitbreiden: popups tonen echte tekst (excerpten met caps) en de RegelRecht-omzetting dan wel onthouding; bronnen (documentstructuur + instrument-YAML).

## 4. Begrenzing en fouten

- Caps: artikeltekst 500, lidtekst 350, inputs 2 (+teller), actions 4 (+teller); truncatie altijd met "…" gemarkeerd.
- Ontbrekend YAML-artikel of documentstructuur-onderdeel → popup valt terug op de huidige vorm (nooit breken; de build logt niets — het is data-afhankelijk).
- YAML is geen cache-artefact maar een `full_export`-output: `build_kg7` faalt hard (sys.exit) als het YAML ontbreekt — gelijk aan de andere artefacten.
- Payloadgroei geschat ≤ ~1,2 MB per hub; `--gent-only` blijft datavrij.

## 5. Bouwvolgorde (plan verfijnt)

1. build: lids/tekst/rr-render + payload-contract
2. template: tooltip-koppeling (overzicht + subgraph)
3. verify + README
4. eindcontrole + hub-herbouw
