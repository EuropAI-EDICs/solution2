# poc/tests/test_agrest_namen.py
import json
from pathlib import Path

ART = json.loads(Path("data/agrest-namen.json").read_text())


def test_artifact_shape():
    assert ART["service"].startswith("https://agrest.geodata-utrecht.nl")
    namen = ART["namen"]
    assert isinstance(namen, list) and namen and namen == sorted(namen)
    assert all(isinstance(n, str) and n.strip() for n in namen)
    assert len(namen) == len(set(namen))


def test_known_names_present():  # regressie op bestaande tracks
    for known in ["Gebied windenergie", "Gebied zonneveld", "Landelijk gebied"]:
        assert known in ART["namen"], known


def test_fase1_alias_naam_binding():  # eindreview-belangrijk-6
    """De vijf gekozen water/bodem-NAAM's staan letterlijk in het artifact
    ÉN letterlijk als WHERE NAAM='<naam>' in het zone-register
    poc/tracks/_zone-sources.json — de alias-binding is dus
    artefact-gefilterd, niet vrij gezocht."""
    zs = json.loads(Path("tracks/_zone-sources.json").read_text())
    for naam in [
        "Waterbergingsgebied",
        "Overstroombaar gebied",
        "Vrijwaringszone regionale waterkering",
        "Grondwaterbeschermingszone",
        "Gebied gesloten stortplaats",
    ]:
        assert naam in ART["namen"], naam
        assert any(f"WHERE NAAM='{naam}'" in (e.get("note") or "") for e in zs.values()), naam


def test_fase2_alias_naam_binding():  # spiegel van de fase-1-bindingsrij
    """De elf gekozen mobiliteit/landschap-NAAM's (fase 2) staan letterlijk
    in het artifact ÉN letterlijk als WHERE NAAM='<naam>' in het
    zone-register poc/tracks/_zone-sources.json."""
    zs = json.loads(Path("tracks/_zone-sources.json").read_text())
    for naam in [
        "Beperkingengebied bouwwerken provinciale weg",
        "Geluidcontour buiten de bebouwde kom",
        "Geluidcontour binnen de bebouwde kom",
        "Beperkingengebied lokale spoorweg",
        "Luchtvaartterrein",
        "UNESCO Werelderfgoed Hollandse Waterlinies",
        "UNESCO Werelderfgoed Neder-Germaanse Limes (kernzone)",
        "UNESCO Werelderfgoed Neder-Germaanse Limes (bufferzone)",
        "Gebied cultuurhistorische hoofdstructuur",
        "Landschap",
        "Gebied aardkundige waarden",
    ]:
        assert naam in ART["namen"], naam
        assert any(f"WHERE NAAM='{naam}'" in (e.get("note") or "") for e in zs.values()), naam
