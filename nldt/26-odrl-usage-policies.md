# 26 — ODRL usage policies: datastoffering van het Utrechtse planproces

*Nummer voorlopig; de function-first-layer (AGENTIC_STATE_PLAN fase E) krijgt bij landing een ander nummer.*

| | |
|---|---|
| Specialiseert | [`13-data-lake-and-space.md`](13-data-lake-and-space.md) (share plane, accessClass) · [`07-trust-and-governance.md`](07-trust-and-governance.md) (V0–V4, cite-or-abstain) · spec [`docs/superpowers/specs/2026-10-07-odrl-usage-policies-design.md`](../docs/superpowers/specs/2026-10-07-odrl-usage-policies-design.md) |
| Beleid | **AI proposes · pipeline disposes · human decides** — op de share plane: de matrix hieronder is een voorstel, per bron aanpasbaar zonder code-wijziging; restricted blijft HITL-gated |
| Code | [`services/adapters/odrl_policies.py`](services/adapters/odrl_policies.py) · [`services/lake/publish.py`](services/lake/publish.py) · [`services/adapters/dataspace_connector.py`](services/adapters/dataspace_connector.py) · [`schemas/dataspace-policies.json`](schemas/dataspace-policies.json) |
| Status | live — publicatiegolf van 15 offers gedraaid 2026-10-07 (artefacten onder `nldt/data/dataspace/`, gitignored; de werkelijke JSON's staan in dit doc) |

---

## 1. Wat dit laag doet

De share plane had al connector, offers en HITL-gates — maar het beleid was documentair: een pseudo-constraint (`leftOperand: "accessClass"`) en een ContractDefinition die naar `policy-{accessClass}` verwees zonder dat die policy bestond. Sinds dit mijlpaal zijn er **drie vaste ODRL 2.2 usage-policies** (`schemas/dataspace-policies.json`), geëmbed in elk offer en meegeleverd in elk EDC-manifest — de DSSC-bouwsteen *usage control* is daarmee machinaal leesbaar. Enforcement gebeurt bij de ontvangende EDC zodra live; deze laag levert de beleidsobjecten.

| Policy | permission | prohibition | Betekenis in de planpraktijk |
|---|---|---|---|
| `policy-open` | use, distribute | — | CC0 — transparantie en contestability: iedereen mag gebruiken en herpubliceren |
| `policy-internal` | use, distribute *(binnen `nldt-participant`)* | distribute *(naar `external-party`)* | programming-kring: provincie, gemeenten, waterschappen, omgevingsdiensten, RES delen onderling; heruitgifte naar buitenstaanders verboden |
| `policy-restricted` | use | distribute (altijd) | besluitvormingstadium: gebruik alleen (bv. het scenario-team), geen enkele heruitgifte |

De vocabulaire-operanden (`nldt-participant`, `external-party`) zijn in `dataspace-policies.json` gedocumenteerd; binding aan echte participant-claims komt met de wallet-koppeling (nldt/16) — tot dan zijn ze documentair.

## 2. Fase × databron × acteur-matrix

De fasen volgen de policyStage-vierklap van de architectuur; actoren de stakeholder-tabel (SOLUTIONS_ARCHITECTURE §2) plus waterschappen/omgevingsdiensten. **✅ = aanwezig in de repo, ❌ = gat** — de gaten-kolom is tevens de databehoeftekaart voor het planproces.

| Fase | Databronnen (repo-status) | Provincie | Gemeente/waterschap/OD | RES/ontwikkelaar | Burger |
|---|---|---|---|---|---|
| **design** — beleidsvorming, verordening | Omgevingsvisie + CVDR704250 ✅ · stilte-/Natura2000-GIO's ✅ · planMER/planologie ❌ | eigenaar: alles | **open** lezen | **open** lezen | **open** inzien (contestability) |
| **programming** — programmering, RES | 13 track-analyses + crosstrack ✅ · scenario-sweeps ✅ · peilgebieden-stream Rijnland ✅ · energienetdata (EnergyCast) ❌ | **internal** alles | **internal** (use+distribute in de kring) | kanskaarten **open**; scenario-varianten op verzoek | samenvattingsniveau |
| **permission** — vergunning, plan | DSO omgevingsdocumenten ❌ (key-gated, 401-geverifieerd) · BAG/BGT via PDOK ❌ · bp2op plandocumenten ✅ | eigenaar/beoordelaar | **internal** + aanva-specifiek | eigen aanvraagdata: `restricted-pending` *(klasse-in-uitbreiding, nog niet gebouwd)* | eigen aanvraag inzien; besloten delen niet |
| **monitoring** — toezicht, herziening | source-monitor-freshness ✅ · DONL-harvest ✅ · herzieningsdiffs verordening 🟡 | **internal** | **internal** | samenvattingen | monitoring-dashboard **open** |

Input-caches en het norm-corpus (`poc/data/cache`, `poc/corpus`) krijgen **geen offer** — dat is bronmateriaal van provincie/CVDR/arcgisservices; de toolbox verwijst naar de autoritatieve bron, herpubliceert hem niet.

## 3. Live-publicatiegolf (15 offers, 2026-10-07)

Gedraaid tegen de echte stack (`NLDT_LAKE_BACKEND=fs`, connector `edc-manifest`): per canonieke track `sync_local_to_gold` + `publish_dataset`. Batch:

| # | Offer | Dataset (gold) | Klasse | Policy | Status |
|---|---|---|---|---|---|
| 1 | `offer-eb39d2cee7` | wind zones | open | policy-open | published |
| 2 | `offer-62b8cad434` | zon zones | open | policy-open | published |
| 3 | `offer-282d98257b` | bos zones | open | policy-open | published |
| 4 | `offer-be83e1713e` | water zones | open | policy-open | published |
| 5 | `offer-909a3a7d85` | bodem zones | open | policy-open | published |
| 6 | `offer-81017bd115` | mobiliteit zones | open | policy-open | published |
| 7 | `offer-231f1ee244` | landschap zones | open | policy-open | published |
| 8 | `offer-445f4f9c91` | landbouw zones | open | policy-open | published |
| 9 | `offer-c0a26604cb` | wonen zones | open | policy-open | published |
| 10 | `offer-47ae5b38e0` | werken zones | open | policy-open | published |
| 11 | `offer-bcc6425b8a` | recreatie zones | open | policy-open | published |
| 12 | `offer-81cf478e2c` | biomassa zones | open | policy-open | published |
| 13 | `offer-f58d06a433` | energietoets zones | open | policy-open | published |
| 14 | `offer-b508df9634` | zon-scenario-report | internal | policy-internal | published |
| 15 | `offer-82ba24424f` | zon world-scene-bundel | restricted | policy-restricted | published (HITL-approved) |

Rijen 1–13 instantiëren de design-fase (transparantie); rij 14 de programming-kring; rij 15 het besluitvormingstadium.

### 3.1 Uitwerking open — water-track (rij 4)

```json
{
  "@type": "Offer",
  "uid": "offer-be83e1713e",
  "datasetId": "gold-utrecht-run-20261004T185116Z-water-zones.geojson",
  "lakeUri": "lake://nldt-poc-lake/gold/utrecht/run/20261004T185116Z-water/zones.geojson",
  "accessClass": "open",
  "license": "CC0-1.0",
  "permission": [ { "odrl:action": ["odrl:use", "odrl:distribute"] } ],
  "createdAt": "2026-10-07T15:07:04.536843+00:00",
  "status": "published"
}
```

EDC-manifest: Asset + ContractDefinition (`accessPolicyId: policy-open`) + Policy-Definition `policy-open`. Wat een ontvangende EDC afdwingt: niets behalve de licentie — gebruik en heruitgifte zijn vrij (CC0). Dit is de contestability-laag: burgers en ontwikkelaars kunnen elke zone terugvoeren naar bronartikel + versie + quote.

### 3.2 Uitwerking internal — zon-scenario (rij 14)

```json
{
  "@type": "Offer",
  "uid": "offer-b508df9634",
  "datasetId": "gold-utrecht-scenario-20260831T175842Z-zon-scen-scenario-report.json",
  "lakeUri": "lake://nldt-poc-lake/gold/utrecht/scenario/20260831T175842Z-zon-scen/scenario-report.json",
  "accessClass": "internal",
  "permission": [
    { "odrl:action": ["odrl:use", "odrl:distribute"],
      "odrl:constraint": [{ "odrl:leftOperand": "odrl:spatial", "odrl:operator": "odrl:isA", "odrl:rightOperand": "nldt-participant" }] }
  ],
  "prohibition": [
    { "odrl:action": ["odrl:distribute"],
      "odrl:constraint": [{ "odrl:leftOperand": "odrl:spatial", "odrl:operator": "odrl:isA", "odrl:rightOperand": "external-party" }] }
  ],
  "status": "published"
}
```

Wat een ontvangende EDC afdwingt: use en distribute **binnen de deelnemerskring** (provincie ↔ gemeenten ↔ waterschap ↔ OD ↔ RES); heruitgifte aan een externe partij is een ODRL-prohibitie — het scenario-overleg tussen gebiedspartners kan onderling delen, de buitenwereld niet.

### 3.3 Uitwerking restricted — world-scene-bundel (rij 15)

```json
{
  "@type": "Offer",
  "uid": "offer-82ba24424f",
  "datasetId": "gold-utrecht-scenario-20260831T074604Z-zon-scen-worldscene-world-scene-specs.json",
  "lakeUri": "lake://nldt-poc-lake/gold/utrecht/scenario/20260831T074604Z-zon-scen-worldscene/world-scene-specs.json",
  "accessClass": "restricted",
  "permission": [ { "odrl:action": ["odrl:use"] } ],
  "prohibition": [ { "odrl:action": ["odrl:distribute"] } ],
  "hitlApproved": true,
  "status": "published"
}
```

De publicatie zelf ging door de HITL-gate (`force_hitl_approved=True` — zonder die vlag weigert `publish_dataset` restricted). Wat een ontvangende EDC afdwingt: gebruik alleen; elke distributie is verboden. Dit is het besluitvormingstadium: de hypothetische scènes (expliciet NIET juridisch gegronde stempel) zijn voor het team, niet voor buiten.

**Het HITL-moment als planproces-moment.** Opwaardering van een offer (bijv. internal → open ná bestuurlijk overleg en PS-instelling) is een menselijke stap in de planpraktijk, geen pipeline-stap: nieuwe offer, nieuwe klasse, menselijke goedkeuring — de doctrine "AI proposes · pipeline disposes · human decides" doorloopt de share plane.

## 4. Wat een aanbieder/ontvanger concreet heeft

| Onderdeel | Waar | Rol |
|---|---|---|
| Beleidsbron | `schemas/dataspace-policies.json` | drie ODRL-sets + vocabulair-documentatie (in git; beleid is contract) |
| Offer met ingebeten beleid | `nldt/data/dataspace/offers/` | leesbaar zonder opslag te raadplegen |
| Compleet EDC-manifest | `data/dataspace/edc-manifests/` (of env-override) | Asset + ContractDefinition **+ Policy-Definition** — een import heeft alles |
| http-backend | `NLDT_EDC_MANAGEMENT_URL` | POST policy → asset; fallback naar manifest bij fouten |
| Validatie | offer-schema + policy-schema + V-gates | beleidsvorm machinaal gecontroleerd vóór publicatie |

## 5. Notities en grenzen

- **Enforcement is niet van deze laag**: de policies zijn machinaal leesbaar en overdraagbaar; afdwingen gebeurt bij de ontvangende EDC zodra live (contract negotiation, transfer-audit — de volgende dataspace-mijlpalen).
- **De matrix is een voorstel**: per bron kan een mens een andere klasse kiezen zonder code-wijziging (alleen het `access_class`-argument van `publish_dataset`).
- **`restricted-pending`** (eigen aanvraagdata in de permission-fase) is benoemd maar niet gebouwd — kandidaat voor de dataspace-mijlpaal na DCAT-AP.
- **Vocabulair-binding**: `nldt-participant`/`external-party` worden documentair gehanteerd; met de wallet-dienst (nldt/16) worden het verifieerbare participant-claims.
- **Gaten-kolom** (planMER, PDOK, DSO, energienet) voedt de volgende databronnen-mijlpaal: de matrix is ook de databehoeftekaart van het planproces.
