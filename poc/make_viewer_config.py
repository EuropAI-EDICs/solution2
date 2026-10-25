"""Utrecht-PoC run-output → Leia-config (NSPD-patroon, make_viewer_config.py van
poc-nspd geport). Genereert deep-agents/viewer-utrecht/: de Leia-build met een
Utrecht-config (achtergrondkaart, 3D-gebouwcontext, scenario-zones per
uitdaging, what-if-runs, landelijke bronlagen) — Lagenbeheer met aan/uit per
groep en laag, opstart-schoon (alleen basiskaarten aan).

Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 make_viewer_config.py
Kijk: http://127.0.0.1:8765/viewer-utrecht/index.html
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.scenario_labels import (  # noqa: E402
    BASELINE_VERSCHIL,
    final_only_fc,
    scenario_kort,
    scenario_kleur as _scenario_kleur,
    scenario_verschil as _scenario_verschil,
)

SCENARIO_RUNS = ROOT / "scenario-runs"
UITDAGINGEN = ROOT / "scenarios" / "uitdagingen.json"
ALIASES = ROOT / "tracks" / "_zone-aliases.json"
NATIONAL = ROOT / "data" / "cache" / "national"
# De Leia-build (poc-nspd/viewer/build) is voor ROOT-hosting gebouwd
# (APP_URL gebakken op http://localhost:8010): alle app-fetches resolven daar
# naartoe via <base href>. De Utrecht-viewer is dus een SUBMAP van die build
# (config.json + layers/), geserveerd door de draaiende NSPD-server op 8010 —
# zelfde origin, geen CORS, en laag-URL's zijn root-absoluut (/utrecht/...).
# Bron = static/utrecht: een npm-build leegt build/ en kopieert static/ mee,
# dus hier schrijven en daarna (of bij de volgende build) naar build/ kopiëren.
OUT = REPO / "poc-nspd" / "viewer" / "static" / "utrecht"
URL_PREFIX = "/utrecht"
BRT_WMTS = "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0?"
BAG_3D = "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"

# Leia (geojson-layer.ts): vul-transparantie komt uitsluitend uit laag-opacity;
# een hex-alpha wordt door withAlpha() overschreven. Zie NSPD-variant.
ZONE_OPACITY = 20

CONTROL_STIJL = {"fill": "#5e5c64", "stroke": "#3d3846"}


def _uitdaging_featured() -> list[dict]:
    """[{uitdaging: {id, titel}, track, run_id}] uit het curation-contract."""
    uj = json.loads(UITDAGINGEN.read_text(encoding="utf-8"))
    per: dict[str, dict] = {}
    for uit in uj["uitdagingen"]:
        for track in uit["tracks"]:
            run_id = uj["scenarioRuns"].get(track)
            if run_id:
                per[track] = {"uitdaging": uit, "track": track, "run_id": run_id}
    volgorde = [t for u in uj["uitdagingen"] for t in u["tracks"]]
    return sorted(per.values(), key=lambda x: volgorde.index(x["track"]))


# --------------------------------------------------------------------------- #
# normverwijzingen: ruleId -> echt wetsartikel (normkaart: artikel, citaat,
# bron-URL) uit de baseline-run van de scenario-run — zodat een klik op een
# zone in de viewer naar het wetsartikel leidt in plaats van "FR-x-x".
# --------------------------------------------------------------------------- #

_NORM_INDEX_CACHE: dict[str, dict | None] = {}


def _norm_index(scenario_run_dir: Path) -> dict[str, dict[str, str]]:
    """{ruleId: {artikel, instrument, citaat, bron, normkaart}} uit de
    baseline-run van een scenario-run. Vastgezette normkaartvelden: source.
    article / instrument / quote / uri (cite-or-abstain contract)."""
    run_id = scenario_run_dir.name
    if run_id in _NORM_INDEX_CACHE:
        return _NORM_INDEX_CACHE[run_id] or {}
    try:
        rapport = json.loads((scenario_run_dir / "scenario-report.json")
                             .read_text(encoding="utf-8"))
        basis = (REPO / "poc" / "runs" /
                 str(rapport.get("baselineRunId")))
        regels = json.loads((basis / "formalrules.json").read_text(encoding="utf-8"))
        regels = regels.get("formalRules", regels) if isinstance(regels, dict) else regels
        regel_naar_kaart = {str(r["id"]): str(r.get("normCardId") or "")
                            for r in rules_list(regels)}
        kaarten = json.loads((basis / "normcards.json").read_text(encoding="utf-8"))
        kaarten = kaarten.get("normCards", kaarten) if isinstance(kaarten, dict) else kaarten
        kaart_by_id = {str(c["id"]): c for c in kaarten}
    except (OSError, ValueError, KeyError) as exc:
        print(f"[normverwijzingen] {run_id}: baseline niet leesbaar ({exc})")
        _NORM_INDEX_CACHE[run_id] = {}
        return {}

    sem_naar_nl = {
        "exclusion": "hier niet toegestaan",
        "conditional": "hier voorwaardelijk",
        "inclusion": "hier mogelijk",
        "attention": "aandachtsgebied",
        "compensation": "compensatieplicht",
        "none": "geen ruimtelijke werking",
    }
    index: dict[str, dict[str, str]] = {}
    for r in regels:
        rid, ncid = str(r["id"]), str(r.get("normCardId") or "")
        kaart = kaart_by_id.get(ncid)
        if not kaart:
            continue
        bron = kaart.get("source") or {}
        index[rid] = {
            "artikel": str(bron.get("article") or ""),
            "instrument": str(kaart.get("instrument") or ""),
            "citaat": str(bron.get("quote") or ""),
            "bron": str(bron.get("uri") or ""),
            "normkaart": ncid,
            "werking": sem_naar_nl.get(str(r.get("zoneSemantics") or ""),
                                       str(r.get("zoneSemantics") or "")),
        }
    _NORM_INDEX_CACHE[run_id] = index
    return index


def rules_list(regels):
    return regels if isinstance(regels, list) else regels.get("formalRules", [])


def _unieke_refs(fc: dict, index: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    """Unieke normverwijzingen over alle features (volgorde van eerste gebruik)."""
    gezien: list[str] = []
    for f in fc.get("features", []):
        for r in (f.get("properties") or {}).get("ruleIds") or []:
            r = str(r)
            if r in index and r not in gezien:
                gezien.append(r)
    return [index[r] for r in gezien]


def _verrijk_features(fc: dict, index: dict[str, dict[str, str]],
                       *, titel: str, weblink: str,
                       verschil: str = "",
                       context_regels: dict[str, str] | None = None) -> None:
    """Popup-attributen in leesbaar Nederlands: wat betekent dit vlak, welke
    wetsartikelen horen erbij, en de weblink naar de leesbare regelpagina.
    Technische eigenschappen (ruleIds/operation/prov/km²) verdwijnen uit de
    popup; de geometrie blijft onaangetast.

    De normkaart-quote is de Nederlandse wettekst zelf — eerste zin = leesbare
    samenvatting; de volledige tekst + weblink staan in de regelpagina."""
    for f in fc.get("features", []):
        props = f.get("properties")
        if not isinstance(props, dict):
            continue
        rids = [str(r) for r in (props.get("ruleIds") or [])]
        refs = [index[r] for r in rids if r in index]
        context = context_regels or {}
        regels_leesbaar = []
        artikelen = []
        for n, r in enumerate(refs, 1):
            citaat = r["citaat"]
            if len(citaat) > 600:
                citaat = citaat[:597].rstrip() + "…"
            werking = r.get("werking", "")
            regels_leesbaar.append(
                f"{n}) {r['artikel']} ({werking}): {citaat}")
            artikelen.append(r["artikel"])
        for n, (rid, contexttekst) in enumerate(context.items(), len(refs) + 1):
            regels_leesbaar.append(f"{n}) {rid}: {contexttekst}")
        props.clear()
        props["gebied"] = titel
        if verschil:
            props["verschil"] = verschil
        if regels_leesbaar:
            # popup toont max 5 volledige regels; de rest via de weblink
            getoond = regels_leesbaar[:5]
            if len(regels_leesbaar) > 5:
                getoond.append(f"… nog {len(regels_leesbaar) - 5} artikelen — "
                               "zie de weblink hieronder")
            props["wat_betreft_dit_vlak"] = " ".join(getoond)
        if artikelen:
            props["wetsartikelen"] = " · ".join(artikelen)
        if refs:
            props["weblink_leesbare_regels"] = (
                f"http://localhost:8010{weblink}" if weblink.startswith("/") else weblink)
            # Leia url:-protocol → klikbare link in de featureInfo-popup
            # (label mag géén komma bevatten: parts = value.split(","))
            props["wetsartikel"] = (
                f"url:{weblink},Leesbare regels & wetsartikel van dit vlak")
        props["regel_ids"] = ", ".join(rids)


def _regel_rapport(scid: str, titel: str, refs: list[dict[str, str]],
                   reports_dir: Path, *, verschil: str = "") -> str:
    """Leesbare regelpagina (HTML): per wetsartikel de volledige Nederlandse
    wettekst + de weblink naar het artikel. Dit is de 'recursieve verwijzing':
    popup → pagina → wetsartikel."""
    kaarten = "".join(
        f"<div class='kaart'><h2>{r['artikel']}</h2>"
        + (f"<p class='werking'>in dit vlak en scenario: {r['werking']}</p>"
           if r.get("werking") else "")
        + f"<p class='citaat'>\u201c{r['citaat']}\u201d</p>"
        f"<p class='instrument'>{r['instrument']}</p>"
        f"<p><a href='{r['bron']}' target='_blank'>→ Open het wetsartikel "
        f"(lokaleregelgeving.overheid.nl)</a></p>"
        f"<p class='meta'>normkaart: {r['normkaart']}</p></div>"
        for r in refs)
    verschil_html = (f'<p class="verschil">{verschil}</p>' if verschil else "")
    html = f"""<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<title>Leesbare regels — {titel}</title><style>
body {{ font: 16px/1.55 -apple-system, sans-serif; max-width: 780px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
h1 {{ font-size: 1.4rem; }} .kaart {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }}
.citaat {{ font-style: italic; background: #f6f4ee; padding: .75rem 1rem; border-radius: 6px; }}
.instrument {{ color: #555; font-size: .9rem; }} .meta {{ color: #999; font-size: .8rem; }}
.werking {{ display: inline-block; background: #eef3f8; color: #1a4a7a; padding: .1rem .5rem; border-radius: 4px; font-size: .9rem; }}
.verschil {{ background: #fff6e0; border-left: 4px solid #e5a50a; padding: .6rem .9rem; margin: .75rem 0 1.25rem; font-weight: 500; }}
a {{ color: #0b57a4; }} .disclaimer {{ color: #777; font-size: .85rem; margin-top: 2rem; }}
</style></head><body>
<h1>Leesbare regels — {titel}</h1>
{verschil_html}
<p>De wetsartikelen die voor dit vlak en scenario gelden, met de volledige
wettekst. Onderaan elk onderdeel staat de weblink naar het wetsartikel zelf
(lokaleregelgeving.overheid.nl, Omgevingsverordening provincie Utrecht).</p>
{kaarten}
<p class="disclaimer">Scenariodoel: besluitondersteuning. Dit is geen juridisch
advies; per locatie blijft een afzonderlijke beoordeling nodig.</p>
</body></html>"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{scid}.html"
    out.write_text(html, encoding="utf-8")
    return out.name


def _scenario_groep_en_lagen(layers_dir: Path) -> tuple[list[dict], list[dict]]:
    """Per uitdaging een subgroep met baseline + scenario-lagen.
    Laagtitel = éénregel-verschil (geen km²); kleur per scenario zodat
    het verschil op de kaart zichtbaar is. Opstart: alles uit."""
    groepen: list[dict] = []
    lagen: list[dict] = []
    for item in _uitdaging_featured():
        track, run_id = item["track"], item["run_id"]
        bron = SCENARIO_RUNS / run_id
        rapport_pad = bron / "scenario-report.json"
        if not rapport_pad.is_file():
            continue
        rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
        gid = f"scenario-{track}"
        groepen.append({"id": gid, "parentId": "scenario",
                        "title": f"Uitdaging: {item['uitdaging']['titel']} — {track}",
                        "isOpen": False})
        control = bron / "scenarios" / "CONTROL.geojson"
        if control.is_file():
            # Alleen final-kanszone — anders tekent inclusion de hele provincie.
            fc_ctl = final_only_fc(json.loads(control.read_text(encoding="utf-8")))
            titel_ctl = f"{track} — baseline (huidige regels)"
            verschil_ctl = BASELINE_VERSCHIL
            # refs vóór _verrijk_features: die wist de properties (ruleIds erbij)
            norm = _norm_index(bron)
            refs_ctl = _unieke_refs(fc_ctl, norm)
            _verrijk_features(fc_ctl, norm, titel=titel_ctl, verschil=verschil_ctl,
                              weblink=f"{URL_PREFIX}/reports/{track}-CONTROL.html")
            (layers_dir / f"zones-{track}-CONTROL.geojson").write_text(
                json.dumps(fc_ctl, ensure_ascii=False), encoding="utf-8")
            _regel_rapport(f"{track}-CONTROL", titel_ctl, refs_ctl,
                           layers_dir.parent / "reports", verschil=verschil_ctl)
            lagen.append({
                "id": f"zones-{track}-CONTROL", "type": "geojson",
                "title": f"{track}: baseline (huidige regels)",
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 15,
                "description": verschil_ctl,
                "metadataUrl": f"{URL_PREFIX}/reports/{track}-CONTROL.html",
                "settings": {"url": f"{URL_PREFIX}/layers/zones-{track}-CONTROL.geojson",
                             "style": CONTROL_STIJL},
            })
        for i, s in enumerate(rapport.get("scenarios", [])):
            geo = bron / str(s.get("geometryFile") or "")
            if not geo.is_file():
                continue
            scid = str(s.get("scenarioId") or Path(geo).stem)
            delta = float(s.get("deltaVsControlKm2") or 0)
            kleur = _scenario_kleur(i, delta)
            verschil = _scenario_verschil(s)
            titel_sc = f"{track}: {scenario_kort(s)}"
            fc_sc = final_only_fc(json.loads(geo.read_text(encoding="utf-8")))
            norm = _norm_index(bron)
            refs_sc = _unieke_refs(fc_sc, norm)
            _verrijk_features(fc_sc, norm,
                              titel=titel_sc, verschil=verschil,
                              weblink=f"{URL_PREFIX}/reports/{scid}.html")
            (layers_dir / f"zones-{track}-{scid}.geojson").write_text(
                json.dumps(fc_sc, ensure_ascii=False), encoding="utf-8")
            _regel_rapport(scid, titel_sc, refs_sc,
                           layers_dir.parent / "reports", verschil=verschil)
            lagen.append({
                "id": f"zones-{track}-{scid}", "type": "geojson",
                "title": titel_sc,
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": ZONE_OPACITY,
                "description": verschil,
                "metadataUrl": f"{URL_PREFIX}/reports/{scid}.html",
                "settings": {"url": f"{URL_PREFIX}/layers/zones-{track}-{scid}.geojson",
                             "style": {"fill": kleur, "stroke": kleur}},
            })
    return groepen, lagen


def _whatif_groep_en_lagen(layers_dir: Path) -> tuple[list[dict], list[dict]]:
    """De data-gegronde what-ifs (fase 3): *-whatif-sets met add_zone_rule."""
    groepen: list[dict] = []
    lagen: list[dict] = []
    for rapport_pad in sorted(SCENARIO_RUNS.glob("*-whatif/scenario-report.json")):
        try:
            rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rapport.get("verdict") != "pass":
            continue
        usecase = rapport_pad.parent.name.removesuffix("-whatif")
        gid = f"whatif-{usecase}"
        groepen.append({"id": gid, "parentId": "whatif",
                        "title": f"What-if: {usecase}", "isOpen": False})
        bron = rapport_pad.parent
        control = bron / "scenarios" / "CONTROL.geojson"
        if control.is_file():
            fc_ctl = final_only_fc(json.loads(control.read_text(encoding="utf-8")))
            titel_ctl = f"{usecase} — baseline (huidige regels)"
            verschil_ctl = BASELINE_VERSCHIL
            norm = _norm_index(bron)
            refs_ctl = _unieke_refs(fc_ctl, norm)
            _verrijk_features(fc_ctl, norm, titel=titel_ctl, verschil=verschil_ctl,
                              weblink=f"{URL_PREFIX}/reports/{usecase}-CONTROL.html")
            (layers_dir / f"whatif-{usecase}-CONTROL.geojson").write_text(
                json.dumps(fc_ctl, ensure_ascii=False), encoding="utf-8")
            _regel_rapport(f"{usecase}-CONTROL", titel_ctl, refs_ctl,
                           layers_dir.parent / "reports", verschil=verschil_ctl)
            lagen.append({
                "id": f"whatif-{usecase}-CONTROL", "type": "geojson",
                "title": f"{usecase}: baseline (huidige regels)",
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 15,
                "description": verschil_ctl,
                "metadataUrl": f"{URL_PREFIX}/reports/{usecase}-CONTROL.html",
                "settings": {"url": f"{URL_PREFIX}/layers/whatif-{usecase}-CONTROL.geojson",
                             "style": CONTROL_STIJL},
            })
        for i, s in enumerate(rapport.get("scenarios", [])):
            geo = bron / str(s.get("geometryFile") or "")
            if not geo.is_file():
                continue
            scid = str(s.get("scenarioId") or Path(geo).stem)
            delta = float(s.get("deltaVsControlKm2") or 0)
            kleur = _scenario_kleur(i, delta)
            verschil = _scenario_verschil(s)
            titel_sc = f"{usecase}: {scenario_kort(s)}"
            fc_sc = final_only_fc(json.loads(geo.read_text(encoding="utf-8")))
            dg_note = ((s.get("basis") or {}).get("dataGrounding") or {}).get("note") \
                if isinstance((s.get("basis") or {}).get("dataGrounding"), dict) else None
            ctx = {str(scid): "data-gegrond what-if op basis van "
                   + (dg_note or "landelijke bron")} \
                if str((s.get("basis") or {}).get("type")) == "hypothetical" else {}
            norm = _norm_index(bron)
            refs_sc = _unieke_refs(fc_sc, norm)
            _verrijk_features(fc_sc, norm,
                              titel=titel_sc, verschil=verschil,
                              weblink=f"{URL_PREFIX}/reports/{scid}.html",
                              context_regels=ctx)
            (layers_dir / f"whatif-{usecase}-{scid}.geojson").write_text(
                json.dumps(fc_sc, ensure_ascii=False), encoding="utf-8")
            _regel_rapport(scid, titel_sc, refs_sc,
                           layers_dir.parent / "reports", verschil=verschil)
            lagen.append({
                "id": f"whatif-{usecase}-{scid}", "type": "geojson",
                "title": titel_sc,
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 25,
                "description": verschil,
                "metadataUrl": f"{URL_PREFIX}/reports/{scid}.html",
                "settings": {"url": f"{URL_PREFIX}/layers/whatif-{usecase}-{scid}.geojson",
                             "style": {"fill": kleur, "stroke": kleur}},
            })
    return groepen, lagen


#: de nationale caches met geometrie (plan 2); RD-caches gaan naar WGS84 en
#: worden boven 2 MB display-gesimplificeerd (5 m) — zelfde patroon als NSPD.
_BRON_KEUZES = [
    ("netcongestie", "Netcongestie voedingsgebieden (Landelijke Capaciteitskaart)",
     "#a51d2d", "#620e14", "scenario-basis voor energietoets en de what-ifs; "
     "afnamecodes 0-3 (3 = tekort met wachtrij)."),
    ("rce-monumenten", "Rijksmonumenten (RCE)", "#8c564b", "#4e2f28",
     "punten; erfgoed-context bij wonen/landschap."),
    ("rce-iam-archeologie", "Archeologische monumenten (AMK-2014)", "#b5835a", "#614434",
     "substituut voor IAM (geen open WMS); erfgoed-context."),
    ("nwb-wegvakken", "NWB-wegvakken (RWS)", "#17becf", "#0b5f66",
     "wegennet-context bij mobiliteit."),
    ("prorail-spoor", "Spoorlijnen (ProRail)", "#984ea3", "#4c1547",
     "spoor-context bij mobiliteit."),
]


def _eerste_coord(fc: dict) -> float | None:
    """Eerste x-coördinaat, diep genest (Point t/m MultiPolygon)."""
    def dig(c):
        while isinstance(c, (list, tuple)) and c and isinstance(c[0], (list, tuple)):
            c = c[0]
        return c[0] if isinstance(c, (list, tuple)) and c else None

    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        x = dig(g.get("coordinates"))
        if x is not None:
            return float(x)
    return None


def _bron_lagen(layers_dir: Path) -> list[dict]:
    sys_path = str(ROOT)
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    from pipeline.geodata import feature_collection_to_wgs84
    from shapely.geometry import mapping, shape

    aliases = json.loads(ALIASES.read_text(encoding="utf-8"))
    lagen: list[dict] = []
    for zone_id, titel, fill, stroke, uitleg in _BRON_KEUZES:
        alias = aliases.get(zone_id) or {}
        bron = ROOT / alias.get("cachePath", "")
        if not bron.is_file():
            print(f"[bronnen] {zone_id} overgeslagen: cache ontbreekt ({bron})")
            continue
        doel = layers_dir / f"bron-{zone_id}.geojson"
        if not doel.is_file():
            try:
                fc = json.loads(bron.read_text(encoding="utf-8"))
                fc = fc.get("records", fc)
                if bron.stat().st_size > 2_000_000:
                    for f in fc.get("features", []):
                        g = f.get("geometry")
                        if g:
                            f["geometry"] = mapping(shape(g).simplify(5.0, preserve_topology=True))
                if fc.get("features"):
                    x = _eerste_coord(fc)
                    if x is not None and abs(x) > 180:  # RD → WGS84
                        fc = feature_collection_to_wgs84(fc)
                fc["properties"] = {"viewerNote": "display-kopie van de nationale "
                                    "pipeline-cache; autoritatieve geometrie: de cache zelf"}
                doel.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:  # nooit crashen: laag overslaan
                print(f"[bronnen] {zone_id} overgeslagen: {exc}")
                continue
        lagen.append({
            "id": f"bron-{zone_id}", "type": "geojson",
            "title": titel, "groupId": "bronnen",
            "defaultOn": False, "defaultAddToManager": True, "opacity": 55,
            "attribution": "landelijke open bronnen (plan 2 data-kalibratie)",
            "description": f"{uitleg} Rol: {alias.get('role', 'context')}.",
            "settings": {"url": f"{URL_PREFIX}/layers/bron-{zone_id}.geojson",
                         "style": {"fill": fill, "stroke": stroke}},
        })
    return lagen



PANEEL_TEMPLATE = """<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<title>Utrecht-PoC — kaart + leesbare regels</title>
<style>
 body { margin:0; display:flex; height:100vh; font:14px/1.4 -apple-system, sans-serif; }
 #kaart { flex:1; border:0; }
 #paneel { width:22%; min-width:210px; border-left:1px solid #c9c6c2; display:flex; flex-direction:column; background:#fafaf8; }
 #paneel header { padding:10px 14px; background:#1a1a1a; color:#fff; }
 #paneel header small { color:#bbb; }
 #status { padding:8px 14px; background:#eef3f8; color:#1a4a7a; font-size:13px; }
 select { margin:8px 14px; padding:6px; max-width:calc(100% - 28px); }
 #regels { flex:1; border:0; }
</style></head><body>
<iframe id="kaart" title="Kaart"></iframe>
<div id="paneel">
 <header><b>Leesbare regels &amp; wetsartikel</b><br>
  <small>klik op een zone in de kaart — of op een link in de popup — het paneel opent de regels van dat vlak</small></header>
 <div id="status">Nog geen zone gekozen — je kunt ook hieronder een scenario kiezen.</div>
 <select id="lijst"><option value="">— kies een scenario —</option></select>
 <iframe id="regels" src="about:blank" title="Leesbare regels"></iframe>
</div>
<script>
// [{file, label}] — label = éénregel-verschil t.o.v. baseline
const rapporten = __RAPPORTEN__;
const labelByFile = Object.fromEntries(rapporten.map(r => [r.file, r.label]));
const lijst = document.getElementById("lijst");
for (const r of rapporten) {
  const o = document.createElement("option");
  o.value = "/utrecht/reports/" + r.file;
  o.textContent = r.label;
  lijst.appendChild(o);
}
function labelVoor(href) {
  const file = (href || "").split("/").pop().split("?")[0];
  return labelByFile[file] || file;
}
lijst.addEventListener("change", () => {
  if (lijst.value) laadInPaneel(lijst.value, labelVoor(lijst.value));
});
const kaartFrame = document.getElementById("kaart");
// cache-buster: anders kan de browser na een rebuild de oude index.html uit cache geven
kaartFrame.src = "/index.html?config=/utrecht/config.json&refresh=" + Date.now();
function laadInPaneel(href, statusTekst) {
  const regels = document.getElementById("regels");
  document.getElementById("status").textContent = statusTekst;
  const absoluut = new URL(href, location.origin).href;
  // vergelijk zonder query (cache-buster) zodat hetzelfde rapport niet dubbel laadt
  if (regels.src.split("?")[0] !== absoluut.split("?")[0])
    regels.src = absoluut + (absoluut.includes("?") ? "&" : "?") + "bust=" + Date.now();
}
function koppel() {
  const doc = kaartFrame.contentDocument;
  if (!doc) return;
  // klik op een link in de featureInfo-popup → openen in het leespaneel, niet in een nieuw tabblad
  doc.addEventListener("click", (e) => {
    const target = e.target;
    const a = target && target.closest ? target.closest("a[href]") : null;
    if (!a) return;
    const href = a.getAttribute("href");
    if (!href || !/^(https?:\\/\\/|\\/)/i.test(href)) return;
    if (!a.closest(".fiView") && !href.includes("/utrecht/reports/")) return;
    e.preventDefault();
    e.stopPropagation();
    laadInPaneel(href, labelVoor(href));
  }, true);
  const observer = new MutationObserver(() => {
    // alléén de featureInfo-popup volgen; niet de metadata-links in Lagenbeheer
    const links = doc.querySelectorAll('.fiView a[href*="/utrecht/reports/"]');
    if (links.length) {
      const href = links[links.length - 1].getAttribute("href");
      laadInPaneel(href, labelVoor(href));
    }
  });
  observer.observe(doc.documentElement, { subtree: true, childList: true });
}
kaartFrame.addEventListener("load", koppel);
</script></body></html>"""


def main() -> int:
    layers_dir = OUT / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    # geen Leia-kopie nodig: de root (../index.html, ../_app, ../Cesium) doet al het werk

    scenario_groepen, scenario_lagen = _scenario_groep_en_lagen(layers_dir)
    whatif_groepen, whatif_lagen = _whatif_groep_en_lagen(layers_dir)
    bron_lagen = _bron_lagen(layers_dir)

    cfg = {
        "name": "ldttoolbox — Utrecht-PoC",
        "viewer": {
            "title": "Utrecht-PoC — waar kan ik wat?",
            "subTitle": "5 uitdagingen × 13 tracks × 3 scenario's (+ what-ifs), "
                        "elke claim geciteerd uit de Omgevingsverordening",
            # top-down start: de camera centreert dan gegarandeerd op Utrecht
            # (pitch -45 schuift het midden van het beeld ten noorden van de
            #  doelcoördinaat — de kaart leek 'rond Amsterdam' te hangen)
            "startPosition": {"x": 5.121, "y": 52.075, "z": 42000,
                              "heading": 0, "pitch": -45, "duration": 3},
            "startCameraMode3D": False,
        },
        "groups": [
            {"id": "achtergrond", "title": "Achtergrond", "isOpen": True},
            {"id": "d3", "title": "Gebouwcontext (3D BAG)", "isOpen": True},
            {"id": "scenario", "title": "Scenario-zones per uitdaging", "isOpen": True},
            *scenario_groepen,
            {"id": "whatif", "title": "What-if scenario's (data-gegrond)",
             "isOpen": bool(whatif_groepen)},
            *whatif_groepen,
            {"id": "bronnen", "title": "Landelijke bronlagen (kalibratie plan 2)",
             "isOpen": False},
        ],
        "layers": [
            {"id": "bg-brt", "type": "wmts", "title": "BRT Achtergrondkaart (NL)",
             "groupId": "achtergrond", "isBackground": True, "defaultOn": True,
             "attribution": "PDOK", "defaultAddToManager": True,
             "settings": {"url": BRT_WMTS, "featureName": "standaard",
                          "contentType": "image/png"}},
            # 3D BAG staat bewust standaard UIT: de tileset crashte de Cesium-
            # renderloop bij opstart (bisect 2026-10-18, [object Object]); als
            # schakelaar in Lagenbeheer probeert hij opnieuw bij het aanzetten.
            {"id": "bag3d", "type": "3dtiles", "title": "3D BAG LoD2.2 (NL-gebouwen)",
             "groupId": "d3", "defaultOn": False, "attribution": "3D BAG / TU Delft, CC-BY-4.0",
             "defaultAddToManager": True,
             "description": "3D-gebouwcontext; bij crash de schakelaar weer uit — "
                            "de tileset faalt soms afhankelijk van net/werkgeheugen.",
             "settings": {"url": BAG_3D, "enableHeightControl": True}},
            *scenario_lagen,
            *whatif_lagen,
            *bron_lagen,
        ],
        "tools": [{"id": "layerManager", "enabled": True},
                  {"id": "layerLibrary", "enabled": True},
                  {"id": "featureInfo", "enabled": True}],
    }
    # Opstart-schone kaart (NSPD-conventie): alléén de basiskaarten staan aan;
    # alles thematische staat één klik weg in Lagenbeheer.
    for laag in cfg["layers"]:
        if laag["id"] != "bg-brt":
            laag["defaultOn"] = False

    (OUT / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Leia-config: {OUT / 'config.json'} "
          f"({len(cfg['layers'])} lagen, {len(cfg['groups'])} groepen)")

    # paneel.html: viewer + apart leespaneel — klik op een zone en het rechter-
    # paneel opent de leesbare regelpagina met het wetsartikel (zelfde origin,
    # dus de parent leest de popup-DOM van de viewer via MutationObserver).
    # Labels = laagtitel / éénregel-verschil (geen technische SC-id of km²).
    label_by_file: dict[str, str] = {}
    for laag in cfg["layers"]:
        meta = laag.get("metadataUrl") or ""
        if "/reports/" not in meta:
            continue
        file = meta.rsplit("/", 1)[-1]
        label_by_file[file] = laag.get("title") or file
    for pad in (OUT / "reports").glob("*.html"):
        label_by_file.setdefault(pad.name, pad.stem.replace("-", " "))
    rapporten = [{"file": f, "label": label_by_file[f]}
                 for f in sorted(label_by_file)]
    paneel = PANEEL_TEMPLATE.replace("__RAPPORTEN__", json.dumps(rapporten, ensure_ascii=False))
    (OUT / "paneel.html").write_text(paneel, encoding="utf-8")
    print(f"paneel: {OUT / 'paneel.html'} (rapporten: {len(rapporten)})")
    print("kijk op: http://localhost:8010/index.html?config=/utrecht/config.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
