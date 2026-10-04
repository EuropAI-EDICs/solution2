"""Deterministic PoC implementations of the planning-plane norm agents.

Implements MULTI_AGENT_PLAN.md section 3.2 agents #3 and #4:

* ``NormAnalyst``     — harvests NormCards from a corpus shard (evidence +
  sources). Deterministic by default; an optional ``llm_hook`` (callable)
  can be plugged in by a future deployment to refine English claims. With
  the default ``None`` the agent is fully deterministic, which is what the
  V3 semantic re-execution check relies on.
* ``NormFormalizer``  — converts NormCards into typed FormalRules using
  explicit deterministic templates per theme/card (zone inclusion in
  'Gebied windenergie', exclusion of Natura 2000/ganzenrustgebieden,
  1500 m stiltegebied attention buffer, Groene contour compensation, ...).
  Cards without a deterministic template are flagged ``ambiguous`` (or
  ``rejected``) with a reason — never guessed (cite-or-abstain).

There is NO callable LLM at PoC runtime: every step is a deterministic
implementation behind the agent interface, and every agent boundary emits
JSON validated against poc/schemas/*.schema.json (V0 gate).

Run ``python3 -m pipeline.agents`` (from poc/) to (re)generate the per-track
corpora poc/corpus/normcards-{wind,zon,bos}.json and formalrules-{wind,zon,bos}.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

try:  # normal import when poc/ is on sys.path (tests, python3 -m pipeline.agents)
    from pipeline import contracts
    from pipeline.contracts import FormalRule, NormCard
except ImportError:  # pragma: no cover - direct script execution inside poc/pipeline
    import contracts as contracts  # type: ignore[no-redef]
    from contracts import FormalRule, NormCard  # type: ignore[no-redef]

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus"
SOURCES_PATH = CORPUS_DIR / "sources.json"

#: a complete GIO JOIN-id as used in Bijlage II of CVDR704250
GIO_JOIN_RE = re.compile(
    r"/join/id/regdata/pv26/\d{4}/gio"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"/nld@\d{4}-\d{2}-\d{2};\d+"
)

ANALYST_RUN = "legal-recon-agent#cvdr704250-geldend-2025-10-13"
FORMALIZER_RUN = "norm-formalizer#deterministic-templates-v1"
RUN_DATE = "2026-08-30"

CAVEAT_GIO_ACCESS = (
    "GIO-versie overgenomen uit Bijlage II van CVDR704250 (geldend 13-10-2025); "
    "DSO Omgevingsdocumenten Downloaden API gaf HTTP 401 zonder API-key, dus de "
    "join-id is geciteerd uit de geconsolideerde regelingtekst (S07)"
)
CAVEAT_GIO_TRUNCATED = (
    "GIO staat in Bijlage II van CVDR704250 maar de join-id is slechts afgekapt "
    "overgenomen in de recon-notities; her-verifieer tegen Bijlage II voor V3"
)
#: water-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 2.14-2.16 quote no join-id),
#: so no gioJoinId may be claimed; geometry is served by the agrest IMOW
#: open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
CAVEAT_GIO_WATER = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json)"
)
#: bodem-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 3.7-3.10 and 3.108 quote no
#: join-id), so no gioJoinId may be claimed; geometry is served by the agrest
#: IMOW open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
#: The umbrella alias 'Grondwaterbeschermingszone' was live-verified (task 8)
#: as the exact union of the seven literal designation areas of art. 3.7/3.9/3.10.
CAVEAT_GIO_BODEM = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json): "
    "umbrella 'Grondwaterbeschermingszone', live geverifieerd als de vereniging van "
    "de zeven letterlijke aanwijzingsgebieden van art. 3.7/3.9/3.10 (taak-8-verslag)"
)

# ---------------------------------------------------------------------------
# Deterministic engine operations referenced by FormalRule.executableRef.
# Track B (zone engine) implements these; V3 re-executes them independently.
# ---------------------------------------------------------------------------

ENGINE_OPERATIONS: Dict[str, Dict[str, Any]] = {
    "engine.zone.within@poc-v1": {
        "deterministic": True,
        "description": "Select the part of the area of interest within the zone(s) named by the rule's zoneSelector.",
    },
    "engine.zone.exclude_within@poc-v1": {
        "deterministic": True,
        "description": "Remove from the area of interest everything within the zone(s) named by the rule's zoneSelector (difference).",
    },
    "engine.zone.buffer@poc-v1": {
        "deterministic": True,
        "description": "Buffer the derivedFrom zone by bufferDistanceM metres (EPSG:28992 metric) and select within it.",
    },
    "engine.compensation.ratio@poc-v1": {
        "deterministic": True,
        "description": "Do not eliminate area; attach a compensation requirement (ratio + within-zone) to affected parcels.",
    },
    "engine.procedural.human_review@poc-v1": {
        "deterministic": True,
        "description": "Mark the rule as requiring procedural/human assessment; contributes no geometry by itself.",
    },
    "engine.scope.none@poc-v1": {
        "deterministic": True,
        "description": "No-op: the card is declarative scope or a non-executable duplicate; contributes no geometry.",
    },
}

_REVIEW_REF = "engine.procedural.human_review@poc-v1"
_NOOP_REF = "engine.scope.none@poc-v1"

# ---------------------------------------------------------------------------
# Curated enrichment for the wind evidence shard (English claims, confidence,
# context tags, geo bindings). Keyed by evidence id from evidence-wind.json.
# This is the single source of truth: poc/corpus/normcards-wind.json is its
# deterministic replay (see main() and test_contracts.py).
# ---------------------------------------------------------------------------

EVIDENCE_ENRICHMENT: Dict[str, Dict[str, Any]] = {
    "W-01": {
        "claim": "Section 5.1 ('Wind, zon en biomassa') of the Omgevingsverordening applies to new functions for energy from wind, sun and biomass; it scopes all provincial energy-siting rules including every wind-turbine norm.",
        "contextTags": ["scope_afdeling_5_1", "new_energy_functions"],
    },
    "W-02": {
        "claim": "Article 5.2 lets an omgevingsplan allow urbanisation in the Landelijk gebied in deviation from art. 9.3 where needed to enable new energy functions or transformer stations: the gateway through the rural urbanisation prohibition that wind turbines (which count as urbanisation) must pass.",
        "contextTags": ["wind_turbines_are_urbanisation", "gateway_deviation_art_9_3"],
    },
    "W-03": {
        "claim": "Within the 'Gebied kleine windturbine' an omgevingsplan may contain rules allowing a wind turbine up to a hub height (ashoogte) of 20 metres, on condition that it is placed on or in connection with an existing building plot (bestaand bouwperceel).",
        "confidence": 0.95,
        "contextTags": ["ashoogte_le_20m", "on_or_adjacent_to_existing_building_plot"],
        "geoBinding": {
            "zoneIds": ["gebied_kleine_windturbine"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-04": {
        "claim": "In deviation from art. 5.3 first paragraph, an omgevingsplan may allow a wind turbine up to 30 m hub height where that is necessary to fully or almost fully meet the own energy demand of the existing buildings.",
        "contextTags": ["ashoogte_le_30m", "own_energy_demand_exception"],
    },
    "W-05": {
        "claim": "Within the 'Gebied windenergie' an omgevingsplan may contain rules allowing wind turbines of 3 MW or more, provided (a) they are erected in an environmentally fitting combination of multiple turbines (clustering) and (b) a removal duty after termination of the activity is provided.",
        "confidence": 0.95,
        "contextTags": ["capacity_ge_3mw", "clustering_of_multiple_turbines", "removal_duty_after_termination"],
        "geoBinding": {
            "zoneIds": ["gebied_windenergie"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-06": {
        "claim": "In deviation from art. 5.4 first paragraph, an omgevingsplan may allow wind turbines with a capacity below 3 MW within the Gebied windenergie, provided it is substantiated why turbines of 3 MW or more are not possible.",
        "contextTags": ["capacity_lt_3mw_deviation", "substantiation_required"],
    },
    "W-07": {
        "claim": "In deviation from art. 5.4 first paragraph, an omgevingsplan may allow a solitary wind turbine, provided it is substantiated why multiple turbines are not possible and that the energy yield of the solitary turbine outweighs its impact on the surroundings.",
        "contextTags": ["solitary_turbine_deviation", "substantiation_required"],
    },
    "W-08": {
        "claim": "The explanatory notes (toelichting) to art. 5.4 state that the article concerns the landelijk gebied excluding the Natura 2000 areas and the ganzenrustgebieden: the geographic reading that grounds zone elimination for wind turbines in those areas.",
        "confidence": 0.8,
        "contextTags": ["scope_landelijk_gebied", "exclusion_natura_2000", "exclusion_ganzenrustgebied"],
        "geoBinding": {
            "zoneIds": ["natura_2000", "ganzenrustgebied"],
            "geometrySource": "national_source",
            "caveat": "geen provinciale GIO in Bijlage II; geometrie moet uit nationale bronnen komen (geo-analyst, met provenance)",
        },
    },
    "W-09": {
        "claim": "The toelichting to art. 5.4 considers it important to test wind-turbine placement against the Rekenvoorschrift Omgevingsbeleid Module IV calculations and to consult the high-voltage grid operator, linking turbine siting to grid-capacity (congestion) considerations.",
        "confidence": 0.8,
        "contextTags": ["grid_congestion_check", "rekenvoorschrift_module_iv"],
    },
    "W-10": {
        "claim": "A Stiltegebied consists of the Gebied stille kern plus the Bufferzone stiltegebied, and the Aandachtsgebied stiltegebied is a zone of 1500 metres around a Stiltegebied (art. 9.25): a fully deterministic buffer geometry.",
        "confidence": 0.95,
        "contextTags": ["aandachtsgebied_buffer_1500m"],
        "geoBinding": {
            "zoneIds": ["stiltegebied", "gebied_stille_kern", "bufferzone_stiltegebied", "aandachtsgebied_stiltegebied"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_TRUNCATED,
        },
    },
    "W-11": {
        "claim": "Art. 9.26 sets noise targets for stiltegebieden: LAeq,24h of at most 40 dB(A) in the Gebied stille kern and preferably 40 but at most 45 dB(A) in the Bufferzone stiltegebied; these are the only provincial dB-values that can bear on wind turbines (via art. 9.27/9.28).",
        "contextTags": ["laeq_24h_40dba_stille_kern", "laeq_24h_45dba_bufferzone"],
    },
    "W-12": {
        "claim": "An omgevingsplan for locations within a Stiltegebied may contain rules allowing wind turbines only under the conditions of art. 9.28: regional coordination, fitting cluster placement, minimisation of effects on the Stiltegebied, alignment with the art. 9.26 noise objective, and a removal duty.",
        "contextTags": ["regionally_coordinated", "fitting_cluster_placement", "effects_minimised", "aligned_with_art_9_26_noise_objective", "removal_duty_after_termination"],
        "geoBinding": {
            "zoneIds": ["stiltegebied"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_TRUNCATED,
        },
    },
    "W-13": {
        "claim": "An omgevingsplan for locations within the Natuurnetwerk Nederland must contain rules for the protection, conservation, improvement and development of the quality, essential characteristics and values, and cohesion of the NNN (art. 6.2).",
        "contextTags": ["nnn_protection_instruction"],
        "geoBinding": {
            "zoneIds": ["natuurnetwerk_nederland"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio3111b509-00cb-46c0-9967-b8102f81c85f/nld@2025-08-18;803",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-14": {
        "claim": "An omgevingsplan for locations within the Natuurnetwerk Nederland must not contain rules allowing activities that may adversely affect the essential characteristics and values of the NNN or reduce its quality, area or cohesion (art. 6.3): the operative basis for zone elimination, subject to the statutory exceptions in its second paragraph.",
        "contextTags": ["nnn_no_adverse_activities", "exceptions_lid_2_discretionary"],
        "geoBinding": {
            "zoneIds": ["natuurnetwerk_nederland"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio3111b509-00cb-46c0-9967-b8102f81c85f/nld@2025-08-18;803",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-15": {
        "claim": "Within the Groene contour an omgevingsplan may not allow activities that limit the possibilities to realise new nature (art. 6.5); because wind turbines count as urbanisation, placing them inside the contour requires compensation with new nature of at least 1:1 within the contour.",
        "contextTags": ["wind_turbines_are_urbanisation", "compensation_min_1_to_1_within_contour"],
        "geoBinding": {
            "zoneIds": ["groene_contour"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-16": {
        "claim": "Within the Weidevogelkerngebied an omgevingsplan may allow new developments only on condition that the quality of the meadow-bird habitat is demonstrably preserved at minimum on balance (art. 6.7); the toelichting names wind turbines explicitly as a potentially negative development.",
        "contextTags": ["meadow_bird_habitat_quality_on_balance"],
        "geoBinding": {
            "zoneIds": ["weidevogelkerngebied"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_TRUNCATED,
        },
    },
    "W-17": {
        "claim": "Afdeling 5.3 (art. 5.10/5.11) subjects new functions that can overload the electricity infrastructure to an energy test: connection capacity (aansluitbaarheid) must be taken into account, including an inventariserend overleg with the grid operator.",
        "contextTags": ["energy_test", "grid_connection_capacity", "inventariserend_overleg"],
    },
    "W-18": {
        "claim": "Within the Gebied UNESCO Werelderfgoed Hollandse Waterlinies an omgevingsplan must take the outstanding universal value into account and contain no rules allowing activities that damage that value (art. 7.3).",
        "contextTags": ["unesco_ouv_protection"],
        "geoBinding": {
            "zoneIds": ["gebied_unesco_hollandse_waterlinies"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_TRUNCATED,
        },
    },
    "W-19": {
        "claim": "Within a Landschap an omgevingsplan must contain rules protecting the applicable kernkwaliteiten and no rules allowing new activities that disproportionately damage those kernkwaliteiten (art. 7.11a; five landscapes per art. 7.11, qualities in Bijlage XVI).",
        "contextTags": ["landscape_core_qualities", "open_norm_onevenredig_aantasten"],
    },
    "W-20": {
        "claim": "Within the six groundwater-related zones (waterwingebied, grondwaterbeschermingsgebied, boringsvrije zone, beschermingszone oppervlaktewaterwinning, 100-jaarsaandachtsgebied, gebied kwetsbare strategische grondwatervoorraad) an omgevingsplan allows no activities that pose a risk to water abstraction for human consumption (art. 3.7).",
        "contextTags": ["groundwater_protection_zones_six"],
        "geoBinding": {
            "zoneIds": [
                "waterwingebied",
                "grondwaterbeschermingsgebied",
                "boringsvrije_zone",
                "beschermingszone_oppervlaktewaterwinning",
                "honderd_jaars_aandachtsgebied",
                "gebied_kwetsbare_strategische_grondwatervoorraad",
            ],
            "geometrySource": "provincial_gio_unverified",
            "caveat": "zes GIO's per Bijlage II van CVDR704250; join-ids niet vastgelegd in de recon",
        },
    },
    "W-21": {
        "claim": "The province consists of the Landelijk gebied and the Stedelijk gebied (art. 9.2); an omgevingsplan for the Landelijk gebied allows no urbanisation unless the verordening provides otherwise (art. 9.3), and the toelichting to art. 5.4 states the verordening contains no provisions for wind energy in the stedelijk gebied.",
        "contextTags": ["no_wind_provisions_for_stedelijk_gebied", "urbanisation_prohibition_art_9_3"],
        "geoBinding": {
            "zoneIds": ["landelijk_gebied"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio17d47ef4-f140-45b7-8809-c5068d74698f/nld@2025-10-10;843",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "W-22": {
        "claim": "The (non-binding) Omgevingsvisie 2021 excludes wind energy and solar fields in the Natura 2000 areas and the ganzenrustgebieden.",
        "confidence": 0.7,
        "contextTags": ["exclusion_natura_2000", "exclusion_ganzenrustgebied"],
        "geoBinding": {
            "zoneIds": ["natura_2000", "ganzenrustgebied"],
            "geometrySource": "national_source",
            "caveat": "visie-uitsluiting zonder provinciale GIO; nationale geometrie vereist (geo-analyst)",
        },
    },
    "W-23": {
        "claim": "The (non-binding) Omgevingsvisie 2021 strives, for 2030, towards meeting the WHO advisory values for wind-turbine noise at homes and other noise-sensitive buildings, in addition to the statutory requirements.",
        "confidence": 0.7,
        "contextTags": ["who_advisory_values_2030"],
    },
    "W-24": {
        "claim": "The (non-binding) Omgevingsvisie 2021 states the province in principle does not facilitate turbines from 20 metres up with an installed capacity below 3 MW, because their impact is too large relative to the limited societal return; it includes the 2019 map of placement possibilities for turbines from 3 MW.",
        "confidence": 0.7,
        "contextTags": ["no_facilitation_ge_20m_lt_3mw", "placement_map_2019"],
    },
    # -- ZON track (solar fields; shard evidence-zon.json) --------------------
    "Z-01": {
        "objectType": "solar_field",
        "claim": "A 'zonneveld' (Bijlage I) is any grouping of solar panels placed on or above the ground or on the water surface, but not on roofs of buildings: the object definition that scopes the ZON use case to ground- and water-mounted solar fields and excludes rooftop installations.",
        "contextTags": ["definition_zonneveld", "ground_or_water_mounted", "rooftop_out_of_scope"],
    },
    "Z-02": {
        "objectType": "solar_field",
        "claim": "Within the 'Gebied zonneveld' an omgevingsplan may contain rules allowing the realisation of solar-energy generation by means of zonnevelden, provided (a) the structures in the landscape remain recognisable and good landscape integration is provided, (b) the panels are arranged so as to allow soil and water quality fitting the area, and (c) a removal duty after termination of the activity is provided.",
        "confidence": 0.95,
        "contextTags": ["inclusion_zone_gebied_zonneveld", "landscape_integration_required", "soil_water_quality_fitting_area", "removal_duty_after_termination"],
        "geoBinding": {
            "zoneIds": ["gebied_zonneveld"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gioa748cb8c-4f7f-4bbb-83d4-54becd3e0d1d/nld@2025-10-10;849",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "Z-03": {
        "objectType": "solar_field",
        "claim": "The explanatory notes (toelichting) to art. 5.5 state that the verordening contains no provisions for solar energy in the stedelijk gebied and that the article concerns the landelijk gebied excluding the Natura 2000 areas and the ganzenrustgebieden: the geographic reading that grounds zone elimination for zonnevelden in those areas.",
        "confidence": 0.8,
        "contextTags": ["scope_landelijk_gebied", "no_zon_provisions_for_stedelijk_gebied", "exclusion_natura_2000", "exclusion_ganzenrustgebied"],
        "geoBinding": {
            "zoneIds": ["natura_2000", "ganzenrustgebied"],
            "geometrySource": "national_source",
            "caveat": "geen provinciale GIO in Bijlage II; geometrie moet uit nationale bronnen komen (geo-analyst, met provenance)",
        },
    },
    "Z-04": {
        "objectType": "solar_field",
        "claim": "Art. 6.5a third paragraph deviates from its second paragraph for the realisation of new nature as compensation for the placement of a zonneveld: the management measures must be executed at the latest 25 years after placement of the solar panels — zonnevelden inside the Groene contour are thereby implicitly temporary (deviating from the 3-year term of the second paragraph).",
        "confidence": 0.95,
        "contextTags": ["compensation_within_groene_contour", "zonneveld_implicitly_temporary", "compensation_deadline_25_years"],
        "geoBinding": {
            "zoneIds": ["groene_contour"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "Z-05": {
        "objectType": "solar_field",
        "claim": "The (non-binding) Omgevingsvisie 2021 finds wind turbines and zonnevelden in the stedelijk gebied admissible and formulates no further rules for them, with a preference for placing solar panels on roofs and for siting zonnevelden and turbines on or near industrial estates.",
        "confidence": 0.7,
        "contextTags": ["stedelijk_gebied_toelaatbaar_visie", "preference_roofs_facades_infrastructure", "preference_industrial_estates"],
    },
    # -- BOS track (new nature / forest planting; shard evidence-bos.json) ----
    "B-01": {
        "objectType": "forest_planting",
        "claim": "An omgevingsplan for locations within the Groene contour must contain rules that protect and create the possibilities to realise new nature on the grounds within the Groene contour (art. 6.4): the contour is the provincial search area for new nature, including forest planting through voluntary conversion, with realised nature added to the Natuurnetwerk Nederland.",
        "confidence": 0.9,
        "contextTags": ["zoekgebied_nieuwe_natuur", "inclusion_zone_groene_contour", "vrijwillige_omvorming", "nnn_addition_after_realisation"],
        "geoBinding": {
            "zoneIds": ["groene_contour"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "B-02": {
        "objectType": "forest_planting",
        "claim": "The remaining loss of possibilities to realise new nature must be compensated by realising new nature within the Groene contour with an area of at least the area of the loss (art. 6.5 second paragraph, under d): a deterministic minimum 1:1 compensation ratio inside the contour; deviation from the protective first paragraph is only possible for great public interest without real alternatives.",
        "confidence": 0.95,
        "contextTags": ["compensation_min_1_to_1_within_contour", "deviation_only_great_public_interest"],
        "geoBinding": {
            "zoneIds": ["groene_contour"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "B-03": {
        "objectType": "forest_planting",
        "claim": "An omgevingsplan for locations within the 'Waardevolle Houtopstanden - oude bosgroeiplaatsen' must contain rules for the protection and conservation of the values present at the location of those old forest growth sites (art. 6.13): new forest/nature development inside these zones is conditional on protecting the existing old-forest values.",
        "confidence": 0.95,
        "contextTags": ["oude_bosgroeiplaatsen_protection_instruction", "existing_values_protection"],
        "geoBinding": {
            "zoneIds": ["oude_bosgroeiplaatsen"],
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio3940cf76-bee0-4a1a-8d51-aa0d49be7153/nld@2025-10-10;842",
            "caveat": CAVEAT_GIO_ACCESS,
        },
    },
    "B-04": {
        "objectType": "forest_planting",
        "claim": "Within the Gebied houtopstand, making rejuvenation gaps is exempt from the national velling-reporting duty provided the gaps are not larger than 10 are, jointly cover at most 10% of the forest parcel, occur at most once per 4 years at the same location, and serve sustainable forest management (art. 6.15, under a).",
        "confidence": 0.95,
        "contextTags": ["vellingsmelding_exemption", "verjongingsgaten_max_10_are", "max_10pct_of_parcel", "max_once_per_4_years", "duurzaam_bosbeheer"],
    },
    "B-05": {
        "objectType": "forest_planting",
        "claim": "The (non-binding) Omgevingsvisie 2021 aims to realise 3,000 hectares of new nature within the Groene contour by 2040, ecologically connecting large nature units, and explicitly investigates opportunities for expanding woodstands that contribute to CO2 reduction: it quantifies the bos/nature task but adds no siting rule.",
        "confidence": 0.7,
        "contextTags": ["ambition_3000ha_new_nature_by_2040", "woodstand_expansion_for_co2"],
    },
    # -- WATER track (riparian development; shard evidence-water.json) --------
    "WA-01": {
        "objectType": "riparian_development",
        "claim": "An omgevingsplan for locations within the 'Vrijwaringszone regionale waterkering' must contain rules that protect the water-retaining function (waterkerende functie) and provide for a vrijwaringszone on both sides of the waterkering (art. 2.14): riparian development inside the zone is conditional on such protective plan rules.",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_2_14", "conditional_vrijwaringszone_waterkering", "waterkerende_functie_beschermen", "vrijwaringszone_weerszijden_waterkering"],
        "geoBinding": {
            "zoneIds": ["vrijwaringszone_waterkering"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_WATER,
        },
    },
    "WA-02": {
        "objectType": "riparian_development",
        "claim": "An omgevingsplan for locations within the 'Waterbergingsgebied' must contain no rules allowing developments in the physical living environment that conflict with the water-storage function (waterbergingsfunctie), unless those developments take place on the basis of existing expansion rights at the location of the already present functions (art. 2.15): the operative zone exclusion for riparian development, with an existing-rights exception.",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_2_15", "exclusion_waterbergingsgebied", "bestaande_uitbreidingsrechten_exception"],
        "geoBinding": {
            "zoneIds": ["waterbergingsgebied"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_WATER,
        },
    },
    "WA-03": {
        "objectType": "riparian_development",
        "claim": "An omgevingsplan for locations within the 'Overstroombaar gebied' must contain rules that take flood risks into account (art. 2.16): binnendijks this applies to vulnerable and vital objects, residential quarters and industrial estates, buitendijks also to individual homes and businesses — a conditional zone requirement differentiated by dyk-side and object type.",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_2_16", "conditional_overstroombaar_gebied", "binnendijks_kwetsbaar_vitaal_woonwijken_bedrijventerreinen", "buitendijks_ook_individuele_woningen_bedrijven"],
        "geoBinding": {
            "zoneIds": ["overstroombaar_gebied"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_WATER,
        },
    },
    # -- BODEM track (soil activity; shard evidence-bodem.json) -----------------
    "BO-01": {
        "objectType": "soil_activity",
        "claim": "An omgevingsplan for locations within a Waterwingebied, Grondwaterbeschermingsgebied, Boringsvrije zone, Beschermingszone oppervlaktewaterwinning, 100-jaarsaandachtsgebied or Gebied kwetsbare strategische grondwatervoorraad allows no activities that pose a risk to the groundwater and surface-water abstraction for human consumption (art. 3.7): soil-affecting activity inside these six designated protection zones is conditional on the plan refusing risky activities — the umbrella zone alias conservatively covers the union of the designation areas (superset per article).",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_3_7", "geen_risico_activiteiten_winning_menselijke_consumptie", "zes_aanwijzingsgebieden_letterlijk", "exclusion_family_non_permission", "umbrella_superset_conservatief"],
        "geoBinding": {
            "zoneIds": ["grondwater_beschermingszone"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_BODEM,
        },
    },
    "BO-02": {
        "objectType": "soil_activity",
        "claim": "An omgevingsplan for locations within the 'Waterwingebied Bethunepolder' must contain rules that protect the water-abstraction interest for the parking of motor vehicles and must, notably in busy periods of summer or winter recreation, allow parking only on locations explicitly designated for that purpose (art. 3.8): a zone-bound parking instruction whose literal designation has no registered open-data alias and whose predicate is object-specific (parking arrangements), so it is carried without a geo binding, routed to V4.",
        "confidence": 0.9,
        "contextTags": ["instructieregel_art_3_8", "waterwingebied_bethunepolder_parkeren", "geen_alias_geregistreerd", "v4_human_review"],
    },
    "BO-03": {
        "objectType": "soil_activity",
        "claim": "An omgevingsplan for locations within a Waterwingebied or Grondwaterbeschermingsgebied forbids the establishment of a new cemetery or scattering field (Wet op de lijkbezorging art. 66a/66b) or an animal cemetery (art. 3.9): soil-invasive new burial facilities inside the protection zones are prohibited outright, with rules for having or extending existing facilities following in its second paragraph — bound to the umbrella zone alias as a conservative superset (superset per article).",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_3_9", "verbod_nieuwe_begraafplaats_uitstrooiveld_dierenbegraafplaats", "nieuw_versus_bestaand", "exclusion_family_verbod", "umbrella_superset_conservatief"],
        "geoBinding": {
            "zoneIds": ["grondwater_beschermingszone"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_BODEM,
        },
    },
    "BO-04": {
        "objectType": "soil_activity",
        "claim": "An omgevingsplan for locations within the 'Gebied matig kwetsbare strategische grondwatervoorraad' must take the protection of the quality of the groundwater for abstraction for human consumption into account (art. 3.10): the weakest variant of the instructieregel family (a take-into-account duty, mirroring art. 2.16 for water) — a conditional marker inside the umbrella zone alias, which conservatively covers the matig-kwetsbare designation as part of the verified union.",
        "confidence": 0.95,
        "contextTags": ["instructieregel_art_3_10", "rekening_houden_grondwaterkwaliteit", "matig_kwetsbare_strategische_grondwatervoorraad", "conditional_marker_binnen_umbrella", "umbrella_superset_conservatief"],
        "geoBinding": {
            "zoneIds": ["grondwater_beschermingszone"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_BODEM,
        },
    },
    "BO-05": {
        "objectType": "soil_activity",
        "claim": "An omgevingsplan activity taking place in the 'Gebied gesloten stortplaats' is an omgevingsplan activity of provincial importance (art. 3.108): an unconditional designation rule that routes jurisdiction to the province — which can thereby determine whether activities on the closed landfill can take place (soil protection when opening the landfill) — carried as a context marker, never an elimination.",
        "confidence": 0.95,
        "contextTags": ["aanwijzingsregel_art_3_108", "omgevingsplanactiviteit_provinciaal_belang", "provincial_jurisdiction_marker", "bodembescherming_bij_openen_stortplaats"],
        "geoBinding": {
            "zoneIds": ["gesloten_stortplaats"],
            "geometrySource": "provincial_gio_unverified",
            "caveat": CAVEAT_GIO_BODEM,
        },
    },
}


def _detect_legal_force(instrument: str) -> str:
    """Deterministically derive legal force from the instrument description."""
    lowered = (instrument or "").lower()
    if "niet-bindende" in lowered or "niet bindende" in lowered:
        return "non_binding"
    if "toelichting" in lowered and "artikeltekst" not in lowered:
        return "interpretive"
    return "binding"


def _default_confidence(legal_force: str) -> float:
    return {"binding": 0.9, "interpretive": 0.8, "non_binding": 0.7}[legal_force]


# ---------------------------------------------------------------------------
# Norm Analyst (plan section 3.2, agent #3)
# ---------------------------------------------------------------------------

class NormAnalyst:
    """Reads a corpus shard (evidence + sources) and emits schema-validated NormCards.

    Deterministic mode (default, ``llm_hook=None``): cards are built from the
    evidence records plus the curated EVIDENCE_ENRICHMENT table; cite-or-abstain
    is enforced by dropping every evidence item whose ``verified`` flag is not
    true (recorded in ``self.rejected`` with a reason).

    ``llm_hook`` (optional): ``callable(evidence: dict, source: dict) -> dict``
    returning e.g. ``{"claim": ..., "confidence": 0.9}``. Proposals are only
    allowed to refine the English claim/confidence — never the citation, legal
    force or geo binding — and the resulting card is still schema-validated.
    """

    agent_name = "legal-recon-agent"

    def __init__(
        self,
        corpus_dir: Optional[Path] = None,
        llm_hook: Optional[Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]] = None,
        run_ref: str = ANALYST_RUN,
    ) -> None:
        self.corpus_dir = Path(corpus_dir) if corpus_dir else CORPUS_DIR
        self.llm_hook = llm_hook
        self.run_ref = run_ref
        self.rejected: List[Dict[str, Any]] = []

    # -- shard loading ------------------------------------------------------

    def _load_sources(self) -> Dict[str, Dict[str, Any]]:
        with (self.corpus_dir / "sources.json").open(encoding="utf-8") as fh:
            return {src["id"]: src for src in json.load(fh)}

    def _load_shard(
        self, shard: Union[str, Path, Sequence[Mapping[str, Any]], Mapping[str, Any]]
    ) -> List[Dict[str, Any]]:
        if isinstance(shard, (str, Path)):
            path = Path(shard)
            if not path.is_absolute():
                path = self.corpus_dir / path
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = shard
        if isinstance(data, Mapping):
            return list(data.get("evidence", []))
        if isinstance(data, Sequence):
            return [dict(item) for item in data]
        raise ValueError(f"unsupported shard type: {type(data).__name__}")

    # -- card building ------------------------------------------------------

    def _fallback_claim(self, ev: Mapping[str, Any]) -> str:
        return (
            f"Deterministic fallback claim: article '{ev.get('article', '?')}' of "
            f"{ev.get('instrument', 'the instrument')} — see the verbatim Dutch quote "
            f"and recon notes; no curated English summary is registered for this evidence id."
        )

    def _to_card(self, ev: Mapping[str, Any], src: Mapping[str, Any]) -> NormCard:
        ev_id = ev["id"]
        enrichment = EVIDENCE_ENRICHMENT.get(ev_id, {})
        instrument = ev.get("instrument", "")
        legal_force = enrichment.get("legalForce") or _detect_legal_force(instrument)
        confidence = float(enrichment.get("confidence", _default_confidence(legal_force)))
        claim = enrichment.get("claim") or self._fallback_claim(ev)
        notes = ev.get("notes")
        extracted_by = self.run_ref

        if self.llm_hook is not None:
            proposal = self.llm_hook(ev, src) or {}
            if proposal.get("claim"):
                claim = str(proposal["claim"])
            if "confidence" in proposal:
                confidence = float(proposal["confidence"])
            # S1 seam stamps identity; the deterministic citation/legal-force/
            # geo-binding fields above are unreachable for the hook by design.
            stamp = getattr(self.llm_hook, "stamp", None)
            if proposal and stamp:
                agent, _, _version = self.run_ref.partition("#")
                extracted_by = f"{agent}#{stamp}"
            seam_bits = []
            if proposal.get("notes"):
                seam_bits.append(str(proposal["notes"]))
            seam_bits.append(
                "llm hook answered (claim/confidence refined)"
                if proposal else "llm hook declined; deterministic replay used"
            )
            notes = ((notes.rstrip(". ") + ". ") if notes else "") + " S1 seam: " + "; ".join(seam_bits) + "."

        card_payload: Dict[str, Any] = {
            "id": f"NC-{ev_id}",
            "evidenceId": ev_id,
            "claim": claim,
            "source": {
                "docId": ev.get("sourceId"),
                "article": ev.get("article"),
                "version": src.get("version"),
                "quote": ev.get("quote_nl"),
                "quoteLanguage": "nl",
                "uri": ev.get("url") or src.get("url"),
                "retrievedAt": src.get("retrieved_at"),
            },
            "instrument": instrument,
            "legalForce": legal_force,
            "theme": ev.get("theme"),
            "confidence": confidence,
            "verified": True,
            "extractedBy": extracted_by,
            "extractedAt": RUN_DATE,
            "appliesTo": {
                "objectType": enrichment.get("objectType", "wind_turbine"),
                "contextTags": enrichment.get("contextTags"),
            },
            "geoBinding": enrichment.get("geoBinding"),
            "notes": notes,
        }
        return NormCard.from_dict(card_payload)  # validates against norm-card.schema.json

    # -- public interface ----------------------------------------------------

    def read(
        self,
        shard: Union[str, Path, Sequence[Mapping[str, Any]], Mapping[str, Any]],
    ) -> List[NormCard]:
        """Harvest NormCards from ``shard``.

        ``shard`` may be: a path to an evidence-*.json file (relative paths
        resolve against the corpus dir), a list of evidence dicts, or a dict
        ``{"evidence": [...], "sources": {...}}``.
        """
        self.rejected = []
        evidence_list = self._load_shard(shard)
        sources = self._load_sources()
        if isinstance(shard, Mapping) and shard.get("sources"):
            extra_sources = shard["sources"]
            if isinstance(extra_sources, Mapping):
                sources.update(dict(extra_sources))
            else:
                sources.update({s["id"]: s for s in extra_sources})

        cards: List[NormCard] = []
        for ev in evidence_list:
            if ev.get("verified") is not True:
                self.rejected.append(
                    {
                        "evidenceId": ev.get("id"),
                        "theme": ev.get("theme"),
                        "article": ev.get("article"),
                        "reason": (
                            "evidence.verified is not true — cite-or-abstain: no NormCard "
                            "without a verified, verbatim citation (docId+article+version+quote+uri)"
                        ),
                    }
                )
                continue
            src = sources.get(ev.get("sourceId", ""), {})
            cards.append(self._to_card(ev, src))
        return cards


# ---------------------------------------------------------------------------
# Norm Formalizer (plan section 3.2, agent #4) — deterministic templates
# ---------------------------------------------------------------------------

def _base_rule(
    card: NormCard,
    *,
    status: str,
    rule_type: str,
    zone_semantics: str,
    executable_ref: str,
    extra_tags: Sequence[str] = (),
    reason: Optional[str] = None,
    rationale: Optional[str] = None,
    zone_selector: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    related: Optional[List[str]] = None,
) -> Dict[str, Any]:
    tags = list(card.appliesTo.contextTags or [])
    for tag in extra_tags:
        if tag not in tags:
            tags.append(tag)
    rule: Dict[str, Any] = {
        "id": f"FR-{card.evidenceId}",
        "normCardId": card.id,
        "status": status,
        "ruleType": rule_type,
        "zoneSemantics": zone_semantics,
        "appliesTo": {"objectType": card.appliesTo.objectType, "contextTags": tags},
        "executableRef": executable_ref,
        "formalizedBy": FORMALIZER_RUN,
        "formalizedAt": RUN_DATE,
    }
    if zone_selector is not None:
        rule["zoneSelector"] = zone_selector
    if conditions is not None:
        rule["conditions"] = conditions
    if related:
        rule["relatedNormCardIds"] = related
    if reason is not None:
        rule["reason"] = reason
    if rationale is not None:
        rule["rationale"] = rationale
    return rule


_NNN_GIO = "/join/id/regdata/pv26/2025/gio3111b509-00cb-46c0-9967-b8102f81c85f/nld@2025-08-18;803"
_GROENE_CONTOUR_GIO = "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798"
_GEBIED_WINDENERGIE_GIO = "/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846"
_GEBIED_KLEINE_WIND_GIO = "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822"
_LANDELIJK_GEBIED_GIO = "/join/id/regdata/pv26/2025/gio17d47ef4-f140-45b7-8809-c5068d74698f/nld@2025-10-10;843"
_GEBIED_ZONNEVELD_GIO = "/join/id/regdata/pv26/2025/gioa748cb8c-4f7f-4bbb-83d4-54becd3e0d1d/nld@2025-10-10;849"
_OUDE_BOSGROEIPLAATSEN_GIO = "/join/id/regdata/pv26/2025/gio3940cf76-bee0-4a1a-8d51-aa0d49be7153/nld@2025-10-10;842"

#: deterministic templates, keyed by evidence id. kind:
#: inclusion | exclusion | attention | conditional | compensation | ambiguous | reject
TEMPLATE_SPECS: Dict[str, Dict[str, Any]] = {
    "W-01": {
        "kind": "reject",
        "rule_type": "scope_declaration",
        "reason": "Declarative scope of Afdeling 5.1 (wind, zon en biomassa); carries no zone or threshold semantics to execute.",
        "rationale": "Card retained for provenance: the operational wind norms are art. 5.3/5.4 (see FR-W-03 and FR-W-05), so this card yields no independent rule.",
        "executable_ref": _NOOP_REF,
    },
    "W-02": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Procedural gateway (deviation from the art. 9.3 urbanisation prohibition) that is exercised through the specific energy articles; no independent spatial predicate exists.",
        "rationale": "Art. 5.2 opens the rural urbanisation prohibition for energy functions; for wind turbines the operative gates are art. 5.3/5.4, formalized separately. Guessing an extra predicate here would double-count the gateway.",
        "executable_ref": _REVIEW_REF,
    },
    "W-03": {
        "kind": "inclusion",
        "zone": {"zoneIds": ["gebied_kleine_windturbine"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GEBIED_KLEINE_WIND_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [
            {"parameter": "hub_height", "operator": "<=", "value": 20, "unit": "m"},
            {"parameter": "location", "operator": "==", "value": "existing_building_plot"},
        ],
        "extra_tags": ["inclusion_zone_gebied_kleine_windturbine"],
        "rationale": "Art. 5.3 lid 1 permits, within the 'Gebied kleine windturbine' (GIO Bijlage II), rules allowing a turbine up to 20 m hub height on/at an existing building plot; both the zone and both conditions are quoted verbatim in NC-W-03.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "W-04": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Exception path to 30 m hub height requires substantiation of (near-)self-sufficiency of the existing buildings' energy demand — a case-specific assessment the deterministic engine must not guess.",
        "rationale": "Art. 5.3 lid 2 'als dat noodzakelijk is om volledig of bijna volledig in eigen energiebehoefte te voorzien' is a motivational test on facts outside the corpus; flagged for human/procedural review.",
        "executable_ref": _REVIEW_REF,
    },
    "W-05": {
        "kind": "inclusion",
        "zone": {"zoneIds": ["gebied_windenergie"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GEBIED_WINDENERGIE_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [
            {"parameter": "capacity", "operator": ">=", "value": 3, "unit": "MW"},
        ],
        "extra_tags": ["inclusion_zone_gebied_windenergie", "clustering_required", "removal_duty_required"],
        "rationale": "CORE WIND RULE. Art. 5.4 lid 1 permits, within the 'Gebied windenergie' (GIO Bijlage II), turbines of >= 3 MW when clustered in a fitting combination and with a removal duty; the numeric threshold and zone are quoted verbatim, the clustering/removal duties are carried as procedural context tags.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "W-06": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Deviation path for < 3 MW requires substantiation why >= 3 MW turbines are not possible; a discretionary assessment without a deterministic predicate.",
        "rationale": "Art. 5.4 lid 2 is an explicitly motivated deviation from the >= 3 MW rule of FR-W-05; the engine keeps FR-W-05 as the only deterministic inclusion for large turbines.",
        "executable_ref": _REVIEW_REF,
    },
    "W-07": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Solitary-turbine deviation requires substantiation both of clustering impossibility and of yield-versus-impact; discretionary, no deterministic predicate.",
        "rationale": "Art. 5.4 lid 3 overrides the clustering preference of lid 1 under a; without a case file the engine cannot evaluate the substantiation, so it is never guessed.",
        "executable_ref": _REVIEW_REF,
    },
    "W-08": {
        "kind": "exclusion",
        "zone": {"zoneIds": ["natura_2000", "ganzenrustgebied"], "selection": "within", "geometrySource": "national_source", "caveat": "exclusion grounded in the toelichting on art. 5.4 (interpretive) + Omgevingsvisie 2021 (non-binding); no provincial GIO exists — geo analyst must attach national geometry with provenance"},
        "conditions": [],
        "extra_tags": ["exclusion_natura_2000", "exclusion_ganzenrustgebied"],
        "related": ["NC-W-22"],
        "rationale": "The toelichting to art. 5.4 restricts the article to the landelijk gebied 'met uitzondering van de Natura 2000-gebieden en de ganzenrustgebieden'; the Omgevingsvisie (NC-W-22) states the same exclusion as policy. Geometry must come from national sources because no provincial GIO covers these areas.",
        "executable_ref": "engine.zone.exclude_within@poc-v1",
    },
    "W-09": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Grid-capacity consultation (Rekenvoorschrift Omgevingsbeleid Module IV, high-voltage grid operator) is procedural and data-dependent; no deterministic predicate without grid data.",
        "rationale": "Toelichting on art. 5.4 ties turbine siting to supply-security calculations and TenneT consultation; the PoC has no grid-capacity dataset, so the congestion check (paper-B use case) is flagged rather than guessed.",
        "executable_ref": _REVIEW_REF,
    },
    "W-10": {
        "kind": "attention",
        "zone": {
            "zoneIds": ["aandachtsgebied_stiltegebied"],
            "selection": "within",
            "geometrySource": "derived",
            "derivedFrom": "stiltegebied",
            "bufferDistanceM": 1500,
            "caveat": "art. 9.25 lid 2 defines the Aandachtsgebied as a 1500 m zone around a Stiltegebied; the Stiltegebied GIO join-ids still need re-verification against Bijlage II (truncated in recon notes)",
        },
        "conditions": [
            {"parameter": "buffer_distance", "operator": "==", "value": 1500, "unit": "m"},
        ],
        "extra_tags": ["attention_zone_aandachtsgebied_stiltegebied"],
        "rationale": "Art. 9.25 gives a fully deterministic geometry: buffer the Stiltegebied by 1500 m (EPSG:28992). The zone is an attention zone (toetsingskader for art. 9.27/9.28), not a blanket exclusion.",
        "executable_ref": "engine.zone.buffer@poc-v1",
    },
    "W-11": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "Art. 9.26 states LAeq,24h targets for stiltegebieden as such; applying them to a specific turbine requires an acoustic emission model and source data — no deterministic predicate. General wind-turbine noise limits are national law (Wgh/Bal) and were abstained from.",
        "rationale": "The 40/45 dB(A) doelstellingen are quoted verbatim, but a dB value cannot be turned into a contour without turbine emission data; inventing one would violate cite-or-abstain.",
        "executable_ref": _REVIEW_REF,
    },
    "W-12": {
        "kind": "conditional",
        "zone": {"zoneIds": ["stiltegebied"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_TRUNCATED},
        "conditions": [],
        "extra_tags": ["conditional_inclusion_within_stiltegebied", "regionally_coordinated", "removal_duty_required"],
        "rationale": "Art. 9.28 lid 1 allows wind turbines within a Stiltegebied only under its five conditions (regional coordination, fitting clustering, effect minimisation, alignment with the art. 9.26 objective, removal duty). The zone overlay is deterministic; the conditions are procedural and are marked for human assessment (V4), not guessed.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "W-13": {
        "kind": "conditional",
        "zone": {"zoneIds": ["natuurnetwerk_nederland"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _NNN_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["nnn_quality_overlay"],
        "rationale": "Art. 6.2 lid 1 is an instructieregel directing omgevingsplannen to protect and develop the NNN; formalized as a conditional overlay on the NNN GIO. The operative prohibition is FR-W-14.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "W-14": {
        "kind": "exclusion",
        "zone": {"zoneIds": ["natuurnetwerk_nederland"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _NNN_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["exclusion_natuurnetwerk_nederland", "lid_2_exceptions_discretionary"],
        "rationale": "Art. 6.3 lid 1 forbids omgevingsplan rules allowing activities with adverse effects on the NNN's essential characteristics/values or its quality, area or cohesion — the operative basis for zone elimination. Lid 2 exceptions (great public interest, meerwaardebenadering, beperkte wijziging) are discretionary and always require compensation; the deterministic engine applies the default exclusion.",
        "executable_ref": "engine.zone.exclude_within@poc-v1",
    },
    "W-15": {
        "kind": "compensation",
        "zone": {"zoneIds": ["groene_contour"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GROENE_CONTOUR_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [
            {"parameter": "compensation_ratio_new_nature", "operator": ">=", "value": 1, "unit": "ratio"},
        ],
        "extra_tags": ["compensation_within_groene_contour"],
        "rationale": "Art. 6.5 lid 1 forbids limiting new-nature possibilities inside the Groene contour; lid 2 under d requires >= 1:1 compensation with new nature within the contour, and the toelichting states that wind turbines placed inside the contour trigger this. Not an elimination: an obligation attached to affected parcels.",
        "executable_ref": "engine.compensation.ratio@poc-v1",
    },
    "W-16": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "Art. 6.7 conditions development on demonstrable preservation of meadow-bird habitat quality 'per saldo' — an ecological assessment requiring field data; not deterministic.",
        "rationale": "The Weidevogelkerngebied zone is GIO-bounded, but the predicate is an ecological on-balance test the PoC cannot execute; flagged for expert assessment.",
        "executable_ref": _REVIEW_REF,
    },
    "W-17": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "The energy test (art. 5.10/5.11) depends on grid-capacity data and an inventariserend overleg with the grid operator; no deterministic predicate exists in the PoC.",
        "rationale": "Afdeling 5.3's aansluitbaarheid check is procedural; linking it to the paper-B congestion use case requires a grid dataset the corpus does not contain.",
        "executable_ref": _REVIEW_REF,
    },
    "W-18": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "UNESCO protection is qualitative: 'aantasten' of the outstanding universal value must be assessed against kernkwaliteiten (Bijlage XV) and gebiedsanalyses; case-specific impact assessment, not a deterministic predicate.",
        "rationale": "The Hollandse Waterlinies zone is GIO-bounded, but no threshold exists that the engine could evaluate without a heritage impact assessment.",
        "executable_ref": _REVIEW_REF,
    },
    "W-19": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "'Onevenredig aantasten' of landscape kernkwaliteiten (art. 7.11a, Bijlage XVI) is an open norm requiring a landscape-quality assessment; not deterministic.",
        "rationale": "The five landscapes and their kernkwaliteiten are identified, but proportionality of impact is a professional judgement; the formalizer refuses to guess a proxy.",
        "executable_ref": _REVIEW_REF,
    },
    "W-20": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "Art. 3.7 prohibitions are risk-based ('een risico vormen voor de winning') and case-specific (e.g. foundation works of a turbine); the six zones are GIO-bounded but the predicate is not deterministic.",
        "rationale": "Zone geometry exists (six GIO's, Bijlage II), yet whether a turbine's foundations pose a risk to abstraction is a hydrological assessment outside the corpus.",
        "executable_ref": _REVIEW_REF,
    },
    "W-21": {
        "kind": "inclusion",
        "zone": {"zoneIds": ["landelijk_gebied"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _LANDELIJK_GEBIED_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["scope_landelijk_gebied", "stedelijk_gebied_out_of_scope"],
        "rationale": "Art. 9.2/9.3 divide the province and forbid urbanisation in the Landelijk gebied unless the verordening provides otherwise (which arts. 5.3/5.4 do for wind); the toelichting to art. 5.4 confirms the verordening has no wind-energy provisions for the stedelijk gebied, so the provincial wind pathway is scoped to the landelijk gebied.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "W-22": {
        "kind": "reject",
        "rule_type": "unsupported_claim",
        "reason": "Non-binding visie ambition whose executable content (Natura 2000 / ganzenrust exclusion) is already formalized from NC-W-08 (toelichting); kept only as a supporting citation on FR-W-08.",
        "rationale": "The visie is policy, not rule; issuing an independent executable rule from it alone would break the binding/interpretive grounding chain (V2).",
        "executable_ref": _NOOP_REF,
    },
    "W-23": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "WHO advisory values are a non-binding 2030 ambition without a provincial dB limit; no numeric threshold may be derived without guessing (national Wgh/Bal applies — abstained).",
        "rationale": "The visie explicitly frames the WHO values as an aspiration 'in aanvulling op de wettelijke vereisten'; the formalizer must not convert an ambition into a limit.",
        "executable_ref": _REVIEW_REF,
    },
    "W-24": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "Non-binding system-choice explanation (no facilitation of turbines from 20 m with < 3 MW); the binding thresholds are already encoded in FR-W-03 (<= 20 m) and FR-W-05 (>= 3 MW), so nothing new is executable.",
        "rationale": "The visie text explains the design of arts. 5.3/5.4; re-issuing it as a rule would duplicate existing formalizations with weaker legal force.",
        "executable_ref": _REVIEW_REF,
    },
    # -- ZON track --------------------------------------------------------------
    "Z-01": {
        "kind": "reject",
        "rule_type": "scope_declaration",
        "reason": "Definitional scope of the object type 'zonneveld' (Bijlage I): ground/water-mounted panel groupings, roofs excluded. Carries no zone or threshold semantics to execute.",
        "rationale": "The definition scopes the ZON use case; the operative siting norm is art. 5.5 (FR-Z-02), so this card yields no independent rule.",
        "executable_ref": _NOOP_REF,
    },
    "Z-02": {
        "kind": "inclusion",
        "zone": {"zoneIds": ["gebied_zonneveld"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GEBIED_ZONNEVELD_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["inclusion_zone_gebied_zonneveld"],
        "rationale": "CORE ZON RULE. Art. 5.5 lid 1 permits, within the 'Gebied zonneveld' (GIO Bijlage II), rules allowing zonnevelden; the zone is quoted verbatim in NC-Z-02. The three proviso's (recognisable structures/landscape integration, soil-water-quality-fitting arrangement, removal duty) are qualitative duties carried as procedural context tags, never guessed as geometry.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "Z-03": {
        "kind": "exclusion",
        "zone": {"zoneIds": ["natura_2000", "ganzenrustgebied"], "selection": "within", "geometrySource": "national_source", "caveat": "exclusion grounded in the toelichting on art. 5.5 (interpretive) + Omgevingsvisie 2021 (non-binding); no provincial GIO exists — geo analyst must attach national geometry with provenance"},
        "conditions": [],
        "extra_tags": ["exclusion_natura_2000", "exclusion_ganzenrustgebied", "no_zon_provisions_for_stedelijk_gebied"],
        "rationale": "The toelichting to art. 5.5 restricts the article to the landelijk gebied 'met uitzondering van de natura 2000-gebieden en de ganzenrustgebieden' — the same geographic reading as wind FR-W-08. Geometry must come from national sources because no provincial GIO covers these areas. The stedelijk gebied needs no separate exclusion: the Gebied zonneveld designation itself does not extend there.",
        "executable_ref": "engine.zone.exclude_within@poc-v1",
    },
    "Z-04": {
        "kind": "compensation",
        "zone": {"zoneIds": ["groene_contour"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GROENE_CONTOUR_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [
            {"parameter": "compensation_realisation_deadline_years", "operator": "<=", "value": 25, "unit": "jaar"},
        ],
        "extra_tags": ["compensation_within_groene_contour", "zonneveld_implicitly_temporary"],
        "rationale": "Art. 6.5a lid 3 sets a fully deterministic compensation regime for zonnevelden inside the Groene contour: the compensation new nature (with its management measures) must be realised at the latest 25 years after placement of the panels. Not an elimination: a temporally bounded obligation attached to affected parcels.",
        "executable_ref": "engine.compensation.ratio@poc-v1",
    },
    "Z-05": {
        "kind": "reject",
        "rule_type": "unsupported_claim",
        "reason": "Non-binding visie statement of admissibility and preference (roofs/facades/infrastructure first, then industrial estates); the visie formulates no further rules, and the toelichting to art. 5.5 (NC-Z-03) confirms the verordening contains no provisions for solar energy in the stedelijk gebied.",
        "rationale": "Visie-admissibility of zonnevelden in the stedelijk gebied is policy, not a verordeningsrule; issuing an executable inclusion from it alone would break the binding/interpretive grounding chain (V2). Note the contrast with wind, where the toelichting itself excludes the stedelijk gebied.",
        "executable_ref": _NOOP_REF,
    },
    # -- BOS track --------------------------------------------------------------
    "B-01": {
        "kind": "inclusion",
        "zone": {"zoneIds": ["groene_contour"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GROENE_CONTOUR_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["zoekgebied_nieuwe_natuur", "vrijwillige_omvorming"],
        "rationale": "CORE BOS RULE. Art. 6.4 lid 1 directs omgevingsplannen within the Groene contour to protect and create the possibilities to realise new nature; the contour is thereby the provincial search area (zoekgebied) for new nature — including forest planting via voluntary conversion, added to the NNN after realisation. Formalized as the opportunity inclusion for the forest_planting object type; the voluntary character (no obligation on individual landowners) is carried as a context tag, not a predicate.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "B-02": {
        "kind": "compensation",
        "zone": {"zoneIds": ["groene_contour"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _GROENE_CONTOUR_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [
            {"parameter": "compensation_ratio_new_nature", "operator": ">=", "value": 1, "unit": "ratio"},
        ],
        "extra_tags": ["compensation_within_groene_contour"],
        "rationale": "Art. 6.5 lid 2 under d requires >= 1:1 compensation with new nature within the contour for the remaining loss of new-nature possibilities. For the BOS track this is the contour's protection regime attached as an obligation (marker), mirroring FR-W-15 for wind; it never eliminates the zoekgebied itself.",
        "executable_ref": "engine.compensation.ratio@poc-v1",
    },
    "B-03": {
        "kind": "conditional",
        "zone": {"zoneIds": ["oude_bosgroeiplaatsen"], "selection": "within", "geometrySource": "provincial_gio", "gioJoinId": _OUDE_BOSGROEIPLAATSEN_GIO, "caveat": CAVEAT_GIO_ACCESS},
        "conditions": [],
        "extra_tags": ["conditional_within_oude_bosgroeiplaatsen", "existing_values_protection"],
        "rationale": "Art. 6.13 lid 1 is an instructieregel directing omgevingsplannen within the 'Waardevolle Houtopstanden - oude bosgroeiplaatsen' to protect and conserve the old-forest values present at those locations. The zone overlay is deterministic; whether a specific planting spares the values is a case-specific assessment marked for human review (V4), not guessed.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "B-04": {
        "kind": "ambiguous",
        "rule_type": "procedural_condition",
        "reason": "Art. 6.15 under a exempts small rejuvenation gaps (<= 10 are, jointly <= 10% of the parcel, <= 1x per 4 years, sustainable forest management) from the national velling-reporting duty within the Gebied houtopstand: a forest-management reporting exemption, not an opportunity-siting predicate for new nature/forest.",
        "rationale": "The thresholds are quoted verbatim and fully deterministic, but they govern reporting duties on felling — a different activity than realising new forest/nature. Converting them into a siting zone would change their legal meaning; the rule is routed to human review with its thresholds recorded in the context tags.",
        "executable_ref": _REVIEW_REF,
    },
    "B-05": {
        "kind": "reject",
        "rule_type": "unsupported_claim",
        "reason": "Non-binding visie ambition (3,000 ha new nature by 2040 within the Groene contour; woodstand expansion for CO2); it quantifies the opgave but adds no rule — the binding zoekgebied is already formalized from NC-B-01.",
        "rationale": "The visie gives the business case behind art. 6.4, not an independent executable norm; re-issuing it as a rule would duplicate FR-B-01 with weaker legal force.",
        "executable_ref": _NOOP_REF,
    },
    # -- WATER track --------------------------------------------------------------
    "WA-01": {
        "kind": "conditional",
        "zone": {"zoneIds": ["vrijwaringszone_waterkering"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_WATER},
        "conditions": [],
        "extra_tags": ["conditional_within_vrijwaringszone_waterkering", "waterkerende_functie_beschermen"],
        "rationale": "CORE WATER RULE (art. 2.14). Instructieregel directing omgevingsplannen for locations within the 'Vrijwaringszone regionale waterkering' to contain rules that protect the waterkerende functie and provide in a vrijwaringszone on both sides of the waterkering. The zone overlay is deterministic; whether a specific riparian development's plan rules adequately protect the waterkering is a plan-quality assessment marked for human review (V4), not guessed — hence a conditional marker (mirroring FR-W-12/FR-B-03), never an elimination.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "WA-02": {
        "kind": "exclusion",
        "zone": {"zoneIds": ["waterbergingsgebied"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_WATER},
        "conditions": [],
        "extra_tags": ["exclusion_waterbergingsgebied", "bestaande_uitbreidingsrechten_exception"],
        "rationale": "Art. 2.15 instructieregel: an omgevingsplan for locations within the 'Waterbergingsgebied' contains no rules allowing developments that conflict with the waterbergingsfunctie, 'tenzij die ontwikkelingen plaatsvinden op basis van bestaande uitbreidingsrechten ter plaatse van de al aanwezige functies'. Formalized as the default zone exclusion for new riparian development; the existing-expansion-rights exception is parcel-specific and cannot be predicated without a case file, so it is carried as a context tag routed to V4 (the engine applies the default, exactly like FR-W-14's discretionary lid-2 exceptions).",
        "executable_ref": "engine.zone.exclude_within@poc-v1",
    },
    "WA-03": {
        "kind": "conditional",
        "zone": {"zoneIds": ["overstroombaar_gebied"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_WATER},
        "conditions": [],
        "extra_tags": ["conditional_within_overstroombaar_gebied", "binnendijks_buitendijks_objectdifferentiatie"],
        "rationale": "Art. 2.16 instructieregel: plans for locations within the 'Overstroombaar gebied' must contain rules that take flood risk into account, differentiated binnendijks (vulnerable and vital objects, woonwijken, bedrijventerreinen) versus buitendijks (also individual homes and businesses). The zone overlay is deterministic; the 'rekening houden met overstromingsrisico's' test is object-type- and case-specific, so the rule is a conditional marker for the riparian_development object type routed to V4 — it never eliminates area by itself.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    # -- BODEM track --------------------------------------------------------------
    # NOTE on the umbrella rules (BO-01/BO-03/BO-04): art. 3.7 ('laat geen
    # activiteiten toe') and art. 3.9 ('verbiedt') are of the non-permission
    # family that FR-WA-02 formalizes as engine.zone.exclude_within, and the
    # zone alias carries registry role 'exclusion'. They are executed as
    # conditional markers because the umbrella (701.18 km2) as an AOI-seeded
    # exclusion breaks the V3 independent re-execution: engine.reexecute_independent
    # skips exclusions when no inclusion rule seeds the zone (documented
    # pre-existing engine bug, engine.py left untouched per task brief), so a
    # 701 km2 exclusion would flip the pipeline verdict to fail. The exclusion
    # semantics are carried in the context tags (exclusion_family_*) and can be
    # switched to engine.zone.exclude_within when the V3 seeding bug is fixed.
    "BO-01": {
        "kind": "conditional",
        "zone": {"zoneIds": ["grondwater_beschermingszone"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_BODEM},
        "conditions": [],
        "extra_tags": ["conditional_within_grondwater_beschermingszone", "exclusion_family_non_permission"],
        "rationale": "CORE BODEM RULE (art. 3.7). Instructieregel directing omgevingsplannen for locations within the six literal designation areas (Waterwingebied, Grondwaterbeschermingsgebied, Boringsvrije zone, Beschermingszone oppervlaktewaterwinning, 100-jaarsaandachtsgebied, Gebied kwetsbare strategische grondwatervoorraad) to allow no activities posing a risk to abstraction for human consumption. The umbrella zone overlay is deterministic (live-verified union of the seven designation areas, conservative superset per article); whether a specific soil activity 'een risico vormt voor de winning' is a case-specific assessment marked for human review (V4) — the same reading FR-W-20 gives this article for wind — hence a conditional marker (mirroring FR-WA-01/FR-WA-03), never an elimination at PoC stage (see the BODEM track note above).",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "BO-03": {
        "kind": "conditional",
        "zone": {"zoneIds": ["grondwater_beschermingszone"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_BODEM},
        "conditions": [],
        "extra_tags": ["conditional_within_grondwater_beschermingszone", "verbod_nieuwe_begraafplaats_uitstrooiveld_dierenbegraafplaats", "exclusion_family_verbod"],
        "rationale": "Art. 3.9 instructieregel: an omgevingsplan for locations within a Waterwingebied or Grondwaterbeschermingsgebied forbids establishing a new cemetery, scattering field or animal cemetery; the second paragraph adds rules for existing facilities. The prohibition is object-specific (new burial facilities, a soil-invasive activity class within soil_activity), not a blanket prohibition of soil activity, so for the soil_activity object type it is carried as a conditional marker inside the umbrella (conservative superset: both named designations are covered by the verified union), with the prohibited activity classes in the context tags — executed per the BODEM track note above (exclusion family, marker until the V3 seeding fix).",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "BO-04": {
        "kind": "conditional",
        "zone": {"zoneIds": ["grondwater_beschermingszone"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_BODEM},
        "conditions": [],
        "extra_tags": ["conditional_within_grondwater_beschermingszone", "rekening_houden_grondwaterkwaliteit"],
        "rationale": "Art. 3.10 instructieregel, the weakest variant of the family: plans within the 'Gebied matig kwetsbare strategische grondwatervoorraad' must 'rekening houden met' groundwater-quality protection for abstraction — a take-into-account duty, exactly the art. 2.16 form that FR-WA-03 formalizes as a conditional marker routed to V4, never an elimination. The matig-kwetsbare designation is fully inside the umbrella union (verified in task 8), so the umbrella binding is a conservative superset for this marker.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "BO-05": {
        "kind": "conditional",
        "zone": {"zoneIds": ["gesloten_stortplaats"], "selection": "within", "geometrySource": "provincial_gio_unverified", "caveat": CAVEAT_GIO_BODEM},
        "conditions": [],
        "extra_tags": ["conditional_within_gesloten_stortplaats", "provincial_jurisdiction_marker"],
        "rationale": "Art. 3.108 aanwijzingsregel: every omgevingsplan activity in the 'Gebied gesloten stortplaats' is of provincial importance — the province can thereby determine whether activities on the closed landfill can take place (soil protection when opening it). This routes jurisdiction, it does not refuse or allow the activity, so it is a context/conditional marker on the gesloten_stortplaats zone (mirroring the FR-WA-03 marker idiom); the permit/assessment chain of afdeling 3.5 (arts. 3.103-3.107) is motivatedly abstained in the ledger.",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "BO-02": {
        "kind": "ambiguous",
        "rule_type": "unsupported_claim",
        "reason": "The literal designation 'Waterwingebied Bethunepolder' has no registered open-data alias (task-8 gap analysis: it matches no selectieregel name and no alias may be invented), and the art. 3.8 predicate is object-specific parking regulation ('uitsluitend parkeren op daartoe expliciet aangewezen locaties' during busy recreation periods) — no deterministic zone predicate for the soil_activity object type without guessing geometry or content.",
        "rationale": "Nearest existing pattern chosen: the FR-W-18/W-19/W-20 ambiguous family (zone exists in the verordening but no executable predicate/geometry can be cited) rather than the FR-W-01/FR-Z-01 scope_declaration reject, because unlike a definitional scope card, art. 3.8 does carry a gebiedsaanwijzing and binding plan content — it stays routed to the V4 human-expert checkpoint instead of being dismissed as non-executable. A dedicated alias (WHERE NAAM='Waterwingebied Bethunepolder') plus a parking-condition template is the phase-2 follow-up.",
        "executable_ref": _REVIEW_REF,
    },
}


class NormFormalizer:
    """Converts NormCards into typed FormalRules via deterministic templates.

    Every card yields exactly one FormalRule (total coverage by construction):
    status ``formalized`` when a template with zone semantics exists, otherwise
    ``ambiguous`` or ``rejected`` with a mandatory reason — never a guess.
    """

    agent_name = "norm-formalizer"

    def __init__(self, run_ref: str = FORMALIZER_RUN,
                 llm_hook: Optional[Callable[[Mapping[str, Any]], Optional[Mapping[str, Any]]]] = None) -> None:
        self.run_ref = run_ref
        self.llm_hook = llm_hook
        self.last_coverage: Dict[str, int] = {}
        self._llm_proposed = 0

    def formalize(
        self, normcards: Sequence[Union[NormCard, Mapping[str, Any]]]
    ) -> List[FormalRule]:
        cards: List[NormCard] = [
            card if isinstance(card, NormCard) else NormCard.from_dict(card)
            for card in normcards
        ]
        rules = [self._formalize_card(card) for card in cards]
        self._check_integrity(cards, rules)
        counts = {"formalized": 0, "ambiguous": 0, "rejected": 0}
        for rule in rules:
            counts[rule.status] += 1
        self.last_coverage = {
            "input_cards": len(cards),
            "output_rules": len(rules),
            **counts,
            "llm_proposed": self._llm_proposed,
            "llm_rejected": len(self.llm_hook.rejected) if self.llm_hook is not None else 0,
        }
        return rules

    # -- internals ------------------------------------------------------------

    def _llm_rule(self, card: NormCard, proposal: Mapping[str, Any]) -> Dict[str, Any]:
        """Assemble a FormalRule from a *gated* S2 proposal.

        The hook has already validated kind/zone grounding/quote grounding;
        this builder remains deterministic: geometrySource/gioJoinId/caveat
        come from the card's own geoBinding (never from the model), the
        kind→ruleType/zoneSemantics/executableRef mapping is a fixed table,
        and the seam stamps identity into ``formalizedBy``.
        """
        from pipeline.norm_llm import KIND_MAP

        meta = KIND_MAP[proposal["kind"]]
        gb_obj = getattr(card, "geoBinding", None)
        gb: Dict[str, Any] = {}
        if gb_obj is not None:
            import dataclasses

            gb = dataclasses.asdict(gb_obj) if dataclasses.is_dataclass(gb_obj) else dict(gb_obj)
        zone_selector: Dict[str, Any] = {
            "zoneIds": list(proposal["zoneIds"]),
            "selection": meta["selection"],
            "geometrySource": gb.get("geometrySource") or "national_source",
        }
        if gb.get("gioJoinId"):
            zone_selector["gioJoinId"] = gb.get("gioJoinId")
        if gb.get("caveat"):
            zone_selector["caveat"] = gb.get("caveat")
        if proposal.get("bufferDistanceM") is not None:
            zone_selector["bufferDistanceM"] = proposal["bufferDistanceM"]
        rule = _base_rule(
            card,
            status="formalized",
            rule_type=meta["rule_type"],
            zone_semantics=meta["zone_semantics"],
            executable_ref=meta["executable_ref"],
            extra_tags=("llm_proposed",),
            rationale=(
                str(proposal["rationale"]).rstrip(". ")
                + ". [gated LLM proposal (S2); deterministic gates passed; human review required]"
            ),
            zone_selector=zone_selector,
            conditions=list(proposal.get("conditions") or []),
        )
        stamp = getattr(self.llm_hook, "stamp", None)
        if stamp:
            agent, _, _version = self.run_ref.partition("#")
            rule["formalizedBy"] = f"{agent}#{stamp}"
        self._llm_proposed += 1
        return rule

    def _formalize_card(self, card: NormCard) -> FormalRule:
        spec = TEMPLATE_SPECS.get(card.evidenceId)
        if spec is None:
            # S2 seam: only template-less cards consult the hook. Curated
            # abstentions (template kind ambiguous/reject) are never
            # re-proposed — the model cannot override a curated reason.
            if self.llm_hook is not None:
                proposal = self.llm_hook(card.to_dict())
                if proposal is not None:
                    return FormalRule.from_dict(self._llm_rule(card, proposal))
            rule = _base_rule(
                card,
                status="ambiguous",
                rule_type="unsupported_claim",
                zone_semantics="none",
                executable_ref=_REVIEW_REF,
                reason=(
                    f"no deterministic template registered for evidence {card.evidenceId} "
                    f"(theme {card.theme}); refusing to guess"
                ),
                rationale=(
                    f"cite-or-abstain: without a registered template the formalizer must not "
                    f"invent predicates for theme '{card.theme}'."
                ),
            )
            return FormalRule.from_dict(rule)

        kind = spec["kind"]
        if kind == "inclusion":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_inclusion",
                zone_semantics="inclusion",
                executable_ref=spec.get("executable_ref", "engine.zone.within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "exclusion":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_exclusion",
                zone_semantics="exclusion",
                executable_ref=spec.get("executable_ref", "engine.zone.exclude_within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "attention":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_attention",
                zone_semantics="attention",
                executable_ref=spec.get("executable_ref", "engine.zone.buffer@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "conditional":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_conditional",
                zone_semantics="conditional",
                executable_ref=spec.get("executable_ref", "engine.zone.within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "compensation":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="compensation_requirement",
                zone_semantics="compensation",
                executable_ref=spec.get("executable_ref", "engine.compensation.ratio@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "ambiguous":
            rule = _base_rule(
                card,
                status="ambiguous",
                rule_type=spec["rule_type"],
                zone_semantics="none",
                executable_ref=spec.get("executable_ref", _REVIEW_REF),
                extra_tags=spec.get("extra_tags", ()),
                reason=spec["reason"],
                rationale=spec["rationale"],
            )
        elif kind == "reject":
            rule = _base_rule(
                card,
                status="rejected",
                rule_type=spec["rule_type"],
                zone_semantics="none",
                executable_ref=spec.get("executable_ref", _NOOP_REF),
                extra_tags=spec.get("extra_tags", ()),
                reason=spec["reason"],
                rationale=spec["rationale"],
            )
        else:  # pragma: no cover - authoring guard
            raise ValueError(f"unknown template kind {kind!r} for {card.evidenceId}")
        return FormalRule.from_dict(rule)  # validates against formal-rule.schema.json

    def _check_integrity(self, cards: List[NormCard], rules: List[FormalRule]) -> None:
        card_ids = {card.id for card in cards}
        covered = {rule.normCardId for rule in rules} | {
            rel for rule in rules for rel in (rule.relatedNormCardIds or [])
        }
        missing = card_ids - {rule.normCardId for rule in rules}
        if missing:
            raise RuntimeError(f"formalizer coverage failure: cards without a rule: {sorted(missing)}")
        unknown_related = covered - card_ids
        if unknown_related:
            raise RuntimeError(f"formalizer references unknown NormCards: {sorted(unknown_related)}")
        for rule in rules:
            if rule.executableRef not in ENGINE_OPERATIONS:
                raise RuntimeError(
                    f"rule {rule.id} references unregistered engine operation {rule.executableRef}"
                )
            if rule.status == "formalized" and (rule.zoneSelector is None or rule.conditions is None):
                raise RuntimeError(f"formalized rule {rule.id} lacks zoneSelector/conditions")
            if rule.status != "formalized" and (rule.conditions or rule.zoneSelector):
                raise RuntimeError(
                    f"non-formalized rule {rule.id} must not carry executable predicates"
                )


# ---------------------------------------------------------------------------
# corpus (re)generation — python3 -m pipeline.agents
# ---------------------------------------------------------------------------

def generate_corpus() -> Dict[str, Path]:
    """Deterministically (re)generate the per-track normcard/formalrule corpora.

    Tracks: wind (evidence-wind.json), zon (evidence-zon.json, solar fields)
    and bos (evidence-bos.json, new nature / forest planting)."""
    out: Dict[str, Path] = {}
    analyst = NormAnalyst()
    formalizer = NormFormalizer()
    for track in ("wind", "zon", "bos"):
        shard = CORPUS_DIR / f"evidence-{track}.json"
        cards = analyst.read(shard)
        if analyst.rejected:
            raise RuntimeError(
                f"verified-only invariant broken by: {[r['evidenceId'] for r in analyst.rejected]}"
            )
        cards_path = CORPUS_DIR / f"normcards-{track}.json"
        cards_path.write_text(
            json.dumps([card.to_dict() for card in cards], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rules = formalizer.formalize(cards)
        rules_path = CORPUS_DIR / f"formalrules-{track}.json"
        rules_path.write_text(
            json.dumps([rule.to_dict() for rule in rules], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        out[track] = rules_path
    return out


def main() -> None:
    generate_corpus()
    analyst = NormAnalyst()
    formalizer = NormFormalizer()
    for track in ("wind", "zon", "bos"):
        cards = analyst.read(CORPUS_DIR / f"evidence-{track}.json")
        formalizer.formalize(cards)
        print(f"wrote corpus/normcards-{track}.json ({len(cards)} cards) and "
              f"corpus/formalrules-{track}.json {formalizer.last_coverage}")


if __name__ == "__main__":  # pragma: no cover
    main()
