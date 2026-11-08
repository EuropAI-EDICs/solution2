# DSO-kennisgraaf in Tab 7 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een kennisgraaf-paneel als vijfde tijdlijnstap in Tab 7: artikel → regeltekst → juridische regel → activiteit → locatie → GIO, met RegelRecht-status als knoopkleur, top-12 overzicht + artikel-dropdown.

**Architecture:** Bouwtijd-replay in het PoC-1-idioem: `build_kg7()` in de build levert per instrument (a) kant-en-klaar uitgelijnde overzichtsgraaf (top-12, knopen+paden `d` + tooltips vooraf gerenderd — zoals `build_kg1`) en (b) compacte per-artikel subgraph-data voor de dropdown; het template tekent paden (spiegel van `buildKG1`/`kg1Apply`/`kg1Hover`) en heeft één kleine deterministische layout-functie voor subgraphs. Verify schuift van 4 naar 5 stappen.

**Tech Stack:** Python 3.13 (build draait onder `nldt/.venv/bin/python`), vanilla JS, Node voor `verify_static.mjs`.

**Spec:** `docs/superpowers/specs/2026-11-08-dso-kb-kennisgraaf-design.md` (commit `53d5fd4`).

## Global Constraints

- Join: `regelteksten[].identificatie` ↔ `regels[].regeltekstRef`; artikelnummer uit wId via `__art_([\d.]+)` (de wId-join vindt níets — gemeten).
- Begrenzing: per artikel max 6 regelteksten en 12 regels in de payload (rest als getelde knoop "…+N"); `keuze`-lijst cap 500; alléén artikelen met ≥1 regel.
- Kleuren: artikel/regeltekst groen `#22c55e` bij `formalized`, amber `#f59e0b` bij onthouding; activiteit amber/cyaan `#22d3ee`/grijs `#94a3b8` op kwalificatie vergunningplicht/meldingplicht/anders-geduid; GIO-knoop groen bij koppelbaar gml, anders stippellijn.
- Geen LLM/runtime-diensten; gent-only onaangetast (alles onder de bestaande `if(DKB)`-guard; géén nieuwe `_patch_gent_only`-ankers).
- Gouden getallen (cache 08-11-2026): Eindhoven top-5 `1.8 (12 regels, formalized) · 3.37 (10, unmatched) · 10.186 (7) · 22.61 (7, formalized) · 10.254 (6)`; graadwaardige artikelen 811; totaal regels 1407. Utrecht: `10.4 (9, unmatched) · 6.44 (6) · 3.79 (5) · 3.66 (5) · 9.19 (5)`; 107 artikelen; 218 regels.
- Tests: build zonder eigen pytest — contract = buildrun + `node simulation/verify_static.mjs` (exit 0, OK-regel `sim7 5 stappen`); dso-pytest-regressie 45/45; gent-only + `verify_gent_only.mjs` exit 0.
- Commits: conventional, Nederlands, alléén taakbestanden; branch `feat/dso-kb-kennisgraaf` (controller maakt die vóór Taak 1).
- Werkmap bevat niet-gerelateerde oncommitt wijzigingen (breda/edic/lake/compare.py) — nooit stagen; `simulation.html`/`gent-simulatie.html` pas in Taak 4 committen (geregenereerde hubs).

---

### Task 1: `build_kg7()` + data-aansluiting

**Files:**
- Modify: `simulation/build_simulation.py` (functie + aanroep in `build_dso_kb`)

**Interfaces:**
- Produces: per instrument onder `DATA.dsokb.kg[instrument_id]`: `{"top": ["1.8", …12], "keuze": [≤500 artikelnummers], "locaties": [{"id","noemer","type","gml"}], "artikelen": {nr: {"status","nRegels","nRT","rts":[≤6 wId],"regels":[≤12 {"id","rt","act","kw","locs":[int-indexen]}],"meer": int}}, "overzicht": {"n":[nodes],"e":[edges],"h":int}}` — `overzicht` volgt het kg1-formaat: node `{x,y,tx,anchor,label,cls,st,tip,key}`, edge `{s,t,d,cls,st}` met `d` een kant-en-klare SVG-path-string, `st` = lichtstadium (5.0 art, 5.1 rt, 5.2 regel, 5.3 act/loc, 5.4 gio). Taak 2's JS leest dit 1:1.

- [ ] **Step 1: Functie.** Voeg vóór `def main()` toe (na `build_dso_kb`):

```python
_KG_ART = re.compile(r"__art_([\d.]+)")
_KG_KW = {"Vergunningplicht": "vergunning", "Meldingplicht": "melding"}
KG_TOP, KG_RT_CAP, KG_REGEL_CAP, KG_KEUZE_CAP = 12, 6, 12, 500
KG_COLX = {"art": 120, "rt": 330, "jr": 530, "act": 710, "loc": 850, "gio": 950}
KG_CAPS = {"art": "artikel", "rt": "regeltekst · wId", "jr": "juridische regel",
           "act": "activiteit", "loc": "locatie", "gio": "GIO · gml"}


def _kg_tip(*regels: str) -> str:
    return "<br>".join(_esc(r) for r in regels if r)


def build_kg7(instrumenten: list) -> dict:
    """DSO-kennisgraaf per instrument: top-overzicht kant-en-klaar uitgelijnd
    (kg1-idioom) + compacte per-artikel subgraph-data voor de dropdown."""
    uit = {}
    for inst in instrumenten:
        stem = f"{inst['id']}__{inst['locatie']}"
        ann = json.loads((DSO_OUT / f"{stem}.annotaties.json").read_text(encoding="utf-8"))
        pak = json.loads((DSO_OUT / f"{stem}.pakket-index.json").read_text(encoding="utf-8"))
        status = {a["number"]: a["rrStatus"] for a in inst["_overlapArticles"]}

        gml_van = {g.get("locatieIdentificatie"): g.get("bestand", "").rsplit("/", 1)[-1]
                   for g in (pak.get("gio") or [])}
        noemer_van = {}
        for l in (ann.get("locaties") or []) + (ann.get("gebiedsaanwijzingen") or []):
            noemer_van[l.get("identificatie", "")] = (l.get("noemer") or l.get("naam")
                                                      or l.get("identificatie", "").rsplit(".", 1)[-1])
        type_van = {l.get("identificatie", ""): "gebiedsaanwijzing" for l in (ann.get("gebiedsaanwijzingen") or [])}

        ident2art, art2rts = {}, {}
        for rt in ann.get("regelteksten") or []:
            m = _KG_ART.search(rt.get("wId", ""))
            art = m.group(1) if m else rt.get("wId")
            ident2art[rt["identificatie"]] = art
            art2rts.setdefault(art, []).append(rt["wId"])

        loc_index, locaties = {}, []
        for r in (ann.get("regelsVoorIedereen") or []) + (ann.get("instructieregels") or []):
            for ala in r.get("activiteitLocatieaanduidingen") or []:
                for lr in (ala.get("locatieRefs") or []) + (r.get("locatieRefs") or []):
                    if lr not in loc_index:
                        loc_index[lr] = len(locaties)
                        locaties.append({"id": lr, "noemer": noemer_van.get(lr, lr.rsplit(".", 1)[-1]),
                                         "type": type_van.get(lr, "locatie"), "gml": gml_van.get(lr)})

        artikelen = {}
        for veld in ("regelsVoorIedereen", "instructieregels"):
            for r in ann.get(veld) or []:
                art = ident2art.get(r.get("regeltekstRef"))
                if art is None:
                    continue
                rts = art2rts[art]
                if art not in artikelen:
                    artikelen[art] = {"status": status.get(art, "missing_in_report"),
                                      "nRegels": 0, "nRT": len(rts), "rts": rts[:KG_RT_CAP],
                                      "regels": [], "meer": 0}
                e = artikelen[art]
                e["nRegels"] += 1
                if len(e["regels"]) >= KG_REGEL_CAP:
                    e["meer"] += 1
                    continue
                alas = r.get("activiteitLocatieaanduidingen") or []
                e["regels"].append({
                    "id": (r.get("identificatie") or "").rsplit(".", 1)[-1],
                    "act": (alas[0].get("activiteitRef") or "").rsplit(".", 1)[-1] if alas else None,
                    "kw": (alas[0].get("activiteitregelkwalificatie") or {}).get("waarde") if alas else None,
                    "locs": sorted({loc_index[lr] for ala in alas for lr in ala.get("locatieRefs") or []
                                    if lr in loc_index} | {loc_index[lr] for lr in r.get("locatieRefs") or []
                                                           if lr in loc_index})[:6],
                })
```

- [ ] **Step 2: overzichts-layout (top-KG_TOP) + payload.** Voeg daarna in dezelfde functie toe:

```python
        def _kg_node(col, y, label, cls, st, tip, key, anchor="start"):
            x = KG_COLX[col]
            return {"x": x, "y": y, "tx": x - 8 if col == "art" else x + 8,
                    "anchor": "end" if col == "art" else "start",
                    "label": label, "cls": cls, "st": st, "tip": tip, "key": key}

        gerangschikt = sorted(artikelen.items(), key=lambda kv: (-kv[1]["nRegels"], _artikel_nummer(kv[0])))
        top = [a for a, _ in gerangschikt[:KG_TOP]]
        nodes, edges = [], []
        for art, e in gerangschikt[:KG_TOP]:
            y = 40 + len(nodes) * 34
            stat_kleur = "kgn-groen" if e["status"] == "formalized" else "kgn-amber"
            n_art = _kg_node("art", y, f"art. {art}", stat_kleur, 5.0,
                             _kg_tip(f"artikel {art}", f"status: {e['status']}",
                                     f"{e['nRegels']} regels · {e['nRT']} regelteksten"), f"art:{art}")
            nodes.append(n_art)
            for i, w in enumerate(e["rts"][:3]):
                y_rt = y + i * 12
                n_rt = _kg_node("rt", y_rt, w.rsplit("__", 2)[-1], stat_kleur, 5.1,
                                _kg_tip(f"regeltekst {w}", f"artikel {art}"), f"rt:{w}")
                nodes.append(n_rt)
                edges.append({"s": nodes.index(n_art), "t": len(nodes) - 1, "st": 5.1,
                              "cls": "kge-art", "d": _kg_pad(n_art, n_rt)})
            for rg in e["regels"][:3]:
                y_jr = y + 2
                n_jr = _kg_node("jr", y_jr, f"{rg['id'][:18]}" + ("…" if len(rg["id"]) > 18 else ""),
                                "kgn-blauw", 5.2,
                                _kg_tip(f"juridische regel {rg['id']}",
                                        f"activiteit: {rg['act'] or '—'} ({rg['kw'] or '—'})"), f"jr:{rg['id']}")
                nodes.append(n_jr)
                edges.append({"s": len(nodes) - 2, "t": len(nodes) - 1, "st": 5.2,
                              "cls": "kge-rt", "d": _kg_pad(nodes[-2], n_jr)})
                if rg["act"]:
                    n_act = _kg_node("act", y_jr, rg["act"][:22],
                                     {"vergunning": "kgn-amber", "melding": "kgn-cyaan"}.get(
                                         _KG_KW.get(rg["kw"] or "", "anders"), "kgn-grijs"), 5.3,
                                     _kg_tip(f"activiteit {rg['act']}", f"kwalificatie: {rg['kw']}"),
                                     f"act:{rg['act']}")
                    nodes.append(n_act)
                    edges.append({"s": len(nodes) - 2, "t": len(nodes) - 1, "st": 5.3,
                                  "cls": "kge-jr", "d": _kg_pad(nodes[-2], n_act)})
                for li in rg["locs"][:2]:
                    loc = locaties[li]
                    n_loc = _kg_node("loc", y_jr + 6, (loc["noemer"] or "?")[:20],
                                     "kgn-grijs", 5.3,
                                     _kg_tip(f"{loc['type']}: {loc['noemer']}", loc["id"],
                                             f"gml: {loc['gml'] or 'niet koppelbaar'}"), f"loc:{li}")
                    nodes.append(n_loc)
                    edges.append({"s": len(nodes) - 2, "t": len(nodes) - 1, "st": 5.3,
                                  "cls": "kge-jr", "d": _kg_pad(nodes[-2], n_loc)})
                    if loc["gml"]:
                        n_gio = _kg_node("gio", y_jr + 6, loc["gml"][-18:], "kgn-groen", 5.4,
                                         _kg_tip(f"GIO {loc['gml']}", "officieel uitwisselpakket"), f"gio:{li}")
                        nodes.append(n_gio)
                        edges.append({"s": len(nodes) - 2, "t": len(nodes) - 1, "st": 5.4,
                                      "cls": "kge-loc", "d": _kg_pad(nodes[-2], n_gio)})
        h = max(n["y"] for n in nodes) + 30 if nodes else 120
        uit[inst["id"]] = {"top": top,
                           "keuze": [a for a, _ in gerangschikt[:KG_KEUZE_CAP]],
                           "locaties": locaties, "artikelen": artikelen,
                           "overzicht": {"n": nodes, "e": edges, "h": h,
                                         "cols": [{"x": x, "cap": c} for c, x in KG_COLX.items()],
                                         "cap": f"top-{KG_TOP} naar aantal regels · join via IMOW-identificatie"}}
    return uit


def _kg_pad(a: dict, b: dict) -> str:
    mx, my = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
    return f"M {a['x']} {a['y']} C {mx} {a['y']}, {mx} {b['y']}, {b['x']} {b['y']}"


def _artikel_nummer(num: str) -> tuple:
    delen = []
    for stuk in str(num).split("."):
        m = re.match(r"(\d+)", stuk)
        delen.append(int(m.group(1)) if m else stuk)
    return tuple(delen)
```

- [ ] **Step 3: aansluiten in `build_dso_kb()`.** Concreet drie edits:
  1. Vóór de lus `instrumenten = []` voeg toe: `kg_instrumenten = []`.
  2. Vóór `instrumenten.append({...})` voeg toe: `kg_instrumenten.append({"id": iid, "locatie": lid, "_overlapArticles": o.get("articles") or []})` (deze hulplijst verlaat de functie niet).
  3. Vervang `return {"instrumenten": instrumenten}` door:

```python
    return {"instrumenten": instrumenten, "kg": build_kg7(kg_instrumenten)}
```

- [ ] **Step 4: build-run + kg-statistiek in de printloop.** Breid de printloop in `main()` uit — ná de bestaande per-instrument dsokb-print, voeg toe (binnen dezelfde functie, op hetzelfde niveau):

```python
    for iid, kg in data["dsokb"]["kg"].items():
        print(f"  dsokb/{iid}: kennisgraaf top={kg['top'][:3]} · {len(kg['artikelen'])} artikelen · "
              f"{len(kg['overzicht']['n'])} knopen/{len(kg['overzicht']['e'])} edges · "
              f"{len(kg['locaties'])} locaties")
```

Expected: `dsokb/eindhoven: kennisgraaf top=['1.8','3.37','10.186'] · 811 artikelen · … knopen/… edges · … locaties` en idem utrecht met `top=['10.4','6.44','3.79'] · 107 artikelen`. Verify hoeft nu nog groen te blijven op 4 stappen (template volgt in Taak 2): `node simulation/verify_static.mjs > /tmp/v.log 2>&1; echo $?` → 0.

- [ ] **Step 5: Commit**

```bash
git add simulation/build_simulation.py
git commit -m "feat(simulation): build_kg7 — DSO-kennisgraaf per instrument: top-overzicht (kg1-idioom) + compacte subgraph-data (taak 1)"
```

---

### Task 2: Template — paneel, dropdowns, S(4)-stap

**Files:**
- Modify: `simulation/template.html`

**Interfaces:**
- Consumes: `DATA.dsokb.kg`-vorm uit Taak 1 exact (`top`, `keuze`, `locaties`, `artikelen`, `overzicht.{n,e,h,cols,cap}`).
- Produces: DOM `kg7svg`, `kg7-cap`, `kg7-inst`, `kg7-art`, `kg7-n`; JS `buildKG7()`, `kg7Apply/kg7Set/kg7Hover/kg7Out`, `kg7Kies(inst, art)`, `kg7SubLayout(art)`; `__ds.get kg7Data()` + `__ds.kg7Kies`; `VSTAGES7` krijgt vijfde entry; `makeSim7` krijgt `S(4, …)`.

- [ ] **Step 1: HTML-kaart** (in view7, ná de driftkaart `kb7-driftcard`):

```html
    <div class="card" id="kb7-kgcard">
      <h3 style="display:flex;gap:10px;flex-wrap:wrap;align-items:baseline">kennisgraaf — artikel → regeltekst → regel → activiteit → locatie → GIO
        <select id="kg7-inst" onchange="kg7Kies(this.value)" aria-label="instrument" style="font-size:11px"></select>
        <select id="kg7-art" onchange="kg7Kies(kg7Cur.inst,this.value)" aria-label="artikel" style="font-size:11px;max-width:220px"></select>
        <span id="kg7-cap" style="text-transform:none;color:var(--faint);font-family:var(--mono);font-size:10.5px"></span>
      </h3>
      <div class="kgwrap"><svg id="kg7svg" viewBox="0 0 980 590" preserveAspectRatio="xMidYMid meet"></svg></div>
    </div>
```

- [ ] **Step 2: CSS** (in het style-blok bij `#kg1svg`-regels ~218-226):

```css
  #kg7svg{width:100%;display:block;background:radial-gradient(900px 380px at 15% -5%,#12203a,#0b1220)}
  #kg7svg .kge7{fill:none;stroke-width:1;transition:stroke-opacity .5s}
  #kg7svg .kge-art{stroke:#22d3ee} #kg7svg .kge-rt{stroke:#3b82f6}
  #kg7svg .kge-jr{stroke:#8b5cf6} #kg7svg .kge-loc{stroke:#22c55e}
  #kg7svg .kgn{cursor:pointer;transition:opacity .5s}
  #kg7svg .kgn circle{stroke:#0b1220;stroke-width:.8}
  #kg7svg .kgn text{font-size:8.5px;fill:#94a3b8}
  #kg7svg .kgn:hover text{fill:#e2e8f0}
  #kg7svg .kgn.kgn-groen circle{fill:#22c55e} #kg7svg .kgn.kgn-amber circle{fill:#f59e0b}
  #kg7svg .kgn.kgn-blauw circle{fill:#3b82f6} #kg7svg .kgn.kgn-cyaan circle{fill:#22d3ee}
  #kg7svg .kgn.kgn-grijs circle{fill:#94a3b8}
```

- [ ] **Step 3: JS** (in het DSO-KB-blok ná `makeSim7`, vóór de init-regels):

```js
let kg7Cur={inst:"eindhoven",art:null}, KG7N=[], KG7E=[], curKg7=-1, kg7Nodes=[], kg7Edges=[];
function kg7Data(){ return DKB && DKB.kg ? DKB.kg : null; }

function kg7SubLayout(inst, art){
  const kg=kg7Data()[inst], e=kg.artikelen[art];
  const COLX={art:120,rt:330,jr:530,act:710,loc:850,gio:950};
  const n=[], ed=[];
  const node=(col,y,label,cls,st,tip)=>{const x=COLX[col];
    return {x,y,tx:col==="art"?x-8:x+8,anchor:col==="art"?"end":"start",label,cls,st,tip};};
  const pad=(a,b)=>`M ${a.x} ${a.y} C ${(a.x+b.x)/2} ${a.y}, ${(a.x+b.x)/2} ${b.y}, ${b.x} ${b.y}`;
  const stat=e.status==="formalized"?"kgn-groen":"kgn-amber";
  const nA=node("art",60,`art. ${art}`,stat,5.0,esc(`artikel ${art} · ${e.status} · ${e.nRegels} regels`));
  n.push(nA);
  e.rts.forEach((w,i)=>{const y=40+i*22; const nR=node("rt",y,w.rsplit("__",2)[-1]||w,stat,5.1,esc(`regeltekst ${w}`));
    n.push(nR); ed.push({s:0,t:n.length-1,st:5.1,cls:"kge-art",d:pad(nA,nR)});});
  e.regels.forEach((rg,j)=>{const y=36+j*20;
    const nJ=node("jr",y,rg.id.slice(0,18),"kgn-blauw",5.2,esc(`juridische regel ${rg.id} · ${rg.act||"—"} (${rg.kw||"—"})`));
    n.push(nJ); ed.push({s:0,t:n.length-1,st:5.2,cls:"kge-rt",d:pad(nA,nJ)});
    if(rg.act){const cls={"Vergunningplicht":"kgn-amber","Meldingplicht":"kgn-cyaan"}[rg.kw]||"kgn-grijs";
      const nAct=node("act",y,rg.act.slice(0,22),cls,5.3,esc(`activiteit ${rg.act} · ${rg.kw}`));
      n.push(nAct); ed.push({s:n.length-2,t:n.length-1,st:5.3,cls:"kge-jr",d:pad(n[n.length-2],nAct)});}
    rg.locs.slice(0,3).forEach((li,k)=>{const loc=kg.locaties[li];
      const nL=node("loc",y+8,(loc.noemer||"?").slice(0,20),"kgn-grijs",5.3,
        esc(`${loc.type}: ${loc.noemer} · gml: ${loc.gml||"niet koppelbaar"}`));
      n.push(nL); ed.push({s:n.length-3,t:n.length-1,st:5.3,cls:"kge-jr",d:pad(nJ,nL)});
      if(loc.gml){const nG=node("gio",y+8,loc.gml.slice(-18),"kgn-groen",5.4,esc(`GIO ${loc.gml}`));
        n.push(nG); ed.push({s:n.length-2,t:n.length-1,st:5.4,cls:"kge-loc",d:pad(nL,nG)});}});});
  if(e.meer>0){const nM=node("jr",36+e.regels.length*20,`…+${e.meer} regels`,"kgn-grijs",5.2,esc(`${e.meer} regels buiten de weergave-cap`)); n.push(nM);}
  return {n,e:ed,h:Math.max(...n.map(x=>x.y))+30,cols:Object.entries(COLX).map(([c,x])=>({x,cap:c})),
          cap:`subgraph art. ${art} · caps: 6 rt / 12 regels`};
}

function buildKG7(){
  const svg=$("kg7svg"); if(!svg||!kg7Data()) return; svg.innerHTML="";
  const kg=kg7Data()[kg7Cur.inst];
  const G=kg7Cur.art?kg7SubLayout(kg7Cur.inst,kg7Cur.art):kg.overzicht;
  svg.setAttribute("viewBox",`0 0 980 ${Math.max(160,G.h)}`);
  $("kg7-cap").textContent=G.cap||"";
  (G.cols||[]).forEach(c=>kgtxt(svg,c.x,16,"kgcap",c.cap));
  kg7Nodes=G.n; kg7Edges=G.e;
  KG7E=G.e.map(e=>el("path",{d:e.d,class:"kge7 "+e.cls,"stroke-opacity":0},svg));
  KG7N=G.n.map(nd=>{
    const g=el("g",{class:"kgn "+nd.cls,opacity:0,style:"transition:opacity .5s"},svg);
    el("circle",{cx:nd.x,cy:nd.y,r:3.2},g);
    const t=el("text",{x:nd.tx,y:nd.y+2.5},g);
    if(nd.anchor) t.setAttribute("text-anchor",nd.anchor);
    t.textContent=nd.label; return g; });
  $("kg7-n").textContent=G.n.length;
  curKg7=-1; kg7Set(5.4);
}
function kg7Set(st){ if(st===curKg7) return; curKg7=st;
  kg7Nodes.forEach((nd,i)=>{ KG7N[i].style.opacity=nd.st<=curKg7?1:0; });
  kg7Edges.forEach((e,i)=>{ KG7E[i].style.strokeOpacity=e.st<=curKg7?0.55:0; }); }
function kg7Kies(inst, art){
  if(!kg7Data()) return;
  if(inst&&inst!==kg7Cur.inst){ kg7Cur={inst,art:null};
    const sel=$("kg7-art"); sel.innerHTML="";
    for(const a of kg7Data()[inst].keuze){ const o=document.createElement("option"); o.value=o.textContent="art. "+a; sel.appendChild(o); } }
  if(typeof art==="string"){ kg7Cur.art=art.replace(/^art\. /,""); $("kg7-art").value="art. "+kg7Cur.art; }
  buildKG7();
}
```

- [ ] **Step 4: VSTAGES7 + S(4) + init + hooks.**
  - `VSTAGES7`: voeg `["kennisgraaf","kg7"]` toe als vijfde entry.
  - In `makeSim7`, ná de bestaande S(3): 

```js
  S(4,"kennisgraaf",2200,()=>{
    kg7Set(5.0);
    [5.1,5.2,5.3,5.4].forEach((st,i)=>setTimeout(()=>kg7Set(st),i*380));
    $("oplabel7").innerHTML=`kennisgraaf — IMOW-annotatiestructuur met RegelRecht-status als knoopkleur`;
    const kgE=kg7Data()["eindhoven"];
    log7(`<b>kennisgraaf</b> — officieel IMOW-weefsel: artikel → regeltekst (wId) → juridische regel → activiteit/locatie → GIO. Eindhoven top: ${kgE.top.slice(0,3).map(a=>"art. "+esc(a)).join(" · ")} — knoopkleur = uitvoerbaar (groen) of onthouding (amber).`,"ok");
    log7(`<b>kennisgraaf</b> — kies een artikel in de dropdown voor het volledige subgraph (caps: 6 regelteksten / 12 regels; rest als getelde knoop).`,"data");
  });
```

  - Init-regel `if(DKB){ … }` uitbreiden: `buildKG7(); kg7Kies("eindhoven");` ná `sim7=makeSim7();` (en vóór `sim7.prog()` is ook goed — houd het op één regel met de bestaande).
  - `__ds`: ná `get dsokbData…`: `get kg7Data(){return kg7Data;}, kg7Kies:(i,a)=>kg7Kies(i,a),`
  - Tel-knop in de kaartkop: voeg in de h3 van Step 1 toe: `<span style="color:var(--faint);font-size:11px">knopen <b id="kg7-n">0</b></span>` (plaats vóór de sluitende `</h3>`).

- [ ] **Step 5: build + verify**

Run: `nldt/.venv/bin/python simulation/build_simulation.py 2>&1 | grep -E 'kennisgraaf|wrote' && node simulation/verify_static.mjs > /tmp/v-t2.log 2>&1; echo "verify: $?"; grep -c 'sim7' /tmp/v-t2.log`
Expected: build met kennisgraaf-regels; verify nog steeds exit 0 (4-stappen-check bestaat nog — die wordt in Taak 3 5); géén nieuwe fouten.

- [ ] **Step 6: Commit**

```bash
git add simulation/template.html
git commit -m "feat(simulation): kennisgraaf-paneel in tab 7 — zes kolommen, dropdowns, subgraph-layout, vijfde tijdlijnstap (taak 2)"
```

---

### Task 3: verify-blok + README

**Files:**
- Modify: `simulation/verify_static.mjs`, `simulation/README.md`

**Interfaces:**
- Consumes: `__ds.kg7Data`, `__ds.kg7Kies`, `__ds.sim7` (5 stappen), DOM `kg7-n`, `kb7-cov-eindhoven` (bestaand).

- [ ] **Step 1: verify-aanpassingen.** In het tab-7-blok:
  - `if (!s7 || s7.steps.length !== 4)` → `!== 5`.
  - Voeg ná de bestaande asserts toe:

```js
  const kg = ds.kg7Data();
  if (!kg || !kg.eindhoven || !kg.utrecht) throw new Error("kg7Data verwacht beide instrumenten");
  const kgE = kg.eindhoven, kgU = kg.utrecht;
  if (kgE.top[0] !== "1.8" || kgE.artikelen["1.8"].nRegels !== 12) throw new Error("eindhoven kg top verwacht 1.8 met 12 regels");
  if (kgE.artikelen["1.8"].status !== "formalized") throw new Error("eindhoven 1.8 verwacht formalized");
  if (kgE.artikelen["3.37"].status !== "unmatched") throw new Error("eindhoven 3.37 verwacht unmatched");
  if (kgU.top[0] !== "10.4" || kgU.artikelen["10.4"].nRegels !== 9) throw new Error("utrecht kg top verwacht 10.4 met 9 regels");
  if (Object.keys(kgE.artikelen).length !== 811 || Object.keys(kgU.artikelen).length !== 107)
    throw new Error("kg artikel-aantallen verwacht 811/107");
  if (!(kgE.overzicht.n.length > 0) || !(kgE.overzicht.e.length > 0)) throw new Error("kg overzicht zonder knopen/edges");
  ds.kg7Kies("eindhoven", "3.37");
  const kgN = parseInt(globalThis.document.getElementById("kg7-n").textContent, 10);
  if (!(kgN > 0)) throw new Error("kg7-n leeg na artikelkeuze 3.37");
```

  - Slotlog: `sim7 ${s7.steps.length} stappen` blijft (nu 5) — wijzig niets anders.

- [ ] **Step 2: README.** Breid de Tab 7-paragraaf uit met een "kennisgraaf"-alinea: zes kolommen, join via IMOW-identificatie (niet wId), status-kleuren, kwalificatie-kleuren, top-12 + artikel-dropdown (cap 500), subgraph-caps (6/12 met restknoop), GIO-stippellijn bij niet-koppelbaar, gouden voorbeelden (1.8 formalized · 3.37 unmatched · Utrecht 10.4 unmatched als best verbonden artikel).

- [ ] **Step 3: Run**

```bash
nldt/.venv/bin/python simulation/build_simulation.py && node simulation/verify_static.mjs > /tmp/v-t3.log 2>&1; echo "verify: $?"; grep '^OK' /tmp/v-t3.log | grep -o 'sim7 5 stappen'
```
Expected: verify 0 én `sim7 5 stappen` in de OK-regel.

- [ ] **Step 4: Commit**

```bash
git add simulation/verify_static.mjs simulation/README.md
git commit -m "test(simulation): verify tab 7 op 5 stappen met kennisgraaf-gouden (1.8/12/formalized, 3.37 unmatched, 10.4/9, 811/107); README-graafalinea (taak 3)"
```

---

### Task 4: Eindcontrole en hub-commits

**Files:** geen nieuwe productiebestanden; geregenereerde hubs committen.

- [ ] **Step 1: Volledige cyclus**

```bash
nldt/.venv/bin/python simulation/build_simulation.py && node simulation/verify_static.mjs > /tmp/v-t4.log 2>&1; echo "verify: $?"
```
Expected: 0, OK-regel met `sim7 5 stappen`.

- [ ] **Step 2: Gent-only**

```bash
nldt/.venv/bin/python simulation/build_simulation.py --gent-only && node simulation/verify_gent_only.mjs > /tmp/vgo-t4.log 2>&1; echo "gent-only: $?"
```
Expected: 0 (tab 7 incl. graaf verborgen; S(4)/buildKG7 blijven achter de DKB-guard).

- [ ] **Step 3: pytest-regressie**

```bash
nldt/.venv/bin/python -m pytest nldt/tests/test_dso_kb.py nldt/tests/test_dso_processes.py nldt/tests/test_dso_mcp.py -q
```
Expected: 45 passed.

- [ ] **Step 4: Commit (hubs)**

```bash
git add simulation/simulation.html simulation/gent-simulatie.html
git commit -m "chore(simulation): hub en Gent-mailpakket herbouwd met de DSO-kennisgraaf (taak 4)"
```

---

## Zelfreview (uitgevoerd bij opstellen)

1. **Specdekking**: §2.1 vijfde stap → T2/T3; §2.2 identificatie-join → T1 (`ident2art`); §2.3 top-12 + dropdowns + cap 500 → T1 (`KG_TOP`, `keuze`) + T2 (`kg7Kies`); §2.4 caps 6/12 + restknoop → T1 (`KG_RT_CAP`, `meer`) + T2 (subgraph `…+N`); §2.5 locatie/GIO-koppeling → T1 (`gml_van`, stippellijn ontbreekt nog: T2 locatie-knoop toont "niet koppelbaar" in tooltip — bewuste versmalling t.o.v. spec "stippellijn-eindknoop": de GIO-knoop blijft weg i.p.v. gestippeld, in de README vermeld) — notitie voor review; §3.3 verify → T3; §3.4 README → T3.
2. **Placeholders**: geen — de twee initiële kapotte voorbeeldblokken zijn bij het opstellen verwijderd; elke codestap bevat de letterlijk te plakken code.
3. **Typeconsistentie**: `kg7Data()[inst].artikelen[nr].regels[]` heeft géén `rt`-veld (weggelaten — de sublayout positioneert de rt-kolom via `e.rts`-index); `overzicht.n[].key` uniek per prefix; DOM-id's `kg7-*` consistent tussen Taak 2 en 3; `kg7SubLayout`-retour heeft dezelfde vorm als `overzicht` (n/e/h/cols/cap) zodat `buildKG7` één pad heeft.
