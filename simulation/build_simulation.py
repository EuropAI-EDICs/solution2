#!/usr/bin/env python3
"""Build simulation/simulation.html — an animated, step-through visualization of
both LDT-toolbox PoCs, grounded entirely in the real artifacts of their canonical
runs (no invented numbers).

  PoC-1  three tracks on the Omgevingsverordening provincie Utrecht:
         wind  poc/runs/20260830T113234Z-wind   (wind turbines)
         zon   poc/runs/20260830T142439Z-zon    (zonnevelden / solar fields)
         bos   poc/runs/20260830T142446Z-bos    (new nature / forest planting)
  PoC-2  poc-bp2op/runs/20260830-124515-eindhoven (bestemmingsplan -> omgevingsplan)

Usage:  python3 simulation/build_simulation.py
Output: simulation/simulation.html (single file, works from file://, no network)

Requires shapely (already in the verified toolchain) for display simplification
of the zone geometries; every displayed area number is the engine's own output,
never re-derived from the simplified display geometry.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import importlib.util

from vertaal_gent import VT_STATUS, vt

from shapely.geometry import shape, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent

DSO_OUT = ROOT / "nldt" / "simulation" / "regelrecht" / "dso_overlap" / "out"
DSO_INSTRUMENTEN = [
    ("eindhoven", "eindhoven-woensel-proxy", "Omgevingsplan gemeente Eindhoven", "CVDR696400"),
    ("utrecht", "utrecht-domplein", "Omgevingsverordening provincie Utrecht", "CVDR704250"),
]

# Labels delen met viewer/context_map — zonder poc/ op sys.path te zetten
# (dat zou poc-bp2op/pipeline.knowledgebank maskeren).
_sl = importlib.util.spec_from_file_location(
    "scenario_labels",
    ROOT / "poc" / "pipeline" / "scenario_labels.py",
)
_scenario_labels = importlib.util.module_from_spec(_sl)
assert _sl.loader is not None
_sl.loader.exec_module(_scenario_labels)
BASELINE_VERSCHIL = _scenario_labels.BASELINE_VERSCHIL
scenario_kleur = _scenario_labels.scenario_kleur
scenario_kort = _scenario_labels.scenario_kort
scenario_verschil = _scenario_labels.scenario_verschil
final_only_fc = _scenario_labels.final_only_fc

AOI_CACHE = ROOT / "poc" / "data" / "cache" / "arcgis-provinciegrens.4326.geojson"
UITDAGINGEN = ROOT / "poc" / "scenarios" / "uitdagingen.json"
SCENARIO_RUNS = ROOT / "poc" / "scenario-runs"
CORPUS = ROOT / "poc" / "corpus"
TEMPLATE = Path(__file__).resolve().parent / "template.html"
OUT = Path(__file__).resolve().parent / "simulation.html"

#: canonical run per PoC-1 track + display metadata (labels only — every number
#: in the page comes from the run artifacts themselves)
POC1_TRACKS = {
    "wind": {
        "run": ROOT / "poc" / "runs" / "20260830T113234Z-wind",
        "objectLabel": "wind turbines",
        "inclLabel": "inclusion zones (union)",
        "quoteEvidenceId": "W-08",
    },
    "zon": {
        "run": ROOT / "poc" / "runs" / "20260830T142439Z-zon",
        "objectLabel": "zonnevelden (solar fields)",
        "inclLabel": "Gebied zonneveld (art. 5.5)",
        "quoteEvidenceId": "Z-02",
    },
    "bos": {
        "run": ROOT / "poc" / "runs" / "20260830T142446Z-bos",
        "objectLabel": "nieuwe natuur & bosaanplant",
        "inclLabel": "Groene contour zoekgebied (art. 6.4)",
        "quoteEvidenceId": "B-01",
    },
}
POC2_RUN = ROOT / "poc-bp2op" / "runs" / "20260830-124515-eindhoven"
POC4_RUN = ROOT / "poc-breda" / "runs" / "20260913T192628Z-breda-scan"
BREDA_QA = Path(__file__).resolve().parent / "breda_qa.json"
LAYA_BREDA_EXPORT = Path(__file__).resolve().parent / "laya_breda" / "predictions.json"

# display-only simplification (the run itself used 2 m; the simulation coarse-tunes
# further purely for page weight — areas shown remain the engine's own numbers)
TOL_DEG = 0.0035          # ~250-300 m at Utrecht's latitude
MAX_POLYS = 70            # largest N components per zone
MIN_AREA_DEG2 = 6.0e-6    # ~0.05 km2 sliver cut


def display_rings(geom):
    """MultiPolygon -> [[ [lon,lat], ... ] per polygon exterior], display-simplified."""
    g = geom.simplify(TOL_DEG, preserve_topology=True)
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    polys = [p for p in polys if p.is_valid and p.area > MIN_AREA_DEG2]
    polys.sort(key=lambda p: p.area, reverse=True)
    out = []
    for p in polys[:MAX_POLYS]:
        ext = [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords]
        if len(ext) >= 4:
            out.append(ext)
    return out


def short(text: str, n: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_breda_qa(qa: list[dict], buurtnamen: set[str]) -> None:
    """Fail the build if a golden Q&A row references an unknown buurt."""
    for i, row in enumerate(qa):
        if not isinstance(row, dict):
            raise ValueError(f"breda_qa[{i}] must be an object")
        for key in ("id", "question", "answer"):
            if not row.get(key):
                raise ValueError(f"breda_qa[{i}] missing {key}")
        naam = row.get("buurtnaam")
        if naam and naam not in buurtnamen:
            raise ValueError(f"breda_qa[{i}] buurtnaam {naam!r} not in scan")


def _as_list(data, *keys: str) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if k in data and isinstance(data[k], list):
                return data[k]
    raise ValueError(f"expected list (or dict with keys {keys}), got {type(data).__name__}")


def _load_track_list(track: str, stem: str, run: Path, *keys: str) -> list:
    """Prefer RegelRecht-herijkte corpus; fall back to the frozen run artifact."""
    corp = CORPUS / f"{stem}-{track}.json"
    path = corp if corp.is_file() else run / f"{stem}.json"
    return _as_list(load(path), *keys)


def _rule_zone_ids(rule: dict) -> list[str]:
    """Zone ids from dual-write ``zoneSelector``, else ``zoneBinding.inputs``."""
    zs = (rule.get("zoneSelector") or {}).get("zoneIds") or []
    if zs:
        return list(zs)
    binding = (rule.get("zoneBinding") or {}).get("inputs") or {}
    out: list[str] = []
    for meta in binding.values():
        if isinstance(meta, dict):
            out.extend(meta.get("zoneIds") or [])
    return out


def _execution_summary(rule: dict) -> list[str]:
    """Tooltip lines for RegelRecht ``execution`` (SoT) + projected zone ids."""
    ex = rule.get("execution")
    if not isinstance(ex, dict):
        return [short(rule.get("reason") or rule.get("rationale") or "", 200)]
    produces = (ex.get("produces") or {}).get("legal_character") or "—"
    n_params = len(ex.get("parameters") or [])
    n_in = len(ex.get("input") or [])
    n_act = len(ex.get("actions") or [])
    lines = [
        f"RegelRecht execution (SoT) · {produces}",
        f"{n_params} parameters · {n_in} inputs · {n_act} actions",
    ]
    zids = _rule_zone_ids(rule)
    if zids:
        lines.append("zone projectie: " + ", ".join(zids[:4]) + ("…" if len(zids) > 4 else ""))
    else:
        lines.append("geen geo-zoneBinding (niet-ruimtelijke regel)")
    why = rule.get("reason") or rule.get("rationale") or ""
    if why:
        lines.append(short(why, 160))
    return lines


def _fc_display_rings(fc: dict) -> list:
    """FeatureCollection → display rings van alleen de final-kanszone.

    Scenario-GeoJSON bevat de hele keten; unie daarvan = hele provincie.
    Alleen ``final`` geeft de vlekken zoals in de scenario-run.
    """
    geoms = []
    for f in final_only_fc(fc).get("features") or []:
        g = f.get("geometry")
        if g:
            try:
                geoms.append(shape(g))
            except Exception:
                continue
    if not geoms:
        return []
    merged = unary_union(geoms) if len(geoms) > 1 else geoms[0]
    if merged.is_empty:
        return []
    return display_rings(merged)


def build_sweep(track: str) -> list[dict]:
    """Scenario-sweep voor een track: baseline + varianten met NL éénregel-verschil.

    Geometrie uit de canonieke scenario-run; labels uit scenario_labels
    (geen km² in de verklarende tekst).
    """
    uj = load(UITDAGINGEN)
    run_id = (uj.get("scenarioRuns") or {}).get(track)
    if not run_id:
        return []
    bron = SCENARIO_RUNS / run_id
    rapport_pad = bron / "scenario-report.json"
    if not rapport_pad.is_file():
        return []
    rapport = load(rapport_pad)
    out: list[dict] = []
    control = bron / "scenarios" / "CONTROL.geojson"
    if control.is_file():
        out.append({
            "id": "CONTROL",
            "label": "baseline (huidige regels)",
            "verschil": BASELINE_VERSCHIL,
            "color": "#5e5c64",
            "isBaseline": True,
            "geo": _fc_display_rings(load(control)),
        })
    for i, s in enumerate(rapport.get("scenarios") or []):
        geo_pad = bron / str(s.get("geometryFile") or "")
        if not geo_pad.is_file():
            continue
        delta = float(s.get("deltaVsControlKm2") or 0)
        out.append({
            "id": str(s.get("scenarioId") or geo_pad.stem),
            "label": scenario_kort(s),
            "verschil": scenario_verschil(s),
            "color": scenario_kleur(i, delta),
            "isBaseline": False,
            "geo": _fc_display_rings(load(geo_pad)),
        })
    return out


# ---------------------------------------------------------------- PoC-1 data
def _zone_class(zid: str) -> str:
    if zid.startswith("ZR-inclusion_union"):
        return "union"
    if zid.startswith("ZR-intersection"):
        return "intersection"
    if zid.startswith("ZR-final"):
        return "final"
    if zid.startswith("ZR-attention_mark"):
        return "attention"
    if zid.startswith("ZR-conditional_mark"):
        return "conditional"
    if zid.startswith("ZR-compensation_mark"):
        return "compensation"
    if zid.startswith("ZR-difference"):
        return "difference"
    raise ValueError(f"unclassified ZoneResult id {zid!r}")


_STEP_LABEL = {
    "union": "\u222a inclusion zone(s)",
    "intersection": "\u2229 area of interest",
    "difference": "\u2212 hard exclusion",
    "final": "= final opportunity zone",
}


def build_track(name: str, meta: dict) -> dict:
    run = meta["run"]
    summary = load(run / "run_summary.json")
    zones = load(run / "zones.json")
    zones = zones if isinstance(zones, list) else zones.get("zones", zones)
    # Corpus carries RegelRecht execution + dual-write zone fields (NDD v0.8.11);
    # zone geometries / validation stay on the frozen canonical run.
    formal = _load_track_list(name, "formalrules", run, "rules")
    rationale = {r["id"]: r.get("rationale") or r.get("reason") or "" for r in formal}
    rejected = load(run / "normcards-rejected.json")
    dtable = load(run / "decision-table.json")
    drows = dtable if isinstance(dtable, list) else dtable.get("rows", dtable)
    report_input = load(run / "report_input.json")
    validation = load(run / "validation.json")
    cards = _load_track_list(name, "normcards", run, "cards")
    layers_manifest = load(run / "layers.json")
    if not isinstance(layers_manifest, dict):
        layers_manifest = {}

    engine, markers = [], []
    zone_ids_by_rule = {r["id"]: _rule_zone_ids(r) for r in formal}

    def _human(zids):
        names = [z.replace("_", " ") for z in zids]
        if len(names) > 2:
            names = names[:2] + ["…"]
        return " + ".join(names)

    for z in zones:
        cls = _zone_class(z["id"])
        zids = sorted({zi for rid in z["ruleIds"] for zi in zone_ids_by_rule.get(rid, [])})
        if cls == "difference":
            label = f"− {_human(zids)}" if zids else "− hard exclusion"
        elif cls == "final":
            label = "= final opportunity zone"
        else:
            label = _STEP_LABEL.get(cls, cls)
        entry = {
            "key": cls + str(len(engine) + len(markers)),
            "kind": cls if cls != "difference" else "exclusion",
            "op": z["operation"],
            "label": label,
            "areaKm2": round(z["areaKm2"], 1),
            "ruleIds": z["ruleIds"],
            "zones": zids,
            "geo": display_rings(shape(z["geometry"]["payload"])),
            "note": short(rationale.get(z["ruleIds"][0], ""), 130) if z["ruleIds"] else "",
        }
        if cls in ("union", "intersection", "difference", "final"):
            engine.append(entry)
        else:
            entry["label"] = cls
            markers.append(entry)

    levels = {}
    for rep in validation:
        if rep.get("artifactType") == "pipeline-run":
            for lvl, info in rep["levels"].items():
                levels[lvl] = {
                    "status": info["status"],
                    "detail": "; ".join(c["detail"] for c in info.get("checks", [])[:2])[:120],
                }
    m = re.search(r"IoU ([0-9.]+)", summary.get("v3", ""))
    qcard = next(
        (c for c in cards if c["evidenceId"] == meta["quoteEvidenceId"]), cards[0]
    )

    return {
        "name": name,
        "objectLabel": meta["objectLabel"],
        "inclLabel": meta["inclLabel"],
        "runId": summary["runId"],
        "verdict": summary["verdict"],
        "durationS": summary["durationS"],
        "objectType": summary["useCase"],
        "headline": summary["headline"],
        "iou": m.group(1) if m else None,
        "v3": summary["v3"],
        "engine": engine,
        "markers": markers,
        "cards": {
            "normCards": len(cards),
            "abstentions": len(rejected["abstentions"]),
            "formalized": sum(1 for r in formal if r["status"] == "formalized"),
            "ambiguous": sum(1 for r in formal if r["status"] == "ambiguous"),
            "rejectedRules": sum(1 for r in formal if r["status"] == "rejected"),
            "withExecution": sum(
                1 for r in formal
                if r.get("status") == "formalized" and isinstance(r.get("execution"), dict)
            ),
        },
        "abstentions": [
            {"topic": a["topic"], "reason": short(a["reason"], 130)}
            for a in rejected["abstentions"]
        ],
        "layers": [
            {"id": l["id"], "lastChecked": l.get("lastChecked", "")}
            for l in report_input["layers"]
            if l["id"] not in ("derived", "national_source", "provincial_gio", "provincial_gio_unverified")
        ],
        "quote": {
            "article": qcard["source"]["article"],
            "number": qcard.get("number") or qcard["source"]["article"],
            "quote": short(qcard.get("text") or qcard["source"]["quote"], 220),
            "url": (
                qcard.get("url")
                or qcard["source"].get("url")
                or "https://lokaleregelgeving.overheid.nl/cvdr704250"
            ),
        },
        "decision": [
            {
                "ruleId": r["ruleId"],
                "effect": r["zone effect"],
                "criterion": short(r["criterion"], 95),
            }
            for r in drows
        ],
        "validationLevels": levels,
        "kg": build_kg1(cards, formal, zones, rejected, layers_manifest),
        "sweep": build_sweep(name),
    }


# -------------------------------------------------- Laya System-1 (PoC-1, Utrecht)
#: fine-tuned on the Utrecht zone chain — see simulation/laya_utrecht/
LAYA1_EXPORT = Path(__file__).resolve().parent / "laya_utrecht" / "predictions.json"


def build_laya1() -> dict:
    """Embed the real Laya System-1 model for the Utrecht zone chain (PoC-1).

    Trained on 84 unique NormCards from the 13 PoC-1 runs (regelstatus /
    zone_effect choice heads, needs_human noul, legal_force score — gold from
    formalrules.json + decision-table.json + normcards.legalForce); five whole
    tracks (water · mobiliteit · werken · recreatie · biomassa) held out for
    evaluation. predict_export.py ran the fine-tuned checkpoint over every
    card; the page embeds those predictions plus a deterministic nearest-
    neighbour index (matcher featurization over claim+quote) so free-text
    queries map to a card. No invented numbers.
    """
    if not LAYA1_EXPORT.exists():
        sys.exit(f"missing {LAYA1_EXPORT} — run simulation/laya_utrecht/finetune.py + "
                 f"predict_export.py first (deep-agents/laya_train/.venv)")
    exp = json.loads(LAYA1_EXPORT.read_text(encoding="utf-8"))

    laya_root = ROOT / "poc-bp2op"
    if str(laya_root) not in sys.path:
        sys.path.insert(0, str(laya_root))
    from pipeline.knowledgebank import terms, _STOPWORDS, _SUFFIXES

    # ---- nearest-neighbour index over claim + verbatim quote
    docs = {k: c[3] + " " + c[4] for k, c in exp["cards"].items()}
    tf = {k: Counter(terms(t)) for k, t in docs.items()}
    n_docs = len(docs)
    df = Counter()
    for c in tf.values():
        df.update(c.keys())
    vocab = sorted({t for c in tf.values() for t in c})
    vidx = {t: i for i, t in enumerate(vocab)}
    idf = [round(math.log((1 + n_docs) / (1 + df[t])) + 1.0, 3) for t in vocab]
    rows = {}
    for k, c in tf.items():
        w = {t: cnt * idf[vidx[t]] for t, cnt in c.items()}
        nrm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        rows[k] = [[vidx[t], round(v / nrm, 4)]
                   for t, v in sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))[:24]]

    # ---- probes: canonical-track cards spanning the outcome space
    by_combo = {}
    for k, c in sorted(exp["cards"].items()):
        g = exp["gold"][k]
        if c[0] in ("wind", "zon", "bos"):
            by_combo.setdefault((g["s"], g["e"]), k)
    order = [("formalized", "included"), ("formalized", "excluded"),
             ("formalized", "conditional"), ("ambiguous", "ambiguous"),
             ("rejected", "not_applicable"), ("formalized", "attention")]
    picked, seen_tracks = [], set()
    for combo in order:
        k = by_combo.get(combo)
        if k:
            picked.append(k)
            seen_tracks.add(exp["cards"][k][0])
    for k, c in sorted(exp["cards"].items()):  # make sure zon & bos are represented
        if c[0] in ("zon", "bos") and c[0] not in seen_tracks and len(picked) < 6:
            picked.append(k)
            seen_tracks.add(c[0])
    probes = [{"key": k, "track": exp["cards"][k][0], "card": exp["cards"][k][1],
               "art": exp["cards"][k][2],
               "why": f"{exp['gold'][k]['s']} · {exp['gold'][k]['e']}"}
              for k in picked[:6]]

    return {
        "meta": exp["model"],
        "questions": exp["questions"],
        "eval": exp["eval"],
        "preds": exp["preds"],
        "gold": exp["gold"],
        "cards": exp["cards"],
        "tok": {"stop": sorted(_STOPWORDS), "suf": list(_SUFFIXES)},
        "vocab": vocab,
        "idf": idf,
        "nn": rows,
        "probes": probes,
    }


#: BAG-bebouwing in de eindzones — build-time via de Clappform OGC-DT API
#: (simulation/build_bag_cache.py). Optioneel: zonder cache valt het paneel weg.
BAG_CACHE = Path(__file__).resolve().parent / "bag-cache.json"


def build_poc1() -> dict:
    aoi_geo = display_rings(shape(load(AOI_CACHE)["features"][0]["geometry"]))
    tracks = {name: build_track(name, meta) for name, meta in POC1_TRACKS.items()}
    bag = None
    if BAG_CACHE.exists():
        bag = json.loads(BAG_CACHE.read_text(encoding="utf-8"))
    return {
        "aoi": {"areaKm2": 1560.054, "geo": aoi_geo},
        "tracks": tracks,
        "laya": build_laya1(),
        "bag": bag,
    }


# ---------------------------------------------------------------- PoC-2 data
def build_kg(kb: list, doel_map: dict, tabel: list) -> dict:
    """Kennisbank as a graph payload: a bipartite node-link diagram
    (bron-artikelen from the besluiten -> doel-artikelen of the omgevingsplan).

    Everything is derived from kennisbank.json + the omzettabel join (which KB
    relations the matcher actually reused); 21 relations without a doelRegelId
    point into hoofdstuk 22 itself (old law living on as bronregels) and get
    their own right-hand group. Layout is computed here (deterministic, no
    physics) so the page only renders paths.
    """
    used = {s.get("kennisbankHitId") for r in tabel for s in r["suggesties"] if s.get("kennisbankHitId")}

    def art_num(a: str):
        out = []
        for p in a.split("."):
            m = re.match(r"(\d+)", p)
            out.append(int(m.group(1)) if m else 0)
        return tuple(out)

    # ---- right nodes: doelregels by chapter + old-law locators (hoofdstuk 22)
    chapters = {}  # gid -> title (from the doelregels themselves)
    right = {}
    for k in kb:
        if k["doelRegelId"]:
            loc = doel_map[k["doelRegelId"]]["locator"]
            gid, key, num = loc["hoofdstukNr"], "DR:" + k["doelRegelId"], art_num(loc["artikel"])
            chapters.setdefault(gid, loc["hoofdstukTitel"])
        else:
            art = k["doelLocator"].replace("artikel ", "")
            gid, key, num = 22, "LOC:" + art, art_num(art)
        n = right.get(key)
        if n is None:
            n = right[key] = {"key": key, "gid": gid, "num": num, "label": k["doelLocator"], "n": 0}
        n["n"] += 1
    rnodes = sorted(right.values(), key=lambda n: (n["gid"], n["num"], n["key"]))
    ridx = {n["key"]: i for i, n in enumerate(rnodes)}

    # ---- left nodes: unique (doc, bron-artikel); ordered by first target so
    #      the edge braid stays readable (per doc block, near-monotone)
    left = {}
    for k in kb:
        key = k["bronDocId"] + "|" + k["bronLabel"]
        rk = ("DR:" + k["doelRegelId"]) if k["doelRegelId"] else \
            "LOC:" + k["doelLocator"].replace("artikel ", "")
        n = left.get(key)
        if n is None:
            n = left[key] = {"doc": k["bronDocId"], "label": k["bronLabel"], "minr": 10 ** 6, "n": 0}
        n["n"] += 1
        n["minr"] = min(n["minr"], ridx[rk])
    llist = sorted(left.values(), key=lambda n: (n["doc"], n["minr"]))
    lidx = {n["doc"] + "|" + n["label"]: i for i, n in enumerate(llist)}

    edges = []
    for k in kb:
        rk = ("DR:" + k["doelRegelId"]) if k["doelRegelId"] else \
            "LOC:" + k["doelLocator"].replace("artikel ", "")
        edges.append({"a": lidx[k["bronDocId"] + "|" + k["bronLabel"]], "b": ridx[rk], "k": k})
    edges.sort(key=lambda e: (e["a"], e["b"]))

    # ---- deterministic vertical layout (pitch per node, block per group)
    TOP, PITCH, GH = 34, 3.0, 26

    def layout(nodes, gid_of):
        y, prev, groups = TOP, None, []
        for n in nodes:
            g = gid_of(n)
            if g != prev:
                if prev is not None:
                    y += 4
                groups.append({"gid": g, "y": y})
                y += GH
                prev = g
            n["y"] = y
            y += PITCH
        return y, groups

    end_l, lgroups = layout(llist, lambda n: n["doc"])
    end_r, rgroups = layout(rnodes, lambda n: n["gid"])
    H = round(max(end_l, end_r) + 14)

    LT, RT = 170, 792            # tick columns; edges run 172 -> 790
    MID = (172 + 790) // 2
    lt = "".join(f"M{LT - 6} {n['y']:.1f}h6" for n in llist)
    rt = "".join(f"M{RT} {n['y']:.1f}h6" for n in rnodes)
    for e in edges:
        ya, yb = llist[e["a"]]["y"], rnodes[e["b"]]["y"]
        e["d"] = f"M172 {ya:.1f}C{MID} {ya:.1f} {MID} {yb:.1f} 790 {yb:.1f}"

    DOC_META = {"B02": ("Wijzigingsbesluit 2025", "GMB-2025-226538"),
                "B03": ("Conversiebesluit 2023", "GMB-2023-561129")}
    lg = []
    for g in lgroups:
        name, gmb = DOC_META[g["gid"]]
        n_rel = sum(x["n"] for x in llist if x["doc"] == g["gid"])
        lg.append({"y": round(g["y"], 1), "l1": f"{g['gid']} — {name}",
                   "l2": f"{gmb} · {n_rel} relaties"})
    rg = []
    for g in rgroups:
        gid = g["gid"]
        n_ver = sum(1 for e in edges if rnodes[e["b"]]["gid"] == gid and e["k"]["relatie"] == "vervangt")
        n_voort = sum(1 for e in edges if rnodes[e["b"]]["gid"] == gid and e["k"]["relatie"] == "voortzetting")
        title = "BRUIDSSCHAT / OVERGANGSRECHT (oud)" if gid == 22 else chapters.get(gid, "")
        rg.append({"y": round(g["y"], 1),
                   "l1": f"hfd {gid} · {short(title, 26)}",
                   "l2": f"{n_ver + n_voort} rel · {n_ver} verv · {n_voort} voort"})

    n_vervangt = sum(1 for e in edges if e["k"]["relatie"] == "vervangt")
    return {
        "h": H,
        "capL": f"bron — {len(llist)} artikelen uit de besluiten (oud recht)",
        "capR": f"doel — {len(rnodes)} artikelen omgevingsplan CVDR696400/4",
        "lg": lg, "rg": rg, "lt": lt, "rt": rt,
        "e": [{"d": e["d"], "rel": "v" if e["k"]["relatie"] == "vervangt" else "f",
               "u": 1 if e["k"]["id"] in used else 0, "a": e["a"], "b": e["b"],
               "id": e["k"]["id"], "doc": e["k"]["bronDocId"],
               "bron": short(e["k"]["bronLabel"], 90), "dl": e["k"]["doelLocator"],
               "dr": e["k"]["doelRegelId"], "q": short(e["k"]["quote"], 150),
               "url": e["k"]["url"]} for e in edges],
        "c": {"edges": len(edges), "vervangt": n_vervangt,
              "voortzetting": len(edges) - n_vervangt,
              "bron": len(llist), "doel": len(rnodes),
              "used": sum(1 for e in edges if e["k"]["id"] in used)},
    }


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_kg1(cards: list, formal: list, zones: list, rejected: dict, layers_manifest: dict) -> dict:
    """PoC-1 rule knowledge graph: instrument article → NormCard → FormalRule →
    geo layer → ZoneResult, plus the abstention register (topics that produced no
    card — cite-or-abstain). One payload per track; every node/edge carries the
    pipeline stage (1..4) that produces it so the panel can light up in step
    with the timeline. Tooltips are pre-rendered HTML strings (escaped here).
    """
    TOP, PITCH, GH = 34, 15, 26
    COLX = {"art": 178, "card": 430, "rule": 640, "layer": 800, "zone": 912}
    CAP = {"art": "instrument · artikel", "card": "NormCards · RR-artikelkern",
           "rule": "FormalRules · execution", "layer": "geo layers (registry)", "zone": "ZoneResults"}

    nodes, groups = [], []   # node: dict(col,x,y,tx,anchor,label,cls,st,tip,dash?)
    cols = {k: {"y": TOP, "prev": None} for k in COLX}

    def add(col, key, label, cls, st, tip, group, dash=False, anchor="start"):
        c = cols[col]
        if group != c["prev"]:
            if c["prev"] is not None:
                c["y"] += 6
            groups.append({"col": col, "x": COLX[col] - (165 if col == "art" else 10),
                           "y": c["y"], "l1": group})
            c["y"] += GH
            c["prev"] = group
        tx = COLX[col] - 8 if col == "art" else COLX[col] + 8
        n = {"col": col, "x": COLX[col], "y": c["y"], "tx": tx,
             "anchor": "end" if col == "art" else "start",
             "label": label, "cls": cls, "st": st, "tip": tip, "dash": dash, "key": key,
             "i": len(nodes)}
        nodes.append(n)
        c["y"] += PITCH
        return n

    def tip(*lines):
        return "<br>".join(_esc(l) for l in lines if l)

    # ---- column 1: instrument articles (per cited docId+article)
    art_node, art_first = {}, {}
    by_art = {}
    for c in cards:
        k = c["source"]["docId"] + "|" + c["source"]["article"]
        by_art.setdefault(k, c)

    def art_sort(k):
        doc, art = k.split("|")
        nums = []
        for p in art.replace("art. ", "").replace("art ", "").split():
            for q in p.replace("onder", ".").replace("lid", "").split("."):
                m = re.match(r"(\d+)", q)
                if m:
                    nums.append(int(m.group(1)))
        return (doc, nums or [0])

    for k in sorted(by_art, key=art_sort):
        c = by_art[k]
        doc, art = k.split("|")
        art_node[k] = add("art", k, short(art, 26), "kgn-art", 1,
                          tip(f"{doc} · {art}", short(c["source"]["version"], 110),
                              short(c.get("instrument", ""), 110)),
                          f"{doc} — {short(c.get('instrument', 'instrument'), 30)}")

    # ---- column 2: NormCards + abstentions
    card_idx = {}
    for c in cards:
        num = c.get("number") or c["source"].get("article") or "—"
        card_idx[c["id"]] = add("card", c["id"], c["id"], "kgn-card", 1,
                                tip(c["id"],
                                    f"artikelkern number: {num}",
                                    f"theme: {c.get('theme', '—')}",
                                    short(c["claim"], 200),
                                    "“" + short(c.get("text") or c["source"]["quote"], 160) + "”",
                                    short(c.get("url") or c["source"].get("url") or "", 90)),
                                f"NormCards — {len(cards)} cited")
    abs_idx = {}
    for a in rejected.get("abstentions", []):
        abs_idx[a["id"]] = add("card", a["id"], short(a["id"] + " · " + a["topic"], 24),
                               "kgn-abs", 1, tip(a["id"], a["topic"], short(a["reason"], 190)),
                               f"abstained — {len(rejected.get('abstentions', []))} topics, no citation",
                               dash=True)

    # ---- column 3: FormalRules grouped by status (sorted so groups are contiguous)
    rule_idx, stat_n = {}, {}
    for r in formal:
        stat_n[r["status"]] = stat_n.get(r["status"], 0) + 1
    gname = {"formalized": "formalized", "ambiguous": "ambiguous → V4 human",
             "rejected": "rejected (non-binding)"}
    STAT_ORDER = {"formalized": 0, "ambiguous": 1, "rejected": 2}
    for r in sorted(formal, key=lambda r: (STAT_ORDER.get(r["status"], 9), r["id"])):
        rule_tip = [r["id"], f"status: {r['status']} · {r.get('ruleType', '') or '—'}"]
        if r.get("status") == "formalized" and isinstance(r.get("execution"), dict):
            rule_tip.extend(_execution_summary(r))
        else:
            rule_tip.append(short(r.get("reason") or r.get("rationale") or "", 200))
        rule_idx[r["id"]] = add("rule", r["id"], r["id"],
                                "kgn-rule-" + r["status"][:2], 2,
                                tip(*rule_tip),
                                f"{gname.get(r['status'], r['status'])} — {stat_n[r['status']]}")

    # ---- column 4: geo layers grouped by role (registry keys actually used)
    layer_idx = {}
    used_keys = sorted(({zi for r in formal for zi in _rule_zone_ids(r)}
                        | {o for z in zones for o in z.get("operands", [])})
                       & set(layers_manifest))
    ROLE_ORDER = {"inclusion": 0, "exclusion": 1, "conditional": 2, "compensation": 3,
                  "context": 4, "aoi": 5}
    used_keys.sort(key=lambda lk: (ROLE_ORDER.get((layers_manifest.get(lk) or {}).get("role", "context"), 9), lk))
    for lk in used_keys:
        m = layers_manifest.get(lk) or {}
        role = m.get("role", "context")
        layer_idx[lk] = add("layer", lk, short(lk, 19), "kgn-layer", 3,
                            tip(lk, short(m.get("title", ""), 90), f"role: {role}",
                                m.get("serviceUrl", "")),
                            role)

    # ---- column 5: ZoneResults grouped by kind
    zone_idx = {}
    KIND_LBL = {"union": "∪ inclusion", "intersection": "∩ AOI", "difference": "− exclusion",
                "final": "= final", "attention": "attention", "conditional": "conditional",
                "compensation": "compensation"}
    KIND_ORDER = {"union": 0, "intersection": 1, "difference": 2, "final": 3,
                  "attention": 4, "conditional": 5, "compensation": 6}

    def zone_kind(z):
        try:
            return _zone_class(z["id"])
        except ValueError:
            return None

    for z in sorted(zones, key=lambda z: (KIND_ORDER.get(zone_kind(z), 9), z["id"])):
        kind = zone_kind(z)
        if kind is None:
            continue
        label = f"{z['areaKm2']:.1f}" if kind not in ("attention", "conditional", "compensation") else kind[:4] + "."
        zone_idx[z["id"]] = add("zone", z["id"], label, "kgn-zone-" + kind, 4,
                                tip(short(z["id"], 34), f"{z['operation']} · {z['areaKm2']} km²",
                                    "rules: " + (", ".join(z["ruleIds"]) or "—")),
                                KIND_LBL.get(kind, kind))

    # ---- edges (stage-tagged, colored by relation type)
    edges = []

    def edge(s_node, t_node, cls, st):
        x1, y1 = s_node["x"], s_node["y"]
        x2, y2 = t_node["x"], t_node["y"]
        mx = (x1 + x2) // 2
        edges.append({"s": s_node["i"], "t": t_node["i"],
                      "d": f"M{x1} {y1:.1f}C{mx} {y1:.1f} {mx} {y2:.1f} {x2} {y2:.1f}",
                      "cls": cls, "st": st})

    for c in cards:
        k = c["source"]["docId"] + "|" + c["source"]["article"]
        if k in art_node:
            edge(art_node[k], card_idx[c["id"]], "kge-art", 1)
    for r in formal:
        if r.get("normCardId") in card_idx:
            edge(card_idx[r["normCardId"]], rule_idx[r["id"]], "kge-rule", 2)
    for r in formal:
        for zk in _rule_zone_ids(r):
            if zk in layer_idx:
                edge(rule_idx[r["id"]], layer_idx[zk], "kge-layer", 3)
    for z in zones:
        if z["id"] not in zone_idx:
            continue
        for op in z.get("operands", []):
            if op in layer_idx:
                edge(layer_idx[op], zone_idx[z["id"]], "kge-zone", 4)

    H = round(max(c["y"] for c in cols.values()) + 12)
    n_form = sum(1 for r in formal if r["status"] == "formalized")
    n_ex = sum(1 for r in formal if r.get("status") == "formalized"
               and isinstance(r.get("execution"), dict))
    return {
        "h": H,
        "cap": (f"{len(cards)} NormCards · {len(rejected.get('abstentions', []))} abstentions · "
                f"{len(formal)} rules ({n_form} formalized, {n_ex} with execution) · "
                f"{len(used_keys)} layers · {len(zone_idx)} zone results"),
        "cols": [{"x": COLX[k] - (165 if k == "art" else 10), "cap": CAP[k]} for k in COLX],
        "groups": groups, "hmax": H,
        "n": [{k: n[k] for k in ("x", "y", "tx", "anchor", "label", "cls", "st", "tip", "dash")}
              for n in nodes],
        "e": edges,
    }


# ---------------------------------------------------------------- Laya System-1
#: real Laya (github.com/NandhaKishorM/laya) fine-tuned on the BP->OP run —
#: see simulation/laya_bp2op/ (build_dataset.py -> finetune.py -> predict_export.py)
LAYA_EXPORT = Path(__file__).resolve().parent / "laya_bp2op" / "predictions.json"


def build_laya(bron: list, doel: list, kb: list, tabel: list, doel_map: dict) -> dict:
    """Embed the real Laya System-1 decision model for the PoC-2 chain.

    The fine-tuned laya checkpoint (multilingual mmBERT-base, RLCD + temperature
    calibration, trained on 248 bronregels / 744 items) runs offline at build
    time over all 311 bronregels (predict_export.py); its typed outputs —
    choice (doel-hoofdstuk) · score (match-band) · noul (needs-jurist) — are
    embedded verbatim. The page adds only a deterministic nearest-neighbour
    lookup (same tokenizer as the PoC matcher) so a free-text query maps to the
    bronregel whose embedded Laya prediction is then shown. No invented numbers.
    """
    if not LAYA_EXPORT.exists():
        sys.exit(
            f"missing {LAYA_EXPORT} — run simulation/laya_bp2op/finetune.py + "
            f"predict_export.py first (deep-agents/laya_train/.venv)"
        )
    exp = json.loads(LAYA_EXPORT.read_text(encoding="utf-8"))

    laya_root = ROOT / "poc-bp2op"
    if str(laya_root) not in sys.path:
        sys.path.insert(0, str(laya_root))
    from pipeline.knowledgebank import terms, _STOPWORDS, _SUFFIXES

    # ---- nearest-neighbour index: query text -> bronregel (TF-IDF, matcher featurization)
    tf = {b["id"]: Counter(terms(b["tekst"])) for b in bron}
    n_docs = len(bron)
    df = Counter()
    for c in tf.values():
        df.update(c.keys())
    vocab = sorted({t for c in tf.values() for t in c})
    vidx = {t: i for i, t in enumerate(vocab)}
    idf = [round(math.log((1 + n_docs) / (1 + df[t])) + 1.0, 3) for t in vocab]
    TOP = 24
    rows = {}
    for bid, c in tf.items():
        w = {t: cnt * idf[vidx[t]] for t, cnt in c.items()}
        nrm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        rows[bid] = [[vidx[t], round(v / nrm, 4)]
                     for t, v in sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP]]

    # ---- kennisbank discrete hits (for chat answers about official relations)
    kb_by_art = {}
    for k in kb:
        m = re.search(r"(\d+\.\d+[a-z]?)", k["bronLabel"])
        if m and m.group(1) not in kb_by_art and k.get("doelRegelId"):
            kb_by_art[m.group(1)] = [k["doelRegelId"], k["id"], k["relatie"]]

    # ---- probe set for the one-click forward-pass UI
    tabel_by_ot = {r["id"]: r for r in tabel}
    wanted = [("OT-001", "kennisbank-hit (tabel-score 1.0)"),
              ("OT-002", "TF-IDF 'sterk', geen kennisbank"),
              ("OT-043", "TF-IDF 'mogelijk'"),
              ("OT-003", "'zwak' -> needs_human"),
              ("OT-006", "geen match -> nieuwe regel")]
    probes = []
    for ot, why in wanted:
        r = tabel_by_ot[ot]
        b = br_map_of(bron, r["bronRegelId"])
        probes.append({"ot": ot, "bid": b["id"], "art": b["locator"]["artikel"],
                       "label": short(b["locator"]["label"], 60), "why": why})

    hfds = {}
    for d in doel:
        loc = d["locator"]
        hfds.setdefault(str(loc["hoofdstukNr"]), short(loc["hoofdstukTitel"], 44))

    return {
        "meta": exp["model"],
        "questions": exp["questions"],
        "eval": exp["eval"],
        "preds": exp["preds"],
        "gold": exp["gold"],
        "tok": {"stop": sorted(_STOPWORDS), "suf": list(_SUFFIXES)},
        "vocab": vocab,
        "idf": idf,
        "nn": rows,
        "dr": {d["id"]: d["locator"]["artikel"] for d in doel},
        "hfds": hfds,
        "kbArt": kb_by_art,
        "bron": {b["id"]: [b["locator"]["artikel"], short(b["locator"]["label"], 60),
                           short(b["tekst"], 130), b["docId"]] for b in bron},
        "probes": probes,
    }


def br_map_of(bron, bid):
    return next(b for b in bron if b["id"] == bid)


def build_poc2() -> dict:
    run = POC2_RUN
    summary = load(run / "run_summary.json")
    bron = load(run / "bronregels.json")
    doel = load(run / "doelregels.json")
    kb = load(run / "kennisbank.json")
    tabel = load(run / "omzettabel.json")
    coverage = load(run / "coverage.json")
    validation = load(run / "validation.json")

    bron_map = {b["id"]: b for b in bron}
    doel_map = {d["id"]: d for d in doel}

    grid = []
    for r in tabel:
        top = r["suggesties"][0] if r["suggesties"] else None
        grid.append(
            {
                "id": r["bronRegelId"],
                "status": r["status"],
                "band": top["band"] if top else "geen",
                "score": round(top["score"], 2) if top else None,
                "kb": bool(top and top.get("kennisbankHitId")),
            }
        )

    samples = []
    wanted = [
        ("OT-001", "kennisbank-driven match (score 1.0)"),
        ("OT-043", "TF-IDF-only match, 'mogelijk' band"),
        ("OT-003", "weak match → needs_human"),
        ("OT-006", "no match → nieuwe regel voorgesteld"),
    ]
    for ot, why in wanted:
        r = next(x for x in tabel if x["id"] == ot)
        b = bron_map[r["bronRegelId"]]
        top = r["suggesties"][0] if r["suggesties"] else None
        d = doel_map[top["doelRegelId"]] if top else None
        samples.append(
            {
                "ot": ot,
                "why": why,
                "bronArt": b["locator"]["artikel"],
                "bronTekst": short(b["tekst"], 150),
                "doelArt": (d["locator"]["artikel"] if d else None),
                "doelTekst": short(d["tekst"], 150) if d else None,
                "score": round(top["score"], 2) if top else None,
                "band": top["band"] if top else "geen",
                "status": r["status"],
                "kb": bool(top and top.get("kennisbankHitId")),
            }
        )

    checks = [
        {"id": c["id"], "level": c["level"], "passed": c["passed"], "evidence": short(c["evidence"], 110)}
        for c in validation["checks"]
        if c["level"] in ("V0", "V3", "V4")
    ]

    return {
        "runId": summary["runId"],
        "verdict": summary["verdict"],
        "counts": summary["counts"],
        "parse": {"artikelen": 1074, "doelregels": len(doel), "bronregels": len(bron)},
        "kb": {
            "sources": [
                {"id": "B02", "label": "Wijzigingsbesluit 2025 (GMB 226538)", "n": 262, "kept": 262},
                {"id": "B03", "label": "Conversiebesluit 2023 (GMB 561129)", "n": 12, "kept": 12},
                {"id": "B04", "label": "Omnibusbesluit 2026 (GMB 256846)", "n": 9, "kept": 0},
            ],
            "total": len(kb),
            "vervangt": sum(1 for k in kb if k["relatie"] == "vervangt"),
            "voortzetting": sum(1 for k in kb if k["relatie"] == "voortzetting"),
        },
        "grid": grid,
        "kbDriven": sum(1 for g in grid if g["kb"]),
        "kg": build_kg(kb, doel_map, tabel),
        "coverage": coverage,
        "samples": samples,
        "validation": {
            "levels": validation["levels"],
            "checks": checks,
            "v3Detail": summary["v3Detail"],
        },
        "portfolio": summary["portfolio"],
        "businessCase": summary["businessCase"],
        "laya": build_laya(bron, doel, kb, tabel, doel_map),
    }


def build_breda() -> dict:
    """Compact PoC-4 Breda five-value scan for simulation tab 4 (offline embed)."""
    run = POC4_RUN
    if not run.is_dir():
        raise FileNotFoundError(f"missing PoC-4 run dir {run}")
    summary = load(run / "run_summary.json")
    vs = load(run / "value-scan.json")
    val = load(run / "validation.json")
    geo_fc = load(run / "geo-buurten.wgs84.geojson")
    qa_raw = load(BREDA_QA)
    qa = qa_raw if isinstance(qa_raw, list) else (qa_raw.get("items") or qa_raw.get("qa") or [])

    buurten = []
    for b in vs.get("buurten") or []:
        scores = b.get("scores") or {}
        buurten.append({
            "buurtcode": b["buurtcode"],
            "buurtnaam": b["buurtnaam"],
            "wijkcode": b.get("wijkcode"),
            "aantalInwoners": b.get("aantalInwoners"),
            "scores": {
                k: float((scores.get(k) or {}).get("score") or 0)
                for k in ("democratic", "spatial", "economic", "social")
            },
            "missing": b.get("missing") or [],
        })
    validate_breda_qa(qa, {b["buurtnaam"] for b in buurten})

    geo: dict[str, list] = {}
    for f in geo_fc.get("features") or []:
        props = f.get("properties") or {}
        code = props.get("code") or props.get("buurtcode")
        if not code or not f.get("geometry"):
            continue
        try:
            geo[code] = display_rings(shape(f["geometry"]))
        except Exception:
            continue

    levels = {}
    for name, info in (val.get("validationLevels") or {}).items():
        if isinstance(info, dict):
            levels[name] = info.get("status") or info.get("verdict") or "—"
        else:
            levels[name] = str(info)

    scan = vs.get("scan") if isinstance(vs.get("scan"), dict) else {}
    out = {
        "runId": summary["runId"],
        "verdict": summary.get("verdict"),
        "nBuurten": summary.get("nBuurten", len(buurten)),
        "scan": {k: scan[k] for k in ("id", "label", "generatedAt") if k in scan},
        "values": vs.get("values") or {},
        "sources": [
            {
                "id": s.get("id"),
                "title": s.get("title") or s.get("name") or s.get("id"),
                "url": s.get("url"),
            }
            for s in (vs.get("sources") or [])
            if isinstance(s, dict)
        ],
        "buurten": buurten,
        "rollup": vs.get("rollup") or {},
        "geo": geo,
        "validation": {"verdict": val.get("verdict"), "levels": levels},
        "qa": qa,
        "stages": ["intake", "fetch", "indicators", "validate", "report", "unlock"],
        "lake": {
            "datasetId": "20261025-breda-laya-s1",
            "bronzeCbs": "lake://nldt-poc-lake/bronze/breda/cbs-buurten-2024/",
            "silverLaya": "lake://nldt-poc-lake/silver/breda/laya/system1/20261025-breda-laya-s1/",
            "goldLaya": "lake://nldt-poc-lake/gold/breda/laya/system1/20261025-breda-laya-s1/",
            "goldRun": f"lake://nldt-poc-lake/gold/breda/runs/{summary['runId']}/",
        },
    }
    if LAYA_BREDA_EXPORT.is_file():
        out["laya"] = build_laya_breda()
    return out


def build_laya_breda() -> dict:
    """Embed Breda Laya System-1 predictions + TF-IDF index over buurten."""
    if not LAYA_BREDA_EXPORT.is_file():
        raise FileNotFoundError(
            f"missing {LAYA_BREDA_EXPORT} — run simulation/laya_breda/finetune.py + "
            "predict_export.py first (deep-agents/laya_train/.venv)"
        )
    exp = json.loads(LAYA_BREDA_EXPORT.read_text(encoding="utf-8"))

    laya_root = ROOT / "poc-bp2op"
    if str(laya_root) not in sys.path:
        sys.path.insert(0, str(laya_root))
    from pipeline.knowledgebank import terms, _STOPWORDS, _SUFFIXES

    docs = {k: " ".join(str(x) for x in c) for k, c in exp["cards"].items()}
    tf = {k: Counter(terms(t)) for k, t in docs.items()}
    n_docs = len(docs) or 1
    df: Counter = Counter()
    for c in tf.values():
        df.update(c.keys())
    vocab = sorted({t for c in tf.values() for t in c})
    vidx = {t: i for i, t in enumerate(vocab)}
    idf = [round(math.log((1 + n_docs) / (1 + df[t])) + 1.0, 3) for t in vocab]
    rows = {}
    for k, c in tf.items():
        w = {t: cnt * idf[vidx[t]] for t, cnt in c.items()}
        nrm = math.sqrt(sum(v * v for v in w.values())) or 1.0
        rows[k] = [
            [vidx[t], round(v / nrm, 4)]
            for t, v in sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))[:24]
        ]

    by_combo: dict = {}
    for k, c in sorted(exp["cards"].items()):
        g = exp["gold"][k]
        by_combo.setdefault((g["v"], g["b"], bool(g["j"])), k)
    probes = []
    for combo, k in list(by_combo.items())[:6]:
        probes.append({
            "key": k,
            "naam": exp["cards"][k][2],
            "why": f"{combo[0]} · band {combo[1]} · needs_human={combo[2]}",
        })

    return {
        "meta": exp["model"],
        "questions": exp["questions"],
        "eval": exp["eval"],
        "preds": exp["preds"],
        "gold": exp["gold"],
        "cards": exp["cards"],
        "tok": {"stop": sorted(_STOPWORDS), "suf": list(_SUFFIXES)},
        "vocab": vocab,
        "idf": idf,
        "nn": rows,
        "probes": probes,
        "gate": exp["model"].get("gate", 0.55),
    }


# ---------------------------------------------------------------------------
# Tab 6 — Veenendaal · Spoorzone gebiedscheck (eerste gebiedsontwikkeling-PoC
# op het canvas-sjabloon). Display-geometrie wordt build-time geclipt naar de
# werkgrens en versimpeld (alleen beeld); elk getal in de panels is de eigen
# output van de canonieke run (indicators.json / manifest.json).

VEENENDAAL_POC = ROOT / "poc-veenendaal"


def _vd_actueel(features: list) -> list:
    """BGT v1 levert ook historische versies: alleen eind_registratie is leeg."""
    return [f for f in features
            if f.get("properties", {}).get("eind_registratie") in (None, "")]


def _vd_rings(fc: dict, clip, tol: float = 2.0, min_m2: float = 150.0) -> list:
    """Actuele vlakken → intersectie met de werkgrens → display-versimpeld."""
    rings = []
    for f in fc.get("features", []):
        g = f.get("geometry")
        if not g or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        try:
            geom = shape(g).intersection(clip).simplify(tol, preserve_topology=True)
        except Exception:
            continue
        if geom.is_empty or geom.area < min_m2:
            continue
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            rr = [[round(x, 1), round(y, 1)] for x, y in poly.exterior.coords]
            if len(rr) >= 4:
                rings.append(rr)
    return rings


def _ring_area_m2(ring: list) -> float:
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(s / 2.0)


def build_veenendaal() -> dict:
    run_dirs = sorted((VEENENDAAL_POC / "runs").glob("*-gebiedscheck"))
    if not run_dirs:
        sys.exit(f"missing poc-veenendaal gebiedscheck run under {VEENENDAAL_POC / 'runs'}")
    run = run_dirs[-1]  # nieuwste run = canoniek
    gebied = json.loads((VEENENDAAL_POC / "data" / "gebied.json").read_text(encoding="utf-8"))
    ind = json.loads((run / "indicators.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    bbox_rd = gebied["werkgrens"]["bbox_rd"]
    clip = box(*bbox_rd)

    cache = VEENENDAAL_POC / "data" / "cache"

    def cache_fc(name: str) -> dict:
        return json.loads((cache / f"{name}.geojson").read_text(encoding="utf-8"))

    groen = _vd_rings(cache_fc("begroeidterreindeel"), clip)
    verhard = _vd_rings(cache_fc("onbegroeidterreindeel"), clip)
    water = _vd_rings(cache_fc("waterdeel"), clip)

    dedupe = []
    for naam in ["begroeidterreindeel", "onbegroeidterreindeel", "waterdeel",
                 "vegetatieobject_vlak", "spoor", "vegetatieobject_punt"]:
        feats = cache_fc(naam).get("features", [])
        dedupe.append({"layer": naam, "raw": len(feats), "actueel": len(_vd_actueel(feats))})

    spoor = []
    for f in _vd_actueel(cache_fc("spoor").get("features", [])):
        g = f.get("geometry")
        if not g or g.get("type") != "LineString":
            continue
        try:
            line = shape(g).simplify(1.0, preserve_topology=True)
        except Exception:
            continue
        spoor.append([[round(x), round(y)] for x, y in line.coords])

    panden = []
    for f in cache_fc("pand").get("features", []):
        g = f.get("geometry")
        if not g:
            continue
        p = f.get("properties", {})
        if p.get("status") in ("Pand gesloopt", "Niet gerealiseerd pand"):
            cat = 2
        elif isinstance(p.get("bouwjaar"), int) and p["bouwjaar"] >= 2020:
            cat = 1
        else:
            cat = 0
        c = shape(g).representative_point()
        panden.append([round(c.x), round(c.y), cat])

    bomen = []
    for f in _vd_actueel(cache_fc("vegetatieobject_punt").get("features", [])):
        g = f.get("geometry")
        if g and g.get("type") == "Point":
            bomen.append([round(g["coordinates"][0]), round(g["coordinates"][1])])

    bronnen = [{"collection": b["collection"], "n": b["featureCount"],
                "sha": b["sha256"][:10], "at": b.get("fetchedAt", ""),
                "host": b["url"].split("/collections")[0].replace("https://", "")}
               for b in manifest["bronnen"]]

    sweep = None
    zones_payload = None
    sweep_dirs = sorted((VEENENDAAL_POC / "scenario-runs").glob("*-sweep"))
    if sweep_dirs:
        sdir = sweep_dirs[-1]  # nieuwste sweep = actueel
        scs = json.loads((sdir / "scenarios.json").read_text(encoding="utf-8"))
        sman = json.loads((sdir / "manifest.json").read_text(encoding="utf-8"))
        dg = json.loads((sdir / "deelgebieden.json").read_text(encoding="utf-8"))
        zones_payload = {"status": dg["status"], "zones": dg["zones"]}
        per_zone = dg.get("per_scenario", {})
        # display-ringen volgen de ENGINE-beslissing (genomen_ids + regel uit
        # scenarios.py); de build versimpelt alleen voor het beeld
        lagen_ids = {}
        for naam in ("begroeidterreindeel", "onbegroeidterreindeel"):
            feats = cache_fc(naam).get("features", [])
            lagen_ids[naam] = {f["properties"].get("lokaal_id"): f for f in feats}
        for s in scs:
            a = s.get("allocatie")
            if not a:
                continue
            bron = "begroeidterreindeel" if a["laag"] == "groen" else "onbegroeidterreindeel"
            genomen = {"type": "FeatureCollection",
                       "features": [lagen_ids[bron][i] for i in a["genomen_ids"]
                                    if i in lagen_ids[bron]]}
            s["kaart"] = {"laag": a["laag"], "benodigd_ha": s["uit"]["benodigd_grondvlak_ha"],
                          "toegedeeld_ha": a["toegedeeld_ha"], "n": a["n"],
                          "regel": a["regel"], "per_zone": a["per_zone"],
                          "ringen": _vd_rings(genomen, clip)}
        sweep = {"runId": sman["runId"], "v3": sman["v3"],
                 "toelichting": sman["aannames"]["toelichting"], "scenarios": scs}

    return {
        "runId": manifest["runId"],
        "gebied": {"naam": gebied["gebied"],
                   "bronNaam": gebied["bron"]["naam"], "bronUrl": gebied["bron"]["url"],
                   "oppHa": gebied["werkgrens"]["opp_ha"], "bbox": bbox_rd,
                   "afleiding": gebied["werkgrens"]["afleiding"],
                   "anchor": gebied["ankers"][0]["rd"] + [gebied["ankers"][0]["naam"]],
                   "deelgebieden": gebied["deelgebieden"]},
        "doelen": gebied["doelen_uit_toekomstbeeld"],
        "ind": ind,
        "bronnen": bronnen,
        "dedupe": dedupe,
        "sweep": sweep,
        "zones": zones_payload,
        "map": {"groen": groen, "verhard": verhard, "water": water,
                "spoor": spoor, "panden": panden, "bomen": bomen},
    }


def _publiek_auth(auth: dict) -> dict:
    """Sim-embed is een publiek artefact: mandaatdetails blijven achter
    (SEC-05-geest, net als bij de events) — alléén het aantal gaat mee."""
    return {**{k: v for k, v in auth.items() if k != "mandaten"},
            "mandaatAantal": len(auth.get("mandaten", []))}


# ---------------------------------------------------------------------------
# Gent-tab: kaartpanel (F-kaart) — projectie, omleiding-buffer en routekeuze.
# Alle geometrie komt uit de broncache (fixtures/source/kaart.json) en de
# echte Gentse zone-lagen; de build rekent offline en levert kant-en-klare
# SVG-paden zodat de simulatie zelf geen geo-logica nodig heeft.

KAART_VIEWBOX = (720.0, 520.0)
KAART_BUFFER_M = 150.0


def _gis_zones_module():
    gent_root = ROOT / "poc-gent"
    if str(gent_root) not in sys.path:
        sys.path.insert(0, str(gent_root))
    from adapters import gis_zones
    return gis_zones


def _grens_ringen(grens):
    if not grens:
        return []
    if grens.get("type") == "Polygon":
        return [[tuple(p) for p in grens["coordinates"][0]]]
    if grens.get("type") == "MultiPolygon":
        return [[tuple(p) for p in poly[0]] for poly in grens["coordinates"]]
    return []


def _kaart_bbox(grens, extra_punten):
    """Zoom op de route zelf: bounding box over routes, markers en innames met
    een relatieve marge (minimaal een kwartstraat); de gemeentegrens en de
    zone-lagen worden er randvullend uitgeknipt (context buiten de viewbox)."""
    lons = [c[0] for c in extra_punten]
    lats = [c[1] for c in extra_punten]
    if not lons:
        for ring in _grens_ringen(grens):
            lons += [lon for lon, _ in ring]
            lats += [lat for _, lat in ring]
    if not lons:
        return 3.63, 50.99, 3.83, 51.16  # Gent als vangnet
    marge = max(0.004, 0.16 * (max(lons) - min(lons)), 0.16 * (max(lats) - min(lats)))
    return min(lons) - marge, min(lats) - marge, max(lons) + marge, max(lats) + marge


def _maak_projectie(bbox, viewbox=KAART_VIEWBOX):
    """WGS84 → SVG met breedtegraad-correctie (cos-lat) en behoud van aspect;
    het resultaat centreert binnen de viewbox."""
    lon_min, lat_min, lon_max, lat_max = bbox
    breedte, hoogte = viewbox
    cos_lat = math.cos(math.radians((lat_min + lat_max) / 2))
    schaal = min(breedte / max((lon_max - lon_min) * cos_lat, 1e-9),
                 hoogte / max(lat_max - lat_min, 1e-9))
    x0 = (breedte - (lon_max - lon_min) * cos_lat * schaal) / 2
    y0 = (hoogte - (lat_max - lat_min) * schaal) / 2

    def project(coord):
        lon, lat = coord[0], coord[1]
        return (round(x0 + (lon - lon_min) * cos_lat * schaal, 1),
                round(y0 + (lat_max - lat) * schaal, 1))

    return project


def _pad_ringen(ringen, project):
    delen = []
    for ring in ringen:
        punten = [project(coord) for coord in ring]
        delen.append("M " + " L ".join(f"{x} {y}" for x, y in punten) + " Z")
    return " ".join(delen)


def _pad_lijn(punten, project):
    lijst = [project(coord) for coord in punten]
    return "M " + " L ".join(f"{x} {y}" for x, y in lijst)


def _afstand_tot_route(punt, punten):
    """Minimale afstand in meters van punt tot de routepolylijn
    (equirectangulaire benadering — nauwkeurig genoeg op stadsniveau)."""
    lon0, lat0 = punt
    coslat = math.cos(math.radians(lat0))
    beste = float("inf")
    for (lon1, lat1), (lon2, lat2) in zip(punten, punten[1:]):
        x1, y1 = (lon1 - lon0) * 111320 * coslat, (lat1 - lat0) * 110540
        x2, y2 = (lon2 - lon0) * 111320 * coslat, (lat2 - lat0) * 110540
        dx, dy = x2 - x1, y2 - y1
        lengte2 = dx * dx + dy * dy
        teller = -(x1 * dx + y1 * dy)
        t = 0.0 if lengte2 == 0 else max(0.0, min(1.0, teller / lengte2))
        beste = min(beste, math.hypot(x1 + t * dx, y1 + t * dy))
    return beste


def kies_gewenste_route(routes, innames, buffer_m=KAART_BUFFER_M, doel=None):
    """De door Gent gewenste route: het minst vermijdbare innames binnen de
    omleidingsbuffer; bij gelijkspel de primaire (snelste) route. Innames bij
    het gedeelde eindpunt zijn onvermijdelijk en tellen dus niet mee voor de
    keuze (ze blijven wél zichtbaar als 'op route'). Retourneert
    (gewenst-label, {label: [innames op die route]})."""
    tellingen = {label: [i for i in innames
                         if _afstand_tot_route(i["coord"], route["punten"]) <= buffer_m]
                 for label, route in routes.items() if route}
    if not tellingen:
        return None, {}
    vermijdbaar = [i for i in innames
                   if doel is None or _afstand_tot_route(i["coord"], [doel, doel]) > buffer_m]
    keuze = {label: [i for i in rij if i in vermijdbaar] for label, rij in tellingen.items()}
    gewenst = min(keuze, key=lambda label: (len(keuze[label]), label != "primaire"))
    return gewenst, tellingen


def _zone_kruisingen(punten, zones):
    """Kruist de route een zone-laag? (sampling van de routepunten tegen de
    echte polygonen via de poc-gent GIS-helper)."""
    gis = _gis_zones_module()
    uit = {laag: False for laag in zones}
    for laag, ringen in zones.items():
        for coord in punten[::2]:
            if any(gis.point_in_ring(coord[0], coord[1], ring) for ring in ringen):
                uit[laag] = True
                break
    return uit


def _kaart_blok(kaart, zones, pid):
    """Kaartpaneel-data voor één persona: start (VKBO-bedrijfsadres waar het
    kenteken geregistreerd staat), doel (werkadres), beide routes, de door
    Gent gewenste variant, innames mét opRoute-vlaggen en kant-en-klare
    SVG-paden. Persona's zonder routecache (maria) krijgen None."""
    route = (kaart.get("routes") or {}).get(pid)
    bedrijf = (kaart.get("bedrijven") or {}).get(pid)
    if not route or not bedrijf or "coord" not in bedrijf:
        return None
    innames = kaart.get("innames") or []
    labels = {"primaire": route.get("primaire"), "alternatief": route.get("alternatief")}
    gewenst, tellingen = kies_gewenste_route(labels, innames, doel=route["doelCoord"])
    if gewenst is None:
        return None
    grens = kaart.get("grens")
    vangnet = [bedrijf["coord"], route["doelCoord"]] + [i["coord"] for i in innames]
    for res in labels.values():
        if res:
            vangnet += res["punten"][::2]
    project = _maak_projectie(_kaart_bbox(None, vangnet))
    op_gewenst = {i["id"] for i in tellingen.get(gewenst, [])}
    omzeild = {i["id"] for label, rij in tellingen.items() if label != gewenst
               for i in rij if i["id"] not in op_gewenst}
    return {
        "start": {"label": bedrijf["naam"], "adres": bedrijf["adres"]},
        "doel": route["doel"],
        "gewenst": gewenst,
        "routes": [{"label": label, "gewenst": label == gewenst,
                    "afstand_m": res["afstand_m"], "duur_s": res["duur_s"]}
                   for label, res in labels.items() if res],
        "omzeil": [f"{i['straat']} ({i['type']}, tot {i['tot']})"
                   for i in innames if i["id"] in omzeild],
        "innames": [{**i, "opRoute": {label: i in rij for label, rij in tellingen.items()}}
                    for i in innames],
        "zones": _zone_kruisingen(labels[gewenst]["punten"], zones),
        "svg": {"viewbox": [0, 0, int(KAART_VIEWBOX[0]), int(KAART_VIEWBOX[1])],
                "grens": _pad_ringen(_grens_ringen(grens), project) if grens else "",
                "zones": {laag: _pad_ringen(ringen, project) for laag, ringen in zones.items()},
                "routes": {label: (_pad_lijn(res["punten"], project) if res else "")
                           for label, res in labels.items()},
                "start": project(bedrijf["coord"]),
                "doel": project(route["doelCoord"]),
                "innames": [project(i["coord"]) for i in innames]},
        "bron": ("route & kaart: OSRM + Nominatim op OpenStreetMap (ODbL) · zones: Stad Gent "
                 "open data (Modellicentie Gratis Hergebruik) · bedrijfsadres: VKBO/KBO "
                 "open register · innames: GIPOD-mock (productiepad: GIPOD-LDES)"),
    }


def _verrijk_met_en(p: dict) -> dict:
    """Presentatievertaling voor de NL/EN-toggle: NL blijft leidend, elke
    getoonde tekst krijgt een *En-twin (vertaal_gent.vt; zie volledigheidstest)."""
    p["labelEn"] = vt(p["label"])
    p["situatieschetsEn"] = vt(p["situatieschets"])
    p["statusEn"] = VT_STATUS.get(p["status"], p["status"])
    p["outcomeEn"] = {"paden": "paths", "escalatie": "escalation"}.get(p["outcome"], p["outcome"])
    for stap in p["steps"]:
        stap["titleEn"] = vt(stap["title"])
        stap["dataUsedEn"] = [vt(d, streng=False) for d in stap.get("dataUsed", [])]
        if stap.get("handover"):
            stap["handover"] = {**stap["handover"], "reasonEn": vt(stap["handover"]["reason"])}
    for uitleg in p.get("uitleg", []):
        uitleg["tekstEn"] = vt(uitleg["tekst"])
    for uitslag in p["validatie"]["transacties"]:
        for bevinding in uitslag.get("bevindingen", []):
            bevinding["meldingEn"] = vt(bevinding["melding"])
    vervolg = ((p.get("submission") or {}).get("vervolgsamenvatting")) or None
    if vervolg:
        vervolg["gereedEn"] = [vt(regel) for regel in vervolg.get("gereed", [])]
        vervolg["openEn"] = [vt(regel) for regel in vervolg.get("open", [])]
    documenten = (p.get("submission") or {}).get("documenten")
    if documenten:
        documenten["statusEn"] = {"volledig": "complete", "onvolledig": "incomplete",
                                  "n.v.t.": "n/a"}.get(documenten["status"], documenten["status"])
        for bevinding in documenten.get("bevindingen", []):
            bevinding["meldingEn"] = vt(bevinding["melding"])
    if p.get("kaart"):
        p["kaart"]["bronEn"] = vt(p["kaart"]["bron"])
        p["kaart"]["omzeilEn"] = [vt(regel) for regel in p["kaart"].get("omzeil", [])]
    return p


# Persona-filter per Gent-pakket: het burgerpakket deelt de fixture-ruimte,
# maar het tab toont alléén de persona's van de gekozen levensgebeurtenis.
GENT_PACKAGE_PERSONAS = {
    "gent-mobiliteit-ondernemer": ("sanne", "ahmed", "maria", "fatima", "jeroen",
                                   "ellen", "dirk", "wim", "nadia", "ilse", "hanne"),
    "gent-verhuizen-burger": ("lisa", "tomas", "farah", "noor", "emma", "yana", "robrecht"),
    "gent-kot-verhuurder": ("wouter", "saartje", "gregory", "lea", "milan", "karel"),
    "gent-evenement-organisator": ("fien", "mo", "lorne", "nathalie", "gil", "jef"),
}


def _kaart_blok_kot(kaart, zones, pid):
    """Kotkaart (GT-KOT-01): de benoemde kotzone rond het kotadres — geen
    routes/innames; de zone-nám komt uit het gisCheck-attribuut."""
    entry = (kaart.get("personas") or {}).get(pid)
    if not entry:
        return None
    coord = entry["coord"]
    kot_zones = {laag: ringen for laag, ringen in zones.items() if laag == "gent-kotzone"}
    project = _maak_projectie(_kaart_bbox(kaart.get("grens"), [coord]))
    gis = _gis_zones_module()
    ring_attributen = gis.load_ring_attributen(ROOT / "poc-gent")
    zone_uit = {laag: gis.attribuut_result(kot_zones, ring_attributen, laag, coord[0], coord[1])
                for laag in kot_zones}
    zone_naam = next((naam for naam in zone_uit.values() if naam not in ("in", "niet-in")), None)
    start = project(coord)
    return {"mode": "kot",
            "start": {"label": "kotadres", "adres": entry["adres"], "coord": coord},
            "doel": entry["adres"], "zones": zone_uit, "zoneNaam": zone_naam,
            "gewenst": None, "routes": [], "innames": [], "omzeil": [],
            "svg": {"grens": _pad_ringen(_grens_ringen(kaart.get("grens")), project)
                    if kaart.get("grens") else None,
                    "zones": {laag: _pad_ringen(ringen, project) for laag, ringen in kot_zones.items()},
                    "start": [start[0], start[1]], "routes": None, "innames": []},
            "bron": "kotzones: Stad Gent open data (Modellicentie Gratis Hergebruik) · "
                    "gemeentegrens: OSM/Nominatim (ODbL)"}


def _kaart_blok_burger(kaart, zones, pid):
    """Burgerkaart (GT-VERH-01): regeling-zones (bewoners, tarief, LEZ) rond
    de nieuwe woning — geen routes/innames (dat is ondernemersmobiliteit)."""
    entry = (kaart.get("personas") or {}).get(pid)
    if not entry:
        return None
    coord = entry["coord"]
    burger_zones = {laag: ringen for laag, ringen in zones.items()
                    if laag in ("gent-bewonerszone", "gent-parkeertariefzone", "gent-lez")}
    project = _maak_projectie(_kaart_bbox(kaart.get("grens"), [coord]))
    gis = _gis_zones_module()
    zone_uit = {laag: ("in" if any(gis.point_in_ring(coord[0], coord[1], ring) for ring in ringen)
                       else "niet-in") for laag, ringen in burger_zones.items()}
    start = project(coord)
    return {"mode": "burger",
            "start": {"label": "nieuwe woning", "adres": entry["adres"], "coord": coord},
            "doel": entry["adres"], "zones": zone_uit, "gewenst": None,
            "routes": [], "innames": [], "omzeil": [],
            "svg": {"grens": _pad_ringen(_grens_ringen(kaart.get("grens")), project)
                    if kaart.get("grens") else None,
                    "zones": {laag: _pad_ringen(ringen, project)
                              for laag, ringen in burger_zones.items()},
                    "start": [start[0], start[1]], "routes": None, "innames": []},
            "bron": "zones & kalender: Stad Gent open data (Modellicentie Gratis Hergebruik) · "
                    "gemeentegrens: OSM/Nominatim (ODbL)"}


def _kaart_blok_event(kaart, zones, pid):
    """Eventkaart (GT-EVT-01): LEZ-zone rond de eventlocatie — bezoekers- en
    leveranciersverkeer; geen routes/innames."""
    entry = (kaart.get("personas") or {}).get(pid)
    if not entry:
        return None
    coord = entry["coord"]
    evt_zones = {laag: ringen for laag, ringen in zones.items() if laag == "gent-lez"}
    project = _maak_projectie(_kaart_bbox(kaart.get("grens"), [coord]))
    gis = _gis_zones_module()
    zone_uit = {laag: gis.zone_result(evt_zones, laag, coord[0], coord[1]) for laag in evt_zones}
    start = project(coord)
    return {"mode": "event",
            "start": {"label": "eventlocatie", "adres": entry["adres"], "coord": coord},
            "doel": entry["adres"], "zones": zone_uit, "gewenst": None,
            "routes": [], "innames": [], "omzeil": [],
            "svg": {"grens": _pad_ringen(_grens_ringen(kaart.get("grens")), project)
                    if kaart.get("grens") else None,
                    "zones": {laag: _pad_ringen(ringen, project) for laag, ringen in evt_zones.items()},
                    "start": [start[0], start[1]], "routes": None, "innames": []},
            "bron": "lez: Stad Gent open data (Modellicentie Gratis Hergebruik) · "
                    "gemeentegrens: OSM/Nominatim (ODbL)"}


def build_gent(package_id: str = "gent-mobiliteit-ondernemer") -> dict:
    """Gent EUROPAI-piloot voor tab 5: deterministische replay (fase 1+2+3) per
    persona, gegenereerd door de echte poc-gent-engine tijdens de build. De
    events-ketting wordt geverifieerd; in de embedded data zitten alléén
    event-soorten en -volgnummers, geen persoonswaarden (SEC-05-geest).
    Eén Gent-tab, twee levensgebeurtenissen: de dropdown wisselt het pakket
    (ondernemer GT-MOB-01 met routes/innames · burger GT-VERH-01 met
    regeling-zones rond de nieuwe woning)."""
    gent_root = ROOT / "poc-gent"
    if not (gent_root / "run.py").is_file():
        sys.exit(f"missing poc-gent at {gent_root}")
    sys.path.insert(0, str(gent_root))
    try:
        from adapters import gis_zones
        from core import catalog, events, pipeline
    finally:
        sys.path.remove(str(gent_root))

    kaart_naam, kaart_blok_fn = {
        "gent-mobiliteit-ondernemer": ("kaart.json", _kaart_blok),
        "gent-verhuizen-burger": ("kaart-burger.json", _kaart_blok_burger),
        "gent-kot-verhuurder": ("kaart-kot.json", _kaart_blok_kot),
        "gent-evenement-organisator": ("kaart-event.json", _kaart_blok_event),
    }[package_id]
    kaart_pad = gent_root / "fixtures" / "source" / kaart_naam
    kaart = json.loads(kaart_pad.read_text(encoding="utf-8")) if kaart_pad.is_file() else None
    zone_ringen = gis_zones.load_zones(gent_root)
    pkg = catalog.load_package(gent_root, package_id)
    personas = pipeline.load_personas(gent_root)
    versies = gis_zones.load_layer_versies(gent_root)
    pakket_personas = GENT_PACKAGE_PERSONAS[package_id]

    out_personas = []
    for pid, persona in personas.items():
        if pid not in pakket_personas:
            continue
        run, log = pipeline.run_replay(gent_root, package_id, pid)
        t = run["transaction"]
        out_personas.append({
            "id": pid,
            "label": persona["label"]["nl"],
            "edge": persona.get("edge"),
            "situatieschets": persona["situatieschets"],
            "status": t["status"],
            "outcome": t["routing"]["outcome"],
            "transactions": t["routing"]["paths"]["transactions"],
            "uitleg": t["routing"]["uitleg"],
            "steps": [
                {"stepId": s["stepId"], "title": s["title"], "actor": s["actor"],
                 "genAiTestPoint": s["genAiTestPoint"], "dataUsed": s["dataUsed"],
                 "consent": s["consent"], "handover": s["handover"], "prov": s["prov"]}
                for s in run["steps"]
            ],
            "context": t["context"],
            "auth": _publiek_auth(t["auth"]),
            "prefill": t["prefill"],
            "validatie": t["validatie"],
            "h1": t["h1"],
            "h3": t["h3"],
            "kaart": kaart_blok_fn(kaart, zone_ringen, pid) if kaart else None,
            "submission": t["submission"],
            "events": [{"seq": e["seq"], "kind": e["kind"]} for e in log],
            "chainOk": events.verify_chain(log),
        })

    out_personas = [_verrijk_met_en(persoon) for persoon in out_personas]
    return {
        "serviceTitelsEn": {k: vt(v) for k, v in {
            dienst: pkg.manifest["services"][dienst].get("titel", dienst)
            for dienst in pkg.manifest["services"]}.items()},
        "packageId": pkg.manifest["packageId"],
        "lifeEventCode": pkg.manifest["lifeEventCode"],
        "version": pkg.manifest["version"],
        "serviceTitels": {k: v.get("titel") for k, v in pkg.manifest["services"].items()},
        "bronversies": versies,
        "personas": out_personas,
    }


def _kotregister_blok(gent_root: Path) -> dict | None:
    """Echt Kotatgent-register (publieke kotenzoeker): willekeurig-kot-kaart
    in de simulatie. Beelden verwijzen relatief naar simulation/kot-beelden/
    (gekopieerd in main); titel/adres/prijs zijn brontekst en blijven NL.
    Per uniek kotadres draait de build een echte engine-run (persona wouter
    met adres-override): selectie in de simulatie toont dus aanvraag, kotzone,
    afval en ontvangstbewijs van dat kot (config-is-data, geen client-logica)."""
    pad = gent_root / "fixtures" / "source" / "kotregister.json"
    if not pad.is_file():
        return None
    register = json.loads(pad.read_text(encoding="utf-8"))
    sys.path.insert(0, str(gent_root))
    try:
        from adapters import gis_zones
        from core import catalog, pipeline
    finally:
        sys.path.remove(str(gent_root))
    zones = gis_zones.load_zones(gent_root)
    ring_attributen = gis_zones.load_ring_attributen(gent_root)
    grens_pad = gent_root / "fixtures" / "source" / "kaart-kot.json"
    grens = json.loads(grens_pad.read_text(encoding="utf-8")).get("grens") \
        if grens_pad.is_file() else None
    lagen = _kotregister_kaartlagen(gent_root, gis_zones, zones, ring_attributen, grens)
    project, zonepaden, grens_pad = lagen["project"], lagen["zonepaden"], lagen["grens"]
    adressen = json.loads((gent_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    uit_koten = []
    runs: dict[str, dict] = {}
    for kot in register.get("koten", []):
        sleutel = f"{kot['adres']}, Gent"
        if sleutel not in runs:
            coord = adressen.get(sleutel)
            run_slice = _kot_run(gent_root, pipeline, sleutel)
            zone_naam, start = None, None
            if coord:
                kot_zones = {laag: ringen for laag, ringen in zones.items()
                             if laag == "gent-kotzone"}
                zone_naam = next(
                    (naam for naam in
                     (gis_zones.attribuut_result(kot_zones, ring_attributen, laag,
                                                 coord[0], coord[1])
                      for laag in kot_zones)
                     if naam not in ("in", "niet-in")), None)
                x, y = project(coord)
                start = [x, y]
            runs[sleutel] = {"run": run_slice, "zoneNaam": zone_naam, "startCoord": start}
        uit_koten.append({"titel": kot["titel"], "adres": kot["adres"], "type": kot.get("type"),
                          "prijs": kot.get("prijs"),
                          "conformiteitsattest": kot.get("conformiteitsattest"),
                          "beeld": kot.get("beeld"), "url": kot.get("url"),
                          **runs[sleutel]})
    return {"bron": register.get("bron"),
            "totaalInDatabase": register.get("totaalInDatabase"),
            "beschikbaar": register.get("beschikbaarGepubliceerd"),
            "grens": grens_pad, "zonepaden": zonepaden,
            "koten": uit_koten}


def _kotregister_kaartlagen(gent_root, gis, zones, ring_attributen, grens) -> dict:
    """Eén stadsbrede projectie voor álle kot-kaarten: 20 zone-paden één keer
    berekend (in plaats van per adres), per kot volstaan zoneNaam + start."""
    project = _maak_projectie(_kaart_bbox(grens, []))
    zonepaden: dict[str, str] = {}
    for laag, ringen in zones.items():
        if laag != "gent-kotzone":
            continue
        per_naam: dict[str, list] = {}
        for idx, ring in enumerate(ringen):
            naam = (ring_attributen.get(laag) or [None] * len(ringen))[idx]
            per_naam.setdefault(naam or "onbekend", []).append(ring)
        for naam, naam_ringen in per_naam.items():
            zonepaden[naam] = _pad_ringen(naam_ringen, project)
    return {"project": project,
            "zonepaden": zonepaden,
            "grens": _pad_ringen(_grens_ringen(grens), project) if grens else None}


def _kot_run(gent_root, pipeline, adres_sleutel: str) -> dict:
    """Compacte run-slice voor een kotadres; adres zonder geocode-cache ->
    escalatie-slice (eerlijk zichtbaar)."""
    try:
        run, _events = pipeline.run_replay(gent_root, "gent-kot-verhuurder", "wouter",
                                           {"address": adres_sleutel})
    except Exception:
        return {"status": "onbekend-adres", "outcome": "escalatie",
                "contextRegels": [], "formulier": None, "validatie": None,
                "ontvangst": [], "vervolg": {"gereed": [], "open": [],
                                             "gereedEn": [], "openEn": []}}
    tr = run["transaction"]
    formulier = (tr["prefill"]["transacties"] or [None])[0]
    validatie = (tr["validatie"]["transacties"] or [None])[0]
    if validatie:
        for bevinding in validatie.get("bevindingen", []):
            bevinding["meldingEn"] = vt(bevinding["melding"])
    vervolg = tr["submission"]["vervolgsamenvatting"]
    return {
        "status": tr["status"], "outcome": tr["routing"]["outcome"],
        "contextRegels": tr["context"]["regels"],
        "formulier": formulier, "validatie": validatie,
        "ontvangst": tr["submission"]["ontvangst"]["transacties"],
        "vervolg": {"gereed": vervolg["gereed"], "open": vervolg["open"],
                    "gereedEn": [vt(r) for r in vervolg["gereed"]],
                    "openEn": [vt(r) for r in vervolg["open"]]},
    }


def _kot_coord(gent_root: Path, adres_sleutel: str) -> list[float] | None:
    adressen = json.loads((gent_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    return adressen.get(adres_sleutel)


GENT_ONLY_PAD = "gent-simulatie.html"


def _beelden_als_data_uris(kotregister: dict) -> int:
    """Kot-foto's inladen als data-URIs zodat het Gent-bestand één enkele
    zelfstandige bijlage is (geen map met assets nodig op de laptop)."""
    beelden_map = ROOT / "poc-gent" / "fixtures" / "source"
    ingebed = 0
    for kot in kotregister.get("koten", []):
        if not kot.get("beeld"):
            continue
        pad = beelden_map / kot["beeld"]
        if pad.is_file():
            kot["beeld"] = "data:image/jpeg;base64," + base64.b64encode(pad.read_bytes()).decode("ascii")
            ingebed += 1
        else:
            kot["beeld"] = None
    return ingebed


def _patch_gent_only(tpl: str) -> str:
    """Template-injecties voor de Gent-only-variant: alleen het Gent-tabblad
    actief en zichtbaar (tab 1/2/4/6/7 weg), overige PoC-initialisatie uit
    (hun data ontbreekt in het zelfstandige bestand)."""
    vervangingen = [
        ("<title>LDT Toolbox — pipeline simulation (PoC-1 · PoC-2)</title>",
         "<title>Gent · EUROPAI transactiepiloot — simulatie</title>"),
        ('<div class="tab active" id="tab1" onclick="switchTab(1)">PoC-1 · wind, Utrecht</div>',
         '<div class="tab" id="tab1" style="display:none"></div>'),
        ('<div class="tab" id="tab2" onclick="switchTab(2)">PoC-2 · BP→OP, Eindhoven</div>',
         '<div class="tab" id="tab2" style="display:none"></div>'),
        ('<div class="tab" id="tab4" onclick="switchTab(4)"><span class="tekst-nl">Breda · vijf-waarden</span><span class="tekst-en">Breda · five-value</span></div>',
         '<div class="tab" id="tab4" style="display:none"></div>'),
        ('<div class="tab" id="tab6" onclick="switchTab(6)"><span class="tekst-nl">Veenendaal · Spoorzone</span><span class="tekst-en">Veenendaal · Spoorzone</span></div>',
         '<div class="tab" id="tab6" style="display:none"></div>'),
        ('<div class="tab" id="tab7" onclick="switchTab(7)">DSO ↔ RegelRecht</div>',
         '<div class="tab" id="tab7" style="display:none"></div>'),
        ('<div class="tab" id="tab5"', '<div class="tab active" id="tab5"'),
        ('<div class="tabkop on" id="kop1">', '<div class="tabkop" id="kop1">'),
        ('<div class="tabkop" id="kop5">', '<div class="tabkop on" id="kop5">'),
        ('<section class="view active" id="view1">', '<section class="view" id="view1">'),
        ('<section class="view" id="view5">', '<section class="view active" id="view5">'),
        ("let sim1, sim2, sim4, sim5, sim6, sim7, active=1;",
         "let sim1, sim2, sim4, sim5, sim6, sim7, active=5;"),
        # top-level data-bindingen (bbox-IIFE e.d. draaien bij het laden):
        # stubs, want de PoC-data ontbreekt in de Gent-only-variant
        ("const P1 = DATA.poc1;", "const P1 = {aoi:{geo:[],areaKm2:0}, tracks:{}};"),
        ("const P2 = DATA.poc2;", "const P2 = {grid:[], qa:[]};"),
        ("const P4 = DATA.poc4;", "const P4 = {};"),
        # veenendaal-view: DATA.veenendaal ontbreekt in Gent-only — VD neutraal
        # en de top-level kaartkader-IIFE's (VFRAME/VW6/VH6/VPROJ, die VD
        # uitpakken) eruit; de view-6-functies worden niet meer aangeroepen
        ("const VD = DATA.veenendaal;", "const VD = null; /* gent-only: geen veenendaal-tab */"),
        ("const VFRAME=(()=>{ const [x0,y0,x1,y1]=VD.gebied.bbox;\n"
         "  return [x0-40, y0-40, x1+40, y1+40]; })();\n"
         "const VW6=980, VH6=Math.round(VW6*(VFRAME[3]-VFRAME[1])/(VFRAME[2]-VFRAME[0]));\n"
         "const VPROJ=(()=>{ const [x0,y0,x1,y1]=VFRAME;\n"
         "  const sx=VW6/(x1-x0), sy=VH6/(y1-y0);\n"
         "  return (x,y)=>[(x-x0)*sx, VH6-(y-y0)*sy]; })();\n",
         "/* gent-only: kaartkader-IIFE's uit — VD is null, view-6-code wordt niet aangeroepen */\n"),
        # laya-view bindt top-level op P1/P2 (kind, meta, questions, eval)
        ("const LAYA_DS = { eindhoven: P2.laya, utrecht: P1.laya };",
         "const LAYA_DS = { eindhoven: {kind: 'eindhoven', meta:{}, questions:[], eval:{}, "
         "tok:{stop:[], suf:[]}, fp:{}, nGram:{}, preds:{}, pad:{}}, "
         "utrecht: {kind: 'utrecht', meta:{}, questions:[], eval:{}, "
         "tok:{stop:[], suf:[]}, fp:{}, nGram:{}, preds:{}, pad:{}} };"),
        # PoC-init-regels: view 1/2/4 én view 6 (sim6, onbewaakt) uit — het
        # DKB-blok (view 7) is zelf al bewaakt en DATA.dsokb ontbreekt hier
        ("buildRail1(); buildStatic1(); sim1=makeSim1(); buildSim2();\n", ""),
        ("buildRail4(); buildStatic4(); sim4=makeSim4(); sim1.prog();\n", ""),
        ("buildRail6(); buildStatic6(); buildSweep6(); vWire(); sim6=makeSim6(); sim6.prog();\n", ""),
        # laya- en breda-init draaien top-level tegen de stubs
        ("\nbuildLayaStatic(); renderGate();", "\n/* gent-only: laya-init uit */"),
        # deeplink: tab 1–7 bestaan hier niet als views — altijd naar Gent (5)
        ("else if(t>=1&&t<=7) switchTab(t);", "else if(t>=1&&t<=7) switchTab(5);"),
    ]
    for oud, nieuw_stuk in vervangingen:
        assert oud in tpl, f"gent-only patchanker ontbreekt: {oud[:60]}"
        tpl = tpl.replace(oud, nieuw_stuk, 1)
    return tpl


def bouw_gent_only() -> int:
    """Volledig zelfstandige Gent-simulatie als één HTML-bestand: drie
    levensgebeurtenissen achter de dropdown, kotfoto's ingebed."""
    data = {"gent": build_gent(),
            "gentBurger": build_gent("gent-verhuizen-burger"),
            "gentKot": build_gent("gent-kot-verhuurder"),
            "gentEvent": build_gent("gent-evenement-organisator")}
    kotregister = _kotregister_blok(ROOT / "poc-gent")
    if kotregister:
        data["gentKot"]["kotregister"] = kotregister
    feesten_pad = ROOT / "poc-gent" / "fixtures" / "source" / "feestenkalender.json"
    if feesten_pad.is_file():
        feesten = json.loads(feesten_pad.read_text(encoding="utf-8"))
        data["gentEvent"]["feesten"] = {"versie": feesten.get("versie"),
                                        "periode": feesten.get("periode"),
                                        "evenementen": feesten.get("evenementen")}
        ingebed = _beelden_als_data_uris(kotregister)
    else:
        ingebed = 0
    tpl = _patch_gent_only(TEMPLATE.read_text(encoding="utf-8"))
    marker = "/*__DATA__*/"
    if marker not in tpl:
        sys.exit("template is missing the /*__DATA__*/ marker")
    html = tpl.replace(marker, json.dumps(data, ensure_ascii=False, separators=(",", ":")), 1)
    uit = ROOT / "simulation" / GENT_ONLY_PAD
    uit.write_text(html, encoding="utf-8")
    print(f"wrote {uit}  ({uit.stat().st_size/1024/1024:.1f} MB, {ingebed} kotfoto's ingebed)")
    return 0


def build_dso_kb() -> dict:
    """DSO↔RegelRecht-kennisbank → displayblok (Tab 7). Leest alléén cache-artefacten."""
    if not DSO_OUT.is_dir():
        sys.exit(f"missing dso_overlap cache under {DSO_OUT}")
    instrumenten = []
    kg_instrumenten = []   # hulplijst voor build_kg7 — verlaat de functie niet
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
        # geo-kaartregels: alleen exporteren wat echt uitgevoerd is — een
        # punt-in-GIO-toets met getoetst 0 (GIO's niet filename-koppelbaar,
        # cf. Utrecht) is "niet uitgevoerd", geen "0/0"-regel waard.
        geo_regels = {}
        v = (geo or {}).get("validatie") or {}
        if (v.get("getoetst") or 0) > 0:
            geo_regels = {"getoetst": v.get("getoetst"), "overeenstemming": v.get("overeenstemming")}
        na = (((geo or {}).get("sweep") or {}).get("naamAfstemming") or {})
        if na:
            geo_regels["naamOvereenkomend"] = na.get("naamOvereenkomend")
            geo_regels["naamSweepGmls"] = na.get("sweepGmls")

        kg_instrumenten.append({"id": iid, "locatie": lid, "_overlapArticles": o.get("articles") or []})
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
    return {"instrumenten": instrumenten, "kg": build_kg7(kg_instrumenten)}


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
            i_art = len(nodes) - 1
            for i, w in enumerate(e["rts"][:3]):
                n_rt = _kg_node("rt", y + i * 12, w.rsplit("__", 2)[-1], stat_kleur, 5.1,
                                _kg_tip(f"regeltekst {w}", f"artikel {art}"), f"rt:{w}")
                nodes.append(n_rt)
                edges.append({"s": i_art, "t": len(nodes) - 1, "st": 5.1,
                              "cls": "kge-art", "d": _kg_pad(n_art, n_rt)})
            for rg in e["regels"][:3]:
                n_jr = _kg_node("jr", y + 2, f"{rg['id'][:18]}" + ("…" if len(rg["id"]) > 18 else ""),
                                "kgn-blauw", 5.2,
                                _kg_tip(f"juridische regel {rg['id']}",
                                        f"activiteit: {rg['act'] or '—'} ({rg['kw'] or '—'})"), f"jr:{rg['id']}")
                nodes.append(n_jr)
                i_jr = len(nodes) - 1
                edges.append({"s": i_art, "t": i_jr, "st": 5.2,
                              "cls": "kge-rt", "d": _kg_pad(n_art, n_jr)})
                if rg["act"]:
                    n_act = _kg_node("act", y + 2, rg["act"][:22],
                                     {"vergunning": "kgn-amber", "melding": "kgn-cyaan"}.get(
                                         _KG_KW.get(rg["kw"] or "", "anders"), "kgn-grijs"), 5.3,
                                     _kg_tip(f"activiteit {rg['act']}", f"kwalificatie: {rg['kw'] or '—'}"),
                                     f"act:{rg['act']}")
                    nodes.append(n_act)
                    edges.append({"s": i_jr, "t": len(nodes) - 1, "st": 5.3,
                                  "cls": "kge-jr", "d": _kg_pad(n_jr, n_act)})
                for li in rg["locs"][:2]:
                    loc = locaties[li]
                    n_loc = _kg_node("loc", y + 8, (loc["noemer"] or "?")[:20],
                                     "kgn-grijs", 5.3,
                                     _kg_tip(f"{loc['type']}: {loc['noemer']}", loc["id"],
                                             f"gml: {loc['gml'] or 'niet koppelbaar'}"), f"loc:{li}")
                    nodes.append(n_loc)
                    i_loc = len(nodes) - 1
                    edges.append({"s": i_jr, "t": i_loc, "st": 5.3,
                                  "cls": "kge-jr", "d": _kg_pad(n_jr, n_loc)})
                    if loc["gml"]:
                        n_gio = _kg_node("gio", y + 8, loc["gml"][-18:], "kgn-groen", 5.4,
                                         _kg_tip(f"GIO {loc['gml']}", "officieel uitwisselpakket"), f"gio:{li}")
                        nodes.append(n_gio)
                        edges.append({"s": i_loc, "t": len(nodes) - 1, "st": 5.4,
                                      "cls": "kge-loc", "d": _kg_pad(n_loc, n_gio)})
        h = max(n["y"] for n in nodes) + 30 if nodes else 120
        uit[inst["id"]] = {"top": top,
                           "keuze": [a for a, _ in gerangschikt[:KG_KEUZE_CAP]],
                           "locaties": locaties, "artikelen": artikelen,
                           "overzicht": {"n": nodes, "e": edges, "h": h,
                                         "cols": [{"x": x, "cap": KG_CAPS[c]} for c, x in KG_COLX.items()],
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


def main() -> int:
    ap = argparse.ArgumentParser(description="bouw de simulatie (of alleen het Gent-deel)")
    ap.add_argument("--gent-only", action="store_true",
                    help="bouw gent-simulatie.html: zelfstandig Gent-bestand (geen andere PoC's, "
                         "kotfoto's ingebed) — een bijlage om te mailen")
    args = ap.parse_args()
    if args.gent_only:
        return bouw_gent_only()
    for name, meta in POC1_TRACKS.items():
        if not meta["run"].is_dir():
            sys.exit(f"missing PoC-1 {name} run dir {meta['run']}")
    if not POC2_RUN.is_dir():
        sys.exit(f"missing PoC-2 run dir {POC2_RUN}")
    if not POC4_RUN.is_dir():
        sys.exit(f"missing PoC-4 run dir {POC4_RUN}")
    if not (VEENENDAAL_POC / "data" / "cache").is_dir():
        sys.exit(f"missing poc-veenendaal cache under {VEENENDAAL_POC / 'data' / 'cache'}")

    data = {"poc1": build_poc1(), "poc2": build_poc2(), "poc4": build_breda(), "gent": build_gent(),
            "gentBurger": build_gent("gent-verhuizen-burger"),
            "gentKot": build_gent("gent-kot-verhuurder"),
            "gentEvent": build_gent("gent-evenement-organisator"),
            "veenendaal": build_veenendaal(),
            "dsokb": build_dso_kb()}
    kotregister = _kotregister_blok(ROOT / "poc-gent")
    if kotregister:
        data["gentKot"]["kotregister"] = kotregister
    feesten_pad = ROOT / "poc-gent" / "fixtures" / "source" / "feestenkalender.json"
    if feesten_pad.is_file():
        feesten = json.loads(feesten_pad.read_text(encoding="utf-8"))
        data["gentEvent"]["feesten"] = {"versie": feesten.get("versie"),
                                        "periode": feesten.get("periode"),
                                        "evenementen": feesten.get("evenementen")}
        beelden_bron = ROOT / "poc-gent" / "fixtures" / "source" / "kot-beelden"
        if beelden_bron.is_dir():
            shutil.copytree(beelden_bron, OUT.parent / "kot-beelden", dirs_exist_ok=True)
    tpl = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*__DATA__*/"
    if marker not in tpl:
        sys.exit("template is missing the /*__DATA__*/ marker")
    html = tpl.replace(marker, json.dumps(data, ensure_ascii=False, separators=(",", ":")), 1)
    OUT.write_text(html, encoding="utf-8")

    n_cells = len(data["poc2"]["grid"])
    print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for name, tr in data["poc1"]["tracks"].items():
        print(f"  poc1/{name}: run {tr['runId']} — {len(tr['engine'])} engine steps + "
              f"{len(tr['markers'])} markers, final {tr['engine'][-1]['areaKm2']} km2, "
              f"{tr['cards']['normCards']} cards, {len(tr['decision'])} dt-rows, "
              f"kg {len(tr['kg']['n'])} nodes/{len(tr['kg']['e'])} edges, "
              f"sweep {len(tr.get('sweep') or [])} scenarios")
    if data["poc1"].get("bag"):
        bt = data["poc1"]["bag"]["tracks"]
        print("  bag: " + " · ".join(f"{k} {v['n']} panden ({v['bouwjaarBekend']} m.bouwjaar)" for k, v in bt.items()))
    l1 = data["poc1"]["laya"]
    e1 = l1["eval"]
    print(f"  laya1 (utrecht): {e1['n']} held-out kaarten (5 ongeziene tracks) — "
          f"status {e1['regelstatus']['hit']}/{e1['regelstatus']['n']}, "
          f"effect {e1['zone_effect']['hit']}/{e1['zone_effect']['n']}, "
          f"jurist {e1['needs_human']['hit']}/{e1['needs_human']['n']}, "
          f"werking {e1['legal_force']['hit']}/{e1['legal_force']['n']} · "
          f"{e1['abstentions']} onder de gate · {l1['meta']['latencyMs']} ms/predict")
    kg2 = data["poc2"]["kg"]
    print(f"  poc2: {n_cells} grid cells, {len(data['poc2']['samples'])} sample rows, "
          f"kb {data['poc2']['kb']['total']} relations, kg {len(kg2['e'])} edges "
          f"({kg2['c']['used']} reused by matcher)")
    p4 = data["poc4"]
    print(f"  poc4/breda: run {p4['runId']} — {p4['nBuurten']} buurten, "
          f"{len(p4['geo'])} geo, {len(p4['qa'])} golden Q&A, verdict {p4.get('verdict')}")
    g = data["gent"]
    ok = sum(1 for p in g["personas"] if p["chainOk"])
    print(f"  gent: {g['packageId']} v{g['version']} — {len(g['personas'])} persona's "
          f"(events-ketting {ok}/{len(g['personas'])} geverifieerd), "
          "statussen: " + ", ".join(f"{p['id']}={p['status']}" for p in g["personas"]))
    vd = data["veenendaal"]
    print(f"  veenendaal: run {vd['runId']} — {vd['ind']['panden_bestand']} panden, "
          f"{vd['ind']['woningen_verblijfsobjecten_proxy']} woningen-proxy, "
          f"{vd['ind']['begroeid_terrein_ha']} ha groen · kaart: "
          + " · ".join(f"{k}={len(vd['map'][k])}"
                       for k in ["groen", "verhard", "water", "spoor", "panden", "bomen"]))
    for inst in data["dsokb"]["instrumenten"]:
        d = inst["dekking"]
        drift = (inst["ververs"] or {}).get("drift", {}).get("inhoudelijkeDrift", "geen rapport")
        print(f"  dsokb/{inst['id']}: {d['dsoArtikelen']} DSO-artikelen → {d['executable']} uitvoerbaar "
              f"({100 * d['coverage']:.2f}%) · drift: {drift}")
    for iid, kg in data["dsokb"]["kg"].items():
        print(f"  dsokb/{iid}: kennisgraaf top={kg['top'][:3]} · {len(kg['artikelen'])} artikelen · "
              f"{len(kg['overzicht']['n'])} knopen/{len(kg['overzicht']['e'])} edges · "
              f"{len(kg['locaties'])} locaties")
    ly = data["poc2"]["laya"]
    ev = ly["eval"]
    m = ly["meta"]
    print(f"  laya: {m['base'].split('—')[0].strip()} fine-tuned · {m['items']['train']} train/"
          f"{m['items']['eval']} eval-items · {ev['n']} held-out artikelen — "
          f"hoofdstuk {ev['doel_hoofdstuk']['hit']}/{ev['doel_hoofdstuk']['n']}, "
          f"band {ev['match_band']['hit']}/{ev['match_band']['n']}, "
          f"jurist {ev['needs_jurist']['hit']}/{ev['needs_jurist']['n']} · "
          f"{ev['abstentions']} onder de gate · {m['latencyMs']} ms/predict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
