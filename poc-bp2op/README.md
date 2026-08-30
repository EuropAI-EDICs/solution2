# poc-bp2op — "van bestemmingsplan naar omgevingsplan met AI" (gemeente Eindhoven)

PoC-2 of the LDT-toolbox. Where [PoC-1](../poc/README.md) (wind turbines, province
Utrecht) answered *"waar kan wat?"*, this proof-of-concept implements the **recorded
methods of the Amsterdams aanpak** — VNG netwerksessie *"Van bestemmingsplan naar
omgevingsplan met AI"* (19 juni 2026, Peter Lans, gemeente Amsterdam; tool **Plangids**)
— projected on **gemeente Eindhoven**: rule-for-rule matching of the old-law rules that
live on in the *tijdelijk deel* (bruidschat, hoofdstukken 22/23) of the Omgevingsplan
gemeente Eindhoven to the new doelregeling (hoofdstukken 1–21), with match scores, a
kennisbank of earlier conversions, a bulk gereedheidsanalyse, and an always-pending
jurist checkpoint.

Every pipeline feature cites the method card that motivated it: **MC-1 … MC-12** in
[`corpus/METHOD-CARDS.md`](corpus/METHOD-CARDS.md), each card with transcript
timestamps, distilled from the [archived video transcript](corpus/vng-netwerksessie-19jun2026-transcript.txt).

## Run it (offline, corpus-first)

```bash
python3 poc-bp2op/run.py                        # Eindhoven use case -> poc-bp2op/runs/<ts>-eindhoven
python3 poc-bp2op/run.py --use-case eindhoven --out /tmp/demo
python3 -m unittest discover -s poc-bp2op/tests # 32 offline tests incl. full e2e
```

Stdlib + `jsonschema`; no network at runtime, no LLM at runtime — the LLM-hook is
pluggable but deliberately off (MC-4: "validatie blijft altijd nodig"). Exit code 0
only when the Critic's pipeline-run verdict is `pass`; **V4 (jurist) stays pending by
design** (MC-6).

## Corpus (archived official publications)

| file | what | role |
|---|---|---|
| `omgevingsplan-eindhoven-cvdr696400-geldend-2026-06-29.html` | Omgevingsplan gemeente Eindhoven, CVDR696400/4 (geldend 29-06-2026), Lokale wet- en regelgeving | doelregeling (hfd 1–21) **and** bronpopulatie (hfd 22/23 tijdelijk deel/bruidschat) |
| `gmb-2025-226538.html` | Wijzigingsbesluit met integrale tekstvervanging (Gemeenteblad 2025, 226538) | kennisbank seed: 262 "komt in de plaats van"-relaties (B02) |
| `gmb-2023-561129-wijzigingsbesluit-conversie.html` | Conversiebesluit omgevingsplan (Gemeenteblad 2023, 561129) | kennisbank seed: 12 relations (B03), incl. voortzettingen |
| `gmb-2026-256846.html` | Omnibuswijzigingsbesluit met renvooi (Gemeenteblad 2026, 256846) | kennisbank seed (B04): its 9 relations duplicate B02's — dedupe keeps the earliest publication |
| `gmb-2025-275768.html` | Kennisgeving TAM-omgevingsplan (Gemeenteblad 2025, 275768, voormalig belastingkantoor/azc) | context: the TAM track that converts areas one by one |
| `planviewer-eindhoven-inventory.html` | Planviewer bestemmingsplannen-inventaris Eindhoven | MC-8 portefeuille-statistiek (370 plannen, 338 vastgesteld, 18 TAM) |

DSO API's are key-gated (HTTP 401, verified in PoC-1); the PoC reads the same
official source through its public publications instead — see the limitations in the
report.

## Pipeline

```
intake (use-case request)          MC-1/MC-2/MC-9   use-cases/eindhoven.json
  -> parsers.parse_doelregeling    MC-4  automatisch inlezen + opknippen: CVDR-consolidatie ->
                                    1074 artikelen -> 762 doelregels (hfd 1-21) + 311 bronregels
                                    (hfd 22/23), verbatim tekst + dieptelinks, niets verzonnen
  -> parsers.parse_kennisbank_pairs MC-5  'komt in de plaats van'/'voortzetting van' uit de
                                    wijzigingsbesluiten -> 274 relaties (dedupe op
                                    doelLocator+bronLabel, vroegste publicatie wint)
  -> knowledgebank.suggereer       MC-5/MC-6 TF-IDF-cosinus (unigrammen+bigrammen, Dutch-aware
                                    normalisatie) + kennisbank-boost (gepubliceerde relatie =
                                    score 1.0); banden 0.90/0.70 zoals de tool; SUGGEERT enkel
  -> analyser.coverage             MC-8  match-ratio + conversie-gereedheid per brondocument,
                                    'doelregeling eerst uitbreiden'-clusters, portefeuille
  -> critic.validate_pipeline      MC-6  V0 schema's · V1 volledigheid · V2 verbatim-grounding ·
                                    V3 onafhankelijke Jaccard re-executie · V4 jurist (pending)
  -> explainer + report            MC-3/MC-7 omzettabel.json/md, PROV-bundle, single-file HTML
```

## Method → implementation traceability

| kaart | methode (transcript) | implementatie |
|---|---|---|
| MC-1 | Transitiestrategie met doelregeling [02:31–07:33] | doelregeling-index = CVDR696400 hfd 1–21 (`doelregels.json`); `needsNewRules` clusters in `coverage.json` signaleren eerst-uitbreiden |
| MC-2 | Beleidsneutraal omzetten [15:44–16:31] | `conversion-request` pinned `beleid: neutraal`; geen rij verzint beleid; twijfel → `needs_human` |
| MC-3 | De omzettabel als kernartefact [20:13–30:06] | `omzettabel-row` contract; `omzettabel.json`/`.md`; 1-op-n suggesties (activiteiten stapelen) |
| MC-4 | Automatisch inlezen en opknippen [21:07–26:55] | `parsers.py`: deterministische HTML-tokenizer, artikel/lid-splitsing, verbatim quotes + dieptelinks; LLM-hook uit |
| MC-5 | Kennisbank met hergebruik en match-scores [33:13–34:58] | `kennisbank-pair` contract; seeds uit B02/B03/B04; TF-IDF + boost; banden ≥0.90/0.70–0.90/<0.70; status blijft `voorgesteld` |
| MC-6 | Mens blijft op de knoppen [26:07–35:45] | geen `gekoppeld`-status in het schema (test verifieert dit); V4 altijd pending; V3 onafhankelijke matcher |
| MC-7 | Controleerbaarheid [34:23–37:26] | elke regel: permalink + letterlijk citaat; `toelichting`-veld + `reviewTrail` per rij; rapport toont beide kanten |
| MC-8 | Bulk-analyse voor planning [54:43–55:43] | `coverage-report` contract: match-ratio, gereedheidsbanden, needs-new-rule clusters, Planviewer-portefeuille |
| MC-9 | Procesontwerp [09:04–17:26] | `pilotCriteria` in de request; Amsterdams cijfers (>1000 u/plan → ≈450 FTE; ≈20× versnelling) als business case in `run_summary.json` |
| MC-10 | Input-kwaliteit en stapeling [60:00–63:20] | document-lineage per bronregel; `stackingRef`-veld; vervallen/stapel-twijfel → `needs_human` met reden |
| MC-11 | Werkingsgebieden zijn (nog) geen AI [37:28–38:11] | bewust geen geometriemotor; `werkingsgebiedRef` placeholder voor de robotiseringsstap |
| MC-12 | Kwaliteitsborging van de tool [52:53–54:13] | deterministisch + offline; QA-self-assessment checklist in `run_summary.json` |

Every run artifact (rij, relatie, cluster, rapportsectie) draagt zijn eigen
`methodTrace`-veld; `prov.json` verbindt agents, entities (sha256), activities en
derivations aan de kaarten.

## Artifacts per run (`runs/<ts>-eindhoven/`)

`request.json` · `bronregels.json` · `doelregels.json` · `kennisbank.json` ·
`omzettabel.json` · `omzettabel.md` · `plan-inventory.json` · `coverage.json` ·
`validation.json` · `prov.json` · `report.html` (single-file, werkt vanaf schijf) ·
`run_summary.json`

## Validatie (V0–V4)

- **V0 syntactic** — elk artifact schema-valid tegen `schemas/*.schema.json` (7 contracten)
- **V1 completeness** — elke bronregel precies één omzettabel-rij; alle doelRegelId-
  verwijzingen en kennisbank-koppelingen losen op
- **V2 grounding** — elke bron-/doeltekst letterlijk (na whitespace-normalisatie)
  aanwezig in het gearchiveerde bronbestand; kennisbankcitaten verbatim in het besluit;
  permalinks dragen het juiste CVDR-id
- **V3 semantic** — een onafhankelijke matcher (Jaccard i.p.v. TF-IDF) herscoort elke
  tekst-gedreven suggestie; top-1 overeenkomst en score-delta's worden gemeten
  (canonieke run: 0.43 over 82 rijen; 220 kennisbank-gedreven rijen buiten vergelijking)
- **V4 human** — de juristtoets: altijd `pending`; 70 rijen aangewezen

## Kannonieke run (20260830-124515-eindhoven)

311 bronregels · 762 doelregels · 274 kennisbank-relaties · 311 rijen:
232 `voorgesteld` (waarvan 220 kennisbank-gedreven), 9 `nieuwe_regel_voorgesteld`,
70 `needs_human` · verdict **pass** (V4 pending). Beste match-ratio 75%
(`deels_gereed`); cluster 'gebruik:overig' (9 regels) vraagt doelregeling-uitbreiding
eerst (MC-1/MC-8).

## Tests

```bash
python3 -m unittest discover -s poc-bp2op/tests   # 32 tests, ~2 min (e2e dominant)
```

`test_parsers.py` — opknippen (artikelen, leden, paden, [Vervallen]-status),
kennisbank-extractie, matcher (TF-IDF rangschikking, kennisbank-boost domineert,
stopwoorden, Jaccard), coverage-banden, omzettabel-contract (o.a. MC-6: de status
`gekoppeld_door_ai` bestaat niet en moet V0-falen).
`test_pipeline.py` — critic-gates V0/V1/V2/V3/V4 (missende/dubbele/spook-rijen,
onoplosbare verwijzingen, niet-verbatim teksten, verkeerde permalinks, schema-
overtreding, kennisbank-gedreven rijen buiten V3-vergelijking), explainer
(omzettabel.md-inhoud, write_outputs, PROV-bundle), report (twaalf kaarten, beide
zijden zichtbaar, geen externe imports — file:// werkt), en een volledige
**end-to-end run over het gearchiveerde Eindhoven-corpus** die alle twaalf artifacts,
de contracten en de V1-invarianten onafhankelijk hercontroleert.

## Relation to PoC-1

Deze PoC hergebruikt PoC-1's bewezen architectuur (contracts → deterministic agents →
critic met validatieniveaus → explainer/PROV → single-file rapport; zie
[`../poc/`](../poc) en [`../docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md))
en herhaalt die voor het regel-conversie-domein: nieuw contractencatalogus
(omzettabel i.p.v. norm-cards), nieuwe parsers (CVDR/GMB i.p.v. geodata), nieuwe
matching-opgave (regel→regel i.p.v. zone→zone).
