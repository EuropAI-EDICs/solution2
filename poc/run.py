#!/usr/bin/env python3
"""CLI orchestrator for the opportunity-map PoC (plan section 3.2, agent #1).

Tracks: ``wind`` (wind turbines), ``zon`` (zonnevelden / solar fields),
``bos`` (new nature / forest planting), ``water`` (riparian development
bounded by the watersysteem instructieregels) and ``bodem`` (soil activity
bounded by the ondergrond-en-bodem instructieregels) — same instrument
(Omgevingsverordening provincie Utrecht, CVDR704250), same agent architecture,
per-track evidence shards and cite-or-abstain ledgers.

Wires the planning plane end-to-end:

    Intake (use-case request) -> NormAnalyst -> NormFormalizer -> Geo Analyst
    (geodata fetch of every zone referenced by a formalized rule) -> zone
    engine -> Cartographer -> Critic (V0-V3 + V4 pending) -> Explainer
    (decision table + PROV) -> single-file HTML report -> run summary.

Every agent boundary emits JSON validated against poc/schemas/*.schema.json
(the V0 gate); every legal claim stays chained to its NormCard citation
(cite-or-abstain); every artifact lands in the run directory with PROV.

Usage (no install, from the workspace root):

    python3 poc/run.py                     # wind use case, cache-first
    python3 poc/run.py --use-case zon      # solar fields (zonnevelden)
    python3 poc/run.py --use-case bos      # new nature / forest planting
    python3 poc/run.py --use-case water    # riparian development (watersysteem rule bounds)
    python3 poc/run.py --use-case bodem    # soil activity (ondergrond-en-bodem rule bounds)
    python3 poc/run.py --refresh           # re-download live layers
    python3 poc/run.py --bbox 130000,440000,160000,470000   # EPSG:28992 clip
    python3 poc/run.py --out poc/runs/demo

Exit code 0 only when the Critic's pipeline-run verdict is ``pass``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

POC_ROOT = Path(__file__).resolve().parent
WORKSPACE = POC_ROOT.parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from shapely.geometry import box, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from pipeline import agents, cartographer, contracts, critic, engine, explainer, geodata, norm_llm, report  # noqa: E402
from pipeline.contracts import OpportunityMapRequest  # noqa: E402

RUN_VERSION = "poc-run/1.0"
ORCHESTRATOR_AGENT = {"id": "orchestrator", "name": "run.py orchestrator", "version": RUN_VERSION,
                      "role": "plan -> dispatch -> verify -> synthesize (plan section 3.2 agent #1)"}

# --------------------------------------------------------------------------- #
# zone -> open-data alias registry (provenance aliases for the Bijlage-II GIO
# join-ids whose DSO download API is key-gated, HTTP 401 verified)
# --------------------------------------------------------------------------- #

ZONE_SOURCES: Dict[str, Dict[str, Any]] = {
    "gebied_windenergie": {
        "sourceId": "agrest-ov-gebied-windenergie",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied windenergie'",
    },
    "gebied_kleine_windturbine": {
        "sourceId": "agrest-ov-gebied-kleine-windturbine",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied kleine windturbine'",
    },
    "natura_2000": {
        "sourceId": "arcgis-natura2000",
        "note": "national Natura 2000 designation layer on the province hub (no provincial GIO exists)",
    },
    "ganzenrustgebied": {
        "sourceId": "agrest-ov-ganzenrustgebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Ganzenrustgebied'",
    },
    "stiltegebied": {
        "sourceId": "agrest-ov-stiltegebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Stiltegebied' (stille kern + bufferzone, art. 9.25 lid 1)",
    },
    "aandachtsgebied_stiltegebied": {
        "sourceId": "agrest-ov-stiltegebied",
        "note": "derived: the zone engine buffers Stiltegebied by 1500 m per art. 9.25 lid 2 (FR-W-10 bufferDistanceM)",
    },
    "natuurnetwerk_nederland": {
        "sourceId": "agrest-ov-natuurnetwerk",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Natuurnetwerk Nederland'",
    },
    "groene_contour": {
        "sourceId": "agrest-ov-groene-contour",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Groene contour'",
    },
    "landelijk_gebied": {
        "sourceId": "agrest-ov-landelijk-gebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Landelijk gebied'",
    },
    "gebied_zonneveld": {
        "sourceId": "agrest-ov-gebied-zonneveld",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied zonneveld' (art. 5.5)",
    },
    "oude_bosgroeiplaatsen": {
        "sourceId": "agrest-ov-oude-bosgroeiplaatsen",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Waardevolle Houtopstanden - oude bosgroeiplaatsen' (art. 6.13)",
    },
    "waterbergingsgebied": {
        "sourceId": "agrest-ov-waterbergingsgebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Waterbergingsgebied' (art. 2.15 instructieregel, WA-02)",
    },
    "overstroombaar_gebied": {
        "sourceId": "agrest-ov-overstroombaar-gebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Overstroombaar gebied' (art. 2.16 instructieregel, WA-03)",
    },
    "vrijwaringszone_waterkering": {
        "sourceId": "agrest-ov-vrijwaringszone-regionale-waterkering",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Vrijwaringszone regionale waterkering' (art. 2.14 instructieregel, WA-01)",
    },
    "grondwater_beschermingszone": {
        "sourceId": "agrest-ov-grondwaterbeschermingszone",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Grondwaterbeschermingszone' (bodem-instructieregels BO-01/BO-03/BO-04: umbrella-werkingsgebied, live geverifieerd exact gelijk aan de vereniging van de zeven letterlijke aanwijzingsgebieden van art. 3.7/3.9/3.10)",
    },
    "gesloten_stortplaats": {
        "sourceId": "agrest-ov-gebied-gesloten-stortplaats",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied gesloten stortplaats' (art. 3.108 aanwijzingsregel, BO-05: omgevingsplanactiviteit van provinciaal belang)",
    },
    "beperkingengebied_bouwwerken_provinciale_weg": {
        "sourceId": "agrest-ov-beperkingengebied-bouwwerken-provinciale-weg",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Beperkingengebied bouwwerken provinciale weg' (art. 4.7 instructieregel, MO-01: bouwwerken kan-mits rekening houden met instandhouding/uitbreiding provinciale weg)",
    },
    "geluidcontour_buiten_bebouwde_kom": {
        "sourceId": "agrest-ov-geluidcontour-buiten-bebouwde-kom",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Geluidcontour buiten de bebouwde kom' (art. 4.71 instructieregel, MO-02: nieuwe geluidgevoelige gebouwen tot maximaal 60 dB Lden op de gevel)",
    },
    "geluidcontour_binnen_bebouwde_kom": {
        "sourceId": "agrest-ov-geluidcontour-binnen-bebouwde-kom",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Geluidcontour binnen de bebouwde kom' (art. 4.71 instructieregel, MO-02: nieuwe geluidgevoelige gebouwen tot maximaal 65 dB Lden op de gevel)",
    },
    "beperkingengebied_lokale_spoorweg": {
        "sourceId": "agrest-ov-beperkingengebied-lokale-spoorweg",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Beperkingengebied lokale spoorweg' (art. 4.47/4.48 instructieregels, MO-03/MO-04; umbrella = Kernzone ∪ Beschermingszone per art. 4.46, live geverifieerd met 0,0000 km2 symdiff)",
    },
    "luchtvaartterrein": {
        "sourceId": "agrest-ov-luchtvaartterrein",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Luchtvaartterrein' (art. 4.65 instructieregel, MO-05: geen regels voor nieuwvestiging luchtvaartterrein gemotoriseerde luchtvaartuigen; Buffer luchtvaartterrein art. 4.66 gemotiveerd onthouden)",
    },
    "unesco_werelderfgoed_hollandse_waterlinies": {
        "sourceId": "agrest-ov-unesco-werelderfgoed-hollandse-waterlinies",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='UNESCO Werelderfgoed Hollandse Waterlinies' (art. 7.3 instructieregel, LS-01 lid 1b: geen regels die activiteiten toestaan die de uitzonderlijke universele waarde aantasten)",
    },
    "unesco_werelderfgoed_neder_germaanse_limes_kernzone": {
        "sourceId": "agrest-ov-unesco-werelderfgoed-neder-germaanse-limes-kernzone",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='UNESCO Werelderfgoed Neder-Germaanse Limes (kernzone)' (art. 7.3a instructieregel, LS-02 lid 1b: zelfde niet-toestaan-vorm als 7.3)",
    },
    "unesco_werelderfgoed_neder_germaanse_limes_bufferzone": {
        "sourceId": "agrest-ov-unesco-werelderfgoed-neder-germaanse-limes-bufferzone",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='UNESCO Werelderfgoed Neder-Germaanse Limes (bufferzone)' (art. 7.4 instructieregel, LS-03: versterkingsplicht + vergunningsverbod 100 m2/30 cm-maaiveld)",
    },
    "gebied_cultuurhistorische_hoofdstructuur": {
        "sourceId": "agrest-ov-gebied-cultuurhistorische-hoofdstructuur",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied cultuurhistorische hoofdstructuur' (art. 7.9 instructieregel, LS-04; umbrella = vereniging van de vijf art.-7.8-gebieden, live geverifieerd met 0,000004 km2 symdiff)",
    },
    "landschap": {
        "sourceId": "agrest-ov-landschap",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Landschap' (art. 7.11a instructieregel, LS-05; umbrella = vereniging van de vijf art.-7.11-landschappen, live geverifieerd met 0,0000 km2 symdiff)",
    },
    "gebied_aardkundige_waarden": {
        "sourceId": "agrest-ov-gebied-aardkundige-waarden",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied aardkundige waarden' (art. 7.12 instructieregel, LS-06: regels ter bescherming van aangewezen aardkundige waarden)",
    },
    "gebied_agrarische_bedrijven": {
        "sourceId": "agrest-ov-gebied-agrarische-bedrijven",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied agrarische bedrijven' (art. 8.1 instructieregel, LB-01: mengvorm verbod nieuwe bouwpercelen/omschakeling + voorschrift bouwperceel max 1,5 ha)",
    },
    "landbouwontwikkelingsgebied": {
        "sourceId": "agrest-ov-landbouwontwikkelingsgebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Landbouwontwikkelingsgebied' (art. 8.2 instructieregel, LB-02: kan-mits uitbreiding niet-grondgebonden landbouw tot max 2,5 ha)",
    },
    "landbouwstabiliseringsgebied": {
        "sourceId": "agrest-ov-landbouwstabiliseringsgebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Landbouwstabiliseringsgebied' (art. 8.3 instructieregel, LB-03: geen uitbreiding niet-grondgebonden bouwperceel)",
    },
    "concentratiegebied_glastuinbouw": {
        "sourceId": "agrest-ov-concentratiegebied-glastuinbouw",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Concentratiegebied glastuinbouw' (art. 8.5 instructieregel, LB-04: beschermende instructie, geen belemmering van glastuinbouw)",
    },
    "gebied_glastuinbouw_niet_toegestaan": {
        "sourceId": "agrest-ov-gebied-glastuinbouw-niet-toegestaan",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied glastuinbouw niet toegestaan' (art. 8.6 instructieregel, LB-05: geen glastuinbouw, tenzij verplaatsing Ronde Venen -> Polder Derde Bedijking)",
    },
    "gebied_beperken_bodembewerking": {
        "sourceId": "agrest-ov-gebied-beperken-bodembewerking",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied beperken bodembewerking' (art. 8.7 instructieregel, LB-06: geen veenblootleggende bodembewerking in agrarische gronden, tenzij graslandvernieuwing/blijvende teelt)",
    },
    "kernrandzone": {
        "sourceId": "agrest-ov-kernrandzone",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Kernrandzone' (art. 9.10 instructieregel, WN-04: kan-mits verstedelijking ter versterking ruimtelijke kwaliteit; uitzondering op art. 9.3)",
    },
    "gebied_recreatiewoning": {
        "sourceId": "agrest-ov-gebied-recreatiewoning",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied recreatiewoning' (art. 9.8 instructieregel, WN-03: recreatief gebruik gegarandeerd, omvorming tot permanente bewoning uitgesloten)",
    },
    "gebied_uitbreiding_woningbouw": {
        "sourceId": "agrest-ov-gebied-uitbreiding-woningbouw",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Gebied uitbreiding woningbouw onder voorwaarden mogelijk' (art. 9.14/9.14a/9.15 instructieregels, WN-07/WN-08/WN-09: 50 woningen vitaliteit, flexwoningen, woningbouw onder voorwaarden)",
    },
    "stedelijk_gebied": {
        "sourceId": "agrest-ov-stedelijk-gebied",
        "note": "vigerende Omgevingsverordening IMOW layer, WHERE NAAM='Stedelijk gebied' (art. 9.17 instructieregel, WN-10: kan verstedelijking/woningbouw-mits; aanwijzing art. 9.2)",
    },
}

INSTRUMENT = "Omgevingsverordening provincie Utrecht, CVDR704250 geldend 13-10-2025 t/m heden"

# --------------------------------------------------------------------------- #
# per-track configuration: evidence shard, cite-or-abstain ledger, report texts
# and track-specific limitations. Every use case shares the instrument, the
# agent architecture and the zone-alias registry above.
# --------------------------------------------------------------------------- #

TRACKS: Dict[str, Dict[str, Any]] = {
    "wind": {
        "shard": "corpus/evidence-wind.json",
        "ledger": "corpus/normcards-rejected.json",
        "report_title": "Where can wind turbines be sited in province Utrecht?",
        "decision_table_id": "DT-wind-utrecht-poc1",
        "decision_table_title": "Where can wind turbines be sited in province Utrecht? "
                               "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:wind:",
        "headline_note": (
            "Semantics: the final zone is the union of the formalized inclusion zones (Gebied windenergie \u22653 MW "
            "path, Gebied kleine windturbine \u226420 m path, Landelijk gebied scope) clipped to the province "
            "boundary, minus Natura 2000 areas, ganzenrustgebieden and the Natuurnetwerk Nederland (default "
            "exclusion; art. 6.3 lid 2 exceptions are discretionary). Stiltegebied / Groene contour overlays are "
            "markers (attention / compensation), not eliminations. This is a programming-stage screening artifact; "
            "per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "The province-scale 'Gebied windenergie' polygon (1166.5 km\u00b2) is a designation envelope, not a "
            "'suitable everywhere' area: clustering, removal duty, beeldkwaliteit and municipal omgevingsplan "
            "rules still apply per location.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms such as "
                "'onevenredig aantasten', deviation paths, noise ambitions): they carry no executable predicate "
                "(cite-or-abstain) and are routed to the V4 human-expert checkpoint; the deterministic map "
                f"consumed only the {cov['formalized']} formalized rules."
            ),
            "Abstained topics (no verified provincial citation): stikstof deposition, national wind-turbine noise "
            "limits (Wgh/Bal), tip height/setback distances, Natura 2000 GIO absence, ET_wind tracking-layer "
            "misrepresentation risk, the pending 1-1-2027 amendment.",
        ],
    },
    "zon": {
        "shard": "corpus/evidence-zon.json",
        "ledger": "corpus/normcards-rejected-zon.json",
        "report_title": "Where can zonnevelden (solar fields) be sited in province Utrecht?",
        "decision_table_id": "DT-zon-utrecht-poc1",
        "decision_table_title": "Where can zonnevelden (solar fields) be sited in province Utrecht? "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:zon:",
        "headline_note": (
            "Semantics: the opportunity zone is the 'Gebied zonneveld' designation (art. 5.5 lid 1) clipped to "
            "the province boundary, minus the Natura 2000 areas and ganzenrustgebieden (toelichting on art. 5.5: "
            "the article covers the landelijk gebied excluding those areas, and the verordening contains no solar "
            "provisions for the stedelijk gebied). The Groene contour overlay is a compensation marker (art. 6.5a "
            "lid 3: new nature as compensation realised within 25 years of panel placement \u2014 zonnevelden "
            "inside the contour are implicitly temporary), not an elimination. Rooftop/facade solar is outside "
            "the zonneveld object definition (Bijlage I). Programming-stage screening artifact; per-location "
            "assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "The 'Gebied zonneveld' designation is a designation envelope: the three qualitative proviso's of "
            "art. 5.5 lid 1 (recognisable structures / landscape integration, soil- and water-quality-fitting "
            "panel arrangement, removal duty) are per-project assessments routed to V4/procedural review, never "
            "executed as geometry.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are 'ambiguous' (routed to V4); "
                f"{cov['formalized']} formalized and {cov['rejected']} rejected as non-binding "
                "(definition / visie ambition) — every zonneveld norm in the verordening is either executed or "
                "explicitly grounded as non-executable."
            ),
            "Abstained topics (no verified provincial citation): stikstof, national solar-field rules "
            "(BAL / Bouwbesluit / grid law), the energy test for the zon track, rooftop/facade solar (outside "
            "the zonneveld definition), GIO download access, the pending 1-1-2027 amendment.",
        ],
    },
    "bos": {
        "shard": "corpus/evidence-bos.json",
        "ledger": "corpus/normcards-rejected-bos.json",
        "report_title": "Where can new nature / forest planting be realised in province Utrecht?",
        "decision_table_id": "DT-bos-utrecht-poc1",
        "decision_table_title": "Where can new nature / forest planting be realised in province Utrecht? "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:bos:",
        "headline_note": (
            "Semantics: the opportunity zone is the Groene contour \u2014 the provincial zoekgebied for new "
            "nature (art. 6.4 lid 1) \u2014 clipped to the province boundary; forest planting proceeds through "
            "voluntary conversion, with realised nature added to the Natuurnetwerk Nederland. The art. 6.5 lid 2 "
            "onder d \u22651:1 compensation ratio is a marker attached to the contour, and the 'Waardevolle "
            "Houtopstanden - oude bosgroeiplaatsen' (art. 6.13) a conditional overlay (protect existing "
            "old-forest values) \u2014 neither eliminates area. Programming-stage screening artifact; realisation "
            "runs through area processes and the Natuurbeheerplan."
        ),
        "limitations": lambda cov, abst: [
            "The Groene contour is a zoekgebied (search area) for voluntary conversion: art. 6.4 obliges "
            "omgevingsplannen to keep possibilities for new nature open within the contour \u2014 it binds plans, "
            "not landowners; actual realisation depends on voluntary participation, land acquisition and the "
            "Natuurbeheerplan (see the abstentions ledger).",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are 'ambiguous' (routed to V4; the art. 6.15 "
                "velling-reporting exemption thresholds are deterministic but govern forest management, not "
                f"siting); {cov['formalized']} formalized, {cov['rejected']} rejected as non-binding ambition."
            ),
            "Abstained topics (no verified provincial citation): stikstof, the NNN-addition procedure, land "
            "acquisition / area-process financing, nature-type selection (Natuurbeheerplan maatgevend), GIO "
            "download access, the pending 1-1-2027 amendment.",
        ],
    },
    "water": {
        "shard": "corpus/evidence-water.json",
        "ledger": "corpus/normcards-rejected-water.json",
        "report_title": "Where is riparian development bounded by the watersysteem rules in province Utrecht?",
        "decision_table_id": "DT-water-utrecht-poc1",
        "decision_table_title": "Watersysteem rule bounds for riparian development "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:water:",
        "headline_note": (
            "Semantics: instructieregels art. 2.14 (vrijwaringszone regionale waterkering), 2.15 "
            "(waterbergingsgebied) and 2.16 (overstroombaar gebied) bound development in and around "
            "the watersysteem; zones are the provincial designations clipped to the province "
            "boundary. Omgevingswaarden (monitoring norms) are deliberately abstained. "
            "Programming-stage screening artifact; per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Waterkering-omgevingswaarden (art. 2.2-2.11) are monitoring norms for water boards, "
            "not zone rules: abstained under cite-or-abstain.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms, "
                "procedural rules): routed to the V4 human-expert checkpoint."
            ),
            "Peilbesluit/legger/waterschaarste articles are procedural for water boards: abstained.",
        ],
    },
    "bodem": {
        "shard": "corpus/evidence-bodem.json",
        "ledger": "corpus/normcards-rejected-bodem.json",
        "report_title": "Where is soil activity bounded by groundwater and soil rules in province Utrecht?",
        "decision_table_id": "DT-bodem-utrecht-poc1",
        "decision_table_title": "Ondergrond-en-bodem rule bounds for soil activity "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:bodem:",
        "headline_note": (
            "Semantics: the opportunity zone is the province AOI minus the "
            "grondwaterbeschermingszone umbrella — the art. 3.7 instructieregel "
            "('laat geen activiteiten toe die een risico vormen voor de winning') "
            "and the art. 3.9 verbod (new burial facilities) are executed as "
            "default exclusions on the conservative umbrella union of the "
            "designation areas; art. 3.10 ('rekening houden met') stays a "
            "conditional marker (weakest take-into-account variant, V4), and the "
            "art. 3.108 gesloten stortplaats aanwijzingsregel a context marker. "
            "Groundwater permitting frames (art. 3.1) are procedural and "
            "deliberately abstained. Programming-stage screening artifact; "
            "per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Grondwaterbeheer (art. 3.1) and verontreiniging (art. 3.3) are permitting/assessment "
            "frames: abstained under cite-or-abstain.",
            "The art. 3.7/3.9 exclusions run on the conservative umbrella union of the designation "
            "areas (superset per article); whether a specific activity 'een risico vormt voor de "
            "winning' is a per-case V4 assessment, and art. 3.10 (matig kwetsbare voorraad, "
            "'rekening houden met') is deliberately a marker, not an extra elimination.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
    "mobiliteit": {
        "shard": "corpus/evidence-mobiliteit.json",
        "ledger": "corpus/normcards-rejected-mobiliteit.json",
        "report_title": "Where is roadside development bounded by mobility rules in province Utrecht?",
        "decision_table_id": "DT-mobiliteit-utrecht-poc1",
        "decision_table_title": "Mobiliteitsregel bounds for roadside development "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:mobiliteit:",
        "headline_note": (
            "Semantics: instructieregels art. 4.7 (Beperkingengebied bouwwerken provinciale "
            "weg), 4.47/4.48 (Beperkingengebied lokale spoorweg; umbrella = Kernzone ∪ "
            "Beschermingszone per art. 4.46, live geverifieerd) and 4.71 (Geluidcontour van "
            "provinciale wegen, buiten/binnen de bebouwde kom) are kan-mits rules with dB "
            "thresholds and care duties — executed as conditional markers routed to the V4 "
            "checkpoint. Art. 4.65 (Luchtvaartterrein) is an unconditional verbod on "
            "nieuwvestiging van een luchtvaartterrein voor gemotoriseerde luchtvaartuigen, "
            "activity-scoped to aviation and therefore also a marker, never an elimination "
            "of roadside-development area. No hoofdstuk-4 rule unconditionally refuses "
            "roadside development itself, so the opportunity zone equals the province AOI "
            "with five marker overlays. Vergunnings-/meldingsketens (beheer, vrij zicht, "
            "vaarweg) and the reserved basisnet articles (4.67/4.68 [Gereserveerd]) are "
            "deliberately abstained. Programming-stage screening artifact; per-location "
            "permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Provinciale-weg beheer/vrij zicht (art. 4.8-4.44), vaarweg (art. 4.52-4.64) and "
            "bestuursorgaan bepalingen are vergunnings-/meldingsketens: abstained under "
            "cite-or-abstain; the externe veiligheid basisnet articles 4.67/4.68 are "
            "[Gereserveerd] in the consolidated text.",
            "The art. 4.65 verbod is activity-scoped (nieuwvestiging luchtvaartterrein voor "
            "gemotoriseerde luchtvaartuigen — aviation, not roadside development): it never "
            "subtracts roadside-development area, and the Luchtvaartterrein designation "
            "(1014.496 km2 union incl. a 676.516 km2 feature) is reported as a marker. The "
            "Buffer luchtvaartterrein variant (art. 4.66, onderzoeksgestuurde tenzij-"
            "uitzondering) is motivatedly abstained.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
    "landschap": {
        "shard": "corpus/evidence-landschap.json",
        "ledger": "corpus/normcards-rejected-landschap.json",
        "report_title": "Where is landscape intervention bounded by heritage and landscape rules in province Utrecht?",
        "decision_table_id": "DT-landschap-utrecht-poc1",
        "decision_table_title": "Cultuurhistorie-en-landschap rule bounds for landscape intervention "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:landschap:",
        "headline_note": (
            "Semantics: the werelderfgoed-instructieregels art. 7.3 (Gebied UNESCO "
            "Werelderfgoed Hollandse Waterlinies) and 7.3a (Neder-Germaanse Limes "
            "kernzone) carry the niet-toestaan-form in lid 1b and are executed as "
            "default exclusions for landscape intervention, with the aantasten-toets "
            "routed to V4 per case (BO-01-idiom). The weaker instructiefamilies stay "
            "conditional markers: art. 7.4 (Limes bufferzone: versterkingsplicht + "
            "100 m2/30 cm-vergunningsverbodprescriptie), art. 7.9 (cultuurhistorische "
            "hoofdstructuur, rekening-houden; umbrella = vijf art.-7.8-gebieden, live "
            "geverifieerd), art. 7.11a (Landschap-kernkwaliteiten, onevenredig-"
            "proportionaliteit; umbrella = vijf art.-7.11-landschappen, live "
            "geverifieerd) and art. 7.12 (aardkundige waarden, beschermingsplicht). "
            "The 7.10 verstedelijkingsgateway, the beoordelings-/vergunningsketens "
            "(7.5/7.5a/7.6) and the borden-activiteitenketen (7.13-7.17) are "
            "deliberately abstained under cite-or-abstain. Programming-stage "
            "screening artifact; per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Beoordelingsregels (art. 7.5/7.5a/7.6) and the borden-activiteitenketen "
            "(art. 7.13-7.17, incl. the onvoorwaardelijke gedragsregel-verbod 7.16) are "
            "aanvraag-/kennisafhankelijk of buiten het landscape_intervention-"
            "objecttype: abstained under cite-or-abstain.",
            "The art. 7.3/7.3a exclusions apply the protective default on the full "
            "werelderfgoed designations (HW 134.092 km2, NGL-kernzone 0.013 km2); "
            "whether a specific intervention 'die waarde aantast' is a per-case V4 "
            "assessment, and the art. 7.11a 'onevenredig'-verbod (Landschap-umbrella, "
            "1411.133 km2) is deliberately a marker, not an elimination.",
            "The art. 7.10 verstedelijkingsgateway (Historische buitenplaatszone, "
            "Militair erfgoed) is a permissive deviation path under three open norms "
            "(kleinschalig, kostendragers, zorgvuldige inpassing): motivatedly "
            "abstained, documented as heroverwegingskandidaat.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
    "landbouw": {
        "shard": "corpus/evidence-landbouw.json",
        "ledger": "corpus/normcards-rejected-landbouw.json",
        "report_title": "Where is agricultural expansion bounded by the landbouw instructieregels in province Utrecht?",
        "decision_table_id": "DT-landbouw-utrecht-poc1",
        "decision_table_title": "Landbouw rule bounds for agricultural expansion "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:landbouw:",
        "headline_note": (
            "Semantics: three H8 instructieregels carry the niet-toestaan-form with "
            "refused activity classes inside agricultural_expansion and are executed "
            "as default exclusions — art. 8.3 (Landbouwstabiliseringsgebied: no "
            "expansion of niet-grondgebonden farm plots), art. 8.6 (Gebied "
            "glastuinbouw niet toegestaan: no glastuinbouw, tenzij verplaatsing Ronde "
            "Venen -> Polder Derde Bedijking; the designation covers 1557.796 km2, "
            "almost the whole province minus the kassenconcentraties) and art. 8.7 "
            "(Gebied beperken bodembewerking: no veen-exposing agricultural soil "
            "work, tenzij graslandvernieuwing/blijvende teelt). The mixed/kan-mits/"
            "protective instructieregels stay conditional markers: art. 8.1 (Gebied "
            "agrarische bedrijven: verbod nieuwe bouwpercelen + voorschrift "
            "bouwpercelen max 1,5 ha — a blanket exclusion would contradict its own "
            "lid 2), art. 8.2 (Landbouwontwikkelingsgebied: kan-mits 2,5 ha) and "
            "art. 8.5 (Concentratiegebied glastuinbouw: plans may not hinder "
            "glastuinbouw). Art. 8.4 (geitenhouderij) is a province-wide verbod "
            "without gebiedsaanwijzing: motivatedly abstained (no zone predicate; "
            "ALB-01). Programming-stage screening artifact; per-location permission "
            "assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Art. 8.4 (geitenhouderij) is a province-wide verbod without "
            "gebiedsaanwijzing: the engine refuses zone-less exclusion rules, so it "
            "is abstained under cite-or-abstain (ALB-01; heroverwegingskandidaat "
            "voor een zone-loos verbod-rule-kind).",
            "The art. 8.3/8.6/8.7 exclusions apply the protective default per "
            "activity scope: art. 8.3 names niet-grondgebonden expansion only "
            "(grondgebonden businesses stay V4-assessable), art. 8.6 keeps the "
            "tenzij-verplaatsing and the lid-2 kan-mits 2-ha expansion, art. 8.7 "
            "keeps graslandvernieuwing/blijvende teelt outside the verbod.",
            "The art. 8.5 marker is protective (it forbids PLANS from hindering "
            "glastuinbouw) and the art. 8.1 marker mixes a verbod with a "
            "voorschrift; both are plan-content assessments routed to the V4 "
            "human-expert checkpoint, never area eliminations.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
    "wonen": {
        "shard": "corpus/evidence-wonen.json",
        "ledger": "corpus/normcards-rejected-wonen.json",
        "report_title": "Where is housing development possible under the wonen instructieregels in province Utrecht?",
        "decision_table_id": "DT-wonen-utrecht-poc1",
        "decision_table_title": "Wonen rule bounds for housing development "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:wonen:",
        "headline_note": (
            "Semantics: the opportunity zone is the inclusion composition — "
            "Stedelijk gebied (art. 9.17), Kernrandzone (art. 9.10) and the "
            "Gebied uitbreiding woningbouw onder voorwaarden mogelijk "
            "(arts. 9.14/9.14a/9.15: 50-woningen-vitaliteit, flexwoningen, "
            "woningbouw onder voorwaarden) — the verordeningeigen exceptions to "
            "the core art.-9.3 verstedelijkingsverbod in het Landelijk gebied. "
            "The verbod itself is a conditional marker: its tenzij ('tenzij in "
            "deze verordening anders is bepaald') is operationalized by those "
            "inclusions, and executing it as an exclusion would erase the "
            "exception zones (engine applies inclusion-then-exclusion). "
            "Art. 9.8 (Gebied recreatiewoning) is a conditional marker: its "
            "verbod is OBJECT-scoped (omvorming van bestaande recreatiewoningen "
            "tot permanente bewoning), not an area-wide housing refusal over "
            "the landelijk-gebied-wide designation (1245.814 km2) — an "
            "exclusion would nullify the housing exceptions (FR-MO-05-mirror). "
            "Arts. 9.6/9.12/9.13 (kan-mits wonen in het Landelijk gebied) and "
            "9.27/9.29 (rekening-houden stiltegebied, fase-1-aliases hergebruikt) "
            "are conditional markers. Werken/recreatie-regels (9.16-9.23), de "
            "[Gereserveerde] 9.21, de bebouwingsenclaves-gap (9.7, geen GIO) en "
            "de vergunningsketen van paragraaf 9.4.2 zijn gemotiveerd "
            "onthouden (AWN-03/04/06/07/10). Programming-stage screening "
            "artifact; per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Werken/recreatie-regels (arts. 9.16, 9.18-9.20 kantoren/detailhandel/"
            "bedrijventerreinen en 9.22/9.23 recreatie) are zone-gebonden but "
            "outside the housing_development object type: abstained with fase-4 "
            "werken/recreatie-track heroverwegingsnotities (AWN-04/07).",
            "The art. 9.3 verbod is a conditional marker: its verordening-brede "
            "tenzij is operationalized by the inclusion composition (FR-WN-04/"
            "07/08/09/10); outside those zones and the Stedelijk gebied the "
            "verbod remains the default. Art. 9.8 is object-scoped (omvorming "
            "van bestaande recreatiewoningen; designation 1245.814 km2 = de "
            "landelijk-gebied-omvang) and therefore a marker, not an "
            "exclusion — otherwise the housing exceptions would be "
            "nullified.",
            "Bebouwingsenclaves/-linten (art. 9.7) have no registered GIO/NAAM "
            "(AWN-03): gap, no surrogate alias. Art. 9.21 is [Gereserveerd]. "
            "Art. 9.48a exists only as a toelichting reference, not as a body "
            "article (AWN-11).",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
}

_LIMITATIONS = [
    "GIO geometry via the DSO Omgevingsdocumenten Downloaden API is key-gated (HTTP 401, verified); "
    "provincial zones are therefore served by the province's own vigerende-verordening open data "
    "(agrest Omgevingsverordening FeatureServer, IMOW ids + AKN DOCUMENT_URL) as provenance aliases of "
    "the Bijlage-II join-ids cited on each NormCard.",
    "Natura 2000 geometry is the 2021 national designation layer (14 features, province hub copy), not a "
    "provincial instrument; ganzenrustgebieden come from the verordening's own designation set.",
    "A major verordening/visie amendment is in progress (PS decision expected 18-11-2026, in werking "
    "01-01-2027): re-run the legal recon and this pipeline before using results after that date.",
    "Map geometry in this report is display-simplified; authoritative full-resolution geometry is "
    "zones.geojson / zones.gml in the run directory.",
    "Zone algebra inputs are Douglas-Peucker simplified (tolerance recorded per run in run_summary.json "
    "tunings and per layer in the engine provenance) so province-scale GEOS overlays stay tractable; at "
    "the recorded 2 m tolerance the final area shifts by ~0.002% versus full resolution.",
]

# engine operation -> zone-result contract operation
_OP_MAP = {
    "intersection": "intersection",
    "inclusion_union": "union",
    "union": "union",
    "difference": "difference",
    "final": "difference",
    "attention_mark": "buffer",
    "conditional_mark": "union",
    "compensation_mark": "union",
}


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump_json(path: Path, obj: Any, indent: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    return path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class RunLog:
    """Collects PROV activities (stages) with wall-clock timestamps."""

    def __init__(self) -> None:
        self.activities: List[Dict[str, Any]] = []

    def stage(self, name: str, label: str, agent: str, used: Sequence[str] = (), generated: Sequence[str] = ()):
        log = self

        class _Ctx:
            def __enter__(self2):
                self2.started = time.time()
                self2.started_iso = utcnow()
                return self2

            def __exit__(self2, *exc):
                log.activities.append(
                    {
                        "id": name,
                        "label": label,
                        "type": name,
                        "agent": agent,
                        "startedAt": self2.started_iso,
                        "endedAt": utcnow(),
                        "durationS": round(time.time() - self2.started, 3),
                        "used": list(used),
                        "generated": list(generated),
                    }
                )
                return False

        return _Ctx()


# --------------------------------------------------------------------------- #
# stage implementations
# --------------------------------------------------------------------------- #

def load_request(use_case: str, bbox=None) -> Dict[str, Any]:
    path = POC_ROOT / "use-cases" / f"{use_case}.json"
    if not path.is_file():
        raise SystemExit(f"unknown use case {use_case!r}: {path} not found")
    request = json.loads(path.read_text(encoding="utf-8"))
    contracts.validate(request, "opportunity-map-request")
    OpportunityMapRequest.from_dict(request)  # round-trip check
    if bbox is not None:
        aoi = shape(request["areaOfInterest"]["geometry"])
        clipped = aoi.intersection(box(*bbox))
        # __geo_interface__ yields tuples; the JSON Schema requires arrays
        clipped_geojson = json.loads(json.dumps(clipped.__geo_interface__))
        request = dict(request)
        request["areaOfInterest"] = {
            "geometry": clipped_geojson,
            "crs": request["areaOfInterest"].get("crs", "EPSG:28992"),
        }
        request.setdefault("parameters", {})
        request["parameters"]["bboxClip"] = list(bbox)
        contracts.validate(request, "opportunity-map-request")
    return request


def fetch_layers(
    zone_ids: Sequence[str],
    *,
    refresh: bool,
    bbox=None,
    timeout: float = 120.0,
    geo_bindings: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """Fetch every zone layer; returns (layers, manifest, degradations, source_of_zone)."""
    sources_registry = geodata.load_sources()
    by_source: Dict[str, Dict[str, Any]] = {}
    layers: Dict[str, Dict[str, Any]] = {}
    manifest: Dict[str, Dict[str, Any]] = {}
    degradations: List[Dict[str, Any]] = []
    source_of_zone: Dict[str, str] = {}

    for zone in zone_ids:
        spec = ZONE_SOURCES.get(zone)
        if spec is None:
            degradations.append(
                {"kind": "zone-alias", "zone": zone,
                 "error": f"no open-data alias registered for zone {zone!r}"}
            )
            continue
        sid = spec["sourceId"]
        source_of_zone[zone] = sid
        if sid in by_source:
            layers[zone] = by_source[sid]
        else:
            try:
                fc = geodata.fetch_layer(sid, bbox=bbox, refresh=refresh, sources=sources_registry, timeout=timeout)
            except geodata.GeoDataError as exc:
                by_source[sid] = None  # remember failure
                degradations.append({"kind": "layer-fetch", "zone": zone, "sourceId": sid, "error": str(exc)})
                continue
            except Exception as exc:  # unexpected transport failure -> degrade, never crash
                by_source[sid] = None
                degradations.append({"kind": "layer-fetch", "zone": zone, "sourceId": sid,
                                     "error": f"{type(exc).__name__}: {exc}"})
                continue
            by_source[sid] = fc
            layers[zone] = fc
        fc = layers[zone]
        props = fc.get("properties") or {}
        reg = sources_registry.get(sid, {})
        binding = (geo_bindings or {}).get(zone) or {}
        manifest[zone] = {
            "zoneId": zone,
            "aliasSourceId": sid,
            "serviceUrl": props.get("serviceUrl"),
            "layerId": props.get("layerId"),
            "title": props.get("title") or reg.get("title"),
            "role": props.get("role") or reg.get("role"),
            "authoritative": props.get("authoritative", reg.get("authoritative")),
            "licenseNote": props.get("licenseNote") or reg.get("licenseNote"),
            "where": props.get("where"),
            "featureCount": props.get("featureCount"),
            "pages": props.get("pages"),
            "fetchedAt": props.get("fetchedAt"),
            "lastChecked": props.get("lastChecked") or reg.get("lastChecked"),
            "cachePath": str(geodata.DEFAULT_CACHE_DIR / f"{sid}.28992.geojson"),
            "aliasNote": spec["note"],
            "geoBinding": {
                "geometrySource": binding.get("geometrySource"),
                "gioJoinId": binding.get("gioJoinId"),
                "caveat": binding.get("caveat"),
            },
        }
    return layers, manifest, degradations, source_of_zone


def rule_zones(rule: Mapping[str, Any]) -> List[str]:
    zs = rule.get("zoneSelector") or {}
    zones = list(zs.get("zoneIds") or [])
    if zs.get("derivedFrom"):
        zones.append(zs["derivedFrom"])
    seen: set = set()
    out = []
    for z in zones:
        if z not in seen:
            seen.add(z)
            out.append(z)
    return out


def wrap_contract_zones(rich_zones: Sequence[Mapping[str, Any]], request_id: str) -> List[Dict[str, Any]]:
    now = utcnow()
    out = []
    for z in rich_zones:
        op = str(z.get("operation", "none"))
        mapped = _OP_MAP.get(op, "none")
        if op == "final":
            mapped = "difference" if any(z2.get("operation") == "difference" for z2 in rich_zones) else "union"
        rid = str(z.get("id", "zr-?"))
        if rid.startswith("zr-"):
            rid = "ZR-" + rid[3:]
        payload = (z.get("geometry") or {}).get("payload")
        out.append(
            {
                "id": rid,
                "requestId": request_id,
                "ruleIds": list(z.get("ruleIds") or []),
                "operation": mapped,
                "geometry": {
                    "format": "GeoJSON",
                    "payload": payload,
                    "crs": "EPSG:4326",
                },
                "geometryValid": bool(z.get("geometryValid")),
                "areaKm2": z.get("areaKm2"),
                "operands": [str(o) for o in (z.get("layers") or z.get("operands") or [])],
                "provenance": str(z.get("prov") or z.get("provenance") or ""),
                "computedBy": "geo-analyst#poc-zone-engine-0.1",
                "computedAt": now,
            }
        )
    for zone in out:
        contracts.validate(zone, "zone-result")
    return out


def per_rule_stats(rules: Sequence[Mapping[str, Any]], layers: Mapping[str, Any], aoi) -> List[Dict[str, Any]]:
    """Informational per-rule footprint (zone union, buffered, intersected with AOI)."""
    stats = []
    for r in rules:
        zs = r.get("zoneSelector") or {}
        lids = [z for z in (zs.get("zoneIds") or []) if z in layers]
        if zs.get("derivedFrom") and zs["derivedFrom"] in layers:
            lids.append(zs["derivedFrom"])
        if not lids:
            continue
        geoms = []
        for lid in lids:
            for f in layers[lid].get("features", []):
                g = f.get("geometry")
                if g is not None:
                    geoms.append(shape(g))
        if not geoms:
            continue
        u = unary_union(geoms)
        dist = float(zs.get("bufferDistanceM") or 0)
        if dist > 0:
            u = u.buffer(dist, quad_segs=engine.BUFFER_RESOLUTION)
        clipped = u.intersection(aoi) if aoi is not None else u
        stats.append(
            {
                "ruleId": r["id"],
                "zoneSemantics": r.get("zoneSemantics"),
                "zones": lids,
                "bufferM": dist or None,
                "features": len(geoms),
                "zoneAreaKm2": round(u.area / 1e6, 3),
                "zoneIntersectAoiKm2": round(clipped.area / 1e6, 3),
            }
        )
    return stats


def count_repairs(steps: Sequence[str]) -> int:
    total = 0
    for step in steps or []:
        for m in re.finditer(r"make_valid_repairs=(\d+)", str(step)):
            total += int(m.group(1))
    return total


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--use-case", default="wind",
                    help="use case id (default: wind; wind=wind turbines, zon=solar fields, "
                         "bos=new nature/forest planting, water=riparian development, "
                         "bodem=soil activity)")
    ap.add_argument("--refresh", action="store_true", help="ignore the layer cache and re-download live layers")
    ap.add_argument("--bbox", default=None,
                    help="optional clip xmin,ymin,xmax,ymax in EPSG:28992 applied to the AOI")
    ap.add_argument("--out", default=None, help="output directory (default: poc/runs/<timestamp>-<usecase>)")
    ap.add_argument("--display-tolerance-m", type=float, default=report.DEFAULT_DISPLAY_TOLERANCE_M,
                    help="Douglas-Peucker tolerance (m) for report display geometry (default 25)")
    ap.add_argument("--input-simplify-m", type=float, default=2.0,
                    help="Douglas-Peucker tolerance (m, EPSG:28992) applied to fetched layer geometries "
                         "before the zone algebra so province-scale overlays stay tractable; recorded "
                         "per layer in the engine provenance and in the run summary (0 = full resolution)")
    ap.add_argument("--timeout", type=float, default=120.0, help="per-page HTTP timeout for layer fetches")
    ap.add_argument("--norm-analyst", choices=["deterministic", "llm"], default="deterministic",
                    help="Norm Analyst leg (S1): deterministic replay (default, offline) or "
                         "propose-only local open model (needs LDT_NORM_LLM_ENDPOINT; loud "
                         "fallback to deterministic on any transport failure)")
    ap.add_argument("--formalizer", choices=["deterministic", "llm"], default="deterministic",
                    help="Norm Formalizer leg (S2): deterministic templates (default) or gated "
                         "LLM proposals for template-less ambiguous cards (needs "
                         "LDT_NORM_LLM_ENDPOINT; loud fallback on any transport failure)")
    ap.add_argument("--skip-us", action="store_true",
                    help="skip Urban Strategy stiltegebied noise screening (wind track)")
    ap.add_argument("--refresh-us", action="store_true",
                    help="ignore poc/data/cache/us and re-invoke nldt us-* processes")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()
    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{run_ts}-{args.use_case}"
    run_dir = Path(args.out) if args.out else POC_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log = RunLog()
    tunings: List[Dict[str, Any]] = [
        {"k": "display_tolerance_m", "v": args.display_tolerance_m},
        {"k": "input_simplify_m", "v": args.input_simplify_m},
        {"k": "payload_coord_decimals", "v": 6},
        {"k": "buffer_resolution_quad_segs", "v": engine.BUFFER_RESOLUTION},
    ]
    degradations: List[Dict[str, Any]] = []

    print(f"[run] {run_id} -> {run_dir}")

    # ---------------- 1. intake ------------------------------------------- #
    with log.stage("intake", "Intake: load + validate OpportunityMapRequest", "run.py-orchestrator",
                  used=[f"use-cases/{args.use_case}.json"], generated=["request.json"]):
        bbox = None
        if args.bbox:
            parts = [float(p) for p in args.bbox.split(",")]
            if len(parts) != 4:
                raise SystemExit("--bbox must be xmin,ymin,xmax,ymax")
            bbox = parts
        request = load_request(args.use_case, bbox=bbox)
        dump_json(run_dir / "request.json", request)
        aoi = shape(request["areaOfInterest"]["geometry"])
        print(f"[intake] request {request['id']} objectType={request['objectType']} "
              f"stage={request['policyStage']} AOI={aoi.area/1e6:.3f} km2")

    # ---------------- 2. Norm Analyst ------------------------------------- #
    track_cfg = TRACKS.get(args.use_case)
    if track_cfg is None:
        raise SystemExit(f"unknown use case {args.use_case!r}: no track registered (known: {sorted(TRACKS)})")
    shard_rel = track_cfg["shard"]

    analyst_hook = None
    analyst_fallback = None
    if args.norm_analyst == "llm":
        try:
            analyst_hook = norm_llm.build_analyst_hook()
        except norm_llm.NormLLMError as exc:
            analyst_fallback = str(exc)
            print(f"[norm-analyst] LLM leg requested but unavailable — LOUD FALLBACK to "
                  f"deterministic replay ({analyst_fallback})")

    with log.stage("norm-analyst", "Norm Analyst: harvest NormCards (deterministic replay)",
                   agents.NormAnalyst.agent_name, used=[shard_rel, "corpus/sources.json"],
                   generated=["normcards.json", "normcards-rejected.json"]):
        analyst = agents.NormAnalyst(llm_hook=analyst_hook)
        cards_obj = analyst.read(POC_ROOT / shard_rel)
        cards = [c.to_dict() for c in cards_obj]
        for c in cards:
            contracts.validate(c, "norm-card")
        rejected_ledger = json.loads((POC_ROOT / track_cfg["ledger"]).read_text(encoding="utf-8"))
        rejected_ledger["analystRejectedThisRun"] = analyst.rejected
        dump_json(run_dir / "normcards.json", cards, indent=1)
        dump_json(run_dir / "normcards-rejected.json", rejected_ledger, indent=1)
        llm_note = ""
        if analyst_hook is not None:
            llm_note = (f"; S1 llm leg: {analyst_hook.accepted} accepted, "
                        f"{len(analyst_hook.rejected)} rejected")
        print(f"[norm-analyst] {len(cards)} verified NormCards, "
              f"{len(rejected_ledger.get('abstentions', []))} abstentions, "
              f"{len(analyst.rejected)} rejected evidence items{llm_note}")

    # ---------------- 3. Norm Formalizer ---------------------------------- #
    formalizer_hook = None
    formalizer_fallback = None
    if args.formalizer == "llm":
        allowed_zones = set(ZONE_SOURCES)
        for _eid, spec in agents.TEMPLATE_SPECS.items():
            allowed_zones.update((spec.get("zone") or {}).get("zoneIds") or [])
        try:
            formalizer_hook = norm_llm.build_formalizer_hook(sorted(allowed_zones))
        except norm_llm.NormLLMError as exc:
            formalizer_fallback = str(exc)
            print(f"[norm-formalizer] LLM leg requested but unavailable — LOUD FALLBACK to "
                  f"deterministic templates ({formalizer_fallback})")

    with log.stage("norm-formalizer", "Norm Formalizer: NormCards -> FormalRules (deterministic templates)",
                   agents.NormFormalizer.agent_name, used=["normcards.json"], generated=["formalrules.json"]):
        formalizer = agents.NormFormalizer(llm_hook=formalizer_hook)
        rules_obj = formalizer.formalize(cards_obj)
        rules = [r.to_dict() for r in rules_obj]
        for r in rules:
            contracts.validate(r, "formal-rule")
        dump_json(run_dir / "formalrules.json", rules, indent=1)
        cov = formalizer.last_coverage
        llm_note = ""
        if formalizer_hook is not None:
            llm_note = (f"; S2 llm leg: {cov['llm_proposed']} proposed, "
                        f"{cov['llm_rejected']} rejected")
        print(f"[norm-formalizer] {cov['output_rules']} rules: {cov['formalized']} formalized, "
              f"{cov['ambiguous']} ambiguous, {cov['rejected']} rejected{llm_note}")

    if args.norm_analyst == "llm" or args.formalizer == "llm":
        dump_json(run_dir / "norm-llm-ledger.json", {
            "requested": {"normAnalyst": args.norm_analyst, "formalizer": args.formalizer},
            "analyst": {
                "fallback": analyst_fallback,
                "accepted": analyst_hook.accepted if analyst_hook else 0,
                "rejected": analyst_hook.rejected if analyst_hook else [],
                "stamp": analyst_hook.stamp if analyst_hook else None,
            },
            "formalizer": {
                "fallback": formalizer_fallback,
                "accepted": formalizer_hook.accepted if formalizer_hook else 0,
                "rejected": formalizer_hook.rejected if formalizer_hook else [],
                "stamp": formalizer_hook.stamp if formalizer_hook else None,
                "coverage": formalizer.last_coverage,
            },
        }, indent=1)

    # geo bindings per zone (provenance aliases for the GIO join-ids)
    geo_bindings: Dict[str, Dict[str, Any]] = {}
    for c in cards:
        gb = c.get("geoBinding") or {}
        for z in gb.get("zoneIds", []):
            geo_bindings.setdefault(
                z,
                {
                    "geometrySource": gb.get("geometrySource"),
                    "gioJoinId": gb.get("gioJoinId"),
                    "caveat": gb.get("caveat"),
                },
            )

    # ---------------- 4. Geo Analyst: fetch layers ------------------------ #
    formalized = [r for r in rules if r.get("status") == "formalized"]
    needed_zones: List[str] = []
    for r in formalized:
        for z in rule_zones(r):
            if z not in needed_zones:
                needed_zones.append(z)
    with log.stage("geo-analyst-fetch", "Geo Analyst: fetch zone layers (cache-first ArcGIS REST)",
                   geodata.USER_AGENT.split(" ")[0], used=["data/sources.json"],
                   generated=["layers.json"]):
        layers, manifest, fetch_degrades, source_of_zone = fetch_layers(
            needed_zones, refresh=args.refresh, bbox=bbox, timeout=args.timeout, geo_bindings=geo_bindings
        )
        degradations.extend(fetch_degrades)
        dump_json(run_dir / "layers.json", manifest, indent=1)
        total_feats = sum((fc.get("properties") or {}).get("featureCount", 0) for fc in layers.values())
        print(f"[geo] {len(layers)}/{len(needed_zones)} zone layers resolved "
              f"({total_feats} features); {len(fetch_degrades)} degradation(s)")

    # ---------------- 5. zone engine --------------------------------------- #
    # Recorded tuning: province-scale multipolygons (NNN 390 polygons against a
    # ~1300 km2 inclusion union) make GEOS overlays intractable at full source
    # resolution; simplify inputs deterministically (recorded per layer in the
    # engine provenance via properties.simplifiedM) before the zone algebra.
    if args.input_simplify_m and args.input_simplify_m > 0:
        layers, simplify_notes = engine.simplify_layers(layers, args.input_simplify_m)
        aoi = aoi.simplify(args.input_simplify_m, preserve_topology=True)
        for zone in manifest:
            manifest[zone]["inputSimplifyM"] = args.input_simplify_m
        dump_json(run_dir / "layers.json", manifest, indent=1)

    engine_rules = []
    for r in formalized:
        missing = [z for z in rule_zones(r) if z not in layers]
        if missing:
            degradations.append(
                {"kind": "rule-dropped", "rule": r["id"], "zones": missing,
                 "error": "zone layer unavailable this run; rule excluded from deterministic execution "
                          "and flagged for human review"}
            )
        else:
            engine_rules.append(r)
    sources_prov = {
        zone: {
            "serviceUrl": (fc.get("properties") or {}).get("serviceUrl"),
            "layerId": (fc.get("properties") or {}).get("layerId"),
            "lastChecked": (fc.get("properties") or {}).get("lastChecked"),
        }
        for zone, fc in layers.items()
    }
    with log.stage("zone-engine", "Geo Analyst: deterministic FormalRule execution (shapely path)",
                   "zone-engine", used=["formalrules.json", "layers.json"], generated=["zones.json"]):
        attempts = 0
        while True:
            try:
                rich_zones = engine.execute_rules(engine_rules, layers, aoi=aoi, sources=sources_prov,
                                                  payload_round_dp=6)
                break
            except engine.RuleError as exc:
                attempts += 1
                if attempts > 6:
                    raise
                msg = str(exc)
                dropped = None
                for r in engine_rules:
                    if r["id"] in msg:
                        dropped = r
                        break
                if dropped is None:
                    raise
                degradations.append({"kind": "rule-dropped", "rule": dropped["id"], "error": msg})
                engine_rules.remove(dropped)
                print(f"[engine] dropped rule {dropped['id']} after RuleError: {msg[:140]}")
        final_rich = next(z for z in rich_zones if z.get("operation") == "final")
        # Marker-only tracks (bodem: every formalized rule is a conditional/
        # context marker, nothing is eliminated) seed the final zone from the
        # AOI, so the engine's final carries no core rule id — but the
        # zone-result contract requires non-empty ruleIds. Stamp the executed
        # rules (the rules that bound the final zone) on the final only.
        if not final_rich.get("ruleIds"):
            final_rich["ruleIds"] = [r["id"] for r in engine_rules]
        inclusion_zone = next(
            (z for z in rich_zones if z.get("operation") == "intersection"),
            next((z for z in rich_zones if z.get("operation") == "inclusion_union"), None),
        )
        contract_zones = wrap_contract_zones(rich_zones, request["id"])
        dump_json(run_dir / "zones.json", contract_zones, indent=1)
        rule_stats = per_rule_stats(engine_rules, layers, aoi)
        dump_json(run_dir / "rule-stats.json", rule_stats, indent=1)
        print(f"[engine] {len(rich_zones)} zones; inclusion\u2229AOI="
              f"{(inclusion_zone['areaKm2'] if inclusion_zone else float('nan')):.3f} km2; "
              f"final={final_rich['areaKm2']:.3f} km2")

    # ---------------- 6. Cartographer --------------------------------------- #
    with log.stage("cartographer", "Cartographer: zones.geojson + GML + report input",
                   cartographer.CARTOGRAPHER_VERSION, used=["zones.json"],
                   generated=["zones.geojson", "zones.gml"]):
        gj = cartographer.write_geojson(rich_zones, run_dir / "zones.geojson")
        gml = cartographer.write_gml(gj)
        if not gml["ok"]:
            print(f"[cartographer] GML export degraded: {gml['error']}")
        report_input = cartographer.build_report_input(
            rich_zones, sources=sources_prov,
            outputs={"geojson": str(gj), "gml": gml["path"] if gml["ok"] else None, "gmlStatus": gml},
            title=track_cfg["report_title"],
        )
        dump_json(run_dir / "report_input.json", report_input, indent=1)

    # ---------------- 6b. Urban Strategy stiltegebied screen (wind) ---------- #
    us_eval: Optional[Dict[str, Any]] = None
    if args.use_case == "wind" and not args.skip_us:
        with log.stage(
            "urbanstrategy-stiltegebied",
            "Urban Strategy: art. 9.26 stiltegebied noise exceedance screen (decision-support)",
            "usstep",
            used=["layers.json"],
            generated=["urbanstrategy-stiltegebied.json"],
        ):
            try:
                from pipeline import usstep

                stilte_4326 = None
                twin = geodata.DEFAULT_CACHE_DIR / "agrest-ov-stiltegebied.4326.geojson"
                if twin.exists():
                    stilte_4326 = json.loads(twin.read_text(encoding="utf-8"))
                elif "stiltegebied" in layers:
                    stilte_4326 = geodata.feature_collection_to_wgs84(layers["stiltegebied"])
                if stilte_4326 is None:
                    degradations.append({
                        "kind": "urbanstrategy-skipped",
                        "error": "stiltegebied layer unavailable for US screen",
                    })
                    print("[us] skipped: stiltegebied layer unavailable")
                else:
                    us_eval = usstep.stiltegebied_noise_screen(
                        stilte_4326, refresh=args.refresh_us,
                    )
                    dump_json(run_dir / "urbanstrategy-stiltegebied.json", us_eval, indent=1)
                    c = us_eval["counts"]
                    print(
                        f"[us] stiltegebied screen: {c['receptorsTotal']} receptors; "
                        f"{c['exceedancesTotal']} exceedance(s) "
                        f"(kern={c['exceedancesStilleKern']}, buf={c['exceedancesBufferzone']})"
                    )
            except Exception as exc:  # noqa: BLE001 — degrade, never flip verdict
                degradations.append({
                    "kind": "urbanstrategy-error",
                    "error": str(exc)[:500],
                })
                print(f"[us] degraded: {exc}")

    # ---------------- 7. Critic ---------------------------------------------- #
    with log.stage("critic", "Critic/Validator: V0-V3 deterministic + V4 pending",
                   critic.Critic.agent_name,
                   used=["request.json", "normcards.json", "formalrules.json", "zones.json", "decision-table.json"],
                   generated=["validation.json"]):
        critic_obj = critic.Critic()
        reports_l = critic_obj.evaluate_run(
            request=request,
            normcards=cards,
            formalrules=rules,
            zones=contract_zones,
            decision_table=None,  # replaced below after the explainer runs
            layers=layers,
            aoi=aoi,
            engine_rules=engine_rules,
            final_zone=final_rich,
            inclusion_area_m2=inclusion_zone["areaM2"] if inclusion_zone else None,
            degradations=degradations,
            run_id=run_id,
            track=args.use_case,
        )
        verdict0 = reports_l[-1]["verdict"]
        print(f"[critic] pre-explainer pipeline verdict: {verdict0}")

    # ---------------- 8. Explainer ------------------------------------------- #
    with log.stage("explainer", "Explainer: decision table + PROV bundle",
                   explainer.Explainer.agent_name,
                   used=["normcards.json", "formalrules.json", "zones.json"],
                   generated=["decision-table.json", "decision-table.md", "prov.json"]):
        expl = explainer.Explainer()
        prov_narrative = (
            f"run {run_id} of {RUN_VERSION}; norm corpus poc/{shard_rel} replayed by "
            f"{agents.ANALYST_RUN}; rules by {agents.FORMALIZER_RUN}; instrument {INSTRUMENT}; "
            f"zone geometry from provincial open data (agrest Omgevingsverordening FeatureServer + "
            f"province ArcGIS hub), lastChecked stamps in layers.json; full PROV in prov.json"
        )
        dt = expl.build_decision_table(
            request=request, normcards=cards, formalrules=rules,
            generated_at=utcnow(), prov_narrative=prov_narrative,
            table_id=track_cfg["decision_table_id"], title=track_cfg["decision_table_title"],
        )
        dump_json(run_dir / "decision-table.json", dt, indent=1)
        (run_dir / "decision-table.md").write_text(expl.decision_table_markdown(dt), encoding="utf-8")

        # re-run the critic with the decision table included (V0+V2 over it)
        reports_l = critic_obj.evaluate_run(
            request=request,
            normcards=cards,
            formalrules=rules,
            zones=contract_zones,
            decision_table=dt,
            layers=layers,
            aoi=aoi,
            engine_rules=engine_rules,
            final_zone=final_rich,
            inclusion_area_m2=inclusion_zone["areaM2"] if inclusion_zone else None,
            degradations=degradations,
            run_id=run_id,
            track=args.use_case,
        )
        vdir = run_dir / "validation"
        for vr in reports_l:
            dump_json(vdir / f"{vr['artifactType']}.json", vr, indent=1)
        dump_json(run_dir / "validation.json", reports_l, indent=1)
        verdict = reports_l[-1]["verdict"]
        print(f"[critic] pipeline verdict: {verdict}")

        # PROV bundle (hashes over what is already on disk)
        ent = [
            explainer.entity_for(run_dir / "request.json", "OpportunityMapRequest"),
            explainer.entity_for(POC_ROOT / shard_rel, "evidence shard"),
            explainer.entity_for(POC_ROOT / "corpus" / "sources.json", "document source registry"),
            explainer.entity_for(POC_ROOT / "data" / "sources.json", "geo source registry"),
            explainer.entity_for(run_dir / "normcards.json", "NormCard[]"),
            explainer.entity_for(run_dir / "normcards-rejected.json", "cite-or-abstain ledger"),
            explainer.entity_for(run_dir / "formalrules.json", "FormalRule[]"),
            explainer.entity_for(run_dir / "layers.json", "layer manifest"),
            explainer.entity_for(run_dir / "zones.json", "ZoneResult[]"),
            explainer.entity_for(run_dir / "rule-stats.json", "per-rule footprint stats"),
            explainer.entity_for(gj, "zones GeoJSON (RFC 7946)"),
            explainer.entity_for(run_dir / "report_input.json", "cartographer report input"),
            explainer.entity_for(run_dir / "decision-table.json", "DecisionTable"),
            explainer.entity_for(run_dir / "decision-table.md", "DecisionTable (markdown)"),
            explainer.entity_for(run_dir / "validation.json", "ValidationReport[]"),
        ]
        us_path = run_dir / "urbanstrategy-stiltegebied.json"
        if us_path.exists():
            ent.append(explainer.entity_for(
                us_path,
                "Urban Strategy stiltegebied noise screen (NC-W-11 annex)",
            ))
        if gml["ok"]:
            ent.append(explainer.entity_for(Path(gml["path"]), "zones GML 3.2"))
        for zone, sid in sorted(source_of_zone.items()):
            cache = geodata.DEFAULT_CACHE_DIR / f"{sid}.28992.geojson"
            if cache.exists():
                ent.append(explainer.entity_for(cache, "layer cache (EPSG:28992)",
                                                {"zone": zone, "sourceId": sid}))
        prov = expl.build_prov(
            run_id=run_id,
            generated_at=utcnow(),
            request_id=str(request["id"]),
            namespace=track_cfg["prov_namespace"],
            agents=[
                ORCHESTRATOR_AGENT,
                {"id": "legal-recon-agent", "name": "NormAnalyst",
                 "version": (f"legal-recon-agent#{analyst_hook.stamp}" if analyst_hook else agents.ANALYST_RUN),
                 "role": "deterministic replay of the verified legal recon (agent #3)"
                         + (" + S1 gated llm claim/confidence proposals" if analyst_hook else "")},
                {"id": "norm-formalizer", "name": "NormFormalizer",
                 "version": (f"norm-formalizer#{formalizer_hook.stamp}" if formalizer_hook else agents.FORMALIZER_RUN),
                 "role": "deterministic templates (agent #4)"
                         + (" + S2 gated llm proposals for template-less cards" if formalizer_hook else "")},
                {"id": "geo-connector", "name": "GeoData connector", "version": geodata.USER_AGENT.split(" ")[0],
                 "role": "ArcGIS REST fetch, cache-first (agent #5 tool)"},
                {"id": "zone-engine", "name": "FormalRule zone engine", "version": engine.ENGINE_VERSION,
                 "role": "deterministic execution + validation repair provenance (agent #5)"},
                {"id": "cartographer", "name": "Cartographer", "version": cartographer.CARTOGRAPHER_VERSION,
                 "role": "GeoJSON/GML serialization (agent #6)"},
                {"id": "critic-validator", "name": "Critic/Validator", "version": critic.CRITIC_VERSION,
                 "role": "V0-V3 deterministic checks, V4 pending (agent #7)"},
                {"id": "explainer", "name": "Explainer", "version": explainer.EXPLAINER_VERSION,
                 "role": "decision table + PROV (agent #8)"},
                {"id": "report", "name": "HTML report renderer", "version": report.REPORT_VERSION,
                 "role": "single-file report (agent #6 view tier)"},
            ],
            activities=log.activities,
            entities=ent,
            derivations=[
                {"generatedEntity": "formalrules.json", "usedEntity": "normcards.json",
                 "note": "NormFormalizer deterministic templates"},
                {"generatedEntity": "normcards.json", "usedEntity": Path(shard_rel).name,
                 "note": "NormAnalyst replay (cite-or-abstain)"},
                {"generatedEntity": "zones.json", "usedEntity": "formalrules.json",
                 "note": "engine executed FormalRules over fetched layers"},
                {"generatedEntity": "decision-table.json", "usedEntity": "normcards.json",
                 "note": "every row links a normCardId"},
                {"generatedEntity": "validation.json", "usedEntity": "zones.json",
                 "note": "V0-V3 over the artifact tree"},
            ],
            sources=[
                {
                    "zone": zone,
                    "sourceId": sid,
                    "service": f"{(manifest[zone] or {}).get('serviceUrl')}/{(manifest[zone] or {}).get('layerId')}",
                    "lastChecked": (manifest[zone] or {}).get("lastChecked"),
                    "fetchedAt": (manifest[zone] or {}).get("fetchedAt"),
                    "features": (manifest[zone] or {}).get("featureCount"),
                    "aliasFor": (manifest[zone] or {}).get("geoBinding", {}).get("gioJoinId")
                    or (manifest[zone] or {}).get("geoBinding", {}).get("geometrySource"),
                    "authoritative": (manifest[zone] or {}).get("authoritative"),
                }
                for zone, sid in sorted(source_of_zone.items())
            ],
        )
        dump_json(run_dir / "prov.json", prov, indent=1)

    # ---------------- 9. HTML report ----------------------------------------- #
    with log.stage("report", "Report: single-file HTML with Leaflet map + tables",
                   report.REPORT_VERSION,
                   used=["zones.geojson", "decision-table.json", "validation.json", "normcards.json", "prov.json"],
                   generated=["report.html"]):
        total_repairs = count_repairs(final_rich.get("provSteps"))
        verdicts = {vr["artifactType"]: vr["verdict"] for vr in reports_l}
        badges = [{"label": f"verdict: {verdict}", "cls": verdict},
                  {"label": "V4 human: pending", "cls": "pending"},
                  {"label": f"cite-or-abstain: {len(cards)} cards / {len(rejected_ledger.get('abstentions', []))} abstentions", "cls": ""}]
        headline = [
            {"k": "AOI (province)", "v": f"{aoi.area/1e6:,.1f} km\u00b2", "s": "Provinciegrens Utrecht (EPSG:28992)"},
            {"k": "Inclusion \u2229 AOI", "v": f"{inclusion_zone['areaKm2']:,.1f} km\u00b2" if inclusion_zone else "\u2014",
             "s": "union of the formalized inclusion zones"},
            {"k": "Final opportunity zone", "v": f"{final_rich['areaKm2']:,.1f} km\u00b2",
             "s": "after Natura 2000 / ganzenrust / NNN exclusions"},
            {"k": "Rules executed", "v": f"{len(engine_rules)} of {len(rules)}",
             "s": f"{cov['formalized']} formalized; {cov['ambiguous']} ambiguous \u2192 V4; {cov['rejected']} rejected"},
            {"k": "Zones emitted", "v": str(len(rich_zones)), "s": "incl. markers (attention/conditional/compensation)"},
            {"k": "Geometry repairs", "v": str(total_repairs), "s": "invalid-as-served features, recorded in prov"},
        ]
        zones_table = [
            {
                "id": z.get("id"),
                "operation": z.get("operation"),
                "ruleIds": z.get("ruleIds", []),
                "areaKm2": f"{z.get('areaKm2', 0):,.3f}",
                "layers": z.get("layers", []),
                "provSteps": len(z.get("provSteps") or []),
                "repairs": count_repairs(z.get("provSteps")),
            }
            for z in rich_zones
        ]
        validation_view = [
            {
                "id": vr["id"],
                "artifactType": vr["artifactType"],
                "verdict": vr["verdict"],
                "levels": [
                    {"name": name, "status": lvl["status"], "checks": lvl.get("checks") or [],
                     "notes": lvl.get("notes")}
                    for name, lvl in vr["levels"].items()
                ],
            }
            for vr in reports_l
        ]
        normcards_view = [
            {
                "id": c["id"], "article": c["source"]["article"], "instrument": c["instrument"],
                "legalForce": c["legalForce"], "confidence": c["confidence"], "claim": c["claim"],
                "quote": c["source"]["quote"], "uri": c["source"]["uri"], "docId": c["source"]["docId"],
                "version": c["source"]["version"], "theme": c["theme"],
                "zoneIds": (c.get("geoBinding") or {}).get("zoneIds"),
                "gioJoinId": (c.get("geoBinding") or {}).get("gioJoinId"),
                "caveat": (c.get("geoBinding") or {}).get("caveat"),
            }
            for c in cards
        ]
        map_data = report.build_map_data(rich_zones, request["areaOfInterest"]["geometry"],
                                         tolerance_m=args.display_tolerance_m)
        prov_view = {
            "activities": [
                {"label": a["label"], "agent": a["agent"], "startedAt": a["startedAt"],
                 "endedAt": a["endedAt"], "used": a["used"], "generated": a["generated"]}
                for a in log.activities
            ],
            "agents": [a for a in prov["agent"]],
            "sources": [
                {
                    "zone": s["zone"], "sourceId": s["sourceId"], "service": s["service"],
                    "features": s["features"], "lastChecked": s["lastChecked"],
                    "aliasFor": s["aliasFor"] or "(national source)",
                }
                for s in prov["hadPrimarySource"]
            ],
        }
        limitations = list(_LIMITATIONS) + list(
            track_cfg["limitations"](cov, rejected_ledger.get("abstentions", []))
        )
        for d in degradations:
            limitations.append(f"Degradation this run: {json.dumps(d, ensure_ascii=False)}")
        report_data = {
            "run": {
                "title": track_cfg["report_title"],
                "run_id": run_id,
                "use_case": args.use_case,
                "generated_at": utcnow(),
                "policy_stage": request["policyStage"],
                "instrument": INSTRUMENT,
                "badges": badges,
            },
            "headline": headline,
            "headline_note": track_cfg["headline_note"],
            "map": map_data,
            "zones_table": zones_table,
            "decision": {"columns": dt["columns"], "rows": dt["rows"]},
            "validation": validation_view,
            "normcards": normcards_view,
            "abstentions": rejected_ledger.get("abstentions", []),
            "prov": prov_view,
            "limitations": limitations,
            "tunings": tunings,
            "paths": {"listing": " / ".join(sorted(p.name for p in run_dir.iterdir() if p.is_file()))},
        }
        report.write_report(run_dir / "report.html", report_data)

    # ---------------- 9b. PROV completion for late artifacts ------------------ #
    # The PROV bundle (stage 8) hashes only what is on disk when it is built;
    # report.html, the per-artifact validation reports and zones.xsd are
    # written after it, and the explainer/report activities complete only when
    # their stage blocks exit. Complete the bundle here — before
    # run_summary.json hashes prov.json — so every artifact file in the run
    # directory is a PROV entity. prov.json and run_summary.json are recorded
    # without sha256 (a file cannot contain its own hash); their integrity is
    # carried by run_summary.json's artifact list and the bundle's own entity
    # hashes of every other file.
    prov["activity"] = list(log.activities)
    activity_ids = {a.get("id") for a in prov["activity"]}
    existing_ids = {e["id"] for e in prov["entity"]}

    def _late_entity(rel: str, etype: str, *, with_sha: bool = True,
                     note: str = "") -> Dict[str, Any]:
        p = run_dir / rel
        ent_late: Dict[str, Any] = {"id": rel, "type": etype, "path": str(p)}
        if with_sha and p.exists():
            ent_late["sha256"] = sha256_of(p)
        if note:
            ent_late["note"] = note
        return ent_late

    late_entities = [_late_entity(f"validation/{vr['artifactType']}.json", "ValidationReport")
                     for vr in reports_l]
    if (run_dir / "zones.xsd").exists() and "zones.xsd" not in existing_ids:
        late_entities.append(explainer.entity_for(run_dir / "zones.xsd",
                                                  "zones GML 3.2 XML schema"))
    late_entities.extend([
        _late_entity("report.html", "single-file HTML report"),
        _late_entity("prov.json", "PROV bundle (this file)", with_sha=False,
                     note="self-referential; integrity via run_summary.json artifact hashes"),
        _late_entity("run_summary.json",
                     "run summary (headline, tunings, artifact hashes)", with_sha=False,
                     note="written after prov.json; its sha256 lives in its own artifacts list"),
    ])
    prov["entity"].extend(e for e in late_entities if e["id"] not in existing_ids)
    ent_ids = {e["id"] for e in prov["entity"]}
    late_links = [(f"validation/{vr['artifactType']}.json", "critic") for vr in reports_l] + [
        ("zones.xsd", "cartographer"), ("report.html", "report"), ("prov.json", "explainer"),
    ]
    for rel, act in late_links:
        if rel in ent_ids and act in activity_ids and not any(
                w.get("entity") == rel for w in prov["wasGeneratedBy"]):
            prov["wasGeneratedBy"].append({"entity": rel, "activity": act,
                                           "time": utcnow()})
    dump_json(run_dir / "prov.json", prov, indent=1)

    # ---------------- 10. run summary ---------------------------------------- #
    artifacts = sorted(p for p in run_dir.iterdir() if p.is_file())
    summary = {
        "runId": run_id,
        "useCase": args.use_case,
        "generatedAt": utcnow(),
        "durationS": round(time.time() - started, 1),
        "orchestrator": RUN_VERSION,
        "instrument": INSTRUMENT,
        "verdict": verdict,
        "verdicts": verdicts,
        "headline": {
            "aoiKm2": round(aoi.area / 1e6, 3),
            "inclusionIntersectAoiKm2": inclusion_zone["areaKm2"] if inclusion_zone else None,
            "finalOpportunityKm2": final_rich["areaKm2"],
            "rulesTotal": len(rules),
            "rulesExecuted": len(engine_rules),
            "zones": len(rich_zones),
            "geometryRepairs": total_repairs,
            "normCards": len(cards),
            "abstentions": len(rejected_ledger.get("abstentions", [])),
            "usStiltegebiedExceedances": (
                us_eval["counts"]["exceedancesTotal"] if us_eval else None
            ),
        },
        "perRule": rule_stats,
        "degradations": degradations,
        "tunings": tunings,
        "urbanstrategyStiltegebied": (
            {
                "exceedancesTotal": us_eval["counts"]["exceedancesTotal"],
                "inStilleKern": us_eval["counts"]["inStilleKern"],
                "normCardId": us_eval.get("normCardId"),
            }
            if us_eval
            else None
        ),
        "v3": next(
            (c["detail"] for vr in reports_l for lvl in vr["levels"].values()
             for c in lvl.get("checks", []) if c["id"] == "v3-reexecution-agreement"),
            None,
        ),
        "artifacts": [{"name": p.name, "path": str(p), "sha256": sha256_of(p),
                       "bytes": p.stat().st_size} for p in artifacts],
        "agents": prov["agent"],
    }
    dump_json(run_dir / "run_summary.json", summary, indent=1)

    # ---------------- console summary ---------------------------------------- #
    print()
    print("=" * 78)
    print(f"RUN {run_id} — verdict: {verdict.upper()}")
    print("=" * 78)
    rows = [
        ("AOI (province)", f"{aoi.area/1e6:,.3f} km2"),
        ("Inclusion ∩ AOI", f"{inclusion_zone['areaKm2']:,.3f} km2" if inclusion_zone else "—"),
        ("Final opportunity zone", f"{final_rich['areaKm2']:,.3f} km2"),
        ("Rules executed / total", f"{len(engine_rules)} / {len(rules)} "
         f"({cov['formalized']} formalized, {cov['ambiguous']} ambiguous→V4, {cov['rejected']} rejected)"),
        ("Zones emitted", str(len(rich_zones))),
        ("Geometry repairs (recorded)", str(total_repairs)),
        ("Verdicts", ", ".join(f"{k}={v}" for k, v in verdicts.items())),
    ]
    for k, v in rows:
        print(f"  {k:<28} {v}")
    if summary["v3"]:
        print(f"  {'V3 re-execution':<28} {summary['v3']}")
    if degradations:
        print(f"  DEGRADATIONS ({len(degradations)}):")
        for d in degradations:
            print(f"    - {json.dumps(d, ensure_ascii=False)[:160]}")
    print(f"  Duration {summary['durationS']}s; artifacts:")
    for p in artifacts:
        print(f"    {run_dir / p.name}")
    print("=" * 78)
    print(f"[report] open {run_dir / 'report.html'} (works from file://)")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        traceback.print_exc()
        print(f"[run] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
