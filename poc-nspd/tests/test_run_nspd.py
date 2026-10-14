import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# fase-1-tracks: corpus-shards bestaan; fase-2-tracks: curatie volgt in taken 3-7
FASE1_TRACKS = ("wind", "zon", "energietoets")
FASE2_TRACKS = ("bos", "water", "bodem", "mobiliteit", "landschap",
                "landbouw", "wonen", "werken", "recreatie", "biomassa")
ALLE_TRACKS = FASE1_TRACKS + FASE2_TRACKS

from bbox import NSPD_BBOX_WGS84  # noqa: E402
from pyproj import Transformer  # noqa: E402


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
    # de helften delen alléén de split-meridiaanrand: make_aoi.py splitst op
    # SPLIT_LON=3.73°E, waarvan de RD-projectie een schuin segment is — de twee
    # hoekpunten daarvan (op de zuid- en noordrand van de bbox, RD-x ≈ 38724.26
    # en ≈ 39885.87) zijn precies de gedeelde punten, en beide ringen zijn
    # gesloten (eerste == laatste punt)
    nl_ring = _aoi_use_case("nl")["areaOfInterest"]["geometry"]["coordinates"][0]
    be_ring = _aoi_use_case("be")["areaOfInterest"]["geometry"]["coordinates"][0]
    assert nl_ring[0] == nl_ring[-1], "NL-ring niet gesloten"
    assert be_ring[0] == be_ring[-1], "BE-ring niet gesloten"
    _t = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    split_x = {round(_t.transform(3.73, y)[0], 3) for y in (NSPD_BBOX_WGS84[1], NSPD_BBOX_WGS84[3])}
    gedeeld = {round(p[0], 3) for p in nl_ring} & {round(p[0], 3) for p in be_ring}
    assert gedeeld == split_x, gedeeld


def test_make_aoi_schrijft_alle_use_cases():
    uit = ROOT / "use-cases"
    subprocess.run([sys.executable, str(uit / "make_aoi.py")], check=True, cwd=ROOT)
    for track in ALLE_TRACKS:
        for land in ("nl", "be"):
            assert (uit / f"{track}-{land}.json").is_file()


def test_use_cases_valideren_tegen_request_schema():
    sys.path.insert(0, str(ROOT))
    from pipeline import contracts  # noqa: E402

    for track in ALLE_TRACKS:
        for land in ("nl", "be"):
            req = json.loads(
                (ROOT / "use-cases" / f"{track}-{land}.json").read_text(encoding="utf-8")
            )
            contracts.validate(req, "opportunity-map-request")
            assert req["parameters"]["aoiSourceId"] == "poc-nspd-bbox", f"{track}-{land}"
            # deterministische, jurisdictie-onderscheidene ids
            assert req["id"] != json.loads(
                (ROOT / "use-cases" / f"{track}-{'be' if land == 'nl' else 'nl'}.json").read_text(
                    encoding="utf-8"
                )
            )["id"]


def _veld_toetst(veld: str) -> str:
    return {"shard": "formal-rules", "evidence": "evidence", "normcards": "normcards"}[veld]


veld_toetst = _veld_toetst


def test_run_module_importeert_en_tracks_tabelgedreven():
    sys.path.insert(0, str(ROOT))
    import run  # noqa: E402

    verwacht = {
        f"{track}-{land}"
        for track in ALLE_TRACKS
        for land in ("nl", "be")
    }
    assert set(run.TRACKS) == verwacht
    assert len(run.TRACKS) == 26
    for key, cfg in run.TRACKS.items():
        land = key.rsplit("-", 1)[1]
        track = key.rsplit("-", 1)[0]
        assert cfg["jurisdictie"] == land
        # padpatroon geldt voor alle 26; bestandsbestaan pas ná curatie (taken 3-7)
        for veld in ("shard", "evidence", "normcards"):
            verwacht_pad = f"corpus/{veld_toetst(veld)}-{land}-{track}.json"
            assert cfg[veld] == verwacht_pad, f"{key}: {cfg[veld]} != {verwacht_pad}"
        if track in FASE1_TRACKS:
            for veld in ("shard", "evidence", "normcards"):
                assert (ROOT / cfg[veld]).is_file(), f"{key}: {cfg[veld]} ontbreekt"
    # zone-aliases: gepinde zoneIds uit bestaande formal-rules-shards geregistreerd
    for key, cfg in run.TRACKS.items():
        if not (ROOT / cfg["shard"]).is_file():
            continue  # fase-2-shards volgen in taken 3-7
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
