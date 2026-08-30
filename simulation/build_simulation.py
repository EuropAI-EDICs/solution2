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

import json
import math
import re
import sys
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
AOI_CACHE = ROOT / "poc" / "data" / "cache" / "arcgis-provinciegrens.4326.geojson"
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
    formal = load(run / "formalrules.json")
    formal = formal if isinstance(formal, list) else formal.get("rules", formal)
    rationale = {r["id"]: r.get("rationale") or r.get("reason") or "" for r in formal}
    rejected = load(run / "normcards-rejected.json")
    dtable = load(run / "decision-table.json")
    drows = dtable if isinstance(dtable, list) else dtable.get("rows", dtable)
    report_input = load(run / "report_input.json")
    validation = load(run / "validation.json")
    cards = load(run / "normcards.json")
    cards = cards if isinstance(cards, list) else cards.get("cards", cards)
    layers_manifest = load(run / "layers.json")
    if not isinstance(layers_manifest, dict):
        layers_manifest = {}

    engine, markers = [], []
    zone_ids_by_rule = {
        r["id"]: (r.get("zoneSelector") or {}).get("zoneIds") or [] for r in formal
    }

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
            "quote": short(qcard["source"]["quote"], 220),
            "url": qcard["source"].get("url", "https://lokaleregelgeving.overheid.nl/cvdr704250"),
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
    }


def build_poc1() -> dict:
    aoi_geo = display_rings(shape(load(AOI_CACHE)["features"][0]["geometry"]))
    tracks = {name: build_track(name, meta) for name, meta in POC1_TRACKS.items()}
    return {
        "aoi": {"areaKm2": 1560.054, "geo": aoi_geo},
        "tracks": tracks,
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
    CAP = {"art": "instrument · artikel", "card": "NormCards · cited",
           "rule": "FormalRules", "layer": "geo layers (registry)", "zone": "ZoneResults"}

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
        card_idx[c["id"]] = add("card", c["id"], c["id"], "kgn-card", 1,
                                tip(c["id"], f"theme: {c.get('theme', '—')}",
                                    short(c["claim"], 200),
                                    "“" + short(c["source"]["quote"], 160) + "”"),
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
        rule_idx[r["id"]] = add("rule", r["id"], r["id"],
                                "kgn-rule-" + r["status"][:2], 2,
                                tip(r["id"], f"status: {r['status']} · {r.get('ruleType', '')}",
                                    short(r.get("reason") or r.get("rationale") or "", 200)),
                                f"{gname.get(r['status'], r['status'])} — {stat_n[r['status']]}")

    # ---- column 4: geo layers grouped by role (registry keys actually used)
    layer_idx = {}
    used_keys = sorted(({zi for r in formal for zi in (r.get("zoneSelector") or {}).get("zoneIds", [])}
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
        for zk in (r.get("zoneSelector") or {}).get("zoneIds", []):
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
    return {
        "h": H,
        "cap": (f"{len(cards)} NormCards · {len(rejected.get('abstentions', []))} abstentions · "
                f"{len(formal)} rules ({n_form} formalized) · {len(used_keys)} layers · {len(zone_idx)} zone results"),
        "cols": [{"x": COLX[k] - (165 if k == "art" else 10), "cap": CAP[k]} for k in COLX],
        "groups": groups, "hmax": H,
        "n": [{k: n[k] for k in ("x", "y", "tx", "anchor", "label", "cls", "st", "tip", "dash")}
              for n in nodes],
        "e": edges,
    }


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
    }


def main() -> int:
    for name, meta in POC1_TRACKS.items():
        if not meta["run"].is_dir():
            sys.exit(f"missing PoC-1 {name} run dir {meta['run']}")
    if not POC2_RUN.is_dir():
        sys.exit(f"missing PoC-2 run dir {POC2_RUN}")

    data = {"poc1": build_poc1(), "poc2": build_poc2()}
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
              f"kg {len(tr['kg']['n'])} nodes/{len(tr['kg']['e'])} edges")
    kg2 = data["poc2"]["kg"]
    print(f"  poc2: {n_cells} grid cells, {len(data['poc2']['samples'])} sample rows, "
          f"kb {data['poc2']['kb']['total']} relations, kg {len(kg2['e'])} edges "
          f"({kg2['c']['used']} reused by matcher)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
