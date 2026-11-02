"""Kotregister: echte-data-cache uit de publieke Kotatgent-kotenzoeker,
adres-status met normalisatie, en fixture-prioriteit in de magda-mock."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters import kotregister, magda_mock  # noqa: E402

POC_ROOT = Path(__file__).resolve().parents[1]

MANIFEST = {"authenticSources": [
    {"slot": "bestaandeMelding", "source": "gent:kotregister", "purpose": "p"}
]}


def _cache(tmp_path, koten):
    (tmp_path / "fixtures" / "source").mkdir(parents=True, exist_ok=True)
    (tmp_path / "fixtures" / "source" / "kotregister.json").write_text(json.dumps(
        {"bron": "test", "koten": koten}, ensure_ascii=False), encoding="utf-8")


def test_bekend_adres_is_gemeld_met_normalisatie(tmp_path):
    _cache(tmp_path, [{"titel": "studio - Rodelijvekensstraat 106", "adres": "Rodelijvekensstraat 106"}])
    assert kotregister.status_voor(tmp_path, "rodelijvekensstraat 106, Gent") == {"status": "gemeld"}
    assert kotregister.status_voor(tmp_path, "RODELIJVEKENSSTRAAT 106") == {"status": "gemeld"}


def test_onbekend_adres_is_nieuw(tmp_path):
    _cache(tmp_path, [{"adres": "Rodelijvekensstraat 106"}])
    assert kotregister.status_voor(tmp_path, "Overpoortstraat 1, Gent") == {"status": "nieuw"}
    assert kotregister.status_voor(tmp_path, None) == {"status": "nieuw"}


def test_echte_cache_dekt_de_beschikbare_advertenties():
    register = kotregister.laad_register(POC_ROOT)
    assert register["totaalInDatabase"] >= 5000       # volledige database (5.130)
    assert len(register["koten"]) >= 90               # beschikbare advertenties (106)
    assert all(kot["adres"] for kot in register["koten"])


def test_magda_fallback_op_cache_en_fixture_wint(tmp_path, monkeypatch):
    _cache(tmp_path, [{"adres": "Rodelijvekensstraat 106"}])
    (tmp_path / "fixtures").mkdir(exist_ok=True)
    (tmp_path / "fixtures" / "magda.json").write_text(json.dumps(
        {"personas": {"saartje": {"gent:kotregister": {"status": "gemeld"}}}}), encoding="utf-8")
    context = {"address": "Overpoortstraat 1, Gent"}
    # geen fixture voor deze persona → cache-backing: Overpoortstraat is niet gepubliceerd
    assert magda_mock.raadpleeg(MANIFEST, "gent:kotregister", "p", tmp_path, "wouter",
                                context=context) == {"status": "nieuw"}
    # adres uit het echte register → gemeld
    context_regel = {"address": "Rodelijvekensstraat 106, Gent"}
    assert magda_mock.raadpleeg(MANIFEST, "gent:kotregister", "p", tmp_path, "wouter",
                                context=context_regel) == {"status": "gemeld"}
    # fixture-record wint boven de cache (bewuste edge-persona)
    assert magda_mock.raadpleeg(MANIFEST, "gent:kotregister", "p", tmp_path, "saartje",
                                context=context) == {"status": "gemeld"}
    # zonder context-adres géén cache-lookup: gewone KeyError
    try:
        magda_mock.raadpleeg(MANIFEST, "gent:kotregister", "p", tmp_path, "wouter")
        raise AssertionError("KeyError verwacht zonder context")
    except KeyError:
        pass
