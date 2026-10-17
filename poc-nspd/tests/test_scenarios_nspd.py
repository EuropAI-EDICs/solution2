"""S7-port in poc-nspd: scenario-engine, control-reproductie, gates (fase 3, task 6).

Gereduceerde port van ``poc/tests/test_scenarios.py`` op de poc-nspd-machinerie:
V0-schema's, mutatie-semantiek op synthetische lagen (gepinde km²), skip-met-
reden voor ambiguous, onbekende ruleId = authoring-error, control-reproductie,
narratie-gate (magnitude-fold) en de V2-data-grounding-check tegen
poc-nspd/data/sources.json. Plus een file-author e2e op de nieuwste wind-nl
baseline (cache-first, netwerkvrij; skipped zonder runs).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts, scenarios  # noqa: E402
from pipeline.scenarios import (  # noqa: E402
    check_narrative_grounding, deterministic_narrative, eligible_rules,
    evaluate_scenario_run, load_baseline, run_scenario_set,
)

VIERKANT = {"type": "Polygon", "coordinates": [
    [[20500.0, 403000.0], [25500.0, 403000.0], [25500.0, 408000.0],
     [20500.0, 408000.0], [20500.0, 403000.0]]]}  # 5×5 km = 25 km²
VIERKANT_KLEIN = {"type": "Polygon", "coordinates": [
    [[21000.0, 403500.0], [23000.0, 403500.0], [23000.0, 405500.0],
     [21000.0, 405500.0], [21000.0, 403500.0]]]}  # 2×2 km = 4 km²
VIERKANT_MIDDEL = {"type": "Polygon", "coordinates": [
    [[20500.0, 403000.0], [24500.0, 403000.0], [24500.0, 407000.0],
     [20500.0, 407000.0], [20500.0, 403000.0]]]}  # 4×4 km = 16 km²


def _rules() -> list:
    return [
        {"id": "FR-T-01", "normCardId": "NC-T-01", "status": "formalized",
         "ruleType": "zone_inclusion", "zoneSemantics": "inclusion",
         "instrumentType": "omgevingsverordening-nl", "jurisdictie": "nl",
         "appliesTo": {"objectType": "wind_turbine", "contextTags": ["geometry_zeeland_ovz"]},
         "executableRef": "engine.zone.within@poc-v1",
         "zoneSelector": {"zoneIds": ["zone-a"], "selection": "within",
                          "geometrySource": "national_source"},
         "conditions": []},
        {"id": "FR-T-02", "normCardId": "NC-T-02", "status": "formalized",
         "ruleType": "zone_exclusion", "zoneSemantics": "exclusion",
         "instrumentType": "omgevingsverordening-nl", "jurisdictie": "nl",
         "appliesTo": {"objectType": "wind_turbine", "contextTags": ["geometry_zeeland_ovz"]},
         "executableRef": "engine.zone.exclude_within@poc-v1",
         "zoneSelector": {"zoneIds": ["zone-b"], "selection": "within",
                          "geometrySource": "national_source"},
         "conditions": []},
        {"id": "FR-T-03", "normCardId": "NC-T-03", "status": "ambiguous",
         "ruleType": "zone_conditional", "zoneSemantics": "conditional",
         "instrumentType": "omgevingsverordening-nl", "jurisdictie": "nl",
         "appliesTo": {"objectType": "wind_turbine",
                       "contextTags": ["zone_loos_gedocumenteerd", "v4_human_review"]},
         "executableRef": "engine.procedural.human_review@poc-v1",
         "conditions": []},
    ]


def _cards() -> list:
    return [{"id": f"NC-T-0{i}", "claim": "c",
             "source": {"docId": "S01", "article": "a", "version": "v", "quote": "q",
                        "quoteLanguage": "nl", "uri": "u", "retrievedAt": "2026-10-16"},
             "extractedBy": "curator#t", "extractedAt": "2026-10-16",
             "appliesTo": {"objectType": "wind_turbine", "track": "wind"},
             "instrumentType": "omgevingsverordening-nl", "jurisdictie": "nl"}
            for i in (1, 2, 3)]


def _schrijf_baseline(tmp: Path) -> Path:
    """Minimale canonieke run-map (de vijf bestanden die load_baseline eist)."""
    run = tmp / "20261016T000000Z-wind-nl"
    run.mkdir(parents=True)
    request = {"id": "93c2a803-4bb4-52e1-b415-e547d0f14725",
               "objectType": "wind_turbine", "ambitions": ["energy"],
               "areaOfInterest": {"geometry": VIERKANT, "crs": "EPSG:28992"},
               "policyStage": "programming",
               "effortBudget": {"maxSubagents": 1, "maxCostEur": 0.0, "maxLatencyS": 60},
               "requestedAt": "2026-10-16T00:00:00Z", "requestedBy": "test"}
    (run / "request.json").write_text(json.dumps(request), encoding="utf-8")
    (run / "formalrules.json").write_text(json.dumps(_rules()), encoding="utf-8")
    (run / "normcards.json").write_text(json.dumps(_cards()), encoding="utf-8")
    (run / "run_summary.json").write_text(json.dumps({
        "runId": run.name, "verdict": "pass", "v2b": {"status": "pass"},
        "tunings": []}), encoding="utf-8")
    (run / "layers.json").write_text(json.dumps({}), encoding="utf-8")
    return run


def _lagen() -> dict:
    def fc(geom):
        return {"type": "FeatureCollection", "crs": {"type": "name",
                "properties": {"name": "EPSG:28992"}},
                "features": [{"type": "Feature", "properties": {}, "geometry": geom}]}
    return {"aoi": fc(VIERKANT), "zone-a": fc(VIERKANT_MIDDEL), "zone-b": fc(VIERKANT_KLEIN)}


def _spec(sid: str, mutaties: list) -> dict:
    spec = {"id": sid, "name": sid, "objectType": "wind_turbine",
            "basis": {"type": "policy_variant", "normCardId": "NC-T-01",
                      "provenanceNote": "test-variant"},
            "mutations": mutaties, "proposedBy": "test#poc-nspd"}
    contracts.validate(spec, "scenario-spec")
    return spec


def _draai(tmp: Path, specs: list):
    baseline = load_baseline(_schrijf_baseline(tmp))
    return run_scenario_set(
        baseline=baseline, layers=_lagen(), specs=specs,
        scenario_set_id="SSET-test", report_id="SR-test")


def test_mutatie_semantiek_gepinde_km2(tmp_path):
    """Control: inclusion zone-a (16 km²) − exclusie zone-b (4 km²) = 12 km².
    Drop van de inclusion → terugval op FR-AOI-01 (hele AOI) − zone-b = 21 km²;
    500 m-buffer rond de 2×2-exclusie → kleiner dan 12."""
    report = _draai(tmp_path, [
        _spec("SC-T-DROP", [{"ruleId": "FR-T-01", "action": "drop"}]),
        _spec("SC-T-BUF", [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m",
                            "bufferDistanceM": 500}]),
    ])
    per = {s["scenarioId"]: s for s in report["scenarios"]}
    assert report["control"]["finalAreaKm2"] == pytest.approx(12.0, abs=0.01)
    assert per["SC-T-DROP"]["finalAreaKm2"] == pytest.approx(21.0, abs=0.01)
    assert per["SC-T-BUF"]["finalAreaKm2"] < 12.0


def test_eligible_rules_allen_formalized():
    assert [r["id"] for r in eligible_rules(_rules())] == ["FR-T-01", "FR-T-02"]


def test_critic_v4_pending_en_verdict(tmp_path):
    report = _draai(tmp_path, [
        _spec("SC-T-VAR", [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m",
                            "bufferDistanceM": 250}])])
    rapport = evaluate_scenario_run(
        report=report, unknown_rule_ids=[], normcard_missing=[],
        executed_count=len(report["scenarios"]))
    assert rapport["verdict"] == "pass"
    assert rapport["levels"]["V4"]["status"] == "pending"


def test_narratie_gate_magnitude_fold(tmp_path):
    """Elk getal in de narratie moet in het rapport staan; 'fail' claimen op een
    pass-rapport wordt geweigerd (regression-guard)."""
    report = _draai(tmp_path, [
        _spec("SC-T-DROP", [{"ruleId": "FR-T-02", "action": "drop"}])])
    rapport = evaluate_scenario_run(
        report=report, unknown_rule_ids=[], normcard_missing=[],
        executed_count=len(report["scenarios"]))
    assert rapport["verdict"] == "pass"
    tekst = deterministic_narrative(report)
    assert check_narrative_grounding(tekst, report)["status"] == "pass"
    assert check_narrative_grounding(tekst + " Het eindoordeel is fail.", report)["status"] == "fail"


def test_v2_data_grounding_eist_scenario_basis_rol():
    """basis.dataGrounding verwijst naar een bron met role scenario-basis;
    netcongestie heeft die rol in poc-nspd/data/sources.json."""
    bronnen = {"netbeheerder-netcongestie": {"role": "scenario-basis"}}
    assert scenarios._data_grounding_errors(bronnen, {
        "sourceId": "netbeheerder-netcongestie", "retrieved": "2026-10-16",
        "note": "voedingsgebied-codes als verkenning"}) == []
    assert scenarios._data_grounding_errors(bronnen, {
        "sourceId": "netbeheerder-netcongestie", "retrieved": "geen-datum"})
    assert scenarios._data_grounding_errors(
        {"andere-bron": {"role": "scenario-basis"}},
        {"sourceId": "netbeheerder-netcongestie", "retrieved": "2026-10-16"})


def test_ambiguous_niet_mutabel_en_onbekende_rule_id_faalt(tmp_path):
    from pipeline.scenarios import apply_mutations
    baseline = load_baseline(_schrijf_baseline(tmp_path))
    # ambiguous muteren: apply_mutations slaat over mét reden (nooit stil)
    _, _, geskipt, onbekend = apply_mutations(baseline["formalrules"], [
        {"ruleId": "FR-T-03", "action": "drop"}])
    assert geskipt and "FR-T-03" in json.dumps(geskipt) and not onbekend
    _, _, _, onbekend2 = apply_mutations(baseline["formalrules"], [
        {"ruleId": "FR-BESTAAT-NIET", "action": "drop"}])
    assert onbekend2 == ["FR-BESTAAT-NIET"], "authoring-error via het ledger"


def test_file_author_e2e_wind_nl_baseline():
    """File-author over de nieuwste wind-nl baseline (cache-first): verdict pass,
    control-reproductie exact, SC-geojson's geschreven. Skipped zonder runs."""
    runs = [r for r in sorted((ROOT / "runs").glob("*wind-nl"))
            if (r / "layers.json").is_file()]
    if not runs:
        pytest.skip("geen wind-nl baseline run aanwezig")
    uit = ROOT / "scenario-runs" / f"test-e2e-{runs[-1].name}"
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "scenarios" / "run.py"), "--use-case", "wind-nl",
         "--baseline", str(runs[-1]), "--author", "file", "--no-h3", "--out", str(uit)],
        capture_output=True, text=True, cwd=ROOT,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin",
             "POC_H3_OFFLINE": "1"})
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    report = json.loads((uit / "scenario-report.json").read_text(encoding="utf-8"))
    assert report["verdict"] == "pass"
    assert report["control"]["reproductionRelDelta"] <= 0.001
    assert len(list((uit / "scenarios").glob("*.geojson"))) >= 2  # CONTROL + scenario's


# --------------------------------------------------------------------------- #
# add_zone_rule (PDOK-catalogus 2026-10-16): data-grounded what-if-operanden
# --------------------------------------------------------------------------- #

_ALIASSEN = {"alias-x": {"sourceId": "bron-x", "note": "testlaag"}}


def _hyp_spec(sid: str, mutaties: list, basis_type: str = "hypothetical",
              dg_source: str = "bron-x") -> dict:
    basis = {"type": basis_type, "provenanceNote": "fictief — geen citatie",
             "dataGrounding": {"sourceId": dg_source, "retrieved": "2026-10-16"}}
    if basis_type == "hypothetical":
        basis["rationale"] = "verkenning op een gepinde datalaag"
    else:
        basis["normCardId"] = "NC-T-01"
    spec = {"id": sid, "name": sid, "objectType": "wind_turbine", "basis": basis,
            "mutations": mutaties, "proposedBy": "test#poc-nspd"}
    contracts.validate(spec, "scenario-spec")
    return spec


def _draai_met_alias(tmp: Path, specs: list, bronnen_rol: str = "scenario-basis"):
    """run_scenario_set met de alias-laag al in ``layers`` (zoals de CLI doet)
    en de registry-rol van bron-x gemonkeypatcht via geodata.load_sources."""
    import tempfile
    baseline = load_baseline(_schrijf_baseline(Path(tempfile.mkdtemp(dir=tmp))))
    lagen = _lagen()
    lagen["alias-x"] = lagen["zone-b"]  # 4 km²-vierkant als what-if-operand
    import pipeline.geodata as geodata
    origineel = geodata.load_sources
    geodata.load_sources = lambda path=None: {"bron-x": {"role": bronnen_rol}}
    try:
        return run_scenario_set(
            baseline=baseline, layers=lagen, specs=specs,
            scenario_set_id="SSET-test", report_id="SR-test",
            zone_aliases=_ALIASSEN,
            extra_layers_manifest={"alias-x": {"serviceUrl": "https://api.pdok.nl/x",
                                               "layerId": "c", "lastChecked": "2026-10-16"}})
    finally:
        geodata.load_sources = origineel


def _v2_check(rapport: dict, check_id: str) -> dict:
    return next(c for c in rapport["_validation"]["levels"]["V2"]["checks"] if c["id"] == check_id)


def test_add_zone_rule_voegt_synthetische_regel_toe_en_rekent_door(tmp_path):
    from pipeline.scenarios import apply_mutations
    baseline = load_baseline(_schrijf_baseline(tmp_path))
    nieuw, toegepast, geskipt, onbekend = apply_mutations(baseline["formalrules"], [
        {"ruleId": "HYP-X", "action": "add_zone_rule", "zoneId": "alias-x",
         "zoneSemantics": "exclusion", "bufferDistanceM": 100}])
    assert not geskipt and not onbekend
    regel = next(r for r in nieuw if r["id"] == "HYP-X")
    assert regel["status"] == "formalized" and regel["zoneSemantics"] == "exclusion"
    assert regel["zoneSelector"]["zoneIds"] == ["alias-x"]
    assert regel["zoneSelector"]["bufferDistanceM"] == 100.0
    assert regel["normCardId"] is None and regel["synthetic"] is True
    assert toegepast[0]["zoneId"] == "alias-x" and toegepast[0]["bufferDistanceM"] == 100.0
    # end-to-end: exclusion van het 4 km²-vierkant (zonder buffer) op de
    # 16 km²-inclusie minus zone-b (zelfde vierkant) = geen extra verlies;
    # als inclusion-union komt het vierkant er juist niét bij (al binnen zone-a)
    rapport = _draai_met_alias(tmp_path, [
        _hyp_spec("SC-ADD-EXCL", [{"ruleId": "HYP-X", "action": "add_zone_rule",
                                   "zoneId": "alias-x", "zoneSemantics": "exclusion",
                                   "bufferDistanceM": 500}])])
    rij = rapport["scenarios"][0]
    assert rij["status"] == "ok" and rij["finalAreaKm2"] < rapport["control"]["finalAreaKm2"]
    assert _v2_check(rapport, "v2-data-grounding")["status"] == "pass"
    assert rij["mutationsApplied"][0]["action"] == "add_zone_rule"
    contracts.validate({k: v for k, v in rapport.items() if not k.startswith("_")}, "scenario-report")


def test_add_zone_rule_collision_en_ontbrekende_velden_zijn_authoring_fouten(tmp_path):
    from pipeline.scenarios import apply_mutations
    baseline = load_baseline(_schrijf_baseline(tmp_path))
    _, toegepast, geskipt, _ = apply_mutations(baseline["formalrules"], [
        {"ruleId": "FR-T-01", "action": "add_zone_rule", "zoneId": "alias-x", "zoneSemantics": "inclusion"},
        {"ruleId": "HYP-LEEG", "action": "add_zone_rule", "zoneSemantics": "inclusion"},
    ])
    assert not toegepast and len(geskipt) == 2
    assert "botst" in geskipt[0]["v2Error"] and "verplicht" in geskipt[1]["v2Error"]
    rapport = _draai_met_alias(tmp_path, [
        _hyp_spec("SC-BOTS", [{"ruleId": "FR-T-01", "action": "add_zone_rule",
                               "zoneId": "alias-x", "zoneSemantics": "inclusion"}])])
    assert rapport["verdict"] == "fail"
    assert "botst" in _v2_check(rapport, "v2-mutation-rule-ids")["detail"] or any(
        "botst" in json.dumps(c) for c in rapport["_validation"]["levels"]["V2"]["checks"])


def test_v2_add_zone_rule_eist_hypothetical_en_passende_dataGrounding(tmp_path):
    mut = [{"ruleId": "HYP-X", "action": "add_zone_rule", "zoneId": "alias-x",
            "zoneSemantics": "exclusion"}]
    # policy_variant mag géén datalaag toevoegen
    rapport = _draai_met_alias(tmp_path, [_hyp_spec("SC-PV", mut, basis_type="policy_variant")])
    detail = _v2_check(rapport, "v2-data-grounding")["detail"]
    assert "hypothetical" in detail and rapport["verdict"] == "fail"
    # dataGrounding op een andere bron dan de alias-bron
    import pipeline.geodata as geodata
    origineel = geodata.load_sources
    try:
        rapport = _draai_met_alias(tmp_path, [_hyp_spec("SC-ANDER", mut, dg_source="bron-y")])
    finally:
        geodata.load_sources = origineel
    assert "≠ alias-bron" in _v2_check(rapport, "v2-data-grounding")["detail"]
    # onbekende alias
    rapport = _draai_met_alias(tmp_path, [_hyp_spec("SC-ONB", [
        {"ruleId": "HYP-Y", "action": "add_zone_rule", "zoneId": "alias-bestaat-niet",
         "zoneSemantics": "exclusion"}])])
    assert "geen geregistreerde alias" in _v2_check(rapport, "v2-data-grounding")["detail"]


def test_v2_rol_context_mag_nooit_zone_bepalend_zijn(tmp_path):
    mut = [{"ruleId": "HYP-X", "action": "add_zone_rule", "zoneId": "alias-x",
            "zoneSemantics": "exclusion"}]
    ok = _draai_met_alias(tmp_path, [_hyp_spec("SC-EXCL", mut)], bronnen_rol="exclusion")
    assert _v2_check(ok, "v2-data-grounding")["status"] == "pass", "zone-geschikte rol mag"
    fout = _draai_met_alias(tmp_path, [_hyp_spec("SC-CTX", mut)], bronnen_rol="context")
    assert _v2_check(fout, "v2-data-grounding")["status"] == "fail"
    assert "context" in _v2_check(fout, "v2-data-grounding")["detail"]


def test_load_extra_zone_layers_uit_cache_en_degradaties(tmp_path):
    from pipeline.scenarios import load_extra_zone_layers, add_zone_rule_zone_ids
    cache = tmp_path / "cache"
    cache.mkdir()
    fc = _lagen()["zone-b"]
    fc["properties"] = {"serviceUrl": "https://api.pdok.nl/x/ogc/v1", "collection": "c",
                        "featureCount": 1, "lastChecked": "2026-10-16"}
    (cache / "bron-x.28992.geojson").write_text(json.dumps(fc), encoding="utf-8")
    specs = [{"mutations": [{"action": "add_zone_rule", "zoneId": "alias-x"},
                            {"action": "drop", "ruleId": "FR-T-01"},
                            {"action": "add_zone_rule", "zoneId": "alias-x"}]},
             {"mutations": [{"action": "add_zone_rule", "zoneId": "alias-onbekend"}]}]
    assert add_zone_rule_zone_ids(specs) == ["alias-x", "alias-onbekend"]
    lagen, manifest, degr = load_extra_zone_layers(
        ["alias-x", "alias-onbekend", "alias-geen-cache"],
        {**_ALIASSEN, "alias-geen-cache": {"sourceId": "bron-zonder-cache"}},
        simplify_m=2.0, cache_dir=cache)
    assert set(lagen) == {"alias-x"}
    assert manifest["alias-x"]["layerId"] == "c" and manifest["alias-x"]["aliasSourceId"] == "bron-x"
    assert manifest["alias-x"]["cachePath"].endswith("bron-x.28992.geojson")
    soorten = sorted(d["kind"] for d in degr)
    assert soorten == ["layer-cache-missing", "zone-alias"]


def test_load_layers_seedt_aoi_zone_uit_request(tmp_path):
    """AOI-brede baselines (FR-AOI-01): de 'aoi'-zone heeft geen cache; met de
    request-AOI meegegeven wordt ze geseed zoals run.py doet (geen degradatie,
    FR-AOI-01 blijft draaien)."""
    from shapely.geometry import shape
    from pipeline.scenarios import load_layers
    manifest = {"aoi": {"zoneId": "aoi", "aliasSourceId": "request-aoi", "cachePath": None}}
    lagen, degr = load_layers(manifest, simplify_m=2.0)
    assert not lagen and degr and degr[0]["kind"] == "layer-cache-missing"
    lagen, degr = load_layers(manifest, simplify_m=2.0, aoi_geometry=shape(VIERKANT))
    assert not degr and "aoi" in lagen
    assert lagen["aoi"]["properties"]["sourceId"] == "request-aoi"
    assert abs(shape(lagen["aoi"]["features"][0]["geometry"]).area - 25e6) < 1.0
