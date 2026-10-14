import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bbox import NSPD_BBOX_WGS84  # noqa: E402


def _aoi_use_case(land: str) -> dict:
    pad = ROOT / "use-cases" / f"wind-{land}.json"
    return json.loads(pad.read_text(encoding="utf-8"))


def test_use_cases_bestaan_en_aoi_in_landing():
    for land in ("nl", "be"):
        req = _aoi_use_case(land)
        ring = req["areaOfInterest"]["geometry"]["coordinates"][0]
        xs = [p[0] for p in ring]
        # RD-x van de jurisdictie-helften (bbox 3.45–3.88°E gesplitst op 3.73°E):
        # NL-helft x ≈ 19.100–39.900, BE-helft x ≈ 38.700–50.300. (De schatting
        # "30.000–60.000" uit de task-brief dekte de echte hoekpunten niet; de
        # grenzen hieronder zijn de werkelijke, deterministisch getransformeerde
        # bbox-hoeken met marge.)
        if land == "nl":
            assert all(18000 < x < 45000 for x in xs)
        else:
            assert all(35000 < x < 60000 for x in xs)
        assert req["areaOfInterest"]["crs"] == "EPSG:28992"
    # de helften delen de split-meridiaanrand: de RD-projectie van 3.73°E is een
    # schuin segment, beide hoekpunten daarvan zitten in beide ringen
    nl_xs = {p[0] for p in _aoi_use_case("nl")["areaOfInterest"]["geometry"]["coordinates"][0]}
    be_xs = {p[0] for p in _aoi_use_case("be")["areaOfInterest"]["geometry"]["coordinates"][0]}
    gedeeld = nl_xs & be_xs
    assert len(gedeeld) == 2 and gedeeld == (nl_xs & be_xs)


def test_make_aoi_schrijft_zes_use_cases(tmp_path):
    uit = ROOT / "use-cases"
    subprocess.run([sys.executable, str(uit / "make_aoi.py")], check=True, cwd=ROOT)
    for track in ("wind", "zon", "energietoets"):
        for land in ("nl", "be"):
            assert (uit / f"{track}-{land}.json").is_file()


def test_use_cases_valideren_tegen_request_schema():
    sys.path.insert(0, str(ROOT))
    from pipeline import contracts  # noqa: E402

    for track in ("wind", "zon", "energietoets"):
        for land in ("nl", "be"):
            req = json.loads(
                (ROOT / "use-cases" / f"{track}-{land}.json").read_text(encoding="utf-8")
            )
            contracts.validate(req, "opportunity-map-request")
            # deterministische, jurisdictie-onderscheidene ids
            assert req["id"] != json.loads(
                (ROOT / "use-cases" / f"{track}-{'be' if land == 'nl' else 'nl'}.json").read_text(
                    encoding="utf-8"
                )
            )["id"]


def test_run_module_importeert_en_tracks_tabelgedreven():
    sys.path.insert(0, str(ROOT))
    import run  # noqa: E402

    verwacht = {
        f"{track}-{land}"
        for track in ("wind", "zon", "energietoets")
        for land in ("nl", "be")
    }
    assert set(run.TRACKS) == verwacht
    for key, cfg in run.TRACKS.items():
        # geen lege entries: elke track wijst op bestaande corpus-shards
        for veld in ("shard", "evidence", "normcards"):
            assert (ROOT / cfg[veld]).is_file(), f"{key}: {cfg[veld]} ontbreekt"
        assert cfg["jurisdictie"] == key.rsplit("-", 1)[1]
    # zone-aliases: gepinde zoneIds uit de formal-rules-shards moeten geregistreerd zijn
    for key, cfg in run.TRACKS.items():
        regels = json.loads((ROOT / cfg["shard"]).read_text(encoding="utf-8"))
        for r in regels:
            for zid in (r.get("zoneSelector") or {}).get("zoneIds") or []:
                assert zid in run.ZONE_SOURCES, f"{key}: zoneId {zid} niet in ZONE_SOURCES"


def test_v2b_gate_wire():
    sys.path.insert(0, str(ROOT))
    import json as _json

    from pipeline.jurisdictie_gate import run_v2b  # noqa: E402

    document_registry = _json.loads(
        (ROOT / "corpus" / "sources.json").read_text(encoding="utf-8")
    )
    sources_registry = _json.loads(
        (ROOT / "data" / "sources.json").read_text(encoding="utf-8")
    )
    for land in ("nl", "be"):
        normcards = _json.loads(
            (ROOT / "corpus" / f"normcards-{land}-wind.json").read_text(encoding="utf-8")
        )
        formal = _json.loads(
            (ROOT / "corpus" / f"formal-rules-{land}-wind.json").read_text(encoding="utf-8")
        )
        res = run_v2b(
            normcards=normcards,
            formal_rules=formal,
            sources_registry=sources_registry,
            document_registry=document_registry,
            jurisdictie=land,
            strict=True,
        )
        assert res["status"] == "pass"
