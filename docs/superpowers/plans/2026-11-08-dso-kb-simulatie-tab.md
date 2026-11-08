# Tab 7 "DSO ↔ RegelRecht" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een zevende tab in `simulation/simulation.html` die de DSO↔RegelRecht-keten her-speelt uit de kennisbank-artefacten, met drift-kaart via nieuwe `ververs()`-persistentie.

**Architecture:** Bouwtijd-replay (huispatroon `build_veenendaal`): `build_dso_kb()` leest `dso_overlap/out/*.json` rechtstreeks (stdlib/json, geen dso_kb-import, geen MCP), injecteert als `DATA.dsokb` via de `/*__DATA__*/`-marker; de template krijgt tab 7 met een vier-stappen-`Sim`; `verify_static.mjs` krijgt een gouden-getallen-blok. Eén uitzondering op "build leest alleen": `ververs()` in `nldt/services/dso_kb.py` schrijft voortaan `{stem}.ververs.json` (voedt de drift-kaart).

**Tech Stack:** Python 3.13 (`nldt/.venv` voor dso_kb; de build draait met de python die ook shapely heeft — ongewijzigd), vanilla JS in de single-file template, Node voor `verify_static.mjs`.

**Spec:** `docs/superpowers/specs/2026-11-08-dso-kb-simulatie-tab-design.md` (commit `7201676`).

## Global Constraints

- Geen runtime-diensten, géén MCP-aanroepen, géén LLM in tab 7; alle getallen komen uit de cache-artefacten (`dso_overlap/out/`).
- Ontbrekende artefacten → build stopt hard met duidelijke melding (als `missing poc-veenendaal …`).
- Voorbeeldlijsten max 5 items; geen volledige artikel-/GIO-lijsten in de data.
- `--gent-only` blijft werken: alle tab-7-JS achter een `if (DKB)`-guard; `_patch_gent_only` wordt niet aangeraast.
- Gouden getallen (uit de meting van 07-11-2026): Eindhoven 811/457/**0.5635** (statusCounts formalized 457 · unmatched 285 · missing_in_report 67 · ambiguous 2), Utrecht 107/7/**0.0654**; toets Eindhoven scenario 434 · onthouding 23 · enginefout 0, Utrecht getoetst 7; geo Eindhoven **34/34**, Utrecht naamafstemming **8/8**; drift `"geen"` (uitsluitend geasserteerd als een `ververs`-rapport in de data zit).
- Template-wijzigingen volgen de bestaande idomen exact: rail-card `st7-${i}`, `Sim`-klasse ongewijzigd hergebruikt, `switchTab`-lus + `sim()`-ternary uitgebreid, `__ds` krijgt getters.
- Tests: dso_kb via `nldt/.venv/bin/python -m pytest nldt/tests/test_dso_kb.py -v`; build+template via `python3 simulation/build_simulation.py` + `node simulation/verify_static.mjs` (werkende directory repo-root; de build heeft geen eigen pytest).
- Commits: conventional, Nederlands, alléén de bestanden van de taak; uitgevoerd op branch `feat/dso-kb-tab7` (controller maakt die aan vóór Taak 1).

---

### Task 1: `ververs()`-persistentie in `dso_kb`

**Files:**
- Modify: `nldt/services/dso_kb.py` (import-blok + staart van `ververs()`)
- Test: `nldt/tests/test_dso_kb.py` (één test erbij)

**Interfaces:**
- Produces: `ververs()` schrijft `{stem}.ververs.json` (volledig resultaat-dict + `"gegenereerdOp"` iso-UTC) in `out_dir` en geeft datzelfde dict terug (bestaande velden ongewijzigd; `gegenereerdOp` erbij). Taak 2 leest dit bestand.

- [ ] **Step 1: Falende test** (toevoegen aan `nldt/tests/test_dso_kb.py`, onder de ververs-tests):

```python
def test_ververs_schrijft_rapport(tmp_path, monkeypatch):
    monkeypatch.delenv("NLDT_OFFLINE", raising=False)  # hermetisch t.o.v. ambient env
    out = _kopieer_fixtures(tmp_path)
    (out / "testgm__test-loc.annotaties.json").write_text(
        (DRIFT / "oud.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    nieuw = json.loads((DRIFT / "nieuw_gewijzigd.json").read_text(encoding="utf-8"))

    def nep_runner(args):
        (out / "testgm__test-loc.annotaties.json").write_text(
            json.dumps(nieuw, ensure_ascii=False), encoding="utf-8"
        )

    uit = dso_kb.ververs(
        "testgm", met_tpod=False, out_dir=out, runner=nep_runner,
        instrumenten=INSTR, locaties=LOCS,
    )
    rapport = json.loads((out / "testgm__test-loc.ververs.json").read_text(encoding="utf-8"))
    assert rapport["drift"]["inhoudelijkeDrift"] == "wel"
    assert rapport["gegenereerdOp"]
    assert rapport == {k: uit[k] for k in rapport}
```

- [ ] **Step 2: Run — moet falen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_dso_kb.py -v`
Expected: 1 FAIL — `FileNotFoundError` op `testgm__test-loc.ververs.json` (de overige 26 PASS).

- [ ] **Step 3: Implementatie.** In `nldt/services/dso_kb.py`:

3a. Bij de imports bovenin (na `import sys`):

```python
from datetime import datetime, timezone
```

3b. Vervang de staart van `ververs()` — het huidige blok:

```python
    return {
        "instrument": instrument,
        "locatie": lid,
        "annShaOud": sha_oud,
        "annShaNieuw": sha_nieuw,
        "drift": drift,
        "tpod": {"herbouwd": herbouwd},
    }
```

door:

```python
    uit = {
        "instrument": instrument,
        "locatie": lid,
        "annShaOud": sha_oud,
        "annShaNieuw": sha_nieuw,
        "drift": drift,
        "tpod": {"herbouwd": herbouwd},
        "gegenereerdOp": datetime.now(timezone.utc).isoformat(),
    }
    (out / f"{stem}.ververs.json").write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return uit
```

- [ ] **Step 4: Run — slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_dso_kb.py -v`
Expected: 27 PASS, pristine.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/dso_kb.py nldt/tests/test_dso_kb.py
git commit -m "feat(nldt): ververs-rapport-persistentie — ververs() schrijft {stem}.ververs.json met gegenereerdOp (Tab 7-driftkaart, taak 1)"
```

---

### Task 2: `build_dso_kb()` in de build

**Files:**
- Modify: `simulation/build_simulation.py` (constante + functie + `main()`-aansluiting)

**Interfaces:**
- Consumes: `dso_overlap/out/`-artefacten: `{stem}.overlap.json`, `.toets.json`, `.geo-validatie.json` (optioneel), `.annotaties.meta.json` (optioneel), `.ververs.json` (optioneel); `stem = "<instrument>__<locatie>"`.
- Produces: `DATA.dsokb = {"instrumenten": [ … ]}` met per instrument exact de velden die Taak 3's JS leest: `id, label, cvdr, locatie, locatieLabel, punt, counts{regelteksten,activiteiten,locaties,gebiedsaanwijzingen,regelsVoorIedereen,instructieregels}, dekking{dsoArtikelen,executable,abstain,coverage}, statusCounts, toets, geo{getoetst,overeenstemming,naamOvereenkomend?}, voorbeelden[≤5]{artikel,status,reden}, annotatiesSha16, fetchedAt, gegenereerdOp, ververs|null`.

- [ ] **Step 1: Constante + functie.** Voeg direct ná de constante `ROOT = Path(__file__).resolve().parent.parent` (en vóór het eerste gebruik ervan) toe:

```python
DSO_OUT = ROOT / "nldt" / "simulation" / "regelrecht" / "dso_overlap" / "out"
DSO_INSTRUMENTEN = [
    ("eindhoven", "eindhoven-woensel-proxy", "Omgevingsplan gemeente Eindhoven", "CVDR696400"),
    ("utrecht", "utrecht-domplein", "Omgevingsverordening provincie Utrecht", "CVDR704250"),
]
```

En de functie (plaats vóór `def main()`):

```python
def build_dso_kb() -> dict:
    """DSO↔RegelRecht-kennisbank → displayblok (Tab 7). Leest alléén cache-artefacten."""
    if not DSO_OUT.is_dir():
        sys.exit(f"missing dso_overlap cache under {DSO_OUT}")
    instrumenten = []
    for iid, lid, label, cvdr in DSO_INSTRUMENTEN:
        stem = f"{iid}__{lid}"
        ov = json.loads((DSO_OUT / f"{stem}.overlap.json").read_text(encoding="utf-8"))
        toets = json.loads((DSO_OUT / f"{stem}.toets.json").read_text(encoding="utf-8"))
        geo_pad, meta_pad, vers_pad = (DSO_OUT / f"{stem}.geo-validatie.json",
                                       DSO_OUT / f"{stem}.annotaties.meta.json",
                                       DSO_OUT / f"{stem}.ververs.json")
        geo = json.loads(geo_pad.read_text(encoding="utf-8")) if geo_pad.is_file() else {}
        meta = json.loads(meta_pad.read_text(encoding="utf-8")) if meta_pad.is_file() else {}
        ververs = json.loads(vers_pad.read_text(encoding="utf-8")) if vers_pad.is_file() else None

        counts = ov["dso"]["counts"]
        o = ov["overlap"]
        geo_regels = {}
        v = (geo or {}).get("validatie") or {}
        if v:
            geo_regels = {"getoetst": v.get("getoetst"), "overeenstemming": v.get("overeenstemming")}
        na = (((geo or {}).get("sweep") or {}).get("naamAfstemming") or {})
        if na:
            geo_regels["naamOvereenkomend"] = na.get("naamOvereenkomend")

        instrumenten.append({
            "id": iid,
            "label": label,
            "cvdr": cvdr,
            "locatie": lid,
            "locatieLabel": (ov.get("location") or {}).get("label") or lid,
            "punt": ov["location"]["geometry"]["coordinates"],
            "counts": {k: counts.get(k) for k in
                       ("regelteksten", "activiteiten", "locaties", "gebiedsaanwijzingen",
                        "regelsVoorIedereen", "instructieregels")},
            "dekking": {"dsoArtikelen": counts.get("uniqueArticleNumbers"),
                        "executable": o.get("executableCount"),
                        "abstain": o.get("abstainCount"),
                        "coverage": o.get("coverageExecutable")},
            "statusCounts": o.get("statusCounts") or {},
            "toets": toets.get("tellingen") or {},
            "geo": geo_regels,
            "voorbeelden": [
                {"artikel": a.get("number"), "status": a.get("rrStatus"), "reden": a.get("reason")}
                for a in (o.get("articles") or []) if not a.get("executable")
            ][:5],
            "annotatiesSha16": (ov.get("dso", {}).get("annotatiesSha256") or "")[:16],
            "fetchedAt": meta.get("fetchedAt"),
            "gegenereerdOp": ov.get("generatedAt"),
            "ververs": ververs,
        })
    return {"instrumenten": instrumenten}
```

- [ ] **Step 2: `main()`-aansluiting.** In de `data = {…}`-dict: voeg ná `"veenendaal": build_veenendaal()}` een nieuwe regel toe zodat het wordt:

```python
    data = {"poc1": build_poc1(), "poc2": build_poc2(), "poc4": build_breda(), "gent": build_gent(),
            "gentBurger": build_gent("gent-verhuizen-burger"),
            "gentKot": build_gent("gent-kot-verhuurder"),
            "gentEvent": build_gent("gent-evenement-organisator"),
            "veenendaal": build_veenendaal(),
            "dsokb": build_dso_kb()}
```

En ná het `vd = data["veenendaal"]`-printblok (vóór het `ly = data["poc2"]["laya"]`-blok):

```python
    for inst in data["dsokb"]["instrumenten"]:
        d = inst["dekking"]
        drift = (inst["ververs"] or {}).get("drift", {}).get("inhoudelijkeDrift", "geen rapport")
        print(f"  dsokb/{inst['id']}: {d['dsoArtikelen']} DSO-artikelen → {d['executable']} uitvoerbaar "
              f"({100 * d['coverage']:.2f}%) · drift: {drift}")
```

- [ ] **Step 3: Run — build slaagt**

Run: `python3 simulation/build_simulation.py 2>&1 | grep -E 'dsokb|wrote'`
Expected: `dsokb/eindhoven: 811 DSO-artikelen → 457 uitvoerbaar (56.35%) · drift: geen rapport` (tot Taak 4 het rapport vult) en de `wrote …`-regel. (De template negeert `dsokb` tot Taak 3 — geen breuk.)

- [ ] **Step 4: Gent-only onaangetast**

Run: `python3 simulation/build_simulation.py --gent-only 2>&1 | tail -2`
Expected: reguliere gent-only-output (geen dsokb-regel; `gent-simulatie.html` geschreven).

- [ ] **Step 5: Commit**

```bash
git add simulation/build_simulation.py
git commit -m "feat(simulation): build_dso_kb — kennisbank-artefacten als DATA.dsokb in de build (Tab 7, taak 2)"
```

---

### Task 3: Tab 7 in de template

**Files:**
- Modify: `simulation/template.html` (tabregel, kop, view-sectie, sim/switchTab/sim7-JS, `__ds`-hooks)

**Interfaces:**
- Consumes: `DATA.dsokb`-vorm uit Taak 2 (velden daar exact).
- Produces: `sim7` (4 stappen), `switchTab(7)`, `__ds.get sim7`, `__ds.dsokbData()`; DOM-id's met prefix `kb7-` + `rail7`, `st7-*`, `log7`, `oplabel7`, `kb7-done`.

- [ ] **Step 1: Tabregel.** ná de tab6-div (regel met `id="tab6"`):

```html
    <div class="tab" id="tab7" onclick="switchTab(7)">DSO ↔ RegelRecht</div>
```

- [ ] **Step 2: Kop.** ná het `kop6`-blok (de div met `id="kop6"` inclusief zijn afsluitende `</div>`). De kop-structuur is `tabkop` > `div.nl` + `div.en` (zoals kop1/kop6, template-regels 470–481):

```html
  <div class="tabkop" id="kop7">
    <div class="nl">
      <div class="tabkop-titel">DSO ↔ RegelRecht — kennisbank versus formele toets</div>
      <div class="tabkop-tekst">Drie lagen, niet door elkaar: <b>DSO annoteert</b> (welke regels horen bij deze plek?) ·
        <b>RegelRecht toetst</b> (alleen de geformaliseerde subset is uitvoerbaar — de rest is onthouding) ·
        <b>AI verkent</b>. Elk getal komt uit de kennisbank-artefacten (<code>dso_overlap/out/</code>); geen LLM in de beslislijn.</div>
    </div>
    <div class="en">
      <div class="tabkop-titel">DSO ↔ RegelRecht — knowledge base versus formal test</div>
      <div class="tabkop-tekst">Three layers, never mixed: <b>DSO annotates</b> · <b>RegelRecht tests</b> (only the formalized subset executes — the rest abstains) · <b>AI explores</b>. Every number is read from the cache artifacts; no LLM in the decision line.</div>
    </div>
  </div>
```

- [ ] **Step 3: View-sectie.** ná `</section>` van view6:

```html
<section class="view" id="view7">
  <aside class="rail card" id="rail7"></aside>
  <div class="stagepane">
    <div class="card" style="padding:10px 14px">
      <h3 id="kb7-titel">DSO annoteert · RegelRecht toetst · AI verkent</h3>
      <div class="oplabel" id="oplabel7">kennisbank — klaar.</div>
    </div>
    <div class="card" id="kb7-eindhoven"></div>
    <div class="card" id="kb7-utrecht"></div>
    <div class="card" id="kb7-driftcard"></div>
    <div class="card"><h3>run log</h3>
      <div class="logkop" id="logkop7"></div>
      <div class="log" id="log7"></div>
    </div>
  </div>
</section>
```

- [ ] **Step 4: JS-kern.** Breid eerst de declaraties exact aan:

4a. `let sim1, sim2, sim4, sim5, sim6, active=1;` → `let sim1, sim2, sim4, sim5, sim6, sim7, active=1;`

4b. `const sim = ()=> active===1?sim1:active===4?sim4:active===5?sim5:active===6?sim6:sim2;` →
`const sim = ()=> active===1?sim1:active===4?sim4:active===5?sim5:active===6?sim6:active===7?sim7:sim2;`

4c. In `switchTab`: de lus `for(const k of [1,2,4,5,6])` → `for(const k of [1,2,4,5,6,7])`.

4d. Nieuw scriptblok (plaats ná het Gent-blok / vóór de `__ds`-definitie; alles achter de guard):

```js
/* ================================================================ DSO-KB view (tab 7) */
const DKB = (typeof DATA!=="undefined" && DATA.dsokb) || null;
const VSTAGES7 = [["DSO annoteert","annotaties.json"],["koppeling","overlap.json"],
                  ["RegelRecht toetst","toets.json"],["verversen & drift","ververs.json"]];
const KB_KLEUR = {formalized:"#22c55e", unmatched:"#f59e0b", missing_in_report:"#94a3b8",
                  ambiguous:"#eab308", rejected:"#ef4444"};
const log7=(html,klasse="ok")=>{ const l=$("log7"); if(!l) return;
  l.insertAdjacentHTML("beforeend",`<div class="lr ${klasse}">${html}</div>`); l.scrollTop=l.scrollHeight; };

function kb7StatusBalk(sc){
  const tot=Object.values(sc).reduce((a,b)=>a+b,0)||1;
  const seg=Object.entries(sc).map(([k,v])=>
    `<div style="flex:0 0 ${(100*v/tot).toFixed(2)}%;background:${KB_KLEUR[k]||"#64748b"}" title="${esc(k)} ${esc(String(v))}"></div>`).join("");
  const leg=Object.entries(sc).map(([k,v])=>
    `<span style="white-space:nowrap"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${KB_KLEUR[k]||"#64748b"}"></span> ${esc(k)} ${esc(String(v))}</span>`).join(" · ");
  return `<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;background:#1e293b">${seg}</div>
          <div style="font-size:10.5px;color:var(--faint,#94a3b8);margin-top:4px">${leg}</div>`;
}

function kb7InstCard(inst){
  const d=inst.dekking, c=inst.counts, t=inst.toets||{};
  const geo=inst.geo||{};
  const geolijst=[]; if(geo.getoetst!=null) geolijst.push(`punt-in-GIO ${geo.getoetst}/${geo.getoetst} overeenstemming`);
  if(geo.naamOvereenkomend!=null) geolijst.push(`naamafstemming ${geo.naamOvereenkomend}/${geo.naamOvereenkomend}`);
  const pct=(100*d.coverage).toFixed(2).replace(".",",");
  return `<h3>${esc(inst.label)} <span style="color:var(--faint,#94a3b8);font-size:11px">${esc(inst.cvdr)} · locatie ${esc(inst.locatieLabel)} (RD ${esc(String(inst.punt[0]))}, ${esc(String(inst.punt[1]))})</span></h3>
    <div style="display:flex;gap:18px;flex-wrap:wrap;align-items:baseline">
      <div><div class="kb7-big" id="kb7-cov-${esc(inst.id)}">0</div><div style="font-size:10.5px;color:var(--faint)">uitvoerbaar (van ${esc(String(d.dsoArtikelen))} DSO-artikelen)</div></div>
      <div style="font-size:12.5px;line-height:1.55">
        <b>${esc(String(d.executable))}</b> uitvoerbaar · <b>${esc(String(d.abstain))}</b> onthouding<br>
        regelteksten ${esc(String(c.regelteksten))} · activiteiten ${esc(String(c.activiteiten))} ·
        locaties ${esc(String(c.locaties))} · gebiedsaanwijzingen ${esc(String(c.gebiedsaanwijzingen))}<br>
        toets: ${Object.entries(t).filter(([k])=>k!=="formalizedInHit"&&k!=="artikelen").map(([k,v])=>`${esc(k)} ${esc(String(v))}`).join(" · ")||"—"}
        ${geolijst.length?("<br>"+geolijst.map(g=>`✓ ${esc(g)}`).join(" · ")):""}
      </div>
    </div>
    <div id="kb7-balk-${esc(inst.id)}" style="margin-top:8px"></div>
    <div style="font-size:10px;color:var(--faint,#94a3b8);font-family:var(--mono,monospace);margin-top:6px">
      annotaties sha256:${esc(inst.annotatiesSha16)} · fetched ${esc(inst.fetchedAt||"?")}</div>`;
}

function buildStatic7(){
  if(!DKB) return;
  for(const inst of DKB.instrumenten){
    $("kb7-"+inst.id).innerHTML=kb7InstCard(inst);
  }
  const v=DKB.instrumenten.find(i=>i.ververs);
  $("kb7-driftcard").innerHTML = v ? kb7DriftCard(v) : `
    <h3>verversen &amp; drift</h3>
    <div style="font-size:12.5px;color:var(--faint,#94a3b8)">Nog geen ververs-rapport in de cache
    (<code>*.ververs.json</code>) — draai <code>dso_kb.ververs()</code> of de refresh-tool één keer;
    de kaart toont daarna de canonieke drift-uitslag.</div>`;
}

function kb7DriftCard(inst){
  const v=inst.ververs, d=v.drift||{};
  const geen=d.inhoudelijkeDrift==="geen";
  return `<h3>verversen &amp; drift — ${esc(inst.id)}</h3>
    <div style="display:flex;gap:18px;align-items:baseline;flex-wrap:wrap">
      <div><div class="kb7-big" style="color:${geen?"#22c55e":"#f59e0b"}" id="kb7-done">${geen?"geen":"wel"}</div>
        <div style="font-size:10.5px;color:var(--faint)">inhoudelijke drift</div></div>
      <div style="font-size:12.5px;line-height:1.55">
        verversd ${esc(v.gegenereerdOp||"?")}<br>
        annotaties sha256 <code>${esc(v.annShaOud||"?")}</code> → <code>${esc(v.annShaNieuw||"?")}</code><br>
        byte-verschil ≠ inhoudelijke drift: de API echoot aanvraagdatums
        (<code>geldigOp</code>/<code>inWerkingOp</code>/<code>beschikbaarOp</code>) en wisselt lijstvolgorde —
        de canonieke vergelijking sorteert en stript die vóór het oordeel.
      </div>
    </div>`;
}

function buildRail7(){ $("rail7").innerHTML = VSTAGES7.map((s,i)=>
  `<div class="stage" id="st7-${i}" onclick="sim7.jumpToStage(${i})">
     <div class="num">${i+1}</div><div><div class="sname">${s[0]}</div><div class="sartifact">${s[1]}</div></div>
   </div>`).join(""); }
function stageCls7(i){ for(let k=0;k<VSTAGES7.length;k++){ const s=$("st7-"+k); if(!s) continue;
  s.classList.toggle("active",k===i); s.classList.toggle("done",k<i); } }

function makeSim7(){
  const [EH,UT]=DKB.instrumenten;
  const steps=[]; const S=(stage,t,dur,run)=>steps.push({stage,t,dur,run});

  S(0,"DSO annoteert",1600,()=>{
    for(const inst of [EH,UT]){
      const el=$("kb7-cov-"+inst.id); if(el) animNum(el,100*inst.dekking.coverage,1200,x=>x.toFixed(2).replace(".",",")+"%");
    }
    $("oplabel7").innerHTML=`DSO Presenteren — punt-annotaties op de fixture-locaties (${esc(EH.locatieLabel)} · ${esc(UT.locatieLabel)})`;
    log7(`<b>DSO</b> — annoteert: welke regelteksten, activiteiten en gebieden horen bij dit punt? Eindhoven: ${EH.counts.regelteksten} regelteksten · ${EH.counts.activiteiten} activiteiten · ${EH.counts.locaties} locaties. Utrecht: ${UT.counts.regelteksten} · ${UT.counts.activiteiten} · ${UT.counts.locaties}.`,"ok");
    log7(`<b>DSO</b> — dit is deterministische retrieval, géén uitvoeringsbesluit: de annotatie zegt wélk artikel hier werkt, niet wat er mag.`,"data");
  });

  S(1,"koppeling",1800,()=>{
    for(const inst of [EH,UT]){ const b=$("kb7-balk-"+inst.id); if(b) b.innerHTML=kb7StatusBalk(inst.statusCounts); }
    $("oplabel7").innerHTML=`koppeling — DSO-artikelen ↔ formalization-report (artikelnummer-join)`;
    log7(`<b>koppeling</b> — Eindhoven: ${EH.dekking.dsoArtikelen} DSO-artikelen → <b>${EH.dekking.executable} uitvoerbaar</b> (${(100*EH.dekking.coverage).toFixed(2).replace(".",",")}%) · ${EH.dekking.abstain} onthouding.`,"ok");
    log7(`<b>koppeling</b> — Utrecht: ${UT.dekking.dsoArtikelen} → <b>${UT.dekking.executable}</b> (${(100*UT.dekking.coverage).toFixed(2).replace(".",",")}%). Een verordening bevat vooral instructieregels — structureel slechter formaliseerbaar dan een omgevingsplan; onthouding is eerlijk, geen falen.`,"data");
    const vb=EH.voorbeelden.slice(0,3).map(v=>`art. ${esc(v.artikel)} (${esc(v.status)}${v.reden?": "+esc(v.reden):""})`).join(" · ");
    if(vb) log7(`<b>koppeling</b> — onthoudingsvoorbeelden Eindhoven: ${vb}.`,"warn");
  });

  S(2,"RegelRecht toetst",1900,()=>{
    $("oplabel7").innerHTML=`RegelRecht-punttoets — feit / afwezigheid / scenario / onthouding per execution-input`;
    const t=EH.toets||{};
    log7(`<b>RegelRecht</b> — punttoets Eindhoven: ${t.scenario??0} scenario-uitkomsten · ${t.onthouding??0} onthouding · ${t.engineFout??0} enginefouten (nooit gissen).`,"ok");
    log7(`<b>RegelRecht</b> — Utrecht: ${ (UT.toets||{}).getoetst??0 } getoetst, 0 onthouding.`,"data");
    log7(`<b>kruisvalidatie</b> — de DSO-puntselectie tegen de échte GIO-geometrie uit het uitwisselpakket: Eindhoven ${EH.geo.getoetst}/${EH.geo.getoetst} locaties in overeenstemming · Utrecht geometrie-sweep + naamafstemming ${UT.geo.naamOvereenkomend}/${UT.geo.naamOvereenkomend}.`,"ok");
  });

  S(3,"verversen & drift",2000,()=>{
    const v=DKB.instrumenten.find(i=>i.ververs);
    $("oplabel7").innerHTML=`verversen — live PRE-refresh met canonieke drift-uitslag`;
    if(v){ log7(`<b>drift</b> — laatste verversing ${esc(v.ververs.gegenereerdOp)}: byte-sha's veranderden, canoniek oordeel: <b>${esc(v.ververs.drift.inhoudelijkeDrift)}</b>.`,"ok"); }
    else { log7(`<b>drift</b> — nog geen ververs-rapport in de cache; zie de drift-kaart.`,"warn"); }
    log7(`<b>doctrine</b> — DSO annoteert · RegelRecht toetst · AI verkent — geen LLM in de beslislijn.`,"data");
  });

  return new Sim(steps, { reset: buildStatic7,
    stage:(st, idx)=>{ stageCls7(idx); } });
}
```

4e. Nog één regel CSS (in het bestaande `<style>`-blok, bij de andere component-stijlen):

```css
.kb7-big{font-size:30px;font-weight:700;line-height:1.05}
```

- [ ] **Step 5: Initialisatie + `__ds`.**

5a. Bij de initialisatieregels (`buildRail6(); buildStatic6(); … sim6=makeSim6(); sim6.prog();`) er direct ná:

```js
if(DKB){ buildRail7(); buildStatic7(); sim7=makeSim7(); sim7.prog(); }
```

5b. In het `globalThis.__ds={…}`-object, ná de `get sim6()`-regel:

```js
  get sim7(){return sim7;}, get dsokbData(){return ()=>DKB;},
```

- [ ] **Step 6: Build + snelle handcheck**

Run: `python3 simulation/build_simulation.py 2>&1 | grep -E 'dsokb|wrote' && node simulation/verify_static.mjs 2>&1 | tail -3`
Expected: build OK; verify groen (bestaande blokken — tab 7 wordt pas in Taak 4 geasserteerd, maar de pagina mag niet breken: geen nieuwe fouten in de output).

- [ ] **Step 7: Commit**

```bash
git add simulation/template.html
git commit -m "feat(simulation): tab 7 DSO ↔ RegelRecht — vier stappen, statusCounts-balken, toets- en driftkaart uit DATA.dsokb (taak 3)"
```

---

### Task 4: verify-blok, ververs-rapport vullen, eindcontrole

**Files:**
- Modify: `simulation/verify_static.mjs` (nieuw blok + slotlog)
- Geen productiewijzigingen verder; éénmalige live `ververs()`-run (netwerk, keys uit `.env`) vult `*.ververs.json`.

**Interfaces:**
- Consumes: `__ds.sim7`, `__ds.dsokbData()` (Taak 3); `ververs.json` (Taak 1).

- [ ] **Step 1: Verify-blok.** ná het Veenendaal-blok (na de `s6`-controles, vóór de slot-`console.log`):

```js
  // ---- DSO-KB tab 7: coverage + toets + drift ----------------------------
  ds.switchTab(7);
  const s7 = ds.sim7;
  if (!s7 || s7.steps.length !== 4) throw new Error("sim7 verwacht 4 stappen (kreeg: " + (s7 ? s7.steps.length : "none") + ")");
  s7.jumpToStage(3); drain();
  const kb = ds.dsokbData();
  if (!kb || kb.instrumenten.length !== 2) throw new Error("dsokbData verwacht 2 instrumenten");
  const eh7 = kb.instrumenten.find(i => i.id === "eindhoven");
  const ut7 = kb.instrumenten.find(i => i.id === "utrecht");
  if (eh7.dekking.coverage !== 0.5635) throw new Error("eindhoven coverage verwacht 0.5635, kreeg " + eh7.dekking.coverage);
  if (eh7.dekking.executable !== 457 || eh7.dekking.dsoArtikelen !== 811) throw new Error("eindhoven 811/457 verwacht");
  if (ut7.dekking.coverage !== 0.0654) throw new Error("utrecht coverage verwacht 0.0654, kreeg " + ut7.dekking.coverage);
  if (ut7.dekking.executable !== 7) throw new Error("utrecht executable verwacht 7");
  if (eh7.geo.getoetst !== 34 || eh7.geo.overeenstemming !== 34) throw new Error("eindhoven geo verwacht 34/34");
  if (ut7.geo.naamOvereenkomend !== 8) throw new Error("utrecht naamafstemming verwacht 8");
  if (eh7.ververs && eh7.ververs.drift.inhoudelijkeDrift !== "geen")
    throw new Error("eindhoven drift verwacht 'geen', kreeg " + eh7.ververs.drift.inhoudelijkeDrift);
  if (!globalThis.document.getElementById("kb7-cov-eindhoven").textContent.includes("56,35"))
    throw new Error("kb7-cov-eindhoven mist gouden 56,35%");
```

En de slot-`console.log` (regel die met `` `OK — script evaluated…`` begint) uitbreiden: vóór de sluitende backtick ``, sim7 ${s7.steps.length} stappen (dekking ${eh7.dekking.coverage})`` toevoegen.

- [ ] **Step 2: Ververs-rapporten vullen (live, netwerk)**

```bash
nldt/.venv/bin/python -c "from services import dso_kb; import json; print(json.dumps(dso_kb.ververs('eindhoven'), ensure_ascii=False)[:200])"
nldt/.venv/bin/python -c "from services import dso_kb; import json; print(json.dumps(dso_kb.ververs('utrecht'), ensure_ascii=False)[:200])"
```

Expected: beide printen JSON met `"inhoudelijkeDrift": "geen"` (of de actuele uitslag — bij `"wel"`: rapporteren, niet doorpatchen). Mislukt netwerk/keys: rapporteren; de drift-assert in verify is guard-on-`ververs` en de tab valt terug op de cache-kaart.

- [ ] **Step 3: Volledige cyclus**

```bash
python3 simulation/build_simulation.py && node simulation/verify_static.mjs
```

Expected: build print nu `drift: geen`; verify eindigt met de OK-regel inclusief `sim7 4 stappen`.

- [ ] **Step 4: Regressie**

```bash
python3 simulation/build_simulation.py --gent-only && node simulation/verify_gent_only.mjs && nldt/.venv/bin/python -m pytest nldt/tests/test_dso_kb.py nldt/tests/test_dso_processes.py nldt/tests/test_dso_mcp.py -q
```

Expected: gent-only groen; 44 DSO-tests groen (27+13+4).

- [ ] **Step 5: Commit**

```bash
git add simulation/verify_static.mjs
git commit -m "test(simulation): verify-blok tab 7 — gouden dekking/toets/geo-getallen en drift-'geen' via __ds (taak 4)"
```

---

## Zelfreview (uitgevoerd bij opstellen)

1. **Specdekking**: §3.1 datablok → Taak 2 (velden 1:1); §3.2 tab/stappen → Taak 3 (vier `S()`-stappen, kop-doctrine, geen kaartlaag); §3.3 persistentie → Taak 1; §3.4 verify → Taak 4 (gouden getallen incl. guard); §4 foutafhandeling → `sys.exit` in build; §5 testen → per taak.
2. **Placeholders**: geen — de kop-structuurnoot is ingetrokken tot een vaststaand feit (nl/en-divs geverifieerd op template-regels 470–481); alle codestappen bevatten letterlijk te plakken code.
3. **Typeconsistentie**: `dekking.coverage` (float) doorloophoudend in build → JS → verify; `geo.getoetst/overeenstemming/naamOvereenkomend` alleen waar aanwezig (Utrecht géén getoetst-veld — verify assert alleen naamOvereenkomend); DOM-id's `kb7-*` komen in Taak 3 en 4 overeen; `DATA.dsokb`-guard houdt `--gent-only` heel.
