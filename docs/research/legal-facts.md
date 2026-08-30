# Legal facts — wind-turbine opportunity mapping in Provincie Utrecht (NL)

**Role:** Norm Analyst scout (legal-domain reconnaissance) for the wind PoC of the LDT Toolbox multi-agent plan (§3.2 agent #3).
**Retrieval date:** 2026-08-30 (all URLs in this document were fetched that day; see §9 and `poc/corpus/sources.json`).
**Method:** cite-or-abstain. Every article number below was read in a fetched source (consolidated CVDR text, official publication HTML, or PDF extracted with `pdftotext`). Dutch legal text is quoted verbatim in Dutch and explained in English. Where a claim could not be verified in a fetched source it is explicitly marked **unverified** or **abstained**.

---

## 1. Executive summary

1. The **current binding instrument** for wind-turbine siting rules in province Utrecht is the **Omgevingsverordening provincie Utrecht**, citeertitel "Omgevingsverordening provincie Utrecht", consolidated on the CVDR as **CVDR704250**, *geldend van 13-10-2025 t/m heden*. It was originally vastgesteld by Provinciale Staten on **30 March 2022** (Ontwerp 30-03-2022; bekendmaking Provinciaal blad 2023, 13766) and entered into force **1 January 2024** together with the Omgevingswet. Subsequent amendments (all under the 2024 delegation decision): 01-03-2024, 14-06-2024, 01-09-2024, 01-09-2025, plus a rectificatie effective 13-10-2025 (working back to 01-09-2025).
2. The **current Omgevingsvisie** is the *Omgevingsvisie provincie Utrecht*, vastgesteld by Provinciale Staten **10 March 2021** (referentienummer 82224DED, "Status: Definitief"), in werking **1 April 2021**. The province explicitly states: *"De huidige omgevingsvisie, die in werking is getreden in 2021, is op dit moment geldig."* It is **non-binding policy** (ambitions), but is the source of the well-known "zoekgebieden"-style energy maps.
3. A **major amendment of both instruments is in progress but NOT yet law**: ontwerp wijziging Omgevingsverordening and ontwerp omgevingsvisie were adopted in draft by Gedeputeerde Staten on **16 December 2025** (Provinciaal blad 2026, 12), ter inzage 6 Jan–16 Feb 2026 (≈1000 zienswijzen), PS besluitvorming expected **18 November 2026**, inwerkingtreding **1 January 2027**. The PoC must therefore pin to the 13-10-2025 verordening and the 2021 visie, and model the 2027 instruments as a future version.
4. **Where the wind norms live:** Hoofdstuk 5 (Energie), Afdeling 5.1 *Wind, zon en biomassa* — art. 5.1 (scope), 5.2 (exception to the rural verstedelijkingsverbod), **5.3 (kleine windturbine ≤20 m / ≤30 m ashoogte)**, **5.4 (windenergielocatie ≥3 MW in Gebied windenergie)**; plus **art. 9.28 (windturbines in stiltegebied)**, and the constraint layers of chapters 3 (grondwater), 6 (natuur: NNN, Groene contour, weidevogels), 7 (UNESCO Hollandse Waterlinies, landschapskernkwaliteiten) and 9 (landelijk gebied verstedelijkingsverbod, stiltegebied geluid). There are **no provincial tip-height/distance-to-dwelling dB limits for wind turbines** — those live in national law (see §6, abstentions).
5. **How text binds to maps:** every gebied (werkingsgebied) used in an article is a **GIO (Geografisch Informatie Object)** with a versioned JOIN-id listed in **Bijlage II "Overzicht Informatieobjecten"** of the verordening, e.g. `gebied windenergie → /join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025‑10‑10;846`. There are **no paper kaartbladen**; the binding is digital via the DSO ("klik op de kaart"). The geometry itself is downloadable only through the DSO **Omgevingsdocumenten Downloaden API**, which **requires an API key** (verified 401) — the PoC must therefore either apply for a key or fall back to the province's open ArcGIS layers / PDOK, accepting a provenance indirection (see §7).

---

## 2. Verification log (what was actually fetched, and dead ends)

Fetched and verified on 2026-08-30 (snapshots saved under `docs/research/sources/`):

| # | Source | Result |
|---|---|---|
| 1 | provincie-utrecht.nl hub + 6 subpages (omgevingsverordening, omgevingsvisie, wijziging…, handreikingen-bij-regels, projectbesluit, monitor, ingetrokken) | HTTP 200, text extracted |
| 2 | lokaleregelgeving.overheid.nl/cvdr704250 (+ `?&show-wti=true`) | HTTP 200; full consolidated regeling + wetstechnische info (3.8 MB HTML snapshot) |
| 3 | zoek.officielebekendmakingen.nl: prb-2023-13766, prb-2024-10798, prb-2025-13284, prb-2025-16760, prb-2026-12 | all HTTP 200 |
| 4 | Omgevingsvisie PDF (91.7 MB) via /media/8648 and Handreiking PDF (2025) | downloaded, `pdftotext` extracted |
| 5 | nationaalgeoregister.nl metadata 3a2f022d-… (Omgevingsverordening Provincie Utrecht) | HTTP 200 |
| 6 | geo-point.provincie-utrecht.nl Hub search API (`/api/v3/search?q=…`) | HTTP 200; found province layers |
| 7 | services.arcgis.com/m4kxECHTi6Dj9hfa/.../ET_wind_gebieden_windenergie/FeatureServer/13?f=json | HTTP 200; layer metadata (EPSG:28992) |

**Dead ends (recorded honestly):**

- **wetten.overheid.nl** — `https://wetten.overheid.nl/cgi-bin/deeplink/law1/title=Omgevingsverordening%20provincie%20Utrecht` → **HTTP 404**. Decentrale regelingen are no longer consolidated on wetten.overheid.nl; the consolidated channel is lokaleregelgeving.overheid.nl (CVDR). No BWBR identifier for this verordening exists to cite.
- **DSO Omgevingsdocumenten Downloaden API v1** (`https://service.omgevingswet.overheid.nl/publiek/omgevingsdocumenten/api/downloaden/v1/…`) — endpoint and spec verified via developer.omgevingswet.overheid.nl, but every call returns **HTTP 401 "Inloggegevens ontbreken"**: an API key is mandatory ("Om API's te gebruiken dient bij elke request een API-key meegegeven te worden"). No key is available in this environment → the officially machine-readable GIO geometry is **not accessible for the PoC without registration**. Spec URL: https://developer.omgevingswet.overheid.nl/api-register/api/omgevingsdocument-downloaden/
- **Regels op de kaart** (omgevingswet.overheid.nl/regels-op-de-kaart/documenten/…) — the province's own links resolve, but the application is an Angular SPA that renders server-side only an empty shell (verified: 1.9 kB shell HTML); document content is loaded from key-gated/API-driven endpoints. Human-readable reference channel only.
- **omgevingsbeleid.provincie-utrecht.nl** (province plannenviewer, cited by the NGR metadata) — also an SPA shell; layer configuration is loaded dynamically. Left to the geo recon agent.

---

## 3. Instrument inventory (exact titles, versions, dates)

### 3.1 Omgevingsverordening provincie Utrecht (binding)

- **Officiële naam / citeertitel:** "Omgevingsverordening provincie Utrecht" (art. 10.22 Citeertitel in the oorspronkelijke besluit: *"Deze verordening wordt aangehaald als: Omgevingsverordening provincie Utrecht."*)
- **Wetstechnische aard:** Verordening; "Regeling onder de Omgevingswet: Ja"; grondslag **artikel 2.6 Omgevingswet** (besluit-aanhef also cites art. 4.1 and 4.5 Ow en art. 143, 145, 146, 150 Provinciewet); vastgesteld door **Provinciale Staten** (oorspronkelijk), latere wijzigingen onder delegatie door **Gedeputeerde Staten**.
- **Consolidatie:** CVDR704250, **geldend van 13-10-2025 t/m heden** (verified 2026-08-30). Permalink current version: https://lokaleregelgeving.overheid.nl/CVDR704250 (viewed version: …/CVDR704250/8).
- **Version history** (from the CVDR "Overzicht van in de tekst verwerkte wijzigingen"):

| In werking | Betreft | Ondertekend | Bekendmaking |
|---|---|---|---|
| 01-01-2024 | nieuwe regeling (vastgesteld 30-03-2022) | — | Provinciaal blad 2023, 13766 (bekendgemaakt 23-11-2023) |
| 01-03-2024 | wijziging | 07-02-2024 | Provinciaal blad 2024, 2766 |
| 14-06-2024 | wijziging | 11-06-2024 | Provinciaal blad 2024, 8813 |
| 01-09-2024 | wijziging | 07-02-2024 | Provinciaal blad 2024, 11627 |
| 01-09-2025 | wijziging (technisch, via delegatie) | 08-07-2025 | Provinciaal blad 2025, 13284 |
| 13-10-2025 | wijziging/rectificatie, terugwerkend tot 01-09-2025 | 08-07-2025 | Provinciaal blad 2025, 16760 |

- **Delegation basis:** *Delegatiebesluit Omgevingsverordening provincie Utrecht 2024* (delegatie- of mandaatbesluit, published 18-07-2024) — Provinciaal blad 2024, 10798: https://zoek.officielebekendmakingen.nl/prb-2024-10798.html. Its art. 2.1 delegates power to adjust "gebieden en tekst".
- **Province page statement (fetched):** "Op 1 september 2025 is de wijziging van de Omgevingsverordening op grond van het Delegatiebesluit Omgevingsverordening provincie Utrecht 2024 in werking getreden. … Het gaat alleen om technische aanpassingen in teksten en werkingsgebieden van de Omgevingsverordening."
- **Pending (NOT current law):** *Ontwerp wijziging Omgevingsverordening provincie Utrecht* — GS 16-12-2025, Provinciaal blad 2026, 12 (https://zoek.officielebekendmakingen.nl/prb-2026-12.html), ter inzage 06-01-2026…16-02-2026; PS vaststelling expected 18-11-2026; inwerkingtreding 01-01-2027.

### 3.2 Omgevingsvisie provincie Utrecht (non-binding)

- **Title:** *Omgevingsvisie provincie Utrecht 10 maart 2021* (PDF colofon: "Vastgesteld bij besluit Provinciale Staten, 10 maart 2021", "Status: Definitief", "Referentienummer: 82224DED").
- **In werking:** 1 April 2021 (province page: "De Omgevingsvisie is op 1 april 2021 in werking getreden."; the verordening-toelichting refers to the predecessor "Interim Omgevingsverordening … (vastgesteld door PS op 10 maart 2021 en op 1 april 2021 in werking getreden)" — same PS date, different instruments).
- **DSO registration:** the province links the visie in the Omgevingsloket as AKN `akn-nl-act-pv26-2023-omgevingsvisie-1` (URL pattern verified; content behind SPA — see §2 dead ends).
- **Pending:** *Ontwerp-omgevingsvisie 16 december 2025* (PDF, 36.5 MB, listed on the wijziging page) — draft only, same 18-11-2026/01-01-2027 timeline.
- **Legal status:** an omgevingsvisie is a visiedocument (art. 3.1 Ow strategy instrument) — ambitions, not rules. All visie-derived facts in the evidence files are flagged `binding: false`-style notes.

### 3.3 Secondary/administrative sources

- **Handreiking Omgevingsverordening september 2025 (definitief)** — province guidance PDF (24 pp.) explaining each chapter and the "Regels op de kaart" workflow; useful for the Explainer, not a legal source.
- **NGR/PDOK metadata** "Omgevingsverordening Provincie Utrecht" (unique resource identifier 8c1baa7a-cc25-4a69-8f41-553f3e0d8bb8; publication 2025-07-08, revision 2025-10-13; EPSG:28992; denominator 1000; contact GIS@provincie-utrecht.nl; CC PDM "Open data (publiek)") — the geodata twin of the verordening's werkingsgebieden; points to the province plannenviewer https://omgevingsbeleid.provincie-utrecht.nl.

---

## 4. Where the authoritative consolidated text lives (channel ranking for the PoC)

1. **CVDR (lokaleregelgeving.overheid.nl) — recommended for the PoC.** Consolidated, versioned, citation-grade HTML of the geldende regeling; scrapeable without a key; includes Bijlage II GIO inventory and the full toelichting. URL: https://lokaleregelgeving.overheid.nl/cvdr704250 (current) / https://lokaleregelgeving.overheid.nl/CVDR704250/8 (viewed version).
2. **Officiële bekendmakingen (zoek.officielebekendmakingen.nl)** — the immutable per-amendment besluiten (prb numbers above); needed for version pinning and for the ontwerp 2026.
3. **Regels op de kaart / Omgevingsloket (omgevingswet.overheid.nl)** — the legally operative digital publication ("klik op de kaart"); human/SPA only, machine API key-gated.
4. **DSO Omgevingsdocumenten Downloaden API** — the only channel that serves the regelingversie + GIO's + OW-objecten as a zip (and GPKG geometries); **requires API key** (401 verified). Register via developer.omgevingswet.overheid.nl. Note: per the API page, the GPKG endpoints are deprecated per 01-05-2026 in favour of the "Omgevingsdocumenten geometrie opvragen" API.
5. ~~wetten.overheid.nl~~ — not applicable to decentrale verordeningen (404 verified; no BWBR id to cite).
6. **PDOK/NGR IMRO metadata** — dataset-level metadata only; geometry served through the province's own services (geo recon's domain).

---

## 5. Wind norms — full analysis (all quotes verbatim from CVDR704250 geldend 13-10-2025 unless noted)

> Dutch text is quoted exactly as published (including the DSO's italic gebied-names rendered here plainly). English glosses are mine.

### 5.1 Scope and the rural-development gateway

**Artikel 5.1 Toepassingsbereik nieuwe functies voor energie** — *"Deze afdeling is van toepassing op nieuwe functies voor energie uit wind, zon en biomassa."* → the PoC's wind/solar/biomass rules all hang off Afdeling 5.1.

**Artikel 5.2 Afwijking van instructieregel verstedelijkingsverbod landelijk gebied** — *"In afwijking van Artikel 9.3 kan een omgevingsplan verstedelijking in het Landelijk gebied toestaan om nieuwe functies voor energie en transformatorstations mogelijk te maken."* → energy functions are "verstedelijking" (Bijlage I begripsbepaling) but art. 5.2 is the gateway through the rural prohibition (art. 9.3).

**Artikel 9.2 Aanwijzing landelijk gebied en stedelijk gebied** — *"De provincie bestaat uit: a. het Landelijk gebied; en b. het Stedelijk gebied."* (both are GIO's). **Artikel 9.3** — *"Een omgevingsplan dat betrekking heeft op locaties binnen het Landelijk gebied laat geen verstedelijking toe, tenzij in deze verordening anders is bepaald."*

### 5.2 Kleine windturbine (own-use) — art. 5.3

- **Lid 1 (20 m inclusion zone):** *"Een omgevingsplan dat betrekking heeft op locaties binnen het Gebied kleine windturbine kan regels bevatten die de realisatie van een windturbine tot een ashoogte van 20 meter toestaat onder de voorwaarde dat de windturbine wordt geplaatst op of in aansluiting op bestaand bouwperceel."*
- **Lid 2 (30 m exception):** *"In afwijking van het eerste lid kan een omgevingsplan regels bevatten die de realisatie van een windturbine tot een ashoogte van 30 meter toestaan als dat noodzakelijk is om volledig of bijna volledig in eigen energiebehoefte van de bestaande bouwwerken te voorzien."*
- **Lid 3:** motiverings-eis (energieopbrengst vs. impact). Toelichting: opwekken "voor eigen behoefte", teruglevering aan het net zoveel mogelijk beperken.
- **Zone semantics for the Formalizer:** inclusion zone `Gebied kleine windturbine` (GIO `…/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822`) ∩ on/near existing bouwperceel; parameter `ashoogte ≤ 20 m` (rule) / `≤ 30 m` (conditional exception).

### 5.3 Windenergielocatie (regional-scale) — art. 5.4

- **Lid 1 (≥3 MW inclusion zone + conditions):** *"Een omgevingsplan dat betrekking heeft op locaties binnen het Gebied windenergie kan regels bevatten die de realisatie van windturbines met een vermogen van 3 MW of meer toestaan, mits voldaan is aan de volgende voorwaarden: a. de windturbines worden in een in de omgeving passende combinatie van meerdere windturbines opgesteld; en b. er wordt voorzien in een opruimplicht na beëindiging van de activiteit."*
- **Lid 2 (<3 MW deviation):** *"In afwijking van het eerste lid kan een omgevingsplan regels bevatten die de realisatie van windturbines met een vermogen van minder dan 3 MW toestaan, mits wordt onderbouwd waarom windturbines met een vermogen van 3 MW of meer niet mogelijk zijn."*
- **Lid 3 (solitary turbine deviation):** *"In afwijking van het eerste lid kan een omgevingsplan regels bevatten die de realisatie van een solitaire windturbine toestaan, mits wordt onderbouwd waarom meerdere windturbines niet mogelijk zijn en dat de energieopbrengst van die solitaire windturbine opweegt tegen de impact die een solitaire turbine heeft op de omgeving."*
- **Lid 4:** motivering must contain onderbouwing + **beeldkwaliteitsparagraaf** + stakeholder-betrokkenheid.
- **Toelichting (geographic scope):** *"Dit artikel heeft betrekking op het landelijk gebied met uitzondering van de Natura 2000-gebieden en de ganzenrustgebieden."* (toelichting, niet-artikeltekst — but the province applies it as the reading of the instructieregel; visie states the same exclusion as ambition, see 5.8).
- **Toelichting (grid):** *"Uit oogpunt van leveringszekerheid en maatschappelijk belang acht de provincie het van belang plaatsing van windturbines te toetsen aan de berekeningen zoals opgenomen in het Rekenvoorschrift Omgevingsbeleid Module IV en in overleg te treden met de beheerder van hoogspanningsverbindingen."*
- **Zone semantics:** inclusion zone `Gebied windenergie` (GIO `…/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846`) within `Landelijk gebied` minus Natura 2000 / ganzenrustgebieden; qualitative conditions (clustering, opruimplicht, beeldkwaliteit) are non-spatial obligations for the Norm Formalizer to carry as `zoneSemantics: "inclusion"` with condition flags.

### 5.4 Stiltegebieden (quiet areas) — noise

**Artikel 9.25 Aanwijzing stiltegebied en aandachtsgebied stiltegebied:** lid 1 — *"Een Stiltegebied bestaat uit: a. het Gebied stille kern; en b. de Bufferzone stiltegebied."* lid 2 — *"Een Aandachtsgebied stiltegebied is een zone van 1500 meter rondom een Stiltegebied."* (→ a **deterministic 1500 m buffer** the Geo Analyst can compute from the Stiltegebied GIO.)

**Artikel 9.26 Doelstelling geluidniveau in stiltegebied:** *"De regels in deze paragraaf zijn gericht op het bereiken en behouden van: a. een 24-uursgemiddeld geluidniveau LAeq,24h van maximaal 40 dB(A) in het Gebied stille kern; en b. een 24-uursgemiddeld geluidniveau LAeq,24h van bij voorkeur 40 dB(A) maar maximaal 45 dB(A) in de Bufferzone stiltegebied."*

**Artikel 9.27 Instructieregel geluidniveau in stiltegebied:** omgevingsplannen binnen het Stiltegebied must contain rules that reckon with the art. 9.26 doelstelling.

**Artikel 9.28 Instructieregel windturbines in stiltegebied:** lid 1 — *"Een omgevingsplan dat betrekking heeft op locaties binnen het Stiltegebied kan regels bevatten die de realisatie van windturbines toestaan, mits voldaan is aan de volgende voorwaarden: a. de windturbines zijn regionaal afgestemd; b. de windturbines worden in een in de omgeving passende combinatie van meerdere windturbines opgesteld; c. de windturbines worden zodanig opgesteld dat de effecten op het Stiltegebied zo beperkt mogelijk zijn; d. er wordt voor wat betreft de effecten op het stiltegebied zoveel mogelijk aangesloten op de doelstelling voor het geluidniveau in stiltegebieden, bedoeld in Artikel 9.26; en e. er wordt voorzien in een opruimplicht na beëindiging van de activiteit."* Lid 2 requires motivation incl. that the locatie binnen het Stiltegebied "het meest geschikt is voor windturbines". Toelichting: de regionale afstemming "gaat over windturbines met een vermogen van 3 MW of meer" (RES / OER).

→ **Zone semantics:** conditional-inclusion in Stiltegebied with the 40/45 dB(A) LAeq,24h targets as assessment anchors; the Aandachtsgebied (1500 m) carries art. 9.29 "rekening houden met" instructieregel for noise sources outside.

### 5.5 Natuur: NNN, Groene contour, weidevogels

**Artikel 6.2 Instructieregel bescherming natuurnetwerk Nederland** lid 1: omgevingsplannen binnen het NNN "bevat regels die strekken tot bescherming, instandhouding, verbetering en ontwikkeling van de kwaliteit, de wezenlijke kenmerken en waarden en samenhang van het Natuurnetwerk Nederland."

**Artikel 6.3 Instructieregel geen aantasting natuurnetwerk Nederland** lid 1: geen regels die activiteiten toestaan die *"nadelige gevolgen kunnen hebben voor de wezenlijke kenmerken en waarden van het natuurnetwerk Nederland, bedoeld in Bijlage XI Wezenlijke kenmerken en waarden; of … kunnen leiden tot een vermindering van de kwaliteit, de oppervlakte of de samenhang van het natuurnetwerk Nederland."* Lid 2 lists the only exceptions (groot openbaar belang zonder reële alternatieven; meerwaardebenadering; beperkte wijziging) plus compensatie (paragraaf 6.1.3, art. 6.8–6.11; oppervlaktecompensatie berekening in Bijlage XII).

**Artikel 6.5 Instructieregel ontwikkelingen binnen de Groene contour** lid 1: binnen de Groene contour geen regels die activiteiten toestaan die *"de mogelijkheid om nieuwe natuur te realiseren op die gronden beperken waardoor deze gronden niet meer of in mindere mate kunnen bijdragen aan uitbreiding en versterking van het natuurnetwerk Nederland."* Lid 2 deviation requires o.a. compensatie "met een oppervlakte van minimaal de oppervlakte van het verlies" (≥1:1, inside the contour). Toelichting on wind: *"Dit betekent dat als windturbines worden geplaatst binnen de Groene contour, nieuwe natuur moet worden gerealiseerd."* (Wind = verstedelijking per Bijlage I / Afdeling 5.1-toelichting.)

**Artikel 6.7 Instructieregel ontwikkelingen weidevogelkerngebied** lid 1: nieuwe ontwikkelingen toegestaan *"onder voorwaarde dat de kwaliteit van het leefgebied van de weidevogels aantoonbaar per saldo minimaal wordt behouden."* (Toelichting explicitly names windturbines and zonnevelden as potentially negative developments.)

**Natura 2000 / stikstof — see §6 abstentions:** the verordening contains **no** Natura 2000 GIO and **no** stikstof-deposition articles; the wind exclusion from Natura 2000-gebieden rests on the toelichting/visie + national law.

### 5.6 Landschap & cultuurhistorie

**Artikel 7.3 Instructieregel instandhouding en versterking UNESCO Werelderfgoed Hollandse Waterlinies** lid 1: omgevingsplan binnen het gebied "neemt de uitzonderlijke universele waarde van de Hollandse Waterlinies in acht en bevat regels voor instandhouding en versterking daarvan; en bevat geen regels die activiteiten toestaan die die waarde aantasten." Lid 2 ties "uitzonderlijke universele waarde" to **Bijlage XV Cultuurhistorie** en de Gebiedsanalyses Kernkwaliteiten Hollandse Waterlinies. (Analogous: 7.3a/7.4 Neder-Germaanse Limes kernzone/bufferzone.)

**Artikel 7.11 Aanwijzing landschap:** het Landschap bestaat uit vijf gebieden (Eemland, Gelderse Vallei, Groene Hart, Rivierengebied, Utrechtse Heuvelrug). **Artikel 7.11a** lid 1: omgevingsplannen in een Landschap "bevat: a. regels ter bescherming van de voorkomende kernkwaliteiten; en b. geen regels die nieuwe activiteiten toestaan die de kernkwaliteiten onevenredig aantasten." Lid 2: kernkwaliteiten per gebied in **Bijlage XVI Kernkwaliteiten landschap**. The art.-5.4 toelichting explicitly requires windturbine placement to reckon with these kernkwaliteiten.

### 5.7 Grondwater

**Artikel 3.7 Instructieregel ruimtelijke bescherming grondwater** lid 1: binnen een Waterwingebied, Grondwaterbeschermingsgebied, Boringsvrije zone, Beschermingszone oppervlaktewaterwinning, 100-jaarsaandachtsgebied of Gebied kwetsbare strategische grondwatervoorraad "laat geen activiteiten toe die een risico vormen voor de grond- en oppervlaktewaterwinning voor menselijke consumptie." (All these zones are GIO's in Bijlage II; chapter 3 also contains direct verbods, e.g. art. 3.27–3.34 for het Grondwaterbeschermingsgebied — foundation piles/borings etc., relevant to turbine foundations.)

### 5.8 Energie-infrastructuur (netcongestion)

**Artikel 5.10/5.11 Energietoets:** afdeling applies to "nieuwe functies die tot een overbelasting van de elektriciteits-infrastructuur kunnen leiden"; art. 5.11 lid 1: *"Voor zover een omgevingsplan voorziet in nieuwe functies, niet zijnde minder dan 10 woningen, die tot een aanvullende belasting van de elektriciteits-infrastructuur kunnen leiden, wordt rekening gehouden met de aansluitbaarheid op de elektriciteits-infrastructuur."* Lid 2: energieparagraaf + inventariserend overleg met the netbeheerder. (Ties directly to paper B's power-net congestion use case.)

### 5.9 Omgevingsvisie 2021 — ambitions (non-binding, clearly labeled)

- *"Wij sluiten windenergie en zonnevelden uit in Natura 2000-gebieden en ganzenrustgebieden."* (duurzame-energie paragraaf)
- *"Ook streven wij voor 2030 bij woningen en andere geluidgevoelige gebouwen naar het voldoen aan de WHO-advieswaarden voor geluid van windturbines in aanvulling op de wettelijke vereisten."*
- *"Wij faciliteren in principe geen turbines vanaf 20 meter en met een opgesteld vermogen van minder dan 3 MW, omdat deze turbines een te grote impact hebben op de omgeving in relatie tot het beperkte maatschappelijke rendement."*
- Visie map (figure caption): *"Plaatsingsmogelijkheden in landelijk gebied voor windturbines vanaf 3 MW en zonnepanelen in veldopstelling (bron: provincie Utrecht, 2019)"* — plus legend "Windturbines > 3 MW — Aanduiding buiten het stedelijk gebied — Hoe paarser, hoe meer mogelijk". This 2019-derived opportunity gradient is the visie-level analog of the verordening's `Gebied windenergie` GIO.
- Stedelijk gebied: *"Windturbines en zonnevelden in het stedelijk gebied vinden wij toelaatbaar. Wij formuleren daarvoor geen nadere regels."*

---

## 6. Abstentions and honest gaps (V2-relevant)

1. **Wind-turbine noise limits (general):** the provincial verordening sets **no** dB limits for wind turbines outside stiltegebied doelstellingen. Wind-turbine geluid is governed by national law (Wet geluidhinder/Bal under Omgevingswet). **Abstained** — no national instrument was fetched/verified in this run; the PoC must add a national-law NormCard source or mark this check unavailable. (The verordening-toelichting only refers to "milieubeheer zoals geluidnormen".)
2. **Stikstof (nitrogen deposition):** **no stikstof articles found in the verordening** (grep over the full consolidated text; the only occurrence of "stikstofbelasting" is in a toelichting on gebiedsopgaven). Nitrogen permitting for Natura 2000 is national law. **Abstained from formalizing a provincial stikstof rule.**
3. **Distance/hoogte beyond art. 5.3:** no provincial tip-height (tiphoogte), rotor-diameter, or setback distances (e.g. x×h from woningen) exist in the verordening. Any such numbers in the PoC must come from national rules or be parameterized as assumptions.
4. **Natura 2000 geometry:** not a provincial GIO; the exclusion is expressed in toelichting/visie. Geometry must come from a national source (RWS/Nationale Georegister) — geo recon's task.
5. **Radar/vrijwaringszones** (Luchtvaartterrein buffer GIO exists: `buffer luchtvaartterrein`; but rijkse radar policy is national): art. 5.4-toelichting mentions "rijksbeleid met betrekking tot vrijwaringszones voor radar" — no provincial article; abstain on formalizing distances.
6. **The exact geometry of `Gebied windenergie`:** not verifiable without the DSO API key (§2). The province's open ArcGIS layer `ET_wind_gebieden_windenergie` is an **energy-transition tracking layer** ("meest kansrijke gebieden"), **not** the juridische GIO — the PoC must not present it as the legal werkingsgebied without that caveat.

---

## 7. How the verordening binds to its map layers (task 5 answer)

- **No kaartbladen.** The verordening is born digital under STOP/TPOD: the algemene toelichting states the digitaliseringsopgave is leading — *"Hiermee kan zij formeel gepubliceerd worden en voor digitale dienstverlening aan burgers, bedrijven en partners via 'een klik op de kaart' toegankelijk zijn via het DSO. … Na een 'klik op de kaart' zijn de regels en informatie te zien die gelden op een specifieke locatie. Op een specifieke locatie kunnen meerdere regels uit de Omgevingsverordening van toepassing zijn."*
- **Binding mechanism:** each italicized gebied term in an article is defined by a **GIO** in **Bijlage II "Overzicht Informatieobjecten"**, each with a versioned JOIN-id of the form `/join/id/regdata/pv26/<jaar>/gio<uuid>/nld@<datum>;<versie>`. Wind/ZON/BOS-relevant examples captured verbatim from Bijlage II:

| Gebied | JOIN-id (version pinned by the verordening) |
|---|---|
| gebied kleine windturbine | `/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822` |
| gebied windenergie | `/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846` |
| gebied zonneveld | `/join/id/regdata/pv26/2025/gioa748cb8c-4f7f-4bbb-83d4-54becd3e0d1d/nld@2025-10-10;849` |
| groene contour | `/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798` |
| natuurnetwerk nederland | `/join/id/regdata/pv26/2025/gio3111b509-00cb-46c0-9967-b8102f81c85f/nld@2025-08-18;803` |
| stiltegebied / gebied stille kern / bufferzone stiltegebied / aandachtsgebied stiltegebied | `/join/id/regdata/pv26/2024/33gio8e108c08-f07d-431a-b17e-c5ca0b7df029/nld@2024-07-29;490` / `…/33gio0db8b52d-dc4d-4c36-a3eb-4aa1a871e63e/nld@2024-07-29;607` / `…/33gio0747a337-7964-4cd6-bf03-007a38a2724f/nld@2024-07-29;422` / `…/33gio9b5d732c-7a15-4007-a240-67569ca28950/nld@2024-07-29;550` |
| unesco werelderfgoed hollandse waterlinies | `/join/id/regdata/pv26/2024/33giobaba1ce0-087f-481b-b245-4e654690ac37/nld@2024-07-29;597` |
| waardevolle houtopstanden - oude bosgroeiplaatsen | `/join/id/regdata/pv26/2025/gio3940cf76-bee0-4a1a-8d51-aa0d49be7153/nld@2025-10-10;842` |
| landelijk gebied / stedelijk gebied | `…/gio17d47ef4-f140-45b7-8809-c5068d74698f/nld@2025-10-10;843` / `…/giob5049ae2-9548-4a0d-8e69-f0f1350202de/nld@2025-10-10;837` |
| waterwingebied / grondwaterbeschermingsgebied / grondwaterbeschermingszone | `…/giod90590cf-9ebc-46cc-8477-0b635fbf3d64/nld@2025-10-10;847` / `…/gioaf47db5b-c099-4603-828d-015197f15524/nld@2025-10-10;839` / `…/giod62bc3e3-b9b3-4a55-b01a-6640dbcb9ac8/nld@2025-10-10;841` |

*(Full list: Bijlage II in the CVDR snapshot; `33gio…` prefixes denote the 2024 instrument wave, `gio…` the 2025 wave — useful for version forensics.)*

- **Province-page URLs connecting regulation ↔ geo:**
  - Omgevingsverordening page → Regels op de kaart document: `https://omgevingswet.overheid.nl/regels-op-de-kaart/documenten/_akn_nl_act_pv26_2022_omgevingsverordening/overzicht` (AKN: `akn-nl-act-pv26-2022-omgevingsverordening`).
  - Omgevingsvisie page → Regels op de kaart document: `https://omgevingswet.overheid.nl/regels-op-de-kaart/documenten/akn-nl-act-pv26-2023-omgevingsvisie-1`.
  - NGR metadata record (dataset twin of the werkingsgebieden): `https://nationaalgeoregister.nl/geonetwork/srv/metadata/3a2f022d-cd39-4620-b43c-687d890c6e42` → plannenviewer `https://omgevingsbeleid.provincie-utrecht.nl`.
  - Province ArcGIS Hub search: `https://geo-point.provincie-utrecht.nl/api/v3/search?q=gebieden%20windenergie` → e.g. Feature Layer `Gebieden windenergie` at `https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/ET_wind_gebieden_windenergie/FeatureServer/13` (verified metadata: polygon, EPSG:28992, description "meest kansrijke gebieden … procedure voor windenergie verder opgepakt" — **tracking layer, not the legal GIO**). The `ow_bwp_*` services named by the geo recon did not surface under that name in Hub search — cross-check with the geo recon agent which service hosts them (likely the omgevingsbeleid plannenviewer's backing services).
- **PoC implication:** the NormCard→FormalRule chain should carry the JOIN-id as the canonical zone key (it is version-pinned *in the legal text itself*), with ArcGIS/PDOK layer ids only as render/provenance aliases.

---

## 8. BOS and ZON briefs (for architecture generalization)

### BOS (forest planting / nieuwe natuur)

1. **Art. 6.4 Instructieregel bescherming Groene contour ter omvorming naar natuur** — omgevingsplannen in de Groene contour "bevat regels die strekken tot het beschermen en creëren van de mogelijkheden om op de gronden gelegen binnen de Groene contour nieuwe natuur te realiseren." The Groene contour is the province's designated zoekgebied for new nature/forest (voluntary conversion; after realisatie it joins the NNN).
2. **Art. 6.5** (see §5.5): activities that reduce the nature-realization potential are prohibited unless groot openbaar belang + ≥1:1 compensation inside the contour.
3. **Art. 6.13 Instructieregel bescherming waardevolle houtopstanden - oude bosgroeiplaatsen** — omgevingsplannen in "Waardevolle Houtopstanden - oude bosgroeiplaatsen" "bevat regels die strekken tot bescherming en instandhouding van op de locatie van die oude bosgroeiplaats aanwezige waarden."
4. **Art. 6.15 Vrijstelling meldplicht vellen houtopstand** — vrijstellingen voor verjongingsgaten (≤10 are; samen ≤10% van het bosperceel; max 1× per 4 jaar; duurzaam bosbeheer) en voor natuurherstel van spontane boomopslag (<20 jaar, niet voor compensatie) — relevant when forest *management* interacts with planting plans.
5. **Visie (non-binding):** *"Voor 2040 realiseren we in totaal 3.000 hectares natuur in de Groene contour."* en *"Daarnaast onderzoeken wij de kansen voor uitbreiding van houtopstanden die bijdragen aan CO2-reductie."* (plus de stikstofproblematiek sentence that follows — context for siting difficulty).

### ZON (solar fields)

1. **Begripsbepaling (Bijlage I):** *"zonneveld: elke groepering van zonnepanelen die op of boven de grond of op het wateroppervlak wordt geplaatst, maar niet op daken van gebouwen."*
2. **Art. 5.5 Instructieregel zonneveld** lid 1 — binnen het `Gebied zonneveld` mogen zonnevelden worden toegestaan mits: a. *"de structuren in het landschap herkenbaar blijven en voorzien wordt in een goede landschappelijke inpassing"*; b. opstelling passend bij bodem- en waterkwaliteit; c. opruimplicht. Lid 2: motivering incl. beeldkwaliteitsparagraaf en kavelruil-beleid.
3. **Toelichting 5.5:** artikel betreft "het landelijk gebied met uitzondering van de natura 2000-gebieden en de ganzenrustgebieden"; voorkeur voor daken/gevels/infrastructuur boven veldopstellingen.
4. **Art. 6.5a lid 3 (Groene contour, tijdelijkheid):** *"In afwijking van tweede lid geldt voor de realisatie van nieuwe natuur als compensatie voor de plaatsing van zonneveld en dat de inrichtingsmaatregelen uiterlijk 25 jaar na plaatsing van de zonnepanelen worden uitgevoerd."* — solar in the Groene contour is implicitly temporary (25 jaar), after which the nieuwe-natuur inrichting follows.
5. **Visie (non-binding):** voorkeursvolgorde — zonnepanelen op daken, zonnevelden op/nabij bedrijventerreinen, buffers rond natuurgebieden, waterplassen, combinatie met recreatie/landbouw; uitsluiting Natura 2000 & ganzenrustgebieden (same quote as wind).

---

## 9. Source list (all verified 2026-08-30)

See machine-readable copy: `poc/corpus/sources.json`. Key URLs:

- Hub: https://www.provincie-utrecht.nl/onderwerpen/omgevingsvisie-en-omgevingsverordening (+ subpages …/omgevingsverordening, …/omgevingsvisie, …/wijziging-omgevingsvisie-en-verordening, …/handreikingen-bij-regels, …/projectbesluit, …/monitor-omgevingsbeleid, …/ingetrokken-visies-en-verordeningen)
- Consolidated verordening: https://lokaleregelgeving.overheid.nl/cvdr704250 (WTI: `?&show-wti=true`; version 8: https://lokaleregelgeving.overheid.nl/CVDR704250/8)
- Omgevingsvisie PDF: https://www.provincie-utrecht.nl/media/8648 (local: `docs/research/sources/omgevingsvisie-provincie-utrecht-ps-10-maart-2021-interactief.pdf`)
- Handreiking PDF: https://www.provincie-utrecht.nl/sites/default/files/2025-10/Handreiking%20Omgevingsverordening%20september%202025%20definitief.pdf
- Official publications: prb-2023-13766, prb-2024-2766/8813/11627 (WTI-listed, not fetched), prb-2024-10798, prb-2025-13284, prb-2025-16760, prb-2026-12 at https://zoek.officielebekendmakingen.nl/prb-<jaar>-<nr>.html
- Regels op de kaart documents: https://omgevingswet.overheid.nl/regels-op-de-kaart/documenten/_akn_nl_act_pv26_2022_omgevingsverordening/overzicht and …/akn-nl-act-pv26-2023-omgevingsvisie-1
- DSO developer portal (API, key-gated): https://developer.omgevingswet.overheid.nl/api-register/api/omgevingsdocument-downloaden/
- NGR metadata: https://nationaalgeoregister.nl/geonetwork/srv/metadata/3a2f022d-cd39-4620-b43c-687d890c6e42
- Province ArcGIS Hub search API: https://geo-point.provincie-utrecht.nl/api/v3/search?q=…
- ET_wind layer: https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/ET_wind_gebieden_windenergie/FeatureServer/13
- Dead end: https://wetten.overheid.nl/cgi-bin/deeplink/law1/title=Omgevingsverordening%20provincie%20Utrecht (HTTP 404)

**Local snapshots:** `docs/research/sources/` — CVDR HTML (geldende versie + WTI), tekst-extract, prb HTML snapshots, NGR metadata HTML, both PDFs and their pdftotext extracts.

---

## 10. Hand-over notes for the Norm Formalizer / Critic

- NormCard `source.article` for instructieregels should be `"art. 5.4 lid 1"`-style with `instrumentVersion = "Omgevingsverordening provincie Utrecht, CVDR704250 geldend 13-10-2025"` and the CVDR permalink as `uri`.
- Two evidence classes must stay distinguishable: **artikeltekst** (binding instructieregel) vs **toelichting** (interpretive, same document) vs **omgevingsvisie** (non-binding ambition). The evidence JSONs mark this via `instrument` + `notes`.
- Zone keys: carry the Bijlage-II JOIN-id verbatim; do not substitute the ET_wind ArcGIS layer for `Gebied windenergie`.
- Deterministic geometry derivable from legal text alone: the 1500 m Aandachtsgebied buffer (art. 9.25 lid 2) and the ≥1:1 Groene-contour compensation (art. 6.5 lid 2 d).
- Watch the 18-11-2026 / 01-01-2027 amendment: re-run this recon before then; the corpus store must version the CVDR snapshot (already saved) so V3 re-execution remains reproducible after the instrument changes.
