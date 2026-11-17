# Corpus-staging — eerste lokale instrumenten voor regelrecht-corpus

Deze map plant de twee PoC-instrumenten in de padconventie van
[NederlandseDigitaleDienst/regelrecht-corpus](https://github.com/NederlandseDigitaleDienst/regelrecht-corpus)
(`regulation/nl/<laag>/<slug>/<valid_from>.yaml` + `status.yaml`, vorm
geverifieerd tegen het HHNK-precedent CVDR686061_1). Beide bestanden zijn
byte-identieke kopieën van de tegen schema v0.8.11 gevalideerde
full-export (pin: `nldt/simulation/regelrecht/schema/pin.json`).

## Stand van het landelijke corpus (8-11-2026, live gecheckt)

`regulation/nl/` bevat alleen `wet`, `amvb`, `beleidsregel` en
`waterschaps_verordening` — géén enkele gemeentelijke of provinciale
verordening en geen enkel omgevingsplan. Deze staging levert de eerste
kandidaten voor `gemeentelijke_verordening` en `provinciale_verordening`.

## Bewuste keuzes (vóór indienen te beslissen)

- **Omgevingsplan onder `gemeentelijke_verordening`**: schema v0.8.11 kent
  géén `OMGEVINGSPLAN`-laag; dit is de dichtstbijzijnde laag mét
  `gemeente_code`. Moet samen met de laag-uitbreiding in RFC 1/2
  (docs/POC_REGELRECHT_INTEGRATION.md, upstream-issues) worden neergelegd.
- **`cvdr_id`**: schrijft het veld gewoon mee ( valideert, maar het
  upstream law-model leest het sinds v0.7.1 niet meer ) — zelfde issue.
- **`status: poc_export`** in `status.yaml`: eerlijk over de herkomst
  (PoC-export, geen harvest uit BWB); upstream PR's gebruiken `harvested`.

## Indienen (MC-6: voorstel, nooit autonoom)

1. Fork het corpus, branch `poc/lokale-ov-op`.
2. Kopieer `regulation/` uit deze map naar de fork.
3. Open een PR met verwijzing naar
   [POC_REGELRECHT_INTEGRATION.md](../../../docs/POC_REGELRECHT_INTEGRATION.md)
   en [MAPPING_DSO_NAAR_REGELRECHT.md](../../../docs/MAPPING_DSO_NAAR_REGELRECHT.md);
   de PR-review is de mens-op-de-knop.

Herbouwen: `nldt/.venv/bin/python -m nldt.simulation.regelrecht.corpus_export`.
