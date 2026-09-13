"""Rapportbouw van de Breda vijf-waardenscan: report.html + report.md.

Eén zelfstandig HTML-bestand (Leaflet via CDN met leesbare fallback, data
inline), volgens de PoC-1/PoC-3-reportidiom. Ingebedde JSON wordt letterlijk
``<``-ge-escaped (les uit PoC-1: escaping moet écht, anders injectie).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

from .values import CONGRESS, LIMITATIONS, PROGRAMME_URL, VALUES

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = Path(__file__).resolve().parent / "report_template.html"

PALETTE_CSS = {
    "democratic": "#08519e",
    "spatial": "#006d2c",
    "economic": "#a63603",
    "social": "#a50f15",
    "autonomous": "#5e35b1",
}
VALUE_ORDER = ("democratic", "spatial", "economic", "social")
DISPLAY_SIMPLIFY_DEG = 0.00025  # ≈ 25 m


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _json_for_html(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")


# --------------------------------------------------------------------------- #
# Geo-emballage (WGS84 voor het rapport, gesimplificeerd voor beeldschermlast)
# --------------------------------------------------------------------------- #


def _simplify_geom(geom, tolerance=DISPLAY_SIMPLIFY_DEG):
    try:
        return geom.simplify(tolerance=tolerance, preserve_topology=True)
    except Exception:
        return geom


def _geom_to_geojson(geom):
    from shapely.geometry import mapping

    return mapping(_simplify_geom(geom))


def _wgs84_geom(geom):
    """RD → WGS84 zonder pyproj-afhankelijkheid herinvoeren: pipeline.geodata heeft
    een collectie-converter; hier is per-geometrie voldoende (pyproj zit in de venv)."""
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    return _transform(geom, tr.transform)


def _transform(geom, fn):
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import transform as shp_transform

    return shp_transform(fn, geom)


def _shapes(fc):
    from shapely.geometry import shape as _shape

    out = []
    for f in (fc or {}).get("features", []):
        if f.get("geometry"):
            try:
                out.append(_shape(f["geometry"]))
            except Exception:
                continue
    return out


def build_geo_payload(scan: dict, buurten_fc: dict) -> dict:
    """Buurtvlakken (WGS84, gesimplificeerd) + score-properties voor de kaart."""
    shapes = _shapes(buurten_fc)

    features = []
    for geom, buurt in zip(shapes, scan["buurten"]):
        score_map = {v: buurt["scores"][v]["score"] for v in VALUE_ORDER}
        props = {
            "code": buurt["buurtcode"],
            "naam": buurt.get("buurtnaam"),
            "wijkcode": buurt.get("wijkcode"),
            "water": buurt.get("water"),
            "inw": buurt.get("aantalInwoners"),
            "s": score_map,
            "det": buurt["scores"],
            "k": buurt.get("kansenkaart"),
            "missing": buurt.get("missing"),
        }
        features.append(
            {"type": "Feature", "properties": props, "geometry": _geom_to_geojson(_wgs84_geom(geom))}
        )
    return {"type": "FeatureCollection", "features": features}


def build_overlays_payload(layers: dict) -> dict:
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union

    # wijkdeals → centroidpunten (2.009 kleine vlakken; als punten leesbaar)
    deals = {"type": "FeatureCollection", "features": []}
    for f in (layers.get("wijkdeals") or {}).get("features", []):
        try:
            from shapely.geometry import shape as _shape

            pt = _shape(f["geometry"]).centroid
            wg = _wgs84_geom(pt)
            deals["features"].append(
                {"type": "Feature", "properties": {}, "geometry": {"type": "Point",
                 "coordinates": [round(wg.x, 6), round(wg.y, 6)]}}
            )
        except Exception:
            continue

    # hoofdgroenstructuur → gedissolveerde omtrek (26k vlakken is te zwaar inline)
    groen = {"type": "FeatureCollection", "features": []}
    groen_shapes = _shapes(layers.get("hoofdgroenstructuur"))
    if groen_shapes:
        union = unary_union(groen_shapes)
        if not isinstance(union, (Polygon, MultiPolygon)):
            union = union.convex_hull
        groen["features"].append(
            {"type": "Feature", "properties": {"naam": "Hoofdgroenstructuur (gedissolveerd)"},
             "geometry": _geom_to_geojson(_wgs84_geom(union))}
        )

    # kansenkaart → 227 vlakken, gesimplificeerd
    kansen = {"type": "FeatureCollection", "features": []}
    for f in (layers.get("kansenkaart") or {}).get("features", []):
        p = f.get("properties") or {}
        omschr = p.get("OMSCHRIJV") or p.get("WIJK") or "kans"
        try:
            from shapely.geometry import shape as _shape

            g = _shape(f["geometry"])
            kansen["features"].append(
                {"type": "Feature", "properties": {"omschrijving": omschr},
                 "geometry": _geom_to_geojson(_wgs84_geom(g))}
            )
        except Exception:
            continue

    return {"wijkdeals": deals, "hoofdgroenstructuur": groen, "kansenkaart": kansen}


# --------------------------------------------------------------------------- #
# Server-side HTML-fragmenten
# --------------------------------------------------------------------------- #


def _value_cards(scan: dict) -> str:
    cards = []
    for key in list(VALUE_ORDER) + ["autonomous"]:
        spec = scan["values"][key]
        card_color = PALETTE_CSS[key]
        quote = spec.get("quote")
        quote_html = f'<div class="quote">&ldquo;{_esc(quote)}&rdquo;</div>' if quote else ""
        items_html = "".join(f"<li>{_esc(i)}</li>" for i in spec.get("programmeItems", []))
        tables = ""
        if key in scan.get("rollup", {}):
            ru = scan["rollup"][key]
            tables = (
                '<table><tr><th colspan="2">Top 5 (highest score)</th></tr>'
                + "".join(f"<tr><td>{_esc(n)}</td><td>{s}</td></tr>" for n, s in ru["top"])
                + '<tr><th colspan="2">Bottom 5</th></tr>'
                + "".join(f"<tr><td>{_esc(n)}</td><td>{s}</td></tr>" for n, s in ru["bottom"])
                + f'<tr><td colspan="2"><em>{ru["n"]} neighbourhoods scored</em></td></tr></table>'
            )
        manifest_html = ""
        if key == "autonomous":
            rows = "".join(
                f'<tr><td>{"✓" if m["met"] else "✗"} <b>{_esc(m["criterion"])}</b></td>'
                f"<td>{_esc(m['evidence'])}</td></tr>"
                for m in scan["values"]["autonomous"]["manifest"]
            )
            manifest_html = f'<table class="data"><tr><th>Criterium</th><th>Bewijs</th></tr>{rows}</table>'
        cards.append(
            f'<div class="vcard" style="--vc:{card_color}">'
            f'<h3>{_esc(spec["label"])}</h3>{quote_html}'
            f"<p>{_esc(spec['description'])}</p>"
            f'<p style="font-size:12.5px;color:var(--muted)"><b>Formula:</b> {_esc(spec["formula"]) if spec.get("formula") else "—"}</p>'
            f"{tables}{manifest_html}"
            f'<div class="items"><b>Answers (programme):</b><ul style="margin:4px 0">{items_html}</ul>'
            f'<a href="{PROGRAMME_URL}" style="font-size:12px">indestad.ai/#programme</a></div>'
            f"</div>"
        )
    return "\n".join(cards)


def _manifest_html(scan: dict) -> str:
    rows = "".join(
        f'<tr><td><span class="{"ok" if m["met"] else "fail"}">{"MET" if m["met"] else "NOT MET"}</span> '
        f"<b>{_esc(m['criterion'])}</b></td><td>{_esc(m['evidence'])}</td></tr>"
        for m in scan["values"]["autonomous"]["manifest"]
    )
    return (
        f"<p>Autonomous value is not a map layer but this demonstrable manifest — "
        f"matching the congress programme item <em>Sovereignty</em> and the AI walk "
        f"<em>Data sovereignty and -continuity</em>.</p>"
        f'<table class="data"><tr><th>Criterion</th><th>Evidence in this run</th></tr>{rows}</table>'
    )


def _validation_html(validation: dict) -> str:
    status = "ok" if validation["verdict"] == "pass" else "fail"
    rows = "".join(
        f'<tr><td><span class="{"ok" if c["ok"] else "fail"}">'
        f'{"PASS" if c["ok"] else "FAIL"}</span> {_esc(c["id"])}</td><td>{_esc(c["detail"])}</td></tr>'
        for c in validation["checks"]
    )
    warn_rows = "".join(
        f'<tr><td><span class="warn">WARNING</span> {_esc(w["id"])}</td><td>{_esc(w["detail"])}</td></tr>'
        for w in validation.get("warnings", [])
    )
    degr = validation.get("degradations") or []
    degr_rows = "".join(
        f'<tr><td><span class="warn">DEGRADED</span> {_esc(d.get("sourceId"))}</td>'
        f"<td>{_esc(d.get('error'))}</td></tr>"
        for d in degr
    )
    return (
        f'<p>Validator verdict: <span class="{status}">{_esc(validation["verdict"].upper())}</span> '
        f'— {len(validation["checks"])} checks, {len(validation.get("errors", []))} errors, '
        f"{len(validation.get('warnings', []))} warnings.</p>"
        f'<table class="data"><tr><th>Check</th><th>Detail</th></tr>{rows}{warn_rows}{degr_rows}</table>'
        f'<p style="font-size:12.5px;color:var(--muted)">V4 (human check at the congress) '
        f"remains pending by design.</p>"
    )


def _prov_html(scan: dict, prov: dict) -> str:
    src_rows = "".join(
        f"<tr><td>{_esc(s['id'])}</td><td>{_esc(s['title'])}</td><td>"
        f"<a href='{_esc(s['url'])}'>{_esc(s['url'])}</a></td>"
        f"<td>{_esc(s.get('authoritative') or '')}</td><td>{_esc(s.get('fetchedAt') or '')}</td>"
        f"<td>{s.get('featureCount') if s.get('featureCount') is not None else '—'}</td></tr>"
        for s in scan["sources"]
    )
    art_rows = "".join(
        f"<tr><td>{_esc(e['name'])}</td><td><code>{e['sha256'][:16]}…</code></td></tr>"
        for e in prov.get("entities", [])
    )
    return (
        f'<table class="data"><tr><th>Source id</th><th>Title</th><th>URL</th>'
        f"<th>Owner</th><th>fetchedAt</th><th>features</th></tr>{src_rows}</table>"
        f"<h3>Artifacts (sha256)</h3>"
        f'<table class="data">{art_rows}</table>'
    )


def _limits_html() -> str:
    return "<ul>" + "".join(f"<li>{_esc(l)}</li>" for l in LIMITATIONS) + "</ul>"


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #


def build_headline(scan: dict) -> str:
    n = len(scan["buurten"])
    land = [b for b in scan["buurten"] if b.get("water") == "NEE"]
    deals = sum(1 for b in land if (b["scores"]["democratic"]["inputs"].get("deals") or 0) > 0)
    social_top = scan["rollup"]["social"]["top"][:3]
    eco_top = scan["rollup"]["economic"]["top"][:3]
    social_names = ", ".join(f"{_esc(nm)} ({sc})" for nm, sc in social_top) or "—"
    eco_names = ", ".join(f"{_esc(nm)} ({sc})" for nm, sc in eco_top) or "—"
    return (
        f"This scan across {n} Breda neighbourhoods ({len(land)} land neighbourhoods) shows "
        f"per neighbourhood where open data already creates value today — {deals} "
        f"neighbourhoods carry one or more neighbourhood deals (democratic value); the "
        f"highest heat attention (social value) lies in {social_names}; the most unused "
        f"roof potential (economic value) in {eco_names}. Every score is a percentile "
        f"within Breda and traces to the source table at the bottom of this report."
    )


def build_reports(scan: dict, layers: dict, validation: dict, prov: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    buurten_fc = layers.get("buurten") or {}
    geo_payload = build_geo_payload(scan, buurten_fc)
    overlays_payload = build_overlays_payload(layers)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = (
        template.replace("__TITLE__", "Breda vijf-waardenscan — AI in the City 2026")
        .replace("__GENERATED__", scan["scan"]["generatedAt"])
        .replace("__LEDE__", build_headline(scan))
        .replace("__VALUE_CARDS__", _value_cards(scan))
        .replace("__MANIFEST_HTML__", _manifest_html(scan))
        .replace("__VALIDATION_HTML__", _validation_html(validation))
        .replace("__PROV_HTML__", _prov_html(scan, prov))
        .replace("__LIMITS_HTML__", _limits_html())
        .replace("__SCAN_JSON__", _json_for_html(scan))
        .replace("__GEO_JSON__", _json_for_html(geo_payload))
        .replace("__OVERLAYS_JSON__", _json_for_html(overlays_payload))
    )
    (out_dir / "report.html").write_text(html, encoding="utf-8")

    # markdown-tweeling voor diff/GitHub-vriendelijkheid
    md = [_md_report(scan, validation)]
    (out_dir / "report.md").write_text("\n".join(md), encoding="utf-8")

    (out_dir / "geo-buurten.wgs84.geojson").write_text(
        json.dumps(geo_payload, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "overlays.wgs84.geojson").write_text(
        json.dumps(overlays_payload, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "artifacts": {
            name: _sha256(out_dir / name)
            for name in ("report.html", "report.md", "geo-buurten.wgs84.geojson",
                         "overlays.wgs84.geojson")
        }
    }


def _md_report(scan: dict, validation: dict) -> str:
    lines = [
        f"# Breda five-value scan — {CONGRESS}",
        "",
        f"Generated {scan['scan']['generatedAt']}. Verdict: **{validation['verdict']}**.",
        "",
        build_headline(scan),
        "",
    ]
    for key in list(VALUE_ORDER) + ["autonomous"]:
        spec = scan["values"][key]
        lines += [f"## {spec['label']}", ""]
        if spec.get("quote"):
            lines += [f"> {spec['quote']}", ""]
        lines += [spec["description"], ""]
        if spec.get("formula"):
            lines += [f"Formule: {spec['formula']}", ""]
        if key in scan.get("rollup", {}):
            ru = scan["rollup"][key]
            lines += ["| buurt | score |", "|---|---|"]
            lines += [f"**top** {_esc(n)} | {s}" for n, s in ru["top"]]
            lines += [""] + [f"**bottom** {_esc(n)} | {s}" for n, s in ru["bottom"]]
            lines += ["", f"_{ru['n']} neighbourhoods scored._", ""]
        if key == "autonomous":
            lines += ["| criterion | evidence |", "|---|---|"]
            lines += [f"{m['criterion']} | {'MET' if m['met'] else 'NOT MET'} — {m['evidence']}"
                      for m in scan["values"]["autonomous"]["manifest"]]
            lines += [""]
        lines += ["Answers (programme): " + "; ".join(spec["programmeItems"]), ""]
    lines += ["## Sources", "", "| source | title | url | fetched |", "|---|---|---|---|"]
    lines += [
        f"{s['id']} | {s['title']} | {s['url']} | {s.get('fetchedAt') or '—'}"
        for s in scan["sources"]
    ]
    lines += ["", "## Limitations", ""]
    lines += [f"- {l}" for l in LIMITATIONS]
    return "\n".join(lines)
