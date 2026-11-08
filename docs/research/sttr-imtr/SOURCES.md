# Bronnen STTR/IMTR 3.0.1 — vastgepinde downloads + live metingen

Alle specificaties zijn op **8 november 2026** gedownload van de officiële bronnen
(IPLO = publicatiekanaal; standaard beheerd door RWS/Reneso, zie de [IPLO STTR/IMTR-pagina](https://iplo.nl/digitaal-stelsel/aansluiten/standaarden/sttr-imtr))
en vastgepinnd op sha256. Doel: de kansen-notitie [POC_STTR_IMTR_KANSEN.md](../../POC_STTR_IMTR_KANSEN.md)
moet offline herleidbaar blijven, ook als IPLO pagina's hernummert.

## Vastgepinde specificaties (deze map)

| bestand | bron-URL | sha256 |
|---|---|---|
| `sttr-3.0.1-specificatie.pdf` | <https://iplo.nl/publish/pages/162385/20250801-dso-specificatie-sttr-3-0-1_1.pdf> | `dc2b0b285f8071730e1a06b4dead99322579a990a76bbd736ac80fdf792941ce` |
| `imtr-3.0.1-specificatie.pdf` | <https://iplo.nl/publish/pages/162385/20251204-dso-specificatie-imtr-3-0-1-def.pdf> | `f44c0585d31494a8aede23ce0378ad1c1fa2da564ac3d6a2a59dbbdbc1f94a43` |
| `voorbeeldbestanden-sttr-3.0.0.zip` → `dmn-voorbeelden-sttr-3.0.0/` | <https://iplo.nl/publish/pages/162385/voorbeeldbestanden-sttr-3-0-0.zip> | `93f397a2a060fb86acc76f08c56110c69cea2b896b742fae68f6095a9c25be6b` |
| `xsd-sttr-3.0.zip` → `xsd-sttr-3.0/` (incl. `DMN_v11.xsd` én `DMN_v12.xsd`) | <https://iplo.nl/publish/pages/162385/xsd-3-0-2025-05-01.zip> | `67e683ae5c750681327782758f265728160918d865163c9bad5d2669339c241e` |
| `oas-toepasbareregels-uitvoerengegevens-v2.json` (OAS 2.1.0) | <https://developer.omgevingswet.overheid.nl/publish/pages/183874/toepasbareregels-uitvoerengegevens-v2.json> | `baa8b0c1dbf18f40b2427a1ea53b2a6f57bfc3ebc52a9ed0667d706897e7f1a2` |
| `oas-toepasbareregels-samengesteldertrservices-v2.json` | <https://developer.omgevingswet.overheid.nl/publish/pages/165401/toepasbareregels-samengesteldertrservices-v2.json> | `5631a6f60a3e7f4661964a1f02f5dac43c4a04e31a92592e7b0e9eee1d80ef33` |
| `oas-toepasbareregels-zoekinterface-v2.json` | <https://developer.omgevingswet.overheid.nl/publish/pages/235013/toepasbareregels-zoekinterface-v2.json> | `edba56fa1fcf1957367f6a60b73f6bb47a84699bc06c219571586824f9b8f107` |

De zes officiële voorbeeld-DMN's (STTR 3.0.0, DMN 1.2): `ConclusieBouwenDakkapel.dmn`,
`IndieningsvereistenVergunningBoomsoortKappen.dmn`, `IndieningsvereistenVergunningEvenementOrganiseren.dmn`,
`IndieningsvereistenMeldingGebruikBouwwerkenRijk.dmn`, `MaatregelenGlastuinbouwbedrijf.dmn`,
`MaatregelenVerwerkenVanThermoplastischKunststof.dmn`.

## Live RTR-meting (PRE, 8 november 2026)

Uitgevoerd met de bestaande `DSO_API_KEY` uit de gitignored `.env` (header `x-api-key`;
productie-endpoint weert de PRE-key met 401 — zelfde beheersmaatregel als bij de
Presenteren-metingen in [POC_TPOD_IMOW_KANSEN.md](../../POC_TPOD_IMOW_KANSEN.md)).

- Base PRE: `https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/toepasbareregelsuitvoerengegevens/v2`
- Registratie-omvang: **66.474** actuele `toepasbareRegels`-entries (133 pagina's à 500);
  op de eerste zes pagina's al 98 distincte OIN's (gemeenten, waterschappen, rijk).
- **Gemeente Eindhoven: OIN `00000001001172773000`** — gevonden door te pagingen en op
  `nl.imow-gm0855…` in `functioneleStructuurRef` te filteren (de metadata bevat geen
  gemeentenamen, alleen OIN's). Direct filterbaar via `?oin=…`.
- Eindhoven heeft **20 geldige STTR-bestanden** (170 entries incl. historie met `einddatum`),
  begindata 29-06-2022 t/m 03-10-2023, activiteiten o.a. `BouwwerkSlopen`,
  `MakenHandelsreclame`, `OngewoonVoorvalMBAOP`, `GeluidProdWindturbine`.
- Alle 20 zijn als DMN-xml gedownload naar `rtr-pre-eindhoven/` (met
  `toepasbare-regels.metadata.json` als metadata-cache). Aanleveringen zijn **DMN 1.1 met
  STTR v1.0-namespaces** (exporter "Geodan FLO Legal STTR Builder") — dus níet de huidige
  3.0.1/DMN 1.2-vorm; zie de eerlijke grenzen in de notitie.

## Reproduceren

```bash
# 567-testcase (offline, leest de full export + report):
nldt/.venv/bin/python docs/research/sttr-imtr/scan_executies.py   # → eindhoven-567-dmn-scan.json

# Eindhoven in de RTR (PRE; sleutel nooit committen):
KEY=$(grep -E '^DSO_API_KEY=' .env | cut -d= -f2-)
curl -sS -H "x-api-key: $KEY" \
  'https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/toepasbareregelsuitvoerengegevens/v2/toepasbareRegels?oin=00000001001172773000'
```

## Verdere officiële bronnen (niet gedownload)

- IPLO STTR/IMTR-hub (alle versies 1.5.1/2.0.1/3.0.1, verificatiematrix's, introductiepresentaties): <https://iplo.nl/digitaal-stelsel/aansluiten/standaarden/sttr-imtr>
- IPLO RTR-introductie: <https://iplo.nl/digitaal-stelsel/introductie/landelijke-voorziening/registratie-toepasbare-regels>
- DSO API-register — [Uitvoeren gegevens toepasbare regels](https://developer.omgevingswet.overheid.nl/api-register/api/raadplegen-uitvoeren-gegevens-toepasbare-regels), [Samengestelde RTR-services](https://developer.omgevingswet.overheid.nl/api-register/api/samengestelde-registratie-toepasbare-regels), [Toepasbare regels zoeken](https://developer.omgevingswet.overheid.nl/api-register/api/toepasbare-regels-zoeken), [Aanleveren (SOAP/ebMS, PKIoverheid)](https://developer.omgevingswet.overheid.nl/api-register/api/toepasbare-regels-aanleveren)
- Voorbeeldbestanden in GitHub-spiegels: [RicharddeGraaf1/imtr_voorbeeldbestanden](https://github.com/RicharddeGraaf1/imtr_voorbeeldbestanden) (DMN 1.1 én 1.2), [Amsterdam/vergunningcheck](https://github.com/Amsterdam/vergunningcheck) (mock-DMN's), [hdsr-mid/Omgevingswet_archivering_STTR](https://github.com/hdsr-mid/Omgevingswet_archivering_STTR) (RTR-archivering in Python), [MinBZK/regels.overheid.nl](https://github.com/MinBZK/regels.overheid.nl) (RegelRecht-initiatief)
