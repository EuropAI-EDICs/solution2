# Breda vijf-waarden-tab in simulation.html — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voeg PoC-4 (Breda five-value scan) toe als tab 4 in `simulation/simulation.html`, met Laya-achtige karakteristieken: offline DATA-embed, timeline-replay, unlock-daarna-chat met golden Q&A.

**Architecture:** `build_simulation.py` pin’t canonieke run `poc-breda/runs/20260913T192628Z-breda-scan`, compacteert `value-scan` + display-geo + validatie, en embed’t `simulation/breda_qa.json`. `template.html` krijgt tab 4 (SVG-choropleth zonder CDN, waarden-switcher, 6-staps timeline, lokale unlock + chat). `verify_static.mjs` drijft timeline + probe aan.

**Tech Stack:** Python 3 + shapely (zelfde als bestaande simulation-build; bv. miniconda of project-venv met shapely), single-file HTML/JS, Node voor `verify_static.mjs`. Spec: `docs/superpowers/specs/2026-10-25-simulation-breda-five-value-tab-design.md`.

## Global Constraints

- Single-file / `file://`: geen CDN, geen Leaflet, geen netwerk in de pagina.
- Geen live `poc-breda/run.py` of in-browser `breda.qa`.
- Unlock lokaal aan tab 4 (`bredaUnlocked`); niet koppelen aan Laya-datasets.
- Canonieke run-pin: `20260913T192628Z-breda-scan` (volledige artefacten + `run_summary`).
- Golden Q&A: ~8–12 entries in `simulation/breda_qa.json`; build faalt als `buurtnaam` niet in scan zit.
- Kaart: SVG + bestaande projectie-stijl (eigen bbox voor Breda), niet Utrecht-`P1.aoi`.
- Python-build: env mét shapely (zoals huidige `build_simulation.py`).
- Commits: `feat(simulation): …` / `test(simulation): …` / `docs(simulation): …`.

---

## File map

| Path | Responsibility |
|---|---|
| `simulation/breda_qa.json` | gecureerde golden Q&A + probe-labels |
| `simulation/build_simulation.py` | `POC4_RUN`, `build_breda()`, DATA.poc4 |
| `simulation/template.html` | tab 4 UI, timeline, map, chat, `?tab=4` |
| `simulation/simulation.html` | gegenereerde output (niet handmatig editen) |
| `simulation/verify_static.mjs` | smoke: timeline → unlock → chat-probe |
| `simulation/README.md` | tab 4 + rebuild-instructie |
| `simulation/test_build_breda.py` | unit tests voor builder-helpers / QA-gate |

---

### Task 1: Golden Q&A + build-gate tests

**Files:**
- Create: `simulation/breda_qa.json`
- Create: `simulation/test_build_breda.py`
- Modify: `simulation/build_simulation.py` (alleen helpers + later gebruikt door Task 2)

**Interfaces:**
- Consumes: buurtnamen uit `poc-breda/runs/20260913T192628Z-breda-scan/value-scan.json`; Q&A-teksten uit `poc-breda/runs/20260913T152919Z-breda-scan/qa/*/answer.json` (+ 2–3 handmatige)
- Produces: `breda_qa.json` schema per item: `{id, question, answer, probe?, buurtnaam?, waarde?, mode?}`; helper `validate_breda_qa(qa: list[dict], buurtnamen: set[str]) -> None` (raises `ValueError`)

- [ ] **Step 1: Schrijf falende test voor QA-gate**

```python
# simulation/test_build_breda.py
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"

class TestBredaQaGate(unittest.TestCase):
    def test_unknown_buurt_raises(self):
        from build_simulation import validate_breda_qa
        with self.assertRaises(ValueError):
            validate_breda_qa(
                [{"id": "x", "question": "q", "answer": "a", "buurtnaam": "Nergenshuizen"}],
                {"Belcrum", "Ginneken"},
            )

    def test_known_buurt_ok(self):
        from build_simulation import validate_breda_qa
        validate_breda_qa(
            [{"id": "x", "question": "q", "answer": "a", "buurtnaam": "Belcrum"}],
            {"Belcrum", "Ginneken"},
        )

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect fail (helper missing)**

Run: `cd simulation && python3 -m unittest test_build_breda.py -v`  
Expected: `ImportError` of `validate_breda_qa` / FAIL

- [ ] **Step 3: Implementeer `validate_breda_qa` + minimale stub in build_simulation.py**

```python
def validate_breda_qa(qa: list[dict], buurtnamen: set[str]) -> None:
    for i, row in enumerate(qa):
        for key in ("id", "question", "answer"):
            if not row.get(key):
                raise ValueError(f"breda_qa[{i}] missing {key}")
        naam = row.get("buurtnaam")
        if naam and naam not in buurtnamen:
            raise ValueError(f"breda_qa[{i}] buurtnaam {naam!r} not in scan")
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd simulation && python3 -m unittest test_build_breda.py -v`  
Expected: PASS

- [ ] **Step 5: Schrijf `simulation/breda_qa.json` (≥8 items)**

Harvest/adapt from:
- `poc-breda/runs/20260913T152919Z-breda-scan/qa/welke-buurten-scoren-het-hoogst-op-democratische-waarde/answer.json`
- `…/waarom-scoort-belcrum-laag-op-ruimtelijke-waarde/`
- `…/hoe-scoort-ginneken-op-alle-waarden/`
- `…/top-3-buurten-onbenut-dakpotentieel/`
- `…/welke-buurten-hebben-de-meeste-hitte-aandacht/`
- `…/wat-is-de-mediaan-op-sociale-waarde/`

Plus handmatig:
- probe over autonome waarde / soevereiniteitsmanifest (geen buurt)
- één Engelse variant van Belcrum spatial (uit `20260913T192628Z-breda-scan/qa/answer.json`) als extra match

Elke entry: `id`, `question`, `answer` (tekst uit answer.json `answer`-veld), `probe` (korte chip-label ≤40 chars), optioneel `buurtnaam`, `waarde` (`democratic|spatial|economic|social|autonomous|alle`), `mode`.

- [ ] **Step 6: Commit**

```bash
git add simulation/breda_qa.json simulation/test_build_breda.py simulation/build_simulation.py
git commit -m "$(cat <<'EOF'
feat(simulation): breda golden Q&A + build-gate helper

EOF
)"
```

---

### Task 2: `build_breda()` + DATA.poc4

**Files:**
- Modify: `simulation/build_simulation.py`
- Modify: `simulation/test_build_breda.py`

**Interfaces:**
- Consumes: `POC4_RUN = ROOT / "poc-breda/runs/20260913T192628Z-breda-scan"`; `CORPUS`-stijl load; `display_rings` / TOL; `simulation/breda_qa.json`; `validate_breda_qa`
- Produces: `build_breda() -> dict` met keys:

```python
{
  "runId": str,
  "verdict": str,
  "nBuurten": int,
  "scan": dict,          # subset: id/label/generatedAt indien aanwezig
  "values": dict,        # inclusief autonomous.manifest (ingekort evidence ok)
  "sources": list,       # id, title/url compact
  "buurten": [           # 56
    {"buurtcode", "buurtnaam", "wijkcode", "aantalInwoners",
     "scores": {"democratic": float, "spatial": float, "economic": float, "social": float},
     "missing": list}
  ],
  "rollup": dict,        # per waarde top/bottom
  "geo": {buurtcode: [[lon,lat], ...] rings},  # display_rings output
  "validation": {"verdict": str, "levels": {name: status}},
  "qa": list,            # from breda_qa.json after validate
  "stages": ["intake","fetch","indicators","validate","report","unlock"],
}
```

- [ ] **Step 1: Falende test op payload-vorm**

```python
class TestBuildBreda(unittest.TestCase):
    def test_build_breda_shape(self):
        from build_simulation import build_breda
        p = build_breda()
        self.assertEqual(p["runId"], "20260913T192628Z-breda-scan")
        self.assertEqual(p["nBuurten"], 56)
        self.assertEqual(len(p["buurten"]), 56)
        self.assertIn("BU07580100", p["geo"])  # Belcrum code — verify from run
        self.assertGreaterEqual(len(p["qa"]), 8)
        self.assertEqual(len(p["stages"]), 6)
        b0 = p["buurten"][0]
        for k in ("democratic", "spatial", "economic", "social"):
            self.assertIn(k, b0["scores"])
```

(Pas `BU07580100` aan als de run een andere code voor Belcrum heeft — lees uit value-scan.)

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd simulation && python3 -m unittest test_build_breda.TestBuildBreda -v`  
Expected: FAIL / ImportError `build_breda`

- [ ] **Step 3: Implementeer `build_breda`**

```python
POC4_RUN = ROOT / "poc-breda" / "runs" / "20260913T192628Z-breda-scan"
BREDA_QA = Path(__file__).resolve().parent / "breda_qa.json"

def build_breda() -> dict:
    run = POC4_RUN
    summary = load(run / "run_summary.json")
    vs = load(run / "value-scan.json")
    val = load(run / "validation.json")
    geo_fc = load(run / "geo-buurten.wgs84.geojson")
    qa = load(BREDA_QA)
    if not isinstance(qa, list):
        qa = qa.get("items") or qa.get("qa") or []

    buurten = []
    for b in vs["buurten"]:
        scores = b.get("scores") or {}
        buurten.append({
            "buurtcode": b["buurtcode"],
            "buurtnaam": b["buurtnaam"],
            "wijkcode": b.get("wijkcode"),
            "aantalInwoners": b.get("aantalInwoners"),
            "scores": {k: float((scores.get(k) or {}).get("score") or 0)
                       for k in ("democratic", "spatial", "economic", "social")},
            "missing": b.get("missing") or [],
        })
    namen = {b["buurtnaam"] for b in buurten}
    validate_breda_qa(qa, namen)

    geo = {}
    for f in geo_fc.get("features") or []:
        props = f.get("properties") or {}
        code = props.get("code") or props.get("buurtcode")
        if not code or not f.get("geometry"):
            continue
        geo[code] = display_rings(shape(f["geometry"]))

    levels = {}
    for name, info in (val.get("validationLevels") or {}).items():
        if isinstance(info, dict):
            levels[name] = info.get("status") or info.get("verdict") or "—"
        else:
            levels[name] = str(info)

    return {
        "runId": summary["runId"],
        "verdict": summary.get("verdict"),
        "nBuurten": summary.get("nBuurten", len(buurten)),
        "scan": {k: vs.get("scan", {}).get(k) for k in ("id", "label", "generatedAt")
                 if isinstance(vs.get("scan"), dict)},
        "values": vs.get("values") or {},
        "sources": [
            {"id": s.get("id"), "title": s.get("title") or s.get("name"), "url": s.get("url")}
            for s in (vs.get("sources") or [])
        ],
        "buurten": buurten,
        "rollup": vs.get("rollup") or {},
        "geo": geo,
        "validation": {"verdict": val.get("verdict"), "levels": levels},
        "qa": qa,
        "stages": ["intake", "fetch", "indicators", "validate", "report", "unlock"],
    }
```

Wire in `main`:

```python
data = {"poc1": build_poc1(), "poc2": build_poc2(), "poc4": build_breda()}
```

- [ ] **Step 4: Run tests + dry build**

Run:
```bash
cd simulation && python3 -m unittest test_build_breda.py -v
# shapely-python, e.g.:
/opt/homebrew/Caskroom/miniconda/base/bin/python3 simulation/build_simulation.py
```
Expected: tests PASS; build writes `simulation.html` mentioning `poc4` / runId.

- [ ] **Step 5: Commit**

```bash
git add simulation/build_simulation.py simulation/test_build_breda.py
git commit -m "$(cat <<'EOF'
feat(simulation): embed PoC-4 Breda value-scan payload

EOF
)"
```

---

### Task 3: Tab 4 shell — markup, tabs, deep-link

**Files:**
- Modify: `simulation/template.html` (tabs, `#view4`, CSS grid, `switchTab`, URL `?tab=4` / `?waarde=`)

**Interfaces:**
- Consumes: `DATA.poc4` (bestaat na Task 2 rebuild)
- Produces: DOM ids: `view4`, `tab4`, `map4`, `waardeTabs`, `b4-detail`, `rail4`, `log4`, `chat4`, `chatin4`, `probes4`, `fr-note`-stijl meta; JS: `const P4 = DATA.poc4`, `bredaUnlocked=false`, `curWaarde='spatial'`

- [ ] **Step 1: Voeg tab-knop + view-skelet toe**

Naast bestaande tabs:

```html
<div class="tab" id="tab4" onclick="switchTab(4)">Breda · vijf-waarden</div>
```

Nieuwe `<section class="view" id="view4">` met:
- links/midden: SVG `#map4` viewBox `0 0 980 620`, waarden-switcher knoppen, detailpane `#b4-detail`, rollup `#b4-rollup`, autonomous pane `#b4-auto` (hidden by default)
- rechts: rail stages `#rail4`, sources chips, validation chips, chat panel (locked overlay)

- [ ] **Step 2: Extend `switchTab` + boot URL**

```javascript
function switchTab(n){
  if(n===active) return;
  sim().pause();
  active=n;
  // bestaande show/hide views 1..3
  ["view1","view2","view3","view4"].forEach((id,i)=>$(id).classList.toggle("active", i+1===n));
  // tab active classes incl tab4
  if(n===4) buildStatic4();
}
// on load:
const params = new URLSearchParams(location.search);
if(params.get("tab")==="4") switchTab(4);
const w0 = params.get("waarde");
if(w0 && ["democratic","spatial","economic","social","autonomous"].includes(w0)) curWaarde=w0;
```

- [ ] **Step 3: Rebuild + open smoke (handmatig)**

Run: rebuild `build_simulation.py`; open `simulation.html?tab=4` — tab zichtbaar, geen JS-errors in console.

- [ ] **Step 4: Commit**

```bash
git add simulation/template.html simulation/simulation.html
git commit -m "$(cat <<'EOF'
feat(simulation): tab 4 shell for Breda five-value scan

EOF
)"
```

---

### Task 4: Choropleth-kaart + waarden-switcher + timeline/unlock

**Files:**
- Modify: `simulation/template.html`
- Modify: `simulation/simulation.html` (via rebuild)

**Interfaces:**
- Consumes: `P4.geo`, `P4.buurten`, `P4.rollup`, `P4.values`, `P4.validation`, `P4.stages`
- Produces: `buildMap4()`, `setWaarde(w)`, `makeSim4()` / `sim4` with 6 steps; `bredaUnlock()`; expose on `__ds`: `bredaOn`, `sim4`, `setWaarde`, `bredaChatSend`

- [ ] **Step 1: SVG-projectie voor Breda bbox**

Eigen `bbox4` over alle rings in `P4.geo` (niet `P1.aoi`). Hergebruik `ringPath`-formule met `px4`/`py4`.

- [ ] **Step 2: Choropleth**

```javascript
function scoreColor(t){ // t in 0..1
  // blue→amber→green ramp, YAGNI: 3 stops
  const c=[[30,64,175],[245,158,11],[16,185,129]];
  // linear interpolate…
}
function buildMap4(){
  const svg=$("map4"); svg.innerHTML="";
  for(const b of P4.buurten){
    const rings=P4.geo[b.buurtcode]; if(!rings) continue;
    const path=el("path",{d:ringsPath4(rings), "data-code":b.buurtcode, class:"buurt"},svg);
    path.addEventListener("mouseenter",()=>showBuurt(b));
    path.addEventListener("click",()=>showBuurt(b));
  }
  paintWaarde(curWaarde);
}
function paintWaarde(w){
  curWaarde=w;
  if(w==="autonomous"){
    // grey fill all; show #b4-auto manifest; hide choropleth legend
    return;
  }
  // fill each path by b.scores[w]/100
}
```

- [ ] **Step 3: Timeline `makeSim4`**

Steps 0–5 zoals spec (§2): intake → fetch (source chips on) → indicators (counters) → validate (level chips) → report (`paintWaarde('spatial')` + rollup) → unlock (`bredaUnlock()`).

```javascript
function bredaUnlock(){
  bredaUnlocked=true;
  $("chat4").classList.remove("locked");
  bredaWelcome();
}
```

Wire play/pause/reset analog to sim1; register `sim4` in `sim()` dispatcher when `active===4`.

- [ ] **Step 4: Rebuild + handmatige check**

Timeline speelt af; na unlock is chat niet locked; `?waarde=economic` kleurt economisch.

- [ ] **Step 5: Commit**

```bash
git add simulation/template.html simulation/simulation.html
git commit -m "$(cat <<'EOF'
feat(simulation): Breda choropleth, timeline and unlock

EOF
)"
```

---

### Task 5: Golden chat (Laya-ritme)

**Files:**
- Modify: `simulation/template.html`

**Interfaces:**
- Consumes: `P4.qa[]`
- Produces: `bredaMatch(q) -> row|null`, `bredaChatSend()`, probe chips from rows with `probe`; abstain copy vast

- [ ] **Step 1: Matcher**

```javascript
function normQ(s){ return String(s||"").toLowerCase().normalize("NFKD")
  .replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9\s]/g," ").replace(/\s+/g," ").trim(); }
function bredaMatch(q){
  const n=normQ(q); if(!n) return null;
  let best=null, bestScore=0;
  for(const row of P4.qa){
    const nn=normQ(row.question);
    if(n===nn) return row;
    if(nn.includes(n) || n.includes(nn)){ const sc=Math.min(n.length,nn.length)/Math.max(n.length,nn.length);
      if(sc>bestScore){ best=row; bestScore=sc; } }
  }
  return bestScore>=0.45 ? best : null;
}
```

- [ ] **Step 2: Send + probes + lock guard**

```javascript
function bredaChatSend(){
  if(!bredaUnlocked){ bredaMsg("Chat locked — speel eerst de scan-timeline uit.","warn"); return; }
  const v=$("chatin4").value.trim(); if(!v) return;
  $("chatin4").value="";
  bredaMsg(v,"user");
  const hit=bredaMatch(v);
  if(!hit){ bredaMsg("Geen grounded antwoord in de scan — herformuleer of kies een probe. (System-2: ask_scan buiten deze pagina.)","warn"); return; }
  bredaMsg(hit.answer,"bot");
  if(hit.waarde && hit.waarde!=="alle") setWaarde(hit.waarde==="autonomous"?"autonomous":hit.waarde);
  if(hit.buurtnaam){ const b=P4.buurten.find(x=>x.buurtnaam===hit.buurtnaam); if(b) showBuurt(b); }
}
```

Welkomst + chips na unlock (max 6 probes).

- [ ] **Step 3: Expose op `__ds`**

```javascript
// alongside existing __ds fields:
bredaOn: ()=>bredaUnlocked,
setWaarde, bredaChatSend, bredaMatch,
get sim4(){ return sim4; },
```

- [ ] **Step 4: Rebuild + handmatige probe**

Na timeline: klik probe Belcrum → antwoord + spatial kleuren.

- [ ] **Step 5: Commit**

```bash
git add simulation/template.html simulation/simulation.html
git commit -m "$(cat <<'EOF'
feat(simulation): Breda golden Q&A chat after unlock

EOF
)"
```

---

### Task 6: verify_static + README + acceptatie

**Files:**
- Modify: `simulation/verify_static.mjs`
- Modify: `simulation/README.md`
- Modify: `simulation/simulation.html` (rebuild)

**Interfaces:**
- Consumes: `__ds.sim4`, `__ds.bredaOn`, `__ds.bredaChatSend`, `__ds.setWaarde`
- Produces: smoke OK-regel die `poc4` noemt

- [ ] **Step 1: Extend verify**

Na Laya-checks:

```javascript
  ds.switchTab(4);
  const s4 = ds.sim4;
  if (!s4 || s4.steps.length < 6) throw new Error("sim4 missing or too few steps");
  s4.jumpToStage(5); drain();
  if (!ds.bredaOn()) throw new Error("breda chat not unlocked after timeline");
  document.getElementById("chatin4").value = "Belcrum"; // or exact probe question substring
  ds.bredaChatSend();
  document.getElementById("chatin4").value = "xyzzy onbekend";
  ds.bredaChatSend();
  ds.setWaarde("autonomous");
  ds.setWaarde("democratic");
  s4.reset(); drain();
  if (ds.bredaOn()) throw new Error("breda chat not re-locked after reset");
```

Pas `switchTab` exposure aan: als die nog niet op `__ds` staat, voeg `switchTab` toe.

Update OK-logregel.

- [ ] **Step 2: Run verify**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python3 simulation/build_simulation.py
node simulation/verify_static.mjs
```
Expected: `OK — … poc4 …`

- [ ] **Step 3: README-paragraaf**

Kort blok: tab 4 Breda, rebuild-commando, `?tab=4`, golden Q&A unlock, pin run-id.

- [ ] **Step 4: Commit**

```bash
git add simulation/verify_static.mjs simulation/README.md simulation/template.html simulation/simulation.html
git commit -m "$(cat <<'EOF'
test(simulation): verify Breda tab timeline and chat unlock

EOF
)"
```

---

## Spec coverage (self-review)

| Spec | Task |
|---|---|
| Tab 4 native, niet Laya-switcher | 3 |
| Offline value-scan + simplified geo | 2 |
| Waarden-switcher + autonomous manifest | 4 |
| Timeline 0–5 + lokale unlock | 4 |
| Golden Q&A + abstain + probes | 1, 5 |
| `?tab=4` / `?waarde=` | 3 |
| verify + file:// / no CDN | 4, 6 |
| Build-gate buurtnamen | 1–2 |

## Placeholder scan

Geen TBD; run-id vastgepind; map = SVG; Q&A-bestand vastgelegd.
