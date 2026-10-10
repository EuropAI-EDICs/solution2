# HCS-recipes fase 2 — city dishes — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fase 2 van spec [`2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md): de acht city-recipes (UAM-01/09, GRN-01/03, CIR-04/01, MIN-01/04) landen als nldt-recipes met baselines en EDIC-adoptie, draaien via `hcs-recipe-run` (nu met `lang`-parameter), en krijgen vier dish-demo's plus de volledige menu-plaat (alle 53 recipes als kaarten) en de volledige agentic-state-mappingdoc.

**Architecture:** Hergebruik van de fase 1-patronen: tweetalige fixtures ({"nl","en"}) → deterministische executor (`_build_hcs_run` lokaliseert al; `execute_hcs_recipe_run` krijgt `lang`) → generator `build_runs.py` uitgebreid met `build_dish_pages` die **één gedeelde dish-template** per dish vult (offline SVG-visualisaties: kaartgrid, bladerdak-raster, tijdreeks, hubladder — bewust géén Leaflet/netwerk, conform de deterministische replay-filosofie) → menu-demo volledig. Klare-taalstem conform herziening R1 (inwoners-/professional-perspectief, geen systeemnamen in de hoofdtoon).

**Tech Stack:** Python 3 (`nldt/.venv`: stdlib + `jsonschema`), JSON Schema draft 2020-12, plain HTML/CSS/JS met inline SVG (huisstijl `nldt/simulation`), pytest.

**Spec:** [`docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md) v1.1 (goedgekeurd) + herziening R1 (volledig tweetalige weergavelaag, klare taal). Fase 1 is afgerond (zie executiestatus in het fase 1-plan).

## Global Constraints

- Python altijd `nldt/.venv/bin/python`; tests vanaf repo-root: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v` (conftest lost imports).
- JSON-schema's: draft 2020-12, `additionalProperties: false`; alle wijzigingen additief. De enige schema-wijziging in dit plan: `"cargo"` toevoegen aan de `serviceType`-enum (UAM-01).
- **Tweetalige fixtures:** elke weergavetekst `{"nl": "...", "en": "..."}`; canoniek enkelvoudig blijven: recipeId, stepId, scenario-`id`s, edge-slugs, KPI-namen, `dataSource`, `frequency`, `kviRollup`. NL-teksten van de disk-runs mogen wijzigen zolang de generator ze opnieuw genereert met dezelfde stamp.
- **Klare taal (stem R1):** professional/inwoner-perspectief, korte zinnen, "je/jij" waar een persoon wordt aangesproken; systeemnamen alleen als bronvermelding (canonieke citaten: PDOK, BRP, energienetbeheerder, SenSenNet e.d.).
- **Offline-deterministisch:** geen LLM, geen netwerk; demo's single-file en `file://`-werkend; **SVG-visualisaties in plaats van Leaflet** (afwijking op de letterlijke spec-formulering "Leaflet-stijl met tile-invert": we nemen "stijl" letterlijk — donkere kaartlook — maar bouwen offline SVG; echte kaartkoppeling = fase 3-optie). Determinisme: zelfde stamp → byte-identiek.
- City-demos zijn **NL** (EN blijft voorbehouden aan The Key volgens herziening R1); de fixture-tweetaligheid maakt EN later goedkoop.
- KPI-waarden letterlijk uit `recipes/05_KPI-framework_per-recipe.xlsx` (staan in dit plan).
- Demo-pagina's embedden hun payload via placeholders (`__DISH_DATA__`, `__DISH_ID__`, `__BUILD_STAMP__`) die de generator vult; geen `__...__`-restanten in output.
- Commit-stijl: `feat(nldt): …` / `test(nldt): …` / `docs(nldt): …` Nederlands; alleen eigen taakbestanden; untracked `recipes/` nooit committen.

---

### Task 1: Infra — `lang` op `hcs-recipe-run`, `cargo`-enum, city-fixture-contract

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (executor + process-definitie)
- Modify: `nldt/schemas/recipe.schema.json` (enum + `"cargo"`)
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Produces: `execute_hcs_recipe_run` accepteert `lang` (default "nl", zelfde gedrag als `hcs-life-event-run`); `hcs-recipe-run`-procesdefinitie krijgt input `lang`. `serviceType`-enum: `["reactive","proactive","measure","plan","share","system","infrastructure","cargo"]`.
- City-fixture-contract (Tasks 3–6 volgen dit exact): `{"recipeId", "scenarioKind": "city", "scenarios": [{"id", "label": {"nl","en"}}], "steps": [{"stepId", "title": {"nl","en"}, "defaults": {"actor", "genAiTestPoint", "dataUsed": [{"nl","en"}…], "consent", "kpiEvents": [{"kpi" (canoniek), "effect": {"nl","en"}}], "prov": {"sources": [{"nl","en"}…]}} , "perScenario": {<scenario-id>: {override velden}}}], "stopConditions": [{"id","condition": {"nl","en"},"action": {"nl","en"}}], "kpiSnapshot": [{"kpi","baseline","target"}], "learningState": [{...tweetalig}]}`. Alle lokalisatie loopt via de bestaande `localize`-helpers in `_build_hcs_run` (titel, dataUsed, kpiEffects, handover, prov.sources, stopconditions, learning) — géén nieuwe lokalisatiecode behalve scenario-labels in de paginabouwer (Task 2, via `localize`).

- [ ] **Step 1: Schrijf de falende tests**

Aan `nldt/tests/test_hcs.py`:

```python
def test_service_type_cargo_enum():
    recipe = {
        "id": "probe-cargo", "title": "Cargo-probe", "version": "1.0.0",
        "inputs": {}, "outputs": {},
        "steps": [{"id": "s1", "processId": "hcs-recipe-run", "inputs": {}}],
        "riskLevel": "medium",
        "service": {"dish": "urban-air-mobility", "lifeEventCode": "UAM-01",
                    "serviceType": "cargo"},
    }
    validate_instance(recipe, "recipe.schema.json")
    bad = dict(recipe, service={"dish": "urban-air-mobility", "serviceType": "raket"})
    with pytest.raises(Exception):
        validate_instance(bad, "recipe.schema.json")


def test_recipe_run_english(tmp_path):
    city = tmp_path / "city"
    city.mkdir()
    (city / "probe-city.json").write_text(json.dumps({
        "recipeId": "probe-city", "scenarioKind": "city",
        "scenarios": [{"id": "sc-1", "label": {"nl": "Proef", "en": "Probe"}}],
        "steps": [{
            "stepId": "meten", "title": {"nl": "We meten het groen", "en": "We measure the green"},
            "defaults": {"actor": "agent", "genAiTestPoint": "G2",
                          "dataUsed": [{"nl": "luchtbeelden", "en": "aerial imagery"}],
                          "consent": "n.v.t.", "kpiEvents": [], "consent": "n.v.t.",
                          "prov": {"sources": [{"nl": "remote sensing", "en": "remote sensing"}]}},
            "perScenario": {}}},
        ], "stopConditions": [{"id": "sc-1", "condition": {"nl": "c", "en": "c"},
                                "action": {"nl": "a", "en": "a"}}],
        "kpiSnapshot": [{"kpi": "k", "baseline": "", "target": ""}]}))
    from services.process_adapter.poc_handlers import execute_hcs_recipe_run
    out = execute_hcs_recipe_run({"recipeId": "probe-city", "scenario": "sc-1",
                                  "lang": "en"}, fixture_dir=tmp_path)
    assert out["run"]["steps"][0]["title"] == "We measure the green"
    assert out["run"]["steps"][0]["dataUsed"] == ["aerial imagery"]
```

Let op: in de dict-literal hierboven staat `"consent"` tweemaal in `defaults` — verwijder de dubbele regel bij overnemen (Python dicts staan het toe, maar het is rommel).

- [ ] **Step 2: Draai — moet falen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: FAIL — `cargo` niet in enum; `lang`-input bestaat niet (titel blijft Nederlands).

- [ ] **Step 3: Implementeer**

1. `nldt/schemas/recipe.schema.json`: in `$defs.serviceBlock.properties.serviceType.enum` voeg `"cargo"` toe.
2. `nldt/services/process_adapter/poc_handlers.py`:
   - `execute_hcs_recipe_run`: voeg `lang=inputs.get("lang") or "nl"` toe aan de `_build_hcs_run`-aanroep.
   - In `POC_PROCESS_DEFINITIONS["hcs-recipe-run"]["inputs"]`: voeg toe `"lang": {"title": "Taal van de weergaveteksten (nl|en)", "schema": {"type": "string", "default": "nl"}}`.

- [ ] **Step 4: Draai — moet slagen + regressie**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nldt/schemas/recipe.schema.json nldt/services/process_adapter/poc_handlers.py nldt/tests/test_hcs.py
git commit -m "feat(nldt): hcs-recipe-run met lang-parameter; serviceType cargo; city-fixture-contract"
```

---

### Task 2: Gedeelde dish-template + generator-uitbreiding

**Files:**
- Create: `nldt/simulation/hcs/dish-demo.template.html`
- Modify: `nldt/simulation/hcs/build_runs.py` (`DISHES`, `build_dish_pages(stamp)`, hook in `main`)
- Test: `nldt/tests/test_hcs.py` (uitbreiden — async per dish; hier alleen de generator-mechaniek testen met een probe-fixture)

**Interfaces:**
- Template-placeholders: `__DISH_DATA__` (JSON: `{dishes: {<dish>: {i18n, recipes: [{run, scenarioLabels, fixture}], siblings: [{code,title,mode,kpi,lens}]}}}` — alleen de eigen dish gevuld), `__DISH_ID__` (`"urban-air-mobility"` e.d.), `__BUILD_STAMP__`. Output: `nldt/simulation/hcs-uam-demo.html`, `hcs-grn-demo.html`, `hcs-cir-demo.html`, `hcs-min-demo.html`.
- `build_dish_pages` per dish: leest de twee city-fixtures, bouwt per scenario een run via `execute_hcs_recipe_run` (lang "nl"), localiseert scenario-labels via `localize`, laadt recipe-`service`-blokken (zoals `_fixture_service`), en rendert één pagina.
- Viz: de template bevat vier SVG-renderers (`vizMap`, `vizCanopy`, `vizSeries`, `vizTiers`); per recipe bepaalt `service.serviceType`/dish de keuze via een `viz`-veld in de dish-data (Task 3–6 vullen `"viz": "map"|"canopy"|"series"|"tiers"` + `vizData`).

- [ ] **Step 1: Schrijf de falende test** (template-niveau — de gegenereerde pagina's worden per dish in Tasks 3–6 getest)

```python
DISH_TEMPLATE = HCS_ROOT / "dish-demo.template.html"


def test_dish_template_contract():
    text = DISH_TEMPLATE.read_text()
    for marker in ("__DISH_DATA__", "__DISH_ID__", "__BUILD_STAMP__",
                   "function vizMap", "function vizCanopy", "function vizSeries", "function vizTiers"):
        assert marker in text
```

- [ ] **Step 2: Draai — moet falen** (template bestaat niet)

- [ ] **Step 3: Template schrijven**

`nldt/simulation/hcs/dish-demo.template.html` — volledige inhoud (zelfde `:root`-palet als fase 1):

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>HCS · dish-demo</title>
<style>
  :root {
    --papier: #f6f8fb; --inkt: #06121b; --inkt-2: #0d1e2c; --ijs: #dff3ff; --ijs-rand: #c4d0da;
    --blauw: #2ba8ff; --hemel: #79c9ff; --oranje: #ff9815; --oranje-donker: #ef8700; --amber: #ffc37e;
    --rood: #e10500; --mint: #1cefa5; --groen: #0f7a4d;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    --sans: Roboto, "Helvetica Neue", system-ui, -apple-system, Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--inkt); color: var(--papier); font-family: var(--sans); line-height: 1.5; padding: 22px clamp(14px, 4vw, 44px) 60px; }
  h1 { font-size: clamp(1.5rem, 3.2vw, 2.2rem); } h1 .dish { color: var(--oranje); }
  .sub { color: var(--hemel); font-family: var(--mono); font-size: .74rem; letter-spacing: .08em; text-transform: uppercase; }
  #selftest-badge { font-family: var(--mono); font-size: .72rem; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--ijs-rand); color: var(--ijs); }
  #selftest-badge.ok { border-color: var(--mint); color: var(--mint); }
  #selftest-badge.fail { border-color: var(--rood); color: var(--rood); font-weight: 700; }
  .topbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
  section { background: var(--inkt-2); border: 1px solid rgba(196,208,218,.25); border-radius: 4px; padding: 16px 18px; margin: 14px 0; }
  h2 { font-size: 1rem; color: var(--oranje); margin-bottom: 8px; }
  h3 { font-size: .92rem; color: var(--hemel); margin: 10px 0 6px; }
  .scenarios { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 14px; }
  .scenarios button { font: inherit; font-size: .8rem; background: transparent; color: var(--ijs); border: 1px dashed var(--ijs-rand); border-radius: 999px; padding: 6px 14px; cursor: pointer; }
  .scenarios button.active { border-style: solid; border-color: var(--blauw); color: #fff; background: rgba(43,168,255,.16); }
  .rail { display: flex; gap: 6px; margin: 10px 0; flex-wrap: wrap; }
  .rail button { font: inherit; font-size: .82rem; background: var(--inkt-2); color: var(--papier); border: 1px solid var(--ijs-rand); border-radius: 3px; padding: 8px 12px; cursor: pointer; }
  .rail button.active { background: var(--oranje-donker); border-color: var(--oranje); color: var(--inkt); font-weight: 700; }
  .rail button .g { font-family: var(--mono); font-size: .66rem; display: block; color: var(--hemel); }
  .rail button.active .g { color: var(--inkt); }
  .stapmeta { display: flex; flex-wrap: wrap; gap: 10px; font-family: var(--mono); font-size: .72rem; color: var(--hemel); margin-bottom: 10px; }
  .stapmeta b { color: var(--papier); }
  .actor-agent { color: var(--mint); } .actor-mens { color: var(--amber); } .actor-partij { color: var(--blauw); }
  .handover { border-left: 4px solid var(--amber); background: rgba(255,195,126,.1); padding: 10px 12px; margin: 10px 0; font-size: .9rem; }
  .handover b { color: var(--amber); }
  ul.data { list-style: none; font-size: .86rem; }
  ul.data li { padding: 4px 8px; border-left: 2px solid var(--ijs-rand); margin: 4px 0; }
  .src { font-family: var(--mono); font-size: .68rem; color: #7f93a2; margin-top: 8px; }
  .kvpanel table, .testbank table { width: 100%; border-collapse: collapse; font-size: .8rem; }
  .kvpanel th, .kvpanel td, .testbank th, .testbank td { text-align: left; padding: 5px 8px; border-bottom: 1px solid rgba(196,208,218,.2); }
  .lens { font-family: var(--mono); font-size: .7rem; padding: 1px 7px; border-radius: 3px; background: rgba(255,152,21,.15); color: var(--oranje); }
  .viz { background: rgba(223,243,255,.04); border: 1px solid rgba(196,208,218,.2); border-radius: 4px; padding: 10px; margin-top: 12px; }
  .viz svg { display: block; width: 100%; height: auto; }
  .viznote { font-family: var(--mono); font-size: .66rem; color: #7f93a2; margin-top: 6px; }
  .siblings { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 8px; margin-top: 8px; }
  .card { border: 1px solid rgba(196,208,218,.2); border-radius: 3px; padding: 8px 10px; font-size: .8rem; }
  .card b { color: var(--oranje); font-family: var(--mono); font-size: .72rem; }
  .card .kpi { display: block; color: var(--ijs); font-size: .74rem; margin-top: 4px; }
  .card.poc { border-color: var(--oranje); }
  .voet { font-family: var(--mono); font-size: .66rem; color: #7f93a2; margin-top: 24px; }
  a { color: var(--blauw); }
</style>
</head>
<body>
<div class="topbar">
  <div>
    <div class="sub" id="eyecatcher"></div>
    <h1><span class="dish" id="dish-title"></span></h1>
  </div>
  <span id="selftest-badge">selftest…</span>
</div>
<p class="sub" id="lede"></p>
<div class="scenarios" id="scenarios"></div>
<div class="rail" id="rail"></div>
<section id="step-detail">
  <h2 id="step-title"></h2>
  <div class="stapmeta" id="step-meta"></div>
  <div id="step-handover"></div>
  <ul class="data" id="step-data"></ul>
  <div class="src" id="step-src"></div>
  <div class="viz" id="viz-box"><div id="viz"></div><div class="viznote" id="viz-note"></div></div>
</section>
<section class="testbank"><h2 id="tb-title"></h2><table><tbody id="tb-body"></tbody></table></section>
<section class="kvpanel"><h2 id="kpi-title"></h2><p class="sub" id="kpi-sub"></p><table><thead id="kpi-head"></thead><tbody id="kpi-body"></tbody></table></section>
<section><h2 id="sib-title"></h2><div class="siblings" id="siblings"></div></section>
<div class="voet" id="voet"></div>
<script>
window.DISH_DATA = __DISH_DATA__;
window.DISH_ID = __DISH_ID__;
window.DISH_STAMP = "__BUILD_STAMP__";
</script>
<script>
(function () {
  "use strict";
  var D = window.DISH_DATA, t = D.i18n, state = { recipe: 0, scenario: 0, step: 0 };
  function el(id) { return document.getElementById(id); }
  function recipe() { return D.recipes[state.recipe]; }
  function run() { return recipe().runs[state.scenario]; }

  function renderHeader() {
    el("eyecatcher").textContent = t.eyecatcher;
    el("dish-title").textContent = t.title;
    el("lede").textContent = t.lede;
    el("tb-title").textContent = t.testbank;
    el("kpi-title").textContent = t.kpiPanel;
    el("kpi-sub").textContent = t.kpiSub;
    el("sib-title").textContent = t.siblings;
    el("voet").textContent = t.foot.replace("{stamp}", window.DISH_STAMP);
  }

  function renderScenarios() {
    var box = el("scenarios"); box.innerHTML = "";
    recipe().scenarioLabels.forEach(function (label, i) {
      var b = document.createElement("button");
      b.textContent = label;
      if (i === state.scenario) b.className = "active";
      b.onclick = function () { state.scenario = i; state.step = 0; renderAll(); };
      box.appendChild(b);
    });
  }

  function renderRail() {
    var rail = el("rail"); rail.innerHTML = "";
    run().steps.forEach(function (s, i) {
      var b = document.createElement("button");
      b.innerHTML = (i + 1) + ". " + s.title + '<span class="g">' + s.genAiTestPoint + "</span>";
      if (i === state.step) b.className = "active";
      b.onclick = function () { state.step = i; renderRail(); renderStep(); };
      rail.appendChild(b);
    });
  }

  function renderStep() {
    var s = run().steps[state.step];
    el("step-title").textContent = s.title;
    el("step-meta").innerHTML =
      '<span><b>' + t.actor + ':</b> <span class="actor-' + s.actor + '">' + t.actorNames[s.actor] + "</span></span>" +
      '<span><b>GenAI:</b> ' + s.genAiTestPoint + "</span>" +
      '<span><b>' + t.consent + ':</b> ' + t.consentNames[s.consent] + "</span>";
    el("step-handover").innerHTML = s.handover
      ? '<div class="handover"><b>' + t.handover + ":</b> " + s.handover.reason + " → " + s.handover.to + "</div>"
      : "";
    el("step-data").innerHTML = s.dataUsed.map(function (d) { return "<li>" + d + "</li>"; }).join("");
    el("step-src").textContent = t.sources + ": " + s.prov.sources.join(" · ");
    renderViz(s);
  }

  var VIZ = {
    map: vizMap, canopy: vizCanopy, series: vizSeries, tiers: vizTiers
  };

  function renderViz(s) {
    var v = recipe().viz;
    var box = el("viz"); box.innerHTML = "";
    el("viz-note").textContent = v.note;
    if (VIZ[v.kind]) box.innerHTML = VIZ[v.kind](v.data, state.scenario, state.step);
  }

  function svgOpen(h) { return '<svg viewBox="0 0 640 ' + h + '" xmlns="http://www.w3.org/2000/svg" role="img">'; }
  function grid(h) {
    var out = "";
    for (var x = 0; x < 640; x += 32) out += '<line x1="' + x + '" y1="0" x2="' + x + '" y2="' + h + '" stroke="rgba(196,208,218,.08)"/>';
    for (var y = 0; y < h; y += 32) out += '<line x1="0" y1="' + y + '" x2="640" y2="' + y + '" stroke="rgba(196,208,218,.08)"/>';
    return out;
  }

  function vizMap(data, sc, step) {
    var h = 300, out = svgOpen(h) + grid(h);
    data.zones.forEach(function (z) {
      out += '<circle cx="' + z.x + '" cy="' + z.y + '" r="' + z.r + '" fill="rgba(225,5,0,.14)" stroke="var(--rood)" stroke-dasharray="6 4"/>';
    });
    (data.routes[sc] || []).forEach(function (r, i) {
      var pts = r.points.map(function (p) { return p[0] + "," + p[1]; }).join(" ");
      out += '<polyline points="' + pts + '" fill="none" stroke="' + (i === 0 ? "var(--oranje)" : "var(--blauw)") + '" stroke-width="3" stroke-linejoin="round"/>';
      r.points.forEach(function (p) { out += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="5" fill="var(--hemel)"/>'; });
    });
    (data.labels || []).forEach(function (l) {
      out += '<text x="' + l.x + '" y="' + l.y + '" fill="var(--ijs)" font-size="13" font-family="var(--sans)">' + l.text + "</text>";
    });
    return out + "</svg>";
  }

  function vizCanopy(data, sc) {
    var h = 300, out = svgOpen(h) + grid(h), cell = data.cell;
    data.cells[sc].forEach(function (c) {
      out += '<rect x="' + c.x + '" y="' + c.y + '" width="' + cell + '" height="' + cell +
        '" rx="4" fill="' + (c.cover >= 30 ? "rgba(28,239,165,.55)" : "rgba(255,152,21,.45)") + '"/>' +
        '<text x="' + (c.x + cell / 2) + '" y="' + (c.y + cell / 2 + 4) + '" text-anchor="middle" font-size="11" fill="var(--inkt)" font-family="var(--mono)">' + c.cover + "%</text>";
    });
    return out + "</svg>";
  }

  function vizSeries(data, sc) {
    var h = 300, s = data.series[sc], out = svgOpen(h) + grid(h), pts = "";
    s.points.forEach(function (p, i) {
      var x = 40 + i * (560 / (s.points.length - 1)), y = 260 - p.value * 2.2;
      pts += (i ? " " : "") + x + "," + y;
      if (i % 2 === 0) out += '<text x="' + x + '" y="285" text-anchor="middle" font-size="11" fill="#7f93a2" font-family="var(--mono)">' + p.label + "</text>";
    });
    out += '<polyline points="' + pts + '" fill="none" stroke="var(--mint)" stroke-width="3"/>';
    out += '<line x1="40" y1="' + (260 - s.target * 2.2) + '" x2="600" y2="' + (260 - s.target * 2.2) + '" stroke="var(--oranje)" stroke-dasharray="6 4"/>';
    out += '<text x="40" y="' + (250 - s.target * 2.2) + '" font-size="12" fill="var(--oranje)" font-family="var(--sans)">' + t.vizTarget + " " + s.target + "%</text>";
    return out + "</svg>";
  }

  function vizTiers(data) {
    var h = 300, out = svgOpen(h) + grid(h), cx = 320, cy = 150;
    data.tiers.forEach(function (tier, i) {
      out += '<circle cx="' + cx + '" cy="' + cy + '" r="' + tier.r + '" fill="none" stroke="' +
        (tier.live > 0 ? "var(--mint)" : "var(--ijs-rand)") + '" stroke-width="2" stroke-dasharray="' + (tier.live > 0 ? "none" : "6 4") + '"/>';
      out += '<text x="' + cx + '" y="' + (cy - tier.r + 16) + '" text-anchor="middle" font-size="12" fill="var(--ijs)" font-family="var(--sans)">' + tier.name + " · " + tier.live + "/" + tier.plan + "</text>";
    });
    out += '<circle cx="' + cx + '" cy="' + cy + '" r="6" fill="var(--oranje)"/>';
    return out + "</svg>";
  }

  function renderTestbank() {
    el("tb-body").innerHTML = D.common.testbank.map(function (axis) {
      var name = (t.axisNames && t.axisNames[axis]) || axis;
      var verdict = D.selftestVerdicts[D.dishId][axis];
      var state = verdict === true ? ["var(--mint)", t.tbOk] : verdict === false ? ["var(--rood)", t.tbFail] : ["var(--amber)", t.tbCheck];
      return "<tr><td>" + name + "</td><td style='color:" + state[0] + "'>" + state[1] + "</td></tr>";
    }).join("");
  }

  function renderKpi() {
    el("kpi-head").innerHTML = "<tr><th>" + t.kpi + "</th><th>" + t.kpiType + "</th><th>Lens</th><th>" + t.dataSource + "</th><th>KVI</th></tr>";
    el("kpi-body").innerHTML = recipe().service.kpis.map(function (k) {
      return "<tr><td>" + k.kpi + "</td><td>" + k.kpiType + "</td><td><span class='lens'>" + k.outcomeLens + "</span></td><td>" + k.dataSource + "</td><td>" + (k.kviRollup || "—") + "</td></tr>";
    }).join("");
  }

  function renderSiblings() {
    el("siblings").innerHTML = D.siblings.map(function (r) {
      return "<div class='card" + (r.poc ? " poc" : "") + "'><b>" + r.code + "</b> " + r.title +
        "<span class='kpi'>" + r.kpi + "</span><span class='lens'>" + r.mode + " · lens " + r.lens + "</span></div>";
    }).join("");
  }

  function selftest() {
    var checks = [];
    checks.push(["recipes aanwezig", D.recipes.length === 2]);
    checks.push(["runs per recipe", D.recipes.every(function (r) { return r.runs.length >= 1; })]);
    checks.push(["stappen per run", D.recipes.every(function (r) {
      return r.runs.every(function (run) { return run.steps.length >= 3; }); })]);
    checks.push(["viz-config aanwezig", D.recipes.every(function (r) { return r.viz && r.viz.kind; })]);
    checks.push(["G-punt per stap", D.recipes.every(function (r) {
      return r.runs[0].steps.every(function (s) { return !!s.genAiTestPoint; }); })]);
    checks.push(["bron per stap", D.recipes.every(function (r) {
      return r.runs[0].steps.every(function (s) { return s.prov.sources.length > 0; }); })]);
    checks.push(["stopcondities (poort 5)", D.recipes.every(function (r) {
      return r.runs[0].stopConditions.length > 0; })]);
    checks.push(["KPI's per recipe (poort 1)", D.recipes.every(function (r) {
      return r.service.kpis.length > 0; })]);
    checks.push(["sibling-kaarten", D.siblings.length >= 3]);
    checks.push(["testbank-assen", D.common.testbank.length === 7]);
    var failed = checks.filter(function (c) { return !c[1]; });
    var badge = el("selftest-badge");
    badge.textContent = (failed.length === 0 ? "selftest " : "SELFTEST ") + (checks.length - failed.length) + "/" + checks.length;
    badge.className = failed.length === 0 ? "ok" : "fail";
    return failed.length === 0;
  }

  function renderAll() { renderScenarios(); renderRail(); renderStep(); renderTestbank(); renderKpi(); renderSiblings(); }
  renderHeader(); renderAll(); selftest();
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Generator-uitbreiding**

In `build_runs.py` (boven `main`):

```python
DISH_DEFS = {
    "uam": {"file": NLDT_ROOT / "simulation" / "hcs-uam-demo.html",
            "recipes": ["uam-01-medical-logistics", "uam-09-geofencing-zones"],
            "viz": {"uam-01-medical-logistics": {"kind": "map"},
                    "uam-09-geofencing-zones": {"kind": "map"}}},
    "grn": {"file": NLDT_ROOT / "simulation" / "hcs-grn-demo.html",
            "recipes": ["grn-01-canopy-measure", "grn-03-300m-gaps"],
            "viz": {"grn-01-canopy-measure": {"kind": "canopy"},
                    "grn-03-300m-gaps": {"kind": "canopy"}}},
    "cir": {"file": NLDT_ROOT / "simulation" / "hcs-cir-demo.html",
            "recipes": ["cir-04-shared-energy", "cir-01-circular-condition"],
            "viz": {"cir-04-shared-energy": {"kind": "series"},
                    "cir-01-circular-condition": {"kind": "series"}}},
    "min": {"file": NLDT_ROOT / "simulation" / "hcs-min-demo.html",
            "recipes": ["min-01-proximity-analysis", "min-04-hub-network"],
            "viz": {"min-01-proximity-analysis": {"kind": "tiers"},
                    "min-04-hub-network": {"kind": "tiers"}}},
}

DISH_I18N = {
    "uam": {"eyecatcher": "Human-Centred Services · dish: Urban Air Mobility", "title": "De lucht in — zonder de stad te verstoppen",
            "lede": "Twee recipes uit deze dish, gedraaid als deterministische replay: wat gebeurt er, wie bepaalt het, en waar komt de informatie vandaan.",
            "foot": "HCS fase 2 · build {stamp} · runs gevalideerd tegen hcs-run.schema.json · doctrine: AI stelt voor · pijplijn beslist · mens beslist",
            "testbank": "Wat we hebben getest voordat dit live ging", "tbOk": "go", "tbCheck": "nog niet getoetst", "tbFail": "geen go",
            "kpiPanel": "Wat we willen bereiken — gemeten vanaf dag één", "kpiSub": "Elke recipe meet of het echt beter wordt.",
            "kpi": "KPI", "kpiType": "Type", "dataSource": "Bron", "siblings": "De andere recipes in deze dish",
            "actor": "Wie handelt", "consent": "Toestemming", "handover": "Een mens neemt over", "sources": "Waar deze informatie vandaan komt",
            "actorNames": {"agent": "het systeem (onder toezicht)", "mens": "een mens", "partij": "de betrokken organisatie"},
            "consentNames": {"n.v.t.": "niet nodig", "gevraagd": "gevraagd", "gegeven": "gegeven", "geweigerd": "geweigerd"},
            "vizTarget": "doel:",
            "axisNames": {"accuracy": "nauwkeurig", "plain language": "gewone taal", "once-only": "één keer vragen",
                           "explainability": "uitlegbaar", "human handover": "mens neemt over",
                           "bias": "vooringenomenheid", "AI Act risk class": "AI-wet risicoklasse"}},
    # grn / cir / min: zelfde structuur met eigen titel/lede; Exacte teksten per dish staan bij Tasks 3–6.
}
DISH_I18N["grn"] = dict(DISH_I18N["uam"], title="Groen meten, groen doen",
                        lede="Twee 3-30-300-recipes: hoeveel bladerdak heeft je wijk, en wie woont verder dan 300 meter van echt goed groen?")
DISH_I18N["grn"]["eyecatcher"] = "Human-Centred Services · dish: 3-30-300"
DISH_I18N["cir"] = dict(DISH_I18N["uam"], title="Delen is het nieuwe bezitten",
                        lede="Twee circular-recipes: gedeelde energie in de buurt en circulariteit als harde eis bij nieuwbouw.")
DISH_I18N["cir"]["eyecatcher"] = "Human-Centred Services · dish: Circular neighborhoods"
DISH_I18N["min"] = dict(DISH_I18N["uam"], title="Alles wat je dagelijks nodig hebt, dichtbij",
                        lede="Twee 15-minute-city-recipes: welke wijk ligt buiten bereik van voorzieningen, en waar komen de hubs?")
DISH_I18N["min"]["eyecatcher"] = "Human-Centred Services · dish: 15-minute city"


def build_dish_pages(stamp: str) -> None:
    template = (HCS_ROOT / "dish-demo.template.html").read_text(encoding="utf-8")
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text(encoding="utf-8"))
    for dish, spec in DISH_DEFS.items():
        recipes = []
        for rid in spec["recipes"]:
            fx = json.loads((HCS_ROOT / "fixtures" / "city" / f"{rid}.json").read_text(encoding="utf-8"))
            recipe = json.loads((NLDT_ROOT / "recipes" / f"{rid}.json").read_text(encoding="utf-8"))
            runs, labels = [], []
            for sc in fx["scenarios"]:
                out = execute_hcs_recipe_run({"recipeId": rid, "scenario": sc["id"], "mode": "replay"})
                runs.append(out["run"])
                labels.append(localize(sc["label"], "nl"))
            recipes.append({
                "id": rid, "runs": runs, "scenarioLabels": labels,
                "service": recipe["service"],
                "viz": dict(spec["viz"][rid], data=_viz_data(rid)),
            })
        data = {"dishId": dish, "recipes": recipes, "common": common,
                "i18n": DISH_I18N[dish], "siblings": _menu_siblings(dish),
                "selftestVerdicts": {dish: {"bias": True, "AI Act risk class": True}}}
        html = (template
                .replace("__DISH_DATA__", json.dumps(data, ensure_ascii=False))
                .replace("__DISH_ID__", json.dumps(dish))
                .replace("__BUILD_STAMP__", stamp))
        spec["file"].write_text(html, encoding="utf-8")
        print(f"OK dish {spec['file'].relative_to(NLDT_ROOT)}")
```

`_viz_data(rid)` levert per recipe het viz-data-object (zones/routes, canopy-cellen, tijdreeks, hub-tiers) — **de exacte inhoud staat bij de dish-taken** (Tasks 3–6). `_menu_siblings(dish)` levert de sibling-kaarten uit het menu-data-bestand dat Task 7 aanmaakt (`nldt/simulation/hcs/menu-data.json` met alle 53 rijen); tot die taak bestaat het nog niet — maak `menu-data.json` **al in deze taak** met alle 53 rijen (zie Task 7 voor de exacte rijen) zodat `_menu_siblings` direct werkt:

```python
def _menu_siblings(dish: str) -> list[dict]:
    rows = json.loads((HCS_ROOT / "menu-data.json").read_text(encoding="utf-8"))[dish]
    poc = set(DISH_DEFS[dish]["recipes"])
    return [{"code": r[0], "title": r[1], "mode": r[2], "kpi": r[3], "lens": r[4],
             "poc": r[5] in poc} for r in rows]
```

(menu-data-rijen zijn 6-koloms: code, titel, mode, kpi, lens, recipeId-of-"").

Hook in `main()`, na de bestaande `build_pages`-aanroep: `build_dish_pages(args.stamp)` (vervang de betekenis van `--only-runs`: alleen runs, géén pagina's — dishes vallen daar ook onder).

- [ ] **Step 5: Draai en commit de infra**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: PASS (template-contract). Commit:

```bash
git add nldt/simulation/hcs/dish-demo.template.html nldt/simulation/hcs/build_runs.py nldt/tests/test_hcs.py
git commit -m "feat(nldt): gedeelde dish-template met offline SVG-viz en build_dish_pages-generator"
```

(page-tests per dish volgen in Tasks 3–6; `build_dish_pages` faalt pas netjes als city-fixtures ontbreken — dat is pas aan de orde in Task 3.)

---

### Task 3: Urban Air Mobility — fixtures, recipes, baselines, EDIC, dish-pagina

**Files:**
- Create: `nldt/simulation/hcs/fixtures/city/uam-01-medical-logistics.json`
- Create: `nldt/simulation/hcs/fixtures/city/uam-09-geofencing-zones.json`
- Create: `nldt/recipes/uam-01-medical-logistics.json`, `uam-09-geofencing-zones.json`
- Create: `nldt/recipes/baselines/uam-01-medical-logistics.baseline.json`, `uam-09-geofencing-zones.baseline.json`
- Modify: `nldt/recipes/edic-asset-map.json` (twee entries, `updated` op vandaag)
- Modify: `nldt/simulation/hcs/build_runs.py` (`_viz_data` voor UAM)
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- City-recipes hebben steps: één step `{"id": "life-event"→"run", "processId": "hcs-recipe-run", "inputs": {"recipeId": <id>, "scenario": "${recipe.inputs.scenario}", "mode": "${recipe.inputs.mode}"}, "outputs": {"run": "run"}}`, `requiredProcesses: ["hcs-recipe-run"]`, inputs `scenario` + `mode` (beide optional), `service`-blok met dish, lifeEventCode (UAM-01/UAM-09), serviceType (`cargo` resp. `infrastructure`), partijen, legalBasis, humanMeasure, genAiTestPoints, kpis — KPI's letterlijk uit het framework.

- [ ] **Step 1: Falende tests**

```python
CITY_IDS = ("uam-01-medical-logistics", "uam-09-geofencing-zones",
            "grn-01-canopy-measure", "grn-03-300m-gaps",
            "cir-04-shared-energy", "cir-01-circular-condition",
            "min-01-proximity-analysis", "min-04-hub-network")
CITY_FIXTURES_DIR = HCS_ROOT / "fixtures" / "city"


@pytest.mark.parametrize("rid", ["uam-01-medical-logistics", "uam-09-geofencing-zones"])
def test_city_recipe_and_baseline_valid(rid):
    recipe = load_recipe(rid)
    assert recipe["service"]["dish"] == "urban-air-mobility"
    assert recipe["requiredProcesses"] == ["hcs-recipe-run"]
    baseline = json.loads((NLDT_ROOT / "recipes" / "baselines" / f"{rid}.baseline.json").read_text())
    validate_instance(baseline, "hcs-baseline.schema.json")
    assert baseline["recipeId"] == rid and baseline["disappearingStep"]


def test_city_fixtures_bilingual_and_runnable(rid="uam-01-medical-logistics"):
    fx = json.loads((CITY_FIXTURES_DIR / f"{rid}.json").read_text())
    sc_ids = {s["id"] for s in fx["scenarios"]}
    assert len(sc_ids) >= 1
    for step in fx["steps"]:
        assert isinstance(step["title"], dict) and set(step["title"]) >= {"nl", "en"}
    out = execute_local("hcs-recipe-run", {"recipeId": rid, "scenario": sorted(sc_ids)[0]})
    validate_instance(out["run"], "hcs-run.schema.json")


def test_uam_page_generated():
    text = (NLDT_ROOT / "simulation" / "hcs-uam-demo.html").read_text()
    assert "window.DISH_DATA" in text and 'window.DISH_ID = "uam"' in text
    for marker in ("__DISH_DATA__", "__DISH_ID__", "__BUILD_STAMP__"):
        assert marker not in text
    assert "UAM-01" in text and "uam-01-medical-logistics" in text
    assert "selftest-badge" in text
```

- [ ] **Step 2: Draai — moet falen** (recipes/fixtures ontbreken)

- [ ] **Step 3: Fixtures schrijven**

`nldt/simulation/hcs/fixtures/city/uam-01-medical-logistics.json` (bron: xlsx UAM-01 "Hospital → sample → drone corridor → lab in minutes"; KPI "Delivery-time reduction vs road", outcome %, lens W; G-punten zijn het goedgekeurde voorstel uit spec §1):

```json
{
  "recipeId": "uam-01-medical-logistics",
  "scenarioKind": "city",
  "scenarios": [
    {"id": "routine", "label": {"nl": "Vaste route: ziekenhuis → lab via de corridor", "en": "Fixed route: hospital → lab via the corridor"}},
    {"id": "spoed", "label": {"nl": "Spoedzending buiten de vaste route", "en": "Urgent delivery off the fixed route"}}
  ],
  "steps": [
    {
      "stepId": "route", "title": {"nl": "De snelste veilige route wordt bepaald", "en": "The fastest safe route is chosen"},
      "defaults": {"actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": [{"nl": "de luchtroute van ziekenhuis naar lab", "en": "the air route from hospital to lab"},
                      {"nl": "actuele weers- en windinformatie", "en": "current weather and wind"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Delivery-time reduction vs road", "effect": {"nl": "de droneweegtijd wordt vergeleken met de routetijd over de weg", "en": "drone travel time is compared with road travel time"}}],
        "prov": {"sources": [{"nl": "luchtruimregister (geo-registry)", "en": "geo-registry"}, {"nl": "weerdienst", "en": "weather service"}]}},
      "perScenario": {}
    },
    {
      "stepId": "corridor", "title": {"nl": "De route wordt getoetst aan beschermde zones", "en": "The route is checked against protected zones"},
      "defaults": {"actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": [{"nl": "de vaste medische corridor", "en": "the fixed medical corridor"},
                      {"nl": "zones waar niet gevlogen mag worden", "en": "zones where flying is not allowed"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Delivery-time reduction vs road", "effect": {"nl": "de route blijft binnen de toegestane corridor", "en": "the route stays inside the allowed corridor"}}],
        "prov": {"sources": [{"nl": "geo-registry: geofencing-zones", "en": "geo-registry: geofencing zones"}]}},
      "perScenario": {
        "spoed": {"handover": {"reason": {"nl": "De route wijkt af van de vaste corridor — een mens bevestigt de omweg.", "en": "The route leaves the fixed corridor — a human confirms the detour."},
                                 "to": {"nl": "de luchtverkeersleider van de gemeente", "en": "the municipal air-traffic operator"}},
                   "actor": "mens"}
      }
    },
    {
      "stepId": "status", "title": {"nl": "Ziekenhuis en lab zien de zending live", "en": "Hospital and lab follow the delivery live"},
      "defaults": {"actor": "partij", "genAiTestPoint": "G4",
        "dataUsed": [{"nl": "statusmeldingen aan beide ziekenhuispunten", "en": "status updates to both hospital endpoints"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Delivery-time reduction vs road", "effect": {"nl": "ontvangsttijd wordt geregistreerd en vergeleken met de weg", "en": "arrival time is logged and compared with the road"}}],
        "prov": {"sources": [{"nl": "logistiek-systeem van het ziekenhuis", "en": "hospital logistics system"}]}},
      "perScenario": {}
    }
  ],
  "stopConditions": [
    {"id": "sc-uam01-1", "condition": {"nl": "Meer dan 1 op de 20 zendingen heeft een menselijke omweg-bevestiging nodig.", "en": "More than 1 in 20 deliveries needs a human detour confirmation."},
     "action": {"nl": "Corridor-voorspelbaarheid verbeteren voordat de spoedroute automatisch mag.", "en": "Improve corridor predictability before the urgent route may run automatically."}},
    {"id": "sc-uam01-2", "condition": {"nl": "Tijdswinst vergeleken met de weg valt weg.", "en": "The time advantage over the road disappears."},
     "action": {"nl": "Terug naar ontwerp: is de corridor nog de juiste?", "en": "Back to design: is the corridor still the right one?"}}
  ],
  "kpiSnapshot": [{"kpi": "Delivery-time reduction vs road", "baseline": "", "target": ""}],
  "learningState": [
    {"signal": {"nl": "Spoedzendingen gebeuren vooral bij slecht weer.", "en": "Urgent deliveries cluster in bad weather."},
     "why": {"nl": "Dan zijn wegambulances trager.", "en": "Road ambulances are slower then."},
     "change": {"nl": "Weerlimieten per corridor-type publiceren in de recipe.", "en": "Publish weather limits per corridor type in the recipe."},
     "decidesBy": {"nl": "function steward + ziekenhuislogistiek", "en": "function steward + hospital logistics"}, "helped": null}
  ]
}
```

`nldt/simulation/hcs/fixtures/city/uam-09-geofencing-zones.json` (bron: xlsx UAM-09 "Define no-fly & sensitive-site zones → Identity of Things → …"; KPI "Protected / geofenced zones defined", output #, lens —; geo-registry quarterly):

```json
{
  "recipeId": "uam-09-geofencing-zones",
  "scenarioKind": "city",
  "scenarios": [
    {"id": "ziekenhuis", "label": {"nl": "Een vaste beschermde zone rond het ziekenhuis", "en": "A permanent protected zone around the hospital"}},
    {"id": "evenement", "label": {"nl": "Een tijdelijke zone boven een evenement", "en": "A temporary zone above an event"}}
  ],
  "steps": [
    {
      "stepId": "definieer", "title": {"nl": "De zone wordt vastgelegd op de kaart", "en": "The zone is drawn on the map"},
      "defaults": {"actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": [{"nl": "de plek die beschermd moet worden", "en": "the location that needs protection"},
                      {"nl": "bestaande zones in de buurt", "en": "existing zones nearby"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Protected / geofenced zones defined", "effect": {"nl": "de zone wordt als kaartobject aangemaakt", "en": "the zone is created as a map object"}}],
        "prov": {"sources": [{"nl": "geo-registry", "en": "geo-registry"}]}},
      "perScenario": {}
    },
    {
      "stepId": "toets", "title": {"nl": "De nieuwe zone wordt getoetst aan bestaande zones en regels", "en": "The new zone is checked against existing zones and rules"},
      "defaults": {"actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": [{"nl": "overlap met bestaande no-flyzones en corridors", "en": "overlap with existing no-fly zones and corridors"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Protected / geofenced zones defined", "effect": {"nl": "botsingen met corridors worden vóór publicatie gevonden", "en": "conflicts with corridors are found before publishing"}}],
        "prov": {"sources": [{"nl": "geo-registry: corridors en no-flyzones", "en": "geo-registry: corridors and no-fly zones"}]}},
      "perScenario": {
        "evenement": {"handover": {"reason": {"nl": "Een tijdelijke zone raakt een vaste corridor — een mens weegt de belangen.", "en": "A temporary zone touches a fixed corridor — a human weighs the interests."},
                                     "to": {"nl": "de luchtverkeersleider van de gemeente", "en": "the municipal air-traffic operator"}}}
      }
    },
    {
      "stepId": "publiceer", "title": {"nl": "Drones krijgen de zone automatisch mee", "en": "Drones receive the zone automatically"},
      "defaults": {"actor": "partij", "genAiTestPoint": "—",
        "dataUsed": [{"nl": "de zone gaat de lucht in via het identificatiesysteem voor drones", "en": "the zone is broadcast via the drone identification system"}],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Protected / geofenced zones defined", "effect": {"nl": "de zone telt mee in de kwartaaltelling", "en": "the zone counts in the quarterly count"}}],
        "prov": {"sources": [{"nl": "U-space identificatiesysteem", "en": "U-space identification system"}]}},
      "perScenario": {}
    }
  ],
  "stopConditions": [
    {"id": "sc-uam09-1", "condition": {"nl": "Een gepubliceerde zone botst achteraf met een corridor.", "en": "A published zone turns out to conflict with a corridor."},
     "action": {"nl": "Publiceren stopt tot de toets is bijgesteld.", "en": "Publishing stops until the check is fixed."}},
    {"id": "sc-uam09-2", "condition": {"nl": "Zone-schendingen worden niet (op tijd) gemeld.", "en": "Zone violations are not reported (in time)."},
     "action": {"nl": "Handhavingsketen toetsen met de handhaver — geen automatische boetes.", "en": "Review the enforcement chain with the enforcer — no automated fines."}}
  ],
  "kpiSnapshot": [{"kpi": "Protected / geofenced zones defined", "baseline": "", "target": ""}],
  "learningState": [
    {"signal": {"nl": "Tijdelijke zones worden vaker aangevraagd dan verwacht.", "en": "Temporary zones are requested more often than expected."},
     "why": {"nl": "Elk evenement vraagt er een aan.", "en": "Every event requests one."},
     "change": {"nl": "Standaard-procedure voor evenementzones opnemen in de recipe.", "en": "Add a standard procedure for event zones to the recipe."},
     "decidesBy": {"nl": "function steward + Openbare Ruimte", "en": "function steward + Public Space"}, "helped": null}
  ]
}
```

- [ ] **Step 4: Recipes + baselines + EDIC**

`nldt/recipes/uam-01-medical-logistics.json`:

```json
{
  "id": "uam-01-medical-logistics",
  "title": "Urban Air Mobility UAM-01 — 'I want medical logistics by air'",
  "description": "City-recipe: ziekenhuis → monster → dronecorridor → lab in minuten. De route wordt getoetst aan beschermde zones; wijkt ze af van de vaste corridor, dan bevestigt een mens de omweg. KPI: tijdswinst ten opzichte van de weg. Deterministische replay via hcs-recipe-run.",
  "version": "1.0.0",
  "tags": ["hcs", "edic", "urban-air-mobility", "uam-01", "city-recipe"],
  "requiredProcesses": ["hcs-recipe-run"],
  "inputs": {"scenario": {"type": "string", "description": "scenario-id: routine|spoed", "required": false}, "mode": {"type": "string", "description": "replay|execute", "required": false}, "lang": {"type": "string", "description": "nl|en", "required": false}},
  "outputs": {"run": {"type": "json", "description": "HCS run-artefact"}},
  "steps": [{"id": "run", "processId": "hcs-recipe-run", "title": "Replay medische logistiek", "inputs": {"recipeId": "uam-01-medical-logistics", "scenario": "${recipe.inputs.scenario}", "mode": "${recipe.inputs.mode}", "lang": "${recipe.inputs.lang}"}, "outputs": {"run": "run"}, "backend": "local"}],
  "riskLevel": "medium",
  "service": {
    "dish": "urban-air-mobility", "lifeEventCode": "UAM-01", "serviceType": "cargo",
    "parties": [{"name": "Ziekenhuis", "role": "afzender en ontvanger"}, {"name": "Drone-operator", "role": "uitvoering"}, {"name": "Gemeente", "role": "corridor- en zones-beheer"}],
    "legalBasis": [{"basis": "Omgevingswet / droneswetgeving (U-space)", "timeLimit": "per zending geregistreerd"}],
    "humanMeasure": {"handover": ["Afwijkende route (buiten de vaste corridor) → mens bevestigt"], "exceptions": ["spoed bij slecht weer", "noodzendingen"]},
    "localVariant": "corridor-keuze is gemeentelijk beleid",
    "genAiTestPoints": [
      {"point": "G2", "description": "Routekiezer stelt alleen routes voor binnen toegestane corridors", "testCases": ["routine-route blijft binnen corridor"]},
      {"point": "G4", "description": "Status-uitleg naar ziekenhuis en lab", "testCases": ["beide eindpunten zien dezelfde status"]},
      {"point": "G5", "description": "Tijdswinst wordt geregistreerd en teruggekoppeld", "testCases": ["KPI-effect per zending"]}
    ],
    "kpis": [{"kpi": "Delivery-time reduction vs road", "kpiType": "outcome", "unit": "%", "outcomeLens": "W", "baseline": "", "target": "", "dataSource": "logistics logs", "frequency": "monthly", "kviRollup": "KVI 1 (Mobility: clean, shared) · KVI 5 (Digital)"}]
  },
  "cookbookUri": "http://localhost:8081/recipes/uam-01-medical-logistics"
}
```

`nldt/recipes/uam-09-geofencing-zones.json`: zelfde scaffold met `id: "uam-09-geofencing-zones"`, title "…UAM-09 — 'I want geofencing & security zones'", serviceType `"infrastructure"`, service-kpis `{"kpi": "Protected / geofenced zones defined", "kpiType": "output", "unit": "#", "outcomeLens": "—", "dataSource": "geo-registry", "frequency": "quarterly", "kviRollup": "KVI 1 (Mobility: clean, shared) · KVI 5 (Digital)"}`, riskLevel `"high"`, humanMeasure handover `["Tijdelijke zone die een corridor raakt → mens weegt belangen"]`, genAiTestPoints G2 (zonetoets) + G5 (signaal bij schending), inputs scenario `ziekenhuis|evenement`.

`nldt/recipes/baselines/uam-01-medical-logistics.baseline.json`:

```json
{
  "recipeId": "uam-01-medical-logistics",
  "publicOutcome": "Kritische medische zendingen zijn er in minuten in plaats van in het verkeer — met corridors die de stad veilig houdt.",
  "disappearingStep": "De koerier-rit door druk verkeer verdwijnt voor monsters en materialen tussen ziekenhuispunten.",
  "kpis": [{"kpi": "Delivery-time reduction vs road", "kpiType": "outcome", "unit": "%", "outcomeLens": "W", "baseline": "", "target": "", "dataSource": "logistics logs", "frequency": "monthly", "kviRollup": "KVI 1 (Mobility: clean, shared) · KVI 5 (Digital)"}],
  "stopConditions": [
    {"condition": "Meer dan 1 op de 20 zendingen heeft een menselijke omweg-bevestiging nodig.", "action": "Corridor-voorspelbaarheid verbeteren voordat de spoedroute automatisch mag."},
    {"condition": "Tijdswinst vergeleken met de weg valt weg.", "action": "Terug naar ontwerp: is de corridor nog de juiste?"}
  ],
  "goNoGo": [
    "Elke route blijft binnen toegestane corridors (100% van de replays)",
    "Afwijkende routes gaan nooit zonder menselijke bevestiging",
    "Tijdswinst per zending gemeten tegen de weg-logistiek"
  ]
}
```

`uam-09-geofencing-zones.baseline.json`: zelfde scaffold — publicOutcome "Beschermde plekken zijn op de drone-kaart zichtbaar voordat de eerste drone opsteekt.", disappearingStep "Het handmatig waarschuwen van drone-operators per zone verdwijnt; drones krijgen zones automatisch mee.", kpi's als in de recipe, stopConditions als fixture-sc-1/2, goNoGo: ["Geen gepubliceerde zone botst met een corridor", "Schendingen worden altijd gemeld aan de handhaver (mens beslist over optreden)", "Tijdelijke zones verlopen automatisch op einddatum"].

EDIC (in `edic-asset-map.json`, `updated` op de datum van uitvoering): twee entries met `assetClass: "hcs-city-recipe"`, owner "Digital Toolbox (EDIC)", relationshipOwners `["Serendipity"]`, readiness `"hybrid"`, riskLevel zoals recipe, acceptance `"GenAI-testbank + function-baseline; deterministische replay via hcs-recipe-run"`.

- [ ] **Step 5: Viz-data + menu-data + pagina genereren**

1. Maak `nldt/simulation/hcs/menu-data.json` met de rijen in **6 kolommen** `[code, titel-nl, mode-nl, kpi-nl, lens, recipeId]` — de **THK-rijen letterlijk uit de bestaande menu-demo** (THK-array, 5 kolommen) mét als zesde kolom het recipeId voor de drie PoC's (`thk-08-move-home`, `thk-02-having-a-baby`, `thk-24-build-renovate`) en `""` voor de overige 22; plus de twee uam-rijen: `["UAM-01","Ik wil medische logistiek per lucht","cargo","Tijdswinst vergeleken met de weg","W","uam-01-medical-logistics"]` en `["UAM-09","Ik wil geofencing en beveiligingszones","infrastructure · security","Beschermde zones vastgelegd","—","uam-09-geofencing-zones"]`. Structuur: `{"the-key": […25…], "urban-air-mobility": […2 van 9…], "3-30-300": [], "circular-neighborhoods": [], "15-minute-city": []}` — de lege dishes vullen Tasks 4–6 (alle 9/5/9/5 rijen, met recipeId voor de PoC's); Task 7 controleert het totaal (53).
2. `_viz_data("uam-01-medical-logistics")` in build_runs.py:

```python
UAM01_VIZ = {
    "kind": "map", "note": "Schema van de situatie — geen echte kaart: corridors (oranje/blauw) en beschermde zones (rood gestippeld).",
    "data": {"zones": [{"x": 420, "y": 90, "r": 55}, {"x": 180, "y": 220, "r": 40}],
             "routes": {"routine": [{"points": [[60, 260], [220, 180], [380, 110], [560, 60]]}],
                          "spoed": [{"points": [[60, 260], [200, 230], [330, 170], [560, 60]]}]},
             "labels": [{"x": 470, "y": 95, "text": "no-fly"}, {"x": 70, "y": 250, "text": "ziekenhuis"}, {"x": 520, "y": 50, "text": "lab"}]}}
```

   `_viz_data("uam-09-geofencing-zones")`: zelfde kaartvorm — zones voor `ziekenhuis` (één grote vaste zone) en `evenement` (tijdelijke zone die de corridor raakt):

```python
UAM09_VIZ = {
    "kind": "map", "note": "Schema: de nieuwe zone (blauw gevuld) tegen corridors (oranje) en bestaande zones (rood gestippeld).",
    "data": {"zones": [{"x": 150, "y": 100, "r": 45}],
             "routes": {"ziekenhuis": [{"points": [[320, 270], [320, 160], [320, 60]]}],
                          "evenement": [{"points": [[320, 270], [240, 190], [180, 130]]}]},
             "labels": [{"x": 130, "y": 105, "text": "no-fly"}, {"x": 300, "y": 50, "text": "corridor"}]}}
```

   (Viz-data is display-only; deterministisch en vast.)

3. Genereer en controleer:

```bash
nldt/.venv/bin/python nldt/simulation/hcs/build_runs.py --stamp 20261009T120000Z
```

Expected: 8 runs OK (nu nog NL-fase-1-rijen + 2 nieuwe city-runs ×2 scenario's = in totaal 12 run-bestanden zodra alle dishes er zijn; hier: 8 + 4 = 12? Nee — city-runs komen alleen in de pagina-payload; `--only-runs`-pad schrijft alleen life-event-runs. Dus: 8× OK run + 1× OK dish (uam).

4. Tests: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v` — alle PASS, behalve `test_dish_pages_exist_and_filled` die nog faalt op grn/cir/min (pas in Tasks 4–6 groen).

- [ ] **Step 6: Commit**

```bash
git add nldt/simulation/hcs/fixtures/city nldt/recipes/uam-01-medical-logistics.json nldt/recipes/uam-09-geofencing-zones.json nldt/recipes/baselines nldt/recipes/edic-asset-map.json nldt/simulation/hcs/menu-data.json nldt/simulation/hcs/build_runs.py nldt/simulation/hcs/dish-demo.template.html nldt/simulation/hcs-uam-demo.html nldt/tests/test_hcs.py
git commit -m "feat(nldt): UAM-dish — medische logistiek en geofencing als city-recipes, met gedeelde dish-template"
```

---

### Task 4: 3-30-300 — GRN-01 en GRN-03

**Files:** zelfde patroon als Task 3: `fixtures/city/grn-01-canopy-measure.json`, `grn-03-300m-gaps.json`; `recipes/grn-01-canopy-measure.json`, `grn-03-300m-gaps.json`; baselines; EDIC; `_viz_data` voor beide; `hcs-grn-demo.html`; tests.

**Inhoud (bron: xlsx — GRN-01: "Aerial/satellite imagery → AI canopy map → a gap heat-map by [wijk]", KPI "Canopy cover per neighbourhood" outcome % lens L W, remote sensing yearly; GRN-03: "Walkability analysis → find green deserts → green them first", KPI "Residents within 300 m of quality green" outcome % lens Z L, network analysis yearly; serviceTypes: `measure` resp. `plan`; riskLevel low/low):**

- GRN-01 scenarios: `wijk-noord` ({"nl": "Wijk Noord — onder de 30%", "en": "North district — below 30%"}), `wijk-zuid` ({"nl": "Wijk Zuid — ruim boven de 30%", "en": "South district — well above 30%"}). Steps: 1. `beelden` (G2, agent: "Nieuwe luchtfoto's worden opgehaald", sources remote sensing/PDOK), 2. `canopy` (G2, agent: "Het bladerdak wordt per stukje wijk gemeten" — dataUsed "de computer herkent bladerdak op de foto's" + "steekproef door een medewerker controleert een paar stukjes", perScenario wijk-noord: handover? nee — handover hoort bij G5), 3. `heat-map` (G5, agent: "De wijk krijgt een heat-map en een signaal waar het bladerdak groeit of krimpt", kpiEvents effect "per wijk wordt het percentage geregistreerd"). Stopconditions: "De computer meet staanders en schaduw als bladerdak bij meer dan 5% van de steekproef" → "meetmethode bijstellen"; "Een wijk daalt twee jaren achter elkaar" → "proactief signaal naar het gebiedsteam". learningState: signaal "Wijk Noord groeit langzaam maar gestaag", change "doel per wijk uitsplitsen in de recipe".
- GRN-03 scenarios: `binnen-norm` ({"nl": "Wijk waar bijna iedereen binnen 300 meter groen heeft", "en": "District where almost everyone has green within 300 m"}), `groeidesert` ({"nl": "Wijk met een groene woestijn", "en": "District with a green desert"}). Steps: 1. `loopafstand` (G2: "Van elk adres wordt de loopafstand tot goed groen berekend"), 2. `deserts` (G5: "Waar meer dan 10% van de bewoners verder dan 300 meter woont, komt een signaal"), 3. `prioriteer` (actor **mens**, G5 → handover default: reason "Over welke straat eerst vergroent, beslissen mensen met kennis van de wijk." to "het gebiedsteam met bewoners" — in scenario binnen-norm actor mens zonder handover? Nee: binnen-norm: stap 3 = handover null, actor mens (vast); groeidesert: handover met reden "Deze wijk staat bovenaan."). Stopconditions: "Loopafstand-meting slaat adressen zonder voetpad over" → "netwerkmethode bijstellen"; "Signaal komt te laat voor de begrotingsronde" → "frequentie verhogen naar halfjaarlijks". learningState: "Bewonerswaardering volgt de 300-meter-norm niet altijd" → "ook kwaliteit van groen meenemen".
- Recipes: zelfde scaffold als Task 3, `requiredProcesses: ["hcs-recipe-run"]`, serviceType `measure` resp. `plan`, KPI's letterlijk (dataSource "remote sensing"/"network analysis", frequency "yearly", kviRollup "KVI 7 (Biodiversity) · KVI 6 (Soil & Water) · KVI 2 (Cooling)" resp. idem + lens Z L).
- Baselines: publicOutcome GRN-01 "Elke wijk weet hoeveel bladerdak ze heeft en waar het groeit of verdwijnt — zonder dure veldinspectie." disappearingStep "De jaarlijkse handmatige boominventarisatie op straatniveau wordt een gerichte steekproef." GRN-03 publicOutcome "Gemeente en bewoners zien zwart-op-wit welke straten verder dan 300 meter van goed groen wonen." disappearingStep "De discussie over 'waar staat de wijk slecht scoort' verdwijnt in een gedeelde kaart." goNoGo zoals fixtures-stopconditions + steekproef-controle.
- `_viz_data` GRN-01: `"kind": "canopy"`, `data.cell = 70` en `data.cells` **gekeyst op scenario-id**: `wijk-noord` 12 cellen (4×3) met cover 18–27 (oranje), `wijk-zuid` 12 cellen met cover 32–48 (mint); note "Schema per wijkblok: mint = boven de 30%, oranje = eronder. Geen echte kaart."
- `_viz_data` GRN-03: `"kind": "canopy"`, `data.cell = 70`, `cells` gekeyst op `binnen-norm` (12 cellen 78–95) en `groeidesert` (12 cellen 45–62, waarvan twee < 50), note "Percentage bewoners binnen 300 meter groen per wijkblok."

- [ ] Steps: falende tests (parametrize grn-paar over `test_city_recipe_and_baseline_valid` + `test_city_fixtures_bilingual_and_runnable(rid="grn-01-canopy-measure")`) → implementeer → genereer (`--stamp 20261009T120000Z`, expected 1× OK dish grn) → commit `feat(nldt): 3-30-300-dish — bladerdakmeting en 300-meter-gaten als city-recipes` (bestanden analoog aan Task 3, geen template-wijziging tenzij een defect uit de template blijkt — rapporteer dat).

---

### Task 5: Circular neighborhoods — CIR-04 en CIR-01

**Files:** `fixtures/city/cir-04-shared-energy.json`, `cir-01-circular-condition.json`; recipes, baselines, EDIC, `_viz_data`, `hcs-cir-demo.html`; tests — analoog aan Task 3.

**Inhoud (bron: xlsx — CIR-04: "Resident-owned generation → shared heat & cold networks → ba[ttery]", KPI "Energy generated locally" outcome % lens Z W, grid/meter data monthly; CIR-01: "Land tender → circularity as a hard requirement → design", KPI "Circular / reused material in build" outcome % lens W, material ledger per project; serviceTypes: `share` resp. `system`; riskLevel medium/medium):**

- CIR-04 scenarios: `overproductie` ({"nl": "De buurt wekt meer stroom op dan ze verbruikt", "en": "The neighbourhood generates more power than it uses"}), `piek` ({"nl": "Koude piekavond: iedereen tegelijk", "en": "Cold peak evening: everyone at once"}). Steps: 1. `koppel` (G2: "Opwek en verbruik van alle buurtleden worden gekoppeld", sources "energiemeters (geanonimiseerd, met toestemming)", consent "gegeven"), 2. `verdeel` (G4: "De verdeling wordt voorgesteld: wie levert, wie verbruikt, wat naar de batterij gaat"), 3. `akkoord` (G3: "Iedereen ziet en bevestigt zijn eigen deel", perScenario piek: handover reason "Belangen lopen uiteen op de piekavond — de energiecoöperatie schikt." to "de energiecoöperatie (mens)"), 4. `leer` (G5: "De piek wordt geregistreerd als leermoment voor de batterij"). Stopconditions: "Meer dan 5% van de leden weigert deelname aan de verdeling" → "verdelingsregel herzien met de coöperatie"; "De batterij haalt twee winters de piek niet" → "capaciteitsbesluit terug naar de ledenvergadering". learningState: "Piekuren schuiven door zonnepanelen naar de avond" → "verdelingsregel per seizoen".
- CIR-01 scenarios: `tender` ({"nl": "Grond uitgegeven met circulariteit als harde eis", "en": "Land issued with circularity as a hard requirement"}). Steps: 1. `voorwaarde` (G2: "In de tender staat hoeveel hergebruikt materiaal het gebouw minimaal bevat"), 2. `bewijs` (G3: "Het materiaalpaspoort laat zien wat er in het gebouw zit", sources "materiaalregister (bv. Madaster)"), 3. `toets` (actor **mens**, G "—": "Bij oplevering beoordeelt een mens of de eis echt is gehaald"). Stopconditions: "Materiaalpaspoort ontbreekt bij oplevering" → "geen eindoplevering tot het bewijs er is"; "Circulariteit blijkt alleen op papier" → "inkoopvoorwaarden aanscherpen, leveranciersgesprek". learningState: "Hergebruik scoort beter bij stal- en gevelonderdelen" → "voorwaarde differentiëren per onderdeel".
- Recipes: serviceType `share` resp. `system`; KPI's letterlijk (dataSource "grid/meter data" monthly resp. "material ledger" per project; kviRollup "KVI 3 (Housing: circular) · KVI 8 (Circular economy) · KVI 4"; lens Z W resp. W); riskLevel medium.
- `_viz_data` CIR-04: `"kind": "series"`, `series.overproductie.points` = 6 maanden (labels J–J) values 45,52,60,68,62,55 met target 50; `series.piek` values 22,25,30,28,26,24 target 30; note "Lokale opwek als % van verbruik (schema) — oranje stippellijn = doel."
- `_viz_data` CIR-01: `"kind": "series"`, één reeks in beide scenario's: fases (Oprichting, Ontwerp, Bouw, Oplevering) values 20,35,55,68 target 50; note "Circulair/hergebruikt materiaal als % van het bouwmateriaal (schema)."

- [ ] Steps: falende tests (cir-paar) → implementeer → genereer (1× OK dish cir) → commit `feat(nldt): circular-dish — gedeelde energie en circulaire voorwaarde als city-recipes`.

---

### Task 6: 15-minute city — MIN-01 en MIN-04

**Files:** `fixtures/city/min-01-proximity-analysis.json`, `min-04-hub-network.json`; recipes, baselines, EDIC, `_viz_data`, `hcs-min-demo.html`; tests — analoog aan Task 3.

**Inhoud (bron: xlsx — MIN-01: "Isochrones → reachable amenities → find the service deserts", KPI "Residents within 15 min of daily needs" outcome % lens Z L, isochrone model yearly; MIN-04: "A ladder of hubs: NextPole microhub → neighbourhood hub → district", KPI "Hubs live per tier (micro/nbhd/district/city)" output # per tier, hub register quarterly; serviceTypes `measure` resp. `plan`; riskLevel low/low):**

- MIN-01 scenarios: `centrumwijk` ({"nl": "Centrumwijk: voorzieningen dichtbij", "en": "Centre district: amenities close by"}), `randwijk` ({"nl": "Randwijk: een servicedesert", "en": "Edge district: a service desert"}). Steps: 1. `voorzieningen` (G2: "Alle dagelijkse voorzieningen worden op de kaart gezet", sources "PDOK / gemeentelijke voorzieningenregister"), 2. `bereik` (G2: "Van elk adres wordt berekend wat binnen 15 minuten lopen of fietsen bereikbaar is"), 3. `signaal` (G5, perScenario randwijk: handover reason "Deze wijk scoort onder de norm — het gebiedsteam gaat met bewoners in gesprek." to "het gebiedteam van de wijk"). Stopconditions: "Bereikmodel negeert veilige routes (bv. oversteekplaatsen)" → "model met veiligheidslaag bijstellen"; "Signaal bereikt het gebiedsteam niet vóór de begroting" → "koppeling met de begrotingskalender". learningState: "Pakketpunten en zorglocaties tellen zwaarder mee dan gedacht" → "weegfactoren in de recipe publiceren".
- MIN-04 scenarios: `microhub` ({"nl": "Een nieuwe microhub bij de winkelstraat", "en": "A new micro-hub by the shopping street"}). Steps: 1. `behoefte` (G2: "Per niveau — micro, wijk, stadsdeel, stad — wordt de behoefte opgeteld"), 2. `voorstel` (G2: "Een voorstel: waar komt de hub, wat levert hij per niveau"), 3. `besluit` (actor **mens**, G5 → handover default: reason "Over de plek van de hub beslissen wijkbewoners en bestuur samen." to "de wijkavond en het college"). Stopconditions: "Een hub staat een halfjaar leeg" → "locatie heroverwegen, geen nieuwe hubs tot dan"; "Bewonersavond mist kwartieren van de wijk" → "bereik van de avond verbreden". learningState: "Microhubs werken het beste aan winkelas" → "plaatsingsregel in de recipe".
- Recipes: serviceType `measure` resp. `plan`; KPI's letterlijk (dataSource "isochrone model" yearly resp. "hub register" quarterly; kviRollup "KVI 1 (Mobility) · KVI 3 (Housing: mixed-use, density)"; lens Z L resp. "—"); riskLevel low.
- `_viz_data` MIN-01: `"kind": "tiers"` — `tiers` = [{name: "winkels", r: 90, live: 14, plan: 15}, {name: "zorg", r: 130, live: 9, plan: 10}, {name: "onderwijs", r: 170, live: 6, plan: 8}, {name: "groen", r: 210, live: 4, plan: 6}] (zelfde voor beide scenario's; het verschil zit in de runs); note "Bereikte voorzieningen per ring (schema) — de randwijk haalt de buitenringen niet."
- `_viz_data` MIN-04: `"kind": "tiers"` — tiers [{name: "micro", r: 80, live: 11, plan: 12}, {name: "wijk", r: 125, live: 4, plan: 5}, {name: "stadsdeel", r: 165, live: 2, plan: 3}, {name: "stad", r: 205, live: 1, plan: 1}]; note "De hubladder: live versus gepland per niveau."

- [ ] Steps: falende tests (min-paar + **de volledige `test_dish_pages_exist_and_filled` over alle vier dishes** — zelfde assertions als `test_uam_page_generated` maar loop over uam/grn/cir/min) → implementeer → genereer (1× OK dish min; vier pagina's test volledig groen) → commit `feat(nldt): 15-minute-city-dish — nabijheidsanalyse en hubladder als city-recipes`.

---

### Task 7: Menu volledig, index, README/04, mappingdoc city-completion

**Files:**
- Modify: `nldt/simulation/hcs-menu-demo.html` (vier dish-stubs → volledige kaarten)
- Modify: `nldt/simulation/index.html` (HCS-sectie: vier dish-demo-links)
- Modify: `nldt/simulation/README.md`, `nldt/04-recipes-and-processes.md` (rijen; recipe-count 24 → 32)
- Modify: `docs/HCS_RECIPES_AGENTIC_STATE.md` (city-grens-tabellen; B3/B4/B14-notitie)
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- `menu-data.json` (Task 3, gevuld in 3–6) wordt de enige bron voor de menu-kaarten: de menu-demo laadt geen extern bestand (file://) — de 28 nieuwe rijen worden **letterlijk uit menu-data.json overgenomen** in de THK-array-stijl van de menu-demo (4 arrays of één array met dish-veld), en een consistenzetest vergelijkt menu-demo tegen menu-data.json.

- [ ] **Step 1: Falende tests**

```python
def test_menu_demo_lists_all_53():
    text = MENU_HTML.read_text()
    data = json.loads((HCS_ROOT / "menu-data.json").read_text())
    total = sum(len(v) for v in data.values())
    assert total == 53
    for dish, rows in data.items():
        for row in rows:
            assert row[0] in text, f"{row[0]} ontbreekt in menu-demo"
    assert text.count("poc") >= 8  # elf PoC-kaarten: 3 THK + 8 city (marker-teller)


def test_index_links_all_dish_demos():
    text = INDEX_HTML.read_text()
    for d in ("uam", "grn", "cir", "min"):
        assert f'href="hcs-{d}-demo.html"' in text


def test_mapping_doc_city_tables():
    text = MAPPING_DOC.read_text()
    for marker in ("UAM-01", "GRN-03", "CIR-04", "MIN-04", "hcs-recipe-run"):
        assert marker in text
```

(Opmerking: de exacte poc-teller in de test afstemmen op de feitelijke markering in de menu-demo; bedoeling: alle 11 PoC-kaarten gemarkeerd.)

- [ ] **Step 2: Draai — moet falen**

- [ ] **Step 3: Implementeer**

1. **Menu-demo:** vervang de vier `<div class="dish next">`-stubs door volledige dish-blokken met `.cards`-rasters gevuld uit menu-data.json (JS: zelfde render-patroon als de THK-array, nu per dish; PoC-kaarten linken naar `hcs-<dish>-demo.html` in plaats van de key-demo). Titel van de sectie: "De vijf dishes — alle 53 recipes; elf als PoC uitgewerkt". De `h2` van de stappen/rollup/cyclus-secties ongewijzigd.
2. **Index:** vier kaarten toevoegen aan de HCS-sectie (UAM · 3-30-300 · Circular · 15-minute city, elke met `.t`/`.d` conform bestaande markup).
3. **README:** HCS-subsectie uitbreiden met de vier dish-demo's en de herbouw-instructie (stempel ongewijzigd). **04-doc:** catalogue-rij uitbreiden: `| thk-*/uam-*/grn-*/cir-*/min-* (11 HCS-recipes) | medium–high | hcs-life-event-run / hcs-recipe-run |`; "(24 recipes)" → "(32 recipes)"; HCS-paragraaf: één zin over city-recipes.
4. **Mappingdoc:** stadsgrens-tabellen per dish toevoegen (uit de fixtures' humanMeasure/stopconditions, zelfde tabelvorm als §2), `hcs-recipe-run` in de landingsplaats-kolom, en een notitie over B3/B4/B14 (readyheidskaart, prioriteitsvragen, 18-maanden-leerperiode: "deze blocks raken de HCS-recipes via de KPI-baseline (B4/B9) en de go/no-go (B14); een NL-readyheidskaart is fase 3-werk").
5. **menu-data.json consistentietest** (uit Step 1) + dish-pages-test nu volledig groen.

- [ ] **Step 4: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/hcs-menu-demo.html nldt/simulation/hcs/menu-data.json nldt/simulation/index.html nldt/simulation/README.md nldt/04-recipes-and-processes.md docs/HCS_RECIPES_AGENTIC_STATE.md nldt/tests/test_hcs.py
git commit -m "docs(nldt): menu volledig (53 recipes), dish-links, README/04-rijen en city-grens-tabellen"
```

---

### Task 8: Volledige suite, visuele gate en afronding

**Files:** geen nieuwe; alleen verificatie.

- [ ] **Step 1: Volledige suite** — `nldt/.venv/bin/python -m pytest nldt/tests -q`; alle PASS.
- [ ] **Step 2: CLI-check** — `cd nldt && NLDT_OFFLINE=1 .venv/bin/python -m services.cli run-recipe grn-01-canopy-measure --input scenario=wijk-noord --input mode=replay` → geldige run met `scenario == "wijk-noord"`.
- [ ] **Step 3: Visuele gate** — render `hcs-uam-demo.html`, `hcs-grn-demo.html`, `hcs-cir-demo.html`, `hcs-min-demo.html`, `hcs-menu-demo.html` (volle hoogte), `index.html` naar PNG (Brave headless, zelfde methode als fase 1) en laat de `presentations:visual-judge` beoordelen: palet, klare taal (geen systeemjargon in de hoofdtoon), SVG-leesbaarheid (legenda/notities), geen overlap; menu toont 53 kaarten waarvan 11 PoC-gemarkeerd. Bij afkeur herstellen en her-renderen.
- [ ] **Step 4: Slot-commit** indien herbouw-artefacten open staan; `git status` anders leeg.

---

## Buiten dit plan

EN-tweelingen van de dish-demo's (fixture-tweetaligheid maakt dit goedkoop) · echte Leaflet/PDOK-kaarten · bestuurdersdemo-scène · echte LLM-intake — fase 3-opties volgens spec §6.

---

## Executiestatus (10 oktober 2026)

Fase 2 is uitgevoerd en afgerond: 8 commits `375757b..11b9fba` op main, suite 457 groen, visuele gate 6/6 (controller-inspectie na herhaalde subagent-timeouts). Gedocumenteerde deviaties op het plan: (1) `outcomeLens` accepteert lens-arrays (xlsx kent "L W" e.d.) — additief in serviceKpi + baselineKpi; (2) `MENU_DISH`-brug tussen DISH_DEFS- en schema-dish-keys; (3) `build_dish_pages` vlakt de viz-data af tot één niveau (`{kind, note, data}`) en geeft het scenario-id (niet de index) aan de renderers — beide gevonden door de visuele gate; (4) menu-rendering vanuit ingebed `MENU`-literal met `cards-the-key`-container-id; (5) hubladder-viewport 440px. Deferred minors: lang-title-unificatie processen, vizSeries één-punt-NaN, DISH_ID kort vs schema-id. Fase 3-opties (EN-dish-demo's, echte kaarten, bestuurdersdemo-scène, LLM-intake) staan in de spec.
