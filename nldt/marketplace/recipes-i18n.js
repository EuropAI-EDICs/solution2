/** Localized title / description / acceptance per recipe id. */

export const recipeLocales = {
  "spatial-overlay-analysis": {
    title: {
      nl: "Spatiale overlay-analyse",
      en: "Spatial Overlay Analysis",
    },
    description: {
      nl: "Generiek nLDT-referentierecept: haal twee lagen op, snijd ze en bereken oppervlaktestatistieken. Use-case onafhankelijk.",
      en: "Generic nLDT reference recipe: fetch two layers, intersect, compute area statistics. Use-case agnostic.",
    },
    acceptance: {
      nl: "OGC Records/Processes; ValidationReport + PROV; live Marketplace- en P&V-pad op *.ldttoolbox.app",
      en: "OGC Records/Processes; ValidationReport + PROV; live Marketplace + P&V path on *.ldttoolbox.app",
    },
  },
  "hex-overlay-analysis": {
    title: {
      nl: "Hex-overlay-analyse (H3)",
      en: "Hex Overlay Analysis (H3)",
    },
    description: {
      nl: "nLDT-referentierecept: discretiseer een zonelaag naar H3-cellen, koppel punten per cel en meet spatiale autocorrelatie — het h3-py urban-analytics patroon op Nederlandse data. GeoJSON-input moet EPSG:4326 zijn (RFC 7946).",
      en: "nLDT reference recipe: discretise a zone layer into H3 cells, join point data per cell, and measure spatial autocorrelation — the h3-py urban-analytics pattern on Dutch data. All geojson inputs must be EPSG:4326 (RFC 7946).",
    },
    acceptance: {
      nl: "OGC Processes; schema-valide GeoJSON/H3-uitvoer; catalogus-process-id's",
      en: "OGC Processes; schema-valid GeoJSON/H3 outputs; catalog process ids",
    },
  },
  "beleidskompas-omgevingsanalyse": {
    title: {
      nl: "Beleidskompas omgevingsanalyse (overlay)",
      en: "Beleidskompas environmental analysis (overlay)",
    },
    description: {
      nl: "GENAI-veilige omgevingsanalyse voor de Beleidskompas-beleidsstap: twee lagen ophalen, snijden, oppervlakte berekenen. Wraps de generieke overlay-processen; oppervlaktecijfers blijven machine-berekend.",
      en: "GENAI-safe environmental analysis for the Beleidskompas policy step: fetch two layers, intersect, compute area statistics. Wraps the generic overlay processes; area figures stay machine-computed.",
    },
    acceptance: {
      nl: "Zelfde overlay-contract als spatial-overlay-analysis; de front-door app zelf is Digital Commons",
      en: "Same overlay contract as spatial-overlay-analysis; front-door app itself is Digital Commons",
    },
  },
  "breda-five-value-scan": {
    title: {
      nl: "Breda vijf-waarden scan",
      en: "Breda five-value scan run",
    },
    description: {
      nl: "Plane A via nLDT: herhaal of voer de Breda vijf-waarden scan uit; gold-artefacten syncen naar de lake wanneer NLDT_LAKE_POST_RUN=1.",
      en: "Plane A via nLDT: replay or execute Breda five-value scan; gold artifacts sync to lake when NLDT_LAKE_POST_RUN=1.",
    },
    acceptance: {
      nl: "Cite-or-abstain artefacten; ValidationReport V0–V4; city-facing capacity module",
      en: "Cite-or-abstain artefacts; ValidationReport V0–V4; city-facing capacity module",
    },
  },
  "breda-gebiedsafweging": {
    title: {
      nl: "Breda Plane D — integrale gebiedsafweging",
      en: "Breda Plane D — integral area trade-off",
    },
    description: {
      nl: "Stel spatiale claims (woningverdichting / dak-PV) samen op de Breda vijf-waarden scan; trade-off rapport met V4 menselijke beslissing. mode=offline-fixtures voor CI; mode=replay voor demos.",
      en: "Compose spatial claims (housing densification / rooftop PV) on the Breda five-value scan; trade-off report with V4 human decision. mode=offline-fixtures for CI; mode=replay for demos.",
    },
    acceptance: {
      nl: "SpatialClaimSpec + gebiedsafweging-rapport; control V3; V4 mens; geen winnaarscore",
      en: "SpatialClaimSpec + gebiedsafweging-report; control V3; V4 human; no winner score",
    },
  },
  "breda-scan-qa": {
    title: {
      nl: "Breda vijf-waarden scan Q&A",
      en: "Breda five-value scan Q&A",
    },
    description: {
      nl: "GENAI-seam S4 via nLDT: grounded Q&A over een canonieke Breda value-scan run (cite-or-abstain + number gate).",
      en: "GENAI seam S4 via nLDT: grounded Q&A over a canonical Breda value-scan run (cite-or-abstain + number gate).",
    },
    acceptance: {
      nl: "S4 cite-or-abstain; number gate; PROV; Toolbox IM bearer op A2A",
      en: "S4 cite-or-abstain; number gate; PROV; Toolbox IM bearer on A2A",
    },
  },
  "utrecht-opportunity-map": {
    title: {
      nl: "Utrecht opportunity-map (replay)",
      en: "Utrecht opportunity-map (replay)",
    },
    description: {
      nl: "Plane A via nLDT: herhaal de samenvatting van een canonieke poc/runs opportunity-map (execute-modus beschikbaar op het process).",
      en: "Plane A via nLDT: replay summary of a canonical poc/runs opportunity-map (execute mode available on the process).",
    },
    acceptance: {
      nl: "Machineleesbare planningsregels (NormCard/FormalRule); HITL; MIM + Rulebook-declaratie",
      en: "Machine-readable planning rules (NormCard/FormalRule); HITL; MIM + Rulebook declaration",
    },
  },
  "utrecht-scenario-author": {
    title: {
      nl: "Utrecht scenario-auteur (S7-voorstellen)",
      en: "Utrecht scenario author (S7 proposals)",
    },
    description: {
      nl: "GENAI-seam S7 via nLDT: hybride (deterministische vloer + LLM-verkenner) scenariovoorstellen vanaf een baseline-run (reject-ledger; geen zone-writes).",
      en: "GENAI seam S7 via nLDT: hybrid (det floor + LLM explorer) scenario proposals from a baseline run (reject ledger; no zone writes).",
    },
    acceptance: {
      nl: "LLM stelt alleen voor; engine berekent geometrie; reject-ledger; HITL",
      en: "LLM proposes only; engine-computed geometry; reject ledger; HITL",
    },
  },
  "utrecht-scenario-sweep": {
    title: {
      nl: "Utrecht scenario-sweep",
      en: "Utrecht scenario sweep",
    },
    description: {
      nl: "Plane B via nLDT: offline scenario-sweep tegen een baseline opportunity-map run (bestand of auto-author, control-reproductie).",
      en: "Plane B via nLDT: offline scenario sweep against a baseline opportunity-map run (file or auto author, control reproduction).",
    },
    acceptance: {
      nl: "Control-reproductie Δ ≤ 0,1%; scenariokeuze blijft menselijk (V4)",
      en: "Control reproduction Δ ≤ 0.1%; scenario choice remains human (V4)",
    },
  },
  "utrecht-world-scene": {
    title: {
      nl: "Utrecht world-scene opbouw",
      en: "Utrecht world scene build",
    },
    description: {
      nl: "Plane B-copilot: bouw world-scene-specs.json vanuit een scenario-run (engine GeoJSON-refs + gated Marble-prompts).",
      en: "Plane B copilot: build world-scene-specs.json from a scenario-run (engine GeoJSON refs + gated Marble prompts).",
    },
    acceptance: {
      nl: "Alleen ScenarioReport-rijen; engine GeoJSON-refs; Marble gated hypothetical+HITL; groundingStamp",
      en: "ScenarioReport-rows only; engine GeoJSON refs; Marble gated hypothetical+HITL; groundingStamp",
    },
  },
  "multi-track-crosstrack": {
    title: {
      nl: "Utrecht multi-track crosstrack",
      en: "Utrecht multi-track crosstrack",
    },
    description: {
      nl: "Plane C via nLDT: crosstrack-overlay over wind×solar×forest baseline-runs.",
      en: "Plane C via nLDT: crosstrack overlay across wind×solar×forest baseline runs.",
    },
    acceptance: {
      nl: "Paarsgewijze conflict-overlay; arbitrage = mens; ValidationReport",
      en: "Pairwise conflict overlay; arbitration = human; ValidationReport",
    },
  },
  "rijnland-peil-conflict": {
    title: {
      nl: "Rijnland peilconflict",
      en: "Rijnland peil conflict",
    },
    description: {
      nl: "PoC-3: peilgebied (vigerend) × peilafwijking (praktijk) via OGC-process rijnland-peil-conflict (replay van canonieke run).",
      en: "PoC-3: peilgebied (formal) × peilafwijking (practice) via OGC process rijnland-peil-conflict (replay of canonical run).",
    },
    acceptance: {
      nl: "Deterministische engine; catalogus-process-id; replay-artefacten",
      en: "Deterministic engine; catalog process id; replay artefacts",
    },
  },
  "rijnland-peil-conflict-live": {
    title: {
      nl: "Rijnland peilconflict (CDC lake-snapshot)",
      en: "Rijnland peil conflict (CDC lake snapshot)",
    },
    description: {
      nl: "Hybride: freshness-gate op CDC-toegepaste peilen-silver, daarna replay/execute van rijnland-peil-conflict. Streamtabel is lake-only (geen RisingWave).",
      en: "Hybrid: freshness gate on CDC-applied peilen silver, then replay/execute rijnland-peil-conflict. Stream table is lake-only (no RisingWave).",
    },
    acceptance: {
      nl: "HITL op live lake-snapshot; PROV; accessClass gerespecteerd",
      en: "HITL on live lake snapshot; PROV; accessClass respected",
    },
  },
  "rijnland-peil-whatif": {
    title: {
      nl: "Rijnland peilen what-if (CDC)",
      en: "Rijnland peilen what-if (CDC)",
    },
    description: {
      nl: "What-if peilen-delta → CDC bronze/silver → whatif-rapport + multi-scenario whatif-map.html (demo pack map-only) + optionele conflict-replay. Lake-only voor de actieve stream.",
      en: "What-if peilen delta → CDC bronze/silver → whatif-report + multi-scenario whatif-map.html (demo pack map-only) + optional conflict replay. Lake-only for the active stream.",
    },
    acceptance: {
      nl: "What-if blijft een voorstel; engine berekent Δ; HITL",
      en: "What-if remains a proposal; engine computes Δ; HITL",
    },
  },
  "eindhoven-bp2op": {
    title: {
      nl: "Eindhoven bp2op-transformatie",
      en: "Eindhoven bp2op transform",
    },
    description: {
      nl: "Bestemmingsplan → omgevingsplan conversie voor Eindhoven (poc-bp2op). V4 HITL altijd pending.",
      en: "Zoning plan → environmental plan conversion for Eindhoven (poc-bp2op). V4 HITL always pending.",
    },
    acceptance: {
      nl: "Method cards MC-1…12 traceerbaar; HITL; MIM-declaratie",
      en: "Method cards MC-1…12 traceable; HITL; MIM declaration",
    },
  },
  "minigim-gebiedscheck": {
    title: {
      nl: "MiniGIM gebiedscheck (Lijst + ILS-concept)",
      en: "MiniGIM area check (List + ILS draft)",
    },
    description: {
      nl: "PoC-5 via nLDT: MiniGIM-omgevingsanalyse voor een AOI — 74 Lijst-v0.91 items automatisch gevuld uit keyless open data (PDOK BGT/BAG/BRK/CBS/NWB/RCE, …).",
      en: "PoC-5 via nLDT: run the MiniGIM environmental analysis for an AOI — 74 List-v0.91 items auto-filled from keyless open data (PDOK BGT/BAG/BRK/CBS/NWB/RCE, …).",
    },
    acceptance: {
      nl: "74/74 Lijst-items gebonden; V0–V3 pass; PROV met sha256; V4 pending (HITL by design)",
      en: "74/74 List items bound; V0–V3 pass; PROV with sha256; V4 pending (HITL by design)",
    },
  },
  "timeseries-open-ingest": {
    title: {
      nl: "Open tijdreeks-ingest (silver)",
      en: "Open time-series ingest (silver)",
    },
    description: {
      nl: "Curated TS-ingest: Rijnland peilen/WKP + KNMI Gilze-Rijen (350) + CBS KWB Breda → bronze + silver/timeseries. Cross-twin lake-laag voor Elasticsearch-discovery.",
      en: "Curated TS ingest: Rijnland peilen/WKP + KNMI Gilze-Rijen (350) + CBS KWB Breda → bronze + silver/timeseries. Cross-twin lake layer for Elasticsearch discovery.",
    },
    acceptance: {
      nl: "Medallion silver-contract; alleen open bronnen; catalogus-datasetrecord",
      en: "Medallion silver contract; open sources only; catalog dataset record",
    },
  },
  "donl-harvest-run": {
    title: {
      nl: "Harvest data.overheid.nl naar nLDT data lake",
      en: "Harvest data.overheid.nl into nLDT data lake",
    },
    description: {
      nl: "CKAN-harvest van DONL-watchlist → bronze + catalog/dcat (DCAT-AP-NL). Bestandsdownloads optioneel; WFS/WMS als DataService-manifesten in silver.",
      en: "CKAN harvest from DONL watchlist → bronze + catalog/dcat (DCAT-AP-NL). File downloads optional; WFS/WMS registered as DataService manifests in silver.",
    },
    acceptance: {
      nl: "Bronze-snapshotintegriteit; DCAT-metadata; geen restricted publish zonder HITL",
      en: "Bronze snapshot integrity; DCAT metadata; no restricted publish without HITL",
    },
  },
  "donl-harvest-publish": {
    title: {
      nl: "DONL-dataset harvesten en Data Space-offer publiceren",
      en: "Harvest DONL dataset and publish Data Space offer",
    },
    description: {
      nl: "End-to-end: harvest één DONL-pakket → DCAT-catalogusrecord → Data Space-offer (EDC-manifest). Pilotpad voor open overheidsdata.",
      en: "End-to-end: harvest one DONL package → DCAT catalog record → Data Space offer (EDC-manifest). Pilot path for open government data.",
    },
    acceptance: {
      nl: "ODRL-offer; SIMPL/EDC-patroon of gelogde technical debt; HITL voor restricted",
      en: "ODRL offer; SIMPL/EDC pattern or logged technical debt; HITL for restricted",
    },
  },
  "lake-publish-offer": {
    title: {
      nl: "Lake-dataset publiceren als Data Space-offer",
      en: "Publish lake dataset as Data Space offer",
    },
    description: {
      nl: "Fase 6: maak een ODRL-stub Data Space-offer over een lake:// URI. accessClass=restricted vereist forceHitlApproved en Critic V4.",
      en: "Phase 6: create an ODRL-stub Data Space offer over a lake:// URI. accessClass=restricted requires forceHitlApproved and Critic V4.",
    },
    acceptance: {
      nl: "ValidationReport V0/V2/V4; pluggable connector mock|edc-manifest|http; SIMPL-alignment note",
      en: "ValidationReport V0/V2/V4; pluggable connector mock|edc-manifest|http; SIMPL alignment note",
    },
  },
  "source-monitor-run": {
    title: {
      nl: "Bronmonitor (open-data continuïteit)",
      en: "Source monitor (open-data continuity)",
    },
    description: {
      nl: "Deterministische ArcGIS REST-probes vs sources.json; machine diff + change report + registry-patchvoorstel. Nooit auto-apply — mens merged (V4).",
      en: "Deterministic ArcGIS REST probes vs sources.json; machine diff + change report + registry patch proposal. Never auto-applies — human merges (V4).",
    },
    acceptance: {
      nl: "Human-merge patches; geen stille overwrite van silver; HITL",
      en: "Human-merge patches; no silent overwrite of silver; HITL",
    },
  },
  "thk-08-move-home": {
    title: {
      nl: "The Key THK-08 — 'Ik wil verhuizen'",
      en: "The Key THK-08 — 'I want to move home'",
    },
    description: {
      nl: "Life-event recept uit de Human-Centred Services Blueprint (EDIC): verhuizen als één gesorteerde reis over gemeente, energie, bank, verzekeraar en zorgverzekeraar.",
      en: "Life-event recipe from the Human-Centred Services Blueprint (EDIC): moving home as one sorted journey across municipality, energy, bank, insurer and health insurer.",
    },
    acceptance: {
      nl: "GenAI-testbank G1–G5 + function-baseline; deterministische replay via OGC API Processes (hcs-life-event-run)",
      en: "GenAI testbank G1–G5 + function-baseline; deterministic replay via OGC API Processes (hcs-life-event-run)",
    },
  },
  "thk-02-having-a-baby": {
    title: {
      nl: "The Key THK-02 — 'Ik krijg een kind'",
      en: "The Key THK-02 — 'I'm having a baby'",
    },
    description: {
      nl: "Life-event recept (reactief → proactief): zwangerschap start het traject vóór de geboorte; geboorteaangifte binnen 5 dagen; keten naar SVB, Belastingdienst en zorg.",
      en: "Life-event recipe (reactive → proactive): pregnancy starts the journey before birth; birth registration within 5 days; chain to social security, tax and care.",
    },
    acceptance: {
      nl: "GenAI-testbank G2/G5 + function-baseline; deterministische replay via OGC API Processes (hcs-life-event-run)",
      en: "GenAI testbank G2/G5 + function-baseline; deterministic replay via OGC API Processes (hcs-life-event-run)",
    },
  },
  "thk-24-build-renovate": {
    title: {
      nl: "The Key THK-24 — 'Ik wil bouwen of verbouwen'",
      en: "The Key THK-24 — 'I want to build or renovate'",
    },
    description: {
      nl: "Life-event recept: bouwplan → vergunningcheck (Omgevingsloket) → aanvraag → beoordeling door de mens → besluit binnen 8 weken (regulier). De vergunningcheck gebruikt MiniGIM-ingredienten.",
      en: "Life-event recipe: building plan → permit check (Omgevingsloket) → application → human review → decision within 8 weeks (regular). The permit check uses MiniGIM ingredients.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; menselijke beoordeling by design; declaratieve minigim-ingredienten",
      en: "GenAI testbank + function-baseline; human review by design; declarative minigim ingredients",
    },
  },
  "uam-01-medical-logistics": {
    title: {
      nl: "Urban Air Mobility UAM-01 — 'Medische logistiek door de lucht'",
      en: "Urban Air Mobility UAM-01 — 'I want medical logistics by air'",
    },
    description: {
      nl: "City-recipe: ziekenhuis → monster → dronecorridor → lab in minuten. De route wordt getoetst aan beschermde zones; wijkt ze af van de vaste corridor, dan bevestigt een mens.",
      en: "City recipe: hospital → sample → drone corridor → lab in minutes. The route is checked against protected zones; if it leaves the fixed corridor, a human confirms.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "uam-09-geofencing-zones": {
    title: {
      nl: "Urban Air Mobility UAM-09 — 'Geofencing & security zones'",
      en: "Urban Air Mobility UAM-09 — 'I want geofencing & security zones'",
    },
    description: {
      nl: "City-recipe: beschermde en no-flyzones worden op de drone-kaart vastgelegd, getoetst aan bestaande zones en corridors, en via het U-space-identificatiesysteem aangesloten.",
      en: "City recipe: protected and no-fly zones are fixed on the drone map, checked against existing zones and corridors, and linked via the U-space identification system.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "grn-01-canopy-measure": {
    title: {
      nl: "3-30-300 GRN-01 — 'Bladerdak meten (de 30%)'",
      en: "3-30-300 GRN-01 — 'I want to measure canopy (the 30%)'",
    },
    description: {
      nl: "City-recipe: luchtfoto's → AI-bladerdakmeting → heat-map per wijk. Een medewerker controleert een steekproef; wijken onder de 30% krijgen een proactief signaal.",
      en: "City recipe: aerial imagery → AI canopy measurement → heat map per neighbourhood. A staff member checks a sample; neighbourhoods under 30% get a proactive signal.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "grn-03-300m-gaps": {
    title: {
      nl: "3-30-300 GRN-03 — 'De 300 m-gaten dichten'",
      en: "3-30-300 GRN-03 — 'I want to close the 300 m gaps'",
    },
    description: {
      nl: "City-recipe: loopafstand naar goed groen per adres → groene woestijnen benoemen → het gebiedsteam (mens) prioriteert met bewoners welke straat eerst vergroent.",
      en: "City recipe: walking distance to quality green per address → name green deserts → the area team (human) prioritises with residents which street greening first.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "cir-04-shared-energy": {
    title: {
      nl: "Circulaire buurten CIR-04 — 'Gedeelde energie'",
      en: "Circular neighborhoods CIR-04 — 'I want shared energy'",
    },
    description: {
      nl: "City-recipe: bewoners-eigen opwekking wordt gekoppeld aan verbruik, de verdeling wordt voorgesteld en door iedereen bevestigd; op de piekavond schikt de energie mee.",
      en: "City recipe: resident-owned generation is linked to demand, allocation is proposed and confirmed by everyone; on peak evening energy is reshaped accordingly.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "cir-01-circular-condition": {
    title: {
      nl: "Circulaire buurten CIR-01 — 'Circulaire ontwikkelvoorwaarde'",
      en: "Circular neighborhoods CIR-01 — 'I want a circular development condition'",
    },
    description: {
      nl: "City-recipe: bij gronduitgifte staat circulariteit als harde eis; het materiaalpaspoort levert het bewijs, en bij oplevering beoordeelt een mens of de eis echt is gehaald.",
      en: "City recipe: at land issuance circularity is a hard condition; the material passport provides evidence, and at handover a human judges whether the condition was truly met.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "min-01-proximity-analysis": {
    title: {
      nl: "15-minutenstad MIN-01 — 'Nabijheidsanalyse'",
      en: "15-minute city MIN-01 — 'I want a proximity analysis'",
    },
    description: {
      nl: "City-recipe: alle dagelijkse voorzieningen op de kaart, per adres het bereik binnen 15 minuten (met veilige routes), en servicedeserts als proactief signaal naar beleid.",
      en: "City recipe: all daily amenities on the map, per-address reach within 15 minutes (with safe routes), and service deserts as a proactive signal to policy.",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
  "min-04-hub-network": {
    title: {
      nl: "15-minutenstad MIN-04 — 'Hubnetwerk plannen'",
      en: "15-minute city MIN-04 — 'I want to plan my hub network'",
    },
    description: {
      nl: "City-recipe: behoefte per hubniveau (micro → wijk → stadsdeel → stad), een locatievoorstel met opbrengst, en het besluit samen met wijkbewoners en bestuur (mens).",
      en: "City recipe: demand per hub level (micro → neighbourhood → district → city), a siting proposal with yield, and the decision together with residents and governance (human).",
    },
    acceptance: {
      nl: "GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run",
      en: "GenAI testbank + function-baseline; deterministic replay via hcs-recipe-run",
    },
  },
};

const riskLabels = {
  low: { nl: "laag", en: "low" },
  medium: { nl: "middel", en: "medium" },
  high: { nl: "hoog", en: "high" },
};

const readinessLabels = {
  hybrid: { nl: "hybride", en: "hybrid" },
  mock: { nl: "mock", en: "mock" },
  live: { nl: "live", en: "live" },
};

export function recipeField(recipe, field, lang) {
  const loc = recipeLocales[recipe.id];
  if (loc && loc[field] && (loc[field][lang] || loc[field].nl)) {
    return loc[field][lang] || loc[field].nl;
  }
  return recipe[field] || "";
}

export function riskLabel(level, lang) {
  const key = String(level || "").toLowerCase();
  return (riskLabels[key] && (riskLabels[key][lang] || riskLabels[key].en)) || level || "";
}

export function readinessLabel(value, lang) {
  const key = String(value || "").toLowerCase();
  return (readinessLabels[key] && (readinessLabels[key][lang] || readinessLabels[key].en)) || value || "";
}
