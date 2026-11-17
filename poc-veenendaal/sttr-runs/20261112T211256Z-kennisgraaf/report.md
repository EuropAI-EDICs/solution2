# Kennisgraaf/v1 — DSO-beeld over de Spoorzone — 20261112T211256Z-kennisgraaf

*Run 2026-11-12T21:12:56Z · engine `poc-veenendaal/kennisgraaf.py` · afgeleide projectie met contract `kennisgraaf/v1` — herbouwbare graaf over sha256-vaste bronruns.*

**380 knopen** (96× activiteit, 1× gebied, 83× gio, 7× programma-feit, 1× regeling, 185× rtr, 7× zone) · **408 relaties** (7× bestaat_uit, 83× bevat_geo_laag, 118× overlapt, 7× raakt, 7× uit_programma, 1× valt_onder, 185× vraagt_over).

## Contract-controles

- ✓ **unieke node-ids** 380 nodes, 0 duplicaten
- ✓ **edges resolveerbaar** 408 edges
- ✓ **zone-aantal ≡ gebied.json** 7 zones
- ✓ **gio-aantal ≡ pakket-sweep** 83 gio's (27 snijden de werkgrens)
- ✓ **rtr-aantal ≡ geldige bestanden** 185 rtr's
- ✓ **zone→gio ≡ zones-run** 118 overlapt-edges
- ✓ **Σ zone-opp ≈ werkgrens** 161.5 vs 161.6 ha
- ✓ **elke node heeft bron** 

## Koppelgaten (eerlijk)

- **rtr→gio via geoVerwijzing**: 20 geoVerwijzing-vragen, statusverdeling {'afwezig-in-pakket': 18, 'aanwezig-als-ow-object': 2} — geen enkele legt hard aan een GIO-bestand in dit pakket → geen rtr→gio-edges in deze graaf; zone→gio is de enige meetbare gebiedsbinding

## Leeswijzer

- `zone→gio (overlapt)` is de enige meetbare gebiedsbinding, met overlap-ha en
  dekking% uit de zones-run; `regeling→gio` volgt het uitwisselpakket (83 lagen,
  waarvan de snijdende gemarkeerd).
- `rtr→activiteit` volgt de RTR-metadata (geldigheid als attribuut);
  `programma→activiteit` draagt altijd bewijs uit het Toekomstbeeld/de nulmeting.
- Graaf is volledig afgeleid: `kennisgraaf.json` herbouwt uit de bronruns in
  `manifest.json` (zelfde paden, zelfde sha256's).

*Bronruns: loket `20261112T210133Z-loketvragen` · zones `20261112T210519Z-zones` · RTR-index `veenendaal.sttr.json`.*