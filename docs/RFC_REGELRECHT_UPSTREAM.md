# RFC-concepten voor RegelRecht upstream (NDD) — locale regelgeving & geo

| | |
|---|---|
| **Status** | Concept — nog **niet** ingediend bij [NederlandseDigitaleDienst/regelrecht](https://github.com/NederlandseDigitaleDienst/regelrecht); indienloopt via issues/PR's onder MC-6 (voorstel, mens op de knop) |
| **Datum** | 8 november 2026 |
| **Aanleiding** | Fase 4 van [MAPPING_DSO_NAAR_REGELRECHT.md](MAPPING_DSO_NAAR_REGELRECHT.md); issues uit [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md); bewijs uit de Utrecht- en Eindhoven-PoC's |
| **Corpus-stand** | 8-11-2026 live gecheckt: `regulation/nl/` kent alleen `wet`, `amvb`, `beleidsregel`, `waterschaps_verordening` — nul lokale OV/OP-bestanden (gap G5 in [GAP_REGISTER_NOVEX_NOTA_RUIMTE.md](GAP_REGISTER_NOVEX_NOTA_RUIMTE.md)) |

---

## RFC 1 — `cvdr_id` herinvoeren in de metadata

**Probleem.** Zonder CVDR-identificatie is lokale regelgeving alleen via de
`url` herleidbaar. Het veld bestond in schema v0.5.2 (het
HHNK-precedent `regulation/nl/waterschaps_verordening/kwijtscheldingsregeling_waterschapsbelastingen_hhnk_2023/2023-01-01.yaml`
draagt `cvdr_id: CVDR686061_1`), verdween in v0.7.1 en is ook in v0.8.11 niet
terug. Door `additionalProperties` valideert het veld wél, maar het law-model
leest het niet — stille metadata-dood.

**Voorstel.** Herinvoeren als optioneel metadataveld naast de landelijke
identificatie, patroon `^CVDR\d{6}(_\d+)?$` (het HHNK-precedent laat zien dat
de versie-suffix `_1` voorkomt).

**Bewijs uit de PoC's.** Beide corpus-kandidaten
([corpus_export](../nldt/simulation/regelrecht/corpus_export/)) dragen het veld
al; de export-valideert groen tegen v0.8.11 en blijft na herinvoer ongewijzigd.

## RFC 2 — `legal_basis`/`references` openen voor lokale regelgeving

**Probleem.** `references` vereist een `bwb_id` (patroon `^BWBR\d{7}$`).
Verwijzingen van/naar lokale regelgeving (CVDR, loket lokale regelgeving) passen
daar niet in. Concreet houdt dat tegen: de Eindhovense
"komt in de plaats van"-relaties *binnen* het eigen omgevingsplan (CVDR→CVDR),
en de omzettabel (311 rijen) en kennisbank (274 relaties) als enrichment naast
het corpus.

**Voorstel.** Eén van twee routes, met voorkeur voor (a):

- (a) **source-object**: `{ "type": "bwb" | "cvdr", "id": "BWBR0037885" | "CVDR696400", "artikel": "…" }`
  — uitbreidbaar naar andere bronnen zonder patroon-wijzigingen;
- (b) `bwb_id` laten bestaan en een zuster-veld `cvdr_id` op de referentie
  toevoegen (kleiner, minder uitdrukbaar).

**Bewijs uit de PoC's.** Het Eindhoven-voorbeeld
([examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml](examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml))
verwijst nu alleen naar de Omgevingswet (BWBR0037885) omdat de interne
conversierelatie er niet in past.

## RFC 3 — geo-feittype / GIO-referentie als first-class input

**Probleem.** Gebiedsgebonden regels ("binnen het werkingsgebied van art. X")
moeten nu als gewone booleaanse input zonder `source.regulation` — een feit dat
"buiten de wet-YAML" wordt opgelost. Dat werkt (schema staat het expliciet toe),
maar de GIO-identificatie heeft geen eersteklas plek, zodat de wet zelf niet
zegt wélk gebied wordt bedoeld.

**Voorstel.** Een geo-input-variant op `execution.input[]`, bijvoorbeeld:

```yaml
- name: in_werkingsgebied_art_5_3
  type: boolean
  source:
    geo: nl.imow-pv26.gebied.…. : het IMOW-locatie/GIO-identificatiepatroon
```

De STTR-standaard heeft exact deze vorm al als `uitv:geoVerwijzing/uitv:locatie
@identificatie` — dit RFC stemt RegelRecht ermee op één lijn (crosswalk in
[POC_STTR_IMTR_KANSEN.md](POC_STTR_IMTR_KANSEN.md)).

**Bewijs uit de PoC's.** 63 geo-inputs in de 567-artikelen-export Eindhoven;
GIO-kruisvalidatie 34/34 (Eindhoven) en 8/8 (Utrecht); de Utrechtse
zonevraag (art. 5.3 kleine windturbine) draait vandaag al op dit patroon via de
externe zone-engine ([POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md)).

## RFC 4 — harvester-bron voor lokale regelgeving naast BWB

**Probleem.** De harvester oogst alleen het BWB. Gemeentelijke en provinciale
instrumenten (omgevingsplan, omgevingsverordening, gemeentelijke verordening)
komen daardoor structureel niet het corpus in — het schema ondersteunt de lagen
(`GEMEENTELIJKE_VERORDENING`/`PROVINCIALE_VERORDENING` met
`gemeente_code`/`provincie_code`) al wél.

**Voorstel.** Tweede harvester-bron: de
[API lokale regelgeving](https://lokaleregelgeving.overheid.nl) (CVDR's,
officiële bekendmakingen decentrale overheden), met dezelfde
versie-per-bestand-conventie (`valid_from`-datum als bestandsnaam). Scope per
laag configureerbaar; nieuwe lagen `gemeentelijke_verordening` en
`provinciale_verordening` ontstaan vanzelf bij eerste oogst.

**Bewijs uit de PoC's.** De corpus-staging levert de eerste twee kandidaten;
zonder harvester blijft iedere lokale bijdrage handwerk. NB: het corpus kent
per regeling een `status.yaml` met `status: harvested` — de PoC-exporten
gebruiken naar eerlijkheid `status: poc_export`.

---

## Indien-volgorde (voorstel)

1. RFC 1 (klein, precedent bestaat) → openent de deur voor de staging-PR.
2. RFC 4 (harvester) → maakt lokaal structureel i.p.v. handmatig.
3. RFC 2 (referenties) → opent conversie-/kennisbank-enrichment.
4. RFC 3 (geo) → sluit de laatste naad met de DSO/STTR-kant; heeft de meeste
   ontwerp-afwegingen (nodig voor `zoneSelector` in de wet-YAML zelf).

Elke RFC kan onafhankelijk; geen van de PoC-fasen 1–3 blokkeert op een ervan.
