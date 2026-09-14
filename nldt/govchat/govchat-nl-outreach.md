# nLDT × GovChat-NL — beleidskompas-koppeling: demo & vraag

*One-pager voor het GovChat-NL community-overleg (tweetalig voorblad; Nederlandse
tekst). Slotdatum demo: 14 september 2026.*

## Wat we hebben gebouwd

Het nLDT-testbed (referentie-implementatie Local Digital Twin, gekoppeld aan de
EU LDT Toolbox) heeft een **volledig bestuurbare, bestuurde koppelvlaklaag** voor
externe apps zoals de apps in de GovChat-NL app-launcher:

- **MCP-servers** (catalog, process, data, poc) over streamable-HTTP, achter
  bearer-authenticatie (nu statische tokens; Keycloak/EU LDT IM klaar voor
  productie).
- **OGC API Records & Processes** als open standaarden (AppStore → Cookbook →
  Cook), engine-agnostisch: elke workflow-engine (n8n, Kestra, Node-RED) of
  OpenWebUI-tool kan ze bedienen.
- **Recepten als orkestratiestandaard** (DT recipes): twee beleidsstappen van
  beleidskompas zijn al gedekt — *omgevingsanalyse* (ruimtelijke overlay) en
  *onderbouwing Q&A* (gegronde vraag-antwoord met cite-or-abstain en
  number-gate, seam S4).

## De demo (14 september 2026, live)

Vraag in chat: *'Why does Belcrum score low on spatial value?'*

Kestra (Docker) → MCP-handshake met bearer-token → `ask_scan` → antwoord
**gegrond in de officiële Breda five-value scan**: elke score letterlijk
aanwezig in de brondata (`groundingFails: []`), jobId traceerbaar (PROV), en de
hele keten als per-taak gecontroleerde Kestra-executie terug te spelen.
Beleidskompas is daarmee in de catalogus geregistreerd als **eerste externe
app** (record-type `application`) — het App Store-patroon uit de NLDT
referentiearchitectuur, nu werkend aangetoond.

Doelstelling-driehoek: *LLM's stellen voor · engines beslissen · mensen
beslissen.* Alle code open source in de LDT Toolbox-repo.

## Wat we vragen

1. **Roadmap & API** van beleidskompas: wanneer komt code, en welke koppelvlakken
   krijgt de app (MCP-tools? HTTP? alleen n8n-intern)?
2. **Licentie van de app-code**: de platformlicentie (Open WebUI License) is
   helder; de terms van de beleidskompas-app zelf zodra die landt.
3. **Interesse in een gezamenlijke pilot** (bijv. via Utrecht of direct met
   Limburg/CGI Smartlab): wij leveren de bestuurde nLDT-seams, jullie de
   policy-workflow.

## Links

- Architectuur & besluiten: `nldt/14-beleidskompas-integration.md` (Engels)
- Runbook & demo-artefacten: `nldt/govchat/README.md` ·
  `nldt/govchat/kestra-bk1-mcp-ask-scan.yaml`
- Catalog live: `GET /records?q=beleidskompas` (type `application`, `recipe`)

*Contact: nLDT-testbed / LDT Toolbox-team.*
