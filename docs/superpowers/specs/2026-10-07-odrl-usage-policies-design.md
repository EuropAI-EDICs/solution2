# Ontwerp — ODRL usage policies: van stub naar machinaal leesbaar dataspacebeleid, gedemonstreerd op Utrecht

| | |
|---|---|
| **Datum** | 7 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | drie vaste ODRL 2.2 Policy-Definitions (één per accessClass) als eerste-klas beleidsartefacten + schema + lader; `build_odrl_offer` embedt echt beleid; EDC-manifest en `http`-backend leveren Policy-Definitions mee; uitgebreid worked example: **datastoffering van het Utrechtse planproces** (fase × databron × acteur-matrix over design/programming/permission/monitoring, inclusief bron-gaten, + live-publicatiegolf van 15 offers) (`nldt/26-odrl-usage-policies.md`, nummer voorlopig) |
| **Buiten scope** | enforcement-runtime (afdwingen bij transfer — EDC wanneer live), configureerbare policy-templates (variabelen als verloopdatum/partner-groep), contract-negotiation, DCAT-AP-mapping (volgende dataspace-mijlpaal), wijzigingen aan lake-deny of de HITL-gate |
| **Bronnen** | [`nldt/13-data-lake-and-space.md`](../../../nldt/13-data-lake-and-space.md) (share plane, accessClass-tabel, "contract negotiation remains with the EDC/DSR stack") · [`nldt/services/lake/publish.py`](../../../nldt/services/lake/publish.py) (`build_odrl_offer` pseudo-ODRL, HITL-gate, deny-lijst) · [`nldt/services/adapters/dataspace_connector.py`](../../../nldt/services/adapters/dataspace_connector.py) (mock/edc-manifest/http; ContractDefinition verwijst naar `policy-{accessClass}` zonder dat die policy bestaat — het gat) · [`nldt/schemas/dataspace-offer.schema.json`](../../../nldt/schemas/dataspace-offer.schema.json) · DSSC-bouwstenen (usage control: van documentair naar machinaal) · ODRL 2.2 informatiemodel (W3C) |
| **Keuzes uit de sessie** | aanpak: **vaste policy-bibliotheek** (geen configureerbare templates — YAGNI) · beleidsregel heruitgifte: **binnen de groep** — open: use+distribute vrij (CC0); internal: use+distribute binnen nLDT-deelnemers, distribute aan externe partijen verboden; restricted: use only · Utrecht-voorbeeld = datastoffering van het planproces: **fase × databron × acteur** (op gebruikerscorrectie: niet alleen artefact-uitvoer, maar álle benodigde bronnen per fase en de actortoegang) |

## Context en doel

De share plane bestaat (connector met mock/edc-manifest/http-backends, offers met `accessClass`, deny-lijst, HITL-gate) maar het beleid is documentair: `build_odrl_offer` schrijft een pseudo-ODRL-constraint (`leftOperand: "accessClass"` is geen ODRL-operand) en de `ContractDefinition` in het EDC-manifest verwijst naar `policy-{accessClass}` zonder dat die Policy-Definition bestaat — een import in een echte EDC zou daarop vallen. Dit ontwerp maakt het gebruiksbeleid machinaal leesbaar en overdraagbaar: drie vaste ODRL 2.2 sets, geëmbed in offers én meegeleverd in EDC-manifests, gedemonstreerd op Utrecht-data.

## 1. Policy-bibliotheek

**`nldt/schemas/dataspace-policies.json`** (in git — beleid is contract, dus bij de schema's; `nldt/data/**` is gitignored) met drie ODRL 2.2 Set-policies:

| Policy | permission | prohibition | constraint |
|---|---|---|---|
| `policy-open` | use, distribute | — | geen — CC0: gebruik en heruitgifte zijn vrij (de beoogde kring staat in het doc, niet als constraint in het beleid) |
| `policy-internal` | use, distribute | distribute | permission-constraint `odrl:spatial isA nldt-participant`; prohibition richt zich op `odrl:spatial isA external-party` |
| `policy-restricted` | use | distribute | onbeperkte distribute-prohibitie |

Vormgeving conform ODRL 2.2 JSON-LD (context `https://www.w3.org/ns/odrl.jsonld`, `@type: odrl:Set`, `odrl:permission`/`odrl:prohibition` met `odrl:action`/`odrl:constraint`/`odrl:leftOperand`/`odrl:operator`/`odrl:rightOperand`). `policy-open` heeft dus geen constraints. De vocabulaire-operanden `nldt-participant` en `external-party` worden gedefinieerd in een klein vocabulairobject in hetzelfde bestand (documentair; binding aan echte participant-claims is de wallet-koppeling, buiten scope).

**`nldt/schemas/dataspace-policy.schema.json`**: valideert `@id` (enum van de drie), `@type`, permission/prohibition-arrayvorm.

**`nldt/services/adapters/odrl_policies.py`** (nieuw, puur): `load_policies() -> dict` (schema-gevalideerd), `policy_for(access_class: str) -> dict` (mapt open/internal/restricted → policy; `KeyError` bij onbekende klasse), `policy_ids_referenced_by(offer) -> list[str]`.

## 2. Changes aan de bestaande keten (klein, terugwaarts compatibel)

- **`build_odrl_offer`** (`services/lake/publish.py`): `permission` en nieuw `prohibition` komen uit `policy_for(access_class)`; het offer embedt de volledige policy-content (leesbaar zonder opslag te raadplegen). `accessClass`-veld en status/HITL-logica ongewijzigd. `dataspace-offer.schema.json` uitbreiden met `prohibition` (zelfde arrayvorm) — bestaande offers zonder `prohibition` blijven geldig.
- **`write_edc_manifest`** (`services/adapters/dataspace_connector.py`): bundle krijgt `"policies": [policy_for(access_class)]` naast asset + contractDefinition; de `policy-{accessClass}`-referentie in de ContractDefinition wordt daarmee vervuld.
- **`http_register_offer`**: POST Policy-Definition (`POST …/v3/policydefinitions`) vóór de Asset, met dezelfde fallback-naar-manifest als nu.
- **mock-backend**: register-entry krijgt `"policyId"`-veld; ongewijzigd verder.

## 3. Worked example — datastoffering van het Utrechtse planproces (`nldt/26-odrl-usage-policies.md`)

Het voorbeeld organiseert het volledige Utrecht-landschap rond de kernvraag van de dataspace: **welke databronnen zijn in welke fase van het planproces nodig, en welke actoren krijgen daar wel/geen toegang toe, onder welk beleid?** De fasen volgen de bestaande policyStage-vierklap (design → programming → permission → monitoring); de actoren volgen de stakeholder-tabel uit SOLUTIONS_ARCHITECTURE §2, aangevuld met waterschappen en omgevingsdiensten.

**3a. Fase × databron × acteur-matrix** (het hart van het doc). Per fase de benodigde bronnen — in de repo aanwezig of expliciet als gat benoemd — en het toegangsprofiel per actor:

| Fase | Databronnen (repo-status) | Provincie | Gemeente/waterschap/OD | RES/ontwikkelaar | Burger |
|---|---|---|---|---|---|
| **design** (beleidsvorming, verordening) | Omgevingsvisie + verordening CVDR704250 (✅ corpus); planMER/planologie-bronnen (❌ gat); stilte-/Natura2000-GIO's (✅ caches) | eigenaar: alles | **open** lezen | **open** lezen | **open** inzien (contestability) |
| **programming** (programmering, RES) | 13 track-analyses + crosstrack (✅ gold); scenario-sweeps (✅); peilgebieden-stream Rijnland (✅ CDC); energienetdata EnergyCast (❌ open seam) | **internal** alles | **internal** (policy-internal: use+distribute binnen deelnemers) | deelprofiel: kanskaarten **open**, scenario-varianten **op verzoek** | samenvattingsniveau |
| **permission** (vergunning, plan) | DSO omgevingsdocumenten (❌ key-gated, 401-geverifieerd); BAG/BGT via PDOK (❌ nog niet in lake); bp2op plandocumenten Eindhoven (✅ eigen PoC) | eigenaar/beoordelaar | **internal** + specifieke anva-data | eigen aanvraagdata: **restricted-pending** — nog te bouwen klasse; toegang via verzoek | eigen aanvraag inzien; besloten delen niet |
| **monitoring** (toezicht, herziening) | source-monitor-freshness (✅); DONL-harvest (✅); herzieningsdiffs verordening (🟡 deels) | **internal** | **internal** | samenvattingen | monitoring-dashboard **open** |

Legend: policy-open = use+distribute vrij; policy-internal = use+distribute binnen nLDT-deelnemers; restricted = use only. `restricted-pending` is als klasse-in-uitbreiding expliciet benoemd, niet gebouwd.

Bronnen die nog níet in de repo zitten (planMER, PDOK-lagen, DSO, energienet) worden in de matrix als **gat met bronvermelding** opgenomen — de matrix is daarmee ook de databehoeftekaart voor het planproces, niet alleen een deelcatalogus.

**3b. Live-publicatiegolf** — het aanbod dat de design/programming-kolommen vandaag al dekt, gedraaid tegen de echte stack:

1. **13 open offers** — de track-analyses (zones + decision tables + PROV per canonieke run), `license_="CC0-1.0"`: de design-fase-transparantie (contestability voor burgers en ontwikkelaars).
2. **1 internal offer** — crosstrack/scenario-output: de programming-kring (provincie + gemeenten + waterschap + RES), use+distribute binnen deelnemers.
3. **1 restricted offer** — world-scene-bundel van de nieuwste zon-scenario-run mét `force_hitl_approved=True`: use-only vóór het besluitvormingsteam; het doc toont de HITL-gate als planproces-moment (besluit ná bestuurlijk overleg → klasse-opwaardering is een menselijke stap).

Drie volledige uitwerkingen (één per klasse): offer-JSON, EDC-manifest mét Policy-Definition, ValidationReport; afsluitend de tabel offer ↔ policy ↔ fase ↔ actoren ↔ wat een ontvangende EDC afdwingt.

Het doc noteert: enforcement bij de ontvangende EDC zodra live; de matrix is voorstel (AI proposes · human decides) — per bron kan een mens de klasse bijstellen zonder code-wijziging; en de gaten-kolom voedt de volgende databronnen-mijlpaal.## 4. Testing

- Policy-bibliotheek: schema-validatie van alle drie; `policy_for` happy + onbekende klasse; ids-referentie-helper.
- Offer: `build_odrl_offer` embedt prohibition bij internal/restricted, niet bij open; generated offers valideren tegen het uitgebreide offer-schema; bestaande publish-tests groen (return-vorm ongewijzigd).
- Connector: manifest-bundle bevat policies met de `@id` die de ContractDefinition refereert; mock-register-entry met policyId.
- Worked example: live uitgevoerd tijdens de taak; het doc bevat de werkelijke artefacten (geen verzonnen JSON).

## Risico's

- **Beleidwijziging achteraf**: policies zijn in git en versienloos — een beleidswijziging verandert alle toekomstige offers, niet historische. Voor dit stadium acceptabel; versiebeheer per policy is uitbreidbaar later (veld `odrl:uid` + versie-suffix).
- **Vocabulairoperanden** (`nldt-participant`, `external-party`) zijn documentair tot de wallet-koppeling — expliciet in het doc benoemd zodat het geen impliciete aannames worden.
