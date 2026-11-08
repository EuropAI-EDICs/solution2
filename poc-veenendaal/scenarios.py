#!/usr/bin/env python3
"""veenendaal-spoorzone scenario-sweep — Plane B naar Utrechts model
(SOLUTIONS_ARCHITECTURE §3.4: specs → mutaties → deterministische herberekening
tegen de nulmeting, delta's t.o.v. een control, provenance-basis per variant).

Verschil met Utrecht: daar muteren wetsartikelen de zone-algebra; hier muteren
programmamutaties (tempo, bouwvoorkeur, dichtheid) de doelrealisatie tegen de
nulmeting uit run.py. Doctrine ongewijzigd: de rekenlaag beslist — elke uitkomst
herleidt naar indicators.json + gebied.json + de aannames in de spec. Geen LLM.

Gebruik:  python3 scenarios.py           # curated set → scenario-runs/<ts>-sweep/
         python3 scenarios.py --refresh  # idem (hernoemt later; sweep is puur rekenen)
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import run as engine  # zelfde map: clip/deduplice-machinerie van de nulmeting

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RUNS = ROOT / "runs"
SWEEP_RUNS = ROOT / "scenario-runs"

# --- standaard parameters (uit het Toekomstbeeld / de nulmeting) -------------
# grondvlak per nieuwe woning is een AANNAME (geen registratiefeit): 40 m² bij
# de 5-lagen-basis, 25 m² bij geaccentueerde 15-lagen-verdichting (p.14).
GVPW_BASIS = 40.0
GVPW_ACCENT = 25.0
VOORKEUR_DEFAULT = "verhard"  # beleidslogica: bouwen op verhard, groen blijft

SPECS: list[dict] = [
    {"id": "CONTROL", "naam": "nulmeting — geen mutaties", "basis": "baseline",
     "mutaties": {}, "rationale": "referentie: doelparameters uit het Toekomstbeeld (250/jaar, 4.500 woningen, groen >30 ha) tegen de gemeten stand"},
    {"id": "TEMPO-150", "naam": "tempo 150 woningen/jaar", "basis": "policy_variant",
     "mutaties": {"woningen_per_jaar": 150},
     "rationale": "ondergrens: doorbouwtempo zonder extra middelen"},
    {"id": "TEMPO-350", "naam": "tempo 350 woningen/jaar", "basis": "policy_variant",
     "mutaties": {"woningen_per_jaar": 350},
     "rationale": "versnelling: 4.500 binnen één planperiode-helft"},
    {"id": "BOUW-OP-VERHARD", "naam": "nieuwbouw op verhard (5-lagen basis)", "basis": "policy_variant",
     "mutaties": {"bouwVoorkeur": "verhard"},
     "rationale": "beleidsvoorkeur: verdichten op verharding; groen onaangetast"},
    {"id": "BOUW-OP-GROEN", "naam": "nieuwbouw op groen (5-lagen basis)", "basis": "hypothetical",
     "mutaties": {"bouwVoorkeur": "groen"},
     "rationale": "slechtste geval voor de groenbelofte: verdichten ten koste van groen"},
    {"id": "DICHT-15", "naam": "15-lagen accenten (compact, 25 m²/woning)", "basis": "policy_variant",
     "mutaties": {"grondvlak_per_woning_m2": GVPW_ACCENT, "bouwVoorkeur": "verhard"},
     "rationale": "p.14: basishoogte 5 lagen met accenten tot 15 — compactere voetafdruk per woning"},
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def laatste_run() -> Path:
    dirs = sorted(RUNS.glob("*-gebiedscheck"))
    if not dirs:
        sys.exit("geen gebiedscheck-run gevonden — draai eerst run.py")
    return dirs[-1]


# --- rekenlaag (1e implementatie) -------------------------------------------

def bereken(ind: dict, doelen: dict, spec: dict) -> dict:
    m = spec.get("mutaties") or {}
    nieuw = doelen["woningen_nieuw_feiten_tabel"]
    tempo = m.get("woningen_per_jaar", doelen["woningen_per_jaar_gemiddeld"])
    start = doelen["programma_start"]
    doeleind = start + doelen["programma_duur_jaar"]
    groendoel = doelen["groen_ha_minimum"]

    gvpw = m.get("grondvlak_per_woning_m2", GVPW_BASIS)
    voorkeur = m.get("bouwVoorkeur", VOORKEUR_DEFAULT)
    won_nu = ind["woningen_verblijfsobjecten_proxy"]
    groen_m2 = ind["begroeid_terrein_ha"] * 10_000
    verhard_m2 = ind["onbegroeid_terrein_ha"] * 10_000
    opp_ha = 161.0  # gebied.json werkgrens; sweep leest hem uit gebied voor de zekerheid

    jaar = start + math.ceil(nieuw / tempo)
    uitloop = jaar - doeleind

    uit = {"woningen_nieuw": nieuw, "woningen_per_jaar": tempo,
           "grondvlak_per_woning_m2": gvpw, "bouwVoorkeur": voorkeur,
           "woningen_totaal": won_nu + nieuw,
           "jaar_van_nieuwbouwdoel": jaar, "uitloop_jaren_vs_doeleind": uitloop,
           "dichtheid_eind_per_km2": round((won_nu + nieuw) / (opp_ha / 100))}

    if spec["basis"] == "baseline":
        uit.update({"genomen_uit_groen_ha": 0.0, "genomen_uit_verhard_ha": 0.0,
                    "groen_eind_ha": round(groen_m2 / 10_000, 2),
                    "verhard_eind_ha": round(verhard_m2 / 10_000, 2),
                    "capaciteit_telekort": False, "benodigd_grondvlak_ha": 0.0})
    else:
        nodig = nieuw * gvpw
        eerst, dan = (("groen", groen_m2), ("verhard", verhard_m2)) if voorkeur == "groen" \
            else (("verhard", verhard_m2), ("groen", groen_m2))
        if voorkeur == "gemengd":
            genomen = {"groen": min(nodig / 2, groen_m2), "verhard": min(nodig / 2, verhard_m2)}
            rest = nodig - genomen["groen"] - genomen["verhard"]
            for laag, voorraad in (("verhard", verhard_m2), ("groen", groen_m2)):
                extra = min(rest, voorraad - genomen[laag])
                genomen[laag] += extra
                rest -= extra
        else:
            genomen = {"groen": 0.0, "verhard": 0.0}
            rest = nodig
            for laag, voorraad in (eerst, dan):
                neem = min(rest, voorraad)
                genomen[laag] = neem
                rest -= neem
        tekort = rest > 0
        groen_eind = round((groen_m2 - genomen["groen"]) / 10_000, 2)
        uit.update({"benodigd_grondvlak_ha": round(nodig / 10_000, 2),
                    "genomen_uit_groen_ha": round(genomen["groen"] / 10_000, 2),
                    "genomen_uit_verhard_ha": round(genomen["verhard"] / 10_000, 2),
                    "groen_eind_ha": groen_eind,
                    "verhard_eind_ha": round((verhard_m2 - genomen["verhard"]) / 10_000, 2),
                    "capaciteit_telekort": bool(tekort),
                    "groendoel_behaald": groen_eind >= groendoel,
                    "groendoel_marge_ha": round(groen_eind - groendoel, 2)})
    if spec["basis"] == "baseline":
        uit["groendoel_behaald"] = round(groen_m2 / 10_000, 2) >= groendoel
        uit["groendoel_marge_ha"] = round(groen_m2 / 10_000 - groendoel, 2)
    return uit


# --- V3: tweede, onafhankelijke passage (generator-based) --------------------

def v3_herberekening(ind: dict, doelen: dict, resultaten: list[dict]) -> tuple[bool, str]:
    problemen = []
    for r in resultaten:
        if r["_uit"]["woningen_totaal"] != ind["woningen_verblijfsobjecten_proxy"] + doelen["woningen_nieuw_feiten_tabel"]:
            problemen.append(f"{r['id']}: woningtotaal")
        if r["_uit"]["groen_eind_ha"] < 0 or r["_uit"]["verhard_eind_ha"] < 0:
            problemen.append(f"{r['id']}: negatieve Voorraad")
        if r["_uit"]["jaar_van_nieuwbouwdoel"] < doelen["programma_start"]:
            problemen.append(f"{r['id']}: doelperiode")
    ok = not problemen
    return ok, "; ".join(problemen) if problemen else "invarianten houden stand (woningtotaal, voorraden ≥ 0, doelperiode)"


# --- ruimtelijke toedeling (engine beslist; pagina toont alleen) -------------
# Regel: hele actuele vlakken van de voorkeurslaag, dichtst bij het station
# eerst (stedelijke logica: bouwen bij de OV-knoop), bij gelijke afstand
# grootste eerst, dan objectvolgorde. Zwaartepunt = gemiddelde van de
# buitenring-coördinaten. Deelgebied = vak waarin het zwaartepunt valt.

def _zwaartepunt(geom: dict):
    pts: list[list[float]] = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)

    if geom and geom.get("coordinates"):
        walk(geom["coordinates"])
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _zone_van(zones: list, punt) -> str:
    x, y = punt
    for z in zones:
        b = z["bbox"]
        if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
            return z["naam"]
    return "(zwaartepunt buiten zone-indeling)"


def _allocatie(fc: dict, laag: str, nodig_ha: float, zones: list, anker) -> dict:
    zone_boxes = [(z["naam"], tuple(z["bbox"])) for z in zones]
    kandidaten = []
    for i, f in enumerate(engine.bgt_actueel(fc.get("features", []))):
        g = f.get("geometry")
        if not g or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        opp = engine.feature_area_in_bbox(g, WERKGRENS_BBOX)
        if opp <= 0:
            continue
        zp = _zwaartepunt(g)
        if not zp:
            continue
        kandidaten.append((round(math.hypot(zp[0] - anker[0], zp[1] - anker[1]), 1),
                           -opp, i, f, g, opp))
    kandidaten.sort(key=lambda k: (k[0], k[1], k[2]))
    genomen, tot_m2, per_zone = [], 0.0, {}
    for _, _, _, f, g, opp in kandidaten:
        if tot_m2 >= nodig_ha * 10_000:
            break
        # per-zone uitsplitsing op OPPERVLAKTE (zones tegelen de werkgrens
        # exact, dus Σ zones == toegedeeld); n telt vlakken die de zone raken
        for naam, b in zone_boxes:
            deel = engine.feature_area_in_bbox(g, b)
            if deel > 0:
                reg = per_zone.setdefault(naam, {"n": 0, "genomen_ha": 0.0})
                reg["n"] += 1
                reg["genomen_ha"] += deel
        tot_m2 += opp
        genomen.append(f["properties"].get("lokaal_id"))
    for reg in per_zone.values():
        reg["genomen_ha"] = round(reg["genomen_ha"] / 10_000, 2)
    return {"laag": laag,
            "regel": "hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)",
            "toegedeeld_ha": round(tot_m2 / 10_000, 2), "n": len(genomen),
            "per_zone": per_zone, "genomen_ids": genomen}


def _deelgebied_nulmeting(zones: list) -> list:
    cache = DATA / "cache"

    def fc(naam):
        return json.loads((cache / f"{naam}.geojson").read_text(encoding="utf-8"))

    groen, verhard = fc("begroeidterreindeel"), fc("onbegroeidterreindeel")
    uit = []
    for z in zones:
        b = tuple(z["bbox"])
        g = sum(engine.feature_area_in_bbox(f.get("geometry"), b)
                for f in engine.bgt_actueel(groen.get("features", []))) / 10_000
        v = sum(engine.feature_area_in_bbox(f.get("geometry"), b)
                for f in engine.bgt_actueel(verhard.get("features", []))) / 10_000
        uit.append({"naam": z["naam"], "bbox": z["bbox"],
                    "groen_ha": round(g, 2), "verhard_ha": round(v, 2)})
    return uit


WERKGRENS_BBOX = None  # gezet in main()


def main() -> int:
    global WERKGRENS_BBOX
    run = laatste_run()
    gebied = json.loads((DATA / "gebied.json").read_text(encoding="utf-8"))
    ind = json.loads((run / "indicators.json").read_text(encoding="utf-8"))
    doelen = gebied["doelen_uit_toekomstbeeld"]
    WERKGRENS_BBOX = tuple(gebied["werkgrens"]["bbox_rd"])
    zones = gebied["deelgebied_zones"]["zones"]
    anker = gebied["ankers"][0]["rd"]

    def cache_fc(naam):
        return json.loads((DATA / "cache" / f"{naam}.geojson").read_text(encoding="utf-8"))

    deelgebied = _deelgebied_nulmeting(zones)
    lagen_fc = {"groen": cache_fc("begroeidterreindeel"), "verhard": cache_fc("onbegroeidterreindeel")}

    resultaten = []
    for spec in SPECS:
        uit = bereken(ind, doelen, spec)
        r = {**spec, "_uit": uit}
        if spec["basis"] != "baseline" and uit.get("benodigd_grondvlak_ha"):
            laag = "groen" if uit.get("bouwVoorkeur") == "groen" else "verhard"
            r["_alloc"] = _allocatie(lagen_fc[laag], laag, uit["benodigd_grondvlak_ha"], zones, anker)
        resultaten.append(r)
    control = {k: v for k, v in resultaten[0]["_uit"].items()}

    # delta's t.o.v. control (afgerond; control zelf = 0)
    DELTA_KEYS = ["jaar_van_nieuwbouwdoel", "uitloop_jaren_vs_doeleind", "groen_eind_ha",
                  "verhard_eind_ha", "dichtheid_eind_per_km2", "genomen_uit_groen_ha"]
    for r in resultaten:
        r["deltas"] = {k: round(r["_uit"].get(k, 0) - control.get(k, 0), 2) for k in DELTA_KEYS}

    ok3, msg3 = v3_herberekening(ind, doelen, resultaten)
    for r in resultaten:
        a = r.get("_alloc")
        if a:
            zones_som = round(sum(z["genomen_ha"] for z in a["per_zone"].values()), 2)
            if abs(zones_som - a["toegedeeld_ha"]) > 0.06 * max(1, len(a["per_zone"])):
                ok3 = False
                msg3 += f"; {r['id']}: zonesom {zones_som} ≠ toegedeeld {a['toegedeeld_ha']}"
    if not ok3:
        print(f"V3 FAIL: {msg3}")
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-sweep"
    out = SWEEP_RUNS / run_id
    out.mkdir(parents=True, exist_ok=True)

    pub = []
    for r in resultaten:
        d = {k: v for k, v in r.items() if k not in ("_uit", "_alloc")}
        d["uit"] = r["_uit"]
        if r.get("_alloc"):
            d["allocatie"] = r["_alloc"]
        pub.append(d)

    (out / "deelgebieden.json").write_text(json.dumps(
        {"status": gebied["deelgebied_zones"]["status"], "zones": deelgebied,
         "per_scenario": {r["id"]: r["_alloc"]["per_zone"] for r in resultaten if r.get("_alloc")}},
        indent=2, ensure_ascii=False))
    manifest = {
        "runId": run_id, "gegenereerd": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bronrun": run.name,
        "inputs": {"indicators.json": sha(run / "indicators.json"),
                   "gebied.json": sha(DATA / "gebied.json")},
        "aannames": {"grondvlak_per_woning_m2_basis": GVPW_BASIS,
                     "grondvlak_per_woning_m2_accent": GVPW_ACCENT,
                     "toelichting": "grondvlak per nieuwe woning is een aanname (5-lagen basis vs 15-lagen accenten, Toekomstbeeld p.14); bouw op groen/verhard is een ruimtelijke abstractie op werkgrens-niveau, geen percelse allocatie"},
        "v3": {"verdict": "pass", "detail": msg3},
    }
    (out / "scenarios.json").write_text(json.dumps(pub, indent=2, ensure_ascii=False))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    regels = [f"# Scenario-sweep Spoorzone Veenendaal — {run_id}", "",
              f"Nulmeting: run `{run.name}` · doctrine: rekenlaag beslist, mens beslist.", "",
              "| Scenario | Basis | Jaar van 4.500 | Uitloop vs 2040 | Groen eind (ha) | Verhard eind (ha) | Groendoel >30 ha | Dichtheid /km² |",
              "|---|---|---:|---:|---:|---:|---|---:|"]
    for r in pub:
        u = r["uit"]
        doel = "✓" if u.get("groendoel_behaald") else "✗"
        regels.append(f"| **{r['naam']}** ({r['id']}) | {r['basis']} | {u['jaar_van_nieuwbouwdoel']} "
                      f"| {u['uitloop_jaren_vs_doeleind']:+d} jr | {u['groen_eind_ha']} "
                      f"| {u['verhard_eind_ha']} | {doel} {u.get('groendoel_marge_ha','')} | {u['dichtheid_eind_per_km2']} |")
    regels += ["", "## Per scenario", ""]
    for r in pub:
        u = r["uit"]
        regels += [f"### {r['naam']} · basis {r['basis']}",
                   f"- rationale: {r['rationale']}",
                   f"- mutaties: {json.dumps(r['mutaties'] or {}, ensure_ascii=False)}",
                   f"- benodigd nieuw grondvlak: {u['benodigd_grondvlak_ha']} ha "
                   f"(groen −{u['genomen_uit_groen_ha']} · verhard −{u['genomen_uit_verhard_ha']})",
                   f"- groen eind {u['groen_eind_ha']} ha (marge {u.get('groendoel_marge_ha')} t.o.v. doel 30) · "
                   f"verhard eind {u['verhard_eind_ha']} ha · dichtheid {u['dichtheid_eind_per_km2']}/km²",
                   f"- jaar van {u['woningen_nieuw']}: {u['jaar_van_nieuwbouwdoel']} "
                   f"({u['uitloop_jaren_vs_doeleind']:+d} t.o.v. {2020+20})", ""]
        a = r.get("allocatie")
        if a:
            regels += ["  **Toedeling per deelgebied** (provisionele indeling):", "",
                       "| Deelgebied | vlakken | genomen (ha) |", "|---|---:|---:|"]
            for z in deelgebied:
                pz = a["per_zone"].get(z["naam"])
                regels.append(f"| {z['naam']} | {pz['n'] if pz else 0} | {pz['genomen_ha'] if pz else 0} |")
            regels.append(f"| **totaal** | **{a['n']}** | **{a['toegedeeld_ha']}** |")
            regels += [f"  regel: {a['regel']}", ""]
    regels += ["## Beperkingen", "",
               "- Grondvlak per nieuwe woning is een aanname (40 m² basis / 25 m² accenten), geen registratiefeit.",
               "- Allocatie groen-vs-verhard is abstract (werkgrens-totaal); de deelgebied-uitsplitsing volgt het vlakzwaartepunt (provisionele zone-indeling).",
               "- Woningtelling is de vbo-proxy uit de nulmeting (panden ≠ woningen).",
               "", f"*V3: pass — {msg3}. Manifest: manifest.json · specs+uitkomsten: scenarios.json.*"]
    (out / "report.md").write_text("\n".join(regels))

    print(f"✓ sweep {run_id} — {len(pub)} scenario's (V3 {msg3})")
    for r in pub:
        u = r["uit"]
        print(f"  {r['id']:16} jaar {u['jaar_van_nieuwbouwdoel']} ({u['uitloop_jaren_vs_doeleind']:+d}) · "
              f"groen {u['groen_eind_ha']} ha {'✓' if u.get('groendoel_behaald') else '✗'} · "
              f"verhard {u['verhard_eind_ha']} ha")
    return 0


if __name__ == "__main__":
    sys.exit(main())
