#!/usr/bin/env python3
"""Integration-layer unit tests: critic (V0-V3), explainer, report renderer,
and the run.py orchestration helpers. Offline, deterministic, synthetic
fixtures only — no network.

Run from the workspace root:

    python3 -m unittest discover -s poc/tests
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = POC_ROOT.parent
for p in (str(POC_ROOT / "pipeline"), str(POC_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import engine  # noqa: E402
import geodata  # noqa: E402
import critic as critic_mod  # noqa: E402
import explainer as explainer_mod  # noqa: E402
import report as report_mod  # noqa: E402
import run as run_mod  # noqa: E402

from shapely.geometry import box, mapping, shape  # noqa: E402
from pipeline import contracts  # noqa: E402

X0, Y0 = 140000.0, 455000.0
CARD = {
    "id": "NC-W-05",
    "evidenceId": "W-05",
    "claim": "Within the Gebied windenergie an omgevingsplan may allow wind turbines of 3 MW or more under conditions.",
    "source": {
        "docId": "S07",
        "article": "art. 5.4, eerste lid",
        "version": "CVDR704250, geldend van 13-10-2025 t/m heden",
        "quote": "Een omgevingsplan dat betrekking heeft op locaties binnen het Gebied windenergie kan regels bevatten.",
        "uri": "https://lokaleregelgeving.overheid.nl/cvdr704250",
    },
    "instrument": "Omgevingsverordening provincie Utrecht (CVDR704250, geldend 13-10-2025)",
    "legalForce": "binding",
    "theme": "energy:wind-groot-inclusion",
    "confidence": 0.95,
    "verified": True,
    "extractedBy": "legal-recon-agent#cvdr704250-geldend-2025-10-13",
    "extractedAt": "2026-08-30",
    "appliesTo": {"objectType": "wind_turbine"},
}

RULE_FORMALIZED = {
    "id": "FR-W-05",
    "normCardId": "NC-W-05",
    "status": "formalized",
    "ruleType": "zone_inclusion",
    "zoneSemantics": "inclusion",
    "appliesTo": {"objectType": "wind_turbine"},
    "zoneSelector": {"zoneIds": ["incl"], "selection": "within", "geometrySource": "derived",
                     "bufferDistanceM": 10, "derivedFrom": "incl"},
    "conditions": [],
    "executableRef": "engine.zone.within@poc-v1",
    "rationale": "Article 5.4 permits turbines inside the Gebied windenergie designation (GIO Bijlage II).",
    "formalizedBy": "norm-formalizer#deterministic-templates-v1",
    "formalizedAt": "2026-08-30",
}

RULE_EXCL = {
    "id": "FR-W-08",
    "normCardId": "NC-W-05",
    "status": "formalized",
    "ruleType": "zone_exclusion",
    "zoneSemantics": "exclusion",
    "appliesTo": {"objectType": "wind_turbine"},
    "zoneSelector": {"zoneIds": ["excl"], "selection": "within", "geometrySource": "derived",
                     "bufferDistanceM": 5, "derivedFrom": "excl"},
    "conditions": [],
    "executableRef": "engine.zone.exclude_within@poc-v1",
    "rationale": "Toelichting to art. 5.4 excludes Natura 2000 and ganzenrust areas from the wind pathway.",
    "formalizedBy": "norm-formalizer#deterministic-templates-v1",
    "formalizedAt": "2026-08-30",
}

RULE_AMBIGUOUS = {
    "id": "FR-W-06",
    "normCardId": "NC-W-05",
    "status": "ambiguous",
    "ruleType": "procedural_condition",
    "zoneSemantics": "none",
    "appliesTo": {"objectType": "wind_turbine"},
    "reason": "Deviation path below 3 MW requires substantive justification; open norm.",
    "executableRef": "engine.procedural.human_review@poc-v1",
    "formalizedBy": "norm-formalizer#deterministic-templates-v1",
    "formalizedAt": "2026-08-30",
}


def fc(*geoms, source_id="fixture"):
    return {
        "type": "FeatureCollection",
        "name": source_id,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [
            {"type": "Feature", "id": i, "properties": {"fid": i}, "geometry": mapping(g)}
            for i, g in enumerate(geoms)
        ],
        "properties": {"sourceId": source_id, "serviceUrl": "https://example.test/FeatureServer",
                       "layerId": 0, "lastChecked": "2026-08-30T00:00:00Z"},
    }


def synth_env():
    aoi = box(X0, Y0, X0 + 400, Y0 + 400)
    layers = {
        "incl": fc(box(X0, Y0, X0 + 200, Y0 + 200), source_id="incl"),
        "excl": fc(box(X0 + 100, Y0 + 100, X0 + 160, Y0 + 160), source_id="excl"),
    }
    rules = [RULE_FORMALIZED, RULE_EXCL]
    zones = engine.execute_rules(rules, layers, aoi=mapping(aoi))
    return aoi, layers, rules, zones


def _polygon(geom):
    """GeoJSON dict with JSON-native lists (tuples would fail the schemas)."""
    return json.loads(json.dumps(mapping(geom)))


REQUEST = {
    "id": "0d9f61aa-4b8e-4f2f-9f6a-6f21cb53d001",
    "objectType": "wind_turbine",
    "areaOfInterest": {"geometry": _polygon(box(X0, Y0, X0 + 400, Y0 + 400)), "crs": "EPSG:28992"},
    "policyStage": "programming",
    "effortBudget": {"maxSubagents": 2},
    "requestedAt": "2026-08-30T00:00:00Z",
}


class TestCriticLevels(unittest.TestCase):
    def setUp(self):
        self.c = critic_mod.Critic()
        self.aoi, self.layers, self.rules, self.zones = synth_env()
        self.final = self.zones[-1]
        self.contract_zones = run_mod.wrap_contract_zones(self.zones, REQUEST["id"])

    def test_v0_pass_and_fail(self):
        checks = self.c.v0_checks({"norm-card": ("norm-card", [CARD])})
        self.assertEqual(checks[0]["status"], "pass")
        bad = dict(CARD)
        bad.pop("source")
        checks = self.c.v0_checks({"norm-card": ("norm-card", [bad])})
        self.assertEqual(checks[0]["status"], "fail")

    def test_v2_orphan_rule_flagged(self):
        orphan = dict(RULE_AMBIGUOUS)
        orphan["normCardId"] = "NC-W-99"
        checks = self.c.v2_checks([CARD], [RULE_FORMALIZED, orphan], self.contract_zones, None)
        linkage = next(ch for ch in checks if ch["id"] == "v2-rule-card-linkage")
        self.assertEqual(linkage["status"], "fail")
        self.assertIn("FR-W-06", linkage["detail"])

    def test_v2_bad_citation_flagged(self):
        nocite = dict(CARD)
        nocite["source"] = dict(CARD["source"])
        nocite["source"]["quote"] = ""
        checks = self.c.v2_checks([nocite], [], [], None)
        cites = next(ch for ch in checks if ch["id"] == "v2-card-citations")
        self.assertEqual(cites["status"], "fail")

    def test_v1_detects_invalid_output_and_area_sanity(self):
        checks = self.c.v1_checks(self.contract_zones, self.layers, self.aoi)
        by_id = {ch["id"]: ch for ch in checks}
        self.assertEqual(by_id["v1-output-geometry-valid"]["status"], "pass")
        self.assertEqual(by_id["v1-final-zone-sanity"]["status"], "pass")
        # final zone larger than AOI must fail
        huge = dict(self.contract_zones[-1])
        huge["areaKm2"] = 9999.0
        checks = self.c.v1_checks(self.contract_zones[:-1] + [huge], self.layers, self.aoi)
        by_id = {ch["id"]: ch for ch in checks}
        self.assertEqual(by_id["v1-final-zone-sanity"]["status"], "fail")

    def test_v3_agreement_and_divergence(self):
        checks = self.c.v3_checks(self.rules, self.layers, mapping(self.aoi), self.final)
        self.assertEqual(checks[0]["status"], "pass")
        # a divergent final zone (unrelated geometry) must fail V3
        divergent = dict(self.final)
        divergent["geometry"] = engine.to_zone_geometry(box(X0 + 5000, Y0 + 5000, X0 + 5100, Y0 + 5100))[0]
        divergent["areaM2"] = 10000.0
        checks = self.c.v3_checks(self.rules, self.layers, mapping(self.aoi), divergent)
        self.assertEqual(checks[0]["status"], "fail")

    def test_report_v4_pending_and_verdict_rollup(self):
        dt = explainer_mod.Explainer().build_decision_table(
            request=REQUEST, normcards=[CARD],
            formalrules=[RULE_FORMALIZED, RULE_EXCL, RULE_AMBIGUOUS],
            generated_at="2026-08-30T00:00:00Z", prov_narrative="unit test run narrative",
        )
        reports = self.c.evaluate_run(
            request=REQUEST, normcards=[CARD],
            formalrules=[RULE_FORMALIZED, RULE_EXCL, RULE_AMBIGUOUS],
            zones=self.contract_zones, decision_table=dt,
            layers=self.layers, aoi=mapping(self.aoi),
            engine_rules=self.rules, final_zone=self.final,
            run_id="unittest",
        )
        for vr in reports:
            contracts.validate(vr, "validation-report")  # schema-valid, would raise otherwise
        pipeline = reports[-1]
        self.assertEqual(pipeline["artifactType"], "pipeline-run")
        self.assertEqual(pipeline["verdict"], "pass")
        self.assertEqual(pipeline["levels"]["V4"]["status"], "pending")
        # a degradation flips the verdict to needs_human without failing checks
        reports = self.c.evaluate_run(
            request=REQUEST, normcards=[CARD],
            formalrules=[RULE_FORMALIZED, RULE_EXCL, RULE_AMBIGUOUS],
            zones=self.contract_zones, decision_table=dt,
            layers=self.layers, aoi=mapping(self.aoi),
            engine_rules=self.rules, final_zone=self.final,
            degradations=[{"kind": "layer-fetch", "zone": "x", "error": "boom"}],
            run_id="unittest",
        )
        self.assertEqual(reports[-1]["verdict"], "needs_human")


class TestExplainer(unittest.TestCase):
    def test_decision_table_contract_and_effects(self):
        expl = explainer_mod.Explainer()
        dt = expl.build_decision_table(
            request=REQUEST, normcards=[CARD],
            formalrules=[RULE_FORMALIZED, RULE_EXCL, RULE_AMBIGUOUS],
            generated_at="2026-08-30T00:00:00Z", prov_narrative="unit test run narrative",
        )
        contracts.validate(dt, "decision-table")
        effects = [row["zone effect"] for row in dt["rows"]]
        self.assertEqual(effects, ["included", "excluded", "ambiguous"])
        md = expl.decision_table_markdown(dt)
        self.assertIn("| criterion |", md)
        self.assertEqual(md.count("\n| "), len(dt["rows"]) + 1)  # header + rows

    def test_rejected_maps_to_not_applicable(self):
        rejected = dict(RULE_AMBIGUOUS)
        rejected["status"] = "rejected"
        dt = explainer_mod.Explainer().build_decision_table(
            request=REQUEST, normcards=[CARD], formalrules=[rejected],
            generated_at="2026-08-30T00:00:00Z", prov_narrative="unit test run narrative",
        )
        self.assertEqual(dt["rows"][0]["zone effect"], "not_applicable")

    def test_prov_bundle_structure(self):
        expl = explainer_mod.Explainer()
        prov = expl.build_prov(
            run_id="r", generated_at="2026-08-30T00:00:00Z", request_id="req",
            agents=[{"id": "a", "name": "x", "version": "1"}],
            activities=[{"id": "act", "label": "L", "agent": "x", "startedAt": "t0", "endedAt": "t1",
                         "used": ["missing-entity"], "generated": ["out.json"]}],
            entities=[{"id": "out.json", "type": "entity"}],
            derivations=[{"generatedEntity": "out.json", "usedEntity": "missing-entity"}],
            sources=[{"zone": "z", "lastChecked": "2026-08-30T00:00:00Z"}],
        )
        # referenced-but-unhashed entities are backfilled, links generated
        self.assertIn("missing-entity", {e["id"] for e in prov["entity"]})
        self.assertEqual(prov["wasGeneratedBy"][0]["activity"], "act")
        self.assertEqual(prov["hadPrimarySource"][0]["zone"], "z")


class TestReport(unittest.TestCase):
    def test_simplify_and_map_data(self):
        # payloads are WGS84 (as the engine emits); the AOI is EPSG:28992
        wgs_payload = engine.to_zone_geometry(box(X0, Y0, X0 + 500, Y0 + 500))[0]["payload"]
        zone = {"id": "zr-final-x", "operation": "final", "ruleIds": ["FR-W-05"],
                "layers": ["incl"], "areaKm2": 0.25,
                "geometry": {"payload": wgs_payload}}
        data = report_mod.build_map_data([zone], mapping(box(X0, Y0, X0 + 600, Y0 + 600)), tolerance_m=1.0)
        fc = json.loads(data["geojson"].replace("\\u003c", "<"))
        self.assertEqual(fc["type"], "FeatureCollection")
        self.assertEqual(fc["features"][0]["properties"]["__cat"], "final")
        self.assertEqual(len(data["bounds"]), 2)
        aoi = json.loads(data["aoi"].replace("\\u003c", "<"))
        self.assertIn(aoi["type"], ("Polygon", "MultiPolygon"))

    def test_render_html_embeds_valid_json(self):
        aoi, layers, rules, zones = synth_env()
        dt = explainer_mod.Explainer().build_decision_table(
            request=REQUEST, normcards=[CARD], formalrules=[RULE_FORMALIZED, RULE_AMBIGUOUS],
            generated_at="2026-08-30T00:00:00Z", prov_narrative="unit test run narrative",
        )
        map_data = report_mod.build_map_data(zones, REQUEST["areaOfInterest"]["geometry"], 1.0)
        reports = critic_mod.Critic().evaluate_run(
            request=REQUEST, normcards=[CARD], formalrules=[RULE_FORMALIZED, RULE_AMBIGUOUS],
            zones=run_mod.wrap_contract_zones(zones, REQUEST["id"]), decision_table=dt,
            layers=layers, aoi=mapping(aoi), engine_rules=[RULE_FORMALIZED], final_zone=zones[-1],
            run_id="unittest",
        )
        data = {
            "run": {"title": "t", "run_id": "r", "use_case": "wind", "generated_at": "now",
                    "policy_stage": "programming", "instrument": "i",
                    "badges": [{"label": "verdict: pass", "cls": "pass"}]},
            "headline": [{"k": "k", "v": "v", "s": "s"}],
            "headline_note": "note",
            "map": map_data,
            "zones_table": [{"id": "z", "operation": "final", "ruleIds": [], "areaKm2": "1",
                             "layers": [], "provSteps": 1, "repairs": 0}],
            "decision": {"columns": dt["columns"], "rows": dt["rows"]},
            "validation": [{"id": vr["id"], "artifactType": vr["artifactType"], "verdict": vr["verdict"],
                            "levels": [{"name": n, "status": l["status"], "checks": l.get("checks", []),
                                        "notes": l.get("notes")} for n, l in vr["levels"].items()]}
                           for vr in reports],
            "normcards": [{"id": CARD["id"], "article": "a", "instrument": "i", "legalForce": "binding",
                           "confidence": 0.9, "claim": "c", "quote": "q", "uri": "https://x.test",
                           "docId": "S07", "version": "v", "theme": "t", "zoneIds": None,
                           "gioJoinId": None, "caveat": None}],
            "abstentions": [{"id": "A-01", "topic": "t", "reason": "r"}],
            "prov": {"activities": [{"label": "l", "agent": "a", "startedAt": "t0", "endedAt": "t1",
                                     "used": [], "generated": []}],
                     "agents": [{"name": "n", "version": "v"}],
                     "sources": [{"zone": "z", "sourceId": "s", "service": "srv", "features": 1,
                                  "lastChecked": "lc", "aliasFor": None}]},
            "limitations": ["l1"],
            "tunings": [{"k": "k", "v": 1}],
            "paths": {"listing": "a / b"},
        }
        html = report_mod.render_report_html(data)
        for section in ("Opportunity map", "Decision table", "Validation report",
                        "Norm cards", "Provenance", "Limitations"):
            self.assertIn(section, html)
        self.assertIn("unpkg.com/leaflet", html)
        m = re.search(r'<script type="application/json" id="zones-data">(.*?)</script>', html, re.S)
        embedded = m.group(1)
        self.assertNotIn("&#34;", embedded)  # must NOT be html-escaped
        fc = json.loads(embedded.replace("\\u003c", "<"))
        self.assertEqual(fc["type"], "FeatureCollection")
        self.assertTrue(fc["features"])


class TestRunHelpers(unittest.TestCase):
    def test_wrap_contract_zones_maps_operations_and_validates(self):
        aoi, layers, rules, zones = synth_env()
        wrapped = run_mod.wrap_contract_zones(zones, REQUEST["id"])
        self.assertEqual(len(wrapped), len(zones))
        for z in wrapped:
            contracts.validate(z, "zone-result")
            self.assertTrue(z["id"].startswith("ZR-"))
            self.assertTrue(z["computedAt"])  # wall-clock stamped by the wrapper
            self.assertIn(z["operation"], ("intersection", "difference", "union", "buffer"))
        self.assertEqual(wrapped[-1]["operation"], "difference")  # final after exclusions

    def test_zone_alias_registry_covers_corpus_rules(self):
        rules = json.loads((POC_ROOT / "corpus" / "formalrules-wind.json").read_text(encoding="utf-8"))
        for r in rules:
            if r.get("status") != "formalized":
                continue
            for z in run_mod.rule_zones(r):
                self.assertIn(z, run_mod.ZONE_SOURCES,
                              f"zone {z!r} of {r['id']} has no open-data alias")

    def test_count_repairs(self):
        steps = ["op=x; make_valid_repairs=2", "op=y; make_valid_repairs=3"]
        self.assertEqual(run_mod.count_repairs(steps), 5)
        self.assertEqual(run_mod.count_repairs([]), 0)

    def test_simplify_layers_records_provenance(self):
        aoi, layers, rules, zones = synth_env()
        simplified, notes = engine.simplify_layers(layers, 1.0)
        self.assertEqual(len(notes), len(layers))
        self.assertIn("tolerance_m=1.0", notes[0])
        for fc in simplified.values():
            self.assertEqual(fc["properties"]["simplifiedM"], 1.0)
        # provenance naming picks the simplification up
        name = engine._layer_prov_name("incl", simplified, {})
        self.assertIn("simplifiedM=1.0", name)
        # geometry shrinks but stays valid
        for f in simplified["incl"]["features"]:
            self.assertTrue(shape(f["geometry"]).is_valid)

    def test_engine_reexecute_partitions_rules_like_execute(self):
        # a late inclusion rule must NOT resurrect excluded area in V3
        aoi = box(X0, Y0, X0 + 500, Y0 + 500)
        incl = {"id": "R1", "zoneSemantics": "inclusion", "sourceLayerId": "a"}
        excl = {"id": "R2", "zoneSemantics": "exclusion", "sourceLayerId": "b"}
        late_incl = {"id": "R3", "zoneSemantics": "inclusion", "sourceLayerId": "c"}
        layers = {
            "a": fc(box(X0, Y0, X0 + 100, Y0 + 100)),
            "b": fc(box(X0 + 50, Y0 + 50, X0 + 70, Y0 + 70)),
            "c": fc(box(X0 + 200, Y0 + 200, X0 + 280, Y0 + 280)),
        }
        rules = [incl, excl, late_incl]
        zones = engine.execute_rules(rules, layers, aoi=mapping(aoi))
        indep = engine.reexecute_independent(rules, layers, aoi=mapping(aoi))
        rel = abs(zones[-1]["areaM2"] - indep.area) / max(zones[-1]["areaM2"], indep.area, 1e-12)
        self.assertLessEqual(rel, 1e-9)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
