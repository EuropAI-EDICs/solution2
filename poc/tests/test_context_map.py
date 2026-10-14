"""Context-map generator — offline, op fixtures.

De contextpagina's zijn besluit-ondersteuning: de control-zone (juridisch)
plus contextlagen die expliciet 'context — geen juridische zone' dragen.
Alle tests draaien zonder netwerk en zonder de (gitignored) nationale cache:
``nd.CACHE`` wordt naar ``tmp_path`` gezet, precies zoals in
test_national_data.py.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import context_map as cm  # noqa: E402
from pipeline import national_data as nd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "national"
EMPTY_FC = '{"type": "FeatureCollection", "features": []}'


# --------------------------------------------------------------------------- #
# context_layers — cache-waarnemend, nooit netwerk, elke bron verantwoord
# --------------------------------------------------------------------------- #

def test_context_layers_voor_uitdaging(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    # netcongestie-fixture op de verwachte plek (nd.CACHE = tmp_path)
    nc = tmp_path / "netcongestie" / "netcongestie.geojson"
    nc.parent.mkdir(parents=True)
    nc.write_text(EMPTY_FC)
    layers = cm.context_layers("energietransitie")
    names = [l["name"] for l in layers]
    assert "Netcongestie (context)" in names
    assert all(l["legal"] is False for l in layers)


def test_context_layers_tekent_aanwezige_bron_als_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    nc = tmp_path / "netcongestie" / "netcongestie.geojson"
    nc.parent.mkdir(parents=True)
    nc.write_text((FIXTURES / "netcongestie_sample.json").read_text())
    (layer,) = [l for l in cm.context_layers("energietransitie")
                if l["name"] == "Netcongestie (context)"]
    fc = json.loads(layer["geojson"])
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) == 1
    assert layer["legal"] is False
    assert "1 object" in layer["status"]  # aantal getekende objecten in de legenda


def test_context_layers_meldt_ontbrekende_bronnen_als_status(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)  # lege cache: geen enkele bron aanwezig
    layers = cm.context_layers("landschap-infra")
    assert layers, "elke geconfigureerde bron komt terug — als laag óf als status-regel"
    for l in layers:
        assert l["legal"] is False
        assert l["geojson"] == ""      # niets te tekenen …
        assert l["status"]             # … maar wél verantwoord in de legenda
    names = {l["name"] for l in layers}
    assert {"Rijksmonumenten (context)", "Spoorlijnen ProRail (context)"} <= names


def test_cbs_grid_komt_als_legenda_status_niet_als_laag(tmp_path, monkeypatch):
    """Grid-besluit: 18k cellen gaan niet als puntwolk de pagina in; de
    legenda vermeldt de cache-status (aantal cellen) in plaats daarvan."""
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    grid = tmp_path / "cbs-grid-kerncijfers-100m.json"
    grid.write_text(json.dumps({"sourceId": "cbs-grid-kerncijfers-100m", "records": [
        {"crs28992res100m": "E1300N4400", "aantal_inwoners": 5},
        {"crs28992res100m": "E1301N4400", "aantal_inwoners": 7}]}))
    layers = cm.context_layers("wonen-werken")
    grid_l = next(l for l in layers if l["name"] == "CBS 100m-kerncijfers (context)")
    assert grid_l["geojson"] == "" and grid_l["legal"] is False
    assert "2 cellen" in grid_l["status"] and "niet op de kaart" in grid_l["status"]


def test_onbekende_uitdaging_geeft_lege_lijst(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    assert cm.context_layers("bestaat-niet") == []


# --------------------------------------------------------------------------- #
# prepare_fc — RD/WGS84 → WGS84, geclipt op de Utrecht-AOI, vereenvoudigd
# --------------------------------------------------------------------------- #

def test_prepare_fc_reprojecteert_clipt_en_rondt_af():
    # RD-lijn die deels buiten de Utrecht-bbox ligt (x < 130000) → geclipt
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"wegnummer": "N201", "wvkId": 1},
         "geometry": {"type": "LineString", "coordinates": [[120000, 450000], [140000, 450000]]}},
        {"type": "Feature", "properties": {"wegnummer": "buiten"},   # volledig buiten de AOI
         "geometry": {"type": "LineString", "coordinates": [[100000, 400000], [110000, 400000]]}},
        {"type": "Feature", "properties": {}, "geometry": None}]}    # geen geometrie
    out = cm.prepare_fc(fc, crs="rd", tolerance_m=10, keep=["wegnummer"])
    assert out["type"] == "FeatureCollection" and len(out["features"]) == 1
    f = out["features"][0]
    assert f["properties"] == {"wegnummer": "N201"}        # alleen de whitelist
    coords = f["geometry"]["coordinates"]
    lons, lats = [c[0] for c in coords], [c[1] for c in coords]
    assert all(4.9 < lon < 5.6 and 51.9 < lat < 52.3 for lon, lat in zip(lons, lats))
    # geclipt op RD x=130000; pyproj: RD(130000, 450000) = (5.022846, 52.037765)
    assert min(lons) == pytest.approx(5.0228, abs=1e-3)
    # 5 decimalen (~1 m): compact en sub-pixel tot zoom ~15
    assert all(len(str(v).split(".")[1]) <= 5 for v in lons + lats)


def test_prepare_fc_accepteert_wgs84_invoer():
    fc = json.loads((FIXTURES / "netcongestie_sample.json").read_text())
    out = cm.prepare_fc(fc, crs="wgs84", tolerance_m=25, keep=["netgebied"])
    assert len(out["features"]) == 1
    assert out["features"][0]["properties"] == {"netgebied": "Utrecht-Stad"}
    ring = out["features"][0]["geometry"]["coordinates"][0]
    assert min(p[0] for p in ring) == pytest.approx(5.05, abs=1e-4)


# --------------------------------------------------------------------------- #
# render_html — toggle, label, legenda; status-regels zonder overlay
# --------------------------------------------------------------------------- #

def test_html_legt_toggle_en_label_vast(tmp_path):
    html = cm.render_html("Energietransitie", control_geojson=EMPTY_FC,
                          layers=[{"name": "Netcongestie (context)", "geojson": EMPTY_FC,
                                   "color": "#c0392b", "legal": False}])
    assert "context" in html.lower()
    assert "geen juridische zone" in html
    assert "overlay" in html.lower() or "toggled" in html.lower()
    (tmp_path / "x.html").write_text(html)  # schrijft zonder fout


def test_html_zet_status_in_legenda_zonder_overlay():
    drawable = {"name": "Netcongestie (context)", "geojson": EMPTY_FC, "color": "#c0392b", "legal": False}
    status = {"name": "CBS 100m-kerncijfers (context)", "geojson": "", "color": "#2980b9",
              "legal": False, "status": "cache aanwezig — niet op de kaart"}
    assert cm.split_layers([drawable, status]) == ([drawable], [status])
    html = cm.render_html("Wonen & Werken", control_geojson=EMPTY_FC, layers=[drawable, status])
    assert "niet op de kaart" in html                       # status-regel in de legenda …
    assert html.count('"Netcongestie (context)"') >= 1       # … overlay-data alleen voor de tekenbare laag
    assert "Wonen &amp; Werken" in html                      # titel HTML-ge-escaped


def test_html_benoemt_run_en_disclaimer():
    html = cm.render_html("Energietransitie", control_geojson=EMPTY_FC, layers=[],
                          run_id="20261013T193408Z-wind-scen")
    assert "20261013T193408Z-wind-scen" in html
    assert "juridisch advies" in html                        # besluit-ondersteuning, geen advies
    assert "vereenvoudigd" in html                           # weergave-tolerantie benoemd


def test_html_escapt_script_sluiter_in_data():
    # '</script>' in een property mag de pagina niet breken (json → \u003c)
    fc = json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"naam": "</script><b>x"},
         "geometry": {"type": "Point", "coordinates": [5.1, 52.1]}}]})
    html = cm.render_html("T", control_geojson=fc, layers=[])
    assert "</script><b>x" not in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node niet beschikbaar")
def test_gerenderde_js_is_syntactisch_geldig(tmp_path):
    """Plan-1-task-10-stijl: het inline-script van een gerenderde pagina moet
    door `node --check` komen (vangt kapotte accolade-escapes in de template)."""
    layers = [{"name": "Netcongestie (context)", "geojson": EMPTY_FC, "color": "#c0392b", "legal": False,
               "styleBy": {"prop": "afname", "palette": {"3": "#c0392b"}}, "popup": ["afname"]},
              {"name": "CBS 100m-kerncijfers (context)", "geojson": "", "color": "#2980b9",
               "legal": False, "status": "x"}]
    html = cm.render_html("Energietransitie", control_geojson=EMPTY_FC, layers=layers, run_id="r")
    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    assert scripts, "inline script ontbreekt"
    js = tmp_path / "page.js"
    js.write_text("\n".join(scripts), encoding="utf-8")
    subprocess.run(["node", "--check", str(js)], check=True)


# --------------------------------------------------------------------------- #
# main — één pagina per uitdaging, in de map die het dashboard serveert
# --------------------------------------------------------------------------- #

def test_out_dir_is_de_simulation_map_van_het_dashboard():
    # dashboard.html laadt simulationPages via /simulation/<path>; live_server
    # serveert dat pad uit nldt/simulation — dáár moeten de pagina's dus staan
    # (deep-agents/runs/ is gitignored en wordt níet onder /simulation/ geserveerd).
    assert cm.OUT_DIR == cm.REPO / "nldt" / "simulation"
    assert cm.OUT_DIR.is_dir()


def test_main_schrijft_een_pagina_per_uitdaging(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path / "cache")          # lege cache → alleen status-regels
    monkeypatch.setattr(cm, "OUT_DIR", tmp_path / "out")
    runs = tmp_path / "scenario-runs"
    ctl = runs / "run-a" / "scenarios" / "CONTROL.geojson"
    ctl.parent.mkdir(parents=True)
    ctl.write_text((FIXTURES / "netcongestie_sample.json").read_text())  # een WGS84-polygoon volstaat
    monkeypatch.setattr(cm, "SCENARIO_RUNS", runs)
    monkeypatch.setattr(cm, "UITDAGINGEN", {
        "uitdagingen": [{"id": "energietransitie", "titel": "Energietransitie", "tracks": ["wind"]},
                        {"id": "water-bodem", "titel": "Water & Bodem", "tracks": ["water"]}],
        "scenarioRuns": {"wind": "run-a"}})                          # 'water' heeft géén run → lege control
    assert cm.main() == 0
    paden = sorted(p.name for p in (tmp_path / "out").glob("utrecht-context-*.html"))
    assert paden == ["utrecht-context-energietransitie.html", "utrecht-context-water-bodem.html"]
    et = (tmp_path / "out" / "utrecht-context-energietransitie.html").read_text()
    assert "geen juridische zone" in et and "run-a" in et
    wb = (tmp_path / "out" / "utrecht-context-water-bodem.html").read_text()
    assert "geen control-zone" in wb                                 # ontbrekende run eerlijk benoemd
