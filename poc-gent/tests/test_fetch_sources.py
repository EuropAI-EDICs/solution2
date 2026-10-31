"""Normalisatielogica van de broncache-bouw (F1.5): filter op de officiële
autovrij-afbakening en versie-tagging per laag."""

import fetch_sources


def _feature(autovrijgebied=None):
    geometry = {"type": "Polygon", "coordinates": [[[3.72, 51.05], [3.73, 51.05], [3.73, 51.06], [3.72, 51.06], [3.72, 51.05]]]}
    return {"type": "Feature", "geometry": geometry, "properties": {"naam": "test", "autovrijgebied": autovrijgebied}}


def test_autovrij_filter_houdt_alleen_officiele_autovrijgebieden():
    features = fetch_sources.normaliseer(
        "gent-autovrij",
        [_feature("Autovrij gebied 1"), _feature(None), _feature("Autovrij gebied 4")],
        "stad-gent-open-data 2026-09-30",
    )
    assert len(features) == 2
    assert all(f["properties"]["layer"] == "gent-autovrij" for f in features)
    assert all(f["properties"]["versie"] == "stad-gent-open-data 2026-09-30" for f in features)


def test_lez_normalisatie_tagt_alle_features_zonder_filter():
    features = fetch_sources.normaliseer("gent-lez", [_feature(None), _feature(None)], "stad-gent-open-data 2026-06-30")
    assert len(features) == 2
    assert all(f["properties"]["layer"] == "gent-lez" for f in features)


def test_straatnaam_norm_stript_nummer_gemeente_en_diakritiek():
    assert fetch_sources.straatnaam_norm("Veldstraat 1, Gent") == "veldstraat"
    assert fetch_sources.straatnaam_norm("Koningin Maria Hendrikaplein 12 bus 3, Gent") == "koningin maria hendrikaplein"
    assert fetch_sources.straatnaam_norm("Ottergemsesteenweg-Zuid 1, Gent") == "ottergemsesteenweg-zuid"


def test_vatten_afval_deterministisch_uit_rijen():
    rijen = [{"fracties": "PMD", "datum": "2026-10-06"},
             {"fracties": "PMD", "datum": "2026-10-13"},
             {"fracties": "REST", "datum": "2026-10-07"},
             {"fracties": "GLAS, PAPIER", "datum": "2026-10-08"},
             {"fracties": "GFT, GROFVUIL, PAPIER, PMD", "datum": "05/05/2026"},
             # feestdagverschuiving: zelfde fractie op een afwijkende weekdag
             {"fracties": "PMD", "datum": "2026-10-21"}]
    uit = fetch_sources.vatten_afval(rijen)
    assert uit["afvalPmd"]["dag"] == "dinsdag"          # modus: 3× dinsdag vs 1× woensdag
    assert uit["afvalPmd"]["aantal"] == 4
    assert uit["afvalPmd"]["eerste"] == "2026-05-05"
    assert uit["afvalPmd"]["dagen"] == ["dinsdag", "woensdag"]
    assert uit["afvalRest"]["dag"] == "woensdag"
    assert uit["afvalGlas"]["eerste"] == "2026-10-08"
    assert uit["afvalPapier"]["eerste"] == "2026-05-05"
    assert uit["afvalGft"]["dag"] == "dinsdag"
    assert "afvalGrofvuil" not in uit  # geen slot voor grofvuil in het burgerpakket


def test_vatten_afval_filtert_op_huisnummerbereik():
    rijen = [
        {"fracties": "REST", "datum": "2026-10-07"},                                  # hele straat
        {"fracties": "REST", "datum": "2026-10-14", "even_van": 2, "even_tot": 100},  # even zijde
        {"fracties": "REST", "datum": "2026-10-15", "on_van": 1, "on_tot": 99},       # oneven zijde
    ]
    oneven = fetch_sources.vatten_afval(rijen, huisnummer=1)
    assert oneven["afvalRest"]["aantal"] == 2          # hele straat + oneven
    even = fetch_sources.vatten_afval(rijen, huisnummer=10)
    assert even["afvalRest"]["aantal"] == 2            # hele straat + even
