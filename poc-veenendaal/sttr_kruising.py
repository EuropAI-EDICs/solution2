#!/usr/bin/env python3
"""veenendaal-spoorzone kruising — scenario-toedeling ∩ officiële GIO-lagen.

Derde stap in het loket-verhaal (na `sttr.py`): de scenario-sweep wijst per
programmavariant hele BGT-vlakken toe (scenarios.py, engine-beslissing); deze
kruising snijdt die genomen vlakken met de officiële omgevingsplan-GIO-lagen
die de werkgrens bedekken (uit de sttr.py-sweep). Per scenario: welke
officiële lagen raakt de variant — hoeveel m² en hoeveel GIO-objecten.

Doctrine: rekenlaag beslist — dit is een **geometrisch feit**, geen toets:
"raakt" betekent overlappen met de toegedeelde vlakken, níet "niet
toegestaan". De conclusie-enum (Vergunningplicht/…) volgt pas met een concreet
voorstel; de koppeling specifieke STTR-vraag ↔ locatie is bij Veenendaal niet
legbaar (zie het loketvragen-rapport). Geen LLM; elke input heeft een sha256 in
manifest.json.

Gebruik:
  nldt/.venv/bin/python sttr_kruising.py
Bronnen: nieuwste scenario-runs/*-sweep (scenarios.json) · nieuwste
sttr-runs/*-loketvragen (loketvragen.json) · data/cache (BGT-vlakken +
uitwisselpakket) — alles cache-first; geen netwerk.
Uitvoer: sttr-runs/<ts>-kruising/{kruising.json, report.md, manifest.json}
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DATA = ROOT / "data"
CACHE = DATA / "cache"
RUNS = ROOT / "sttr-runs"

_MIN_OVERLAP_M2 = 1.0  # onder deze overlap tellen we een GIO-object niet als geraakt


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def laatste_dir(patroon: str) -> Path:
    dirs = sorted(RUNS.glob(patroon))
    if not dirs:
        raise SystemExit(f"geen run gevonden onder {RUNS} voor {patroon} — draai sttr.py")
    return dirs[-1]


# ---------------------------------------------------------------- GML → shapely

def _poslist(ring: ET.Element) -> list[tuple[float, float]]:
    tekst = ring.find("{http://www.opengis.net/gml/3.2}posList")
    if tekst is None or not (tekst.text or "").strip():
        return []
    getallen = [float(w) for w in tekst.text.split()]
    return list(zip(getallen[0::2], getallen[1::2]))


def gml_polygonen(data: bytes) -> list:
    """Eén GIO-GML → lijst shapely-polygonen (per feature-object, exterior+interior)."""
    import shapely

    root = ET.fromstring(data)
    uit = []
    for el in root.iter():
        lokaal = el.tag.rsplit("}", 1)[-1]
        if lokaal not in ("Polygon", "PolygonPatch"):
            continue
        exterior = ring = None
        for kind in el.iter():
            naam = kind.tag.rsplit("}", 1)[-1]
            if naam == "exterior" and exterior is None:
                exterior = kind
        if exterior is None:
            continue
        buiten = None
        for kind in exterior.iter():
            if kind.tag.rsplit("}", 1)[-1] == "LinearRing":
                ring = kind
                break
        if ring is None:
            continue
        buiten = _poslist(ring)
        if len(buiten) < 4:
            continue
        gaten = []
        for kind in el.iter():
            if kind.tag.rsplit("}", 1)[-1] != "interior":
                continue
            for sub in kind.iter():
                if sub.tag.rsplit("}", 1)[-1] == "LinearRing":
                    gat = _poslist(sub)
                    if len(gat) >= 4:
                        gaten.append(gat)
                    break
        try:
            poly = shapely.Polygon(buiten, gaten)
            # buffer(0): repareren van ongeldige ringen (GEOS TopologyException
            # anders gegarandeerd bijValidatie-foute GIO-aanleveringen)
            poly = poly.buffer(0) if not poly.is_valid else poly
            if not poly.is_empty and poly.area > 0:
                uit.append(poly)
        except Exception:  # onregelmatige ring: overslaan, nooit gokken
            continue
    return uit


def gio_lagen(pakket_zip: Path, gewenste: set[str]) -> dict[str, dict]:
    """Per GIO-bestandsnaam: polygonen-lijst + FRBRWork (alleen de gewenste)."""
    uit: dict[str, dict] = {}
    with zipfile.ZipFile(pakket_zip) as z:
        for naam in sorted(z.namelist()):
            if not naam.endswith(".gml") or "/" not in naam:
                continue
            kort = naam.rsplit("/", 1)[-1]
            if kort not in gewenste:
                continue
            data = z.read(naam)
            m = re.search(rb"<geo:FRBRWork>([^<]+)</geo:FRBRWork>", data)
            polygonen = gml_polygonen(data)
            if polygonen:
                uit[kort] = {
                    "frbrWork": m.group(1).decode("utf-8", errors="replace") if m else None,
                    "polygonen": polygonen,
                }
    return uit


# ---------------------------------------------------------------- kruising

def genomen_unie(scenario: dict, lagen_ids: dict, werkgrens) -> tuple:
    """Union van de genomen BGT-vlakken van één scenario, geclipt op de werkgrens."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    alloc = scenario.get("allocatie")
    if not alloc or not alloc.get("genomen_ids"):
        return None, None
    bron = "begroeidterreindeel" if alloc["laag"] == "groen" else "onbegroeidterreindeel"
    geomen = []
    for lokaal_id in alloc["genomen_ids"]:
        f = lagen_ids[bron].get(lokaal_id)
        if not f or not f.get("geometry"):
            continue
        geomen.append(shape(f["geometry"]))
    if not geomen:
        return None, None
    unie = unary_union(geomen).intersection(werkgrens)
    if not unie.is_valid:
        unie = unie.buffer(0)
    return unie, alloc


def kruis_scenario(unie, lagen: dict[str, dict]) -> list[dict]:
    """Union van genomen vlakken × GIO-lagen → geraakte lagen (aflopend op m²)."""
    uit = []
    for naam, gio in lagen.items():
        overlap = 0.0
        geraakt = 0
        for poly in gio["polygonen"]:
            if not poly.intersects(unie):
                continue
            deel = poly.intersection(unie).area
            if deel >= _MIN_OVERLAP_M2:
                overlap += deel
                geraakt += 1
        if overlap >= _MIN_OVERLAP_M2:
            uit.append({"gio": naam[:-4], "frbrWork": gio["frbrWork"],
                        "overlapM2": round(overlap, 1), "objecten": geraakt})
    uit.sort(key=lambda r: -r["overlapM2"])
    return uit


def main() -> int:
    from shapely.geometry import box as shapely_box

    gebied = json.loads((DATA / "gebied.json").read_text(encoding="utf-8"))
    werkgrens = shapely_box(*gebied["werkgrens"]["bbox_rd"])

    sweep_dirs = sorted((ROOT / "scenario-runs").glob("*-sweep"))
    if not sweep_dirs:
        raise SystemExit("geen scenario-sweep gevonden — draai eerst scenarios.py")
    sweep = sweep_dirs[-1]
    loket = laatste_dir("*-loketvragen")
    scs = json.loads((sweep / "scenarios.json").read_text(encoding="utf-8"))
    loket_data = json.loads((loket / "loketvragen.json").read_text(encoding="utf-8"))

    snijdende = [g for g in (loket_data.get("locatieGebonden") or {}).get("gios") or []
                 if g.get("snijdtWerkgrens")]
    if not snijdende:
        raise SystemExit("loketvragen-run heeft geen snijdende GIO's — draai sttr.py zonder --skip-live")
    pakket = CACHE / "omgevingsplan-pakket.zip"
    if not pakket.is_file():
        raise SystemExit(f"uitwisselpakket ontbreekt: {pakket} — draai sttr.py (live)")

    lagen = gio_lagen(pakket, {g["bestand"] for g in snijdende})
    lagen_ids = {}
    for naam in ("begroeidterreindeel", "onbegroeidterreindeel"):
        fc = json.loads((CACHE / f"{naam}.geojson").read_text(encoding="utf-8"))
        lagen_ids[naam] = {f["properties"].get("lokaal_id"): f for f in fc.get("features", [])}

    per_scenario = []
    for s in scs:
        unie, alloc = genomen_unie(s, lagen_ids, werkgrens)
        if unie is None:
            continue
        raakt = kruis_scenario(unie, lagen)
        per_scenario.append({
            "id": s["id"], "naam": s["naam"], "laag": alloc["laag"],
            "toegedeeld_ha": alloc["toegedeeld_ha"], "n_vlakken": alloc["n"],
            "raakt": raakt, "n_lagen": len(raakt),
        })

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-kruising"
    uit_dir = RUNS / run_id
    uit_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "runId": run_id, "gegenereerdOp": utcnow(),
        "sweepRunId": json.loads((sweep / "manifest.json").read_text())["runId"],
        "loketRunId": loket_data["runId"],
        "gioLagen": sorted(lagen),
        "perScenario": per_scenario,
        "grens": ("geometrisch feit (genomen vlakken ∩ GIO-laag), geen toets; "
                  "conclusie-enum volgt pas met een concreet voorstel"),
    }
    (uit_dir / "kruising.json").write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                           encoding="utf-8")

    manifest = {
        "runId": run_id, "gegenereerdOp": utcnow(),
        "bronnen": [
            {"bron": "scenario-sweep", "pad": str(sweep / "scenarios.json"),
             "sha256": sha256_file(sweep / "scenarios.json")},
            {"bron": "loketvragen-run", "pad": str(loket / "loketvragen.json"),
             "sha256": sha256_file(loket / "loketvragen.json")},
            {"bron": "ow-uitwisselpakket", "pad": str(pakket),
             "sha256": sha256_file(pakket)},
            {"bron": "bgt-begroeid", "pad": str(CACHE / "begroeidterreindeel.geojson"),
             "sha256": sha256_file(CACHE / "begroeidterreindeel.geojson")},
            {"bron": "bgt-onbegroeid", "pad": str(CACHE / "onbegroeidterreindeel.geojson"),
             "sha256": sha256_file(CACHE / "onbegroeidterreindeel.geojson")},
            {"bron": "gebied.json", "pad": str(DATA / "gebied.json"),
             "sha256": sha256_file(DATA / "gebied.json")},
        ],
        "drempels": {"minOverlapM2": _MIN_OVERLAP_M2},
    }
    (uit_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                           encoding="utf-8")

    regels = [
        f"# Scenario-kruising Spoorzone Veenendaal — {run_id}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/sttr_kruising.py` · **geometrisch feit, "
        f"geen toets**: genomen vlakken per programmavariant ∩ "
        f"{len(lagen)} officiële GIO-lagen over de werkgrens (uit {loket_data['runId']}).*",
        "",
    ]
    for p in per_scenario:
        regels += [
            f"## {p['naam']} ({p['id']})",
            "",
            f"Toedeling: {p['n_vlakken']} vlakken uit **{p['laag']}** "
            f"({p['toegedeeld_ha']} ha) → raakt **{p['n_lagen']} officiële lagen**:",
            "",
            "| GIO-laag | Overlap | Objecten |", "|---|---:|---:|",
        ]
        for r in p["raakt"]:
            regels.append(f"| {r['gio']} | {r['overlapM2']:,.0f} m² | {r['objecten']} |"
                          .replace(",", "."))
        if not p["raakt"]:
            regels.append("| — geen van de GIO-lagen geraakt — | | |")
        regels.append("")
    regels += [
        "## Leeswijzer & grenzen",
        "",
        "- **Raakt ≠ verboden**: de kruising zegt welke officiële beleidslagen de variant",
        "  fysiek overlapt; of dat tot een vergunningplicht leidt, beslist het loket bij een",
        "  concreet voorstel (conclusie-enum).",
        "- GIO-polygonen zijn exterior+interior zoals aangeleverd; overlap ≥ 1 m² telt.",
        "- De toedeling volgt de engine-regel van `scenarios.py` (hele vlakken, afstand tot",
        "  het station oplopend) tegen de provisionele bbox-werkgrens.",
        "",
        f"*Artefacten: `kruising.json` · `manifest.json` · bronnen: sweep "
        f"`{data['sweepRunId']}` · loket `{data['loketRunId']}`.*",
    ]
    (uit_dir / "report.md").write_text("\n".join(regels), encoding="utf-8")

    print(f"✓ kruising {run_id}")
    for p in per_scenario:
        top = p["raakt"][0] if p["raakt"] else None
        print(f"  {p['id']:16} raakt {p['n_lagen']:2} lagen"
              + (f" — top: {top['gio']} ({top['overlapM2']:,.0f} m²)".replace(",", ".")
                 if top else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
