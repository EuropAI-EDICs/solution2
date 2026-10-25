/** @typedef {{ nl: string, en: string }} Str */

export const strings = {
  brand: { nl: "LDT CitiVERSE EDIC", en: "LDT CitiVERSE EDIC" },
  heroEyebrow: { nl: "PROJECT", en: "PROJECT" },
  heroBrand: { nl: "Marketplace", en: "Marketplace" },
  tagline: {
    nl: "Herbruikbare recepten voor lokale digitale tweelingen",
    en: "Reusable recipes for local digital twins",
  },
  heroLead: {
    nl: "Een catalogus van spatiale blueprints, city recipes en lake-workflows uit het LDT CitiVERSE EDIC-ecosysteem.",
    en: "A catalogue of spatial blueprints, city recipes and lake workflows from the LDT CitiVERSE EDIC ecosystem.",
  },
  ctaCatalog: { nl: "Bekijk recepten", en: "Browse recipes" },
  ctaExplain: { nl: "Wat zijn recepten?", en: "What are recipes?" },
  catalogEyebrow: { nl: "OVERZICHT", en: "OVERVIEW" },
  explainTitle: { nl: "Recepten & JSON-bronnen", en: "Recipes & JSON sources" },
  explainLead: {
    nl: "Een recept is een uitvoerbaar stappenplan voor de digitale twin: welke OGC-processen in welke volgorde, met welk risico en welke acceptatiecriteria.",
    en: "A recipe is an executable playbook for the digital twin: which OGC processes run in which order, at what risk level, and with which acceptance criteria.",
  },
  explainRecipesTitle: { nl: "Wat doet een recept?", en: "What does a recipe do?" },
  explainRecipesBody: {
    nl: "Recepten sturen AppStore → Cookbook → Cook. Ze verwijzen naar processen (bijv. peil-conflict, opportunity-map) en produceren herhaalbare resultaten met validatie en herkomst (PROV). In deze catalogus zie je de toepassing in gewone taal; open een kaart voor detail, processen en eigenaar (LDT EDIC of EuropAI).",
    en: "Recipes drive AppStore → Cookbook → Cook. They reference processes (e.g. peil conflict, opportunity map) and produce repeatable outcomes with validation and provenance (PROV). This catalogue shows the application in plain language; open a card for detail, processes and owner (LDT EDIC or EuropAI).",
  },
  explainJsonTitle: { nl: "Waar komt de JSON vandaan?", en: "Where does the JSON come from?" },
  explainJsonBody: {
    nl: "De canonieke bestanden staan in de nLDT-repo onder nldt/recipes/*.json. De EuropAI/EDIC-index nldt/recipes/edic-asset-map.json koppelt elk recept aan EDIC, assetklasse en gereedheid. Bij bouwen van deze site worden ze gekopieerd naar marketplace/data/recipes/ en samengevat in marketplace/data/catalog.json — de .json-link in het detailpaneel opent precies die brondefinitie. Deze site gebruikt alleen die lokale catalogus.",
    en: "Canonical files live in the nLDT repo under nldt/recipes/*.json. The EuropAI/EDIC index nldt/recipes/edic-asset-map.json maps each recipe to EDIC, asset class and readiness. When this site is built they are copied to marketplace/data/recipes/ and summarised in marketplace/data/catalog.json — the .json link in the detail panel opens that source definition. This site uses that local catalogue only.",
  },
  catalogTitle: { nl: "Receptencatalogus", en: "Recipe catalogue" },
  catalogLead: {
    nl: "Filter op thema, zoek op titel, open een recept voor toepassing en processen.",
    en: "Filter by theme, search by title, open a recipe for application notes and processes.",
  },
  searchPlaceholder: { nl: "Zoek recepten…", en: "Search recipes…" },
  allThemes: { nl: "Alles", en: "All" },
  risk: { nl: "Risico", en: "Risk" },
  owner: { nl: "Eigenaar", en: "Owner" },
  readiness: { nl: "Gereedheid", en: "Readiness" },
  processes: { nl: "Processen", en: "Processes" },
  application: { nl: "Toepassing", en: "Application" },
  acceptance: { nl: "Acceptatie", en: "Acceptance" },
  sourceJson: { nl: "Bron-JSON", en: "Source JSON" },
  workflowPipeline: { nl: "Componentenpipeline", en: "Component pipeline" },
  workflowAgent: { nl: "Agent / AI-workflow", en: "Agent / AI workflow" },
  workflowStep: { nl: "Stap", en: "Step" },
  workflowProcess: { nl: "Proces", en: "Process" },
  workflowBackend: { nl: "Backend", en: "Backend" },
  workflowParties: { nl: "Partijen", en: "Parties" },
  workflowBlueprint: { nl: "Blueprint-stappen", en: "Blueprint steps" },
  workflowGenAi: { nl: "GenAI-testpunten", en: "GenAI test points" },
  workflowHuman: { nl: "Mens-overname", en: "Human handover" },
  workflowExceptions: { nl: "Uitzonderingen", en: "Exceptions" },
  workflowLoading: { nl: "Workflow laden…", en: "Loading workflow…" },
  computeAlgorithm: { nl: "Algoritme", en: "Algorithm" },
  computeGenai: { nl: "GenAI-model", en: "GenAI model" },
  computeHybrid: { nl: "Hybride", en: "Hybrid" },
  computeAlgorithmHint: {
    nl: "Deterministische code — geen taalmodel.",
    en: "Deterministic code — no language model.",
  },
  computeGenaiHint: {
    nl: "Kan een GenAI-model aanroepen (voorstel/vraag); pipeline + mens beslissen.",
    en: "May call a GenAI model (propose/ask); pipeline + human decide.",
  },
  computeHybridHint: {
    nl: "Deterministische vloer + GenAI-verkenner (AI stelt voor, pipeline beslist).",
    en: "Deterministic floor + GenAI explorer (AI proposes, pipeline disposes).",
  },
  empty: { nl: "Geen recepten voor deze filter.", en: "No recipes for this filter." },
  close: { nl: "Sluiten", en: "Close" },
  themes: {
    utrecht: { nl: "Utrecht", en: "Utrecht" },
    breda: { nl: "Breda", en: "Breda" },
    rijnland: { nl: "Rijnland", en: "Rijnland" },
    eindhoven: { nl: "Eindhoven", en: "Eindhoven" },
    lake: { nl: "Lake & data", en: "Lake & data" },
    gis: { nl: "GIS & beleid", en: "GIS & policy" },
    key: { nl: "The Key", en: "The Key" },
    city: { nl: "City recipes", en: "City recipes" },
    other: { nl: "Overig", en: "Other" },
  },
  footer: {
    nl: "LDT CitiVERSE EDIC · BUILD · nLDT Testbed · Medegefinancierd door de EU (Digital Europe)",
    en: "LDT CitiVERSE EDIC · BUILD · nLDT Testbed · Co-funded by the EU (Digital Europe)",
  },
};

/** Application blurbs (why / when to use) — keyed by recipe id */
export const applications = {
  "spatial-overlay-analysis": {
    nl: "Generieke spatiale analyse: twee lagen ophalen, snijden en oppervlakte berekenen. Basisbouwsteen voor beleid- en twin-overlays.",
    en: "Generic spatial analysis: fetch two layers, intersect, and compute area statistics. Building block for policy and twin overlays.",
  },
  "hex-overlay-analysis": {
    nl: "Zelfde vraag als overlay, maar in H3-hexcellen — handig voor dichtheid, hotspots en Moran's I over een stad.",
    en: "Same question as overlay, but in H3 hex cells — useful for density, hotspots and Moran's I across a city.",
  },
  "beleidskompas-omgevingsanalyse": {
    nl: "GENAI-veilige omgevingsanalyse voor het Beleidskompas: spatiale feiten eerst, taalmodel alleen als uitleg — geen losse claims.",
    en: "GENAI-safe environmental analysis for Beleidskompas: spatial facts first, LLM only for explanation — no freestyle claims.",
  },
  "breda-five-value-scan": {
    nl: "Voer of herhaal de Breda vijf-waarden scan; resultaten landen in gold op de lake wanneer post-run sync aan staat.",
    en: "Run or replay the Breda five-value scan; results land in gold on the lake when post-run sync is enabled.",
  },
  "breda-gebiedsafweging": {
    nl: "Integrale afweging van claims (woning / dak-PV) op de scan — trade-offs zichtbaar, geen automatische winnaar (HITL).",
    en: "Integral weighing of claims (housing / rooftop PV) on the scan — trade-offs visible, no automatic winner (HITL).",
  },
  "breda-scan-qa": {
    nl: "Stel vragen over een canonieke scan-run met cite-or-abstain: antwoorden alleen met bron in de artefacts.",
    en: "Ask questions over a canonical scan run with cite-or-abstain: answers only with evidence in the artefacts.",
  },
  "utrecht-opportunity-map": {
    nl: "Opportunity-map voor Utrecht (Plane A): zones en kansen uit de twin-engine, herhaalbaar via OGC Process.",
    en: "Opportunity map for Utrecht (Plane A): zones and opportunities from the twin engine, replayable via OGC Process.",
  },
  "utrecht-scenario-author": {
    nl: "Stel scenario's voor op een baseline-run (S7): deterministische vloer + LLM-verkenner, met reject-ledger.",
    en: "Propose scenarios on a baseline run (S7): deterministic floor + LLM explorer, with a reject ledger.",
  },
  "utrecht-scenario-sweep": {
    nl: "Offline sweep van scenario's tegen een opportunity-map — vergelijk control vs. mutaties.",
    en: "Offline sweep of scenarios against an opportunity map — compare control vs mutations.",
  },
  "utrecht-world-scene": {
    nl: "Bouw world-scene specs uit een scenario-run voor 3D/visualisatie (Marble-prompts gated).",
    en: "Build world-scene specs from a scenario run for 3D/visualisation (gated Marble prompts).",
  },
  "multi-track-crosstrack": {
    nl: "Leg wind-, solar- en forest-tracks over elkaar voor conflict- en synergie-inzicht.",
    en: "Overlay wind, solar and forest tracks for conflict and synergy insight.",
  },
  "rijnland-peil-conflict": {
    nl: "Vergelijk vigerend peilgebied met praktijkafwijking — kern van de Rijnland-waterschapstwin.",
    en: "Compare formal water-level areas with practice deviations — core of the Rijnland water-board twin.",
  },
  "rijnland-peil-conflict-live": {
    nl: "Zelfde conflictanalyse, maar gevoed door een verse CDC-snapshot uit de lake (freshness gate).",
    en: "Same conflict analysis, but fed by a fresh CDC snapshot from the lake (freshness gate).",
  },
  "rijnland-peil-whatif": {
    nl: "What-if op peilen: delta → lake CDC → rapport + multi-scenario kaart voor bestuurdersdemo's.",
    en: "Peilen what-if: delta → lake CDC → report + multi-scenario map for decision-maker demos.",
  },
  "eindhoven-bp2op": {
    nl: "Bestemmingsplan naar omgevingsplan (bp2op) met verplichte menselijke goedkeuring (V4).",
    en: "Zoning plan to environmental plan (bp2op) with mandatory human approval (V4).",
  },
  "minigim-gebiedscheck": {
    nl: "Snelle omgevingscheck (MiniGIM): Lijst-items uit open data + ILS-concept voor een AOI.",
    en: "Quick area check (MiniGIM): list items from open data + ILS draft for an AOI.",
  },
  "donl-harvest-run": {
    nl: "Haal metadata/bestanden van data.overheid.nl naar bronze + DCAT in de nLDT-lake.",
    en: "Pull metadata/files from data.overheid.nl into bronze + DCAT in the nLDT lake.",
  },
  "donl-harvest-publish": {
    nl: "Harvest één DONL-pakket én publiceer een Data Space-offer (EDC-manifest) — open-data pilotpad.",
    en: "Harvest one DONL package and publish a Data Space offer (EDC manifest) — open-data pilot path.",
  },
  "lake-publish-offer": {
    nl: "Maak een ODRL-offer over een lake://-dataset; restricted vereist expliciete HITL-goedkeuring.",
    en: "Create an ODRL offer over a lake:// dataset; restricted requires explicit HITL approval.",
  },
  "timeseries-open-ingest": {
    nl: "Curated tijdreeksen (peilen, WKP, KNMI, CBS) naar silver — input voor twin-freshness en marts.",
    en: "Curated time series (peilen, WKP, KNMI, CBS) into silver — input for twin freshness and marts.",
  },
  "source-monitor-run": {
    nl: "Bewaak ArcGIS/open-data bronnen: detecteer drift, stel registry-patch voor — nooit auto-apply.",
    en: "Monitor ArcGIS/open-data sources: detect drift, propose registry patches — never auto-apply.",
  },
  "thk-02-having-a-baby": {
    nl: "Life-event: zwangerschap → geboorteaangifte als één reis over meerdere loketten (HCS-blueprint).",
    en: "Life event: pregnancy → birth registration as one journey across counters (HCS blueprint).",
  },
  "thk-08-move-home": {
    nl: "Life-event verhuizen: één gesorteerde burgerreis over gemeente, energie en registratie.",
    en: "Life event moving home: one sorted citizen journey across municipality, energy and registration.",
  },
  "thk-24-build-renovate": {
    nl: "Bouwen/verbouwen: vergunningcheck + MiniGIM-gebiedscheck, besluit blijft bij de mens.",
    en: "Build/renovate: permit check + MiniGIM area check; the decision stays with the human.",
  },
  "uam-01-medical-logistics": {
    nl: "Medische drone-logistiek: corridor toetsen aan beschermde zones vóór operationeel gebruik.",
    en: "Medical drone logistics: validate corridors against protected zones before operational use.",
  },
  "uam-09-geofencing-zones": {
    nl: "Geofencing & security zones voor UAM vastleggen en toetsen aan bestaande no-fly/corridors.",
    en: "Define UAM geofencing & security zones and check against existing no-fly/corridors.",
  },
  "grn-01-canopy-measure": {
    nl: "3-30-300: bladerdak (30%) meten per wijk uit luchtfoto's, met steekproefcontrole door een medewerker.",
    en: "3-30-300: measure canopy (30%) per neighbourhood from imagery, with staff sample checks.",
  },
  "grn-03-300m-gaps": {
    nl: "3-30-300: vind adressen buiten 300 m van goed groen en laat het gebiedsteam prioriteren.",
    en: "3-30-300: find addresses beyond 300 m of quality green and let the area team prioritise.",
  },
  "cir-01-circular-condition": {
    nl: "Circulariteit als harde eis bij gronduitgifte, met materiaalpaspoort als bewijs.",
    en: "Circularity as a hard condition in land issuance, with a material passport as evidence.",
  },
  "cir-04-shared-energy": {
    nl: "Gedeelde energie in de buurt: opwek koppelen aan verbruik en verdeling laten bekrachtigen.",
    en: "Shared neighbourhood energy: link generation to demand and ratify the allocation.",
  },
  "min-01-proximity-analysis": {
    nl: "15-minutenstad: voorzieningenbereik per adres, inclusief veilige routes.",
    en: "15-minute city: amenity reach per address, including safe routes.",
  },
  "min-04-hub-network": {
    nl: "15-minutenstad: hubnetwerk plannen (micro → stad) met locatievoorstel en besluitvorming.",
    en: "15-minute city: plan the hub network (micro → city) with siting proposal and decision step.",
  },
};

export function t(key, lang) {
  const node = key.split(".").reduce((o, k) => (o ? o[k] : undefined), strings);
  if (!node) return key;
  if (typeof node === "string") return node;
  return node[lang] || node.nl || key;
}

export function appText(recipeId, lang) {
  const a = applications[recipeId];
  if (!a) return "";
  return a[lang] || a.nl || "";
}
