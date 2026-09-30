# De rule graph van de Eindhoven-PoC: bronregel → kennisbank → omzettabel-rij → coverage

Deze pagina legt de kernketen van PoC-2 ([`poc-bp2op/`](../poc-bp2op/)) uit:
*"van bestemmingsplan naar omgevingsplan met AI"* voor gemeente Eindhoven.
Waar de [Utrecht-PoC (PoC-1)](POC_RULE_GRAPH.md) de keten
**artikel → NormCard → FormalRule → geolaag → zone** doorloopt (norm wordt
geometrie), is de keten in Eindhoven gespiegeld: **oude regel wordt nieuwe
regel** — geometrie is bewust een placeholder (methodekaart MC-11:
"werkingsgebieden zijn (nog) geen AI").

De PoC implementeert de vastgelegde methode van de Amsterdams aanpak (VNG
netwerksessie 19 juni 2026, tool **Plangids**), geprojecteerd op Eindhoven:
regel-voor-regel koppelen van de oude-wetre regels die voortleven in het
*tijdelijk deel* (bruidschat, hoofdstukken 22/23) van het Omgevingsplan
gemeente Eindhoven (CVDR696400/4) aan de nieuwe doelregeling
(hoofdstukken 1–21). Elke pipeline-feature citeert de methodokaart
(MC-1 … MC-12) die haar motiveerde; elk run-artefact draagt zijn eigen
`methodTrace`-veld.

```text
CVDR696400 (consolidatie)  +  GMB-wijzigingsbesluiten (kennisbank-bronnen)
  ├─ parsers.parse_doelregeling        1074 artikelen → 762 doelregels (hfd 1–21)
  │                                    + 311 bronregels (hfd 22/23), verbatim + dieptelinks
  └─ parsers.parse_kennisbank_pairs    274 "komt in de plaats van"/"voortzetting van"-relaties
        └─ knowledgebank.suggereer     TF-IDF-cosinus + kennisbank-boost → gescoorde suggesties
              └─ omzettabel            1 rij per bronregel: status + suggesties + werkingsgebiedRef
                    └─ coverage        match-ratio, gereedheidsbanden, needsNewRules-clusters
                          └─ critic    V0–V4 (V3 = onafhankelijke Jaccard-matcher, V4 = jurist, altijd pending)
```

## 1. Bronregels en doelregels — de populatie

De parsers lezen de gearchiveerde, officiële publicaties deterministisch in
en knippen ze op (MC-4): het CVDR-bestand levert **762 doelregels**
(hoofdstukken 1–21, de nieuwe omgevingsplan-regels) en **311 bronregels**
(hoofdstukken 22/23, het tijdelijk deel waarin oude bestemmingsplanregels
voortleven). Elke regel draagt: letterlijke tekst, dieptelink
(`…#chp_22__subchp_22.1__art_22.1`), locator (hoofdstuk/afdeling/artikel),
`statusInBron` (bijv. `geldend` of `[Vervallen]`) en een `thema`
(bijv. `gebruik:overig`). Niets wordt verzonnen — V2 verifieert later dat
elke tekst na whitespace-normalisatie letterlijk in het bronbestand staat.

## 2. Kennisbank — de eerder gemaakte conversies

Uit de officiële wijzigingsbesluiten (Gemeenteblad) haalt de parser
**274 "komt in de plaats van"- en "voortzetting van"-relaties**: regels die
het college eerder officieel heeft gekoppeld bij conversie of wijziging.
Deduplicatie op doelLocator+bronLabel laat de vroegste publicatie winnen.
Dit is de kennisbank uit de Amsterdams aanpak (MC-5): hergebruik van
eerdere conversies met match-scores.

## 3. Suggesties — TF-IDF plus kennisbank-boost

De matcher stelt per bronregel doelregels voor (MC-5/MC-6), en *suggereert
enkel*: TF-IDF-cosinus over unigrammen en bigrammen (met Nederlandstalige
normalisatie), aangevuld met een kennisbank-boost — een gepubliceerde
relatie krijgt score **1,0** en domineert altijd. De banden zijn zoals de
tool ze hanteert: **≥ 0,90 sterk**, 0,70–0,90 midden, < 0,70 zwak.

Voorbeeld uit de canonieke run (`runs/20260830-124515-eindhoven/`), rij
`OT-001`:

- bronregel `BR-001` — **artikel 22.1 Voorrangsbepaling** (tijdelijk deel):
  de regels van afdelingen 22.2/22.3 wijken voor strijdige regels in het
  tijdelijke deel, bedoeld in artikel 22.1, onder a, van de Omgevingswet;
- beste suggestie `DR-478` — **artikel 10.2 Voorrangsbepaling** (doelregeling):
  zelfde vangnet-bouw, nu voor hoofdstuk 10 (milieubelastende activiteiten);
  score 1,0 via kennisbankrelatie `KB-031` ("vervangt") uit het
  wijzigingsbesluit — de TF-IDF-score bedraagt ter vergelijking 0,764;
- de nummers 2 en 3 (`DR-648`, `DR-501`) blijven zwak (0,39 / 0,28) en worden
  als alternatief meegeleverd.

## 4. De omzettabel — één rij per bronregel, nooit gekoppeld door AI

Het kernartefact (MC-3) is de **omzettabel**: precies één rij per bronregel
met suggesties (1-op-n: activiteiten stapelen), status, toelichting en
`reviewTrail`. De status is `voorgesteld`, `nieuwe_regel_voorgesteld` of
`needs_human` — de status `gekoppeld` **bestaat bewust niet in het schema**
(MC-6: de mens blijft op de knoppen; een test verifieert dat een rij met
`gekoppeld_door_ai` op V0 faalt). Twijfel (vervallen regels, stapeling,
meerdere sterke kandidaten) levert `needs_human` met reden op. Elke rij kan
een `werkingsgebiedRef` dragen: de placeholder voor de robotiseringsstap
waarmee het werkingsgebied (geometrie) later automatisch mee verhuist.

## 5. Coverage en critic — planning en kwaliteitspoort

De coverage-analyse (MC-8) aggregeert de rijen tot een gereedheidsbeeld per
brondocument: match-ratio, gereedheidsbanden, clusters die eerst
doelregeling-uitbreiding vragen (`needsNewRules`, bijv. `gebruik:overig`,
9 regels) en de Planviewer-portefeuille (370 plannen, 338 vastgesteld,
18 TAM). De Critic gate de run daarna op vijf niveaus:

- **V0 syntactisch** — elk artefact schema-valide (7 contracten in
  [`poc-bp2op/schemas/`](../poc-bp2op/schemas/), incl. `bron-regel`,
  `doel-regel`, `kennisbank-pair`, `omzettabel-row`, `coverage-report`);
- **V1 volledigheid** — elke bronregel precies één rij; alle verwijzingen
  lossen op;
- **V2 verbatim-grounding** — elke bron- en doeltekst letterlijk in het
  gearchiveerde bestand; kennisbankcitaten letterlijk in het besluit;
  permalinks dragen het juiste CVDR-id;
- **V3 semantisch** — een onafhankelijke matcher (Jaccard i.p.v. TF-IDF)
  herscoort elke tekst-gedreven suggestie (canonieke run: top-1
  overeenkomst 0,43 over 82 rijen; de 220 kennisbank-gedreven rijen zijn
  buiten vergelijking, want geen giswerk);
- **V4 jurist** — de juristtoets: altijd `pending` (70 rijen aangewezen).

Canonieke eindstand: 311 rijen — 232 `voorgesteld` (waarvan 220
kennisbank-gedreven), 9 `nieuwe_regel_voorgesteld`, 70 `needs_human`;
verdict **pass** (V4 pending); beste match-ratio 75% (`deels_gereed`).

## Waarom deze opbouw

De traceback-keten is hier:

```text
omzettabel-rij → bronregel + doelregels (letterlijk citaat + dieptelink)
              → kennisbankrelatie → wijzigingsbesluit (Gemeenteblad)
              → methodokaart (MC-x) en prov.json (agents, sha256, derivations)
```

Elk voorstel is dus herleidbaar tot ofwel een officiële eerdere koppeling,
ofwel een expliciete, gescoorde tekstgelijkenis — en nooit tot een beslissing
van de AI. Samen met PoC-1 dekt dit beide kanten van het omgevingsrecht in
de toolbox: **wat mag waar?** (Utrecht, norm→zone) en **hoe verhuizen regels
van oud naar nieuw recht?** (Eindhoven, regel→regel). De RegelRecht-integratie
van beide PoC's staat in [`POC_REGELRECHT_INTEGRATION.md`](POC_REGELRECHT_INTEGRATION.md);
het Eindhovense voorbeeld-YAML is
[`examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml`](examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml).
