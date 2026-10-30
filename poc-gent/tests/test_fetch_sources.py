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
