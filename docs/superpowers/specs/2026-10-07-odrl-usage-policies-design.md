# Ontwerp — ODRL usage policies: van stub naar machinaal leesbaar dataspacebeleid, gedemonstreerd op Utrecht

| | |
|---|---|
| **Datum** | 7 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | drie vaste ODRL 2.2 Policy-Definitions (één per accessClass) als eerste-klas beleidsartefacten + schema + lader; `build_odrl_offer` embedt echt beleid; EDC-manifest en `http`-backend leveren Policy-Definitions mee; uitgebreid worked example over het **volledige Utrecht-artefactlandschap** (classificatiematrix 13 tracks + scenario/crosstrack/world-scene + live-publicatiegolf van 15 offers) (`nldt/26-odrl-usage-policies.md`, nummer voorlopig) |
| **Buiten scope** | enforcement-runtime (afdwingen bij transfer — EDC wanneer live), configureerbare policy-templates (variabelen als verloopdatum/partner-groep), contract-negotiation, DCAT-AP-mapping (volgende dataspace-mijlpaal), wijzigingen aan lake-deny of de HITL-gate |
| **Bronnen** | [`nldt/13-data-lake-and-space.md`](../../../nldt/13-data-lake-and-space.md) (share plane, accessClass-tabel, "contract negotiation remains with the EDC/DSR stack") · [`nldt/services/lake/publish.py`](../../../nldt/services/lake/publish.py) (`build_odrl_offer` pseudo-ODRL, HITL-gate, deny-lijst) · [`nldt/services/adapters/dataspace_connector.py`](../../../nldt/services/adapters/dataspace_connector.py) (mock/edc-manifest/http; ContractDefinition verwijst naar `policy-{accessClass}` zonder dat die policy bestaat — het gat) · [`nldt/schemas/dataspace-offer.schema.json`](../../../nldt/schemas/dataspace-offer.schema.json) · DSSC-bouwstenen (usage control: van documentair naar machinaal) · ODRL 2.2 informatiemodel (W3C) |
| **Keuzes uit de sessie** | aanpak: **vaste policy-bibliotheek** (geen configureerbare templates — YAGNI) · beleidsregel heruitgifte: **binnen de groep** — open: use+distribute vrij (CC0); internal: use+distribute binnen nLDT-deelnemers, distribute aan externe partijen verboden; restricted: use only, distribute altijd verboden · Utrecht-voorbeeld expliciet als deliverable |

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

## 3. Worked example — volledig Utrecht-artefactlandschap (`nldt/26-odrl-usage-policies.md`)

Utrecht heeft 13 canonieke tracks plus scenario-, crosstrack- en world-scene-artefacten — het voorbeeld behandelt het landschap, niet drie kersen. Twee delen:

**3a. Classificatiematrix** — álle Utrecht-artefactfamilies, voorgestelde `accessClass` + policy + rationale:

| Familie | Omvang | Voorgestelde klasse + policy | Rationale |
|---|---|---|---|
| Track-zones (zones.geojson/zones.gml van de 13 canonieke runs) | 13 datasets | **open** (policy-open, CC0) | deterministische afleidingen van open overheidsdata (agrest IMOW-mirror, CVDR, ArcGIS Hub); schema-gevalideerd met PROV; herpubliceerbaar |
| Decision tables + normcard-sets per track | 13×2 | **open** (policy-open) | afgeleide, geciteerde legal mapping; contestability juist waardevol als open artefact |
| PROV- en ValidationReports (zijsporen) | per run | **open** (policy-open) | provenance is de kern van betwistbaarheid — hoort bij het zone-aanbod |
| Crosstrack-overlay (multi-track composities) | 1+ | **internal** (policy-internal) | combinatie-inzicht is de meerwaarde voor mede-deelnemers (RES/provincie-overleg), nog niet voor publiek |
| Scenario-runs (S7-proposals, sweeps) | per run | **internal** (policy-internal) | beleidsvarianten vóór besluitvorming — deelbaar binnen de kring, niet als publiek feit |
| World-scene-bundels (scenario-copilot) | per run | **restricted** (policy-restricted) | hypothetische scènes, expliciet NIET juridisch gegronde stempel; gebruik alleen, heruitgifte verboden |
| Input-caches + norm-corpus (poc/data/cache, corpus) | groot | **geen offer** (documentatie in matrix) | bronmateriaal van de provincie/CVDR — herpublicatie niet aan de toolbox; verwijzing naar de autoritatieve bron volstaat |

De matrix is een **voorstel** (doctrine: AI proposes · human decides); de live-golf hieronder voert hij uit zoals hij staat, zodat het doc een echt gedragen voorbeeld is.

**3b. Live-publicatiegolf** — gedraaid tegen de echte stack, vastgelegd in het doc met werkelijke artefacten:

1. **13 open offers** — per canonieke track de zones.geojson via `sync_local_to_gold` + `publish_dataset(access_class="open", license_="CC0-1.0")`; batch-tabel in het doc (offer-id ↔ track ↔ policy-open).
2. **1 internal offer** — de crosstrack-overlay (of, als die geen aparte gold-artefact heeft, de nieuwste scenario-sweep-output): use+distribute binnen deelnemers.
3. **1 restricted offer** — de world-scene-bundel van de nieuwste zon-scenario-run, mét `force_hitl_approved=True`: toont de HITL-gate + use-only.
4. Drie volledige uitwerkingen in het doc (één per klasse): offer-JSON, EDC-manifest mét Policy-Definition, ValidationReport, uitleg beleidskeuze; afsluitend de tabel offer ↔ policy ↔ wat een ontvangende EDC afdwingt.

Het doc noteert expliciet: enforcement gebeurt bij de ontvangende EDC zodra live; deze laag levert de beleidsobjecten. En: de matrix is voorstel — per artefactfamilie kan de mens een andere klasse kiezen zonder code-wijziging (alleen het publish-argument).

## 4. Testing

- Policy-bibliotheek: schema-validatie van alle drie; `policy_for` happy + onbekende klasse; ids-referentie-helper.
- Offer: `build_odrl_offer` embedt prohibition bij internal/restricted, niet bij open; generated offers valideren tegen het uitgebreide offer-schema; bestaande publish-tests groen (return-vorm ongewijzigd).
- Connector: manifest-bundle bevat policies met de `@id` die de ContractDefinition refereert; mock-register-entry met policyId.
- Worked example: live uitgevoerd tijdens de taak; het doc bevat de werkelijke artefacten (geen verzonnen JSON).

## Risico's

- **Beleidwijziging achteraf**: policies zijn in git en versienloos — een beleidswijziging verandert alle toekomstige offers, niet historische. Voor dit stadium acceptabel; versiebeheer per policy is uitbreidbaar later (veld `odrl:uid` + versie-suffix).
- **Vocabulairoperanden** (`nldt-participant`, `external-party`) zijn documentair tot de wallet-koppeling — expliciet in het doc benoemd zodat het geen impliciete aannames worden.
