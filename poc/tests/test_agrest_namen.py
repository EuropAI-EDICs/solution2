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
