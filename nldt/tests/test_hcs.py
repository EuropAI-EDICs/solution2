"""Tests voor de HCS-recipes (spec 2026-10-09-hcs-recipes-pocs-design, fase 1)."""
import json
from pathlib import Path

import pytest

from services.common.schema import load_recipe, validate_instance
from services.process_adapter.handlers import describe_process, execute_local

NLDT_ROOT = Path(__file__).resolve().parents[1]
HCS_ROOT = NLDT_ROOT / "simulation" / "hcs"

SERVICE_MIN = {
    "dish": "the-key",
    "serviceType": "reactive",
}


def test_service_block_accepted():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe met service-blok",
        "version": "1.0.0",
        "inputs": {},
        "outputs": {},
        "steps": [
            {"id": "s1", "processId": "hcs-life-event-run", "inputs": {}}
        ],
        "riskLevel": "low",
        "service": dict(
            SERVICE_MIN,
            lifeEventCode="THK-08",
            blueprintSteps=[1, 2, 3, 4, 5],
            parties=[{"name": "Gemeente Zoetermeer", "role": "lead"}],
            legalBasis=[{"basis": "Wet BRP", "timeLimit": "redelijke termijn (Awb)"}],
            humanMeasure={"handover": ["adresonderzoek bij twijfel → medewerker"], "exceptions": []},
            localVariant="gemeentelijk parkeerbeleid",
            genAiTestPoints=[{"point": "G1", "description": "intake-assistent", "testCases": ["laaggeletterde persona"]}],
            kpis=[{
                "kpi": "Moves processed without manual handling",
                "kpiType": "outcome", "unit": "%", "outcomeLens": "Z",
                "baseline": "", "target": "", "dataSource": "case system",
                "frequency": "monthly", "kviRollup": "KVI 5 (Digital)",
            }],
        ),
    }
    validate_instance(recipe, "recipe.schema.json")


def test_service_block_rejects_unknown_field_and_bad_point():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe onbekend veld",
        "version": "1.0.0",
        "inputs": {}, "outputs": {},
        "steps": [{"id": "s1", "processId": "x", "inputs": {}}],
        "riskLevel": "low",
        "service": {"dish": "the-key", "serviceType": "reactive", "onbekend": True},
    }
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")

    recipe["service"] = {"dish": "the-key", "serviceType": "reactive",
                         "genAiTestPoints": [{"point": "G9", "description": "bestaat niet"}]}
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")


RUN_MIN = {
    "schemaVersion": "1.0",
    "runId": "thk-08-move-home-sanne-20261009T000000Z",
    "generatedAt": "2026-10-09T00:00:00Z",
    "recipeId": "thk-08-move-home",
    "processId": "hcs-life-event-run",
    "mode": "replay",
    "scenario": "sanne",
    "steps": [{
        "stepId": "intake", "title": "Life event & intake", "actor": "agent",
        "genAiTestPoint": "G1", "dataUsed": ["BRP (Haal Centraal)"],
        "consent": "n.v.t.", "handover": None, "kpiEvents": [],
        "prov": {"sources": ["BRP (Haal Centraal)"]},
    }],
    "stopConditions": [{"id": "sc-1", "condition": "mens-overnames > 20%", "action": "pauzeer"}],
    "kpiSnapshot": [{"kpi": "Moves processed without manual handling", "baseline": "", "target": ""}],
}


def test_hcs_run_schema():
    validate_instance(RUN_MIN, "hcs-run.schema.json")
    bad = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], actor="robot")])
    with pytest.raises(Exception):
        validate_instance(bad, "hcs-run.schema.json")
    bad2 = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], handover={"reden": "x"})])
    with pytest.raises(Exception):
        validate_instance(bad2, "hcs-run.schema.json")  # handover vereist reason+to


def test_hcs_baseline_schema():
    baseline = {
        "recipeId": "thk-08-move-home",
        "publicOutcome": "verhuizen is één gesorteerde reis",
        "disappearingStep": "herhaalde loketbezoeken",
        "kpis": [{"kpi": "Moves processed without manual handling", "kpiType": "outcome",
                  "unit": "%", "outcomeLens": "Z"}],
        "stopConditions": [{"condition": "c", "action": "a"}],
        "goNoGo": ["accuracy ≥ 95% op testbank-personas"],
    }
    validate_instance(baseline, "hcs-baseline.schema.json")
    with pytest.raises(Exception):
        validate_instance(dict(baseline, kpis=[{"kpi": "x"}]), "hcs-baseline.schema.json")


LIFE_FIXTURES = HCS_ROOT / "fixtures" / "life-events"
EXPECTED_LIFE = {"thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate"}


def test_life_event_fixtures_present_and_consistent():
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text())
    assert set(common["parties"].keys()) >= {"gemeente", "energie", "bank", "verzekeraar", "zorgverzekeraar"}
    found = {p.stem for p in LIFE_FIXTURES.glob("*.json")}
    assert found == EXPECTED_LIFE
    for path in LIFE_FIXTURES.glob("*.json"):
        fx = json.loads(path.read_text())
        persona_ids = {p["id"] for p in fx["personas"]}
        assert len(persona_ids) >= 2
        assert len(fx["steps"]) == 5  # de vijf blueprint-stappen
        for step in fx["steps"]:
            for pid in step.get("perPersona", {}):
                assert pid in persona_ids, f"onbekende persona {pid} in {path.name}"
        assert fx["stopConditions"], "poort 5: stopcondities verplicht"
        assert fx["kpiSnapshot"], "poort 1: KPI-snapshot verplicht"


def test_hcs_processes_registered():
    for pid in ("hcs-life-event-run", "hcs-recipe-run"):
        assert describe_process(pid)["id"] == pid


def test_life_event_run_replay_sanne():
    out = execute_local("hcs-life-event-run",
                        {"recipeId": "thk-08-move-home", "persona": "sanne", "mode": "replay"})
    run = out["run"]
    validate_instance(run, "hcs-run.schema.json")
    assert run["scenario"] == "sanne"
    assert [s["stepId"] for s in run["steps"]] == ["intake", "solution", "contract", "delivery", "followup"]
    assert all(s["handover"] is None for s in run["steps"])
    assert run["steps"][0]["genAiTestPoint"] == "G1"


def test_life_event_run_edge_cases():
    ahmed = execute_local("hcs-life-event-run",
                          {"recipeId": "thk-08-move-home", "persona": "ahmed", "mode": "replay"})["run"]
    intake = next(s for s in ahmed["steps"] if s["stepId"] == "intake")
    assert intake["handover"] == {"reason": "Twijfel over het adres (adresonderzoek nodig)",
                                  "to": "medewerker Burgerzaken"}
    delivery = next(s for s in ahmed["steps"] if s["stepId"] == "delivery")
    assert delivery["actor"] == "mens"

    jeroen = execute_local("hcs-life-event-run",
                           {"recipeId": "thk-08-move-home", "persona": "jeroen", "mode": "replay"})["run"]
    follow = next(s for s in jeroen["steps"] if s["stepId"] == "followup")
    assert follow["handover"]["to"].startswith("wijkteam")


def test_life_event_run_unknown_persona_fails():
    from services.process_adapter.poc_handlers import execute_hcs_life_event_run
    with pytest.raises(KeyError):
        execute_hcs_life_event_run({"recipeId": "thk-08-move-home", "persona": "bestaatniet"})


THK_IDS = ("thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate")


@pytest.mark.parametrize("rid", THK_IDS)
def test_thk_recipe_valid_with_service(rid):
    recipe = load_recipe(rid)
    validate_instance(recipe, "recipe.schema.json")
    assert recipe["service"]["dish"] == "the-key"
    assert recipe["service"]["lifeEventCode"] in {"THK-08", "THK-02", "THK-24"}
    assert recipe["service"]["kpis"], "KPI's uit het framework verplicht"


@pytest.mark.parametrize("rid", THK_IDS)
def test_thk_baseline_valid(rid):
    baseline = json.loads(
        (NLDT_ROOT / "recipes" / "baselines" / f"{rid}.baseline.json").read_text())
    validate_instance(baseline, "hcs-baseline.schema.json")
    assert baseline["recipeId"] == rid
    assert baseline["disappearingStep"], "poort 1: verdwijnende stap benoemen (B5)"


def test_thk08_run_recipe_offline(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.recipe_runner import run_recipe
    result = run_recipe("thk-08-move-home", {"persona": "sanne", "mode": "replay"})
    run = result["outputs"]["run"]
    validate_instance(run, "hcs-run.schema.json")
    assert run["scenario"] == "sanne"


def test_thk08_run_recipe_empty_inputs(monkeypatch):
    """Ontbrekende optionele inputs (persona/mode=None) mogen niet crashen."""
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.recipe_runner import run_recipe
    result = run_recipe("thk-08-move-home", {})
    run = result["outputs"]["run"]
    validate_instance(run, "hcs-run.schema.json")
    assert run["mode"] == "replay"


def test_thk24_declares_minigim_ingredient():
    recipe = load_recipe("thk-24-build-renovate")
    assert "minigim-gebiedscheck-run" in recipe["requiredProcesses"]


def test_edic_map_has_thk_entries():
    from services.common.schema import load_edic_asset_map
    payload = load_edic_asset_map()
    ids = {a["id"] for a in payload["assets"]}
    for rid in THK_IDS:
        assert f"recipe:{rid}" in ids


def test_recipe_run_generic_with_tmp_fixture(tmp_path):
    city = tmp_path / "city"
    city.mkdir()
    (city / "probe-city.json").write_text(json.dumps({
        "recipeId": "probe-city",
        "scenarioKind": "city",
        "scenarios": [{"id": "wijk-01", "label": "Proefwijk"}],
        "steps": [{
            "stepId": "measure", "title": "Met de groendak", "blueprintStep": None,
            "defaults": {"actor": "agent", "genAiTestPoint": "G2", "dataUsed": ["remote sensing"],
                          "consent": "n.v.t.", "kpiEvents": [], "prov": {"sources": ["remote sensing"]}},
            "perScenario": {}
        }],
        "stopConditions": [{"id": "sc-1", "condition": "c", "action": "a"}],
        "kpiSnapshot": [{"kpi": "k", "baseline": "", "target": ""}],
    }))
    from services.process_adapter.poc_handlers import execute_hcs_recipe_run
    out = execute_hcs_recipe_run({"recipeId": "probe-city", "scenario": "wijk-01", "mode": "replay"},
                                 fixture_dir=tmp_path)
    validate_instance(out["run"], "hcs-run.schema.json")
    assert out["run"]["processId"] == "hcs-recipe-run"


RUNS_DIR = HCS_ROOT / "runs"


def test_build_runs_deterministic(tmp_path):
    import subprocess

    venv = NLDT_ROOT / ".venv" / "bin" / "python"
    stamp = "20261009T000000Z"

    def run_build(outdir: Path) -> str:
        cmd = [str(venv), str(HCS_ROOT / "build_runs.py"), "--stamp", stamp,
               "--outdir", str(outdir), "--only-runs"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return proc.stdout

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    assert "OK" in run_build(out1)
    assert "OK" in run_build(out2)

    names1 = sorted(p.name for p in out1.glob("*.json"))
    names2 = sorted(p.name for p in out2.glob("*.json"))
    assert names1 == names2, (names1, names2)
    assert len(names1) == 8, names1
    for name in names1:
        a = (out1 / name).read_bytes()
        b = (out2 / name).read_bytes()
        assert a == b  # zelfde stamp → byte-identiek over aparte outdirs
    run = json.loads((out1 / "thk-08-move-home_sanne.json").read_text())
    assert run["generatedAt"].endswith("Z")
    assert run["runId"].endswith(stamp)


KEY_DEMO = NLDT_ROOT / "simulation" / "hcs-key-demo.html"
KEY_DEMO_EN = NLDT_ROOT / "simulation" / "hcs-key-demo-en.html"


class TestKeyDemo:
    def test_pages_generated_and_filled(self):
        for path in (KEY_DEMO, KEY_DEMO_EN):
            text = path.read_text()
            assert "window.HCS_DATA" in text
            assert "id=\"selftest-badge\"" in text
            for marker in ("__HCS_DATA__", "__LANG__", "__BUILD_STAMP__"):
                assert marker not in text, f"{marker} niet gevuld in {path.name}"

    def test_nl_content(self):
        text = KEY_DEMO.read_text()
        assert '<html lang="nl">' in text
        assert "Ik ga verhuizen" in text
        assert "adresonderzoek" in text.lower()
        assert "Mens-agent-grens" in text

    def test_en_content(self):
        text = KEY_DEMO_EN.read_text()
        assert '<html lang="en">' in text
        assert "I want to move home" in text           # i18n-titel
        assert "Human-agent boundary" in text          # i18n-label
        assert 'window.HCS_LANG = "en"' in text        # taalvlag
        # Run-data (staptitels, handover-redenen) blijft in fase 1 Nederlands;
        # een volledig Engelse run-laag is fase 3-werk (spec §6).


MENU_HTML = NLDT_ROOT / "simulation" / "hcs-menu-demo.html"
INDEX_HTML = NLDT_ROOT / "simulation" / "index.html"
MAPPING_DOC = NLDT_ROOT.parent / "docs" / "HCS_RECIPES_AGENTIC_STATE.md"


def test_menu_demo_lists_all_thk():
    text = MENU_HTML.read_text()
    for code in ("THK-01", "THK-08", "THK-14", "THK-24", "THK-25"):
        assert code in text
    assert "fase 2" in text and "UAM" in text and "GRN" in text


def test_index_links_hcs():
    text = INDEX_HTML.read_text()
    assert 'href="hcs-key-demo.html"' in text and 'href="hcs-menu-demo.html"' in text


def test_mapping_doc_exists_with_mapping_table():
    text = MAPPING_DOC.read_text()
    for marker in ("B1", "poort 1", "hcs-life-event-run", "baselines"):
        assert marker in text
