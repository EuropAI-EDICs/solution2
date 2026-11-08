# Tekst- en RegelRecht-popups in de kennisgraaf — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Graaf-popups met echte wettekst en leesbare RegelRecht-omzetting: artikel-popups krijgen tekstexcerpt + executie-render (of onthouding), regeltekst-popups de echte lidtekst.

**Architecture:** Build-time extractie en render (kg1-idioom): `build_kg7()` breidt uit met een lidtekst-map (documentstructuur → wId), artikeltekst + voorgemaakte executie-HTML (instrument-YAML); overzicht-tooltips worden build-side samengesteld, subgraph-tooltips lezen dezelfde data-velden. Verify krijgt tekst-gouden; hubs herbouwd in de slot-taak.

**Tech Stack:** Python 3.13 (`nldt/.venv`, pyyaml beschikbaar), vanilla JS, Node voor verify.

**Spec:** `docs/superpowers/specs/2026-11-08-dso-kb-graaf-tekstpopups-design.md`.

## Global Constraints

- Caps: artikeltekst 500, lidtekst 350, inputs 2 (+teller), actions 4 (+teller); truncatie altijd met "…"; alle waarden `_esc`d vóór HTML-samenvoeging.
- Geen tekst ín knopen — alléén tooltips; jr/act/loc/gio-tooltips ongewijzigd; de vier bestaande stappen ongewijzigd (verify blijft `sim7 5 stappen`).
- Bronnen: `documentstructuur.json` (blad-`identificatie` ↔ wId, 1407/1407), instrument-YAML `full_export/out/<id>-<cvdr-lower>.yaml` (velden `number/text/machine_readable`), bestaande rrStatus. Ontbrekend YAML → harde `sys.exit`; ontbrekend lid/tekst → terugval op huidige tooltip (nooit breken).
- Executie-render: `produces.legal_character`, inputs (naam+beschrijving cap 90), outputs, actions recursief met opera-symboolmap `{"AND":"EN","EQUALS":"=","LESS_THAN_OR_EQUAL":"≤","IF":"ALS"}`; niet-geformaliseerd → `<i>niet geformaliseerd — status: <status></i>`.
- Gouden fragmenten: art 1.8-tekst bevat **"meet- en rekenbepalingen"**; rr bevat `toegestaan_art_1_8` én (`limiet_m` of `in_werkingsgebied`); utrecht 10.4-tekst is `[Vervallen per 01‑03‑2024]`-achtig kort en rr = niet-geformaliseerd/unmatched; eerste 1.8-wId heeft lids-tekst ≥ 40 tekens.
- `--gent-only` blijft datavrij; hub-groei ≤ ~1,2 MB; commit alléén taakbestanden; branch `feat/dso-kb-tekstpopups` (controller maakt die vóór Taak 1).

---

### Task 1: build — lidtekst, artikeltekst, executie-render

**Files:**
- Modify: `simulation/build_simulation.py`

**Interfaces:**
- Produces: kg-payload per instrument uitgebreid met `artikelen[nr]["tekst"]` (str, cap 500), `artikelen[nr]["rr"]` (voorgemaakt HTML), topveld `"lids": {wId: {"lid": str, "tekst": str}}` (alléén wIds uit payload-`rts`); overzicht-artikel/rt-tooltips samengesteld uit dezelfde velden. Taak 2 leest dit 1:1.

- [ ] **Step 1: imports + constanten + helpers.** Bovenaan bij de imports: `import html` en (bestaand yaml-gebruik lokaliseren; als `yaml` nog niet geïmporteerd is in dit bestand) `import yaml`. Na de `DSO_INSTRUMENTEN`-constante:

```python
FULL_EXPORT = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export" / "out"
TEKST_CAP, LID_CAP, RR_INPUT_CAP, RR_ACTION_CAP, RR_DESC_CAP = 500, 350, 2, 4, 90

_AL_RE = re.compile(r"<Al>(.*?)</Al>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_NUM_RE = re.compile(r"<Nummer>(.*?)</Nummer>")
_RR_OPSYM = {"AND": "EN", "EQUALS": "=", "LESS_THAN_OR_EQUAL": "≤", "IF": "ALS"}


def _cap(tekst: str, n: int) -> str:
    tekst = (tekst or "").strip()
    return tekst if len(tekst) <= n else tekst[:n].rstrip() + "…"


def _xml_tekst(xml: str | None) -> str:
    if not xml:
        return ""
    delen = []
    for al in _AL_RE.findall(xml):
        stuk = html.unescape(_TAG_RE.sub("", al)).strip()
        if stuk:
            delen.append(stuk)
    return " ".join(delen)


def _rr_operand(v) -> str:
    if isinstance(v, str) and v.startswith("$"):
        return v[1:]
    if isinstance(v, dict) and ("operation" in v or "conditions" in v):
        return _rr_expr(v)
    return json.dumps(v, ensure_ascii=False)


def _rr_expr(knoop) -> str:
    op = _RR_OPSYM.get(str(knoop.get("operation", "?")), str(knoop.get("operation", "?")))
    if "conditions" in knoop:
        return f"{op}(" + " ∧ ".join(_rr_expr(c) for c in knoop["conditions"]) + ")"
    return f"{_rr_operand(knoop.get('subject', '?'))} {op} {_rr_operand(knoop.get('value', '?'))}"


def _rr_html(mr: dict | None, status: str) -> str:
    ex = (mr or {}).get("execution")
    if not ex:
        return f"<i>niet geformaliseerd — status: {_esc(status)}</i>"
    regels = []
    prod = (ex.get("produces") or {}).get("legal_character")
    if prod:
        regels.append(f"karakter: {_esc(str(prod))}")
    for inp in (ex.get("input") or [])[:RR_INPUT_CAP]:
        regels.append(f"input: <b>{_esc(str(inp.get('name', '?')))}</b> — {_esc(_cap(str(inp.get('description') or ''), RR_DESC_CAP))}")
    if len(ex.get("input") or []) > RR_INPUT_CAP:
        regels.append(f"… +{len(ex['input']) - RR_INPUT_CAP} inputs")
    for uit in (ex.get("output") or [])[:2]:
        regels.append(f"output: <b>{_esc(str(uit.get('name', '?')))}</b>")
    for act in (ex.get("actions") or [])[:RR_ACTION_CAP]:
        waarde = act.get("value")
        expr = _rr_expr(waarde) if isinstance(waarde, dict) else _rr_operand(waarde)
        regels.append(f"<b>{_esc(str(act.get('output', '?')))}</b> ← {_esc(expr)}")
    if len(ex.get("actions") or []) > RR_ACTION_CAP:
        regels.append(f"… +{len(ex['actions']) - RR_ACTION_CAP} actions")
    return "<b>Omgezet naar RegelRecht (v0.8.11)</b><br>" + "<br>".join(regels)
```

- [ ] **Step 2: bronnen inladen in `build_kg7`.** Direct ná het inladen van `pak` (pakket-index) in de instrument-lus:

```python
        yaml_pad = FULL_EXPORT / f"{inst['id']}-{inst['cvdr'].lower()}.yaml"
        if not yaml_pad.is_file():
            sys.exit(f"missing instrument yaml {yaml_pad}")
        yart = {a["number"]: a for a in
                (yaml.safe_load(yaml_pad.read_text(encoding="utf-8")) or {}).get("articles") or []}

        struct = json.loads((DSO_OUT / f"{stem}.documentstructuur.json").read_text(encoding="utf-8"))
        bladcomponenten: list = []

        def _blad(c):
            kids = (c.get("_embedded") or {}).get("documentComponenten") or []
            if not kids:
                bladcomponenten.append(c)
            for k in kids:
                _blad(k)

        for c in struct.get("_embedded", {}).get("documentComponenten", []):
            _blad(c)
        lids: dict = {}
        for b in bladcomponenten:
            wid = b.get("identificatie")
            if not wid:
                continue
            tekst = _xml_tekst(b.get("inhoud"))
            if not tekst:
                continue
            num = _NUM_RE.search(b.get("kop") or "")
            lids[wid] = {"lid": html.unescape(num.group(1)).strip() if num else "",
                         "tekst": _cap(tekst, LID_CAP)}
```

- [ ] **Step 3: artikelen verrijken + lids in payload.** In de artikel-aanmaak-tak (waar `artikelen[art] = {...}` wordt gezet) twee velden toevoegen — de dict wordt:

```python
                if art not in artikelen:
                    ymatch = yart.get(art) or {}
                    artikelen[art] = {"status": status.get(art, "missing_in_report"),
                                      "nRegels": 0, "nRT": len(rts), "rts": rts[:KG_RT_CAP],
                                      "regels": [], "meer": 0,
                                      "tekst": _cap(str(ymatch.get("text") or ""), TEKST_CAP),
                                      "rr": _rr_html(ymatch.get("machine_readable"),
                                                     status.get(art, "missing_in_report"))}
```

En in het payload-dict van het instrument (`uit[inst["id"]] = {...}`) een nieuw veld ná `"artikelen": artikelen`:

```python
        gebruikte_wids = {w for e in artikelen.values() for w in e["rts"]}
```

en in de dict: `"lids": {w: lids[w] for w in sorted(gebruikte_wids) if w in lids},`.

- [ ] **Step 4: overzicht-tooltips samengesteld.** In de overzicht-lus: vervang de `n_art`-tip en de `n_rt`-tip:

```python
            e_tekst = e.get("tekst") or ""
            e_rr = e.get("rr") or ""
            tip_art = (_kg_tip(f"artikel {art}", f"status: {e['status']}",
                               f"{e['nRegels']} regels · {e['nRT']} regelteksten")
                       + (f"<br><br>{_esc(e_tekst)}" if e_tekst else "")
                       + (f"<br><br>{e_rr}" if e_rr else ""))
```

(waar `n_art = _kg_node("art", y, f"art. {art}", stat_kleur, 5.0, tip_art, f"art:{art}")` — de oude inline `_kg_tip(...)` vervalt) en in de rt-lus:

```python
            for i, w in enumerate(e["rts"][:3]):
                ld = lids.get(w)
                tip_rt = (f"lid {ld['lid']} — {_esc(ld['tekst'])}" if ld and ld.get("tekst")
                          else _kg_tip(f"regeltekst {w}", f"artikel {art}"))
                n_rt = _kg_node("rt", y - 6 + i * 12, w.rsplit("__", 2)[-1], stat_kleur, 5.1,
                                tip_rt, f"rt:{w}")
```

- [ ] **Step 5: build-run + standalone gouden check.**

Run: `nldt/.venv/bin/python simulation/build_simulation.py > /tmp/b.log 2>&1; echo $?; grep kennisgraaf /tmp/b.log` (kennisgraaf-regels ongewijzigd) en daarna de standalone check (importlib-truc):

```python
kb = m.build_dso_kb()["kg"]["eindhoven"]
a18 = kb["artikelen"]["1.8"]
assert "meet- en rekenbepalingen" in a18["tekst"]
assert "toegestaan_art_1_8" in a18["rr"] and ("limiet_m" in a18["rr"] or "in_werkingsgebied" in a18["rr"])
w0 = a18["rts"][0]
assert kb["lids"][w0]["tekst"].__len__() >= 40
u = m.build_dso_kb()["kg"]["utrecht"]["artikelen"]["10.4"]
assert "niet geformaliseerd" in u["rr"] and "unmatched" in u["rr"]
```

Expected: alles assert-groen; verify_static nog exit 0.

- [ ] **Step 6: Commit**

```bash
git add simulation/build_simulation.py
git commit -m "feat(simulation): kg7-popups met echte tekst — lidtekst uit documentstructuur, artikeltekst + leesbare RegelRecht-executie uit instrument-YAML (taak 1)"
```

---

### Task 2: template — subgraph- en kaart-tooltips op dezelfde data

**Files:**
- Modify: `simulation/template.html`

**Interfaces:**
- Consumes: `artikelen[nr].tekst/.rr`, `kg.lids[wId]` (Taak 1).
- Produces: subgraph-artikel- en regeltekst-tooltips tonen tekst + rr; geen DOM/structuurwijzigingen.

- [ ] **Step 1: `kg7SubLayout` tooltips.** Vervang de `nA`-creatie:

```js
  const nA=node("art",60,`art. ${art}`,stat,5.0,
    `${esc(`artikel ${art} · ${e.status} · ${e.nRegels} regels`)}` +
    (e.tekst?`<br><br>${esc(e.tekst)}`:"") + (e.rr?`<br><br>${e.rr}`:""));
```

en de rt-node in de `e.rts.forEach`:

```js
  e.rts.forEach((w,i)=>{const y=40+i*22; const parts=w.split("__"); const lbl=parts.slice(-2).join("__")||w;
    const ld=(kg.lids||{})[w];
    const tipR= ld&&ld.tekst ? `lid ${esc(ld.lid||"—")} — ${esc(ld.tekst)}` : esc(`regeltekst ${w}`);
    const nR=node("rt",y,lbl,stat,5.1,tipR);
    n.push(nR); ed.push({s:0,t:n.length-1,st:5.1,cls:"kge-art",d:pad(nA,nR)});});
```

- [ ] **Step 2: build + verify + smoke**

Run: `nldt/.venv/bin/python simulation/build_simulation.py > /tmp/b.log 2>&1; echo $?` en `node simulation/verify_static.mjs > /tmp/v.log 2>&1; echo $?` (nog exit 0 — de nieuwe asserts komen in Taak 3). Smoke via de verify-eval-truc: `__ds.kg7Data()["eindhoven"]["artikelen"]["1.8"].tekst.includes("meet- en rekenbepalingen")` → true.

- [ ] **Step 3: Commit**

```bash
git add simulation/template.html
git commit -m "feat(simulation): kg7-subgraph-popups op tekst- en RegelRecht-data — artikel met tekst+executie, regeltekst met lidtekst (taak 2)"
```

---

### Task 3: verify-gouden + README

**Files:**
- Modify: `simulation/verify_static.mjs`, `simulation/README.md`

- [ ] **Step 1: verify-asserts** (ná de bestaande kg-asserts):

```js
  const a18 = kgE.artikelen["1.8"];
  if (!a18.tekst || !a18.tekst.includes("meet- en rekenbepalingen"))
    throw new Error("kg 1.8-popup mist gouden tekstfragment");
  if (!a18.rr.includes("toegestaan_art_1_8") || !(a18.rr.includes("limiet_m") || a18.rr.includes("in_werkingsgebied")))
    throw new Error("kg 1.8-popup mist executie-output/input");
  const w18 = a18.rts[0], ld18 = (kgE.lids || {})[w18];
  if (!ld18 || !(ld18.tekst.length >= 40))
    throw new Error("kg lids mist echte lidtekst voor " + w18);
  const u104 = kgU.artikelen["10.4"];
  if (!u104.rr.includes("niet geformaliseerd") || !u104.rr.includes("unmatched"))
    throw new Error("kg utrecht 10.4 rr verwacht niet-geformaliseerd/unmatched");
```

- [ ] **Step 2: README** — graaf-alinea aanvullen: popups tonen artikeltekst (cap 500) en de leesbare RegelRecht-executie (inputs/outputs/actions met EN/=/≤, caps 2/4) of de onthouding; regeltekst-popups tonen de echte lidtekst (cap 350); bronnen documentstructuur + instrument-YAML.

- [ ] **Step 3: gate** — `nldt/.venv/bin/python simulation/build_simulation.py && node simulation/verify_static.mjs > /tmp/v.log 2>&1; echo $?` → 0, OK-regel met `sim7 5 stappen`.

- [ ] **Step 4: Commit**

```bash
git add simulation/verify_static.mjs simulation/README.md
git commit -m "test(simulation): tekst- en regelrecht-gouden voor kg7-popups (1.8-fragment, executie, lidtekst, utrecht-onthouding); README-popup-alinea (taak 3)"
```

---

### Task 4: Eindcontrole en hub-commits

- [ ] **Step 1:** volledige cyclus: build + verify (0, `sim7 5 stappen`).
- [ ] **Step 2:** `--gent-only` + `verify_gent_only.mjs` (0; gent-hub blijft kg-datavrij — grep `"lids":` = 0).
- [ ] **Step 3:** pytest-regressie (45 passed).
- [ ] **Step 4:** hub-grootte loggen (`ls -la simulation/simulation.html`) en committen:

```bash
git add simulation/simulation.html simulation/gent-simulatie.html
git commit -m "chore(simulation): hub en Gent-mailpakket herbouwd met tekst- en RegelRecht-popups (taak 4)"
```

---

## Zelfreview (uitgevoerd bij opstellen)

1. **Specdekking**: §3.1 (lids/tekst/rr + caps) → T1; §3.2 (tooltip-koppeling incl. subgraph-omschakeling naar vooraf gerenderde HTML — de artikel-rr is build-HTML, de tekst blijft template-`esc`; overzicht-tips build-side) → T1 Step 4 + T2; §3.3 gouden → T3; §3.4 README → T3; §4 fouten/terugval → beide taken.
2. **Placeholders**: geen — alle stappen letterlijk.
3. **Typeconsistentie**: `lids` topveld per instrument, gelezen als `kg.lids[w]` (T2) en `kgE.lids` (T3); `tekst`/`rr` in `artikelen[nr]` consistent over build/template/verify; Utrecht-10.4-tekst is kort (`[Vervallen …]`) — geen assert op tekstlengte daar, alléén op rr-status.
