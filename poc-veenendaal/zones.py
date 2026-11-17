#!/usr/bin/env python3
"""veenendaal-spoorzone deelgebied-uitsnede — wat lágt en wat géldt er, per deelgebied.

Vierde artefact-laag na run.py (gebiedscheck), sttr.py (loket) en
sttr_kruising.py (scenario's): per deelgebied-zone uit gebied.json twee kanten:

1. **nulmeting** — BAG/BGT-indicatoren geclipt op de zone-polygon, hergebruik van
   de engine-functies uit run.py (zelfde meetkunde,zelfde zwaartepuntregel);
2. **regel-lagen** — officiële GIO-lagen uit het omgevingsplan-pakket die de zone
   snijden, met overlap in ha (shapely, zoals het loket meet). Geometrisch feit,
   géén toets: raakt ≠ verboden.

Invariant (V-check in dit script): de zones tegelen de werkgrens exact, dus
Σ zone-tellingen == de nulmeting uit de canonieke gebiedscheck-run.

Gebruik:
  nldt/.venv/bin/python zones.py      # cache-first; nieuwste loketvragen-run + caches
Uitvoer: sttr-runs/<ts>-zones/{zones.json, report.md, manifest.json}
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run as engine  # zelfde map: engine-meetkunde van de gebiedscheck
import sttr_kruising  # zelfde map: GML→shapely + gio_lagen-hergebruik

from shapely.geometry import shape as shapely_shape

DATA = ROOT / "data"
CACHE = DATA / "cache"
RUNS = ROOT / "sttr-runs"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def laatste_dir(patroon: str) -> Path:
    dirs = sorted(RUNS.glob(patroon))
    if not dirs:
        raise SystemExit(f"geen run onder {RUNS} voor {patroon} — draai eerst sttr.py (zonder --skip-live)")
    return dirs[-1]


def zone_nulmeting(zone_grens: dict, cache: dict) -> dict:
    """BAG/BGT-indicatoren op één zone, met de engine-functies (deterministisch)."""
    panden = [f for f in cache["pand"]
              if f.get("properties", {}).get("status") not in engine.NIET_BESTAAND
              and engine.grens_bevat_zwaartepunt(f.get("geometry"), zone_grens)]
    woningen = som_ge2020 = vloer = 0
    for f in panden:
        p = f["properties"]
        if "woonfunctie" in (p.get("gebruiksdoel") or ""):
            woningen += p.get("aantal_verblijfsobjecten") or 0
        if isinstance(p.get("bouwjaar"), int) and p["bouwjaar"] >= 2020:
            som_ge2020 += 1
        vloer += engine.grens_area_in(f.get("geometry"), zone_grens)

    def vlak_ha(naam: str) -> float:
        return round(sum(engine.grens_area_in(f.get("geometry"), zone_grens)
                         for f in engine.bgt_actueel(cache[naam])) / 10_000, 2)

    bomen = sum(1 for f in engine.bgt_actueel(cache["vegetatieobject_punt"])
                if engine.grens_bevat_zwaartepunt(f.get("geometry"), zone_grens))
    return {
        "panden_bestand": len(panden),
        "woningen_verblijfsobjecten_proxy": woningen,
        "panden_bouwjaar_vanaf_2020": som_ge2020,
        "pand_vloeroppervlak_m2": round(vloer),
        "begroeid_terrein_ha": vlak_ha("begroeidterreindeel"),
        "onbegroeid_terrein_ha": vlak_ha("onbegroeidterreindeel"),
        "waterdeel_ha": vlak_ha("waterdeel"),
        "vegetatieobject_punt": bomen,
    }


def zone_gio_lagen(zone_geom, lagen: dict[str, dict]) -> list[dict]:
    """Per GIO-laag: overlap met de zone (ha) + aantal GIO-objecten dat de zone raakt."""
    opp = zone_geom.area / 10_000
    uit = []
    for naam, gio in lagen.items():
        overlap_m2 = 0.0
        geraakt = 0
        for poly in gio["polygonen"]:
            if not poly.intersects(zone_geom):
                continue
            deel = poly.intersection(zone_geom).area
            if deel >= 1.0:
                overlap_m2 += deel
                geraakt += 1
        if overlap_m2 >= 1.0:
            uit.append({"gio": naam[:-4], "frbrWork": gio["frbrWork"],
                        "overlapHa": round(overlap_m2 / 10_000, 2),
                        "objecten": geraakt,
                        "dekkingPct": round(overlap_m2 / zone_geom.area * 100, 1)})
    uit.sort(key=lambda r: -r["overlapHa"])
    return uit


def main() -> int:
    gebied = json.loads((DATA / "gebied.json").read_text(encoding="utf-8"))
    check_runs = sorted((ROOT / "runs").glob("*-gebiedscheck"))
    if not check_runs:
        raise SystemExit("geen gebiedscheck-run — draai eerst run.py")
    nulmeting = json.loads((check_runs[-1] / "indicators.json").read_text(encoding="utf-8"))

    loket = laatste_dir("*-loketvragen")
    loket_data = json.loads((loket / "loketvragen.json").read_text(encoding="utf-8"))
    snijdende = [g for g in (loket_data.get("locatieGebonden") or {}).get("gios") or []
                 if g.get("snijdtWerkgrens")]
    if not snijdende:
        raise SystemExit("loketvragen-run zonder snijdende GIO's — draai sttr.py zonder --skip-live")
    pakket = CACHE / "omgevingsplan-pakket.zip"
    if not pakket.is_file():
        raise SystemExit(f"uitwisselpakket ontbreekt: {pakket} — draai sttr.py (live)")

    lagen = sttr_kruising.gio_lagen(pakket, {g["bestand"] for g in snijdende})

    def cache_fc(naam: str) -> list:
        return json.loads((CACHE / f"{naam}.geojson").read_text(encoding="utf-8"))["features"]

    cache = {naam: cache_fc(naam) for naam in
             ("pand", "begroeidterreindeel", "onbegroeidterreindeel",
              "waterdeel", "vegetatieobject_punt")}

    zones_uit = []
    for z in gebied["deelgebied_zones"]["zones"]:
        naam = z["naam"]
        zone_grens = engine.laad_werkgrens({"geojson_rd": z["polygon"]})
        zone_geom = shapely_shape(z["polygon"])
        print(f"→ {naam} ({zone_grens['area_m2'] / 10_000:.1f} ha) …")
        zones_uit.append({
            "naam": naam,
            "opp_ha": round(zone_grens["area_m2"] / 10_000, 2),
            "nulmeting": zone_nulmeting(zone_grens, cache),
            "gio_lagen": zone_gio_lagen(zone_geom, lagen),
            "n_gio_lagen": 0,  # gevuld na de pass (zie onder)
        })
    for zn in zones_uit:
        zn["n_gio_lagen"] = len(zn["gio_lagen"])

    # V-check: zones tegelen de werkgrens → Σ zone-tellingen == nulmeting-run
    # (tellingen exact; ha-sommen met kleine tolerantie vooraccumulerende afronding)
    checks = []
    for sleutel, som, ref, tol in (
        ("panden_bestand", sum(z["nulmeting"]["panden_bestand"] for z in zones_uit),
         nulmeting["panden_bestand"], 0),
        ("woningen-proxy", sum(z["nulmeting"]["woningen_verblijfsobjecten_proxy"] for z in zones_uit),
         nulmeting["woningen_verblijfsobjecten_proxy"], 0),
        ("begroeid_ha", round(sum(z["nulmeting"]["begroeid_terrein_ha"] for z in zones_uit), 2),
         nulmeting["begroeid_terrein_ha"], 0.05),
        ("opp_ha", round(sum(z["opp_ha"] for z in zones_uit), 1),
         round(engine.laad_werkgrens(gebied["werkgrens"])["area_m2"] / 10_000, 1), 0.2),
    ):
        checks.append((sleutel, som, ref, abs(som - ref) <= tol))
    v_ok = all(c[3] for c in checks)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-zones"
    uit_dir = RUNS / run_id
    uit_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "runId": run_id, "gegenereerdOp": utcnow(),
        "bronRunGebiedscheck": check_runs[-1].name,
        "bronRunLoket": loket_data["runId"],
        "werkgrens": {"modus": "polygon",
                      "oppHa": round(engine.laad_werkgrens(gebied["werkgrens"])["area_m2"] / 10_000, 2)},
        "zones": zones_uit,
        "vChecks": [{"check": c[0], "som": c[1], "referentie": c[2], "ok": c[3]} for c in checks],
    }
    (uit_dir / "zones.json").write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                        encoding="utf-8")

    bronnen = [
        {"bron": "gebied.json", "pad": str(DATA / "gebied.json"), "sha256": sha256_file(DATA / "gebied.json")},
        {"bron": "gebiedscheck-indicatoren", "pad": str(check_runs[-1] / "indicators.json"),
         "sha256": sha256_file(check_runs[-1] / "indicators.json")},
        {"bron": "loketvragen-run", "pad": str(loket / "loketvragen.json"),
         "sha256": sha256_file(loket / "loketvragen.json")},
        {"bron": "ow-uitwisselpakket", "pad": str(pakket), "sha256": sha256_file(pakket)},
        {"bron": "bag-pand", "pad": str(CACHE / "pand.geojson"), "sha256": sha256_file(CACHE / "pand.geojson")},
    ]
    (uit_dir / "manifest.json").write_text(
        json.dumps({"runId": run_id, "gegenereerdOp": utcnow(), "bronnen": bronnen},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------- rapport
    regels = [
        f"# Deelgebied-uitsnede Spoorzone — {run_id}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/zones.py` · nulmeting via de engine uit "
        f"`run.py` · regel-lagen via het omgevingsplan-pakket (loket {loket_data['runId']}). "
        f"**Feiten, geen toets**: raakt ≠ verboden.*",
        "",
        f"Werkgrens: polygon (assengrenzen Toekomstbeeld) · {data['werkgrens']['oppHa']} ha · "
        f"{len(zones_uit)} deelgebieden die de werkgrens exact tegelen.",
        "",
        "## Samenvatting",
        "",
        "| Deelgebied | opp (ha) | panden | woningen | groen (ha) | verhard (ha) | water (ha) | GIO-lagen |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for z in zones_uit:
        n = z["nulmeting"]
        regels.append(
            f"| {z['naam']} | {z['opp_ha']:.1f} | {n['panden_bestand']} | "
            f"{n['woningen_verblijfsobjecten_proxy']} | {n['begroeid_terrein_ha']} | "
            f"{n['onbegroeid_terrein_ha']} | {n['waterdeel_ha']} | {z['n_gio_lagen']} |"
        )
    regels += [
        "",
        f"**V-checks** (Σ zones ≡ gebiedscheck): " + " · ".join(
            f"{c[0]} {c[1]}={c[2]} {'✓' if c[3] else '✗'}" for c in checks) + ".",
        "",
        "## Per deelgebied",
        "",
    ]
    for z in zones_uit:
        n = z["nulmeting"]
        regels += [
            f"### {z['naam']} — {z['opp_ha']:.1f} ha",
            "",
            f"panden {n['panden_bestand']} (≥2020: {n['panden_bouwjaar_vanaf_2020']}) · "
            f"woningen-proxy {n['woningen_verblijfsobjecten_proxy']} · "
            f"grondvlak {n['pand_vloeroppervlak_m2']:,} m² · bomen {n['vegetatieobject_punt']}".replace(",", "."),
            "",
            f"**Regel-lagen over dit deelgebied ({z['n_gio_lagen']}):**",
            "",
        ]
        if z["gio_lagen"]:
            regels += ["| GIO-laag | overlap | dekking | objecten |", "|---|---:|---:|---:|"]
            for g in z["gio_lagen"]:
                regels.append(f"| {g['gio']} | {g['overlapHa']:.2f} ha | {g['dekkingPct']}% | {g['objecten']} |")
        else:
            regels.append("*(geen van de werkgrens-snijdende GIO-lagen raakt dit deelgebied)*")
        regels.append("")

    regels += [
        "## Leeswijzer & grenzen",
        "",
        "- Overlap = geometrisch snijvlak (shapely, EPSG:28992); dekking = overlap als %",
        "  van de zone-oppervlakte. Objecten = GIO-polygonen die de zone raken.",
        "- Raakt ≠ verboden: of een laag tot een vergunningplicht leidt, beslist het loket",
        "  bij een concreet voorstel (conclusie-enum).",
        "- Nulmeting-getallen volgen dezelfde engine-meetkunde en zwaartepuntregel als de",
        "  canonieke gebiedscheck; de V-checks hierboven bewaken de som.",
        "- Zone-indeling blijft provisioneel (geen officiële deelgebiedsgrenzen).",
        "",
        f"*Artefacten: `zones.json` · `manifest.json` · bronnen: gebiedscheck "
        f"`{data['bronRunGebiedscheck']}` · loket `{data['bronRunLoket']}`.*",
    ]
    (uit_dir / "report.md").write_text("\n".join(regels), encoding="utf-8")

    print(f"\n✓ {run_id}")
    for z in zones_uit:
        print(f"  {z['naam']:42s} {z['opp_ha']:6.1f} ha · {z['n_gio_lagen']:2} GIO-lagen")
    print(f"  V-checks: {'PASS' if v_ok else 'FAIL'} — " +
          "; ".join(f"{c[0]} {c[1]} vs {c[2]}" for c in checks if not c[3]))
    return 0 if v_ok else 2


if __name__ == "__main__":
    sys.exit(main())
