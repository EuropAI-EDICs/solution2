"""Kaart-broncache (F-kaart): deterministische VKBO-bedrijfstoewijzing,
polylijn-verdunning en cachevorm mét bronvermelding — netwerk alléén in de
expliciete cache-stap (offline doctrine)."""

import json
from pathlib import Path

import fetch_sources

POC_ROOT = Path(__file__).resolve().parents[1]

VKBO_RIJEN = [
    {"naam": "BVBA Zeilers", "straat": "Sleepstraat", "huisnr": "1", "postcode": "9000", "inschrijving": "2001-01-01"},
    {"naam": "BVBA Aannemers", "straat": "Kortrijksesteenweg", "huisnr": "10", "postcode": "9000", "inschrijving": "2005-05-05"},
    {"naam": "Loodgieterij De Vries", "straat": "Korenmarkt", "huisnr": "5", "postcode": "9000", "inschrijving": "2015-03-02"},
]


def test_bedrijf_toewijzing_is_deterministisch_en_volledig():
    personas = ("sanne", "ahmed", "maria")
    toewijzing = fetch_sources.bedrijf_toewijzing(VKBO_RIJEN, personas)
    assert fetch_sources.bedrijf_toewijzing(VKBO_RIJEN, personas) == toewijzing
    assert set(toewijzing) == set(personas)
    for pid, bedrijf in toewijzing.items():
        assert bedrijf["naam"] and "Gent" in bedrijf["adres"] and bedrijf["adres"].count(",") == 1
    adressen = [b["adres"] for b in toewijzing.values()]
    assert len(set(adressen)) == len(adressen)  # vaste offset → geen duplicaten zolang cache groot genoeg is


def test_bedrijf_toewijzing_sorteer_volgorde_is_stabiel():
    bedrijf = fetch_sources.bedrijf_toewijzing(VKBO_RIJEN, ("sanne",))["sanne"]
    assert bedrijf["naam"] == "BVBA Aannemers"  # gesorteerd op naam, offset 0


def test_dun_punten_behoudt_eindpunten_en_begrenzing():
    lang = [[float(i), 51.0] for i in range(500)]
    dun = fetch_sources.dun_punten(lang, max_punten=80)
    assert len(dun) <= 80
    assert dun[0] == lang[0] and dun[-1] == lang[-1]
    assert fetch_sources.dun_punten(lang[:5], max_punten=80) == [[float(i), 51.0] for i in range(5)]


def test_kaart_cache_vorm_en_meta(tmp_path, monkeypatch):
    """haal_kaart zonder netwerk: responses gefaked via monkeypatch; de cache
    bevat bedrijven, routes (primair + alternatief), innames-punten, grens en
    meta met bronnen/licenties en productiepaden."""
    (tmp_path / "fixtures" / "source").mkdir(parents=True)
    (tmp_path / "fixtures" / "addresses.json").write_text(json.dumps({
        "Korenmarkt 1, Gent": [3.7222201, 51.055388],
        "Koningin Maria Hendrikaplein 1, Gent": [3.7108051, 51.0360946],
    }), encoding="utf-8")
    (tmp_path / "fixtures" / "personas.json").write_text(json.dumps({"personas": [
        {"id": "sanne", "intentSlots": {"address": "Korenmarkt 1, Gent"}, "corrections": {}},
        {"id": "jeroen", "intentSlots": {"address": "Koningin Maria Hendrikaplein 1, Gent"},
         "corrections": {"address": "Korenmarkt 1, Gent"}},
    ]}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "fixtures" / "source" / "vkbo-gent.json").write_text(json.dumps(VKBO_RIJEN), encoding="utf-8")
    (tmp_path / "fixtures" / "source" / "gipod-gent.json").write_text(json.dumps(
        {"mode": "mock", "innames": [{"id": "GP-1", "straat": "Korenmarkt", "type": "grondwerk",
                                      "van": "2026-11-02", "tot": "2026-11-06"}]}), encoding="utf-8")

    def _fake_fetch(url):
        if "nominatim" in url:
            if "polygon_geojson" in url:
                return [{"geojson": {"type": "Polygon", "coordinates": [[[3.6, 51.0], [3.8, 51.0], [3.8, 51.1], [3.6, 51.0]]]}}]
            from urllib.parse import parse_qs, urlparse
            street = parse_qs(urlparse(url).query).get("street", [""])[0]
            return [{"lon": "3.718", "lat": "51.048", "addresstype": "house",
                     "display_name": f"{street}, 9000 Gent, Oost-Vlaanderen, België",
                     "address": {"road": street.rsplit(" ", 1)[0],
                                 "city": "Gent", "postcode": "9000"}}]
        if "router.project-osrm.org" in url:
            return {"routes": [
                {"distance": 871.2, "duration": 176.7, "geometry": {"coordinates": [[3.72, 51.05], [3.721, 51.055], [3.722, 51.055]]}},
                {"distance": 1079.9, "duration": 189.7, "geometry": {"coordinates": [[3.72, 51.05], [3.725, 51.052], [3.722, 51.055]]}},
            ]}
        raise AssertionError(f"onverwachte url in test: {url}")

    monkeypatch.setattr(fetch_sources, "_fetch_json", _fake_fetch)
    monkeypatch.setattr(fetch_sources, "POC_ROOT", tmp_path)
    monkeypatch.setattr(fetch_sources.time, "sleep", lambda *_: None)

    kaart = fetch_sources.haal_kaart(tmp_path, kenteken_personas=("sanne", "jeroen"))

    assert set(kaart["bedrijven"]) == {"sanne", "jeroen"}
    for pid in ("sanne", "jeroen"):
        route = kaart["routes"][pid]
        assert route["primaire"]["afstand_m"] == 871 and route["alternatief"]["afstand_m"] == 1080
        assert len(route["primaire"]["punten"]) == 3
    assert kaart["innames"][0]["coord"] and kaart["innames"][0]["bron"].startswith("gipod")
    assert kaart["grens"]["type"] == "Polygon"
    bronnen = kaart["meta"]["bronnen"]
    assert {"osrm", "nominatim", "vkbo", "gipod"} <= set(bronnen)
    assert all(b["licentie"] for b in bronnen.values())
    assert "BeSt Address" in kaart["meta"]["productiepaden"]["geocoding"]
    assert (tmp_path / "fixtures" / "source" / "kaart.json").is_file()
